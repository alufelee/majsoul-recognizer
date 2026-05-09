"""设置弹窗"""

from __future__ import annotations

import dataclasses
import tkinter as tk
import tkinter.ttk as ttk
from typing import Callable

from majsoul_recognizer.gui.settings import GUISettings


class SettingsDialog:
    """设置弹窗 — 独立 Toplevel 对话框，关闭时检测未保存修改并自动应用。"""

    def __init__(self, parent: tk.Tk, settings: GUISettings,
                 on_apply: Callable[[], None]):
        self._dialog = tk.Toplevel(parent)
        self._dialog.title("设置")
        self._dialog.geometry("480x520")
        self._dialog.transient(parent)
        self._dialog.grab_set()
        self._settings = settings
        self._on_apply = on_apply
        self._initial_snapshot = dataclasses.asdict(settings)
        self._fields: dict[str, tk.Variable] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self._dialog, padding=12)
        main.pack(fill="both", expand=True)

        row = 0
        row = self._add_section(main, row, "识别设置")
        row = self._add_field(main, row, "模型路径", "model_path", self._settings.model_path or "")
        row = self._add_field(main, row, "模板目录", "template_dir", self._settings.template_dir or "")
        row = self._add_field(main, row, "区域配置", "config_path", self._settings.config_path or "")
        row = self._add_field(main, row, "检测置信度", "detection_confidence",
                              str(self._settings.detection_confidence))
        row = self._add_field(main, row, "NMS IoU 阈值", "nms_iou_threshold",
                              str(self._settings.nms_iou_threshold))

        row = self._add_section(main, row, "界面偏好")
        row = self._add_field(main, row, "捕获间隔(ms)", "capture_interval_ms",
                              str(self._settings.capture_interval_ms))

        row = self._add_section(main, row, "主题")
        self._theme_var = tk.StringVar(value=self._settings.theme)
        theme_frame = ttk.Frame(main)
        theme_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Radiobutton(theme_frame, text="深色", variable=self._theme_var, value="dark").pack(side="left")
        ttk.Radiobutton(theme_frame, text="浅色", variable=self._theme_var, value="light").pack(side="left")
        row += 1

        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=12)
        ttk.Button(btn_frame, text="应用", command=self._on_apply_clicked).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="关闭", command=self._on_close_clicked).pack(side="left", padx=4)

    def _add_section(self, parent, row, title) -> int:
        ttk.Label(parent, text=title, font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(8, 2))
        return row + 1

    def _add_field(self, parent, row, label, key, default) -> int:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(default))
        entry = ttk.Entry(parent, textvariable=var, width=40)
        entry.grid(row=row, column=1, sticky="ew", pady=2, padx=(8, 0))
        self._fields[key] = var
        return row + 1

    def _sync_to_settings(self) -> None:
        for key, var in self._fields.items():
            value = var.get()
            field_type = type(getattr(self._settings, key, ""))
            if value == "" and key.endswith("_path"):
                setattr(self._settings, key, None)
            elif field_type is float:
                try:
                    setattr(self._settings, key, float(value))
                except ValueError:
                    pass
            elif field_type is int:
                try:
                    setattr(self._settings, key, int(value))
                except ValueError:
                    pass
            else:
                setattr(self._settings, key, value)
        self._settings.theme = self._theme_var.get()

    def _on_apply_clicked(self) -> None:
        self._sync_to_settings()
        self._settings.save()
        self._on_apply()
        self._initial_snapshot = dataclasses.asdict(self._settings)

    def _on_close_clicked(self) -> None:
        self._sync_to_settings()
        if dataclasses.asdict(self._settings) != self._initial_snapshot:
            self._settings.save()
            self._on_apply()
        self._dialog.destroy()
