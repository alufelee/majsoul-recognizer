# ViT 分类器集成设计

## 背景

当前 pipeline 使用 YOLO (MajsoulBot YOLOv11n) 同时做牌面定位和分类，但分类质量不稳定：
- 牌面标签错误（如 1s 识别为 1m）
- 牌河区域漏检
- 副露区域检测不稳定
- 宝牌指示器识别差

参考模型 [pjura/mahjong_soul_vision](https://huggingface.co/pjura/mahjong_soul_vision) 是基于 ViT 的单牌分类器，99.67% 准确率。

## 方案

**YOLO 定位 + ViT 分类**：两阶段 pipeline，YOLO 只负责定位（bbox），ViT 负责精确分类。

## 架构

```
游戏截图
  ↓
[Zone Splitter] → 裁剪 14 个区域
  ↓
[YOLO Detector] → 全图检测，获取每张牌的 bbox
  ↓
[Crop Extractor] → 根据 bbox 从原图裁剪每张牌的小图
  ↓
[ViT Classifier] → 批量分类，替换 YOLO 的 tile_code
  ↓
[State Builder + Validator] → 组装 GameState (不变)
```

## 模块设计

### TileClassifier (`recognition/tile_classifier.py`)

- 加载 `pjura/mahjong_soul_vision` (ViTForImageClassification)
- `ViTImageProcessor` 处理 resize 到 224x224 + normalize
- `classify(crop) -> (tile_code, confidence)` — 单张分类
- `classify_batch(crops) -> list[(tile_code, confidence)]` — 批量分类

### 标签映射

pjura 模型 34 类 → 项目标准编码：

| pjura | 项目编码 | 说明 |
|-------|---------|------|
| `1b`-`9b` | `1s`-`9s` | 索子 |
| `1n`-`9n` | `1m`-`9m` | 万子 |
| `1p`-`9p` | `1p`-`9p` | 筒子 |
| `ew` | `1z` | 东 |
| `sw` | `2z` | 南 |
| `ww` | `3z` | 西 |
| `nw` | `4z` | 北 |
| `wd` | `5z` | 白 |
| `gd` | `6z` | 发 |
| `rd` | `7z` | 中 |

### RecognitionEngine 修改

在 `recognize()` 方法中，YOLO 检测后插入 ViT 分类：
1. YOLO 检测 → 获取所有 Detection（含 bbox）
2. 从原图裁剪每张检测到的牌
3. 批量送入 ViT 分类
4. 用 ViT 结果替换 Detection 的 tile_code 和 confidence
5. 后续状态组装逻辑不变

### RecognitionConfig 扩展

- `enable_vit_classifier: bool = True`
- `vit_classifier_threshold: float = 0.5`
- `vit_model_name: str = "pjura/mahjong_soul_vision"`

## 赤宝牌处理

ViT 模型只有 34 类，不含赤宝牌 (5mr/5pr/5sr)。策略：
1. ViT 分类结果如果是 5m/5p/5s，额外做颜色分析
2. HSV 空间检测红色区域占比
3. 红色占比超阈值（~10%）则标记为赤宝牌

## 降级策略

- ViT 不可用 → 回退到纯 YOLO 分类
- ViT 置信度低于阈值 → 用 YOLO 分类结果
- YOLO 未检测到牌 → 不送 ViT

## 性能

- YOLO 推理: ~50ms
- ViT 批量分类（~60 张）: ~100-150ms
- OCR + 状态组装: ~50ms
- 总计: ~200-300ms/帧，满足 1fps 需求

## 依赖

- `torch` (PyTorch)
- `transformers>=4.34` (HuggingFace Transformers)

模型首次运行自动从 HuggingFace 下载并缓存到 `~/.cache/huggingface/`。
