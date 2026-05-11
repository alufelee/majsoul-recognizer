# GUI 视觉重设计规格

> 日期: 2026-05-11（v3 — 二次严审修复版）
> 分支: feat/gui
> 前置: 现有 GUI 功能代码已完成（51 tests passing）

## 1. 概述

对现有 Tkinter GUI 进行视觉全面升级，解决四个核心问题：风格太素、配色不和谐、布局比例失调、缺少交互反馈。

**设计方向**: 现代深色工具风（VS Code / Discord 风格），图标式侧边栏 + 可折叠结果面板 + 紧凑状态栏。

**不含**: 功能变更、新增视图、数据流变更。仅改变视觉表现层。

## 2. 整体布局

```
┌──────────────────────────────────────────────────────┐
│ 标题栏 (36px): 雀魂麻将识别助手           主题  设置 │
├──┬───────────────────────────────────────────────────┤
│  │ ┌─────────────────────────┬─────────────────────┐ │
│图│ │                         │ 识别结果         ◀ │ │
│标│ │       ImageCanvas       │  ┌SectionCards┐    │ │
│侧│ │                         │  │ 局次        │    │ │
│栏│ │                         │  │ 手牌        │    │ │
│48│ │                         │  │ 分数 ...    │    │ │
│px│ │                         │  └────────────┘    │ │
│  │ ├─────────────────────────┴─────────────────────┤ │
│  │ │ [操作按钮] ● 状态文字             FPS | 延迟  │ │
│  │ └───────────────────────────────────────────────┘ │
├──┴───────────────────────────────────────────────────┤
└──────────────────────────────────────────────────────┘
              ↑ 状态栏在视图内部，非 App 层
```

### 2.1 侧边栏 (48px)

- 纯图标按钮，无文字
- 图标使用 Canvas 绘制简单几何图形（跨平台一致，不依赖 Unicode/emoji）
  - 截图: 矩形 + 左上角折线（文件/截图图标）
  - 实时: 圆圈 + 右侧辐射短线（信号/广播图标）
  - 调试: 外圆 + 内圆 + 辐射齿（齿轮图标）
- 选中态: 背景色 `accent_dim` + 左侧 2px `accent` 色条（通过 Canvas 绘制）
- 未选中: 透明背景
- Hover: `bg_surface0` 背景
- 按钮实现: 使用 `tk.Canvas`（36x36px）+ `<Button-1>` / `<Enter>` / `<Leave>` 事件绑定，**不使用 `ttk.Button`**
- 按钮间距: 顶部 12px，项间 4px

### 2.2 标题栏 (36px)

- 高度 36px，背景 `bg_mantle`
- 底部 1px `bg_surface0` 分割线（通过 `height=1` 的 Canvas）
- 左侧: 应用标题（12px bold）
- 右侧: 版本号（10px muted，最右侧）
- 右侧按钮: `ttk.Button`，文字标签分别为"主题"和"设置"（10px 字体），不限制固定宽度，通过 padding 控制尺寸。**不使用图标**（24px 放不下中文文字）

### 2.3 状态栏 — 视图内嵌 + App 消息委托

**关键决策: 状态栏由各视图自行创建和管理。App 不创建底部 UI。**

**理由**: 避免视图向 App 注入按钮的接口复杂度，各视图保持自治。视觉上各视图状态栏颜色一致，用户感知为统一的底部栏。

**BaseView 提供 `_create_status_bar()` helper:**

```python
class BaseView(ttk.Frame):
    def _create_status_bar(self) -> tuple[ttk.Frame, tk.Canvas, ttk.Label, ttk.Label]:
        """创建统一风格的状态栏区域。

        Returns: (status_frame, status_dot, status_label, status_info)
        """
        # 1px 顶部分割线 (Canvas, height=1, bg=surface0)
        # 32px 高 Frame (bg=bg_crust)
        #   左: 操作按钮区 + 6px 圆点 Canvas + 状态文字 Label
        #   右: 信息 Label (FPS/延迟/帧)
```

各视图在 `__init__` 中调用此方法，自行添加操作按钮到返回的 `status_frame` 左侧。

**App 级状态消息委托:**

App 不再拥有状态栏，但需要显示 App 级消息（"检测器降级模式"、"引擎重建失败"）。通过 `BaseView.set_status_text(text: str)` 方法委托给当前活跃视图:

```python
# BaseView 新增方法
def set_status_text(self, text: str) -> None:
    """App 级状态消息委托"""
    if hasattr(self, '_status_label'):
        self._status_label.config(text=text)
```

```python
# App 使用方式
def _rebuild_engine(self) -> None:
    ...
    except Exception as e:
        logger.error("Engine rebuild failed: %s", e)
        # 委托给当前视图显示
        self._active_view.set_status_text(f"引擎重建失败: {e}")
```

**通用状态栏结构:**
```
┌─ 1px bg_surface0 分割线 ─────────────────────────────┐
│ [按钮...]  ● 状态文字                    FPS | 延迟   │
│ (32px 高, bg_crust 背景)                              │
└───────────────────────────────────────────────────────┘
```

- 高度 32px，背景 `bg_crust`
- 左侧: 操作按钮 + 状态指示灯（6px Canvas 圆点）+ 状态文字
- 右侧: FPS / 延迟 / 帧数
- 字号: 10px，颜色 `fg_secondary`

**状态指示灯颜色:**

| 状态 | Token | 深色值 | 浅色值 |
|------|-------|--------|--------|
| 就绪 | `green` | `#a6e3a1` | `#40a02b` |
| 处理中 | `accent` | `#89b4fa` | `#1e66f5` |
| 错误 | `red` | `#f38ba8` | `#d20f39` |
| 警告 | `peach` | `#fab387` | `#fe640b` |

## 3. 配色方案

基于 Catppuccin Mocha。`blue` 与 `accent` 共享同一色值 `#89b4fa`，但语义不同: `accent` 用于 UI 控件（按钮、选中态），`blue` 用于数据标签（局次卡片）。未来如需独立调整，只需拆分值。

### 3.1 Theme Dict 迁移映射

现有 `Theme.DARK` / `Theme.LIGHT` 的 key 全部替换。以下是旧→新映射:

| 旧 key | 新 key | 深色值 | 浅色值 | 用途 |
|--------|--------|--------|--------|------|
| `bg_primary` | `bg_base` | `#1e1e2e` | `#eff1f5` | 主背景 |
| `bg_secondary` | `bg_mantle` | `#181825` | `#e6e9ef` | 标题栏、面板、卡片底色 |
| `bg_tertiary` | `bg_surface0` | `#313244` | `#ccd0da` | 卡片背景、输入框 |
| _(新增)_ | `bg_surface1` | `#45475a` | `#bcc0cc` | hover 背景 |
| `bg_sidebar` | `bg_crust` | `#11111b` | `#dce0e8` | 侧边栏、画布底色、状态栏 |
| `bg_header` | `bg_mantle` | `#181825` | `#e6e9ef` | 标题栏（复用 mantle） |
| `fg_primary` | `fg_primary` | `#cdd6f4` | `#4c4f69` | 主要文字 |
| `fg_secondary` | `fg_secondary` | `#a6adc8` | `#7c7f93` | 标签文字 |
| `fg_muted` | `fg_muted` | `#6c7086` | `#9ca0b0` | 禁用/提示 |
| `accent` | `accent` | `#89b4fa` | `#1e66f5` | 主强调 |
| `accent_dim` | `accent_dim` | `#1a3a5c` | `#a8c8f0` | 选中态背景 |
| `success` | `green` | `#a6e3a1` | `#40a02b` | 成功 |
| `warning` | `peach` | `#fab387` | `#fe640b` | 警告 |
| `error` | `red` | `#f38ba8` | `#d20f39` | 错误 |
| `highlight` | `peach` | `#fab387` | `#fe640b` | 摸牌高亮（复用 peach） |
| `border` | `bg_surface0` | `#313244` | `#ccd0da` | 分割线（复用 surface0） |
| `canvas_bg` | `bg_crust` | `#11111b` | `#dce0e8` | 画布背景（复用 crust） |
| _(新增)_ | `blue` | `#89b4fa` | `#1e66f5` | 局次标签 |
| _(新增)_ | `yellow` | `#f9e2af` | `#df8e1d` | 副露标签 |
| _(新增)_ | `mauve` | `#cba6f7` | `#8839ef` | 分数标签 |
| _(新增)_ | `teal` | `#94e2d5` | `#179299` | 牌河标签 |
| _(新增)_ | `lavender` | `#b4befe` | `#7287fd` | 万子检测框 |
| _(新增)_ | `sky` | `#89dceb` | `#04a5e5` | 筒子检测框 |
| _(新增)_ | `flamingo` | `#f2cdcd` | `#dd7878` | 字牌检测框 |
| _(新增)_ | `surface_hover` | `#45475a` | `#bcc0cc` | 按钮 hover 背景 |

**迁移影响**: 所有引用 `theme["bg_primary"]` → `theme["bg_base"]`，`theme["bg_secondary"]` → `theme["bg_mantle"]` 等。需全项目搜索替换（约 20+ 处）。

### 3.2 浅色主题 (Catppuccin Latte)

浅色主题配色已在上表列出。设计原则:
- 浅色主题使用 Catppuccin Latte 色板，与深色 Mocha 保持相同的 token 名称
- `accent_dim` 浅色值使用 `#a8c8f0`（中等饱和蓝），在 `bg_base` (`#eff1f5`) 浅背景上有足够对比度（RGB 168,200,240 vs 239,241,245，色差明显可辨）
- SectionCard 左边框颜色使用浅色版本的对应色
- Accent 按钮文字色: 浅色主题下改为 `#ffffff`（浅色 `accent` `#1e66f5` 上白色文字可读性更好）

### 3.3 检测框颜色

| 类别 | 深色值 | 浅色值 | 适用 tile_code |
|------|--------|--------|----------------|
| 万子 (m) | `#b4befe` | `#7287fd` | 1m-9m |
| 筒子 (p) | `#89dceb` | `#04a5e5` | 1p-9p |
| 索子 (s) | `#f38ba8` | `#d20f39` | 1s-9s |
| 字牌 (z) | `#f2cdcd` | `#dd7878` | 1z-7z |
| 赤宝 (r) | `#fab387` | `#fe640b` | 5mr/5pr/5sr |
| 特殊 (x) | `#6c7086` | `#9ca0b0` | back/rotated/dora_frame |

## 4. 组件设计

### 4.1 ResultPanel — 卡片式结果面板

从 `tk.Text` 重写为 `ttk.Frame` 内嵌多个 SectionCard。

**外部 API 保持不变:**
```python
class ResultPanel(ttk.Frame):
    def update_state(self, state: GameState | None, latency_ms: float = 0) -> None: ...
    def on_theme_changed(self, theme: dict[str, str]) -> None: ...
```

**创建一次、更新内容（不销毁重建）:**

`__init__` 时创建固定数量的 SectionCard 实例（局次、宝牌、手牌、摸牌、副露、分数、牌河、动作、警告、延迟），初始为空/隐藏。`update_state()` 仅更新每个卡片的内容文字和可见性，不销毁/重建 widget。这样在实时模式 5 FPS 下无闪烁和性能问题。

`on_theme_changed` 更新面板背景、每个 SectionCard 的 Canvas 边框色和标签色。

**面板容器:**
- 宽度 240px，通过 `grid(columnconfigure)` 的 `minsize=240` 固定，背景 `bg_mantle`
- 顶部标题行 (`ttk.Frame`, 28px 高): 左侧 "识别结果" Label + 右侧折叠按钮
- 左侧 1px `bg_surface0` 分割线（面板内嵌的 Canvas, `width=1`, `pack(side="left")`)

**折叠/展开机制:**
- 面板通过 grid 放置: `grid(row=0, column=1, sticky="ns")` 在父视图中
- 折叠: 父视图 `columnconfigure(1, minsize=24)`，面板内 `title_label.pack_forget()` + `cards_container.pack_forget()`，仅保留折叠按钮列
- 展开: 父视图 `columnconfigure(1, minsize=240)`，`pack()` 恢复标题和卡片
- 折叠按钮始终可见（24px 窄条中垂直居中）

**SectionCard 实现:**
```
┌──────────────────────┐
│▌ 局次                │  ← 标签用区域色，9px
│▌ 东一局 0本场 0供托   │  ← 值用 fg_primary，11px
└──────────────────────┘
```

- 使用 `ttk.Frame` 作为容器，背景 `bg_crust`
- 左边框: 内嵌 `tk.Canvas`（width=2, height=自动）, fill=区域色
- **不做圆角**: 通过 2px 左边框色条 + 背景色差异 + 间距实现视觉分层
- 内边距: 6px 8px（`padx=8, pady=6`）
- 卡片间距: 6px（`pady=3` 上下各 3px）
- 无数据时: 值显示 "-"（`fg_muted` 色），卡片仍保留但内容为占位符
- 更新时仅修改 Label 的 `text` 属性，不重建 widget

**区域对应色:**

| 区域 | Token | 深色值 | 浅色值 |
|------|-------|--------|--------|
| 局次/宝牌 | `blue` | `#89b4fa` | `#1e66f5` |
| 手牌/摸牌 | `green` | `#a6e3a1` | `#40a02b` |
| 副露 | `yellow` | `#f9e2af` | `#df8e1d` |
| 分数 | `mauve` | `#cba6f7` | `#8839ef` |
| 牌河 | `teal` | `#94e2d5` | `#179299` |
| 动作 | `peach` | `#fab387` | `#fe640b` |
| 警告 | `red` | `#f38ba8` | `#d20f39` |

### 4.2 ImageCanvas — 空状态

当无图像时，画布通过 Canvas 方法绘制居中提示（不使用 Unicode/emoji）:

- Canvas `create_text` 绘制提示文字（`fg_muted` 色，11px）
- 可选: 在文字上方绘制简单几何图形（矩形框，表示占位图），颜色 `bg_surface0`
- `show_empty_state(hint_text: str)` 方法由视图在初始化和 `clear()` 时调用
- `show_image()` 时自动清除空状态

各视图的提示文字:
- 截图视图: "拖放或点击加载截图"
- 实时视图: "点击「开始」捕获窗口"
- 调试视图: "在其他视图识别后切换查看"

### 4.3 按钮

**实现: 使用 `ttk.Button` + `ttk.Style` 配置。不使用圆角。**

**基础样式 `TButton` 配置为与 `Default.TButton` 相同的视觉效果。** 现有代码中未指定 `style` 参数的 `ttk.Button()` 自动使用 `TButton`，因此无需逐个修改。需要显式不同样式的按钮才指定 `style="Accent.TButton"` 等。

| 样式名 | 背景色 | 文字色 | Hover 背景 | 用途 |
|--------|--------|--------|-----------|------|
| `TButton` (默认) | `bg_surface0` | `fg_primary` | `bg_surface1` | 未指定 style 的所有按钮 |
| `Accent.TButton` | `accent` | `bg_crust`(深)/`#ffffff`(浅) | `surface_hover` | "识别"、"开始"、"应用" |
| `Small.TButton` | `bg_surface0` | `fg_primary` | `bg_surface1` | 状态栏内小按钮 |
| `SmallAccent.TButton` | `accent` | `bg_crust`(深)/`#ffffff`(浅) | `surface_hover` | 状态栏内强调按钮 |

禁用态通过 `style.map` 配置:
```python
style.map("TButton",
          background=[("disabled", bg_surface0)],
          foreground=[("disabled", fg_muted)])
style.map("Accent.TButton",
          background=[("active", surface_hover), ("disabled", bg_surface0)],
          foreground=[("disabled", fg_muted)])
```

按钮高度: 通过 `padding=(12, 4)` 控制（水平 12px，垂直 4px）。

### 4.4 侧边栏图标

使用 `tk.Canvas`（36x36px）绘制，通过 `<Button-1>` 事件触发导航，`<Enter>` / `<Leave>` 控制 hover 效果。

**所有坐标为 Canvas 绝对坐标。** 20x20 图标区域居中于 36x36 Canvas，偏移量 (8,8)。即 20x20 区域的 Canvas 坐标范围为 (8,8) → (28,28)。

**截图图标:**
- 外矩形: (10, 11) → (26, 25), 线宽 1.5px
- 左上角折线: (10, 11) → (10, 15) → (14, 15) → (14, 11), 线宽 1.5px
- 颜色: `fg_secondary`，选中态 `fg_primary`

**实时图标:**
- 中心圆: 半径 3px, 圆心 (18, 18)
- 三段弧线: 从圆心向外辐射，半径 6px / 9px，各占 120°
- 颜色: `fg_secondary`，选中态 `fg_primary`

**调试图标:**
- 外圆: 半径 8px, 圆心 (18, 18)
- 内圆: 半径 3px, 圆心 (18, 18)
- 6 条短辐射线: 从外圆向外延伸 2px, 等间隔 60°
- 颜色: `fg_secondary`，选中态 `fg_primary`

## 5. 各视图布局

所有视图统一使用以下 grid 结构:

```
视图自身 grid (2 行):
  row 0, weight=1:  主内容区 (画布 + 面板, 或三列)
  row 1, weight=0:  状态栏 (32px 固定高度)
```

### 5.1 ScreenshotView

```
主内容区 grid (2 列, row 0):
  column 0, weight=1: ImageCanvas
  column 1, minsize=240: ResultPanel (可折叠至 24px)

状态栏 (row 1, 32px, bg_crust):
  左: [打开文件(SmallAccent)] [识别(Small)] ● 状态文字
  右: (空)
```

### 5.2 LiveView

```
主内容区 grid (2 列, row 0):
  column 0, weight=1: ImageCanvas
  column 1, minsize=240: ResultPanel (可折叠至 24px)

状态栏 (row 1, 32px, bg_crust):
  左: [开始(SmallAccent)] [暂停(Small)] [重置(Small)] ● 状态文字
  右: FPS: x.x | 帧: 42
```

按钮 enabled/disabled 状态机不变。

### 5.3 DevView

```
主内容区 grid (3 列, row 0):
  column 0, weight=1: zone_canvas
  column 1, weight=1: det_canvas
  column 2, minsize=280: JSON 面板

JSON 面板:
  顶部: "JSON 输出" 标题 (PanelHeader)
  中部: tk.Text (scrollbar, mono font 10px, bg_crust)
  底部: [复制JSON(Small)] 按钮

状态栏 (row 1, 32px, bg_crust):
  左: (空)
  右: 帧: 42 | 静态
```

DevView 不包含 ResultPanel（数据通过 JSON 输出和画布叠加展示）。

### 5.4 SettingsDialog

**样式更新:**
- 弹窗背景: `bg_base`
- 分组标题 (`_add_section`): `fg_primary`, 11px bold, 上方 8px 间距
- 标签 (`_add_field`): `fg_secondary`
- 输入框: `bg_surface0` 背景, `fg_primary` 文字, 1px `bg_surface1` 边框
- 按钮行: [应用(Accent)] [关闭(TButton 默认)]

## 6. 实现策略

### 6.1 实现阶段（原子提交单元）

**阶段 1: 基础 — 配色和样式**

同步修改，可独立编译:
- `theme.py` — 替换所有颜色 key 和值，更新 `apply_style()`，将 `TButton` 默认样式配置为 `surface0` 背景
- `widgets/colors.py` — 更新检测框和区域颜色为 Catppuccin 色
- 全项目搜索替换旧 theme key（`bg_primary`→`bg_base` 等），更新所有引用处
- 运行测试，修复断言

**阶段 2: 框架 + 视图 — 同步改动（不可拆分）**

以下改动必须在一个提交中完成，否则中间态会崩溃:
- `base_view.py` — 新增 `_create_status_bar()` helper + `set_status_text()` 委托方法
- `app.py` — 移除 App 层状态栏和分割线、侧边栏改为 Canvas 图标、标题栏按钮改文字、状态消息改为调用 `active_view.set_status_text()`
- `views/screenshot_view.py` — 使用 `_create_status_bar()`，grid 布局，移除旧 toolbar
- `views/live_view.py` — 同上
- `views/dev_view.py` — 三列 grid 布局，使用 `_create_status_bar()`

**阶段 3: 核心组件**

- `widgets/result_panel.py` — 重写为卡片式 Frame（创建一次、更新内容）
- `widgets/image_canvas.py` — 新增 `show_empty_state()` 方法

**阶段 4: 收尾**

- `settings_dialog.py` — 输入框/按钮样式更新
- 所有测试更新修复

### 6.2 不变的部分

- `worker.py` — 异步识别逻辑不变
- `app_state.py` — 数据结构不变
- `settings.py` — 配置字段不变
- `fps_counter.py` — FPS 计算逻辑不变
- 所有数据流和回调机制不变
- `_WorkerResult` 数据类不变
- `on_result` 回调签名不变

### 6.3 ttk.Style 新增/变更样式

```python
# 侧边栏: 使用 tk.Canvas，不使用 ttk 样式
# (移除 "Nav.TButton", "NavActive.TButton" — 被 Canvas 图标替代)

# 变更
"TButton"                # 默认按钮样式 → surface0 背景（原为 bg_tertiary）
"Accent.TButton"         # 主操作按钮（更新配色）

# 新增
"Small.TButton"          # 状态栏内小按钮（surface0 背景）
"SmallAccent.TButton"    # 状态栏内强调按钮（accent 背景）
"PanelHeader.TLabel"     # 面板标题行标签
"CardLabel.TLabel"       # 卡片标签（fg_secondary, 9px）
"CardValue.TLabel"       # 卡片值（fg_primary, 11px）

# 移除
"Nav.TButton"            # 被 Canvas 图标替代
"NavActive.TButton"      # 被 Canvas 图标替代
"Toolbar.TFrame"         # 被视图内嵌状态栏替代
"Sidebar.TFrame"         # 侧边栏背景色通过 Canvas 自身 bg 控制
```

## 7. 测试策略

### 7.1 单元测试更新

| 测试文件 | 更新内容 |
|---------|---------|
| `test_theme.py` | 颜色 key 从旧名更新为新名，新增浅色 Latte 断言，验证 `TButton` 默认样式配置 |
| `test_app.py` | 侧边栏宽度 140→48，App 不再拥有 `_status_label`（改为 `active_view.set_status_text()` 调用验证） |
| `test_screenshot_view.py` | 工具栏断言更新为状态栏模式，验证 `_create_status_bar()` 被调用 |
| `test_live_view.py` | 同上 |
| `test_dev_view.py` | 布局从 pack 改为 grid 的断言更新 |
| `test_result_panel.py` | **全部重写**: 验证卡片数量（7-8 个 SectionCard）、`update_state(None)` 各卡片显示"-"、`update_state(state)` 各卡片内容正确、`on_theme_changed()` Canvas 边框色更新、快速连续调用 `update_state()` 无闪烁/widget 泄漏 |
| `widgets/test_image_canvas.py` | 新增 `show_empty_state()` 和 `clear()` 清除空状态的测试 |
| `test_base_view.py` | 新增 `_create_status_bar()` 返回值类型断言、`set_status_text()` 委托断言 |
| `test_worker.py` | 不变 |
| `test_settings_dialog.py` | 按钮样式断言更新 |

### 7.2 手动测试清单

- [ ] 深色主题: 截图加载 → 识别 → 卡片结果正确显示
- [ ] 深色主题: 实时模式启动/暂停/重置 → 状态栏按钮和文字正确
- [ ] 浅色主题切换: 所有区域颜色正确更新（侧边栏、标题栏、画布、卡片、按钮）
- [ ] 面板折叠/展开: 收缩到 24px 后可展开恢复，画布自动扩展
- [ ] App 级消息: 模型路径错误时状态栏显示"检测器降级模式"
- [ ] 空状态: 各视图切换后显示正确的空状态提示文字
- [ ] 侧边栏图标: 选中态高亮 + 色条，hover 态背景变化
- [ ] 设置弹窗: 输入框和按钮在新配色下可读
- [ ] 窗口缩放: 画布自适应，卡片面板宽度固定

## 8. 不涉及

- 功能逻辑变更
- 新增视图或组件
- 数据流/回调机制变更
- 设置项增减
- 拖放功能变更
- 深色/浅色以外的主题
