"""ONNX 模型导出

将训练好的 YOLOv8 PyTorch 权重导出为 ONNX 格式。

用法:
    python -m tools.export_onnx --weights runs/train/weights/best.pt --output models/tile_detector.onnx
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_to_onnx(
    weights_path: Path,
    output_path: Path,
    imgsz: int = 640,
    simplify: bool = True,
) -> Path:
    """导出 YOLOv8 模型为 ONNX 格式

    Args:
        weights_path: PyTorch 权重文件路径 (best.pt)
        output_path: ONNX 输出路径
        imgsz: 输入图像尺寸
        simplify: 是否简化 ONNX 图

    Returns:
        导出的 ONNX 文件路径
    """
    from ultralytics import YOLO

    weights_path = Path(weights_path)
    output_path = Path(output_path)

    if not weights_path.exists():
        raise FileNotFoundError(f"Weights not found: {weights_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Exporting %s → %s (imgsz=%d)", weights_path, output_path, imgsz)

    model = YOLO(str(weights_path))
    model.export(
        format="onnx",
        imgsz=imgsz,
        simplify=simplify,
        opset=13,
    )

    # ultralytics 导出到 weights_path 同目录的 .onnx 文件
    auto_onnx = weights_path.with_suffix(".onnx")
    if auto_onnx != output_path and auto_onnx.exists():
        import shutil
        shutil.move(str(auto_onnx), str(output_path))

    if not output_path.exists():
        # 尝试在 weights 同目录查找
        alt = weights_path.parent / (weights_path.stem + ".onnx")
        if alt.exists() and alt != output_path:
            import shutil
            shutil.move(str(alt), str(output_path))

    assert output_path.exists(), f"ONNX export failed: {output_path} not found"
    logger.info("ONNX export complete: %s (%.1f MB)",
                output_path, output_path.stat().st_size / 1024 / 1024)
    return output_path


def verify_onnx_shape(onnx_path: Path) -> dict:
    """验证 ONNX 模型的输入输出 shape

    Returns:
        {"input": [1, 3, 640, 640], "output": [1, 44, 8400]}
    """
    import onnxruntime as ort

    session = ort.InferenceSession(str(onnx_path))
    input_info = session.get_inputs()[0]
    output_info = session.get_outputs()[0]

    result = {
        "input": input_info.shape,
        "output": output_info.shape,
    }

    expected_input = [1, 3, 640, 640]
    expected_output = [1, 44, 8400]

    if result["input"] != expected_input:
        logger.warning("Input shape %s != expected %s", result["input"], expected_input)
    if result["output"] != expected_output:
        logger.warning("Output shape %s != expected %s", result["output"], expected_output)

    logger.info("ONNX shape: input=%s, output=%s", result["input"], result["output"])
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse

    parser = argparse.ArgumentParser(description="导出 ONNX 模型")
    parser.add_argument("--weights", type=Path, required=True, help="PyTorch 权重路径")
    parser.add_argument("--output", type=Path, default=Path("models/tile_detector.onnx"))
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()

    onnx_path = export_to_onnx(args.weights, args.output, args.imgsz)
    verify_onnx_shape(onnx_path)
