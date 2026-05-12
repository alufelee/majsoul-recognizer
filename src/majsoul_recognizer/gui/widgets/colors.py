"""牌面颜色映射 + 区域颜色方案

纯逻辑模块，无 tkinter 依赖，可全平台测试。
Cyberpunk HUD 风格 — 霓虹色检测框。
"""

_TILE_CATEGORY_COLORS: dict[str, str] = {
    "m": "#8888ff",    # Manzu - lavender neon
    "p": "#00ddee",    # Pinzu - cyan neon
    "s": "#ff3366",    # Souzu - red neon
    "z": "#ff6688",    # Honors - pink neon
    "r": "#ffcc00",    # Red dora - yellow neon
    "x": "#4a4a6a",    # Special - muted
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
    "hand": "#00ff88",
    "dora": "#ffcc00",
    "round_info": "#00bbff",
    "score_self": "#cc44ff", "score_right": "#cc44ff",
    "score_opposite": "#cc44ff", "score_left": "#cc44ff",
    "discards_self": "#00ccaa", "discards_right": "#00ccaa",
    "discards_opposite": "#00ccaa", "discards_left": "#00ccaa",
    "calls_self": "#ff8844",
    "actions": "#ff8844",
    "timer": "#4a4a6a",
}
