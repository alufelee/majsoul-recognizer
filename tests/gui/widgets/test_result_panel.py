"""ResultPanel 测试 — 需要 tkinter。无 tkinter 环境自动跳过。"""

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
        assert "3s" in content

    def test_update_state_shows_hand(self, panel):
        state = _make_state()
        panel.update_state(state)
        content = panel._text.get("1.0", "end")
        assert "1m" in content
        assert "5p" in content

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
        assert "1" in content

    def test_update_state_with_latency(self, panel):
        state = _make_state()
        panel.update_state(state, latency_ms=180.5)
        content = panel._text.get("1.0", "end")
        assert "180" in content

    def test_on_theme_changed(self, panel):
        panel.on_theme_changed(Theme.LIGHT)
        assert panel._theme is Theme.LIGHT
