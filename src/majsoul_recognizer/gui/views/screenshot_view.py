"""截图模式视图 — 加载截图文件 → 执行识别 → 展示结果。"""

from __future__ import annotations

import tkinter.filedialog as filedialog
import tkinter.ttk as ttk

import cv2
import numpy as np

from majsoul_recognizer.gui.base_view import BaseView
from majsoul_recognizer.gui.widgets.image_canvas import ImageCanvas
from majsoul_recognizer.gui.widgets.result_panel import ResultPanel
from majsoul_recognizer.types import FrameResult, GameState

try:
    from tkinterdnd2 import DND_FILES
    _HAS_DND = True
except ImportError:
    _HAS_DND = False


class ScreenshotView(BaseView):
    """截图模式视图"""

    def __init__(self, parent, app_state, theme, on_result=None, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        self._current_image: np.ndarray | None = None
        self._current_frame: FrameResult | None = None
        self._current_state: GameState | None = None
        self._on_result = on_result
        self._is_busy = False

        # 布局: 左侧画布 + 右侧结果面板
        self._canvas = ImageCanvas(self, theme)
        self._canvas.pack(side="left", fill="both", expand=True)

        self._result_panel = ResultPanel(self, theme)
        self._result_panel.pack(side="right", fill="y")

        # 底部工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(side="bottom", fill="x")

        self._open_button = ttk.Button(toolbar, text="打开文件", command=self._on_open_file)
        self._open_button.pack(side="left", padx=4, pady=4)

        self._recognize_button = ttk.Button(toolbar, text="识别", command=self._on_recognize)
        self._recognize_button.pack(side="left", padx=4, pady=4)

        self._status_label = ttk.Label(toolbar, text="就绪")
        self._status_label.pack(side="left", padx=8)

        if _HAS_DND:
            self._canvas.drop_target_register(DND_FILES)
            self._canvas.dnd_bind("<<Drop>>", self._on_drop)

    def recognize(self, image: np.ndarray) -> None:
        """执行识别"""
        worker = self._ensure_worker()
        if not worker.submit(image):
            self._status_label.config(text="正在处理中，请稍候...")
            return
        self._current_image = image
        self._is_busy = True
        self._open_button.config(state="disabled")
        self._recognize_button.config(state="disabled")
        self._status_label.config(text="识别中...")
        self.after(50, self._poll_result)

    def _poll_result(self) -> None:
        if self._worker is None:
            return
        result = self._worker.get_result()
        if result is not None:
            self._is_busy = False
            self._open_button.config(state="normal")
            self._recognize_button.config(state="normal")
            if result.is_error:
                self._status_label.config(text=f"错误: {result.error}")
            else:
                self._current_frame = result.frame
                self._current_state = result.state
                self._update_display(result.image, result.frame, result.state, result.detections)
                self._status_label.config(text="就绪")
                if result.frame is not None and self._on_result:
                    self._on_result(result.image, result.frame, result.state,
                                    detections=getattr(result, "detections", []))
        else:
            self.after(50, self._poll_result)

    def _update_display(self, image, frame, state, detections=None) -> None:
        if image is not None:
            if detections:
                self._canvas.set_detections(detections)
            self._canvas.show_image(image)
        self._result_panel.update_state(state)

    def _on_open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择截图文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp"), ("所有文件", "*.*")],
        )
        if path:
            image = cv2.imread(path)
            if image is not None:
                self._canvas.show_image(image)
                self._current_image = image
                self._status_label.config(text=f"已加载: {path}")
            else:
                self._status_label.config(text="无法读取图像文件")

    def _on_recognize(self) -> None:
        if self._current_image is not None:
            self.recognize(self._current_image)
        else:
            self._status_label.config(text="请先加载截图文件")

    def _on_drop(self, event) -> None:
        path = event.data.strip("{}")
        image = cv2.imread(path)
        if image is not None:
            self._canvas.show_image(image)
            self._current_image = image
            self.recognize(image)

    def on_theme_changed(self, theme: dict) -> None:
        super().on_theme_changed(theme)
        self._canvas.on_theme_changed(theme)
        self._result_panel.on_theme_changed(theme)
