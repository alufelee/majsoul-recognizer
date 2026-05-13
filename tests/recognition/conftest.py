"""识别引擎测试共享 fixtures"""

from pathlib import Path

import numpy as np
import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def sample_bbox():
    """创建一个标准 BBox"""
    from majsoul_recognizer.types import BBox
    return BBox(x=10, y=20, width=60, height=80)


def make_detection(x, y, w, h, tile_code="1m", confidence=0.95, zone_name=None):
    """创建 Detection 的辅助函数"""
    from majsoul_recognizer.types import BBox, Detection, ZoneName
    zn = ZoneName(zone_name) if zone_name else None
    return Detection(
        bbox=BBox(x=x, y=y, width=w, height=h),
        tile_code=tile_code,
        confidence=confidence,
        zone_name=zn,
    )


@pytest.fixture(scope="session")
def dummy_detector_path(tmp_path_factory):
    """生成假 ONNX 检测模型（session 级别共享）"""
    import numpy as np
    import onnx
    from onnx import helper, TensorProto, numpy_helper

    output = np.zeros((1, 44, 8400), dtype=np.float32)

    # index 0: cx=80, cy=80, w=60, h=80, class=0(1m), conf=0.95
    output[0, 0, 0] = 80.0   # cx
    output[0, 1, 0] = 80.0   # cy
    output[0, 2, 0] = 60.0   # w
    output[0, 3, 0] = 80.0   # h
    output[0, 4, 0] = 0.95   # class 0 (1m)

    # index 1: cx=200, cy=100, w=50, h=70, class=9(1p), conf=0.88
    output[0, 0, 1] = 200.0
    output[0, 1, 1] = 100.0
    output[0, 2, 1] = 50.0
    output[0, 3, 1] = 70.0
    output[0, 4 + 9, 1] = 0.88  # class 9 (1p)

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
    import cv2

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


@pytest.fixture
def mock_vit_classifier():
    """Mock TileClassifier for engine tests"""
    from unittest.mock import MagicMock
    classifier = MagicMock()
    classifier.classify_batch.return_value = [("9s", 0.99)]
    return classifier
