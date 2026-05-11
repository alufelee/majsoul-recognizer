# Phase 1: 配色和样式迁移

> 母规格: `2026-05-11-gui-visual-redesign.md` (v3)
> 阶段: Phase 1 — 可独立编译、独立提交

## 涉及文件

| 文件 | 改动类型 |
|------|---------|
| `src/majsoul_recognizer/gui/theme.py` | 重写 Theme dicts + apply_style |
| `src/majsoul_recognizer/gui/widgets/colors.py` | 更新检测框和区域颜色 |
| `src/majsoul_recognizer/gui/app.py` | theme key 引用替换 |
| `src/majsoul_recognizer/gui/views/dev_view.py` | theme key 引用替换 |
| `src/majsoul_recognizer/gui/views/screenshot_view.py` | theme key 引用替换（无结构性改动） |
| `src/majsoul_recognizer/gui/views/live_view.py` | theme key 引用替换（无结构性改动） |
| `src/majsoul_recognizer/gui/widgets/result_panel.py` | theme key 引用替换（Phase 3 重写前过渡） |
| `src/majsoul_recognizer/gui/widgets/image_canvas.py` | theme key 引用替换 |
| `tests/gui/test_theme.py` | 断言更新 |
| `tests/gui/widgets/test_colors.py` | 断言更新 |

## 不变的文件

`worker.py`, `app_state.py`, `settings.py`, `fps_counter.py`, `base_view.py`, `settings_dialog.py` — 无 theme key 直接引用。

## 1. Theme Dict 迁移映射

| 旧 key | 新 key | 深色值 | 浅色值 | 用途 |
|--------|--------|--------|--------|------|
| `bg_primary` | `bg_base` | `#1e1e2e` | `#eff1f5` | 主背景 |
| `bg_secondary` | `bg_mantle` | `#181825` | `#e6e9ef` | 标题栏、面板底色 |
| `bg_tertiary` | `bg_surface0` | `#313244` | `#ccd0da` | 卡片背景、输入框 |
| _(新增)_ | `bg_surface1` | `#45475a` | `#bcc0cc` | hover 背景 |
| `bg_sidebar` | `bg_crust` | `#11111b` | `#dce0e8` | 侧边栏、画布底色、状态栏 |
| `bg_header` | `bg_mantle` | `#181825` | `#e6e9ef` | 标题栏（复用 mantle） |
| `fg_primary` | `fg_primary` | `#cdd6f4` | `#4c4f69` | _(不变)_ |
| `fg_secondary` | `fg_secondary` | `#a6adc8` | `#7c7f93` | _(不变)_ |
| `fg_muted` | `fg_muted` | `#6c7086` | `#9ca0b0` | _(不变)_ |
| `accent` | `accent` | `#89b4fa` | `#1e66f5` | _(不变)_ |
| `accent_dim` | `accent_dim` | `#1a3a5c` | `#a8c8f0` | _(值变化)_ |
| `success` | `green` | `#a6e3a1` | `#40a02b` | 成功/就绪 |
| `warning` | `peach` | `#fab387` | `#fe640b` | 警告 |
| `error` | `red` | `#f38ba8` | `#d20f39` | 错误 |
| `highlight` | `peach` | `#fab387` | `#fe640b` | 摸牌高亮（复用 peach） |
| `border` | `bg_surface0` | `#313244` | `#ccd0da` | 分割线（复用 surface0） |
| `canvas_bg` | `bg_crust` | `#11111b` | `#dce0e8` | 画布背景（复用 crust） |
| _(新增)_ | `blue` | `#89b4fa` | `#1e66f5` | 局次标签 |
| _(新增)_ | `yellow` | `#f9e2af` | `#df8e1d` | 副露标签 |
| _(新增)_ | `mauve` | `#cba6f7` | `#8839ef` | 分数标签 |
| _(新增)_ | `teal` | `#94e2d5` | `#179299` | 牌河标签 |
| _(新增)_ | `lavender` | `#b4befe` | `#7287fd` | 万子检测框 |
| _(新增)_ | `sky` | `#89dceb` | `#04a5e5` | 筒子检测框 |
| _(新增)_ | `flamingo` | `#f2cdcd` | `#dd7878` | 字牌检测框 |
| _(新增)_ | `surface_hover` | `#45475a` | `#bcc0cc` | 按钮 hover 背景 |

**新 key 集合 (21个):** `bg_base`, `bg_mantle`, `bg_surface0`, `bg_surface1`, `bg_crust`, `fg_primary`, `fg_secondary`, `fg_muted`, `accent`, `accent_dim`, `green`, `peach`, `red`, `blue`, `yellow`, `mauve`, `teal`, `lavender`, `sky`, `flamingo`, `surface_hover`

## 2. apply_style() 变更

**Phase 1 保留旧样式名**（Phase 2 删除）: `Sidebar.TFrame`, `Header.TFrame`, `Nav.TButton`, `NavActive.TButton`, `Toolbar.TFrame` — 但内部引用的 theme key 更新为新名。

**Phase 1 新增样式:**
- `Small.TButton` — 状态栏小按钮 (padding=(8,2))
- `SmallAccent.TButton` — 状态栏强调按钮 (padding=(8,2))
- `PanelHeader.TLabel` — 面板标题
- `CardLabel.TLabel` — 卡片标签 (9px)
- `CardValue.TLabel` — 卡片值 (11px)
- `StatusBar.TFrame` — 状态栏容器背景 (bg_crust)
- `Card.TFrame` — 卡片容器背景 (bg_crust)

**TButton 默认样式更新:**
- 背景: `bg_tertiary` → `bg_surface0`
- Hover: `accent` → `bg_surface1`
- 禁用前景: `fg_muted`（不变）

**Accent.TButton 更新:**
- Hover 背景: `highlight` → `surface_hover`
- 禁用背景: `bg_surface0`

**Status.TLabel 更新:**
- 背景: `bg_primary` → `bg_crust`

## 3. 检测框颜色

`colors.py` 更新为 Catppuccin 色板:

```python
_TILE_CATEGORY_COLORS: dict[str, str] = {
    "m": "#b4befe",    # 万子 - lavender
    "p": "#89dceb",    # 筒子 - sky
    "s": "#f38ba8",    # 索子 - red
    "z": "#f2cdcd",    # 字牌 - flamingo
    "r": "#fab387",    # 赤宝牌 - peach
    "x": "#6c7086",    # 特殊 - fg_muted
}

ZONE_COLORS: dict[str, str] = {
    "hand": "#a6e3a1",
    "dora": "#fab387",
    "round_info": "#89b4fa",
    "score_self": "#cba6f7",
    "score_right": "#cba6f7",
    "score_opposite": "#cba6f7",
    "score_left": "#cba6f7",
    "discards_self": "#94e2d5",
    "discards_right": "#94e2d5",
    "discards_opposite": "#94e2d5",
    "discards_left": "#94e2d5",
    "calls_self": "#f9e2af",
    "actions": "#fab387",
    "timer": "#6c7086",
}
```

## 4. 全项目 key 引用替换

以下为每个文件的精确替换映射:

**`image_canvas.py`:**
- `theme["canvas_bg"]` → `theme["bg_crust"]` (2处)

**`result_panel.py` (Phase 1 仅 key 替换，Phase 3 重写):**
- `theme["bg_secondary"]` → `theme["bg_mantle"]` (3处)
- `theme["highlight"]` → `theme["peach"]` (1处)
- `theme["warning"]` → `theme["peach"]` (1处)

**`dev_view.py`:**
- `theme["bg_secondary"]` → `theme["bg_mantle"]` (1处)

**`app.py`:**
- `theme["bg_primary"]` → `theme["bg_base"]` (多处)
- `theme["bg_secondary"]` → `theme["bg_mantle"]`
- `theme["bg_tertiary"]` → `theme["bg_surface0"]`
- `theme["bg_sidebar"]` → `theme["bg_crust"]`
- `theme["bg_header"]` → `theme["bg_mantle"]`
- `theme["success"]` → `theme["green"]`
- `theme["border"]` → `theme["bg_surface0"]`

## 5. 测试断言更新

**`test_theme.py`:**
- `expected_keys` 从 16 个旧 key 更新为 21 个新 key
- `get_theme("dark")` 返回值断言 `accent` 值不变 (`#89b4fa`)
- `get_theme("light")` 返回值断言 `accent` 值从 `#1565c0` 更新为 `#1e66f5`

**`test_colors.py`:**
- 颜色值断言随 `colors.py` 更新（测试只检查 hex 格式和类别覆盖，不检查具体值，因此可能无需改动）
