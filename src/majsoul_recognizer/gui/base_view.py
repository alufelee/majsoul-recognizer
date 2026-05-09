"""视图基类 — 统一的生命周期接口

App 通过 BaseView 的 start/stop/on_theme_changed/on_engine_changed
管理视图切换，无需知道具体视图类型。
"""

from __future__ import annotations

import tkinter.ttk as ttk

from majsoul_recognizer.gui.worker import _RecognizeWorker


class BaseView(ttk.Frame):
    """视图基类，定义统一生命周期

    子类:
    - ScreenshotView / LiveView: 调用 _ensure_worker() 创建异步识别线程
    - DevView: 不调用 _ensure_worker()，不创建 Worker
    """

    def __init__(self, parent, app_state, theme: dict, **kwargs):
        super().__init__(parent, **kwargs)
        self._app_state = app_state
        self._theme = theme
        self._worker: _RecognizeWorker | None = None

    def _ensure_worker(self) -> _RecognizeWorker:
        """延迟创建 Worker（仅需要异步识别的视图调用）

        S5: 每次 ensure 通过 pipeline_factory 创建新的 pipeline 实例，
        避免跨视图状态泄漏。
        """
        if self._worker is None:
            pipeline = self._app_state.pipeline_factory()
            self._worker = _RecognizeWorker(
                self._app_state.engine, pipeline
            )
        return self._worker

    def start(self) -> None:
        """视图激活时调用（切换到该视图时）"""

    def stop(self) -> None:
        """视图停用时调用（离开该视图时）"""
        if self._worker is not None:
            self._worker.stop()
            self._worker = None

    def on_theme_changed(self, theme: dict) -> None:
        """主题切换通知"""
        self._theme = theme

    def on_engine_changed(self, engine) -> None:
        """引擎重建通知（设置变更后由 App 调用）"""
        if self._worker is not None:
            self._worker.update_engine(engine)
