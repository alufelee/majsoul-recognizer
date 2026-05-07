#!/bin/bash
set -euo pipefail

# 一键训练脚本：合成数据 → 训练 → 导出 ONNX
# 用法:
#   docker run -v $(pwd)/models:/app/models majsoul-train
#   docker run -v $(pwd)/models:/app/models majsoul-train --epochs 100 --num-train 500

EPOCHS=${1:-50}
NUM_TRAIN=${2:-100}
NUM_VAL=${3:-20}
DEVICE=${4:-cpu}
BATCH=${5:-4}
IMGSZ=${6:-320}

echo "=== Step 1: 生成合成训练数据 ==="
python -m tools.synthesize \
    --output data/synthetic \
    --num-train "$NUM_TRAIN" \
    --num-val "$NUM_VAL" \
    --tiles-per-image 8 \
    --seed 42

echo "=== Step 2: 训练 YOLOv8 模型 ($EPOCHS epochs, batch=$BATCH, imgsz=$IMGSZ, device=$DEVICE) ==="
python -m tools.train \
    --dataset config/dataset.yaml \
    --output runs \
    --epochs "$EPOCHS" \
    --imgsz "$IMGSZ" \
    --batch "$BATCH" \
    --device "$DEVICE"

echo "=== Step 3: 导出 ONNX 模型 ==="
python -m tools.export_onnx \
    --weights runs/train/weights/best.pt \
    --output models/tile_detector.onnx \
    --imgsz "$IMGSZ"

echo "=== 训练完成 ==="
ls -lh models/tile_detector.onnx
