"""截图捕获模块"""

from majsoul_recognizer.capture.finder import WindowFinder, WindowInfo, create_finder
from majsoul_recognizer.capture.screenshot import ScreenCapture, create_capture
from majsoul_recognizer.capture.frame import FrameChecker

__all__ = [
    "WindowFinder", "WindowInfo", "create_finder",
    "ScreenCapture", "create_capture",
    "FrameChecker",
]
