# GUI 基础设施实施计划 (Spec A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 GUI 模块建立基础设施：包入口、主题系统、配置持久化、共享状态、识别工作线程、视图基类。

**Architecture:** 6 个核心模块，纯逻辑层（settings、worker、app_state、theme 颜色定义）不依赖 tkinter 运行时可测。base_view 和 theme.apply_style 需要 tkinter，用 skip 标记隔离。

**Tech Stack:** Python 3.10+, tkinter/ttk, threading, queue, pytest

**设计文档:** `docs/superpowers/specs/2026-05-09-gui-spec-a-foundation.md`

**依赖的现有代码:**
- `src/majsoul_recognizer/recognition/config.py` — `RecognitionConfig` (12 个字段)
- `src/majsoul_recognizer/pipeline.py` — `CapturePipeline(config_path, frame_threshold)`
- `src/majsoul_recognizer/types.py` — `FrameResult, GameState`
- `src/majsoul_recognizer/cli.py` — CLI `main()` 入口
- `src/majsoul_recognizer/recognition/engine.py` — `RecognitionEngine`

---

## File Structure

```
src/majsoul_recognizer/gui/
├── __init__.py          # tkinter 可用性检查 + main()
├── theme.py             # Theme 颜色定义 + apply_style + get_theme
├── settings.py          # GUISettings dataclass (load/save/to_config)
├── app_state.py         # AppState dataclass
├── worker.py            # _WorkerResult + _RecognizeWorker
├── base_view.py         # BaseView(ttk.Frame) 抽象类

tests/gui/
├── __init__.py
├── conftest.py          # needs_tk marker 注册
├── test_theme.py
├── test_settings.py
├── test_app_state.py
├── test_worker.py
├── test_base_view.py    # [S4] BaseView 生命周期测试
```

---

### Task 1: 包骨架 + pyproject.toml + CLI 入口

**Files:**
- Create: `src/majsoul_recognizer/gui/__init__.py`
- Create: `tests/gui/__init__.py`
- Modify: `pyproject.toml` — 添加 `gui` optional-dependencies
- Modify: `src/majsoul_recognizer/cli.py` — 添加 `gui` 子命令

- [ ] **Step 1: 创建 gui 包和测试包空文件**

```bash
mkdir -p src/majsoul_recognizer/gui tests/gui
touch tests/gui/__init__.py
```

- [ ] **Step 2: 创建 `gui/__init__.py`**

```python
"""GUI 包入口

[C1 修复] tkinter 检测仅在 main() 中执行，不影响子模块导入。
纯逻辑模块（settings, worker, theme, app_state）可在无 tkinter 环境下正常导入和测试。
"""


def main() -> None:
    """启动 GUI 主窗口"""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        raise SystemExit(
            "tkinter 不可用。macOS: brew install python-tk@3.14\n"
            "Windows: tkinter 随 Python 安装包自带。"
        )

    from majsoul_recognizer.gui.app import App

    app = App()
    app.run()
```

- [ ] **Step 3: 修改 `pyproject.toml` 添加 gui 依赖**

在 `pyproject.toml` 的 `[project.optional-dependencies]` 段（第 21 行起），在 `training` 组之后（第 38 行 `"ultralytics>=8.1",` 的 `]` 之后）添加新组:

```toml
# 在第 38 行 ] 之后、第 40 行 dev 组之前插入:
gui = [
    "Pillow>=10.0",
]
```

- [ ] **Step 4: 修改 `cli.py` 添加 gui 子命令**

文件: `src/majsoul_recognizer/cli.py`

**4a**: 在 `rec_parser` 定义块之后（第 274 行 `rec_parser.add_argument("--template-dir", ...)` 之后），第 276 行 `args = parser.parse_args()` 之前，插入:

```python
    # gui 命令: 启动图形界面
    subparsers.add_parser("gui", help="启动图形界面")
```

**4b**: 在 `elif args.command == "recognize":` 块的末尾（第 302 行 `])` 之后），第 304 行 `else:` 之前，插入:

```python
    elif args.command == "gui":
        from majsoul_recognizer.gui import main
        main()
```

- [ ] **Step 5: 验证包可导入（预期失败 — app.py 尚不存在）**

Run: `python -c "from majsoul_recognizer.gui import main"`
Expected: `ImportError: cannot import name 'App' from 'majsoul_recognizer.gui.app'`（或 `ModuleNotFoundError`）

这是预期行为 — app.py 在 Spec C 中创建。

- [ ] **Step 6: Commit**

```bash
git add src/majsoul_recognizer/gui/__init__.py tests/gui/__init__.py pyproject.toml src/majsoul_recognizer/cli.py
git commit -m "feat(gui): add package skeleton, CLI entry point, and Pillow dependency"
```

---

### Task 2: Theme 颜色定义 + 纯逻辑测试

**Files:**
- Create: `src/majsoul_recognizer/gui/theme.py`
- Create: `tests/gui/conftest.py`
- Create: `tests/gui/test_theme.py`

- [ ] **Step 1: 编写 theme 颜色测试**

`tests/gui/conftest.py`:
```python
"""GUI 测试共享 fixtures

[S1 修复] Spec A 的所有测试（theme/settings/worker/app_state）不依赖 tkinter。
仅注册 needs_tk marker 供 Spec C 中 tkinter 相关测试使用。
"""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "needs_tk: test requires tkinter")
```

`tests/gui/test_theme.py`:
```python
"""主题系统测试 — 颜色定义部分（不需要 tkinter）"""

from majsoul_recognizer.gui.theme import Theme, get_theme


class TestThemeColors:
    """颜色方案完整性测试"""

    def test_dark_has_all_keys(self):
        expected_keys = {
            "bg_primary", "bg_secondary", "bg_tertiary", "bg_sidebar",
            "fg_primary", "fg_secondary", "fg_muted",
            "accent", "success", "warning", "error", "highlight",
            "border", "canvas_bg",
        }
        assert set(Theme.DARK.keys()) == expected_keys

    def test_light_has_all_keys(self):
        expected_keys = {
            "bg_primary", "bg_secondary", "bg_tertiary", "bg_sidebar",
            "fg_primary", "fg_secondary", "fg_muted",
            "accent", "success", "warning", "error", "highlight",
            "border", "canvas_bg",
        }
        assert set(Theme.LIGHT.keys()) == expected_keys

    def test_dark_and_light_have_same_keys(self):
        assert set(Theme.DARK.keys()) == set(Theme.LIGHT.keys())

    def test_all_values_are_hex_colors(self):
        for name, colors in [("DARK", Theme.DARK), ("LIGHT", Theme.LIGHT)]:
            for key, value in colors.items():
                assert value.startswith("#"), f"{name}.{key} = {value!r}, expected hex color"
                assert len(value) == 7, f"{name}.{key} = {value!r}, expected #RRGGBB format"


class TestGetTheme:
    def test_get_dark(self):
        result = get_theme("dark")
        assert result is Theme.DARK

    def test_get_light(self):
        result = get_theme("light")
        assert result is Theme.LIGHT

    def test_get_unknown_returns_dark(self):
        result = get_theme("unknown")
        assert result is Theme.DARK
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/gui/test_theme.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'majsoul_recognizer.gui.theme'`

- [ ] **Step 3: 实现 `gui/theme.py`**

```python
"""深色/浅色主题管理

[C1/M1 修复] Theme 类和 get_theme() 不依赖 tkinter。
apply_style() 内部延迟导入 tkinter，仅在运行时需要。
"""

from __future__ import annotations

from typing import Any


class Theme:
    """主题颜色方案"""

    DARK = {
        "bg_primary": "#1a1a2e",
        "bg_secondary": "#16213e",
        "bg_tertiary": "#0f3460",
        "bg_sidebar": "#0d1b2a",
        "fg_primary": "#e0e0e0",
        "fg_secondary": "#a0a0a0",
        "fg_muted": "#666666",
        "accent": "#00d4ff",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#e94560",
        "highlight": "#ff5722",
        "border": "#2a2a4a",
        "canvas_bg": "#12122e",
    }

    LIGHT = {
        "bg_primary": "#f5f5f5",
        "bg_secondary": "#ffffff",
        "bg_tertiary": "#e8eaf6",
        "bg_sidebar": "#e0e0e0",
        "fg_primary": "#212121",
        "fg_secondary": "#616161",
        "fg_muted": "#9e9e9e",
        "accent": "#1565c0",
        "success": "#388e3c",
        "warning": "#f57c00",
        "error": "#d32f2f",
        "highlight": "#e64a19",
        "border": "#bdbdbd",
        "canvas_bg": "#eeeeee",
    }


def get_theme(name: str) -> dict[str, str]:
    """获取主题颜色方案

    Args:
        name: "dark" 或 "light"，未知名称返回 dark。

    Returns:
        颜色字典（DARK 或 LIGHT 的引用）。
    """
    if name == "light":
        return Theme.LIGHT
    return Theme.DARK


def apply_style(style: Any, theme: dict[str, str]) -> None:
    """将主题应用到 ttk.Style 全局样式

    [M1] tkinter 在此函数内延迟导入。调用方（App）已确保 tkinter 可用。
    style 参数类型为 Any 避免模块顶层导入 tkinter。
    """
    style.configure(".", background=theme["bg_primary"],
                     foreground=theme["fg_primary"],
                     borderwidth=0)
    style.configure("TFrame", background=theme["bg_primary"])
    style.configure("TLabel", background=theme["bg_primary"],
                     foreground=theme["fg_primary"])
    style.configure("TButton", background=theme["bg_tertiary"],
                     foreground=theme["fg_primary"])
    style.map("TButton",
              background=[("active", theme["accent"])],
              foreground=[("active", "#ffffff")])
    style.configure("Sidebar.TFrame", background=theme["bg_sidebar"])
    style.configure("Sidebar.TButton", background=theme["bg_sidebar"],
                     foreground=theme["fg_primary"])
    style.configure("Status.TLabel", background=theme["bg_primary"],
                     foreground=theme["fg_secondary"])
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/gui/test_theme.py -v`
Expected: 全部 PASS（7 个测试）

- [ ] **Step 5: Commit**

```bash
git add src/majsoul_recognizer/gui/theme.py tests/gui/conftest.py tests/gui/test_theme.py
git commit -m "feat(gui): add theme system with dark/light color schemes"
```

---

### Task 3: GUISettings 配置持久化

**Files:**
- Create: `src/majsoul_recognizer/gui/settings.py`
- Create: `tests/gui/test_settings.py`

- [ ] **Step 1: 编写 settings 测试**

`tests/gui/test_settings.py`:
```python
"""GUISettings 配置持久化测试"""

import json
from pathlib import Path

import pytest

from majsoul_recognizer.gui.settings import GUISettings


class TestGUISettingsDefaults:
    def test_default_values(self):
        s = GUISettings()
        assert s.model_path is None
        assert s.theme == "dark"
        assert s.detection_confidence == 0.7
        assert s.window_width == 1280
        assert s.window_height == 800

    def test_custom_values(self):
        s = GUISettings(theme="light", detection_confidence=0.9, window_width=1920)
        assert s.theme == "light"
        assert s.detection_confidence == 0.9
        assert s.window_width == 1920


class TestGUISettingsSaveLoad:
    def test_save_and_load_roundtrip(self, tmp_path):
        """[C2/M2 修复] 使用 path 参数替代 _PATH 实例属性赋值"""
        path = tmp_path / "test_settings.json"
        original = GUISettings(theme="light", model_path="/path/to/model", window_width=1920)
        original.save(path=path)

        loaded = GUISettings.load(path=path)

        assert loaded.theme == "light"
        assert loaded.model_path == "/path/to/model"
        assert loaded.window_width == 1920

    def test_load_missing_file_returns_defaults(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        result = GUISettings.load(path=path)
        assert result.theme == "dark"
        assert result.model_path is None

    def test_load_corrupted_file_returns_defaults(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{invalid json!!!")
        result = GUISettings.load(path=path)
        assert result.theme == "dark"

    def test_save_is_atomic(self, tmp_path):
        path = tmp_path / "atomic.json"
        s = GUISettings(theme="dark")
        s.save(path=path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["theme"] == "dark"


class TestToRecognitionConfig:
    def test_default_maps_to_config(self):
        from majsoul_recognizer.recognition.config import RecognitionConfig

        s = GUISettings()
        config = s.to_recognition_config()
        assert isinstance(config, RecognitionConfig)
        assert config.model_path is None
        assert config.detection_confidence == 0.7
        assert config.nms_iou_threshold == 0.55
        assert config.enable_batch_detection is True
        assert config.drawn_tile_gap_multiplier == 2.5

    def test_custom_path_converted(self):
        s = GUISettings(model_path="/models/detector.onnx")
        config = s.to_recognition_config()
        assert config.model_path == Path("/models/detector.onnx")

    def test_all_fields_mapped(self):
        """[C3 修复] 确保每个 RecognitionConfig 字段都被映射
        RecognitionConfig 是 Pydantic BaseModel，用 model_fields 而非 dataclasses.fields。
        """
        from majsoul_recognizer.recognition.config import RecognitionConfig

        rc_fields = set(RecognitionConfig.model_fields.keys())
        s = GUISettings(
            model_path="/m", mapping_path="/map", template_dir="/t",
            ocr_model_dir="/ocr", detection_confidence=0.8,
            nms_iou_threshold=0.6, score_min=-100, score_max=100000,
            fusion_window_size=5, enable_batch_detection=False,
            drawn_tile_gap_multiplier=3.0, call_group_gap_multiplier=2.5,
        )
        config = s.to_recognition_config()
        assert config.mapping_path == Path("/map")
        assert config.ocr_model_dir == Path("/ocr")
        assert config.score_min == -100
        assert config.score_max == 100000
        assert config.fusion_window_size == 5
        assert config.enable_batch_detection is False


class TestToPipelineConfig:
    def test_default_returns_none_path(self):
        s = GUISettings()
        config_path, threshold = s.to_pipeline_config()
        assert config_path is None
        assert threshold == 0.02

    def test_custom_path(self):
        s = GUISettings(config_path="/config/zones.yaml")
        config_path, threshold = s.to_pipeline_config()
        assert config_path == Path("/config/zones.yaml")
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/gui/test_settings.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 `gui/settings.py`**

```python
"""GUI 配置持久化

GUISettings 将所有可配置项映射到 RecognitionConfig + GUI 偏好。
保存为 JSON 文件，原子写入。
"""

from __future__ import annotations

import dataclasses
import json
import logging
import tempfile
from dataclasses import dataclass, field, ClassVar
from pathlib import Path

from majsoul_recognizer.recognition.config import RecognitionConfig

logger = logging.getLogger(__name__)


@dataclass
class GUISettings:
    """GUI 配置 — 映射 RecognitionConfig 全部字段 + GUI 偏好"""

    # RecognitionConfig 映射
    model_path: str | None = None
    mapping_path: str | None = None
    template_dir: str | None = None
    config_path: str | None = None
    ocr_model_dir: str | None = None
    detection_confidence: float = 0.7
    nms_iou_threshold: float = 0.55
    score_min: int = -99999
    score_max: int = 200000
    fusion_window_size: int = 3
    enable_batch_detection: bool = True
    drawn_tile_gap_multiplier: float = 2.5
    call_group_gap_multiplier: float = 2.0

    # GUI 偏好
    theme: str = "dark"
    capture_interval_ms: int = 200
    show_detection_boxes: bool = True
    show_confidence: bool = True

    # 窗口几何
    window_width: int = 1280
    window_height: int = 800
    window_x: int = 100
    window_y: int = 100

    _PATH: ClassVar[Path] = Path.home() / ".majsoul-recognizer" / "settings.json"

    @classmethod
    def load(cls, path: Path | None = None) -> GUISettings:
        """加载配置，文件不存在或损坏时返回默认值

        [M2 修复] path 参数用于测试注入，None 时使用 cls._PATH。
        """
        file_path = path or cls._PATH
        try:
            text = file_path.read_text(encoding="utf-8")
            data = json.loads(text)
            return cls(**{k: v for k, v in data.items() if k in {f.name for f in dataclasses.fields(cls)}})
        except FileNotFoundError:
            return cls()
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("配置文件损坏，使用默认值: %s", e)
            return cls()

    def save(self, path: Path | None = None) -> None:
        """原子写入（先写临时文件再 rename）

        [M2 修复] path 参数用于测试注入，None 时使用 cls._PATH。
        """
        file_path = path or self._PATH
        file_path.parent.mkdir(parents=True, exist_ok=True)
        data = dataclasses.asdict(self)
        try:
            fd, tmp = tempfile.mkstemp(dir=str(file_path.parent), suffix=".json")
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            Path(tmp).rename(file_path)
        except Exception:
            Path(tmp).unlink(missing_ok=True)
            raise

    def to_recognition_config(self) -> RecognitionConfig:
        """转换为 RecognitionConfig（完整映射所有字段）"""
        return RecognitionConfig(
            model_path=Path(self.model_path) if self.model_path else None,
            mapping_path=Path(self.mapping_path) if self.mapping_path else None,
            template_dir=Path(self.template_dir) if self.template_dir else None,
            ocr_model_dir=Path(self.ocr_model_dir) if self.ocr_model_dir else None,
            nms_iou_threshold=self.nms_iou_threshold,
            detection_confidence=self.detection_confidence,
            score_min=self.score_min,
            score_max=self.score_max,
            fusion_window_size=self.fusion_window_size,
            enable_batch_detection=self.enable_batch_detection,
            drawn_tile_gap_multiplier=self.drawn_tile_gap_multiplier,
            call_group_gap_multiplier=self.call_group_gap_multiplier,
        )

    def to_pipeline_config(self) -> tuple[Path | None, float]:
        """返回 (config_path, frame_threshold)"""
        return (
            Path(self.config_path) if self.config_path else None,
            0.02,
        )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/gui/test_settings.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/majsoul_recognizer/gui/settings.py tests/gui/test_settings.py
git commit -m "feat(gui): add GUISettings with full RecognitionConfig mapping and atomic save"
```

---

### Task 4: AppState 共享状态

**Files:**
- Create: `src/majsoul_recognizer/gui/app_state.py`
- Create: `tests/gui/test_app_state.py`

- [ ] **Step 1: 编写 app_state 测试**

`tests/gui/test_app_state.py`:
```python
"""AppState 测试"""

from unittest.mock import MagicMock

from majsoul_recognizer.gui.app_state import AppState


class TestAppState:
    def _make_state(self, **kwargs):
        defaults = {
            "engine": MagicMock(),
            "pipeline_factory": lambda: MagicMock(),
            "config": MagicMock(),
            "theme_name": "dark",
        }
        defaults.update(kwargs)
        return AppState(**defaults)

    def test_creation(self):
        state = self._make_state()
        assert state.theme_name == "dark"
        assert state.engine is not None

    def test_engine_can_be_replaced(self):
        state = self._make_state()
        new_engine = MagicMock()
        state.engine = new_engine
        assert state.engine is new_engine

    def test_pipeline_factory_creates_new_instances(self):
        """S5: 工厂函数每次返回独立实例"""
        state = self._make_state()
        p1 = state.pipeline_factory()
        p2 = state.pipeline_factory()
        assert p1 is not p2
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/gui/test_app_state.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 `gui/app_state.py`**

```python
"""应用共享状态

AppState 由 App 构建并注入各视图。
engine 可通过 App._rebuild_engine() 替换。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from majsoul_recognizer.recognition.config import RecognitionConfig
from majsoul_recognizer.recognition.engine import RecognitionEngine
from majsoul_recognizer.pipeline import CapturePipeline


@dataclass
class AppState:
    """App 管理的共享资源

    Attributes:
        engine: 识别引擎，可被 App._rebuild_engine() 替换。
            Worker 通过本地引用持有旧实例直到当前迭代完成（S2 线程安全）。
        pipeline_factory: 工厂函数，每次调用返回新的 CapturePipeline 实例（S5 隔离）。
        config: 当前识别配置。
        theme_name: "dark" | "light"。
    """

    engine: RecognitionEngine
    pipeline_factory: Callable[[], CapturePipeline]
    config: RecognitionConfig
    theme_name: str
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/gui/test_app_state.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/majsoul_recognizer/gui/app_state.py tests/gui/test_app_state.py
git commit -m "feat(gui): add AppState dataclass with pipeline factory pattern"
```

---

### Task 5: _WorkerResult + _RecognizeWorker

**Files:**
- Create: `src/majsoul_recognizer/gui/worker.py`
- Create: `tests/gui/test_worker.py`

- [ ] **Step 1: 编写 worker 测试**

`tests/gui/test_worker.py`:
```python
"""识别工作线程测试

[S2 修复] 使用 _poll_result 替代脆弱的 time.sleep 同步。
[M3 修复] _make_frame_result 使用参数化时间戳。
"""

import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from majsoul_recognizer.gui.worker import _RecognizeWorker, _WorkerResult
from majsoul_recognizer.types import FrameResult


def _make_image(h=100, w=100):
    return np.zeros((h, w, 3), dtype=np.uint8)


def _make_frame_result(is_static=True, frame_id=1, timestamp="2026-05-09T00:00:00Z"):
    """[M3] 参数化 timestamp 和 frame_id"""
    return FrameResult(
        frame_id=frame_id,
        timestamp=timestamp,
        zones={"hand": _make_image()} if is_static else {},
        is_static=is_static,
    )


def _poll_result(worker, timeout=2.0, interval=0.01):
    """[S2] 轮询等待结果，替代脆弱的 time.sleep

    以 interval 为间隔轮询，总超时 timeout 秒。
    比一次性 time.sleep(0.2) 更可靠：快时更快，慢时不会假失败。
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = worker.get_result()
        if result is not None:
            return result
        time.sleep(interval)
    raise TimeoutError(f"Worker did not produce result within {timeout}s")


class TestWorkerResult:
    def test_normal_result(self):
        r = _WorkerResult(image=_make_image(), frame=_make_frame_result(), state=None)
        assert not r.is_error
        assert r.image is not None
        assert r.frame is not None

    def test_error_result(self):
        r = _WorkerResult(error="boom")
        assert r.is_error
        assert r.error == "boom"
        assert r.image is None


class TestRecognizeWorker:
    def _make_worker(self, process_returns=None, recognize_returns=None):
        """创建 Worker，mock pipeline 和 engine"""
        pipeline = MagicMock()
        engine = MagicMock()

        if process_returns is not None:
            pipeline.process_image.return_value = process_returns
        else:
            pipeline.process_image.return_value = _make_frame_result()

        if recognize_returns is not None:
            engine.recognize.return_value = recognize_returns

        worker = _RecognizeWorker(engine, pipeline)
        return worker, engine, pipeline

    def test_submit_and_get_result(self):
        frame = _make_frame_result(is_static=True)
        state = MagicMock()
        worker, engine, _ = self._make_worker(process_returns=frame, recognize_returns=state)

        image = _make_image()
        assert worker.submit(image) is True

        result = _poll_result(worker)
        assert not result.is_error
        assert result.frame is frame
        assert result.state is state

        worker.stop()

    def test_submit_drops_when_busy(self):
        """上一帧未处理完时丢弃新提交"""
        def slow_process(img):
            time.sleep(1.0)
            return _make_frame_result()

        worker, _, pipeline = self._make_worker()
        pipeline.process_image.side_effect = slow_process

        image1 = _make_image()
        assert worker.submit(image1) is True

        # 立即提交第二帧，应被丢弃
        image2 = _make_image()
        assert worker.submit(image2) is False

        worker.stop()

    def test_non_static_frame_skips_recognition(self):
        """非静态帧跳过 engine.recognize"""
        frame = _make_frame_result(is_static=False)
        worker, engine, pipeline = self._make_worker(process_returns=frame)

        worker.submit(_make_image())
        result = _poll_result(worker)

        assert result.state is None  # 非静态帧不识别
        engine.recognize.assert_not_called()

        worker.stop()

    def test_exception_becomes_error_result(self):
        """pipeline 异常转为 error 结果"""
        worker, _, pipeline = self._make_worker()
        pipeline.process_image.side_effect = RuntimeError("model not found")

        worker.submit(_make_image())
        result = _poll_result(worker)

        assert result.is_error
        assert "model not found" in result.error

        worker.stop()

    def test_stop_terminates_thread(self):
        worker, _, _ = self._make_worker()
        assert worker._thread.is_alive()
        worker.stop()
        assert not worker._thread.is_alive()

    def test_get_result_empty_when_nothing_submitted(self):
        worker, _, _ = self._make_worker()
        result = worker.get_result()
        assert result is None
        worker.stop()

    def test_update_engine(self):
        """引擎引用可被更新"""
        worker, old_engine, _ = self._make_worker()
        new_engine = MagicMock()
        worker.update_engine(new_engine)
        # 引用已更新（内部 _engine_ref 指向 new_engine）
        assert worker._engine_ref is new_engine
        worker.stop()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/gui/test_worker.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 `gui/worker.py`**

```python
"""识别工作线程

在独立线程中串行处理图像识别任务。
支持丢弃旧帧、引擎热更新、错误捕获。
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass

import numpy as np

from majsoul_recognizer.pipeline import CapturePipeline
from majsoul_recognizer.recognition.engine import RecognitionEngine
from majsoul_recognizer.types import FrameResult, GameState


@dataclass
class _WorkerResult:
    """Worker 输出结果，区分正常和错误"""

    image: np.ndarray | None = None
    frame: FrameResult | None = None
    state: GameState | None = None
    error: str | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


class _RecognizeWorker:
    """单工作线程识别器

    串行处理提交的图像，处理中丢弃新提交（skip-latest 策略）。
    通过 result_queue（maxsize=1）传递结果，旧结果自动丢弃。
    """

    def __init__(self, engine: RecognitionEngine, pipeline: CapturePipeline) -> None:
        self._engine_ref = engine
        self._pipeline_ref = pipeline
        self._task: np.ndarray | None = None
        self._result_queue: queue.Queue[_WorkerResult] = queue.Queue(maxsize=1)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update_engine(self, engine: RecognitionEngine) -> None:
        """更新 engine 引用（线程安全）

        _run() 每次循环开头持有 engine 本地引用（S2），
        即使 update_engine 在循环中途被调用，当前迭代不会中途切换。
        """
        self._engine_ref = engine

    def submit(self, image: np.ndarray) -> bool:
        """提交图像。上一帧未处理完则丢弃（返回 False）"""
        with self._lock:
            if self._task is not None:
                return False
            self._task = image
        return True

    def _run(self) -> None:
        """工作线程主循环"""
        while not self._stop_event.is_set():
            with self._lock:
                image = self._task
                self._task = None
            if image is None:
                self._stop_event.wait(0.01)
                continue
            # S2: 持有 engine 本地引用
            engine = self._engine_ref
            try:
                frame = self._pipeline_ref.process_image(image)
                state = engine.recognize(frame.zones) if frame.is_static else None
                result = _WorkerResult(image=image, frame=frame, state=state)
            except Exception as e:
                result = _WorkerResult(error=str(e))
            # 非阻塞清理旧结果
            try:
                self._result_queue.get_nowait()
            except queue.Empty:
                pass
            self._result_queue.put(result)

    def get_result(self) -> _WorkerResult | None:
        """非阻塞获取最新结果"""
        try:
            return self._result_queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self) -> None:
        """停止工作线程并等待退出（M2: join timeout 防止挂起）"""
        self._stop_event.set()
        self._thread.join(timeout=2.0)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/gui/test_worker.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 运行全部测试确认无回归**

Run: `pytest tests/ -v --timeout=30`
Expected: 全部 PASS（含新增的 worker 测试）

- [ ] **Step 6: Commit**

```bash
git add src/majsoul_recognizer/gui/worker.py tests/gui/test_worker.py
git commit -m "feat(gui): add _RecognizeWorker with skip-latest and error capture"
```

---

### Task 6: BaseView 视图基类

**Files:**
- Create: `src/majsoul_recognizer/gui/base_view.py`
- Create: `tests/gui/test_base_view.py`

注意: BaseView 继承 `ttk.Frame`，需要 tkinter。测试通过 `pytest.importorskip("tkinter")` 在无 tkinter 时自动跳过。

- [ ] **Step 1: 编写 BaseView 测试**

`tests/gui/test_base_view.py`:
```python
"""BaseView 生命周期测试

[S4 修复] BaseView 继承 ttk.Frame，需要 tkinter。
测试使用 Tk root 创建真实 widget 实例，验证生命周期逻辑。
无 tkinter 环境自动跳过。
"""

import pytest

# tkinter 不可用时跳过整个模块
pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk
from unittest.mock import MagicMock, patch

from majsoul_recognizer.gui.base_view import BaseView


@pytest.fixture
def tk_root():
    """创建隐藏的 Tk root 窗口"""
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def mock_app_state():
    pipeline1 = MagicMock()
    pipeline2 = MagicMock()
    pipelines = iter([pipeline1, pipeline2])
    return MagicMock(
        engine=MagicMock(),
        pipeline_factory=lambda: next(pipelines),
        config=MagicMock(),
        theme_name="dark",
    )


class TestBaseViewLifecycle:
    def test_ensure_worker_creates_worker(self, tk_root, mock_app_state):
        """_ensure_worker 创建 _RecognizeWorker"""
        with patch("majsoul_recognizer.gui.base_view._RecognizeWorker") as MockWorker:
            mock_worker = MagicMock()
            MockWorker.return_value = mock_worker

            view = BaseView(tk_root, mock_app_state, {})
            result = view._ensure_worker()

            assert result is mock_worker
            MockWorker.assert_called_once()

    def test_ensure_worker_is_idempotent(self, tk_root, mock_app_state):
        """多次调用 _ensure_worker 只创建一次 Worker"""
        with patch("majsoul_recognizer.gui.base_view._RecognizeWorker") as MockWorker:
            view = BaseView(tk_root, mock_app_state, {})
            view._ensure_worker()
            view._ensure_worker()
            assert MockWorker.call_count == 1

    def test_stop_cleans_up_worker(self, tk_root, mock_app_state):
        """stop() 调用 worker.stop() 并置空"""
        mock_worker = MagicMock()
        view = BaseView(tk_root, mock_app_state, {})
        view._worker = mock_worker

        view.stop()
        mock_worker.stop.assert_called_once()
        assert view._worker is None

    def test_stop_no_worker_is_noop(self, tk_root, mock_app_state):
        """无 Worker 时 stop() 安全返回"""
        view = BaseView(tk_root, mock_app_state, {})
        view.stop()  # 不应抛异常

    def test_on_theme_changed_updates_theme(self, tk_root, mock_app_state):
        new_theme = {"bg_primary": "#fff"}
        view = BaseView(tk_root, mock_app_state, {})
        view.on_theme_changed(new_theme)
        assert view._theme == new_theme

    def test_on_engine_changed_updates_worker(self, tk_root, mock_app_state):
        mock_worker = MagicMock()
        new_engine = MagicMock()
        view = BaseView(tk_root, mock_app_state, {})
        view._worker = mock_worker

        view.on_engine_changed(new_engine)
        mock_worker.update_engine.assert_called_once_with(new_engine)

    def test_on_engine_changed_without_worker_is_safe(self, tk_root, mock_app_state):
        """无 Worker 时 on_engine_changed 不抛异常"""
        new_engine = MagicMock()
        view = BaseView(tk_root, mock_app_state, {})
        view.on_engine_changed(new_engine)  # 不应抛异常

    def test_start_is_noop_by_default(self, tk_root, mock_app_state):
        """基类 start() 默认为空操作（子类覆写）"""
        view = BaseView(tk_root, mock_app_state, {})
        view.start()  # 不应抛异常
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/gui/test_base_view.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'majsoul_recognizer.gui.base_view'`
（当前环境 tkinter 不可用时: SKIP "tkinter not available"）

- [ ] **Step 3: 实现 `gui/base_view.py`**

```python
"""视图基类 — 统一的生命周期接口

App 通过 BaseView 的 start/stop/on_theme_changed/on_engine_changed
管理视图切换，无需知道具体视图类型。
"""

from __future__ import annotations

import tkinter.ttk as ttk

from majsoul_recognizer.gui.worker import _RecognizeWorker


class BaseView(ttk.Frame):
    """视图基类，定义统一生命周期

    子类:
    - ScreenshotView / LiveView: 调用 _ensure_worker() 创建异步识别线程
    - DevView: 不调用 _ensure_worker()，不创建 Worker
    """

    def __init__(self, parent, app_state, theme: dict, **kwargs):
        super().__init__(parent, **kwargs)
        self._app_state = app_state
        self._theme = theme
        self._worker: _RecognizeWorker | None = None

    def _ensure_worker(self) -> _RecognizeWorker:
        """延迟创建 Worker（仅需要异步识别的视图调用）

        S5: 每次 ensure 通过 pipeline_factory 创建新的 pipeline 实例，
        避免跨视图状态泄漏。
        """
        if self._worker is None:
            pipeline = self._app_state.pipeline_factory()
            self._worker = _RecognizeWorker(
                self._app_state.engine, pipeline
            )
        return self._worker

    def start(self) -> None:
        """视图激活时调用（切换到该视图时）"""

    def stop(self) -> None:
        """视图停用时调用（离开该视图时）"""
        if self._worker is not None:
            self._worker.stop()
            self._worker = None

    def on_theme_changed(self, theme: dict) -> None:
        """主题切换通知"""
        self._theme = theme

    def on_engine_changed(self, engine) -> None:
        """引擎重建通知（设置变更后由 App 调用）"""
        if self._worker is not None:
            self._worker.update_engine(engine)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/gui/test_base_view.py -v`
Expected: 全部 PASS（8 个测试），或 SKIP "tkinter not available"

- [ ] **Step 5: Commit**

```bash
git add src/majsoul_recognizer/gui/base_view.py tests/gui/test_base_view.py
git commit -m "feat(gui): add BaseView with lazy worker creation and lifecycle tests"
```

---

### Task 7: 全量回归测试

- [ ] **Step 1: 运行全部测试**

Run: `pytest tests/ -v`
Expected: 全部 PASS（新增约 20+ 个 GUI 测试 + 原有 222 passing）

- [ ] **Step 2: 确认无 lint 错误**

Run: `ruff check src/majsoul_recognizer/gui/`
Expected: 无输出（无错误）

- [ ] **Step 3: 最终 Commit（如有 lint 修复）**

```bash
git add -A
git commit -m "fix(gui): resolve lint issues in foundation modules"
```

---

## Self-Review

**1. Spec 覆盖率:**
| Spec A 章节 | 对应 Task | 状态 |
|-------------|----------|------|
| §3.1 `__init__.py` 包入口 | Task 1 | ✅ |
| §3.2 `theme.py` 主题系统 | Task 2 | ✅ |
| §3.3 `settings.py` 配置持久化 | Task 3 | ✅ |
| §3.4 `app_state.py` 共享状态 | Task 4 | ✅ |
| §3.5 `base_view.py` 视图基类 | Task 6 | ✅ |
| §3.6 `worker.py` 识别工作线程 | Task 5 | ✅ |
| §4 依赖管理 | Task 1 (pyproject.toml) | ✅ |
| §5 CLI 入口 | Task 1 (cli.py) | ✅ |

**2. 占位符扫描:** 无 TBD/TODO/后续实现。

**3. 类型一致性:** 所有方法签名和属性名与后续 Spec B/C 引用一致（`_ensure_worker()`, `_worker`, `stop()`, `start()`, `on_theme_changed()`, `on_engine_changed()`, `update_engine()`, `submit()`, `get_result()`）。

**4. 评审修复清单:**
| ID | 问题 | 修复 |
|----|------|------|
| C1 | tkinter 不可用导致所有测试失败 | ✅ tkinter 检测移至 main() 函数体 |
| C2 | `_PATH` 实例属性赋值不影响 cls 级别 | ✅ load/save 添加 path 参数 |
| C3 | `dataclasses.fields(RecognitionConfig)` 失败 | ✅ 改用 `RecognitionConfig.model_fields.keys()` |
| S1 | conftest.py tkinter skip 在 import 前无效 | ✅ 简化为仅注册 marker |
| S2 | Worker 测试用 time.sleep 同步脆弱 | ✅ 替换为 _poll_result 轮询 |
| S3 | Task 1 cli.py/pyproject.toml 无精确位置 | ✅ 添加行号和上下文 |
| S4 | Task 6 BaseView 无测试 | ✅ 添加 8 个 mock + tk_root 测试 |
| M1 | theme.py 顶层导入 tkinter | ✅ 延迟导入 + Any 类型 |
| M2 | `_PATH` ClassVar 不可测试 | ✅ load/save 添加 path 参数 |
| M3 | `_make_frame_result` 硬编码时间戳 | ✅ 参数化 timestamp 和 frame_id |
