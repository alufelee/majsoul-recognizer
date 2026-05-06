"""区域坐标校准工具

在游戏截图上绘制区域框，输出标注图供目视校验。
用法: python -m majsoul_recognizer calibrate --screenshot <path>
"""

import logging
from pathlib import Path

import cv2
import numpy as np

from majsoul_recognizer.pipeline import _DEFAULT_CONFIG_PATH
from majsoul_recognizer.zones.config import load_zone_config

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
    """在截图上绘制所有区域框和标签

    复用 load_zone_config 加载配置，通过 ZoneDefinition.to_bbox()
    计算像素坐标，保持与 ZoneSplitter 一致的坐标逻辑。
    """
    config = load_zone_config(config_path)
    overlay = image.copy()
    h, w = image.shape[:2]

    for i, (zone_name, zone_def) in enumerate(config.zones.items()):
        bbox = zone_def.to_bbox(w, h)
        color = COLORS[i % len(COLORS)]

        cv2.rectangle(overlay, (bbox.x, bbox.y),
                       (bbox.x + bbox.width, bbox.y + bbox.height), color, 2)
        label = f"{zone_name.value} ({zone_def.x:.2f},{zone_def.y:.2f})"
        cv2.putText(overlay, label, (bbox.x, bbox.y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    return overlay


def calibrate(screenshot_path: str, config_path: str | None = None, output_path: str | None = None):
    """校准区域坐标

    Args:
        screenshot_path: 雀魂游戏截图文件路径
        config_path: 当前区域配置路径
        output_path: 标注图输出路径
    """
    config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    output_path = output_path or str(Path(screenshot_path).with_name("calibration_preview.png"))

    image = cv2.imread(screenshot_path)
    if image is None:
        logger.error("Cannot read: %s", screenshot_path)
        return

    h, w = image.shape[:2]
    logger.info("Screenshot: %dx%d", w, h)

    annotated = draw_zones_on_image(image, config_path)
    cv2.imwrite(output_path, annotated)
    logger.info("Calibration preview saved to: %s", output_path)
    return output_path
