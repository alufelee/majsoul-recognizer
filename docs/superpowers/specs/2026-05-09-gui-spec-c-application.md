# GUI 子规格 C — 应用层

> 日期: 2026-05-09
> 主设计文档: `docs/superpowers/specs/2026-05-08-gui-design.md`（以下简称"主文档"）
> 本文档为主文档的切片，仅包含应用层模块的详细设计。
> 前置依赖: 子规格 A（基础设施）+ 子规格 B（组件层）已完成。

## 涵盖范围

| 模块 | 文件 | 对应主文档章节 |
|------|------|--------------|
| 主窗口 | `gui/app.py` | §3.3 |
| 设置弹窗 | `gui/settings_dialog.py` | §3.6 |
| 截图模式 | `gui/views/screenshot_view.py` | §3.7 |
| 实时模式 | `gui/views/live_view.py` | §3.8 |
| 开发调试 | `gui/views/dev_view.py` | §3.9 |
| 错误处理 | — | §6 |
| 测试策略 | — | §7 |

## 1. `gui/app.py` — 主窗口

**职责**: 创建 Tkinter 根窗口，管理侧边栏导航，切换视图，维护全局状态。

```python
class App:
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
1. 创建根窗口 — M6: `tkinterdnd2` 可用时使用 `TkinterDnD.Tk()`，否则 `tk.Tk()`。从 `GUISettings` 恢复窗口尺寸和位置
2. 配置 `ttk.Style`（`theme.apply_style()`）
3. 创建标题栏 `Frame`（标题 + 主题按钮 + 设置按钮）
4. 创建侧边栏 `Frame`（文字导航按钮）
5. 创建主内容区 `Frame`
6. 创建状态栏 `Frame`
7. 实例化 `RecognitionEngine`（`GUISettings.to_recognition_config()`）
8. 创建 `AppState`
9. 实例化三个视图（Worker 延迟创建）
10. 显示默认视图（截图模式）

**M6 根窗口条件初始化**:
```python
def _create_root(self) -> tk.Tk:
    try:
        from tkinterdnd2 import TkinterDnD
        return TkinterDnD.Tk()
    except ImportError:
        return tk.Tk()
```

**AppState**（定义在 Spec A §3.4）:
```python
@dataclass
class AppState:
    engine: RecognitionEngine
    pipeline_factory: Callable[[], CapturePipeline]
    config: RecognitionConfig
    theme_name: str  # "dark" | "light"
```

**视图切换**:
```python
def _switch_view(self, view_name: str) -> None:
    if self._active_view:
        self._active_view.stop()
    self._active_view = self._views[view_name]
    self._active_view.start()
```

**Engine 重建**（设置变更时）:
```python
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
```

**P4 结果回调** — 视图产生结果时通知 App，供 DevView 使用:
```python
self._last_frame: FrameResult | None = None
self._last_state: GameState | None = None

def _make_on_result(self) -> Callable:
    def on_result(frame: FrameResult, state: GameState | None):
        self._last_frame = frame
        self._last_state = state
        if isinstance(self._active_view, DevView):
            self._active_view.update_data(frame, state)
    return on_result
```

**运行入口**:
```python
def run(self) -> None:
    self._root.protocol("WM_DELETE_WINDOW", self._on_close)
    self._root.mainloop()

def _on_close(self) -> None:
    for view in self._views.values():
        view.stop()
    # 保存窗口几何到 GUISettings
    self._settings.window_width = self._root.winfo_width()
    self._settings.window_height = self._root.winfo_height()
    self._settings.window_x = self._root.winfo_x()
    self._settings.window_y = self._root.winfo_y()
    self._settings.save()
    self._root.destroy()
```

**侧边栏**: 文字标签（"截图"/"实时"/"调试"），选中项背景高亮，字体 size=10。

**布局管理**: 使用 `grid()`，所有视图 `grid()` 在同一位置 `(row=0, column=0)`，切换时 `grid_remove()` / `grid()`。

**状态栏**: 左侧状态指示灯（Canvas 圆点 ●）+ 状态文字，右侧 FPS/延迟/帧数。

## 2. `gui/settings_dialog.py` — 设置弹窗

**职责**: 独立的 `tkinter.Toplevel` 对话框，管理所有可配置项。

```python
class SettingsDialog:
    def __init__(self, parent: tk.Tk, settings: GUISettings,
                 on_apply: Callable[[], None]):
        self._dialog = tk.Toplevel(parent)
        self._dialog.title("设置")
        self._settings = settings
        self._on_apply = on_apply
        self._initial_snapshot = dataclasses.asdict(settings)

    def _on_apply_clicked(self) -> None:
        self._sync_to_settings()
        self._settings.save()
        self._on_apply()  # App._rebuild_engine()
        self._initial_snapshot = dataclasses.asdict(self._settings)

    def _on_close_clicked(self) -> None:
        self._sync_to_settings()
        if dataclasses.asdict(self._settings) != self._initial_snapshot:
            self._settings.save()
            self._on_apply()  # M4: 关闭前未应用的修改也生效
        self._dialog.destroy()
```

**配置项**: 模型路径、模板目录、区域配置、检测置信度、NMS IoU 阈值、捕获间隔、主题选择。

## 3. `gui/views/screenshot_view.py` — 截图模式

**职责**: 加载截图文件（文件选择/拖放）→ 执行识别 → 展示结果。

**布局**:
```
┌─────────────────────────┬───────────────────────┐
│                         │ 局次: 东一局 0本场      │
│   ImageCanvas           │ 宝牌: 3s               │
│   (截图 + 区域标注      │                        │
│    + 检测框)            │ 手牌: 1m 2m 3m...4p   │
│                         │                        │
│                         │ 分数: 自 25000 ...     │
│                         │ 牌河: 自 1m 2m 3m ...  │
├─────────────────────────┴───────────────────────┤
│ [打开文件] [识别] | 拖放截图文件到此处              │
└─────────────────────────────────────────────────┘
```

```python
class ScreenshotView(BaseView):
    def __init__(self, parent, app_state, theme, on_result, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        self._current_image: np.ndarray | None = None
        self._current_frame: FrameResult | None = None
        self._current_state: GameState | None = None
        self._on_result = on_result  # P4: 回调
        self._is_busy = False  # [S2] 识别进行中标志
        self._open_button: ttk.Button  # [S2] 打开文件按钮
        self._recognize_button: ttk.Button  # [S2] 识别按钮
```

**异步识别（[S2 修复] 含并发保护）**:
```python
def recognize(self, image: np.ndarray) -> None:
    # [S2] 如果 Worker 正忙，禁用按钮并提示
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
        # [S2] 无论成功失败，恢复按钮状态
        self._is_busy = False
        self._open_button.config(state="normal")
        self._recognize_button.config(state="normal")
        if result.is_error:
            self._status_label.config(text=f"错误: {result.error}")
        else:
            self._current_frame = result.frame
            self._current_state = result.state
            self._update_display(result.image, result.frame, result.state)
            self._status_label.config(text="就绪")
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
- 可用时: 注册 `dnd_bind('<<Drop>>', _on_drop)`
- 不可用时: 隐藏拖放提示，仅显示"打开文件"按钮

## 4. `gui/views/live_view.py` — 实时模式

**职责**: 连续捕获雀魂窗口画面 → 自动识别 → 实时更新结果。

**布局**:
```
┌──────────────────────────────────────────────┐
│  ImageCanvas (实时截图 + 检测框标注)           │
├──────────────────────────────────────────────┤
│ [开始] [暂停] [重置]  FPS: 5.2  延迟: 180ms   │
│ 局次: 东一局 0本场  |  手牌: 1m 2m...4p       │
│ 分数: 自 25000 右 25000 对 25000 左 25000     │
└──────────────────────────────────────────────┘
```

```python
class LiveView(BaseView):
    CAPTURE_INTERVAL = 0.2
    WINDOW_RETRY_INTERVAL = 2.0
    MAX_CONSECUTIVE_FAILS = 10

    def __init__(self, parent, app_state, theme, on_result, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        self._capture_thread: threading.Thread | None = None
        self._capture_stop = threading.Event()
        self._status_queue: queue.Queue = queue.Queue()
        self._fps_counter = _FPSCounter()
        self._current_state: GameState | None = None
        self._on_result = on_result
```

**实时捕获循环**（独立线程）:
```python
def _capture_loop(self) -> None:
    # [C4 修复] 顶层 try/except 防止线程静默崩溃
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
        # ScreenCapture 初始化失败、mss 异常等
        self._status_queue.put(("capture_error", str(e)))
```

**生命周期覆盖**:
```python
def start(self) -> None:
    super().start()
    self._capture_stop.clear()
    self._capture_thread = threading.Thread(
        target=self._capture_loop, daemon=True
    )
    self._capture_thread.start()
    self.after(50, self._poll_result)

def stop(self) -> None:
    self._capture_stop.set()
    if self._capture_thread and self._capture_thread.is_alive():
        self._capture_thread.join(timeout=2.0)
    super().stop()
```

**FPSCounter**（内置在 live_view.py 中）:
```python
class _FPSCounter:
    """简单 FPS 计数器（GIL 保证线程安全）"""
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

**状态机 + [S3 修复] 按钮状态定义**:
```
[空闲] --开始--> [捕获中] --暂停--> [暂停] --继续--> [捕获中]
  ↑                  |
  │              窗口丢失
  │                  ↓
  └────重置←── [等待重连]
```

**各状态下按钮 enabled/disabled**:

| 状态 | 开始 | 暂停 | 重置 | 说明 |
|------|------|------|------|------|
| 空闲 | **启用** | 禁用 | 禁用 | 初始状态，等待用户点击"开始" |
| 捕获中 | 禁用 | **启用** | 禁用 | 正在捕获+识别 |
| 暂停 | **启用** | 禁用 | **启用** | 用户主动暂停，可继续或重置 |
| 等待重连 | 禁用 | 禁用 | **启用** | 窗口丢失，自动重试中 |

```python
# [S3] 按钮状态管理
def _update_buttons(self, state: str) -> None:
    """根据状态机更新按钮"""
    self._start_button.config(state="normal" if state in ("idle", "paused") else "disabled")
    self._pause_button.config(state="normal" if state == "capturing" else "disabled")
    self._reset_button.config(state="normal" if state in ("paused", "reconnecting") else "disabled")
    self._state = state
```

**"重置"行为**:
- 停止捕获线程
- 重置 FPSCounter
- 清空 ImageCanvas 和 ResultPanel
- 状态回到"空闲"

## 5. `gui/views/dev_view.py` — 开发调试视图

**职责**: 展示区域分割图 + 检测框可视化 + JSON 输出 + 性能统计。

**布局**:
```
┌──────────────────────┬──────────────────────┐
│  ImageCanvas         │  ImageCanvas          │
│  (区域标注模式)       │  (检测框模式)          │
├──────────────────────┴──────────────────────┤
│  JSON 输出 (Text，可滚动，可复制)              │
├─────────────────────────────────────────────┤
│  性能: 总计 180ms | 检测 120ms | 帧: 42       │
└─────────────────────────────────────────────┘
```

**继承**: `BaseView`（`start()`/`stop()` 为空操作，不使用 Worker）。

**[C3 修复] DevView 完整接口**:
```python
class DevView(BaseView):
    def __init__(self, parent, app_state, theme, **kwargs):
        super().__init__(parent, app_state, theme, **kwargs)
        self._zone_canvas: ImageCanvas  # 左侧 — 区域标注模式
        self._det_canvas: ImageCanvas   # 右侧 — 检测框模式
        self._json_text: tk.Text        # JSON 输出
        self._perf_label: ttk.Label     # 性能统计
        self._copy_button: ttk.Button   # 复制 JSON
        self._current_image: np.ndarray | None = None

    def start(self) -> None:
        """视图激活时，显示 App 缓存的最近数据"""
        super().start()
        if self._app_state_last_frame is not None:
            # 从 App 获取最近数据（App 在 switch_view 时注入）
            pass  # 实际逻辑见 App._switch_view

    # [C3 修复] App 调用此方法推送数据
    def update_data(self, frame: FrameResult, state: GameState | None) -> None:
        """接收最新的 FrameResult + GameState，更新所有子组件

        由 App._make_on_result() 回调触发，仅在 DevView 活跃时调用。
        """
        # 1. 从 frame.zones 重建原始图像上的区域标注
        if self._current_image is not None:
            # 区域标注画布：绘制所有 zone 矩形
            zone_rects = self._compute_zone_rects(frame)
            self._zone_canvas.show_image(self._current_image)
            self._zone_canvas.set_zones(zone_rects, ZONE_COLORS)
            self._zone_canvas.set_mode("zones")

            # 检测框画布：绘制检测结果
            if state is not None:
                all_dets = self._collect_detections(frame, state)
                self._det_canvas.show_image(self._current_image)
                self._det_canvas.set_detections(all_dets)
                self._det_canvas.set_mode("detection")

        # 2. JSON 输出
        from majsoul_recognizer.cli import format_output
        output = format_output(frame, state)
        import json
        self._json_text.config(state="normal")
        self._json_text.delete("1.0", "end")
        self._json_text.insert("1.0", json.dumps(output, indent=2, ensure_ascii=False))
        self._json_text.config(state="disabled")

        # 3. 性能统计（文字）
        # （性能数据来源于 FrameResult 或额外计时，首版显示帧 ID 和状态）
        self._perf_label.config(
            text=f"帧: {frame.frame_id} | {'静态' if frame.is_static else '动画'}"
        )

    def set_current_image(self, image: np.ndarray) -> None:
        """设置当前显示的原始图像（App 在截图/实时视图产生结果时调用）"""
        self._current_image = image

    def _compute_zone_rects(self, frame: FrameResult) -> dict[str, tuple]:
        """从 FrameResult 的 zones 计算区域矩形（像素坐标）"""
        # 使用 ZoneSplitter 的配置重建区域位置
        # 实现时从 app_state.config 或 zones.yaml 获取区域定义
        ...

    def _collect_detections(self, frame: FrameResult, state: GameState) -> list:
        """从 GameState 的 hand/discards 等收集所有 Detection"""
        # 实现时需要 engine 返回的原始 Detection 数据
        # 或从 GameState 反推（首版可简化为空列表）
        ...
```

**数据来源**: App 维护 `_last_frame` / `_last_state` / `_last_image`，视图产生结果时更新。DevView 通过两种方式获取数据:
1. **实时推送**: `App._make_on_result()` 在截图/实时视图产生结果时，如果 DevView 活跃则直接调用 `update_data()`
2. **初始化加载**: `App._switch_view("dev")` 时，如果有缓存数据则调用 `update_data()`

```python
# App._switch_view 增强（C3 修复）
def _switch_view(self, view_name: str) -> None:
    if self._active_view:
        self._active_view.stop()
    self._active_view = self._views[view_name]
    self._active_view.start()
    # DevView 激活时推送缓存数据
    if view_name == "dev" and self._last_frame is not None:
        self._active_view.set_current_image(self._last_image)
        self._active_view.update_data(self._last_frame, self._last_state)

# App._make_on_result 增强
def _make_on_result(self) -> Callable:
    def on_result(frame: FrameResult, state: GameState | None):
        self._last_frame = frame
        self._last_state = state
        if isinstance(self._active_view, DevView):
            self._active_view.update_data(frame, state)
    return on_result
```

**区域标注**: 使用 `ZONE_COLORS` 颜色方案，虚线框 + 区域名称标注。

**检测框可视化**: 按牌面类别着色（万绿/筒蓝/索红/字紫/赤宝橙/特殊灰），标签含 `tile_code` 和 `confidence%`。

**JSON 输出**: `tkinter.Text`，`format_output()` 的 JSON 格式化输出，"复制 JSON" 按钮。

**性能统计**（文字）:
```
性能统计:
  总耗时: 180ms | 识别: 120ms
  FPS: 5.2 | 平均: 4.8 | 最大延迟: 320ms
  已处理: 42 帧 | 跳过(动画): 8 帧
```

## 6. 错误处理

| 场景 | 处理方式 |
|------|---------|
| tkinter 不可用 | CLI `gui` 命令报错退出 |
| 模型文件不存在 | 状态栏显示"检测器降级模式" |
| 窗口未找到 | 状态栏显示"未找到雀魂窗口，2秒后重试" |
| 窗口丢失后恢复 | LiveView 自动重连 |
| 图像格式不支持 | 弹出错误对话框 |
| onnxruntime 不可用 | 状态栏静默显示"检测器降级" |
| Worker 内异常 | `_WorkerResult(error=str(e))`，状态栏显示错误 |
| Engine 重建失败 | 保持旧 engine，弹窗提示 |
| 捕获线程异常 | [C4] 顶层 try/except → 通过 `_status_queue` 通知主线程（含 `capture_error`） |
| Worker stop 超时 | `join(timeout=2.0)` 后放弃 |
| 不支持的平台 | `create_finder()` 抛 RuntimeError |
| 配置文件损坏 | GUISettings.load() 返回默认值 |
| tkinterdnd2 不可用 | 隐藏拖放提示 |
| 识别慢于捕获速率 | 丢弃中间帧（`maxsize=1` 队列） |

## 7. 测试策略

### 7.1 单元测试

| 模块 | 测试内容 |
|------|---------|
| `settings.py` | 序列化/反序列化、默认值、损坏文件恢复、to_recognition_config() |
| `theme.py` | 颜色方案完整性、apply_style 不抛异常 |
| `worker.py` | submit/get_result、丢弃旧帧、stop+join、异常捕获 |
| `base_view.py` | start/stop 生命周期、on_engine_changed |
| `_FPSCounter` | tick + fps 计算 |
| `settings_dialog.py` | 设置变更 → on_apply 回调、关闭按钮检测未保存修改 |
| `ImageCanvas` | winfo 尺寸 <= 1 时不绘制 |
| App 根窗口 | tkinterdnd2 可用时使用 TkinterDnD.Tk() |
| Pipeline 隔离 | Worker 创建独立 pipeline 实例 |

### 7.2 集成测试

| 场景 | 测试方式 |
|------|---------|
| 截图完整流程 | 合成图像 → mock 文件加载 → 验证 GameState 渲染 |
| 实时模式窗口丢失 | mock WindowFinder → 验证重连逻辑 |
| 降级模式 | 无 onnxruntime → 验证区域分割仍正常 |
| 视图切换 | 验证 start/stop 生命周期正确调用 |
| Engine 重建 | mock 设置变更 → 验证 Worker 更新 engine |

### 7.3 手动测试清单

- [ ] 截图文件加载 → 识别 → 结果显示
- [ ] 拖放截图文件 → 自动识别
- [ ] 实时模式启动/暂停/重置/窗口丢失重连
- [ ] 深色/浅色主题切换
- [ ] 设置修改 → 保存 → 重启后加载
- [ ] 模型不可用时的降级体验
- [ ] 窗口缩放 → 图像 Canvas 自适应

## 8. 需要参考的现有代码

| 文件 | 用途 |
|------|------|
| `src/majsoul_recognizer/recognition/engine.py` | RecognitionEngine 接口 |
| `src/majsoul_recognizer/recognition/config.py` | RecognitionConfig 字段 |
| `src/majsoul_recognizer/pipeline.py` | CapturePipeline 接口 |
| `src/majsoul_recognizer/types.py` | FrameResult, GameState, Detection, BBox, ZoneName |
| `src/majsoul_recognizer/capture/finder.py` | create_finder(), WindowInfo |
| `src/majsoul_recognizer/capture/screenshot.py` | ScreenCapture (context manager) |
| `src/majsoul_recognizer/cli.py` | format_output(), CLI 入口 |
| `src/majsoul_recognizer/zones/config.py` | 区域定义 |
