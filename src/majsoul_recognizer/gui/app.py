"""主窗口 — 应用入口

创建 Tkinter 根窗口，管理侧边栏导航，切换视图，维护全局状态。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import numpy as np
import tkinter as tk
import tkinter.ttk as ttk

from majsoul_recognizer.gui.settings import GUISettings
from majsoul_recognizer.gui.settings_dialog import SettingsDialog
from majsoul_recognizer.gui.app_state import AppState
from majsoul_recognizer.gui.theme import apply_style, get_theme
from majsoul_recognizer.gui.views.screenshot_view import ScreenshotView
from majsoul_recognizer.gui.views.live_view import LiveView
from majsoul_recognizer.gui.views.dev_view import DevView
from majsoul_recognizer.pipeline import CapturePipeline
from majsoul_recognizer.recognition.engine import RecognitionEngine
from majsoul_recognizer.types import Detection, FrameResult, GameState

logger = logging.getLogger(__name__)


class App:
    """主窗口"""

    WINDOW_MIN_WIDTH = 960
    WINDOW_MIN_HEIGHT = 640
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 800
    SIDEBAR_WIDTH = 64

    NAV_ITEMS = [
        ("截图", "screenshot"),
        ("实时", "live"),
        ("调试", "dev"),
    ]

    def __init__(self) -> None:
        self._settings = GUISettings.load()
        theme = get_theme(self._settings.theme)

        self._root = self._create_root()
        self._root.title("雀魂麻将识别助手 v0.1")
        self._root.geometry(
            f"{self._settings.window_width}x{self._settings.window_height}"
            f"+{self._settings.window_x}+{self._settings.window_y}"
        )
        self._root.minsize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)

        style = ttk.Style()
        apply_style(style, theme)

        self._build_ui(theme)

        # [S2] Engine init — degraded mode on failure
        config = self._settings.to_recognition_config()
        try:
            engine = RecognitionEngine(config)
        except Exception as e:
            logger.warning("Engine init failed (degraded mode): %s", e)
            engine = None  # type: ignore[assignment]
            self._status_label.config(text="检测器降级模式")

        self._app_state = AppState(
            engine=engine,
            pipeline_factory=lambda: CapturePipeline(
                config_path=Path(self._settings.config_path) if self._settings.config_path else None,
            ),
            config=config,
            theme_name=self._settings.theme,
        )

        on_result = self._make_on_result()
        self._views: dict[str, ttk.Frame] = {
            "screenshot": ScreenshotView(self._content, self._app_state, theme, on_result=on_result),
            "live": LiveView(self._content, self._app_state, theme, on_result=on_result),
            "dev": DevView(self._content, self._app_state, theme),
        }

        self._last_frame: FrameResult | None = None
        self._last_state: GameState | None = None
        self._last_image: np.ndarray | None = None
        self._last_detections: list[Detection] = []
        self._active_view = None

        self._switch_view("screenshot")

    def _create_root(self) -> tk.Tk:
        try:
            from tkinterdnd2 import TkinterDnD
            return TkinterDnD.Tk()
        except ImportError:
            return tk.Tk()

    def _build_ui(self, theme: dict) -> None:
        header = ttk.Frame(self._root)
        header.pack(side="top", fill="x")
        ttk.Label(header, text="雀魂麻将识别助手 v0.1",
                  font=("", 12, "bold")).pack(side="left", padx=8, pady=4)
        ttk.Button(header, text="切换主题", command=self._toggle_theme).pack(side="right", padx=4)
        ttk.Button(header, text="设置", command=self._show_settings).pack(side="right", padx=4)

        body = ttk.Frame(self._root)
        body.pack(side="top", fill="both", expand=True)

        sidebar = ttk.Frame(body, width=self.SIDEBAR_WIDTH, style="Sidebar.TFrame")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self._nav_buttons: dict[str, ttk.Button] = {}
        for label, view_name in self.NAV_ITEMS:
            btn = ttk.Button(sidebar, text=label, style="Sidebar.TButton",
                             command=lambda n=view_name: self._switch_view(n))
            btn.pack(fill="x", padx=4, pady=8)
            self._nav_buttons[view_name] = btn

        # [S3] Content area uses grid for view switching
        self._content = ttk.Frame(body)
        self._content.pack(side="left", fill="both", expand=True)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        status_bar = ttk.Frame(self._root)
        status_bar.pack(side="bottom", fill="x")
        self._status_dot = tk.Canvas(status_bar, width=12, height=12,
                                     bg=theme["bg_primary"], highlightthickness=0)
        self._status_dot.pack(side="left", padx=4, pady=4)
        self._status_dot.create_oval(2, 2, 10, 10, fill=theme["success"], outline="")
        self._status_label = ttk.Label(status_bar, text="就绪", style="Status.TLabel")
        self._status_label.pack(side="left")
        self._status_info = ttk.Label(status_bar, text="", style="Status.TLabel")
        self._status_info.pack(side="right", padx=8)

    def _switch_view(self, view_name: str) -> None:
        if self._active_view:
            self._active_view.stop()
            self._active_view.grid_remove()

        self._active_view = self._views[view_name]
        self._active_view.grid(row=0, column=0, sticky="nsew", in_=self._content)
        self._active_view.start()

        # [C1] Push cached data to DevView
        if view_name == "dev" and self._last_frame is not None:
            if hasattr(self._active_view, "set_current_image") and self._last_image is not None:
                self._active_view.set_current_image(self._last_image)
            if hasattr(self._active_view, "update_data"):
                self._active_view.update_data(
                    self._last_frame, self._last_state,
                    detections=self._last_detections,
                )

    def _make_on_result(self) -> Callable:
        def on_result(image: np.ndarray | None, frame: FrameResult, state: GameState | None,
                      detections: list | None = None):
            self._last_frame = frame
            self._last_state = state
            if image is not None:
                self._last_image = image
            if detections is not None:
                self._last_detections = detections
            if isinstance(self._active_view, DevView):
                self._active_view.update_data(frame, state, detections=detections or [])
        return on_result

    def _toggle_theme(self) -> None:
        new_name = "light" if self._app_state.theme_name == "dark" else "dark"
        new_theme = get_theme(new_name)
        self._app_state.theme_name = new_name
        self._settings.theme = new_name

        style = ttk.Style()
        apply_style(style, new_theme)

        for view in self._views.values():
            view.on_theme_changed(new_theme)
        self._settings.save()

    def _show_settings(self) -> None:
        SettingsDialog(self._root, self._settings, self._rebuild_engine)

    def _rebuild_engine(self) -> None:
        self._settings.save()
        config = self._settings.to_recognition_config()
        try:
            new_engine = RecognitionEngine(config)
            self._app_state.engine = new_engine
            for view in self._views.values():
                view.on_engine_changed(new_engine)
        except Exception as e:
            logger.error("Engine rebuild failed: %s", e)

    def run(self) -> None:
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    def _on_close(self) -> None:
        for view in self._views.values():
            view.stop()
        self._settings.window_width = self._root.winfo_width()
        self._settings.window_height = self._root.winfo_height()
        self._settings.window_x = self._root.winfo_x()
        self._settings.window_y = self._root.winfo_y()
        self._settings.save()
        self._root.destroy()
