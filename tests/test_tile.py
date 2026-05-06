"""Tile 枚举与编码测试"""

import pytest

from majsoul_recognizer.tile import Tile, tile_from_str, TileCategory


class TestTileEnum:
    """Tile 枚举基本属性测试"""

    def test_total_tile_count(self):
        """总牌面类型数: 34 标准 (9+9+9+7) + 3 赤宝牌 = 37"""
        assert len(Tile) == 37

    def test_manzu_tiles(self):
        """万子 1-9 编码正确"""
        for i in range(1, 10):
            tile = Tile[f"M{i}"]
            assert tile.value == f"{i}m"

    def test_pinzu_tiles(self):
        """筒子 1-9 编码正确"""
        for i in range(1, 10):
            tile = Tile[f"P{i}"]
            assert tile.value == f"{i}p"

    def test_souzu_tiles(self):
        """索子 1-9 编码正确"""
        for i in range(1, 10):
            tile = Tile[f"S{i}"]
            assert tile.value == f"{i}s"

    def test_wind_tiles(self):
        """风牌编码: 东南西北"""
        assert Tile.TZ1.value == "1z"  # 东
        assert Tile.TZ2.value == "2z"  # 南
        assert Tile.TZ3.value == "3z"  # 西
        assert Tile.TZ4.value == "4z"  # 北

    def test_dragon_tiles(self):
        """三翻身编码: 白发中"""
        assert Tile.TZ5.value == "5z"  # 白
        assert Tile.TZ6.value == "6z"  # 发
        assert Tile.TZ7.value == "7z"  # 中

    def test_red_dora_tiles(self):
        """赤宝牌编码"""
        assert Tile.M5R.value == "5mr"
        assert Tile.P5R.value == "5pr"
        assert Tile.S5R.value == "5sr"


class TestTileCategory:
    """牌面分类属性测试"""

    def test_manzu_category(self):
        assert Tile.M1.category == TileCategory.MANZU
        assert Tile.M9.category == TileCategory.MANZU

    def test_pinzu_category(self):
        assert Tile.P1.category == TileCategory.PINZU
        assert Tile.P9.category == TileCategory.PINZU

    def test_souzu_category(self):
        assert Tile.S1.category == TileCategory.SOUZU
        assert Tile.S9.category == TileCategory.SOUZU

    def test_tsuhai_category(self):
        assert Tile.TZ1.category == TileCategory.TSUHAI
        assert Tile.TZ7.category == TileCategory.TSUHAI

    def test_red_dora_category(self):
        """赤宝牌归类到对应花色"""
        assert Tile.M5R.category == TileCategory.MANZU
        assert Tile.P5R.category == TileCategory.PINZU
        assert Tile.S5R.category == TileCategory.SOUZU

    def test_numbered_tiles_have_number(self):
        """数牌有数字属性"""
        assert Tile.M3.number == 3
        assert Tile.P7.number == 7
        assert Tile.S1.number == 1

    def test_tsuhai_no_number(self):
        """字牌无数字"""
        assert Tile.TZ1.number is None

    def test_red_dora_number(self):
        """赤宝牌数字为 5"""
        assert Tile.M5R.number == 5

    def test_is_red_dora(self):
        assert Tile.M5R.is_red_dora is True
        assert Tile.M5.is_red_dora is False
        assert Tile.TZ1.is_red_dora is False

    def test_display_name(self):
        """显示名称正确"""
        assert Tile.M1.display_name == "一万"
        assert Tile.P5.display_name == "五筒"
        assert Tile.TZ1.display_name == "东"
        assert Tile.TZ5.display_name == "白"
        assert Tile.M5R.display_name == "赤五万"


class TestTileFromString:
    """从字符串解析牌面测试"""

    @pytest.mark.parametrize(
        "code,expected",
        [
            ("1m", Tile.M1),
            ("9m", Tile.M9),
            ("1p", Tile.P1),
            ("9p", Tile.P9),
            ("1s", Tile.S1),
            ("9s", Tile.S9),
            ("1z", Tile.TZ1),
            ("7z", Tile.TZ7),
            ("5mr", Tile.M5R),
            ("5pr", Tile.P5R),
            ("5sr", Tile.S5R),
        ],
    )
    def test_valid_codes(self, code, expected):
        assert tile_from_str(code) == expected

    def test_invalid_code_raises(self):
        with pytest.raises(ValueError, match="Unknown tile code"):
            tile_from_str("0m")

    def test_empty_code_raises(self):
        with pytest.raises(ValueError, match="Unknown tile code"):
            tile_from_str("")
