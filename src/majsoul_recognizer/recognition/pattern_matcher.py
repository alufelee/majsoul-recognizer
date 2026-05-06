"""动作按钮模板匹配"""

import logging
from pathlib import Path

import cv2
import numpy as np

from majsoul_recognizer.types import ActionMatch

logger = logging.getLogger(__name__)

# 模板文件名 → 动作名称映射
_TEMPLATE_NAMES = {
    "chi": "吃", "pon": "碰", "kan": "杠",
    "ron": "荣和", "tsumo": "自摸", "riichi": "立直", "skip": "过",
}


class PatternMatcher:
    """动作按钮模板匹配"""

    def __init__(self, template_dir: Path | str):
        self._templates: list[tuple[str, np.ndarray]] = []
        template_dir = Path(template_dir)
        if not template_dir.exists():
            logger.warning("Template directory not found: %s", template_dir)
            return

        for filename, action_name in _TEMPLATE_NAMES.items():
            path = template_dir / f"{filename}.png"
            if path.exists():
                img = cv2.imread(str(path))
                if img is not None:
                    self._templates.append((action_name, img))
                    logger.debug("Loaded template: %s", filename)
            else:
                logger.debug("Template not found: %s", path)

    def match(self, image: np.ndarray, threshold: float = 0.85) -> list[ActionMatch]:
        """匹配动作按钮"""
        if image is None or image.size == 0:
            return []

        results: list[ActionMatch] = []
        for action_name, template in self._templates:
            th, tw = template.shape[:2]
            ih, iw = image.shape[:2]
            if th > ih or tw > iw:
                continue

            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val >= threshold:
                results.append(ActionMatch(name=action_name, score=round(float(max_val), 4)))

        return sorted(results, key=lambda x: x.score, reverse=True)
