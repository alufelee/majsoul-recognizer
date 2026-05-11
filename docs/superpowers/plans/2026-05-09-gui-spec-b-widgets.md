# GUI 组件层实施计划 (Spec B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 GUI 组件层：牌面颜色映射、图像画布（检测框+区域标注）、结果面板。

**Architecture:** 将纯逻辑（颜色映射、tile_code 分类）提取到独立模块 `colors.py`，无 tkinter 依赖可全平台测试。ImageCanvas 和 ResultPanel 是 tkinter widget，测试通过 `pytest.importorskip("tkinter")` 自动跳过无 tkinter 环境。

**Tech Stack:** Python 3.10+, tkinter, Pillow, OpenCV, pytest

**设计文档:** `docs/superpowers/specs/2026-05-09-gui-spec-b-widgets.md`

**前置依赖:** Spec A 计划已完成（`gui/` 包、theme、settings、worker、base_view 存在）

**依赖的现有代码:**
- `src/majsoul_recognizer/types.py` — `Detection, BBox, GameState, ZoneName, RoundInfo, CallGroup`
- `src/majsoul_recognizer/gui/theme.py` — `Theme, get_theme`（Spec A Task 2）

---

## File Structure

```
src/majsoul_recognizer/gui/widgets/
├── __init__.py
├── colors.py             # 纯逻辑：牌面颜色 + 区域颜色 + _get_tile_category
├── image_canvas.py       # ImageCanvas(tk.Canvas) — 图像显示+检测框+区域标注
└── result_panel.py       # ResultPanel(ttk.Frame) — 识别结果文字面板

tests/gui/widgets/
├── __init__.py
├── test_colors.py        # 纯逻辑测试，无 tkinter 依赖
├── test_image_canvas.py  # tkinter widget 测试（自动跳过）
└── test_result_panel.py  # tkinter widget 测试（自动跳过）
```

---

### Task 1: 纯逻辑 — colors.py 牌面颜色映射

**Files:**
- Create: `src/majsoul_recognizer/gui/widgets/__init__.py`
- Create: `src/majsoul_recognizer/gui/widgets/colors.py`
- Create: `tests/gui/widgets/__init__.py`
- Create: `tests/gui/widgets/test_colors.py`

- [ ] **Step 1: 创建包骨架**

```bash
mkdir -p src/majsoul_recognizer/gui/widgets tests/gui/widgets
touch src/majsoul_recognizer/gui/widgets/__init__.py
touch tests/gui/widgets/__init__.py
```

- [ ] **Step 2: 编写 colors 纯逻辑测试**

`tests/gui/widgets/test_colors.py`:
```python
"""牌面颜色映射测试 — 纯逻辑，无 tkinter 依赖"""

from majsoul_recognizer.gui.widgets.colors import (
    ZONE_COLORS,
    _TILE_CATEGORY_COLORS,
    _get_tile_category,
)


class TestGetTileCategory:
    """tile_code → 类别字母映射"""

    def test_manpin(self):
        """万子"""
        for i in range(1, 10):
            assert _get_tile_category(f"{i}m") == "m"

    def test_pin(self):
        """筒子"""
        for i in range(1, 10):
            assert _get_tile_category(f"{i}p") == "p"

    def test_sou(self):
        """索子"""
        for i in range(1, 10):
            assert _get_tile_category(f"{i}s") == "s"

    def test_honor(self):
        """字牌 1z-7z"""
        for i in range(1, 8):
            assert _get_tile_category(f"{i}z") == "z"

    def test_red_dora(self):
        """赤宝牌"""
        assert _get_tile_category("5mr") == "r"
        assert _get_tile_category("5pr") == "r"
        assert _get_tile_category("5sr") == "r"

    def test_special(self):
        """特殊牌"""
        assert _get_tile_category("back") == "x"
        assert _get_tile_category("rotated") == "x"
        assert _get_tile_category("dora_frame") == "x"

    def test_unknown(self):
        """未知类别归入特殊"""
        assert _get_tile_category("unknown") == "x"
        assert _get_tile_category("") == "x"


class TestTileCategoryColors:
    def test_all_categories_have_colors(self):
        """每个类别字母都有对应颜色"""
        for cat in ("m", "p", "s", "z", "r", "x"):
            assert cat in _TILE_CATEGORY_COLORS

    def test_colors_are_hex(self):
        for key, value in _TILE_CATEGORY_COLORS.items():
            assert value.startswith("#"), f"{key} = {value!r}"
            assert len(value) == 7, f"{key} = {value!r}"


class TestZoneColors:
    def test_zone_colors_is_dict(self):
        assert isinstance(ZONE_COLORS, dict)
        assert len(ZONE_COLORS) > 0

    def test_zone_colors_are_hex(self):
        for key, value in ZONE_COLORS.items():
            assert value.startswith("#"), f"{key} = {value!r}"
            assert len(value) == 7, f"{key} = {value!r}"
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/gui/widgets/test_colors.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: 实现 `gui/widgets/colors.py`**

```python
"""牌面颜色映射 + 区域颜色方案

纯逻辑模块，无 tkinter 依赖，可全平台测试。
"""

_TILE_CATEGORY_COLORS: dict[str, str] = {
    "m": "#4caf50",    # 万子 - 绿
    "p": "#2196f3",    # 筒子 - 蓝
    "s": "#f44336",    # 索子 - 红
    "z": "#9c27b0",    # 字牌 - 紫
    "r": "#ff9800",    # 赤宝牌 - 橙
    "x": "#9e9e9e",    # 特殊 - 灰
}


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
    if suffix == "z":
        return "z"
    return "x"


ZONE_COLORS: dict[str, str] = {
    "hand": "#4caf50",
    "dora": "#ff9800",
    "round_info": "#2196f3",
    "score_self": "#9c27b0",
    "score_right": "#9c27b0",
    "score_opposite": "#9c27b0",
    "score_left": "#9c27b0",
    "discards_self": "#00bcd4",
    "discards_right": "#00bcd4",
    "discards_opposite": "#00bcd4",
    "discards_left": "#00bcd4",
    "calls_self": "#e91e63",
    "actions": "#ff5722",
    "timer": "#607d8b",
}
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/gui/widgets/test_colors.py -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add src/majsoul_recognizer/gui/widgets/ tests/gui/widgets/
git commit -m "feat(gui): add tile color mapping and zone colors module"
```

---

### Task 2: ImageCanvas 图像画布

**Files:**
- Create: `src/majsoul_recognizer/gui/widgets/image_canvas.py`
- Create: `tests/gui/widgets/test_image_canvas.py`

注意: ImageCanvas 继承 `tk.Canvas`，需要 tkinter + Pillow。测试使用 `pytest.importorskip` 自动跳过。

- [ ] **Step 1: 编写 ImageCanvas 测试**

`tests/gui/widgets/test_image_canvas.py`:
```python
"""ImageCanvas 测试

需要 tkinter + Pillow。无 tkinter 环境自动跳过。
"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk
from unittest.mock import MagicMock, patch

import numpy as np

from majsoul_recognizer.gui.widgets.image_canvas import ImageCanvas
from majsoul_recognizer.gui.theme import Theme


@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    yield root
    root.destroy()


@pytest.fixture
def canvas(tk_root):
    c = ImageCanvas(tk_root, Theme.DARK, width=400, height=300)
    c.pack()
    tk_root.update_idletasks()
    return c


class TestImageCanvasBasic:
    def test_creation(self, canvas):
        assert canvas._mode == "detection"
        assert canvas._photo is None
        assert canvas._pending_image is None

    def test_clear(self, canvas):
        canvas._pending_image = np.zeros((10, 10, 3))
        canvas.clear()
        assert canvas._photo is None
        assert canvas._pending_image is None

    def test_set_mode(self, canvas):
        canvas.set_mode("zones")
        assert canvas._mode == "zones"
        canvas.set_mode("detection")
        assert canvas._mode == "detection"

    def test_on_theme_changed(self, canvas):
        canvas.on_theme_changed(Theme.LIGHT)
        assert canvas._theme is Theme.LIGHT


class TestImageCanvasShowImage:
    def test_show_image_stores_pending_when_unmapped(self, canvas):
        """窗口未映射时缓存图像"""
        # 强制 winfo 返回 1（未映射状态）
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        canvas.winfo_height = lambda: 1
        canvas.winfo_width = lambda: 1
        canvas.show_image(image)
        assert canvas._pending_image is not None

    def test_show_image_creates_photo(self, canvas):
        """正常尺寸时生成 PhotoImage"""
        # 给 canvas 实际尺寸
        canvas.winfo_height = lambda: 300
        canvas.winfo_width = lambda: 400
        canvas.winfo_reqheight = lambda: 300
        canvas.winfo_reqwidth = lambda: 400

        image = np.full((200, 200, 3), 128, dtype=np.uint8)
        canvas.show_image(image)
        assert canvas._photo is not None
        assert canvas._scale > 0


class TestImageCanvasDetections:
    def test_set_detections(self, canvas):
        """设置检测框数据"""
        from majsoul_recognizer.types import BBox, Detection
        det = Detection(
            bbox=BBox(x=10, y=20, width=30, height=40),
            tile_code="1m",
            confidence=0.95,
        )
        canvas.set_detections([det])
        assert len(canvas._detections) == 1
        assert canvas._detections[0].tile_code == "1m"

    def test_set_zones(self, canvas):
        """设置区域矩形"""
        from majsoul_recognizer.gui.widgets.colors import ZONE_COLORS
        zones = {"hand": (10, 20, 100, 50)}
        canvas.set_zones(zones, ZONE_COLORS)
        assert "hand" in canvas._zone_rects


class TestToCanvasCoords:
    def test_coordinate_transform(self, canvas):
        """坐标转换：原始坐标 → Canvas 坐标"""
        # 设置已知缩放参数
        canvas._scale = 0.5
        canvas._offset = (10, 20)
        x1, y1, x2, y2 = canvas._to_canvas_coords(100, 200, 50, 80)
        # x1 = int(100*0.5) + 10 = 60
        # y1 = int(200*0.5) + 20 = 120
        # x2 = int(150*0.5) + 10 = 85
        # y2 = int(280*0.5) + 20 = 160
        assert x1 == 60
        assert y1 == 120
        assert x2 == 85
        assert y2 == 160
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/gui/widgets/test_image_canvas.py -v`
Expected: FAIL — `ModuleNotFoundError`（或 SKIP "tkinter not available"）

- [ ] **Step 3: 实现 `gui/widgets/image_canvas.py`**

```python
"""图像显示画布

在 Tkinter Canvas 上显示图像，支持检测框和区域标注叠加。
"""

from __future__ import annotations

import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk

from majsoul_recognizer.gui.widgets.colors import (
    ZONE_COLORS,
    _TILE_CATEGORY_COLORS,
    _get_tile_category,
)


class ImageCanvas(tk.Canvas):
    """图像显示画布"""

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, bg=theme["canvas_bg"], **kwargs)
        self._theme = theme
        self._photo: ImageTk.PhotoImage | None = None
        self._detections: list = []
        self._zone_rects: dict[str, tuple] = {}
        self._zone_colors: dict[str, str] = {}
        self._show_boxes: bool = True
        self._show_confidence: bool = True
        self._mode: str = "detection"  # "detection" | "zones"
        self._pending_image: np.ndarray | None = None
        self._scale: float = 1.0
        self._offset: tuple[int, int] = (0, 0)
        self.bind("<Configure>", self._on_configure)

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

    def set_detections(self, detections: list) -> None:
        """设置检测框数据"""
        self._detections = detections

    def set_zones(self, zone_rects: dict[str, tuple], colors: dict[str, str]) -> None:
        """设置区域矩形 {name: (x, y, w, h) 像素坐标}"""
        self._zone_rects = zone_rects
        self._zone_colors = colors

    def set_mode(self, mode: str) -> None:
        """切换叠加模式: "detection" | "zones" """
        self._mode = mode

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

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/gui/widgets/test_image_canvas.py -v`
Expected: 全部 PASS，或 SKIP "tkinter not available"

- [ ] **Step 5: Commit**

```bash
git add src/majsoul_recognizer/gui/widgets/image_canvas.py tests/gui/widgets/test_image_canvas.py
git commit -m "feat(gui): add ImageCanvas with detection boxes and zone overlays"
```

---

### Task 3: ResultPanel 结果面板

**Files:**
- Create: `src/majsoul_recognizer/gui/widgets/result_panel.py`
- Create: `tests/gui/widgets/test_result_panel.py`

- [ ] **Step 1: 编写 ResultPanel 测试**

`tests/gui/widgets/test_result_panel.py`:
```python
"""ResultPanel 测试

需要 tkinter。无 tkinter 环境自动跳过。
"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk

from majsoul_recognizer.gui.theme import Theme
from majsoul_recognizer.gui.widgets.result_panel import ResultPanel
from majsoul_recognizer.types import GameState, RoundInfo, CallGroup


@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    yield root
    root.destroy()


@pytest.fixture
def panel(tk_root):
    p = ResultPanel(tk_root, Theme.DARK)
    p.pack(fill="both", expand=True)
    tk_root.update_idletasks()
    return p


def _make_state(**overrides) -> GameState:
    defaults = {
        "round_info": RoundInfo(wind="东", number=1, honba=0, kyotaku=0),
        "dora_indicators": ["3s"],
        "hand": ["1m", "2m", "3m", "4p"],
        "drawn_tile": "5p",
        "scores": {"self": 25000, "right": 25000, "opposite": 25000, "left": 25000},
        "discards": {"self": ["6m", "7m"], "right": ["1p"]},
        "calls": {},
        "actions": [],
        "warnings": [],
    }
    defaults.update(overrides)
    return GameState(**defaults)


class TestResultPanelBasic:
    def test_creation(self, panel):
        assert panel._text is not None

    def test_update_state_none_shows_muted(self, panel):
        panel.update_state(None)
        content = panel._text.get("1.0", "end")
        assert "非静态帧" in content

    def test_update_state_shows_round_info(self, panel):
        state = _make_state()
        panel.update_state(state)
        content = panel._text.get("1.0", "end")
        assert "东1局" in content
        assert "3s" in content  # dora

    def test_update_state_shows_hand(self, panel):
        state = _make_state()
        panel.update_state(state)
        content = panel._text.get("1.0", "end")
        assert "1m" in content
        assert "5p" in content  # drawn tile

    def test_update_state_shows_scores(self, panel):
        state = _make_state()
        panel.update_state(state)
        content = panel._text.get("1.0", "end")
        assert "25000" in content

    def test_update_state_shows_discards(self, panel):
        state = _make_state()
        panel.update_state(state)
        content = panel._text.get("1.0", "end")
        assert "6m" in content
        assert "7m" in content

    def test_update_state_empty_hand(self, panel):
        state = _make_state(hand=[], drawn_tile=None, dora_indicators=[], discards={}, scores={})
        panel.update_state(state)
        content = panel._text.get("1.0", "end")
        assert "-" in content

    def test_update_state_with_calls(self, panel):
        state = _make_state(
            calls={"self": [CallGroup(type="pon", tiles=["1m", "1m", "1m"], from_player="right")]}
        )
        panel.update_state(state)
        content = panel._text.get("1.0", "end")
        assert "pon" in content or "1m" in content

    def test_update_state_with_warnings(self, panel):
        state = _make_state(warnings=["low_confidence"])
        panel.update_state(state)
        content = panel._text.get("1.0", "end")
        assert "1" in content  # warning count

    def test_update_state_with_latency(self, panel):
        state = _make_state()
        panel.update_state(state, latency_ms=180.5)
        content = panel._text.get("1.0", "end")
        assert "180" in content

    def test_on_theme_changed(self, panel):
        panel.on_theme_changed(Theme.LIGHT)
        assert panel._theme is Theme.LIGHT
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/gui/widgets/test_result_panel.py -v`
Expected: FAIL — `ModuleNotFoundError`（或 SKIP "tkinter not available"）

- [ ] **Step 3: 实现 `gui/widgets/result_panel.py`**

```python
"""识别结果面板

以结构化文字展示 GameState 各字段，使用 Text 标签实现彩色输出。
"""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.ttk as ttk

from majsoul_recognizer.types import GameState


class ResultPanel(ttk.Frame):
    """识别结果面板"""

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, **kwargs)
        self._theme = theme
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
        self._text.pack(fill="both", expand=True)

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

    def _render_state(self, state: GameState, latency_ms: float = 0) -> None:
        """渲染 GameState 各字段"""
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

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/gui/widgets/test_result_panel.py -v`
Expected: 全部 PASS，或 SKIP "tkinter not available"

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `pytest tests/ -v --timeout=30`
Expected: 全部 PASS（含 Spec A + Spec B 测试）

- [ ] **Step 6: Commit**

```bash
git add src/majsoul_recognizer/gui/widgets/result_panel.py tests/gui/widgets/test_result_panel.py
git commit -m "feat(gui): add ResultPanel with colored GameState rendering"
```

---

## Self-Review

**1. Spec 覆盖率:**
| Spec B 章节 | 对应 Task | 状态 |
|-------------|----------|------|
| §2 ImageCanvas | Task 2 | ✅ |
| §2 检测框颜色方案 | Task 1 (colors.py) | ✅ |
| §2 区域颜色方案 | Task 1 (colors.py) | ✅ |
| §2 _get_tile_category | Task 1 (colors.py) | ✅ |
| §2 坐标转换 | Task 2 | ✅ |
| §2 图像转换链 | Task 2 (show_image) | ✅ |
| §3 ResultPanel | Task 3 | ✅ |
| §3 _render_state | Task 3 | ✅ |

**2. 占位符扫描:** 无 TBD/TODO。

**3. 类型一致性:**
- `ImageCanvas.show_image(image: np.ndarray)` — 与 ScreenshotView/LiveView 调用一致
- `ImageCanvas.set_detections(detections: list)` — 接受 `Detection` 列表，与 worker 输出一致
- `ImageCanvas.set_zones(zone_rects: dict, colors: dict)` — 与 DevView 调用一致
- `ResultPanel.update_state(state: GameState | None, latency_ms: float)` — 与视图回调一致
- `_get_tile_category(tile_code: str) -> str` — 与 `_TILE_CATEGORY_COLORS` 键一致
- `colors.py` 中的 `ZONE_COLORS` — 与 Spec C DevView 引用一致
