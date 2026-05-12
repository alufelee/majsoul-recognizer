"""视图基类 — 统一的生命周期接口

App 通过 BaseView 的 start/stop/on_theme_changed/on_engine_changed
管理视图切换，无需知道具体视图类型。
"""

from __future__ import annotations

import tkinter as tk
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

    def _create_status_bar(self) -> tuple[ttk.Frame, tk.Canvas, ttk.Label, ttk.Label]:
        """Create a uniform status bar component — HUD style.

        Returns: (outer_frame, status_dot, status_label, status_info)
                 Place outer_frame in grid (row=1).
                 Add buttons to self._status_bar_frame.
        """
        outer = ttk.Frame(self)

        sep = tk.Canvas(outer, height=1, bg=self._theme["accent"],
                        highlightthickness=0)
        sep.pack(side="top", fill="x")

        bar = ttk.Frame(outer, style="StatusBar.TFrame", height=32)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        # HUD-style status indicator: small diamond
        dot = tk.Canvas(bar, width=16, height=16,
                        bg=self._theme["bg_crust"], highlightthickness=0)
        dot.pack(side="left", padx=(8, 4), pady=8)
        dot.create_polygon(8, 3, 13, 8, 8, 13, 3, 8,
                           fill=self._theme["accent"], outline="")

        status_label = ttk.Label(bar, text="就绪", style="Status.TLabel")
        status_label.pack(side="left")

        info_label = ttk.Label(bar, text="", style="Status.TLabel")
        info_label.pack(side="right", padx=8)

        self._status_label = status_label
        self._status_bar_frame = bar
        return outer, dot, status_label, info_label

    def set_status_text(self, text: str) -> None:
        """App-level status message delegation"""
        if hasattr(self, '_status_label') and self._status_label is not None:
            self._status_label.config(text=text)
