"""测试 MajsoulBot 预训练模型在真实游戏截图上的效果"""

import sys
from pathlib import Path

import cv2
import numpy as np

MODEL_PATH = Path("models/mahjong_majsoulbot.pt")
TEST_IMAGE = Path("debug_full_game.png")


def test_model():
    if not MODEL_PATH.exists():
        print(f"Model not found: {MODEL_PATH}")
        sys.exit(1)

    if not TEST_IMAGE.exists():
        print(f"Test image not found: {TEST_IMAGE}")
        sys.exit(1)

    from ultralytics import YOLO

    model = YOLO(str(MODEL_PATH))
    print(f"Model loaded: {MODEL_PATH}")
    print(f"Model class names: {model.names}")

    image = cv2.imread(str(TEST_IMAGE))
    print(f"Image shape: {image.shape}")

    # 方式1: 检测整张图
    print("\n=== Full image detection ===")
    results = model.predict(source=image, conf=0.25, augment=True)
    result = results[0]
    print(f"Detections: {len(result.boxes)}")
    for box in result.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        xyxy = box.xyxy[0].cpu().numpy()
        name = result.names[cls_id]
        print(f"  {name}: conf={conf:.3f} bbox=[{xyxy[0]:.0f},{xyxy[1]:.0f},{xyxy[2]:.0f},{xyxy[3]:.0f}]")

    # 方式2: 仿照 MajsoulBot 裁剪下方1/4区域
    print("\n=== Cropped bottom 1/4 (MajsoulBot style) ===")
    h, w = image.shape[:2]
    left, right = w // 10, w * 9 // 10
    top, bottom = h * 3 // 4, h
    cropped = image[top:bottom, left:right]
    print(f"Cropped shape: {cropped.shape}")

    results2 = model.predict(source=cropped, imgsz=(224, 1024), conf=0.25, augment=True)
    result2 = results2[0]
    print(f"Detections: {len(result2.boxes)}")
    for box in result2.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        xyxy = box.xyxy[0].cpu().numpy()
        name = result2.names[cls_id]
        # 还原到原图坐标
        orig_xyxy = [xyxy[0] + left, xyxy[1] + top, xyxy[2] + left, xyxy[3] + top]
        print(f"  {name}: conf={conf:.3f} bbox=[{orig_xyxy[0]:.0f},{orig_xyxy[1]:.0f},{orig_xyxy[2]:.0f},{orig_xyxy[3]:.0f}]")

    # 保存可视化结果
    vis = image.copy()
    for box in result2.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        xyxy = box.xyxy[0].cpu().numpy()
        name = result2.names[cls_id]
        x1, y1 = int(xyxy[0] + left), int(xyxy[1] + top)
        x2, y2 = int(xyxy[2] + left), int(xyxy[3] + top)
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(vis, f"{name} {conf:.2f}", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.imwrite("debug_majsoulbot_result.png", vis)
    print("\nSaved: debug_majsoulbot_result.png")


if __name__ == "__main__":
    test_model()
