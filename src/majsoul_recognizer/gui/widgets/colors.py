"""牌面颜色映射 + 区域颜色方案

纯逻辑模块，无 tkinter 依赖，可全平台测试。
玻璃质感 — 柔和饱和色检测框。
"""

_TILE_CATEGORY_COLORS: dict[str, str] = {
    "m": "#818CF8",    # Manzu - lavender
    "p": "#0EA5E9",    # Pinzu - sky
    "s": "#FB7185",    # Souzu - flamingo
    "z": "#A855F7",    # Honors - purple
    "r": "#EAB308",    # Red dora - yellow
    "x": "#64748B",    # Special - muted
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
    "hand": "#22C55E",
    "dora": "#EAB308",
    "round_info": "#3B82F6",
    "score_self": "#A855F7", "score_right": "#A855F7",
    "score_opposite": "#A855F7", "score_left": "#A855F7",
    "discards_self": "#14B8A6", "discards_right": "#14B8A6",
    "discards_opposite": "#14B8A6", "discards_left": "#14B8A6",
    "calls_self": "#F97316",
    "actions": "#F97316",
    "timer": "#64748B",
}
