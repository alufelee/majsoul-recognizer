"""文字识别器"""

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

def _parse_score_text(text: str, score_min: int = -99999, score_max: int = 200000) -> int | None:
    """分数后处理"""
    text = text.strip()
    if not text:
        return None

    is_negative = text.startswith("-")
    # 提取连续数字
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return None

    score = int(digits)
    if is_negative:
        score = -score

    if score < score_min or score > score_max:
        return None
    return score


def _parse_round_text(text: str) -> RoundInfo | None:
    """局次后处理"""
    wind = None
    number = None
    honba = 0
    kyotaku = 0

    # 匹配风位
    for char in text:
        if char in _WIND_MAP:
            wind = _WIND_MAP[char]
            break

    # 匹配局数
    for char in text:
        if char in _NUMBER_MAP:
            number = _NUMBER_MAP[char]
            break

    if wind is None or number is None:
        return None

    # 匹配本场
    for kw in _HONBA_KEYWORDS:
        idx = text.find(kw)
        if idx > 0:
            prefix = text[:idx]
            digits = re.sub(r"[^0-9]", "", prefix)
            if digits:
                honba = int(digits[-3:])  # 最多3位
            break

    # 匹配供托
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

    # 处理 MM:SS 格式
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


class TextRecognizer:
    """文字识别器"""

    def __init__(self, model_dir: Path | str | None = None,
                 score_min: int = -99999, score_max: int = 200000):
        self._model_dir = model_dir
        self._score_min = score_min
        self._score_max = score_max
        # 延迟初始化：每种识别场景使用独立的 OCR 实例，配合对应的字典文件
        self._score_ocr = None
        self._round_ocr = None
        self._timer_ocr = None

    def _get_dict_path(self, dict_name: str) -> str | None:
        """获取字典文件路径"""
        # 开发模式：相对于 recognition 模块的上级目录
        dev_path = Path(__file__).parent.parent / "ocr_dicts" / dict_name
        if dev_path.exists():
            return str(dev_path)
        # 安装模式：通过 importlib.resources 查找
        try:
            import importlib.resources
            ref = importlib.resources.files("majsoul_recognizer").joinpath(f"ocr_dicts/{dict_name}")
            if ref.is_file():
                return str(ref)
        except Exception:
            pass
        return None

    def _create_ocr(self, dict_name: str | None = None):
        """创建 PaddleOCR 实例，可选指定字典文件实现字符白名单过滤"""
        try:
            from paddleocr import PaddleOCR
            kwargs = dict(
                use_angle_cls=False,
                lang="ch",
                use_gpu=False,
                show_log=False,
            )
            if self._model_dir:
                kwargs["det_model_dir"] = self._model_dir
            dict_path = self._get_dict_path(dict_name) if dict_name else None
            if dict_path:
                kwargs["rec_char_dict_path"] = dict_path
            return PaddleOCR(**kwargs)
        except ImportError:
            logger.warning("PaddleOCR not available, text recognition disabled")
            return None
        except Exception as e:
            logger.warning("Failed to initialize PaddleOCR: %s", e)
            return None

    def recognize_score(self, image: np.ndarray) -> int | None:
        """识别分数区域"""
        if image is None or image.size == 0:
            return None
        if self._score_ocr is None:
            self._score_ocr = self._create_ocr("score_dict.txt")
        if self._score_ocr is None:
            return None
        text = self._run_ocr(image, self._score_ocr)
        if text is None:
            return None
        return _parse_score_text(text, self._score_min, self._score_max)

    def recognize_round(self, image: np.ndarray) -> RoundInfo | None:
        """识别局次信息"""
        if image is None or image.size == 0:
            return None
        if self._round_ocr is None:
            self._round_ocr = self._create_ocr("round_dict.txt")
        if self._round_ocr is None:
            return None
        text = self._run_ocr(image, self._round_ocr)
        if text is None:
            return None
        return _parse_round_text(text)

    def recognize_timer(self, image: np.ndarray) -> int | None:
        """识别倒计时"""
        if image is None or image.size == 0:
            return None
        if image.shape[0] < 5 or image.shape[1] < 5:
            return None
        if self._timer_ocr is None:
            self._timer_ocr = self._create_ocr("timer_dict.txt")
        if self._timer_ocr is None:
            return None
        text = self._run_ocr(image, self._timer_ocr)
        if text is None:
            return None
        return _parse_timer_text(text)

    def _run_ocr(self, image: np.ndarray, ocr) -> str | None:
        """执行 OCR 推理"""
        if ocr is None:
            return None
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            result = ocr.ocr(binary, cls=False)
            if result and result[0]:
                texts = [line[1][0] for line in result[0] if line[1]]
                return " ".join(texts)
        except Exception as e:
            logger.warning("OCR failed: %s", e)
        return None
