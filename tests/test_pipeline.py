"""截图流水线集成测试"""

import numpy as np
import pytest

from majsoul_recognizer.pipeline import CapturePipeline
from majsoul_recognizer.capture.finder import WindowInfo
from majsoul_recognizer.types import ZoneName


class TestCapturePipeline:
    """截图流水线测试"""

    @pytest.fixture
    def pipeline(self):
        return CapturePipeline()

    def test_pipeline_creation(self, pipeline):
        assert pipeline is not None

    def test_process_image_splits_zones(self, pipeline, sample_screenshot):
        """处理图像返回分割后的区域"""
        result = pipeline.process_image(sample_screenshot)
        assert result is not None
        assert result.is_static is True
        assert "hand" in result.zones  # ZoneName 转为字符串键
        assert len(result.zones) == 14

    def test_process_image_with_state_detection(self, pipeline, sample_screenshot):
        """帧状态检测正常工作"""
        # 第一帧应判定为静止
        result1 = pipeline.process_image(sample_screenshot)
        assert result1.is_static is True

        # 相同帧应判定为静止
        result2 = pipeline.process_image(sample_screenshot)
        assert result2.is_static is True

    def test_process_image_animated_frame(self, pipeline, sample_screenshot):
        """动画帧检测"""
        result1 = pipeline.process_image(sample_screenshot)
        # 大幅修改图像
        animated = np.ones_like(sample_screenshot) * 128
        result2 = pipeline.process_image(animated)
        assert result2.is_static is False

    def test_process_image_increments_frame_id(self, pipeline, sample_screenshot):
        """帧 ID 递增"""
        r1 = pipeline.process_image(sample_screenshot)
        r2 = pipeline.process_image(sample_screenshot)
        assert r2.frame_id == r1.frame_id + 1

    def test_process_image_nonstandard_resolution(self, pipeline, sample_screenshot_small):
        """非基准分辨率图像正常处理"""
        result = pipeline.process_image(sample_screenshot_small)
        assert result is not None
        assert "hand" in result.zones
