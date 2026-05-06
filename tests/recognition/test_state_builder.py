"""GameStateBuilder 测试"""

import pytest

from majsoul_recognizer.types import (
    BBox, Detection, ActionMatch, CallGroup, RoundInfo, GameState, ZoneName,
)
from tests.recognition.conftest import make_detection


class TestZoneKeyMapping:
    """键名映射测试"""

    def test_score_self_to_self(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        assert builder._zone_key("score_self") == "self"

    def test_discards_right_to_right(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        assert builder._zone_key("discards_right") == "right"

    def test_unknown_zone_returns_as_is(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        assert builder._zone_key("hand") == "hand"


class TestHandSorting:
    """手牌排序测试"""

    def test_hand_sorted_by_x(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "hand": [
                make_detection(200, 0, 50, 70, "3m"),
                make_detection(100, 0, 50, 70, "1m"),
                make_detection(150, 0, 50, 70, "2m"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert state.hand == ["1m", "2m", "3m"]


class TestDrawnTileDetection:
    """drawn_tile 间隔检测测试"""

    def test_drawn_tile_detected_by_gap(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        config = RecognitionConfig(drawn_tile_gap_multiplier=2.0)
        builder = GameStateBuilder(config)

        # 13 tiles + 1 drawn_tile (large gap)
        hand_dets = [make_detection(i * 55, 0, 50, 70, f"{i+1}m") for i in range(13)]
        hand_dets.append(make_detection(13 * 55 + 80, 0, 50, 70, "9m"))

        detections = {"hand": hand_dets}
        state = builder.build(detections, {}, None, None, [])
        assert state.drawn_tile == "9m"
        assert len(state.hand) == 13

    def test_no_drawn_tile_13_tiles(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        hand_dets = [make_detection(i * 55, 0, 50, 70, f"{(i % 9) + 1}m") for i in range(13)]
        detections = {"hand": hand_dets}
        state = builder.build(detections, {}, None, None, [])
        assert state.drawn_tile is None
        assert len(state.hand) == 13


class TestDoraBuilding:
    """宝牌构建测试"""

    def test_dora_from_detections(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "dora": [
                make_detection(10, 10, 50, 70, "5m"),
                make_detection(70, 10, 50, 70, "back"),  # should be filtered
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert state.dora_indicators == ["5m"]


class TestScoresBuilding:
    """分数构建测试"""

    def test_scores_from_zones(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        scores = {"score_self": 25000, "score_right": 30000, "score_opposite": None}
        state = builder.build({}, scores, None, None, [])
        assert state.scores == {"self": 25000, "right": 30000}
        assert "opposite" not in state.scores


class TestActionsBuilding:
    """动作构建测试"""

    def test_actions_from_matches(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        actions = [ActionMatch(name="碰", score=0.92), ActionMatch(name="过", score=0.88)]
        state = builder.build({}, {}, None, None, actions)
        assert state.actions == ["碰", "过"]


class TestDiscardsBuilding:
    """牌河构建测试"""

    def test_discards_self_sorted(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "discards_self": [
                make_detection(60, 0, 50, 70, "3m"),
                make_detection(0, 0, 50, 70, "1m"),
                make_detection(120, 0, 50, 70, "5p"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert state.discards == {"self": ["1m", "3m", "5p"]}

    def test_discards_filters_auxiliary(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "discards_self": [
                make_detection(0, 0, 50, 70, "1m"),
                make_detection(60, 0, 50, 70, "back"),
                make_detection(120, 0, 50, 70, "dora_frame"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert state.discards == {"self": ["1m"]}


class TestCallsParsing:
    """副露解析测试"""

    def test_chi_calls(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "calls_self": [
                make_detection(0, 0, 50, 70, "1s"),
                make_detection(55, 0, 50, 70, "2s"),
                make_detection(110, 0, 50, 70, "3s"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert "self" in state.calls
        assert len(state.calls["self"]) == 1
        call = state.calls["self"][0]
        assert call.type == "chi"
        assert call.tiles == ["1s", "2s", "3s"]

    def test_pon_calls(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "calls_self": [
                make_detection(0, 0, 50, 70, "5p"),
                make_detection(55, 0, 50, 70, "5p"),
                make_detection(110, 0, 50, 70, "5p"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert "self" in state.calls
        call = state.calls["self"][0]
        assert call.type == "pon"
        assert call.tiles == ["5p", "5p", "5p"]

    def test_empty_detections_returns_empty_state(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        state = builder.build({}, {}, None, None, [])
        assert state.hand == []
        assert state.drawn_tile is None
        assert state.dora_indicators == []


class TestHand13TilePrevState:
    """手牌 13 张 prev_state 判断测试 (Bug 1 / C2)"""

    def test_13_tiles_prev_state_13_no_drawn(self):
        """上一帧 13 张 + drawn_tile=None（等摸牌中），当前帧 13 张无 drawn_tile"""
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        hand_dets = [make_detection(i * 55, 0, 50, 70, f"{(i % 9) + 1}m") for i in range(13)]
        prev_state = GameState(hand=["1m"] * 13, drawn_tile=None)
        state = builder.build({"hand": hand_dets}, {}, None, None, [], prev_state=prev_state)
        assert len(state.hand) == 13
        assert state.drawn_tile is None

    def test_13_tiles_prev_state_12(self):
        """上一帧 12 张，当前帧 13 张但无法定位 drawn_tile"""
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        hand_dets = [make_detection(i * 55, 0, 50, 70, f"{(i % 9) + 1}m") for i in range(13)]
        prev_state = GameState(hand=["1m"] * 12, drawn_tile=None)
        state = builder.build({"hand": hand_dets}, {}, None, None, [], prev_state=prev_state)
        assert len(state.hand) == 13
        assert state.drawn_tile is None

    def test_13_tiles_prev_state_13_with_drawn(self):
        """上一帧 13 张 + drawn_tile（摸牌后丢弃一张），当前帧 13 张"""
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        hand_dets = [make_detection(i * 55, 0, 50, 70, f"{(i % 9) + 1}m") for i in range(13)]
        prev_state = GameState(hand=["1m"] * 13, drawn_tile="9m")
        state = builder.build({"hand": hand_dets}, {}, None, None, [], prev_state=prev_state)
        assert len(state.hand) == 13
        assert state.drawn_tile is None

    def test_13_tiles_no_prev_state(self):
        """无 prev_state 时 13 张牌保持原行为"""
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        hand_dets = [make_detection(i * 55, 0, 50, 70, f"{(i % 9) + 1}m") for i in range(13)]
        state = builder.build({"hand": hand_dets}, {}, None, None, [])
        assert len(state.hand) == 13
        assert state.drawn_tile is None


class TestKakanUnknownSourceWarning:
    """kakan_unknown_source warning 测试 (Bug 2 / I2)"""

    def test_4_same_tiles_with_rotated_no_prev_state(self):
        """4 张相同牌 + rotated，无 prev_state，产生 kakan_unknown_source warning"""
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        # rotated 牌的 bbox 需要和某个 normal 牌重叠才能被 _resolve_rotated_tiles 关联
        detections = {
            "calls_self": [
                make_detection(0, 0, 50, 70, "5p"),
                make_detection(55, 0, 50, 70, "5p"),
                make_detection(110, 0, 50, 70, "5p"),
                make_detection(115, 0, 50, 70, "rotated"),  # 与第三张 5p 重叠
                make_detection(165, 0, 50, 70, "5p"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert "self" in state.calls
        call = state.calls["self"][0]
        assert call.type == "kan"
        assert any("kakan_unknown_source" in w for w in state.warnings)

    def test_4_same_tiles_no_rotated_no_warning(self):
        """4 张相同牌无 rotated，无 prev_state，不产生 warning"""
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "calls_self": [
                make_detection(0, 0, 50, 70, "5p"),
                make_detection(55, 0, 50, 70, "5p"),
                make_detection(110, 0, 50, 70, "5p"),
                make_detection(165, 0, 50, 70, "5p"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert "self" in state.calls
        call = state.calls["self"][0]
        assert call.type == "kan"
        assert not any("kakan_unknown_source" in w for w in state.warnings)

    def test_kakan_matched_prev_state_no_warning(self):
        """有 prev_state 匹配到碰组时，识别为 kakan 且无 warning"""
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        prev_state = GameState(
            calls={"self": [CallGroup(type="pon", tiles=["5p", "5p", "5p"], from_player="right")]},
        )
        detections = {
            "calls_self": [
                make_detection(0, 0, 50, 70, "5p"),
                make_detection(55, 0, 50, 70, "5p"),
                make_detection(110, 0, 50, 70, "5p"),
                make_detection(165, 0, 50, 70, "5p"),
            ],
        }
        state = builder.build(detections, {}, None, None, [], prev_state=prev_state)
        assert "self" in state.calls
        call = state.calls["self"][0]
        assert call.type == "kakan"
        assert call.from_player == "right"
        assert not any("kakan_unknown_source" in w for w in state.warnings)
