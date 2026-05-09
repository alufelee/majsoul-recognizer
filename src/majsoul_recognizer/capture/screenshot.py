"""屏幕截图

截取指定窗口的画面内容。
使用 mss 库作为跨平台截图方案。
"""

import logging

import cv2
import numpy as np
import mss

from majsoul_recognizer.capture.finder import WindowInfo

logger = logging.getLogger(__name__)


class ScreenCapture:
    """屏幕截图器"""

    def __init__(self):
        self._sct = mss.mss()

    def capture_window(self, window_info: WindowInfo) -> np.ndarray | None:
        try:
            monitor = {
                "left": window_info.x,
                "top": window_info.y,
                "width": window_info.width,
                "height": window_info.height,
            }
            screenshot = self._sct.grab(monitor)
            img = np.array(screenshot, dtype=np.uint8)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            logger.warning("Screenshot failed: %s", e)
            return None

    def capture_monitor(self, monitor_index: int = 0) -> np.ndarray | None:
        try:
            monitor = self._sct.monitors[monitor_index + 1]
            screenshot = self._sct.grab(monitor)
            img = np.array(screenshot, dtype=np.uint8)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            logger.warning("Monitor capture failed: %s", e)
            return None

    def close(self):
        self._sct.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def create_capture() -> ScreenCapture:
    return ScreenCapture()
