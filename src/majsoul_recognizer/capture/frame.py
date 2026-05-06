"""帧状态检测"""

import cv2
import numpy as np


class FrameChecker:
    """帧静止检测器"""

    def __init__(self, threshold: float = 0.02):
        self._threshold = threshold
        self._prev_frame: np.ndarray | None = None

    def is_static(self, frame: np.ndarray) -> bool:
        if self._prev_frame is None:
            self._prev_frame = self._preprocess(frame)
            return True

        current = self._preprocess(frame)
        diff_ratio = self._compute_diff_ratio(self._prev_frame, current)
        self._prev_frame = current

        return bool(diff_ratio < self._threshold)

    def reset(self):
        self._prev_frame = None

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        small = cv2.resize(frame, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return gray

    def _compute_diff_ratio(self, prev: np.ndarray, curr: np.ndarray) -> float:
        diff = cv2.absdiff(prev, curr)
        changed_pixels = np.count_nonzero(diff > 10)
        total_pixels = prev.size
        return changed_pixels / total_pixels
