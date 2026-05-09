"""FPSCounter 测试 — 纯逻辑，无 tkinter 依赖"""

import time

from majsoul_recognizer.gui.fps_counter import FPSCounter


class TestFPSCounter:
    def test_initial_fps_is_zero(self):
        counter = FPSCounter(window=1.0)
        assert counter.fps == 0.0

    def test_single_tick_fps_is_zero(self):
        counter = FPSCounter(window=1.0)
        counter.tick()
        assert counter.fps == 0.0

    def test_two_ticks_gives_nonzero_fps(self):
        counter = FPSCounter(window=1.0)
        counter.tick()
        time.sleep(0.05)
        counter.tick()
        assert counter.fps > 0.0

    def test_old_ticks_are_pruned(self):
        counter = FPSCounter(window=0.1)
        counter.tick()
        time.sleep(0.15)
        counter.tick()
        assert counter.fps == 0.0

    def test_multiple_ticks_in_window(self):
        counter = FPSCounter(window=1.0)
        for _ in range(5):
            counter.tick()
            time.sleep(0.02)
        assert counter.fps > 0.0
        assert counter.fps < 200.0
