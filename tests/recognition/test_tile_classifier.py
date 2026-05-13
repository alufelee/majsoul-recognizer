"""TileClassifier 测试"""

from unittest.mock import MagicMock

import numpy as np
import pytest

from majsoul_recognizer.tile import Tile

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False


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


class TestIsRedDora:
    """P2: 赤宝牌颜色检测测试"""

    def test_red_image_detected(self):
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        red_img = np.zeros((50, 50, 3), dtype=np.uint8)
        red_img[:, :, 2] = 200
        assert _is_red_dora(red_img, "5m") is True

    def test_blue_image_not_red(self):
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        blue_img = np.zeros((50, 50, 3), dtype=np.uint8)
        blue_img[:, :, 0] = 200
        assert _is_red_dora(blue_img, "5p") is False

    def test_green_image_not_red(self):
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        green_img = np.zeros((50, 50, 3), dtype=np.uint8)
        green_img[:, :, 1] = 200
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
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        img = np.full((60, 50, 3), [40, 80, 40], dtype=np.uint8)
        img[10:50, 5:45] = [220, 220, 220]
        img[20:40, 15:35] = [0, 0, 200]
        assert _is_red_dora(img, "5m") is True

    def test_synthetic_normal_tile_not_red(self):
        from majsoul_recognizer.recognition.tile_classifier import _is_red_dora
        img = np.full((60, 50, 3), [40, 80, 40], dtype=np.uint8)
        img[10:50, 5:45] = [220, 220, 220]
        img[20:40, 15:35] = [200, 100, 0]
        assert _is_red_dora(img, "5m") is False


_PJURA_ID2LABEL = {
    0: "1b", 1: "1n", 2: "1p", 3: "2b", 4: "2n", 5: "2p",
    6: "3b", 7: "3n", 8: "3p", 9: "4b", 10: "4n", 11: "4p",
    12: "5b", 13: "5n", 14: "5p", 15: "6b", 16: "6n", 17: "6p",
    18: "7b", 19: "7n", 20: "7p", 21: "8b", 22: "8n", 23: "8p",
    24: "9b", 25: "9n", 26: "9p", 27: "ew", 28: "gd", 29: "nw",
    30: "rd", 31: "sw", 32: "wd", 33: "ww",
}


def _make_mock_classifier():
    from majsoul_recognizer.recognition.tile_classifier import TileClassifier
    classifier = TileClassifier.__new__(TileClassifier)
    classifier._model = MagicMock()
    classifier._processor = MagicMock()
    classifier._model.config.id2label = _PJURA_ID2LABEL
    classifier._device = MagicMock()
    return classifier


def _set_mock_output(classifier, class_index, batch_size=1):
    try:
        import torch
    except ImportError:
        pytest.skip("torch not installed")
    logits = torch.full((batch_size, 34), -10.0)
    logits[0, class_index] = 10.0
    mock_output = MagicMock()
    mock_output.logits = logits
    classifier._model.return_value = mock_output
    classifier._processor.return_value = {"pixel_values": MagicMock()}


@pytest.mark.skipif(
    not _HAS_TORCH,
    reason="torch not installed",
)
class TestTileClassifierBatch:
    """P3: TileClassifier classify_batch 测试"""

    def test_batch_maps_1b_to_1s(self):
        classifier = _make_mock_classifier()
        _set_mock_output(classifier, 0)
        results = classifier.classify_batch([np.zeros((50, 50, 3), dtype=np.uint8)])
        assert results[0][0] == "1s"
        assert results[0][1] > 0.99

    def test_batch_maps_ew_to_1z(self):
        classifier = _make_mock_classifier()
        _set_mock_output(classifier, 27)
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
        _set_mock_output(classifier, 30)
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
        classifier = _make_mock_classifier()
        _set_mock_output(classifier, 13)  # "5n" → "5m"
        red_img = np.zeros((50, 50, 3), dtype=np.uint8)
        red_img[:, :, 2] = 200
        results = classifier.classify_batch([red_img])
        assert results[0][0] == "5mr"

    def test_normal_five_not_red_dora(self):
        classifier = _make_mock_classifier()
        _set_mock_output(classifier, 13)  # "5n" → "5m"
        blue_img = np.zeros((50, 50, 3), dtype=np.uint8)
        blue_img[:, :, 0] = 200
        results = classifier.classify_batch([blue_img])
        assert results[0][0] == "5m"
