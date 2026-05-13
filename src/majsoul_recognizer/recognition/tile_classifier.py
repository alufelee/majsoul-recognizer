"""ViT 牌面分类器

使用 pjura/mahjong_soul_vision ViT 模型对单张牌面裁剪图进行分类。
"""

import logging

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
