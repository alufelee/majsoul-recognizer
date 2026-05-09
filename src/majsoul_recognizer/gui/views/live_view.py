"""实时模式视图 — 连续捕获雀魂窗口画面 → 自动识别 → 实时更新结果。

状态机: 空闲 → 捕获中 → 暂停 → 捕获中
                 ↓ 窗口丢失
               等待重连 → 重置 → 空闲
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import tkinter.ttk as ttk

from majsoul_recognizer.capture.finder import create_finder
from majsoul_recognizer.capture.screenshot import ScreenCapture
from majsoul_recognizer.gui.base_view import BaseView
from majsoul_recognizer.gui.fps_counter import FPSCounter
from majsoul_recognizer.gui.widgets.image_canvas import ImageCanvas
from majsoul_recognizer.gui.widgets.result_panel import ResultPanel
from majsoul_recognizer.types import GameState

logger = logging.getLogger(__name__)


class LiveView(BaseView):
    """实时模式视图"""

    CAPTURE_INTERVAL = 0.2
    WINDOW_RETRY_INTERVAL = 2.0
    MAX_CONSECUTIVE_FAILS = 10

    def __init__(self, parent, app_state, theme, on_result=None, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        self._capture_thread: threading.Thread | None = None
        self._capture_stop = threading.Event()
        self._status_queue: queue.Queue = queue.Queue()
        self._fps_counter = FPSCounter()
        self._current_state: GameState | None = None
        self._on_result = on_result
        self._state: str = "idle"

        self._canvas = ImageCanvas(self, theme)
        self._canvas.pack(side="top", fill="both", expand=True)

        self._result_panel = ResultPanel(self, theme)
        self._result_panel.pack(side="top", fill="x")

        toolbar = ttk.Frame(self)
        toolbar.pack(side="bottom", fill="x")

        self._start_button = ttk.Button(toolbar, text="开始", command=self._on_start)
        self._start_button.pack(side="left", padx=4, pady=4)

        self._pause_button = ttk.Button(toolbar, text="暂停", command=self._on_pause)
        self._pause_button.pack(side="left", padx=4, pady=4)

        self._reset_button = ttk.Button(toolbar, text="重置", command=self._on_reset)
        self._reset_button.pack(side="left", padx=4, pady=4)

        self._fps_label = ttk.Label(toolbar, text="FPS: --")
        self._fps_label.pack(side="right", padx=8)

        self._status_label = ttk.Label(toolbar, text="就绪")
        self._status_label.pack(side="right", padx=8)

        self._update_buttons("idle")

    def _update_buttons(self, state: str) -> None:
        self._start_button.config(state="normal" if state in ("idle", "paused") else "disabled")
        self._pause_button.config(state="normal" if state == "capturing" else "disabled")
        self._reset_button.config(
            state="normal" if state in ("paused", "reconnecting") else "disabled"
        )
        self._state = state

    def _on_start(self) -> None:
        self._capture_stop.clear()
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        self._update_buttons("capturing")
        self.after(50, self._poll_result)

    def _on_pause(self) -> None:
        self._capture_stop.set()
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        self._update_buttons("paused")

    def _on_reset(self) -> None:
        self._capture_stop.set()
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        self._fps_counter = FPSCounter()
        self._canvas.clear()
        self._result_panel.update_state(None)
        self._current_state = None
        self._fps_label.config(text="FPS: --")
        self._status_label.config(text="就绪")
        self._update_buttons("idle")

    def _capture_loop(self) -> None:
        try:
            try:
                finder = create_finder()
            except RuntimeError:
                self._status_queue.put(("unsupported_platform", None))
                return

            with ScreenCapture() as capture:
                window = None
                consecutive_fails = 0

                while not self._capture_stop.is_set():
                    t0 = time.perf_counter()

                    if window is None:
                        window = finder.find_window()
                        if window is None:
                            self._status_queue.put(("window_not_found", None))
                            self._capture_stop.wait(self.WINDOW_RETRY_INTERVAL)
                            continue

                    image = capture.capture_window(window)
                    if image is None:
                        consecutive_fails += 1
                        if consecutive_fails >= self.MAX_CONSECUTIVE_FAILS:
                            window = None
                            consecutive_fails = 0
                        self._capture_stop.wait(0.1)
                        continue

                    consecutive_fails = 0
                    worker = self._ensure_worker()
                    worker.submit(image)
                    self._fps_counter.tick()

                    elapsed = time.perf_counter() - t0
                    remaining = max(0, self.CAPTURE_INTERVAL - elapsed)
                    self._capture_stop.wait(remaining)
        except Exception as e:
            self._status_queue.put(("capture_error", str(e)))

    def _poll_result(self) -> None:
        if self._state not in ("capturing", "reconnecting"):
            return

        while True:
            try:
                status_type, detail = self._status_queue.get_nowait()
                if status_type == "window_not_found":
                    self._status_label.config(text="未找到雀魂窗口，2秒后重试...")
                    self._update_buttons("reconnecting")
                elif status_type == "unsupported_platform":
                    self._status_label.config(text="不支持的平台")
                    self._update_buttons("idle")
                    return
                elif status_type == "capture_error":
                    self._status_label.config(text=f"捕获错误: {detail}")
                    self._update_buttons("idle")
                    return
            except queue.Empty:
                break

        if self._worker:
            result = self._worker.get_result()
            if result is not None and not result.is_error:
                if result.image is not None:
                    self._canvas.show_image(result.image)
                self._current_state = result.state
                self._result_panel.update_state(result.state)
                if result.frame is not None and self._on_result:
                    self._on_result(
                        result.image,
                        result.frame,
                        result.state,
                        detections=getattr(result, "detections", []),
                    )
                self._status_label.config(text="捕获中")
        fps = self._fps_counter.fps
        self._fps_label.config(text=f"FPS: {fps:.1f}")

        self.after(50, self._poll_result)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        self._capture_stop.set()
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        super().stop()

    def on_theme_changed(self, theme: dict) -> None:
        super().on_theme_changed(theme)
        self._canvas.on_theme_changed(theme)
        self._result_panel.on_theme_changed(theme)
