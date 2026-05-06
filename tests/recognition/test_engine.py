"""RecognitionEngine 集成测试"""

import numpy as np
import pytest

from majsoul_recognizer.types import GameState, ZoneName
from majsoul_recognizer.recognition.config import RecognitionConfig


class TestRecognitionEngineInit:
    """引擎初始化测试"""

    def test_create_with_default_config(self):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig()
        engine = RecognitionEngine(config)
        assert engine is not None

    def test_create_with_none_config(self):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        engine = RecognitionEngine()
        assert engine is not None


class TestRecognitionEngineRecognize:
    """引擎识别测试"""

    def test_empty_zones_returns_warning(self):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        engine = RecognitionEngine()
        state = engine.recognize({})
        assert isinstance(state, GameState)
        assert "empty_zones" in state.warnings

    def test_recognize_with_zones(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        zones = {
            "hand": np.zeros((100, 200, 3), dtype=np.uint8),
            "dora": np.zeros((60, 150, 3), dtype=np.uint8),
        }
        state = engine.recognize(zones)
        assert isinstance(state, GameState)

    def test_recognize_non_static_none_safe(self, dummy_detector_path, fake_template_dir):
        """空区域图像不崩溃"""
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        zones = {
            "hand": np.zeros((100, 200, 3), dtype=np.uint8),
            "score_self": np.array([], dtype=np.uint8),  # 空
        }
        state = engine.recognize(zones)
        assert isinstance(state, GameState)


class TestRecognitionEngineLifecycle:
    """生命周期测试"""

    def test_context_manager(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        with RecognitionEngine(config) as engine:
            state = engine.recognize({})
            assert isinstance(state, GameState)

    def test_reset(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        engine.reset()
        assert engine._validator.prev_state is None

    def test_warmup(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        engine.warmup()
        assert engine._warmed_up is True
