"""帧状态检测测试"""

import numpy as np
import pytest

from majsoul_recognizer.capture.frame import FrameChecker


class TestFrameChecker:
    @pytest.fixture
    def checker(self):
        return FrameChecker(threshold=0.02)

    def test_identical_frames_are_static(self, checker):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        assert checker.is_static(frame) is True

    def test_slightly_different_frames_are_static(self, checker):
        frame1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame2 = frame1.copy()
        frame2[0:50, 0:50] = 10
        assert checker.is_static(frame2) is True

    def test_very_different_frames_are_animated(self, checker):
        frame1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame2 = np.ones((1080, 1920, 3), dtype=np.uint8) * 128
        checker.is_static(frame1)
        assert checker.is_static(frame2) is False

    def test_first_frame_is_always_static(self, checker):
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        assert checker.is_static(frame) is True

    def test_threshold_customization(self):
        strict_checker = FrameChecker(threshold=0.001)
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = frame1.copy()
        frame2[0:5, 0:5] = 50
        strict_checker.is_static(frame1)
        assert strict_checker.is_static(frame2) is False

    def test_reset(self, checker):
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        checker.is_static(frame1)
        checker.reset()
        frame2 = np.ones((100, 100, 3), dtype=np.uint8) * 200
        assert checker.is_static(frame2) is True
