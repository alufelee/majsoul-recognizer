# Task: live_view.py — grid 布局 + 状态栏

## 文件
- 修改: `src/majsoul_recognizer/gui/views/live_view.py`
- 更新: `tests/gui/test_live_view.py`

## 布局变更: pack → grid

```
视图 grid (2 行):
  row 0, weight=1:  [ImageCanvas(col=0)] [ResultPanel(col=1)]
  row 1, weight=0:  状态栏
```

## __init__ 重写要点

1. grid 配置同 screenshot_view
2. ImageCanvas: `grid(row=0, column=0, sticky="nsew")`
3. ResultPanel: `grid(row=0, column=1, sticky="ns")`
4. `_create_status_bar()` → `grid(row=1, column=0, columnspan=2, sticky="ew")`
5. status_frame 左侧按钮:
   - "开始" → `style="SmallAccent.TButton"`
   - "暂停" → `style="Small.TButton"`
   - "重置" → `style="Small.TButton"`
6. status_info 右侧显示 FPS 和帧数

## 状态栏信息更新

```python
# _poll_result 中:
self._status_info.config(text=f"FPS: {fps:.1f} | 帧: {frame.frame_id}")
# _on_reset 中:
self._status_info.config(text="")
```

## 移除
- toolbar Frame + pack
- 旧的 _fps_label, _status_label (toolbar 中的)
- `_fps_label` → 合并进 `_status_info`

## 保留
- `_canvas`, `_result_panel` (grid)
- `_start_button`, `_pause_button`, `_reset_button` (Small 样式)
- 状态机逻辑完全不变
- `_status_label` (来自 helper)

## 测试更新

- 按钮状态测试不变（_start_button 等仍存在，只是样式变了）
- `_fps_label` → `_status_info`，如测试引用了需更新
