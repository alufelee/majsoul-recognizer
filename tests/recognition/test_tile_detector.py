"""TileDetector 测试"""

import numpy as np
import pytest

from majsoul_recognizer.types import BBox, Detection, ZoneName

# onnxruntime may not be available on Python 3.14
try:
    import onnxruntime
    HAS_ORT = True
except ImportError:
    HAS_ORT = False

requires_ort = pytest.mark.skipif(not HAS_ORT, reason="onnxruntime not available")


class TestComputeIoU:
    """IoU 计算测试 (pure logic, no ONNX)"""

    def test_identical_boxes(self):
        from majsoul_recognizer.recognition.tile_detector import _compute_iou
        a = BBox(x=0, y=0, width=100, height=100)
        assert _compute_iou(a, a) == 1.0

    def test_no_overlap(self):
        from majsoul_recognizer.recognition.tile_detector import _compute_iou
        a = BBox(x=0, y=0, width=50, height=50)
        b = BBox(x=100, y=100, width=50, height=50)
        assert _compute_iou(a, b) == 0.0

    def test_partial_overlap(self):
        from majsoul_recognizer.recognition.tile_detector import _compute_iou
        a = BBox(x=0, y=0, width=100, height=100)
        b = BBox(x=50, y=50, width=100, height=100)
        iou = _compute_iou(a, b)
        assert 0.0 < iou < 1.0


class TestResolveRotatedTiles:
    """横置牌定位测试 (pure logic)"""

    def test_rotated_associated_to_nearest(self):
        from majsoul_recognizer.recognition.tile_detector import _resolve_rotated_tiles
        normal = Detection(bbox=BBox(x=0, y=0, width=50, height=70), tile_code="1m", confidence=0.9)
        rotated = Detection(bbox=BBox(x=5, y=5, width=45, height=65), tile_code="rotated", confidence=0.85)
        result = _resolve_rotated_tiles([normal, rotated])
        assert 0 in result

    def test_no_rotated_returns_empty(self):
        from majsoul_recognizer.recognition.tile_detector import _resolve_rotated_tiles
        normal = Detection(bbox=BBox(x=0, y=0, width=50, height=70), tile_code="1m", confidence=0.9)
        result = _resolve_rotated_tiles([normal])
        assert result == {}


class TestClassMap:
    """类别映射测试 (no ONNX)"""

    def test_default_class_map(self):
        from majsoul_recognizer.recognition.tile_detector import _DEFAULT_CLASS_MAP
        assert _DEFAULT_CLASS_MAP[0] == "1m"
        assert _DEFAULT_CLASS_MAP[36] == "5sr"
        assert _DEFAULT_CLASS_MAP[37] == "back"
        assert _DEFAULT_CLASS_MAP[38] == "rotated"
        assert _DEFAULT_CLASS_MAP[39] == "dora_frame"

    def test_class_map_covers_all_tiles(self):
        from majsoul_recognizer.recognition.tile_detector import _DEFAULT_CLASS_MAP
        from majsoul_recognizer.tile import Tile
        tile_codes = {v for k, v in _DEFAULT_CLASS_MAP.items() if k <= 36}
        assert tile_codes == {t.value for t in Tile}


class TestNMS:
    """NMS 测试 (pure logic)"""

    def test_nms_removes_overlapping(self):
        from majsoul_recognizer.recognition.tile_detector import _nms
        dets = [
            Detection(bbox=BBox(x=0, y=0, width=50, height=70), tile_code="1m", confidence=0.95),
            Detection(bbox=BBox(x=2, y=2, width=50, height=70), tile_code="1m", confidence=0.85),
        ]
        result = _nms(dets, iou_threshold=0.55)
        assert len(result) == 1
        assert result[0].confidence == 0.95

    def test_nms_keeps_non_overlapping(self):
        from majsoul_recognizer.recognition.tile_detector import _nms
        dets = [
            Detection(bbox=BBox(x=0, y=0, width=50, height=70), tile_code="1m", confidence=0.9),
            Detection(bbox=BBox(x=200, y=0, width=50, height=70), tile_code="2m", confidence=0.9),
        ]
        result = _nms(dets, iou_threshold=0.55)
        assert len(result) == 2

    def test_nms_empty_input(self):
        from majsoul_recognizer.recognition.tile_detector import _nms
        assert _nms([], iou_threshold=0.55) == []


class TestCanvasHelpers:
    """画布辅助函数测试 (pure logic)"""

    def test_canvas_slot_image_rect(self):
        from majsoul_recognizer.recognition.tile_detector import _CanvasSlot
        slot = _CanvasSlot(zone_name="hand", x_offset=0, y_offset=0, scale=0.5, orig_w=200, orig_h=100, slot_size=320)
        x1, y1, x2, y2 = slot.image_rect
        assert x1 == 110  # (320 - 100) // 2
        assert x2 == 210  # 110 + 100
        assert y1 == 135  # (320 - 50) // 2
        assert y2 == 185  # 135 + 50

    def test_canvas_to_local(self):
        from majsoul_recognizer.recognition.tile_detector import _CanvasSlot, _canvas_to_local
        slot = _CanvasSlot(zone_name="hand", x_offset=100, y_offset=0, scale=2.0, orig_w=100, orig_h=50, slot_size=200)
        bbox = BBox(x=120, y=10, width=40, height=20)
        local = _canvas_to_local(bbox, slot)
        assert local.x == 10   # (120-100)/2
        assert local.y == 5    # 10/2
        assert local.width == 20  # 40/2
        assert local.height == 10  # 20/2

    def test_assign_to_slot(self):
        from majsoul_recognizer.recognition.tile_detector import _CanvasSlot, _assign_to_slot
        slot = _CanvasSlot(zone_name="hand", x_offset=0, y_offset=0, scale=1.0, orig_w=200, orig_h=100, slot_size=200)
        det = Detection(bbox=BBox(x=10, y=10, width=30, height=40), tile_code="1m", confidence=0.9)
        result = _assign_to_slot([det], [slot])
        assert "hand" in result
        assert len(result["hand"]) == 1


@requires_ort
class TestTileDetectorDetect:
    """单图检测测试 (requires onnxruntime)"""

    def test_detect_returns_detections(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        results = detector.detect(image, confidence=0.5)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_detect_first_result_is_1m(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        results = detector.detect(image, confidence=0.5)
        codes = [d.tile_code for d in results]
        assert "1m" in codes

    def test_detect_bbox_positive_size(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        results = detector.detect(image, confidence=0.5)
        for det in results:
            assert det.bbox.width > 0
            assert det.bbox.height > 0

    def test_detect_confidence_filter(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        high = detector.detect(image, confidence=0.96)
        low = detector.detect(image, confidence=0.5)
        assert len(low) >= len(high)


@requires_ort
class TestTileDetectorBatch:
    """多区域拼接检测测试 (requires onnxruntime)"""

    def test_detect_batch_returns_dict(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        images = [
            ("hand", np.zeros((100, 200, 3), dtype=np.uint8)),
            ("dora", np.zeros((60, 150, 3), dtype=np.uint8)),
        ]
        results = detector.detect_batch(images, confidence=0.5)
        assert isinstance(results, dict)
        assert "hand" in results
        assert "dora" in results

    def test_detect_batch_single_image(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        images = [("hand", np.zeros((100, 200, 3), dtype=np.uint8))]
        results = detector.detect_batch(images, confidence=0.5)
        assert "hand" in results

    def test_detect_batch_empty_list(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        results = detector.detect_batch([], confidence=0.5)
        assert results == {}


class TestDetectNoneInput:
    """None/空输入测试 (不需要 onnxruntime)"""

    def test_detect_none_returns_empty(self):
        """detect(None) 返回空列表 (spec §9.3)"""
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector.__new__(TileDetector)  # 不调用 __init__
        assert detector.detect(None) == []

    def test_detect_empty_image_returns_empty(self):
        """detect(空数组) 返回空列表"""
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector.__new__(TileDetector)  # 不调用 __init__
        assert detector.detect(np.array([], dtype=np.uint8)) == []

    def test_detect_batch_filters_none_images(self):
        """detect_batch 过滤 None 图像"""
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector.__new__(TileDetector)  # 不调用 __init__
        results = detector.detect_batch([("hand", None)], confidence=0.5)
        assert results == {}

    def test_detect_batch_filters_empty_images(self):
        """detect_batch 过滤空数组图像"""
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector.__new__(TileDetector)  # 不调用 __init__
        results = detector.detect_batch(
            [("hand", np.array([], dtype=np.uint8))], confidence=0.5
        )
        assert results == {}
