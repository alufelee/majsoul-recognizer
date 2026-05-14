"""实时识别测试脚本

使用 MajsoulBot 预训练模型实时识别雀魂游戏画面。
按 Ctrl+C 退出。

用法:
    python tools/live_recognize.py
"""

import cv2
import logging
import time

# 抑制 OCR 不可用警告
logging.getLogger("majsoul_recognizer").setLevel(logging.ERROR)

from majsoul_recognizer.capture.finder import create_finder
from majsoul_recognizer.capture.screenshot import ScreenCapture
from majsoul_recognizer.recognition.config import RecognitionConfig
from majsoul_recognizer.recognition.engine import RecognitionEngine
from majsoul_recognizer.pipeline import CapturePipeline

# 牌面显示名称
_DISPLAY = {
    **{f"{i}m": f"{i}万" for i in range(1, 10)},
    **{f"{i}p": f"{i}筒" for i in range(1, 10)},
    **{f"{i}s": f"{i}索" for i in range(1, 10)},
    "1z": "东", "2z": "南", "3z": "西", "4z": "北",
    "5z": "白", "6z": "发", "7z": "中",
}


def display_hand(hand: list[str]) -> str:
    return " ".join(_DISPLAY.get(t, t) for t in hand)


def main():
    config = RecognitionConfig()
    config.detection_confidence = 0.25
    engine = RecognitionEngine(config)
    pipeline = CapturePipeline()

    print("寻找游戏窗口...")
    finder = create_finder()
    # 列出所有窗口并找到雀魂
    windows = finder.list_windows()
    window = None
    for w in windows:
        if "雀魂" in w.title and w.width < 3000:
            window = w
            break
    if window is None:
        print("未找到雀魂窗口，请确保游戏已打开")
        return
    print(f"游戏窗口: {window.title} ({window.width}x{window.height})")

    with ScreenCapture() as capture:
        print("开始实时识别 (Ctrl+C 退出)...\n")

        frame_count = 0
        while True:
            img = capture.capture_window(window)
            if img is None:
                time.sleep(0.5)
                continue

            frame_count += 1
            result = pipeline.process_image(img)

            if not result.is_static or not result.zones:
                continue

            gs = engine.recognize(
                result.zones,
                full_image=img,
                zone_rects=result.zone_rects,
            )

            parts = [f"[帧{frame_count}]"]
            if gs.hand:
                hand_str = display_hand(gs.hand)
                drawn = display_hand([gs.drawn_tile]) if gs.drawn_tile else ""
                dora_str = display_hand(gs.dora_indicators) if gs.dora_indicators else "无"
                parts.append(f"手牌({len(gs.hand)}): {hand_str}")
                if drawn:
                    parts.append(f"摸牌: {drawn}")
                parts.append(f"宝牌: {dora_str}")
            if gs.round_info:
                ri = gs.round_info
                parts.append(f"局次: {ri.wind}{ri.number}局 本场{ri.honba}")
            if gs.scores:
                score_str = " ".join(f"{k}={v}" for k, v in gs.scores.items())
                parts.append(f"分数: {score_str}")
            if gs.timer_remaining is not None:
                m, s = divmod(gs.timer_remaining, 60)
                parts.append(f"计时: {m:02d}:{s:02d}")
            if gs.warnings:
                parts.append(f"⚠ {gs.warnings}")
            if len(parts) > 1:
                print("  ".join(parts))

            time.sleep(1.0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已退出")
