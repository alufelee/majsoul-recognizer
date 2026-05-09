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
