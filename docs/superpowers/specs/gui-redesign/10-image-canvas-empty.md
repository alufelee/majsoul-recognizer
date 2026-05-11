# Task: image_canvas.py — 空状态提示

## 文件
- 修改: `src/majsoul_recognizer/gui/widgets/image_canvas.py`
- 更新: `tests/gui/widgets/test_image_canvas.py`

## 新增方法: show_empty_state

```python
def show_empty_state(self, hint_text: str) -> None:
    """显示空状态居中提示"""
    self.delete("all")
    self._photo = None
    cw = max(self.winfo_width(), self.winfo_reqwidth(), 200)
    ch = max(self.winfo_height(), self.winfo_reqheight(), 150)
    # 占位矩形 (48x36)
    rw, rh = 48, 36
    rx, ry = (cw - rw) // 2, (ch - rh) // 2 - 12
    self.create_rectangle(rx, ry, rx + rw, ry + rh,
                          outline=self._theme["bg_surface0"], width=2)
    # 提示文字
    self.create_text(cw // 2, ry + rh + 16, text=hint_text,
                     fill=self._theme["fg_muted"], font=("", 11))
```

## 现有 clear() — 无需改动

已有 `self.delete("all")` + 置空 `_photo`/`_pending_image`，能清除空状态。

## show_image() — 无需改动

已有 `self.delete("all")`，自动清除空状态。

## 测试新增

```python
class TestImageCanvasEmptyState:
    def test_show_empty_state_draws_items(self, canvas): ...
    def test_show_image_clears_empty_state(self, canvas): ...
    def test_clear_removes_empty_state(self, canvas): ...
```

## 视图调用 (Phase 2 视图改造时添加)

- ScreenshotView: `"拖放或点击加载截图"`
- LiveView: `"点击「开始」捕获窗口"`
- DevView: `"在其他视图识别后切换查看"`
