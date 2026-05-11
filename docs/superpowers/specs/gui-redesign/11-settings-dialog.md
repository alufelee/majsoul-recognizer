# Task: settings_dialog.py — 样式更新

## 文件
- 修改: `src/majsoul_recognizer/gui/settings_dialog.py`
- 无专用测试文件（测试通过手动验证）

## 变更

1. "应用" 按钮: 添加 `style="Accent.TButton"`
2. _dialog Toplevel 背景: 不变（ttk.Frame 使用 bg_base）
3. 其他: Phase 1 的 TEntry/TButton 默认样式更新会自动生效

```python
# 唯一代码改动:
ttk.Button(btn_frame, text="应用", style="Accent.TButton",
           command=self._on_apply_clicked).pack(side="left", padx=4)
```
