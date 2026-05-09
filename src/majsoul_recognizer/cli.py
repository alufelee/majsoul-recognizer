"""命令行入口

提供端到端的截图 → 区域分割 → 保存流水线。
支持两种模式:
  1. 实时截取: finder → capture → pipeline → save
  2. 离线处理: 从已有截图文件 → pipeline → save
"""

import argparse
import json as _json
import logging
import sys
from pathlib import Path

import cv2
import numpy as np

from majsoul_recognizer.capture.finder import create_finder
from majsoul_recognizer.capture.screenshot import create_capture
from majsoul_recognizer.pipeline import CapturePipeline
from majsoul_recognizer.types import FrameResult, GameState

logger = logging.getLogger(__name__)


def build_capture_chain(config_path: str | Path | None = None) -> CapturePipeline:
    """构建截图处理流水线

    Args:
        config_path: 区域配置文件路径，默认使用内置配置

    Returns:
        配置好的 CapturePipeline 实例
    """
    return CapturePipeline(config_path=config_path)


def capture_and_save(
    image: np.ndarray,
    output_dir: Path,
    pipeline: CapturePipeline | None = None,
) -> Path:
    """将图像分割为区域并保存到磁盘

    Args:
        image: BGR 格式的游戏截图
        output_dir: 输出目录
        pipeline: 流水线实例，None 则自动创建

    Returns:
        输出目录路径
    """
    if pipeline is None:
        pipeline = build_capture_chain()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = pipeline.process_image(image)

    if not result.is_static:
        logger.warning("Frame is not static, zones may be empty")

    for zone_name, zone_img in result.zones.items():
        filename = f"{zone_name}.png"
        filepath = output_dir / filename
        cv2.imwrite(str(filepath), zone_img)
        logger.info(f"Saved {zone_name}: {zone_img.shape}")

    return output_dir


def capture_from_screen(output_dir: Path, config_path: str | None = None) -> bool:
    """从屏幕截取雀魂窗口并分割保存

    Args:
        output_dir: 输出目录
        config_path: 区域配置文件路径

    Returns:
        True 成功，False 失败（窗口未找到等）
    """
    finder = create_finder()
    window = finder.find_window()

    if window is None:
        logger.error("Mahjong Soul window not found. Is the game running?")
        return False

    logger.info(f"Found window: {window.title} ({window.width}x{window.height})")

    with create_capture() as capture:
        image = capture.capture_window(window)

    if image is None:
        logger.error("Failed to capture window screenshot")
        return False

    logger.info(f"Captured screenshot: {image.shape}")
    output = capture_and_save(image, output_dir, build_capture_chain(config_path))
    logger.info(f"Zones saved to: {output}")
    return True


def format_output(frame: FrameResult, state: GameState | None) -> dict:
    """将 FrameResult + GameState 转换为产品规格书 §3 格式的 dict

    Args:
        frame: 帧处理结果
        state: 识别结果，None 表示非静态帧（跳过识别）

    Returns:
        可被 json.dumps 序列化的 dict
    """
    if state is None:
        return {
            "frame_id": frame.frame_id,
            "timestamp": frame.timestamp,
            "is_static": False,
            "round": None,
            "dora_indicators": [],
            "scores": {},
            "hand": [],
            "drawn_tile": None,
            "calls": {},
            "discards": {},
            "actions": [],
            "timer": None,
            "warnings": ["frame_not_static"],
        }

    timer = None
    if state.timer_remaining is not None:
        timer = {"active": True, "remaining": state.timer_remaining}

    return {
        "frame_id": frame.frame_id,
        "timestamp": frame.timestamp,
        "is_static": True,
        "round": state.round_info.model_dump() if state.round_info else None,
        "dora_indicators": state.dora_indicators,
        "scores": state.scores,
        "hand": state.hand,
        "drawn_tile": state.drawn_tile,
        "calls": {k: [c.model_dump() for c in v] for k, v in state.calls.items()},
        "discards": state.discards,
        "actions": state.actions,
        "timer": timer,
        "warnings": state.warnings,
    }


def recognize_command(argv: list[str] | None = None) -> None:
    """recognize 子命令: 截图 → 识别 → JSON

    Args:
        argv: 命令行参数，None 时从 sys.argv 读取
    """
    # 抑制非关键日志输出到 stderr（设计规格 §4.6）
    logging.getLogger("majsoul_recognizer").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(
        prog="majsoul-recognizer recognize",
        description="识别截图中的游戏状态并输出 JSON",
    )
    parser.add_argument("-i", "--image", required=True, help="输入截图文件路径")
    parser.add_argument("--config", default=None, help="区域配置文件路径")
    parser.add_argument("--model", default=None, help="ONNX 模型文件路径")
    parser.add_argument("--template-dir", default=None, help="动作按钮模板目录")

    args = parser.parse_args(argv)

    # 1. 读取图片
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Cannot read image: {args.image}", file=sys.stderr)
        raise SystemExit(1)

    # 2. 构建 RecognitionConfig
    try:
        from majsoul_recognizer.recognition import RecognitionConfig
        config_kwargs = {}
        if args.model:
            model_path = Path(args.model)
            if not model_path.exists():
                print(f"Error: Model file not found: {model_path}", file=sys.stderr)
                raise SystemExit(1)
            config_kwargs["model_path"] = model_path
        if args.template_dir:
            config_kwargs["template_dir"] = Path(args.template_dir)
        config = RecognitionConfig(**config_kwargs)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: Failed to create config: {e}", file=sys.stderr)
        raise SystemExit(1)

    # 3. 构建 Pipeline + Engine
    try:
        from majsoul_recognizer.recognition import RecognitionEngine
        pipeline = build_capture_chain(args.config)
        engine = RecognitionEngine(config)
    except Exception as e:
        print(f"Error: Initialization failed: {e}", file=sys.stderr)
        raise SystemExit(1)

    # 4. 处理帧
    try:
        frame = pipeline.process_image(image)
    except Exception as e:
        print(f"Error: Pipeline failed: {e}", file=sys.stderr)
        raise SystemExit(1)

    # 5. 识别（仅静态帧）
    state = None
    if frame.is_static:
        try:
            state = engine.recognize(frame.zones)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            raise SystemExit(1)
        except Exception as e:
            print(f"Error: Recognition failed: {e}", file=sys.stderr)
            raise SystemExit(1)

    # 6. 输出 JSON
    output = format_output(frame, state)
    print(_json.dumps(output, ensure_ascii=False, indent=2))
    raise SystemExit(0)


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="majsoul-recognizer",
        description="雀魂麻将画面识别助手 — 基础架构",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # capture 命令: 实时截取游戏画面并分割
    cap_parser = subparsers.add_parser("capture", help="截取雀魂窗口并分割区域")
    cap_parser.add_argument(
        "-o", "--output", default="./output/zones",
        help="输出目录 (默认: ./output/zones)",
    )
    cap_parser.add_argument(
        "--config", default=None,
        help="区域配置文件路径",
    )

    # split 命令: 从已有截图文件分割
    split_parser = subparsers.add_parser("split", help="从截图文件分割区域")
    split_parser.add_argument("image", help="截图文件路径")
    split_parser.add_argument(
        "-o", "--output", default="./output/zones",
        help="输出目录 (默认: ./output/zones)",
    )
    split_parser.add_argument(
        "--config", default=None,
        help="区域配置文件路径",
    )

    # calibrate 命令: 校准区域坐标
    cal_parser = subparsers.add_parser("calibrate", help="校准区域坐标")
    cal_parser.add_argument("--screenshot", required=True, help="雀魂游戏截图路径")
    cal_parser.add_argument("--config", default=None, help="区域配置文件路径")
    cal_parser.add_argument("--output", default=None, help="标注图输出路径")

    # recognize 命令: 识别截图并输出 JSON
    rec_parser = subparsers.add_parser("recognize", help="识别截图中的游戏状态")
    rec_parser.add_argument("-i", "--image", required=True, help="输入截图文件路径")
    rec_parser.add_argument("--config", default=None, help="区域配置文件路径")
    rec_parser.add_argument("--model", default=None, help="ONNX 模型文件路径")
    rec_parser.add_argument("--template-dir", default=None, help="动作按钮模板目录")

    # gui 命令: 启动图形界面
    subparsers.add_parser("gui", help="启动图形界面")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.command == "capture":
        success = capture_from_screen(Path(args.output), args.config)
        sys.exit(0 if success else 1)

    elif args.command == "split":
        image = cv2.imread(args.image)
        if image is None:
            logger.error(f"Cannot read image: {args.image}")
            sys.exit(1)
        output = capture_and_save(image, Path(args.output), build_capture_chain(args.config))
        logger.info(f"Zones saved to: {output}")

    elif args.command == "calibrate":
        from majsoul_recognizer.calibrate import calibrate
        calibrate(args.screenshot, args.config, args.output)

    elif args.command == "recognize":
        recognize_command([
            "--image", args.image,
            *([] if args.config is None else ["--config", args.config]),
            *([] if args.model is None else ["--model", args.model]),
            *([] if args.template_dir is None else ["--template-dir", args.template_dir]),
        ])

    elif args.command == "gui":
        from majsoul_recognizer.gui import main
        main()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
