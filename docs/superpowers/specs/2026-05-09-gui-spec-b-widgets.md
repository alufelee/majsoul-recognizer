# GUI 子规格 B — 组件层

> 日期: 2026-05-09
> 主设计文档: `docs/superpowers/specs/2026-05-08-gui-design.md`（以下简称"主文档"）
> 本文档为主文档的切片，仅包含 widgets 层模块的详细设计。
> 前置依赖: 子规格 A（基础设施）已完成。

## 涵盖范围

| 模块 | 文件 | 对应主文档章节 |
|------|------|--------------|
| 图像画布 | `gui/widgets/image_canvas.py` | §3.10 |
| 结果面板 | `gui/widgets/result_panel.py` | §3.11 |

## 1. widgets 包结构

```
src/majsoul_recognizer/gui/widgets/
├── __init__.py
├── image_canvas.py       # 图像显示 + 检测框 + 区域标注
└── result_panel.py       # 识别结果文字面板
```

## 2. `widgets/image_canvas.py` — 图像画布

**职责**: 在 Tkinter Canvas 上显示图像，支持区域标注和检测框叠加。

```python
class ImageCanvas(tk.Canvas):
    """图像显示画布"""

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, bg=theme["canvas_bg"], **kwargs)
        self._theme = theme
        self._photo: ImageTk.PhotoImage | None = None
        self._detections: list[Detection] = []
        self._zone_rects: dict[str, tuple] = {}
        self._show_boxes: bool = True
        self._show_confidence: bool = True
        self._mode: str = "detection"  # "detection" | "zones"
        self._pending_image: np.ndarray | None = None
        self.bind("<Configure>", self._on_configure)
```

**核心方法**:

```python
def show_image(self, image: np.ndarray) -> None:
    """显示 BGR 图像（自动缩放适应画布尺寸）"""
    h, w = image.shape[:2]
    ch = max(self.winfo_height(), self.winfo_reqheight())
    cw = max(self.winfo_width(), self.winfo_reqwidth())
    if ch <= 1 or cw <= 1:
        self._pending_image = image
        return
    scale = min(cw / w, ch / h, 1.0)
    new_w, new_h = int(w * scale), int(h * scale)

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb).resize((new_w, new_h), Image.LANCZOS)
    self._photo = ImageTk.PhotoImage(pil_img)

    self.delete("all")
    x_offset = (cw - new_w) // 2
    y_offset = (ch - new_h) // 2
    self.create_image(x_offset, y_offset, anchor="nw", image=self._photo)
    self._scale = scale
    self._offset = (x_offset, y_offset)

    if self._mode == "zones":
        self._draw_zones()
    else:
        self._draw_detections()

def set_detections(self, detections: list[Detection]) -> None:
    """设置检测框数据"""

def set_zones(self, zone_rects: dict[str, tuple], colors: dict[str, str]) -> None:
    """设置区域矩形 {name: (x, y, w, h) 像素坐标}"""

def set_mode(self, mode: str) -> None:
    """切换叠加模式: "detection" | "zones" """

def on_theme_changed(self, theme: dict[str, str]) -> None:
    """主题切换时更新背景色"""
    self._theme = theme
    self.configure(bg=theme["canvas_bg"])

def clear(self) -> None:
    """清空画布"""
    self.delete("all")
    self._photo = None
    self._pending_image = None

def _on_configure(self, event) -> None:
    """窗口 resize 时重绘缓存的图像"""
    if self._pending_image is not None:
        self.show_image(self._pending_image)
```

**P3 坐标转换** — 核心绘制逻辑:

```python
def _to_canvas_coords(self, x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
    """原始图像坐标 → Canvas 坐标（考虑缩放和偏移）"""
    ox, oy = self._offset
    s = self._scale
    return (int(x * s) + ox, int(y * s) + oy,
            int((x + w) * s) + ox, int((y + h) * s) + oy)

def _draw_detections(self) -> None:
    """绘制检测框"""
    if self._photo is None:
        return
    for det in self._detections:
        x1, y1, x2, y2 = self._to_canvas_coords(
            det.bbox.x, det.bbox.y, det.bbox.width, det.bbox.height
        )
        color = _TILE_CATEGORY_COLORS.get(_get_tile_category(det.tile_code), "#9e9e9e")
        self.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
        label = f"{det.tile_code} ({det.confidence:.0%})" if self._show_confidence else det.tile_code
        self.create_text(x1, y1 - 4, anchor="sw", text=label,
                        fill=color, font=("Arial", 9))

def _draw_zones(self) -> None:
    """绘制区域标注"""
    if self._photo is None:
        return
    for name, (x, y, w, h) in self._zone_rects.items():
        x1, y1, x2, y2 = self._to_canvas_coords(x, y, w, h)
        color = self._zone_colors.get(name, "#ffffff")
        self.create_rectangle(x1, y1, x2, y2, outline=color, width=2, dash=(4, 4))
        self.create_text(x1 + 4, y1 + 2, anchor="nw", text=name,
                        fill=color, font=("Arial", 9))
```

**检测框颜色方案**:
```python
_TILE_CATEGORY_COLORS = {
    "m": "#4caf50",    # 万子 - 绿
    "p": "#2196f3",    # 筒子 - 蓝
    "s": "#f44336",    # 索子 - 红
    "z": "#9c27b0",    # 字牌 - 紫
    "r": "#ff9800",    # 赤宝牌 - 橙
    "x": "#9e9e9e",    # 特殊 - 灰
}

# [C1 修复] tile_code → 类别字母的映射
def _get_tile_category(tile_code: str) -> str:
    """将 tile_code 映射为类别字母，用于检测框着色

    映射规则（与 _DEFAULT_CLASS_MAP 一致）:
      5mr/5pr/5sr → "r" (赤宝牌)
      back/rotated/dora_frame → "x" (特殊)
      1m-9m → "m", 1p-9p → "p", 1s-9s → "s" (数字牌)
      1z-7z → "z" (字牌)
    """
    if tile_code in ("5mr", "5pr", "5sr"):
        return "r"
    if tile_code in ("back", "rotated", "dora_frame"):
        return "x"
    suffix = tile_code[-1:]
    if suffix in ("m", "p", "s"):
        return suffix
    # 1z-7z (东南西北白发中) — 最后一个字符是 z
    if suffix == "z":
        return "z"
    return "x"  # 未知类别归入特殊
```

**区域颜色方案** (DevView 使用):
```python
ZONE_COLORS = {
    "hand": "#4caf50",           # 绿
    "dora": "#ff9800",           # 橙
    "round_info": "#2196f3",     # 蓝
    "score_self": "#9c27b0",     # 紫
    "score_right": "#9c27b0",
    "score_opposite": "#9c27b0",
    "score_left": "#9c27b0",
    "discards_self": "#00bcd4",  # 青
    "discards_right": "#00bcd4",
    "discards_opposite": "#00bcd4",
    "discards_left": "#00bcd4",
    "calls_self": "#e91e63",     # 粉
    "actions": "#ff5722",        # 深橙
    "timer": "#607d8b",          # 蓝灰
}
```

**图像转换链**:
- `cv2` BGR ndarray → `cv2.cvtColor(BGR2RGB)` → `PIL.Image.fromarray` → `ImageTk.PhotoImage`
- 缩放使用 `PIL.Image.resize()` 的 `LANCZOS` 算法
- `show_image()` 时转换，不在实时循环中重复转换

**关键边界处理**:
- L2: `winfo_height/width` 在窗口映射前返回 1，使用 `reqwidth` 回退
- P5: 缓存图像，等 `Configure` 事件重绘

## 3. `widgets/result_panel.py` — 结果面板

**职责**: 以结构化文字展示 GameState 各字段。

```python
class ResultPanel(ttk.Frame):
    """识别结果面板"""

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, **kwargs)
        self._theme = theme
        import sys
        mono = "Menlo" if sys.platform == "darwin" else "Consolas"
        self._text = tk.Text(self, wrap="word", state="disabled",
                             font=(mono, 11),
                             bg=theme["bg_secondary"],
                             fg=theme["fg_primary"])
        self._text.tag_configure("label", foreground=theme["fg_secondary"])
        self._text.tag_configure("value", foreground=theme["fg_primary"])
        self._text.tag_configure("highlight", foreground=theme["highlight"])
        self._text.tag_configure("warning", foreground=theme["warning"])
        self._text.tag_configure("muted", foreground=theme["fg_muted"])

    def update_state(self, state: GameState | None, latency_ms: float = 0) -> None:
        """更新识别结果"""
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        if state is None:
            self._text.insert("end", "非静态帧 — 识别跳过", "muted")
        else:
            self._render_state(state, latency_ms)
        self._text.config(state="disabled")

    def on_theme_changed(self, theme: dict[str, str]) -> None:
        """主题切换"""
        self._theme = theme
        self._text.configure(bg=theme["bg_secondary"], fg=theme["fg_primary"])
        self._text.tag_configure("label", foreground=theme["fg_secondary"])
        self._text.tag_configure("value", foreground=theme["fg_primary"])
        self._text.tag_configure("highlight", foreground=theme["highlight"])
        self._text.tag_configure("warning", foreground=theme["warning"])
        self._text.tag_configure("muted", foreground=theme["fg_muted"])

    # [C2 修复] _render_state 完整实现
    def _render_state(self, state: GameState, latency_ms: float = 0) -> None:
        """渲染 GameState 各字段，使用 Text 标签实现彩色输出"""
        t = self._text
        SEP = "─" * 30 + "\n"

        # 局次
        if state.round_info:
            ri = state.round_info
            t.insert("end", "局次: ", "label")
            t.insert("end", f"{ri.wind}{ri.number}局 {ri.honba}本场 {ri.kyotaku}供托\n", "value")
        else:
            t.insert("end", "局次: ", "label")
            t.insert("end", "-\n", "muted")

        # 宝牌
        t.insert("end", "宝牌: ", "label")
        t.insert("end", (" ".join(state.dora_indicators) if state.dora_indicators else "-"), "value")
        t.insert("end", "\n")
        t.insert("end", SEP)

        # 手牌
        t.insert("end", "手牌: ", "label")
        t.insert("end", (" ".join(state.hand) if state.hand else "-"), "value")
        t.insert("end", "\n")

        # 摸牌
        if state.drawn_tile is not None:
            t.insert("end", "摸牌: ", "label")
            t.insert("end", f"{state.drawn_tile}\n", "highlight")
        t.insert("end", SEP)

        # 副露
        t.insert("end", "副露: ", "label")
        if state.calls:
            parts = []
            for player, groups in state.calls.items():
                for g in groups:
                    tiles_str = " ".join(g.tiles)
                    parts.append(f"{player}: [{tiles_str}]")
            t.insert("end", " ".join(parts), "value")
        else:
            t.insert("end", "-", "muted")
        t.insert("end", "\n")
        t.insert("end", SEP)

        # 分数
        t.insert("end", "分数:\n", "label")
        if state.scores:
            player_map = {"self": "自", "right": "右", "opposite": "对", "left": "左"}
            line1 = "  "
            for key in ("self", "right"):
                label = player_map.get(key, key)
                score = state.scores.get(key, "?")
                line1 += f"{label}: {score}  "
            t.insert("end", line1.rstrip() + "\n", "value")
            line2 = "  "
            for key in ("opposite", "left"):
                label = player_map.get(key, key)
                score = state.scores.get(key, "?")
                line2 += f"{label}: {score}  "
            t.insert("end", line2.rstrip() + "\n", "value")
        else:
            t.insert("end", "  -\n", "muted")
        t.insert("end", SEP)

        # 牌河
        t.insert("end", "牌河:\n", "label")
        if state.discards:
            player_map = {"self": "自", "right": "右", "opposite": "对", "left": "左"}
            for key in ("self", "right", "opposite", "left"):
                tiles = state.discards.get(key, [])
                label = player_map.get(key, key)
                t.insert("end", f"  {label}: ", "label")
                t.insert("end", (" ".join(tiles) if tiles else "-"), "value")
                t.insert("end", "\n")
        else:
            t.insert("end", "  -\n", "muted")
        t.insert("end", SEP)

        # 动作
        t.insert("end", "动作: ", "label")
        t.insert("end", (" ".join(state.actions) if state.actions else "-"), "value")
        t.insert("end", "\n")

        # 延迟
        if latency_ms > 0:
            t.insert("end", "延迟: ", "label")
            t.insert("end", f"{latency_ms:.0f}ms\n", "value")

        # 警告
        t.insert("end", "警告: ", "label")
        if state.warnings:
            t.insert("end", f"{len(state.warnings)}\n", "warning")
            for w in state.warnings:
                t.insert("end", f"  {w}\n", "warning")
        else:
            t.insert("end", "0\n", "value")
```

**显示格式**（使用 Text 标签实现彩色）:
```
局次: 东一局 0本场 0供托
宝牌: 3s
────────────────
手牌: 1m 2m 3m 4m 5m 6m 7m 8m 9m 1p 2p 3p
摸牌: 4p                   ← highlight 颜色
────────────────
副露: -
────────────────
分数:
  自: 25000  右: 25000
  对: 25000  左: 25000
────────────────
牌河:
  自: 1m 2m 3m
  右: 4p 5p
  对: 6s 7s
  左: 1z 2z
────────────────
动作: -
延迟: 180ms
警告: 0
```

**P6 字体**: 单一字体名 + 平台检测，不支持 Tkinter fallback 列表:
```python
import sys
_MONO_FONT = "Menlo" if sys.platform == "darwin" else "Consolas"
```

## 4. 需要参考的现有代码

| 文件 | 用途 |
|------|------|
| `src/majsoul_recognizer/types.py` | Detection, BBox, GameState, ZoneName |
| `src/majsoul_recognizer/cli.py` | `format_output()` 输出格式参考 |
