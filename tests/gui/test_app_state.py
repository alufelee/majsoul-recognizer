"""AppState 测试"""

from unittest.mock import MagicMock

from majsoul_recognizer.gui.app_state import AppState


class TestAppState:
    def _make_state(self, **kwargs):
        defaults = {
            "engine": MagicMock(),
            "pipeline_factory": lambda: MagicMock(),
            "config": MagicMock(),
            "theme_name": "dark",
        }
        defaults.update(kwargs)
        return AppState(**defaults)

    def test_creation(self):
        state = self._make_state()
        assert state.theme_name == "dark"
        assert state.engine is not None

    def test_engine_can_be_replaced(self):
        state = self._make_state()
        new_engine = MagicMock()
        state.engine = new_engine
        assert state.engine is new_engine

    def test_pipeline_factory_creates_new_instances(self):
        """S5: 工厂函数每次返回独立实例"""
        state = self._make_state()
        p1 = state.pipeline_factory()
        p2 = state.pipeline_factory()
        assert p1 is not p2
