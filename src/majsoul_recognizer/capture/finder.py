"""窗口发现

查找雀魂游戏窗口并获取窗口信息。
支持 macOS 和 Windows 平台。
"""

import platform
import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel

logger = logging.getLogger(__name__)

TARGET_KEYWORDS = ("Mahjong Soul", "雀魂", "majsoul")


class WindowInfo(BaseModel):
    """窗口基本信息"""
    model_config = {"frozen": True}

    title: str
    x: int
    y: int
    width: int
    height: int
    window_id: int | str | None = None

    @property
    def is_valid(self) -> bool:
        return self.width > 0 and self.height > 0


class WindowFinder(ABC):
    """窗口发现抽象基类"""

    def __init__(self, target_keywords: tuple[str, ...] = TARGET_KEYWORDS):
        self._target_keywords = target_keywords

    @property
    def target_keywords(self) -> tuple[str, ...]:
        return self._target_keywords

    @target_keywords.setter
    def target_keywords(self, value: tuple[str, ...]):
        self._target_keywords = value

    @abstractmethod
    def find_window(self) -> WindowInfo | None:
        ...

    @abstractmethod
    def list_windows(self) -> list[WindowInfo]:
        ...

    def _match_title(self, title: str) -> bool:
        title_lower = title.lower()
        return any(kw.lower() in title_lower for kw in self.target_keywords)


class MacOSWindowFinder(WindowFinder):
    def find_window(self) -> WindowInfo | None:
        try:
            import Quartz  # noqa: F401
        except ImportError:
            logger.warning("pyobjc not available, using fallback")
            return self._fallback_find()

        windows = self.list_windows()
        for win in windows:
            if self._match_title(win.title):
                return win
        return None

    def list_windows(self) -> list[WindowInfo]:
        try:
            from Quartz import (
                CGWindowListCopyWindowInfo,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
            )
        except ImportError:
            return []

        window_list = CGWindowListCopyWindowInfo(
            kCGWindowListOptionOnScreenOnly, kCGNullWindowID
        )
        result = []
        for win in window_list:
            bounds = win.get("kCGWindowBounds", {})
            if not bounds:
                continue
            w = int(bounds.get("Width", 0))
            h = int(bounds.get("Height", 0))
            if w <= 0 or h <= 0:
                continue
            result.append(WindowInfo(
                title=win.get("kCGWindowName", ""),
                x=int(bounds.get("X", 0)),
                y=int(bounds.get("Y", 0)),
                width=w,
                height=h,
                window_id=win.get("kCGWindowNumber"),
            ))
        return result

    def _fallback_find(self) -> WindowInfo | None:
        logger.warning("macOS window discovery requires pyobjc. Install with: pip install pyobjc-framework-Quartz")
        return None


class WindowsWindowFinder(WindowFinder):
    def find_window(self) -> WindowInfo | None:
        try:
            import win32gui
        except ImportError:
            logger.warning("pywin32 not available")
            return None

        result = []

        def enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if title and self._match_title(title):
                rect = win32gui.GetWindowRect(hwnd)
                result.append(WindowInfo(
                    title=title,
                    x=rect[0], y=rect[1],
                    width=rect[2] - rect[0],
                    height=rect[3] - rect[1],
                    window_id=hwnd,
                ))

        win32gui.EnumWindows(enum_callback, None)
        return result[0] if result else None

    def list_windows(self) -> list[WindowInfo]:
        try:
            import win32gui
        except ImportError:
            return []

        result = []

        def enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            result.append(WindowInfo(
                title=title,
                x=rect[0], y=rect[1],
                width=rect[2] - rect[0],
                height=rect[3] - rect[1],
                window_id=hwnd,
            ))

        win32gui.EnumWindows(enum_callback, None)
        return result


def create_finder() -> WindowFinder:
    system = platform.system()
    if system == "Darwin":
        return MacOSWindowFinder()
    elif system == "Windows":
        return WindowsWindowFinder()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
