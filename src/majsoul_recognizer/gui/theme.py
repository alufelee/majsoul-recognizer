"""深色/浅色主题管理

Theme 类和 get_theme() 不依赖 tkinter。
apply_style() 内部延迟导入 tkinter，仅在运行时需要。
"""

from __future__ import annotations

from typing import Any


class Theme:
    """主题颜色方案"""

    DARK = {
        "bg_primary": "#1a1a2e",
        "bg_secondary": "#16213e",
        "bg_tertiary": "#0f3460",
        "bg_sidebar": "#0d1b2a",
        "fg_primary": "#e0e0e0",
        "fg_secondary": "#a0a0a0",
        "fg_muted": "#666666",
        "accent": "#00d4ff",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#e94560",
        "highlight": "#ff5722",
        "border": "#2a2a4a",
        "canvas_bg": "#12122e",
    }

    LIGHT = {
        "bg_primary": "#f5f5f5",
        "bg_secondary": "#ffffff",
        "bg_tertiary": "#e8eaf6",
        "bg_sidebar": "#e0e0e0",
        "fg_primary": "#212121",
        "fg_secondary": "#616161",
        "fg_muted": "#9e9e9e",
        "accent": "#1565c0",
        "success": "#388e3c",
        "warning": "#f57c00",
        "error": "#d32f2f",
        "highlight": "#e64a19",
        "border": "#bdbdbd",
        "canvas_bg": "#eeeeee",
    }


def get_theme(name: str) -> dict[str, str]:
    """获取主题颜色方案"""
    if name == "light":
        return Theme.LIGHT
    return Theme.DARK


def apply_style(style: Any, theme: dict[str, str]) -> None:
    """将主题应用到 ttk.Style 全局样式"""
    style.configure(".", background=theme["bg_primary"],
                     foreground=theme["fg_primary"],
                     borderwidth=0)
    style.configure("TFrame", background=theme["bg_primary"])
    style.configure("TLabel", background=theme["bg_primary"],
                     foreground=theme["fg_primary"])
    style.configure("TButton", background=theme["bg_tertiary"],
                     foreground=theme["fg_primary"])
    style.map("TButton",
              background=[("active", theme["accent"])],
              foreground=[("active", "#ffffff")])
    style.configure("Sidebar.TFrame", background=theme["bg_sidebar"])
    style.configure("Sidebar.TButton", background=theme["bg_sidebar"],
                     foreground=theme["fg_primary"])
    style.configure("Status.TLabel", background=theme["bg_primary"],
                     foreground=theme["fg_secondary"])
