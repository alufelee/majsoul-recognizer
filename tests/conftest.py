"""共享测试 fixtures"""

from pathlib import Path

import numpy as np
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CONFIG_DIR = Path(__file__).parent.parent / "config"


@pytest.fixture
def fixtures_dir():
    """测试 fixtures 目录路径"""
    return FIXTURES_DIR


@pytest.fixture
def config_dir():
    """配置文件目录路径"""
    return CONFIG_DIR


@pytest.fixture
def sample_screenshot():
    """创建一个模拟的 1920x1080 游戏截图（深绿色桌面背景）"""
    img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    img[:] = (30, 50, 40)
    return img


@pytest.fixture
def sample_screenshot_small():
    """创建一个模拟的 1280x720 游戏截图"""
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    img[:] = (30, 50, 40)
    return img
