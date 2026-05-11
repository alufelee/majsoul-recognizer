"""深色/浅色主题管理

Theme 类和 get_theme() 不依赖 tkinter。
apply_style() 内部延迟导入 tkinter，仅在运行时需要。
"""

from __future__ import annotations

from typing import Any


class Theme:
    """主题颜色方案 — Catppuccin Mocha (dark) / Latte (light)"""

    DARK = {
        "bg_base": "#1e1e2e",
        "bg_mantle": "#181825",
        "bg_surface0": "#313244",
        "bg_surface1": "#45475a",
        "bg_crust": "#11111b",
        "fg_primary": "#cdd6f4",
        "fg_secondary": "#bac2de",
        "fg_muted": "#6c7086",
        "accent": "#89b4fa",
        "accent_dim": "#1a3a5c",
        "green": "#a6e3a1",
        "peach": "#fab387",
        "red": "#f38ba8",
        "blue": "#89b4fa",
        "yellow": "#f9e2af",
        "mauve": "#cba6f7",
        "teal": "#94e2d5",
        "lavender": "#b4befe",
        "sky": "#89dceb",
        "flamingo": "#f2cdcd",
        "surface_hover": "#7287fd",
    }

    LIGHT = {
        "bg_base": "#eff1f5",
        "bg_mantle": "#e6e9ef",
        "bg_surface0": "#ccd0da",
        "bg_surface1": "#bcc0cc",
        "bg_crust": "#dce0e8",
        "fg_primary": "#4c4f69",
        "fg_secondary": "#5c5f77",
        "fg_muted": "#9ca0b0",
        "accent": "#1e66f5",
        "accent_dim": "#bbdefb",
        "green": "#40a02b",
        "peach": "#fe640b",
        "red": "#d20f39",
        "blue": "#1e66f5",
        "yellow": "#df8e1d",
        "mauve": "#8839ef",
        "teal": "#179299",
        "lavender": "#7287fd",
        "sky": "#04a5e5",
        "flamingo": "#dd7878",
        "surface_hover": "#585b70",
    }


def get_theme(name: str) -> dict[str, str]:
    """获取主题颜色方案（返回副本，防止外部修改常量）"""
    if name == "light":
        return dict(Theme.LIGHT)
    return dict(Theme.DARK)


def apply_style(style: Any, theme: dict[str, str]) -> None:
    """将主题应用到 ttk.Style 全局样式

    使用 'clam' 主题引擎以确保自定义颜色在所有平台生效。
    macOS 默认 'aqua' 主题会忽略 background/foreground 等自定义属性。
    """
    if "clam" in style.theme_names():
        style.theme_use("clam")

    # Global
    style.configure(".", background=theme["bg_base"],
                     foreground=theme["fg_primary"], borderwidth=0)
    style.configure("TFrame", background=theme["bg_base"])
    style.configure("TLabel", background=theme["bg_base"],
                     foreground=theme["fg_primary"])

    # Default button — surface0 background
    style.configure("TButton", background=theme["bg_surface0"],
                     foreground=theme["fg_primary"], padding=(12, 4))
    style.map("TButton",
              background=[("active", theme["bg_surface1"]),
                          ("disabled", theme["bg_surface0"])],
              foreground=[("active", theme["fg_primary"]),
                          ("disabled", theme["fg_muted"])])

    # Accent button
    style.configure("Accent.TButton", background=theme["accent"],
                     foreground="#ffffff", padding=(12, 4))
    style.map("Accent.TButton",
              background=[("active", theme["surface_hover"]),
                          ("disabled", theme["bg_surface0"])],
              foreground=[("disabled", theme["fg_muted"])])

    # Small status bar buttons
    style.configure("Small.TButton", background=theme["bg_surface0"],
                     foreground=theme["fg_primary"], padding=(8, 2))
    style.map("Small.TButton",
              background=[("active", theme["bg_surface1"])],
              foreground=[("active", theme["fg_primary"])])

    style.configure("SmallAccent.TButton", background=theme["accent"],
                     foreground="#ffffff", padding=(8, 2))
    style.map("SmallAccent.TButton",
              background=[("active", theme["surface_hover"])],
              foreground=[("active", "#ffffff")])

    # Panel labels
    style.configure("PanelHeader.TLabel", background=theme["bg_mantle"],
                     foreground=theme["fg_primary"], font=("", 11, "bold"))
    style.configure("CardLabel.TLabel", background=theme["bg_crust"],
                     foreground=theme["fg_secondary"], font=("", 9))
    style.configure("CardValue.TLabel", background=theme["bg_crust"],
                     foreground=theme["fg_primary"], font=("", 11))

    # Status bar
    style.configure("StatusBar.TFrame", background=theme["bg_crust"])
    style.configure("Card.TFrame", background=theme["bg_crust"])
    style.configure("Status.TLabel", background=theme["bg_crust"],
                     foreground=theme["fg_secondary"])

    # Entry
    style.configure("TEntry",
                    fieldbackground=theme["bg_surface0"],
                    foreground=theme["fg_primary"])
