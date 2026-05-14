"""YOLO vs YOLO+ViT comparison on real game screenshots.

Tests on actual game screenshots from the project root, showing
detailed per-image results.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cv2
import numpy as np


def main():
    from majsoul_recognizer.recognition.ultralytics_detector import UltralyticsTileDetector

    detector = UltralyticsTileDetector("models/tile_detector.onnx")
    print("YOLO model loaded")

    classifier = None
    try:
        from majsoul_recognizer.recognition.tile_classifier import TileClassifier
        classifier = TileClassifier()
        print("ViT classifier loaded")
    except Exception as e:
        print(f"ViT unavailable: {e}")

    # Real game screenshots to test
    screenshots = [
        "game_capture.png",
        "game_capture_1080.png",
        "game_fresh.png",
        "game_fresh_1080.png",
        "game_live.png",
        "debug_current_game.png",
        "debug_full_game.png",
        "debug_live_frame.png",
        "debug_live_frame2.png",
        "debug_live_frame3.png",
        "debug_fresh_capture.png",
        "screenshot.png",
    ]

    _NON_TILE_CLASSES = {"back", "rotated", "dora_frame"}

    for fname in screenshots:
        path = os.path.join("F:/majong", fname)
        img = cv2.imread(path)
        if img is None:
            print(f"\n{'='*60}")
            print(f"SKIP {fname}: not found")
            continue

        print(f"\n{'='*60}")
        print(f"IMAGE: {fname} ({img.shape[1]}x{img.shape[0]})")

        # YOLO detection on full image
        dets = detector.detect(img, confidence=0.25)
        if not dets:
            print("  No detections")
            continue

        yolo_tiles = [d.tile_code for d in dets]
        print(f"  YOLO detected {len(dets)} tiles: {yolo_tiles}")

        # Show per-tile confidence
        for i, d in enumerate(dets):
            print(f"    [{i}] {d.tile_code} (conf={d.confidence:.3f}, "
                  f"bbox=({d.bbox.x},{d.bbox.y},{d.bbox.width},{d.bbox.height}))")

        # ViT reclassification
        if classifier is not None:
            tile_indices = [i for i, d in enumerate(dets) if d.tile_code not in _NON_TILE_CLASSES]
            if tile_indices:
                crops = []
                for i in tile_indices:
                    d = dets[i]
                    crop = img[max(0, d.bbox.y):min(img.shape[0], d.bbox.y + d.bbox.height),
                               max(0, d.bbox.x):min(img.shape[1], d.bbox.x + d.bbox.width)]
                    crops.append(crop)

                vit_results = classifier.classify_batch(crops)
                print(f"\n  ViT reclassification ({len(tile_indices)} tiles):")
                changes = 0
                for j, (tile_code, conf) in enumerate(vit_results):
                    orig_i = tile_indices[j]
                    yolo_tc = dets[orig_i].tile_code
                    changed = "CHANGED" if tile_code != yolo_tc and tile_code else ""
                    if tile_code != yolo_tc and tile_code:
                        changes += 1
                    print(f"    [{orig_i}] {yolo_tc} → {tile_code} (vit_conf={conf:.3f}) {changed}")
                print(f"  ViT changes: {changes}/{len(tile_indices)}")


if __name__ == "__main__":
    main()
