# Task: dev_view.py — 3 列 grid + 状态栏

## 文件
- 修改: `src/majsoul_recognizer/gui/views/dev_view.py`
- 更新: `tests/gui/test_dev_view.py`

## 布局变更: pack → 3 列 grid

```
视图 grid (2 行):
  row 0, weight=1:  [zone_canvas(c0)] [det_canvas(c1)] [JSON面板(c2)]
  row 1, weight=0:  状态栏
```

## __init__ 重写要点

1. grid: `grid_rowconfigure(0, weight=1)`, `grid_columnconfigure(0, weight=1)`, `grid_columnconfigure(1, weight=1)`, `grid_columnconfigure(2, minsize=280)`
2. zone_canvas: `grid(row=0, column=0, sticky="nsew")`
3. det_canvas: `grid(row=0, column=1, sticky="nsew")`
4. JSON 面板 (Frame): `grid(row=0, column=2, sticky="ns")`
5. JSON 面板内部: 顶部标题 + tk.Text + scrollbar + 底部"复制JSON"按钮
6. `_create_status_bar()` → `grid(row=1, column=0, columnspan=3, sticky="ew")`

## 状态栏信息

```python
# update_data 中:
self._status_info.config(
    text=f"帧: {frame.frame_id} | {'静态' if frame.is_static else '动画'}"
)
```

## 移除
- canvas_frame + pack
- json_frame + pack
- bottom Frame + _perf_label + pack

## 保留
- `_zone_canvas`, `_det_canvas` (grid)
- `_json_text` (在 JSON 面板 Frame 内)
- `_copy_button` (Small 样式，JSON 面板底部)
- `_current_image`, `_compute_zone_rects` 逻辑不变
- `_status_info` 替代 `_perf_label`

## 测试更新

- `_perf_label.cget("text")` → `_status_info.cget("text")`
- 断言内容不变（"帧: 1" 等）
