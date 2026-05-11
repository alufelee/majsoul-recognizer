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
    SIDEBAR_WIDTH = 140

    NAV_ITEMS = [
        ("\U0001f4f7 截图", "screenshot"),
        ("\u26a1 实时", "live"),
        ("\U0001f527 调试", "dev"),
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

        zone_path = Path(self._settings.config_path) if self._settings.config_path else None
        self._app_state = AppState(
            engine=engine,
            pipeline_factory=lambda: CapturePipeline(config_path=zone_path),
            config=config,
            theme_name=self._settings.theme,
            zone_config_path=zone_path,
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
        self._active_view_name: str | None = None

        self._switch_view("screenshot")

    def _create_root(self) -> tk.Tk:
        try:
            from tkinterdnd2 import TkinterDnD
            return TkinterDnD.Tk()
        except ImportError:
            return tk.Tk()

    def _build_ui(self, theme: dict) -> None:
        # Header with accent bottom border
        header_frame = ttk.Frame(self._root, style="Header.TFrame")
        header_frame.pack(side="top", fill="x")

        header = ttk.Frame(header_frame, style="Header.TFrame")
        header.pack(side="top", fill="x")
        ttk.Label(header, text="雀魂麻将识别助手 v0.1",
                  font=("", 12, "bold")).pack(side="left", padx=12, pady=6)
        ttk.Button(header, text="切换主题", command=self._toggle_theme).pack(side="right", padx=4, pady=4)
        ttk.Button(header, text="设置", command=self._show_settings).pack(side="right", padx=4, pady=4)

        # Accent bottom border via Canvas
        border_canvas = tk.Canvas(header_frame, height=2, bg=theme["accent"],
                                  highlightthickness=0)
        border_canvas.pack(side="bottom", fill="x")
        self._header_border = border_canvas

        body = ttk.Frame(self._root)
        body.pack(side="top", fill="both", expand=True)

        sidebar = ttk.Frame(body, width=self.SIDEBAR_WIDTH, style="Sidebar.TFrame")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self._nav_buttons: dict[str, ttk.Button] = {}
        for label, view_name in self.NAV_ITEMS:
            btn = ttk.Button(sidebar, text=label, style="Nav.TButton",
                             command=lambda n=view_name: self._switch_view(n))
            btn.pack(fill="x", padx=8, pady=(12, 4))
            self._nav_buttons[view_name] = btn

        # [S3] Content area uses grid for view switching
        self._content = ttk.Frame(body)
        self._content.pack(side="left", fill="both", expand=True)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # Status bar with top border
        status_outer = ttk.Frame(self._root)
        status_outer.pack(side="bottom", fill="x")
        status_border = tk.Canvas(status_outer, height=1, bg=theme["bg_surface0"],
                                  highlightthickness=0)
        status_border.pack(side="top", fill="x")
        self._status_border = status_border

        status_bar = ttk.Frame(status_outer)
        status_bar.pack(side="top", fill="x", padx=8, pady=6)
        self._status_dot = tk.Canvas(status_bar, width=16, height=16,
                                     bg=theme["bg_base"], highlightthickness=0)
        self._status_dot.pack(side="left", padx=(0, 4))
        self._status_dot.create_oval(2, 2, 14, 14, fill=theme["green"], outline="")
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

        # Update nav button active states
        for name, btn in self._nav_buttons.items():
            if name == view_name:
                btn.configure(style="NavActive.TButton")
            else:
                btn.configure(style="Nav.TButton")
        self._active_view_name = view_name

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

        # Update accent border and status border colors
        self._header_border.configure(bg=new_theme["accent"])
        self._status_border.configure(bg=new_theme["bg_surface0"])

        # Update status dot
        self._status_dot.configure(bg=new_theme["bg_base"])
        self._status_dot.delete("all")
        self._status_dot.create_oval(2, 2, 14, 14, fill=new_theme["green"], outline="")

        # Re-apply active nav button styles
        for name, btn in self._nav_buttons.items():
            if name == self._active_view_name:
                btn.configure(style="NavActive.TButton")
            else:
                btn.configure(style="Nav.TButton")

        for view in self._views.values():
            view.on_theme_changed(new_theme)
        self._settings.save()

    def _show_settings(self) -> None:
        SettingsDialog(self._root, self._settings, self._rebuild_engine)

    def _rebuild_engine(self) -> None:
        self._settings.save()
        config = self._settings.to_recognition_config()
        # 同步 zone_config_path（设置可能更改了 config_path）
        self._app_state.zone_config_path = (
            Path(self._settings.config_path) if self._settings.config_path else None
        )
        try:
            new_engine = RecognitionEngine(config)
            self._app_state.engine = new_engine
            for view in self._views.values():
                view.on_engine_changed(new_engine)
        except Exception as e:
            logger.error("Engine rebuild failed: %s", e)
            self._app_state.engine = None
            self._status_label.config(text=f"引擎重建失败: {e}")

    def run(self) -> None:
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    def _on_close(self) -> None:
        for view in self._views.values():
            view.stop()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        if w >= self.WINDOW_MIN_WIDTH and h >= self.WINDOW_MIN_HEIGHT:
            self._settings.window_width = w
            self._settings.window_height = h
            self._settings.window_x = self._root.winfo_x()
            self._settings.window_y = self._root.winfo_y()
        self._settings.save()
        self._root.destroy()
