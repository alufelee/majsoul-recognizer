"""核心数据类型测试"""

import numpy as np
import pytest
from pydantic import ValidationError

from majsoul_recognizer.types import (
    BBox,
    ZoneDefinition,
    ZoneName,
    Detection,
    RoundInfo,
    GameState,
    FrameResult,
)


class TestBBox:
    """边界框测试"""

    def test_create_bbox(self):
        bbox = BBox(x=10, y=20, width=100, height=50)
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 100
        assert bbox.height == 50

    def test_bbox_area(self):
        bbox = BBox(x=0, y=0, width=100, height=50)
        assert bbox.area == 5000

    def test_bbox_center(self):
        bbox = BBox(x=100, y=200, width=60, height=40)
        assert bbox.center == (130, 220)

    def test_bbox_to_slice(self):
        bbox = BBox(x=10, y=20, width=30, height=40)
        s = bbox.to_slice()
        assert s == (slice(20, 60), slice(10, 40))

    def test_bbox_crop_image(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[30:60, 10:50] = 255
        bbox = BBox(x=10, y=30, width=40, height=30)
        cropped = bbox.crop(img)
        assert cropped.shape == (30, 40, 3)
        assert (cropped == 255).all()

    def test_bbox_negative_size_raises(self):
        with pytest.raises(ValidationError):
            BBox(x=0, y=0, width=-1, height=10)


class TestZoneDefinition:
    """区域定义测试"""

    def test_create_zone(self):
        zone = ZoneDefinition(
            name=ZoneName.HAND,
            x=0.25, y=0.82, width=0.50, height=0.12,
        )
        assert zone.name == ZoneName.HAND
        assert zone.x == 0.25

    def test_zone_to_bbox(self):
        zone = ZoneDefinition(
            name=ZoneName.HAND,
            x=0.25, y=0.82, width=0.50, height=0.12,
        )
        bbox = zone.to_bbox(1920, 1080)
        assert bbox.x == 480
        assert bbox.y == 885
        assert bbox.width == 960
        assert bbox.height == 129

    def test_zone_ratio_range(self):
        with pytest.raises(ValidationError):
            ZoneDefinition(name=ZoneName.HAND, x=-0.1, y=0.5, width=0.2, height=0.1)


class TestDetection:
    """检测结果测试"""

    def test_create_detection(self):
        det = Detection(
            bbox=BBox(x=10, y=20, width=30, height=40),
            tile_code="1m",
            confidence=0.95,
        )
        assert det.tile_code == "1m"
        assert det.confidence == 0.95

    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            Detection(
                bbox=BBox(x=0, y=0, width=10, height=10),
                tile_code="1m",
                confidence=1.5,
            )

    def test_is_high_confidence(self):
        high = Detection(
            bbox=BBox(x=0, y=0, width=10, height=10),
            tile_code="1m", confidence=0.92,
        )
        low = Detection(
            bbox=BBox(x=0, y=0, width=10, height=10),
            tile_code="1m", confidence=0.75,
        )
        assert high.is_high_confidence is True
        assert low.is_high_confidence is False


class TestRoundInfo:
    """局次信息测试"""

    def test_create_round_info(self):
        info = RoundInfo(wind="东", number=1, honba=0, kyotaku=0)
        assert info.wind == "东"
        assert info.number == 1

    def test_invalid_wind_raises(self):
        with pytest.raises(ValidationError):
            RoundInfo(wind="西", number=1, honba=0, kyotaku=0)

    def test_invalid_number_raises(self):
        with pytest.raises(ValidationError):
            RoundInfo(wind="东", number=5, honba=0, kyotaku=0)


class TestGameState:
    """游戏状态测试"""

    def test_create_empty_state(self):
        state = GameState()
        assert state.hand == []
        assert state.scores == {}
        assert state.round_info is None

    def test_state_with_data(self):
        state = GameState(
            hand=["1m", "2m", "3m"],
            drawn_tile="东",
            dora_indicators=["5m"],
        )
        assert len(state.hand) == 3
        assert state.drawn_tile == "东"


class TestFrameResult:
    """帧结果测试"""

    def test_create_frame_result(self):
        result = FrameResult(
            frame_id=1,
            timestamp="2026-05-06T10:00:00",
            zones={ZoneName.HAND: np.zeros((100, 200, 3), dtype=np.uint8)},
        )
        assert result.frame_id == 1
        assert ZoneName.HAND in result.zones
