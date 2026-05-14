"""识别引擎配置管理"""

import importlib.resources
import logging
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _resolve_resource_path(rel_path: str) -> Path | None:
    """优先从 importlib.resources 查找，回退到 __file__ 相对路径"""
    # 开发模式: src/ 和项目根目录
    for base in [
        Path(__file__).parent.parent.parent,        # src/
        Path(__file__).parent.parent.parent.parent,  # project root
    ]:
        candidate = base / rel_path
        if candidate.exists():
            return candidate
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
    ultralytics_model_path: Path | None = None
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

    # TileClassifier (ViT)
    vit_model_name: str = "pjura/mahjong_soul_vision"
    enable_vit_classifier: bool = True
    vit_classifier_threshold: float = 0.5
    vit_device: str | None = None  # None=auto, "cpu", "cuda"

    def get_model_path(self) -> Path:
        """获取 ONNX 模型路径，None 时自动解析"""
        if self.model_path is not None:
            return self.model_path
        for candidate in [
            "models/current/tile_detector.onnx",
            "models/tile_detector.onnx",
        ]:
            resolved = _resolve_resource_path(candidate)
            if resolved is not None:
                return resolved
        raise FileNotFoundError("tile_detector.onnx not found")

    def get_ultralytics_model_path(self) -> Path | None:
        """获取 ultralytics (PyTorch) 模型路径"""
        if self.ultralytics_model_path is not None:
            return self.ultralytics_model_path
        for candidate in [
            "models/mahjong_majsoulbot.pt",
        ]:
            resolved = _resolve_resource_path(candidate)
            if resolved is not None:
                return resolved
        return None

    def get_template_dir(self) -> Path:
        """获取模板目录，None 时自动解析"""
        if self.template_dir is not None:
            return self.template_dir
        resolved = _resolve_resource_path("templates/")
        if resolved is not None:
            return resolved
        raise FileNotFoundError("templates/ directory not found")
