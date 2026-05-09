"""牌面颜色映射 + 区域颜色方案

纯逻辑模块，无 tkinter 依赖，可全平台测试。
"""

_TILE_CATEGORY_COLORS: dict[str, str] = {
    "m": "#4caf50",    # 万子 - 绿
    "p": "#2196f3",    # 筒子 - 蓝
    "s": "#f44336",    # 索子 - 红
    "z": "#9c27b0",    # 字牌 - 紫
    "r": "#ff9800",    # 赤宝牌 - 橙
    "x": "#9e9e9e",    # 特殊 - 灰
}


def _get_tile_category(tile_code: str) -> str:
    """将 tile_code 映射为类别字母，用于检测框着色

    映射规则（与 _DEFAULT_CLASS_MAP 一致）:
      5mr/5pr/5sr → "r" (赤宝牌)
      back/rotated/dora_frame → "x" (特殊)
      1m-9m → "m", 1p-9p → "p", 1s-9s → "s" (数字牌)
      1z-7z → "z" (字牌)
    """
    if tile_code in ("5mr", "5pr", "5sr"):
        return "r"
    if tile_code in ("back", "rotated", "dora_frame"):
        return "x"
    suffix = tile_code[-1:]
    if suffix in ("m", "p", "s"):
        return suffix
    if suffix == "z":
        return "z"
    return "x"


ZONE_COLORS: dict[str, str] = {
    "hand": "#4caf50",
    "dora": "#ff9800",
    "round_info": "#2196f3",
    "score_self": "#9c27b0",
    "score_right": "#9c27b0",
    "score_opposite": "#9c27b0",
    "score_left": "#9c27b0",
    "discards_self": "#00bcd4",
    "discards_right": "#00bcd4",
    "discards_opposite": "#00bcd4",
    "discards_left": "#00bcd4",
    "calls_self": "#e91e63",
    "actions": "#ff5722",
    "timer": "#607d8b",
}
