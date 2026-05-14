"""区域分割器

将完整游戏截图分割为各个识别区域。
支持分辨率归一化（统一缩放到 1920x1080）。
"""

import cv2
import numpy as np

from majsoul_recognizer.types import ZoneName
from majsoul_recognizer.zones.config import ZoneConfig

# 基准分辨率
BASE_WIDTH = 1920
BASE_HEIGHT = 1080


class ZoneSplitter:
    """区域分割器"""

    def __init__(self, config: ZoneConfig):
        self._config = config

    def split(self, image: np.ndarray) -> dict[ZoneName, np.ndarray]:
        normalized = self._normalize(image)
        return {
            name: self._crop_zone(normalized, name)
            for name in self._config.zone_names
        }

    def get_zone(self, image: np.ndarray, zone_name: ZoneName) -> np.ndarray | None:
        zone_def = self._config.get_zone(zone_name)
        if zone_def is None:
            return None
        normalized = self._normalize(image)
        return self._crop_zone(normalized, zone_name)

    def _normalize(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        if w == BASE_WIDTH and h == BASE_HEIGHT:
            return image
        return cv2.resize(image, (BASE_WIDTH, BASE_HEIGHT), interpolation=cv2.INTER_LINEAR)

    def normalize(self, image: np.ndarray) -> np.ndarray:
        """公开接口：将图像归一化到 1920x1080"""
        return self._normalize(image)

    def _crop_zone(self, image: np.ndarray, zone_name: ZoneName) -> np.ndarray:
        zone_def = self._config.get_zone(zone_name)
        if zone_def is None:
            return np.array([])
        bbox = zone_def.to_bbox(BASE_WIDTH, BASE_HEIGHT)
        return bbox.crop(image)

    def get_zone_rects(
        self, img_shape: tuple[int, ...]
    ) -> dict[str, tuple[int, int, int, int]]:
        """获取各区域在归一化图像上的像素矩形 (x, y, w, h)"""
        rects: dict[str, tuple[int, int, int, int]] = {}
        for name in self._config.zone_names:
            zone_def = self._config.get_zone(name)
            if zone_def is None:
                continue
            bbox = zone_def.to_bbox(BASE_WIDTH, BASE_HEIGHT)
            rects[name.value] = (bbox.x, bbox.y, bbox.width, bbox.height)
        return rects
