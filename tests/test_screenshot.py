"""屏幕截图测试"""

import numpy as np
import pytest

from majsoul_recognizer.capture.screenshot import ScreenCapture, create_capture
from majsoul_recognizer.capture.finder import WindowInfo


class TestScreenCapture:
    @pytest.fixture
    def capture(self):
        return create_capture()

    def test_create_capture_returns_instance(self, capture):
        assert isinstance(capture, ScreenCapture)

    def test_capture_from_window_info(self, capture):
        fake_info = WindowInfo(title="test", x=0, y=0, width=100, height=100)
        result = capture.capture_window(fake_info)
        if result is not None:
            assert isinstance(result, np.ndarray)
            assert result.shape[2] == 3

    def test_capture_has_capture_method(self, capture):
        assert hasattr(capture, "capture_window")


class TestCreateCapture:
    def test_factory_creates_capture(self):
        capture = create_capture()
        assert capture is not None
