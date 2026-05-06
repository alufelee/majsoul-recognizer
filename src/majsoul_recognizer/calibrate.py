"""区域坐标校准工具

在游戏截图上绘制区域框，输出标注图供目视校验。
用法: python -m majsoul_recognizer calibrate --screenshot <path>
"""

import argparse
import logging
from pathlib import Path

import cv2
import numpy as np

from majsoul_recognizer.pipeline import _PROJECT_ROOT

logger = logging.getLogger(__name__)

# 区域标注颜色 (BGR)，6 色循环
COLORS = [
    (0, 255, 0),    # 绿
    (255, 0, 0),    # 蓝
    (0, 0, 255),    # 红
    (255, 255, 0),  # 青
    (0, 255, 255),  # 黄
    (255, 0, 255),  # 品红
]


def draw_zones_on_image(image: np.ndarray, config_path: Path) -> np.ndarray:
    """在截图上绘制所有区域框和标签"""
    import yaml

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    overlay = image.copy()
    h, w = image.shape[:2]

    for i, (name, coords) in enumerate(raw.get("zones", {}).items()):
        x = int(coords["x"] * w)
        y = int(coords["y"] * h)
        bw = int(coords["width"] * w)
        bh = int(coords["height"] * h)
        color = COLORS[i % len(COLORS)]

        cv2.rectangle(overlay, (x, y), (x + bw, y + bh), color, 2)
        label = f"{name} ({coords['x']:.2f},{coords['y']:.2f})"
        cv2.putText(overlay, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    return overlay


def calibrate(screenshot_path: str, config_path: str | None = None, output_path: str | None = None):
    """校准区域坐标

    Args:
        screenshot_path: 雀魂游戏截图文件路径
        config_path: 当前区域配置路径
        output_path: 标注图输出路径
    """
    config_path = Path(config_path) if config_path else _PROJECT_ROOT / "config" / "zones.yaml"
    output_path = output_path or str(Path(screenshot_path).with_name("calibration_preview.png"))

    image = cv2.imread(screenshot_path)
    if image is None:
        logger.error(f"Cannot read: {screenshot_path}")
        return

    h, w = image.shape[:2]
    logger.info(f"Screenshot: {w}x{h}")

    annotated = draw_zones_on_image(image, config_path)
    cv2.imwrite(output_path, annotated)
    logger.info(f"Calibration preview saved to: {output_path}")
    return output_path
