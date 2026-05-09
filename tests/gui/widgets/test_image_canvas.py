"""ImageCanvas 测试

需要 tkinter + Pillow。无 tkinter 环境自动跳过。
"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk

import numpy as np

from majsoul_recognizer.gui.widgets.image_canvas import ImageCanvas
from majsoul_recognizer.gui.theme import Theme


@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    yield root
    root.destroy()


@pytest.fixture
def canvas(tk_root):
    c = ImageCanvas(tk_root, Theme.DARK, width=400, height=300)
    c.pack()
    tk_root.update_idletasks()
    return c


class TestImageCanvasBasic:
    def test_creation(self, canvas):
        assert canvas._mode == "detection"
        assert canvas._photo is None
        assert canvas._pending_image is None

    def test_clear(self, canvas):
        canvas._pending_image = np.zeros((10, 10, 3))
        canvas.clear()
        assert canvas._photo is None
        assert canvas._pending_image is None

    def test_set_mode(self, canvas):
        canvas.set_mode("zones")
        assert canvas._mode == "zones"
        canvas.set_mode("detection")
        assert canvas._mode == "detection"

    def test_on_theme_changed(self, canvas):
        canvas.on_theme_changed(Theme.LIGHT)
        assert canvas._theme is Theme.LIGHT


class TestImageCanvasShowImage:
    def test_show_image_stores_pending_when_unmapped(self, canvas):
        """窗口未映射时缓存图像"""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        canvas.winfo_height = lambda: 1
        canvas.winfo_width = lambda: 1
        canvas.show_image(image)
        assert canvas._pending_image is not None

    def test_show_image_creates_photo(self, canvas):
        """正常尺寸时生成 PhotoImage"""
        canvas.winfo_height = lambda: 300
        canvas.winfo_width = lambda: 400
        canvas.winfo_reqheight = lambda: 300
        canvas.winfo_reqwidth = lambda: 400

        image = np.full((200, 200, 3), 128, dtype=np.uint8)
        canvas.show_image(image)
        assert canvas._photo is not None
        assert canvas._scale > 0


class TestImageCanvasDetections:
    def test_set_detections(self, canvas):
        """设置检测框数据"""
        from majsoul_recognizer.types import BBox, Detection
        det = Detection(
            bbox=BBox(x=10, y=20, width=30, height=40),
            tile_code="1m",
            confidence=0.95,
        )
        canvas.set_detections([det])
        assert len(canvas._detections) == 1
        assert canvas._detections[0].tile_code == "1m"

    def test_set_zones(self, canvas):
        """设置区域矩形"""
        from majsoul_recognizer.gui.widgets.colors import ZONE_COLORS
        zones = {"hand": (10, 20, 100, 50)}
        canvas.set_zones(zones, ZONE_COLORS)
        assert "hand" in canvas._zone_rects


class TestToCanvasCoords:
    def test_coordinate_transform(self, canvas):
        """坐标转换：原始坐标 → Canvas 坐标"""
        canvas._scale = 0.5
        canvas._offset = (10, 20)
        x1, y1, x2, y2 = canvas._to_canvas_coords(100, 200, 50, 80)
        assert x1 == 60
        assert y1 == 120
        assert x2 == 85
        assert y2 == 160
