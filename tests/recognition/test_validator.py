"""Validator 测试"""

import pytest

from majsoul_recognizer.types import (
    BBox, Detection, CallGroup, GameState, RoundInfo, ZoneName,
)
from majsoul_recognizer.recognition.config import RecognitionConfig
from tests.recognition.conftest import make_detection


class TestHandCountValidation:
    """手牌数量校验测试"""

    def test_valid_13_tiles_no_drawn(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(hand=["1m"] * 13)
        result = validator.validate(state)
        hand_warnings = [w for w in result.warnings if "hand_count" in w]
        assert len(hand_warnings) == 0

    def test_valid_13_tiles_with_drawn(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(hand=["1m"] * 13, drawn_tile="9m")
        result = validator.validate(state)
        hand_warnings = [w for w in result.warnings if "hand_count" in w]
        assert len(hand_warnings) == 0

    def test_invalid_hand_count(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(hand=["1m"] * 10)
        result = validator.validate(state)
        hand_warnings = [w for w in result.warnings if "hand_count" in w]
        assert len(hand_warnings) > 0

    def test_hand_count_with_kan(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        kan = CallGroup(type="kan", tiles=["1m", "1m", "1m", "1m"])
        state = GameState(hand=["2m"] * 12, calls={"self": [kan]})
        result = validator.validate(state)
        hand_warnings = [w for w in result.warnings if "hand_count" in w]
        assert len(hand_warnings) == 0


class TestTileOverflow:
    """牌数上限校验测试"""

    def test_no_overflow(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(hand=["1m", "1m", "1m"])
        result = validator.validate(state)
        overflow = [w for w in result.warnings if "tile_overflow" in w]
        assert len(overflow) == 0

    def test_overflow_detected(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        # 同一种牌出现 5 次（超过上限 4）
        state = GameState(hand=["1m", "1m", "1m", "1m", "1m"])
        result = validator.validate(state)
        overflow = [w for w in result.warnings if "tile_overflow" in w]
        assert len(overflow) > 0

    def test_red_dora_counted_with_normal(self):
        """赤宝牌与普通牌合并计数"""
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        # 4 张 5m + 1 张 5mr = 5 次，超过上限
        state = GameState(hand=["5m", "5m", "5m", "5m", "5mr"])
        result = validator.validate(state)
        overflow = [w for w in result.warnings if "tile_overflow" in w]
        assert len(overflow) > 0


class TestScoreValidation:
    """分数合理性测试"""

    def test_valid_score(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(scores={"self": 25000})
        result = validator.validate(state)
        score_warnings = [w for w in result.warnings if "score_anomaly" in w]
        assert len(score_warnings) == 0

    def test_negative_score_allowed(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(scores={"self": -1000})
        result = validator.validate(state)
        score_warnings = [w for w in result.warnings if "score_anomaly" in w]
        assert len(score_warnings) == 0

    def test_score_too_high(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(scores={"self": 999999})
        result = validator.validate(state)
        score_warnings = [w for w in result.warnings if "score_anomaly" in w]
        assert len(score_warnings) > 0


class TestDiscardContinuity:
    """牌河连续性测试"""

    def test_first_frame_always_valid(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(discards={"self": ["1m", "2m", "3m"]})
        result = validator.validate(state)
        discard_warnings = [w for w in result.warnings if "discard_jump" in w]
        assert len(discard_warnings) == 0

    def test_one_new_discard_is_valid(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state1 = GameState(discards={"self": ["1m"]})
        validator.validate(state1)
        state2 = GameState(discards={"self": ["1m", "2m"]})
        result = validator.validate(state2)
        discard_warnings = [w for w in result.warnings if "discard_jump" in w]
        assert len(discard_warnings) == 0

    def test_two_new_discards_is_invalid(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state1 = GameState(discards={"self": ["1m"]})
        validator.validate(state1)
        state2 = GameState(discards={"self": ["1m", "2m", "3m"]})
        result = validator.validate(state2)
        discard_warnings = [w for w in result.warnings if "discard_jump" in w]
        assert len(discard_warnings) > 0


class TestDetectionFusion:
    """Detection 级帧间融合测试"""

    def test_first_frame_returns_as_is(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        dets = {"hand": [make_detection(0, 0, 50, 70, "1m")]}
        result = validator.fuse_detections(dets)
        assert "hand" in result
        assert len(result["hand"]) == 1

    def test_fusion_majority_vote(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        # 帧 1: 1m
        frame1 = {"hand": [make_detection(0, 0, 50, 70, "1m", 0.9)]}
        validator.fuse_detections(frame1)
        # 帧 2: 9m (同位置)
        frame2 = {"hand": [make_detection(0, 0, 50, 70, "9m", 0.85)]}
        validator.fuse_detections(frame2)
        # 帧 3: 1m (同位置) — 多数投票: 1m 出现 2 次 vs 9m 出现 1 次
        frame3 = {"hand": [make_detection(0, 0, 50, 70, "1m", 0.92)]}
        result = validator.fuse_detections(frame3)
        assert result["hand"][0].tile_code == "1m"

    def test_reset_clears_history(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        frame1 = {"hand": [make_detection(0, 0, 50, 70, "1m")]}
        validator.fuse_detections(frame1)
        validator.reset()
        assert validator.prev_state is None


class TestNoDetectionWarning:
    """连续无检测结果 warning 测试"""

    def test_no_detection_5_frames_warning(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        # 连续 5 帧空检测结果
        for _ in range(5):
            validator.fuse_detections({"hand": []})
        state = GameState()
        result = validator.validate(state)
        assert any("no_detection_5_frames" in w for w in result.warnings)

    def test_has_detection_no_warning(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        for _ in range(5):
            validator.fuse_detections({"hand": [make_detection(0, 0, 50, 70, "1m")]})
        state = GameState()
        result = validator.validate(state)
        assert not any("no_detection_5_frames" in w for w in result.warnings)
