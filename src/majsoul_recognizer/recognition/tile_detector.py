"""YOLOv8 ONNX 牌面检测器"""

import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from majsoul_recognizer.types import BBox, Detection

logger = logging.getLogger(__name__)

_DEFAULT_CLASS_MAP: dict[int, str] = {
    0: "1m", 1: "2m", 2: "3m", 3: "4m", 4: "5m",
    5: "6m", 6: "7m", 7: "8m", 8: "9m",
    9: "1p", 10: "2p", 11: "3p", 12: "4p", 13: "5p",
    14: "6p", 15: "7p", 16: "8p", 17: "9p",
    18: "1s", 19: "2s", 20: "3s", 21: "4s", 22: "5s",
    23: "6s", 24: "7s", 25: "8s", 26: "9s",
    27: "1z", 28: "2z", 29: "3z", 30: "4z",
    31: "5z", 32: "6z", 33: "7z",
    34: "5mr", 35: "5pr", 36: "5sr",
    37: "back", 38: "rotated", 39: "dora_frame",
}


def _compute_iou(bbox_a: BBox, bbox_b: BBox) -> float:
    """计算两个 BBox 的 IoU"""
    x1 = max(bbox_a.x, bbox_b.x)
    y1 = max(bbox_a.y, bbox_b.y)
    x2 = min(bbox_a.x + bbox_a.width, bbox_b.x + bbox_b.width)
    y2 = min(bbox_a.y + bbox_a.height, bbox_b.y + bbox_b.height)

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = bbox_a.area + bbox_b.area - intersection
    return intersection / union if union > 0 else 0.0


def _resolve_rotated_tiles(all_detections: list[Detection]) -> dict[int, Detection]:
    """将 rotated 类别的检测关联到最近的正常牌面检测"""
    normals = [(i, d) for i, d in enumerate(all_detections)
               if d.tile_code not in ("back", "rotated", "dora_frame")]
    rotated = [d for d in all_detections if d.tile_code == "rotated"]

    rotated_map: dict[int, Detection] = {}
    for r in rotated:
        best_iou = 0.0
        best_idx = -1
        for idx, n in normals:
            iou = _compute_iou(r.bbox, n.bbox)
            if iou > best_iou:
                best_iou = iou
                best_idx = idx
        if best_idx >= 0 and best_iou > 0.3:
            rotated_map[best_idx] = r
    return rotated_map


def _nms(detections: list[Detection], iou_threshold: float) -> list[Detection]:
    """非极大值抑制"""
    if not detections:
        return []

    sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
    keep: list[Detection] = []

    for det in sorted_dets:
        should_keep = True
        for kept in keep:
            if _compute_iou(det.bbox, kept.bbox) > iou_threshold:
                should_keep = False
                break
        if should_keep:
            keep.append(det)
    return keep


@dataclass
class _CanvasSlot:
    """记录每个区域在画布上的位置"""
    zone_name: str
    x_offset: int
    y_offset: int
    scale: float
    orig_w: int
    orig_h: int
    slot_size: int

    @property
    def image_rect(self) -> tuple[int, int, int, int]:
        """实际图像在画布上的范围 (x1, y1, x2, y2)"""
        scaled_w = int(self.orig_w * self.scale)
        scaled_h = int(self.orig_h * self.scale)
        pad_x = (self.slot_size - scaled_w) // 2
        pad_y = (self.slot_size - scaled_h) // 2
        return (
            self.x_offset + pad_x,
            self.y_offset + pad_y,
            self.x_offset + pad_x + scaled_w,
            self.y_offset + pad_y + scaled_h,
        )


def _canvas_to_local(bbox: BBox, slot: _CanvasSlot) -> BBox:
    """将画布坐标转换为区域本地坐标"""
    local_x = (bbox.x - slot.x_offset) / slot.scale
    local_y = (bbox.y - slot.y_offset) / slot.scale
    local_w = bbox.width / slot.scale
    local_h = bbox.height / slot.scale
    return BBox(
        x=max(0, int(local_x)),
        y=max(0, int(local_y)),
        width=max(1, int(local_w)),
        height=max(1, int(local_h)),
    )


def _assign_to_slot(
    detections: list[Detection],
    slots: list[_CanvasSlot],
) -> dict[str, list[Detection]]:
    """将画布上的检测结果归属到对应的区域 slot"""
    result: dict[str, list[Detection]] = {s.zone_name: [] for s in slots}

    for det in detections:
        cx = det.bbox.x + det.bbox.width // 2
        cy = det.bbox.y + det.bbox.height // 2

        assigned = False
        for slot in slots:
            x1, y1, x2, y2 = slot.image_rect
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                local_bbox = _canvas_to_local(det.bbox, slot)
                local_det = det.model_copy(update={"bbox": local_bbox})
                result[slot.zone_name].append(local_det)
                assigned = True
                break

        if not assigned:
            logger.debug("Discarding detection in padding area: %s", det)

    return result


class TileDetector:
    """YOLOv8 ONNX 牌面检测器"""

    def __init__(
        self,
        model_path: Path | str,
        class_map: dict[int, str] | None = None,
        nms_iou: float = 0.55,
    ):
        import onnxruntime as ort

        self.class_map = class_map or _DEFAULT_CLASS_MAP
        self._nms_iou = nms_iou

        providers = []
        if "CoreMLExecutionProvider" in ort.get_available_providers():
            providers.append("CoreMLExecutionProvider")
        if "CUDAExecutionProvider" in ort.get_available_providers():
            providers.append("CUDAExecutionProvider")
        providers.append("CPUExecutionProvider")

        self._session = ort.InferenceSession(str(model_path), providers=providers)

        # 从模型输入 shape 自动推断 letterbox 目标尺寸
        input_shape = self._session.get_inputs()[0].shape  # [1, 3, H, W]
        self._input_size = input_shape[2] if isinstance(input_shape[2], int) else 640

        logger.info("TileDetector loaded from %s (input_size=%d)", model_path, self._input_size)

    def detect(self, image: np.ndarray, confidence: float = 0.7) -> list[Detection]:
        """检测单张图像中的牌面"""
        if image is None or (hasattr(image, 'size') and image.size == 0):
            return []
        try:
            t0 = time.perf_counter()
            input_tensor, (orig_h, orig_w), (pad_x, pad_y, scale) = self._preprocess(image)
            output = self._session.run(None, {"images": input_tensor})
            raw_detections = self._postprocess(output[0], confidence, orig_w, orig_h, pad_x, pad_y, scale)
            result = _nms(raw_detections, self._nms_iou)
            elapsed = (time.perf_counter() - t0) * 1000
            logger.debug("detect: %d results in %.1fms", len(result), elapsed)
            return result
        except Exception as e:
            logger.warning("ONNX inference failed: %s", e)
            return []

    def detect_batch(
        self,
        images: list[tuple[str, np.ndarray]],
        confidence: float = 0.7,
    ) -> dict[str, list[Detection]]:
        """多区域拼接检测"""
        if not images:
            return {}

        # 过滤掉 None 或空图像
        valid_images = [
            (name, img) for name, img in images
            if img is not None and not (hasattr(img, 'size') and img.size == 0)
        ]
        if not valid_images:
            return {}

        if len(valid_images) == 1:
            name, img = valid_images[0]
            return {name: self.detect(img, confidence)}

        canvas, slots = self._build_canvas(valid_images)
        all_dets = self.detect(canvas, confidence)
        return _assign_to_slot(all_dets, slots)

    def _preprocess(self, image: np.ndarray) -> tuple:
        """Letterbox 预处理"""
        orig_h, orig_w = image.shape[:2]
        target = self._input_size
        scale = min(target / orig_w, target / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((target, target, 3), 114, dtype=np.uint8)
        pad_x = (target - new_w) // 2
        pad_y = (target - new_h) // 2
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

        blob = canvas.astype(np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)[np.newaxis, ...]  # (1, 3, 640, 640)

        return blob, (orig_h, orig_w), (pad_x, pad_y, scale)

    def _postprocess(self, output: np.ndarray, confidence: float,
                     orig_w: int, orig_h: int,
                     pad_x: int, pad_y: int, scale: float) -> list[Detection]:
        """YOLOv8 输出后处理"""
        predictions = output[0].T  # (8400, 44)

        detections: list[Detection] = []
        for pred in predictions:
            bbox_vals = pred[:4]
            class_scores = pred[4:]
            class_id = int(np.argmax(class_scores))
            score = float(class_scores[class_id])

            if score < confidence:
                continue

            tile_code = self.class_map.get(class_id, f"unknown_{class_id}")

            cx = float((bbox_vals[0] - pad_x) / scale)
            cy = float((bbox_vals[1] - pad_y) / scale)
            w = float(bbox_vals[2] / scale)
            h = float(bbox_vals[3] / scale)

            x = max(0, int(cx - w / 2))
            y = max(0, int(cy - h / 2))

            detections.append(Detection(
                bbox=BBox(x=x, y=y, width=max(1, int(w)), height=max(1, int(h))),
                tile_code=tile_code,
                confidence=round(score, 4),
            ))
        return detections

    def _build_canvas(self, images: list[tuple[str, np.ndarray]]) -> tuple:
        """构建多区域拼接画布"""
        n = len(images)
        grid_size = max(2, math.ceil(math.sqrt(n)))
        target = self._input_size
        slot_size = target // grid_size

        canvas = np.full((target, target, 3), 114, dtype=np.uint8)
        slots: list[_CanvasSlot] = []

        for idx, (name, img) in enumerate(images):
            row = idx // grid_size
            col = idx % grid_size
            x_offset = col * slot_size
            y_offset = row * slot_size

            orig_h, orig_w = img.shape[:2]
            scale = min(slot_size / orig_w, slot_size / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)

            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            pad_x = (slot_size - new_w) // 2
            pad_y = (slot_size - new_h) // 2
            canvas[y_offset + pad_y:y_offset + pad_y + new_h,
                   x_offset + pad_x:x_offset + pad_x + new_w] = resized

            slots.append(_CanvasSlot(
                zone_name=name,
                x_offset=x_offset,
                y_offset=y_offset,
                scale=scale,
                orig_w=orig_w,
                orig_h=orig_h,
                slot_size=slot_size,
            ))

        return canvas, slots
