"""CLI 入口测试"""

import json
import subprocess
import sys

import cv2
import numpy as np
import pytest

from majsoul_recognizer.cli import (
    build_capture_chain,
    capture_and_save,
    format_output,
    recognize_command,
)
from majsoul_recognizer.types import FrameResult, GameState, RoundInfo

# 检测 onnxruntime 是否可用
try:
    import onnxruntime  # noqa: F401

    _HAS_ORT = True
except ImportError:
    _HAS_ORT = False

_SKIP_ORT = pytest.mark.skipif(not _HAS_ORT, reason="onnxruntime not installed")


class TestBuildCaptureChain:
    """端到端串联测试"""

    def test_chain_returns_pipeline(self):
        """build_capture_chain 返回 CapturePipeline 实例"""
        from majsoul_recognizer.pipeline import CapturePipeline

        chain = build_capture_chain()
        assert isinstance(chain, CapturePipeline)
        assert hasattr(chain, "process_image")

    def test_chain_with_synthetic_image(self, sample_screenshot, tmp_path):
        """对合成图像执行完整链路并保存结果"""
        output_dir = tmp_path / "zones"
        capture_and_save(
            image=sample_screenshot,
            output_dir=output_dir,
        )
        # 验证输出了 14 个区域文件
        png_files = list(output_dir.glob("*.png"))
        assert len(png_files) == 14
        # 验证文件非空
        for f in png_files:
            assert f.stat().st_size > 0


class TestCLIModule:
    """python -m 入口测试"""

    def test_module_help(self):
        """python -m majsoul_recognizer --help 不报错"""
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "capture" in result.stdout or "usage" in result.stdout.lower()


class TestFormatOutput:
    """输出适配层测试"""

    def test_static_frame_with_empty_state(self):
        """静态帧 + 空 GameState → 完整 JSON 结构"""
        frame = FrameResult(frame_id=1, timestamp="2026-05-07T10:00:00+00:00")
        state = GameState()
        result = format_output(frame, state)

        assert result["frame_id"] == 1
        assert result["timestamp"] == "2026-05-07T10:00:00+00:00"
        assert result["is_static"] is True
        assert result["round"] is None
        assert result["dora_indicators"] == []
        assert result["hand"] == []
        assert result["timer"] is None
        assert result["warnings"] == []

    def test_static_frame_with_data(self):
        """静态帧 + 有数据的 GameState → 正确映射"""
        frame = FrameResult(frame_id=3, timestamp="2026-05-07T10:00:01+00:00")
        state = GameState(
            round_info=RoundInfo(wind="东", number=2, honba=1, kyotaku=0),
            dora_indicators=["5m"],
            scores={"self": 25000, "right": 23000},
            hand=["1m", "2m", "3m"],
            drawn_tile="东",
            timer_remaining=8,
            warnings=["some_warning"],
        )
        result = format_output(frame, state)

        assert result["is_static"] is True
        assert result["round"] == {"wind": "东", "number": 2, "honba": 1, "kyotaku": 0}
        assert result["dora_indicators"] == ["5m"]
        assert result["scores"] == {"self": 25000, "right": 23000}
        assert result["hand"] == ["1m", "2m", "3m"]
        assert result["drawn_tile"] == "东"
        assert result["timer"] == {"active": True, "remaining": 8}
        assert result["warnings"] == ["some_warning"]

    def test_non_static_frame(self):
        """非静态帧 → state=None → 所有识别字段为空"""
        frame = FrameResult(
            frame_id=2, timestamp="2026-05-07T10:00:00+00:00", is_static=False
        )
        result = format_output(frame, None)

        assert result["is_static"] is False
        assert result["round"] is None
        assert result["hand"] == []
        assert result["timer"] is None
        assert result["warnings"] == ["frame_not_static"]

    def test_timer_none(self):
        """timer_remaining=None → timer=null"""
        frame = FrameResult(frame_id=1, timestamp="t")
        state = GameState(timer_remaining=None)
        result = format_output(frame, state)
        assert result["timer"] is None

    def test_timer_with_value(self):
        """timer_remaining=5 → timer={"active": true, "remaining": 5}"""
        frame = FrameResult(frame_id=1, timestamp="t")
        state = GameState(timer_remaining=5)
        result = format_output(frame, state)
        assert result["timer"] == {"active": True, "remaining": 5}

    def test_no_round_info_key_name(self):
        """输出不含 round_info 键（应为 round）"""
        frame = FrameResult(frame_id=1, timestamp="t")
        state = GameState(round_info=RoundInfo(wind="南", number=3, honba=0, kyotaku=2))
        result = format_output(frame, state)
        assert "round_info" not in result
        assert "round" in result
        assert result["round"]["wind"] == "南"

    def test_json_serializable(self):
        """输出可被 json.dumps 序列化"""
        frame = FrameResult(frame_id=1, timestamp="t")
        state = GameState(
            hand=["1m", "2m"],
            scores={"self": 25000},
            timer_remaining=10,
        )
        result = format_output(frame, state)
        serialized = json.dumps(result, ensure_ascii=False)
        assert '"round": null' in serialized
        assert '"timer": {"active": true, "remaining": 10}' in serialized


class TestRecognizeCommand:
    """recognize CLI 子命令测试"""

    def test_file_not_found(self):
        """图片路径无效 → 退出码 1"""
        with pytest.raises(SystemExit) as exc_info:
            recognize_command(["--image", "/nonexistent/path/screenshot.png"])
        assert exc_info.value.code == 1

    def test_invalid_image_format(self, tmp_path):
        """非图片文件 → 退出码 1"""
        bad_file = tmp_path / "bad.png"
        bad_file.write_text("not an image")
        with pytest.raises(SystemExit) as exc_info:
            recognize_command(["--image", str(bad_file)])
        assert exc_info.value.code == 1

    def test_valid_synthetic_image(self, tmp_path):
        """合成截图 → 退出码 0 + 有效 JSON"""
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img[:] = (30, 50, 40)
        img_path = tmp_path / "synthetic.png"
        cv2.imwrite(str(img_path), img)

        with pytest.raises(SystemExit) as exc_info:
            recognize_command(["--image", str(img_path)])
        assert exc_info.value.code == 0

    @_SKIP_ORT
    def test_model_not_found(self, tmp_path):
        """模型文件路径无效 → 退出码 1（需要 onnxruntime）"""
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img[:] = (30, 50, 40)
        img_path = tmp_path / "synthetic.png"
        cv2.imwrite(str(img_path), img)

        with pytest.raises(SystemExit) as exc_info:
            recognize_command(
                [
                    "--image",
                    str(img_path),
                    "--model",
                    "/nonexistent/model.onnx",
                ]
            )
        assert exc_info.value.code == 1

    def test_subprocess_help(self):
        """子进程调用 recognize --help → 退出码 0"""
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--image" in result.stdout

    def test_subprocess_missing_args(self):
        """子进程调用 recognize 不带参数 → 退出码 2"""
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 2
