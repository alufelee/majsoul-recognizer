# 雀魂麻将识别助手 — 识别引擎设计文档 (Plan 2a)

> 版本: 1.0 | 日期: 2026-05-06 | 阶段: 推理引擎代码

## 1. 概述

本设计定义推理引擎的代码框架，包含四个子模块和一个统一门面。模型训练和数据合成在 Plan 2b 中独立执行。

**范围**:
- TileDetector — YOLOv8 ONNX 推理封装
- TextRecognizer — PaddleOCR 文字识别封装
- PatternMatcher — 动作按钮模板匹配
- GameStateBuilder + Validator — 结果组装与规则校验
- RecognitionEngine — 统一门面

**不含**: 合成数据生成、YOLOv8 训练脚本、PaddleOCR 模型训练、真实数据标注。

**测试策略**: 为每个子模块创建假模型/假模板，使测试端到端可运行。

## 2. 架构

```
CapturePipeline.process_image()
    ↓ FrameResult.zones: dict[str, ndarray]
RecognitionEngine.recognize(zones)
    ↓ 按区域名分派
    ├── TileDetector   → hand, dora, discards_*, calls_self
    ├── TextRecognizer → score_*, round_info, timer
    └── PatternMatcher → actions
    ↓
GameStateBuilder.build()
    ↓ 组装为 GameState
Validator.validate()
    ↓ 校验 + 帧间融合
    ↓
FrameResult.game_state: GameState
```

**调用者视角**:
```python
pipeline = CapturePipeline()
engine = RecognitionEngine()

result = pipeline.process_image(screenshot)
if result.is_static:
    state = engine.recognize(result.zones)
    # state: GameState — 完整的游戏状态
```

## 3. 文件结构

```
src/majsoul_recognizer/
├── recognition/
│   ├── __init__.py          # 导出 RecognitionEngine
│   ├── engine.py            # RecognitionEngine 门面
│   ├── tile_detector.py     # TileDetector
│   ├── text_recognizer.py   # TextRecognizer
│   ├── pattern_matcher.py   # PatternMatcher
│   └── state_builder.py     # GameStateBuilder + Validator
├── pipeline.py              # 现有，不变
├── types.py                 # 现有，可能需小扩展
└── ...

tests/
├── recognition/
│   ├── __init__.py
│   ├── test_tile_detector.py
│   ├── test_text_recognizer.py
│   ├── test_pattern_matcher.py
│   ├── test_state_builder.py
│   └── test_engine.py       # 集成测试
└── fixtures/
    ├── dummy_detector.onnx  # 假 ONNX 模型
    ├── templates/            # 假模板图片
    └── tile_mapping.json    # 类别映射配置
```

## 4. TileDetector

### 4.1 接口

```python
class TileDetector:
    """YOLOv8 ONNX 牌面检测器"""

    def __init__(self, model_path: Path | str, mapping_path: Path | str | None = None):
        """
        Args:
            model_path: ONNX 模型文件路径
            mapping_path: 类别映射 JSON 路径，None 则使用默认 40 类
        """

    def detect(self, image: np.ndarray, confidence: float = 0.7) -> list[Detection]:
        """
        Args:
            image: BGR 格式区域图像
            confidence: 最低置信度阈值

        Returns:
            检测到的牌面列表，每个包含 bbox, tile_code, confidence
        """
```

### 4.2 内部流程

```
输入图像 → letterbox resize (640x640) → 归一化 (0-1, NCHW)
    → ONNX Runtime 推理 → NMS 后处理
    → 类别 ID 映射为 tile_code → 过滤低置信度
    → 输出 list[Detection]
```

### 4.3 类别映射

`tile_mapping.json` 定义 ONNX 输出类别 ID 到 tile_code 的映射：

```json
{
  "0": "1m", "1": "2m", ..., "8": "9m",
  "9": "1p", ..., "17": "9p",
  "18": "1s", ..., "26": "9s",
  "27": "1z", ..., "33": "7z",
  "34": "5mr", "35": "5pr", "36": "5sr",
  "37": "back", "38": "rotated", "39": "dora_frame"
}
```

### 4.4 假模型

测试时生成 `dummy_detector.onnx`：一个 640x640 输入的随机权重 ONNX 模型。推理结果不可靠但能跑通完整流程，验证接口和数据流正确性。

## 5. TextRecognizer

### 5.1 接口

```python
class TextRecognizer:
    """文字识别器 (PaddleOCR 封装)"""

    def __init__(self):
        """初始化 PaddleOCR 引擎"""

    def recognize_score(self, image: np.ndarray) -> int | None:
        """识别分数区域，返回整数分数"""

    def recognize_round(self, image: np.ndarray) -> RoundInfo | None:
        """识别局次信息"""

    def recognize_timer(self, image: np.ndarray) -> int | None:
        """识别倒计时"""
```

### 5.2 内部流程

```
输入图像 → 预处理 (灰度 + 二值化) → PaddleOCR 推理
    → 字符白名单过滤 → 后处理 (去逗号、中文数字映射)
    → 类型转换 → 返回结构化结果
```

### 5.3 字符白名单

| 方法 | 白名单 | 后处理 |
|------|--------|--------|
| `recognize_score` | `[0-9,]` | 去逗号 → int |
| `recognize_round` | `[东南西北一二三四局0-9本]` | 解析风/局数/本场 |
| `recognize_timer` | `[0-9]` | → int |

### 5.4 测试策略

PaddleOCR 依赖较重且在 CI 环境不一定可用。测试采用双层策略：
- **单元测试**: mock PaddleOCR 返回，测试后处理逻辑（去逗号、中文映射、异常值过滤）
- **集成测试**: 在有 PaddleOCR 的环境中可选运行

## 6. PatternMatcher

### 6.1 接口

```python
class PatternMatcher:
    """动作按钮模板匹配"""

    def __init__(self, template_dir: Path):
        """
        Args:
            template_dir: 模板图片目录，包含 chi.png, pon.png, kan.png 等文件
        """

    def match(self, image: np.ndarray, threshold: float = 0.85) -> list[str]:
        """
        Args:
            image: actions 区域图像
            threshold: 匹配阈值 (0-1)

        Returns:
            匹配到的动作名称列表，如 ["碰", "荣和", "过"]
        """
```

### 6.2 内部流程

```
输入图像 → 遍历所有模板 → cv2.matchTemplate (TM_CCOEFF_NORMED)
    → 阈值过滤 → 收集匹配结果
    → 输出动作名称列表
```

### 6.3 模板文件

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

### 6.4 测试策略

测试时生成纯色矩形 + 文字标注的假模板图片。在 actions 区域图像上放置已知的按钮图案，验证匹配结果。

## 7. GameStateBuilder + Validator

### 7.1 GameStateBuilder 接口

```python
class GameStateBuilder:
    """将子模块原始结果组装为 GameState"""

    def build(
        self,
        detections: dict[str, list[Detection]],
        scores: dict[str, int],
        round_info: RoundInfo | None,
        timer: int | None,
        actions: list[str],
    ) -> GameState:
        """
        Args:
            detections: 按区域名分组的检测结果
            scores: 按玩家分组的分数
            round_info: 局次信息
            timer: 倒计时
            actions: 可用动作列表

        Returns:
            完整的 GameState 实例
        """
```

### 7.2 构建逻辑

```
detections["hand"] → 手牌排序 → state.hand
detections["hand"] 最后一张(有间隔) → state.drawn_tile
detections["dora"] → state.dora_indicators
detections["discards_*"] → state.discards
detections["calls_self"] → state.calls
scores → state.scores
round_info → state.round_info
timer → state.timer_remaining
actions → state.actions
```

### 7.3 Validator 接口

```python
class Validator:
    """规则校验与帧间融合"""

    def validate(self, current: GameState, previous: GameState | None = None) -> GameState:
        """校验当前状态，添加 warnings"""

    def fuse(self, window: list[GameState]) -> GameState:
        """多帧融合（3 帧滑动窗口，多数投票）"""
```

### 7.4 校验规则

| 规则 | 说明 |
|------|------|
| 手牌数量 | hand + drawn_tile 数量与副露数匹配 |
| 牌数上限 | 同一 tile_code 全场最多 4 张 |
| 牌河连续性 | 每帧每家最多新增 1 张弃牌 |
| 分数合理性 | 0 <= score <= 200000 |

### 7.5 帧间融合

```
维护最近 3 帧 GameState
对每个检测目标:
  - 类别: 3 帧中出现最多的（多数投票）
  - 置信度: 3 帧平均值
  - 不一致时标记 unstable warning
```

## 8. RecognitionEngine 门面

### 8.1 接口

```python
class RecognitionEngine:
    """识别引擎统一入口"""

    def __init__(
        self,
        model_path: Path | str | None = None,
        mapping_path: Path | str | None = None,
        template_dir: Path | str | None = None,
    ):
        """
        Args:
            model_path: ONNX 模型路径，None 使用默认
            mapping_path: 类别映射路径，None 使用默认
            template_dir: 模板目录路径，None 使用默认
        """

    def recognize(self, zones: dict[str, np.ndarray]) -> GameState:
        """
        识别完整的游戏状态

        Args:
            zones: 区域图像字典（来自 CapturePipeline.process_image().zones）

        Returns:
            完整的 GameState
        """
```

### 8.2 分派逻辑

```python
def recognize(self, zones):
    # 1. 牌面检测
    tile_zones = ["hand", "dora", "discards_self", "discards_right",
                  "discards_opposite", "discards_left", "calls_self"]
    detections = {}
    for zone_name in tile_zones:
        if zone_name in zones:
            detections[zone_name] = self._detector.detect(zones[zone_name])

    # 2. 文字识别
    scores = {}
    for prefix in ["score_self", "score_right", "score_opposite", "score_left"]:
        if prefix in zones:
            scores[prefix] = self._ocr.recognize_score(zones[prefix])

    round_info = self._ocr.recognize_round(zones.get("round_info"))
    timer = self._ocr.recognize_timer(zones.get("timer"))

    # 3. 模板匹配
    actions = self._matcher.match(zones.get("actions", np.array([])))

    # 4. 组装 + 校验
    state = self._builder.build(detections, scores, round_info, timer, actions)
    state = self._validator.validate(state, self._prev_state)
    self._prev_state = state
    return state
```

## 9. 依赖新增

```toml
[project.optional-dependencies]
# 新增识别引擎依赖
recognition = [
    "onnxruntime>=1.16",
    "paddleocr>=2.7",
    "paddlepaddle>=2.5",
]
```

## 10. 实施顺序

按组件逐步集成，每完成一个即可测试：

1. **TileDetector** — ONNX 推理封装 + 假模型测试
2. **TextRecognizer** — PaddleOCR 封装 + 后处理测试（mock）
3. **PatternMatcher** — 模板匹配 + 假模板测试
4. **GameStateBuilder + Validator** — 结果组装 + 规则校验
5. **RecognitionEngine** — 门面集成 + 端到端测试

每个组件完成后独立测试，最后通过 RecognitionEngine 集成。
