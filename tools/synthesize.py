"""合成训练数据生成器

程序化生成牌面检测训练数据：
1. 生成 40 种牌面模板（白色矩形 + 牌面编码文字）
2. 在随机背景上放置牌面
3. 自动生成 YOLO 格式标注
4. 数据增强（亮度、对比度、模糊、噪声）
"""

import logging
import random
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# 与 tile_detector._DEFAULT_CLASS_MAP 一致的 40 类
CLASS_NAMES = [
    "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
    "1z", "2z", "3z", "4z", "5z", "6z", "7z",
    "5mr", "5pr", "5sr",
    "back", "rotated", "dora_frame",
]

# 牌面类别 → 中文显示名
_DISPLAY_NAMES = {
    **{f"{i}m": f"{i}万" for i in range(1, 10)},
    **{f"{i}p": f"{i}筒" for i in range(1, 10)},
    **{f"{i}s": f"{i}索" for i in range(1, 10)},
    "1z": "东", "2z": "南", "3z": "西", "4z": "北",
    "5z": "白", "6z": "发", "7z": "中",
    "5mr": "赤万", "5pr": "赤筒", "5sr": "赤索",
    "back": "背", "rotated": "横", "dora_frame": "宝",
}

# 赤宝牌颜色
_RED_CLASSES = {"5mr", "5pr", "5sr"}


def generate_tile_template(
    class_name: str,
    width: int = 60,
    height: int = 80,
) -> np.ndarray:
    """生成单个牌面模板图像"""
    if class_name == "back":
        # 牌背：绿色矩形
        img = np.full((height, width, 3), (60, 120, 80), dtype=np.uint8)
        cv2.rectangle(img, (3, 3), (width - 4, height - 4), (40, 80, 60), 2)
        return img

    if class_name == "rotated":
        # 横置标记：窄矩形（模拟 90° 旋转）
        rotated_w, rotated_h = height // 2, width
        img = np.full((rotated_h, rotated_w, 3), (200, 200, 200), dtype=np.uint8)
        text = "横"
        cv2.putText(img, text, (5, rotated_h // 2 + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        return img

    if class_name == "dora_frame":
        # 宝牌指示框：矩形边框
        img = np.full((height, width, 3), (240, 240, 240), dtype=np.uint8)
        cv2.rectangle(img, (2, 2), (width - 3, height - 3), (0, 0, 255), 2)
        return img

    # 正常牌面：白色底 + 编码文字
    img = np.full((height, width, 3), (240, 240, 240), dtype=np.uint8)
    cv2.rectangle(img, (1, 1), (width - 2, height - 2), (180, 180, 180), 1)

    display = _DISPLAY_NAMES.get(class_name, class_name)
    color = (0, 0, 200) if class_name in _RED_CLASSES else (0, 0, 0)

    font_scale = 0.5 if len(display) <= 2 else 0.35
    (tw, th), _ = cv2.getTextSize(display, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
    text_x = (width - tw) // 2
    text_y = (height + th) // 2
    cv2.putText(img, display, (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 1, cv2.LINE_AA)
    return img


def place_tiles(
    background: np.ndarray,
    tiles: list[tuple[str, int, int]],
    tile_w: int = 60,
    tile_h: int = 80,
) -> tuple[np.ndarray, list[tuple[int, float, float, float, float]]]:
    """在背景图上放置牌面，返回图像和 YOLO 标注

    Args:
        background: 背景图像 (H, W, 3)
        tiles: [(class_name, x, y), ...] 牌面类别和位置
        tile_w: 牌面宽度
        tile_h: 牌面高度

    Returns:
        (image, labels): 合成图像和 YOLO 格式标注
    """
    image = background.copy()
    bg_h, bg_w = image.shape[:2]
    labels = []

    for class_name, x, y in tiles:
        template = generate_tile_template(class_name, tile_w, tile_h)
        th, tw = template.shape[:2]

        # 裁剪越界部分
        paste_x = max(0, x)
        paste_y = max(0, y)
        tpl_x = paste_x - x
        tpl_y = paste_y - y
        paste_w = min(tw - tpl_x, bg_w - paste_x)
        paste_h = min(th - tpl_y, bg_h - paste_y)

        if paste_w <= 0 or paste_h <= 0:
            continue

        image[paste_y:paste_y + paste_h, paste_x:paste_x + paste_w] = \
            template[tpl_y:tpl_y + paste_h, tpl_x:tpl_x + paste_w]

        # YOLO 归一化坐标
        cx = (x + tw / 2) / bg_w
        cy = (y + th / 2) / bg_h
        nw = tw / bg_w
        nh = th / bg_h
        cls_id = CLASS_NAMES.index(class_name)
        labels.append((cls_id, cx, cy, nw, nh))

    return image, labels


def _random_background(height: int = 640, width: int = 640) -> np.ndarray:
    """生成随机麻将桌面背景"""
    # 深绿色系背景（模拟牌桌）
    base_g = random.randint(40, 70)
    base_r = random.randint(20, 40)
    base_b = random.randint(30, 50)
    bg = np.full((height, width, 3), (base_b, base_g, base_r), dtype=np.uint8)
    # 添加轻微纹理噪声
    noise = np.random.randint(-5, 6, (height, width, 3), dtype=np.int16)
    bg = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return bg


def _augment_image(image: np.ndarray) -> np.ndarray:
    """数据增强"""
    # 亮度调整 ±15%
    alpha = random.uniform(0.85, 1.15)
    image = np.clip(image.astype(np.float32) * alpha, 0, 255).astype(np.uint8)

    # 对比度调整 ±10%
    beta = random.randint(-15, 15)
    image = np.clip(image.astype(np.int16) + beta, 0, 255).astype(np.uint8)

    # 高斯模糊 (50% 概率)
    if random.random() < 0.5:
        k = random.choice([1, 3])
        image = cv2.GaussianBlur(image, (k, k), 0)

    # JPEG 压缩模拟 (30% 概率)
    if random.random() < 0.3:
        quality = random.randint(70, 95)
        _, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    # 随机噪声
    if random.random() < 0.3:
        sigma = random.randint(5, 15)
        noise = np.random.normal(0, sigma, image.shape).astype(np.int16)
        image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return image


def _generate_single_image(
    image_size: int = 640,
    tiles_per_image: int = 8,
    tile_w: int = 60,
    tile_h: int = 80,
) -> tuple[np.ndarray, list[tuple[int, float, float, float, float]]]:
    """生成单张合成图像+标注"""
    bg = _random_background(image_size, image_size)

    # 随机选择牌面和位置
    num_tiles = random.randint(max(1, tiles_per_image // 2), tiles_per_image)
    tiles = []
    for _ in range(num_tiles):
        cls = random.choice(CLASS_NAMES)
        x = random.randint(0, image_size - tile_w)
        y = random.randint(0, image_size - tile_h)
        tiles.append((cls, x, y))

    image, labels = place_tiles(bg, tiles, tile_w, tile_h)
    image = _augment_image(image)
    return image, labels


def generate_dataset(
    output_dir: Path,
    num_train: int = 100,
    num_val: int = 20,
    tiles_per_image: int = 8,
    seed: int = 42,
) -> None:
    """生成完整数据集

    Args:
        output_dir: 输出目录
        num_train: 训练集数量
        num_val: 验证集数量
        tiles_per_image: 每张图平均牌面数
        seed: 随机种子
    """
    random.seed(seed)
    np.random.seed(seed)

    output_dir = Path(output_dir)

    for split, count in [("train", num_train), ("val", num_val)]:
        img_dir = output_dir / "images" / split
        lbl_dir = output_dir / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for i in range(count):
            image, labels = _generate_single_image(
                tiles_per_image=tiles_per_image,
            )
            img_path = img_dir / f"{split}_{i:04d}.png"
            lbl_path = lbl_dir / f"{split}_{i:04d}.txt"

            cv2.imwrite(str(img_path), image)
            label_lines = [f"{cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}"
                           for cls, xc, yc, w, h in labels]
            lbl_path.write_text("\n".join(label_lines) + "\n")

    logger.info("Generated %d train + %d val images in %s", num_train, num_val, output_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse
    parser = argparse.ArgumentParser(description="生成合成训练数据")
    parser.add_argument("--output", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--num-train", type=int, default=100)
    parser.add_argument("--num-val", type=int, default=20)
    parser.add_argument("--tiles-per-image", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate_dataset(args.output, args.num_train, args.num_val,
                     args.tiles_per_image, args.seed)
