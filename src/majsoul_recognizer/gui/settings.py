"""GUI 配置持久化

GUISettings 将所有可配置项映射到 RecognitionConfig + GUI 偏好。
保存为 JSON 文件，原子写入。
"""

import dataclasses
import json
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from majsoul_recognizer.recognition.config import RecognitionConfig

logger = logging.getLogger(__name__)


@dataclass
class GUISettings:
    """GUI 配置 — 映射 RecognitionConfig 全部字段 + GUI 偏好"""

    # RecognitionConfig 映射
    model_path: str | None = None
    mapping_path: str | None = None
    template_dir: str | None = None
    config_path: str | None = None
    ocr_model_dir: str | None = None
    detection_confidence: float = 0.3
    nms_iou_threshold: float = 0.55
    score_min: int = -99999
    score_max: int = 200000
    fusion_window_size: int = 3
    enable_batch_detection: bool = True
    drawn_tile_gap_multiplier: float = 2.5
    call_group_gap_multiplier: float = 2.0

    # GUI 偏好
    theme: str = "dark"
    capture_interval_ms: int = 200
    show_detection_boxes: bool = True
    show_confidence: bool = True

    # 窗口几何
    window_width: int = 1280
    window_height: int = 800
    window_x: int = 100
    window_y: int = 100

    _PATH: ClassVar[Path] = Path.home() / ".majsoul-recognizer" / "settings.json"

    @classmethod
    def load(cls, path: Path | None = None) -> "GUISettings":
        """加载配置，文件不存在或损坏时返回默认值

        [M2 修复] path 参数用于测试注入，None 时使用 cls._PATH。
        """
        file_path = path or cls._PATH
        try:
            text = file_path.read_text(encoding="utf-8")
            data = json.loads(text)
            valid_keys = {f.name for f in dataclasses.fields(cls)}
            return cls(**{k: v for k, v in data.items() if k in valid_keys})
        except FileNotFoundError:
            return cls()
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("配置文件损坏，使用默认值: %s", e)
            return cls()

    def save(self, path: Path | None = None) -> None:
        """原子写入（先写临时文件再 rename）

        [M2 修复] path 参数用于测试注入，None 时使用 cls._PATH。
        """
        file_path = path or self._PATH
        file_path.parent.mkdir(parents=True, exist_ok=True)
        data = dataclasses.asdict(self)
        fd: int = 0
        tmp: str = ""
        try:
            fd, tmp = tempfile.mkstemp(dir=str(file_path.parent), suffix=".json")
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            Path(tmp).rename(file_path)
        except Exception:
            Path(tmp).unlink(missing_ok=True)
            raise

    def to_recognition_config(self) -> RecognitionConfig:
        """转换为 RecognitionConfig（完整映射所有字段）"""
        return RecognitionConfig(
            model_path=Path(self.model_path) if self.model_path else None,
            mapping_path=Path(self.mapping_path) if self.mapping_path else None,
            template_dir=Path(self.template_dir) if self.template_dir else None,
            ocr_model_dir=Path(self.ocr_model_dir) if self.ocr_model_dir else None,
            nms_iou_threshold=self.nms_iou_threshold,
            detection_confidence=self.detection_confidence,
            score_min=self.score_min,
            score_max=self.score_max,
            fusion_window_size=self.fusion_window_size,
            enable_batch_detection=self.enable_batch_detection,
            drawn_tile_gap_multiplier=self.drawn_tile_gap_multiplier,
            call_group_gap_multiplier=self.call_group_gap_multiplier,
        )

    def to_pipeline_config(self) -> tuple[Path | None, float]:
        """返回 (config_path, frame_threshold)"""
        return (
            Path(self.config_path) if self.config_path else None,
            0.02,
        )
