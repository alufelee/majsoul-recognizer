# Phase 4: 设置弹窗 + 收尾

> 母规格: `2026-05-11-gui-visual-redesign.md` (v3)
> 阶段: Phase 4 — 收尾，可独立提交
> 前置: Phase 1 + Phase 2 + Phase 3 完成

## 涉及文件

| 文件 | 改动类型 |
|------|---------|
| `settings_dialog.py` | 样式更新 |
| `tests/gui/test_settings_dialog.py` | 如存在则更新 |

## 1. SettingsDialog 样式更新

### 1.1 弹窗背景

`_dialog` (Toplevel) 背景: `bg_base`

### 1.2 分组标题 (`_add_section`)

- 颜色: `fg_primary`
- 字体: 11px bold
- 间距: 上方 8px

无改动 — 已使用 `("", 11, "bold")` + ttk 默认前景色。Phase 1 的 TButton/TLabel 默认样式更新会自动生效。

### 1.3 标签 (`_add_field`)

- 颜色: `fg_secondary`
- Phase 1 更新后 ttk.Label 默认 foreground 已是 `fg_primary`，如需 `fg_secondary` 需显式设置

### 1.4 输入框

- 背景: `bg_surface0`
- 文字: `fg_primary`
- 边框: 1px `bg_surface1`

`ttk.Entry` 在 clam 主题下的样式:
```python
style.configure("TEntry",
                fieldbackground=theme["bg_surface0"],
                foreground=theme["fg_primary"],
                bordercolor=theme["bg_surface1"],
                insertcolor=theme["fg_primary"])
```

需在 `apply_style()` 中添加 `TEntry` 配置。

### 1.5 按钮行

- "应用" 按钮: `style="Accent.TButton"` (Phase 1 已定义)
- "关闭" 按钮: `TButton` 默认样式（Phase 1 已更新）

当前代码未指定 `Accent.TButton`:
```python
ttk.Button(btn_frame, text="应用", command=self._on_apply_clicked).pack(side="left", padx=4)
```

改为:
```python
ttk.Button(btn_frame, text="应用", style="Accent.TButton",
           command=self._on_apply_clicked).pack(side="left", padx=4)
```

## 2. apply_style 追加

在 Phase 1 的 `apply_style()` 中追加:

```python
# 输入框
style.configure("TEntry",
                fieldbackground=theme["bg_surface0"],
                foreground=theme["fg_primary"])
```

**注意:** 此变更实际属于 Phase 1 的 `apply_style()` 更新，但功能上只有 SettingsDialog 使用，因此标注在 Phase 4 实施时补充。实际操作中可以在 Phase 1 一并添加。

## 3. 手动测试清单

全部阶段完成后的完整验证:

- [ ] 深色主题: 截图加载 → 识别 → 卡片结果正确显示
- [ ] 深色主题: 实时模式启动/暂停/重置 → 状态栏按钮和文字正确
- [ ] 浅色主题切换: 所有区域颜色正确更新
- [ ] 面板折叠/展开: 收缩到 24px 后可展开恢复，画布自动扩展
- [ ] App 级消息: 模型路径错误时状态栏显示"检测器降级模式"
- [ ] 空状态: 各视图切换后显示正确的空状态提示文字
- [ ] 侧边栏图标: 选中态高亮 + 色条，hover 态背景变化
- [ ] 设置弹窗: 输入框和按钮在新配色下可读
- [ ] 窗口缩放: 画布自适应，卡片面板宽度固定

## 4. 不涉及

- 功能逻辑变更
- 新增视图或组件
- 数据流/回调机制变更
- 设置项增减
- 拖放功能变更
