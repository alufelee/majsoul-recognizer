"""RecognitionConfig 测试"""

import pytest

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

    def test_get_template_dir_raises_when_cannot_resolve(self, monkeypatch):
        """自动解析失败时抛 FileNotFoundError"""
        from majsoul_recognizer.recognition import config as config_mod
        monkeypatch.setattr(config_mod, "_resolve_resource_path", lambda _: None)
        config = RecognitionConfig()
        with pytest.raises(FileNotFoundError, match="templates"):
            config.get_template_dir()

    def test_get_template_dir_resolves_default(self):
        """默认配置能自动解析到项目的 templates 目录"""
        config = RecognitionConfig()
        template_dir = config.get_template_dir()
        assert template_dir is not None
        assert template_dir.exists()

    def test_get_template_dir_returns_explicit(self, tmp_path):
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        config = RecognitionConfig(template_dir=template_dir)
        assert config.get_template_dir() == template_dir


class TestRecognitionConfigVit:
    """ViT 分类器配置测试"""

    def test_vit_defaults(self):
        config = RecognitionConfig()
        assert config.enable_vit_classifier is True
        assert config.vit_classifier_threshold == 0.5
        assert config.vit_model_name == "pjura/mahjong_soul_vision"
        assert config.vit_device is None

    def test_vit_custom(self):
        config = RecognitionConfig(
            enable_vit_classifier=False,
            vit_classifier_threshold=0.8,
            vit_model_name="/local/model",
            vit_device="cpu",
        )
        assert config.enable_vit_classifier is False
        assert config.vit_classifier_threshold == 0.8
        assert config.vit_model_name == "/local/model"
        assert config.vit_device == "cpu"
