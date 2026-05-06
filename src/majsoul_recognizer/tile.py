"""牌面类型枚举与编码

定义雀魂麻将中所有牌面类型，支持编码转换和属性查询。
34 种标准牌面 (万子9+筒子9+索子9+字牌7) + 3 种赤宝牌 = 37 种类型。

编码规则:
  万子: 1m-9m  筒子: 1p-9p  索子: 1s-9s
  字牌: 1z-7z (东南西北白发中)
  赤宝牌: 5mr, 5pr, 5sr (红五)
"""

from enum import Enum


class TileCategory(Enum):
    """牌面花色分类"""
    MANZU = "manzu"    # 万子
    PINZU = "pinzu"    # 筒子
    SOUZU = "souzu"    # 索子
    TSUHAI = "tsuhai"  # 字牌


# 字牌显示名映射
_TSUHAI_NAMES = {
    "1z": "东", "2z": "南", "3z": "西", "4z": "北",
    "5z": "白", "6z": "发", "7z": "中",
}

# 中文数字映射
_CN_NUMBERS = {
    1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
    6: "六", 7: "七", 8: "八", 9: "九",
}

# 花色后缀
_SUIT_SUFFIX = {"m": "万", "p": "筒", "s": "索"}


class Tile(str, Enum):
    """雀魂麻将牌面类型

    使用字符串枚举，值即为编码（如 "1m", "5pr"）。
    """

    # 万子 1-9
    M1 = "1m"
    M2 = "2m"
    M3 = "3m"
    M4 = "4m"
    M5 = "5m"
    M6 = "6m"
    M7 = "7m"
    M8 = "8m"
    M9 = "9m"

    # 筒子 1-9
    P1 = "1p"
    P2 = "2p"
    P3 = "3p"
    P4 = "4p"
    P5 = "5p"
    P6 = "6p"
    P7 = "7p"
    P8 = "8p"
    P9 = "9p"

    # 索子 1-9
    S1 = "1s"
    S2 = "2s"
    S3 = "3s"
    S4 = "4s"
    S5 = "5s"
    S6 = "6s"
    S7 = "7s"
    S8 = "8s"
    S9 = "9s"

    # 字牌 (风牌 + 三翻身)
    TZ1 = "1z"  # 东
    TZ2 = "2z"  # 南
    TZ3 = "3z"  # 西
    TZ4 = "4z"  # 北
    TZ5 = "5z"  # 白
    TZ6 = "6z"  # 发
    TZ7 = "7z"  # 中

    # 赤宝牌 (红五)
    M5R = "5mr"
    P5R = "5pr"
    S5R = "5sr"

    @property
    def category(self) -> TileCategory:
        """牌面花色分类"""
        base = self.value.rstrip("r")
        if base.endswith("m"):
            return TileCategory.MANZU
        if base.endswith("p"):
            return TileCategory.PINZU
        if base.endswith("s"):
            return TileCategory.SOUZU
        return TileCategory.TSUHAI

    @property
    def number(self) -> int | None:
        """数牌的数字 (1-9)，字牌返回 None"""
        code = self.value.rstrip("r")
        if code.endswith("z"):
            return None
        return int(code[0])

    @property
    def is_red_dora(self) -> bool:
        """是否为赤宝牌"""
        return self.value.endswith("r")

    @property
    def display_name(self) -> str:
        """中文显示名称"""
        code = self.value
        if code in _TSUHAI_NAMES:
            return _TSUHAI_NAMES[code]
        # 赤宝牌
        if code.endswith("r"):
            num_code = code[0]
            suit = code[-2]
            return f"赤{_CN_NUMBERS[int(num_code)]}{_SUIT_SUFFIX[suit]}"
        # 数牌
        return f"{_CN_NUMBERS[int(code[0])]}{_SUIT_SUFFIX[code[-1]]}"


# 构建快速查找表
_TILE_LOOKUP: dict[str, Tile] = {t.value: t for t in Tile}


def tile_from_str(code: str) -> Tile:
    """从编码字符串解析牌面类型

    Args:
        code: 牌面编码，如 "1m", "5pr", "7z"

    Returns:
        对应的 Tile 枚举成员

    Raises:
        ValueError: 编码无法识别
    """
    if code in _TILE_LOOKUP:
        return _TILE_LOOKUP[code]
    raise ValueError(f"Unknown tile code: '{code}'")
