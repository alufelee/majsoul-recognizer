# Task: colors.py — Catppuccin 检测框/区域颜色

## 文件
- 修改: `src/majsoul_recognizer/gui/widgets/colors.py`
- 测试: `tests/gui/widgets/test_colors.py` (只检查 hex 格式，无需改动)

## _TILE_CATEGORY_COLORS 替换

```python
_TILE_CATEGORY_COLORS: dict[str, str] = {
    "m": "#b4befe",    # 万子 - lavender
    "p": "#89dceb",    # 筒子 - sky
    "s": "#f38ba8",    # 索子 - red
    "z": "#f2cdcd",    # 字牌 - flamingo
    "r": "#fab387",    # 赤宝牌 - peach
    "x": "#6c7086",    # 特殊 - fg_muted
}
```

## ZONE_COLORS 替换

```python
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
```
