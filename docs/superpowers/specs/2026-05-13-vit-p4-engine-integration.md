# ViT 集成 P4: 引擎集成

## 目标

将 TileClassifier 集成到 RecognitionEngine，在 YOLO 检测后用 ViT 重新分类所有检测结果。

## 设计

### RecognitionConfig 扩展

在 `config.py` 中新增字段：

```python
# TileClassifier (ViT)
vit_model_name: str = "pjura/mahjong_soul_vision"
enable_vit_classifier: bool = True
vit_classifier_threshold: float = 0.5
vit_device: str | None = None  # None=auto, "cpu", "cuda"
```

### RecognitionEngine 修改

#### `__init__` 新增

```python
self._classifier: TileClassifier | None = None
self._classifier_attempted: bool = False
```

#### `_ensure_classifier()` 方法

```python
def _ensure_classifier(self):
    if self._classifier is not None:
        return self._classifier
    if not self._config.enable_vit_classifier:
        return None
    if self._classifier_attempted:
        return None
    self._classifier_attempted = True
    try:
        from majsoul_recognizer.recognition.tile_classifier import TileClassifier
        self._classifier = TileClassifier(self._config.vit_model_name)
        logger.info("ViT classifier loaded")
    except ImportError:
        logger.debug("ViT classifier unavailable (torch/transformers not installed)")
    except Exception as e:
        logger.warning("ViT classifier init failed: %s", e)
    return self._classifier
```

仅尝试一次，失败不重试。区分 `ImportError`（依赖缺失）和其他 `Exception`（模型损坏等），日志级别不同。

#### `recognize()` ViT 分类步骤

在 YOLO 检测完成后、zone_name 赋值前插入：

```python
# 初始化 scaled_rects（全图模式在 if 分支填充，区域模式为空）
scaled_rects: dict[str, tuple[int, int, int, int]] = {}

if use_full_image:
    # ... 现有代码填充 scaled_rects ...
    detections = detector.detect_full_image(full_image, scaled_rects, confidence)
else:
    # ... 现有代码 ...
    detections = {name: detector.detect(img, confidence) ...}

# === ViT 二次分类（新增） ===
classifier = self._ensure_classifier()
if classifier is not None and detections:
    for zone_name, dets in detections.items():
        if not dets:
            continue
        # 确定裁剪源和偏移
        if scaled_rects and zone_name in scaled_rects:
            source = full_image
            ox, oy = scaled_rects[zone_name][0], scaled_rects[zone_name][1]
        elif zone_name in zones:
            source = zones[zone_name]
            ox, oy = 0, 0
        else:
            continue
        # 裁剪（使用 model_copy 因为 Detection 是 frozen）
        crops = [
            source[
                max(0, oy + d.bbox.y):min(source.shape[0], oy + d.bbox.y + d.bbox.height),
                max(0, ox + d.bbox.x):min(source.shape[1], ox + d.bbox.x + d.bbox.width),
            ]
            for d in dets
        ]
        vit_results = classifier.classify_batch(crops)
        for i, (tile_code, conf) in enumerate(vit_results):
            if tile_code and conf >= self._config.vit_classifier_threshold:
                dets[i] = dets[i].model_copy(update={
                    "tile_code": tile_code,
                    "confidence": conf,
                })
```

#### 坐标系统说明

**全图模式**: `detect_full_image` 返回区域相对坐标。ViT 裁剪时用 `zone_offset + local_coord` 还原为全局坐标。

**已知边界情况**: `ultralytics_detector.py:130` 中 `max(0, local_x)` 的 clamp 使转换有损（最多偏移 bbox 的一半宽度）。实际影响极小——仅发生在区域边界，且 ViTImageProcessor 会 resize 到 224x224 归一化掉微小偏移。若后续需要像素级精确裁剪，可修改 `detect_full_image` 保留原始全局坐标。

**区域模式**: 检测结果已是区域图内坐标，直接从 `zones[name]` 裁剪，无坐标转换问题。

#### `__exit__` 和 `reset` 修改

```python
def __exit__(self, *args):
    self._detector = None
    self._ocr = None
    self._matcher = None
    self._classifier = None
    self._classifier_attempted = False  # 允许重新初始化
    self._validator.reset()

def reset(self):
    """重置引擎状态（不重载模型）"""
    self._validator.reset()
```

`reset()` 不重置 classifier — 模型加载昂贵，状态验证逻辑不依赖分类器状态。

### 降级行为

- ViT 不可用（`_ensure_classifier` 返回 None）→ 跳过 ViT，保留 YOLO 结果
- ViT 置信度 < `vit_classifier_threshold` → 保留 YOLO tile_code
- ViT 返回 `("", 0.0)`（无效 crop）→ 保留 YOLO tile_code
- 仅在首次调用时打印一次 warning，后续静默跳过

## 文件

- 修改: `src/majsoul_recognizer/recognition/config.py`（+3 字段）
- 修改: `src/majsoul_recognizer/recognition/engine.py`（+_ensure_classifier, recognize 中插入 ViT 步骤, __exit__ 修改）
- 修改: `tests/recognition/test_config.py`（新字段默认值测试）
- 修改: `tests/recognition/test_engine.py`（ViT 集成测试）
- 修改: `tests/recognition/conftest.py`（mock_vit_classifier fixture）

## 测试用例

### test_config.py 新增

1. `test_vit_config_defaults` — `enable_vit_classifier=True`, `vit_classifier_threshold=0.5`, `vit_model_name` 默认值
2. `test_vit_config_custom` — 自定义值正确设置

### test_engine.py 新增

3. **ViT 区域模式重分类** — mock classifier 返回不同 tile_code，验证 Detection 的 tile_code 被替换
4. **ViT 全图模式重分类** — 同上但走 full_image 路径
5. **ViT 置信度低于阈值** — ViT 返回低置信度，验证保留 YOLO 结果
6. **ViT 不可用时降级** — `_ensure_classifier` 返回 None，验证不崩溃且 YOLO 结果完整
7. **`_classifier_attempted` 阻止重复初始化** — 多次 `recognize()` 调用只触发一次 `_ensure_classifier`
8. **`__exit__` 重置状态** — 退出 context manager 后 `_classifier` 和 `_classifier_attempted` 被清除

### conftest.py 新增

```python
@pytest.fixture
def mock_vit_classifier():
    from unittest.mock import MagicMock
    classifier = MagicMock()
    classifier.classify_batch.return_value = [("9s", 0.99)]
    return classifier
```

## 验收

- 默认配置启用 ViT，但 ViT 不可用时优雅降级（仅一次 debug 日志）
- ViT 可用时，检测结果 tile_code 被 ViT 结果替换（使用 `model_copy`）
- ViT 置信度低于阈值时保留 YOLO 结果
- 已有测试全部通过（无回归）
- 所有 8 个新增测试用例通过
