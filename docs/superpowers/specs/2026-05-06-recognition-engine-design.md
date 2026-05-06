# 雀魂麻将识别助手 — 识别引擎设计文档 (Plan 2a)

> 版本: 2.0 | 日期: 2026-05-06 | 阶段: 推理引擎代码

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
    ├── [多区域拼接] → TileDetector.detect_batch() → list[list[Detection]]
    ├── TextRecognizer.recognize_score/round/timer → 分数/局次/倒计时
    └── PatternMatcher.match() → list[ActionMatch]
    ↓
GameStateBuilder.build()
    ↓ 组装为 GameState（含 drawn_tile 间隔检测、手牌排序、副露解析）
Validator.validate()
    ↓ 规则校验 + Detection 级帧间融合
    ↓
GameState
```

## 3. 类型扩展

### 3.1 新增类型（加入 `types.py`）

```python
class CallGroup(BaseModel):
    """一组副露（吃/碰/杠）"""
    model_config = {"frozen": True}
    type: str                              # "chi" | "pon" | "kan" | "ankan" | "kakan"
    tiles: list[str]                       # 组成牌面编码列表
    rotated_index: int | None = None       # 横置牌在 tiles 中的索引（指示来源）
    from_player: str | None = None         # "right" | "opposite" | "left"

class ActionMatch(BaseModel):
    """动作按钮匹配结果"""
    model_config = {"frozen": True}
    name: str                              # 动作名称（"吃"/"碰"/"杠"等）
    score: float = Field(ge=0.0, le=1.0)  # 匹配分数
```

### 3.2 修改现有类型

**`GameState.scores`**: 从 `dict[str, int | PlayerScore]` 改为 `dict[str, int]`，与产品规格输出格式一致。排名信息不在识别范围内。

**`GameState.calls`**: 从 `dict[str, list[Any]]` 改为 `dict[str, list[CallGroup]]`，明确副露结构。

**`GameState.timer_remaining`**: 保留 `int | None`。`None` 表示非自己回合（倒计时不可见），非 None 表示倒计时可见。

## 4. 配置管理

### 4.1 RecognitionConfig

```python
class RecognitionConfig(BaseModel):
    """识别引擎可调参数"""
    # TileDetector
    model_path: Path = Path("models/current/tile_detector.onnx")
    mapping_path: Path | None = None       # None 使用内置默认映射
    nms_iou_threshold: float = 0.45
    detection_confidence: float = 0.7

    # TextRecognizer
    ocr_model_dir: Path | None = None      # None 使用 paddleocr 默认路径

    # PatternMatcher
    template_dir: Path = Path("templates/")

    # Validator
    score_min: int = 0
    score_max: int = 200000
    fusion_window_size: int = 3

    # 性能
    enable_batch_detection: bool = True    # 多区域拼接优化
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
```

## 5. TileDetector

### 5.1 接口

```python
class TileDetector:
    """YOLOv8 ONNX 牌面检测器"""

    def __init__(self, model_path: Path | str,
                 class_map: dict[int, str] | None = None,
                 nms_iou: float = 0.45):
        """
        Args:
            model_path: ONNX 模型文件路径
            class_map: 类别 ID → tile_code 映射，None 使用 _DEFAULT_CLASS_MAP
            nms_iou: NMS IoU 阈值
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

        将多个区域图像拼接到一张 640x640 画布上，只做一次 ONNX 前向传播，
        然后按位置归属拆分结果。每个区域在画布上有固定位置和足够的间距避免跨区域误检。
        """
```

### 5.2 ONNX 模型规格

**导出参数**: `yolo export model=best.pt format=onnx imgsz=640 simplify=True`
- 非端到端导出（不含内置 NMS），需自行实现后处理

**输入**: `images` — shape `(1, 3, 640, 640)`, dtype `float32`, 值域 `[0, 1]`

**输出**: `/output0` — shape `(1, 44, 8400)` 其中 44 = 4(bbox) + 40(classes)

**NMS 后处理**:
1. 转置输出为 `(8400, 44)`
2. 取前 4 列为 bbox (cx, cy, w, h)，后 40 列为类别分数
3. 每行取 max class score，若 >= confidence 阈值则保留
4. 对保留的检测做 NMS（IoU 阈值 `nms_iou`）
5. 将 bbox 从 letterbox 坐标还原到原图坐标
6. 类别 ID 通过 class_map 映射为 tile_code

### 5.3 类别处理策略

40 类中 37 类对应 `Tile` 枚举值，另外 3 类为辅助类别：

| 类别 | tile_code | 处理方式 |
|------|-----------|----------|
| 0-36 | `1m`-`5sr` | 正常牌面，进入 GameState |
| 37 | `back` | 仅计数，用于检测对手暗杠中的暗牌。不进入 hand/discards/calls 的牌面列表，仅在 `GameState.warnings` 中记录 `"opponent_back_tiles: N"` |
| 38 | `rotated` | 不作为独立检测结果。检测到 `rotated` 时，取其 bbox 覆盖范围内置信度最高的牌面检测作为横置牌。在 `CallGroup.rotated_index` 中记录位置 |
| 39 | `dora_frame` | 仅用于辅助定位宝牌区域边界，不进入 GameState |

### 5.4 假模型生成

使用 `onnx` 库生成 `tests/fixtures/dummy_detector.onnx`：

```python
import onnx
from onnx import helper, TensorProto

def create_dummy_detector(path: str):
    """生成 640x640 输入的随机权重 ONNX 模型"""
    # 输入: (1, 3, 640, 640) float32
    # 输出: (1, 44, 8400) float32 — 40 类 + 4 bbox
    X = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])
    Y = helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 44, 8400])
    # Conv + shape 调整节点（最小可行图）
    ...
```

测试 conftest 中调用此函数自动生成假模型。

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

**`recognize_score`**: 去逗号 → `int()` → 校验 `[score_min, score_max]` → 越界返回 None

**`recognize_round`**: OCR 原始文本示例 `"东一局 0 本场"`，解析算法：
1. 遍历字符匹配风：`东` 或 `南` → `wind`
2. 匹配局数：`一/二/三/四` → 映射 `1/2/3/4` → `number`
3. 找数字 + `"本"` 前的数字 → `honba`
4. 找 `"供托"` 或 `"棒"` 前的数字 → `kyotaku`（若不可见则为 0）

若 `wind` 或 `number` 缺失，返回 None。

**`recognize_timer`**: 纯数字 → `int()`。图像面积过小（区域不可见）时直接返回 None。

### 6.4 测试策略

双层测试：
- **单元测试**: 不加载 PaddleOCR，直接构造 `recognize_score("25,000") → 25000` 等后处理函数，覆盖正常/异常/边界值
- **集成测试**: 标记 `@pytest.mark.skipif("not ocr_available")`，需要 PaddleOCR 安装

### 6.5 PaddleOCR 调用方式

```python
from paddleocr import PaddleOCR

self._ocr = PaddleOCR(
    use_angle_cls=False,      # 不做文字方向分类
    lang="ch",                # 中文
    use_gpu=False,            # CPU 推理
    det_model_dir=...,        # 文本检测模型路径
    rec_model_dir=...,        # 文本识别模型路径
    rec_char_dict_path=...,   # 自定义字符字典（限定字符集）
    show_log=False,
)
```

字符白名单通过 PaddleOCR 的自定义字典文件实现，每个识别场景使用不同的字典文件。

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

    def build(
        self,
        detections: dict[str, list[Detection]],
        scores: dict[str, int | None],
        round_info: RoundInfo | None,
        timer: int | None,
        actions: list[ActionMatch],
    ) -> GameState:
        """
        Args:
            detections: 按区域名分组的检测结果
            scores: 按区域名分组的分数（可能含 None）
            round_info: 局次信息
            timer: 倒计时秒数
            actions: 匹配到的动作列表

        Returns:
            完整的 GameState 实例
        """
```

### 8.2 构建逻辑详解

**手牌排序**: `state.hand` 按 Detection 的 bbox.x 坐标（视觉位置）从左到右排序。保持视觉顺序而非 tile_code 字典序，因为 drawn_tile 检测依赖位置。

**drawn_tile 间隔检测算法**:
1. 将 `detections["hand"]` 按 bbox.x 排序
2. 计算相邻 Detection 的 bbox 间距：`gap[i] = dets[i+1].bbox.x - (dets[i].bbox.x + dets[i].bbox.width)`
3. 计算间距中位数 `median_gap`
4. 若某个间距 `gap[i] > median_gap * 2.5`，则 `dets[i+1:]` 为 drawn_tile 及其之后的新牌
5. 特殊处理：手牌总数 <= 1 时无间隔可计算，此时若检测到 14 张则最后一张为 drawn_tile

**副露解析** (`calls_self`):
1. 按 bbox.x 排序所有 Detection
2. 每组吃/碰/杠占 3-4 张牌，通过间距分组
3. 检查组内是否有 "rotated" 辅助检测结果覆盖的牌面 → 设 `rotated_index`
4. 根据 `rotated_index` 推断 `from_player`（横放位置编码来源玩家）

**对手副露**: 当前 `zones.yaml` 无对手副露区域。对手副露位于各家牌河附近，需要从牌河区域中分离。Plan 2a 中对手副露暂不处理，在 `GameState.calls` 中只填充 `self`。后续通过扩展 `zones.yaml` 增加 `calls_right`/`calls_opposite`/`calls_left` 区域来支持。

**牌河排序**:
- 自家 (`discards_self`): 按 bbox.x 从左到右，然后按行从上到下
- 对家 (`discards_opposite`): 同自家
- 左/右家 (`discards_left`/`discards_right`): 按 bbox.y 从上到下，然后按列从左到右

**分数 None 处理**: `scores` 中 `None` 值表示该区域识别失败，不写入 `GameState.scores`。

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
        """校验当前状态，添加 warnings，更新内部 prev_state"""

    def reset(self):
        """重置历史状态（对局结束时调用）"""

    @property
    def prev_state(self) -> GameState | None:
        """供 GameStateBuilder 使用的上一帧状态"""
```

Validator 内部管理 `prev_state` 和检测窗口。`RecognitionEngine` 不再维护状态历史。

### 8.4 校验规则

| 规则 | 说明 | warning key |
|------|------|-------------|
| 手牌数量 | `len(hand) + (1 if drawn_tile else 0) + calls_melds * 3` 应为 13（含杠调整） | `hand_count_mismatch` |
| 牌数上限 | 同一 tile_code 全场（hand+discards+calls+dora）最多 4 张 | `tile_overflow` |
| 牌河连续性 | 每帧每家 discards 最多比上帧多 1 张 | `discard_jump` |
| 分数合理性 | `score_min <= score <= score_max` | `score_anomaly` |

### 8.5 Detection 级帧间融合

融合在 Detection 层面进行（在 `GameStateBuilder.build()` 之前），而非 GameState 层面：

```python
def fuse_detections(self, current: dict[str, list[Detection]]) -> dict[str, list[Detection]]:
    """
    对每个区域的检测结果做帧间融合

    算法：
    1. 维护最近 N 帧（默认 3）的 detections 滑动窗口
    2. 对当前帧的每个 Detection，在历史帧中按 bbox IoU > 0.5 匹配对应目标
    3. 对匹配到的目标组：
       - tile_code: 取出现次数最多的（多数投票）
       - confidence: 取平均值
       - 若 3 帧不一致，在返回的 Detection 中标记（通过 confidence 降低）
    4. 历史帧中有但当前帧没有的目标：保留（可能是暂时遮挡）
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
            zones: 区域图像字典（来自 CapturePipeline.process_image().zones）
                   键为 ZoneName.value 字符串，值为 BGR ndarray

        Returns:
            完整的 GameState
        """

    def reset(self):
        """重置引擎状态（对局结束时调用）"""
```

### 9.2 分派逻辑

```python
def recognize(self, zones: dict[str, np.ndarray]) -> GameState:
    logger.info("Recognition started, %d zones received", len(zones))

    # 1. 牌面检测（多区域拼接优化）
    tile_zone_names = ["hand", "dora", "discards_self", "discards_right",
                       "discards_opposite", "discards_left", "calls_self"]
    tile_images = [(name, zones[name]) for name in tile_zone_names if name in zones]

    if self._config.enable_batch_detection and len(tile_images) > 1:
        detections = self._detector.detect_batch(tile_images)
    else:
        detections = {name: self._detector.detect(img) for name, img in tile_images}

    # 设置 Detection.zone_name
    for zone_name, dets in detections.items():
        for i in range(len(dets)):
            dets[i] = dets[i].model_copy(update={"zone_name": ZoneName(zone_name)})

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
    state = self._builder.build(detections, scores, round_info, timer, actions)
    state = self._validator.validate(state)

    logger.info("Recognition done: hand=%d, warnings=%d",
                len(state.hand), len(state.warnings))
    return state
```

### 9.3 None 值统一处理

所有子模块方法在 `image` 为 None 或 size==0 时返回空结果（不抛异常）：
- `TileDetector.detect(None)` → `[]`
- `TextRecognizer.recognize_*(None)` → `None`
- `PatternMatcher.match(None)` → `[]`

分派逻辑在调用前做 `in zones and zones[x].size > 0` 检查。

## 10. 日志策略

每个子模块使用 `logger = logging.getLogger(__name__)`，关键路径记录：

| 模块 | 日志点 | 级别 |
|------|--------|------|
| TileDetector | 推理耗时、检测数量、置信度分布 | DEBUG |
| TileDetector | 模型加载成功/失败 | INFO/WARNING |
| TextRecognizer | OCR 原始文本、后处理结果 | DEBUG |
| TextRecognizer | 识别失败 | WARNING |
| PatternMatcher | 各模板匹配分数 | DEBUG |
| GameStateBuilder | drawn_tile 检测结果、手牌数量 | DEBUG |
| Validator | 校验 warning 详情 | WARNING |
| RecognitionEngine | 开始/完成/总耗时 | INFO |
| RecognitionEngine | 降级决策 | WARNING |

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

每个子模块用 `time.perf_counter()` 测量耗时并记入日志。无超时强制机制——若单帧超时，日志 WARNING 提醒但不中断。

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

## 13. 依赖新增

```toml
[project.optional-dependencies]
recognition = [
    "onnxruntime>=1.16",
]
recognition-ocr = [
    "paddleocr>=2.7",
    "paddlepaddle>=2.5",     # 仅训练/OCR 推理时需要
]
```

**OCR 依赖策略**: `onnxruntime` 为核心依赖。PaddlePaddle 作为可选依赖——TextRecognizer 支持在没有 PaddleOCR 的环境中降级运行（所有方法返回 None）。后续 Plan 2b 中可用 `paddle2onnx` 将 PaddleOCR 模型转为 ONNX，统一用 `onnxruntime` 推理，彻底移除 PaddlePaddle 运行时依赖。

ONNX Runtime Provider 选择：
```python
providers = []
if "CoreMLExecutionProvider" in ort.get_available_providers():
    providers.append("CoreMLExecutionProvider")  # macOS 加速
if "CUDAExecutionProvider" in ort.get_available_providers():
    providers.append("CUDAExecutionProvider")
providers.append("CPUExecutionProvider")  # 始终作为 fallback
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
├── types.py                 # 新增 CallGroup, ActionMatch; 修改 GameState 字段
└── ...

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

1. **RecognitionConfig + 类型扩展** — 新增 `CallGroup`, `ActionMatch`，修改 `GameState`
2. **TileDetector** — ONNX 推理封装 + 假模型生成 + 单区域测试 + 批量检测测试
3. **TextRecognizer** — 后处理函数 + PaddleOCR 封装 + mock 测试
4. **PatternMatcher** — 模板匹配 + 假模板测试
5. **GameStateBuilder** — 结果组装 + drawn_tile 间隔检测 + 排序测试
6. **Validator** — 规则校验 + Detection 级帧间融合测试
7. **RecognitionEngine** — 门面集成 + 端到端测试

每个组件完成后独立测试，最后通过 RecognitionEngine 集成。

## 16. 已知限制（留待后续）

| 限制 | 计划 |
|------|------|
| 对手副露未识别 | 扩展 zones.yaml 增加 calls_right/opposite/left 区域 |
| PaddlePaddle 重量级依赖 | Plan 2b 用 paddle2onnx 转 ONNX |
| 横置牌检测精度待验证 | 需要真实训练数据验证 rotated 辅助类效果 |
| 帧间融合的目标 ID 追踪 | 当前基于 IoU 匹配，可能需要更稳健的追踪算法 |
