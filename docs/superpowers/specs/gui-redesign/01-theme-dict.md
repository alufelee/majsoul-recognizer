# Task: theme.py — Catppuccin 色板重写

## 文件
- 重写: `src/majsoul_recognizer/gui/theme.py`
- 更新: `tests/gui/test_theme.py`

## Theme.DARK 新 key (21个)

```python
DARK = {
    "bg_base": "#1e1e2e",        # 主背景 (原 bg_primary)
    "bg_mantle": "#181825",      # 标题栏/面板 (原 bg_secondary/bg_header)
    "bg_surface0": "#313244",    # 卡片/输入框 (原 bg_tertiary/border)
    "bg_surface1": "#45475a",    # hover 背景 (新增)
    "bg_crust": "#11111b",       # 侧边栏/画布/状态栏 (原 bg_sidebar/canvas_bg)
    "fg_primary": "#cdd6f4",     # 不变
    "fg_secondary": "#a6adc8",   # 不变
    "fg_muted": "#6c7086",       # 不变
    "accent": "#89b4fa",         # 不变
    "accent_dim": "#1a3a5c",     # 不变
    "green": "#a6e3a1",          # (原 success)
    "peach": "#fab387",          # (原 warning/highlight)
    "red": "#f38ba8",            # (原 error)
    "blue": "#89b4fa",           # 新增: 数据标签
    "yellow": "#f9e2af",         # 新增: 副露标签
    "mauve": "#cba6f7",          # 新增: 分数标签
    "teal": "#94e2d5",           # 新增: 牌河标签
    "lavender": "#b4befe",       # 新增: 万子检测框
    "sky": "#89dceb",            # 新增: 筒子检测框
    "flamingo": "#f2cdcd",       # 新增: 字牌检测框
    "surface_hover": "#45475a",  # 新增: 按钮 hover
}
```

## Theme.LIGHT 新 key (Catppuccin Latte)

```python
LIGHT = {
    "bg_base": "#eff1f5", "bg_mantle": "#e6e9ef",
    "bg_surface0": "#ccd0da", "bg_surface1": "#bcc0cc",
    "bg_crust": "#dce0e8",
    "fg_primary": "#4c4f69", "fg_secondary": "#7c7f93", "fg_muted": "#9ca0b0",
    "accent": "#1e66f5", "accent_dim": "#a8c8f0",
    "green": "#40a02b", "peach": "#fe640b", "red": "#d20f39",
    "blue": "#1e66f5", "yellow": "#df8e1d", "mauve": "#8839ef",
    "teal": "#179299", "lavender": "#7287fd", "sky": "#04a5e5",
    "flamingo": "#dd7878", "surface_hover": "#bcc0cc",
}
```

## apply_style() 更新

1. **TButton 默认**: bg `bg_surface0`, hover `bg_surface1`, disabled fg `fg_muted`
2. **Accent.TButton**: hover `surface_hover`, disabled bg `bg_surface0`
3. **新增样式**: Small.TButton, SmallAccent.TButton, PanelHeader.TLabel, CardLabel.TLabel, CardValue.TLabel, StatusBar.TFrame(bg_crust), Card.TFrame(bg_crust)
4. **Status.TLabel**: bg 改为 `bg_crust`
5. **TEntry**: fieldbackground `bg_surface0`, foreground `fg_primary`
6. **Phase 1 保留**: Sidebar.TFrame, Nav.TButton, NavActive.TButton, Header.TFrame, Toolbar.TFrame (key 更新为新名，Phase 2 删除)

## test_theme.py 更新

- `expected_keys` 从 16 个更新为 21 个
- `get_theme("light")` 断言 `accent` 从 `#1565c0` → `#1e66f5`
