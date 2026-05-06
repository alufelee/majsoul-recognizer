"""识别引擎配置管理"""

import importlib.resources
import logging
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _resolve_resource_path(rel_path: str) -> Path | None:
    """优先从 importlib.resources 查找，回退到 __file__ 相对路径"""
    # 开发模式: 项目根目录下的相对路径
    dev_path = Path(__file__).parent.parent.parent / rel_path
    if dev_path.exists():
        return dev_path
    # pip install: importlib.resources
    try:
        ref = importlib.resources.files("majsoul_recognizer").joinpath(rel_path)
        if ref.is_file() or ref.is_dir():
            return Path(str(ref))
    except Exception:
        pass
    return None


class RecognitionConfig(BaseModel):
    """识别引擎可调参数"""
    model_config = {"arbitrary_types_allowed": True}

    # TileDetector
    model_path: Path | None = None
    mapping_path: Path | None = None
    nms_iou_threshold: float = 0.55
    detection_confidence: float = 0.7

    # TextRecognizer
    ocr_model_dir: Path | None = None

    # PatternMatcher
    template_dir: Path | None = None

    # Validator
    score_min: int = -99999
    score_max: int = 200000
    fusion_window_size: int = 3

    # GameStateBuilder
    drawn_tile_gap_multiplier: float = 2.5
    call_group_gap_multiplier: float = 2.0

    # 性能
    enable_batch_detection: bool = True

    def get_model_path(self) -> Path:
        """获取模型路径，None 时自动解析"""
        if self.model_path is not None:
            return self.model_path
        resolved = _resolve_resource_path("models/current/tile_detector.onnx")
        if resolved is not None:
            return resolved
        raise FileNotFoundError("tile_detector.onnx not found")

    def get_template_dir(self) -> Path:
        """获取模板目录，None 时自动解析"""
        if self.template_dir is not None:
            return self.template_dir
        resolved = _resolve_resource_path("templates/")
        if resolved is not None:
            return resolved
        raise FileNotFoundError("templates/ directory not found")
