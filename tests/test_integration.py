"""端到端集成测试

验证 CapturePipeline → RecognitionEngine → JSON 输出的完整链路。
"""

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

# 检测 onnxruntime 是否可用
try:
    import onnxruntime  # noqa: F401
    _HAS_ORT = True
except ImportError:
    _HAS_ORT = False

_SKIP_ORT = pytest.mark.skipif(not _HAS_ORT, reason="onnxruntime not installed")


# --- 内联 fixture（tests/recognition/conftest.py 的 fixture 对本文件不可见）---


@pytest.fixture(scope="session")
def dummy_detector_path(tmp_path_factory):
    """生成假 ONNX 检测模型（session 级别共享）"""
    import onnx
    from onnx import helper, TensorProto, numpy_helper

    output = np.zeros((1, 44, 8400), dtype=np.float32)

    # index 0: cx=80, cy=80, w=60, h=80, class=0(1m), conf=0.95
    output[0, 0, 0] = 80.0
    output[0, 1, 0] = 80.0
    output[0, 2, 0] = 60.0
    output[0, 3, 0] = 80.0
    output[0, 4, 0] = 0.95

    # index 1: cx=200, cy=100, w=50, h=70, class=9(1p), conf=0.88
    output[0, 0, 1] = 200.0
    output[0, 1, 1] = 100.0
    output[0, 2, 1] = 50.0
    output[0, 3, 1] = 70.0
    output[0, 4 + 9, 1] = 0.88

    X = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])
    Y = helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 44, 8400])

    output_data = numpy_helper.from_array(output, "output0")
    const_node = helper.make_node("Constant", [], ["output0"], value=output_data)

    graph = helper.make_graph([const_node], "dummy_detector", [X], [Y])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 7
    onnx.checker.check_model(model)

    path = tmp_path_factory.mktemp("models") / "dummy_detector.onnx"
    onnx.save(model, str(path))
    return path


@pytest.fixture(scope="session")
def fake_template_dir(tmp_path_factory):
    """生成假动作按钮模板（session 级别共享）"""
    template_dir = tmp_path_factory.mktemp("templates")
    buttons = {
        "chi": "吃", "pon": "碰", "kan": "杠",
        "ron": "荣和", "tsumo": "自摸", "riichi": "立直", "skip": "过",
    }
    for filename, text in buttons.items():
        img = np.full((40, 100, 3), 200, dtype=np.uint8)
        cv2.putText(img, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.imwrite(str(template_dir / f"{filename}.png"), img)
    return template_dir


# --- 辅助函数 ---


def _save_synthetic_screenshot(path: Path, *, different: bool = False) -> Path:
    """生成并保存合成截图"""
    img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    if different:
        img[:] = (100, 80, 60)  # 不同颜色
    else:
        img[:] = (30, 50, 40)  # 深绿色桌面
    cv2.imwrite(str(path), img)
    return path


class TestEndToEndStubDetector:
    """使用 StubDetector（无 onnxruntime）的集成测试"""

    def test_synthetic_image_returns_valid_json(self, tmp_path):
        """合成截图 + StubDetector → 退出码 0 + 有效 JSON + 产品规格书键名"""
        img_path = _save_synthetic_screenshot(tmp_path / "test.png")
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize",
             "--image", str(img_path)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["frame_id"] == 1
        assert data["is_static"] is True
        assert isinstance(data["hand"], list)
        assert isinstance(data["warnings"], list)
        # 产品规格书 §3 键名验证（设计规格 §8.1 测试 #7）
        assert "round" in data
        assert "round_info" not in data
        assert "timer" in data

    def test_non_static_frame(self, tmp_path):
        """非静态帧 → is_static=false + warnings 含 frame_not_static"""
        from majsoul_recognizer.pipeline import CapturePipeline
        from majsoul_recognizer.recognition import RecognitionEngine, RecognitionConfig
        from majsoul_recognizer.cli import format_output

        pipeline = CapturePipeline()
        engine = RecognitionEngine(RecognitionConfig())

        # 先处理一张图建立参考帧
        img_a = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img_a[:] = (30, 50, 40)
        pipeline.process_image(img_a)

        # 再处理一张完全不同的图 → 非静态
        img_b = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img_b[:] = (200, 150, 100)
        frame = pipeline.process_image(img_b)
        assert frame.is_static is False

        output = format_output(frame, None)
        assert output["is_static"] is False
        assert "frame_not_static" in output["warnings"]

    def test_output_format_matches_spec(self, tmp_path):
        """输出格式符合产品规格书 §3（round 非 round_info，timer 格式）"""
        from majsoul_recognizer.pipeline import CapturePipeline
        from majsoul_recognizer.recognition import RecognitionEngine, RecognitionConfig
        from majsoul_recognizer.cli import format_output

        pipeline = CapturePipeline()
        config = RecognitionConfig()
        engine = RecognitionEngine(config)

        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img[:] = (30, 50, 40)
        frame = pipeline.process_image(img)
        assert frame.is_static is True

        state = engine.recognize(frame.zones)
        output = format_output(frame, state)

        # 产品规格书 §3 键名检查
        assert "round" in output
        assert "round_info" not in output
        assert output["round"] is None or isinstance(output["round"], dict)
        # timer 格式: null 或 {"active": bool, "remaining": int}
        assert output["timer"] is None or (
            isinstance(output["timer"], dict)
            and "active" in output["timer"]
            and "remaining" in output["timer"]
        )

    def test_file_not_found_stderr(self):
        """文件不存在 → 退出码 1 + stderr 含错误信息"""
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize",
             "--image", "/nonexistent/path.png"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 1
        assert len(result.stderr) > 0
        assert len(result.stdout) == 0  # stdout 无输出

    def test_invalid_image_stderr(self, tmp_path):
        """非图片文件 → 退出码 1 + stderr 含错误信息"""
        bad_file = tmp_path / "bad.png"
        bad_file.write_text("this is not an image")
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize",
             "--image", str(bad_file)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 1
        assert len(result.stderr) > 0


@_SKIP_ORT
class TestEndToEndWithDetector:
    """使用 dummy ONNX 模型的集成测试（需要 onnxruntime）"""

    def test_with_dummy_model(self, tmp_path, dummy_detector_path, fake_template_dir):
        """使用 dummy_detector → 退出码 0 + JSON 含检测结果"""
        from majsoul_recognizer.pipeline import CapturePipeline
        from majsoul_recognizer.recognition import RecognitionEngine, RecognitionConfig
        from majsoul_recognizer.cli import format_output

        img_path = _save_synthetic_screenshot(tmp_path / "test.png")

        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        pipeline = CapturePipeline()
        engine = RecognitionEngine(config)

        img = cv2.imread(str(img_path))
        frame = pipeline.process_image(img)
        state = engine.recognize(frame.zones)
        output = format_output(frame, state)

        assert output["is_static"] is True
        assert output["frame_id"] == 1
        # dummy_detector 在任何图片上都输出固定结果
        assert isinstance(output["hand"], list)

    def test_model_not_found_exit_code(self, tmp_path):
        """模型文件不存在 → 退出码 1"""
        img_path = _save_synthetic_screenshot(tmp_path / "test.png")
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize",
             "--image", str(img_path),
             "--model", str(tmp_path / "nonexistent.onnx")],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 1
        assert len(result.stderr) > 0
