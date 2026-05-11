# Task: app.py — Canvas 侧边栏 + 状态委托

## 文件
- 修改: `src/majsoul_recognizer/gui/app.py`
- 更新: `tests/gui/test_app.py`

## 常量变更
- `SIDEBAR_WIDTH = 140` → `48`
- `NAV_ITEMS` 改为内部数据: `[("screenshot", "截图"), ("live", "实时"), ("dev", "调试")]`

## 新增 _SidebarIcon 类 (app.py 内)

36x36 tk.Canvas，图标绘制坐标:
- **截图**: 外矩形 (10,11)→(26,25) + 左上折线 (10,11)→(10,15)→(14,15)→(14,11)
- **实时**: 中心圆 r=3 (18,18) + 弧线 r=6/9
- **调试**: 外圆 r=8 (18,18) + 内圆 r=3 + 6条辐射线(60°间隔, 延伸2px)

交互: `<Button-1>` → command, `<Enter/Leave>` → hover, `set_active(bool)` → 选中态

选中态: bg=`accent_dim` + 左侧 2px `accent` 色条
未选中: bg=`bg_crust`, hover 时 bg=`bg_surface0`

## _build_ui 变更

### 移除
- status_outer, status_border, status_bar, status_dot, _status_label, _status_info
- ttk.Button 侧边栏导航按钮 → Canvas 图标

### 保留
- header_frame + _header_border (accent 分割线)
- sidebar Frame → 内放 _SidebarIcon Canvas
- content area (不变)

### 标题栏
- 按钮文字: "切换主题"→"主题", "设置"→"设置"

## 状态委托

```python
# __init__:
self._init_error: str | None = None
try:
    engine = RecognitionEngine(config)
except Exception as e:
    engine = None
    self._init_error = "检测器降级模式"

# _switch_view 末尾:
if self._init_error:
    self._active_view.set_status_text(self._init_error)
    self._init_error = None

# _rebuild_engine:
# 原: self._status_label.config(text=f"引擎重建失败: {e}")
# 新: self._active_view.set_status_text(f"引擎重建失败: {e}")
```

## _toggle_theme 变更

移除: status_dot/status_border 颜色更新
新增: sidebar icon.on_theme_changed(new_theme)

## apply_style 清理 (与 app.py 同步)

移除: Sidebar.TFrame, Nav.TButton, NavActive.TButton, Header.TFrame, Toolbar.TFrame

## 测试更新

- 无 `_status_label` 引用（test_app.py 未直接引用）
- engine 失败测试: 验证 `_init_error` 而非 `_status_label`
