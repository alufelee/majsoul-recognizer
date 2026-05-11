# Phase 3: 核心组件重写

> 母规格: `2026-05-11-gui-visual-redesign.md` (v3)
> 阶段: Phase 3 — 可独立编译、独立提交
> 前置: Phase 1 + Phase 2 完成

## 涉及文件

| 文件 | 改动类型 |
|------|---------|
| `widgets/result_panel.py` | **完全重写**: tk.Text → 卡片式 ttk.Frame |
| `widgets/image_canvas.py` | 新增 `show_empty_state()` 方法 |
| `tests/gui/widgets/test_result_panel.py` | **完全重写** |
| `tests/gui/widgets/test_image_canvas.py` | 新增空状态测试 |

## 不变的文件

所有视图、app.py、base_view.py — 仅通过 ResultPanel/ImageCanvas 的公共 API 交互。

## 1. ResultPanel — 卡片式重写

### 1.1 外部 API（不变）

```python
class ResultPanel(ttk.Frame):
    def __init__(self, parent, theme: dict[str, str], **kwargs): ...
    def update_state(self, state: GameState | None, latency_ms: float = 0) -> None: ...
    def on_theme_changed(self, theme: dict[str, str]) -> None: ...
```

### 1.2 内部结构

**面板容器:**
- 宽度 240px，背景 `bg_mantle`
- 顶部标题行 (28px): "识别结果" + 折叠按钮 "◀"
- 左侧 1px `bg_surface0` 分割线 (Canvas, width=1)
- 卡片容器: 可滚动区域

**SectionCard 列表（创建一次、更新内容）:**

| # | 标签 | 颜色 token | 数据字段 |
|---|------|-----------|---------|
| 0 | 局次 | `blue` | `state.round_info` |
| 1 | 宝牌 | `blue` | `state.dora_indicators` |
| 2 | 手牌 | `green` | `state.hand` |
| 3 | 摸牌 | `green` | `state.drawn_tile` |
| 4 | 副露 | `yellow` | `state.calls` |
| 5 | 分数 | `mauve` | `state.scores` |
| 6 | 牌河 | `teal` | `state.discards` |
| 7 | 动作 | `peach` | `state.actions` |
| 8 | 警告 | `red` | `state.warnings` |

### 1.3 SectionCard 实现

```
┌──────────────────────┐
│▌ 局次                │  ← 标签用区域色，9px
│▌ 东一局 0本场 0供托   │  ← 值用 fg_primary，11px
└──────────────────────┘
```

- 容器: `ttk.Frame(style="Card.TFrame")`
- 左边框: `tk.Canvas(width=2, fill=区域色)`
- 标签: `ttk.Label(style="CardLabel.TLabel")`
- 值: `ttk.Label(style="CardValue.TLabel")`
- 内边距: padx=(8,6), pady=6
- 卡片间距: pady=3
- 无数据时: 值显示 "-"，fg_muted 色

### 1.4 update_state 逻辑

```python
def update_state(self, state: GameState | None, latency_ms: float = 0) -> None:
    if state is None:
        for card in self._cards:
            card.update_value("-")
        return
    # 局次
    if state.round_info:
        ri = state.round_info
        self._cards[0].update_value(f"{ri.wind}{ri.number}局 {ri.honba}本场 {ri.kyotaku}供托")
    else:
        self._cards[0].update_value("-")
    # 宝牌
    self._cards[1].update_value(" ".join(state.dora_indicators) if state.dora_indicators else "-")
    # 手牌
    self._cards[2].update_value(" ".join(state.hand) if state.hand else "-")
    # 摸牌
    self._cards[3].update_value(state.drawn_tile or "-")
    # 副露
    if state.calls:
        parts = []
        for player, groups in state.calls.items():
            for g in groups:
                parts.append(f"{player}: [{(' '.join(g.tiles))}]")
        self._cards[4].update_value(" ".join(parts))
    else:
        self._cards[4].update_value("-")
    # 分数
    if state.scores:
        player_map = {"self": "自", "right": "右", "opposite": "对", "left": "左"}
        lines = []
        for key in ("self", "right", "opposite", "left"):
            label = player_map.get(key, key)
            score = state.scores.get(key, "?")
            lines.append(f"{label}: {score}")
        self._cards[5].update_value("  ".join(lines))
    else:
        self._cards[5].update_value("-")
    # 牌河
    if state.discards:
        player_map = {"self": "自", "right": "右", "opposite": "对", "left": "左"}
        lines = []
        for key in ("self", "right", "opposite", "left"):
            tiles = state.discards.get(key, [])
            label = player_map.get(key, key)
            lines.append(f"{label}: {' '.join(tiles) if tiles else '-'}")
        self._cards[6].update_value("\n".join(lines))
    else:
        self._cards[6].update_value("-")
    # 动作
    self._cards[7].update_value(" ".join(state.actions) if state.actions else "-")
    # 警告
    if state.warnings:
        self._cards[8].update_value(f"{len(state.warnings)}: {'; '.join(state.warnings)}")
    else:
        self._cards[8].update_value("0")
```

### 1.5 on_theme_changed 逻辑

```python
def on_theme_changed(self, theme: dict[str, str]) -> None:
    self._theme = theme
    # 更新面板容器背景
    self.configure(style="Panel.TFrame")
    # 更新标题行背景
    self._header_frame.configure(style="StatusBar.TFrame")
    # 更新分割线
    self._separator.configure(bg=theme["bg_surface0"])
    # 更新每个卡片的边框色和标签样式
    for card in self._cards:
        card.on_theme_changed(theme)
```

### 1.6 折叠/展开机制

- 面板通过 grid 放置在视图中: `grid(row=0, column=1, sticky="ns")`
- 折叠: 父视图 `columnconfigure(1, minsize=24)`，内部隐藏标题和卡片
- 展开: 父视图 `columnconfigure(1, minsize=240)`，恢复显示
- 折叠按钮始终可见

## 2. ImageCanvas — 空状态

### 2.1 新增方法

```python
def show_empty_state(self, hint_text: str) -> None:
    """显示空状态提示"""
    self.delete("all")
    self._photo = None
    cw = max(self.winfo_width(), self.winfo_reqwidth())
    ch = max(self.winfo_height(), self.winfo_reqheight())
    # 占位矩形
    rect_w, rect_h = 48, 36
    rx = (cw - rect_w) // 2
    ry = (ch - rect_h) // 2 - 12
    self.create_rectangle(rx, ry, rx + rect_w, ry + rect_h,
                          outline=self._theme["bg_surface0"], width=2)
    # 提示文字
    self.create_text(cw // 2, ry + rect_h + 16, text=hint_text,
                     fill=self._theme["fg_muted"], font=("", 11))

def clear(self) -> None:
    """清空画布（含空状态）"""
    self.delete("all")
    self._photo = None
    self._pending_image = None
```

**`show_image()` 自动清除空状态** — 已有 `self.delete("all")`，无需额外处理。

### 2.2 视图调用

各视图在 `__init__` 末尾和 `clear()` 后调用:
```python
# ScreenshotView
self._canvas.show_empty_state("拖放或点击加载截图")

# LiveView
self._canvas.show_empty_state("点击「开始」捕获窗口")

# DevView
self._zone_canvas.show_empty_state("在其他视图识别后切换查看")
self._det_canvas.show_empty_state("在其他视图识别后切换查看")
```

## 3. 测试更新要点

### 3.1 test_result_panel.py（完全重写）

```python
class TestResultPanelCards:
    def test_creates_section_cards(self, panel):
        """验证创建了 9 个 SectionCard"""
        assert len(panel._cards) == 9

    def test_update_state_none_shows_dash(self, panel):
        """state=None 时所有卡片显示 '-'"""
        panel.update_state(None)
        for card in panel._cards:
            assert card._value.cget("text") == "-"

    def test_update_state_shows_round_info(self, panel):
        state = _make_state()
        panel.update_state(state)
        assert "东1局" in panel._cards[0]._value.cget("text")

    def test_update_state_shows_hand(self, panel): ...
    def test_update_state_shows_scores(self, panel): ...
    def test_update_state_shows_discards(self, panel): ...
    def test_update_state_empty_hand_shows_dash(self, panel): ...
    def test_update_state_with_calls(self, panel): ...
    def test_update_state_with_warnings(self, panel): ...
    def test_on_theme_changed(self, panel): ...
    def test_rapid_update_no_widget_leak(self, panel):
        """快速连续调用 update_state 不增加 widget 数量"""
        state = _make_state()
        before = len(panel.winfo_children())
        for _ in range(10):
            panel.update_state(state)
        after = len(panel.winfo_children())
        assert before == after
```

### 3.2 test_image_canvas.py（新增）

```python
class TestImageCanvasEmptyState:
    def test_show_empty_state_draws_text(self, canvas):
        canvas.show_empty_state("测试提示")
        items = canvas.find_all()
        assert len(items) >= 2  # 矩形 + 文字

    def test_show_image_clears_empty_state(self, canvas):
        canvas.show_empty_state("提示")
        canvas.winfo_height = lambda: 300
        canvas.winfo_width = lambda: 400
        canvas.winfo_reqheight = lambda: 300
        canvas.winfo_reqwidth = lambda: 400
        canvas.show_image(np.full((200, 200, 3), 128, dtype=np.uint8))
        items = canvas.find_all()
        # show_image 的 delete("all") + create_image，无空状态元素
        assert canvas._photo is not None

    def test_clear_removes_empty_state(self, canvas):
        canvas.show_empty_state("提示")
        canvas.clear()
        assert canvas._photo is None
