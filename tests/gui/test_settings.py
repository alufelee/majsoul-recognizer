"""GUISettings 配置持久化测试"""

import json
from pathlib import Path

from majsoul_recognizer.gui.settings import GUISettings


class TestGUISettingsDefaults:
    def test_default_values(self):
        s = GUISettings()
        assert s.model_path is None
        assert s.theme == "dark"
        assert s.detection_confidence == 0.3
        assert s.window_width == 1280
        assert s.window_height == 800

    def test_custom_values(self):
        s = GUISettings(theme="light", detection_confidence=0.9, window_width=1920)
        assert s.theme == "light"
        assert s.detection_confidence == 0.9
        assert s.window_width == 1920


class TestGUISettingsSaveLoad:
    def test_save_and_load_roundtrip(self, tmp_path):
        """[C2/M2 修复] 使用 path 参数替代 _PATH 实例属性赋值"""
        path = tmp_path / "test_settings.json"
        original = GUISettings(theme="light", model_path="/path/to/model", window_width=1920)
        original.save(path=path)

        loaded = GUISettings.load(path=path)

        assert loaded.theme == "light"
        assert loaded.model_path == "/path/to/model"
        assert loaded.window_width == 1920

    def test_load_missing_file_returns_defaults(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        result = GUISettings.load(path=path)
        assert result.theme == "dark"
        assert result.model_path is None

    def test_load_corrupted_file_returns_defaults(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{invalid json!!!")
        result = GUISettings.load(path=path)
        assert result.theme == "dark"

    def test_save_is_atomic(self, tmp_path):
        path = tmp_path / "atomic.json"
        s = GUISettings(theme="dark")
        s.save(path=path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["theme"] == "dark"


class TestToRecognitionConfig:
    def test_default_maps_to_config(self):
        from majsoul_recognizer.recognition.config import RecognitionConfig

        s = GUISettings()
        config = s.to_recognition_config()
        assert isinstance(config, RecognitionConfig)
        assert config.model_path is None
        assert config.detection_confidence == 0.3
        assert config.nms_iou_threshold == 0.55
        assert config.enable_batch_detection is True
        assert config.drawn_tile_gap_multiplier == 2.5

    def test_custom_path_converted(self):
        s = GUISettings(model_path="/models/detector.onnx")
        config = s.to_recognition_config()
        assert config.model_path == Path("/models/detector.onnx")

    def test_all_fields_mapped(self):
        """[C3 修复] 确保每个 RecognitionConfig 字段都被映射
        RecognitionConfig 是 Pydantic BaseModel，用 model_fields 而非 dataclasses.fields。
        """
        from majsoul_recognizer.recognition.config import RecognitionConfig

        rc_fields = set(RecognitionConfig.model_fields.keys())
        s = GUISettings(
            model_path="/m", mapping_path="/map", template_dir="/t",
            ocr_model_dir="/ocr", detection_confidence=0.8,
            nms_iou_threshold=0.6, score_min=-100, score_max=100000,
            fusion_window_size=5, enable_batch_detection=False,
            drawn_tile_gap_multiplier=3.0, call_group_gap_multiplier=2.5,
        )
        config = s.to_recognition_config()
        # 验证每个 RecognitionConfig 字段都被设置了非默认值
        assert config.mapping_path == Path("/map")
        assert config.ocr_model_dir == Path("/ocr")
        assert config.score_min == -100
        assert config.score_max == 100000
        assert config.fusion_window_size == 5
        assert config.enable_batch_detection is False
        assert len(rc_fields) > 0  # 确保 model_fields 非空


class TestToPipelineConfig:
    def test_default_returns_none_path(self):
        s = GUISettings()
        config_path, threshold = s.to_pipeline_config()
        assert config_path is None
        assert threshold == 0.02

    def test_custom_path(self):
        s = GUISettings(config_path="/config/zones.yaml")
        config_path, threshold = s.to_pipeline_config()
        assert config_path == Path("/config/zones.yaml")
