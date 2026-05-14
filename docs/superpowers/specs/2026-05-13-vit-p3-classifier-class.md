# ViT 集成 P3: TileClassifier 分类器类

## 目标

实现 `TileClassifier` 类，封装 ViT 模型推理，提供单张和批量牌面分类接口。

## 背景

基于 `pjura/mahjong_soul_vision`（ViTForImageClassification，google/vit-base-patch16-224-in21k），输入 224x224 裁剪图，输出 tile_code + confidence。ViT 模型 ~340MB (float32)。

## 设计

### 初始化与依赖检测

```python
try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

try:
    from transformers import ViTForImageClassification, ViTImageProcessor
    _HAS_TRANSFORMERS = True
except ImportError:
    _HAS_TRANSFORMERS = False
```

模块级 import 检测，与 engine.py 的 `_HAS_ORT`/`_HAS_ULTRALYTICS` 模式一致。

### 构造函数

```python
class TileClassifier:
    def __init__(self, model_name_or_path: str):
        if not _HAS_TORCH or not _HAS_TRANSFORMERS:
            raise ImportError(
                "TileClassifier requires torch and transformers. "
                "Install with: pip install torch transformers"
            )
        self._model = ViTForImageClassification.from_pretrained(model_name_or_path)
        self._processor = ViTImageProcessor.from_pretrained(model_name_or_path)
        self._model.eval()
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        logger.info(
            "TileClassifier loaded from %s (device=%s)", model_name_or_path, self._device
        )
        # 运行时标签验证（P1）
        self._validate_labels()
```

**关键点**:
- `model_name_or_path` 既支持 HuggingFace hub 名称（`"pjura/mahjong_soul_vision"`）也支持本地目录路径，遵循 `transformers` 的 `from_pretrained` 约定
- `model.eval()` — 推理模式，禁用 dropout
- 设备自动选择 CUDA/CPU，通过 `RecognitionConfig` 可覆盖
- 构造时执行标签映射验证（P1 的运行时校验）

### 分类接口

```python
def classify(self, crop: np.ndarray) -> tuple[str, float]:
    """单张分类 → (tile_code, confidence)"""
    results = self.classify_batch([crop])
    return results[0]

def classify_batch(self, crops: list[np.ndarray]) -> list[tuple[str, float]]:
    """批量分类"""
```

**返回类型**: `tuple[str, float]` 而非 `Detection`。理由：TileClassifier 只负责分类，不涉及 bbox 定位，返回 Detection 会要求伪造 bbox 数据。引擎层将 `(tile_code, conf)` 通过 `model_copy(update={...})` 合并到现有 Detection 中。

### classify_batch 实现要点

```python
def classify_batch(self, crops):
    if not crops:
        return []

    results = [("", 0.0)] * len(crops)
    valid = [(i, c) for i, c in enumerate(crops)
             if c is not None and hasattr(c, "size") and c.size > 0]
    if not valid:
        return results

    try:
        images = [c for _, c in valid]
        inputs = self._processor(images=images, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)

        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        confs, preds = probs.max(dim=-1)

        for (orig_idx, crop), pred, conf in zip(valid, preds, confs):
            pjura_label = self._model.config.id2label[pred.item()]
            tile_code = _PJURA_TO_TILE_CODE.get(pjura_label, pjura_label)
            if tile_code == pjura_label and pjura_label not in _PJURA_TO_TILE_CODE:
                logger.warning("Unknown pjura label: %s", pjura_label)
            # 赤宝牌检测（P2）
            if tile_code in ("5m", "5p", "5s") and _is_red_dora(crop, tile_code):
                tile_code = tile_code + "r"
            results[orig_idx] = (tile_code, round(conf.item(), 4))

    except Exception as e:
        logger.warning("ViT batch inference failed: %s", e)

    return results
```

**要点**:
- `torch.no_grad()` — 推理必须，避免构建计算图
- inputs 移到设备（CPU 或 CUDA）
- 异常时返回部分结果（已分类的保留，未分类的为 `("", 0.0)`）
- `ViTImageProcessor` 内部处理 resize 到 224x224 + normalize，无需手动预处理
- 赤宝牌检测使用原始 BGR crop（未经 ViT 预处理）

### 日志

- `INFO`: 模型加载成功（含设备信息）
- `WARNING`: 推理失败、未知标签
- `DEBUG`: 每次推理的耗时

### 内存与性能

- ViT-base ~340MB (float32)，可通过 `model.half()` 降至 ~170MB (float16)，CPU 上精度影响可忽略
- 批量 50 张推理：CPU ~500ms-2s，CUDA ~50-100ms
- 输入 tensor 每张 ~600KB (224x224x3 float32)，50 张 ~30MB

## 文件

- 修改: `src/majsoul_recognizer/recognition/tile_classifier.py`
- 测试: `tests/recognition/test_tile_classifier.py`

## 测试策略

### 不依赖 torch/transformers 的测试（纯逻辑）
- 标签映射正确性（P1 的验收条件）
- `_is_red_dora` 颜色检测（P2 的验收条件）

### Mock 模型的测试

构造 `TileClassifier` 实例但不调用 `__init__`，手动注入 mock 属性：

```python
classifier = TileClassifier.__new__(TileClassifier)
classifier._model = MagicMock()
classifier._processor = MagicMock()
classifier._model.config.id2label = {0: "1b", ..., 33: "ww"}  # 完整 34 类
```

测试场景：
1. `classify_batch` 正确映射 pjura 标签到 tile_code
2. `classify_batch` 空列表 → `[]`
3. `classify_batch` 含 None/空数组 → `("", 0.0)` 占位
4. `classify` 委托到 `classify_batch`
5. 推理异常 → 返回部分结果，不崩溃
6. 5m/5p/5s + 红色图像 → 5mr/5pr/5sr（赤宝牌检测集成）

### 集成测试（需要 torch/transformers）

标记 `@pytest.mark.skipif(not _HAS_TORCH, ...)` ，用真实模型 + 合成图像验证端到端流程。不在 CI 中强制运行。
