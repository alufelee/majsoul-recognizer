# 雀魂麻将识别助手 — 识别引擎设计文档 (Plan 2a)

> 版本: 4.0 | 日期: 2026-05-06 | 阶段: 推理引擎代码

## 1. 概述

本设计定义推理引擎的代码框架，包含四个子模块和一个统一门面。模型训练和数据合成在 Plan 2b 中独立执行。

**范围**:
- TileDetector — YOLOv8 ONNX 推理封装
- TextRecognizer — PaddleOCR 后处理封装（ONNX 推理）
- PatternMatcher — 动作按钮模板匹配
- GameStateBuilder + Validator — 结果组装与规则校验
- RecognitionEngine — 统一门面
- RecognitionConfig — 配置管理

**不含**: 合成数据生成、YOLOv8 训练脚本、PaddleOCR 模型训练、真实数据标注。

**测试策略**: 为每个子模块创建假模型/假模板，使测试端到端可运行。

## 2. 架构

### 2.1 集成路径

`RecognitionEngine` 与 `CapturePipeline` 是两个独立的对象，调用者自行编排：

```python
pipeline = CapturePipeline()
engine = RecognitionEngine()

result = pipeline.process_image(screenshot)
if result.is_static:
    game_state = engine.recognize(result.zones)
    # game_state: GameState — 完整的游戏状态
```

`RecognitionEngine.recognize()` 返回独立的 `GameState`，不修改 `FrameResult`。调用者可按需将 `game_state` 赋给 `result.game_state`。

### 2.2 数据流

```
CapturePipeline.process_image()
    ↓ FrameResult.zones: dict[str, ndarray] (键为 ZoneName 的 .value 字符串)
RecognitionEngine.recognize(zones)
    ↓
    ├── [多区域拼接] → TileDetector.detect_batch() → dict[str, list[Detection]]
    │     (返回的 Detection.bbox 已是区域本地坐标)
    ├── TextRecognizer.recognize_score/round/timer → 分数/局次/倒计时
    └── PatternMatcher.match() → list[ActionMatch]
    ↓
    ├── Detection 级帧间融合 (Validator.fuse_detections)
    │     (融合结果保留 zone_name)
    ↓
GameStateBuilder.build()
    ↓ 组装为 GameState（含 drawn_tile 间隔检测、手牌排序、副露解析、牌河构建）
    ↓ 键名统一：zone_name 前缀剥离 → "self"/"right"/"opposite"/"left"
Validator.validate()
    ↓ 规则校验
    ↓
GameState
```

## 3. 类型扩展

### 3.1 新增类型（加入 `types.py`）

```python
from typing import Literal

CallType = Literal["chi", "pon", "kan", "ankan", "kakan"]

class CallGroup(BaseModel):
    """一组副露（吃/碰/杠）

    rotated_index 使用 is not None 检查（0 是合法值，表示横置牌在第一个位置）。
    """
    model_config = {"frozen": True}
    type: CallType                        # 副露类型，使用 Literal 约束
    tiles: list[str]                      # 组成牌面编码列表（合法 tile_code）
    rotated_index: int | None = None      # 横置牌在 tiles 中的索引（指示来源）
    from_player: str | None = None        # "right" | "opposite" | "left"

class ActionMatch(BaseModel):
    """动作按钮匹配结果

    字段名 score（而非 confidence）与 OpenCV matchTemplate 的术语一致。
    """
    model_config = {"frozen": True}
    name: str                              # 动作名称（"吃"/"碰"/"杠"等）
    score: float = Field(ge=0.0, le=1.0)  # 模板匹配分数
```

### 3.2 修改现有类型

**`PlayerScore` 删除与迁移**：

现有 `types.py` 中的 `PlayerScore` 类将被删除。受影响文件清单：
- `types.py`: 删除 `PlayerScore` 类定义（第 135-138 行）
- `test_types.py`: 删除 `PlayerScore` 相关导入和测试（如有）
- `GameState.scores`: 从 `dict[str, int | PlayerScore]` 改为 `dict[str, int]`

迁移策略：直接删除 `PlayerScore`。当前代码库中无外部消费者使用该类型（GameState 创建时 scores 默认为空字典）。若有外部代码使用了 `PlayerScore`，改为直接使用 `int` 值。

**`GameState`**: 修改以下字段：

```python
class GameState(BaseModel):
    """游戏全局状态"""
    model_config = {"frozen": True}      # frozen 模式，validate() 返回新实例
    round_info: RoundInfo | None = None
    dora_indicators: list[str] = Field(default_factory=list)
    scores: dict[str, int] = Field(default_factory=dict)       # 键: "self"/"right"/"opposite"/"left"
    hand: list[str] = Field(default_factory=list)
    drawn_tile: str | None = None
    calls: dict[str, list[CallGroup]] = Field(default_factory=dict)  # 键: "self"（后续扩展 right/opposite/left）
    discards: dict[str, list[str]] = Field(default_factory=dict)     # 键: "self"/"right"/"opposite"/"left"
    actions: list[str] = Field(default_factory=list)
    timer_remaining: int | None = None
    warnings: list[str] = Field(default_factory=list)
```

**`GameState` 设为 frozen**：`Validator.validate()` 使用 `model_copy(update={"warnings": ...})` 返回新实例，而非原地修改。与 `Detection`、`CallGroup` 等保持一致。

**键命名空间统一**：`scores`、`calls`、`discards` 三个字典使用统一键名 `"self"` / `"right"` / `"opposite"` / `"left"`。`GameStateBuilder` 在构建时做 zone_name 前缀剥离（如 `"score_self"` → `"self"`，`"discards_right"` → `"right"`）。

**`GameState.timer_remaining`**: 保留 `int | None`。`None` 表示非自己回合，非 None 表示倒计时可见。

**`Detection`**: `zone_name` 字段已存在（types.py 第 107 行），融合过程中必须保留。

### 3.3 `_DEFAULT_CLASS_MAP` 与 `Tile` 枚举校验

`_DEFAULT_CLASS_MAP` 中 ID 0-36 的 tile_code 必须与 `Tile` 枚举的 `.value` 完全对应。在测试中添加断言：

```python
def test_class_map_covers_all_tiles():
    tile_codes = set(_DEFAULT_CLASS_MAP.values()) - {"back", "rotated", "dora_frame"}
    from majsoul_recognizer.tile import Tile
    assert tile_codes == {t.value for t in Tile}
```

## 4. 配置管理

### 4.1 RecognitionConfig

```python
# 项目根目录（开发模式）和包目录（pip install）的辅助函数
def _resolve_resource_path(rel_path: str) -> Path | None:
    """优先从 importlib.resources 查找，回退到 __file__ 相对路径"""
    # 开发模式: 项目根目录下的相对路径
    dev_path = Path(__file__).parent.parent.parent / rel_path
    if dev_path.exists():
        return dev_path
    # pip install: importlib.resources（仅对包内文件有效）
    try:
        ref = importlib.resources.files("majsoul_recognizer").joinpath(rel_path)
        if ref.is_file():
            return Path(str(ref))
    except Exception:
        pass
    return None

class RecognitionConfig(BaseModel):
    """识别引擎可调参数"""
    model_config = {"arbitrary_types_allowed": True}

    # TileDetector
    model_path: Path | None = None        # None 时调用 _resolve_resource_path("models/current/tile_detector.onnx")
    mapping_path: Path | None = None      # None 使用内置默认映射
    nms_iou_threshold: float = 0.55
    detection_confidence: float = 0.7     # 作为 detect()/detect_batch() 的默认 confidence

    # TextRecognizer
    ocr_model_dir: Path | None = None     # None 使用 paddleocr 默认路径

    # PatternMatcher
    template_dir: Path | None = None      # None 时调用 _resolve_resource_path("templates/")

    # Validator
    score_min: int = -99999               # 雀魂理论最低分，实际很少低于 -30000
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

### 4.2 默认映射

`TileDetector` 内置硬编码的 `_DEFAULT_CLASS_MAP: dict[int, str]`，无需外部 JSON 即可工作：

```python
_DEFAULT_CLASS_MAP = {
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
# 注意: ID 0-36 的值集合必须与 Tile 枚举的 .value 集合完全对应
# 测试中通过 test_class_map_covers_all_tiles() 自动校验
```

## 5. TileDetector

### 5.1 接口

```python
class TileDetector:
    """YOLOv8 ONNX 牌面检测器"""

    def __init__(self, model_path: Path | str,
                 class_map: dict[int, str] | None = None,
                 nms_iou: float = 0.55):
        """
        Args:
            model_path: ONNX 模型文件路径
            class_map: 类别 ID → tile_code 映射，None 使用 _DEFAULT_CLASS_MAP
            nms_iou: NMS IoU 阈值（默认 0.55）
        """

    def detect(self, image: np.ndarray, confidence: float = 0.7) -> list[Detection]:
        """检测单张图像中的牌面"""

    def detect_batch(self, images: list[tuple[str, np.ndarray]],
                     confidence: float = 0.7) -> dict[str, list[Detection]]:
        """
        多区域拼接检测（性能优化）

        Args:
            images: [(zone_name, image), ...] 区域图像列表
            confidence: 最低置信度阈值

        Returns:
            {zone_name: list[Detection]} 按区域分组的检测结果
            返回的 Detection.bbox 已转换为区域本地坐标系
        """
```

### 5.2 ONNX 模型规格

**导出参数**: `yolo export model=best.pt format=onnx imgsz=640 simplify=True`
- 非端到端导出（不含内置 NMS），需自行实现后处理

**输入**: `images` — shape `(1, 3, 640, 640)`, dtype `float32`, 值域 `[0, 1]`

**输出**: `output0` — shape `(1, 44, 8400)` 其中 44 = 4(bbox) + 40(classes)

**NMS 后处理**:
1. 转置输出为 `(8400, 44)`
2. 取前 4 列为 bbox (cx, cy, w, h)，后 40 列为类别分数
3. 每行取 max class score，若 >= confidence 阈值则保留
4. 对保留的检测做 NMS（IoU 阈值 `nms_iou`，默认 0.55）
5. 将 bbox 从 letterbox 坐标还原到原图坐标
6. 类别 ID 通过 class_map 映射为 tile_code

### 5.3 类别处理策略

40 类中 37 类对应 `Tile` 枚举值，另外 3 类为辅助类别：

| 类别 | tile_code | 处理方式 |
|------|-----------|----------|
| 0-36 | `1m`-`5sr` | 正常牌面，进入 GameState |
| 37 | `back` | 仅计数，不进入 hand/discards/calls，仅在 `GameState.warnings` 中记录 |
| 38 | `rotated` | 不作为独立检测。用于辅助横置牌定位（见下方算法） |
| 39 | `dora_frame` | 仅辅助定位宝牌区域，不进入 GameState |

**`rotated` 类别的横置牌定位算法**：

```python
def _resolve_rotated_tiles(
    all_detections: list[Detection],
) -> dict[int, Detection]:
    """
    将 rotated 类别的检测关联到最近的正常牌面检测。

    Returns:
        {normal_detection_index: rotated Detection} 映射
    """
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
```

### 5.4 detect_batch 画布布局

**布局规则**：将多个区域图像以网格方式排列在 640×640 画布上。

```
Canvas (640 x 640):
┌──────────┬──────────┐
│ Zone 0   │ Zone 1   │  y=0, 每个 slot 大小由 N 决定
├──────────┼──────────┤
│ Zone 2   │ Zone 3   │
├──────────┼──────────┤
│ Zone 4   │ Zone 5   │  最多 6 个区域，超过时分多张画布
└──────────┴──────────┘
```

**slot 大小计算**：`slot_size = 640 // max(2, ceil(sqrt(N)))`，确保所有 slot 等大且完整填充画布。

**缩放规则**：
1. 将区域图像等比缩放至 slot 内（保持宽高比，居中放置）
2. 背景填充为 (114, 114, 114)（YOLOv8 标准 pad 色值）

**坐标转换**：
```python
@dataclass
class _CanvasSlot:
    """记录每个区域在画布上的位置"""
    zone_name: str
    x_offset: int     # 区域图像在画布上的 x 偏移
    y_offset: int     # 区域图像在画布上的 y 偏移
    scale: float      # 缩放比例
    orig_w: int       # 原始宽度
    orig_h: int       # 原始高度
    slot_size: int    # slot 尺寸

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
```

**检测结果归属算法**：

```python
def _assign_to_slot(
    detections: list[Detection],
    slots: list[_CanvasSlot],
) -> dict[str, list[Detection]]:
    """将画布上的检测结果归属到对应的区域 slot"""
    result: dict[str, list[Detection]] = {s.zone_name: [] for s in slots}

    for det in detections:
        cx = det.bbox.x + det.bbox.width // 2
        cy = det.bbox.y + det.bbox.height // 2

        # 找中心点落在哪个 slot 的图像范围内
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
            # 中心点在 padding 区域 → 丢弃（背景误检）
            logger.debug("Discarding detection in padding area: %s", det)

    return result
```

detect_batch 内部流程：
1. 根据 `len(images)` 计算 slot 布局
2. 将每个区域图像等比缩放并绘制到画布上，记录 `_CanvasSlot`
3. 执行 ONNX 推理 + NMS 后处理
4. 调用 `_assign_to_slot()` 归属 + 坐标转换
5. 返回 `{zone_name: list[Detection]}`

### 5.5 假模型生成

使用 `onnx` 库生成 `tests/fixtures/dummy_detector.onnx`：

```python
import numpy as np
import onnx
from onnx import helper, TensorProto, numpy_helper

def create_dummy_detector(path: str) -> None:
    """生成 640x640 输入的 ONNX 模型（测试用）

    输入: images (1, 3, 640, 640) float32
    输出: output0 (1, 44, 8400) float32

    在固定位置放置一个可检测的目标，使测试能验证完整的检测管线：
    - 第 0 行：bbox (cx=80, cy=80, w=60, h=80) → letterbox 还原后约为 (80, 80, 60, 80)
    - 第 0 行第 4+0 列（类别 0 = "1m"）分数 0.95
    """
    output = np.zeros((1, 44, 8400), dtype=np.float32)

    # 在 index 0 放置一个高置信度检测目标
    output[0, 0, 0] = 80.0   # cx
    output[0, 1, 0] = 80.0   # cy
    output[0, 2, 0] = 60.0   # w
    output[0, 3, 0] = 80.0   # h
    output[0, 4, 0] = 0.95   # class 0 (1m) confidence

    X = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])
    Y = helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 44, 8400])

    output_data = numpy_helper.from_array(output, "output0")
    const_node = helper.make_node("Constant", [], ["output0"], value=output_data)

    graph = helper.make_graph([const_node], "dummy_detector", [X], [Y])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 7
    onnx.checker.check_model(model)
    onnx.save(model, path)
```

假模型在 index 0 输出一个 cx=80, cy=80, w=60, h=80, class=0(1m), conf=0.95 的检测目标。测试可验证坐标转换、NMS、batch 分组、zone_name 赋值等完整流程。

## 6. TextRecognizer

### 6.1 接口

```python
class TextRecognizer:
    """文字识别器"""

    def __init__(self, model_dir: Path | str | None = None):
        """
        Args:
            model_dir: OCR 模型目录，None 使用 paddleocr 默认
        """

    def recognize_score(self, image: np.ndarray) -> int | None:
        """
        识别分数区域
        Returns: 整数分数，识别失败返回 None
        """

    def recognize_round(self, image: np.ndarray) -> RoundInfo | None:
        """
        识别局次信息，包含 wind, number, honba, kyotaku
        Returns: RoundInfo，识别失败返回 None
        """

    def recognize_timer(self, image: np.ndarray) -> int | None:
        """
        识别倒计时
        Returns: 秒数，区域不可见或识别失败返回 None
        """
```

### 6.2 内部流程

```
输入图像 → 预处理 (灰度 + 自适应二值化)
    → PaddleOCR 推理
    → 字符白名单过滤
    → 后处理 (见下)
    → 类型转换 → 返回结构化结果
```

### 6.3 后处理详解

**`recognize_score`**：
1. OCR 原始文本 → 去除空格和逗号
2. 处理负号：若文本以 `-` 开头，记录为负分
3. 提取连续数字 → `int()` 转换
4. 校验 `[score_min, score_max]` → 越界返回 None
5. 空文本或无数字 → 返回 None

**`recognize_round`**：OCR 原始文本变体及解析：

```python
# 风位映射 — 覆盖简繁体中文
_WIND_MAP = {
    "东": "东", "東": "东",  # 简繁体东风
    "南": "南",              # 南风（简繁同形）
}

# 局数映射 — 覆盖中文数字 + 阿拉伯数字兜底
_NUMBER_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4,
    "1": 1, "2": 2, "3": 3, "4": 4,
}

# "本场" 关键字变体（简繁体，不含日文）
_HONBA_KEYWORDS = ["本场", "本場"]

# "供托" 关键字变体（简繁体。"棒"为日文立直棒表示，中文版不使用）
_KYOTAKU_KEYWORDS = ["供托", "供託"]
```

解析算法：
1. 遍历字符匹配风位 → `_WIND_MAP[char]` → `wind`
2. 匹配局数 → `_NUMBER_MAP[char]` → `number`
3. 找 `_HONBA_KEYWORDS` 前的数字 → `honba`（默认 0）
4. 找 `_KYOTAKU_KEYWORDS` 前的数字 → `kyotaku`（默认 0）

若 `wind` 或 `number` 缺失，返回 None。

**`recognize_timer`**: 纯数字 → `int()`。图像面积过小（区域不可见）时直接返回 None。

### 6.4 测试策略

双层测试：
- **单元测试**: 不加载 PaddleOCR，直接构造 `_parse_score_text("25,000") → 25000` 等后处理函数，覆盖正常/异常/边界值
- **集成测试**: 标记 `@pytest.mark.skipif("not ocr_available")`，需要 PaddleOCR 安装

### 6.5 PaddleOCR 调用方式

```python
from paddleocr import PaddleOCR

self._ocr = PaddleOCR(
    use_angle_cls=False,
    lang="ch",
    use_gpu=False,
    det_model_dir=...,
    rec_model_dir=...,
    rec_char_dict_path=...,   # 自定义字符字典
    show_log=False,
)
```

**字典文件格式**：PaddleOCR 字典文件为 UTF-8 文本文件，**每行一个字符**（非空格分隔）。为不同识别场景创建独立字典：

`score_dict.txt`:
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

`round_dict.txt`:
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

`timer_dict.txt`:
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

**字典文件位置**：放置于 `src/majsoul_recognizer/ocr_dicts/` 目录（包内），在 `pyproject.toml` 中声明为 `package-data`：

```toml
[tool.setuptools.package-data]
majsoul_recognizer = ["ocr_dicts/*.txt"]
```

通过 `importlib.resources` 访问，与 `zones.yaml` 的定位方式一致。开发模式和 pip install 均可正确找到。

## 7. PatternMatcher

### 7.1 接口

```python
class PatternMatcher:
    """动作按钮模板匹配"""

    def __init__(self, template_dir: Path):
        """加载模板目录下所有模板"""

    def match(self, image: np.ndarray, threshold: float = 0.85) -> list[ActionMatch]:
        """
        Args:
            image: actions 区域图像
            threshold: 匹配阈值 (0-1)

        Returns:
            匹配到的动作列表，含名称和匹配分数
        """
```

### 7.2 模板文件

```
templates/
├── chi.png      # 吃
├── pon.png      # 碰
├── kan.png      # 杠
├── ron.png      # 荣和
├── tsumo.png    # 自摸
├── riichi.png   # 立直
└── skip.png     # 过
```

### 7.3 测试策略

conftest 中生成假模板：纯色矩形 + cv2.putText 写入按钮名称。在 actions 区域图像上放置已知的按钮图案后验证匹配。

## 8. GameStateBuilder + Validator

### 8.1 GameStateBuilder

```python
class GameStateBuilder:
    """将子模块原始结果组装为 GameState"""

    def __init__(self, config: RecognitionConfig):
        self._config = config

    # 键名映射：zone_name 前缀 → GameState 字典键
    _ZONE_KEY_MAP = {
        "score_self": "self", "score_right": "right",
        "score_opposite": "opposite", "score_left": "left",
        "discards_self": "self", "discards_right": "right",
        "discards_opposite": "opposite", "discards_left": "left",
        "calls_self": "self",
    }

    def _zone_key(self, zone_name: str) -> str:
        """将 zone_name 转为统一的 GameState 字典键"""
        return self._ZONE_KEY_MAP.get(zone_name, zone_name)

    def build(
        self,
        detections: dict[str, list[Detection]],
        scores: dict[str, int | None],
        round_info: RoundInfo | None,
        timer: int | None,
        actions: list[ActionMatch],
        prev_state: GameState | None = None,
    ) -> GameState:
        """
        Args:
            detections: 按区域名分组的检测结果
            scores: 按区域名分组的分数（可能含 None）
            round_info: 局次信息
            timer: 倒计时秒数
            actions: 匹配到的动作列表
            prev_state: 上一帧状态（用于 drawn_tile 回退和 kakan 来源）

        Returns:
            完整的 GameState 实例
        """
```

### 8.2 构建逻辑详解

**手牌排序**: `state.hand` 按 Detection 的 bbox.x 坐标从左到右排序。

**drawn_tile 间隔检测算法**:
1. 将 `detections["hand"]` 按 bbox.x 排序
2. 计算相邻 Detection 的 bbox 间距：`gap[i] = dets[i+1].bbox.x - (dets[i].bbox.x + dets[i].bbox.width)`
3. 计算间距中位数 `median_gap`
4. 若某个间距 `gap[i] > median_gap * drawn_tile_gap_multiplier`，则 `dets[i+1]` 为 drawn_tile
5. 特殊处理：
   - 手牌总数 <= 1 时无间隔可计算，若检测到 14 张则最后一张为 drawn_tile
   - 手牌 13 张且无间隔：检查 `prev_state`，若上一帧 hand 为 13 张且 drawn_tile 为 None，则当前帧无 drawn_tile（等待摸牌中）。若上一帧 hand 为 12 张，则当前帧多出 1 张但无法定位，添加 `"hand_13_no_gap"` warning。

**副露解析** (`calls_self`):
1. 按 bbox.x 排序所有 Detection（过滤掉 `back` 和 `dora_frame`）
2. 使用 `_resolve_rotated_tiles()` 找出被标记为横置的牌面检测
3. 计算相邻 Detection 的 bbox 间距
4. 使用 `call_group_gap_multiplier`（默认 2.0）乘以中位间距进行分组
5. 根据每组牌数推断副露类型：3 张 → chi/pon，4 张 → kan/ankan
6. 根据 `rotated_map` 中的横置牌位置确定 `rotated_index`
7. 根据副露类型 + `rotated_index` 推断 `from_player`

**from_player 推断** — 完整确定性映射表：

所有副露类型的横置牌位置与来源玩家的关系在雀魂中遵循统一规则：**横置牌指向的玩家即为出牌来源**。横置牌逆时针旋转 90° 指向的方位就是来源方位。

以自家视角（屏幕正下方），三个对手方位的关系：

```
          对家(opposite)
          ↑ 逆时针90°
左家(left) ← 自家(self) → 右家(right)
```

映射规则：

| rotated_index | 副露类型 | from_player | 说明 |
|:---:|:---:|:---:|:---|
| 0 | chi | "right" | 横置牌在位置 0（最左），逆时针指右家 |
| 1 | chi | "opposite" | 横置牌在位置 1（中间），逆时针指对家 |
| 2 | chi | "left" | 横置牌在位置 2（最右），逆时针指左家 |
| 0 | pon | "right" | 碰牌横置在位置 0，来自右家 |
| 1 | pon | "opposite" | 碰牌横置在位置 1，来自对家 |
| 2 | pon | "left" | 碰牌横置在位置 2，来自左家 |
| 0-3 中某位 | kan | 同该位置对应方位 | 明杠中 1 张横置，规则与碰相同 |
| — | ankan | None | 暗杠无横置牌 |
| — | kakan | 继承 prev_state 中对应碰组的 from_player | 加杠的来源与碰牌时相同 |

**kakan 的 from_player 继承**：从 `prev_state.calls["self"]` 中查找与新杠牌有 3 张相同花色数字（不含赤宝牌差异）的碰组，继承其 `from_player`。若 `prev_state` 中无记录（首帧或状态丢失），`from_player` 设为 None，添加 `"kakan_unknown_source"` warning。

**杠的识别**：
- **kan (明杠)**: 4 张牌中 1 张横置（`rotated_index` 指向横置牌），其余正面
- **ankan (暗杠)**: 4 张牌中两侧 2 张为 `back` 类别，中间 2 张正面。`rotated_index = None`，`from_player = None`
- **kakan (加杠)**: 已有碰组 + 新增 1 张横置牌，共 4 张。通过 `prev_state` 识别

**对手副露**: 当前 `zones.yaml` 无对手副露区域。Plan 2a 中对手副露暂不处理，`GameState.calls` 只填充 `"self"` 键。

**牌河构建**：
1. 从 `detections` 中提取 `discards_self`/`discards_right`/`discards_opposite`/`discards_left` 区域的检测结果
2. 过滤掉辅助类别（`tile_code` 为 `back`/`rotated`/`dora_frame` 的 Detection 丢弃）
3. 调用 `_sort_discards()` 排序
4. 提取 `Detection.tile_code` 列表
5. 使用 `_zone_key()` 转换键名后写入 `GameState.discards`
6. 若某方位区域不在 `detections` 中，不写入 `discards` 字典（键不存在）

**牌河排序**：

雀魂牌河布局：
- 自家 (`discards_self`): 水平排列，6 张一行，从左到右，从上到下
- 对家 (`discards_opposite`): 同自家
- 右家 (`discards_right`): 垂直排列，从上到下，从左到右开新列
- 左家 (`discards_left`): 垂直排列，从上到下，从右到左开新列

> **注意**: 排序方向需对照雀魂实际截图确认。以下算法基于当前理解，实施时如发现不符则以实际 UI 为准。

排序算法：
```python
def _sort_discards(detections: list[Detection], zone_name: str) -> list[Detection]:
    """对牌河检测结果排序"""
    if not detections:
        return []

    if zone_name in ("discards_self", "discards_opposite"):
        return _sort_horizontal_grid(detections)
    elif zone_name == "discards_right":
        return _sort_vertical_grid(detections, ascending_x=True)   # 列从左到右
    else:  # discards_left
        return _sort_vertical_grid(detections, ascending_x=False)  # 列从右到左

def _median_height(dets: list[Detection]) -> int:
    """计算检测框的中位高度（避免异常小检测影响阈值）"""
    heights = sorted(d.bbox.height for d in dets)
    return heights[len(heights) // 2]

def _median_width(dets: list[Detection]) -> int:
    """计算检测框的中位宽度"""
    widths = sorted(d.bbox.width for d in dets)
    return widths[len(widths) // 2]

def _sort_horizontal_grid(dets: list[Detection]) -> list[Detection]:
    """水平网格排序（自家/对家牌河）"""
    if len(dets) <= 1:
        return dets
    median_h = _median_height(dets)
    threshold = median_h * 0.5  # 使用中位高度而非单个检测的高度

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
    median_w = _median_width(dets)
    threshold = median_w * 0.5  # 使用中位宽度

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
```

**宝牌构建**: 从 `detections["dora"]` 中提取 `tile_code`，过滤辅助类别后写入 `GameState.dora_indicators`。

**分数构建**: 使用 `_zone_key()` 转换键名。`None` 值表示识别失败，不写入 `GameState.scores`。

**actions 转换**: `list[ActionMatch]` → 提取 `.name` → `state.actions`。

### 8.3 Validator

```python
class Validator:
    """规则校验与 Detection 级帧间融合"""

    def __init__(self, config: RecognitionConfig):
        self._config = config
        self._prev_state: GameState | None = None
        self._detection_window: list[dict[str, list[Detection]]] = []

    def validate(self, state: GameState) -> GameState:
        """
        校验当前状态，返回带 warnings 的新 GameState 实例。
        内部更新 prev_state。使用 model_copy(update=...) 返回新实例（GameState 是 frozen 的）。
        """

    def fuse_detections(self, current: dict[str, list[Detection]]) -> dict[str, list[Detection]]:
        """Detection 级帧间融合"""

    def reset(self):
        """重置历史状态（对局结束时调用）"""

    @property
    def prev_state(self) -> GameState | None:
        """供 GameStateBuilder 使用的上一帧状态"""
```

### 8.4 校验规则

| 规则 | 说明 | warning key |
|------|------|-------------|
| 手牌数量 | 见下方公式 | `hand_count_mismatch` |
| 牌数上限 | 同一 tile_code 全场最多 4 张（赤宝牌 5mr/5pr/5sr 与对应 5m/5p/5s 共享同一物理位置，合并计数） | `tile_overflow` |
| 牌河连续性 | 每帧每家 discards 最多比上帧多 1 张 | `discard_jump` |
| 分数合理性 | `score_min <= score <= score_max` | `score_anomaly` |

**手牌数量校验公式**：

```python
# 每组副露消耗的手牌数：碰/吃消耗 3 张，杠消耗 4 张
all_calls = list(state.calls.values())
flat_calls = [c for group in all_calls for c in group]
kan_count = sum(1 for c in flat_calls if c.type in ("kan", "ankan", "kakan"))
non_kan_count = len(flat_calls) - kan_count

expected_hand = 13 - non_kan_count * 3 - kan_count * 4 + len(flat_calls) * 3
# 简化：expected_hand = 13 - kan_count（每个杠比碰/吃多消耗 1 张）
actual_hand = len(state.hand) + (1 if state.drawn_tile else 0)
if actual_hand != expected_hand:
    warnings.append("hand_count_mismatch")
```

即：`actual_hand = len(hand) + (1 if drawn_tile else 0)`，`expected_hand = 13 - kan_count`。

**赤宝牌计数规则**：`5m` 和 `5mr` 在物理上是同一张牌的不同状态，合并计数时视为同一 tile_code。校验时将 `5mr` 映射为 `5m`、`5pr` 映射为 `5p`、`5sr` 映射为 `5s` 后统计。

### 8.5 Detection 级帧间融合

融合在 Detection 层面进行（在 `GameStateBuilder.build()` 之前）：

```python
def fuse_detections(self, current: dict[str, list[Detection]]) -> dict[str, list[Detection]]:
    """
    对每个区域的检测结果做帧间融合

    算法：
    1. 将 current 加入滑动窗口（保留最近 N 帧，默认 3）
    2. 首帧（窗口中仅 1 帧）：直接返回 current，不做融合
    3. 按区域独立处理（跨区域不做匹配）：
       a. 对当前帧的每个 Detection，在历史帧的**同区域**中匹配
       b. 匹配方式：中心点距离 < bbox 中位宽度 * 0.5（比 IoU 在密集场景更鲁棒）
       c. 对匹配到的目标组：
          - tile_code: 取出现次数最多的（多数投票）
          - confidence: 取平均值
          - 若 3 帧不一致，confidence *= 0.8
       d. 仅返回当前帧中存在的目标（不保留历史幽灵）
    4. 每个融合后的 Detection 继承当前帧的 zone_name
    """
```

## 9. RecognitionEngine 门面

### 9.1 接口

```python
class RecognitionEngine:
    """识别引擎统一入口"""

    def __init__(self, config: RecognitionConfig | None = None):
        """
        Args:
            config: 识别配置，None 使用默认值
        """

    def recognize(self, zones: dict[str, np.ndarray]) -> GameState:
        """
        识别完整的游戏状态

        Args:
            zones: 区域图像字典

        Returns:
            完整的 GameState
        """

    def warmup(self) -> None:
        """
        预热引擎：用零张量执行一次 ONNX 推理，触发图优化和 Provider 初始化。
        首次 recognize() 时自动调用。可手动提前调用。
        """

    def reset(self):
        """重置引擎状态（对局结束时调用）"""

    def __enter__(self) -> "RecognitionEngine":
        return self

    def __exit__(self, *args) -> None:
        """释放 ONNX session 等资源"""
        self._detector = None
        self._validator.reset()
```

### 9.2 分派逻辑

```python
def recognize(self, zones: dict[str, np.ndarray]) -> GameState:
    # 空输入快速返回
    if not zones:
        return GameState(warnings=["empty_zones"])

    logger.info("Recognition started, %d zones received", len(zones))

    # 首次调用时自动预热
    if not self._warmed_up:
        self.warmup()

    # 1. 牌面检测（多区域拼接优化）
    tile_zone_names = ["hand", "dora", "discards_self", "discards_right",
                       "discards_opposite", "discards_left", "calls_self"]
    tile_images = [(name, zones[name]) for name in tile_zone_names if name in zones]

    confidence = self._config.detection_confidence  # 从 config 统一传入

    if self._config.enable_batch_detection and len(tile_images) > 1:
        detections = self._detector.detect_batch(tile_images, confidence)
    else:
        detections = {name: self._detector.detect(img, confidence)
                      for name, img in tile_images}

    # 设置 Detection.zone_name（防御性处理：未知区域名跳过）
    for zone_name_str, dets in detections.items():
        try:
            zn = ZoneName(zone_name_str)
        except ValueError:
            logger.warning("Unknown zone name: %s, skipping zone_name assignment",
                           zone_name_str)
            continue
        detections[zone_name_str] = [
            d.model_copy(update={"zone_name": zn}) for d in dets
        ]

    # 2. Detection 级帧间融合
    detections = self._validator.fuse_detections(detections)

    # 3. 文字识别（None 安全）
    scores: dict[str, int | None] = {}
    for prefix in ["score_self", "score_right", "score_opposite", "score_left"]:
        if prefix in zones and zones[prefix].size > 0:
            scores[prefix] = self._ocr.recognize_score(zones[prefix])

    round_info = None
    if "round_info" in zones and zones["round_info"].size > 0:
        round_info = self._ocr.recognize_round(zones["round_info"])

    timer = None
    if "timer" in zones and zones["timer"].size > 0:
        timer = self._ocr.recognize_timer(zones["timer"])

    # 4. 模板匹配
    actions: list[ActionMatch] = []
    if "actions" in zones and zones["actions"].size > 0:
        actions = self._matcher.match(zones["actions"])

    # 5. 组装 + 校验
    state = self._builder.build(
        detections, scores, round_info, timer, actions,
        prev_state=self._validator.prev_state,
    )
    state = self._validator.validate(state)

    logger.info("Recognition done: hand=%d, warnings=%d",
                len(state.hand), len(state.warnings))
    return state
```

### 9.3 None 值统一处理

所有子模块方法在 `image` 为 None 或 size==0 时返回空结果：
- `TileDetector.detect(None)` → `[]`
- `TextRecognizer.recognize_*(None)` → `None`
- `PatternMatcher.match(None)` → `[]`

分派逻辑在调用前做 `in zones and zones[x].size > 0` 检查。

### 9.4 生命周期管理

`RecognitionEngine` 为有状态对象，支持 `with` 语句自动释放资源：
- 每局开始时调用 `engine.reset()` 重置状态
- `__exit__` 释放 ONNX session 等重资源
- 多个引擎实例可并存（测试或并行处理）

## 10. 日志策略

每个子模块使用 `logger = logging.getLogger(__name__)`，关键路径记录：

| 模块 | 日志点 | 级别 |
|------|--------|------|
| TileDetector | 推理耗时、检测数量、置信度分布 | DEBUG |
| TileDetector | 模型加载成功/失败 | INFO/WARNING |
| TextRecognizer | OCR 原始文本、后处理结果 | DEBUG |
| TextRecognizer | 识别失败 | WARNING |
| PatternMatcher | 各模板匹配分数 | DEBUG |
| GameStateBuilder | drawn_tile 检测结果、手牌数量、副露分组 | DEBUG |
| Validator | 校验 warning 详情 | WARNING |
| Validator | 融合窗口状态 | DEBUG |
| RecognitionEngine | 开始/完成/总耗时 | INFO |
| RecognitionEngine | 降级决策 | WARNING |

日志格式统一使用 `%s` 占位符（非 f-string）。

## 11. 性能预算

| 阶段 | 预算 | 说明 |
|------|------|------|
| TileDetector (batch) | ≤ 50ms | 单次 ONNX 前向（多区域拼接） |
| TextRecognizer | ≤ 50ms | 4 个分数 + 局次 + 倒计时 |
| PatternMatcher | ≤ 10ms | 7 个模板 matchTemplate |
| Detection 融合 | ≤ 5ms | 纯逻辑 |
| GameStateBuilder | ≤ 5ms | 纯逻辑 |
| Validator | ≤ 5ms | 规则校验 |
| **总计** | **≤ 125ms** | **满足 200ms 目标，余量 75ms** |

每个子模块用 `time.perf_counter()` 测量耗时并记入日志。

## 12. 错误恢复与降级

| 场景 | 降级策略 |
|------|----------|
| ONNX 模型文件不存在 | `RecognitionEngine.__init__` 抛出 FileNotFoundError |
| ONNX 推理失败 | `TileDetector.detect()` 捕获异常，返回空列表，logger.warning |
| PaddleOCR 不可用 | `TextRecognizer` 所有方法返回 None，logger.warning |
| 单个区域图像为空 | 跳过该区域，不写入 GameState 对应字段 |
| 全部检测失败 | 返回空 GameState（仅 warnings），不崩溃 |
| 连续 5 帧无检测结果 | Validator 添加 `"no_detection_5_frames"` warning |
| 分数识别结果异常 | 沿用上一帧分数（如有），添加 `"score_anomaly"` warning |
| 空 zones 输入 | 快速返回带 `"empty_zones"` warning 的空 GameState |

## 13. 依赖新增

```toml
[project.optional-dependencies]
recognition = [
    "onnxruntime>=1.16",
]
recognition-ocr = [
    "paddleocr>=2.7",
    "paddlepaddle>=2.5",
]

[tool.setuptools.package-data]
majsoul_recognizer = ["ocr_dicts/*.txt"]
```

ONNX Runtime Provider 选择：
```python
providers = []
if "CoreMLExecutionProvider" in ort.get_available_providers():
    providers.append("CoreMLExecutionProvider")
if "CUDAExecutionProvider" in ort.get_available_providers():
    providers.append("CUDAExecutionProvider")
providers.append("CPUExecutionProvider")
```

## 14. 文件结构

```
src/majsoul_recognizer/
├── recognition/
│   ├── __init__.py          # 导出 RecognitionEngine, RecognitionConfig
│   ├── engine.py            # RecognitionEngine 门面
│   ├── config.py            # RecognitionConfig
│   ├── tile_detector.py     # TileDetector
│   ├── text_recognizer.py   # TextRecognizer
│   ├── pattern_matcher.py   # PatternMatcher
│   └── state_builder.py     # GameStateBuilder + Validator
├── ocr_dicts/               # OCR 字符字典（包内，通过 package-data 打包）
│   ├── score_dict.txt
│   ├── round_dict.txt
│   └── timer_dict.txt
├── types.py                 # 新增 CallGroup, ActionMatch; 删除 PlayerScore; GameState frozen
└── ...

config/
└── zones.yaml

tests/
├── recognition/
│   ├── __init__.py
│   ├── conftest.py          # 假模型生成、假模板生成 fixtures
│   ├── test_tile_detector.py
│   ├── test_text_recognizer.py
│   ├── test_pattern_matcher.py
│   ├── test_state_builder.py
│   ├── test_validator.py
│   └── test_engine.py       # 集成测试
└── fixtures/
    └── dummy_detector.onnx  # 自动生成
```

## 15. 实施顺序

按组件逐步集成，每完成一个即可测试：

1. **RecognitionConfig + 类型扩展** — 新增 `CallGroup`, `ActionMatch`，删除 `PlayerScore`，修改 `GameState`（含 frozen），添加 `_resolve_resource_path`
2. **TileDetector** — ONNX 推理 + 假模型（非零输出）+ 坐标转换 + `_assign_to_slot` + `_resolve_rotated_tiles` 测试
3. **TextRecognizer** — 后处理函数 + 字典文件 + PaddleOCR 封装 + mock 测试
4. **PatternMatcher** — 模板匹配 + 假模板测试
5. **GameStateBuilder** — 键名映射 + drawn_tile + 副露解析（含完整 from_player 表）+ 牌河排序构建
6. **Validator** — 手牌校验公式（含杠）+ 赤宝牌计数 + 融合（中心点距离匹配）测试
7. **RecognitionEngine** — 门面 + warmup + context manager + 空输入处理 + 端到端测试

## 16. 已知限制（留待后续）

| 限制 | 计划 |
|------|------|
| 对手副露未识别 | 扩展 zones.yaml 增加 calls_right/opposite/left 区域 |
| PaddlePaddle 重量级依赖 | Plan 2b 用 paddle2onnx 转 ONNX |
| 横置牌检测精度待验证 | 需要真实训练数据验证 rotated 辅助类效果 |
| 帧间融合目标 ID 追踪 | 当前基于中心点距离匹配 |
| 牌河排序方向 | 需对照雀魂实际截图验证左/右家方向 |

## 17. 变更摘要

### v3.0 → v4.0（30 项修复）

| 修复项 | 原问题 | 修复方式 |
|:---:|:---|:---|
| B1 | PlayerScore 删除无迁移路径 | §3.2 列出受影响文件 + 迁移策略 |
| B2 | rotated bbox 覆盖查询未定义 | §5.3 新增 `_resolve_rotated_tiles()` IoU 匹配算法 |
| B3 | pon/kan from_player 用模糊描述 | §8.2 统一映射规则 + kakan 继承 prev_state + 回退策略 |
| B4 | 画布归属算法缺失 | §5.4 新增 `_assign_to_slot()` 中心点归属 + padding 丢弃 |
| B5 | 手牌校验公式含杠错误 | §8.4 `expected_hand = 13 - kan_count` 明确公式 |
| C1 | calls 类型变更无迁移 | §3.2 明确旧类型 `Any` → 新类型 `CallGroup` 无兼容代码 |
| C2 | ZoneName(zone_name) 可能 ValueError | §9.2 try/except 防御性处理 + 警告日志 |
| C3 | scores 键空间不一致 | §8.1 `_ZONE_KEY_MAP` 统一为 "self"/"right"/"opposite"/"left" |
| C4 | 左/右家牌河排序方向 | §8.2 重新标注方向 + 添加"以实际 UI 为准"注释 |
| C5 | IoU 匹配密集场景错配 | §8.5 改用中心点距离匹配 + 同区域独立处理 |
| C6 | 相对路径不一致 | §4.1 `model_path`/`template_dir` 改为 `None` + `_resolve_resource_path()` |
| M1 | 字典键命名空间不统一 | §8.1 `_ZONE_KEY_MAP` + `_zone_key()` 方法 |
| M2 | 假模型输出全零 | §5.5 在 index 0 放置可检测目标 (1m, conf=0.95) |
| M3 | ONNX 输出名不一致 | §5.2 统一为 `output0`（无前导斜杠） |
| M4 | validate() 返回值语义 | §8.3 明确 model_copy + §3.2 GameState frozen |
| M5 | 排序阈值用单个检测高度 | §8.2 `_median_height()`/`_median_width()` |
| M6 | 缺 discards 构建逻辑 | §8.2 新增"牌河构建"章节（5 步流程） |
| M7 | ocr_dicts 打包路径 | §6.5 移入 `src/majsoul_recognizer/ocr_dicts/` + `package-data` |
| M8 | class_map 无 Tile 交叉校验 | §3.3 新增 `test_class_map_covers_all_tiles` |
| m1 | 空 zones 无快速返回 | §9.2 开头 `if not zones` 快速返回 |
| m2 | confidence 参数优先级不明 | §9.2 `confidence = self._config.detection_confidence` 统一传入 |
| m3 | ActionMatch.score 命名 | §3.1 注明与 OpenCV matchTemplate 术语一致 |
| m4 | rotated_index=0 是 falsy | §3.1 文档字符串警告"使用 is not None" |
| m5 | -99999 魔数 | §4.1 注释说明选择理由 |
| m6 | "棒" 关键字范围 | §6.3 注释说明日文不使用，中文版限定 |
| S1 | Detection 与 Tile 枚举关联 | §8.2 使用 `tile_from_str()` 校验 |
| S2 | 上下文管理器 | §9.1 `__enter__`/`__exit__` |
| S3 | detect_batch 单区域优化 | §9.2 `len(tile_images) > 1` 条件分支 |
| S4 | 赤宝牌计数规则 | §8.4 合并 5mr→5m 等映射后统计 |
| S5 | 字典文件每行一字 | §6.5 展示完整每行一字格式 |
