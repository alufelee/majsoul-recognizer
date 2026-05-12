"""主窗口 — 应用入口

创建 Tkinter 根窗口，管理侧边栏导航，切换视图，维护全局状态。
"""

from __future__ import annotations

import logging
import math
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


class _SidebarIcon(tk.Canvas):
    """Sidebar icon button — HUD style, 44x44 for clear visibility"""

    _SIZE = 44

    def __init__(self, parent, theme: dict, icon_type: str,
                 command, **kwargs):
        super().__init__(parent, width=self._SIZE, height=self._SIZE,
                         bg=theme["bg_crust"],
                         highlightthickness=0, **kwargs)
        self._theme = theme
        self._command = command
        self._active = False
        self._icon_type = icon_type
        self._cx = self._SIZE // 2  # center x
        self._cy = self._SIZE // 2  # center y

        self._draw_icon(theme["fg_secondary"])
        self.bind("<Button-1>", lambda e: self._command())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.delete("active_bar")
        if active:
            # Accent bar on left edge — full height
            self.create_rectangle(0, 0, 3, self._SIZE,
                                  fill=self._theme["accent"],
                                  outline="", tags="active_bar")
            self.configure(bg=self._theme["accent_dim"])
            self._redraw(self._theme["accent"])
        else:
            self.configure(bg=self._theme["bg_crust"])
            self._redraw(self._theme["fg_muted"])

    def on_theme_changed(self, theme: dict) -> None:
        self._theme = theme
        color = theme["accent"] if self._active else theme["fg_muted"]
        bg = theme["accent_dim"] if self._active else theme["bg_crust"]
        self.configure(bg=bg)
        self._redraw(color)
        if self._active:
            self.delete("active_bar")
            self.create_rectangle(0, 0, 3, self._SIZE,
                                  fill=theme["accent"],
                                  outline="", tags="active_bar")

    def _on_enter(self, event):
        if not self._active:
            self.configure(bg=self._theme["bg_surface0"])
            self._redraw(self._theme["fg_secondary"])

    def _on_leave(self, event):
        if not self._active:
            self.configure(bg=self._theme["bg_crust"])
            self._redraw(self._theme["fg_muted"])

    def _redraw(self, color: str) -> None:
        self.delete("icon")
        self._draw_icon(color)

    def _draw_icon(self, color: str) -> None:
        cx, cy = self._cx, self._cy
        w = 2  # line width
        if self._icon_type == "screenshot":
            # Screenshot frame with crosshair
            s = 10  # half size
            self.create_rectangle(cx - s, cy - s, cx + s, cy + s,
                                  outline=color, width=w, tags="icon")
            # Crosshair lines inside
            self.create_line(cx, cy - 5, cx, cy + 5, fill=color,
                             width=1, tags="icon")
            self.create_line(cx - 5, cy, cx + 5, cy, fill=color,
                             width=1, tags="icon")
        elif self._icon_type == "live":
            # Signal broadcast — pulsing dot + arcs
            self.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                             fill=color, outline="", tags="icon")
            self.create_arc(cx - 8, cy - 8, cx + 8, cy + 8,
                            start=45, extent=90,
                            outline=color, style="arc", width=w, tags="icon")
            self.create_arc(cx - 13, cy - 13, cx + 13, cy + 13,
                            start=45, extent=90,
                            outline=color, style="arc", width=w, tags="icon")
        elif self._icon_type == "dev":
            # Terminal window with prompt
            s = 10
            self.create_rectangle(cx - s, cy - s + 2, cx + s, cy + s - 2,
                                  outline=color, width=w, tags="icon")
            # Window title bar line
            self.create_line(cx - s, cy - s + 6, cx + s, cy - s + 6,
                             fill=color, width=1, tags="icon")
            # Prompt lines
            self.create_line(cx - 7, cy, cx - 3, cy,
                             fill=color, width=w, tags="icon")
            self.create_line(cx - 7, cy + 4, cx + 4, cy + 4,
                             fill=color, width=1, tags="icon")


class App:
    """主窗口"""

    WINDOW_MIN_WIDTH = 960
    WINDOW_MIN_HEIGHT = 640
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 800
    SIDEBAR_WIDTH = 56

    NAV_ITEMS = ["screenshot", "live", "dev"]

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
        self._init_error: str | None = None
        try:
            engine = RecognitionEngine(config)
        except Exception as e:
            logger.warning("Engine init failed (degraded mode): %s", e)
            engine = None
            self._init_error = "检测器降级模式"

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
        import sys
        mono = "Menlo" if sys.platform == "darwin" else "Consolas"

        # Header bar — HUD style
        header_frame = tk.Frame(self._root, bg=theme["bg_mantle"])
        header_frame.pack(side="top", fill="x")

        header = tk.Frame(header_frame, bg=theme["bg_mantle"])
        header.pack(side="top", fill="x")

        # Title with accent color — monospace bold
        tk.Label(header, text="▸ 雀魂麻将识别助手", bg=theme["bg_mantle"],
                 fg=theme["accent"],
                 font=(mono, 13, "bold")).pack(side="left", padx=12, pady=6)
        # Version tag
        tk.Label(header, text="v0.1", bg=theme["bg_surface0"],
                 fg=theme["accent"],
                 font=(mono, 9), padx=4, pady=1).pack(side="left", padx=(0, 8), pady=6)

        # Right side: HUD status tag
        tk.Label(header, text="● 就绪", bg=theme["bg_mantle"],
                 fg=theme["green"],
                 font=(mono, 9)).pack(side="right", padx=(8, 4), pady=6)
        self._header_status = header.winfo_children()[-1]

        ttk.Button(header, text="切换主题",
                   command=self._toggle_theme).pack(side="right", padx=4, pady=4)
        ttk.Button(header, text="设置",
                   command=self._show_settings).pack(side="right", padx=4, pady=4)

        # Accent line separator with HUD tick marks
        border_canvas = tk.Canvas(header_frame, height=3, bg=theme["bg_mantle"],
                                  highlightthickness=0)
        border_canvas.pack(side="bottom", fill="x")
        self._header_border = border_canvas
        self._header_border.bind("<Configure>",
                                 lambda e: self._draw_hud_border(theme))

        body = ttk.Frame(self._root)
        body.pack(side="top", fill="both", expand=True)

        # Sidebar — HUD style with accent line separator
        sidebar_outer = tk.Frame(body, bg=theme["bg_crust"])
        sidebar_outer.pack(side="left", fill="y")

        sidebar = tk.Canvas(sidebar_outer, width=self.SIDEBAR_WIDTH,
                            bg=theme["bg_crust"], highlightthickness=0)
        sidebar.pack(side="left", fill="y", expand=True)

        # Right edge accent line
        sidebar_line = tk.Canvas(sidebar_outer, width=1, bg=theme["accent"],
                                 highlightthickness=0)
        sidebar_line.pack(side="right", fill="y")
        self._sidebar_line = sidebar_line

        self._nav_icons: dict[str, _SidebarIcon] = {}
        y_offset = 8
        for view_name in self.NAV_ITEMS:
            icon = _SidebarIcon(sidebar, theme, view_name,
                                command=lambda n=view_name: self._switch_view(n))
            sidebar.create_window(self.SIDEBAR_WIDTH // 2, y_offset + _SidebarIcon._SIZE // 2,
                                  window=icon)
            y_offset += _SidebarIcon._SIZE + 8
            self._nav_icons[view_name] = icon

        # Content area
        self._content = ttk.Frame(body)
        self._content.pack(side="left", fill="both", expand=True)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

    def _draw_hud_border(self, theme: dict) -> None:
        """Draw HUD-style accent line with tick marks"""
        c = self._header_border
        c.delete("all")
        w = c.winfo_width()
        accent = theme["accent"]
        dim = theme["bg_surface0"]
        # Main accent line
        c.create_line(0, 1, w, 1, fill=accent, width=1)
        # Tick marks at 20% intervals
        for i in range(1, 5):
            x = int(w * i / 5)
            c.create_line(x, 0, x, 3, fill=dim, width=1)

    def _switch_view(self, view_name: str) -> None:
        if self._active_view:
            self._active_view.stop()
            self._active_view.grid_remove()

        self._active_view = self._views[view_name]
        self._active_view.grid(row=0, column=0, sticky="nsew", in_=self._content)
        self._active_view.start()

        # Update nav icon active states
        for name, icon in self._nav_icons.items():
            icon.set_active(name == view_name)
        self._active_view_name = view_name

        if self._init_error:
            self._active_view.set_status_text(self._init_error)
            self._init_error = None

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

        self._draw_hud_border(new_theme)
        self._sidebar_line.configure(bg=new_theme["accent"])

        for icon in self._nav_icons.values():
            icon.on_theme_changed(new_theme)

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
            if self._active_view is not None:
                self._active_view.set_status_text(f"引擎重建失败: {e}")

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
