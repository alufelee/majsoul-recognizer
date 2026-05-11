# 雀魂麻将识别助手 — GUI 设计文档

> 版本: 3.0 | 日期: 2026-05-08 | 阶段: GUI 界面
>
> v3.0 变更（方案 B — 中度重构）:
> - 新增 `base_view.py`：BaseView 抽象类，统一视图生命周期
> - 新增 `worker.py`：`_RecognizeWorker` 从 `screenshot_view.py` 抽取为独立模块
> - 新增 `settings_dialog.py`：设置弹窗从 `app.py` 抽取为独立类
> - `AppState` 瘦身：移除 mutable 状态（current_image/frame/state），各视图自行管理数据
> - 明确双线程架构：捕获线程 + 识别线程，通过队列传递

## 1. 概述

为雀魂麻将识别助手添加 Tkinter 桌面 GUI，支持**开发调试**和**实时辅助**双场景。

**核心功能**:
- 截图文件加载（文件选择 + 拖放）→ 区域分割 + 识别 → 结果展示
- 实时窗口捕获 → 连续识别 → 实时更新
- 开发调试视图（区域分割图、检测框、JSON 输出）
- 深色/浅色主题切换

**不含**: 模型训练界面、多语言支持、自动对局策略推荐、图表可视化。

**平台约束**: macOS + Windows，Python 3.10+。

**环境前置**:
- tkinter 必须可用（macOS: `brew install python-tk@3.14`）
- onnxruntime 不可用时使用 `_StubDetector` 降级（区域分割仍正常工作）
- PaddleOCR 不可用时分数/局次/计时器返回 None
- tkinterdnd2 为实验性可选依赖，Python 3.14 兼容性未经验证

**无模型时可用功能**: 区域分割、帧状态检测、模板匹配、CLI JSON 输出查看。截图模式的区域分割图是无模型时最有价值的展示。实时模式需要 onnxruntime + 训练模型作为前提，无模型时仅显示空白区域分割结果。

## 2. 架构

### 2.1 整体布局

```
┌──────────────────────────────────────────────┐
│ 标题栏: 雀魂麻将识别助手 v0.1   [主题] [设置]  │
├──────┬───────────────────────────────────────┤
│      │                                       │
│ 截图 │                                       │
│      │         主视图区域                      │
│ 实时 │    (根据侧边栏选择切换)                  │
│      │                                       │
│ 调试 │                                       │
│      │                                       │
├──────┴───────────────────────────────────────┤
│ 状态栏: ●就绪 | FPS: 5.2 | 延迟: 180ms | 帧: 42│
└──────────────────────────────────────────────┘
```

**侧边栏**: 使用文字标签（非 emoji），宽度固定 64px，每项纵向排列。
- "截图" — 截图模式
- "实时" — 实时模式
- "调试" — 开发调试

选中项背景高亮，未选中为默认背景。设置和主题切换按钮放在标题栏右侧（非侧边栏），避免侧边栏底部空间问题。

### 2.2 模块结构

```
src/majsoul_recognizer/gui/
├── __init__.py               # 入口 + main()
├── app.py                    # 主窗口 + 侧边栏 + 视图切换 + 状态栏
├── base_view.py              # BaseView 抽象类（统一生命周期）
├── worker.py                 # _RecognizeWorker（独立工作线程模块）
├── theme.py                  # 深色/浅色主题 (ttk.Style 管理)
├── settings.py               # GUISettings 持久化
├── settings_dialog.py        # 设置弹窗（Toplevel 对话框）
├── views/
│   ├── __init__.py
│   ├── screenshot_view.py    # 截图模式（文件选择 + 拖放 + 异步识别）
│   ├── live_view.py          # 实时模式（捕获线程 + 异步识别）
│   └── dev_view.py           # 开发调试（区域分割 + JSON + 性能统计）
└── widgets/
    ├── __init__.py
    ├── image_canvas.py       # 图像画布（截图显示 + 检测框 + 区域标注）
    └── result_panel.py       # 识别结果面板（文字 + 牌面编码显示）
```

**共 14 个文件**（v2.1 为 11 个，新增 3 个：base_view.py、worker.py、settings_dialog.py）。

### 2.3 依赖关系

```
app.py
  ├── base_view.py (BaseView 抽象类)
  ├── worker.py (_RecognizeWorker + _WorkerResult)
  ├── theme.py (ttk.Style 主题)
  ├── settings.py (配置持久化)
  ├── settings_dialog.py (设置弹窗)
  ├── views/screenshot_view.py  extends BaseView
  │     ├── worker.py (via _ensure_worker)
  │     ├── widgets/image_canvas.py
  │     └── widgets/result_panel.py
  ├── views/live_view.py  extends BaseView
  │     ├── worker.py (via _ensure_worker)
  │     ├── widgets/image_canvas.py
  │     └── widgets/result_panel.py
  └── views/dev_view.py  extends BaseView (no Worker)
        └── widgets/image_canvas.py
```

### 2.4 数据流

**截图模式**:
```
用户操作 (文件选择/拖放)
    ↓ file_path
cv2.imread(file_path)
    ↓ image: ndarray
worker.submit(image)
    ↓ [识别线程]
CapturePipeline.process_image(image)
    ↓ FrameResult { zones, is_static, frame_id, timestamp }
RecognitionEngine.recognize(zones)        [仅 is_static=True]
    ↓ GameState
result_queue → root.after(50) 轮询
    ↓
ScreenshotView.update(image, game_state, frame_result)
    ├── ImageCanvas: 显示截图 + 区域标注 + 检测框
    └── ResultPanel: 文字识别结果
```

**实时模式**（双线程）:
```
[捕获线程]                      [识别线程]
_live_loop()                    _RecognizeWorker._run()
    ↓ 间隔: capture_interval_ms
WindowFinder.find_window()
    ↓ WindowInfo
ScreenCapture.capture_window()
    ↓ image: ndarray
worker.submit(image) ────────→ task_queue (maxsize=1)
                                    ↓
                                CapturePipeline.process_image()
                                    ↓ FrameResult
                                [is_static?]
                                RecognitionEngine.recognize(zones)
                                    ↓ GameState
                                result_queue (maxsize=1)
                                    ↓
主线程 root.after(50) 轮询 ←────── get_result()
    ↓
LiveView.update(image, game_state, frame_result)
    ├── ImageCanvas: 实时截图
    └── ResultPanel: 实时结果 + FPS
```

## 3. 模块详细设计

### 3.1 base_view.py — 视图基类

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
        """延迟创建 Worker（仅需要异步识别的视图调用）

        S5: 每次 ensure 创建新的 pipeline 实例，避免跨视图状态泄漏。
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

    def on_engine_changed(self, engine: RecognitionEngine) -> None:
        """引擎重建通知（设置变更后由 App 调用）"""
        if self._worker is not None:
            self._worker.update_engine(engine)
```

**Worker 延迟创建**: `BaseView.__init__` 中 `_worker = None`，子类通过 `_ensure_worker()` 按需创建。DevView 不调用 `_ensure_worker()`，不创建 Worker。S1 修复: 避免 DevView 空转线程。

**Pipeline 重置**: 视图切换时 `stop()` 销毁旧 Worker，`start()` 时新 Worker 通过 `_ensure_worker()` 重新创建。新 Worker 获得全新的 `CapturePipeline` 实例（见 S5 修复），避免帧计数器和 FrameChecker 状态跨视图泄漏。

### 3.2 worker.py — 识别工作线程

**职责**: 在独立线程中串行处理图像识别任务，支持丢弃旧帧。

```python
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
    """单工作线程识别器，串行处理提交的图像"""

    def __init__(self, engine: RecognitionEngine, pipeline: CapturePipeline):
        self._engine_ref = engine  # 引用，可被外部更新
        self._pipeline_ref = pipeline
        self._task: np.ndarray | None = None
        self._result_queue: queue.Queue = queue.Queue(maxsize=1)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()  # 可中断的停止信号
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update_engine(self, engine: RecognitionEngine) -> None:
        """更新 engine 引用（设置变更后由 BaseView.on_engine_changed 调用）

        注意: S2 线程安全 — _run() 在每次循环开头持有 engine 本地引用，
        即使 update_engine 在循环中途被调用，当前迭代的 engine 不会中途切换。
        重建后 Validator.prev_state 历史会丢失（第一帧无帧间融合），这是可接受的。
        """
        self._engine_ref = engine

    def submit(self, image: np.ndarray) -> bool:
        """提交图像。如果上一帧还在处理中则丢弃（返回 False）"""
        with self._lock:
            if self._task is not None:
                return False  # 上一帧未处理完，丢弃
            self._task = image
        return True

    def _run(self) -> None:
        """工作线程主循环"""
        while not self._stop_event.is_set():
            with self._lock:
                image = self._task
                self._task = None
            if image is None:
                self._stop_event.wait(0.01)  # 可中断等待
                continue
            # S2: 持有 engine 本地引用，避免循环中途切换
            engine = self._engine_ref
            try:
                # 串行处理
                frame = self._pipeline_ref.process_image(image)
                state = engine.recognize(frame.zones) if frame.is_static else None
                result = _WorkerResult(image=image, frame=frame, state=state)
            except Exception as e:
                result = _WorkerResult(error=str(e))
            # 非阻塞放入结果队列（maxsize=1，旧结果自动丢弃）
            try:
                self._result_queue.get_nowait()  # 清理旧结果
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
        self._stop_event.set()  # 立即唤醒等待中的线程
        self._thread.join(timeout=2.0)  # M2: 等待线程退出，避免资源泄漏
```

**M3 修复**: 使用 `_WorkerResult` 数据类替代裸 tuple。调用者通过 `result.is_error` 判断，不再有解包类型不一致的风险。

**M2 修复**: `stop()` 调用 `join(timeout=2.0)` 等待线程退出。

**S2 修复**: `_run()` 每次循环开头持有 `engine = self._engine_ref` 本地引用，识别全程使用本地引用。

### 3.3 app.py — 主窗口

**职责**: 创建 Tkinter 根窗口，管理侧边栏导航，切换视图，维护全局不可变状态。

```python
class App:
    """GUI 主窗口"""

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
```

**初始化流程**:
1. 创建根窗口 — M6: 当 `tkinterdnd2` 可用时使用 `TkinterDnD.Tk()`，否则使用标准 `tk.Tk()`。从 `GUISettings` 恢复上次窗口尺寸和位置
2. 配置 `ttk.Style`（调用 `theme.apply_style()`）
3. 创建标题栏 `Frame`（标题 + 主题按钮 + 设置按钮）
4. 创建侧边栏 `Frame`（文字导航按钮）
5. 创建主内容区 `Frame`
6. 创建状态栏 `Frame`
7. 实例化 `RecognitionEngine`（使用 `GUISettings.to_recognition_config()`）
8. 创建 `AppState`（engine + pipeline 工厂 + config + theme_name）
9. 实例化三个视图（Worker 延迟创建，不在此步初始化）
10. 显示默认视图（截图模式）

**M6 根窗口条件初始化**:
```python
def _create_root(self) -> tk.Tk:
    """根据 tkinterdnd2 可用性选择根窗口类型"""
    try:
        from tkinterdnd2 import TkinterDnD
        return TkinterDnD.Tk()
    except ImportError:
        return tk.Tk()
```

**运行入口**:
```python
def run(self) -> None:
    """启动 Tkinter 主循环"""
    self._root.protocol("WM_DELETE_WINDOW", self._on_close)
    self._root.mainloop()

def _on_close(self) -> None:
    """窗口关闭: 停止所有视图，保存设置，销毁窗口"""
    for view in self._views.values():
        view.stop()
    self._settings.window_width = self._root.winfo_width()
    self._settings.window_height = self._root.winfo_height()
    self._settings.window_x = self._root.winfo_x()
    self._settings.window_y = self._root.winfo_y()
    self._settings.save()
    self._root.destroy()
```

**全局状态**（仅 App 管理其生命周期）:
```python
class AppState:
    """App 管理的共享资源，engine 可通过 _rebuild_engine 重建"""
    engine: RecognitionEngine             # M1: 可重建，非严格不可变
    pipeline_factory: Callable[[], CapturePipeline]  # S5: 工厂函数，每次创建新实例
    config: RecognitionConfig
    theme_name: str  # "dark" | "light"
    # 注意: current_image/frame/state 已移除
    # 各视图自行管理自己的数据
```

**S5 修复**: `AppState` 不再持有单个 `CapturePipeline` 实例，改为持有工厂函数。每个 Worker 创建时获得独立的 pipeline 实例，避免 `frame_count` 和 `FrameChecker._prev_frame` 跨视图泄漏。`GUISettings.to_pipeline_config()` 提供 pipeline 参数。

**视图切换**（通过 BaseView 生命周期）:
```python
def _switch_view(self, view_name: str) -> None:
    """切换视图"""
    if self._active_view:
        self._active_view.stop()          # 停止旧视图的 Worker
    self._active_view = self._views[view_name]
    # grid_remove() 隐藏旧视图，grid() 显示新视图
    self._active_view.start()             # 启动新视图
```

**Engine 重建**（设置变更时）:
```python
def _rebuild_engine(self) -> None:
    """根据最新 GUISettings 重建 RecognitionEngine"""
    self._settings.save()
    config = self._settings.to_recognition_config()
    try:
        new_engine = RecognitionEngine(config)
        self._app_state.engine = new_engine
        # 通知所有视图更新（非活跃视图的 worker 为 None，on_engine_changed 会跳过）
        for view in self._views.values():
            view.on_engine_changed(new_engine)
    except Exception as e:
        # 重建失败，保持旧 engine
        logger.error("Engine rebuild failed: %s", e)
        # 弹窗提示用户
```

**侧边栏实现**:
- 每个 `Button` 使用文字标签（"截图"/"实时"/"调试"）
- 选中项通过 `tkinter.Frame` 包装，背景色变化
- 字体: 默认系统字体，size=10

**视图切换布局**:
- 使用 `grid()` 布局管理器（而非 `pack_forget`/`pack`）
- 所有视图 `grid()` 在同一位置 `(row=0, column=0)`
- 切换时 `grid_remove()` 隐藏旧视图，`grid()` 显示新视图

**状态栏**:
- 左侧：状态指示灯（Canvas 圆点 ● ，绿=就绪/黄=识别中/红=错误）+ 状态文字
- 右侧：FPS、延迟、帧数
- 仅实时模式时更新 FPS/延迟

**窗口尺寸持久化**:
- 退出时保存窗口 `(width, height, x, y)` 到 `GUISettings`
- 启动时恢复

### 3.4 theme.py — 主题系统

**职责**: 通过 `ttk.Style` 统一管理深色/浅色主题。

**核心原则**: 不做递归遍历子组件。使用 `ttk.Style.configure()` 统一设置样式类，`tk` 组件（非 ttk）在创建时读取当前主题颜色。Canvas 在 `redraw()` 时从 `theme` 字典读取颜色。

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
    """获取主题颜色方案

    L1: 返回类属性 dict（DARK 或 LIGHT），调用者不应修改返回值。
    视图持有 theme dict 引用，主题切换时 App 通过 on_theme_changed
    传递新 dict（不同的 DARK/LIGHT 对象），触发重绘。
    """
```

**切换流程**:
1. 用户点击主题按钮
2. `App` 更新 `app_state.theme_name`
3. 调用 `apply_style(style, new_theme)`
4. 手动更新非 ttk 组件（侧边栏 Frame 背景、Canvas 背景）
5. 各视图的 `on_theme_changed(theme)` → 触发 Canvas `redraw()`
6. 保存主题偏好到 `GUISettings`

### 3.5 settings.py — 配置持久化

```python
from dataclasses import dataclass, field, ClassVar

@dataclass
class GUISettings:
    # RecognitionConfig 映射
    model_path: str | None = None
    template_dir: str | None = None
    config_path: str | None = None
    detection_confidence: float = 0.7
    nms_iou_threshold: float = 0.55
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

    _PATH: ClassVar[Path] = Path.home() / ".majsoul-recognizer" / "settings.json"  # L3: ClassVar 避免被 dataclass 当字段

    @classmethod
    def load(cls) -> "GUISettings":
        """加载，文件不存在或损坏时返回默认值"""

    def save(self) -> None:
        """原子写入（先写临时文件再 rename）"""

    def to_recognition_config(self) -> RecognitionConfig:
        """转换为 RecognitionConfig（缺失字段使用默认值）"""
        return RecognitionConfig(
            model_path=Path(self.model_path) if self.model_path else None,
            template_dir=Path(self.template_dir) if self.template_dir else None,
            nms_iou_threshold=self.nms_iou_threshold,
            detection_confidence=self.detection_confidence,
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

### 3.6 settings_dialog.py — 设置弹窗

**职责**: 独立的 `tkinter.Toplevel` 对话框，管理所有可配置项。

```python
class SettingsDialog:
    """设置弹窗"""

    def __init__(self, parent: tk.Tk, settings: GUISettings,
                 on_apply: Callable[[], None]):
        self._dialog = tk.Toplevel(parent)
        self._dialog.title("设置")
        self._settings = settings
        self._on_apply = on_apply
        self._initial_snapshot = dataclasses.asdict(settings)  # 保存初始快照
        # ... UI 组件初始化 ...

    def _on_apply_clicked(self) -> None:
        """应用按钮: 即时保存设置并通知 App 重建 engine"""
        self._sync_to_settings()
        self._settings.save()
        self._on_apply()  # App._rebuild_engine()
        self._initial_snapshot = dataclasses.asdict(self._settings)  # 更新快照

    def _on_close_clicked(self) -> None:
        """关闭按钮: 应用未保存的修改，然后关闭"""
        self._sync_to_settings()
        if dataclasses.asdict(self._settings) != self._initial_snapshot:
            self._settings.save()
            self._on_apply()  # M4: 有关闭前未应用的修改也生效
        self._dialog.destroy()
```

**M4 修复**: 关闭按钮检测是否有未应用的修改，有则自动保存并触发 engine 重建。

**配置项**: 模型路径、模板目录、区域配置、检测置信度、NMS IoU 阈值、捕获间隔、主题选择。

### 3.7 views/screenshot_view.py — 截图模式

**职责**: 加载截图文件（文件选择/拖放）→ 执行识别 → 展示结果。

**继承**: `BaseView`。

**布局**:
```
┌─────────────────────────┬───────────────────────┐
│                         │ 局次: 东一局 0本场      │
│   ImageCanvas           │ 宝牌: 3s               │
│   (截图 + 区域标注      │                        │
│    + 检测框)            │ 手牌: 1m 2m 3m...4p   │
│                         │   ↑ drawn_tile         │
│                         │                        │
│                         │ 分数: 自 25000 ...     │
│                         │ 牌河: 自 1m 2m 3m ...  │
│                         │ 副露: -                │
│                         │ 动作: -                │
│                         │ 延迟: 180ms            │
│                         │ 警告: 0                │
├─────────────────────────┴───────────────────────┤
│ [打开文件] [识别] | 拖放截图文件到此处              │
└─────────────────────────────────────────────────┘
```

**视图自有状态**（从 AppState 移出）:
```python
class ScreenshotView(BaseView):
    def __init__(self, parent, app_state, theme, on_result, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        # 视图自行管理数据
        self._current_image: np.ndarray | None = None
        self._current_frame: FrameResult | None = None
        self._current_state: GameState | None = None
        self._on_result = on_result  # P4: 回调通知 App 有新结果可用
```

**P4 回调机制**: 视图通过 `on_result` 回调通知 App 新结果可用。App 将结果缓存到 `_last_frame`/`_last_state`，并在 DevView 活跃时转发。

```python
# App.__init__ 中
self._last_frame: FrameResult | None = None
self._last_state: GameState | None = None

def _make_on_result(self) -> Callable:
    """创建结果回调闭包"""
    def on_result(frame: FrameResult, state: GameState | None):
        self._last_frame = frame
        self._last_state = state
        if isinstance(self._active_view, DevView):
            self._active_view.update_data(frame, state)
    return on_result

# 创建视图时传入回调
screenshot_view = ScreenshotView(..., on_result=self._make_on_result())
live_view = LiveView(..., on_result=self._make_on_result())
dev_view = DevView(..., on_result=None)  # DevView 不产生结果
```

**异步识别**:
```python
def recognize(self, image: np.ndarray) -> None:
    """提交图像到工作线程，异步识别"""
    self._current_image = image
    self._status_label.config(text="识别中...")
    worker = self._ensure_worker()  # 延迟创建 Worker
    worker.submit(image)
    self.after(50, self._poll_result)

def _poll_result(self) -> None:
    """主线程定时检查识别结果（每 50ms）"""
    if self._worker is None:
        return
    result = self._worker.get_result()
    if result is not None:
        if result.is_error:
            self._status_label.config(text=f"错误: {result.error}")
        else:
            self._current_frame = result.frame
            self._current_state = result.state
            self._update_display(result.image, result.frame, result.state)
            self._status_label.config(text="就绪")
            # P4: 通知 App 新结果可用（供 DevView 使用）
            if result.frame is not None:
                self._on_result(result.frame, result.state)
    else:
        self.after(50, self._poll_result)
```

**拖放支持**:
```python
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _HAS_DND = True
except ImportError:
    _HAS_DND = False
```
- `tkinterdnd2` 可用时: 注册 `dnd_bind('<<Drop>>', _on_drop)`
- 不可用时: 隐藏拖放提示文字，仅显示"打开文件"按钮

### 3.8 views/live_view.py — 实时模式

**职责**: 连续捕获雀魂窗口画面 → 自动识别 → 实时更新结果。

**继承**: `BaseView`。

**布局**:
```
┌──────────────────────────────────────────────┐
│  ImageCanvas (实时截图 + 检测框标注)           │
│                                              │
│  [截图预览区域，自动刷新]                       │
│                                              │
├──────────────────────────────────────────────┤
│ [开始] [暂停] [重置]  FPS: 5.2  延迟: 180ms   │
│                                              │
│ 局次: 东一局 0本场  |  手牌: 1m 2m...4p       │
│ 分数: 自 25000 右 25000 对 25000 左 25000     │
│ 动作: -  警告: 0                              │
└──────────────────────────────────────────────┘
```

**视图自有状态**:
```python
class LiveView(BaseView):
    CAPTURE_INTERVAL = 0.2   # 200ms
    WINDOW_RETRY_INTERVAL = 2.0  # 窗口丢失后每 2 秒重试
    MAX_CONSECUTIVE_FAILS = 10   # 连续失败 10 次后暂停

    def __init__(self, parent, app_state, theme, on_result, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        self._capture_thread: threading.Thread | None = None
        self._capture_stop = threading.Event()
        self._status_queue: queue.Queue = queue.Queue()
        self._fps_counter = _FPSCounter()
        self._current_state: GameState | None = None
        self._on_result = on_result  # P4: 回调通知 App
```

**实时捕获循环**（在独立线程中运行）:

```python
def _capture_loop(self) -> None:
    """捕获主循环（在独立线程中运行）"""
    try:
        finder = create_finder()  # 使用现有工厂函数
    except RuntimeError:
        # L4: 不支持的平台（非 macOS/Windows）
        self._status_queue.put(("unsupported_platform", None))
        return

    # M5: 使用 context manager 确保 mss.MSS 资源释放
    # S4: ScreenCapture 仅在此线程使用，线程安全
    with ScreenCapture() as capture:
        window = None
        consecutive_fails = 0

        while not self._capture_stop.is_set():
            t0 = time.perf_counter()

            # 查找/重连窗口
            if window is None:
                window = finder.find_window()
                if window is None:
                    self._status_queue.put(("window_not_found", None))
                    self._capture_stop.wait(self.WINDOW_RETRY_INTERVAL)
                    continue

            # 截取
            image = capture.capture_window(window)
            if image is None:
                consecutive_fails += 1
                if consecutive_fails >= self.MAX_CONSECUTIVE_FAILS:
                    window = None  # 重置窗口，下轮重新查找
                    consecutive_fails = 0
                self._capture_stop.wait(0.1)
                continue

            consecutive_fails = 0
            worker = self._ensure_worker()
            worker.submit(image)
            self._fps_counter.tick()

            elapsed = time.perf_counter() - t0
            remaining = max(0, self.CAPTURE_INTERVAL - elapsed)
            self._capture_stop.wait(remaining)  # 可中断等待
```

**生命周期覆盖**:
```python
def start(self) -> None:
    """启动捕获线程"""
    super().start()
    self._capture_stop.clear()
    self._capture_thread = threading.Thread(
        target=self._capture_loop, daemon=True
    )
    self._capture_thread.start()
    self.after(50, self._poll_result)

def stop(self) -> None:
    """停止捕获线程和 Worker"""
    self._capture_stop.set()
    if self._capture_thread and self._capture_thread.is_alive():
        self._capture_thread.join(timeout=2.0)
    super().stop()
```

**FPSCounter**（内置在 live_view.py 中）:
```python
class _FPSCounter:
    """简单的 FPS 计数器

    S3: tick() 在捕获线程调用，fps 在主线程读取。
    Python GIL 保证 list.append 和 list 赋值的原子性，
    列表推导式创建新 list 再赋值也不是问题 — 最坏情况主线程读到
    旧列表（少一个元素），FPS 值略有偏差但可接受。
    """
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

**状态机**:
```
[空闲] --开始--> [捕获中] --暂停--> [暂停] --继续--> [捕获中]
  ↑                  |
  │              窗口丢失
  │                  ↓
  └────重置←── [等待重连]
```

### 3.9 views/dev_view.py — 开发调试视图

**职责**: 展示区域分割图 + 检测框可视化 + JSON 输出 + 文字性能统计。

**继承**: `BaseView`（`start()`/`stop()` 为空操作，不使用 Worker）。

**布局**:
```
┌──────────────────────┬──────────────────────┐
│  ImageCanvas         │  ImageCanvas          │
│  (区域标注模式)       │  (检测框模式)          │
│                      │                      │
│  各区域彩色边框       │  bbox + tile_code     │
│  + 区域名称标注       │  + 置信度             │
├──────────────────────┴──────────────────────┤
│  JSON 输出 (Text 组件，可滚动，可复制)         │
│  {"frame_id": 1, "is_static": true, ...}     │
├─────────────────────────────────────────────┤
│  性能: 总计 180ms | 检测 120ms | 帧 42        │
│  FPS: 5.2 (平均 4.8) | 最大延迟: 320ms        │
└─────────────────────────────────────────────┘
```

**数据来源**: DevView 不持有自己的 Worker。App 在视图切换到调试模式时，将最近一次的 `FrameResult` + `GameState` 传递给 DevView。具体方式：`App` 维护一个 `_last_frame` 和 `_last_state` 引用，每次截图/实时视图产生结果时更新。DevView 切换到前台时调用 `app_state` 上的方法获取最近数据。

```python
# App 中
self._last_frame: FrameResult | None = None
self._last_state: GameState | None = None

# 视图产生结果时
def _on_result_available(self, frame: FrameResult, state: GameState | None):
    self._last_frame = frame
    self._last_state = state
    if isinstance(self._active_view, DevView):
        self._active_view.update_data(frame, state)
```

**区域标注模式 (ImageCanvas)**:
- 在截图上绘制所有区域矩形框
- 每个区域使用 `ZONE_COLORS` 中定义的颜色
- 框旁标注区域名称（如 "hand", "dora", "score_self"）

区域颜色方案：
```python
ZONE_COLORS = {
    "hand": "#4caf50",        # 绿
    "dora": "#ff9800",        # 橙
    "round_info": "#2196f3",  # 蓝
    "score_self": "#9c27b0",  # 紫
    "score_right": "#9c27b0",
    "score_opposite": "#9c27b0",
    "score_left": "#9c27b0",
    "discards_self": "#00bcd4",   # 青
    "discards_right": "#00bcd4",
    "discards_opposite": "#00bcd4",
    "discards_left": "#00bcd4",
    "calls_self": "#e91e63",  # 粉
    "actions": "#ff5722",     # 深橙
    "timer": "#607d8b",       # 蓝灰
}
```

**检测框可视化**:
- 框线颜色按牌面类别：
  - 万子 (m): `#4caf50` 绿
  - 筒子 (p): `#2196f3` 蓝
  - 索子 (s): `#f44336` 红
  - 字牌 (z): `#9c27b0` 紫
  - 赤宝牌 (mr/pr/sr): `#ff9800` 橙
  - 特殊 (back/rotated/dora_frame): `#9e9e9e` 灰
- 框上方标签: `tile_code (confidence%)` 或仅 `tile_code`

**JSON 输出**:
- 使用 `tkinter.Text` 组件
- `format_output(frame_result, game_state)` 的完整 JSON
- `json.dumps(data, indent=2, ensure_ascii=False)` 格式化
- "复制 JSON" 按钮调用 `clipboard_clear()` + `clipboard_append()`
- **不做**树形折叠和语法高亮（首版用纯文本）

**性能统计**（文字，非图表）:
```
性能统计:
  总耗时: 180ms | 识别: 120ms
  FPS: 5.2 | 平均: 4.8 | 最大延迟: 320ms
  已处理: 42 帧 | 跳过(动画): 8 帧
```

### 3.10 widgets/image_canvas.py — 图像画布

**职责**: 在 Tkinter Canvas 上显示图像，支持区域标注和检测框叠加。

```python
class ImageCanvas(tk.Canvas):
    """图像显示画布"""

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, bg=theme["canvas_bg"], **kwargs)
        self._theme = theme
        self._photo: ImageTk.PhotoImage | None = None
        self._detections: list[Detection] = []
        self._zone_rects: dict[str, tuple] = {}  # {name: (x, y, w, h) 像素}
        self._show_boxes: bool = True
        self._show_confidence: bool = True
        self._mode: str = "detection"  # "detection" | "zones"
        self._pending_image: np.ndarray | None = None  # L2: 未绘制的图像缓存
        # P5: 窗口 resize 时重绘
        self.bind("<Configure>", self._on_configure)

    def show_image(self, image: np.ndarray) -> None:
        """显示 BGR 图像（自动缩放适应画布尺寸）"""
        h, w = image.shape[:2]
        # L2: winfo_height/width 在窗口映射前返回 1，使用 reqwidth 回退
        ch = max(self.winfo_height(), self.winfo_reqheight())
        cw = max(self.winfo_width(), self.winfo_reqwidth())
        if ch <= 1 or cw <= 1:
            self._pending_image = image  # P5: 缓存图像，等 Configure 事件重绘
            return
        scale = min(cw / w, ch / h, 1.0)
        new_w, new_h = int(w * scale), int(h * scale)

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb).resize((new_w, new_h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(pil_img)

        self.delete("all")
        x_offset = (cw - new_w) // 2
        y_offset = (ch - new_h) // 2
        self.create_image(x_offset, y_offset, anchor="nw", image=self._photo)
        self._scale = scale
        self._offset = (x_offset, y_offset)

        # 重绘叠加层
        if self._mode == "zones":
            self._draw_zones()
        else:
            self._draw_detections()

    def set_detections(self, detections: list[Detection]) -> None:
        """设置检测框数据"""
        self._detections = detections
        if self._mode == "detection":
            self._draw_detections()

    def set_zones(self, zone_rects: dict[str, tuple], colors: dict[str, str]) -> None:
        """设置区域矩形 {name: (x, y, w, h) 像素坐标}"""
        self._zone_rects = zone_rects
        self._zone_colors = colors
        if self._mode == "zones":
            self._draw_zones()

    def set_mode(self, mode: str) -> None:
        """切换叠加模式: "detection" | "zones" """
        self._mode = mode

    def on_theme_changed(self, theme: dict[str, str]) -> None:
        """主题切换时更新背景色"""
        self._theme = theme
        self.configure(bg=theme["canvas_bg"])

    def clear(self) -> None:
        """清空画布"""
        self.delete("all")
        self._photo = None
        self._pending_image = None

    def _on_configure(self, event) -> None:
        """P5: 窗口 resize 时重绘缓存的图像"""
        if self._pending_image is not None:
            self.show_image(self._pending_image)
```

**图像转换**:
- `cv2` BGR ndarray → `cv2.cvtColor(BGR2RGB)` → `PIL.Image.fromarray` → `ImageTk.PhotoImage`
- 仅在 `show_image()` 时转换，不在实时循环中重复转换已显示的图像
- 缩放使用 `PIL.Image.resize()` 的 `LANCZOS` 算法

**P3 坐标转换** — `_draw_detections()` 和 `_draw_zones()` 的核心逻辑:
```python
def _to_canvas_coords(self, x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
    """原始图像坐标 → Canvas 坐标（考虑缩放和偏移）"""
    ox, oy = self._offset
    s = self._scale
    return (int(x * s) + ox, int(y * s) + oy,
            int((x + w) * s) + ox, int((y + h) * s) + oy)

def _draw_detections(self) -> None:
    """绘制检测框"""
    if self._photo is None:
        return
    for det in self._detections:
        x1, y1, x2, y2 = self._to_canvas_coords(
            det.bbox.x, det.bbox.y, det.bbox.width, det.bbox.height
        )
        color = _TILE_CATEGORY_COLORS.get(_get_tile_category(det.tile_code), "#9e9e9e")
        self.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
        # 标签
        label = f"{det.tile_code} ({det.confidence:.0%})" if self._show_confidence else det.tile_code
        self.create_text(x1, y1 - 4, anchor="sw", text=label,
                        fill=color, font=("Arial", 9))

def _draw_zones(self) -> None:
    """绘制区域标注"""
    if self._photo is None:
        return
    for name, (x, y, w, h) in self._zone_rects.items():
        x1, y1, x2, y2 = self._to_canvas_coords(x, y, w, h)
        color = self._zone_colors.get(name, "#ffffff")
        self.create_rectangle(x1, y1, x2, y2, outline=color, width=2, dash=(4, 4))
        self.create_text(x1 + 4, y1 + 2, anchor="nw", text=name,
                        fill=color, font=("Arial", 9))
```

**P6 字体**: `ResultPanel` 使用单一字体名 + 平台检测，不支持 Tkinter fallback 列表:
```python
import sys
_MONO_FONT = "Menlo" if sys.platform == "darwin" else "Consolas"
# 使用 font=(_MONO_FONT, 11)
```

### 3.11 widgets/result_panel.py — 结果面板

**职责**: 以结构化文字展示 GameState 各字段。

```python
class ResultPanel(ttk.Frame):
    """识别结果面板"""

    def __init__(self, parent, theme: dict[str, str], **kwargs):
        super().__init__(parent, **kwargs)
        self._theme = theme
        import sys
        mono = "Menlo" if sys.platform == "darwin" else "Consolas"
        self._text = tk.Text(self, wrap="word", state="disabled",
                             font=(mono, 11),  # P6: 单一字体，不用 fallback 列表
                             bg=theme["bg_secondary"],
                             fg=theme["fg_primary"])
        # 配置颜色标签
        self._text.tag_configure("label", foreground=theme["fg_secondary"])
        self._text.tag_configure("value", foreground=theme["fg_primary"])
        self._text.tag_configure("highlight", foreground=theme["highlight"])
        self._text.tag_configure("warning", foreground=theme["warning"])
        self._text.tag_configure("muted", foreground=theme["fg_muted"])

    def update_state(self, state: GameState | None, latency_ms: float = 0) -> None:
        """更新识别结果"""
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        if state is None:
            self._text.insert("end", "非静态帧 — 识别跳过", "muted")
        else:
            self._render_state(state, latency_ms)
        self._text.config(state="disabled")

    def on_theme_changed(self, theme: dict[str, str]) -> None:
        """主题切换"""
        self._theme = theme
        self._text.configure(bg=theme["bg_secondary"], fg=theme["fg_primary"])
        self._text.tag_configure("label", foreground=theme["fg_secondary"])
        self._text.tag_configure("value", foreground=theme["fg_primary"])
        self._text.tag_configure("highlight", foreground=theme["highlight"])
        self._text.tag_configure("warning", foreground=theme["warning"])
        self._text.tag_configure("muted", foreground=theme["fg_muted"])
```

**显示格式**（使用 Text 标签实现彩色）:
```
局次: 东一局 0本场 0供托
宝牌: 3s
────────────────
手牌: 1m 2m 3m 4m 5m 6m 7m 8m 9m 1p 2p 3p
摸牌: 4p                   ← highlight 颜色
────────────────
副露: -
────────────────
分数:
  自: 25000  右: 25000
  对: 25000  左: 25000
────────────────
牌河:
  自: 1m 2m 3m
  右: 4p 5p
  对: 6s 7s
  左: 1z 2z
────────────────
动作: -
延迟: 180ms
警告: 0
```

## 4. 依赖管理

### 4.1 新增依赖

```toml
[project.optional-dependencies]
gui = [
    "Pillow>=10.0",    # cv2 ndarray → ImageTk.PhotoImage 转换
]
# tkinterdnd2 作为可选的拖放支持，不写入依赖
# 用户手动安装: pip install tkinterdnd2
```

**环境前置**（不写入 pyproject.toml）:
- tkinter: macOS 需要 `brew install python-tk@3.14`
- tkinterdnd2: 可选拖放支持，`pip install tkinterdnd2`

### 4.2 现有依赖（不新增）

- `tkinter` / `ttk`: Python 标准库
- `opencv-python-headless`: 图像处理
- `numpy`: 数组操作
- `pydantic`: 数据模型

## 5. 入口点

```bash
# 启动 GUI
majsoul-recognizer gui

# 现有命令不变
majsoul-recognizer recognize -i screenshot.png
majsoul-recognizer capture -o ./output
majsoul-recognizer split screenshot.png
majsoul-recognizer calibrate --screenshot screenshot.png
```

```python
# cli.py 新增
elif args.command == "gui":
    from majsoul_recognizer.gui import main
    main()

# src/majsoul_recognizer/gui/__init__.py
def main() -> None:
    from majsoul_recognizer.gui.app import App
    app = App()
    app.run()
```

## 6. 错误处理

| 场景 | 处理方式 |
|------|---------|
| tkinter 不可用 | CLI `gui` 命令报错退出，提示安装方法 |
| 模型文件不存在 | 状态栏显示"检测器降级模式"，区域分割仍正常 |
| 窗口未找到 | 实时模式状态栏显示"未找到雀魂窗口，2秒后重试" |
| 窗口丢失后恢复 | LiveView 自动重连（每 2 秒重试 `find_window()`） |
| 图像格式不支持 | 弹出错误对话框 |
| onnxruntime 不可用 | 状态栏静默显示"检测器降级"，区域分割正常 |
| Worker 内异常 | try/except 包裹 `_run()`，异常放入 `_WorkerResult(error=str(e))`，状态栏显示错误 |
| Engine 重建失败 | 保持旧 engine，弹窗提示用户 |
| 捕获线程异常 | 捕获异常，通过 `_status_queue` 通知主线程 |
| Worker stop 超时 | `join(timeout=2.0)` 后放弃等待（daemon 线程随进程退出） |
| 不支持的平台 | `create_finder()` 抛 RuntimeError → 状态栏显示"不支持的平台" |
| 配置文件损坏 | GUISettings.load() 返回默认值，日志警告 |
| tkinterdnd2 不可用 | 隐藏拖放提示，仅显示"打开文件"按钮 |
| 识别慢于捕获速率 | 丢弃中间帧（`maxsize=1` 队列 + 任务锁） |

## 7. 测试策略

### 7.1 单元测试

| 模块 | 测试内容 |
|------|---------|
| `settings.py` | GUISettings 序列化/反序列化、默认值、损坏文件恢复、to_recognition_config() |
| `theme.py` | 颜色方案完整性、apply_style 不抛异常 |
| `worker.py` | submit/get_result、丢弃旧帧、stop+join、异常捕获、_WorkerResult.is_error |
| `base_view.py` | start/stop 生命周期、on_engine_changed 传递 |
| `_FPSCounter` | tick + fps 计算 |
| `settings_dialog.py` | 设置变更 → on_apply 回调、关闭按钮检测未保存修改 |
| `ImageCanvas` | winfo 尺寸 <= 1 时不绘制（L2） |
| App 根窗口 | tkinterdnd2 可用时使用 TkinterDnD.Tk()（M6） |
| Pipeline 隔离 | Worker 创建独立 pipeline 实例（S5） |

### 7.2 集成测试

| 场景 | 测试方式 |
|------|---------|
| 截图完整流程 | 合成图像 → mock 文件加载 → 验证 GameState 渲染 |
| 实时模式窗口丢失 | mock WindowFinder → 验证重连逻辑 |
| 降级模式 | 无 onnxruntime → 验证区域分割仍正常显示 |
| 视图切换 | 验证 start/stop 生命周期正确调用 |
| Engine 重建 | mock 设置变更 → 验证 Worker 更新 engine 引用 |

### 7.3 手动测试清单

- [ ] 截图文件加载 → 识别 → 结果显示
- [ ] 拖放截图文件 → 自动识别
- [ ] 实时模式启动/暂停/重置/窗口丢失重连
- [ ] 深色/浅色主题切换
- [ ] 设置修改 → 保存 → 重启后加载
- [ ] 模型不可用时的降级体验（区域分割图正常显示）
- [ ] 窗口缩放 → 图像 Canvas 自适应

## 8. 不涉及

- 模型训练 GUI
- 多语言/国际化
- 自动对局策略推荐
- 音频提示
- 历史记录/回放
- 网络功能（远程识别、云端模型）
- Canvas 手绘图表（柱状图/FPS 曲线）
- 树形 JSON 折叠
