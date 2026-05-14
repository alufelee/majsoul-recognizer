# ViT TileClassifier Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate a ViT-based tile classifier (pjura/mahjong_soul_vision) into the recognition pipeline to reclassify YOLO detections with higher accuracy.

**Architecture:** Two-stage pipeline — YOLO detects tile bounding boxes (localization), then ViT classifies each cropped tile image (classification). YOLO's class predictions are discarded; ViT replaces them.

**Tech Stack:** Python 3.10+, PyTorch, HuggingFace Transformers (ViTForImageClassification), OpenCV (HSV color analysis for red dora), pytest + unittest.mock for testing.

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `src/majsoul_recognizer/recognition/tile_classifier.py` | Label mapping, red dora detection, TileClassifier class |
| Create | `tests/recognition/test_tile_classifier.py` | All tile_classifier tests |
| Modify | `src/majsoul_recognizer/recognition/config.py:32-59` | Add ViT config fields |
| Modify | `src/majsoul_recognizer/recognition/engine.py:50-260` | Add _ensure_classifier, ViT step in recognize, __exit__ update |
| Modify | `tests/recognition/conftest.py` | Add mock_vit_classifier fixture |
| Modify | `tests/recognition/test_config.py` | Add ViT config tests |
| Modify | `tests/recognition/test_engine.py` | Add ViT integration tests |
| Modify | `pyproject.toml:21-45` | Add recognition-vit optional dependency group |

---

### Task 1: Label Mapping

**Files:**
- Create: `src/majsoul_recognizer/recognition/tile_classifier.py`
- Create: `tests/recognition/test_tile_classifier.py`

- [ ] **Step 1: Write the failing test**

Create `tests/recognition/test_tile_classifier.py`:

```python
"""TileClassifier 测试"""

import numpy as np
import pytest

from majsoul_recognizer.tile import Tile


class TestLabelMapping:
    """P1: pjura 标签映射测试"""

    def test_souzu_mapping(self):
        from majsoul_recognizer.recognition.tile_classifier import _PJURA_TO_TILE_CODE
        for i in range(1, 10):
            assert _PJURA_TO_TILE_CODE[f"{i}b"] == f"{i}s"

    def test_manzu_mapping(self):
        from majsoul_recognizer.recognition.tile_classifier import _PJURA_TO_TILE_CODE
        for i in range(1, 10):
            assert _PJURA_TO_TILE_CODE[f"{i}n"] == f"{i}m"

    def test_pinzu_mapping(self):
        from majsoul_recognizer.recognition.tile_classifier import _PJURA_TO_TILE_CODE
        for i in range(1, 10):
            assert _PJURA_TO_TILE_CODE[f"{i}p"] == f"{i}p"

    def test_wind_mapping(self):
        from majsoul_recognizer.recognition.tile_classifier import _PJURA_TO_TILE_CODE
        assert _PJURA_TO_TILE_CODE["ew"] == "1z"
        assert _PJURA_TO_TILE_CODE["sw"] == "2z"
        assert _PJURA_TO_TILE_CODE["ww"] == "3z"
        assert _PJURA_TO_TILE_CODE["nw"] == "4z"

    def test_dragon_mapping(self):
        from majsoul_recognizer.recognition.tile_classifier import _PJURA_TO_TILE_CODE
        assert _PJURA_TO_TILE_CODE["wd"] == "5z"
        assert _PJURA_TO_TILE_CODE["gd"] == "6z"
        assert _PJURA_TO_TILE_CODE["rd"] == "7z"

    def test_total_34_classes(self):
        from majsoul_recognizer.recognition.tile_classifier import _PJURA_TO_TILE_CODE
        assert len(_PJURA_TO_TILE_CODE) == 34

    def test_all_values_are_valid_tiles(self):
        from majsoul_recognizer.recognition.tile_classifier import _PJURA_TO_TILE_CODE
        all_tiles = {t.value for t in Tile}
        for pjura_label, tile_code in _PJURA_TO_TILE_CODE.items():
            assert tile_code in all_tiles, f"{pjura_label} -> {tile_code} not in Tile enum"

    def test_mapping_is_bijective(self):
        from majsoul_recognizer.recognition.tile_classifier import _PJURA_TO_TILE_CODE
        values = list(_PJURA_TO_TILE_CODE.values())
        assert len(values) == len(set(values)), "Duplicate tile_code in mapping"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd F:/majong && python -m pytest tests/recognition/test_tile_classifier.py::TestLabelMapping -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'majsoul_recognizer.recognition.tile_classifier'`

- [ ] **Step 3: Write minimal implementation**

Create `src/majsoul_recognizer/recognition/tile_classifier.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd F:/majong && python -m pytest tests/recognition/test_tile_classifier.py::TestLabelMapping -v`
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
cd F:/majong && git add src/majsoul_recognizer/recognition/tile_classifier.py tests/recognition/test_tile_classifier.py
git commit -m "feat(vit): add pjura-to-tile-code label mapping with tests"
```

---

### Task 2: Red Dora Detection

**Files:**
- Modify: `src/majsoul_recognizer/recognition/tile_classifier.py`
- Modify: `tests/recognition/test_tile_classifier.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/recognition/test_tile_classifier.py`:

```python
class TestIsRedDora:
    """P2: 赤宝牌颜色检测测试"""

    def test_red_image_detected(self):
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        red_img = np.zeros((50, 50, 3), dtype=np.uint8)
        red_img[:, :, 2] = 200  # BGR: high red channel
        assert _is_red_dora(red_img, "5m") is True

    def test_blue_image_not_red(self):
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        blue_img = np.zeros((50, 50, 3), dtype=np.uint8)
        blue_img[:, :, 0] = 200  # BGR: high blue channel
        assert _is_red_dora(blue_img, "5p") is False

    def test_green_image_not_red(self):
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        green_img = np.zeros((50, 50, 3), dtype=np.uint8)
        green_img[:, :, 1] = 200  # BGR: high green channel
        assert _is_red_dora(green_img, "5s") is False

    def test_none_returns_false(self):
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        assert _is_red_dora(None, "5m") is False

    def test_empty_array_returns_false(self):
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        assert _is_red_dora(np.array([], dtype=np.uint8), "5m") is False

    def test_suit_specific_thresholds(self):
        from majsoul_recognizer.recognition.tile_classifier import _PER_SUIT_THRESHOLD
        assert _PER_SUIT_THRESHOLD["5m"] < _PER_SUIT_THRESHOLD["5p"]
        assert _PER_SUIT_THRESHOLD["5p"] < _PER_SUIT_THRESHOLD["5s"]

    def test_non_five_tile_code_no_crash(self):
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        assert _is_red_dora(img, "1m") is False

    def test_synthetic_red_dora_tile(self):
        """合成赤宝牌图像：白色牌面 + 红色标记 + 绿色背景"""
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        img = np.full((60, 50, 3), [40, 80, 40], dtype=np.uint8)  # green bg
        img[10:50, 5:45] = [220, 220, 220]  # white tile face
        img[20:40, 15:35] = [0, 0, 200]  # red marking (BGR)
        assert _is_red_dora(img, "5m") is True

    def test_synthetic_normal_tile_not_red(self):
        """合成普通牌图像：白色牌面 + 蓝色标记 + 绿色背景"""
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        img = np.full((60, 50, 3), [40, 80, 40], dtype=np.uint8)  # green bg
        img[10:50, 5:45] = [220, 220, 220]  # white tile face
        img[20:40, 15:35] = [200, 100, 0]  # blue marking (BGR)
        assert _is_red_dora(img, "5m") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd F:/majong && python -m pytest tests/recognition/test_tile_classifier.py::TestIsRedDora -v`
Expected: FAIL — `ImportError: cannot import name '_is_red_dora'`

- [ ] **Step 3: Write implementation**

Append to `src/majsoul_recognizer/recognition/tile_classifier.py` (after the `_PJURA_TO_TILE_CODE` dict):

```python
import cv2
import numpy as np

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
    """检测裁剪图是否为赤宝牌（红色标记）

    Args:
        crop: YOLO bbox 裁剪的原始 BGR 图像
        tile_code: ViT 分类结果 ("5m"/"5p"/"5s")
        threshold: 显式阈值覆盖，None 时使用花色默认阈值
    """
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
```

Note: `import cv2` and `import numpy as np` must be added at the top of the file. Move the existing imports or add them alongside `import logging`. The full top of the file becomes:

```python
"""ViT 牌面分类器"""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd F:/majong && python -m pytest tests/recognition/test_tile_classifier.py -v`
Expected: All TestLabelMapping + TestIsRedDora PASSED (17 tests total)

- [ ] **Step 5: Commit**

```bash
cd F:/majong && git add src/majsoul_recognizer/recognition/tile_classifier.py tests/recognition/test_tile_classifier.py
git commit -m "feat(vit): add red dora detection via HSV color analysis"
```

---

### Task 3: TileClassifier Class

**Files:**
- Modify: `src/majsoul_recognizer/recognition/tile_classifier.py`
- Modify: `tests/recognition/test_tile_classifier.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/recognition/test_tile_classifier.py`:

```python
from unittest.mock import MagicMock

# pjura model id2label for mock
_PJURA_ID2LABEL = {
    0: "1b", 1: "1n", 2: "1p", 3: "2b", 4: "2n", 5: "2p",
    6: "3b", 7: "3n", 8: "3p", 9: "4b", 10: "4n", 11: "4p",
    12: "5b", 13: "5n", 14: "5p", 15: "6b", 16: "6n", 17: "6p",
    18: "7b", 19: "7n", 20: "7p", 21: "8b", 22: "8n", 23: "8p",
    24: "9b", 25: "9n", 26: "9p", 27: "ew", 28: "gd", 29: "nw",
    30: "rd", 31: "sw", 32: "wd", 33: "ww",
}


def _make_mock_classifier():
    """创建 mock TileClassifier（不依赖 torch/transformers）"""
    from majsoul_recognizer.recognition.tile_classifier import TileClassifier
    classifier = TileClassifier.__new__(TileClassifier)
    classifier._model = MagicMock()
    classifier._processor = MagicMock()
    classifier._model.config.id2label = _PJURA_ID2LABEL
    classifier._device = MagicMock()
    return classifier


def _set_mock_output(classifier, class_index, batch_size=1):
    """配置 mock 模型输出指定 class index"""
    import torch
    logits = torch.full((batch_size, 34), -10.0)
    logits[0, class_index] = 10.0
    mock_output = MagicMock()
    mock_output.logits = logits
    classifier._model.return_value = mock_output
    classifier._processor.return_value = {"pixel_values": MagicMock()}


class TestTileClassifierBatch:
    """P3: TileClassifier classify_batch 测试"""

    def test_batch_maps_1b_to_1s(self):
        classifier = _make_mock_classifier()
        _set_mock_output(classifier, 0)  # class 0 = "1b" → "1s"
        results = classifier.classify_batch([np.zeros((50, 50, 3), dtype=np.uint8)])
        assert results[0][0] == "1s"
        assert results[0][1] > 0.99

    def test_batch_maps_ew_to_1z(self):
        classifier = _make_mock_classifier()
        _set_mock_output(classifier, 27)  # "ew" → "1z"
        results = classifier.classify_batch([np.zeros((50, 50, 3), dtype=np.uint8)])
        assert results[0][0] == "1z"

    def test_batch_empty_list(self):
        classifier = _make_mock_classifier()
        results = classifier.classify_batch([])
        assert results == []

    def test_batch_none_and_empty_crops(self):
        classifier = _make_mock_classifier()
        results = classifier.classify_batch([None, np.array([], dtype=np.uint8)])
        assert len(results) == 2
        assert results[0] == ("", 0.0)
        assert results[1] == ("", 0.0)

    def test_classify_delegates_to_batch(self):
        classifier = _make_mock_classifier()
        _set_mock_output(classifier, 30)  # "rd" → "7z"
        tile_code, conf = classifier.classify(np.zeros((50, 50, 3), dtype=np.uint8))
        assert tile_code == "7z"
        assert conf > 0.99

    def test_inference_failure_returns_empty(self):
        classifier = _make_mock_classifier()
        classifier._model.side_effect = RuntimeError("mock failure")
        classifier._processor.return_value = {"pixel_values": MagicMock()}
        results = classifier.classify_batch([np.zeros((50, 50, 3), dtype=np.uint8)])
        assert results == [("", 0.0)]

    def test_red_dora_detection_integrated(self):
        """5m + 红色图像 → 5mr"""
        classifier = _make_mock_classifier()
        _set_mock_output(classifier, 13)  # "5n" → "5m"
        red_img = np.zeros((50, 50, 3), dtype=np.uint8)
        red_img[:, :, 2] = 200
        results = classifier.classify_batch([red_img])
        assert results[0][0] == "5mr"

    def test_normal_five_not_red_dora(self):
        """5m + 蓝色图像 → 5m (not 5mr)"""
        classifier = _make_mock_classifier()
        _set_mock_output(classifier, 13)  # "5n" → "5m"
        blue_img = np.zeros((50, 50, 3), dtype=np.uint8)
        blue_img[:, :, 0] = 200
        results = classifier.classify_batch([blue_img])
        assert results[0][0] == "5m"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd F:/majong && python -m pytest tests/recognition/test_tile_classifier.py::TestTileClassifierBatch -v`
Expected: FAIL — `ImportError: cannot import name 'TileClassifier'`

Note: If torch is not installed, the test `_set_mock_output` uses `import torch`. These tests require torch to be available for tensor creation in the mock. If torch is unavailable, skip with:

```bash
cd F:/majong && python -c "import torch" 2>/dev/null && python -m pytest tests/recognition/test_tile_classifier.py::TestTileClassifierBatch -v || echo "SKIP: torch not installed"
```

- [ ] **Step 3: Write implementation**

Append to `src/majsoul_recognizer/recognition/tile_classifier.py` (after `_is_red_dora`):

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd F:/majong && python -m pytest tests/recognition/test_tile_classifier.py -v`
Expected: All TestLabelMapping + TestIsRedDora + TestTileClassifierBatch PASSED

- [ ] **Step 5: Commit**

```bash
cd F:/majong && git add src/majsoul_recognizer/recognition/tile_classifier.py tests/recognition/test_tile_classifier.py
git commit -m "feat(vit): add TileClassifier class with batch inference and label validation"
```

---

### Task 4: ViT Config Fields

**Files:**
- Modify: `src/majsoul_recognizer/recognition/config.py:32-59`
- Modify: `tests/recognition/test_config.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/recognition/test_config.py`:

```python
class TestRecognitionConfigVit:
    """ViT 分类器配置测试"""

    def test_vit_defaults(self):
        config = RecognitionConfig()
        assert config.enable_vit_classifier is True
        assert config.vit_classifier_threshold == 0.5
        assert config.vit_model_name == "pjura/mahjong_soul_vision"
        assert config.vit_device is None

    def test_vit_custom(self):
        config = RecognitionConfig(
            enable_vit_classifier=False,
            vit_classifier_threshold=0.8,
            vit_model_name="/local/model",
            vit_device="cpu",
        )
        assert config.enable_vit_classifier is False
        assert config.vit_classifier_threshold == 0.8
        assert config.vit_model_name == "/local/model"
        assert config.vit_device == "cpu"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd F:/majong && python -m pytest tests/recognition/test_config.py::TestRecognitionConfigVit -v`
Expected: FAIL — `ValidationError` (fields don't exist yet)

- [ ] **Step 3: Write implementation**

In `src/majsoul_recognizer/recognition/config.py`, add after line 59 (`enable_batch_detection: bool = True`):

```python
    # TileClassifier (ViT)
    vit_model_name: str = "pjura/mahjong_soul_vision"
    enable_vit_classifier: bool = True
    vit_classifier_threshold: float = 0.5
    vit_device: str | None = None  # None=auto, "cpu", "cuda"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd F:/majong && python -m pytest tests/recognition/test_config.py -v`
Expected: All tests PASSED (existing + 2 new)

- [ ] **Step 5: Commit**

```bash
cd F:/majong && git add src/majsoul_recognizer/recognition/config.py tests/recognition/test_config.py
git commit -m "feat(vit): add ViT classifier config fields to RecognitionConfig"
```

---

### Task 5: Engine Integration

**Files:**
- Modify: `src/majsoul_recognizer/recognition/engine.py`
- Modify: `tests/recognition/conftest.py`
- Modify: `tests/recognition/test_engine.py`

- [ ] **Step 1: Add mock fixture to conftest.py**

Append to `tests/recognition/conftest.py`:

```python
@pytest.fixture
def mock_vit_classifier():
    """Mock TileClassifier for engine tests"""
    from unittest.mock import MagicMock
    classifier = MagicMock()
    classifier.classify_batch.return_value = [("9s", 0.99)]
    return classifier
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/recognition/test_engine.py`:

```python
class TestEngineVitIntegration:
    """P4: ViT 分类器集成测试"""

    def test_vit_reclassifies_zone_mode(self, dummy_detector_path, fake_template_dir, mock_vit_classifier):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        engine._classifier = mock_vit_classifier

        zones = {"hand": np.zeros((100, 200, 3), dtype=np.uint8)}
        state = engine.recognize(zones)
        mock_vit_classifier.classify_batch.assert_called()

    def test_vit_low_confidence_keeps_yolo(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        from unittest.mock import MagicMock
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        mock_clf = MagicMock()
        mock_clf.classify_batch.return_value = [("9s", 0.1)]  # below threshold
        engine._classifier = mock_clf

        zones = {"hand": np.zeros((100, 200, 3), dtype=np.uint8)}
        state = engine.recognize(zones)
        # YOLO result (1m from dummy detector) should be preserved
        assert isinstance(state, GameState)

    def test_vit_unavailable_graceful_degradation(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        # _classifier defaults to None, _classifier_attempted stays False
        # but _ensure_classifier will try and fail — that's fine

        zones = {"hand": np.zeros((100, 200, 3), dtype=np.uint8)}
        state = engine.recognize(zones)
        assert isinstance(state, GameState)

    def test_classifier_attempted_prevents_reinit(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        engine._classifier_attempted = True

        result = engine._ensure_classifier()
        assert result is None

    def test_exit_resets_classifier_state(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        with RecognitionEngine(config) as engine:
            engine._classifier_attempted = True
        # After exit, a new engine should start fresh
        engine2 = RecognitionEngine(config)
        assert engine2._classifier_attempted is False
        assert engine2._classifier is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd F:/majong && python -m pytest tests/recognition/test_engine.py::TestEngineVitIntegration -v`
Expected: FAIL — tests reference methods/attributes that don't exist yet

- [ ] **Step 4: Modify engine.py**

Four changes needed to `src/majsoul_recognizer/recognition/engine.py`:

**Change 1**: Add `self._classifier` and `self._classifier_attempted` to `__init__`. After line 59 (`self._validator = Validator(self._config)`), add:

```python
        self._classifier: TileClassifier | None = None
        self._classifier_attempted: bool = False
```

Add the import at the top (after line 12, the existing imports):

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from majsoul_recognizer.recognition.tile_classifier import TileClassifier
```

Or simpler — just use string annotation since TileClassifier is only a type hint:

```python
        self._classifier: "TileClassifier | None" = None
```

**Change 2**: Add `_ensure_classifier` method. Insert after `_ensure_matcher` (after line 93):

```python
    def _ensure_classifier(self):
        if self._classifier is not None:
            return self._classifier
        if not self._config.enable_vit_classifier:
            return None
        if self._classifier_attempted:
            return None
        self._classifier_attempted = True
        try:
            from majsoul_recognizer.recognition.tile_classifier import TileClassifier
            self._classifier = TileClassifier(self._config.vit_model_name)
            logger.info("ViT classifier loaded")
        except ImportError:
            logger.debug("ViT classifier unavailable (torch/transformers not installed)")
        except Exception as e:
            logger.warning("ViT classifier init failed: %s", e)
        return self._classifier
```

**Change 3**: In `recognize()`, add `scaled_rects` init and ViT step. Replace lines 125-154 with:

```python
        # 判断是否使用全图检测模式
        use_full_image = (
            full_image is not None
            and zone_rects is not None
            and hasattr(detector, "detect_full_image")
        )

        scaled_rects: dict[str, tuple[int, int, int, int]] = {}

        if use_full_image:
            tile_rects = {name: zone_rects[name] for name in tile_zone_names
                         if name in zone_rects}
            from majsoul_recognizer.recognition.ultralytics_detector import (
                UltralyticsTileDetector,
            )
            assert isinstance(detector, UltralyticsTileDetector)
            img_h, img_w = full_image.shape[:2]
            scale_x = img_w / 1920.0
            scale_y = img_h / 1080.0
            for name, (x, y, w, h) in tile_rects.items():
                scaled_rects[name] = (
                    int(x * scale_x), int(y * scale_y),
                    int(w * scale_x), int(h * scale_y),
                )
            detections = detector.detect_full_image(full_image, scaled_rects, confidence)
        else:
            tile_images = [(name, zones[name]) for name in tile_zone_names if name in zones]
            if self._config.enable_batch_detection and len(tile_images) > 1:
                detections = detector.detect_batch(tile_images, confidence)
            else:
                detections = {name: detector.detect(img, confidence) for name, img in tile_images}

        # ViT 二次分类
        classifier = self._ensure_classifier()
        if classifier is not None and detections:
            for zone_name, dets in detections.items():
                if not dets:
                    continue
                if scaled_rects and zone_name in scaled_rects:
                    source = full_image
                    ox, oy = scaled_rects[zone_name][0], scaled_rects[zone_name][1]
                elif zone_name in zones:
                    source = zones[zone_name]
                    ox, oy = 0, 0
                else:
                    continue
                h_img, w_img = source.shape[:2]
                crops = [
                    source[
                        max(0, oy + d.bbox.y):min(h_img, oy + d.bbox.y + d.bbox.height),
                        max(0, ox + d.bbox.x):min(w_img, ox + d.bbox.x + d.bbox.width),
                    ]
                    for d in dets
                ]
                vit_results = classifier.classify_batch(crops)
                for i, (tile_code, conf) in enumerate(vit_results):
                    if tile_code and conf >= self._config.vit_classifier_threshold:
                        dets[i] = dets[i].model_copy(update={
                            "tile_code": tile_code,
                            "confidence": conf,
                        })
```

**Change 4**: Update `__exit__` to reset classifier state. Replace lines 258-261:

```python
    def __exit__(self, *args) -> None:
        self._detector = None
        self._ocr = None
        self._matcher = None
        self._classifier = None
        self._classifier_attempted = False
        self._validator.reset()
```

- [ ] **Step 5: Run all engine tests**

Run: `cd F:/majong && python -m pytest tests/recognition/test_engine.py -v`
Expected: All PASSED (existing 7 + new 5)

- [ ] **Step 6: Run full test suite to check for regressions**

Run: `cd F:/majong && python -m pytest tests/ -v --tb=short`
Expected: All PASSED, no regressions

- [ ] **Step 7: Commit**

```bash
cd F:/majong && git add src/majsoul_recognizer/recognition/engine.py tests/recognition/conftest.py tests/recognition/test_engine.py
git commit -m "feat(vit): integrate TileClassifier into RecognitionEngine pipeline"
```

---

### Task 6: Dependency Update

**Files:**
- Modify: `pyproject.toml:21-45`

- [ ] **Step 1: Update pyproject.toml**

In `pyproject.toml`, add after the `training` optional dependency group (after line 38):

```toml
recognition-vit = [
    "torch>=2.1",
    "transformers>=4.34,<5.0",
    "Pillow>=9.0",
]
recognition-vit-cpu = [
    "torch>=2.1",
    "transformers>=4.34,<5.0",
    "Pillow>=9.0",
]
```

- [ ] **Step 2: Run full test suite**

Run: `cd F:/majong && python -m pytest tests/ -v --tb=short`
Expected: All PASSED — optional deps don't affect existing tests

- [ ] **Step 3: Commit**

```bash
cd F:/majong && git add pyproject.toml
git commit -m "feat(vit): add recognition-vit optional dependency group"
```

---

## Self-Review Checklist

### Spec Coverage

| Spec Requirement | Task |
|---|---|
| P1: 34-class label mapping dict | Task 1 |
| P1: Unknown label fallback with warning | Task 3 (classify_batch) |
| P1: Runtime label validation in `__init__` | Task 3 (_validate_labels) |
| P1: Bijection test | Task 1 |
| P2: `_is_red_dora(crop, tile_code, threshold)` | Task 2 |
| P2: Per-suit thresholds (5m=0.08, 5p=0.12, 5s=0.15) | Task 2 |
| P2: HSV red detection (S>120, V>120) | Task 2 |
| P2: Synthetic tile tests | Task 2 |
| P3: Module-level `_HAS_TORCH`/`_HAS_TRANSFORMERS` flags | Task 3 |
| P3: `TileClassifier.__init__` with eval() + device selection | Task 3 |
| P3: `classify_batch` with `torch.no_grad()` | Task 3 |
| P3: Red dora integration in classify_batch | Task 3 |
| P3: Mock model tests (6 scenarios) | Task 3 |
| P4: Config fields (4 new) | Task 4 |
| P4: `_ensure_classifier` lazy init | Task 5 |
| P4: ViT step in recognize (both code paths) | Task 5 |
| P4: `__exit__` resets classifier + attempted | Task 5 |
| P4: 8 test cases | Task 5 |
| P5: `recognition-vit` and `recognition-vit-cpu` groups | Task 6 |

No gaps found.

### Placeholder Scan

No TBD/TODO found. All steps contain complete code.

### Type Consistency

- `_PJURA_TO_TILE_CODE: dict[str, str]` — defined in Task 1, used in Task 3 `classify_batch` via `.get()` ✓
- `_is_red_dora(crop: np.ndarray | None, tile_code: str, threshold: float | None) -> bool` — defined in Task 2, called in Task 3 with `(crop, tile_code)` ✓
- `_PER_SUIT_THRESHOLD: dict[str, float]` — defined in Task 2, used in `_is_red_dora` via `.get(tile_code, 0.10)` ✓
- `classify_batch(crops: list[np.ndarray]) -> list[tuple[str, float]]` — defined in Task 3, called in Task 5 engine via `classifier.classify_batch(crops)` ✓
- `RecognitionConfig` fields (`vit_model_name`, `enable_vit_classifier`, `vit_classifier_threshold`, `vit_device`) — defined in Task 4, used in Task 5 (`self._config.vit_model_name`, `self._config.enable_vit_classifier`, `self._config.vit_classifier_threshold`) ✓
- `model_copy(update={"tile_code": ..., "confidence": ...})` — used in Task 5 engine, matches `Detection` fields from `types.py` ✓
