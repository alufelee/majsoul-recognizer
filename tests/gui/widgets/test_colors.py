"""牌面颜色映射测试 — 纯逻辑，无 tkinter 依赖"""

from majsoul_recognizer.gui.widgets.colors import (
    ZONE_COLORS,
    _TILE_CATEGORY_COLORS,
    _get_tile_category,
)


class TestGetTileCategory:
    """tile_code → 类别字母映射"""

    def test_manpin(self):
        """万子"""
        for i in range(1, 10):
            assert _get_tile_category(f"{i}m") == "m"

    def test_pin(self):
        """筒子"""
        for i in range(1, 10):
            assert _get_tile_category(f"{i}p") == "p"

    def test_sou(self):
        """索子"""
        for i in range(1, 10):
            assert _get_tile_category(f"{i}s") == "s"

    def test_honor(self):
        """字牌 1z-7z"""
        for i in range(1, 8):
            assert _get_tile_category(f"{i}z") == "z"

    def test_red_dora(self):
        """赤宝牌"""
        assert _get_tile_category("5mr") == "r"
        assert _get_tile_category("5pr") == "r"
        assert _get_tile_category("5sr") == "r"

    def test_special(self):
        """特殊牌"""
        assert _get_tile_category("back") == "x"
        assert _get_tile_category("rotated") == "x"
        assert _get_tile_category("dora_frame") == "x"

    def test_unknown(self):
        """未知类别归入特殊"""
        assert _get_tile_category("unknown") == "x"
        assert _get_tile_category("") == "x"


class TestTileCategoryColors:
    def test_all_categories_have_colors(self):
        """每个类别字母都有对应颜色"""
        for cat in ("m", "p", "s", "z", "r", "x"):
            assert cat in _TILE_CATEGORY_COLORS

    def test_colors_are_hex(self):
        for key, value in _TILE_CATEGORY_COLORS.items():
            assert value.startswith("#"), f"{key} = {value!r}"
            assert len(value) == 7, f"{key} = {value!r}"


class TestZoneColors:
    def test_zone_colors_is_dict(self):
        assert isinstance(ZONE_COLORS, dict)
        assert len(ZONE_COLORS) > 0

    def test_zone_colors_are_hex(self):
        for key, value in ZONE_COLORS.items():
            assert value.startswith("#"), f"{key} = {value!r}"
            assert len(value) == 7, f"{key} = {value!r}"
