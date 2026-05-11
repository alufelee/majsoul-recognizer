"""BaseView 生命周期测试

[S4 修复] BaseView 继承 ttk.Frame，需要 tkinter。
测试使用 Tk root 创建真实 widget 实例，验证生命周期逻辑。
无 tkinter 环境自动跳过。
"""

import pytest

# tkinter 不可用时跳过整个模块
pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk
from unittest.mock import MagicMock, patch

from majsoul_recognizer.gui.base_view import BaseView


@pytest.fixture
def tk_root():
    """创建隐藏的 Tk root 窗口"""
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def mock_app_state():
    pipeline1 = MagicMock()
    pipeline2 = MagicMock()
    pipelines = iter([pipeline1, pipeline2])
    return MagicMock(
        engine=MagicMock(),
        pipeline_factory=lambda: next(pipelines),
        config=MagicMock(),
        theme_name="dark",
    )


class TestBaseViewLifecycle:
    def test_ensure_worker_creates_worker(self, tk_root, mock_app_state):
        """_ensure_worker 创建 _RecognizeWorker"""
        with patch("majsoul_recognizer.gui.base_view._RecognizeWorker") as MockWorker:
            mock_worker = MagicMock()
            MockWorker.return_value = mock_worker

            view = BaseView(tk_root, mock_app_state, {})
            result = view._ensure_worker()

            assert result is mock_worker
            MockWorker.assert_called_once()

    def test_ensure_worker_is_idempotent(self, tk_root, mock_app_state):
        """多次调用 _ensure_worker 只创建一次 Worker"""
        with patch("majsoul_recognizer.gui.base_view._RecognizeWorker") as MockWorker:
            view = BaseView(tk_root, mock_app_state, {})
            view._ensure_worker()
            view._ensure_worker()
            assert MockWorker.call_count == 1

    def test_stop_cleans_up_worker(self, tk_root, mock_app_state):
        """stop() 调用 worker.stop() 并置空"""
        mock_worker = MagicMock()
        view = BaseView(tk_root, mock_app_state, {})
        view._worker = mock_worker

        view.stop()
        mock_worker.stop.assert_called_once()
        assert view._worker is None

    def test_stop_no_worker_is_noop(self, tk_root, mock_app_state):
        """无 Worker 时 stop() 安全返回"""
        view = BaseView(tk_root, mock_app_state, {})
        view.stop()  # 不应抛异常

    def test_on_theme_changed_updates_theme(self, tk_root, mock_app_state):
        new_theme = {"bg_base": "#fff"}
        view = BaseView(tk_root, mock_app_state, {})
        view.on_theme_changed(new_theme)
        assert view._theme == new_theme

    def test_on_engine_changed_updates_worker(self, tk_root, mock_app_state):
        mock_worker = MagicMock()
        new_engine = MagicMock()
        view = BaseView(tk_root, mock_app_state, {})
        view._worker = mock_worker

        view.on_engine_changed(new_engine)
        mock_worker.update_engine.assert_called_once_with(new_engine)

    def test_on_engine_changed_without_worker_is_safe(self, tk_root, mock_app_state):
        """无 Worker 时 on_engine_changed 不抛异常"""
        new_engine = MagicMock()
        view = BaseView(tk_root, mock_app_state, {})
        view.on_engine_changed(new_engine)  # 不应抛异常

    def test_start_is_noop_by_default(self, tk_root, mock_app_state):
        """基类 start() 默认为空操作（子类覆写）"""
        view = BaseView(tk_root, mock_app_state, {})
        view.start()  # 不应抛异常
