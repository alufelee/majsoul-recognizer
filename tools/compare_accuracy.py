"""YOLO-only vs YOLO+ViT accuracy comparison on real validation dataset.

Uses the 400 validation images with ground truth labels to compare
tile classification accuracy between YOLO detection alone and
YOLO detection + ViT reclassification.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cv2
import numpy as np
from collections import defaultdict

# Dataset class ID → tile_code mapping
DATASET_NAMES = {
    0: "1m", 1: "2m", 2: "3m", 3: "4m", 4: "5m",
    5: "6m", 6: "7m", 7: "8m", 8: "9m",
    9: "1p", 10: "2p", 11: "3p", 12: "4p", 13: "5p",
    14: "6p", 15: "7p", 16: "8p", 17: "9p",
    18: "1s", 19: "2s", 20: "3s", 21: "4s", 22: "5s",
    23: "6s", 24: "7s", 25: "8s", 26: "9s",
    27: "1z", 28: "2z", 29: "3z", 30: "4z",
    31: "5z", 32: "6z", 33: "7z",
    34: "5mr", 35: "5pr", 36: "5sr",
    37: "back", 38: "rotated", 39: "dora_frame",
}


def load_ground_truth(label_path: str, img_w: int, img_h: int):
    """Load YOLO-format ground truth: class_id, cx, cy, w, h (normalized)."""
    boxes = []
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            cls_id = int(parts[0])
            cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            # Convert to pixel coords (x1, y1, x2, y2)
            x1 = int((cx - w / 2) * img_w)
            y1 = int((cy - h / 2) * img_h)
            x2 = int((cx + w / 2) * img_w)
            y2 = int((cy + h / 2) * img_h)
            tile_code = DATASET_NAMES.get(cls_id, f"cls{cls_id}")
            boxes.append((cls_id, tile_code, x1, y1, x2, y2))
    return boxes


def iou(box1, box2):
    """Compute IoU between two boxes (x1,y1,x2,y2)."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0


def match_detections(gt_boxes, det_boxes, iou_thresh=0.3):
    """Match detections to ground truth by IoU. Returns matched pairs."""
    matched = []
    used_gt = set()
    used_det = set()
    # Sort by IoU descending
    pairs = []
    for gi, gt in enumerate(gt_boxes):
        for di, det in enumerate(det_boxes):
            score = iou((gt[2], gt[3], gt[4], gt[5]),
                       (det[0], det[1], det[2], det[3]))
            if score >= iou_thresh:
                pairs.append((score, gi, di))
    pairs.sort(reverse=True)
    for score, gi, di in pairs:
        if gi not in used_gt and di not in used_det:
            matched.append((gi, di, score))
            used_gt.add(gi)
            used_det.add(di)
    unmatched_gt = [i for i in range(len(gt_boxes)) if i not in used_gt]
    unmatched_det = [i for i in range(len(det_boxes)) if i not in used_det]
    return matched, unmatched_gt, unmatched_det


def run_yolo_only(detector, images_dir, labels_dir, confidence=0.25):
    """Run YOLO detection on all validation images."""
    results = {}
    for fname in sorted(os.listdir(images_dir)):
        if not fname.endswith(".png"):
            continue
        img_path = os.path.join(images_dir, fname)
        label_path = os.path.join(labels_dir, fname.replace(".png", ".txt"))

        img = cv2.imread(img_path)
        if img is None:
            continue

        gt_boxes = []
        if os.path.exists(label_path):
            gt_boxes = load_ground_truth(label_path, img.shape[1], img.shape[0])

        dets = detector.detect(img, confidence)
        det_boxes = [(d.bbox.x, d.bbox.y, d.bbox.x + d.bbox.width, d.bbox.y + d.bbox.height)
                     for d in dets]
        det_labels = [d.tile_code for d in dets]
        det_confs = [d.confidence for d in dets]

        results[fname] = {
            "gt": gt_boxes,
            "det_boxes": det_boxes,
            "det_labels": det_labels,
            "det_confs": det_confs,
        }
    return results


def run_vit_reclassify(classifier, img, det_boxes, threshold=0.5):
    """Run ViT on cropped detections, return updated labels."""
    crops = []
    for x1, y1, x2, y2 in det_boxes:
        crop = img[max(0, y1):min(img.shape[0], y2),
                   max(0, x1):min(img.shape[1], x2)]
        crops.append(crop)

    vit_results = classifier.classify_batch(crops)
    labels = []
    for tile_code, conf in vit_results:
        if tile_code and conf >= threshold:
            labels.append(tile_code)
        else:
            labels.append(None)  # Keep YOLO label
    return labels


def main():
    import argparse
    parser = argparse.ArgumentParser(description="YOLO vs YOLO+ViT accuracy comparison")
    parser.add_argument("--images", default="data/real/images/val",
                       help="Path to validation images directory")
    parser.add_argument("--labels", default="data/real/labels/val",
                       help="Path to validation labels directory")
    parser.add_argument("--model", default="models/tile_detector.onnx",
                       help="YOLO ONNX model path")
    parser.add_argument("--confidence", type=float, default=0.25,
                       help="YOLO confidence threshold")
    parser.add_argument("--vit-threshold", type=float, default=0.5,
                       help="ViT confidence threshold")
    parser.add_argument("--max-images", type=int, default=None,
                       help="Limit number of images to process")
    args = parser.parse_args()

    # Load YOLO detector
    from majsoul_recognizer.recognition.ultralytics_detector import UltralyticsTileDetector
    detector = UltralyticsTileDetector(args.model)
    print(f"YOLO model loaded: {args.model}")

    # Load ViT classifier
    classifier = None
    try:
        from majsoul_recognizer.recognition.tile_classifier import TileClassifier
        classifier = TileClassifier()
        print("ViT classifier loaded")
    except Exception as e:
        print(f"ViT classifier unavailable: {e}")
        print("Running YOLO-only comparison")

    # Collect stats
    stats = {
        "total_images": 0,
        "total_gt_tiles": 0,
        "yolo_correct": 0,
        "vit_correct": 0,
        "yolo_matched": 0,
        "vit_matched": 0,
        "yolo_mismatches": defaultdict(list),
        "vit_mismatches": defaultdict(list),
        "vit_changed": 0,
        "vit_improved": 0,
        "vit_worsened": 0,
        "yolo_unmatched_gt": 0,
        "yolo_false_positives": 0,
    }

    fnames = sorted(os.listdir(args.images))
    if args.max_images:
        fnames = fnames[:args.max_images]

    for fname in fnames:
        if not fname.endswith(".png"):
            continue

        img_path = os.path.join(args.images, fname)
        label_path = os.path.join(args.labels, fname.replace(".png", ".txt"))

        img = cv2.imread(img_path)
        if img is None:
            continue

        gt_boxes = []
        if os.path.exists(label_path):
            gt_boxes = load_ground_truth(label_path, img.shape[1], img.shape[0])

        if not gt_boxes:
            continue

        stats["total_images"] += 1
        stats["total_gt_tiles"] += len(gt_boxes)

        # YOLO detection
        dets = detector.detect(img, args.confidence)
        det_boxes = [(d.bbox.x, d.bbox.y, d.bbox.x + d.bbox.width, d.bbox.y + d.bbox.height)
                     for d in dets]
        yolo_labels = [d.tile_code for d in dets]

        # Match YOLO detections to ground truth
        matched, unmatched_gt, unmatched_det = match_detections(gt_boxes, det_boxes)
        stats["yolo_unmatched_gt"] += len(unmatched_gt)
        stats["yolo_false_positives"] += len(unmatched_det)

        # Evaluate YOLO accuracy
        for gi, di, iou_score in matched:
            gt_label = gt_boxes[gi][1]
            yolo_label = yolo_labels[di]
            stats["yolo_matched"] += 1
            if gt_label == yolo_label:
                stats["yolo_correct"] += 1
            else:
                stats["yolo_mismatches"][(gt_label, yolo_label)].append(fname)

        # ViT reclassification
        _NON_TILE_CLASSES = {"back", "rotated", "dora_frame"}
        if classifier is not None:
            vit_labels = list(yolo_labels)  # Start with YOLO labels
            # Only run ViT on tile detections, skip non-tile classes
            tile_indices = [i for i, lbl in enumerate(yolo_labels) if lbl not in _NON_TILE_CLASSES]
            if tile_indices:
                crops = []
                for i in tile_indices:
                    x1, y1, x2, y2 = det_boxes[i]
                    crop = img[max(0, y1):min(img.shape[0], y2),
                               max(0, x1):min(img.shape[1], x2)]
                    crops.append(crop)
                vit_results = classifier.classify_batch(crops)

                for j, (tile_code, conf) in enumerate(vit_results):
                    if tile_code and conf >= args.vit_threshold:
                        orig_i = tile_indices[j]
                        old_label = vit_labels[orig_i]
                        vit_labels[orig_i] = tile_code
                        if old_label != tile_code:
                            stats["vit_changed"] += 1

            # Evaluate ViT accuracy on same matches
            for gi, di, iou_score in matched:
                gt_label = gt_boxes[gi][1]
                vit_label = vit_labels[di]
                stats["vit_matched"] += 1
                if gt_label == vit_label:
                    stats["vit_correct"] += 1
                else:
                    stats["vit_mismatches"][(gt_label, vit_label)].append(fname)

                # Track improvement/worsening per-tile
                yolo_was_right = (gt_label == yolo_labels[di])
                vit_is_right = (gt_label == vit_label)
                if not yolo_was_right and vit_is_right:
                    stats["vit_improved"] += 1
                elif yolo_was_right and not vit_is_right:
                    stats["vit_worsened"] += 1

    # Print results
    print("\n" + "=" * 70)
    print("ACCURACY COMPARISON RESULTS")
    print("=" * 70)
    print(f"Images processed: {stats['total_images']}")
    print(f"Total ground truth tiles: {stats['total_gt_tiles']}")
    print(f"YOLO matched (IoU>=0.3): {stats['yolo_matched']}")
    print(f"YOLO unmatched GT tiles: {stats['yolo_unmatched_gt']}")
    print(f"YOLO false positives: {stats['yolo_false_positives']}")

    if stats["yolo_matched"] > 0:
        yolo_acc = stats["yolo_correct"] / stats["yolo_matched"] * 100
        print(f"\nYOLO classification accuracy: {yolo_acc:.1f}% "
              f"({stats['yolo_correct']}/{stats['yolo_matched']})")

    if classifier is not None and stats["vit_matched"] > 0:
        vit_acc = stats["vit_correct"] / stats["vit_matched"] * 100
        print(f"YOLO+ViT accuracy:           {vit_acc:.1f}% "
              f"({stats['vit_correct']}/{stats['vit_matched']})")
        print(f"\nViT changed labels: {stats['vit_changed']}")
        print(f"ViT improvements (wrong→right): {stats['vit_improved']}")
        print(f"ViT regressions (right→wrong):  {stats['vit_worsened']}")

    # Top YOLO mismatches
    if stats["yolo_mismatches"]:
        print(f"\nTop YOLO misclassifications (GT → YOLO):")
        sorted_mm = sorted(stats["yolo_mismatches"].items(), key=lambda x: -len(x[1]))
        for (gt, pred), files in sorted_mm[:15]:
            print(f"  {gt} → {pred}: {len(files)} times")

    # Top ViT mismatches
    if classifier is not None and stats["vit_mismatches"]:
        print(f"\nTop ViT misclassifications (GT → ViT):")
        sorted_mm = sorted(stats["vit_mismatches"].items(), key=lambda x: -len(x[1]))
        for (gt, pred), files in sorted_mm[:15]:
            print(f"  {gt} → {pred}: {len(files)} times")

    print("=" * 70)


if __name__ == "__main__":
    main()
