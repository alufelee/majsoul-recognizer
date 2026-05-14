"""文字识别器

使用 RapidOCR (ONNX Runtime) 进行文字识别。
针对雀魂游戏画面的特点做预处理：对比度增强、灰度化、二值化。
"""

import logging
import re
from pathlib import Path

import cv2
import numpy as np

from majsoul_recognizer.types import RoundInfo

logger = logging.getLogger(__name__)

# 风位映射
_WIND_MAP = {
    "东": "东", "東": "东",
    "南": "南",
}

# 局数映射
_NUMBER_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4,
    "1": 1, "2": 2, "3": 3, "4": 4,
}

# "本场" 关键字变体
_HONBA_KEYWORDS = ["本场", "本場"]

# "供托" 关键字变体
_KYOTAKU_KEYWORDS = ["供托", "供託"]

# 分数范围
_SCORE_MIN = -99999
_SCORE_MAX = 200000

# 分数区域允许的字符
_SCORE_CHARS = set("0123456789,.-")
# 局次区域允许的字符
_ROUND_CHARS = set("东東南一二三四0123456789本场供托託")
# 计时器区域允许的字符
_TIMER_CHARS = set("0123456789:")


def _filter_chars(text: str, allowed: set[str]) -> str:
    """过滤只保留允许的字符"""
    return "".join(c for c in text if c in allowed)


def _parse_score_text(text: str) -> int | None:
    """分数后处理"""
    text = text.strip()
    if not text:
        return None

    is_negative = text.startswith("-")
    cleaned = text.replace(" ", "").replace(",", "")
    digits = re.sub(r"[^0-9]", "", cleaned)
    if not digits:
        return None

    score = int(digits)
    if is_negative:
        score = -score

    if score < _SCORE_MIN or score > _SCORE_MAX:
        return None
    return score


def _parse_round_text(text: str) -> RoundInfo | None:
    """局次后处理"""
    wind = None
    number = None
    honba = 0
    kyotaku = 0

    for char in text:
        if char in _WIND_MAP:
            wind = _WIND_MAP[char]
            break

    for char in text:
        if char in _NUMBER_MAP:
            number = _NUMBER_MAP[char]
            break

    if wind is None or number is None:
        return None

    for kw in _HONBA_KEYWORDS:
        idx = text.find(kw)
        if idx > 0:
            prefix = text[:idx]
            digits = re.sub(r"[^0-9]", "", prefix)
            if digits:
                honba = int(digits[-3:])
            break

    for kw in _KYOTAKU_KEYWORDS:
        idx = text.find(kw)
        if idx > 0:
            prefix = text[:idx]
            digits = re.sub(r"[^0-9]", "", prefix)
            if digits:
                kyotaku = int(digits[-3:])
            break

    return RoundInfo(wind=wind, number=number, honba=honba, kyotaku=kyotaku)


def _parse_timer_text(text: str) -> int | None:
    """倒计时后处理"""
    text = text.strip()
    if not text:
        return None

    if ":" in text:
        parts = text.split(":")
        if len(parts) == 2:
            try:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            except ValueError:
                return None

    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return None
    return int(digits)


def _preprocess_for_ocr(image: np.ndarray, enhance_contrast: bool = True) -> np.ndarray:
    """游戏画面文字预处理

    雀魂文字通常为浅色（白/黄/红）配暗色背景或半透明背景。
    策略：CLAHE 对比度增强 → 灰度 → Otsu 二值化。
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if enhance_contrast:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


class TextRecognizer:
    """文字识别器"""

    def __init__(self, model_dir: str | None = None):
        # model_dir 保留接口兼容，RapidOCR 自动管理模型
        self._ocr = None

    def _ensure_ocr(self):
        if self._ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._ocr = RapidOCR()
            except ImportError:
                logger.warning("RapidOCR not available, text recognition disabled")
                self._ocr = False
        return self._ocr if self._ocr is not False else None

    def recognize_score(self, image: np.ndarray) -> int | None:
        """识别分数区域"""
        if image is None or image.size == 0:
            return None
        text = self._run_ocr(image)
        if text is None:
            return None
        text = _filter_chars(text, _SCORE_CHARS)
        return _parse_score_text(text)

    def recognize_round(self, image: np.ndarray) -> RoundInfo | None:
        """识别局次信息"""
        if image is None or image.size == 0:
            return None
        text = self._run_ocr(image, enhance_contrast=True)
        if text is None:
            return None
        text = _filter_chars(text, _ROUND_CHARS)
        return _parse_round_text(text)

    def recognize_timer(self, image: np.ndarray) -> int | None:
        """识别倒计时"""
        if image is None or image.size == 0:
            return None
        if image.shape[0] < 5 or image.shape[1] < 5:
            return None
        text = self._run_ocr(image)
        if text is None:
            return None
        text = _filter_chars(text, _TIMER_CHARS)
        return _parse_timer_text(text)

    def _run_ocr(self, image: np.ndarray, enhance_contrast: bool = True) -> str | None:
        """执行 OCR 推理"""
        ocr = self._ensure_ocr()
        if ocr is None:
            return None
        try:
            binary = _preprocess_for_ocr(image, enhance_contrast)
            result, _ = ocr(binary, use_cls=False)
            if result:
                texts = [item[1] for item in result]
                return " ".join(texts)
            # 二值化失败时尝试原图
            result2, _ = ocr(image, use_cls=False)
            if result2:
                texts = [item[1] for item in result2]
                return " ".join(texts)
        except Exception as e:
            logger.warning("OCR failed: %s", e)
        return None
