"""PatternMatcher 测试"""

import cv2
import numpy as np
import pytest

from majsoul_recognizer.types import ActionMatch


class TestPatternMatcherInit:
    """PatternMatcher 初始化测试"""

    def test_load_templates(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)
        assert matcher is not None
        assert len(matcher._templates) == 7

    def test_template_names(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)
        names = {t[0] for t in matcher._templates}
        assert "吃" in names
        assert "碰" in names
        assert "过" in names


class TestPatternMatcherMatch:
    """模板匹配测试"""

    def test_match_finds_button(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)

        # 构造一张包含"碰"按钮的图像
        action_img = np.full((80, 400, 3), 30, dtype=np.uint8)
        template = cv2.imread(str(fake_template_dir / "pon.png"))
        th, tw = template.shape[:2]
        action_img[20:20 + th, 150:150 + tw] = template

        results = matcher.match(action_img, threshold=0.5)
        assert len(results) >= 1
        names = [r.name for r in results]
        assert "碰" in names

    def test_match_empty_image(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)
        empty = np.zeros((80, 400, 3), dtype=np.uint8)
        results = matcher.match(empty, threshold=0.9)
        assert isinstance(results, list)

    def test_match_threshold_filters(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)
        action_img = np.full((80, 400, 3), 30, dtype=np.uint8)
        low_results = matcher.match(action_img, threshold=0.3)
        high_results = matcher.match(action_img, threshold=0.99)
        assert len(low_results) >= len(high_results)

    def test_match_returns_action_match(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)
        action_img = np.full((80, 400, 3), 30, dtype=np.uint8)
        template = cv2.imread(str(fake_template_dir / "kan.png"))
        th, tw = template.shape[:2]
        action_img[20:20 + th, 150:150 + tw] = template

        results = matcher.match(action_img, threshold=0.5)
        for r in results:
            assert isinstance(r, ActionMatch)
            assert 0.0 <= r.score <= 1.0
