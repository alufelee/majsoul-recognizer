# 雀魂麻将识别助手 — 基础架构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立项目基础架构，实现截图捕获、区域分割、核心类型定义，产出可运行的截图+区域分割流水线。

**Architecture:** 采用模块化管道架构：窗口发现 → 截图 → 分辨率归一化 → 帧状态检测 → 区域分割。每个模块通过明确定义的数据类型（numpy 数组、dataclass）交互，独立可测。优先实现 macOS 平台支持。

**Tech Stack:** Python 3.10+, OpenCV, NumPy, mss, PyYAML, Pydantic v2, pytest, pyobjc (macOS)

---

## 项目范围拆分

整个项目拆分为 4 个独立计划：

| 计划 | 范围 | 前置依赖 |
|------|------|---------|
| **Plan 1 (本计划): 基础架构** | 项目初始化、核心类型、截图捕获、区域分割 | 无 |
| **Plan 2: 识别引擎** | YOLOv8 牌面检测、PaddleOCR、模板匹配 | Plan 1 |
| **Plan 3: 集成验证** | 规则校验、帧间融合、状态管理、主流水线 | Plan 1 + Plan 2 |
| **Plan 4: 训练管线** | 数据合成、模型训练脚本、部署导出 | Plan 1 |

---

## 文件结构

本计划涉及的文件：

```
majong/
├── pyproject.toml                           # 项目配置
├── .gitignore                               # Git 忽略规则
├── config/
│   └── zones.yaml                           # 区域坐标配置
├── src/
│   └── majsoul_recognizer/
│       ├── __init__.py                      # 包入口
│       ├── tile.py                          # 牌面枚举与编码
│       ├── types.py                         # 核心数据类型
│       ├── capture/
│       │   ├── __init__.py                  # 模块入口
│       │   ├── finder.py                    # 窗口发现
│       │   ├── screenshot.py                # 屏幕截图
│       │   └── frame.py                     # 帧状态检测
│       ├── pipeline.py                      # 截图处理流水线
│       └── zones/
│           ├── __init__.py                  # 模块入口
│           ├── config.py                    # 区域配置加载
│           └── splitter.py                  # 区域分割
├── tests/
│   ├── __init__.py
│   ├── conftest.py                          # 共享 fixtures
│   ├── test_tile.py                         # 牌面类型测试
│   ├── test_types.py                        # 数据类型测试
│   ├── test_finder.py                       # 窗口发现测试
│   ├── test_screenshot.py                   # 截图测试
│   ├── test_frame.py                        # 帧检测测试
│   ├── test_zones.py                        # 区域分割测试
│   └── test_pipeline.py                     # 流水线集成测试
└── docs/
    └── specs/                               # (已有设计文档)
```

---

## Task 1: 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/majsoul_recognizer/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 初始化 Git 仓库**

```bash
cd /Users/alufeli/idea/majong
git init
```

- [ ] **Step 2: 创建 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

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
]

[project.optional-dependencies]
macos = [
    "pyobjc-framework-Quartz>=10.0",
    "pyobjc-framework-ApplicationServices>=10.0",
]
windows = [
    "pywin32>=306",
]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.4",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"
```

- [ ] **Step 3: 创建 .gitignore**

```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/
.env
*.onnx
*.pt
models/v*/
data/feedback/
.pytest_cache/
.coverage
htmlcov/
.ruff_cache/
.DS_Store
```

- [ ] **Step 4: 创建包入口文件**

`src/majsoul_recognizer/__init__.py`:
```python
"""雀魂麻将画面识别助手"""

__version__ = "0.1.0"
```

`tests/__init__.py`: 空文件

`tests/conftest.py`:
```python
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
    # 模拟雀魂桌面背景色（深绿色）
    img[:] = (30, 50, 40)
    return img


@pytest.fixture
def sample_screenshot_small():
    """创建一个模拟的 1280x720 游戏截图"""
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    img[:] = (30, 50, 40)
    return img
```

- [ ] **Step 5: 创建目录结构**

```bash
mkdir -p src/majsoul_recognizer/capture
mkdir -p src/majsoul_recognizer/zones
mkdir -p tests/fixtures
mkdir -p config
mkdir -p models
mkdir -p data
```

创建子包占位 `__init__.py`（后续 Task 会替换为实际内容）：

```bash
touch src/majsoul_recognizer/capture/__init__.py
touch src/majsoul_recognizer/zones/__init__.py
```

- [ ] **Step 6: 安装依赖并验证**

```bash
pip install -e ".[dev,macos]"
python -c "import majsoul_recognizer; print(majsoul_recognizer.__version__)"
```
Expected: `0.1.0`

- [ ] **Step 7: 运行 pytest 确认环境正常**

```bash
pytest --co -q
```
Expected: `no tests collected` (正常，因为还没写测试)

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "chore: initialize project structure with pyproject.toml"
```

---

## Task 2: 牌面类型 — Tile 枚举与编码

**Files:**
- Create: `src/majsoul_recognizer/tile.py`
- Create: `tests/test_tile.py`

- [ ] **Step 1: 编写牌面类型测试**

`tests/test_tile.py`:
```python
"""Tile 枚举与编码测试"""

import pytest

from majsoul_recognizer.tile import Tile, tile_from_str, TileCategory


class TestTileEnum:
    """Tile 枚举基本属性测试"""

    def test_total_tile_count(self):
        """总牌面类型数: 34 标准 (9+9+9+7) + 3 赤宝牌 = 37"""
        assert len(Tile) == 37

    def test_manzu_tiles(self):
        """万子 1-9 编码正确"""
        for i in range(1, 10):
            tile = Tile[f"M{i}"]
            assert tile.value == f"{i}m"

    def test_pinzu_tiles(self):
        """筒子 1-9 编码正确"""
        for i in range(1, 10):
            tile = Tile[f"P{i}"]
            assert tile.value == f"{i}p"

    def test_souzu_tiles(self):
        """索子 1-9 编码正确"""
        for i in range(1, 10):
            tile = Tile[f"S{i}"]
            assert tile.value == f"{i}s"

    def test_wind_tiles(self):
        """风牌编码: 东南西北"""
        assert Tile.TZ1.value == "1z"  # 东
        assert Tile.TZ2.value == "2z"  # 南
        assert Tile.TZ3.value == "3z"  # 西
        assert Tile.TZ4.value == "4z"  # 北

    def test_dragon_tiles(self):
        """三翻身编码: 白发中"""
        assert Tile.TZ5.value == "5z"  # 白
        assert Tile.TZ6.value == "6z"  # 发
        assert Tile.TZ7.value == "7z"  # 中

    def test_red_dora_tiles(self):
        """赤宝牌编码"""
        assert Tile.M5R.value == "5mr"
        assert Tile.P5R.value == "5pr"
        assert Tile.S5R.value == "5sr"


class TestTileCategory:
    """牌面分类属性测试"""

    def test_manzu_category(self):
        assert Tile.M1.category == TileCategory.MANZU
        assert Tile.M9.category == TileCategory.MANZU

    def test_pinzu_category(self):
        assert Tile.P1.category == TileCategory.PINZU
        assert Tile.P9.category == TileCategory.PINZU

    def test_souzu_category(self):
        assert Tile.S1.category == TileCategory.SOUZU
        assert Tile.S9.category == TileCategory.SOUZU

    def test_tsuhai_category(self):
        assert Tile.TZ1.category == TileCategory.TSUHAI
        assert Tile.TZ7.category == TileCategory.TSUHAI

    def test_red_dora_category(self):
        """赤宝牌归类到对应花色"""
        assert Tile.M5R.category == TileCategory.MANZU
        assert Tile.P5R.category == TileCategory.PINZU
        assert Tile.S5R.category == TileCategory.SOUZU

    def test_numbered_tiles_have_number(self):
        """数牌有数字属性"""
        assert Tile.M3.number == 3
        assert Tile.P7.number == 7
        assert Tile.S1.number == 1

    def test_tsuhai_no_number(self):
        """字牌无数字"""
        assert Tile.TZ1.number is None

    def test_red_dora_number(self):
        """赤宝牌数字为 5"""
        assert Tile.M5R.number == 5

    def test_is_red_dora(self):
        assert Tile.M5R.is_red_dora is True
        assert Tile.M5.is_red_dora is False
        assert Tile.TZ1.is_red_dora is False

    def test_display_name(self):
        """显示名称正确"""
        assert Tile.M1.display_name == "一万"
        assert Tile.P5.display_name == "五筒"
        assert Tile.TZ1.display_name == "东"
        assert Tile.TZ5.display_name == "白"
        assert Tile.M5R.display_name == "赤五万"


class TestTileFromString:
    """从字符串解析牌面测试"""

    @pytest.mark.parametrize(
        "code,expected",
        [
            ("1m", Tile.M1),
            ("9m", Tile.M9),
            ("1p", Tile.P1),
            ("9p", Tile.P9),
            ("1s", Tile.S1),
            ("9s", Tile.S9),
            ("1z", Tile.TZ1),
            ("7z", Tile.TZ7),
            ("5mr", Tile.M5R),
            ("5pr", Tile.P5R),
            ("5sr", Tile.S5R),
        ],
    )
    def test_valid_codes(self, code, expected):
        assert tile_from_str(code) == expected

    def test_invalid_code_raises(self):
        with pytest.raises(ValueError, match="Unknown tile code"):
            tile_from_str("0m")

    def test_empty_code_raises(self):
        with pytest.raises(ValueError, match="Unknown tile code"):
            tile_from_str("")
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_tile.py -v
```
Expected: FAILED — `ModuleNotFoundError: No module named 'majsoul_recognizer.tile'`

- [ ] **Step 3: 实现 Tile 枚举**

`src/majsoul_recognizer/tile.py`:
```python
"""牌面类型枚举与编码

定义雀魂麻将中所有牌面类型，支持编码转换和属性查询。
34 种标准牌面 (万子9+筒子9+索子9+字牌7) + 3 种赤宝牌 = 37 种类型。

编码规则:
  万子: 1m-9m  筒子: 1p-9p  索子: 1s-9s
  字牌: 1z-7z (东南西北白发中)
  赤宝牌: 5mr, 5pr, 5sr (红五)
"""

from enum import Enum


class TileCategory(Enum):
    """牌面花色分类"""
    MANZU = "manzu"    # 万子
    PINZU = "pinzu"    # 筒子
    SOUZU = "souzu"    # 索子
    TSUHAI = "tsuhai"  # 字牌


# 字牌显示名映射
_TSUHAI_NAMES = {
    "1z": "东", "2z": "南", "3z": "西", "4z": "北",
    "5z": "白", "6z": "发", "7z": "中",
}

# 中文数字映射
_CN_NUMBERS = {
    1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
    6: "六", 7: "七", 8: "八", 9: "九",
}

# 花色后缀
_SUIT_SUFFIX = {"m": "万", "p": "筒", "s": "索"}


class Tile(str, Enum):
    """雀魂麻将牌面类型

    使用字符串枚举，值即为编码（如 "1m", "5pr"）。
    """

    # 万子 1-9
    M1 = "1m"
    M2 = "2m"
    M3 = "3m"
    M4 = "4m"
    M5 = "5m"
    M6 = "6m"
    M7 = "7m"
    M8 = "8m"
    M9 = "9m"

    # 筒子 1-9
    P1 = "1p"
    P2 = "2p"
    P3 = "3p"
    P4 = "4p"
    P5 = "5p"
    P6 = "6p"
    P7 = "7p"
    P8 = "8p"
    P9 = "9p"

    # 索子 1-9
    S1 = "1s"
    S2 = "2s"
    S3 = "3s"
    S4 = "4s"
    S5 = "5s"
    S6 = "6s"
    S7 = "7s"
    S8 = "8s"
    S9 = "9s"

    # 字牌 (风牌 + 三翻身)
    TZ1 = "1z"  # 东
    TZ2 = "2z"  # 南
    TZ3 = "3z"  # 西
    TZ4 = "4z"  # 北
    TZ5 = "5z"  # 白
    TZ6 = "6z"  # 发
    TZ7 = "7z"  # 中

    # 赤宝牌 (红五)
    M5R = "5mr"
    P5R = "5pr"
    S5R = "5sr"

    @property
    def category(self) -> TileCategory:
        """牌面花色分类"""
        base = self.value.rstrip("r")
        if base.endswith("m"):
            return TileCategory.MANZU
        if base.endswith("p"):
            return TileCategory.PINZU
        if base.endswith("s"):
            return TileCategory.SOUZU
        return TileCategory.TSUHAI

    @property
    def number(self) -> int | None:
        """数牌的数字 (1-9)，字牌返回 None"""
        code = self.value.rstrip("r")
        if code.endswith("z"):
            return None
        return int(code[0])

    @property
    def is_red_dora(self) -> bool:
        """是否为赤宝牌"""
        return self.value.endswith("r")

    @property
    def display_name(self) -> str:
        """中文显示名称"""
        code = self.value
        if code in _TSUHAI_NAMES:
            return _TSUHAI_NAMES[code]
        # 赤宝牌
        if code.endswith("r"):
            num_code = code[0]
            suit = code[-2]
            return f"赤{_CN_NUMBERS[int(num_code)]}{_SUIT_SUFFIX[suit]}"
        # 数牌
        return f"{_CN_NUMBERS[int(code[0])]}{_SUIT_SUFFIX[code[-1]]}"


# 构建快速查找表
_TILE_LOOKUP: dict[str, Tile] = {t.value: t for t in Tile}


def tile_from_str(code: str) -> Tile:
    """从编码字符串解析牌面类型

    Args:
        code: 牌面编码，如 "1m", "5pr", "7z"

    Returns:
        对应的 Tile 枚举成员

    Raises:
        ValueError: 编码无法识别
    """
    if code in _TILE_LOOKUP:
        return _TILE_LOOKUP[code]
    raise ValueError(f"Unknown tile code: '{code}'")
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_tile.py -v
```
Expected: 所有测试 PASS

- [ ] **Step 5: 提交**

```bash
git add src/majsoul_recognizer/tile.py tests/test_tile.py
git commit -m "feat: add Tile enum with encoding and category support"
```

---

## Task 3: 核心数据类型

**Files:**
- Create: `src/majsoul_recognizer/types.py`
- Create: `tests/test_types.py`

- [ ] **Step 1: 编写核心类型测试**

`tests/test_types.py`:
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
    PlayerScore,
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


class TestGameState:
    """游戏状态测试"""

    def test_create_empty_state(self):
        state = GameState()
        assert state.hand == []
        assert state.scores == {}
        assert state.round_info is None

    def test_state_with_data(self):
        state = GameState(
            hand=["1m", "2m", "3m"],
            drawn_tile="东",
            dora_indicators=["5m"],
        )
        assert len(state.hand) == 3
        assert state.drawn_tile == "东"


class TestFrameResult:
    """帧结果测试"""

    def test_create_frame_result(self):
        result = FrameResult(
            frame_id=1,
            timestamp="2026-05-06T10:00:00",
            zones={ZoneName.HAND: np.zeros((100, 200, 3), dtype=np.uint8)},
        )
        assert result.frame_id == 1
        assert ZoneName.HAND in result.zones
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_types.py -v
```
Expected: FAILED — `ImportError`

- [ ] **Step 3: 实现核心数据类型**

`src/majsoul_recognizer/types.py`:
```python
"""核心数据类型定义

定义识别管线中所有数据结构: 边界框、区域定义、检测结果、游戏状态等。
使用 Pydantic v2 进行数据验证。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, Field, field_validator


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


class PlayerScore(BaseModel):
    """单名玩家分数信息"""
    score: int = Field(ge=0)
    rank: int | None = Field(default=None, ge=1, le=4)


class GameState(BaseModel):
    """游戏全局状态 (跨帧持久化)"""
    round_info: RoundInfo | None = None
    dora_indicators: list[str] = Field(default_factory=list)
    scores: dict[str, int | PlayerScore] = Field(default_factory=dict)
    hand: list[str] = Field(default_factory=list)
    drawn_tile: str | None = None
    calls: dict[str, list[Any]] = Field(default_factory=dict)
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

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_types.py -v
```
Expected: 所有测试 PASS

- [ ] **Step 5: 提交**

```bash
git add src/majsoul_recognizer/types.py tests/test_types.py
git commit -m "feat: add core data types (BBox, Zone, Detection, GameState)"
```

---

## Task 4: 区域配置

**Files:**
- Create: `config/zones.yaml`
- Create: `src/majsoul_recognizer/zones/__init__.py`
- Create: `src/majsoul_recognizer/zones/config.py`
- Create: `tests/test_zones.py` (配置加载部分)

- [ ] **Step 1: 创建区域坐标配置文件**

`config/zones.yaml`:
```yaml
# 雀魂麻将区域坐标定义
# 坐标为比例值 (0.0-1.0)，基于 1920x1080 基准分辨率
# 注意: 这些是初始估计值，需要从实际截图中校准

# 参考布局:
# +--[Dora]---[Round Info]---[Remaining]--+
# |  Left     Opponent       Right         |
# |  Player   Discards      Player        |
# |  Discards ┌──────────┐  Discards      |
# |  + Calls  │  Central  │  + Calls      |
# |           │  Table    │               |
# |           └──────────┘               |
# |        Self Discards                   |
# |  [Calls] [==== Hand ====] [Actions]    |
# |              [Timer]                   |
# +----------------------------------------+

zones:
  hand:
    x: 0.25
    y: 0.82
    width: 0.50
    height: 0.12

  dora:
    x: 0.35
    y: 0.02
    width: 0.15
    height: 0.06

  round_info:
    x: 0.42
    y: 0.02
    width: 0.16
    height: 0.06

  score_self:
    x: 0.35
    y: 0.75
    width: 0.12
    height: 0.05

  score_right:
    x: 0.85
    y: 0.45
    width: 0.10
    height: 0.05

  score_opposite:
    x: 0.42
    y: 0.10
    width: 0.12
    height: 0.05

  score_left:
    x: 0.05
    y: 0.45
    width: 0.10
    height: 0.05

  discards_self:
    x: 0.20
    y: 0.68
    width: 0.50
    height: 0.10

  discards_right:
    x: 0.75
    y: 0.25
    width: 0.15
    height: 0.35

  discards_opposite:
    x: 0.25
    y: 0.18
    width: 0.50
    height: 0.10

  discards_left:
    x: 0.10
    y: 0.25
    width: 0.15
    height: 0.35

  calls_self:
    x: 0.05
    y: 0.82
    width: 0.20
    height: 0.10

  actions:
    x: 0.70
    y: 0.82
    width: 0.25
    height: 0.10

  timer:
    x: 0.45
    y: 0.92
    width: 0.10
    height: 0.06
```

- [ ] **Step 2: 编写区域配置测试**

`tests/test_zones.py`:
```python
"""区域配置与分割测试"""

from pathlib import Path

import numpy as np
import pytest

from majsoul_recognizer.types import ZoneName, BBox
from majsoul_recognizer.zones.config import ZoneConfig, load_zone_config
from majsoul_recognizer.zones.splitter import ZoneSplitter


CONFIG_DIR = Path(__file__).parent.parent / "config"


class TestZoneConfig:
    """区域配置加载测试"""

    def test_load_config(self):
        config = load_zone_config(CONFIG_DIR / "zones.yaml")
        assert isinstance(config, ZoneConfig)
        assert len(config.zones) == 14

    def test_get_zone(self):
        config = load_zone_config(CONFIG_DIR / "zones.yaml")
        hand = config.get_zone(ZoneName.HAND)
        assert hand is not None
        assert hand.name == ZoneName.HAND
        assert hand.x == 0.25
        assert hand.y == 0.82

    def test_get_all_zone_names(self):
        config = load_zone_config(CONFIG_DIR / "zones.yaml")
        names = config.zone_names
        assert ZoneName.HAND in names
        assert ZoneName.DORA in names
        assert len(names) == 14

    def test_missing_config_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_zone_config(CONFIG_DIR / "nonexistent.yaml")

    def test_zone_to_bbox_on_1080p(self):
        config = load_zone_config(CONFIG_DIR / "zones.yaml")
        hand = config.get_zone(ZoneName.HAND)
        bbox = hand.to_bbox(1920, 1080)
        assert bbox.x == 480
        assert bbox.y == 885
        assert bbox.width == 960
        assert bbox.height == 129


class TestZoneSplitter:
    """区域分割器测试"""

    @pytest.fixture
    def splitter(self):
        config = load_zone_config(CONFIG_DIR / "zones.yaml")
        return ZoneSplitter(config)

    def test_split_returns_all_zones(self, splitter, sample_screenshot):
        """分割 1920x1080 图像返回所有区域"""
        regions = splitter.split(sample_screenshot)
        assert len(regions) == 14
        assert ZoneName.HAND in regions

    def test_split_hand_region_shape(self, splitter, sample_screenshot):
        """手牌区域尺寸正确"""
        regions = splitter.split(sample_screenshot)
        hand = regions[ZoneName.HAND]
        # 1920x1080, hand: x=0.25, y=0.82, w=0.50, h=0.12
        assert hand.shape == (129, 960, 3)

    def test_split_normalizes_resolution(self, splitter, sample_screenshot_small):
        """非基准分辨率图像先归一化再分割"""
        regions = splitter.split(sample_screenshot_small)
        # 所有区域都应该存在
        assert len(regions) == 14

    def test_split_preserves_color_channels(self, splitter, sample_screenshot):
        """分割结果保留 3 个颜色通道"""
        regions = splitter.split(sample_screenshot)
        for name, region in regions.items():
            assert region.shape[2] == 3, f"{name} should have 3 color channels"

    def test_get_hand_region_directly(self, splitter, sample_screenshot):
        """直接获取指定区域"""
        hand = splitter.get_zone(sample_screenshot, ZoneName.HAND)
        assert hand is not None
        assert hand.shape[2] == 3
```

- [ ] **Step 3: 运行测试确认失败**

```bash
pytest tests/test_zones.py -v
```
Expected: FAILED — `ImportError`

- [ ] **Step 4: 实现区域配置加载**

`src/majsoul_recognizer/zones/__init__.py`:
```python
"""区域分割模块"""

from majsoul_recognizer.zones.config import ZoneConfig, load_zone_config
from majsoul_recognizer.zones.splitter import ZoneSplitter

__all__ = ["ZoneConfig", "load_zone_config", "ZoneSplitter"]
```

`src/majsoul_recognizer/zones/config.py`:
```python
"""区域配置加载

从 YAML 文件加载区域坐标定义。坐标为 0.0-1.0 的比例值。
"""

from pathlib import Path

import yaml
from pydantic import BaseModel

from majsoul_recognizer.types import ZoneDefinition, ZoneName


class ZoneConfig(BaseModel):
    """区域配置集合"""
    zones: dict[ZoneName, ZoneDefinition]

    def get_zone(self, name: ZoneName) -> ZoneDefinition | None:
        """获取指定区域定义"""
        return self.zones.get(name)

    @property
    def zone_names(self) -> list[ZoneName]:
        """所有已定义的区域名称"""
        return list(self.zones.keys())


def load_zone_config(path: Path | str) -> ZoneConfig:
    """从 YAML 文件加载区域配置

    Args:
        path: zones.yaml 文件路径

    Returns:
        ZoneConfig 实例

    Raises:
        FileNotFoundError: 配置文件不存在
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Zone config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    zones = {}
    for name_str, coords in raw.get("zones", {}).items():
        zone_name = ZoneName(name_str)
        zones[zone_name] = ZoneDefinition(
            name=zone_name,
            x=coords["x"],
            y=coords["y"],
            width=coords["width"],
            height=coords["height"],
        )

    return ZoneConfig(zones=zones)
```

- [ ] **Step 5: 实现区域分割器**

`src/majsoul_recognizer/zones/splitter.py`:
```python
"""区域分割器

将完整游戏截图分割为各个识别区域。
支持分辨率归一化（统一缩放到 1920x1080）。
"""

import cv2
import numpy as np

from majsoul_recognizer.types import ZoneName
from majsoul_recognizer.zones.config import ZoneConfig

# 基准分辨率
BASE_WIDTH = 1920
BASE_HEIGHT = 1080


class ZoneSplitter:
    """区域分割器

    将游戏截图按区域配置分割为多个子图像。
    非基准分辨率的图像会先被缩放到 1920x1080。
    """

    def __init__(self, config: ZoneConfig):
        self._config = config

    def split(self, image: np.ndarray) -> dict[ZoneName, np.ndarray]:
        """将图像分割为所有区域

        Args:
            image: BGR 格式的游戏截图

        Returns:
            区域名称到裁剪图像的映射
        """
        normalized = self._normalize(image)
        return {
            name: self._crop_zone(normalized, name)
            for name in self._config.zone_names
        }

    def get_zone(self, image: np.ndarray, zone_name: ZoneName) -> np.ndarray | None:
        """获取单个区域的裁剪图像"""
        zone_def = self._config.get_zone(zone_name)
        if zone_def is None:
            return None
        normalized = self._normalize(image)
        return self._crop_zone(normalized, zone_name)

    def _normalize(self, image: np.ndarray) -> np.ndarray:
        """将图像缩放到基准分辨率 1920x1080"""
        h, w = image.shape[:2]
        if w == BASE_WIDTH and h == BASE_HEIGHT:
            return image
        return cv2.resize(image, (BASE_WIDTH, BASE_HEIGHT), interpolation=cv2.INTER_LINEAR)

    def _crop_zone(self, image: np.ndarray, zone_name: ZoneName) -> np.ndarray:
        """从归一化图像中裁剪指定区域"""
        zone_def = self._config.get_zone(zone_name)
        if zone_def is None:
            return np.array([])
        bbox = zone_def.to_bbox(BASE_WIDTH, BASE_HEIGHT)
        return bbox.crop(image)
```

- [ ] **Step 6: 运行测试确认通过**

```bash
pytest tests/test_zones.py -v
```
Expected: 所有测试 PASS

- [ ] **Step 7: 提交**

```bash
git add config/zones.yaml src/majsoul_recognizer/zones/ tests/test_zones.py
git commit -m "feat: add zone config and splitter with resolution normalization"
```

---

## Task 5: 窗口发现

**Files:**
- Create: `src/majsoul_recognizer/capture/__init__.py`
- Create: `src/majsoul_recognizer/capture/finder.py`
- Create: `tests/test_finder.py`

- [ ] **Step 1: 编写窗口发现测试**

`tests/test_finder.py`:
```python
"""窗口发现测试"""

import pytest

from majsoul_recognizer.capture.finder import (
    WindowInfo,
    WindowFinder,
    create_finder,
)


class TestWindowInfo:
    """窗口信息数据结构测试"""

    def test_create_window_info(self):
        info = WindowInfo(title="Mahjong Soul", x=0, y=0, width=1920, height=1080)
        assert info.title == "Mahjong Soul"
        assert info.width == 1920

    def test_window_info_is_valid(self):
        valid = WindowInfo(title="Mahjong Soul", x=0, y=0, width=1920, height=1080)
        assert valid.is_valid is True

        zero_size = WindowInfo(title="test", x=0, y=0, width=0, height=0)
        assert zero_size.is_valid is False


class TestWindowFinder:
    """窗口发现接口测试 (mock 测试)"""

    def test_create_finder_returns_instance(self):
        finder = create_finder()
        assert isinstance(finder, WindowFinder)

    def test_finder_has_find_method(self):
        finder = create_finder()
        assert hasattr(finder, "find_window")

    def test_finder_target_titles(self):
        """确认搜索的窗口标题关键词"""
        finder = create_finder()
        # 搜索标题应包含这些关键词之一
        assert len(finder.target_keywords) > 0
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_finder.py -v
```
Expected: FAILED — `ImportError`

- [ ] **Step 3: 实现窗口发现模块**

`src/majsoul_recognizer/capture/__init__.py`:
```python
"""截图捕获模块"""

from majsoul_recognizer.capture.finder import WindowFinder, WindowInfo, create_finder

# 后续 Task 会追加 screenshot 和 frame 的导入
__all__ = ["WindowFinder", "WindowInfo", "create_finder"]
```

> ⚠️ **连续性说明**: Task 6/7 执行后需追加导入行，最终版本见 Task 7。
```python
"""窗口发现

查找雀魂游戏窗口并获取窗口信息。
支持 macOS 和 Windows 平台。
"""

import platform
import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 搜索的窗口标题关键词
TARGET_KEYWORDS = ("Mahjong Soul", "雀魂", "majsoul")


class WindowInfo(BaseModel):
    """窗口基本信息"""
    model_config = {"frozen": True}

    title: str
    x: int
    y: int
    width: int
    height: int
    window_id: int | str | None = None

    @property
    def is_valid(self) -> bool:
        """窗口尺寸是否有效"""
        return self.width > 0 and self.height > 0


class WindowFinder(ABC):
    """窗口发现抽象基类"""

    def __init__(self, target_keywords: tuple[str, ...] = TARGET_KEYWORDS):
        self.target_keywords = target_keywords

    @property
    def target_keywords(self) -> tuple[str, ...]:
        return self._target_keywords

    @target_keywords.setter
    def target_keywords(self, value: tuple[str, ...]):
        self._target_keywords = value

    @abstractmethod
    def find_window(self) -> WindowInfo | None:
        """查找目标窗口

        Returns:
            窗口信息，未找到返回 None
        """
        ...

    @abstractmethod
    def list_windows(self) -> list[WindowInfo]:
        """列出所有可见窗口"""
        ...

    def _match_title(self, title: str) -> bool:
        """检查窗口标题是否匹配目标关键词"""
        title_lower = title.lower()
        return any(kw.lower() in title_lower for kw in self.target_keywords)


class MacOSWindowFinder(WindowFinder):
    """macOS 窗口发现实现"""

    def find_window(self) -> WindowInfo | None:
        try:
            import Quartz  # noqa: F401 — 仅检查可用性
        except ImportError:
            logger.warning("pyobjc not available, using fallback")
            return self._fallback_find()

        windows = self.list_windows()
        for win in windows:
            if self._match_title(win.title):
                return win
        return None

    def list_windows(self) -> list[WindowInfo]:
        try:
            from Quartz import (
                CGWindowListCopyWindowInfo,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
            )
        except ImportError:
            return []

        window_list = CGWindowListCopyWindowInfo(
            kCGWindowListOptionOnScreenOnly, kCGNullWindowID
        )
        result = []
        for win in window_list:
            bounds = win.get("kCGWindowBounds", {})
            if not bounds:
                continue
            w = int(bounds.get("Width", 0))
            h = int(bounds.get("Height", 0))
            if w <= 0 or h <= 0:
                continue
            result.append(WindowInfo(
                title=win.get("kCGWindowName", ""),
                x=int(bounds.get("X", 0)),
                y=int(bounds.get("Y", 0)),
                width=w,
                height=h,
                window_id=win.get("kCGWindowNumber"),
            ))
        return result

    def _fallback_find(self) -> WindowInfo | None:
        """无 pyobjc 时的回退方案"""
        logger.warning("macOS window discovery requires pyobjc. Install with: pip install pyobjc-framework-Quartz")
        return None


class WindowsWindowFinder(WindowFinder):
    """Windows 窗口发现实现"""

    def find_window(self) -> WindowInfo | None:
        try:
            import win32gui
        except ImportError:
            logger.warning("pywin32 not available")
            return None

        result = []
        def enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if title and self._match_title(title):
                rect = win32gui.GetWindowRect(hwnd)
                result.append(WindowInfo(
                    title=title,
                    x=rect[0], y=rect[1],
                    width=rect[2] - rect[0],
                    height=rect[3] - rect[1],
                    window_id=hwnd,
                ))

        win32gui.EnumWindows(enum_callback, None)
        return result[0] if result else None

    def list_windows(self) -> list[WindowInfo]:
        try:
            import win32gui
        except ImportError:
            return []

        result = []
        def enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            result.append(WindowInfo(
                title=title,
                x=rect[0], y=rect[1],
                width=rect[2] - rect[0],
                height=rect[3] - rect[1],
                window_id=hwnd,
            ))

        win32gui.EnumWindows(enum_callback, None)
        return result


def create_finder() -> WindowFinder:
    """根据当前平台创建对应的 WindowFinder 实例"""
    system = platform.system()
    if system == "Darwin":
        return MacOSWindowFinder()
    elif system == "Windows":
        return WindowsWindowFinder()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_finder.py -v
```
Expected: 所有测试 PASS

- [ ] **Step 5: 提交**

```bash
git add src/majsoul_recognizer/capture/ tests/test_finder.py
git commit -m "feat: add window finder with macOS and Windows support"
```

---

## Task 6: 屏幕截图

**Files:**
- Create: `src/majsoul_recognizer/capture/screenshot.py`
- Create: `tests/test_screenshot.py`

- [ ] **Step 1: 编写截图测试**

`tests/test_screenshot.py`:
```python
"""屏幕截图测试"""

import numpy as np
import pytest

from majsoul_recognizer.capture.screenshot import ScreenCapture, create_capture
from majsoul_recognizer.capture.finder import WindowInfo


class TestScreenCapture:
    """屏幕截图测试"""

    @pytest.fixture
    def capture(self):
        return create_capture()

    def test_create_capture_returns_instance(self, capture):
        assert isinstance(capture, ScreenCapture)

    def test_capture_from_window_info(self, capture):
        """使用已知窗口信息截图（可能失败，因为窗口可能不存在）"""
        # 使用一个很可能不存在的窗口来测试错误处理
        fake_info = WindowInfo(title="test", x=0, y=0, width=100, height=100)
        # 不应该崩溃
        result = capture.capture_window(fake_info)
        # 结果可能是 None 或有效图像
        if result is not None:
            assert isinstance(result, np.ndarray)
            assert result.shape[2] == 3  # BGR

    def test_capture_has_capture_method(self, capture):
        assert hasattr(capture, "capture_window")


class TestCreateCapture:
    """截图工厂测试"""

    def test_factory_creates_capture(self):
        capture = create_capture()
        assert capture is not None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_screenshot.py -v
```
Expected: FAILED — `ImportError`

- [ ] **Step 3: 实现屏幕截图模块**

`src/majsoul_recognizer/capture/screenshot.py`:
```python
"""屏幕截图

截取指定窗口的画面内容。
使用 mss 库作为跨平台截图方案。
"""

import logging
import platform

import cv2
import numpy as np
import mss

from majsoul_recognizer.capture.finder import WindowInfo

logger = logging.getLogger(__name__)


class ScreenCapture:
    """屏幕截图器

    使用 mss 库截取指定区域的屏幕内容。
    返回 BGR 格式的 numpy 数组（与 OpenCV 兼容）。
    """

    def __init__(self):
        self._sct = mss.mss()

    def capture_window(self, window_info: WindowInfo) -> np.ndarray | None:
        """截取指定窗口区域

        Args:
            window_info: 窗口位置和尺寸信息

        Returns:
            BGR 格式图像 (numpy 数组)，失败返回 None
        """
        try:
            monitor = {
                "left": window_info.x,
                "top": window_info.y,
                "width": window_info.width,
                "height": window_info.height,
            }
            screenshot = self._sct.grab(monitor)
            # mss 返回 BGRA，转为 BGR
            img = np.array(screenshot, dtype=np.uint8)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
            return None

    def capture_monitor(self, monitor_index: int = 0) -> np.ndarray | None:
        """截取整个显示器

        Args:
            monitor_index: 显示器索引 (0 = 主显示器)

        Returns:
            BGR 格式图像，失败返回 None
        """
        try:
            monitor = self._sct.monitors[monitor_index + 1]  # index 0 is all monitors combined
            screenshot = self._sct.grab(monitor)
            img = np.array(screenshot, dtype=np.uint8)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            logger.warning(f"Monitor capture failed: {e}")
            return None

    def close(self):
        """释放截图资源"""
        self._sct.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def create_capture() -> ScreenCapture:
    """创建屏幕截图器实例"""
    return ScreenCapture()
```

- [ ] **Step 4: 更新 capture 模块入口**

编辑 `src/majsoul_recognizer/capture/__init__.py`，添加 screenshot 的导出：

```python
"""截图捕获模块"""

from majsoul_recognizer.capture.finder import WindowFinder, WindowInfo, create_finder
from majsoul_recognizer.capture.screenshot import ScreenCapture, create_capture

__all__ = [
    "WindowFinder", "WindowInfo", "create_finder",
    "ScreenCapture", "create_capture",
]
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_screenshot.py -v
```
Expected: 所有测试 PASS

- [ ] **Step 6: 提交**

```bash
git add src/majsoul_recognizer/capture/screenshot.py src/majsoul_recognizer/capture/__init__.py tests/test_screenshot.py
git commit -m "feat: add screen capture using mss library"
```

---

## Task 7: 帧状态检测

**Files:**
- Create: `src/majsoul_recognizer/capture/frame.py`
- Create: `tests/test_frame.py`

- [ ] **Step 1: 编写帧状态检测测试**

`tests/test_frame.py`:
```python
"""帧状态检测测试"""

import numpy as np
import pytest

from majsoul_recognizer.capture.frame import FrameChecker


class TestFrameChecker:
    """帧静止检测测试"""

    @pytest.fixture
    def checker(self):
        return FrameChecker(threshold=0.02)

    def test_identical_frames_are_static(self, checker):
        """完全相同的帧判定为静止"""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        assert checker.is_static(frame) is True

    def test_slightly_different_frames_are_static(self, checker):
        """微小变化 (< 2%) 判定为静止"""
        frame1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame2 = frame1.copy()
        # 修改少于 2% 的像素
        frame2[0:50, 0:50] = 10  # 约 0.12% 的像素
        assert checker.is_static(frame2) is True

    def test_very_different_frames_are_animated(self, checker):
        """大幅变化判定为动画"""
        frame1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame2 = np.ones((1080, 1920, 3), dtype=np.uint8) * 128
        assert checker.is_static(frame2) is False

    def test_first_frame_is_always_static(self, checker):
        """第一帧（无历史）判定为静止"""
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        assert checker.is_static(frame) is True

    def test_threshold_customization(self):
        """自定义阈值生效"""
        strict_checker = FrameChecker(threshold=0.001)
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = frame1.copy()
        frame2[0:5, 0:5] = 10  # 0.25% 变化
        # 0.25% > 0.1%，应判定为动画
        strict_checker.is_static(frame1)  # 先存第一帧
        assert strict_checker.is_static(frame2) is False

    def test_reset(self, checker):
        """重置后第一帧为静止"""
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        checker.is_static(frame1)
        checker.reset()
        frame2 = np.ones((100, 100, 3), dtype=np.uint8) * 200
        assert checker.is_static(frame2) is True
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_frame.py -v
```
Expected: FAILED — `ImportError`

- [ ] **Step 3: 实现帧状态检测**

`src/majsoul_recognizer/capture/frame.py`:
```python
"""帧状态检测

通过比较连续帧之间的差异判断画面是否处于静止状态。
用于跳过动画帧，避免在动画期间做误检。
"""

import cv2
import numpy as np


class FrameChecker:
    """帧静止检测器

    比较当前帧与上一帧的像素差异率，判定画面是否静止。
    差异率低于阈值时判定为静止帧，可进行识别。
    """

    def __init__(self, threshold: float = 0.02):
        """
        Args:
            threshold: 像素差异率阈值 (0.0-1.0)，默认 2%。
                       差异率低于此值判定为静止。
        """
        self._threshold = threshold
        self._prev_frame: np.ndarray | None = None

    def is_static(self, frame: np.ndarray) -> bool:
        """判断当前帧是否为静止帧

        Args:
            frame: BGR 格式图像

        Returns:
            True 表示静止帧，False 表示动画帧
        """
        if self._prev_frame is None:
            self._prev_frame = self._preprocess(frame)
            return True

        current = self._preprocess(frame)
        diff_ratio = self._compute_diff_ratio(self._prev_frame, current)
        self._prev_frame = current

        return diff_ratio < self._threshold

    def reset(self):
        """重置历史帧状态"""
        self._prev_frame = None

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """预处理: 缩小 + 灰度化，加速比较"""
        # 缩小到 1/4 尺寸加速比较
        small = cv2.resize(frame, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return gray

    def _compute_diff_ratio(self, prev: np.ndarray, curr: np.ndarray) -> float:
        """计算两帧之间的像素差异率"""
        diff = cv2.absdiff(prev, curr)
        # 像素值差异 > 10 视为变化
        changed_pixels = np.count_nonzero(diff > 10)
        total_pixels = prev.size
        return changed_pixels / total_pixels
```

- [ ] **Step 4: 更新 capture 模块入口**

编辑 `src/majsoul_recognizer/capture/__init__.py`：

```python
"""截图捕获模块"""

from majsoul_recognizer.capture.finder import WindowFinder, WindowInfo, create_finder
from majsoul_recognizer.capture.screenshot import ScreenCapture, create_capture
from majsoul_recognizer.capture.frame import FrameChecker

__all__ = [
    "WindowFinder", "WindowInfo", "create_finder",
    "ScreenCapture", "create_capture",
    "FrameChecker",
]
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_frame.py -v
```
Expected: 所有测试 PASS

- [ ] **Step 6: 提交**

```bash
git add src/majsoul_recognizer/capture/frame.py src/majsoul_recognizer/capture/__init__.py tests/test_frame.py
git commit -m "feat: add frame state detection for animation filtering"
```

---

## Task 8: 集成 — 截图流水线

**Files:**
- Create: `src/majsoul_recognizer/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: 编写集成测试**

`tests/test_pipeline.py`:
```python
"""截图流水线集成测试"""

import numpy as np
import pytest

from majsoul_recognizer.pipeline import CapturePipeline
from majsoul_recognizer.capture.finder import WindowInfo
from majsoul_recognizer.types import ZoneName


class TestCapturePipeline:
    """截图流水线测试"""

    @pytest.fixture
    def pipeline(self):
        return CapturePipeline()

    def test_pipeline_creation(self, pipeline):
        assert pipeline is not None

    def test_process_image_splits_zones(self, pipeline, sample_screenshot):
        """处理图像返回分割后的区域"""
        result = pipeline.process_image(sample_screenshot)
        assert result is not None
        assert result.is_static is True
        assert "hand" in result.zones  # ZoneName 转为字符串键
        assert len(result.zones) == 14

    def test_process_image_with_state_detection(self, pipeline, sample_screenshot):
        """帧状态检测正常工作"""
        # 第一帧应判定为静止
        result1 = pipeline.process_image(sample_screenshot)
        assert result1.is_static is True

        # 相同帧应判定为静止
        result2 = pipeline.process_image(sample_screenshot)
        assert result2.is_static is True

    def test_process_image_animated_frame(self, pipeline, sample_screenshot):
        """动画帧检测"""
        result1 = pipeline.process_image(sample_screenshot)
        # 大幅修改图像
        animated = np.ones_like(sample_screenshot) * 128
        result2 = pipeline.process_image(animated)
        assert result2.is_static is False

    def test_process_image_increments_frame_id(self, pipeline, sample_screenshot):
        """帧 ID 递增"""
        r1 = pipeline.process_image(sample_screenshot)
        r2 = pipeline.process_image(sample_screenshot)
        assert r2.frame_id == r1.frame_id + 1

    def test_process_image_nonstandard_resolution(self, pipeline, sample_screenshot_small):
        """非基准分辨率图像正常处理"""
        result = pipeline.process_image(sample_screenshot_small)
        assert result is not None
        assert "hand" in result.zones
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_pipeline.py -v
```
Expected: FAILED — `ImportError`

- [ ] **Step 3: 实现截图流水线**

`src/majsoul_recognizer/pipeline.py`:
```python
"""截图处理流水线

整合截图捕获、帧状态检测和区域分割，
提供统一的处理入口。
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from majsoul_recognizer.capture.frame import FrameChecker
from majsoul_recognizer.types import FrameResult, ZoneName
from majsoul_recognizer.zones.config import load_zone_config
from majsoul_recognizer.zones.splitter import ZoneSplitter

logger = logging.getLogger(__name__)

# 默认配置路径: pipeline.py 在 src/majsoul_recognizer/，向上 2 层到项目根
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "zones.yaml"


class CapturePipeline:
    """截图处理流水线

    处理流程: 截图 → 分辨率归一化 → 帧状态检测 → 区域分割

    用法:
        pipeline = CapturePipeline()
        result = pipeline.process_image(screenshot)
        if result.is_static:
            hand_region = result.zones[ZoneName.HAND]
    """

    def __init__(
        self,
        config_path: Path | str | None = None,
        frame_threshold: float = 0.02,
    ):
        """
        Args:
            config_path: 区域配置文件路径，默认使用 config/zones.yaml
            frame_threshold: 帧静止检测阈值
        """
        config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_pipeline.py -v
```
Expected: 所有测试 PASS

- [ ] **Step 5: 运行全部测试**

```bash
pytest -v
```
Expected: 所有测试 PASS

- [ ] **Step 6: 提交**

```bash
git add src/majsoul_recognizer/pipeline.py tests/test_pipeline.py
git commit -m "feat: add capture pipeline integrating frame check and zone split"
```

---

## Task 9: 端到端集成入口

**Files:**
- Create: `src/majsoul_recognizer/__main__.py`
- Create: `src/majsoul_recognizer/cli.py`
- Create: `tests/test_cli.py`

**前置依赖:** Task 1-8 全部完成

- [ ] **Step 1: 编写 CLI 测试**

`tests/test_cli.py`:
```python
"""CLI 入口测试"""

import subprocess
import sys

import numpy as np
import pytest
from pathlib import Path

from majsoul_recognizer.cli import capture_and_save, build_capture_chain


class TestBuildCaptureChain:
    """端到端串联测试"""

    def test_chain_returns_callable(self):
        """build_capture_chain 返回可调用对象"""
        chain = build_capture_chain()
        assert callable(chain)

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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_cli.py -v
```
Expected: FAILED — `ImportError`

- [ ] **Step 3: 实现 CLI 模块**

`src/majsoul_recognizer/cli.py`:
```python
"""命令行入口

提供端到端的截图 → 区域分割 → 保存流水线。
支持两种模式:
  1. 实时截取: finder → capture → pipeline → save
  2. 离线处理: 从已有截图文件 → pipeline → save
"""

import argparse
import logging
import sys
from pathlib import Path

import cv2
import numpy as np

from majsoul_recognizer.capture.finder import create_finder
from majsoul_recognizer.capture.screenshot import create_capture
from majsoul_recognizer.pipeline import CapturePipeline
from majsoul_recognizer.types import ZoneName

logger = logging.getLogger(__name__)


def build_capture_chain(config_path: str | Path | None = None) -> CapturePipeline:
    """构建截图处理流水线

    Args:
        config_path: 区域配置文件路径，默认使用内置配置

    Returns:
        配置好的 CapturePipeline 实例
    """
    return CapturePipeline(config_path=config_path)


def capture_and_save(
    image: np.ndarray,
    output_dir: Path,
    pipeline: CapturePipeline | None = None,
) -> Path:
    """将图像分割为区域并保存到磁盘

    Args:
        image: BGR 格式的游戏截图
        output_dir: 输出目录
        pipeline: 流水线实例，None 则自动创建

    Returns:
        输出目录路径
    """
    if pipeline is None:
        pipeline = build_capture_chain()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = pipeline.process_image(image)

    if not result.is_static:
        logger.warning("Frame is not static, zones may be empty")

    for zone_name, zone_img in result.zones.items():
        filename = f"{zone_name}.png"
        filepath = output_dir / filename
        cv2.imwrite(str(filepath), zone_img)
        logger.info(f"Saved {zone_name}: {zone_img.shape}")

    return output_dir


def capture_from_screen(output_dir: Path, config_path: str | None = None) -> bool:
    """从屏幕截取雀魂窗口并分割保存

    Args:
        output_dir: 输出目录
        config_path: 区域配置文件路径

    Returns:
        True 成功，False 失败（窗口未找到等）
    """
    finder = create_finder()
    window = finder.find_window()

    if window is None:
        logger.error("Mahjong Soul window not found. Is the game running?")
        return False

    logger.info(f"Found window: {window.title} ({window.width}x{window.height})")

    with create_capture() as capture:
        image = capture.capture_window(window)

    if image is None:
        logger.error("Failed to capture window screenshot")
        return False

    logger.info(f"Captured screenshot: {image.shape}")
    output = capture_and_save(image, output_dir, build_capture_chain(config_path))
    logger.info(f"Zones saved to: {output}")
    return True


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="majsoul-recognizer",
        description="雀魂麻将画面识别助手 — 基础架构",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # capture 命令: 实时截取游戏画面并分割
    cap_parser = subparsers.add_parser("capture", help="截取雀魂窗口并分割区域")
    cap_parser.add_argument(
        "-o", "--output", default="./output/zones",
        help="输出目录 (默认: ./output/zones)",
    )
    cap_parser.add_argument(
        "--config", default=None,
        help="区域配置文件路径",
    )

    # split 命令: 从已有截图文件分割
    split_parser = subparsers.add_parser("split", help="从截图文件分割区域")
    split_parser.add_argument("image", help="截图文件路径")
    split_parser.add_argument(
        "-o", "--output", default="./output/zones",
        help="输出目录 (默认: ./output/zones)",
    )
    split_parser.add_argument(
        "--config", default=None,
        help="区域配置文件路径",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.command == "capture":
        success = capture_from_screen(Path(args.output), args.config)
        sys.exit(0 if success else 1)

    elif args.command == "split":
        image = cv2.imread(args.image)
        if image is None:
            logger.error(f"Cannot read image: {args.image}")
            sys.exit(1)
        output = capture_and_save(image, Path(args.output), build_capture_chain(args.config))
        logger.info(f"Zones saved to: {output}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 创建 __main__.py 入口**

`src/majsoul_recognizer/__main__.py`:
```python
"""支持 python -m majsoul_recognizer 运行"""

from majsoul_recognizer.cli import main

main()
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_cli.py -v
```
Expected: 所有测试 PASS

- [ ] **Step 6: 测试 CLI 命令**

```bash
# 测试 help
python -m majsoul_recognizer --help

# 用合成图像测试 split 命令
python -c "
import numpy as np, cv2
img = np.zeros((1080, 1920, 3), dtype=np.uint8)
img[:] = (30, 50, 40)
cv2.imwrite('/tmp/test_screenshot.png', img)
"
python -m majsoul_recognizer split /tmp/test_screenshot.png -o /tmp/test_zones

# 验证输出
ls -la /tmp/test_zones/
```
Expected: 14 个 PNG 文件，每个非空

- [ ] **Step 7: 提交**

```bash
git add src/majsoul_recognizer/cli.py src/majsoul_recognizer/__main__.py tests/test_cli.py
git commit -m "feat: add CLI entry point with capture and split commands"
```

---

## Task 10: 真实数据校准与验证

**Files:**
- Create: `src/majsoul_recognizer/calibrate.py`
- Create: `tests/fixtures/majsoul_screenshot.png` (从网络获取)
- Modify: `src/majsoul_recognizer/cli.py` (注册 calibrate 命令)
- Modify: `config/zones.yaml` (校准坐标)

**前置依赖:** Task 9 完成

> **坐标策略**: zones.yaml 使用比例坐标 (0.0-1.0)，ZoneSplitter 统一缩放到 1920x1080 后裁剪。因此无论截图来源分辨率如何，坐标始终有效。校准只需验证比例值是否匹配游戏界面布局。

- [ ] **Step 1: 从 Steam 商店获取真实游戏截图**

雀魂 Steam 商店页提供官方 1920x1080 截图。获取一张包含四人麻将对局的画面：

- Steam 商店页: `https://store.steampowered.com/app/2739990/Mahjong_Soul/`
- SteamDB 截图页: `https://steamdb.info/app/1329410/screenshots/`
- Steam 社区截图: `https://steamcommunity.com/app/2739990/screenshots/`

下载一张包含手牌、牌河、分数等完整对局元素的截图，保存为 `tests/fixtures/majsoul_screenshot.png`。

```bash
# 示例：从 Steam 商店截图 URL 下载（需替换为实际 URL）
# 或手动从上述页面保存截图到 tests/fixtures/majsoul_screenshot.png
```

- [ ] **Step 2: 编写校准工具和测试**

`src/majsoul_recognizer/calibrate.py`:
```python
"""区域坐标校准工具

在游戏截图上绘制区域框，输出标注图供目视校验。
用法: python -m majsoul_recognizer calibrate --screenshot <path>
"""

import argparse
import logging
from pathlib import Path

import cv2
import numpy as np

from majsoul_recognizer.pipeline import _PROJECT_ROOT

logger = logging.getLogger(__name__)

# 区域标注颜色 (BGR)，6 色循环
COLORS = [
    (0, 255, 0),    # 绿
    (255, 0, 0),    # 蓝
    (0, 0, 255),    # 红
    (255, 255, 0),  # 青
    (0, 255, 255),  # 黄
    (255, 0, 255),  # 品红
]


def draw_zones_on_image(image: np.ndarray, config_path: Path) -> np.ndarray:
    """在截图上绘制所有区域框和标签"""
    import yaml

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    overlay = image.copy()
    h, w = image.shape[:2]

    for i, (name, coords) in enumerate(raw.get("zones", {}).items()):
        x = int(coords["x"] * w)
        y = int(coords["y"] * h)
        bw = int(coords["width"] * w)
        bh = int(coords["height"] * h)
        color = COLORS[i % len(COLORS)]

        cv2.rectangle(overlay, (x, y), (x + bw, y + bh), color, 2)
        label = f"{name} ({coords['x']:.2f},{coords['y']:.2f})"
        cv2.putText(overlay, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    return overlay


def calibrate(screenshot_path: str, config_path: str | None = None, output_path: str | None = None):
    """校准区域坐标

    Args:
        screenshot_path: 雀魂游戏截图文件路径
        config_path: 当前区域配置路径
        output_path: 标注图输出路径
    """
    config_path = Path(config_path) if config_path else _PROJECT_ROOT / "config" / "zones.yaml"
    output_path = output_path or str(Path(screenshot_path).with_name("calibration_preview.png"))

    image = cv2.imread(screenshot_path)
    if image is None:
        logger.error(f"Cannot read: {screenshot_path}")
        return

    h, w = image.shape[:2]
    logger.info(f"Screenshot: {w}x{h}")

    annotated = draw_zones_on_image(image, config_path)
    cv2.imwrite(output_path, annotated)
    logger.info(f"Calibration preview saved to: {output_path}")
    return output_path
```

`tests/test_calibrate.py`:
```python
"""校准工具测试"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from majsoul_recognizer.calibrate import calibrate, draw_zones_on_image

FIXTURES = Path(__file__).parent / "fixtures"
CONFIG = Path(__file__).parent.parent / "config" / "zones.yaml"


class TestCalibrate:
    """校准工具测试"""

    def test_draw_zones_on_synthetic_image(self, sample_screenshot):
        """在合成图像上绘制区域框"""
        result = draw_zones_on_image(sample_screenshot, CONFIG)
        assert result.shape == sample_screenshot.shape
        # 标注图应与原图不同（有绘制内容）
        assert not np.array_equal(result, sample_screenshot)

    def test_draw_zones_with_real_screenshot(self):
        """用真实截图校验区域框绘制"""
        screenshot = FIXTURES / "majsoul_screenshot.png"
        if not screenshot.exists():
            pytest.skip("Real screenshot not available yet")

        image = cv2.imread(str(screenshot))
        assert image is not None

        result = draw_zones_on_image(image, CONFIG)
        assert result.shape[:2] == image.shape[:2]

    def test_calibrate_saves_preview(self, sample_screenshot, tmp_path):
        """calibrate 输出预览图文件"""
        screenshot_path = tmp_path / "test.png"
        cv2.imwrite(str(screenshot_path), sample_screenshot)

        output = calibrate(str(screenshot_path), str(CONFIG))
        assert output is not None
        assert Path(output).exists()
        assert Path(output).stat().st_size > 0
```

- [ ] **Step 3: 注册 calibrate 子命令到 cli.py**

在 `cli.py` 的 `main()` 函数中，`split_parser` 之后添加:

```python
    # calibrate 命令: 校准区域坐标
    cal_parser = subparsers.add_parser("calibrate", help="校准区域坐标")
    cal_parser.add_argument("--screenshot", required=True, help="雀魂游戏截图路径")
    cal_parser.add_argument("--config", default=None, help="区域配置文件路径")
    cal_parser.add_argument("--output", default=None, help="标注图输出路径")
```

在 `elif args.command == "split":` 之后添加:

```python
    elif args.command == "calibrate":
        from majsoul_recognizer.calibrate import calibrate
        calibrate(args.screenshot, args.config, args.output)
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/test_calibrate.py -v
```
Expected: `test_draw_zones_with_real_screenshot` 可能 SKIP（截图未下载），其余 PASS

- [ ] **Step 5: 对真实截图执行校准**

```bash
# 如果 tests/fixtures/majsoul_screenshot.png 已存在
python -m majsoul_recognizer calibrate --screenshot tests/fixtures/majsoul_screenshot.png --output tests/fixtures/calibration_preview.png
```

打开 `calibration_preview.png`，检查 14 个区域框是否对准游戏界面中对应位置。如果有偏移，编辑 `config/zones.yaml` 调整比例坐标后重新生成预览。

- [ ] **Step 6: 用校准后的坐标做端到端验证**

```bash
python -m majsoul_recognizer split tests/fixtures/majsoul_screenshot.png -o /tmp/real_zones
```

检查 `/tmp/real_zones/` 下 14 个 PNG 是否正确截取了手牌、牌河、分数等区域。

- [ ] **Step 7: 提交**

```bash
git add src/majsoul_recognizer/calibrate.py tests/test_calibrate.py config/zones.yaml
git commit -m "feat: add calibration tool and validate with real screenshot"
```

如果下载了真实截图，一并提交:
```bash
git add tests/fixtures/majsoul_screenshot.png
git commit -m "chore: add real game screenshot for calibration"
```

---

## 验证清单

完成所有 Task (1-10) 后运行以下验证：

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
python -c "from majsoul_recognizer.tile import Tile; print(f'Tile count: {len(Tile)}, {Tile.M1.display_name} = {Tile.M1.value}')"
```
Expected: `Tile count: 40, 一万 = 1m`

```bash
python -c "from majsoul_recognizer.pipeline import CapturePipeline; print('Pipeline import OK')"
```
Expected: `Pipeline import OK`

- [ ] **CLI 可用**

```bash
python -m majsoul_recognizer --help
```
Expected: 显示帮助信息，包含 `capture`, `split`, `calibrate` 命令

- [ ] **真实截图校准通过**

```bash
python -m majsoul_recognizer split <真实截图路径> -o /tmp/verify_zones
```
Expected: 14 个 PNG 文件，手牌/牌河/分数等区域与游戏界面匹配

---

## 交付物总结

完成 Plan 1 后，项目将具备:

| 能力 | 交付物 | 验证方式 |
|------|--------|---------|
| 牌面类型编码 | `Tile` 枚举 (40种) | 单元测试 |
| 区域配置与分割 | `ZoneSplitter` + `zones.yaml` | 合成图像测试 + 真实截图校准 |
| 窗口发现 | `WindowFinder` (macOS/Windows) | 实时截图验证 |
| 屏幕截图 | `ScreenCapture` (mss) | CLI `capture` 命令 |
| 帧状态检测 | `FrameChecker` | 单元测试 |
| 端到端流水线 | `CapturePipeline` + CLI | 真实截图分割 |
| 坐标校准工具 | `calibrate` 命令 | 人工目视验证 |

---

## 后续计划预览

**Plan 2: 识别引擎** 将基于本计划产出的区域图像，实现：
- TileDetector: YOLOv8 ONNX 推理封装
- TextRecognizer: PaddleOCR 文字识别封装
- PatternMatcher: 动作按钮模板匹配
