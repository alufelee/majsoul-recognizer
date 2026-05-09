"""DevView 测试"""

import json

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk
from unittest.mock import MagicMock

import numpy as np

from majsoul_recognizer.gui.views.dev_view import DevView
from majsoul_recognizer.gui.theme import Theme
from majsoul_recognizer.types import FrameResult, GameState, RoundInfo


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
def view(tk_root, mock_app_state):
    v = DevView(tk_root, mock_app_state, Theme.DARK)
    v.pack(fill="both", expand=True)
    tk_root.update_idletasks()
    yield v
    v.stop()


def _make_frame_result():
    return FrameResult(
        frame_id=1,
        timestamp="2026-05-09T00:00:00Z",
        zones={"hand": np.zeros((100, 100, 3), dtype=np.uint8)},
        is_static=True,
    )


def _make_game_state():
    return GameState(
        round_info=RoundInfo(wind="东", number=1, honba=0, kyotaku=0),
        hand=["1m", "2m"],
    )


class TestDevView:
    def test_creation(self, view):
        assert view._current_image is None

    def test_set_current_image(self, view):
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        view.set_current_image(image)
        assert view._current_image is not None

    def test_update_data_writes_json(self, view):
        view.set_current_image(np.zeros((200, 200, 3), dtype=np.uint8))
        frame = _make_frame_result()
        state = _make_game_state()
        view.update_data(frame, state)

        content = view._json_text.get("1.0", "end")
        data = json.loads(content)
        assert data["is_static"] is True
        assert data["frame_id"] == 1

    def test_update_data_with_detections(self, view):
        from majsoul_recognizer.types import BBox, Detection

        view.set_current_image(np.zeros((200, 200, 3), dtype=np.uint8))
        frame = _make_frame_result()
        dets = [
            Detection(bbox=BBox(x=10, y=20, width=30, height=40), tile_code="1m", confidence=0.95)
        ]
        view.update_data(frame, None, detections=dets)
        assert len(view._det_canvas._detections) == 1

    def test_update_data_shows_perf(self, view):
        view.set_current_image(np.zeros((200, 200, 3), dtype=np.uint8))
        frame = _make_frame_result()
        view.update_data(frame, None)

        perf_text = view._perf_label.cget("text")
        assert "帧: 1" in perf_text

    def test_start_is_noop_without_data(self, view):
        view.start()

    def test_stop_is_safe(self, view):
        view.stop()
