"""LiveView 测试"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk
from unittest.mock import MagicMock

from majsoul_recognizer.gui.views.live_view import LiveView
from majsoul_recognizer.gui.theme import Theme


@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    yield root
    root.destroy()


@pytest.fixture
def mock_app_state():
    return MagicMock(
        engine=MagicMock(),
        pipeline_factory=lambda: MagicMock(),
        config=MagicMock(),
        theme_name="dark",
    )


@pytest.fixture
def on_result():
    return MagicMock()


@pytest.fixture
def view(tk_root, mock_app_state, on_result):
    v = LiveView(tk_root, mock_app_state, Theme.DARK, on_result=on_result)
    v.pack(fill="both", expand=True)
    tk_root.update_idletasks()
    yield v
    v.stop()


class TestLiveViewButtonStates:
    def test_initial_state_is_idle(self, view):
        assert view._state == "idle"

    def test_update_buttons_idle(self, view):
        view._update_buttons("idle")
        assert str(view._start_button.cget("state")) != "disabled"
        assert str(view._pause_button.cget("state")) == "disabled"
        assert str(view._reset_button.cget("state")) == "disabled"

    def test_update_buttons_capturing(self, view):
        view._update_buttons("capturing")
        assert str(view._start_button.cget("state")) == "disabled"
        assert str(view._pause_button.cget("state")) != "disabled"
        assert str(view._reset_button.cget("state")) == "disabled"

    def test_update_buttons_paused(self, view):
        view._update_buttons("paused")
        assert str(view._start_button.cget("state")) != "disabled"
        assert str(view._pause_button.cget("state")) == "disabled"
        assert str(view._reset_button.cget("state")) != "disabled"

    def test_update_buttons_reconnecting(self, view):
        view._update_buttons("reconnecting")
        assert str(view._start_button.cget("state")) == "disabled"
        assert str(view._pause_button.cget("state")) == "disabled"
        assert str(view._reset_button.cget("state")) != "disabled"


class TestLiveViewLifecycle:
    def test_stop_without_start_is_safe(self, view):
        view.stop()

    def test_on_theme_changed(self, view):
        view.on_theme_changed(Theme.LIGHT)
        assert view._theme is Theme.LIGHT
