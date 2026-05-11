# Phase 2: 框架 + 视图结构改造

> 母规格: `2026-05-11-gui-visual-redesign.md` (v3)
> 阶段: Phase 2 — 原子提交（不可拆分，中间态会崩溃）
> 前置: Phase 1 完成

## 涉及文件

| 文件 | 改动类型 |
|------|---------|
| `base_view.py` | 新增 `_create_status_bar()` + `set_status_text()` |
| `app.py` | 侧边栏→Canvas 图标、移除 App 状态栏、标题栏按钮改文字、状态委托 |
| `views/screenshot_view.py` | pack→grid、`_create_status_bar()`、移除旧 toolbar |
| `views/live_view.py` | pack→grid、`_create_status_bar()`、移除旧 toolbar |
| `views/dev_view.py` | pack→grid 3列、`_create_status_bar()` |
| `tests/gui/test_base_view.py` | 新增 status_bar 和 set_status_text 测试 |
| `tests/gui/test_app.py` | 更新侧边栏宽度、移除 status 断言 |
| `tests/gui/test_screenshot_view.py` | 更新 toolbar→status_bar 断言 |
| `tests/gui/test_live_view.py` | 更新 toolbar→status_bar 断言 |
| `tests/gui/test_dev_view.py` | 更新布局断言 |

## 不变的文件

`worker.py`, `app_state.py`, `settings.py`, `fps_counter.py`, `settings_dialog.py`, `result_panel.py` (Phase 3), `image_canvas.py` (Phase 3)

## 1. 整体布局

```
┌──────────────────────────────────────────────────────┐
│ 标题栏 (36px): 雀魂麻将识别助手           主题  设置 │
├──┬───────────────────────────────────────────────────┤
│  │ ┌─────────────────────────┬─────────────────────┐ │
│图│ │                         │ 识别结果         ◀ │ │
│标│ │       ImageCanvas       │  (Phase 3 重写)    │ │
│侧│ │                         │                    │ │
│栏│ │                         │                    │ │
│48│ ├─────────────────────────┴─────────────────────┤ │
│px│ │ [操作按钮] ● 状态文字             FPS | 延迟  │ │
│  │ └───────────────────────────────────────────────┘ │
├──┴───────────────────────────────────────────────────┤
└──────────────────────────────────────────────────────┘
              ↑ 状态栏在视图内部，非 App 层
```

## 2. BaseView — `_create_status_bar()` helper

```python
def _create_status_bar(self) -> tuple[ttk.Frame, tk.Canvas, ttk.Label, ttk.Label]:
    """创建统一风格的状态栏组件。

    调用方需将返回值放置在 grid(row=1, sticky="ew") 中，
    并在 status_frame 左侧添加操作按钮。

    Returns: (status_frame, status_dot, status_label, status_info)
    """
```

**实现要点:**
- 1px 顶部分割线 (Canvas, height=1, bg=`bg_surface0`)
- 32px 高 Frame (bg=`bg_crust`)
- 左侧: 操作按钮区 + 16x16 Canvas 圆点 (fill=`green`) + 状态文字 Label
- 右侧: 信息 Label (FPS/延迟/帧)
- `self._status_label` 赋值（供 `set_status_text()` 使用）

**`set_status_text()` 委托方法:**

```python
def set_status_text(self, text: str) -> None:
    """App 级状态消息委托"""
    if hasattr(self, '_status_label') and self._status_label is not None:
        self._status_label.config(text=text)
```

## 3. App 变更

### 3.1 侧边栏 → Canvas 图标

**常量变更:**
- `SIDEBAR_WIDTH = 140` → `SIDEBAR_WIDTH = 48`
- `NAV_ITEMS` 从 emoji+文字改为内部数据结构

**`_SidebarIcon` 类** (在 app.py 内定义):

```python
class _SidebarIcon(tk.Canvas):
    """侧边栏图标按钮 — Canvas 绘制"""

    ICON_TYPES = ("screenshot", "live", "dev")

    def __init__(self, parent, theme: dict, icon_type: str,
                 command: Callable, **kwargs):
        super().__init__(parent, width=36, height=36,
                         bg=theme["bg_crust"],
                         highlightthickness=0, **kwargs)
        ...
    def set_active(self, active: bool) -> None: ...
    def _draw_icon(self, color: str) -> None: ...
    def _draw_screenshot(self, color: str) -> None: ...
    def _draw_live(self, color: str) -> None: ...
    def _draw_dev(self, color: str) -> None: ...
    def on_theme_changed(self, theme: dict) -> None: ...
```

**图标绘制坐标 (36x36 Canvas, 20x20 图标区偏移 (8,8)):**

截图: 外矩形 (10,11)→(26,25) + 左上折线 (10,11)→(10,15)→(14,15)→(14,11)
实时: 中心圆 r=3 (18,18) + 三段弧线 r=6/9
调试: 外圆 r=8 (18,18) + 内圆 r=3 + 6条辐射线(等间隔60°, 延伸2px)

**交互:**
- `<Button-1>` → command
- `<Enter>` → 未选中时 bg=`bg_surface0`
- `<Leave>` → 未选中时 bg=`bg_crust`
- 选中态: bg=`accent_dim` + 左侧 2px `accent` 色条

### 3.2 _build_ui 变更

**移除:**
- App 级 status_outer, status_border, status_bar, status_dot, status_label, status_info
- `_status_dot`, `_status_label`, `_status_info`, `_status_border` 实例变量

**保留:**
- header_frame (标题栏)
- _header_border (accent 分割线)
- sidebar → 改为 Canvas 图标容器
- content → 不变

**标题栏:**
- 按钮文字: "切换主题"→"主题", "设置"→"设置"（更短）
- 按钮样式: `TButton` 默认样式（Phase 1 已更新为 surface0 背景）

### 3.3 状态消息委托

`_rebuild_engine()` 和 engine 初始化失败时:
```python
# 原来: self._status_label.config(text="...")
# 现在: self._active_view.set_status_text("...")
```

**engine 初始化时序问题:** views 在 engine 之后创建，init 时 `_active_view` 为 None。解决方案: 存储错误消息，`_switch_view` 首次调用时设置。

```python
# __init__ 中
self._init_error: str | None = None
try:
    engine = RecognitionEngine(config)
except Exception as e:
    engine = None
    self._init_error = "检测器降级模式"

# _switch_view 末尾
if self._init_error and view_name == self._active_view_name:
    self._active_view.set_status_text(self._init_error)
    self._init_error = None
```

### 3.4 _toggle_theme 变更

**移除:**
- status_dot/status_border 颜色更新

**新增:**
- sidebar Canvas 图标主题更新 (`icon.on_theme_changed(new_theme)`)

### 3.5 apply_style 清理

**移除旧样式:**
- `Sidebar.TFrame`, `Nav.TButton`, `NavActive.TButton`
- `Toolbar.TFrame`, `Header.TFrame` (标题栏直接用 bg_mantle)

## 4. 视图布局变更

所有视图统一 grid 结构:
```
视图自身 grid (2 行):
  row 0, weight=1:  主内容区
  row 1, weight=0:  状态栏 (32px)
```

### 4.1 ScreenshotView

```
主内容区 grid (2 列, row 0):
  column 0, weight=1: ImageCanvas
  column 1, minsize=240: ResultPanel

状态栏 (row 1):
  左: [打开文件(SmallAccent)] [识别(Small)] ● 状态文字
  右: (空)
```

**移除:** 旧 toolbar Frame + pack 布局
**新增:** `self._status_bar_frame, self._status_dot, self._status_label, self._status_info = self._create_status_bar()`

### 4.2 LiveView

```
主内容区 grid (2 列, row 0):
  column 0, weight=1: ImageCanvas
  column 1, minsize=240: ResultPanel

状态栏 (row 1):
  左: [开始(SmallAccent)] [暂停(Small)] [重置(Small)] ● 状态文字
  右: FPS: x.x | 帧: 42
```

**按钮样式:** `Small.TButton` / `SmallAccent.TButton`
**按钮状态机:** enabled/disabled 逻辑不变

### 4.3 DevView

```
主内容区 grid (3 列, row 0):
  column 0, weight=1: zone_canvas
  column 1, weight=1: det_canvas
  column 2, minsize=280: JSON 面板

JSON 面板:
  顶部: "JSON 输出" Label
  中部: tk.Text (scrollbar, mono 10px, bg_crust)
  底部: [复制JSON(Small)] 按钮

状态栏 (row 1):
  左: (空)
  右: 帧: 42 | 静态
```

**移除:** 旧 bottom Frame + _perf_label (合并进状态栏 status_info)

## 5. 状态指示灯颜色

| 状态 | Token | 深色值 | 浅色值 |
|------|-------|--------|--------|
| 就绪 | `green` | `#a6e3a1` | `#40a02b` |
| 处理中 | `accent` | `#89b4fa` | `#1e66f5` |
| 错误 | `red` | `#f38ba8` | `#d20f39` |
| 警告 | `peach` | `#fab387` | `#fe640b` |

## 6. 测试更新要点

**`test_base_view.py`:** 新增 `_create_status_bar()` 返回 4-tuple 断言、`set_status_text()` 委托断言

**`test_app.py`:** `SIDEBAR_WIDTH` 从 140→48，移除 `_status_label` 相关断言，验证 `_init_error` 委托

**`test_screenshot_view.py`:** `_status_label` 从 toolbar Label 变为 status_bar Label，断言方式不变

**`test_live_view.py`:** 同上

**`test_dev_view.py`:** `_perf_label` 合并进 `_status_info`，更新断言
