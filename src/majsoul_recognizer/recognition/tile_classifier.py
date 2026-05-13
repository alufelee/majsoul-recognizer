"""ViT 牌面分类器

使用 pjura/mahjong_soul_vision ViT 模型对单张牌面裁剪图进行分类。
"""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# pjura/mahjong_soul_vision label → 项目标准 tile_code
_PJURA_TO_TILE_CODE: dict[str, str] = {
    # 索子 (bamboo): 1b-9b → 1s-9s
    **{f"{i}b": f"{i}s" for i in range(1, 10)},
    # 万子 (numbers): 1n-9n → 1m-9m
    **{f"{i}n": f"{i}m" for i in range(1, 10)},
    # 筒子 (pins): 1p-9p → 1p-9p
    **{f"{i}p": f"{i}p" for i in range(1, 10)},
    # 风牌 (winds)
    "ew": "1z", "sw": "2z", "ww": "3z", "nw": "4z",
    # 三元牌 (dragons)
    "wd": "5z", "gd": "6z", "rd": "7z",
}

_PER_SUIT_THRESHOLD: dict[str, float] = {
    "5m": 0.08,  # 万子: 红色笔画面积最小
    "5p": 0.12,  # 筒子: 红色圆点面积中等
    "5s": 0.15,  # 索子: 红色竹子面积最大
}


def _is_red_dora(
    crop: np.ndarray | None,
    tile_code: str,
    threshold: float | None = None,
) -> bool:
    """检测裁剪图是否为赤宝牌（红色标记）"""
    if crop is None or (hasattr(crop, "size") and crop.size == 0):
        return False
    if crop.ndim != 3 or crop.shape[2] != 3:
        return False

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask_lo = cv2.inRange(hsv, np.array([0, 120, 120]), np.array([10, 255, 255]))
    mask_hi = cv2.inRange(hsv, np.array([170, 120, 120]), np.array([180, 255, 255]))
    red_mask = mask_lo | mask_hi
    total_pixels = crop.shape[0] * crop.shape[1]
    red_ratio = cv2.countNonZero(red_mask) / total_pixels
    thresh = threshold if threshold is not None else _PER_SUIT_THRESHOLD.get(tile_code, 0.10)
    return red_ratio > thresh

import os
os.environ.setdefault("USE_TF", "No")
os.environ.setdefault("USE_JAX", "No")

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

try:
    from transformers import ViTForImageClassification, ViTImageProcessor
    _HAS_TRANSFORMERS = True
except ImportError:
    _HAS_TRANSFORMERS = False


class TileClassifier:
    """ViT 单牌分类器"""

    def __init__(self, model_name_or_path: str = "pjura/mahjong_soul_vision"):
        if not _HAS_TORCH or not _HAS_TRANSFORMERS:
            raise ImportError(
                "TileClassifier requires torch and transformers. "
                "Install with: pip install torch transformers"
            )
        self._model = ViTForImageClassification.from_pretrained(model_name_or_path)
        self._processor = ViTImageProcessor.from_pretrained(model_name_or_path)
        self._model.eval()
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        logger.info("TileClassifier loaded from %s (device=%s)", model_name_or_path, self._device)
        self._validate_labels()

    def _validate_labels(self) -> None:
        model_labels = set(self._model.config.id2label.values())
        mapped_labels = set(_PJURA_TO_TILE_CODE.keys())
        if model_labels != mapped_labels:
            missing = model_labels - mapped_labels
            extra = mapped_labels - model_labels
            logger.warning("Label mapping mismatch: missing=%s extra=%s", missing, extra)

    def classify(self, crop: np.ndarray) -> tuple[str, float]:
        results = self.classify_batch([crop])
        return results[0]

    def classify_batch(self, crops: list[np.ndarray]) -> list[tuple[str, float]]:
        if not crops:
            return []

        results: list[tuple[str, float]] = [("", 0.0)] * len(crops)
        valid = [(i, c) for i, c in enumerate(crops)
                 if c is not None and hasattr(c, "size") and c.size > 0]
        if not valid:
            return results

        try:
            images = [c for _, c in valid]
            inputs = self._processor(images=images, return_tensors="pt")
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)

            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            confs, preds = probs.max(dim=-1)

            for (orig_idx, crop), pred, conf in zip(valid, preds, confs):
                pjura_label = self._model.config.id2label[pred.item()]
                tile_code = _PJURA_TO_TILE_CODE.get(pjura_label, pjura_label)
                if tile_code == pjura_label and pjura_label not in _PJURA_TO_TILE_CODE:
                    logger.warning("Unknown pjura label: %s", pjura_label)
                if tile_code in ("5m", "5p", "5s") and _is_red_dora(crop, tile_code):
                    tile_code = tile_code + "r"
                results[orig_idx] = (tile_code, round(conf.item(), 4))

        except Exception as e:
            logger.warning("ViT batch inference failed: %s", e)

        return results
