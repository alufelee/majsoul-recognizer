"""YOLOv8 训练脚本

使用 ultralytics 训练牌面检测模型。

用法:
    python -m tools.train --dataset config/dataset.yaml --epochs 50
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def train_model(
    dataset_yaml: Path,
    output_dir: Path | None = None,
    epochs: int = 50,
    imgsz: int = 640,
    batch: int = 16,
    device: str = "cpu",
    patience: int = 20,
    project_name: str = "tile_detector",
) -> Path | None:
    """训练 YOLOv8 模型

    Args:
        dataset_yaml: YOLO 数据集配置文件路径
        output_dir: 输出目录
        epochs: 训练轮数
        imgsz: 输入图像尺寸
        batch: 批次大小
        device: 训练设备 (cpu/0/1/...)
        patience: 早停耐心值
        project_name: 项目名称

    Returns:
        best.pt 权重文件路径，训练失败返回 None
    """
    from ultralytics import YOLO

    dataset_yaml = Path(dataset_yaml)
    if not dataset_yaml.exists():
        raise FileNotFoundError(f"Dataset config not found: {dataset_yaml}")

    # 初始化模型（YOLOv8n 最小版本，适合 CPU 训练）
    model = YOLO("yolov8n.pt")

    output_dir = output_dir or Path("runs")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting training: dataset=%s, epochs=%d, device=%s",
                dataset_yaml, epochs, device)

    results = model.train(
        data=str(dataset_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        patience=patience,
        project=str(output_dir),
        name="train",
        exist_ok=True,
        verbose=False,
        # 数据增强参数（来自 config/train_config.yaml）
        mosaic=1.0,
        mixup=0.1,
        copy_paste=0.3,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=0,
        translate=0.1,
        scale=0.5,
        fliplr=0,
        flipud=0,
    )

    best_path = output_dir / "train" / "weights" / "best.pt"
    if best_path.exists():
        logger.info("Training complete. Best weights: %s", best_path)
        return best_path

    logger.warning("Training completed but best.pt not found")
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse

    parser = argparse.ArgumentParser(description="训练 YOLOv8 牌面检测模型")
    parser.add_argument("--dataset", type=Path, default=Path("config/dataset.yaml"),
                        help="数据集配置文件")
    parser.add_argument("--output", type=Path, default=Path("runs"))
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()

    result = train_model(
        dataset_yaml=args.dataset,
        output_dir=args.output,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
    )
    if result is None:
        sys.exit(1)
