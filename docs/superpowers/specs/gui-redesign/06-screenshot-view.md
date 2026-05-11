# Task: screenshot_view.py — grid 布局 + 状态栏

## 文件
- 修改: `src/majsoul_recognizer/gui/views/screenshot_view.py`
- 更新: `tests/gui/test_screenshot_view.py`

## 布局变更: pack → grid

```
视图 grid (2 行):
  row 0, weight=1:  [ImageCanvas(col=0)] [ResultPanel(col=1)]
  row 1, weight=0:  状态栏
```

## __init__ 重写要点

1. 配置 grid: `self.grid_rowconfigure(0, weight=1)`, `self.grid_rowconfigure(1, weight=0)`
2. ImageCanvas: `grid(row=0, column=0, sticky="nsew")`
3. ResultPanel: `grid(row=0, column=1, sticky="ns")`
4. 列权重: `self.grid_columnconfigure(0, weight=1)`, `self.grid_columnconfigure(1, minsize=240)`
5. 调用 `_create_status_bar()` → `grid(row=1, column=0, columnspan=2, sticky="ew")`
6. 在 status_frame 左侧添加按钮:
   - "打开文件" → `style="SmallAccent.TButton"`
   - "识别" → `style="Small.TButton"`

## 移除
- toolbar Frame + pack 布局
- 旧的 `_status_label` (toolbar 中的 Label)

## 保留
- `_canvas`, `_result_panel` (改用 grid)
- `_open_button`, `_recognize_button` (改用 Small 样式，放入 status_frame)
- `_status_label` (来自 _create_status_bar)

## 测试更新

- `test_recognize_with_no_engine_shows_warning`: `view._status_label` 仍存在（来自 helper），断言不变
- 新增 import: `from majsoul_recognizer.gui.theme import Theme`
