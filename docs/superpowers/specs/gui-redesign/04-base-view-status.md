# Task: base_view.py — 状态栏 helper + 状态委托

## 文件
- 修改: `src/majsoul_recognizer/gui/base_view.py`
- 更新: `tests/gui/test_base_view.py`

## 新增 import

```python
import tkinter as tk
```

## 新增 _create_status_bar()

```python
def _create_status_bar(self) -> tuple[ttk.Frame, tk.Canvas, ttk.Label, ttk.Label]:
    """创建统一风格的状态栏组件。

    Returns: (status_frame, status_dot, status_label, status_info)
    """
    outer = ttk.Frame(self)

    # 1px 分割线
    sep = tk.Canvas(outer, height=1, bg=self._theme["bg_surface0"],
                    highlightthickness=0)
    sep.pack(side="top", fill="x")

    # 32px 状态栏
    bar = ttk.Frame(outer, style="StatusBar.TFrame", height=32)
    bar.pack(side="top", fill="x")
    bar.pack_propagate(False)

    # 状态指示灯 (16x16, 内含 10px 圆点)
    dot = tk.Canvas(bar, width=16, height=16,
                    bg=self._theme["bg_crust"], highlightthickness=0)
    dot.pack(side="left", padx=(8, 4), pady=8)
    dot.create_oval(3, 3, 13, 13, fill=self._theme["green"], outline="")

    # 状态文字
    status_label = ttk.Label(bar, text="就绪", style="Status.TLabel")
    status_label.pack(side="left")

    # 右侧信息
    info_label = ttk.Label(bar, text="", style="Status.TLabel")
    info_label.pack(side="right", padx=8)

    self._status_label = status_label
    return bar, dot, status_label, info_label
```

## 新增 set_status_text()

```python
def set_status_text(self, text: str) -> None:
    """App 级状态消息委托"""
    if hasattr(self, '_status_label') and self._status_label is not None:
        self._status_label.config(text=text)
```

## 测试新增

```python
class TestBaseViewStatusBar:
    def test_create_status_bar_returns_tuple(self, tk_root, mock_app_state):
        view = BaseView(tk_root, mock_app_state, Theme.DARK)
        bar, dot, label, info = view._create_status_bar()
        assert bar is not None
        assert dot is not None
        assert label is not None
        assert info is not None

    def test_set_status_text(self, tk_root, mock_app_state):
        view = BaseView(tk_root, mock_app_state, Theme.DARK)
        view._create_status_bar()
        view.set_status_text("测试消息")
        assert view._status_label.cget("text") == "测试消息"

    def test_set_status_text_without_bar_is_safe(self, tk_root, mock_app_state):
        view = BaseView(tk_root, mock_app_state, Theme.DARK)
        view.set_status_text("安全")  # 不应抛异常
```
