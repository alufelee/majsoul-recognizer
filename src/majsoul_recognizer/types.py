"""核心数据类型定义

定义识别管线中所有数据结构: 边界框、区域定义、检测结果、游戏状态等。
使用 Pydantic v2 进行数据验证。
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator


class BBox(BaseModel):
    """矩形边界框 (像素坐标)"""
    model_config = {"frozen": True}

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_slice(self) -> tuple[slice, slice]:
        """转换为 numpy 数组切片"""
        return (slice(self.y, self.y + self.height), slice(self.x, self.x + self.width))

    def crop(self, image: np.ndarray) -> np.ndarray:
        """从图像中裁剪该区域（自动裁剪到图像边界内）"""
        h, w = image.shape[:2]
        y1 = max(0, self.y)
        y2 = min(h, self.y + self.height)
        x1 = max(0, self.x)
        x2 = min(w, self.x + self.width)
        return image[y1:y2, x1:x2]


class ZoneName(str, Enum):
    """预定义的区域名称"""
    HAND = "hand"
    DORA = "dora"
    ROUND_INFO = "round_info"
    SCORE_SELF = "score_self"
    SCORE_RIGHT = "score_right"
    SCORE_OPPOSITE = "score_opposite"
    SCORE_LEFT = "score_left"
    DISCARDS_SELF = "discards_self"
    DISCARDS_RIGHT = "discards_right"
    DISCARDS_OPPOSITE = "discards_opposite"
    DISCARDS_LEFT = "discards_left"
    CALLS_SELF = "calls_self"
    ACTIONS = "actions"
    TIMER = "timer"


class ZoneDefinition(BaseModel):
    """区域定义 (比例坐标 0.0-1.0)"""
    model_config = {"frozen": True}

    name: ZoneName
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_bounds(self) -> "ZoneDefinition":
        """校验区域不超出图像边界"""
        if self.x + self.width > 1.0:
            raise ValueError(
                f"Zone '{self.name.value}': x({self.x}) + width({self.width}) = "
                f"{self.x + self.width} > 1.0, exceeds image boundary"
            )
        if self.y + self.height > 1.0:
            raise ValueError(
                f"Zone '{self.name.value}': y({self.y}) + height({self.height}) = "
                f"{self.y + self.height} > 1.0, exceeds image boundary"
            )
        return self

    def to_bbox(self, img_width: int, img_height: int) -> BBox:
        """将比例坐标转换为像素坐标"""
        return BBox(
            x=int(self.x * img_width),
            y=int(self.y * img_height),
            width=max(1, int(self.width * img_width)),
            height=max(1, int(self.height * img_height)),
        )


class Detection(BaseModel):
    """单次检测结果"""
    model_config = {"frozen": True}

    bbox: BBox
    tile_code: str
    confidence: float = Field(ge=0.0, le=1.0)
    zone_name: ZoneName | None = None

    @property
    def is_high_confidence(self) -> bool:
        """置信度 >= 0.9"""
        return self.confidence >= 0.9

    @property
    def is_low_confidence(self) -> bool:
        """置信度 < 0.7"""
        return self.confidence < 0.7


class RoundInfo(BaseModel):
    """局次信息"""
    wind: str  # 东/南
    number: int = Field(ge=1, le=4)
    honba: int = Field(ge=0)
    kyotaku: int = Field(ge=0)

    @field_validator("wind")
    @classmethod
    def validate_wind(cls, v: str) -> str:
        if v not in ("东", "南"):
            raise ValueError(f"wind must be 东 or 南, got '{v}'")
        return v


CallType = Literal["chi", "pon", "kan", "ankan", "kakan"]


class CallGroup(BaseModel):
    """一组副露（吃/碰/杠）

    rotated_index 使用 is not None 检查（0 是合法值，表示横置牌在第一个位置）。
    """
    model_config = {"frozen": True}
    type: CallType
    tiles: list[str]
    rotated_index: int | None = None
    from_player: str | None = None


class ActionMatch(BaseModel):
    """动作按钮匹配结果"""
    model_config = {"frozen": True}
    name: str
    score: float = Field(ge=0.0, le=1.0)


class GameState(BaseModel):
    """游戏全局状态"""
    model_config = {"frozen": True}
    round_info: RoundInfo | None = None
    dora_indicators: list[str] = Field(default_factory=list)
    scores: dict[str, int] = Field(default_factory=dict)
    hand: list[str] = Field(default_factory=list)
    drawn_tile: str | None = None
    calls: dict[str, list[CallGroup]] = Field(default_factory=dict)
    discards: dict[str, list[str]] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)
    timer_remaining: int | None = None
    warnings: list[str] = Field(default_factory=list)


class FrameResult(BaseModel):
    """单帧处理结果"""
    model_config = {"arbitrary_types_allowed": True}

    frame_id: int
    timestamp: str
    zones: dict[str, np.ndarray] = Field(default_factory=dict)
    is_static: bool = True
    game_state: GameState | None = None
    full_image: np.ndarray | None = None
    zone_rects: dict[str, tuple[int, int, int, int]] | None = None
