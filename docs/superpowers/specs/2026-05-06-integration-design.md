# 雀魂麻将识别助手 — Plan 3: 集成验证设计

> 版本: 1.0 | 日期: 2026-05-06 | 阶段: 第三阶段

## 1. 目标

将 CapturePipeline（Plan 1）与 RecognitionEngine（Plan 2）集成为端到端流水线，提供 CLI 命令入口，并通过集成测试验证整条链路的正确性。

## 2. 范围

| 包含 | 不包含 |
|------|--------|
| `recognize` CLI 子命令 | 实时视频流模式 |
| JSON 格式输出 | GUI 界面 |
| 合成数据集成测试 | 真实截图测试（下一阶段） |
| `[project.scripts]` 入口点 | 模型训练/部署 |
| 非静态帧降级输出 | 多帧流式处理 |
| 错误处理 + 退出码 | — |

## 3. 架构

```
CLI (argparse)
  └─ recognize 命令
      ├─ 读取图片 (cv2.imread)
      ├─ CapturePipeline.process_image(image)
      │   └─ FrameResult { zones, is_static, frame_id, timestamp }
      ├─ is_static? → RecognitionEngine.recognize(zones)
      │           └─ GameState
      └─ 输出 JSON (stdout)
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

### 4.3 输出格式

成功时输出 JSON 到 stdout：

```json
{
  "frame_id": 1,
  "timestamp": "2026-05-06T10:00:00+00:00",
  "is_static": true,
  "game_state": {
    "round_info": null,
    "dora_indicators": [],
    "scores": {},
    "hand": ["1m", "2m"],
    "drawn_tile": null,
    "calls": {},
    "discards": {},
    "actions": [],
    "timer_remaining": null,
    "warnings": []
  }
}
```

非静态帧降级输出：

```json
{
  "frame_id": 1,
  "timestamp": "...",
  "is_static": false,
  "game_state": null,
  "warnings": ["frame_not_static"]
}
```

### 4.4 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1 | 一般错误（文件不存在、格式错误等） |
| 2 | 参数错误（argparse 自动处理） |

### 4.5 错误输出

错误信息输出到 stderr，不影响 stdout 的 JSON。

## 5. 入口点配置

在 `pyproject.toml` 添加：

```toml
[project.scripts]
majsoul-recognizer = "majsoul_recognizer.cli:main"
```

## 6. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/majsoul_recognizer/cli.py` | 修改 | 添加 `recognize` 子命令 |
| `pyproject.toml` | 修改 | 添加 `[project.scripts]` |
| `tests/test_cli.py` | 修改 | 添加 recognize 命令测试 |
| `tests/test_integration.py` | 新建 | 端到端集成测试 |

## 7. 集成测试策略

### 7.1 合成数据测试

使用 `tests/conftest.py` 的 `sample_screenshot` 生成 1920x1080 合成截图，配合 `dummy_detector_path` 和 `fake_template_dir` fixture：

| 测试用例 | 说明 |
|----------|------|
| 合成截图完整流水线 | 截图 → pipeline → engine → JSON |
| 非静态帧降级 | 连续相同帧为静态、不同帧为非静态 |
| 文件不存在 | 图片路径无效 → 退出码 1 |
| 无效图片格式 | 非图片文件 → 退出码 1 |
| 缺少模型文件 | 模型路径无效 → 使用 StubDetector 降级 |

### 7.2 测试隔离

- 合成测试不依赖任何外部资源（无真实模型、无真实截图）
- 使用 `_StubDetector` 降级路径验证端到端流程
- 使用 `dummy_detector_path` fixture 验证有模型时的流程

## 8. 实现约束

- **约 150 行新增代码**（cli.py ~60 行，测试 ~90 行）
- **不修改** `pipeline.py`、`engine.py`、`types.py` 的核心逻辑
- **不引入** 新的依赖包
- JSON 序列化使用 Pydantic 的 `model_dump()` + `json.dumps()`
