# GUI 子规格 A — 基础设施

> 日期: 2026-05-09
> 主设计文档: `docs/superpowers/specs/2026-05-08-gui-design.md`（以下简称"主文档"）
> 本文档为主文档的切片，仅包含基础设施层模块的详细设计。

## 涵盖范围

| 模块 | 文件 | 对应主文档章节 |
|------|------|--------------|
| 概述 + 架构 | — | §1, §2 |
| 主题系统 | `gui/theme.py` | §3.4 |
| 配置持久化 | `gui/settings.py` | §3.5 |
| 视图基类 | `gui/base_view.py` | §3.1 |
| 识别工作线程 | `gui/worker.py` | §3.2 |
| 包入口 | `gui/__init__.py` | §5 |
| 依赖管理 | `pyproject.toml` | §4 |

## 1. 概述（摘要）

为雀魂麻将识别助手添加 Tkinter 桌面 GUI，支持开发调试和实时辅助双场景。

**平台约束**: macOS + Windows，Python 3.10+。

**环境前置**:
- tkinter 必须可用（macOS: `brew install python-tk@3.14`）
- onnxruntime 不可用时使用 `_StubDetector` 降级
- PaddleOCR 不可用时分数/局次/计时器返回 None
- tkinterdnd2 为实验性可选依赖

## 2. 架构（摘要）

### 2.1 模块结构

```
src/majsoul_recognizer/gui/
├── __init__.py               # 入口 + main()
├── app.py                    # [子规格 C]
├── base_view.py              # 视图基类
├── worker.py                 # 识别工作线程
├── theme.py                  # 主题系统
├── settings.py               # 配置持久化
├── settings_dialog.py        # [子规格 C]
├── views/                    # [子规格 C]
└── widgets/                  # [子规格 B]
```

### 2.2 整体布局

```
┌──────────────────────────────────────────────┐
│ 标题栏: 雀魂麻将识别助手 v0.1   [主题] [设置]  │
├──────┬───────────────────────────────────────┤
│      │                                       │
│ 截图 │         主视图区域                      │
│      │    (根据侧边栏选择切换)                  │
│ 实时 │                                       │
│      │                                       │
│ 调试 │                                       │
├──────┴───────────────────────────────────────┤
│ 状态栏: ●就绪 | FPS: 5.2 | 延迟: 180ms | 帧: 42│
└──────────────────────────────────────────────┘
```

侧边栏: 文字标签（"截图"/"实时"/"调试"），宽度固定 64px。

### 2.3 依赖关系

```
app.py
  ├── base_view.py (BaseView)
  ├── worker.py (_RecognizeWorker + _WorkerResult)
  ├── theme.py (ttk.Style 主题)
  ├── settings.py (配置持久化)
  ├── views/* extends BaseView
  │     ├── worker.py
  │     └── widgets/*
  └── views/dev_view.py extends BaseView (no Worker)
```

### 2.4 数据流（截图模式）

```
用户操作 → cv2.imread → worker.submit(image)
    → [识别线程] CapturePipeline.process_image → RecognitionEngine.recognize
    → result_queue → root.after(50) 轮询 → View.update()
```

### 2.5 数据流（实时模式）

```
[捕获线程] _live_loop() → ScreenCapture → worker.submit(image)
    → [识别线程] pipeline + engine
    → result_queue → root.after(50) 轮询 → LiveView.update()
```

## 3. 模块详细设计

### 3.1 `gui/__init__.py` — 包入口

```python
"""GUI 入口"""
try:
    import tkinter  # noqa: F401 — 检测 tkinter 可用性
except ImportError:
    raise SystemExit(
        "tkinter 不可用。macOS: brew install python-tk@3.14\n"
        "Windows: tkinter 随 Python 安装包自带。"
    )

def main() -> None:
    from majsoul_recognizer.gui.app import App
    app = App()
    app.run()
```

**CLI 入口** (`cli.py` 新增):
```python
elif args.command == "gui":
    from majsoul_recognizer.gui import main
    main()
```

### 3.2 `gui/theme.py` — 主题系统

**职责**: 通过 `ttk.Style` 统一管理深色/浅色主题。

**核心原则**: 不做递归遍历子组件。使用 `ttk.Style.configure()` 统一设置样式类，`tk` 组件在创建时读取当前主题颜色。Canvas 在 `redraw()` 时从 `theme` 字典读取颜色。

```python
class Theme:
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
```

**接口**:
```python
def apply_style(style: ttk.Style, theme: dict[str, str]) -> None:
    """将主题应用到 ttk.Style 全局样式"""

def get_theme(name: str) -> dict[str, str]:
    """获取主题颜色方案。返回 DARK 或 LIGHT 类属性 dict"""
```

**切换流程**:
1. 用户点击主题按钮
2. `App` 更新 `app_state.theme_name`
3. 调用 `apply_style(style, new_theme)`
4. 手动更新非 ttk 组件
5. 各视图 `on_theme_changed(theme)` → Canvas `redraw()`
6. 保存主题偏好到 `GUISettings`

### 3.3 `gui/settings.py` — 配置持久化

```python
@dataclass
class GUISettings:
    # RecognitionConfig 映射（完整映射，缺省值与 RecognitionConfig 一致）
    model_path: str | None = None
    mapping_path: str | None = None           # [S1] tile_code 映射文件
    template_dir: str | None = None
    config_path: str | None = None
    ocr_model_dir: str | None = None          # [S1] OCR 模型目录
    detection_confidence: float = 0.7
    nms_iou_threshold: float = 0.55
    score_min: int = -99999                   # [S1] 分数校验下限
    score_max: int = 200000                   # [S1] 分数校验上限
    fusion_window_size: int = 3               # [S1] 帧间融合窗口
    enable_batch_detection: bool = True       # [S1] 批量检测开关
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
    def load(cls) -> "GUISettings":
        """加载，文件不存在或损坏时返回默认值"""

    def save(self) -> None:
        """原子写入（先写临时文件再 rename）"""

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
            0.02,  # frame_threshold 默认值
        )
```

**[S1 修复]**: `GUISettings` 现在完整映射 `RecognitionConfig` 的全部 12 个字段，`to_recognition_config()` 显式传递每个参数。设置弹窗可选择性地暴露部分字段（如 `ocr_model_dir`、`enable_batch_detection`），其余使用默认值。

### 3.4 `gui/app_state.py` — 应用共享状态

**[S4 修复]**: `AppState` 定义为 `dataclass`，由 `App` 构建并注入各视图。

```python
from typing import Callable
from dataclasses import dataclass

@dataclass
class AppState:
    """App 管理的共享资源，engine 可通过 App._rebuild_engine 重建"""
    engine: RecognitionEngine
    pipeline_factory: Callable[[], CapturePipeline]  # S5: 每次创建新实例
    config: RecognitionConfig
    theme_name: str  # "dark" | "light"
```

**生命周期**: App 拥有唯一实例，视图通过 `self._app_state` 读取。`engine` 属性可被 `App._rebuild_engine()` 替换（S2 线程安全由 Worker 本地引用保证）。

### 3.5 `gui/base_view.py` — 视图基类

**职责**: 定义统一的视图生命周期接口，App 通过该接口管理视图切换。

```python
class BaseView(ttk.Frame):
    """视图基类，定义统一生命周期"""

    def __init__(self, parent, app_state: AppState, theme: dict, **kwargs):
        super().__init__(parent, **kwargs)
        self._app_state = app_state
        self._theme = theme
        self._worker: _RecognizeWorker | None = None

    def _ensure_worker(self) -> _RecognizeWorker:
        """延迟创建 Worker（仅需要异步识别的视图调用）"""
        if self._worker is None:
            pipeline = self._app_state.pipeline_factory()
            self._worker = _RecognizeWorker(
                self._app_state.engine, pipeline
            )
        return self._worker

    def start(self) -> None:
        """视图激活时调用"""

    def stop(self) -> None:
        """视图停用时调用"""
        if self._worker is not None:
            self._worker.stop()
            self._worker = None

    def on_theme_changed(self, theme: dict) -> None:
        """主题切换通知"""
        self._theme = theme

    def on_engine_changed(self, engine: RecognitionEngine) -> None:
        """引擎重建通知"""
        if self._worker is not None:
            self._worker.update_engine(engine)
```

**Worker 延迟创建**: DevView 不调用 `_ensure_worker()`，不创建 Worker。

**Pipeline 重置**: 视图切换时 `stop()` 销毁旧 Worker，`start()` 时通过 `_ensure_worker()` 重新创建，新 Worker 获得全新 `CapturePipeline` 实例。

### 3.6 `gui/worker.py` — 识别工作线程

**职责**: 在独立线程中串行处理图像识别任务，支持丢弃旧帧。

```python
@dataclass
class _WorkerResult:
    """Worker 输出结果"""
    image: np.ndarray | None = None
    frame: FrameResult | None = None
    state: GameState | None = None
    error: str | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


class _RecognizeWorker:
    """单工作线程识别器"""

    def __init__(self, engine: RecognitionEngine, pipeline: CapturePipeline):
        self._engine_ref = engine
        self._pipeline_ref = pipeline
        self._task: np.ndarray | None = None
        self._result_queue: queue.Queue = queue.Queue(maxsize=1)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update_engine(self, engine: RecognitionEngine) -> None:
        """更新 engine 引用（线程安全：_run() 每次循环持有本地引用）"""
        self._engine_ref = engine

    def submit(self, image: np.ndarray) -> bool:
        """提交图像。上一帧未处理完则丢弃"""
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
            engine = self._engine_ref  # 本地引用
            try:
                frame = self._pipeline_ref.process_image(image)
                state = engine.recognize(frame.zones) if frame.is_static else None
                result = _WorkerResult(image=image, frame=frame, state=state)
            except Exception as e:
                result = _WorkerResult(error=str(e))
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
        """停止工作线程并等待退出"""
        self._stop_event.set()
        self._thread.join(timeout=2.0)
```

**关键设计点**:
- `_WorkerResult` 数据类替代裸 tuple（M3 修复）
- `stop()` 调用 `join(timeout=2.0)` 等待线程退出（M2 修复）
- `_run()` 每次循环持有 engine 本地引用（S2 修复，线程安全）

## 4. 依赖管理

```toml
[project.optional-dependencies]
gui = [
    "Pillow>=10.0",
]
```

**环境前置**（不写入 pyproject.toml）:
- tkinter: macOS 需要 `brew install python-tk@3.14`
- tkinterdnd2: 可选拖放支持

## 5. 需要参考的现有代码

| 文件 | 用途 |
|------|------|
| `src/majsoul_recognizer/recognition/engine.py` | RecognitionEngine 接口 |
| `src/majsoul_recognizer/recognition/config.py` | RecognitionConfig 字段 |
| `src/majsoul_recognizer/pipeline.py` | CapturePipeline 接口 |
| `src/majsoul_recognizer/types.py` | FrameResult, GameState, Detection, BBox |
| `src/majsoul_recognizer/cli.py` | CLI 入口点 |
