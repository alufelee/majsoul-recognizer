"""区域配置与分割测试"""

from pathlib import Path

import numpy as np
import pytest

from majsoul_recognizer.types import ZoneName, BBox
from majsoul_recognizer.zones.config import ZoneConfig, load_zone_config
from majsoul_recognizer.zones.splitter import ZoneSplitter


CONFIG_DIR = Path(__file__).parent.parent / "config"


class TestZoneConfig:
    """区域配置加载测试"""

    def test_load_config(self):
        config = load_zone_config(CONFIG_DIR / "zones.yaml")
        assert isinstance(config, ZoneConfig)
        assert len(config.zones) == 14

    def test_get_zone(self):
        config = load_zone_config(CONFIG_DIR / "zones.yaml")
        hand = config.get_zone(ZoneName.HAND)
        assert hand is not None
        assert hand.name == ZoneName.HAND
        assert hand.x == 0.25
        assert hand.y == 0.82

    def test_get_all_zone_names(self):
        config = load_zone_config(CONFIG_DIR / "zones.yaml")
        names = config.zone_names
        assert ZoneName.HAND in names
        assert ZoneName.DORA in names
        assert len(names) == 14

    def test_missing_config_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_zone_config(CONFIG_DIR / "nonexistent.yaml")

    def test_zone_to_bbox_on_1080p(self):
        config = load_zone_config(CONFIG_DIR / "zones.yaml")
        hand = config.get_zone(ZoneName.HAND)
        bbox = hand.to_bbox(1920, 1080)
        assert bbox.x == 480
        assert bbox.y == 885
        assert bbox.width == 960
        assert bbox.height == 129


class TestZoneSplitter:
    """区域分割器测试"""

    @pytest.fixture
    def splitter(self):
        config = load_zone_config(CONFIG_DIR / "zones.yaml")
        return ZoneSplitter(config)

    def test_split_returns_all_zones(self, splitter, sample_screenshot):
        regions = splitter.split(sample_screenshot)
        assert len(regions) == 14
        assert ZoneName.HAND in regions

    def test_split_hand_region_shape(self, splitter, sample_screenshot):
        regions = splitter.split(sample_screenshot)
        hand = regions[ZoneName.HAND]
        assert hand.shape == (129, 960, 3)

    def test_split_normalizes_resolution(self, splitter, sample_screenshot_small):
        regions = splitter.split(sample_screenshot_small)
        assert len(regions) == 14

    def test_split_preserves_color_channels(self, splitter, sample_screenshot):
        regions = splitter.split(sample_screenshot)
        for name, region in regions.items():
            assert region.shape[2] == 3, f"{name} should have 3 color channels"

    def test_get_hand_region_directly(self, splitter, sample_screenshot):
        hand = splitter.get_zone(sample_screenshot, ZoneName.HAND)
        assert hand is not None
        assert hand.shape[2] == 3
