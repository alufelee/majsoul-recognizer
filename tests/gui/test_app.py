"""App 主窗口测试"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

from unittest.mock import MagicMock, patch

from majsoul_recognizer.gui.app import App


def _make_mock_settings():
    """创建 mock GUISettings"""
    mock_settings = MagicMock()
    mock_settings.theme = "dark"
    mock_settings.window_width = 800
    mock_settings.window_height = 600
    mock_settings.window_x = 0
    mock_settings.window_y = 0
    mock_settings.config_path = None
    mock_settings.to_recognition_config.return_value = MagicMock()
    return mock_settings


class TestAppCreation:
    def test_app_creates_root(self):
        with patch("majsoul_recognizer.gui.app.GUISettings") as MockSettings:
            MockSettings.load.return_value = _make_mock_settings()

            with patch("majsoul_recognizer.gui.app.RecognitionEngine"):
                app = App()
                assert app._root is not None
                assert app._root.title() != ""
                app._root.destroy()

    def test_engine_failure_degraded_mode(self):
        """[C2] Engine 创建失败时进入降级模式，engine=None"""
        with patch("majsoul_recognizer.gui.app.GUISettings") as MockSettings:
            MockSettings.load.return_value = _make_mock_settings()

            with patch("majsoul_recognizer.gui.app.RecognitionEngine", side_effect=RuntimeError("no model")):
                app = App()
                assert app._app_state.engine is None
                # _init_error is consumed by _switch_view, so check active view's status label
                assert app._active_view is not None
                assert app._active_view._status_label.cget("text") == "检测器降级模式"
                app._root.destroy()

    def test_on_close_saves_valid_geometry(self):
        """[M1] 正常窗口尺寸被保存"""
        with patch("majsoul_recognizer.gui.app.GUISettings") as MockSettings:
            settings = _make_mock_settings()
            MockSettings.load.return_value = settings

            with patch("majsoul_recognizer.gui.app.RecognitionEngine"):
                app = App()
                # 模拟正常尺寸
                app._root.update_idletasks()
                app._root.geometry("960x640+0+0")
                app._root.update_idletasks()
                app._on_close()
                # 窗口已销毁，检查 settings 是否调用了 save
                settings.save.assert_called()
                assert settings.window_width == 960
                assert settings.window_height == 640

    def test_on_close_ignores_minimized_geometry(self):
        """[M1] 最小化时不保存 1x1 几何"""
        with patch("majsoul_recognizer.gui.app.GUISettings") as MockSettings:
            settings = _make_mock_settings()
            MockSettings.load.return_value = settings

            with patch("majsoul_recognizer.gui.app.RecognitionEngine"):
                app = App()
                # 模拟正常尺寸先
                app._root.update_idletasks()
                app._root.geometry("960x640+0+0")
                app._root.update_idletasks()
                # 模拟最小化（覆盖 width/height）
                app._root.winfo_width = lambda: 1
                app._root.winfo_height = lambda: 1
                app._on_close()
                # 尺寸应保持原值，不更新为 1x1
                assert settings.window_width == 960
                assert settings.window_height == 640

    def test_rebuild_engine_failure_sets_none(self):
        """[CRITICAL] _rebuild_engine 失败时 engine 设为 None"""
        with patch("majsoul_recognizer.gui.app.GUISettings") as MockSettings:
            settings = _make_mock_settings()
            MockSettings.load.return_value = settings

            with patch("majsoul_recognizer.gui.app.RecognitionEngine") as MockEngine:
                MockEngine.return_value = MagicMock()
                app = App()

                # 第二次调用失败
                MockEngine.side_effect = RuntimeError("rebuild failed")
                app._rebuild_engine()
                assert app._app_state.engine is None
                app._root.destroy()
