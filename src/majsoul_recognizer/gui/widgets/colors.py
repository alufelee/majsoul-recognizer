"""牌面颜色映射 + 区域颜色方案

纯逻辑模块，无 tkinter 依赖，可全平台测试。
"""

_TILE_CATEGORY_COLORS: dict[str, str] = {
    "m": "#b4befe",    # Manzu - lavender
    "p": "#89dceb",    # Pinzu - sky
    "s": "#f38ba8",    # Souzu - red
    "z": "#f2cdcd",    # Honors - flamingo
    "r": "#fab387",    # Red dora - peach
    "x": "#6c7086",    # Special - fg_muted
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
    "hand": "#a6e3a1",
    "dora": "#fab387",
    "round_info": "#89b4fa",
    "score_self": "#cba6f7", "score_right": "#cba6f7",
    "score_opposite": "#cba6f7", "score_left": "#cba6f7",
    "discards_self": "#94e2d5", "discards_right": "#94e2d5",
    "discards_opposite": "#94e2d5", "discards_left": "#94e2d5",
    "calls_self": "#f9e2af",
    "actions": "#fab387",
    "timer": "#6c7086",
}
