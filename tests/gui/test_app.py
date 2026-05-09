"""App 主窗口测试"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

from unittest.mock import MagicMock, patch

from majsoul_recognizer.gui.app import App


class TestAppCreation:
    def test_app_creates_root(self):
        with patch("majsoul_recognizer.gui.app.GUISettings") as MockSettings:
            mock_settings = MagicMock()
            mock_settings.theme = "dark"
            mock_settings.window_width = 800
            mock_settings.window_height = 600
            mock_settings.window_x = 0
            mock_settings.window_y = 0
            mock_settings.to_recognition_config.return_value = MagicMock()
            MockSettings.load.return_value = mock_settings

            with patch("majsoul_recognizer.gui.app.RecognitionEngine"):
                app = App()
                assert app._root is not None
                assert app._root.title() != ""
                app._root.destroy()
