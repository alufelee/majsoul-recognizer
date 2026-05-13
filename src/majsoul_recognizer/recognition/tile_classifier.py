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
