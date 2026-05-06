"""TextRecognizer 测试"""

import pytest

from majsoul_recognizer.recognition.text_recognizer import (
    _parse_score_text,
    _parse_round_text,
    _parse_timer_text,
)


class TestParseScoreText:
    """分数后处理测试"""

    def test_normal_score(self):
        assert _parse_score_text("25,000") == 25000

    def test_score_no_comma(self):
        assert _parse_score_text("25000") == 25000

    def test_negative_score(self):
        assert _parse_score_text("-5,000") == -5000

    def test_score_with_spaces(self):
        assert _parse_score_text(" 25,000 ") == 25000

    def test_empty_returns_none(self):
        assert _parse_score_text("") is None

    def test_no_digits_returns_none(self):
        assert _parse_score_text("abc") is None

    def test_score_out_of_range_returns_none(self):
        assert _parse_score_text("999999") is None

    def test_zero_score(self):
        assert _parse_score_text("0") == 0


class TestParseRoundText:
    """局次后处理测试"""

    def test_standard_round(self):
        result = _parse_round_text("东一局 0 本场")
        assert result is not None
        assert result.wind == "东"
        assert result.number == 1
        assert result.honba == 0

    def test_with_honba(self):
        result = _parse_round_text("南三局 2 本场")
        assert result is not None
        assert result.wind == "南"
        assert result.number == 3
        assert result.honba == 2

    def test_traditional_chinese(self):
        result = _parse_round_text("東二局 1 本場")
        assert result is not None
        assert result.wind == "东"
        assert result.number == 2
        assert result.honba == 1

    def test_missing_wind_returns_none(self):
        result = _parse_round_text("一局 0 本场")
        assert result is None

    def test_missing_number_returns_none(self):
        result = _parse_round_text("东 0 本场")
        assert result is None

    def test_default_honba(self):
        result = _parse_round_text("东一局")
        assert result is not None
        assert result.honba == 0
        assert result.kyotaku == 0


class TestParseTimerText:
    """倒计时后处理测试"""

    def test_normal_timer(self):
        assert _parse_timer_text("8") == 8

    def test_timer_with_colon(self):
        assert _parse_timer_text("1:30") == 90

    def test_empty_returns_none(self):
        assert _parse_timer_text("") is None

    def test_no_digits_returns_none(self):
        assert _parse_timer_text("abc") is None

    def test_large_number(self):
        assert _parse_timer_text("300") == 300


class TestTextRecognizerInit:
    """TextRecognizer 初始化测试"""

    def test_create_instance(self):
        from majsoul_recognizer.recognition.text_recognizer import TextRecognizer
        recognizer = TextRecognizer()
        assert recognizer is not None

    def test_recognize_score_without_ocr(self):
        """无 PaddleOCR 时返回 None（不崩溃）"""
        from majsoul_recognizer.recognition.text_recognizer import TextRecognizer
        import numpy as np
        recognizer = TextRecognizer()
        img = np.zeros((50, 200, 3), dtype=np.uint8)
        result = recognizer.recognize_score(img)
        assert result is None or isinstance(result, int)
