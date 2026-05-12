"""图像显示画布

在 Tkinter Canvas 上显示图像，支持检测框和区域标注叠加。
"""

from __future__ import annotations

import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk

from majsoul_recognizer.gui.widgets.colors import (
    _TILE_CATEGORY_COLORS,
    _get_tile_category,
)


class ImageCanvas(tk.Canvas):
    """图像显示画布"""

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, bg=theme["bg_crust"], **kwargs)
        self._theme = theme
        self._photo: ImageTk.PhotoImage | None = None
        self._detections: list = []
        self._zone_rects: dict[str, tuple] = {}
        self._zone_colors: dict[str, str] = {}
        self._show_boxes: bool = True
        self._show_confidence: bool = True
        self._mode: str = "detection"  # "detection" | "zones"
        self._pending_image: np.ndarray | None = None
        self._scale: float = 1.0
        self._offset: tuple[int, int] = (0, 0)
        self.bind("<Configure>", self._on_configure)

    def show_image(self, image: np.ndarray) -> None:
        """显示 BGR 图像（自动缩放适应画布尺寸）"""
        self._pending_image = None
        h, w = image.shape[:2]
        ch = max(self.winfo_height(), self.winfo_reqheight())
        cw = max(self.winfo_width(), self.winfo_reqwidth())
        if ch <= 1 or cw <= 1:
            self._pending_image = image
            return
        scale = min(cw / w, ch / h, 1.0)
        new_w, new_h = int(w * scale), int(h * scale)

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb).resize((new_w, new_h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(pil_img)

        self.delete("all")
        x_offset = (cw - new_w) // 2
        y_offset = (ch - new_h) // 2
        self.create_image(x_offset, y_offset, anchor="nw", image=self._photo)
        self._scale = scale
        self._offset = (x_offset, y_offset)

        if self._mode == "zones":
            self._draw_zones()
        else:
            self._draw_detections()

    def set_detections(self, detections: list) -> None:
        """设置检测框数据"""
        self._detections = detections

    def set_zones(self, zone_rects: dict[str, tuple], colors: dict[str, str]) -> None:
        """设置区域矩形 {name: (x, y, w, h) 像素坐标}"""
        self._zone_rects = zone_rects
        self._zone_colors = colors

    def set_mode(self, mode: str) -> None:
        """切换叠加模式: "detection" | "zones" """
        self._mode = mode

    def on_theme_changed(self, theme: dict[str, str]) -> None:
        """主题切换时更新背景色"""
        self._theme = theme
        self.configure(bg=theme["bg_crust"])

    def show_empty_state(self, hint_text: str) -> None:
        """Show centered empty state — glass style dashed border"""
        self.delete("all")
        self._photo = None
        cw = max(self.winfo_width(), self.winfo_reqwidth(), 200)
        ch = max(self.winfo_height(), self.winfo_reqheight(), 150)
        rw, rh = 56, 40
        rx, ry = (cw - rw) // 2, (ch - rh) // 2 - 12
        border = self._theme["glass_border"]
        dim = self._theme["fg_muted"]

        # Dashed rectangle
        self.create_rectangle(rx, ry, rx + rw, ry + rh,
                              outline=border, width=1, dash=(4, 4))

        self.create_text(cw // 2, ry + rh + 18, text=hint_text,
                         fill=dim, font=("", 10))

    def clear(self) -> None:
        """清空画布"""
        self.delete("all")
        self._photo = None
        self._pending_image = None

    def _on_configure(self, event) -> None:
        """窗口 resize 时重绘缓存的图像"""
        if self._pending_image is not None:
            img = self._pending_image
            self._pending_image = None
            self.show_image(img)

    def _to_canvas_coords(self, x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        """原始图像坐标 → Canvas 坐标（考虑缩放和偏移）"""
        ox, oy = self._offset
        s = self._scale
        return (int(x * s) + ox, int(y * s) + oy,
                int((x + w) * s) + ox, int((y + h) * s) + oy)

    def _draw_detections(self) -> None:
        """绘制检测框"""
        if self._photo is None:
            return
        for det in self._detections:
            x1, y1, x2, y2 = self._to_canvas_coords(
                det.bbox.x, det.bbox.y, det.bbox.width, det.bbox.height
            )
            color = _TILE_CATEGORY_COLORS.get(_get_tile_category(det.tile_code), "#9e9e9e")
            self.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
            label = f"{det.tile_code} ({det.confidence:.0%})" if self._show_confidence else det.tile_code
            self.create_text(x1, y1 - 4, anchor="sw", text=label,
                            fill=color, font=("Arial", 9))

    def _draw_zones(self) -> None:
        """绘制区域标注"""
        if self._photo is None:
            return
        for name, (x, y, w, h) in self._zone_rects.items():
            x1, y1, x2, y2 = self._to_canvas_coords(x, y, w, h)
            color = self._zone_colors.get(name, "#ffffff")
            self.create_rectangle(x1, y1, x2, y2, outline=color, width=2, dash=(4, 4))
            self.create_text(x1 + 4, y1 + 2, anchor="nw", text=name,
                            fill=color, font=("Arial", 9))
