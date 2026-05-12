"""深色/浅色主题管理

Theme 类和 get_theme() 不依赖 tkinter。
apply_style() 内部延迟导入 tkinter，仅在运行时需要。

暗色玻璃 (dark) / 浅色玻璃 (light)
"""

from __future__ import annotations

from typing import Any


class Theme:
    """主题颜色方案 — 暗色玻璃 (dark) / 浅色玻璃 (light)"""

    DARK = {
        # 背景 — 深色 slate 层级
        "bg_base": "#0F172A",
        "bg_mantle": "#131C31",
        "bg_surface0": "#1E293B",
        "bg_surface1": "#273549",
        "bg_crust": "#0B1120",
        # 文字
        "fg_primary": "#F1F5F9",
        "fg_secondary": "#94A3B8",
        "fg_muted": "#64748B",
        # 强调 — 靛蓝
        "accent": "#5E6AD2",
        "accent_dim": "#2A305A",
        # 语义色
        "green": "#22C55E",
        "peach": "#F97316",
        "red": "#EF4444",
        "blue": "#3B82F6",
        "yellow": "#EAB308",
        "mauve": "#A855F7",
        "teal": "#14B8A6",
        "lavender": "#818CF8",
        "sky": "#0EA5E9",
        "flamingo": "#FB7185",
        # 交互
        "surface_hover": "#4F5BD5",
        # 玻璃质感
        "glass_border": "#334155",
        "glass_highlight": "#475569",
        "glass_shadow": "#0B1120",
    }

    LIGHT = {
        # 背景 — 浅灰层级
        "bg_base": "#F8FAFC",
        "bg_mantle": "#F1F5F9",
        "bg_surface0": "#E2E8F0",
        "bg_surface1": "#CBD5E1",
        "bg_crust": "#FFFFFF",
        # 文字
        "fg_primary": "#0F172A",
        "fg_secondary": "#475569",
        "fg_muted": "#94A3B8",
        # 强调
        "accent": "#4F46E5",
        "accent_dim": "#E0E7FF",
        # 语义色
        "green": "#16A34A",
        "peach": "#EA580C",
        "red": "#DC2626",
        "blue": "#2563EB",
        "yellow": "#CA8A04",
        "mauve": "#9333EA",
        "teal": "#0D9488",
        "lavender": "#6366F1",
        "sky": "#0284C7",
        "flamingo": "#E11D48",
        # 交互
        "surface_hover": "#6366F1",
        # 玻璃质感
        "glass_border": "#CBD5E1",
        "glass_highlight": "#E2E8F0",
        "glass_shadow": "#94A3B8",
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

    玻璃质感：surface0 按钮 + 微光边框 + 靛蓝强调。
    """
    import sys
    mono = "Menlo" if sys.platform == "darwin" else "Consolas"

    if "clam" in style.theme_names():
        style.theme_use("clam")

    # Global
    style.configure(".", background=theme["bg_base"],
                     foreground=theme["fg_primary"], borderwidth=0,
                     font=(mono, 10))
    style.configure("TFrame", background=theme["bg_base"])
    style.configure("TLabel", background=theme["bg_base"],
                     foreground=theme["fg_primary"],
                     font=(mono, 10))

    # Default button — surface0 + glass border
    style.configure("TButton", background=theme["bg_surface0"],
                     foreground=theme["fg_primary"], padding=(12, 6),
                     font=(mono, 9), relief="flat",
                     borderwidth=1, focuscolor=theme["accent"])
    style.map("TButton",
              background=[("active", theme["bg_surface1"]),
                          ("disabled", theme["bg_surface0"])],
              foreground=[("active", theme["accent"]),
                          ("disabled", theme["fg_muted"])])

    # Accent button
    style.configure("Accent.TButton", background=theme["accent"],
                     foreground="#FFFFFF", padding=(12, 6),
                     font=(mono, 9, "bold"))
    style.map("Accent.TButton",
              background=[("active", theme["surface_hover"]),
                          ("disabled", theme["bg_surface0"])],
              foreground=[("disabled", theme["fg_muted"])])

    # Small buttons
    style.configure("Small.TButton", background=theme["bg_surface0"],
                     foreground=theme["fg_primary"], padding=(8, 3),
                     font=(mono, 9))
    style.map("Small.TButton",
              background=[("active", theme["bg_surface1"])],
              foreground=[("active", theme["accent"])])

    style.configure("SmallAccent.TButton", background=theme["accent"],
                     foreground="#FFFFFF", padding=(8, 3),
                     font=(mono, 9, "bold"))
    style.map("SmallAccent.TButton",
              background=[("active", theme["surface_hover"])],
              foreground=[("active", "#FFFFFF")])

    # Panel labels
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
