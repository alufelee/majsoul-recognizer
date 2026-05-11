# GUI 应用层实施计划 (Spec C)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 GUI 应用层：截图视图、实时视图、开发调试视图、设置弹窗、主窗口。

**Architecture:** 5 个视图/应用模块，全部依赖 tkinter。`_FPSCounter` 是唯一可脱离 tkinter 测试的纯逻辑组件（提取到独立模块）。所有 tkinter 测试通过 `pytest.importorskip("tkinter")` 自动跳过。

**Tech Stack:** Python 3.10+, tkinter/ttk, threading, queue, time, pytest

**设计文档:** `docs/superpowers/specs/2026-05-09-gui-spec-c-application.md`

**前置依赖:** Spec A（基础设施）+ Spec B（组件层）已完成

**Spec A 必要修改:** Spec A Task 5 的 `_WorkerResult` 需新增 `detections: list[Detection] = field(default_factory=list)` 字段，`_RecognizeWorker._run()` 需将 engine 返回的 Detection 列表包含在结果中。如果 engine 不暴露 Detection，可暂设为空列表。

**依赖的现有代码:**
- `src/majsoul_recognizer/types.py` — `FrameResult, GameState, Detection, BBox`
- `src/majsoul_recognizer/pipeline.py` — `CapturePipeline(config_path, frame_threshold)`
- `src/majsoul_recognizer/recognition/engine.py` — `RecognitionEngine(config)`
- `src/majsoul_recognizer/recognition/config.py` — `RecognitionConfig`
- `src/majsoul_recognizer/capture/finder.py` — `create_finder() -> WindowFinder`, `WindowInfo(title, x, y, width, height)`
- `src/majsoul_recognizer/capture/screenshot.py` — `ScreenCapture` (context manager, `capture_window(window_info) -> np.ndarray | None`)
- `src/majsoul_recognizer/cli.py` — `format_output(frame, state) -> dict`
- `src/majsoul_recognizer/gui/base_view.py` — `BaseView`（Spec A Task 6）
- `src/majsoul_recognizer/gui/worker.py` — `_RecognizeWorker, _WorkerResult`（Spec A Task 5）
- `src/majsoul_recognizer/gui/widgets/image_canvas.py` — `ImageCanvas`（Spec B Task 2）
- `src/majsoul_recognizer/gui/widgets/result_panel.py` — `ResultPanel`（Spec B Task 3）
- `src/majsoul_recognizer/gui/widgets/colors.py` — `ZONE_COLORS`（Spec B Task 1）

**关键接口速查（来自 Spec A，子代理必读）:**

```python
# gui/worker.py — _WorkerResult（Spec A Task 5）
@dataclass
class _WorkerResult:
    image: np.ndarray | None = None     # 原始 BGR 截图
    frame: FrameResult | None = None     # 管线处理结果
    state: GameState | None = None       # 识别结果
    detections: list[Detection] = field(default_factory=list)  # 原始检测结果
    error: str | None = None
    @property
    def is_error(self) -> bool: return self.error is not None

# gui/worker.py — _RecognizeWorker（Spec A Task 5）
class _RecognizeWorker:
    def __init__(self, engine: RecognitionEngine, pipeline: CapturePipeline): ...
    def submit(self, image: np.ndarray) -> bool  # True=已提交, False=丢弃
    def get_result(self) -> _WorkerResult | None  # None=尚无结果
    def update_engine(self, engine: RecognitionEngine) -> None
    def stop(self) -> None  # join(timeout=2.0)

# gui/base_view.py — BaseView（Spec A Task 6）
class BaseView(ttk.Frame):
    def __init__(self, parent, app_state: AppState, theme: dict, **kwargs): ...
    def _ensure_worker(self) -> _RecognizeWorker  # 延迟创建 Worker
    def start(self) -> None   # 空操作，子类覆盖
    def stop(self) -> None    # 停止 Worker
    def on_theme_changed(self, theme: dict) -> None
    def on_engine_changed(self, engine) -> None

# gui/app_state.py — AppState（Spec A Task 3）
@dataclass
class AppState:
    engine: RecognitionEngine
    pipeline_factory: Callable[[], CapturePipeline]
    config: RecognitionConfig
    theme_name: str  # "dark" | "light"
```

**回调签名约定 [C1 修复]:**
- `on_result` 回调签名: `Callable[[np.ndarray | None, FrameResult, GameState | None, list | None], None]`
- 参数: `(image, frame, state, detections=None)`
- 各视图在 `_poll_result` 中调用: `self._on_result(result.image, result.frame, result.state, detections=...)`

---

## File Structure

```
src/majsoul_recognizer/gui/
├── app.py                    # App 主窗口
├── settings_dialog.py        # SettingsDialog 设置弹窗
├── fps_counter.py            # _FPSCounter 纯逻辑（提取自 live_view.py）
├── views/
│   ├── __init__.py
│   ├── screenshot_view.py    # ScreenshotView
│   ├── live_view.py          # LiveView
│   └── dev_view.py           # DevView

tests/gui/
├── test_fps_counter.py       # 纯逻辑测试，无 tkinter
├── test_screenshot_view.py   # tkinter 测试
├── test_live_view.py         # tkinter 测试
├── test_dev_view.py          # tkinter 测试
├── test_app.py               # tkinter 测试
```

---

### Task 1: views 包骨架 + _FPSCounter 纯逻辑

**Files:**
- Create: `src/majsoul_recognizer/gui/views/__init__.py`
- Create: `src/majsoul_recognizer/gui/fps_counter.py`
- Create: `tests/gui/test_fps_counter.py`

- [ ] **Step 1: 创建 views 包**

```bash
mkdir -p src/majsoul_recognizer/gui/views
touch src/majsoul_recognizer/gui/views/__init__.py
```

- [ ] **Step 2: 编写 _FPSCounter 测试**

`tests/gui/test_fps_counter.py`:
```python
"""FPSCounter 测试 — 纯逻辑，无 tkinter 依赖"""

import time

from majsoul_recognizer.gui.fps_counter import FPSCounter


class TestFPSCounter:
    def test_initial_fps_is_zero(self):
        counter = FPSCounter(window=1.0)
        assert counter.fps == 0.0

    def test_single_tick_fps_is_zero(self):
        counter = FPSCounter(window=1.0)
        counter.tick()
        assert counter.fps == 0.0

    def test_two_ticks_gives_nonzero_fps(self):
        counter = FPSCounter(window=1.0)
        counter.tick()
        time.sleep(0.05)
        counter.tick()
        assert counter.fps > 0.0

    def test_old_ticks_are_pruned(self):
        """超出时间窗口的 tick 被清理"""
        counter = FPSCounter(window=0.1)
        counter.tick()
        time.sleep(0.15)  # 超过窗口
        counter.tick()
        # 只剩 1 个时间戳在窗口内，fps 应为 0
        assert counter.fps == 0.0

    def test_multiple_ticks_in_window(self):
        counter = FPSCounter(window=1.0)
        for _ in range(5):
            counter.tick()
            time.sleep(0.02)
        assert counter.fps > 0.0
        assert counter.fps < 200.0  # 合理上限
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/gui/test_fps_counter.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: 实现 `gui/fps_counter.py`**

```python
"""FPS 计数器

纯逻辑模块，无 tkinter 依赖。
线程安全由 GIL 保证（仅 append + list comprehension）。
"""

from __future__ import annotations

import time


class FPSCounter:
    """简单 FPS 计数器"""

    def __init__(self, window: float = 1.0):
        self._window = window
        self._timestamps: list[float] = []

    def tick(self) -> None:
        now = time.perf_counter()
        self._timestamps.append(now)
        cutoff = now - self._window
        self._timestamps = [t for t in self._timestamps if t > cutoff]

    @property
    def fps(self) -> float:
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        return (len(self._timestamps) - 1) / elapsed if elapsed > 0 else 0.0
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/gui/test_fps_counter.py -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add src/majsoul_recognizer/gui/views/__init__.py src/majsoul_recognizer/gui/fps_counter.py tests/gui/test_fps_counter.py
git commit -m "feat(gui): add views package and FPSCounter"
```

---

### Task 2: ScreenshotView 截图视图

**Files:**
- Create: `src/majsoul_recognizer/gui/views/screenshot_view.py`
- Create: `tests/gui/test_screenshot_view.py`

- [ ] **Step 1: 编写 ScreenshotView 测试**

`tests/gui/test_screenshot_view.py`:
```python
"""ScreenshotView 测试"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk
from unittest.mock import MagicMock, patch

import numpy as np

from majsoul_recognizer.gui.views.screenshot_view import ScreenshotView
from majsoul_recognizer.gui.theme import Theme


@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    yield root
    root.destroy()


@pytest.fixture
def mock_app_state():
    return MagicMock(
        engine=MagicMock(),
        pipeline_factory=lambda: MagicMock(),
        config=MagicMock(),
        theme_name="dark",
    )


@pytest.fixture
def on_result():
    """[C1] 回调签名: (image, frame, state)"""
    return MagicMock()


@pytest.fixture
def view(tk_root, mock_app_state, on_result):
    v = ScreenshotView(tk_root, mock_app_state, Theme.DARK, on_result=on_result)
    v.pack(fill="both", expand=True)
    tk_root.update_idletasks()
    yield v
    v.stop()


class TestScreenshotView:
    def test_creation(self, view):
        assert view._current_image is None
        assert view._is_busy is False

    def test_recognize_submits_to_worker(self, view):
        """识别流程提交图像到 Worker"""
        with patch.object(view, "_ensure_worker") as mock_ensure:
            mock_worker = MagicMock()
            mock_worker.submit.return_value = True
            mock_ensure.return_value = mock_worker

            image = np.zeros((100, 100, 3), dtype=np.uint8)
            view.recognize(image)

            mock_worker.submit.assert_called_once_with(image)
            assert view._is_busy is True

    def test_recognize_busy_rejects(self, view):
        """Worker 忙时拒绝新提交"""
        view._is_busy = True
        with patch.object(view, "_ensure_worker") as mock_ensure:
            mock_worker = MagicMock()
            mock_worker.submit.return_value = False
            mock_ensure.return_value = mock_worker

            image = np.zeros((100, 100, 3), dtype=np.uint8)
            view.recognize(image)

            # 按钮应保持 disabled
            assert view._is_busy is True

    def test_stop_cleans_up(self, view, mock_app_state):
        with patch.object(view, "_ensure_worker"):
            view.stop()
            # 不应抛异常

    def test_on_theme_changed(self, view):
        view.on_theme_changed(Theme.LIGHT)
        assert view._theme is Theme.LIGHT
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/gui/test_screenshot_view.py -v`
Expected: FAIL 或 SKIP "tkinter not available"

- [ ] **Step 3: 实现 `gui/views/screenshot_view.py`**

```python
"""截图模式视图

加载截图文件 → 执行识别 → 展示结果。
支持拖放（tkinterdnd2 可用时）。
"""

from __future__ import annotations

import tkinter as tk
import tkinter.filedialog as filedialog
import tkinter.ttk as ttk

import cv2
import numpy as np

from majsoul_recognizer.gui.base_view import BaseView
from majsoul_recognizer.gui.widgets.image_canvas import ImageCanvas
from majsoul_recognizer.gui.widgets.result_panel import ResultPanel
from majsoul_recognizer.types import FrameResult, GameState

try:
    from tkinterdnd2 import DND_FILES
    _HAS_DND = True
except ImportError:
    _HAS_DND = False


class ScreenshotView(BaseView):
    """截图模式视图"""

    def __init__(self, parent, app_state, theme, on_result=None, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        self._current_image: np.ndarray | None = None
        self._current_frame: FrameResult | None = None
        self._current_state: GameState | None = None
        self._on_result = on_result
        self._is_busy = False

        # 布局: 左侧画布 + 右侧结果面板
        self._canvas = ImageCanvas(self, theme)
        self._canvas.pack(side="left", fill="both", expand=True)

        self._result_panel = ResultPanel(self, theme)
        self._result_panel.pack(side="right", fill="y")

        # 底部工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(side="bottom", fill="x")

        self._open_button = ttk.Button(toolbar, text="打开文件", command=self._on_open_file)
        self._open_button.pack(side="left", padx=4, pady=4)

        self._recognize_button = ttk.Button(toolbar, text="识别", command=self._on_recognize)
        self._recognize_button.pack(side="left", padx=4, pady=4)

        self._status_label = ttk.Label(toolbar, text="就绪")
        self._status_label.pack(side="left", padx=8)

        if _HAS_DND:
            self._canvas.drop_target_register(DND_FILES)
            self._canvas.dnd_bind("<<Drop>>", self._on_drop)

    def recognize(self, image: np.ndarray) -> None:
        """执行识别（含并发保护 [S2]）"""
        worker = self._ensure_worker()
        if not worker.submit(image):
            self._status_label.config(text="正在处理中，请稍候...")
            return
        self._current_image = image
        self._is_busy = True
        self._open_button.config(state="disabled")
        self._recognize_button.config(state="disabled")
        self._status_label.config(text="识别中...")
        self.after(50, self._poll_result)

    def _poll_result(self) -> None:
        if self._worker is None:
            return
        result = self._worker.get_result()
        if result is not None:
            self._is_busy = False
            self._open_button.config(state="normal")
            self._recognize_button.config(state="normal")
            if result.is_error:
                self._status_label.config(text=f"错误: {result.error}")
            else:
                self._current_frame = result.frame
                self._current_state = result.state
                self._update_display(result.image, result.frame, result.state, result.detections)
                self._status_label.config(text="就绪")
                # [C1] 回调传递 image + detections
                if result.frame is not None and self._on_result:
                    self._on_result(result.image, result.frame, result.state,
                                    detections=getattr(result, "detections", []))
        else:
            self.after(50, self._poll_result)

    def _update_display(self, image, frame, state, detections=None) -> None:
        """[S1] 显示图像 + 检测框 + 结果面板"""
        if image is not None:
            # 先设置检测数据，再显示图像（show_image 内部会触发绘制）
            if detections:
                self._canvas.set_detections(detections)
            self._canvas.show_image(image)
        self._result_panel.update_state(state)

    def _on_open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择截图文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp"), ("所有文件", "*.*")],
        )
        if path:
            image = cv2.imread(path)
            if image is not None:
                self._canvas.show_image(image)
                self._current_image = image
                self._status_label.config(text=f"已加载: {path}")
            else:
                self._status_label.config(text="无法读取图像文件")

    def _on_recognize(self) -> None:
        if self._current_image is not None:
            self.recognize(self._current_image)
        else:
            self._status_label.config(text="请先加载截图文件")

    def _on_drop(self, event) -> None:
        path = event.data.strip("{}")
        image = cv2.imread(path)
        if image is not None:
            self._canvas.show_image(image)
            self._current_image = image
            self.recognize(image)

    def on_theme_changed(self, theme: dict) -> None:
        super().on_theme_changed(theme)
        self._canvas.on_theme_changed(theme)
        self._result_panel.on_theme_changed(theme)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/gui/test_screenshot_view.py -v`
Expected: 全部 PASS，或 SKIP "tkinter not available"

- [ ] **Step 5: Commit**

```bash
git add src/majsoul_recognizer/gui/views/screenshot_view.py tests/gui/test_screenshot_view.py
git commit -m "feat(gui): add ScreenshotView with file open and async recognition"
```

---

### Task 3: LiveView 实时视图

**Files:**
- Create: `src/majsoul_recognizer/gui/views/live_view.py`
- Create: `tests/gui/test_live_view.py`

- [ ] **Step 1: 编写 LiveView 测试**

`tests/gui/test_live_view.py`:
```python
"""LiveView 测试"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk
from unittest.mock import MagicMock, patch

from majsoul_recognizer.gui.views.live_view import LiveView
from majsoul_recognizer.gui.theme import Theme


@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    yield root
    root.destroy()


@pytest.fixture
def mock_app_state():
    return MagicMock(
        engine=MagicMock(),
        pipeline_factory=lambda: MagicMock(),
        config=MagicMock(),
        theme_name="dark",
    )


@pytest.fixture
def on_result():
    return MagicMock()


@pytest.fixture
def view(tk_root, mock_app_state, on_result):
    v = LiveView(tk_root, mock_app_state, Theme.DARK, on_result=on_result)
    v.pack(fill="both", expand=True)
    tk_root.update_idletasks()
    yield v
    v.stop()


class TestLiveViewButtonStates:
    """[S3] 按钮状态矩阵"""

    def test_initial_state_is_idle(self, view):
        assert view._state == "idle"

    def test_update_buttons_idle(self, view):
        view._update_buttons("idle")
        assert str(view._start_button.cget("state")) != "disabled"
        assert str(view._pause_button.cget("state")) == "disabled"
        assert str(view._reset_button.cget("state")) == "disabled"

    def test_update_buttons_capturing(self, view):
        view._update_buttons("capturing")
        assert str(view._start_button.cget("state")) == "disabled"
        assert str(view._pause_button.cget("state")) != "disabled"
        assert str(view._reset_button.cget("state")) == "disabled"

    def test_update_buttons_paused(self, view):
        view._update_buttons("paused")
        assert str(view._start_button.cget("state")) != "disabled"
        assert str(view._pause_button.cget("state")) == "disabled"
        assert str(view._reset_button.cget("state")) != "disabled"

    def test_update_buttons_reconnecting(self, view):
        view._update_buttons("reconnecting")
        assert str(view._start_button.cget("state")) == "disabled"
        assert str(view._pause_button.cget("state")) == "disabled"
        assert str(view._reset_button.cget("state")) != "disabled"


class TestLiveViewLifecycle:
    def test_stop_without_start_is_safe(self, view):
        """未启动时 stop 安全返回"""
        view.stop()

    def test_on_theme_changed(self, view):
        view.on_theme_changed(Theme.LIGHT)
        assert view._theme is Theme.LIGHT
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/gui/test_live_view.py -v`
Expected: FAIL 或 SKIP "tkinter not available"

- [ ] **Step 3: 实现 `gui/views/live_view.py`**

```python
"""实时模式视图

连续捕获雀魂窗口画面 → 自动识别 → 实时更新结果。
状态机: 空闲 → 捕获中 → 暂停 → 捕获中
                 ↓ 窗口丢失
               等待重连 → 重置 → 空闲
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import tkinter as tk
import tkinter.ttk as ttk

from majsoul_recognizer.capture.finder import create_finder
from majsoul_recognizer.capture.screenshot import ScreenCapture
from majsoul_recognizer.gui.base_view import BaseView
from majsoul_recognizer.gui.fps_counter import FPSCounter
from majsoul_recognizer.gui.widgets.colors import ZONE_COLORS
from majsoul_recognizer.gui.widgets.image_canvas import ImageCanvas
from majsoul_recognizer.gui.widgets.result_panel import ResultPanel
from majsoul_recognizer.types import FrameResult, GameState

logger = logging.getLogger(__name__)


class LiveView(BaseView):
    """实时模式视图"""

    CAPTURE_INTERVAL = 0.2
    WINDOW_RETRY_INTERVAL = 2.0
    MAX_CONSECUTIVE_FAILS = 10

    def __init__(self, parent, app_state, theme, on_result=None, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        self._capture_thread: threading.Thread | None = None
        self._capture_stop = threading.Event()
        self._status_queue: queue.Queue = queue.Queue()
        self._fps_counter = FPSCounter()
        self._current_state: GameState | None = None
        self._on_result = on_result
        self._state: str = "idle"

        # 画布
        self._canvas = ImageCanvas(self, theme)
        self._canvas.pack(side="top", fill="both", expand=True)

        # 结果面板（紧凑模式）
        self._result_panel = ResultPanel(self, theme)
        self._result_panel.pack(side="top", fill="x")

        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(side="bottom", fill="x")

        self._start_button = ttk.Button(toolbar, text="开始", command=self._on_start)
        self._start_button.pack(side="left", padx=4, pady=4)

        self._pause_button = ttk.Button(toolbar, text="暂停", command=self._on_pause)
        self._pause_button.pack(side="left", padx=4, pady=4)

        self._reset_button = ttk.Button(toolbar, text="重置", command=self._on_reset)
        self._reset_button.pack(side="left", padx=4, pady=4)

        self._fps_label = ttk.Label(toolbar, text="FPS: --")
        self._fps_label.pack(side="right", padx=8)

        self._status_label = ttk.Label(toolbar, text="就绪")
        self._status_label.pack(side="right", padx=8)

        self._update_buttons("idle")

    # --- 状态机按钮管理 [S3] ---

    def _update_buttons(self, state: str) -> None:
        self._start_button.config(state="normal" if state in ("idle", "paused") else "disabled")
        self._pause_button.config(state="normal" if state == "capturing" else "disabled")
        self._reset_button.config(state="normal" if state in ("paused", "reconnecting") else "disabled")
        self._state = state

    # --- 按钮回调 ---

    def _on_start(self) -> None:
        self._capture_stop.clear()
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        self._update_buttons("capturing")
        self.after(50, self._poll_result)

    def _on_pause(self) -> None:
        self._capture_stop.set()
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        self._update_buttons("paused")

    def _on_reset(self) -> None:
        self._capture_stop.set()
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        self._fps_counter = FPSCounter()
        self._canvas.clear()
        self._result_panel.update_state(None)
        self._current_state = None
        self._fps_label.config(text="FPS: --")
        self._status_label.config(text="就绪")
        self._update_buttons("idle")

    # --- 捕获线程 [C4] ---

    def _capture_loop(self) -> None:
        try:
            try:
                finder = create_finder()
            except RuntimeError:
                self._status_queue.put(("unsupported_platform", None))
                return

            with ScreenCapture() as capture:
                window = None
                consecutive_fails = 0

                while not self._capture_stop.is_set():
                    t0 = time.perf_counter()

                    if window is None:
                        window = finder.find_window()
                        if window is None:
                            self._status_queue.put(("window_not_found", None))
                            self._capture_stop.wait(self.WINDOW_RETRY_INTERVAL)
                            continue

                    image = capture.capture_window(window)
                    if image is None:
                        consecutive_fails += 1
                        if consecutive_fails >= self.MAX_CONSECUTIVE_FAILS:
                            window = None
                            consecutive_fails = 0
                        self._capture_stop.wait(0.1)
                        continue

                    consecutive_fails = 0
                    worker = self._ensure_worker()
                    worker.submit(image)
                    self._fps_counter.tick()

                    elapsed = time.perf_counter() - t0
                    remaining = max(0, self.CAPTURE_INTERVAL - elapsed)
                    self._capture_stop.wait(remaining)
        except Exception as e:
            self._status_queue.put(("capture_error", str(e)))

    # --- 结果轮询 ---

    def _poll_result(self) -> None:
        if self._state not in ("capturing", "reconnecting"):
            return

        # 处理状态队列消息
        while True:
            try:
                status_type, detail = self._status_queue.get_nowait()
                if status_type == "window_not_found":
                    self._status_label.config(text="未找到雀魂窗口，2秒后重试...")
                    self._update_buttons("reconnecting")
                elif status_type == "unsupported_platform":
                    self._status_label.config(text="不支持的平台")
                    self._update_buttons("idle")
                    return
                elif status_type == "capture_error":
                    self._status_label.config(text=f"捕获错误: {detail}")
                    self._update_buttons("idle")
                    return
            except queue.Empty:
                break

        # 处理识别结果
        if self._worker:
            result = self._worker.get_result()
            if result is not None and not result.is_error:
                if result.image is not None:
                    self._canvas.show_image(result.image)
                self._current_state = result.state
                self._result_panel.update_state(result.state)
                if result.frame is not None and self._on_result:
                    # [C1] 回调传递 image + detections
                    self._on_result(result.image, result.frame, result.state,
                                    detections=getattr(result, "detections", []))
                self._status_label.config(text="捕获中")
        fps = self._fps_counter.fps
        self._fps_label.config(text=f"FPS: {fps:.1f}")

        self.after(50, self._poll_result)

    # --- 生命周期 ---

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        self._capture_stop.set()
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        super().stop()

    def on_theme_changed(self, theme: dict) -> None:
        super().on_theme_changed(theme)
        self._canvas.on_theme_changed(theme)
        self._result_panel.on_theme_changed(theme)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/gui/test_live_view.py -v`
Expected: 全部 PASS，或 SKIP "tkinter not available"

- [ ] **Step 5: Commit**

```bash
git add src/majsoul_recognizer/gui/views/live_view.py tests/gui/test_live_view.py
git commit -m "feat(gui): add LiveView with state machine and capture thread"
```

---

### Task 4: DevView 开发调试视图

**Files:**
- Create: `src/majsoul_recognizer/gui/views/dev_view.py`
- Create: `tests/gui/test_dev_view.py`

- [ ] **Step 1: 编写 DevView 测试**

`tests/gui/test_dev_view.py`:
```python
"""DevView 测试"""

import json

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk
from unittest.mock import MagicMock

import numpy as np

from majsoul_recognizer.gui.views.dev_view import DevView
from majsoul_recognizer.gui.theme import Theme
from majsoul_recognizer.types import FrameResult, GameState, RoundInfo


@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    yield root
    root.destroy()


@pytest.fixture
def mock_app_state():
    return MagicMock(
        engine=MagicMock(),
        pipeline_factory=lambda: MagicMock(),
        config=MagicMock(),
        theme_name="dark",
    )


@pytest.fixture
def view(tk_root, mock_app_state):
    v = DevView(tk_root, mock_app_state, Theme.DARK)
    v.pack(fill="both", expand=True)
    tk_root.update_idletasks()
    yield v
    v.stop()


def _make_frame_result():
    return FrameResult(
        frame_id=1,
        timestamp="2026-05-09T00:00:00Z",
        zones={"hand": np.zeros((100, 100, 3), dtype=np.uint8)},
        is_static=True,
    )


def _make_game_state():
    return GameState(
        round_info=RoundInfo(wind="东", number=1, honba=0, kyotaku=0),
        hand=["1m", "2m"],
    )


class TestDevView:
    def test_creation(self, view):
        assert view._current_image is None

    def test_set_current_image(self, view):
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        view.set_current_image(image)
        assert view._current_image is not None

    def test_update_data_writes_json(self, view):
        """update_data 写入 JSON 输出"""
        view.set_current_image(np.zeros((200, 200, 3), dtype=np.uint8))
        frame = _make_frame_result()
        state = _make_game_state()
        view.update_data(frame, state)

        content = view._json_text.get("1.0", "end")
        data = json.loads(content)
        assert data["is_static"] is True
        assert data["frame_id"] == 1

    def test_update_data_with_detections(self, view):
        """[C2] 检测框数据传递到画布"""
        from majsoul_recognizer.types import BBox, Detection
        view.set_current_image(np.zeros((200, 200, 3), dtype=np.uint8))
        frame = _make_frame_result()
        dets = [Detection(bbox=BBox(x=10, y=20, width=30, height=40),
                          tile_code="1m", confidence=0.95)]
        view.update_data(frame, None, detections=dets)
        assert len(view._det_canvas._detections) == 1

    def test_update_data_shows_perf(self, view):
        view.set_current_image(np.zeros((200, 200, 3), dtype=np.uint8))
        frame = _make_frame_result()
        view.update_data(frame, None)

        perf_text = view._perf_label.cget("text")
        assert "帧: 1" in perf_text

    def test_start_is_noop_without_data(self, view):
        """无数据时 start 安全"""
        view.start()

    def test_stop_is_safe(self, view):
        view.stop()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/gui/test_dev_view.py -v`
Expected: FAIL 或 SKIP "tkinter not available"

- [ ] **Step 3: 实现 `gui/views/dev_view.py`**

```python
"""开发调试视图

展示区域分割图 + 检测框可视化 + JSON 输出 + 性能统计。
不使用 Worker（由 App 通过 update_data 推送数据）。
"""

from __future__ import annotations

import json
import logging
import sys

import numpy as np
import tkinter as tk
import tkinter.ttk as ttk

from majsoul_recognizer.cli import format_output
from majsoul_recognizer.gui.base_view import BaseView
from majsoul_recognizer.gui.widgets.colors import ZONE_COLORS
from majsoul_recognizer.gui.widgets.image_canvas import ImageCanvas
from majsoul_recognizer.types import FrameResult, GameState

logger = logging.getLogger(__name__)


class DevView(BaseView):
    """开发调试视图"""

    def __init__(self, parent, app_state, theme, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        self._current_image: np.ndarray | None = None

        # 上半部分: 两个画布并排
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(side="top", fill="both", expand=True)

        self._zone_canvas = ImageCanvas(canvas_frame, theme)
        self._zone_canvas.pack(side="left", fill="both", expand=True)

        self._det_canvas = ImageCanvas(canvas_frame, theme)
        self._det_canvas.pack(side="left", fill="both", expand=True)

        # JSON 输出
        json_frame = ttk.Frame(self)
        json_frame.pack(side="top", fill="both", expand=True)

        # [M2] 使用顶部 import sys，不内联 __import__
        mono = "Menlo" if sys.platform == "darwin" else "Consolas"
        self._json_text = tk.Text(json_frame, wrap="none", state="disabled",
                                  font=(mono, 10),
                                  bg=theme["bg_secondary"], fg=theme["fg_primary"],
                                  height=8)
        json_scroll = ttk.Scrollbar(json_frame, orient="vertical", command=self._json_text.yview)
        self._json_text.configure(yscrollcommand=json_scroll.set)
        self._json_text.pack(side="left", fill="both", expand=True)
        json_scroll.pack(side="right", fill="y")

        # 底部: 性能 + 复制按钮
        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x")

        self._perf_label = ttk.Label(bottom, text="性能: --")
        self._perf_label.pack(side="left", padx=4, pady=4)

        self._copy_button = ttk.Button(bottom, text="复制 JSON", command=self._copy_json)
        self._copy_button.pack(side="right", padx=4, pady=4)

    def set_current_image(self, image: np.ndarray) -> None:
        """设置当前显示的原始图像"""
        self._current_image = image

    def update_data(self, frame: FrameResult, state: GameState | None,
                    detections: list | None = None) -> None:
        """[C2] 接收 FrameResult + GameState + Detection 列表，更新所有子组件"""
        # 1. 区域标注画布
        if self._current_image is not None:
            h, w = self._current_image.shape[:2]
            zone_rects = self._compute_zone_rects(w, h)

            # [C2] 先 set_zones/set_detections，再 show_image（内部触发绘制）
            self._zone_canvas.set_zones(zone_rects, ZONE_COLORS)
            self._zone_canvas.show_image(self._current_image)
            self._zone_canvas.set_mode("zones")

            # 检测框画布
            if detections:
                self._det_canvas.set_detections(detections)
            self._det_canvas.show_image(self._current_image)
            self._det_canvas.set_mode("detection")

        # 2. JSON 输出
        output = format_output(frame, state)
        self._json_text.config(state="normal")
        self._json_text.delete("1.0", "end")
        self._json_text.insert("1.0", json.dumps(output, indent=2, ensure_ascii=False))
        self._json_text.config(state="disabled")

        # 3. 性能统计
        self._perf_label.config(
            text=f"帧: {frame.frame_id} | {'静态' if frame.is_static else '动画'}"
        )

    def _compute_zone_rects(self, img_w: int, img_h: int) -> dict[str, tuple]:
        """[C2] 从 zone 配置计算像素坐标区域矩形

        从 app_state.config 获取 zone 定义路径，
        加载 ZoneDefinition 列表，调用 to_bbox() 转像素坐标。
        返回 {zone_name.value: (x, y, w, h)} 格式。
        """
        try:
            from majsoul_recognizer.zones.config import load_zone_config
            from pathlib import Path

            config_path = getattr(self._app_state.config, "config_path", None)
            if config_path is None:
                return {}
            zone_config = load_zone_config(Path(config_path))
            result = {}
            for zd in zone_config.zones:
                bbox = zd.to_bbox(img_w, img_h)
                result[zd.name.value] = (bbox.x, bbox.y, bbox.width, bbox.height)
            return result
        except Exception:
            logger.debug("Failed to compute zone rects", exc_info=True)
            return {}

    def _copy_json(self) -> None:
        text = self._json_text.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(text)

    def on_theme_changed(self, theme: dict) -> None:
        super().on_theme_changed(theme)
        self._zone_canvas.on_theme_changed(theme)
        self._det_canvas.on_theme_changed(theme)
        self._json_text.configure(bg=theme["bg_secondary"], fg=theme["fg_primary"])
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/gui/test_dev_view.py -v`
Expected: 全部 PASS，或 SKIP "tkinter not available"

- [ ] **Step 5: Commit**

```bash
git add src/majsoul_recognizer/gui/views/dev_view.py tests/gui/test_dev_view.py
git commit -m "feat(gui): add DevView with zone overlay, JSON output, and perf stats"
```

---

### Task 5: SettingsDialog + App 主窗口

**Files:**
- Create: `src/majsoul_recognizer/gui/settings_dialog.py`
- Create: `src/majsoul_recognizer/gui/app.py`
- Create: `tests/gui/test_app.py`

- [ ] **Step 1: 实现 `gui/settings_dialog.py`**

```python
"""设置弹窗"""

from __future__ import annotations

import dataclasses
import tkinter as tk
import tkinter.ttk as ttk
from typing import Callable

from majsoul_recognizer.gui.settings import GUISettings


class SettingsDialog:
    """设置弹窗

    独立 Toplevel 对话框，管理可配置项。
    关闭时检测未保存修改并自动应用 [M4]。
    """

    def __init__(self, parent: tk.Tk, settings: GUISettings,
                 on_apply: Callable[[], None]):
        self._dialog = tk.Toplevel(parent)
        self._dialog.title("设置")
        self._dialog.geometry("480x520")
        self._dialog.transient(parent)
        self._dialog.grab_set()
        self._settings = settings
        self._on_apply = on_apply
        self._initial_snapshot = dataclasses.asdict(settings)
        self._fields: dict[str, tk.Variable] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self._dialog, padding=12)
        main.pack(fill="both", expand=True)

        row = 0
        # 识别设置
        row = self._add_section(main, row, "识别设置")
        row = self._add_field(main, row, "模型路径", "model_path", self._settings.model_path or "")
        row = self._add_field(main, row, "模板目录", "template_dir", self._settings.template_dir or "")
        row = self._add_field(main, row, "区域配置", "config_path", self._settings.config_path or "")
        row = self._add_field(main, row, "检测置信度", "detection_confidence",
                              str(self._settings.detection_confidence))
        row = self._add_field(main, row, "NMS IoU 阈值", "nms_iou_threshold",
                              str(self._settings.nms_iou_threshold))

        # GUI 偏好
        row = self._add_section(main, row, "界面偏好")
        row = self._add_field(main, row, "捕获间隔(ms)", "capture_interval_ms",
                              str(self._settings.capture_interval_ms))

        # 主题选择
        row = self._add_section(main, row, "主题")
        self._theme_var = tk.StringVar(value=self._settings.theme)
        theme_frame = ttk.Frame(main)
        theme_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Radiobutton(theme_frame, text="深色", variable=self._theme_var, value="dark").pack(side="left")
        ttk.Radiobutton(theme_frame, text="浅色", variable=self._theme_var, value="light").pack(side="left")
        row += 1

        # 按钮
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=12)
        ttk.Button(btn_frame, text="应用", command=self._on_apply_clicked).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="关闭", command=self._on_close_clicked).pack(side="left", padx=4)

    def _add_section(self, parent, row, title) -> int:
        ttk.Label(parent, text=title, font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(8, 2))
        return row + 1

    def _add_field(self, parent, row, label, key, default) -> int:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(default))
        entry = ttk.Entry(parent, textvariable=var, width=40)
        entry.grid(row=row, column=1, sticky="ew", pady=2, padx=(8, 0))
        self._fields[key] = var
        return row + 1

    def _sync_to_settings(self) -> None:
        """从 UI 字段同步到 settings"""
        for key, var in self._fields.items():
            value = var.get()
            field_type = type(getattr(self._settings, key, ""))
            if value == "" and key.endswith("_path"):
                setattr(self._settings, key, None)
            elif field_type == float:
                try:
                    setattr(self._settings, key, float(value))
                except ValueError:
                    pass
            elif field_type == int:
                try:
                    setattr(self._settings, key, int(value))
                except ValueError:
                    pass
            else:
                setattr(self._settings, key, value)
        self._settings.theme = self._theme_var.get()

    def _on_apply_clicked(self) -> None:
        self._sync_to_settings()
        self._settings.save()
        self._on_apply()
        self._initial_snapshot = dataclasses.asdict(self._settings)

    def _on_close_clicked(self) -> None:
        self._sync_to_settings()
        if dataclasses.asdict(self._settings) != self._initial_snapshot:
            self._settings.save()
            self._on_apply()
        self._dialog.destroy()
```

- [ ] **Step 2: 编写 App 测试**

`tests/gui/test_app.py`:
```python
"""App 主窗口测试"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

import tkinter as tk
from unittest.mock import MagicMock, patch

from majsoul_recognizer.gui.app import App
from majsoul_recognizer.gui.theme import Theme


class TestAppCreation:
    """App 创建测试（不启动 mainloop）"""

    def test_app_creates_root(self):
        with patch("majsoul_recognizer.gui.app.GUISettings") as MockSettings:
            mock_settings = MagicMock()
            mock_settings.theme = "dark"
            mock_settings.window_width = 800
            mock_settings.window_height = 600
            mock_settings.window_x = 0
            mock_settings.window_y = 0
            mock_settings.to_recognition_config.return_value = MagicMock()
            MockSettings.load.return_value = mock_settings

            with patch("majsoul_recognizer.gui.app.RecognitionEngine"):
                app = App()
                assert app._root is not None
                assert app._root.title() != ""
                app._root.destroy()
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/gui/test_app.py -v`
Expected: FAIL 或 SKIP "tkinter not available"

- [ ] **Step 4: 实现 `gui/app.py`**

```python
"""主窗口 — 应用入口

创建 Tkinter 根窗口，管理侧边栏导航，切换视图，维护全局状态。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import numpy as np
import tkinter as tk
import tkinter.ttk as ttk

from majsoul_recognizer.gui.settings import GUISettings
from majsoul_recognizer.gui.settings_dialog import SettingsDialog
from majsoul_recognizer.gui.app_state import AppState
from majsoul_recognizer.gui.theme import Theme, apply_style, get_theme
from majsoul_recognizer.gui.views.screenshot_view import ScreenshotView
from majsoul_recognizer.gui.views.live_view import LiveView
from majsoul_recognizer.gui.views.dev_view import DevView
from majsoul_recognizer.pipeline import CapturePipeline
from majsoul_recognizer.recognition.engine import RecognitionEngine
from majsoul_recognizer.types import Detection, FrameResult, GameState

logger = logging.getLogger(__name__)


class App:
    """主窗口"""

    WINDOW_MIN_WIDTH = 960
    WINDOW_MIN_HEIGHT = 640
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 800
    SIDEBAR_WIDTH = 64

    NAV_ITEMS = [
        ("截图", "screenshot"),
        ("实时", "live"),
        ("调试", "dev"),
    ]

    def __init__(self) -> None:
        self._settings = GUISettings.load()
        theme = get_theme(self._settings.theme)

        # 创建根窗口 [M6]
        self._root = self._create_root()
        self._root.title("雀魂麻将识别助手 v0.1")
        self._root.geometry(
            f"{self._settings.window_width}x{self._settings.window_height}"
            f"+{self._settings.window_x}+{self._settings.window_y}"
        )
        self._root.minsize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)

        # 应用主题
        style = ttk.Style()
        apply_style(style, theme)

        # 创建 UI 组件
        self._build_ui(theme)

        # [S2] 初始化引擎 — 失败时降级而非崩溃
        config = self._settings.to_recognition_config()
        try:
            engine = RecognitionEngine(config)
        except Exception as e:
            logger.warning("Engine init failed (degraded mode): %s", e)
            engine = None  # type: ignore[assignment]
            self._status_label.config(text="检测器降级模式")

        # [M1] 使用顶部 from pathlib import Path
        self._app_state = AppState(
            engine=engine,
            pipeline_factory=lambda: CapturePipeline(
                config_path=Path(self._settings.config_path) if self._settings.config_path else None,
            ),
            config=config,
            theme_name=self._settings.theme,
        )

        # 创建视图
        on_result = self._make_on_result()
        self._views: dict[str, ttk.Frame] = {
            "screenshot": ScreenshotView(self._content, self._app_state, theme, on_result=on_result),
            "live": LiveView(self._content, self._app_state, theme, on_result=on_result),
            "dev": DevView(self._content, self._app_state, theme),
        }

        # [C1] 缓存数据 — 包含 image 和 detections
        self._last_frame: FrameResult | None = None
        self._last_state: GameState | None = None
        self._last_image: np.ndarray | None = None
        self._last_detections: list[Detection] = []
        self._active_view = None

        # 显示默认视图
        self._switch_view("screenshot")

    def _create_root(self) -> tk.Tk:
        """[M6] tkinterdnd2 可用时使用 TkinterDnD.Tk()"""
        try:
            from tkinterdnd2 import TkinterDnD
            return TkinterDnD.Tk()
        except ImportError:
            return tk.Tk()

    def _build_ui(self, theme: dict) -> None:
        # 标题栏
        header = ttk.Frame(self._root)
        header.pack(side="top", fill="x")
        ttk.Label(header, text="雀魂麻将识别助手 v0.1",
                  font=("", 12, "bold")).pack(side="left", padx=8, pady=4)
        ttk.Button(header, text="切换主题", command=self._toggle_theme).pack(side="right", padx=4)
        ttk.Button(header, text="设置", command=self._show_settings).pack(side="right", padx=4)

        # 中间: 侧边栏 + 内容区
        body = ttk.Frame(self._root)
        body.pack(side="top", fill="both", expand=True)

        # 侧边栏
        sidebar = ttk.Frame(body, width=self.SIDEBAR_WIDTH, style="Sidebar.TFrame")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self._nav_buttons: dict[str, ttk.Button] = {}
        for label, view_name in self.NAV_ITEMS:
            btn = ttk.Button(sidebar, text=label, style="Sidebar.TButton",
                             command=lambda n=view_name: self._switch_view(n))
            btn.pack(fill="x", padx=4, pady=8)
            self._nav_buttons[view_name] = btn

        # [S3] 内容区 — 使用 grid() 放置视图（与 Spec 一致）
        self._content = ttk.Frame(body)
        self._content.pack(side="left", fill="both", expand=True)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # 状态栏
        status_bar = ttk.Frame(self._root)
        status_bar.pack(side="bottom", fill="x")
        self._status_dot = tk.Canvas(status_bar, width=12, height=12,
                                     bg=theme["bg_primary"], highlightthickness=0)
        self._status_dot.pack(side="left", padx=4, pady=4)
        self._status_dot.create_oval(2, 2, 10, 10, fill=theme["success"], outline="")
        self._status_label = ttk.Label(status_bar, text="就绪", style="Status.TLabel")
        self._status_label.pack(side="left")
        self._status_info = ttk.Label(status_bar, text="", style="Status.TLabel")
        self._status_info.pack(side="right", padx=8)

    def _switch_view(self, view_name: str) -> None:
        # [S3] 使用 grid_remove() / grid() 替代 pack_forget() / pack()
        if self._active_view:
            self._active_view.stop()
            self._active_view.grid_remove()

        self._active_view = self._views[view_name]
        self._active_view.grid(row=0, column=0, sticky="nsew", in_=self._content)
        self._active_view.start()

        # [C1] DevView 激活时推送缓存数据（含 image + detections）
        if view_name == "dev" and self._last_frame is not None:
            if hasattr(self._active_view, "set_current_image") and self._last_image is not None:
                self._active_view.set_current_image(self._last_image)
            if hasattr(self._active_view, "update_data"):
                self._active_view.update_data(
                    self._last_frame, self._last_state,
                    detections=self._last_detections,
                )

    # [C1] 回调签名: (image, frame, state) — 各视图 _poll_result 调用时传递
    def _make_on_result(self) -> Callable[[np.ndarray | None, FrameResult, GameState | None], None]:
        def on_result(image: np.ndarray | None, frame: FrameResult, state: GameState | None,
                      detections: list | None = None):
            self._last_frame = frame
            self._last_state = state
            if image is not None:
                self._last_image = image
            if detections is not None:
                self._last_detections = detections
            # DevView 活跃时推送数据
            if isinstance(self._active_view, DevView):
                self._active_view.update_data(frame, state, detections=detections or [])
        return on_result

    def _toggle_theme(self) -> None:
        new_name = "light" if self._app_state.theme_name == "dark" else "dark"
        new_theme = get_theme(new_name)
        self._app_state.theme_name = new_name
        self._settings.theme = new_name

        style = ttk.Style()
        apply_style(style, new_theme)

        for view in self._views.values():
            view.on_theme_changed(new_theme)
        self._settings.save()

    def _show_settings(self) -> None:
        SettingsDialog(self._root, self._settings, self._rebuild_engine)

    def _rebuild_engine(self) -> None:
        self._settings.save()
        config = self._settings.to_recognition_config()
        try:
            new_engine = RecognitionEngine(config)
            self._app_state.engine = new_engine
            for view in self._views.values():
                view.on_engine_changed(new_engine)
        except Exception as e:
            logger.error("Engine rebuild failed: %s", e)

    def run(self) -> None:
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    def _on_close(self) -> None:
        for view in self._views.values():
            view.stop()
        self._settings.window_width = self._root.winfo_width()
        self._settings.window_height = self._root.winfo_height()
        self._settings.window_x = self._root.winfo_x()
        self._settings.window_y = self._root.winfo_y()
        self._settings.save()
        self._root.destroy()
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/gui/test_app.py -v`
Expected: PASS 或 SKIP "tkinter not available"

- [ ] **Step 6: 运行全量测试**

Run: `pytest tests/ -v --timeout=30`
Expected: 全部 PASS（含 Spec A + B + C 所有测试）

- [ ] **Step 7: Commit**

```bash
git add src/majsoul_recognizer/gui/settings_dialog.py src/majsoul_recognizer/gui/app.py tests/gui/test_app.py
git commit -m "feat(gui): add App main window, SettingsDialog, and view switching"
```

---

### Task 6: 集成验证 + lint

- [ ] **Step 1: 运行全部测试**

Run: `pytest tests/ -v --timeout=30`
Expected: 全部 PASS（含新增 GUI 测试 + 原有测试）

- [ ] **Step 2: 确认无 lint 错误**

Run: `ruff check src/majsoul_recognizer/gui/`
Expected: 无输出

- [ ] **Step 3: 最终 Commit（如有 lint 修复）**

```bash
git add -A
git commit -m "fix(gui): resolve lint issues in application layer"
```

---

## Self-Review

**1. Spec 覆盖率:**
| Spec C 章节 | 对应 Task | 状态 |
|-------------|----------|------|
| §1 App 主窗口 | Task 5 | ✅ |
| §2 SettingsDialog | Task 5 | ✅ |
| §3 ScreenshotView | Task 2 | ✅ |
| §3 检测框显示 [S1] | Task 2 (_update_display) | ✅ |
| §4 LiveView | Task 3 | ✅ |
| §4 _FPSCounter | Task 1 | ✅ |
| §4 按钮状态矩阵 [S3] | Task 3 | ✅ |
| §5 DevView | Task 4 | ✅ |
| §5 update_data [C2] | Task 4 (_compute_zone_rects + set_zones/set_detections) | ✅ |
| §5 区域标注 [C2] | Task 4 (_compute_zone_rects) | ✅ |
| §5 检测框可视化 [C2] | Task 4 (detections 参数) | ✅ |
| §6 错误处理: Engine 初始化 [S2] | Task 5 (try/except 降级) | ✅ |
| §6 错误处理: 其他 | 各 Task 内 | ✅ |
| §1 M6 tkinterdnd2 条件初始化 | Task 5 (_create_root) | ✅ |
| §1 _rebuild_engine | Task 5 | ✅ |
| §1 P4 on_result 回调 [C1] | Task 5 (_make_on_result) | ✅ |
| §1 布局管理 grid() [S3] | Task 5 (_switch_view + _build_ui) | ✅ |

**2. 占位符扫描:** 无 TBD/TODO。

**3. 类型一致性:**
- `BaseView.__init__(parent, app_state, theme, **kwargs)` — 所有视图继承一致
- `ScreenshotView.__init__(..., on_result=)` — 与 `LiveView.__init__(..., on_result=)` 一致
- `[C1] on_result` 回调签名: `(image: np.ndarray | None, frame: FrameResult, state: GameState | None, detections: list | None)` — ScreenshotView/LiveView/App 一致
- `[C2] DevView.update_data(frame, state, detections=)` — 与 `App._make_on_result()` 回调匹配
- `DevView.set_current_image(image)` — 与 `App._switch_view` 调用匹配
- `DevView._compute_zone_rects(img_w, img_h)` — 返回 `{name: (x,y,w,h)}` 与 `ImageCanvas.set_zones()` 匹配
- `LiveView._update_buttons(state)` — 4 状态 × 3 按钮矩阵与 Spec C §4 一致
- `SettingsDialog.__init__(parent, settings, on_apply)` — 与 `App._show_settings()` 调用匹配
- `App._on_close()` 保存窗口几何到 `GUISettings` — 与 `GUISettings` 字段匹配
- `[S2] App.__init__` engine 降级 — engine=None 时 AppState.engine 为 None，各视图通过 `_ensure_worker` 懒加载，不会立即崩溃
- `[M4]` 接口速查已内联在头部，子代理可直接使用

**4. 评审修复记录:**
| ID | 修复位置 | 变更摘要 |
|----|---------|---------|
| C1 | App._make_on_result, ScreenshotView/LiveView._poll_result | 回调签名增加 image + detections 参数 |
| C2 | DevView.update_data, DevView._compute_zone_rects | 实现 zone 坐标计算 + set_zones/set_detections 调用 |
| S1 | ScreenshotView._update_display | 增加 detections 参数，调用 set_detections |
| S2 | App.__init__ engine 创建 | 增加 try/except 降级处理 |
| S3 | App._switch_view, App._build_ui | grid_remove()/grid() 替代 pack_forget()/pack() |
| M1 | App imports | `from pathlib import Path` 替代 `__import__("pathlib")` |
| M2 | DevView imports | `import sys` 替代 `__import__("sys")` |
| M3 | LiveView.start() | 保持手动启动（优于 spec 的自动启动） |
| M4 | 计划头部 | 添加 _WorkerResult/_RecognizeWorker/BaseView/AppState 内联接口定义 |
