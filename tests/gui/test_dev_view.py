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

        info_text = view._status_info.cget("text")
        assert "帧: 1" in info_text

    def test_start_is_noop_without_data(self, view):
        view.start()

    def test_stop_is_safe(self, view):
        view.stop()


class TestDevViewComputeZoneRects:
    """[C3/C4] _compute_zone_rects 应使用 .values() 并从 zone_config_path 读取"""

    def test_returns_empty_when_no_config_path(self, view):
        """zone_config_path 为 None 时返回空字典"""
        view._app_state.zone_config_path = None
        result = view._compute_zone_rects(1920, 1080)
        assert result == {}

    def test_returns_empty_on_invalid_path(self, view):
        """无效路径时返回空字典（异常被捕获）"""
        view._app_state.zone_config_path = "/nonexistent/zones.yaml"
        result = view._compute_zone_rects(1920, 1080)
        assert result == {}

    def test_computes_rects_from_zone_config(self, view, mock_app_state):
        """[C3] 正确遍历 .values() 生成区域矩形"""
        from pathlib import Path
        from unittest.mock import patch, MagicMock

        from majsoul_recognizer.types import ZoneName

        mock_zone_config = MagicMock()
        mock_zd = MagicMock()
        mock_zd.name = ZoneName("hand")
        mock_zd.to_bbox.return_value = MagicMock(x=10, y=20, width=100, height=50)
        mock_zone_config.zones = {ZoneName("hand"): mock_zd}

        view._app_state.zone_config_path = Path("/fake/zones.yaml")
        with patch("majsoul_recognizer.zones.config.load_zone_config", return_value=mock_zone_config):
            result = view._compute_zone_rects(1920, 1080)

        assert "hand" in result
        assert result["hand"] == (10, 20, 100, 50)
