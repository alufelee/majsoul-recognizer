# 雀魂麻将识别助手 — Plan 3: 集成验证实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 CapturePipeline 与 RecognitionEngine 集成为端到端流水线，提供 `recognize` CLI 命令和 JSON 输出，并通过集成测试验证整条链路。

**Architecture:** CLI 读取截图 → CapturePipeline 分割区域 → 帧状态检测 → RecognitionEngine 识别 → 输出适配层转换为产品规格书 §3 格式 → JSON 输出到 stdout。非静态帧跳过识别直接降级输出。

**Tech Stack:** Python 3.10+, OpenCV, NumPy, Pydantic v2, pytest, argparse, subprocess (CLI 测试)

---

## 文件结构

本计划涉及的文件：

```
majong/
├── pyproject.toml                              # [修改] 添加 [project.scripts]
├── src/majsoul_recognizer/
│   └── cli.py                                  # [修改] 添加 recognize 子命令 + format_output()
├── tests/
│   ├── test_cli.py                             # [修改] 添加 recognize 命令测试
│   └── test_integration.py                     # [新建] 端到端集成测试
```

---

## Task 1: 输出适配层 `format_output()`

**Files:**
- Modify: `src/majsoul_recognizer/cli.py`
- Test: `tests/test_cli.py`

`format_output()` 是纯函数，将 `FrameResult` + `GameState | None` 转换为产品规格书 §3 定义的 dict。独立于 CLI 子命令实现，便于单独测试。

- [ ] **Step 1: 编写 `format_output` 测试**

在 `tests/test_cli.py` 末尾追加：

```python
import json

from majsoul_recognizer.types import FrameResult, GameState, RoundInfo
from majsoul_recognizer.cli import format_output


class TestFormatOutput:
    """输出适配层测试"""

    def test_static_frame_with_empty_state(self):
        """静态帧 + 空 GameState → 完整 JSON 结构"""
        frame = FrameResult(frame_id=1, timestamp="2026-05-07T10:00:00+00:00")
        state = GameState()
        result = format_output(frame, state)

        assert result["frame_id"] == 1
        assert result["timestamp"] == "2026-05-07T10:00:00+00:00"
        assert result["is_static"] is True
        assert result["round"] is None
        assert result["dora_indicators"] == []
        assert result["hand"] == []
        assert result["timer"] is None
        assert result["warnings"] == []

    def test_static_frame_with_data(self):
        """静态帧 + 有数据的 GameState → 正确映射"""
        frame = FrameResult(frame_id=3, timestamp="2026-05-07T10:00:01+00:00")
        state = GameState(
            round_info=RoundInfo(wind="东", number=2, honba=1, kyotaku=0),
            dora_indicators=["5m"],
            scores={"self": 25000, "right": 23000},
            hand=["1m", "2m", "3m"],
            drawn_tile="东",
            timer_remaining=8,
            warnings=["some_warning"],
        )
        result = format_output(frame, state)

        assert result["is_static"] is True
        assert result["round"] == {"wind": "东", "number": 2, "honba": 1, "kyotaku": 0}
        assert result["dora_indicators"] == ["5m"]
        assert result["scores"] == {"self": 25000, "right": 23000}
        assert result["hand"] == ["1m", "2m", "3m"]
        assert result["drawn_tile"] == "东"
        assert result["timer"] == {"active": True, "remaining": 8}
        assert result["warnings"] == ["some_warning"]

    def test_non_static_frame(self):
        """非静态帧 → state=None → 所有识别字段为空"""
        frame = FrameResult(
            frame_id=2, timestamp="2026-05-07T10:00:00+00:00", is_static=False
        )
        result = format_output(frame, None)

        assert result["is_static"] is False
        assert result["round"] is None
        assert result["hand"] == []
        assert result["timer"] is None
        assert result["warnings"] == ["frame_not_static"]

    def test_timer_none(self):
        """timer_remaining=None → timer=null"""
        frame = FrameResult(frame_id=1, timestamp="t")
        state = GameState(timer_remaining=None)
        result = format_output(frame, state)
        assert result["timer"] is None

    def test_timer_with_value(self):
        """timer_remaining=5 → timer={"active": true, "remaining": 5}"""
        frame = FrameResult(frame_id=1, timestamp="t")
        state = GameState(timer_remaining=5)
        result = format_output(frame, state)
        assert result["timer"] == {"active": True, "remaining": 5}

    def test_no_round_info_key_name(self):
        """输出不含 round_info 键（应为 round）"""
        frame = FrameResult(frame_id=1, timestamp="t")
        state = GameState(round_info=RoundInfo(wind="南", number=3, honba=0, kyotaku=2))
        result = format_output(frame, state)
        assert "round_info" not in result
        assert "round" in result
        assert result["round"]["wind"] == "南"

    def test_json_serializable(self):
        """输出可被 json.dumps 序列化"""
        frame = FrameResult(frame_id=1, timestamp="t")
        state = GameState(
            hand=["1m", "2m"],
            scores={"self": 25000},
            timer_remaining=10,
        )
        result = format_output(frame, state)
        serialized = json.dumps(result, ensure_ascii=False)
        assert '"round": null' in serialized
        assert '"timer": {"active": true, "remaining": 10}' in serialized
```

- [ ] **Step 2: 运行测试确认失败**

```bash
.venv/bin/python -m pytest tests/test_cli.py::TestFormatOutput -v
```
Expected: FAILED — `ImportError: cannot import name 'format_output'`

- [ ] **Step 3: 实现 `format_output()`**

在 `src/majsoul_recognizer/cli.py` 中，在 `main()` 函数之前追加：

```python
import json as _json

from majsoul_recognizer.types import FrameResult, GameState


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
```

同时在文件顶部追加导入：

```python
import json as _json

from majsoul_recognizer.types import FrameResult, GameState
```

- [ ] **Step 4: 运行测试确认通过**

```bash
.venv/bin/python -m pytest tests/test_cli.py::TestFormatOutput -v
```
Expected: 7 passed

- [ ] **Step 5: 运行全部已有测试确认无回归**

```bash
.venv/bin/python -m pytest tests/test_cli.py -v
```
Expected: 所有测试 PASS（原有 + 新增 7 个）

- [ ] **Step 6: 提交**

```bash
git add src/majsoul_recognizer/cli.py tests/test_cli.py
git commit -m "feat: add format_output() adapter for product spec §3 JSON format"
```

---

## Task 2: `recognize` CLI 子命令

**Files:**
- Modify: `src/majsoul_recognizer/cli.py` (追加 `recognize_command()` 和子命令注册)
- Modify: `tests/test_cli.py` (追加 CLI 调用测试)

- [ ] **Step 1: 编写 `recognize` 命令测试**

在 `tests/test_cli.py` 末尾追加：

```python
import subprocess
import sys
import tempfile

import cv2
import numpy as np
import pytest

from majsoul_recognizer.cli import recognize_command

# 检测 onnxruntime 是否可用
try:
    import onnxruntime  # noqa: F401
    _HAS_ORT = True
except ImportError:
    _HAS_ORT = False

_SKIP_ORT = pytest.mark.skipif(not _HAS_ORT, reason="onnxruntime not installed")


class TestRecognizeCommand:
    """recognize CLI 子命令测试"""

    def test_file_not_found(self):
        """图片路径无效 → 退出码 1"""
        with pytest.raises(SystemExit) as exc_info:
            recognize_command(["--image", "/nonexistent/path/screenshot.png"])
        assert exc_info.value.code == 1

    def test_invalid_image_format(self, tmp_path):
        """非图片文件 → 退出码 1"""
        bad_file = tmp_path / "bad.png"
        bad_file.write_text("not an image")
        with pytest.raises(SystemExit) as exc_info:
            recognize_command(["--image", str(bad_file)])
        assert exc_info.value.code == 1

    def test_valid_synthetic_image(self, tmp_path):
        """合成截图 → 退出码 0 + 有效 JSON"""
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img[:] = (30, 50, 40)
        img_path = tmp_path / "synthetic.png"
        cv2.imwrite(str(img_path), img)

        with pytest.raises(SystemExit) as exc_info:
            recognize_command(["--image", str(img_path)])
        assert exc_info.value.code == 0

    @_SKIP_ORT
    def test_model_not_found(self, tmp_path):
        """模型文件路径无效 → 退出码 1（需要 onnxruntime）"""
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img[:] = (30, 50, 40)
        img_path = tmp_path / "synthetic.png"
        cv2.imwrite(str(img_path), img)

        with pytest.raises(SystemExit) as exc_info:
            recognize_command([
                "--image", str(img_path),
                "--model", "/nonexistent/model.onnx",
            ])
        assert exc_info.value.code == 1

    def test_subprocess_help(self):
        """子进程调用 recognize --help → 退出码 0"""
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--image" in result.stdout

    def test_subprocess_missing_args(self):
        """子进程调用 recognize 不带参数 → 退出码 2"""
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 2
```

- [ ] **Step 2: 运行测试确认失败**

```bash
.venv/bin/python -m pytest tests/test_cli.py::TestRecognizeCommand -v
```
Expected: FAILED — `ImportError: cannot import name 'recognize_command'`

- [ ] **Step 3: 实现 `recognize_command()`**

在 `src/majsoul_recognizer/cli.py` 中，`format_output()` 之后、`main()` 之前追加：

```python
def recognize_command(argv: list[str] | None = None) -> None:
    """recognize 子命令: 截图 → 识别 → JSON

    Args:
        argv: 命令行参数，None 时从 sys.argv 读取
    """
    import argparse as _argparse
    import logging

    # 抑制非关键日志输出到 stderr（设计规格 §4.6）
    logging.getLogger("majsoul_recognizer").setLevel(logging.WARNING)

    parser = _argparse.ArgumentParser(
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
```

- [ ] **Step 4: 注册 `recognize` 子命令到 `main()`**

在 `cli.py` 的 `main()` 函数中，在 `cal_parser` 定义之后追加：

```python
    # recognize 命令: 识别截图并输出 JSON
    rec_parser = subparsers.add_parser("recognize", help="识别截图中的游戏状态")
    rec_parser.add_argument("-i", "--image", required=True, help="输入截图文件路径")
    rec_parser.add_argument("--config", default=None, help="区域配置文件路径")
    rec_parser.add_argument("--model", default=None, help="ONNX 模型文件路径")
    rec_parser.add_argument("--template-dir", default=None, help="动作按钮模板目录")
```

在 `elif args.command == "calibrate":` 之后追加：

```python
    elif args.command == "recognize":
        recognize_command([
            "--image", args.image,
            *([] if args.config is None else ["--config", args.config]),
            *([] if args.model is None else ["--model", args.model]),
            *([] if args.template_dir is None else ["--template-dir", args.template_dir]),
        ])
```

- [ ] **Step 5: 运行测试确认通过**

```bash
.venv/bin/python -m pytest tests/test_cli.py::TestRecognizeCommand -v
```
Expected: 6 passed

- [ ] **Step 6: 运行全部测试确认无回归**

```bash
.venv/bin/python -m pytest tests/test_cli.py -v
```
Expected: 所有测试 PASS

- [ ] **Step 7: 手动验证 CLI 命令**

```bash
# 创建合成截图
.venv/bin/python -c "
import numpy as np, cv2
img = np.zeros((1080, 1920, 3), dtype=np.uint8)
img[:] = (30, 50, 40)
cv2.imwrite('/tmp/test_majsoul.png', img)
"

# 运行 recognize 命令
.venv/bin/python -m majsoul_recognizer recognize --image /tmp/test_majsoul.png
```
Expected: JSON 输出到 stdout，包含 `frame_id`、`is_static: true`、`hand: []` 等

- [ ] **Step 8: 提交**

```bash
git add src/majsoul_recognizer/cli.py tests/test_cli.py
git commit -m "feat: add recognize CLI subcommand with JSON output"
```

---

## Task 3: `[project.scripts]` 入口点

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 添加入口点**

在 `pyproject.toml` 的 `[project]` 段之后（`dependencies` 之后），追加：

```toml

[project.scripts]
majsoul-recognizer = "majsoul_recognizer.cli:main"
```

- [ ] **Step 2: 重新安装并验证**

```bash
.venv/bin/pip install -e ".[dev]" 2>&1 | tail -5
.venv/bin/majsoul-recognizer --help
```
Expected: 显示帮助信息，包含 `capture`、`split`、`calibrate`、`recognize` 命令

- [ ] **Step 3: 验证 recognize 子命令可用**

```bash
.venv/bin/majsoul-recognizer recognize --help
```
Expected: 显示 `--image` 参数说明

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml
git commit -m "feat: add [project.scripts] entry point for CLI"
```

---

## Task 4: 端到端集成测试

**Files:**
- Create: `tests/test_integration.py`

这个 Task 创建独立的集成测试文件，验证从截图文件到 JSON 输出的完整链路。

测试中需要检查 `onnxruntime` 是否可用来决定某些测试是否跳过。

**注意**: `tests/recognition/conftest.py` 中的 `dummy_detector_path` 和 `fake_template_dir` fixture **仅对 `tests/recognition/` 目录下的测试可见**（pytest 的 conftest 作用域规则），因此在 `tests/test_integration.py` 中需要重新定义这两个 fixture。

- [ ] **Step 1: 编写集成测试**

`tests/test_integration.py`:

```python
"""端到端集成测试

验证 CapturePipeline → RecognitionEngine → JSON 输出的完整链路。
"""

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

# 检测 onnxruntime 是否可用
try:
    import onnxruntime  # noqa: F401
    _HAS_ORT = True
except ImportError:
    _HAS_ORT = False

_SKIP_ORT = pytest.mark.skipif(not _HAS_ORT, reason="onnxruntime not installed")


# --- 内联 fixture（tests/recognition/conftest.py 的 fixture 对本文件不可见）---


@pytest.fixture(scope="session")
def dummy_detector_path(tmp_path_factory):
    """生成假 ONNX 检测模型（session 级别共享）"""
    import onnx
    from onnx import helper, TensorProto, numpy_helper

    output = np.zeros((1, 44, 8400), dtype=np.float32)

    # index 0: cx=80, cy=80, w=60, h=80, class=0(1m), conf=0.95
    output[0, 0, 0] = 80.0
    output[0, 1, 0] = 80.0
    output[0, 2, 0] = 60.0
    output[0, 3, 0] = 80.0
    output[0, 4, 0] = 0.95

    # index 1: cx=200, cy=100, w=50, h=70, class=9(1p), conf=0.88
    output[0, 0, 1] = 200.0
    output[0, 1, 1] = 100.0
    output[0, 2, 1] = 50.0
    output[0, 3, 1] = 70.0
    output[0, 4 + 9, 1] = 0.88

    X = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])
    Y = helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 44, 8400])

    output_data = numpy_helper.from_array(output, "output0")
    const_node = helper.make_node("Constant", [], ["output0"], value=output_data)

    graph = helper.make_graph([const_node], "dummy_detector", [X], [Y])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 7
    onnx.checker.check_model(model)

    path = tmp_path_factory.mktemp("models") / "dummy_detector.onnx"
    onnx.save(model, str(path))
    return path


@pytest.fixture(scope="session")
def fake_template_dir(tmp_path_factory):
    """生成假动作按钮模板（session 级别共享）"""
    template_dir = tmp_path_factory.mktemp("templates")
    buttons = {
        "chi": "吃", "pon": "碰", "kan": "杠",
        "ron": "荣和", "tsumo": "自摸", "riichi": "立直", "skip": "过",
    }
    for filename, text in buttons.items():
        img = np.full((40, 100, 3), 200, dtype=np.uint8)
        cv2.putText(img, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.imwrite(str(template_dir / f"{filename}.png"), img)
    return template_dir


# --- 辅助函数 ---


def _save_synthetic_screenshot(path: Path, *, different: bool = False) -> Path:
    """生成并保存合成截图"""
    img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    if different:
        img[:] = (100, 80, 60)  # 不同颜色
    else:
        img[:] = (30, 50, 40)  # 深绿色桌面
    cv2.imwrite(str(path), img)
    return path


class TestEndToEndStubDetector:
    """使用 StubDetector（无 onnxruntime）的集成测试"""

    def test_synthetic_image_returns_valid_json(self, tmp_path):
        """合成截图 + StubDetector → 退出码 0 + 有效 JSON + 产品规格书键名"""
        img_path = _save_synthetic_screenshot(tmp_path / "test.png")
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize",
             "--image", str(img_path)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["frame_id"] == 1
        assert data["is_static"] is True
        assert isinstance(data["hand"], list)
        assert isinstance(data["warnings"], list)
        # 产品规格书 §3 键名验证（设计规格 §8.1 测试 #7）
        assert "round" in data
        assert "round_info" not in data
        assert "timer" in data

    def test_non_static_frame(self, tmp_path):
        """非静态帧 → is_static=false + warnings 含 frame_not_static"""
        from majsoul_recognizer.pipeline import CapturePipeline
        from majsoul_recognizer.recognition import RecognitionEngine, RecognitionConfig
        from majsoul_recognizer.cli import format_output

        pipeline = CapturePipeline()
        engine = RecognitionEngine(RecognitionConfig())

        # 先处理一张图建立参考帧
        img_a = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img_a[:] = (30, 50, 40)
        pipeline.process_image(img_a)

        # 再处理一张完全不同的图 → 非静态
        img_b = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img_b[:] = (200, 150, 100)
        frame = pipeline.process_image(img_b)
        assert frame.is_static is False

        output = format_output(frame, None)
        assert output["is_static"] is False
        assert "frame_not_static" in output["warnings"]

    def test_output_format_matches_spec(self, tmp_path):
        """输出格式符合产品规格书 §3（round 非 round_info，timer 格式）"""
        from majsoul_recognizer.pipeline import CapturePipeline
        from majsoul_recognizer.recognition import RecognitionEngine, RecognitionConfig
        from majsoul_recognizer.cli import format_output

        pipeline = CapturePipeline()
        config = RecognitionConfig()
        engine = RecognitionEngine(config)

        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img[:] = (30, 50, 40)
        frame = pipeline.process_image(img)
        assert frame.is_static is True

        state = engine.recognize(frame.zones)
        output = format_output(frame, state)

        # 产品规格书 §3 键名检查
        assert "round" in output
        assert "round_info" not in output
        assert output["round"] is None or isinstance(output["round"], dict)
        # timer 格式: null 或 {"active": bool, "remaining": int}
        assert output["timer"] is None or (
            isinstance(output["timer"], dict)
            and "active" in output["timer"]
            and "remaining" in output["timer"]
        )

    def test_file_not_found_stderr(self):
        """文件不存在 → 退出码 1 + stderr 含错误信息"""
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize",
             "--image", "/nonexistent/path.png"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 1
        assert len(result.stderr) > 0
        assert len(result.stdout) == 0  # stdout 无输出

    def test_invalid_image_stderr(self, tmp_path):
        """非图片文件 → 退出码 1 + stderr 含错误信息"""
        bad_file = tmp_path / "bad.png"
        bad_file.write_text("this is not an image")
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize",
             "--image", str(bad_file)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 1
        assert len(result.stderr) > 0


@_SKIP_ORT
class TestEndToEndWithDetector:
    """使用 dummy ONNX 模型的集成测试（需要 onnxruntime）"""

    def test_with_dummy_model(self, tmp_path, dummy_detector_path, fake_template_dir):
        """使用 dummy_detector → 退出码 0 + JSON 含检测结果"""
        from majsoul_recognizer.pipeline import CapturePipeline
        from majsoul_recognizer.recognition import RecognitionEngine, RecognitionConfig
        from majsoul_recognizer.cli import format_output

        img_path = _save_synthetic_screenshot(tmp_path / "test.png")

        config = RecognitionConfig(
            model_path=dummy_detector_path,
            template_dir=fake_template_dir,
        )
        pipeline = CapturePipeline()
        engine = RecognitionEngine(config)

        img = cv2.imread(str(img_path))
        frame = pipeline.process_image(img)
        state = engine.recognize(frame.zones)
        output = format_output(frame, state)

        assert output["is_static"] is True
        assert output["frame_id"] == 1
        # dummy_detector 在任何图片上都输出固定结果
        assert isinstance(output["hand"], list)

    def test_model_not_found_exit_code(self, tmp_path):
        """模型文件不存在 → 退出码 1"""
        img_path = _save_synthetic_screenshot(tmp_path / "test.png")
        result = subprocess.run(
            [sys.executable, "-m", "majsoul_recognizer", "recognize",
             "--image", str(img_path),
             "--model", str(tmp_path / "nonexistent.onnx")],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 1
        assert len(result.stderr) > 0
```

- [ ] **Step 2: 运行测试确认通过**

```bash
.venv/bin/python -m pytest tests/test_integration.py -v
```
Expected: StubDetector 测试 5 passed；onnxruntime 测试 passed 或 skipped

- [ ] **Step 3: 运行全部测试确认无回归**

```bash
.venv/bin/python -m pytest -v --tb=short
```
Expected: 所有测试 PASS

- [ ] **Step 4: 提交**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration tests for recognize pipeline"
```

---

## 验证清单

完成所有 Task (1-4) 后运行以下验证：

- [ ] **全部测试通过**

```bash
.venv/bin/python -m pytest -v --tb=short
```

- [ ] **代码风格检查**

```bash
.venv/bin/python -m ruff check src/majsoul_recognizer/cli.py tests/test_cli.py tests/test_integration.py
```

- [ ] **CLI recognize 命令可用**

```bash
.venv/bin/majsoul-recognizer recognize --help
```
Expected: 显示 `--image` 参数

- [ ] **端到端手动验证**

```bash
.venv/bin/python -c "
import numpy as np, cv2
img = np.zeros((1080, 1920, 3), dtype=np.uint8)
img[:] = (30, 50, 40)
cv2.imwrite('/tmp/e2e_test.png', img)
"
.venv/bin/majsoul-recognizer recognize --image /tmp/e2e_test.png
```
Expected: JSON 输出，`is_static: true`，`hand: []`

---

## 交付物总结

完成 Plan 3 后，项目将具备：

| 能力 | 交付物 | 验证方式 |
|------|--------|---------|
| 输出适配层 | `format_output()` | 7 个单元测试 |
| recognize 命令 | CLI `majsoul-recognizer recognize` | 6 个 CLI 测试 |
| 入口点 | `[project.scripts]` | `majsoul-recognizer --help` |
| 端到端集成测试 | `test_integration.py` | 7 个集成测试 |
