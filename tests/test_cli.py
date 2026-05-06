"""CLI 入口测试"""

import subprocess
import sys

import numpy as np
import pytest
from pathlib import Path

from majsoul_recognizer.cli import capture_and_save, build_capture_chain


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
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "capture" in result.stdout or "usage" in result.stdout.lower()
