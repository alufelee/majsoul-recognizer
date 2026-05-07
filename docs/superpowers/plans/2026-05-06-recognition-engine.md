# 识别引擎实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现识别引擎的全部代码框架，包含 TileDetector、TextRecognizer、PatternMatcher、GameStateBuilder、Validator 和 RecognitionEngine，使用假模型/假模板让测试端到端可运行。

**Architecture:** 模块化管道架构：区域图像 → TileDetector (YOLOv8 ONNX) + TextRecognizer (PaddleOCR) + PatternMatcher (模板匹配) → GameStateBuilder (组装) → Validator (校验+融合) → GameState。RecognitionEngine 作为统一门面协调各子模块。

**Tech Stack:** Python 3.10+, ONNX Runtime, OpenCV, NumPy, Pydantic v2, PaddleOCR (可选), pytest

**设计文档:** `docs/superpowers/specs/2026-05-06-recognition-engine-design.md` (v4.0)

---

## 文件结构

```
src/majsoul_recognizer/
├── types.py                          # 修改: 新增 CallGroup/ActionMatch, 删除 PlayerScore, GameState frozen
├── recognition/
│   ├── __init__.py                   # 新建: 导出 RecognitionEngine, RecognitionConfig
│   ├── config.py                     # 新建: RecognitionConfig + _resolve_resource_path
│   ├── tile_detector.py              # 新建: TileDetector + NMS + batch 画布
│   ├── text_recognizer.py            # 新建: TextRecognizer + 后处理
│   ├── pattern_matcher.py            # 新建: PatternMatcher + 模板匹配
│   ├── state_builder.py              # 新建: GameStateBuilder + Validator
│   └── engine.py                     # 新建: RecognitionEngine 门面
├── ocr_dicts/                        # 新建: OCR 字符字典
│   ├── score_dict.txt
│   ├── round_dict.txt
│   └── timer_dict.txt
└── ...

tests/
├── test_types.py                     # 修改: 更新 GameState 测试, 移除 PlayerScore
├── recognition/
│   ├── __init__.py                   # 新建: 空
│   ├── conftest.py                   # 新建: 假模型/假模板 fixtures
│   ├── test_config.py                # 新建: RecognitionConfig 测试
│   ├── test_tile_detector.py         # 新建: TileDetector 测试
│   ├── test_text_recognizer.py       # 新建: TextRecognizer 测试
│   ├── test_pattern_matcher.py       # 新建: PatternMatcher 测试
│   ├── test_state_builder.py         # 新建: GameStateBuilder 测试
│   ├── test_validator.py             # 新建: Validator 测试
│   └── test_engine.py                # 新建: RecognitionEngine 集成测试
└── ...
```

---

## Task 1: RecognitionConfig + 类型扩展

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/majsoul_recognizer/types.py`
- Modify: `tests/test_types.py`
- Create: `src/majsoul_recognizer/recognition/__init__.py`
- Create: `src/majsoul_recognizer/recognition/config.py`
- Create: `tests/recognition/__init__.py`
- Create: `tests/recognition/conftest.py`
- Create: `tests/recognition/test_config.py`

- [ ] **Step 1: 更新 pyproject.toml — 添加依赖**

在 `dependencies` 列表末尾添加 `onnxruntime`，在 `dev` 列表添加 `onnx`，添加 `recognition-ocr` 可选组和 `package-data`:

```toml
[project]
name = "majsoul-recognizer"
version = "0.1.0"
description = "雀魂麻将画面识别助手"
requires-python = ">=3.10"
dependencies = [
    "opencv-python-headless>=4.8",
    "numpy>=1.24",
    "mss>=9.0",
    "pydantic>=2.0",
    "PyYAML>=6.0",
    "onnxruntime>=1.16",
]

[project.optional-dependencies]
macos = [
    "pyobjc-framework-Quartz>=10.0",
    "pyobjc-framework-ApplicationServices>=10.0",
]
windows = [
    "pywin32>=306",
]
recognition-ocr = [
    "paddleocr>=2.7",
    "paddlepaddle>=2.5",
]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.4",
    "onnx>=1.14",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
majsoul_recognizer = ["ocr_dicts/*.txt"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"
```

- [ ] **Step 2: 安装新依赖**

```bash
pip install -e ".[dev,macos]"
```

- [ ] **Step 3: 编写类型扩展测试**

更新 `tests/test_types.py` — 移除 PlayerScore 导入和测试，添加 CallGroup/ActionMatch/GameState frozen 测试:

```python
"""核心数据类型测试"""

import numpy as np
import pytest
from pydantic import ValidationError

from majsoul_recognizer.types import (
    BBox,
    ZoneDefinition,
    ZoneName,
    Detection,
    RoundInfo,
    CallGroup,
    ActionMatch,
    GameState,
    FrameResult,
)


class TestBBox:
    """边界框测试"""

    def test_create_bbox(self):
        bbox = BBox(x=10, y=20, width=100, height=50)
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 100
        assert bbox.height == 50

    def test_bbox_area(self):
        bbox = BBox(x=0, y=0, width=100, height=50)
        assert bbox.area == 5000

    def test_bbox_center(self):
        bbox = BBox(x=100, y=200, width=60, height=40)
        assert bbox.center == (130, 220)

    def test_bbox_to_slice(self):
        bbox = BBox(x=10, y=20, width=30, height=40)
        s = bbox.to_slice()
        assert s == (slice(20, 60), slice(10, 40))

    def test_bbox_crop_image(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[30:60, 10:50] = 255
        bbox = BBox(x=10, y=30, width=40, height=30)
        cropped = bbox.crop(img)
        assert cropped.shape == (30, 40, 3)
        assert (cropped == 255).all()

    def test_bbox_negative_size_raises(self):
        with pytest.raises(ValidationError):
            BBox(x=0, y=0, width=-1, height=10)


class TestZoneDefinition:
    """区域定义测试"""

    def test_create_zone(self):
        zone = ZoneDefinition(
            name=ZoneName.HAND,
            x=0.25, y=0.82, width=0.50, height=0.12,
        )
        assert zone.name == ZoneName.HAND
        assert zone.x == 0.25

    def test_zone_to_bbox(self):
        zone = ZoneDefinition(
            name=ZoneName.HAND,
            x=0.25, y=0.82, width=0.50, height=0.12,
        )
        bbox = zone.to_bbox(1920, 1080)
        assert bbox.x == 480
        assert bbox.y == 885
        assert bbox.width == 960
        assert bbox.height == 129

    def test_zone_ratio_range(self):
        with pytest.raises(ValidationError):
            ZoneDefinition(name=ZoneName.HAND, x=-0.1, y=0.5, width=0.2, height=0.1)


class TestDetection:
    """检测结果测试"""

    def test_create_detection(self):
        det = Detection(
            bbox=BBox(x=10, y=20, width=30, height=40),
            tile_code="1m",
            confidence=0.95,
        )
        assert det.tile_code == "1m"
        assert det.confidence == 0.95

    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            Detection(
                bbox=BBox(x=0, y=0, width=10, height=10),
                tile_code="1m",
                confidence=1.5,
            )

    def test_is_high_confidence(self):
        high = Detection(
            bbox=BBox(x=0, y=0, width=10, height=10),
            tile_code="1m", confidence=0.92,
        )
        low = Detection(
            bbox=BBox(x=0, y=0, width=10, height=10),
            tile_code="1m", confidence=0.75,
        )
        assert high.is_high_confidence is True
        assert low.is_high_confidence is False


class TestRoundInfo:
    """局次信息测试"""

    def test_create_round_info(self):
        info = RoundInfo(wind="东", number=1, honba=0, kyotaku=0)
        assert info.wind == "东"
        assert info.number == 1

    def test_invalid_wind_raises(self):
        with pytest.raises(ValidationError):
            RoundInfo(wind="西", number=1, honba=0, kyotaku=0)

    def test_invalid_number_raises(self):
        with pytest.raises(ValidationError):
            RoundInfo(wind="东", number=5, honba=0, kyotaku=0)


class TestCallGroup:
    """副露组测试"""

    def test_create_chi(self):
        call = CallGroup(type="chi", tiles=["1s", "2s", "3s"], rotated_index=0, from_player="right")
        assert call.type == "chi"
        assert len(call.tiles) == 3
        assert call.rotated_index == 0

    def test_create_pon(self):
        call = CallGroup(type="pon", tiles=["5p", "5p", "5p"], rotated_index=1, from_player="opposite")
        assert call.type == "pon"

    def test_create_ankan(self):
        call = CallGroup(type="ankan", tiles=["1z", "1z", "1z", "1z"])
        assert call.rotated_index is None
        assert call.from_player is None

    def test_rotated_index_zero_is_valid(self):
        """rotated_index=0 是合法值，不是 falsy"""
        call = CallGroup(type="chi", tiles=["1s", "2s", "3s"], rotated_index=0)
        assert call.rotated_index is not None
        assert call.rotated_index == 0

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            CallGroup(type="invalid", tiles=["1m"])

    def test_frozen(self):
        call = CallGroup(type="chi", tiles=["1s", "2s", "3s"])
        with pytest.raises(ValidationError):
            call.type = "pon"


class TestActionMatch:
    """动作匹配结果测试"""

    def test_create_action(self):
        action = ActionMatch(name="碰", score=0.92)
        assert action.name == "碰"
        assert action.score == 0.92

    def test_score_range(self):
        with pytest.raises(ValidationError):
            ActionMatch(name="碰", score=1.5)

    def test_frozen(self):
        action = ActionMatch(name="碰", score=0.9)
        with pytest.raises(ValidationError):
            action.score = 0.5


class TestGameState:
    """游戏状态测试"""

    def test_create_empty_state(self):
        state = GameState()
        assert state.hand == []
        assert state.scores == {}
        assert state.round_info is None
        assert state.calls == {}

    def test_state_with_data(self):
        state = GameState(
            hand=["1m", "2m", "3m"],
            drawn_tile="东",
            dora_indicators=["5m"],
            scores={"self": 25000, "right": 25000},
        )
        assert len(state.hand) == 3
        assert state.drawn_tile == "东"
        assert state.scores["self"] == 25000

    def test_frozen_cannot_mutate(self):
        state = GameState(hand=["1m"])
        with pytest.raises(ValidationError):
            state.hand = ["2m"]

    def test_model_copy_update(self):
        """frozen 模式使用 model_copy 返回新实例"""
        state = GameState(warnings=[])
        new_state = state.model_copy(update={"warnings": ["test_warning"]})
        assert state.warnings == []
        assert new_state.warnings == ["test_warning"]

    def test_calls_with_call_group(self):
        call = CallGroup(type="chi", tiles=["1s", "2s", "3s"], rotated_index=0)
        state = GameState(calls={"self": [call]})
        assert state.calls["self"][0].type == "chi"

    def test_scores_are_int(self):
        state = GameState(scores={"self": 25000})
        assert isinstance(state.scores["self"], int)


class TestFrameResult:
    """帧结果测试"""

    def test_create_frame_result(self):
        result = FrameResult(
            frame_id=1,
            timestamp="2026-05-06T10:00:00",
            zones={"hand": np.zeros((100, 200, 3), dtype=np.uint8)},
        )
        assert result.frame_id == 1
        assert "hand" in result.zones
```

- [ ] **Step 4: 运行测试确认失败**

```bash
pytest tests/test_types.py -v
```

Expected: FAIL — `ImportError: cannot import name 'CallGroup'`

- [ ] **Step 5: 实现 types.py 修改**

```python
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
```

- [ ] **Step 6: 运行测试确认通过**

```bash
pytest tests/test_types.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 7: 创建 recognition 包和测试目录**

```bash
touch src/majsoul_recognizer/recognition/__init__.py
touch tests/recognition/__init__.py
```

`src/majsoul_recognizer/recognition/__init__.py` (暂时为空):

```python
"""识别引擎模块"""
```

- [ ] **Step 8: 编写 RecognitionConfig 测试**

`tests/recognition/conftest.py`:

```python
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
```

`tests/recognition/test_config.py`:

```python
"""RecognitionConfig 测试"""

import pytest
from pathlib import Path
from majsoul_recognizer.recognition.config import RecognitionConfig


class TestRecognitionConfig:
    """识别引擎配置测试"""

    def test_default_values(self):
        config = RecognitionConfig()
        assert config.nms_iou_threshold == 0.55
        assert config.detection_confidence == 0.7
        assert config.score_min == -99999
        assert config.score_max == 200000
        assert config.fusion_window_size == 3
        assert config.drawn_tile_gap_multiplier == 2.5
        assert config.call_group_gap_multiplier == 2.0
        assert config.enable_batch_detection is True

    def test_custom_values(self):
        config = RecognitionConfig(
            nms_iou_threshold=0.45,
            detection_confidence=0.5,
            fusion_window_size=5,
        )
        assert config.nms_iou_threshold == 0.45
        assert config.detection_confidence == 0.5
        assert config.fusion_window_size == 5

    def test_get_model_path_raises_when_not_found(self):
        config = RecognitionConfig()
        with pytest.raises(FileNotFoundError, match="tile_detector.onnx"):
            config.get_model_path()

    def test_get_model_path_returns_explicit(self, tmp_path):
        model_file = tmp_path / "tile_detector.onnx"
        model_file.write_bytes(b"fake")
        config = RecognitionConfig(model_path=model_file)
        assert config.get_model_path() == model_file

    def test_get_template_dir_raises_when_not_found(self):
        config = RecognitionConfig()
        with pytest.raises(FileNotFoundError, match="templates/"):
            config.get_template_dir()

    def test_get_template_dir_returns_explicit(self, tmp_path):
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        config = RecognitionConfig(template_dir=template_dir)
        assert config.get_template_dir() == template_dir
```

- [ ] **Step 9: 运行测试确认失败**

```bash
pytest tests/recognition/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'majsoul_recognizer.recognition'`

- [ ] **Step 10: 实现 RecognitionConfig**

`src/majsoul_recognizer/recognition/config.py`:

```python
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
```

- [ ] **Step 11: 运行测试确认通过**

```bash
pytest tests/recognition/test_config.py tests/test_types.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 12: 提交**

```bash
git add pyproject.toml src/majsoul_recognizer/types.py tests/test_types.py \
      src/majsoul_recognizer/recognition/ tests/recognition/
git commit -m "feat: add RecognitionConfig and extend types (CallGroup, ActionMatch, frozen GameState)"
```

---

## Task 2: TileDetector

**Files:**
- Create: `src/majsoul_recognizer/recognition/tile_detector.py`
- Modify: `tests/recognition/conftest.py`
- Create: `tests/recognition/test_tile_detector.py`

- [ ] **Step 1: 更新 conftest.py — 添加假 ONNX 模型 fixture**

在 `tests/recognition/conftest.py` 末尾追加:

```python
@pytest.fixture(scope="session")
def dummy_detector_path(tmp_path_factory):
    """生成假 ONNX 检测模型（session 级别共享）"""
    import numpy as np
    import onnx
    from onnx import helper, TensorProto, numpy_helper

    output = np.zeros((1, 44, 8400), dtype=np.float32)

    # 在 index 0 放置一个高置信度检测: cx=80, cy=80, w=60, h=80, class=0(1m), conf=0.95
    output[0, 0, 0] = 80.0   # cx
    output[0, 1, 0] = 80.0   # cy
    output[0, 2, 0] = 60.0   # w
    output[0, 3, 0] = 80.0   # h
    output[0, 4, 0] = 0.95   # class 0 (1m)

    # 在 index 1 放置第二个检测: cx=200, cy=100, w=50, h=70, class=9(1p), conf=0.88
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
```

- [ ] **Step 2: 编写 TileDetector 测试**

`tests/recognition/test_tile_detector.py`:

```python
"""TileDetector 测试"""

import numpy as np
import pytest

from majsoul_recognizer.types import BBox, Detection, ZoneName


class TestTileDetectorInit:
    """TileDetector 初始化测试"""

    def test_load_model(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        assert detector is not None

    def test_default_class_map(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        assert detector.class_map[0] == "1m"
        assert detector.class_map[36] == "5sr"
        assert detector.class_map[37] == "back"

    def test_class_map_covers_all_tiles(self, dummy_detector_path):
        """ID 0-36 的 tile_code 必须与 Tile 枚举完全对应"""
        from majsoul_recognizer.recognition.tile_detector import TileDetector, _DEFAULT_CLASS_MAP
        from majsoul_recognizer.tile import Tile
        tile_codes = {v for k, v in _DEFAULT_CLASS_MAP.items() if k <= 36}
        assert tile_codes == {t.value for t in Tile}


class TestTileDetectorDetect:
    """单图检测测试"""

    def test_detect_returns_detections(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        results = detector.detect(image, confidence=0.5)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_detect_first_result_is_1m(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        results = detector.detect(image, confidence=0.5)
        # 假模型 index 0 输出 class 0 = "1m"
        codes = [d.tile_code for d in results]
        assert "1m" in codes

    def test_detect_bbox_positive_size(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        results = detector.detect(image, confidence=0.5)
        for det in results:
            assert det.bbox.width > 0
            assert det.bbox.height > 0

    def test_detect_empty_image(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        # 空图像（假模型仍会输出，但测试不崩溃）
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        results = detector.detect(image, confidence=0.99)
        assert isinstance(results, list)

    def test_detect_confidence_filter(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        high = detector.detect(image, confidence=0.96)
        low = detector.detect(image, confidence=0.5)
        assert len(low) >= len(high)


class TestTileDetectorBatch:
    """多区域拼接检测测试"""

    def test_detect_batch_returns_dict(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        images = [
            ("hand", np.zeros((100, 200, 3), dtype=np.uint8)),
            ("dora", np.zeros((60, 150, 3), dtype=np.uint8)),
        ]
        results = detector.detect_batch(images, confidence=0.5)
        assert isinstance(results, dict)
        assert "hand" in results
        assert "dora" in results

    def test_detect_batch_single_image(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        images = [("hand", np.zeros((100, 200, 3), dtype=np.uint8))]
        results = detector.detect_batch(images, confidence=0.5)
        assert "hand" in results
        assert isinstance(results["hand"], list)

    def test_detect_batch_empty_list(self, dummy_detector_path):
        from majsoul_recognizer.recognition.tile_detector import TileDetector
        detector = TileDetector(dummy_detector_path)
        results = detector.detect_batch([], confidence=0.5)
        assert results == {}


class TestComputeIoU:
    """IoU 计算测试"""

    def test_identical_boxes(self):
        from majsoul_recognizer.recognition.tile_detector import _compute_iou
        a = BBox(x=0, y=0, width=100, height=100)
        assert _compute_iou(a, a) == 1.0

    def test_no_overlap(self):
        from majsoul_recognizer.recognition.tile_detector import _compute_iou
        a = BBox(x=0, y=0, width=50, height=50)
        b = BBox(x=100, y=100, width=50, height=50)
        assert _compute_iou(a, b) == 0.0

    def test_partial_overlap(self):
        from majsoul_recognizer.recognition.tile_detector import _compute_iou
        a = BBox(x=0, y=0, width=100, height=100)
        b = BBox(x=50, y=50, width=100, height=100)
        iou = _compute_iou(a, b)
        assert 0.0 < iou < 1.0


class TestResolveRotatedTiles:
    """横置牌定位测试"""

    def test_rotated_associated_to_nearest(self):
        from majsoul_recognizer.recognition.tile_detector import _resolve_rotated_tiles
        normal = Detection(bbox=BBox(x=0, y=0, width=50, height=70), tile_code="1m", confidence=0.9)
        rotated = Detection(bbox=BBox(x=5, y=5, width=45, height=65), tile_code="rotated", confidence=0.85)
        result = _resolve_rotated_tiles([normal, rotated])
        assert 0 in result  # normal at index 0 has rotated match

    def test_no_rotated_returns_empty(self):
        from majsoul_recognizer.recognition.tile_detector import _resolve_rotated_tiles
        normal = Detection(bbox=BBox(x=0, y=0, width=50, height=70), tile_code="1m", confidence=0.9)
        result = _resolve_rotated_tiles([normal])
        assert result == {}
```

- [ ] **Step 3: 运行测试确认失败**

```bash
pytest tests/recognition/test_tile_detector.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: 实现 TileDetector**

`src/majsoul_recognizer/recognition/tile_detector.py`:

```python
"""YOLOv8 ONNX 牌面检测器"""

import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from majsoul_recognizer.types import BBox, Detection

logger = logging.getLogger(__name__)

_DEFAULT_CLASS_MAP: dict[int, str] = {
    0: "1m", 1: "2m", 2: "3m", 3: "4m", 4: "5m",
    5: "6m", 6: "7m", 7: "8m", 8: "9m",
    9: "1p", 10: "2p", 11: "3p", 12: "4p", 13: "5p",
    14: "6p", 15: "7p", 16: "8p", 17: "9p",
    18: "1s", 19: "2s", 20: "3s", 21: "4s", 22: "5s",
    23: "6s", 24: "7s", 25: "8s", 26: "9s",
    27: "1z", 28: "2z", 29: "3z", 30: "4z",
    31: "5z", 32: "6z", 33: "7z",
    34: "5mr", 35: "5pr", 36: "5sr",
    37: "back", 38: "rotated", 39: "dora_frame",
}


def _compute_iou(bbox_a: BBox, bbox_b: BBox) -> float:
    """计算两个 BBox 的 IoU"""
    x1 = max(bbox_a.x, bbox_b.x)
    y1 = max(bbox_a.y, bbox_b.y)
    x2 = min(bbox_a.x + bbox_a.width, bbox_b.x + bbox_b.width)
    y2 = min(bbox_a.y + bbox_a.height, bbox_b.y + bbox_b.height)

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = bbox_a.area + bbox_b.area - intersection
    return intersection / union if union > 0 else 0.0


def _resolve_rotated_tiles(all_detections: list[Detection]) -> dict[int, Detection]:
    """将 rotated 类别的检测关联到最近的正常牌面检测"""
    normals = [(i, d) for i, d in enumerate(all_detections)
               if d.tile_code not in ("back", "rotated", "dora_frame")]
    rotated = [d for d in all_detections if d.tile_code == "rotated"]

    rotated_map: dict[int, Detection] = {}
    for r in rotated:
        best_iou = 0.0
        best_idx = -1
        for idx, n in normals:
            iou = _compute_iou(r.bbox, n.bbox)
            if iou > best_iou:
                best_iou = iou
                best_idx = idx
        if best_idx >= 0 and best_iou > 0.3:
            rotated_map[best_idx] = r
    return rotated_map


def _nms(detections: list[Detection], iou_threshold: float) -> list[Detection]:
    """非极大值抑制"""
    if not detections:
        return []

    sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
    keep: list[Detection] = []

    for det in sorted_dets:
        should_keep = True
        for kept in keep:
            if _compute_iou(det.bbox, kept.bbox) > iou_threshold:
                should_keep = False
                break
        if should_keep:
            keep.append(det)
    return keep


@dataclass
class _CanvasSlot:
    """记录每个区域在画布上的位置"""
    zone_name: str
    x_offset: int
    y_offset: int
    scale: float
    orig_w: int
    orig_h: int
    slot_size: int

    @property
    def image_rect(self) -> tuple[int, int, int, int]:
        """实际图像在画布上的范围 (x1, y1, x2, y2)"""
        scaled_w = int(self.orig_w * self.scale)
        scaled_h = int(self.orig_h * self.scale)
        pad_x = (self.slot_size - scaled_w) // 2
        pad_y = (self.slot_size - scaled_h) // 2
        return (
            self.x_offset + pad_x,
            self.y_offset + pad_y,
            self.x_offset + pad_x + scaled_w,
            self.y_offset + pad_y + scaled_h,
        )


def _canvas_to_local(bbox: BBox, slot: _CanvasSlot) -> BBox:
    """将画布坐标转换为区域本地坐标"""
    local_x = (bbox.x - slot.x_offset) / slot.scale
    local_y = (bbox.y - slot.y_offset) / slot.scale
    local_w = bbox.width / slot.scale
    local_h = bbox.height / slot.scale
    return BBox(
        x=max(0, int(local_x)),
        y=max(0, int(local_y)),
        width=max(1, int(local_w)),
        height=max(1, int(local_h)),
    )


def _assign_to_slot(
    detections: list[Detection],
    slots: list[_CanvasSlot],
) -> dict[str, list[Detection]]:
    """将画布上的检测结果归属到对应的区域 slot"""
    result: dict[str, list[Detection]] = {s.zone_name: [] for s in slots}

    for det in detections:
        cx = det.bbox.x + det.bbox.width // 2
        cy = det.bbox.y + det.bbox.height // 2

        assigned = False
        for slot in slots:
            x1, y1, x2, y2 = slot.image_rect
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                local_bbox = _canvas_to_local(det.bbox, slot)
                local_det = det.model_copy(update={"bbox": local_bbox})
                result[slot.zone_name].append(local_det)
                assigned = True
                break

        if not assigned:
            logger.debug("Discarding detection in padding area: %s", det)

    return result


class TileDetector:
    """YOLOv8 ONNX 牌面检测器"""

    def __init__(
        self,
        model_path: Path | str,
        class_map: dict[int, str] | None = None,
        nms_iou: float = 0.55,
    ):
        self.class_map = class_map or _DEFAULT_CLASS_MAP
        self._nms_iou = nms_iou

        providers = []
        if "CoreMLExecutionProvider" in ort.get_available_providers():
            providers.append("CoreMLExecutionProvider")
        if "CUDAExecutionProvider" in ort.get_available_providers():
            providers.append("CUDAExecutionProvider")
        providers.append("CPUExecutionProvider")

        self._session = ort.InferenceSession(str(model_path), providers=providers)
        logger.info("TileDetector loaded from %s", model_path)

    def detect(self, image: np.ndarray, confidence: float = 0.7) -> list[Detection]:
        """检测单张图像中的牌面"""
        try:
            t0 = time.perf_counter()
            input_tensor, (orig_h, orig_w), (pad_x, pad_y, scale) = self._preprocess(image)
            output = self._session.run(None, {"images": input_tensor})
            raw_detections = self._postprocess(output[0], confidence, orig_w, orig_h, pad_x, pad_y, scale)
            result = _nms(raw_detections, self._nms_iou)
            elapsed = (time.perf_counter() - t0) * 1000
            logger.debug("detect: %d results in %.1fms", len(result), elapsed)
            return result
        except Exception as e:
            logger.warning("ONNX inference failed: %s", e)
            return []

    def detect_batch(
        self,
        images: list[tuple[str, np.ndarray]],
        confidence: float = 0.7,
    ) -> dict[str, list[Detection]]:
        """多区域拼接检测"""
        if not images:
            return {}

        if len(images) == 1:
            name, img = images[0]
            return {name: self.detect(img, confidence)}

        canvas, slots = self._build_canvas(images)
        all_dets = self.detect(canvas, confidence)
        return _assign_to_slot(all_dets, slots)

    def _preprocess(self, image: np.ndarray) -> tuple:
        """Letterbox 预处理"""
        orig_h, orig_w = image.shape[:2]
        target = 640
        scale = min(target / orig_w, target / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((target, target, 3), 114, dtype=np.uint8)
        pad_x = (target - new_w) // 2
        pad_y = (target - new_h) // 2
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

        blob = canvas.astype(np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)[np.newaxis, ...]  # (1, 3, 640, 640)

        return blob, (orig_h, orig_w), (pad_x, pad_y, scale)

    def _postprocess(self, output: np.ndarray, confidence: float,
                     orig_w: int, orig_h: int,
                     pad_x: int, pad_y: int, scale: float) -> list[Detection]:
        """YOLOv8 输出后处理"""
        # output shape: (1, 44, 8400) → transpose to (8400, 44)
        predictions = output[0].T  # (8400, 44)

        detections: list[Detection] = []
        for pred in predictions:
            bbox_vals = pred[:4]  # cx, cy, w, h
            class_scores = pred[4:]
            class_id = int(np.argmax(class_scores))
            score = float(class_scores[class_id])

            if score < confidence:
                continue

            tile_code = self.class_map.get(class_id, f"unknown_{class_id}")

            # Letterbox → 原图坐标
            cx = float((bbox_vals[0] - pad_x) / scale)
            cy = float((bbox_vals[1] - pad_y) / scale)
            w = float(bbox_vals[2] / scale)
            h = float(bbox_vals[3] / scale)

            x = max(0, int(cx - w / 2))
            y = max(0, int(cy - h / 2))

            detections.append(Detection(
                bbox=BBox(x=x, y=y, width=max(1, int(w)), height=max(1, int(h))),
                tile_code=tile_code,
                confidence=round(score, 4),
            ))
        return detections

    def _build_canvas(self, images: list[tuple[str, np.ndarray]]) -> tuple:
        """构建多区域拼接画布"""
        n = len(images)
        grid_size = max(2, math.ceil(math.sqrt(n)))
        slot_size = 640 // grid_size

        canvas = np.full((640, 640, 3), 114, dtype=np.uint8)
        slots: list[_CanvasSlot] = []

        for idx, (name, img) in enumerate(images):
            row = idx // grid_size
            col = idx % grid_size
            x_offset = col * slot_size
            y_offset = row * slot_size

            orig_h, orig_w = img.shape[:2]
            scale = min(slot_size / orig_w, slot_size / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)

            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            pad_x = (slot_size - new_w) // 2
            pad_y = (slot_size - new_h) // 2
            canvas[y_offset + pad_y:y_offset + pad_y + new_h,
                   x_offset + pad_x:x_offset + pad_x + new_w] = resized

            slots.append(_CanvasSlot(
                zone_name=name,
                x_offset=x_offset,
                y_offset=y_offset,
                scale=scale,
                orig_w=orig_w,
                orig_h=orig_h,
                slot_size=slot_size,
            ))

        return canvas, slots
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/recognition/test_tile_detector.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 6: 提交**

```bash
git add src/majsoul_recognizer/recognition/tile_detector.py tests/recognition/test_tile_detector.py tests/recognition/conftest.py
git commit -m "feat: add TileDetector with ONNX inference, NMS, and batch canvas layout"
```

---

## Task 3: TextRecognizer

**Files:**
- Create: `src/majsoul_recognizer/ocr_dicts/score_dict.txt`
- Create: `src/majsoul_recognizer/ocr_dicts/round_dict.txt`
- Create: `src/majsoul_recognizer/ocr_dicts/timer_dict.txt`
- Create: `src/majsoul_recognizer/recognition/text_recognizer.py`
- Create: `tests/recognition/test_text_recognizer.py`

- [ ] **Step 1: 创建 OCR 字典文件**

`src/majsoul_recognizer/ocr_dicts/score_dict.txt`:

```
0
1
2
3
4
5
6
7
8
9
,
.
-
```

`src/majsoul_recognizer/ocr_dicts/round_dict.txt`:

```
东
東
南
一
二
三
四
0
1
2
3
4
5
6
7
8
9
本
場
供
托
託
```

`src/majsoul_recognizer/ocr_dicts/timer_dict.txt`:

```
0
1
2
3
4
5
6
7
8
9
:
```

- [ ] **Step 2: 编写 TextRecognizer 测试**

`tests/recognition/test_text_recognizer.py`:

```python
"""TextRecognizer 测试"""

import pytest

from majsoul_recognizer.recognition.text_recognizer import (
    _parse_score_text,
    _parse_round_text,
    _parse_timer_text,
)


class TestParseScoreText:
    """分数后处理测试"""

    def test_normal_score(self):
        assert _parse_score_text("25,000") == 25000

    def test_score_no_comma(self):
        assert _parse_score_text("25000") == 25000

    def test_negative_score(self):
        assert _parse_score_text("-5,000") == -5000

    def test_score_with_spaces(self):
        assert _parse_score_text(" 25,000 ") == 25000

    def test_empty_returns_none(self):
        assert _parse_score_text("") is None

    def test_no_digits_returns_none(self):
        assert _parse_score_text("abc") is None

    def test_score_out_of_range_returns_none(self):
        assert _parse_score_text("999999") is None

    def test_zero_score(self):
        assert _parse_score_text("0") == 0


class TestParseRoundText:
    """局次后处理测试"""

    def test_standard_round(self):
        result = _parse_round_text("东一局 0 本场")
        assert result is not None
        assert result.wind == "东"
        assert result.number == 1
        assert result.honba == 0

    def test_with_honba(self):
        result = _parse_round_text("南三局 2 本场")
        assert result is not None
        assert result.wind == "南"
        assert result.number == 3
        assert result.honba == 2

    def test_traditional_chinese(self):
        result = _parse_round_text("東二局 1 本場")
        assert result is not None
        assert result.wind == "东"
        assert result.number == 2
        assert result.honba == 1

    def test_missing_wind_returns_none(self):
        result = _parse_round_text("一局 0 本场")
        assert result is None

    def test_missing_number_returns_none(self):
        result = _parse_round_text("东 0 本场")
        assert result is None

    def test_default_honba(self):
        result = _parse_round_text("东一局")
        assert result is not None
        assert result.honba == 0
        assert result.kyotaku == 0


class TestParseTimerText:
    """倒计时后处理测试"""

    def test_normal_timer(self):
        assert _parse_timer_text("8") == 8

    def test_timer_with_colon(self):
        assert _parse_timer_text("1:30") == 90

    def test_empty_returns_none(self):
        assert _parse_timer_text("") is None

    def test_no_digits_returns_none(self):
        assert _parse_timer_text("abc") is None

    def test_large_number(self):
        assert _parse_timer_text("300") == 300


class TestTextRecognizerInit:
    """TextRecognizer 初始化测试"""

    def test_create_instance(self):
        from majsoul_recognizer.recognition.text_recognizer import TextRecognizer
        recognizer = TextRecognizer()
        assert recognizer is not None

    def test_recognize_score_without_ocr(self):
        """无 PaddleOCR 时返回 None（不崩溃）"""
        from majsoul_recognizer.recognition.text_recognizer import TextRecognizer
        import numpy as np
        recognizer = TextRecognizer()
        img = np.zeros((50, 200, 3), dtype=np.uint8)
        result = recognizer.recognize_score(img)
        # 无 PaddleOCR 返回 None，有则返回数字
        assert result is None or isinstance(result, int)
```

- [ ] **Step 3: 运行测试确认失败**

```bash
pytest tests/recognition/test_text_recognizer.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: 实现 TextRecognizer**

`src/majsoul_recognizer/recognition/text_recognizer.py`:

```python
"""文字识别器"""

import logging
import re
from pathlib import Path

import cv2
import numpy as np

from majsoul_recognizer.types import RoundInfo

logger = logging.getLogger(__name__)

# 风位映射
_WIND_MAP = {
    "东": "东", "東": "东",
    "南": "南",
}

# 局数映射
_NUMBER_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4,
    "1": 1, "2": 2, "3": 3, "4": 4,
}

# "本场" 关键字变体
_HONBA_KEYWORDS = ["本场", "本場"]

# "供托" 关键字变体
_KYOTAKU_KEYWORDS = ["供托", "供託"]

# 分数范围
_SCORE_MIN = -99999
_SCORE_MAX = 200000


def _parse_score_text(text: str) -> int | None:
    """分数后处理"""
    text = text.strip()
    if not text:
        return None

    is_negative = text.startswith("-")
    # 去除非数字字符（保留逗号和数字）
    cleaned = text.replace(" ", "").replace(",", "")
    # 提取连续数字
    digits = re.sub(r"[^0-9]", "", cleaned)
    if not digits:
        return None

    score = int(digits)
    if is_negative:
        score = -score

    if score < _SCORE_MIN or score > _SCORE_MAX:
        return None
    return score


def _parse_round_text(text: str) -> RoundInfo | None:
    """局次后处理"""
    wind = None
    number = None
    honba = 0
    kyotaku = 0

    # 匹配风位
    for char in text:
        if char in _WIND_MAP:
            wind = _WIND_MAP[char]
            break

    # 匹配局数
    for char in text:
        if char in _NUMBER_MAP:
            number = _NUMBER_MAP[char]
            break

    if wind is None or number is None:
        return None

    # 匹配本场
    for kw in _HONBA_KEYWORDS:
        idx = text.find(kw)
        if idx > 0:
            prefix = text[:idx]
            digits = re.sub(r"[^0-9]", "", prefix)
            if digits:
                honba = int(digits[-3:])  # 最多3位
            break

    # 匹配供托
    for kw in _KYOTAKU_KEYWORDS:
        idx = text.find(kw)
        if idx > 0:
            prefix = text[:idx]
            digits = re.sub(r"[^0-9]", "", prefix)
            if digits:
                kyotaku = int(digits[-3:])
            break

    return RoundInfo(wind=wind, number=number, honba=honba, kyotaku=kyotaku)


def _parse_timer_text(text: str) -> int | None:
    """倒计时后处理"""
    text = text.strip()
    if not text:
        return None

    # 处理 MM:SS 格式
    if ":" in text:
        parts = text.split(":")
        if len(parts) == 2:
            try:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            except ValueError:
                return None

    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return None
    return int(digits)


class TextRecognizer:
    """文字识别器"""

    def __init__(self, model_dir: Path | str | None = None):
        self._ocr = None
        try:
            from paddleocr import PaddleOCR
            kwargs = dict(
                use_angle_cls=False,
                lang="ch",
                use_gpu=False,
                show_log=False,
            )
            if model_dir:
                kwargs["det_model_dir"] = model_dir
            self._ocr = PaddleOCR(**kwargs)
        except ImportError:
            logger.warning("PaddleOCR not available, text recognition will return None")
        except Exception as e:
            logger.warning("PaddleOCR init failed: %s", e)

    def recognize_score(self, image: np.ndarray) -> int | None:
        """识别分数区域"""
        if image is None or image.size == 0:
            return None
        text = self._run_ocr(image)
        return _parse_score_text(text) if text else None

    def recognize_round(self, image: np.ndarray) -> RoundInfo | None:
        """识别局次信息"""
        if image is None or image.size == 0:
            return None
        text = self._run_ocr(image)
        return _parse_round_text(text) if text else None

    def recognize_timer(self, image: np.ndarray) -> int | None:
        """识别倒计时"""
        if image is None or image.size == 0:
            return None
        if image.shape[0] < 5 or image.shape[1] < 5:
            return None
        text = self._run_ocr(image)
        return _parse_timer_text(text) if text else None

    def _run_ocr(self, image: np.ndarray) -> str | None:
        """执行 OCR 推理"""
        if self._ocr is None:
            return None
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            result = self._ocr.ocr(binary, cls=False)
            if result and result[0]:
                texts = [line[1][0] for line in result[0] if line[1]]
                return " ".join(texts)
        except Exception as e:
            logger.warning("OCR failed: %s", e)
        return None
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/recognition/test_text_recognizer.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 6: 提交**

```bash
git add src/majsoul_recognizer/recognition/text_recognizer.py \
      src/majsoul_recognizer/ocr_dicts/ \
      tests/recognition/test_text_recognizer.py
git commit -m "feat: add TextRecognizer with post-processing and OCR dictionaries"
```

---

## Task 4: PatternMatcher

**Files:**
- Create: `src/majsoul_recognizer/recognition/pattern_matcher.py`
- Modify: `tests/recognition/conftest.py` (添加假模板 fixture)
- Create: `tests/recognition/test_pattern_matcher.py`

- [ ] **Step 1: 更新 conftest.py — 添加假模板 fixture**

在 `tests/recognition/conftest.py` 末尾追加:

```python
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
```

- [ ] **Step 2: 编写 PatternMatcher 测试**

`tests/recognition/test_pattern_matcher.py`:

```python
"""PatternMatcher 测试"""

import cv2
import numpy as np
import pytest

from majsoul_recognizer.types import ActionMatch


class TestPatternMatcherInit:
    """PatternMatcher 初始化测试"""

    def test_load_templates(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)
        assert matcher is not None
        assert len(matcher._templates) == 7

    def test_template_names(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)
        names = {t[0] for t in matcher._templates}
        assert "吃" in names
        assert "碰" in names
        assert "过" in names


class TestPatternMatcherMatch:
    """模板匹配测试"""

    def test_match_finds_button(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)

        # 构造一张包含"碰"按钮的图像
        action_img = np.full((80, 400, 3), 30, dtype=np.uint8)
        template = cv2.imread(str(fake_template_dir / "pon.png"))
        # 将模板放在图像中央
        th, tw = template.shape[:2]
        action_img[20:20 + th, 150:150 + tw] = template

        results = matcher.match(action_img, threshold=0.5)
        assert len(results) >= 1
        names = [r.name for r in results]
        assert "碰" in names

    def test_match_empty_image(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)
        empty = np.zeros((80, 400, 3), dtype=np.uint8)
        results = matcher.match(empty, threshold=0.9)
        assert isinstance(results, list)

    def test_match_threshold_filters(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)
        action_img = np.full((80, 400, 3), 30, dtype=np.uint8)
        # 高阈值应返回更少结果
        low_results = matcher.match(action_img, threshold=0.3)
        high_results = matcher.match(action_img, threshold=0.99)
        assert len(low_results) >= len(high_results)

    def test_match_returns_action_match(self, fake_template_dir):
        from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
        matcher = PatternMatcher(fake_template_dir)
        action_img = np.full((80, 400, 3), 30, dtype=np.uint8)
        template = cv2.imread(str(fake_template_dir / "kan.png"))
        th, tw = template.shape[:2]
        action_img[20:20 + th, 150:150 + tw] = template

        results = matcher.match(action_img, threshold=0.5)
        for r in results:
            assert isinstance(r, ActionMatch)
            assert 0.0 <= r.score <= 1.0
```

- [ ] **Step 3: 运行测试确认失败**

```bash
pytest tests/recognition/test_pattern_matcher.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: 实现 PatternMatcher**

`src/majsoul_recognizer/recognition/pattern_matcher.py`:

```python
"""动作按钮模板匹配"""

import logging
from pathlib import Path

import cv2
import numpy as np

from majsoul_recognizer.types import ActionMatch

logger = logging.getLogger(__name__)

# 模板文件名 → 动作名称映射
_TEMPLATE_NAMES = {
    "chi": "吃", "pon": "碰", "kan": "杠",
    "ron": "荣和", "tsumo": "自摸", "riichi": "立直", "skip": "过",
}


class PatternMatcher:
    """动作按钮模板匹配"""

    def __init__(self, template_dir: Path | str):
        self._templates: list[tuple[str, np.ndarray]] = []
        template_dir = Path(template_dir)
        if not template_dir.exists():
            logger.warning("Template directory not found: %s", template_dir)
            return

        for filename, action_name in _TEMPLATE_NAMES.items():
            path = template_dir / f"{filename}.png"
            if path.exists():
                img = cv2.imread(str(path))
                if img is not None:
                    self._templates.append((action_name, img))
                    logger.debug("Loaded template: %s", filename)
            else:
                logger.debug("Template not found: %s", path)

    def match(self, image: np.ndarray, threshold: float = 0.85) -> list[ActionMatch]:
        """匹配动作按钮"""
        if image is None or image.size == 0:
            return []

        results: list[ActionMatch] = []
        for action_name, template in self._templates:
            th, tw = template.shape[:2]
            ih, iw = image.shape[:2]
            if th > ih or tw > iw:
                continue

            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val >= threshold:
                results.append(ActionMatch(name=action_name, score=round(float(max_val), 4)))

        return sorted(results, key=lambda x: x.score, reverse=True)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/recognition/test_pattern_matcher.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 6: 提交**

```bash
git add src/majsoul_recognizer/recognition/pattern_matcher.py tests/recognition/test_pattern_matcher.py tests/recognition/conftest.py
git commit -m "feat: add PatternMatcher with template-based action button detection"
```

---

## Task 5: GameStateBuilder

**Files:**
- Create: `src/majsoul_recognizer/recognition/state_builder.py`
- Create: `tests/recognition/test_state_builder.py`

- [ ] **Step 1: 编写 GameStateBuilder 测试**

`tests/recognition/test_state_builder.py`:

```python
"""GameStateBuilder 测试"""

import pytest

from majsoul_recognizer.types import (
    BBox, Detection, ActionMatch, CallGroup, RoundInfo, GameState, ZoneName,
)
from tests.recognition.conftest import make_detection


class TestZoneKeyMapping:
    """键名映射测试"""

    def test_score_self_to_self(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        assert builder._zone_key("score_self") == "self"

    def test_discards_right_to_right(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        assert builder._zone_key("discards_right") == "right"

    def test_unknown_zone_returns_as_is(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        assert builder._zone_key("hand") == "hand"


class TestHandSorting:
    """手牌排序测试"""

    def test_hand_sorted_by_x(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "hand": [
                make_detection(200, 0, 50, 70, "3m"),
                make_detection(100, 0, 50, 70, "1m"),
                make_detection(150, 0, 50, 70, "2m"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert state.hand == ["1m", "2m", "3m"]


class TestDrawnTileDetection:
    """drawn_tile 间隔检测测试"""

    def test_drawn_tile_detected_by_gap(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        config = RecognitionConfig(drawn_tile_gap_multiplier=2.0)
        builder = GameStateBuilder(config)

        # 13 张手牌 + 1 张 drawn_tile（间距大）
        hand_dets = [make_detection(i * 55, 0, 50, 70, f"{i+1}m") for i in range(13)]
        # drawn_tile 放远一些
        hand_dets.append(make_detection(13 * 55 + 80, 0, 50, 70, "9m"))

        detections = {"hand": hand_dets}
        state = builder.build(detections, {}, None, None, [])
        assert state.drawn_tile == "9m"
        assert len(state.hand) == 13

    def test_no_drawn_tile_13_tiles(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        hand_dets = [make_detection(i * 55, 0, 50, 70, f"{(i % 9) + 1}m") for i in range(13)]
        detections = {"hand": hand_dets}
        state = builder.build(detections, {}, None, None, [])
        assert state.drawn_tile is None
        assert len(state.hand) == 13


class TestDoraBuilding:
    """宝牌构建测试"""

    def test_dora_from_detections(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "dora": [
                make_detection(10, 10, 50, 70, "5m"),
                make_detection(70, 10, 50, 70, "back"),  # 辅助类别应被过滤
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert state.dora_indicators == ["5m"]


class TestScoresBuilding:
    """分数构建测试"""

    def test_scores_from_zones(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        scores = {"score_self": 25000, "score_right": 30000, "score_opposite": None}
        state = builder.build({}, scores, None, None, [])
        assert state.scores == {"self": 25000, "right": 30000}
        assert "opposite" not in state.scores


class TestActionsBuilding:
    """动作构建测试"""

    def test_actions_from_matches(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        actions = [ActionMatch(name="碰", score=0.92), ActionMatch(name="过", score=0.88)]
        state = builder.build({}, {}, None, None, actions)
        assert state.actions == ["碰", "过"]


class TestDiscardsBuilding:
    """牌河构建测试"""

    def test_discards_self_sorted(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "discards_self": [
                make_detection(60, 0, 50, 70, "3m"),
                make_detection(0, 0, 50, 70, "1m"),
                make_detection(120, 0, 50, 70, "5p"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert state.discards == {"self": ["1m", "3m", "5p"]}

    def test_discards_filters_auxiliary(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "discards_self": [
                make_detection(0, 0, 50, 70, "1m"),
                make_detection(60, 0, 50, 70, "back"),
                make_detection(120, 0, 50, 70, "dora_frame"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert state.discards == {"self": ["1m"]}


class TestCallsParsing:
    """副露解析测试"""

    def test_chi_calls(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "calls_self": [
                make_detection(0, 0, 50, 70, "1s"),
                make_detection(55, 0, 50, 70, "2s"),
                make_detection(110, 0, 50, 70, "3s"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert "self" in state.calls
        assert len(state.calls["self"]) == 1
        call = state.calls["self"][0]
        assert call.type == "chi"
        assert call.tiles == ["1s", "2s", "3s"]

    def test_pon_calls(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        detections = {
            "calls_self": [
                make_detection(0, 0, 50, 70, "5p"),
                make_detection(55, 0, 50, 70, "5p"),
                make_detection(110, 0, 50, 70, "5p"),
            ],
        }
        state = builder.build(detections, {}, None, None, [])
        assert "self" in state.calls
        call = state.calls["self"][0]
        assert call.type == "pon"
        assert call.tiles == ["5p", "5p", "5p"]

    def test_empty_detections_returns_empty_state(self):
        from majsoul_recognizer.recognition.state_builder import GameStateBuilder
        from majsoul_recognizer.recognition.config import RecognitionConfig
        builder = GameStateBuilder(RecognitionConfig())
        state = builder.build({}, {}, None, None, [])
        assert state.hand == []
        assert state.drawn_tile is None
        assert state.dora_indicators == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/recognition/test_state_builder.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 GameStateBuilder**

`src/majsoul_recognizer/recognition/state_builder.py`:

```python
"""游戏状态构建与规则校验"""

import logging
from statistics import median

from majsoul_recognizer.recognition.config import RecognitionConfig
from majsoul_recognizer.recognition.tile_detector import _resolve_rotated_tiles
from majsoul_recognizer.types import (
    ActionMatch, BBox, CallGroup, Detection, GameState, RoundInfo,
)

logger = logging.getLogger(__name__)

# 辅助类别集合
_AUXILIARY_CODES = frozenset(["back", "rotated", "dora_frame"])

# 赤宝牌合并映射 (用于牌数上限校验和副露 kakan 匹配)
_RED_DORA_MERGE = {"5mr": "5m", "5pr": "5p", "5sr": "5s"}

# rotated_index → from_player 映射 (spec §8.2 统一规则)
# 横置牌逆时针 90° 指向的方位 = 来源方位
_ROTATED_INDEX_TO_PLAYER = {
    (0, "chi"): "right",
    (1, "chi"): "opposite",
    (2, "chi"): "left",
    (0, "pon"): "right",
    (1, "pon"): "opposite",
    (2, "pon"): "left",
    (0, "kan"): "right",
    (1, "kan"): "opposite",
    (2, "kan"): "left",
    (3, "kan"): "left",
}

# zone_name 前缀 → GameState 字典键
_ZONE_KEY_MAP = {
    "score_self": "self", "score_right": "right",
    "score_opposite": "opposite", "score_left": "left",
    "discards_self": "self", "discards_right": "right",
    "discards_opposite": "opposite", "discards_left": "left",
    "calls_self": "self",
}


def _median_value(dets: list[Detection], attr: str) -> float:
    """计算检测框某属性的中位值"""
    values = sorted(getattr(d.bbox, attr) for d in dets)
    return values[len(values) // 2] if values else 0


def _sort_horizontal_grid(dets: list[Detection]) -> list[Detection]:
    """水平网格排序（自家/对家牌河）"""
    if len(dets) <= 1:
        return dets
    median_h = _median_value(dets, "height")
    threshold = median_h * 0.5

    sorted_by_y = sorted(dets, key=lambda d: d.bbox.y)
    rows: list[list[Detection]] = []
    current_row = [sorted_by_y[0]]
    for d in sorted_by_y[1:]:
        if abs(d.bbox.y - current_row[0].bbox.y) < threshold:
            current_row.append(d)
        else:
            rows.append(sorted(current_row, key=lambda d: d.bbox.x))
            current_row = [d]
    rows.append(sorted(current_row, key=lambda d: d.bbox.x))
    return [d for row in rows for d in row]


def _sort_vertical_grid(dets: list[Detection], ascending_x: bool) -> list[Detection]:
    """垂直网格排序（左/右家牌河）"""
    if len(dets) <= 1:
        return dets
    median_w = _median_value(dets, "width")
    threshold = median_w * 0.5

    sorted_by_x = sorted(dets, key=lambda d: d.bbox.x, reverse=not ascending_x)
    cols: list[list[Detection]] = []
    current_col = [sorted_by_x[0]]
    for d in sorted_by_x[1:]:
        if abs(d.bbox.x - current_col[0].bbox.x) < threshold:
            current_col.append(d)
        else:
            cols.append(sorted(current_col, key=lambda d: d.bbox.y))
            current_col = [d]
    cols.append(sorted(current_col, key=lambda d: d.bbox.y))
    return [d for col in cols for d in col]


def _sort_discards(detections: list[Detection], zone_name: str) -> list[Detection]:
    """对牌河检测结果排序"""
    if not detections:
        return []
    if zone_name in ("discards_self", "discards_opposite"):
        return _sort_horizontal_grid(detections)
    elif zone_name == "discards_right":
        return _sort_vertical_grid(detections, ascending_x=True)
    else:  # discards_left
        return _sort_vertical_grid(detections, ascending_x=False)


class GameStateBuilder:
    """将子模块原始结果组装为 GameState"""

    def __init__(self, config: RecognitionConfig):
        self._config = config

    def _zone_key(self, zone_name: str) -> str:
        return _ZONE_KEY_MAP.get(zone_name, zone_name)

    def build(
        self,
        detections: dict[str, list[Detection]],
        scores: dict[str, int | None],
        round_info: RoundInfo | None,
        timer: int | None,
        actions: list[ActionMatch],
        prev_state: GameState | None = None,
    ) -> GameState:
        hand, drawn_tile = self._build_hand(detections.get("hand", []))
        dora_indicators = self._build_dora(detections.get("dora", []))
        state_scores = self._build_scores(scores)
        discards = self._build_discards(detections)
        calls = self._build_calls(detections.get("calls_self", []), prev_state)
        state_actions = [a.name for a in actions]

        return GameState(
            round_info=round_info,
            dora_indicators=dora_indicators,
            scores=state_scores,
            hand=hand,
            drawn_tile=drawn_tile,
            calls=calls,
            discards=discards,
            actions=state_actions,
            timer_remaining=timer,
        )

    def _build_hand(self, dets: list[Detection]) -> tuple[list[str], str | None]:
        """构建手牌，返回 (hand_list, drawn_tile)

        算法 (规格 §8.2):
        1. 按 bbox.x 排序
        2. 计算相邻间距
        3. 若 gap[i] > median_gap * multiplier，则 dets[i+1] 为 drawn_tile
        4. 特殊处理: 14 张时最后一张为 drawn_tile；13 张无间距时无 drawn_tile
        """
        # 过滤辅助类别
        valid = [d for d in dets if d.tile_code not in _AUXILIARY_CODES]
        if not valid:
            return [], None

        sorted_dets = sorted(valid, key=lambda d: d.bbox.x)

        if len(sorted_dets) <= 1:
            codes = [d.tile_code for d in sorted_dets]
            return codes, None

        # 计算间距
        gaps = []
        for i in range(len(sorted_dets) - 1):
            gap = sorted_dets[i + 1].bbox.x - (sorted_dets[i].bbox.x + sorted_dets[i].bbox.width)
            gaps.append(gap)

        if not gaps:
            return [d.tile_code for d in sorted_dets], None

        median_gap = float(median(gaps))
        threshold = median_gap * self._config.drawn_tile_gap_multiplier

        # 查找第一个大间距 — 间距后的牌 (dets[i+1]) 为 drawn_tile
        drawn_tile_idx = -1
        for i in range(len(gaps)):
            if gaps[i] > threshold:
                drawn_tile_idx = i + 1
                break

        if drawn_tile_idx >= 0:
            hand_codes = [d.tile_code for d in sorted_dets[:drawn_tile_idx]]
            hand_codes.extend(d.tile_code for d in sorted_dets[drawn_tile_idx + 1:])
            drawn_tile = sorted_dets[drawn_tile_idx].tile_code
            return hand_codes, drawn_tile

        # 无大间距: 14 张时最后一张为 drawn_tile
        if len(sorted_dets) == 14:
            return [d.tile_code for d in sorted_dets[:-1]], sorted_dets[-1].tile_code

        return [d.tile_code for d in sorted_dets], None

    def _build_dora(self, dets: list[Detection]) -> list[str]:
        """构建宝牌指示器"""
        return [d.tile_code for d in sorted(dets, key=lambda d: d.bbox.x)
                if d.tile_code not in _AUXILIARY_CODES]

    def _build_scores(self, scores: dict[str, int | None]) -> dict[str, int]:
        """构建分数"""
        result = {}
        for zone_name, score in scores.items():
            if score is not None:
                key = self._zone_key(zone_name)
                result[key] = score
        return result

    def _build_discards(self, detections: dict[str, list[Detection]]) -> dict[str, list[str]]:
        """构建牌河"""
        result = {}
        discard_zones = ["discards_self", "discards_right", "discards_opposite", "discards_left"]
        for zone_name in discard_zones:
            if zone_name not in detections:
                continue
            dets = [d for d in detections[zone_name] if d.tile_code not in _AUXILIARY_CODES]
            sorted_dets = _sort_discards(dets, zone_name)
            key = self._zone_key(zone_name)
            result[key] = [d.tile_code for d in sorted_dets]
        return result

    def _build_calls(self, dets: list[Detection], prev_state: GameState | None) -> dict[str, list[CallGroup]]:
        """构建副露 (spec §8.2)

        算法:
        1. 按 bbox.x 排序，仅过滤 back 和 dora_frame（保留 rotated）
        2. 使用 _resolve_rotated_tiles() 找横置牌
        3. 仅用正常牌（排除 rotated/back/dora_frame）计算间距分组
        4. 每组根据牌数 + rotated_map 推断副露类型
        """
        if not dets:
            return {}

        # Step 1: 排序，仅过滤 dora_frame（back 和 rotated 保留用于后续分析）
        sorted_all = sorted(dets, key=lambda d: d.bbox.x)
        filtered = [d for d in sorted_all if d.tile_code != "dora_frame"]
        if not filtered:
            return {}

        # Step 2: 找横置牌映射
        rotated_map = _resolve_rotated_tiles(filtered)

        # Step 3: 仅用正常牌（不含 back/rotated）做间距分组
        normals = [d for d in filtered if d.tile_code not in ("back", "rotated")]
        if not normals:
            return {}
        if len(normals) <= 1:
            return {}

        gaps = []
        for i in range(len(normals) - 1):
            gap = normals[i + 1].bbox.x - (normals[i].bbox.x + normals[i].bbox.width)
            gaps.append(gap)

        median_gap = float(median(gaps)) if gaps else 0
        threshold = median_gap * self._config.call_group_gap_multiplier

        # 分组 (基于正常牌的索引)
        groups: list[list[Detection]] = []
        current_group = [normals[0]]
        for i in range(len(gaps)):
            if gaps[i] > threshold:
                groups.append(current_group)
                current_group = [normals[i + 1]]
            else:
                current_group.append(normals[i + 1])
        groups.append(current_group)

        # Step 4: 每组构建 CallGroup
        # 构建 normal detection → group index 映射，用于查找 rotated_index
        normal_to_group_pos: dict[int, tuple[int, int]] = {}
        for gi, group in enumerate(groups):
            for pi, det in enumerate(group):
                # 使用 bbox 中心坐标作为唯一标识
                normal_to_group_pos[id(det)] = (gi, pi)

        calls: list[CallGroup] = []
        for gi, group in enumerate(groups):
            tiles = [d.tile_code for d in group]
            n = len(tiles)

            # 检查该组是否有 rotated 标记
            rotated_idx_in_group: int | None = None
            for pi, det in enumerate(group):
                # 检查 rotated_map 中是否有此 detection 的关联
                for normal_idx, rotated_det in rotated_map.items():
                    if rotated_det is not None:
                        # 通过 bbox 位置匹配
                        nrx, nry = det.bbox.center
                        rrx, rry = rotated_det.bbox.center
                        if abs(nrx - rrx) < det.bbox.width and abs(nry - rry) < det.bbox.height:
                            rotated_idx_in_group = pi
                            break
                if rotated_idx_in_group is not None:
                    break

            # 检查 ankan: 原始 dets 中同区域是否有 back 牌
            has_back = any(d.tile_code == "back" for d in filtered)
            back_count = sum(1 for d in filtered if d.tile_code == "back")

            if n == 4 and back_count >= 2:
                # ankan: 两侧 2 张 back
                call = CallGroup(type="ankan", tiles=tiles, rotated_index=None, from_player=None)
                calls.append(call)
            elif n == 4:
                # kan or kakan
                call = self._infer_kan_call(tiles, rotated_idx_in_group, prev_state)
                if call:
                    calls.append(call)
            elif n == 3:
                # chi or pon
                call_type = "pon" if len(set(tiles)) == 1 else "chi"
                from_player = _ROTATED_INDEX_TO_PLAYER.get(
                    (rotated_idx_in_group, call_type)
                ) if rotated_idx_in_group is not None else None
                call = CallGroup(
                    type=call_type, tiles=tiles,
                    rotated_index=rotated_idx_in_group,
                    from_player=from_player,
                )
                calls.append(call)

        if calls:
            return {"self": calls}
        return {}

    def _infer_kan_call(
        self, tiles: list[str], rotated_index: int | None,
        prev_state: GameState | None,
    ) -> CallGroup | None:
        """推断 4 张牌的杠类型 (kan/kakan)"""
        # 检查 kakan: prev_state 中有 3 张相同花色数字的碰组
        if prev_state is not None:
            for prev_call in prev_state.calls.get("self", []):
                if prev_call.type == "pon":
                    prev_normalized = {_RED_DORA_MERGE.get(t, t) for t in prev_call.tiles}
                    curr_normalized = {_RED_DORA_MERGE.get(t, t) for t in tiles}
                    if prev_normalized == curr_normalized:
                        # kakan: 继承碰组的 from_player
                        return CallGroup(
                            type="kakan", tiles=tiles,
                            rotated_index=rotated_index,
                            from_player=prev_call.from_player,
                        )

        # 默认: kan (明杠)
        from_player = _ROTATED_INDEX_TO_PLAYER.get(
            (rotated_index, "kan")
        ) if rotated_index is not None else None
        return CallGroup(
            type="kan", tiles=tiles,
            rotated_index=rotated_index,
            from_player=from_player,
        )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/recognition/test_state_builder.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 5: 提交**

```bash
git add src/majsoul_recognizer/recognition/state_builder.py tests/recognition/test_state_builder.py
git commit -m "feat: add GameStateBuilder with hand sorting, drawn tile, calls parsing, discards"
```

---

## Task 6: Validator

**Files:**
- Modify: `src/majsoul_recognizer/recognition/state_builder.py` (添加 Validator 类)
- Create: `tests/recognition/test_validator.py`

- [ ] **Step 1: 编写 Validator 测试**

`tests/recognition/test_validator.py`:

```python
"""Validator 测试"""

import pytest

from majsoul_recognizer.types import (
    BBox, Detection, CallGroup, GameState, RoundInfo, ZoneName,
)
from majsoul_recognizer.recognition.config import RecognitionConfig
from tests.recognition.conftest import make_detection


class TestHandCountValidation:
    """手牌数量校验测试"""

    def test_valid_13_tiles_no_drawn(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(hand=["1m"] * 13)
        result = validator.validate(state)
        hand_warnings = [w for w in result.warnings if "hand_count" in w]
        assert len(hand_warnings) == 0

    def test_valid_13_tiles_with_drawn(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(hand=["1m"] * 13, drawn_tile="9m")
        result = validator.validate(state)
        hand_warnings = [w for w in result.warnings if "hand_count" in w]
        assert len(hand_warnings) == 0

    def test_invalid_hand_count(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(hand=["1m"] * 10)
        result = validator.validate(state)
        hand_warnings = [w for w in result.warnings if "hand_count" in w]
        assert len(hand_warnings) > 0

    def test_hand_count_with_kan(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        kan = CallGroup(type="kan", tiles=["1m", "1m", "1m", "1m"])
        state = GameState(hand=["2m"] * 12, calls={"self": [kan]})
        result = validator.validate(state)
        hand_warnings = [w for w in result.warnings if "hand_count" in w]
        assert len(hand_warnings) == 0


class TestTileOverflow:
    """牌数上限校验测试"""

    def test_no_overflow(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(hand=["1m", "1m", "1m"])
        result = validator.validate(state)
        overflow = [w for w in result.warnings if "tile_overflow" in w]
        assert len(overflow) == 0

    def test_overflow_detected(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        # 同一种牌出现 5 次（超过上限 4）
        state = GameState(hand=["1m", "1m", "1m", "1m", "1m"])
        result = validator.validate(state)
        overflow = [w for w in result.warnings if "tile_overflow" in w]
        assert len(overflow) > 0

    def test_red_dora_counted_with_normal(self):
        """赤宝牌与普通牌合并计数"""
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        # 4 张 5m + 1 张 5mr = 5 次，超过上限
        state = GameState(hand=["5m", "5m", "5m", "5m", "5mr"])
        result = validator.validate(state)
        overflow = [w for w in result.warnings if "tile_overflow" in w]
        assert len(overflow) > 0


class TestScoreValidation:
    """分数合理性测试"""

    def test_valid_score(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(scores={"self": 25000})
        result = validator.validate(state)
        score_warnings = [w for w in result.warnings if "score_anomaly" in w]
        assert len(score_warnings) == 0

    def test_negative_score_allowed(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(scores={"self": -1000})
        result = validator.validate(state)
        score_warnings = [w for w in result.warnings if "score_anomaly" in w]
        assert len(score_warnings) == 0

    def test_score_too_high(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(scores={"self": 999999})
        result = validator.validate(state)
        score_warnings = [w for w in result.warnings if "score_anomaly" in w]
        assert len(score_warnings) > 0


class TestDiscardContinuity:
    """牌河连续性测试"""

    def test_first_frame_always_valid(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state = GameState(discards={"self": ["1m", "2m", "3m"]})
        result = validator.validate(state)
        discard_warnings = [w for w in result.warnings if "discard_jump" in w]
        assert len(discard_warnings) == 0

    def test_one_new_discard_is_valid(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state1 = GameState(discards={"self": ["1m"]})
        validator.validate(state1)
        state2 = GameState(discards={"self": ["1m", "2m"]})
        result = validator.validate(state2)
        discard_warnings = [w for w in result.warnings if "discard_jump" in w]
        assert len(discard_warnings) == 0

    def test_two_new_discards_is_invalid(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        state1 = GameState(discards={"self": ["1m"]})
        validator.validate(state1)
        state2 = GameState(discards={"self": ["1m", "2m", "3m"]})
        result = validator.validate(state2)
        discard_warnings = [w for w in result.warnings if "discard_jump" in w]
        assert len(discard_warnings) > 0


class TestDetectionFusion:
    """Detection 级帧间融合测试"""

    def test_first_frame_returns_as_is(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        dets = {"hand": [make_detection(0, 0, 50, 70, "1m")]}
        result = validator.fuse_detections(dets)
        assert "hand" in result
        assert len(result["hand"]) == 1

    def test_fusion_majority_vote(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        # 帧 1: 1m
        frame1 = {"hand": [make_detection(0, 0, 50, 70, "1m", 0.9)]}
        validator.fuse_detections(frame1)
        # 帧 2: 9m (同位置)
        frame2 = {"hand": [make_detection(0, 0, 50, 70, "9m", 0.85)]}
        validator.fuse_detections(frame2)
        # 帧 3: 1m (同位置) — 多数投票: 1m 出现 2 次 vs 9m 出现 1 次
        frame3 = {"hand": [make_detection(0, 0, 50, 70, "1m", 0.92)]}
        result = validator.fuse_detections(frame3)
        assert result["hand"][0].tile_code == "1m"

    def test_reset_clears_history(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        frame1 = {"hand": [make_detection(0, 0, 50, 70, "1m")]}
        validator.fuse_detections(frame1)
        validator.reset()
        assert validator.prev_state is None


class TestNoDetectionWarning:
    """连续无检测结果 warning 测试"""

    def test_no_detection_5_frames_warning(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        # 连续 5 帧空检测结果
        for _ in range(5):
            validator.fuse_detections({"hand": []})
        state = GameState()
        result = validator.validate(state)
        assert any("no_detection_5_frames" in w for w in result.warnings)

    def test_has_detection_no_warning(self):
        from majsoul_recognizer.recognition.state_builder import Validator
        validator = Validator(RecognitionConfig())
        for _ in range(5):
            validator.fuse_detections({"hand": [make_detection(0, 0, 50, 70, "1m")]})
        state = GameState()
        result = validator.validate(state)
        assert not any("no_detection_5_frames" in w for w in result.warnings)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/recognition/test_validator.py -v
```

Expected: FAIL — `ImportError: cannot import name 'Validator'`

- [ ] **Step 3: 在 state_builder.py 中添加 Validator 类**

在 `src/majsoul_recognizer/recognition/state_builder.py` 末尾追加:

```python
class Validator:
    """规则校验与 Detection 级帧间融合"""

    def __init__(self, config: RecognitionConfig):
        self._config = config
        self._prev_state: GameState | None = None
        self._detection_window: list[dict[str, list[Detection]]] = []

    @property
    def prev_state(self) -> GameState | None:
        return self._prev_state

    def validate(self, state: GameState) -> GameState:
        """校验当前状态，返回带 warnings 的新实例"""
        warnings: list[str] = []

        # 规则 1: 手牌数量
        kan_count = sum(
            1 for group in state.calls.values()
            for c in group if c.type in ("kan", "ankan", "kakan")
        )
        expected = 13 - kan_count
        actual = len(state.hand) + (1 if state.drawn_tile else 0)
        if actual != expected:
            warnings.append(f"hand_count_mismatch: got {actual}, expected {expected}")

        # 规则 2: 牌数上限
        tile_counter: dict[str, int] = {}
        all_tiles = list(state.hand)
        if state.drawn_tile:
            all_tiles.append(state.drawn_tile)
        for group_list in state.calls.values():
            for call in group_list:
                all_tiles.extend(call.tiles)
        for zone_tiles in state.discards.values():
            all_tiles.extend(zone_tiles)
        all_tiles.extend(state.dora_indicators)

        for tile in all_tiles:
            key = _RED_DORA_MERGE.get(tile, tile)
            tile_counter[key] = tile_counter.get(key, 0) + 1
        for tile, count in tile_counter.items():
            if count > 4:
                warnings.append(f"tile_overflow: {tile} appears {count} times")

        # 规则 3: 牌河连续性
        if self._prev_state is not None:
            for player in ["self", "right", "opposite", "left"]:
                prev_len = len(self._prev_state.discards.get(player, []))
                curr_len = len(state.discards.get(player, []))
                diff = curr_len - prev_len
                if diff < 0 or diff > 1:
                    warnings.append(f"discard_jump: {player} diff={diff}")

        # 规则 4: 分数合理性
        for player, score in state.scores.items():
            if score < self._config.score_min or score > self._config.score_max:
                warnings.append(f"score_anomaly: {player}={score}")

        # 规则 5: 连续无检测结果 (spec §12)
        total_dets = sum(len(d) for d in self._detection_window[-1:].values()) if self._detection_window else 0
        if len(self._detection_window) >= 5 and all(
            sum(len(d) for d in frame.values()) == 0
            for frame in self._detection_window[-5:]
        ):
            warnings.append("no_detection_5_frames")

        self._prev_state = state
        return state.model_copy(update={"warnings": warnings})

    def fuse_detections(self, current: dict[str, list[Detection]]) -> dict[str, list[Detection]]:
        """Detection 级帧间融合"""
        self._detection_window.append(current)
        window_size = self._config.fusion_window_size
        if len(self._detection_window) > window_size:
            self._detection_window = self._detection_window[-window_size:]

        if len(self._detection_window) == 1:
            return current

        result: dict[str, list[Detection]] = {}
        for zone_name, dets in current.items():
            fused: list[Detection] = []
            for det in dets:
                cx, cy = det.bbox.center
                votes: dict[str, list[float]] = {}

                for frame in self._detection_window:
                    for hist_det in frame.get(zone_name, []):
                        hcx, hcy = hist_det.bbox.center
                        dist = ((cx - hcx) ** 2 + (cy - hcy) ** 2) ** 0.5
                        median_w = _median_value(dets, "width")
                        if dist < median_w * 0.5:
                            votes.setdefault(hist_det.tile_code, []).append(hist_det.confidence)

                if votes:
                    # 多数投票
                    best_code = max(votes.keys(), key=lambda k: len(votes[k]))
                    avg_conf = sum(votes[best_code]) / len(votes[best_code])
                    # 不一致时降低置信度
                    if len(votes) > 1:
                        total_votes = sum(len(v) for v in votes.values())
                        if len(votes[best_code]) < total_votes:
                            avg_conf *= 0.8
                    fused.append(det.model_copy(update={
                        "tile_code": best_code,
                        "confidence": round(avg_conf, 4),
                    }))
                else:
                    fused.append(det)
            result[zone_name] = fused
        return result

    def reset(self):
        """重置历史状态"""
        self._prev_state = None
        self._detection_window = []
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/recognition/test_validator.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 5: 提交**

```bash
git add src/majsoul_recognizer/recognition/state_builder.py tests/recognition/test_validator.py
git commit -m "feat: add Validator with hand count, tile overflow, score, discard rules and fusion"
```

---

## Task 7: RecognitionEngine

**Files:**
- Create: `src/majsoul_recognizer/recognition/engine.py`
- Modify: `src/majsoul_recognizer/recognition/__init__.py`
- Create: `tests/recognition/test_engine.py`

- [ ] **Step 1: 编写 RecognitionEngine 测试**

`tests/recognition/test_engine.py`:

```python
"""RecognitionEngine 集成测试"""

import numpy as np
import pytest

from majsoul_recognizer.types import GameState, ZoneName
from majsoul_recognizer.recognition.config import RecognitionConfig


class TestRecognitionEngineInit:
    """引擎初始化测试"""

    def test_create_with_default_config(self):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig()
        engine = RecognitionEngine(config)
        assert engine is not None

    def test_create_with_none_config(self):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        engine = RecognitionEngine()
        assert engine is not None


class TestRecognitionEngineRecognize:
    """引擎识别测试"""

    def test_empty_zones_returns_warning(self):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        engine = RecognitionEngine()
        state = engine.recognize({})
        assert isinstance(state, GameState)
        assert "empty_zones" in state.warnings

    def test_recognize_with_zones(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        zones = {
            "hand": np.zeros((100, 200, 3), dtype=np.uint8),
            "dora": np.zeros((60, 150, 3), dtype=np.uint8),
        }
        state = engine.recognize(zones)
        assert isinstance(state, GameState)

    def test_recognize_non_static_none_safe(self, dummy_detector_path, fake_template_dir):
        """空区域图像不崩溃"""
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        zones = {
            "hand": np.zeros((100, 200, 3), dtype=np.uint8),
            "score_self": np.array([], dtype=np.uint8),  # 空
        }
        state = engine.recognize(zones)
        assert isinstance(state, GameState)


class TestRecognitionEngineLifecycle:
    """生命周期测试"""

    def test_context_manager(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        with RecognitionEngine(config) as engine:
            state = engine.recognize({})
            assert isinstance(state, GameState)

    def test_reset(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        engine.reset()
        assert engine._validator.prev_state is None

    def test_warmup(self, dummy_detector_path, fake_template_dir):
        from majsoul_recognizer.recognition.engine import RecognitionEngine
        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        engine = RecognitionEngine(config)
        engine.warmup()
        assert engine._warmed_up is True
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/recognition/test_engine.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 RecognitionEngine**

`src/majsoul_recognizer/recognition/engine.py`:

```python
"""识别引擎统一入口"""

import logging
import time

import numpy as np

from majsoul_recognizer.recognition.config import RecognitionConfig
from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
from majsoul_recognizer.recognition.state_builder import GameStateBuilder, Validator
from majsoul_recognizer.recognition.text_recognizer import TextRecognizer
from majsoul_recognizer.recognition.tile_detector import TileDetector
from majsoul_recognizer.types import GameState, ZoneName

logger = logging.getLogger(__name__)


class RecognitionEngine:
    """识别引擎统一入口"""

    def __init__(self, config: RecognitionConfig | None = None):
        self._config = config or RecognitionConfig()
        self._warmed_up = False

        # 延迟初始化重型资源
        self._detector: TileDetector | None = None
        self._ocr: TextRecognizer | None = None
        self._matcher: PatternMatcher | None = None
        self._builder = GameStateBuilder(self._config)
        self._validator = Validator(self._config)

    def _ensure_detector(self) -> TileDetector:
        if self._detector is None:
            model_path = self._config.get_model_path()
            self._detector = TileDetector(
                str(model_path),
                nms_iou=self._config.nms_iou_threshold,
            )
        return self._detector

    def _ensure_ocr(self) -> TextRecognizer:
        if self._ocr is None:
            self._ocr = TextRecognizer(
                str(self._config.ocr_model_dir) if self._config.ocr_model_dir else None
            )
        return self._ocr

    def _ensure_matcher(self) -> PatternMatcher:
        if self._matcher is None:
            self._matcher = PatternMatcher(self._config.get_template_dir())
        return self._matcher

    def recognize(self, zones: dict[str, np.ndarray]) -> GameState:
        """识别完整的游戏状态"""
        if not zones:
            return GameState(warnings=["empty_zones"])

        logger.info("Recognition started, %d zones received", len(zones))
        t_start = time.perf_counter()

        if not self._warmed_up:
            self.warmup()

        # 1. 牌面检测
        tile_zone_names = ["hand", "dora", "discards_self", "discards_right",
                           "discards_opposite", "discards_left", "calls_self"]
        tile_images = [(name, zones[name]) for name in tile_zone_names if name in zones]

        confidence = self._config.detection_confidence
        detector = self._ensure_detector()

        if self._config.enable_batch_detection and len(tile_images) > 1:
            detections = detector.detect_batch(tile_images, confidence)
        else:
            detections = {name: detector.detect(img, confidence) for name, img in tile_images}

        # 设置 zone_name
        for zone_name_str, dets in detections.items():
            try:
                zn = ZoneName(zone_name_str)
            except ValueError:
                logger.warning("Unknown zone name: %s, skipping", zone_name_str)
                continue
            detections[zone_name_str] = [
                d.model_copy(update={"zone_name": zn}) for d in dets
            ]

        # 2. Detection 级帧间融合
        detections = self._validator.fuse_detections(detections)

        # 3. 文字识别
        ocr = self._ensure_ocr()
        scores: dict[str, int | None] = {}
        for prefix in ["score_self", "score_right", "score_opposite", "score_left"]:
            if prefix in zones and zones[prefix].size > 0:
                scores[prefix] = ocr.recognize_score(zones[prefix])

        round_info = None
        if "round_info" in zones and zones["round_info"].size > 0:
            round_info = ocr.recognize_round(zones["round_info"])

        timer = None
        if "timer" in zones and zones["timer"].size > 0:
            timer = ocr.recognize_timer(zones["timer"])

        # 4. 模板匹配
        actions = []
        if "actions" in zones and zones["actions"].size > 0:
            matcher = self._ensure_matcher()
            actions = matcher.match(zones["actions"])

        # 5. 组装 + 校验
        state = self._builder.build(
            detections, scores, round_info, timer, actions,
            prev_state=self._validator.prev_state,
        )
        state = self._validator.validate(state)

        # 分数异常沿用上一帧 (spec §12)
        if self._validator.prev_state is not None:
            prev = self._validator.prev_state
            updates: dict[str, int] = {}
            extra_warnings: list[str] = []
            for player, score in state.scores.items():
                if (score < self._config.score_min or score > self._config.score_max):
                    prev_score = prev.scores.get(player)
                    if prev_score is not None:
                        updates[player] = prev_score
                        extra_warnings.append(f"score_fallback: {player} using prev={prev_score}")
            if updates:
                state = state.model_copy(update={
                    "scores": {**state.scores, **updates},
                    "warnings": state.warnings + extra_warnings,
                })

        elapsed = (time.perf_counter() - t_start) * 1000
        logger.info("Recognition done: hand=%d, warnings=%d, %.1fms",
                    len(state.hand), len(state.warnings), elapsed)
        return state

    def warmup(self) -> None:
        """预热引擎"""
        if self._warmed_up:
            return
        try:
            detector = self._ensure_detector()
            dummy = np.zeros((100, 100, 3), dtype=np.uint8)
            detector.detect(dummy, confidence=0.99)
            self._warmed_up = True
            logger.info("Engine warmup complete")
        except Exception as e:
            logger.warning("Warmup failed: %s", e)
            self._warmed_up = True  # 避免反复尝试

    def reset(self):
        """重置引擎状态"""
        self._validator.reset()

    def __enter__(self) -> "RecognitionEngine":
        return self

    def __exit__(self, *args) -> None:
        self._detector = None
        self._ocr = None
        self._matcher = None
        self._validator.reset()
```

- [ ] **Step 4: 更新 recognition/__init__.py**

`src/majsoul_recognizer/recognition/__init__.py`:

```python
"""识别引擎模块"""

from majsoul_recognizer.recognition.config import RecognitionConfig
from majsoul_recognizer.recognition.engine import RecognitionEngine

__all__ = ["RecognitionEngine", "RecognitionConfig"]
```

- [ ] **Step 5: 运行全部识别引擎测试**

```bash
pytest tests/recognition/ -v
```

Expected: 所有测试 PASS

- [ ] **Step 6: 运行全部测试确认无回归**

```bash
pytest -v
```

Expected: 所有测试 PASS

- [ ] **Step 7: 提交**

```bash
git add src/majsoul_recognizer/recognition/engine.py \
      src/majsoul_recognizer/recognition/__init__.py \
      tests/recognition/test_engine.py
git commit -m "feat: add RecognitionEngine facade with warmup, context manager, and integration"
```

---

## 验证清单

完成所有 Task (1-7) 后运行以下验证：

- [ ] **全部测试通过**

```bash
pytest -v --tb=short
```

- [ ] **代码风格检查**

```bash
ruff check src/ tests/
```

- [ ] **包可正常导入**

```bash
python -c "from majsoul_recognizer.recognition import RecognitionEngine, RecognitionConfig; print('Recognition module OK')"
```

- [ ] **RecognitionEngine 端到端可运行**

```bash
python -c "
from majsoul_recognizer.recognition import RecognitionEngine, RecognitionConfig
import numpy as np
config = RecognitionConfig()
engine = RecognitionEngine(config)
state = engine.recognize({})
print(f'Empty zones: warnings={state.warnings}')
print('Engine test OK')
"
```

---

## 交付物总结

完成 Plan 2 后，识别引擎将具备:

| 能力 | 交付物 | 验证方式 |
|------|--------|---------|
| 配置管理 | `RecognitionConfig` | 单元测试 |
| 牌面检测 | `TileDetector` + 假 ONNX 模型 | 假模型端到端测试 |
| 文字识别 | `TextRecognizer` + 后处理函数 | 后处理单元测试 + OCR 集成测试 |
| 动作匹配 | `PatternMatcher` + 假模板 | 假模板匹配测试 |
| 状态组装 | `GameStateBuilder` | 构造数据单元测试 |
| 规则校验 | `Validator` + 帧间融合 | 校验规则 + 融合测试 |
| 统一门面 | `RecognitionEngine` | 集成测试 |

---

## 后续计划

**Plan 3: 集成验证** — 将 CapturePipeline 与 RecognitionEngine 集成为完整流水线。

**Plan 4: 训练管线** — 合成数据生成 + YOLOv8 训练 + 模型导出。
