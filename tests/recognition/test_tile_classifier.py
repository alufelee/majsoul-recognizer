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
