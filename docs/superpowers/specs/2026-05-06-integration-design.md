# 雀魂麻将识别助手 — Plan 3: 集成验证设计

> 版本: 2.0 | 日期: 2026-05-07 | 阶段: 第三阶段

## 1. 目标

将 CapturePipeline（Plan 1）与 RecognitionEngine（Plan 2）集成为端到端流水线，提供 CLI 命令入口，并通过集成测试验证整条链路的正确性。

## 2. 范围

| 包含 | 不包含 |
|------|--------|
| `recognize` CLI 子命令 | 实时视频流模式 |
| JSON 格式输出（遵循产品规格书 §3） | GUI 界面 |
| 输出适配层（GameState → 产品规格格式） | 修改 GameState/RecognitionEngine |
| 合成数据集成测试 | 真实截图测试（下一阶段） |
| `[project.scripts]` 入口点 | 模型训练/部署 |
| 非静态帧降级输出 | 多帧流式处理 |
| 错误处理 + 退出码 | — |

## 3. 架构

```
CLI (argparse)
  └─ recognize 命令
      ├─ 构建 RecognitionConfig (CLI 参数映射)
      ├─ 读取图片 (cv2.imread)
      ├─ CapturePipeline.process_image(image)
      │   └─ FrameResult { zones, is_static, frame_id, timestamp }
      ├─ is_static?
      │   ├─ 是 → RecognitionEngine.recognize(zones) → GameState
      │   └─ 否 → 跳过识别，game_state = null
      ├─ 输出适配: format_output(FrameResult, GameState | None)
      │   └─ 将 GameState 字段名映射为产品规格书 §3 格式
      └─ JSON → stdout
```

## 4. CLI 设计

### 4.1 命令格式

```bash
majsoul-recognizer recognize --image <path> [--config <zones.yaml>] [--model <model.onnx>] [--template-dir <dir>]
```

### 4.2 参数

| 参数 | 必选 | 说明 |
|------|------|------|
| `--image` / `-i` | 是 | 输入截图文件路径 |
| `--config` | 否 | 区域配置文件路径（默认使用内置配置） |
| `--model` | 否 | ONNX 模型文件路径（默认使用内置路径） |
| `--template-dir` | 否 | 动作按钮模板目录（默认使用内置路径） |

### 4.3 CLI 参数 → RecognitionConfig 映射

```
--config      → CapturePipeline(config_path=...)   # 区域配置，传给 pipeline
--model       → RecognitionConfig(model_path=...)   # 模型路径，传给 engine
--template-dir → RecognitionConfig(template_dir=...) # 模板目录，传给 engine
```

构建逻辑：

```python
# 伪代码
def recognize_command(args):
    # 1. 构建 RecognitionConfig
    config_kwargs = {}
    if args.model:
        config_kwargs["model_path"] = Path(args.model)
    if args.template_dir:
        config_kwargs["template_dir"] = Path(args.template_dir)
    config = RecognitionConfig(**config_kwargs)

    # 2. 构建 Pipeline（config 用于区域分割）
    pipeline = CapturePipeline(config_path=args.config)

    # 3. 构建 Engine
    engine = RecognitionEngine(config)
```

**模型文件不存在时的处理**：`RecognitionConfig.get_model_path()` 抛出 `FileNotFoundError`。CLI 捕获此异常，输出错误到 stderr，退出码 1。不降级到 StubDetector（StubDetector 仅用于 onnxruntime 未安装的情况，而非文件缺失）。

### 4.4 输出格式

输出遵循产品规格书 §3 的扁平结构，通过输出适配层 `format_output()` 将 GameState 字段名映射为产品规格书定义的键名。

**适配映射表**：

| GameState 字段 | 产品规格书键名 | 转换规则 |
|----------------|--------------|---------|
| `round_info` | `round` | 直接重命名 |
| `timer_remaining` | `timer` | `None → null`；`int → {"active": true, "remaining": n}` |
| `dora_indicators` | `dora_indicators` | 无变化 |
| `scores` | `scores` | 无变化 |
| `hand` | `hand` | 无变化 |
| `drawn_tile` | `drawn_tile` | 无变化 |
| `calls` | `calls` | `model_dump()` 序列化（含 from_player） |
| `discards` | `discards` | 无变化 |
| `actions` | `actions` | 无变化 |
| `warnings` | `warnings` | 无变化 |

成功时输出 JSON 到 stdout（静态帧）：

```json
{
  "frame_id": 1,
  "timestamp": "2026-05-07T10:00:00+00:00",
  "is_static": true,
  "round": null,
  "dora_indicators": [],
  "scores": {},
  "hand": [],
  "drawn_tile": null,
  "calls": {},
  "discards": {},
  "actions": [],
  "timer": null,
  "warnings": []
}
```

非静态帧降级输出（跳过识别，game_state 不展开）：

```json
{
  "frame_id": 1,
  "timestamp": "2026-05-07T10:00:00+00:00",
  "is_static": false,
  "round": null,
  "dora_indicators": [],
  "scores": {},
  "hand": [],
  "drawn_tile": null,
  "calls": {},
  "discards": {},
  "actions": [],
  "timer": null,
  "warnings": ["frame_not_static"]
}
```

### 4.5 退出码

| 退出码 | 含义 | stdout | stderr |
|--------|------|--------|--------|
| 0 | 成功（静态帧或非静态帧降级） | JSON | 日志 |
| 1 | 运行时错误 | 无输出 | 错误信息 |
| 2 | 参数错误（argparse 自动处理） | 无输出 | 用法提示 |

### 4.6 输出流分离

- **成功**：JSON 输出到 stdout，日志输出到 stderr（仅 `--verbose` 时）
- **失败**：错误信息输出到 stderr，stdout **无任何输出**

## 5. 输出适配层

`format_output()` 函数负责将 `FrameResult` + `GameState | None` 转换为产品规格书格式的 dict：

```python
# 伪代码
def format_output(frame: FrameResult, state: GameState | None) -> dict:
    if state is None:
        # 非静态帧：所有识别字段为空
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

    # 静态帧：映射 GameState → 产品规格格式
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

## 6. 入口点配置

在 `pyproject.toml` 添加：

```toml
[project.scripts]
majsoul-recognizer = "majsoul_recognizer.cli:main"
```

## 7. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/majsoul_recognizer/cli.py` | 修改 | 添加 `recognize` 子命令 + `format_output()` |
| `pyproject.toml` | 修改 | 添加 `[project.scripts]` |
| `tests/test_cli.py` | 修改 | 添加 recognize 命令测试 |
| `tests/test_integration.py` | 新建 | 端到端集成测试 |

## 8. 集成测试策略

### 8.1 合成数据测试

使用 `tests/conftest.py` 的 `sample_screenshot` 生成 1920x1080 合成截图，配合 `tests/recognition/conftest.py` 的 `dummy_detector_path` 和 `fake_template_dir` fixture。

| # | 测试用例 | 输入 | 预期断言 |
|---|----------|------|---------|
| 1 | 静态帧 + StubDetector 完整流水线 | 合成截图，无模型 | 退出码 0；`is_static=True`；`hand=[]`；`warnings` 含 `"empty_zones"` 或无 detections |
| 2 | 静态帧 + dummy_detector | 合成截图，dummy ONNX 模型 | 退出码 0；`is_static=True`；JSON 可解析；`frame_id=1` |
| 3 | 非静态帧降级 | 连续传入两张不同截图，取第二帧 | 退出码 0；`is_static=False`；`warnings=["frame_not_static"]` |
| 4 | 文件不存在 | `--image /nonexistent.png` | 退出码 1；stderr 含错误信息；stdout 为空 |
| 5 | 无效图片格式 | `--image /dev/null` | 退出码 1；stderr 含错误信息 |
| 6 | 模型文件不存在 | `--model /nonexistent.onnx` | 退出码 1；stderr 含 FileNotFoundError 信息 |
| 7 | 输出格式符合产品规格书 §3 | 合成截图 | 输出含 `round`（非 `round_info`）；`timer` 为 null 或 `{"active":..., "remaining":...}` |

### 8.2 测试隔离

- 合成测试不依赖任何外部资源（无真实模型、无真实截图）
- 测试 #1/#3/#4/#5/#7：无 onnxruntime 时使用 `_StubDetector` 降级
- 测试 #2/#6：需要 onnxruntime（使用 `dummy_detector_path` fixture），标记 `pytest.mark.skipif(not _HAS_ORT)`
- 测试 #3 非静态帧：先调用 `pipeline.process_image(img_a)` 作为参考帧，再调用 `pipeline.process_image(img_b)` 其中 img_b 与 img_a 差异率 > 阈值

## 9. 实现约束

- **约 180 行新增代码**（cli.py ~80 行含 `format_output()`，测试 ~100 行）
- **不修改** `pipeline.py`、`engine.py`、`types.py` 的核心逻辑
- **不引入** 新的依赖包
- JSON 序列化使用 `json.dumps(format_output(...), ensure_ascii=False, indent=2)`
