"""深色/浅色主题管理

Theme 类和 get_theme() 不依赖 tkinter。
apply_style() 内部延迟导入 tkinter，仅在运行时需要。

Cyberpunk HUD (dark) / 冷光科技 (light)
"""

from __future__ import annotations

from typing import Any


class Theme:
    """主题颜色方案 — Cyberpunk HUD (dark) / 冷光科技 (light)"""

    DARK = {
        # 背景
        "bg_base": "#0a0a0f",
        "bg_mantle": "#0e0e16",
        "bg_surface0": "#1a1a2e",
        "bg_surface1": "#252540",
        "bg_crust": "#060609",
        # 文字
        "fg_primary": "#e0e0e8",
        "fg_secondary": "#8888a0",
        "fg_muted": "#4a4a6a",
        # 强调
        "accent": "#00ff88",
        "accent_dim": "#0a2a1a",
        # 语义色
        "green": "#00ff88",
        "peach": "#ff8844",
        "red": "#ff3366",
        "blue": "#00bbff",
        "yellow": "#ffcc00",
        "mauve": "#cc44ff",
        "teal": "#00ccaa",
        "lavender": "#8888ff",
        "sky": "#00ddee",
        "flamingo": "#ff6688",
        # 交互
        "surface_hover": "#00cc66",
        # HUD 专用
        "hud_line": "#00ff8840",
        "hud_accent": "#00ff88",
        "hud_dim": "#00ff8820",
    }

    LIGHT = {
        "bg_base": "#f0f2f5",
        "bg_mantle": "#e4e7ec",
        "bg_surface0": "#c8ccd4",
        "bg_surface1": "#b0b6c2",
        "bg_crust": "#d8dce4",
        "fg_primary": "#1a1a2e",
        "fg_secondary": "#4a4a6a",
        "fg_muted": "#8888a0",
        "accent": "#008844",
        "accent_dim": "#ccffee",
        "green": "#008844",
        "peach": "#cc5500",
        "red": "#cc0033",
        "blue": "#0066cc",
        "yellow": "#997700",
        "mauve": "#7722cc",
        "teal": "#008877",
        "lavender": "#4444cc",
        "sky": "#0088aa",
        "flamingo": "#cc3355",
        "surface_hover": "#00aa66",
        "hud_line": "#00884430",
        "hud_accent": "#008844",
        "hud_dim": "#00884415",
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

    使用等宽字体增加终端/科技感。
    """
    import sys
    mono = "Menlo" if sys.platform == "darwin" else "Consolas"

    if "clam" in style.theme_names():
        style.theme_use("clam")

    # Global — monospace base font
    style.configure(".", background=theme["bg_base"],
                     foreground=theme["fg_primary"], borderwidth=0,
                     font=(mono, 10))
    style.configure("TFrame", background=theme["bg_base"])
    style.configure("TLabel", background=theme["bg_base"],
                     foreground=theme["fg_primary"],
                     font=(mono, 10))

    # Default button — surface0 background with border
    style.configure("TButton", background=theme["bg_surface0"],
                     foreground=theme["fg_primary"], padding=(12, 4),
                     font=(mono, 9), relief="flat",
                     borderwidth=1, focuscolor=theme["accent"])
    style.map("TButton",
              background=[("active", theme["bg_surface1"]),
                          ("disabled", theme["bg_surface0"])],
              foreground=[("active", theme["accent"]),
                          ("disabled", theme["fg_muted"])])

    # Accent button — neon style
    style.configure("Accent.TButton", background=theme["accent"],
                     foreground=theme["bg_base"], padding=(12, 4),
                     font=(mono, 9, "bold"))
    style.map("Accent.TButton",
              background=[("active", theme["surface_hover"]),
                          ("disabled", theme["bg_surface0"])],
              foreground=[("disabled", theme["fg_muted"])])

    # Small status bar buttons
    style.configure("Small.TButton", background=theme["bg_surface0"],
                     foreground=theme["fg_primary"], padding=(8, 2),
                     font=(mono, 9))
    style.map("Small.TButton",
              background=[("active", theme["bg_surface1"])],
              foreground=[("active", theme["accent"])])

    style.configure("SmallAccent.TButton", background=theme["accent"],
                     foreground=theme["bg_base"], padding=(8, 2),
                     font=(mono, 9, "bold"))
    style.map("SmallAccent.TButton",
              background=[("active", theme["surface_hover"])],
              foreground=[("active", theme["bg_base"])])

    # Panel labels — accent colored headers
    style.configure("PanelHeader.TLabel", background=theme["bg_mantle"],
                     foreground=theme["accent"],
                     font=(mono, 11, "bold"))
    style.configure("CardLabel.TLabel", background=theme["bg_crust"],
                     foreground=theme["fg_muted"],
                     font=(mono, 9))
    style.configure("CardValue.TLabel", background=theme["bg_crust"],
                     foreground=theme["fg_primary"],
                     font=(mono, 10))

    # Status bar
    style.configure("StatusBar.TFrame", background=theme["bg_crust"])
    style.configure("Card.TFrame", background=theme["bg_crust"])
    style.configure("Status.TLabel", background=theme["bg_crust"],
                     foreground=theme["fg_muted"],
                     font=(mono, 9))

    # Entry
    style.configure("TEntry",
                    fieldbackground=theme["bg_surface0"],
                    foreground=theme["fg_primary"],
                    font=(mono, 10))
