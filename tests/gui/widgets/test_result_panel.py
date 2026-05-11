"""ResultPanel card-based tests"""

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


class TestResultPanelCards:
    def test_creates_9_cards(self, panel):
        assert len(panel._cards) == 9

    def test_none_shows_dash(self, panel):
        panel.update_state(None)
        for card in panel._cards:
            assert card._value.cget("text") == "-"

    def test_shows_round_info(self, panel):
        panel.update_state(_make_state())
        assert "东1局" in panel._cards[0]._value.cget("text")

    def test_shows_hand(self, panel):
        panel.update_state(_make_state())
        val = panel._cards[2]._value.cget("text")
        assert "1m" in val and "4p" in val

    def test_shows_scores(self, panel):
        panel.update_state(_make_state())
        assert "25000" in panel._cards[5]._value.cget("text")

    def test_shows_discards(self, panel):
        panel.update_state(_make_state())
        assert "6m" in panel._cards[6]._value.cget("text")

    def test_empty_hand_dash(self, panel):
        state = _make_state(hand=[], drawn_tile=None, dora_indicators=[],
                            discards={}, scores={})
        panel.update_state(state)
        assert panel._cards[2]._value.cget("text") == "-"
        assert panel._cards[1]._value.cget("text") == "-"

    def test_with_calls(self, panel):
        state = _make_state(
            calls={"self": [CallGroup(type="pon", tiles=["1m", "1m", "1m"],
                                       from_player="right")]}
        )
        panel.update_state(state)
        assert "1m" in panel._cards[4]._value.cget("text")

    def test_with_warnings(self, panel):
        panel.update_state(_make_state(warnings=["low_confidence"]))
        val = panel._cards[8]._value.cget("text")
        assert "1" in val

    def test_on_theme_changed(self, panel):
        panel.on_theme_changed(Theme.LIGHT)
        assert panel._theme is Theme.LIGHT

    def test_rapid_update_no_widget_leak(self, panel):
        state = _make_state()
        before = len(panel.winfo_children())
        for _ in range(10):
            panel.update_state(state)
        after = len(panel.winfo_children())
        assert before == after
