"""Card-based recognition result panel"""

import tkinter as tk
from tkinter import ttk

from majsoul_recognizer.types import GameState


class _SectionCard(tk.Frame):
    """Single card: HUD border + label row + value row

    Uses tk.Frame directly for bg control (ttk.Frame style bg is less reliable).
    """

    def __init__(self, parent, theme: dict[str, str], label: str,
                 color_token: str, **kwargs):
        super().__init__(parent, bg=theme["bg_crust"], highlightthickness=1,
                         highlightbackground=theme["glass_border"],
                         highlightcolor=theme[color_token], **kwargs)
        self._theme = theme
        self._color_key = color_token

        # Left accent line
        border = tk.Canvas(self, width=3, highlightthickness=0,
                           bg=theme["bg_crust"])
        border.pack(side="left", fill="y")
        self._border = border
        self._draw_border_accent(theme[color_token])

        self._inner = tk.Frame(self, bg=theme["bg_crust"])
        self._inner.pack(side="left", fill="both", expand=True, padx=(8, 6), pady=6)

        self._label = tk.Label(self._inner, text=label, bg=theme["bg_crust"],
                               fg=theme["fg_muted"],
                               font=("Menlo" if __import__("sys").platform == "darwin" else "Consolas", 9),
                               anchor="w")
        self._label.pack(anchor="w", fill="x")

        self._value = tk.Label(self._inner, text="-", bg=theme["bg_crust"],
                               fg=theme["fg_primary"],
                               font=("Menlo" if __import__("sys").platform == "darwin" else "Consolas", 10),
                               anchor="w", wraplength=180, justify="left")
        self._value.pack(anchor="w", fill="x", pady=(2, 0))

    def _draw_border_accent(self, color: str) -> None:
        """Draw accent line on the border canvas"""
        self._border.delete("all")
        self._border.create_line(1, 0, 1, 1000, fill=color, width=2)

    def update_value(self, text: str) -> None:
        self._value.config(text=text)

    def on_theme_changed(self, theme: dict[str, str]) -> None:
        self._theme = theme
        self.configure(bg=theme["bg_crust"],
                       highlightbackground=theme["glass_border"],
                       highlightcolor=theme[self._color_key])
        self._border.configure(bg=theme["bg_crust"])
        self._draw_border_accent(theme[self._color_key])
        self._inner.configure(bg=theme["bg_crust"])
        self._label.configure(bg=theme["bg_crust"], fg=theme["fg_muted"])
        self._value.configure(bg=theme["bg_crust"], fg=theme["fg_primary"])


class ResultPanel(tk.Frame):
    """Card-based recognition result panel — HUD style"""

    _CARD_DEFS: list[tuple[str, str]] = [
        ("局次", "blue"),
        ("宝牌", "yellow"),
        ("手牌", "green"),
        ("摸牌", "green"),
        ("副露", "peach"),
        ("分数", "mauve"),
        ("牌河", "teal"),
        ("动作", "sky"),
        ("警告", "red"),
    ]

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, bg=theme["bg_mantle"], **kwargs)
        self._theme = theme
        self.configure(width=240)
        self.pack_propagate(False)

        # Header row
        self._header = tk.Frame(self, bg=theme["bg_mantle"])
        self._header.pack(fill="x", padx=8, pady=(8, 4))
        self._header_label = tk.Label(self._header, text="识别结果", bg=theme["bg_mantle"],
                                      fg=theme["accent"],
                                      font=("Menlo" if __import__("sys").platform == "darwin" else "Consolas", 11, "bold"),
                                      anchor="w")
        self._header_label.pack(side="left")

        # Card list
        self._cards: list[_SectionCard] = []
        for label, color in self._CARD_DEFS:
            card = _SectionCard(self, theme, label, color)
            card.pack(fill="x", padx=6, pady=2)
            self._cards.append(card)

    def update_state(self, state: GameState | None,
                     latency_ms: float = 0) -> None:
        if state is None:
            for card in self._cards:
                card.update_value("-")
            return

        # 0: Round info
        ri = state.round_info
        if ri:
            self._cards[0].update_value(
                f"{ri.wind}{ri.number}局 {ri.honba}本场 {ri.kyotaku}供托")
        else:
            self._cards[0].update_value("-")

        # 1: Dora indicators
        if state.dora_indicators:
            self._cards[1].update_value(" ".join(state.dora_indicators))
        else:
            self._cards[1].update_value("-")

        # 2: Hand
        if state.hand:
            self._cards[2].update_value(" ".join(state.hand))
        else:
            self._cards[2].update_value("-")

        # 3: Drawn tile
        self._cards[3].update_value(state.drawn_tile or "-")

        # 4: Calls
        if state.calls:
            parts = []
            for player, groups in state.calls.items():
                for g in groups:
                    parts.append(" ".join(g.tiles))
            self._cards[4].update_value(" ".join(parts) if parts else "-")
        else:
            self._cards[4].update_value("-")

        # 5: Scores
        if state.scores:
            self._cards[5].update_value(
                " ".join(f"{v}" for v in state.scores.values()))
        else:
            self._cards[5].update_value("-")

        # 6: Discards
        if state.discards:
            parts = []
            for player, tiles in state.discards.items():
                parts.append(" ".join(tiles) if tiles else "-")
            self._cards[6].update_value(" | ".join(parts) if parts else "-")
        else:
            self._cards[6].update_value("-")

        # 7: Actions
        if state.actions:
            self._cards[7].update_value(str(len(state.actions)))
        else:
            self._cards[7].update_value("-")

        # 8: Warnings
        if state.warnings:
            self._cards[8].update_value(
                f"{len(state.warnings)}: " + ", ".join(state.warnings))
        else:
            self._cards[8].update_value("-")

    def on_theme_changed(self, theme: dict[str, str]) -> None:
        self._theme = theme
        self.configure(bg=theme["bg_mantle"])
        self._header.configure(bg=theme["bg_mantle"])
        self._header_label.configure(bg=theme["bg_mantle"], fg=theme["accent"])
        for card in self._cards:
            card.on_theme_changed(theme)
