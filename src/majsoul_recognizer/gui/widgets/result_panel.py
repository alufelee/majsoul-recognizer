"""Card-based recognition result panel"""

import tkinter as tk
from tkinter import ttk

from majsoul_recognizer.types import GameState


class _SectionCard(ttk.Frame):
    """Single card: left color border + label row + value row"""

    def __init__(self, parent, theme: dict[str, str], label: str,
                 color_token: str, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._theme = theme
        self._color_key = color_token

        border = tk.Canvas(self, width=2, highlightthickness=0,
                           bg=theme[color_token])
        border.pack(side="left", fill="y")
        self._border = border

        inner = ttk.Frame(self, style="Card.TFrame")
        inner.pack(side="left", fill="both", expand=True, padx=(8, 6), pady=6)

        self._label = ttk.Label(inner, text=label, style="CardLabel.TLabel")
        self._label.pack(anchor="w")

        self._value = ttk.Label(inner, text="-", style="CardValue.TLabel",
                                wraplength=180)
        self._value.pack(anchor="w", pady=(2, 0))

    def update_value(self, text: str) -> None:
        self._value.config(text=text)

    def on_theme_changed(self, theme: dict[str, str]) -> None:
        self._theme = theme
        self._border.configure(bg=theme[self._color_key])


class ResultPanel(ttk.Frame):
    """Card-based recognition result panel"""

    _CARD_DEFS: list[tuple[str, str]] = [
        ("局次", "blue"),
        ("宝牌", "blue"),
        ("手牌", "green"),
        ("摸牌", "green"),
        ("副露", "yellow"),
        ("分数", "mauve"),
        ("牌河", "teal"),
        ("动作", "peach"),
        ("警告", "red"),
    ]

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, **kwargs)
        self._theme = theme
        self.configure(width=240)
        self.pack_propagate(False)

        # Container background
        inner = ttk.Frame(self, style="StatusBar.TFrame")
        inner.pack(fill="both", expand=True)

        # Header row
        header = ttk.Frame(inner, style="StatusBar.TFrame")
        header.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(header, text="识别结果", style="PanelHeader.TLabel").pack(
            side="left")

        # Card list
        self._cards: list[_SectionCard] = []
        for label, color in self._CARD_DEFS:
            card = _SectionCard(inner, theme, label, color)
            card.pack(fill="x", padx=6, pady=3)
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
        for card in self._cards:
            card.on_theme_changed(theme)
