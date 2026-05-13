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
