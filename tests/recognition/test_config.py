"""RecognitionConfig 测试"""

import pytest
from pathlib import Path
from majsoul_recognizer.recognition.config import RecognitionConfig


class TestRecognitionConfig:
    """识别引擎配置测试"""

    def test_default_values(self):
        config = RecognitionConfig()
        assert config.nms_iou_threshold == 0.55
        assert config.detection_confidence == 0.7
        assert config.score_min == -99999
        assert config.score_max == 200000
        assert config.fusion_window_size == 3
        assert config.drawn_tile_gap_multiplier == 2.5
        assert config.call_group_gap_multiplier == 2.0
        assert config.enable_batch_detection is True

    def test_custom_values(self):
        config = RecognitionConfig(
            nms_iou_threshold=0.45,
            detection_confidence=0.5,
            fusion_window_size=5,
        )
        assert config.nms_iou_threshold == 0.45
        assert config.detection_confidence == 0.5
        assert config.fusion_window_size == 5

    def test_get_model_path_raises_when_not_found(self):
        config = RecognitionConfig()
        with pytest.raises(FileNotFoundError, match="tile_detector.onnx"):
            config.get_model_path()

    def test_get_model_path_returns_explicit(self, tmp_path):
        model_file = tmp_path / "tile_detector.onnx"
        model_file.write_bytes(b"fake")
        config = RecognitionConfig(model_path=model_file)
        assert config.get_model_path() == model_file

    def test_get_template_dir_raises_when_not_found(self):
        config = RecognitionConfig()
        with pytest.raises(FileNotFoundError, match="templates/"):
            config.get_template_dir()

    def test_get_template_dir_returns_explicit(self, tmp_path):
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        config = RecognitionConfig(template_dir=template_dir)
        assert config.get_template_dir() == template_dir
