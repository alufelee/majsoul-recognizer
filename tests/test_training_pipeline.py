"""训练管线验证测试"""

import os
from pathlib import Path

import cv2
import numpy as np
import pytest


class TestSynthesizeData:
    """合成数据生成器测试"""

    def test_generate_tile_template(self):
        """生成单个牌面模板"""
        from tools.synthesize import generate_tile_template

        img = generate_tile_template("1m", width=60, height=80)
        assert img.shape == (80, 60, 3)
        assert img.dtype == np.uint8

    def test_generate_tile_template_all_classes(self):
        """所有 40 类牌面都能生成模板"""
        from tools.synthesize import CLASS_NAMES, generate_tile_template

        for name in CLASS_NAMES:
            img = generate_tile_template(name)
            assert img is not None
            assert img.size > 0

    def test_place_tiles_on_background(self):
        """在背景上放置牌面并生成标注"""
        from tools.synthesize import place_tiles

        bg = np.zeros((640, 640, 3), dtype=np.uint8)
        bg[:] = (30, 50, 40)

        tiles = [("1m", 50, 50), ("2m", 120, 50), ("3m", 190, 50)]
        image, labels = place_tiles(bg, tiles, tile_w=60, tile_h=80)

        assert image.shape == (640, 640, 3)
        assert len(labels) == 3
        # YOLO 格式: class x_center y_center width height (归一化)
        for cls, xc, yc, w, h in labels:
            assert 0 <= cls < 40
            assert 0 <= xc <= 1
            assert 0 <= yc <= 1
            assert 0 < w <= 1
            assert 0 < h <= 1

    def test_generate_dataset_creates_files(self, tmp_path):
        """生成完整数据集"""
        from tools.synthesize import generate_dataset

        output_dir = tmp_path / "synthetic"
        generate_dataset(
            output_dir=output_dir,
            num_train=10,
            num_val=4,
            tiles_per_image=8,
            seed=42,
        )

        # 检查目录结构
        train_img_dir = output_dir / "images" / "train"
        val_img_dir = output_dir / "images" / "val"
        train_lbl_dir = output_dir / "labels" / "train"
        val_lbl_dir = output_dir / "labels" / "val"

        assert train_img_dir.exists()
        assert val_img_dir.exists()
        assert train_lbl_dir.exists()
        assert val_lbl_dir.exists()

        # 检查文件数量
        train_images = list(train_img_dir.glob("*.png"))
        val_images = list(val_img_dir.glob("*.png"))
        train_labels = list(train_lbl_dir.glob("*.txt"))
        val_labels = list(val_lbl_dir.glob("*.txt"))

        assert len(train_images) == 10
        assert len(val_images) == 4
        assert len(train_labels) == 10
        assert len(val_labels) == 4

    def test_yolo_label_format(self, tmp_path):
        """YOLO 标注文件格式正确"""
        from tools.synthesize import generate_dataset

        output_dir = tmp_path / "synthetic"
        generate_dataset(output_dir=output_dir, num_train=2, num_val=1, seed=42)

        label_file = next((output_dir / "labels" / "train").glob("*.txt"))
        lines = label_file.read_text().strip().split("\n")
        for line in lines:
            parts = line.split()
            assert len(parts) == 5
            cls = int(parts[0])
            assert 0 <= cls < 40
            for val in parts[1:]:
                fval = float(val)
                assert 0 <= fval <= 1


# 训练相关依赖（ultralytics/PyTorch）在当前平台可能不可用
_HAS_ULTRALYTICS = False
try:
    import ultralytics
    _HAS_ULTRALYTICS = True
except ImportError:
    pass

_skip_no_ultralytics = pytest.mark.skipif(
    not _HAS_ULTRALYTICS,
    reason="ultralytics not available on this platform",
)

_HAS_ORT = False
try:
    import onnxruntime
    _HAS_ORT = True
except ImportError:
    pass

_skip_no_ort = pytest.mark.skipif(
    not _HAS_ORT,
    reason="onnxruntime not available on this platform",
)

_IS_SLOW = pytest.mark.skipif(
    os.environ.get("RUN_SLOW_TESTS") != "1",
    reason="Slow test (set RUN_SLOW_TESTS=1 to enable)",
)


class TestTrainScript:
    """训练脚本测试"""

    def test_train_imports(self):
        """训练脚本可导入"""
        from tools.train import train_model
        assert callable(train_model)

    @_skip_no_ultralytics
    def test_train_with_tiny_dataset(self, tmp_path):
        """小数据集训练 → 产出模型权重文件"""
        from tools.synthesize import generate_dataset
        from tools.train import train_model

        # 生成极小数据集
        data_dir = tmp_path / "data"
        generate_dataset(data_dir, num_train=8, num_val=4, tiles_per_image=4, seed=42)

        # 创建数据集配置
        dataset_yaml = tmp_path / "dataset.yaml"
        dataset_yaml.write_text(f"""
path: {data_dir}
train: images/train
val: images/val
names:
  0: 1m
  1: 2m
  2: 3m
  3: 4m
  4: 5m
  5: 6m
  6: 7m
  7: 8m
  8: 9m
  9: 1p
  10: 2p
  11: 3p
  12: 4p
  13: 5p
  14: 6p
  15: 7p
  16: 8p
  17: 9p
  18: 1s
  19: 2s
  20: 3s
  21: 4s
  22: 5s
  23: 6s
  24: 7s
  25: 8s
  26: 9s
  27: 1z
  28: 2z
  29: 3z
  30: 4z
  31: 5z
  32: 6z
  33: 7z
  34: 5mr
  35: 5pr
  36: 5sr
  37: back
  38: rotated
  39: dora_frame
""")

        output_dir = tmp_path / "runs"
        result = train_model(
            dataset_yaml=dataset_yaml,
            output_dir=output_dir,
            epochs=2,
            imgsz=640,
            batch=4,
            device="cpu",
        )

        # 验证训练产出
        assert result is not None
        best_weights = output_dir / "train" / "weights" / "best.pt"
        assert best_weights.exists(), f"best.pt not found at {best_weights}"


class TestExportOnnx:
    """ONNX 导出测试"""

    def test_export_imports(self):
        """导出脚本可导入"""
        from tools.export_onnx import export_to_onnx
        assert callable(export_to_onnx)

    @_skip_no_ultralytics
    @_skip_no_ort
    def test_verify_onnx_shape(self, tmp_path):
        """验证 ONNX 模型输出 shape 为 [1, 44, 8400]"""
        from tools.synthesize import generate_dataset
        from tools.train import train_model
        from tools.export_onnx import export_to_onnx

        # 训练极小模型
        data_dir = tmp_path / "data"
        generate_dataset(data_dir, num_train=6, num_val=3, tiles_per_image=4, seed=42)

        dataset_yaml = tmp_path / "dataset.yaml"
        dataset_yaml.write_text(f"path: {data_dir}\ntrain: images/train\nval: images/val\n"
                                + "names:\n" + "\n".join(f"  {i}: {n}" for i, n in enumerate(
                                    ["1m","2m","3m","4m","5m","6m","7m","8m","9m",
                                     "1p","2p","3p","4p","5p","6p","7p","8p","9p",
                                     "1s","2s","3s","4s","5s","6s","7s","8s","9s",
                                     "1z","2z","3z","4z","5z","6z","7z",
                                     "5mr","5pr","5sr","back","rotated","dora_frame"]
                                )))

        output_dir = tmp_path / "runs"
        best_pt = train_model(dataset_yaml=dataset_yaml, output_dir=output_dir,
                              epochs=2, imgsz=640, batch=4, device="cpu")
        assert best_pt is not None

        # 导出 ONNX
        onnx_path = tmp_path / "tile_detector.onnx"
        export_to_onnx(best_pt, onnx_path)

        # 验证文件存在
        assert onnx_path.exists()

        # 验证输出 shape
        import onnxruntime as ort
        session = ort.InferenceSession(str(onnx_path))
        input_shape = session.get_inputs()[0].shape
        output_shape = session.get_outputs()[0].shape

        assert input_shape == [1, 3, 640, 640], f"Unexpected input shape: {input_shape}"
        assert output_shape == [1, 44, 8400], f"Unexpected output shape: {output_shape}"

    @_skip_no_ultralytics
    @_skip_no_ort
    def test_onnx_model_works_with_tile_detector(self, tmp_path):
        """导出的 ONNX 模型能被 TileDetector 正确加载和推理"""
        from tools.synthesize import generate_dataset, place_tiles
        from tools.train import train_model
        from tools.export_onnx import export_to_onnx
        from majsoul_recognizer.recognition.tile_detector import TileDetector

        # 训练 + 导出
        data_dir = tmp_path / "data"
        generate_dataset(data_dir, num_train=6, num_val=3, tiles_per_image=4, seed=42)

        dataset_yaml = tmp_path / "dataset.yaml"
        dataset_yaml.write_text(f"path: {data_dir}\ntrain: images/train\nval: images/val\n"
                                + "names:\n" + "\n".join(f"  {i}: {n}" for i, n in enumerate(
                                    ["1m","2m","3m","4m","5m","6m","7m","8m","9m",
                                     "1p","2p","3p","4p","5p","6p","7p","8p","9p",
                                     "1s","2s","3s","4s","5s","6s","7s","8s","9s",
                                     "1z","2z","3z","4z","5z","6z","7z",
                                     "5mr","5pr","5sr","back","rotated","dora_frame"]
                                )))

        output_dir = tmp_path / "runs"
        best_pt = train_model(dataset_yaml=dataset_yaml, output_dir=output_dir,
                              epochs=2, imgsz=640, batch=4, device="cpu")
        onnx_path = tmp_path / "tile_detector.onnx"
        export_to_onnx(best_pt, onnx_path)

        # TileDetector 加载
        detector = TileDetector(onnx_path, nms_iou=0.55)

        # 推理合成图像
        bg = np.zeros((640, 640, 3), dtype=np.uint8)
        bg[:] = (30, 50, 40)
        image, _ = place_tiles(bg, [("1m", 50, 50), ("9p", 200, 100)])

        detections = detector.detect(image, confidence=0.3)
        assert isinstance(detections, list)


class TestAnnotateTool:
    """标注工具测试"""

    def test_annotate_imports(self):
        """标注脚本可导入"""
        from tools.annotate import annotate_image, Annotation
        assert callable(annotate_image)

    def test_annotate_synthetic_image(self):
        """标注工具能在合成图上检测到牌面"""
        from tools.synthesize import generate_tile_template, place_tiles
        from tools.annotate import annotate_image

        # 生成已知牌面的合成图
        bg = np.zeros((640, 640, 3), dtype=np.uint8)
        bg[:] = (30, 50, 40)
        tiles_info = [("1m", 50, 50), ("2m", 120, 50)]
        image, _ = place_tiles(bg, tiles_info, tile_w=60, tile_h=80)

        # 生成模板
        templates = {name: generate_tile_template(name) for name in ["1m", "2m"]}

        # 标注
        annotations = annotate_image(image, templates, confidence=0.7)

        assert len(annotations) >= 1  # 至少检测到一个
        for ann in annotations:
            assert ann.class_id < 40
            assert ann.x >= 0
            assert ann.y >= 0
            assert ann.width > 0
            assert ann.height > 0
            assert ann.confidence >= 0.7

    def test_annotation_to_yolo_format(self):
        """标注结果可转为 YOLO 格式"""
        from tools.annotate import Annotation

        ann = Annotation(class_id=0, x=50, y=50, width=60, height=80,
                         confidence=0.95, class_name="1m")
        yolo = ann.to_yolo(image_width=640, image_height=640)
        parts = yolo.split()
        assert len(parts) == 5
        assert int(parts[0]) == 0
        for val in parts[1:]:
            v = float(val)
            assert 0 <= v <= 1


@_IS_SLOW
class TestEndToEndPipeline:
    """端到端训练管线集成测试（慢速）

    验证: 合成数据 → 训练 → ONNX 导出 → TileDetector 推理
    需设置 RUN_SLOW_TESTS=1 启用
    """

    @pytest.fixture(scope="class")
    def trained_onnx(self, tmp_path_factory):
        """训练并导出 ONNX 模型（class 级共享）"""
        from tools.synthesize import generate_dataset
        from tools.train import train_model
        from tools.export_onnx import export_to_onnx

        tmp = tmp_path_factory.mktemp("e2e")

        # 1. 生成数据
        data_dir = tmp / "data"
        generate_dataset(data_dir, num_train=20, num_val=8, tiles_per_image=6, seed=42)

        # 2. 数据集配置
        dataset_yaml = tmp / "dataset.yaml"
        dataset_yaml.write_text(f"path: {data_dir}\ntrain: images/train\nval: images/val\n"
                                + "names:\n" + "\n".join(f"  {i}: {n}" for i, n in enumerate(
                                    ["1m","2m","3m","4m","5m","6m","7m","8m","9m",
                                     "1p","2p","3p","4p","5p","6p","7p","8p","9p",
                                     "1s","2s","3s","4s","5s","6s","7s","8s","9s",
                                     "1z","2z","3z","4z","5z","6z","7z",
                                     "5mr","5pr","5sr","back","rotated","dora_frame"]
                                )))

        # 3. 训练
        output_dir = tmp / "runs"
        best_pt = train_model(dataset_yaml=dataset_yaml, output_dir=output_dir,
                              epochs=3, imgsz=640, batch=4, device="cpu")
        assert best_pt is not None

        # 4. 导出
        onnx_path = tmp / "tile_detector.onnx"
        export_to_onnx(best_pt, onnx_path)
        assert onnx_path.exists()

        return onnx_path

    def test_pipeline_produces_valid_model(self, trained_onnx):
        """管线产出有效 ONNX 模型"""
        import onnxruntime as ort
        session = ort.InferenceSession(str(trained_onnx))
        output_shape = session.get_outputs()[0].shape
        assert output_shape == [1, 44, 8400]

    def test_model_detects_tiles_in_synthetic_image(self, trained_onnx):
        """模型能在合成图像上检测到牌面"""
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        from tools.synthesize import place_tiles

        detector = TileDetector(trained_onnx, nms_iou=0.55)

        bg = np.zeros((640, 640, 3), dtype=np.uint8)
        bg[:] = (30, 50, 40)
        image, _ = place_tiles(bg, [("1m", 100, 200), ("9p", 300, 200)])

        detections = detector.detect(image, confidence=0.25)
        assert len(detections) >= 1, "Should detect at least one tile in synthetic image"

    def test_model_integrates_with_engine(self, trained_onnx):
        """模型能集成到 RecognitionEngine"""
        from majsoul_recognizer.recognition import RecognitionEngine, RecognitionConfig

        config = RecognitionConfig(model_path=trained_onnx)
        engine = RecognitionEngine(config)

        # 构造空 zones
        zones = {
            "hand": np.zeros((100, 400, 3), dtype=np.uint8),
            "dora": np.zeros((50, 200, 3), dtype=np.uint8),
        }
        state = engine.recognize(zones)
        assert state is not None
        assert isinstance(state.hand, list)
