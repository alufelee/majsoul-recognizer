# GUI 视觉重设计实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Tkinter GUI 的配色迁移到 Catppuccin 色板，侧边栏改为 Canvas 图标，视图改为 grid 布局，ResultPanel 重写为卡片式。

**Architecture:** 4 阶段原子提交。Phase 1 仅改颜色 key（无结构变更）。Phase 2 改布局/侧边栏/状态栏（5 文件同步）。Phase 3 重写核心组件。Phase 4 收尾。

**Tech Stack:** Python 3.14 + Tkinter (clam 主题) + ttk.Style + Catppuccin Mocha/Latte 色板

**子规格文档:** `docs/superpowers/specs/gui-redesign/01~11-*.md`

---

## Phase 1: 配色和样式迁移（原子提交）

> Task 1-3 同步提交，中间态测试不通过。

### Task 1: theme.py — Catppuccin 色板重写

**Files:**
- Modify: `src/majsoul_recognizer/gui/theme.py`
- Modify: `tests/gui/test_theme.py`
- Spec: `docs/superpowers/specs/gui-redesign/01-theme-dict.md`

- [ ] **Step 1: 重写 Theme.DARK 和 Theme.LIGHT dicts**

替换 `theme.py` 中 `Theme` 类的 `DARK` 和 `LIGHT` 为 21 个新 key（见 `01-theme-dict.md`）。

- [ ] **Step 2: 重写 apply_style()**

```python
def apply_style(style: Any, theme: dict[str, str]) -> None:
    if "clam" in style.theme_names():
        style.theme_use("clam")

    # 全局
    style.configure(".", background=theme["bg_base"],
                     foreground=theme["fg_primary"], borderwidth=0)
    style.configure("TFrame", background=theme["bg_base"])
    style.configure("TLabel", background=theme["bg_base"],
                     foreground=theme["fg_primary"])

    # 默认按钮 — surface0 背景
    style.configure("TButton", background=theme["bg_surface0"],
                     foreground=theme["fg_primary"], padding=(12, 4))
    style.map("TButton",
              background=[("active", theme["bg_surface1"]),
                          ("disabled", theme["bg_surface0"])],
              foreground=[("active", theme["fg_primary"]),
                          ("disabled", theme["fg_muted"])])

    # 侧边栏 (Phase 2 删除，Phase 1 保留旧样式名但用新 key)
    style.configure("Sidebar.TFrame", background=theme["bg_crust"])
    style.configure("Nav.TButton", background=theme["bg_crust"],
                     foreground=theme["fg_primary"], padding=(8, 6))
    style.map("Nav.TButton",
              background=[("active", theme["bg_surface0"])],
              foreground=[("active", theme["fg_primary"])])
    style.configure("NavActive.TButton", background=theme["accent_dim"],
                     foreground="#ffffff", padding=(8, 6))
    style.map("NavActive.TButton",
              background=[("active", theme["accent"])],
              foreground=[("active", "#ffffff")])

    # 标题栏 / 工具栏 (Phase 2 删除)
    style.configure("Header.TFrame", background=theme["bg_mantle"])
    style.configure("Toolbar.TFrame", background=theme["bg_base"],
                     borderwidth=1, relief="raised")

    # 强调按钮
    style.configure("Accent.TButton", background=theme["accent"],
                     foreground="#ffffff", padding=(12, 4))
    style.map("Accent.TButton",
              background=[("active", theme["surface_hover"]),
                          ("disabled", theme["bg_surface0"])],
              foreground=[("disabled", theme["fg_muted"])])

    # 状态栏小按钮
    style.configure("Small.TButton", background=theme["bg_surface0"],
                     foreground=theme["fg_primary"], padding=(8, 2))
    style.map("Small.TButton",
              background=[("active", theme["bg_surface1"])],
              foreground=[("active", theme["fg_primary"])])

    style.configure("SmallAccent.TButton", background=theme["accent"],
                     foreground="#ffffff", padding=(8, 2))
    style.map("SmallAccent.TButton",
              background=[("active", theme["surface_hover"])],
              foreground=[("active", "#ffffff")])

    # 面板标签
    style.configure("PanelHeader.TLabel", background=theme["bg_mantle"],
                     foreground=theme["fg_primary"], font=("", 11, "bold"))
    style.configure("CardLabel.TLabel", background=theme["bg_crust"],
                     foreground=theme["fg_secondary"], font=("", 9))
    style.configure("CardValue.TLabel", background=theme["bg_crust"],
                     foreground=theme["fg_primary"], font=("", 11))

    # 状态栏
    style.configure("StatusBar.TFrame", background=theme["bg_crust"])
    style.configure("Card.TFrame", background=theme["bg_crust"])
    style.configure("Status.TLabel", background=theme["bg_crust"],
                     foreground=theme["fg_secondary"])

    # 输入框
    style.configure("TEntry",
                    fieldbackground=theme["bg_surface0"],
                    foreground=theme["fg_primary"])
```

- [ ] **Step 3: 重写 test_theme.py**

```python
"""主题系统测试 — Catppuccin Mocha / Latte"""

from majsoul_recognizer.gui.theme import Theme, get_theme

NEW_KEYS = {
    "bg_base", "bg_mantle", "bg_surface0", "bg_surface1", "bg_crust",
    "fg_primary", "fg_secondary", "fg_muted",
    "accent", "accent_dim",
    "green", "peach", "red",
    "blue", "yellow", "mauve", "teal",
    "lavender", "sky", "flamingo",
    "surface_hover",
}


class TestThemeColors:
    def test_dark_has_all_keys(self):
        assert set(Theme.DARK.keys()) == NEW_KEYS

    def test_light_has_all_keys(self):
        assert set(Theme.LIGHT.keys()) == NEW_KEYS

    def test_dark_and_light_have_same_keys(self):
        assert set(Theme.DARK.keys()) == set(Theme.LIGHT.keys())

    def test_all_values_are_hex_colors(self):
        for name, colors in [("DARK", Theme.DARK), ("LIGHT", Theme.LIGHT)]:
            for key, value in colors.items():
                assert value.startswith("#"), f"{name}.{key} = {value!r}"
                assert len(value) == 7, f"{name}.{key} = {value!r}"


class TestGetTheme:
    def test_get_dark(self):
        result = get_theme("dark")
        assert result == Theme.DARK

    def test_get_light(self):
        result = get_theme("light")
        assert result == Theme.LIGHT

    def test_get_unknown_returns_dark(self):
        result = get_theme("unknown")
        assert result == Theme.DARK

    def test_returns_copy_not_reference(self):
        result = get_theme("dark")
        result["accent"] = "#CHANGED"
        assert Theme.DARK["accent"] == "#89b4fa"

    def test_light_returns_copy_not_reference(self):
        result = get_theme("light")
        result["accent"] = "#CHANGED"
        assert Theme.LIGHT["accent"] == "#1e66f5"
```

- [ ] **Step 4: 运行 theme 测试验证**

Run: `pytest tests/gui/test_theme.py -v`
Expected: PASS (6 tests)

---

### Task 2: colors.py — Catppuccin 检测框/区域颜色

**Files:**
- Modify: `src/majsoul_recognizer/gui/widgets/colors.py`
- No test change needed (`test_colors.py` only checks hex format, not values)
- Spec: `docs/superpowers/specs/gui-redesign/02-colors.md`

- [ ] **Step 1: 替换 _TILE_CATEGORY_COLORS**

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

- [ ] **Step 2: 替换 ZONE_COLORS**

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

- [ ] **Step 3: 运行 colors 测试验证**

Run: `pytest tests/gui/widgets/test_colors.py -v`
Expected: PASS (5 tests)

---

### Task 3: 全局 theme key 迁移

**Files:**
- Modify: `src/majsoul_recognizer/gui/widgets/image_canvas.py`
- Modify: `src/majsoul_recognizer/gui/widgets/result_panel.py`
- Modify: `src/majsoul_recognizer/gui/views/dev_view.py`
- Modify: `src/majsoul_recognizer/gui/app.py`
- Spec: `docs/superpowers/specs/gui-redesign/03-key-migration.md`

> **注意:** 仅修改 dict key 查找，不修改 import 语句。保留每个文件现有的所有 import 不变。

- [ ] **Step 1: image_canvas.py — search-replace**

全局替换:
- `theme["canvas_bg"]` → `theme["bg_crust"]` (所有出现)

- [ ] **Step 2: result_panel.py — search-replace**

全局替换:
- `theme["bg_secondary"]` → `theme["bg_mantle"]` (所有出现)
- `theme["highlight"]` → `theme["peach"]` (所有出现)
- `theme["warning"]` → `theme["peach"]` (所有出现)

- [ ] **Step 3: dev_view.py — search-replace**

全局替换:
- `theme["bg_secondary"]` → `theme["bg_mantle"]` (所有出现)

- [ ] **Step 4: app.py — search-replace**

全局替换:
- `theme["bg_primary"]` → `theme["bg_base"]` (所有出现)
- `theme["success"]` → `theme["green"]` (所有出现)
- `new_theme["border"]` → `new_theme["bg_surface0"]` (所有出现)
- `new_theme["bg_primary"]` → `new_theme["bg_base"]` (所有出现)
- `new_theme["success"]` → `new_theme["green"]` (所有出现)

- [ ] **Step 5: 运行全部 GUI 测试**

Run: `pytest tests/gui/ -v`
Expected: ALL PASS (约 51 tests)

- [ ] **Step 6: 提交 Phase 1**

```bash
git add src/majsoul_recognizer/gui/theme.py \
        src/majsoul_recognizer/gui/widgets/colors.py \
        src/majsoul_recognizer/gui/widgets/image_canvas.py \
        src/majsoul_recognizer/gui/widgets/result_panel.py \
        src/majsoul_recognizer/gui/views/dev_view.py \
        src/majsoul_recognizer/gui/app.py \
        tests/gui/test_theme.py
git commit -m "refactor(gui): migrate theme to Catppuccin Mocha/Latte color tokens"
```

---

## Phase 2: 框架 + 视图结构改造（原子提交）

> Task 4-8 同步提交。中间态 app.py 引用 BaseView 新方法，必须一起完成。

### Task 4: base_view.py — 状态栏 helper

**Files:**
- Modify: `src/majsoul_recognizer/gui/base_view.py`
- Modify: `tests/gui/test_base_view.py`
- Spec: `docs/superpowers/specs/gui-redesign/04-base-view-status.md`

- [ ] **Step 1: 新增 import**

在 `base_view.py` 顶部添加:
```python
import tkinter as tk
```

- [ ] **Step 2: 添加 _create_status_bar() 和 set_status_text() 方法**

```python
def _create_status_bar(self) -> tuple[ttk.Frame, tk.Canvas, ttk.Label, ttk.Label]:
    """创建统一风格的状态栏组件。

    Returns: (outer_frame, status_dot, status_label, status_info)
             outer_frame 用于视图 grid 放置 (row=1)。
             按钮应添加到 outer_frame 内的 bar 子容器中，
             通过 self._status_bar_frame 访问。
    """
    outer = ttk.Frame(self)

    sep = tk.Canvas(outer, height=1, bg=self._theme["bg_surface0"],
                    highlightthickness=0)
    sep.pack(side="top", fill="x")

    bar = ttk.Frame(outer, style="StatusBar.TFrame", height=32)
    bar.pack(side="top", fill="x")
    bar.pack_propagate(False)

    dot = tk.Canvas(bar, width=16, height=16,
                    bg=self._theme["bg_crust"], highlightthickness=0)
    dot.pack(side="left", padx=(8, 4), pady=8)
    dot.create_oval(3, 3, 13, 13, fill=self._theme["green"], outline="")

    status_label = ttk.Label(bar, text="就绪", style="Status.TLabel")
    status_label.pack(side="left")

    info_label = ttk.Label(bar, text="", style="Status.TLabel")
    info_label.pack(side="right", padx=8)

    self._status_label = status_label
    self._status_bar_frame = bar  # 按钮添加到此 frame
    return outer, dot, status_label, info_label

def set_status_text(self, text: str) -> None:
    """App 级状态消息委托"""
    if hasattr(self, '_status_label') and self._status_label is not None:
        self._status_label.config(text=text)
```

- [ ] **Step 3: 添加测试**

在 `test_base_view.py` 底部追加:
```python
class TestBaseViewStatusBar:
    def test_create_status_bar_returns_outer_frame(self, tk_root, mock_app_state):
        from majsoul_recognizer.gui.theme import Theme
        view = BaseView(tk_root, mock_app_state, Theme.DARK)
        outer, dot, label, info = view._create_status_bar()
        assert outer is not None
        assert dot is not None
        assert label is not None
        assert info is not None
        assert view._status_bar_frame is not None  # 按钮容器

    def test_set_status_text_updates_label(self, tk_root, mock_app_state):
        from majsoul_recognizer.gui.theme import Theme
        view = BaseView(tk_root, mock_app_state, Theme.DARK)
        view._create_status_bar()
        view.set_status_text("测试消息")
        assert view._status_label.cget("text") == "测试消息"

    def test_set_status_text_without_bar_is_safe(self, tk_root, mock_app_state):
        from majsoul_recognizer.gui.theme import Theme
        view = BaseView(tk_root, mock_app_state, Theme.DARK)
        view.set_status_text("安全")
```

- [ ] **Step 4: 运行 base_view 测试**

Run: `pytest tests/gui/test_base_view.py -v`
Expected: PASS

---

### Task 5: app.py — Canvas 侧边栏 + 状态委托

**Files:**
- Modify: `src/majsoul_recognizer/gui/app.py`
- Modify: `tests/gui/test_app.py`
- Spec: `docs/superpowers/specs/gui-redesign/05-app-sidebar.md`

- [ ] **Step 1: 添加 _SidebarIcon 类**

> **全局替换说明:** `_SidebarIcon` 替换旧的 `Nav.TButton` / `NavActive.TButton` 方案。
> 需删除以下旧变量/引用:
> - `self._nav_buttons: dict[str, ttk.Button]` → 删除，替换为 `self._nav_icons: dict[str, _SidebarIcon]`
> - `_build_ui` 中旧按钮循环 → 删除，替换为 Canvas 图标创建循环
> - `_switch_view` 中 `btn.configure(style=...)` → 删除，替换为 `icon.set_active(...)`
> - `_toggle_theme` 中按钮主题更新 → 删除，替换为 `icon.on_theme_changed(...)`
> - 所有 `self._nav_buttons[...]` 引用 → 替换为 `self._nav_icons[...]`

在 `app.py` 中 `App` 类之前添加:
```python
import math


class _SidebarIcon(tk.Canvas):
    """侧边栏图标按钮"""

    def __init__(self, parent, theme: dict, icon_type: str,
                 command, **kwargs):
        super().__init__(parent, width=36, height=36,
                         bg=theme["bg_crust"],
                         highlightthickness=0, **kwargs)
        self._theme = theme
        self._command = command
        self._active = False
        self._icon_type = icon_type

        self._draw_icon(theme["fg_secondary"])
        self.bind("<Button-1>", lambda e: self._command())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.delete("active_bar")
        if active:
            self.create_rectangle(0, 0, 2, 36, fill=self._theme["accent"],
                                  outline="", tags="active_bar")
            self.configure(bg=self._theme["accent_dim"])
            self._redraw(self._theme["fg_primary"])
        else:
            self.configure(bg=self._theme["bg_crust"])
            self._redraw(self._theme["fg_secondary"])

    def on_theme_changed(self, theme: dict) -> None:
        self._theme = theme
        color = theme["fg_primary"] if self._active else theme["fg_secondary"]
        bg = theme["accent_dim"] if self._active else theme["bg_crust"]
        self.configure(bg=bg)
        self._redraw(color)
        if self._active:
            self.delete("active_bar")
            self.create_rectangle(0, 0, 2, 36, fill=theme["accent"],
                                  outline="", tags="active_bar")

    def _on_enter(self, event):
        if not self._active:
            self.configure(bg=self._theme["bg_surface0"])

    def _on_leave(self, event):
        if not self._active:
            self.configure(bg=self._theme["bg_crust"])

    def _redraw(self, color: str) -> None:
        self.delete("icon")
        self._draw_icon(color)

    def _draw_icon(self, color: str) -> None:
        if self._icon_type == "screenshot":
            self.create_rectangle(10, 11, 26, 25, outline=color,
                                  width=1.5, tags="icon")
            self.create_line(10, 11, 10, 15, 14, 15, 14, 11,
                             fill=color, width=1.5, tags="icon")
        elif self._icon_type == "live":
            self.create_oval(15, 15, 21, 21, outline=color,
                             width=1.5, tags="icon")
            self.create_arc(12, 12, 24, 24, start=30, extent=60,
                            outline=color, style="arc", width=1.5, tags="icon")
            self.create_arc(9, 9, 27, 27, start=30, extent=60,
                            outline=color, style="arc", width=1.5, tags="icon")
        elif self._icon_type == "dev":
            self.create_oval(10, 10, 26, 26, outline=color,
                             width=1.5, tags="icon")
            self.create_oval(15, 15, 21, 21, outline=color,
                             width=1.5, tags="icon")
            for i in range(6):
                angle = math.radians(i * 60)
                x1 = 18 + 8 * math.cos(angle)
                y1 = 18 + 8 * math.sin(angle)
                x2 = 18 + 10 * math.cos(angle)
                y2 = 18 + 10 * math.sin(angle)
                self.create_line(x1, y1, x2, y2, fill=color,
                                 width=1.5, tags="icon")
```

- [ ] **Step 2: 修改 App 类常量**

```python
SIDEBAR_WIDTH = 48

NAV_ITEMS = ["screenshot", "live", "dev"]
```

- [ ] **Step 3: 重写 _build_ui()**

```python
def _build_ui(self, theme: dict) -> None:
    # 标题栏 (不使用 Header.TFrame，Phase 4 会删除该样式)
    header_frame = tk.Frame(self._root, bg=theme["bg_mantle"])
    header_frame.pack(side="top", fill="x")

    header = tk.Frame(header_frame, bg=theme["bg_mantle"])
    header.pack(side="top", fill="x")
    tk.Label(header, text="雀魂麻将识别助手 v0.1", bg=theme["bg_mantle"],
             fg=theme["fg_primary"],
             font=("", 12, "bold")).pack(side="left", padx=12, pady=6)
    ttk.Button(header, text="主题",
               command=self._toggle_theme).pack(side="right", padx=4, pady=4)
    ttk.Button(header, text="设置",
               command=self._show_settings).pack(side="right", padx=4, pady=4)

    border_canvas = tk.Canvas(header_frame, height=2, bg=theme["accent"],
                              highlightthickness=0)
    border_canvas.pack(side="bottom", fill="x")
    self._header_border = border_canvas

    body = ttk.Frame(self._root)
    body.pack(side="top", fill="both", expand=True)

    # Canvas 图标侧边栏
    sidebar = tk.Canvas(body, width=self.SIDEBAR_WIDTH, bg=theme["bg_crust"],
                        highlightthickness=0)
    sidebar.pack(side="left", fill="y", expand=True)

    self._nav_icons: dict[str, _SidebarIcon] = {}
    y_offset = 12
    for view_name in self.NAV_ITEMS:
        icon = _SidebarIcon(sidebar, theme, view_name,
                            command=lambda n=view_name: self._switch_view(n))
        sidebar.create_window(24, y_offset + 18, window=icon)
        y_offset += 40
        self._nav_icons[view_name] = icon

    # 内容区
    self._content = ttk.Frame(body)
    self._content.pack(side="left", fill="both", expand=True)
    self._content.grid_rowconfigure(0, weight=1)
    self._content.grid_columnconfigure(0, weight=1)
```

- [ ] **Step 4: 修改 __init__ — 状态委托 + _init_error**

在 `__init__` 中，engine 初始化改为:
```python
self._init_error: str | None = None
try:
    engine = RecognitionEngine(config)
except Exception as e:
    logger.warning("Engine init failed (degraded mode): %s", e)
    engine = None
    self._init_error = "检测器降级模式"
```

移除 `self._status_label.config(text="检测器降级模式")`。

- [ ] **Step 5: 修改 _switch_view — 首次激活时显示 init error**

在 `_switch_view` 末尾追加:
```python
if self._init_error:
    self._active_view.set_status_text(self._init_error)
    self._init_error = None
```

导航按钮激活改为 icon:
```python
for name, icon in self._nav_icons.items():
    icon.set_active(name == view_name)
```

- [ ] **Step 6: 修改 _toggle_theme — 更新侧边栏图标**

```python
def _toggle_theme(self) -> None:
    new_name = "light" if self._app_state.theme_name == "dark" else "dark"
    new_theme = get_theme(new_name)
    self._app_state.theme_name = new_name
    self._settings.theme = new_name

    style = ttk.Style()
    apply_style(style, new_theme)

    self._header_border.configure(bg=new_theme["accent"])

    for icon in self._nav_icons.values():
        icon.on_theme_changed(new_theme)

    for view in self._views.values():
        view.on_theme_changed(new_theme)
    self._settings.save()
```

- [ ] **Step 7: 修改 _rebuild_engine — 状态委托**

```python
except Exception as e:
    logger.error("Engine rebuild failed: %s", e)
    self._app_state.engine = None
    if self._active_view is not None:
        self._active_view.set_status_text(f"引擎重建失败: {e}")
```

- [ ] **Step 8: 更新 test_app.py**

test_engine_failure_degraded_mode 不再检查 `_status_label`:
```python
def test_engine_failure_degraded_mode(self):
    with patch("majsoul_recognizer.gui.app.GUISettings") as MockSettings:
        MockSettings.load.return_value = _make_mock_settings()
        with patch("majsoul_recognizer.gui.app.RecognitionEngine", side_effect=RuntimeError("no model")):
            app = App()
            assert app._app_state.engine is None
            assert app._init_error is not None
            app._root.destroy()
```

- [ ] **Step 9: 运行 app 测试**

Run: `pytest tests/gui/test_app.py -v`
Expected: PASS

---

### Task 6: screenshot_view.py — grid + 状态栏

**Files:**
- Modify: `src/majsoul_recognizer/gui/views/screenshot_view.py`
- Modify: `tests/gui/test_screenshot_view.py` (如需)
- Spec: `docs/superpowers/specs/gui-redesign/06-screenshot-view.md`

- [ ] **Step 1: 重写 __init__ 布局**

```python
def __init__(self, parent, app_state, theme, on_result=None, **kwargs):
    super().__init__(parent, app_state, theme, **kwargs)
    self._current_image: np.ndarray | None = None
    self._current_frame: FrameResult | None = None
    self._current_state: GameState | None = None
    self._on_result = on_result
    self._is_busy = False

    # grid 布局: row 0 主内容, row 1 状态栏
    self.grid_rowconfigure(0, weight=1)
    self.grid_rowconfigure(1, weight=0)
    self.grid_columnconfigure(0, weight=1)
    self.grid_columnconfigure(1, minsize=240)

    self._canvas = ImageCanvas(self, theme)
    self._canvas.grid(row=0, column=0, sticky="nsew")

    self._result_panel = ResultPanel(self, theme)
    self._result_panel.grid(row=0, column=1, sticky="ns")

    # 状态栏
    outer, dot, self._status_label, self._status_info = self._create_status_bar()
    outer.grid(row=1, column=0, columnspan=2, sticky="ew")

    self._open_button = ttk.Button(self._status_bar_frame, text="打开文件", style="SmallAccent.TButton",
                                    command=self._on_open_file)
    self._open_button.pack(side="left", padx=4, pady=4)

    self._recognize_button = ttk.Button(self._status_bar_frame, text="识别", style="Small.TButton",
                                         command=self._on_recognize)
    self._recognize_button.pack(side="left", padx=4, pady=4)

    if _HAS_DND:
        self._canvas.drop_target_register(DND_FILES)
        self._canvas.dnd_bind("<<Drop>>", self._on_drop)
```

- [ ] **Step 2: 验证测试**

Run: `pytest tests/gui/test_screenshot_view.py -v`
Expected: PASS (test_recognize_with_no_engine 仍通过，_status_label 来自 helper)

---

### Task 7: live_view.py — grid + 状态栏

**Files:**
- Modify: `src/majsoul_recognizer/gui/views/live_view.py`
- Modify: `tests/gui/test_live_view.py` (如需)
- Spec: `docs/superpowers/specs/gui-redesign/07-live-view.md`

- [ ] **Step 1: 重写 __init__ 布局**

```python
def __init__(self, parent, app_state, theme, on_result=None, **kwargs):
    super().__init__(parent, app_state, theme, **kwargs)
    self._capture_thread: threading.Thread | None = None
    self._capture_stop = threading.Event()
    self._status_queue: queue.Queue = queue.Queue()
    self._fps_counter = FPSCounter()
    self._current_state: GameState | None = None
    self._on_result = on_result
    self._state: str = "idle"

    self.grid_rowconfigure(0, weight=1)
    self.grid_rowconfigure(1, weight=0)
    self.grid_columnconfigure(0, weight=1)
    self.grid_columnconfigure(1, minsize=240)

    self._canvas = ImageCanvas(self, theme)
    self._canvas.grid(row=0, column=0, sticky="nsew")

    self._result_panel = ResultPanel(self, theme)
    self._result_panel.grid(row=0, column=1, sticky="ns")

    # 状态栏
    outer, dot, self._status_label, self._status_info = self._create_status_bar()
    outer.grid(row=1, column=0, columnspan=2, sticky="ew")

    self._start_button = ttk.Button(self._status_bar_frame, text="开始", style="SmallAccent.TButton",
                                     command=self._on_start)
    self._start_button.pack(side="left", padx=4, pady=4)

    self._pause_button = ttk.Button(self._status_bar_frame, text="暂停", style="Small.TButton",
                                     command=self._on_pause)
    self._pause_button.pack(side="left", padx=4, pady=4)

    self._reset_button = ttk.Button(self._status_bar_frame, text="重置", style="Small.TButton",
                                     command=self._on_reset)
    self._reset_button.pack(side="left", padx=4, pady=4)

    self._update_buttons("idle")
```

- [ ] **Step 2: 删除 _fps_label 相关代码**

> live_view.py 中需完全删除:
> - `self._fps_label = ttk.Label(...)` 初始化行
> - `self._fps_label.pack(...)` 布局行
> - `self._fps_label.config(text=...)` 更新行
> - 所有 `self._fps_label` 引用 → 替换为 `self._status_info`

更新 _on_reset:

```python
def _on_reset(self) -> None:
    ...
    self._status_info.config(text="")
    ...
```

- [ ] **Step 3: 更新 _poll_result — FPS 显示**

```python
# 在 _poll_result 末尾:
fps = self._fps_counter.fps
self._status_info.config(text=f"FPS: {fps:.1f}")
```

- [ ] **Step 4: 验证测试**

Run: `pytest tests/gui/test_live_view.py -v`
Expected: PASS

---

### Task 8: dev_view.py — 3 列 grid + 状态栏

**Files:**
- Modify: `src/majsoul_recognizer/gui/views/dev_view.py`
- Modify: `tests/gui/test_dev_view.py`
- Spec: `docs/superpowers/specs/gui-redesign/08-dev-view.md`

- [ ] **Step 1: 重写 __init__ 布局**

```python
def __init__(self, parent, app_state, theme, **kwargs):
    super().__init__(parent, app_state, theme, **kwargs)
    self._current_image: np.ndarray | None = None

    # 3 列 grid
    self.grid_rowconfigure(0, weight=1)
    self.grid_rowconfigure(1, weight=0)
    self.grid_columnconfigure(0, weight=1)
    self.grid_columnconfigure(1, weight=1)
    self.grid_columnconfigure(2, minsize=280)

    self._zone_canvas = ImageCanvas(self, theme)
    self._zone_canvas.grid(row=0, column=0, sticky="nsew")

    self._det_canvas = ImageCanvas(self, theme)
    self._det_canvas.grid(row=0, column=1, sticky="nsew")

    # JSON 面板
    json_panel = ttk.Frame(self)
    json_panel.grid(row=0, column=2, sticky="ns")

    ttk.Label(json_panel, text="JSON 输出", style="PanelHeader.TLabel").pack(
        anchor="w", padx=8, pady=(8, 4))

    mono = "Menlo" if sys.platform == "darwin" else "Consolas"
    self._json_text = tk.Text(json_panel, wrap="none", state="disabled",
                              font=(mono, 10), bg=theme["bg_crust"],
                              fg=theme["fg_primary"], height=8)
    json_scroll = ttk.Scrollbar(json_panel, orient="vertical",
                                command=self._json_text.yview)
    self._json_text.configure(yscrollcommand=json_scroll.set)
    self._json_text.pack(side="left", fill="both", expand=True, padx=(8, 0))
    json_scroll.pack(side="right", fill="y")

    ttk.Button(json_panel, text="复制 JSON", style="Small.TButton",
               command=self._copy_json).pack(pady=4)

    # 状态栏
    outer, dot, self._status_label, self._status_info = self._create_status_bar()
    outer.grid(row=1, column=0, columnspan=3, sticky="ew")
```

- [ ] **Step 2: 删除 _perf_label 相关代码**

> dev_view.py 中需完全删除:
> - `self._perf_label = ttk.Label(...)` 初始化行
> - `self._perf_label.pack(...)` 布局行
> - `self._perf_label.config(text=...)` 更新行
> - 所有 `self._perf_label` 引用 → 替换为 `self._status_info`

更新 update_data:

```python
self._status_info.config(
    text=f"帧: {frame.frame_id} | {'静态' if frame.is_static else '动画'}"
)
```

- [ ] **Step 3: 更新 test_dev_view.py**

`_perf_label` → `_status_info` (所有引用):
```python
def test_update_data_shows_perf(self, view):
    view.set_current_image(np.zeros((200, 200, 3), dtype=np.uint8))
    frame = _make_frame_result()
    view.update_data(frame, None)
    info_text = view._status_info.cget("text")
    assert "帧: 1" in info_text
```

- [ ] **Step 4: 验证测试**

Run: `pytest tests/gui/test_dev_view.py -v`
Expected: PASS

- [ ] **Step 5: 提交 Phase 2**

```bash
git add src/majsoul_recognizer/gui/base_view.py \
        src/majsoul_recognizer/gui/app.py \
        src/majsoul_recognizer/gui/views/screenshot_view.py \
        src/majsoul_recognizer/gui/views/live_view.py \
        src/majsoul_recognizer/gui/views/dev_view.py \
        tests/gui/test_base_view.py \
        tests/gui/test_app.py \
        tests/gui/test_dev_view.py
git commit -m "refactor(gui): canvas sidebar, grid layout, view-internal status bars"
```

---

## Phase 3: 核心组件重写

### Task 9: result_panel.py — 卡片式重写

**Files:**
- Rewrite: `src/majsoul_recognizer/gui/widgets/result_panel.py`
- Rewrite: `tests/gui/widgets/test_result_panel.py`
- Spec: `docs/superpowers/specs/gui-redesign/09-result-panel.md`

- [ ] **Step 1: 重写 test_result_panel.py**

```python
"""ResultPanel 卡片式测试"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk

from majsoul_recognizer.gui.theme import Theme
from majsoul_recognizer.gui.widgets.result_panel import ResultPanel
from majsoul_recognizer.types import GameState, RoundInfo, CallGroup


@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    yield root
    root.destroy()


@pytest.fixture
def panel(tk_root):
    p = ResultPanel(tk_root, Theme.DARK)
    p.pack(fill="both", expand=True)
    tk_root.update_idletasks()
    return p


def _make_state(**overrides) -> GameState:
    defaults = {
        "round_info": RoundInfo(wind="东", number=1, honba=0, kyotaku=0),
        "dora_indicators": ["3s"],
        "hand": ["1m", "2m", "3m", "4p"],
        "drawn_tile": "5p",
        "scores": {"self": 25000, "right": 25000, "opposite": 25000, "left": 25000},
        "discards": {"self": ["6m", "7m"], "right": ["1p"]},
        "calls": {},
        "actions": [],
        "warnings": [],
    }
    defaults.update(overrides)
    return GameState(**defaults)


class TestResultPanelCards:
    def test_creates_9_cards(self, panel):
        assert len(panel._cards) == 9

    def test_none_shows_dash(self, panel):
        panel.update_state(None)
        for card in panel._cards:
            assert card._value.cget("text") == "-"

    def test_shows_round_info(self, panel):
        panel.update_state(_make_state())
        assert "东1局" in panel._cards[0]._value.cget("text")

    def test_shows_hand(self, panel):
        panel.update_state(_make_state())
        val = panel._cards[2]._value.cget("text")
        assert "1m" in val and "4p" in val

    def test_shows_scores(self, panel):
        panel.update_state(_make_state())
        assert "25000" in panel._cards[5]._value.cget("text")

    def test_shows_discards(self, panel):
        panel.update_state(_make_state())
        assert "6m" in panel._cards[6]._value.cget("text")

    def test_empty_hand_dash(self, panel):
        state = _make_state(hand=[], drawn_tile=None, dora_indicators=[],
                            discards={}, scores={})
        panel.update_state(state)
        assert panel._cards[2]._value.cget("text") == "-"
        assert panel._cards[1]._value.cget("text") == "-"

    def test_with_calls(self, panel):
        state = _make_state(
            calls={"self": [CallGroup(type="pon", tiles=["1m", "1m", "1m"],
                                       from_player="right")]}
        )
        panel.update_state(state)
        assert "1m" in panel._cards[4]._value.cget("text")

    def test_with_warnings(self, panel):
        panel.update_state(_make_state(warnings=["low_confidence"]))
        val = panel._cards[8]._value.cget("text")
        assert "1" in val

    def test_on_theme_changed(self, panel):
        panel.on_theme_changed(Theme.LIGHT)
        assert panel._theme is Theme.LIGHT

    def test_rapid_update_no_widget_leak(self, panel):
        state = _make_state()
        before = len(panel.winfo_children())
        for _ in range(10):
            panel.update_state(state)
        after = len(panel.winfo_children())
        assert before == after
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/gui/widgets/test_result_panel.py -v`
Expected: FAIL (ResultPanel still uses tk.Text)

- [ ] **Step 3: 重写 result_panel.py**

完整重写为卡片式。`_SectionCard` 内部类 + `ResultPanel` 主类。

```python
"""卡片式识别结果面板"""

import tkinter as tk
from tkinter import ttk

from majsoul_recognizer.types import GameState


class _SectionCard(ttk.Frame):
    """单张卡片: 左侧彩色边框 + 标签行 + 值行"""

    _COLOR_TOKENS = {
        "blue": "blue", "green": "green", "yellow": "yellow",
        "mauve": "mauve", "teal": "teal", "peach": "peach", "red": "red",
    }

    def __init__(self, parent, theme: dict[str, str], label: str,
                 color_token: str, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._theme = theme
        self._color_key = color_token

        border = tk.Canvas(self, width=2, highlightthickness=0,
                           bg=theme[color_token])
        border.pack(side="left", fill="y")
        self._border = border

        inner = ttk.Frame(self, style="Card.TFrame")
        inner.pack(side="left", fill="both", expand=True, padx=(8, 6), pady=6)

        self._label = ttk.Label(inner, text=label, style="CardLabel.TLabel")
        self._label.pack(anchor="w")

        self._value = ttk.Label(inner, text="-", style="CardValue.TLabel",
                                wraplength=180)
        self._value.pack(anchor="w", pady=(2, 0))

    def update_value(self, text: str) -> None:
        self._value.config(text=text)

    def on_theme_changed(self, theme: dict[str, str]) -> None:
        self._theme = theme
        self._border.configure(bg=theme[self._color_key])


class ResultPanel(ttk.Frame):
    """卡片式识别结果面板"""

    # (标签, 颜色 token)
    _CARD_DEFS: list[tuple[str, str]] = [
        ("局次", "blue"),
        ("宝牌", "blue"),
        ("手牌", "green"),
        ("摸牌", "green"),
        ("副露", "yellow"),
        ("分数", "mauve"),
        ("牌河", "teal"),
        ("动作", "peach"),
        ("警告", "red"),
    ]

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, **kwargs)
        self._theme = theme
        self.configure(width=240)
        self.pack_propagate(False)

        # 容器背景
        inner = ttk.Frame(self, style="StatusBar.TFrame")
        inner.pack(fill="both", expand=True)

        # 标题行
        header = ttk.Frame(inner, style="StatusBar.TFrame")
        header.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(header, text="识别结果", style="PanelHeader.TLabel").pack(
            side="left")

        # 左侧 1px 分割线颜色通过 StatusBar.TFrame bg 隐含

        # 卡片列表
        self._cards: list[_SectionCard] = []
        for label, color in self._CARD_DEFS:
            card = _SectionCard(inner, theme, label, color)
            card.pack(fill="x", padx=6, pady=3)
            self._cards.append(card)

    def update_state(self, state: GameState | None,
                     latency_ms: float = 0) -> None:
        if state is None:
            for card in self._cards:
                card.update_value("-")
            return

        # 0: 局次
        ri = state.round_info
        if ri:
            self._cards[0].update_value(
                f"{ri.wind}{ri.number}局 {ri.honba}本场 {ri.kyotaku}供托")
        else:
            self._cards[0].update_value("-")

        # 1: 宝牌
        if state.dora_indicators:
            self._cards[1].update_value(" ".join(state.dora_indicators))
        else:
            self._cards[1].update_value("-")

        # 2: 手牌
        if state.hand:
            self._cards[2].update_value(" ".join(state.hand))
        else:
            self._cards[2].update_value("-")

        # 3: 摸牌
        self._cards[3].update_value(state.drawn_tile or "-")

        # 4: 副露
        if state.calls:
            parts = []
            for player, groups in state.calls.items():
                for g in groups:
                    parts.append(" ".join(g.tiles))
            self._cards[4].update_value(" ".join(parts) if parts else "-")
        else:
            self._cards[4].update_value("-")

        # 5: 分数
        if state.scores:
            self._cards[5].update_value(
                " ".join(f"{v}" for v in state.scores.values()))
        else:
            self._cards[5].update_value("-")

        # 6: 牌河
        if state.discards:
            parts = []
            for player, tiles in state.discards.items():
                parts.append(" ".join(tiles) if tiles else "-")
            self._cards[6].update_value(" | ".join(parts) if parts else "-")
        else:
            self._cards[6].update_value("-")

        # 7: 动作
        if state.actions:
            self._cards[7].update_value(str(len(state.actions)))
        else:
            self._cards[7].update_value("-")

        # 8: 警告
        if state.warnings:
            self._cards[8].update_value(
                f"{len(state.warnings)}: " + ", ".join(state.warnings))
        else:
            self._cards[8].update_value("-")

    def on_theme_changed(self, theme: dict[str, str]) -> None:
        self._theme = theme
        for card in self._cards:
            card.on_theme_changed(theme)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/gui/widgets/test_result_panel.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add src/majsoul_recognizer/gui/widgets/result_panel.py \
        tests/gui/widgets/test_result_panel.py
git commit -m "refactor(gui): rewrite ResultPanel as card-based Frame"
```

---

### Task 10: image_canvas.py — 空状态提示

**Files:**
- Modify: `src/majsoul_recognizer/gui/widgets/image_canvas.py`
- Modify: `tests/gui/widgets/test_image_canvas.py`
- Spec: `docs/superpowers/specs/gui-redesign/10-image-canvas-empty.md`

- [ ] **Step 1: 添加测试**

在 `test_image_canvas.py` 底部追加:
```python
class TestImageCanvasEmptyState:
    def test_show_empty_state_draws_items(self, canvas):
        canvas.show_empty_state("测试提示")
        items = canvas.find_all()
        assert len(items) >= 2

    def test_show_image_clears_empty_state(self, canvas):
        canvas.show_empty_state("提示")
        canvas.winfo_height = lambda: 300
        canvas.winfo_width = lambda: 400
        canvas.winfo_reqheight = lambda: 300
        canvas.winfo_reqwidth = lambda: 400
        canvas.show_image(np.full((200, 200, 3), 128, dtype=np.uint8))
        assert canvas._photo is not None

    def test_clear_removes_empty_state(self, canvas):
        canvas.show_empty_state("提示")
        canvas.clear()
        assert canvas._photo is None
```

- [ ] **Step 2: 添加 show_empty_state 方法**

在 `ImageCanvas` 类中添加:
```python
def show_empty_state(self, hint_text: str) -> None:
    """显示空状态居中提示"""
    self.delete("all")
    self._photo = None
    cw = max(self.winfo_width(), self.winfo_reqwidth(), 200)
    ch = max(self.winfo_height(), self.winfo_reqheight(), 150)
    rw, rh = 48, 36
    rx, ry = (cw - rw) // 2, (ch - rh) // 2 - 12
    self.create_rectangle(rx, ry, rx + rw, ry + rh,
                          outline=self._theme["bg_surface0"], width=2)
    self.create_text(cw // 2, ry + rh + 16, text=hint_text,
                     fill=self._theme["fg_muted"], font=("", 11))
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/gui/widgets/test_image_canvas.py -v`
Expected: ALL PASS

- [ ] **Step 4: 在各视图中调用空状态**

在 screenshot_view.py `__init__` 末尾添加:
```python
self._canvas.show_empty_state("拖放或点击加载截图")
```

在 live_view.py `__init__` 末尾添加:
```python
self._canvas.show_empty_state("点击「开始」捕获窗口")
```

在 dev_view.py `__init__` 末尾添加:
```python
self._zone_canvas.show_empty_state("在其他视图识别后切换查看")
self._det_canvas.show_empty_state("在其他视图识别后切换查看")
```

- [ ] **Step 5: 提交**

```bash
git add src/majsoul_recognizer/gui/widgets/image_canvas.py \
        src/majsoul_recognizer/gui/views/screenshot_view.py \
        src/majsoul_recognizer/gui/views/live_view.py \
        src/majsoul_recognizer/gui/views/dev_view.py \
        tests/gui/widgets/test_image_canvas.py
git commit -m "feat(gui): add ImageCanvas empty state with hint text"
```

---

## Phase 4: 收尾

### Task 11: settings_dialog.py + apply_style 清理

**Files:**
- Modify: `src/majsoul_recognizer/gui/settings_dialog.py`
- Modify: `src/majsoul_recognizer/gui/theme.py` (移除旧样式)
- Spec: `docs/superpowers/specs/gui-redesign/11-settings-dialog.md`

- [ ] **Step 1: settings_dialog.py — "应用" 按钮样式**

```python
ttk.Button(btn_frame, text="应用", style="Accent.TButton",
           command=self._on_apply_clicked).pack(side="left", padx=4)
```

- [ ] **Step 2: theme.py — 移除旧样式**

从 `apply_style()` 中删除: `Sidebar.TFrame`, `Nav.TButton`, `NavActive.TButton`, `Header.TFrame`, `Toolbar.TFrame`

- [ ] **Step 3: 运行全部 GUI 测试**

Run: `pytest tests/gui/ -v`
Expected: ALL PASS

- [ ] **Step 4: 提交**

```bash
git add src/majsoul_recognizer/gui/settings_dialog.py \
        src/majsoul_recognizer/gui/theme.py
git commit -m "refactor(gui): update settings dialog, remove legacy styles"
```

---

## 最终验证

- [ ] **Step 1: 运行完整测试套件**

Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: 手动测试清单**（见 `phase4-settings.md` 第 3 节）
