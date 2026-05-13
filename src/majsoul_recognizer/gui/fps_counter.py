"""FPS 计数器 — 纯逻辑模块，无 tkinter 依赖。线程安全。"""

from __future__ import annotations

import threading
import time


class FPSCounter:
    """简单 FPS 计数器（线程安全）"""

    def __init__(self, window: float = 1.0):
        self._window = window
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def tick(self) -> None:
        now = time.perf_counter()
        with self._lock:
            self._timestamps.append(now)
            cutoff = now - self._window
            self._timestamps = [t for t in self._timestamps if t > cutoff]

    @property
    def fps(self) -> float:
        with self._lock:
            if len(self._timestamps) < 2:
                return 0.0
            elapsed = self._timestamps[-1] - self._timestamps[0]
            return (len(self._timestamps) - 1) / elapsed if elapsed > 0 else 0.0
