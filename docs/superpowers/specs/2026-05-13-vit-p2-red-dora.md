# ViT 集成 P2: 赤宝牌颜色检测

## 目标

在 ViT 分类结果为 5m/5p/5s 时，通过颜色分析判断是否为赤宝牌版本（5mr/5pr/5sr）。

## 背景

pjura 模型只有 34 类标准牌面，不含赤宝牌。赤宝牌在雀魂画面中有明显的红色标记，可通过 HSV 颜色空间检测。

**调用条件**: 仅当 ViT 输出为 `5m`/`5p`/`5s` 时调用，不会对 7z（中牌，也是红色）误触发。

## 设计

### 函数签名

```python
def _is_red_dora(
    crop: np.ndarray,
    tile_code: str,
    threshold: float | None = None,
) -> bool:
```

- `crop`: YOLO bbox 裁剪的原始 BGR 图像（未经 ViT 预处理）
- `tile_code`: ViT 分类结果（`"5m"`/`"5p"`/`"5s"`），用于按花色选择阈值
- `threshold`: 显式阈值覆盖，None 时使用花色默认阈值

### 花色差异化阈值

三种赤宝牌的红色面积差异大，使用按花色区分的阈值：

| 花色 | 默认阈值 | 依据 |
|------|---------|------|
| `5m`（万子/红"五"字） | 0.08 | 红色笔画面积最小 |
| `5p`（筒子/红圆点） | 0.12 | 红色圆点面积中等 |
| `5s`（索子/红竹子） | 0.15 | 红色竹子面积最大 |

**注意**: 这些阈值需要在实现阶段用真实游戏截图标定（见验收条件）。此处为初始值，标注为待标定。

### HSV 检测算法

```python
_PER_SUIT_THRESHOLD = {"5m": 0.08, "5p": 0.12, "5s": 0.15}

def _is_red_dora(crop, tile_code, threshold=None):
    if crop is None or crop.size == 0:
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    # 红色在 HSV 中跨越 0/180 边界，需两个范围
    mask_lo = cv2.inRange(hsv, np.array([0, 120, 120]), np.array([10, 255, 255]))
    mask_hi = cv2.inRange(hsv, np.array([170, 120, 120]), np.array([180, 255, 255]))
    red_mask = mask_lo | mask_hi
    total_pixels = crop.shape[0] * crop.shape[1]
    red_ratio = cv2.countNonZero(red_mask) / total_pixels
    thresh = threshold or _PER_SUIT_THRESHOLD.get(tile_code, 0.10)
    return red_ratio > thresh
```

### 关键设计决策

1. **S/V 下限从 100 提高到 120** — 过滤压缩伪影和暖色阴影中的低饱和度红色
2. **输入为原始 BGR crop** — 不使用 ViT 预处理后的图像（归一化会改变颜色分布）
3. **背景污染** — YOLO bbox 裁剪包含绿色桌布背景，会稀释红色占比。阈值已针对含背景的 crop 校准。若后续发现 bbox 过大导致阈值不准，可在 crop 前做前景分割

### 7z（中牌）安全分析

7z 的"中"字也是红色。但 `_is_red_dora` 仅在 ViT 输出 `5m`/`5p`/`5s` 时调用，不会被 7z 触发。即使 ViT 将 7z 误分类为 5m（极端情况），颜色分析会返回 True（因为确实有红色），产生 5mr 而非 7z。这种降级可接受——后续帧融合和规则校验（GameState Validator 会检测到不合法的牌数）可纠正。

## 文件

- 修改: `src/majsoul_recognizer/recognition/tile_classifier.py`
- 测试: `tests/recognition/test_tile_classifier.py`

## 验收

- 纯红色图像 → `True`
- 纯蓝色/绿色图像 → `False`
- `None` 或空数组 → `False`
- 合成 5mr 图像（红色"五"字笔画 + 白色牌面 + 绿色背景，红色占比 ~10%）→ `True`
- 合成普通 5m 图像（蓝色笔画 + 白色牌面 + 绿色背景）→ `False`
- 不同花色使用不同阈值（`_PER_SUIT_THRESHOLD`）
- `tile_code` 不在 `{"5m", "5p", "5s"}` 时不崩溃
- **待标定**: 实现阶段需用 ≥20 张真实游戏截图（含红/非红各半）验证阈值
