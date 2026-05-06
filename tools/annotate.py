"""真实截图标注工具

使用 OpenCV 模板匹配在截图中自动定位牌面，生成 YOLO 格式标注。

用法:
    # 标注单张图片
    python -m tools.annotate --image screenshot.png --output labels/

    # 批量标注
    python -m tools.annotate --images data/raw/ --output data/real/
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from tools.synthesize import CLASS_NAMES, generate_tile_template

logger = logging.getLogger(__name__)


@dataclass
class Annotation:
    """单个标注结果"""
    class_id: int
    x: int
    y: int
    width: int
    height: int
    confidence: float
    class_name: str

    def to_yolo(self, image_width: int, image_height: int) -> str:
        """转换为 YOLO 归一化格式"""
        cx = (self.x + self.width / 2) / image_width
        cy = (self.y + self.height / 2) / image_height
        w = self.width / image_width
        h = self.height / image_height
        return f"{self.class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def _generate_all_templates(width: int = 60, height: int = 80) -> dict[str, np.ndarray]:
    """生成所有 40 类牌面模板"""
    return {name: generate_tile_template(name, width, height) for name in CLASS_NAMES}


def annotate_image(
    image: np.ndarray,
    templates: dict[str, np.ndarray],
    confidence: float = 0.7,
) -> list[Annotation]:
    """使用模板匹配标注图像中的牌面

    Args:
        image: 输入图像
        templates: {class_name: template_image} 模板字典
        confidence: 匹配置信度阈值

    Returns:
        标注列表
    """
    if image is None or image.size == 0:
        return []

    annotations: list[Annotation] = []
    img_h, img_w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    for class_name, template in templates.items():
        if template is None or template.size == 0:
            continue

        tpl_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        th, tw = tpl_gray.shape[:2]

        if tw > img_w or th > img_h:
            continue

        result = cv2.matchTemplate(gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= confidence)

        for pt in zip(*locations[::-1]):
            score = float(result[pt[1], pt[0]])
            annotations.append(Annotation(
                class_id=CLASS_NAMES.index(class_name),
                x=int(pt[0]),
                y=int(pt[1]),
                width=tw,
                height=th,
                confidence=score,
                class_name=class_name,
            ))

    # NMS：合并重叠标注
    annotations = _nms_annotations(annotations, iou_threshold=0.3)
    return annotations


def _nms_annotations(annotations: list[Annotation], iou_threshold: float) -> list[Annotation]:
    """对标注结果执行 NMS"""
    if not annotations:
        return []

    sorted_anns = sorted(annotations, key=lambda a: a.confidence, reverse=True)
    keep: list[Annotation] = []

    for ann in sorted_anns:
        should_keep = True
        for kept in keep:
            if _compute_iou(ann, kept) > iou_threshold:
                should_keep = False
                break
        if should_keep:
            keep.append(ann)
    return keep


def _compute_iou(a: Annotation, b: Annotation) -> float:
    """计算两个标注的 IoU"""
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.width, b.x + b.width)
    y2 = min(a.y + a.height, b.y + b.height)

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = a.width * a.height + b.width * b.height - intersection
    return intersection / union if union > 0 else 0.0


def annotate_directory(
    image_dir: Path,
    output_dir: Path,
    confidence: float = 0.7,
) -> int:
    """批量标注目录中的图片

    Returns:
        成功标注的图片数量
    """
    image_dir = Path(image_dir)
    output_dir = Path(output_dir)

    img_dir = output_dir / "images"
    lbl_dir = output_dir / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    templates = _generate_all_templates()
    count = 0

    for img_path in sorted(image_dir.glob("*.png")):
        image = cv2.imread(str(img_path))
        if image is None:
            logger.warning("Failed to read: %s", img_path)
            continue

        annotations = annotate_image(image, templates, confidence)
        if not annotations:
            logger.debug("No annotations found: %s", img_path)
            continue

        # 保存图片副本
        import shutil
        shutil.copy(str(img_path), str(img_dir / img_path.name))

        # 保存 YOLO 标注
        lbl_path = lbl_dir / (img_path.stem + ".txt")
        img_h, img_w = image.shape[:2]
        lines = [ann.to_yolo(img_w, img_h) for ann in annotations]
        lbl_path.write_text("\n".join(lines) + "\n")
        count += 1

    logger.info("Annotated %d images from %s", count, image_dir)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse

    parser = argparse.ArgumentParser(description="真实截图标注工具")
    parser.add_argument("--images", type=Path, help="输入图片目录")
    parser.add_argument("--image", type=Path, help="单张输入图片")
    parser.add_argument("--output", type=Path, required=True, help="输出目录")
    parser.add_argument("--confidence", type=float, default=0.7, help="匹配置信度阈值")
    args = parser.parse_args()

    if args.image:
        image = cv2.imread(str(args.image))
        templates = _generate_all_templates()
        annotations = annotate_image(image, templates, args.confidence)
        for ann in annotations:
            print(f"{ann.class_name}: ({ann.x},{ann.y}) {ann.width}x{ann.height} "
                  f"conf={ann.confidence:.3f}")
    elif args.images:
        annotate_directory(args.images, args.output, args.confidence)
    else:
        parser.error("需要 --image 或 --images")
