# Task: 全局 theme key 迁移

## 文件
- 修改: `image_canvas.py`, `result_panel.py`, `dev_view.py`, `app.py`

## 精确替换映射

### image_canvas.py (2处)
- L24: `theme["canvas_bg"]` → `theme["bg_crust"]`
- L82: `theme["canvas_bg"]` → `theme["bg_crust"]`

### result_panel.py (6处)
- L21: `theme["bg_secondary"]` → `theme["bg_mantle"]`
- L26: `theme["highlight"]` → `theme["peach"]`
- L27: `theme["warning"]` → `theme["peach"]`
- L42: `theme["bg_secondary"]` → `theme["bg_mantle"]`
- L45: `theme["highlight"]` → `theme["peach"]`
- L46: `theme["warning"]` → `theme["peach"]`

### dev_view.py (2处)
- L50: `theme["bg_secondary"]` → `theme["bg_mantle"]`
- L124: `theme["bg_secondary"]` → `theme["bg_mantle"]`

### app.py (7处)
- L152: `theme["bg_primary"]` → `theme["bg_base"]`
- L154: `theme["success"]` → `theme["green"]`
- L211: `new_theme["border"]` → `new_theme["bg_surface0"]`
- L214: `new_theme["bg_primary"]` → `new_theme["bg_base"]`
- L216: `new_theme["success"]` → `new_theme["green"]`
- theme.py apply_style 中所有旧 key 引用（已在 Task 01 处理）

## 验证

运行: `pytest tests/gui/ -v` — 全部通过
