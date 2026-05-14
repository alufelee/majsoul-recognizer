# ViT 集成 P5: 依赖更新与导出

## 目标

更新项目依赖，使 ViT 分类器可被正常安装和使用。

## 设计

### pyproject.toml 新增可选依赖组

```toml
[project.optional-dependencies]
# ... 现有组保留 ...
recognition-vit = [
    "torch>=2.1",
    "transformers>=4.34,<5.0",
    "Pillow>=9.0",
]
recognition-vit-cpu = [
    "torch>=2.1",
    "transformers>=4.34,<5.0",
    "Pillow>=9.0",
]
```

**版本约束说明**:
- `torch>=2.1` — pjura 模型用 PyTorch 2.1 训练，2.0 有已知的 ViT 推理问题
- `transformers>=4.34,<5.0` — 4.34 是训练版本，5.0 可能有 breaking change
- `Pillow>=9.0` — ViTImageProcessor 依赖 Pillow 做图像 I/O，显式声明避免隐式依赖

### CPU-only 安装

PyTorch CUDA 版 ~2.5GB，项目目标为"普通电脑无需 GPU 运行"。提供两种安装方式：

**方式 1: 指定 CPU index（推荐）**
```bash
pip install -e ".[recognition-vit-cpu]" \
    --extra-index-url https://download.pytorch.org/whl/cpu
```

`recognition-vit-cpu` 组的 torch 依赖同上，用户需通过 `--extra-index-url` 指定 CPU wheel。这是 PyTorch 官方推荐的 CPU-only 安装方式。

**方式 2: 完整安装（含 CUDA）**
```bash
pip install -e ".[recognition-vit]"
```

会安装 CUDA 版 PyTorch（~2.5GB），适合有 NVIDIA GPU 的用户。

### 全功能安装

```bash
pip install -e ".[recognition-detector,recognition-vit-cpu]" \
    --extra-index-url https://download.pytorch.org/whl/cpu
```

### __init__.py

不修改 `recognition/__init__.py`。TileClassifier 作为内部模块，通过引擎间接使用。直接导入路径：

```python
from majsoul_recognizer.recognition.tile_classifier import TileClassifier
```

## 文件

- 修改: `pyproject.toml`

## 验收

- `pip install -e ".[recognition-vit]"` 能安装 torch + transformers + Pillow
- `pip install -e ".[recognition-vit-cpu]" --extra-index-url https://download.pytorch.org/whl/cpu` 安装 CPU 版 torch
- `from majsoul_recognizer.recognition.tile_classifier import TileClassifier` 可用（安装后）
- `pip install -e .` （不附带可选依赖）不安装 torch/transformers，且已有测试全部通过
- `pip install -e ".[dev]"` 不安装 torch/transformers
