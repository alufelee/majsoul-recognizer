"""基于 ultralytics (PyTorch) 的牌面检测器

使用 MajsoulBot 预训练 YOLOv11n 模型，
在真实雀魂画面上有良好的检测效果。

支持两种检测模式:
1. 全图检测 + 区域映射（推荐，效果最好）
2. 逐区域检测（兼容模式）
"""

import logging
import time
from pathlib import Path

import numpy as np

from majsoul_recognizer.types import BBox, Detection

logger = logging.getLogger(__name__)


def _iou_xyxy(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    """计算两个 (x1, y1, x2, y2) 矩形的 IoU"""
    ix1 = max(a[0], b[0])
    iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2])
    iy2 = min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _nms(detections: list[Detection], iou_threshold: float = 0.5) -> list[Detection]:
    """非极大值抑制"""
    if not detections:
        return []
    sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
    keep: list[Detection] = []
    for det in sorted_dets:
        should_keep = True
        for kept in keep:
            a = (det.bbox.x, det.bbox.y, det.bbox.x + det.bbox.width, det.bbox.y + det.bbox.height)
            b = (kept.bbox.x, kept.bbox.y, kept.bbox.x + kept.bbox.width, kept.bbox.y + kept.bbox.height)
            if _iou_xyxy(a, b) > iou_threshold:
                should_keep = False
                break
        if should_keep:
            keep.append(det)
    return keep


class UltralyticsTileDetector:
    """ultralytics YOLOv11 牌面检测器"""

    def __init__(self, model_path: str | Path):
        from ultralytics import YOLO

        self._model = YOLO(str(model_path))
        self._class_names = self._model.names
        logger.info("UltralyticsTileDetector loaded from %s (%d classes)",
                     model_path, len(self._class_names))

    def detect(self, image: np.ndarray, confidence: float = 0.5) -> list[Detection]:
        """检测单张图像中的牌面"""
        if image is None or (hasattr(image, "size") and image.size == 0):
            return []
        try:
            t0 = time.perf_counter()
            results = self._model.predict(
                source=image, conf=confidence, augment=True, verbose=False,
            )
            result = results[0]
            detections = []
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].cpu().numpy()
                tile_code = self._class_names.get(cls_id, f"unknown_{cls_id}")
                detections.append(Detection(
                    bbox=BBox(
                        x=max(0, int(xyxy[0])),
                        y=max(0, int(xyxy[1])),
                        width=max(1, int(xyxy[2] - xyxy[0])),
                        height=max(1, int(xyxy[3] - xyxy[1])),
                    ),
                    tile_code=tile_code,
                    confidence=round(conf, 4),
                ))
            detections = _nms(detections, iou_threshold=0.5)
            elapsed = (time.perf_counter() - t0) * 1000
            logger.debug("detect: %d results in %.1fms", len(detections), elapsed)
            return detections
        except Exception as e:
            logger.warning("Ultralytics inference failed: %s", e)
            return []

    def detect_full_image(
        self,
        image: np.ndarray,
        zone_rects: dict[str, tuple[int, int, int, int]],
        confidence: float = 0.5,
    ) -> dict[str, list[Detection]]:
        """全图检测并映射到区域

        Args:
            image: 完整游戏截图
            zone_rects: 区域名 -> (x, y, w, h) 像素矩形
            confidence: 检测置信度阈值

        Returns:
            区域名 -> 检测结果列表（坐标为区域内相对坐标）
        """
        all_dets = self.detect(image, confidence)
        result: dict[str, list[Detection]] = {}

        for zone_name, (zx, zy, zw, zh) in zone_rects.items():
            zone_dets: list[Detection] = []
            for det in all_dets:
                # 检测框中心是否在区域内
                cx = det.bbox.x + det.bbox.width // 2
                cy = det.bbox.y + det.bbox.height // 2
                if zx <= cx <= zx + zw and zy <= cy <= zy + zh:
                    # 转为区域相对坐标
                    local_x = det.bbox.x - zx
                    local_y = det.bbox.y - zy
                    zone_dets.append(det.model_copy(update={
                        "bbox": BBox(
                            x=max(0, local_x),
                            y=max(0, local_y),
                            width=det.bbox.width,
                            height=det.bbox.height,
                        ),
                    }))
            result[zone_name] = zone_dets

        return result

    def detect_batch(
        self,
        images: list[tuple[str, np.ndarray]],
        confidence: float = 0.5,
    ) -> dict[str, list[Detection]]:
        """多区域检测（逐区域调用）"""
        if not images:
            return {}
        result = {}
        for name, img in images:
            result[name] = self.detect(img, confidence)
        return result
