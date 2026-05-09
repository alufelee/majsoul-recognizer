"""ScreenshotView 测试"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk
from unittest.mock import MagicMock, patch

import numpy as np

from majsoul_recognizer.gui.views.screenshot_view import ScreenshotView
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
    v = ScreenshotView(tk_root, mock_app_state, Theme.DARK, on_result=on_result)
    v.pack(fill="both", expand=True)
    tk_root.update_idletasks()
    yield v
    v.stop()


class TestScreenshotView:
    def test_creation(self, view):
        assert view._current_image is None
        assert view._is_busy is False

    def test_recognize_submits_to_worker(self, view):
        with patch.object(view, "_ensure_worker") as mock_ensure:
            mock_worker = MagicMock()
            mock_worker.submit.return_value = True
            mock_ensure.return_value = mock_worker

            image = np.zeros((100, 100, 3), dtype=np.uint8)
            view.recognize(image)

            mock_worker.submit.assert_called_once_with(image)
            assert view._is_busy is True

    def test_recognize_busy_rejects(self, view):
        view._is_busy = True
        with patch.object(view, "_ensure_worker") as mock_ensure:
            mock_worker = MagicMock()
            mock_worker.submit.return_value = False
            mock_ensure.return_value = mock_worker

            image = np.zeros((100, 100, 3), dtype=np.uint8)
            view.recognize(image)
            assert view._is_busy is True

    def test_stop_cleans_up(self, view, mock_app_state):
        with patch.object(view, "_ensure_worker"):
            view.stop()

    def test_on_theme_changed(self, view):
        view.on_theme_changed(Theme.LIGHT)
        assert view._theme is Theme.LIGHT
