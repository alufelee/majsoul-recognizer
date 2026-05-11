"""开发调试视图 — 展示区域分割图 + 检测框可视化 + JSON 输出 + 性能统计。
不使用 Worker（由 App 通过 update_data 推送数据）。"""

from __future__ import annotations

import json
import logging
import sys

import numpy as np
import tkinter as tk
import tkinter.ttk as ttk

from majsoul_recognizer.cli import format_output
from majsoul_recognizer.gui.base_view import BaseView
from majsoul_recognizer.gui.widgets.colors import ZONE_COLORS
from majsoul_recognizer.gui.widgets.image_canvas import ImageCanvas
from majsoul_recognizer.types import FrameResult, GameState

logger = logging.getLogger(__name__)


class DevView(BaseView):
    """开发调试视图"""

    def __init__(self, parent, app_state, theme, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        self._current_image: np.ndarray | None = None

        # 上半部分: 两个画布并排
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(side="top", fill="both", expand=True)

        self._zone_canvas = ImageCanvas(canvas_frame, theme)
        self._zone_canvas.pack(side="left", fill="both", expand=True)

        self._det_canvas = ImageCanvas(canvas_frame, theme)
        self._det_canvas.pack(side="left", fill="both", expand=True)

        # JSON 输出
        json_frame = ttk.Frame(self)
        json_frame.pack(side="top", fill="both", expand=True)

        mono = "Menlo" if sys.platform == "darwin" else "Consolas"
        self._json_text = tk.Text(
            json_frame,
            wrap="none",
            state="disabled",
            font=(mono, 10),
            bg=theme["bg_mantle"],
            fg=theme["fg_primary"],
            height=8,
        )
        json_scroll = ttk.Scrollbar(json_frame, orient="vertical", command=self._json_text.yview)
        self._json_text.configure(yscrollcommand=json_scroll.set)
        self._json_text.pack(side="left", fill="both", expand=True)
        json_scroll.pack(side="right", fill="y")

        # 底部: 性能 + 复制按钮
        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x")

        self._perf_label = ttk.Label(bottom, text="性能: --")
        self._perf_label.pack(side="left", padx=4, pady=4)

        self._copy_button = ttk.Button(bottom, text="复制 JSON", command=self._copy_json)
        self._copy_button.pack(side="right", padx=4, pady=4)

    def set_current_image(self, image: np.ndarray) -> None:
        self._current_image = image

    def update_data(
        self, frame: FrameResult, state: GameState | None, detections: list | None = None
    ) -> None:
        if self._current_image is not None:
            h, w = self._current_image.shape[:2]
            zone_rects = self._compute_zone_rects(w, h)

            self._zone_canvas.set_zones(zone_rects, ZONE_COLORS)
            self._zone_canvas.show_image(self._current_image)
            self._zone_canvas.set_mode("zones")

            if detections:
                self._det_canvas.set_detections(detections)
            self._det_canvas.show_image(self._current_image)
            self._det_canvas.set_mode("detection")

        output = format_output(frame, state)
        self._json_text.config(state="normal")
        self._json_text.delete("1.0", "end")
        self._json_text.insert("1.0", json.dumps(output, indent=2, ensure_ascii=False))
        self._json_text.config(state="disabled")

        self._perf_label.config(
            text=f"帧: {frame.frame_id} | {'静态' if frame.is_static else '动画'}"
        )

    def _compute_zone_rects(self, img_w: int, img_h: int) -> dict[str, tuple]:
        try:
            from majsoul_recognizer.zones.config import load_zone_config

            config_path = self._app_state.zone_config_path
            if config_path is None:
                return {}
            zone_config = load_zone_config(config_path)
            result = {}
            for zd in zone_config.zones.values():
                bbox = zd.to_bbox(img_w, img_h)
                result[zd.name.value] = (bbox.x, bbox.y, bbox.width, bbox.height)
            return result
        except Exception:
            logger.debug("Failed to compute zone rects", exc_info=True)
            return {}

    def _copy_json(self) -> None:
        text = self._json_text.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(text)

    def on_theme_changed(self, theme: dict) -> None:
        super().on_theme_changed(theme)
        self._zone_canvas.on_theme_changed(theme)
        self._det_canvas.on_theme_changed(theme)
        self._json_text.configure(bg=theme["bg_mantle"], fg=theme["fg_primary"])
