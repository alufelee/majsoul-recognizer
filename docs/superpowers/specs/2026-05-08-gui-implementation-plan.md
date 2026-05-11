# GUI 实施计划

> 日期: 2026-05-08 | 基于设计文档 v3.1（含 P3-P8 修复）
>
> 核心设计文档: `docs/superpowers/specs/2026-05-08-gui-design.md`
> 需要参考的现有代码:
> - `src/majsoul_recognizer/recognition/engine.py` — RecognitionEngine 接口
> - `src/majsoul_recognizer/recognition/config.py` — RecognitionConfig 字段
> - `src/majsoul_recognizer/pipeline.py` — CapturePipeline 接口
> - `src/majsoul_recognizer/types.py` — FrameResult, GameState, Detection, BBox, ZoneName
> - `src/majsoul_recognizer/capture/finder.py` — create_finder(), WindowInfo
> - `src/majsoul_recognizer/capture/screenshot.py` — ScreenCapture (context manager)
> - `src/majsoul_recognizer/cli.py` — format_output()

---

## Phase 1: 基础设施（无 UI 依赖，可独立测试）

### Step 1: `gui/__init__.py` + CLI 入口 + pyproject.toml

**创建文件**:
- `src/majsoul_recognizer/gui/__init__.py`

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

**修改文件**:
- `src/majsoul_recognizer/cli.py` — 在 `main()` 的 subparsers 后新增 `gui` 子命令:
  ```python
  gui_parser = subparsers.add_parser("gui", help="启动图形界面")
  # ... 在 args.command 判断中:
  elif args.command == "gui":
      from majsoul_recognizer.gui import main
      main()
  ```
- `pyproject.toml` — 新增:
  ```toml
  [project.optional-dependencies]
  gui = ["Pillow>=10.0"]
  ```

**验证**: `python -c "from majsoul_recognizer.gui import main"` 报错（App 尚不存在）

**AI 上下文需求**: 无。仅需 Python 基础和 argparse 知识。

---

### Step 2: `gui/theme.py`

**创建文件**: `src/majsoul_recognizer/gui/theme.py`

从设计文档 §3.4 复制 `Theme.DARK` 和 `Theme.LIGHT` 字典（共 13 个颜色键），实现:
- `get_theme(name: str) -> dict[str, str]` — 返回 `Theme.DARK` 或 `Theme.LIGHT`
- `apply_style(style: ttk.Style, theme: dict) -> None` — 配置 `"."`, `"TFrame"`, `"TLabel"`, `"TButton"`, `"TCheckbutton"` 样式

**关键点**: `apply_style` 中 `style.configure(".", background=theme["bg_primary"], foreground=theme["fg_primary"])` 设置全局默认。Canvas/Text 等 tk（非 ttk）组件在创建时读取 theme 字典。

**验证**: 单元测试 — 验证 DARK/LIGHT 各有 13 个键、键名一致、`apply_style` 不抛异常

**AI 上下文需求**: 低。仅需 `ttk.Style` API 知识。

---

### Step 3: `gui/settings.py`

**创建文件**: `src/majsoul_recognizer/gui/settings.py`

从设计文档 §3.5 复制 `GUISettings` dataclass。关键实现:

```python
from dataclasses import dataclass, ClassVar
from pathlib import Path
import json

@dataclass
class GUISettings:
    # ... 字段见设计文档 §3.5 ...
    _PATH: ClassVar[Path] = Path.home() / ".majsoul-recognizer" / "settings.json"

    @classmethod
    def load(cls) -> "GUISettings":
        if not cls._PATH.exists():
            return cls()
        try:
            data = json.loads(cls._PATH.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError):
            return cls()

    def save(self) -> None:
        self._PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._PATH)  # 原子写入
```

`to_recognition_config()` 直接从设计文档复制。`to_pipeline_config()` 返回 `(config_path, frame_threshold)` 元组。

**验证**: 单元测试 — 序列化/反序列化、损坏文件返回默认值、`to_recognition_config()` 产出正确的 RecognitionConfig

**AI 上下文需求**: 中。需要读取 `recognition/config.py` 理解 RecognitionConfig 字段。任务描述中应附上 RecognitionConfig 的字段列表:
```
RecognitionConfig 字段: model_path, mapping_path, nms_iou_threshold, detection_confidence,
ocr_model_dir, template_dir, score_min, score_max, fusion_window_size,
drawn_tile_gap_multiplier, call_group_gap_multiplier, enable_batch_detection
```

---

### Step 4: `gui/worker.py`

**创建文件**: `src/majsoul_recognizer/gui/worker.py`

从设计文档 §3.2 复制 `_WorkerResult` 和 `_RecognizeWorker`。这是 Phase 1 最关键的模块。

**AI 必须理解的接口签名**（应包含在任务描述中）:
```python
# RecognitionEngine.recognize(zones) -> GameState
#   zones: dict[str, np.ndarray] — 区域名称到 BGR 图像的映射
#   返回: GameState（见 types.py）
#
# CapturePipeline.process_image(image) -> FrameResult
#   image: np.ndarray — BGR 格式完整截图
#   返回: FrameResult(frame_id, timestamp, zones, is_static, game_state)
#     其中 zones: dict[str, np.ndarray], is_static: bool
```

**验证**: 单元测试 — submit→get_result 正常路径、连续 submit 丢弃旧帧、stop→join 线程退出、异常路径返回 is_error=True

**AI 上下文需求**: 中高。需要理解上述两个接口的签名和返回类型，但不需要理解内部实现。任务描述中必须包含接口签名。

---

## Phase 2: 可复用 Widget

### Step 5: `gui/widgets/__init__.py` + `gui/widgets/image_canvas.py`

**创建文件**:
- `src/majsoul_recognizer/gui/widgets/__init__.py`（空文件）
- `src/majsoul_recognizer/gui/widgets/image_canvas.py`

从设计文档 §3.10 复制 `ImageCanvas` 类。

**P3 关键: 坐标转换 — 必须包含在任务描述中**:
```python
def _to_canvas_coords(self, x, y, w, h):
    """原始图像像素坐标 → Canvas 像素坐标"""
    ox, oy = self._offset  # show_image() 中计算
    s = self._scale        # show_image() 中计算
    return (int(x * s) + ox, int(y * s) + oy,
            int((x + w) * s) + ox, int((y + h) * s) + oy)
```

**P5 关键: Configure 事件处理 — 必须包含在任务描述中**:
```python
# __init__ 中:
self._pending_image = None
self.bind("<Configure>", self._on_configure)

# 方法:
def _on_configure(self, event):
    if self._pending_image is not None:
        self.show_image(self._pending_image)
```

**PhotoImage 引用陷阱**: `self._photo = ImageTk.PhotoImage(...)` 必须保存为实例属性，否则会被 GC 回收导致图像消失。

**验证**: 单元测试 — mock ndarray 输入、坐标转换正确性。手动测试需要 Tk 窗口（可延后到 Phase 3）

**AI 上下文需求**: 高。需要理解 Canvas 坐标系、PIL/ImageTk 转换、PhotoImage GC 陷阱。任务描述中必须包含坐标转换代码和 Configure 事件代码。

---

### Step 6: `gui/widgets/result_panel.py`

**创建文件**: `src/majsoul_recognizer/gui/widgets/result_panel.py`

从设计文档 §3.11 复制 `ResultPanel` 类。

**P6 字体修复 — 必须包含在任务描述中**:
```python
import sys
mono = "Menlo" if sys.platform == "darwin" else "Consolas"
self._text = tk.Text(..., font=(mono, 11))  # 不用 fallback 列表
```

**GameState 字段 — 必须包含在任务描述中**:
```python
# GameState 字段（来自 types.py）:
# round_info: RoundInfo | None — wind, number, honba, kyotaku
# dora_indicators: list[str]
# scores: dict[str, int]
# hand: list[str]
# drawn_tile: str | None
# calls: dict[str, list[CallGroup]]
# discards: dict[str, list[str]]
# actions: list[str]
# timer_remaining: int | None
# warnings: list[str]
```

`_render_state()` 方法格式化输出见设计文档 §3.11 末尾的显示格式。

**验证**: 单元测试 — mock GameState 渲染文字、主题切换更新颜色

**AI 上下文需求**: 中。需要理解 GameState 字段。任务描述中应包含字段列表和显示格式。

---

## Phase 3: 骨架 App + BaseView

### Step 7: `gui/base_view.py` + `gui/views/__init__.py`

**创建文件**:
- `src/majsoul_recognizer/gui/views/__init__.py`（空文件）
- `src/majsoul_recognizer/gui/base_view.py`

从设计文档 §3.1 复制 `BaseView` 类。

**P1 关键: pipeline_factory 构造 — 必须包含在任务描述中**:
```python
# AppState.pipeline_factory 是一个 Callable[[], CapturePipeline]
# 在 App 中构造:
def _make_pipeline_factory(settings: GUISettings):
    def factory():
        config_path, frame_threshold = settings.to_pipeline_config()
        return CapturePipeline(config_path=config_path, frame_threshold=frame_threshold)
    return factory
```

**验证**: 单元测试 — mock AppState，验证 start/stop 生命周期、_ensure_worker 创建/复用

**AI 上下文需求**: 中。需要理解 pipeline_factory 的构造方式。任务描述中必须包含工厂函数代码。

---

### Step 8: `gui/app.py` — 最小骨架

**创建文件**: `src/majsoul_recognizer/gui/app.py`

从设计文档 §3.3 复制 `App` 类。

**M6 根窗口条件初始化 — 必须包含在任务描述中**:
```python
def _create_root(self):
    try:
        from tkinterdnd2 import TkinterDnD
        return TkinterDnD.Tk()
    except ImportError:
        return tk.Tk()
```

**P4 回调机制 — 必须包含在任务描述中**:
```python
# App.__init__ 中:
self._last_frame = None
self._last_state = None

def _make_on_result(self):
    def on_result(frame, state):
        self._last_frame = frame
        self._last_state = state
        if isinstance(self._active_view, DevView):
            self._active_view.update_data(frame, state)
    return on_result

# 创建视图时:
on_result = self._make_on_result()
self._views = {
    "screenshot": ScreenshotView(content, app_state, theme, on_result=on_result),
    "live": LiveView(content, app_state, theme, on_result=on_result),
    "dev": DevView(content, app_state, theme, on_result=None),
}
```

**三个空视图占位**: 临时使用 `BaseView` 子类（不做任何事），Phase 4-6 逐步替换。

**App 布局**:
```
root
├── title_bar (Frame, pack top)     — 标题 + 主题按钮 + 设置按钮
├── body (Frame, pack fill+expand)
│   ├── sidebar (Frame, pack left, width=64) — 截图/实时/调试 按钮
│   └── content (Frame, pack fill+expand)     — 视图 grid 在这里
└── status_bar (Frame, pack bottom) — 状态灯 + 文字 + FPS
```

**验证**: `majsoul-recognizer gui` 启动，显示窗口框架 + 侧边栏（三个空白视图）

**AI 上下文需求**: 高。这是最复杂的骨架步骤，需要理解 App 全局结构。任务描述中必须包含: 布局层次、M6 根窗口代码、P4 回调代码、pipeline_factory 构造。

---

## Phase 4: 截图模式（拆分为两步）

### Step 9a: `gui/views/screenshot_view.py` — UI 布局 + 文件加载

**创建文件**: `src/majsoul_recognizer/gui/views/screenshot_view.py`

实现 ScreenshotView 的 UI 布局（不连接识别功能）:
- 左侧: `ImageCanvas`
- 右侧: `ResultPanel`
- 底部: `[打开文件]` 按钮 + 状态标签

`_on_open_file()` → `filedialog.askopenfilename()` → `cv2.imread()` → `self._canvas.show_image(image)`

**不实现**: Worker 集成、拖放

**验证**: 启动 GUI，选择截图文件，看到图像显示在 Canvas 上

**AI 上下文需求**: 中。需要理解 ImageCanvas 和 ResultPanel 的接口（从 Step 5/6 的产出）。

---

### Step 9b: ScreenshotView — 识别集成 + 拖放 + 错误处理

在 Step 9a 基础上添加:
- `recognize()` 方法 → `self._ensure_worker().submit(image)` + `self.after(50, self._poll_result)`
- `_poll_result()` — 处理 `_WorkerResult`（正常路径 + is_error 路径）
- P4 回调: `_poll_result` 中拿到结果后调用 `self._on_result(frame, state)`
- 拖放: `try: from tkinterdnd2 ...` 条件启用
- 状态更新: `_update_display()` → `canvas.show_image()` + `result_panel.update_state()`

**验证**: 选择截图文件 → 图像显示 + 识别结果出现在右侧面板

**AI 上下文需求**: 中高。需要完整理解 Worker 数据流和 _WorkerResult 类型。任务描述中应包含数据流图:
```
用户选文件 → cv2.imread → _ensure_worker().submit(image)
                                    ↓ [识别线程]
                              pipeline.process_image(image)
                                    ↓ FrameResult
                              engine.recognize(frame.zones) [仅 is_static]
                                    ↓ GameState
                              result_queue → root.after(50) 轮询
                                    ↓ _WorkerResult
                              if is_error → 状态栏显示错误
                              else → canvas.show_image + result_panel.update_state
                                    + self._on_result(frame, state)  [P4 回调]
```

---

## Phase 5: 实时模式（拆分为两步）

### Step 10a: `gui/views/live_view.py` — UI 布局 + 捕获线程

**创建文件**: `src/majsoul_recognizer/gui/views/live_view.py`

实现 LiveView 的 UI 布局和捕获线程（不连接识别）:
- 上方: `ImageCanvas`
- 中间: `[开始] [暂停] [重置]` + FPS 显示
- 下方: `ResultPanel`（紧凑布局）

`_capture_loop()` — 仅截图 + `canvas.show_image()`，不提交到 Worker。
`_FPSCounter` 内部类。
L4: `create_finder()` 异常 → status_queue 通知。
M5: `with ScreenCapture() as capture:` 资源管理。

**两个停止信号的区别 — 必须包含在任务描述中**:
```
_capture_stop (threading.Event): 控制捕获线程的生命周期
  - LiveView.start() → clear() → 捕获线程启动
  - LiveView.stop() → set() → join(2.0) → 捕获线程退出

_stop_event (在 Worker 中，通过 BaseView.stop() 控制): 控制识别线程
  - _ensure_worker() → Worker 线程启动
  - BaseView.stop() → worker.stop() → stop_event.set() → join(2.0)
```

**验证**: 启动 GUI → 切换到实时模式 → 点击开始 → 看到雀魂窗口截图（不识别）

**AI 上下文需求**: 高。需要理解双线程架构。任务描述中必须包含两个停止信号的说明。

---

### Step 10b: LiveView — 识别集成 + 状态机

在 Step 10a 基础上添加:
- `_capture_loop()` 中 `worker = self._ensure_worker()` + `worker.submit(image)`
- `_poll_result()` — 同 Step 9b 的模式
- P4 回调: `_poll_result` 中调用 `self._on_result(frame, state)`
- 状态机: 开始→捕获中→暂停→等待重连→重置
- `_status_queue` 消费: `root.after(100, _poll_status)` 处理 "window_not_found" 等

**验证**: 启动实时 → 看到识别结果实时更新。关闭雀魂窗口 → 状态栏显示重连提示

**AI 上下文需求**: 中高。需要理解三层线程协作。任务描述中应包含状态机图和数据流。

---

## Phase 6: 调试视图 + 设置 + 主题

### Step 11: `gui/views/dev_view.py`

**创建文件**: `src/majsoul_recognizer/gui/views/dev_view.py`

- 双 `ImageCanvas`（区域标注模式 + 检测框模式）
- JSON Text + 复制按钮
- 性能统计文字
- `update_data(frame, state)` 方法 — 由 App 通过 P4 回调调用

**区域坐标获取 — 必须包含在任务描述中**:
```python
# 如何从 ZoneDefinition 获取像素坐标:
# ZoneDefinition.to_bbox(img_width, img_height) → BBox(x, y, width, height)
# 然后 image_canvas.set_zones({name: (bbox.x, bbox.y, bbox.width, bbox.height), ...}, ZONE_COLORS)
#
# ZoneDefinition 列表来源: CapturePipeline._splitter._config (list[ZoneDefinition])
# 但 GUI 无法直接访问 pipeline 内部。替代方案:
# 1. 用 load_zone_config(config_path) 加载配置 → 遍历 ZoneDefinition
# 2. 或从 FrameResult.zones 的键名和图像尺寸反推区域位置
```

**验证**: 截图模式识别一张图 → 切换到调试 → 看到区域标注和 JSON

**AI 上下文需求**: 中高。区域坐标获取是关键难点。任务描述中必须包含上述说明。

---

### Step 12: `gui/settings_dialog.py`

**创建文件**: `src/majsoul_recognizer/gui/settings_dialog.py`

从设计文档 §3.6 复制 `SettingsDialog`。M4 关闭按钮行为已在设计文档中。

**验证**: 点击设置按钮 → 弹窗 → 修改参数 → 点应用/关闭 → engine 重建

**AI 上下文需求**: 中。需要理解 GUISettings 字段。任务描述中应包含字段列表。

---

### Step 13: 主题切换集成

在 `App._switch_theme()` 中:
1. `app_state.theme_name = new_name`
2. `apply_style(self._style, new_theme)`
3. 侧边栏 Frame 背景 → `configure(bg=new_theme["bg_sidebar"])`
4. `for view in self._views.values(): view.on_theme_changed(new_theme)`
5. `self._settings.theme = new_name; self._settings.save()`

**验证**: 点击主题按钮 → 全界面切换深色/浅色

**AI 上下文需求**: 低。仅需连接已有的 theme.py 和 BaseView.on_theme_changed。

---

## Phase 7: 集成验证

### Step 14: 集成测试

- 截图完整流程（合成图像 → mock 文件 → 验证 GameState 渲染）
- 视图切换生命周期（start/stop 调用顺序）
- Engine 重建（mock 设置变更 → Worker engine 引用更新）
- 降级模式（无 onnxruntime → 区域分割正常）
- Worker 异常路径（mock engine 抛异常 → is_error=True）
- 运行手动测试清单（设计文档 §7.3）

---

## 依赖关系图

```
Step 1 (CLI入口)
  ↓
Step 2 (theme) ← 独立，可并行
Step 3 (settings) ← 独立，可并行
Step 4 (worker) ← 独立，可并行
  ↓ (Step 2/3/4 全部完成后)
Step 5 (ImageCanvas) ← 依赖 Step 2 (theme)
Step 6 (ResultPanel) ← 依赖 Step 2 (theme) + types.py
Step 7 (BaseView) ← 依赖 Step 4 (worker)
  ↓ (Step 5/6/7 全部完成后)
Step 8 (App骨架) ← 依赖 Step 2/3/4/5/6/7 全部
  ↓
Step 9a (截图UI) ← 依赖 Step 5/6/8
Step 9b (截图识别) ← 依赖 Step 9a
  ↓
Step 10a (实时UI) ← 依赖 Step 5/6/8
Step 10b (实时识别) ← 依赖 Step 10a
  ↓
Step 11 (调试视图) ← 依赖 Step 8 + 9a
Step 12 (设置弹窗) ← 依赖 Step 3/8
Step 13 (主题集成) ← 依赖 Step 2/8
  ↓
Step 14 (集成测试) ← 依赖全部
```

**可并行的步骤**:
- Step 2 + Step 3 + Step 4 可同时执行（三者独立）
- Step 9a 和 Step 10a 可同时执行（都只依赖 Step 5/6/8）

---

## 每步 AI 子代理上下文清单

| Step | 必须提供的上下文 | 风险 |
|------|----------------|------|
| 1 | 无（纯 Python） | 低 |
| 2 | 设计文档 §3.4 全文 | 低 |
| 3 | 设计文档 §3.5 全文 + RecognitionConfig 字段列表 | 低 |
| 4 | 设计文档 §3.2 全文 + Engine/Pipeline 接口签名 | 中 |
| 5 | 设计文档 §3.10 全文 + P3坐标转换代码 + P5 Configure代码 | 高 |
| 6 | 设计文档 §3.11 全文 + GameState字段列表 + P6字体修复 | 中 |
| 7 | 设计文档 §3.1 全文 + P1 pipeline_factory代码 | 中 |
| 8 | 设计文档 §3.3 全文 + M6根窗口 + P4回调 + pipeline_factory | 高 |
| 9a | 设计文档 §3.7 布局部分 + ImageCanvas/ResultPanel 接口 | 中 |
| 9b | 设计文档 §3.7 识别部分 + 数据流图 + _WorkerResult接口 | 中高 |
| 10a | 设计文档 §3.8 布局+捕获部分 + 两个停止信号说明 | 高 |
| 10b | 设计文档 §3.8 识别部分 + 状态机图 + 三层数据流 | 中高 |
| 11 | 设计文档 §3.9 全文 + 区域坐标获取说明 | 中高 |
| 12 | 设计文档 §3.6 全文 + GUISettings字段列表 | 中 |
| 13 | 设计文档 §3.4 主题切换流程 | 低 |
| 14 | 设计文档 §7 测试策略 + 全部模块接口 | 中 |
