# Task: result_panel.py — 卡片式重写

## 文件
- 重写: `src/majsoul_recognizer/gui/widgets/result_panel.py`
- 重写: `tests/gui/widgets/test_result_panel.py`

## 外部 API (不变)

```python
class ResultPanel(ttk.Frame):
    def __init__(self, parent, theme: dict[str, str], **kwargs): ...
    def update_state(self, state: GameState | None, latency_ms: float = 0) -> None: ...
    def on_theme_changed(self, theme: dict[str, str]) -> None: ...
```

## 内部结构

### SectionCard (9个，创建一次)

| # | 标签 | 颜色 token | 数据源 |
|---|------|-----------|--------|
| 0 | 局次 | `blue` | round_info |
| 1 | 宝牌 | `blue` | dora_indicators |
| 2 | 手牌 | `green` | hand |
| 3 | 摸牌 | `green` | drawn_tile |
| 4 | 副露 | `yellow` | calls |
| 5 | 分数 | `mauve` | scores |
| 6 | 牌河 | `teal` | discards |
| 7 | 动作 | `peach` | actions |
| 8 | 警告 | `red` | warnings |

### _SectionCard 结构

```
┌──────────────────────┐
│▌ 局次                │  ← CardLabel.TLabel (9px, 区域色)
│▌ 东一局 0本场 0供托   │  ← CardValue.TLabel (11px, fg_primary)
└──────────────────────┘
```

- 容器: ttk.Frame(style="Card.TFrame")
- 左边框: tk.Canvas(width=2, fill=区域色)
- 内边距: padx=(8,6), pady=6
- 卡片间距: pady=3
- 无数据: 值显示 "-" (fg_muted)

### 面板容器

- 背景 bg_mantle, 宽度 240px
- 顶部标题 "识别结果" + 折叠按钮
- 左侧 1px bg_surface0 分割线

## update_state 核心逻辑

```python
def update_state(self, state, latency_ms=0):
    if state is None:
        for card in self._cards: card.update_value("-")
        return
    # 按上表逐一更新每个卡片的值
```

## 测试 (完全重写)

```python
class TestResultPanelCards:
    def test_creates_9_cards(self, panel): ...
    def test_none_shows_dash(self, panel): ...
    def test_shows_round_info(self, panel): ...
    def test_shows_hand(self, panel): ...
    def test_shows_scores(self, panel): ...
    def test_shows_discards(self, panel): ...
    def test_empty_hand_dash(self, panel): ...
    def test_with_calls(self, panel): ...
    def test_with_warnings(self, panel): ...
    def test_on_theme_changed(self, panel): ...
    def test_rapid_update_no_widget_leak(self, panel): ...
```
