"""截图处理流水线

整合截图捕获、帧状态检测和区域分割，
提供统一的处理入口。
"""

import importlib.resources
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from majsoul_recognizer.capture.frame import FrameChecker
from majsoul_recognizer.types import FrameResult
from majsoul_recognizer.zones.config import load_zone_config
from majsoul_recognizer.zones.splitter import ZoneSplitter

logger = logging.getLogger(__name__)

# 配置文件所在包 — 使用 importlib.resources 定位，打包后也能正确找到
_CONFIG_PACKAGE = "majsoul_recognizer"
_CONFIG_FILENAME = "zones.yaml"


def _get_default_config_path() -> Path:
    """获取默认区域配置文件路径

    优先从包资源查找（支持 pip install 安装），
    回退到项目根目录 config/zones.yaml（开发模式）。
    """
    # 开发模式: config/ 在项目根目录
    dev_path = Path(__file__).parent.parent.parent / "config" / "zones.yaml"
    if dev_path.exists():
        return dev_path

    # 安装模式: 配置文件作为包数据分发
    try:
        ref = importlib.resources.files(_CONFIG_PACKAGE).joinpath(_CONFIG_FILENAME)
        if ref.is_file():
            return Path(str(ref))
    except Exception:
        pass

    # 最终回退到开发路径（load_zone_config 会报 FileNotFoundError）
    return dev_path


_DEFAULT_CONFIG_PATH: Path | None = None


def _get_default_config() -> Path:
    """延迟获取默认配置路径"""
    global _DEFAULT_CONFIG_PATH
    if _DEFAULT_CONFIG_PATH is None:
        _DEFAULT_CONFIG_PATH = _get_default_config_path()
    return _DEFAULT_CONFIG_PATH


class CapturePipeline:
    """截图处理流水线

    处理流程: 截图 → 分辨率归一化 → 帧状态检测 → 区域分割

    用法:
        pipeline = CapturePipeline()
        result = pipeline.process_image(screenshot)
        if result.is_static:
            hand_region = result.zones["hand"]
    """

    def __init__(
        self,
        config_path: Path | str | None = None,
        frame_threshold: float = 0.02,
    ):
        config_path = Path(config_path) if config_path else _get_default_config()
        config = load_zone_config(config_path)

        self._splitter = ZoneSplitter(config)
        self._frame_checker = FrameChecker(threshold=frame_threshold)
        self._frame_count = 0

    def process_image(self, image: np.ndarray) -> FrameResult:
        """处理单张截图

        Args:
            image: BGR 格式游戏截图

        Returns:
            帧处理结果，包含分割后的区域和帧状态
        """
        self._frame_count += 1
        is_static = self._frame_checker.is_static(image)

        if is_static:
            raw_zones = self._splitter.split(image)
            # 将 ZoneName 枚举键转为字符串，保持 FrameResult 类型一致
            zones = {zone_name.value: img for zone_name, img in raw_zones.items()}
        else:
            # 动画帧使用空区域，调用者应沿用上一帧结果
            zones = {}

        return FrameResult(
            frame_id=self._frame_count,
            timestamp=datetime.now(timezone.utc).isoformat(),
            zones=zones,
            is_static=is_static,
        )

    @property
    def frame_count(self) -> int:
        """已处理的帧数"""
        return self._frame_count

    def reset(self):
        """重置流水线状态"""
        self._frame_checker.reset()
        self._frame_count = 0
