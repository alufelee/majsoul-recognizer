# ViT 集成 P1: 标签映射

## 目标

建立 pjura/mahjong_soul_vision 模型 34 类标签到项目标准 tile_code 的映射字典。

## 背景

pjura 模型使用自定义标签命名（`1b`-`9b` 索子、`1n`-`9n` 万子、`1p`-`9p` 筒子、`ew/sw/ww/nw` 风牌、`wd/gd/rd` 三元牌），项目使用 `1m-9m`、`1p-9p`、`1s-9s`、`1z-7z`。

映射路径：模型输出 int class index → `model.config.id2label[int]` 得到 pjura 字符串标签 → `_PJURA_TO_TILE_CODE[label]` 得到项目 tile_code。

## 设计

在 `tile_classifier.py` 中定义模块级常量 `_PJURA_TO_TILE_CODE: dict[str, str]`：

- `1b`-`9b` → `1s`-`9s`（索子）
- `1n`-`9n` → `1m`-`9m`（万子）
- `1p`-`9p` → `1p`-`9p`（筒子，直接对应）
- `ew` → `1z`, `sw` → `2z`, `ww` → `3z`, `nw` → `4z`（风牌）
- `wd` → `5z`, `gd` → `6z`, `rd` → `7z`（三元牌）

共 34 条映射。

### 未知标签处理

查找使用 `dict.get()` 而非 `dict[]`，未知标签回退为原始标签字符串并记录 warning 日志：

```python
tile_code = _PJURA_TO_TILE_CODE.get(pjura_label, pjura_label)
if tile_code == pjura_label and pjura_label not in _PJURA_TO_TILE_CODE:
    logger.warning("Unknown pjura label: %s", pjura_label)
```

与 `tile_detector.py` 的 `self.class_map.get(class_id, f"unknown_{class_id}")` 模式一致。

### 运行时验证

`TileClassifier.__init__` 加载模型后，校验映射表完整性：

```python
model_labels = set(self._model.config.id2label.values())
mapped_labels = set(_PJURA_TO_TILE_CODE.keys())
if model_labels != mapped_labels:
    missing = model_labels - mapped_labels
    extra = mapped_labels - model_labels
    logger.warning(
        "Label mapping mismatch: missing=%s extra=%s", missing, extra
    )
```

不抛异常（映射表可能滞后于模型更新），仅记录 warning。

### 与现有模式的区别

`_DEFAULT_CLASS_MAP`（`tile_detector.py`）映射 `int → str`（YOLO class index → tile_code），`_PJURA_TO_TILE_CODE` 映射 `str → str`（pjura label → tile_code）。两者类型不同是因为 YOLO 使用整数 class ID，ViT/pjura 使用字符串 label。

## 文件

- 创建: `src/majsoul_recognizer/recognition/tile_classifier.py`
- 测试: `tests/recognition/test_tile_classifier.py`

## 验收

- 所有 34 个 pjura 标签都能映射到有效的 tile_code
- 映射后的 tile_code 都存在于 `Tile` 枚举中
- 映射是双射（无重复 value）
- 未知标签返回原始字符串并记录 warning
- `__init__` 执行运行时验证校验标签一致性
