"""从 HuggingFace 数据集生成真实牌面检测训练数据

1. 下载 pjura/mahjong_souls_tiles 数据集（单张牌面分类图）
2. 将 HF 标签映射到项目 40 类
3. 在随机背景上放置真实牌面图片，生成 YOLO 检测标注
4. 对缺失类别（赤宝牌、牌背、横置、宝牌框）用合成模板补充
"""

import logging
import random
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# 项目 40 类
CLASS_NAMES = [
    "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
    "1z", "2z", "3z", "4z", "5z", "6z", "7z",
    "5mr", "5pr", "5sr",
    "back", "rotated", "dora_frame",
]

# HF 标签名 → 项目类名映射
_HF_LABEL_MAP = {
    "1n": "1m", "2n": "2m", "3n": "3m", "4n": "4m", "5n": "5m",
    "6n": "6m", "7n": "7m", "8n": "8m", "9n": "9m",
    "1p": "1p", "2p": "2p", "3p": "3p", "4p": "4p", "5p": "5p",
    "6p": "6p", "7p": "7p", "8p": "8p", "9p": "9p",
    "1b": "1s", "2b": "2s", "3b": "3s", "4b": "4s", "5b": "5s",
    "6b": "6s", "7b": "7s", "8b": "8s", "9b": "9s",
    "ew": "1z", "sw": "2z", "ww": "3z", "nw": "4z",
    "wd": "5z", "gd": "6z", "rd": "7z",
}

_DISPLAY_NAMES = {
    **{f"{i}m": f"{i}万" for i in range(1, 10)},
    **{f"{i}p": f"{i}筒" for i in range(1, 10)},
    **{f"{i}s": f"{i}索" for i in range(1, 10)},
    "1z": "东", "2z": "南", "3z": "西", "4z": "北",
    "5z": "白", "6z": "发", "7z": "中",
    "5mr": "赤万", "5pr": "赤筒", "5sr": "赤索",
    "back": "背", "rotated": "横", "dora_frame": "宝",
}

_RED_CLASSES = {"5mr", "5pr", "5sr"}


def download_hf_dataset():
    """下载 HuggingFace 数据集，返回按类名分组的牌面图像列表"""
    from datasets import load_dataset

    ds = load_dataset("pjura/mahjong_souls_tiles")
    class_names = ds["train"].features["label"].names

    tile_images = {}  # class_name -> [np.ndarray, ...]
    for split_name in ["train", "test"]:
        split = ds[split_name]
        for item in split:
            hf_label = class_names[item["label"]]
            our_class = _HF_LABEL_MAP.get(hf_label)
            if our_class is None:
                continue
            img = np.array(item["image"])
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            elif img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            tile_images.setdefault(our_class, []).append(img)

    logger.info("Downloaded HF dataset: %d classes, %d total images",
                len(tile_images), sum(len(v) for v in tile_images.values()))
    return tile_images


def generate_synthetic_template(class_name: str, width: int = 60, height: int = 80) -> np.ndarray:
    """生成合成牌面模板（用于缺失类别）"""
    if class_name == "back":
        img = np.full((height, width, 3), (60, 120, 80), dtype=np.uint8)
        cv2.rectangle(img, (3, 3), (width - 4, height - 4), (40, 80, 60), 2)
        return img
    if class_name == "rotated":
        rotated_w, rotated_h = height // 2, width
        img = np.full((rotated_h, rotated_w, 3), (200, 200, 200), dtype=np.uint8)
        cv2.putText(img, "横", (5, rotated_h // 2 + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        return img
    if class_name == "dora_frame":
        img = np.full((height, width, 3), (240, 240, 240), dtype=np.uint8)
        cv2.rectangle(img, (2, 2), (width - 3, height - 3), (0, 0, 255), 2)
        return img
    # 正常牌面
    img = np.full((height, width, 3), (240, 240, 240), dtype=np.uint8)
    cv2.rectangle(img, (1, 1), (width - 2, height - 2), (180, 180, 180), 1)
    display = _DISPLAY_NAMES.get(class_name, class_name)
    color = (0, 0, 200) if class_name in _RED_CLASSES else (0, 0, 0)
    font_scale = 0.5 if len(display) <= 2 else 0.35
    (tw, th), _ = cv2.getTextSize(display, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
    cv2.putText(img, display, ((width - tw) // 2, (height + th) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 1, cv2.LINE_AA)
    return img


def resize_tile(img: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
    """缩放牌面图像到目标尺寸"""
    return cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_AREA)


def _random_background(height: int = 640, width: int = 640) -> np.ndarray:
    """生成随机麻将桌面背景"""
    base_g = random.randint(40, 70)
    base_r = random.randint(20, 40)
    base_b = random.randint(30, 50)
    bg = np.full((height, width, 3), (base_b, base_g, base_r), dtype=np.uint8)
    noise = np.random.randint(-5, 6, (height, width, 3), dtype=np.int16)
    bg = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return bg


def _augment_image(image: np.ndarray) -> np.ndarray:
    """数据增强"""
    alpha = random.uniform(0.85, 1.15)
    image = np.clip(image.astype(np.float32) * alpha, 0, 255).astype(np.uint8)
    beta = random.randint(-15, 15)
    image = np.clip(image.astype(np.int16) + beta, 0, 255).astype(np.uint8)
    if random.random() < 0.5:
        k = random.choice([1, 3])
        image = cv2.GaussianBlur(image, (k, k), 0)
    if random.random() < 0.3:
        quality = random.randint(70, 95)
        _, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if random.random() < 0.3:
        sigma = random.randint(5, 15)
        noise = np.random.normal(0, sigma, image.shape).astype(np.int16)
        image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return image


def generate_detection_dataset(
    output_dir: Path,
    tile_images: dict[str, list[np.ndarray]],
    num_train: int = 2000,
    num_val: int = 400,
    tiles_per_image: int = 8,
    seed: int = 42,
):
    """用真实牌面图片生成检测训练数据集"""
    random.seed(seed)
    np.random.seed(seed)

    # 确保所有 40 类都有图像
    all_tiles = {}
    for cls in CLASS_NAMES:
        if cls in tile_images and tile_images[cls]:
            all_tiles[cls] = tile_images[cls]
        else:
            # 用合成模板补充缺失类别
            template = generate_synthetic_template(cls)
            all_tiles[cls] = [template]
            logger.info("Using synthetic template for missing class: %s", cls)

    output_dir = Path(output_dir)
    tile_w, tile_h = 60, 80

    for split, count in [("train", num_train), ("val", num_val)]:
        img_dir = output_dir / "images" / split
        lbl_dir = output_dir / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for i in range(count):
            bg = _random_background()
            num_tiles = random.randint(max(1, tiles_per_image // 2), tiles_per_image)
            tiles = []
            for _ in range(num_tiles):
                cls = random.choice(CLASS_NAMES)
                x = random.randint(0, 640 - tile_w)
                y = random.randint(0, 640 - tile_h)
                tiles.append((cls, x, y))

            image = bg.copy()
            labels = []
            for cls, x, y in tiles:
                src_img = random.choice(all_tiles[cls])
                tile_img = resize_tile(src_img, tile_w, tile_h)
                # 随机微小变换
                dx = random.randint(-2, 2)
                dy = random.randint(-2, 2)
                px, py = max(0, x + dx), max(0, y + dy)
                # 确保不越界
                paste_h = min(tile_h, 640 - py)
                paste_w = min(tile_w, 640 - px)
                if paste_h <= 0 or paste_w <= 0:
                    continue
                image[py:py + paste_h, px:px + paste_w] = tile_img[:paste_h, :paste_w]

                cx = (px + tile_w / 2) / 640
                cy = (py + tile_h / 2) / 640
                nw = tile_w / 640
                nh = tile_h / 640
                cls_id = CLASS_NAMES.index(cls)
                labels.append(f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

            image = _augment_image(image)
            img_path = img_dir / f"{split}_{i:04d}.png"
            lbl_path = lbl_dir / f"{split}_{i:04d}.txt"
            cv2.imwrite(str(img_path), image)
            lbl_path.write_text("\n".join(labels) + "\n")

    logger.info("Generated %d train + %d val detection images in %s",
                num_train, num_val, output_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse

    parser = argparse.ArgumentParser(description="从 HF 数据集生成检测训练数据")
    parser.add_argument("--output", type=Path, default=Path("data/real"))
    parser.add_argument("--num-train", type=int, default=2000)
    parser.add_argument("--num-val", type=int, default=400)
    parser.add_argument("--tiles-per-image", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    tile_images = download_hf_dataset()
    generate_detection_dataset(
        args.output, tile_images,
        args.num_train, args.num_val,
        args.tiles_per_image, args.seed,
    )
