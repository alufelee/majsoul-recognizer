"""识别结果面板 — 以结构化文字展示 GameState 各字段，使用 Text 标签实现彩色输出。"""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.ttk as ttk

from majsoul_recognizer.types import GameState


class ResultPanel(ttk.Frame):
    """识别结果面板"""

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, **kwargs)
        self._theme = theme
        mono = "Menlo" if sys.platform == "darwin" else "Consolas"
        self._text = tk.Text(self, wrap="word", state="disabled",
                             font=(mono, 11), width=36,
                             bg=theme["bg_mantle"],
                             fg=theme["fg_primary"],
                             padx=12, pady=8)
        self._text.tag_configure("label", foreground=theme["fg_secondary"])
        self._text.tag_configure("value", foreground=theme["fg_primary"])
        self._text.tag_configure("highlight", foreground=theme["peach"])
        self._text.tag_configure("warning", foreground=theme["peach"])
        self._text.tag_configure("muted", foreground=theme["fg_muted"])
        self._text.pack(fill="both", expand=True)

    def update_state(self, state: GameState | None, latency_ms: float = 0) -> None:
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        if state is None:
            self._text.insert("end", "非静态帧 — 识别跳过", "muted")
        else:
            self._render_state(state, latency_ms)
        self._text.config(state="disabled")

    def on_theme_changed(self, theme: dict[str, str]) -> None:
        self._theme = theme
        self._text.configure(bg=theme["bg_mantle"], fg=theme["fg_primary"])
        self._text.tag_configure("label", foreground=theme["fg_secondary"])
        self._text.tag_configure("value", foreground=theme["fg_primary"])
        self._text.tag_configure("highlight", foreground=theme["peach"])
        self._text.tag_configure("warning", foreground=theme["peach"])
        self._text.tag_configure("muted", foreground=theme["fg_muted"])

    def _render_state(self, state: GameState, latency_ms: float = 0) -> None:
        t = self._text
        SEP = "━" * 30 + "\n"

        if state.round_info:
            ri = state.round_info
            t.insert("end", "局次: ", "label")
            t.insert("end", f"{ri.wind}{ri.number}局 {ri.honba}本场 {ri.kyotaku}供托\n", "value")
        else:
            t.insert("end", "局次: ", "label")
            t.insert("end", "-\n", "muted")

        t.insert("end", "宝牌: ", "label")
        t.insert("end", (" ".join(state.dora_indicators) if state.dora_indicators else "-"), "value")
        t.insert("end", "\n")
        t.insert("end", SEP)

        t.insert("end", "手牌: ", "label")
        t.insert("end", (" ".join(state.hand) if state.hand else "-"), "value")
        t.insert("end", "\n")

        if state.drawn_tile is not None:
            t.insert("end", "摸牌: ", "label")
            t.insert("end", f"{state.drawn_tile}\n", "highlight")
        t.insert("end", SEP)

        t.insert("end", "副露: ", "label")
        if state.calls:
            parts = []
            for player, groups in state.calls.items():
                for g in groups:
                    tiles_str = " ".join(g.tiles)
                    parts.append(f"{player}: [{tiles_str}]")
            t.insert("end", " ".join(parts), "value")
        else:
            t.insert("end", "-", "muted")
        t.insert("end", "\n")
        t.insert("end", SEP)

        t.insert("end", "分数:\n", "label")
        if state.scores:
            player_map = {"self": "自", "right": "右", "opposite": "对", "left": "左"}
            line1 = "  "
            for key in ("self", "right"):
                label = player_map.get(key, key)
                score = state.scores.get(key, "?")
                line1 += f"{label}: {score}  "
            t.insert("end", line1.rstrip() + "\n", "value")
            line2 = "  "
            for key in ("opposite", "left"):
                label = player_map.get(key, key)
                score = state.scores.get(key, "?")
                line2 += f"{label}: {score}  "
            t.insert("end", line2.rstrip() + "\n", "value")
        else:
            t.insert("end", "  -\n", "muted")
        t.insert("end", SEP)

        t.insert("end", "牌河:\n", "label")
        if state.discards:
            player_map = {"self": "自", "right": "右", "opposite": "对", "left": "左"}
            for key in ("self", "right", "opposite", "left"):
                tiles = state.discards.get(key, [])
                label = player_map.get(key, key)
                t.insert("end", f"  {label}: ", "label")
                t.insert("end", (" ".join(tiles) if tiles else "-"), "value")
                t.insert("end", "\n")
        else:
            t.insert("end", "  -\n", "muted")
        t.insert("end", SEP)

        t.insert("end", "动作: ", "label")
        t.insert("end", (" ".join(state.actions) if state.actions else "-"), "value")
        t.insert("end", "\n")

        if latency_ms > 0:
            t.insert("end", "延迟: ", "label")
            t.insert("end", f"{latency_ms:.0f}ms\n", "value")

        t.insert("end", "警告: ", "label")
        if state.warnings:
            t.insert("end", f"{len(state.warnings)}\n", "warning")
            for w in state.warnings:
                t.insert("end", f"  {w}\n", "warning")
        else:
            t.insert("end", "0\n", "value")
