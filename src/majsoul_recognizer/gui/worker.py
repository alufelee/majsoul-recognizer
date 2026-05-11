"""识别工作线程

在独立线程中串行处理图像识别任务。
支持丢弃旧帧、引擎热更新、错误捕获。
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field

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
    detections: list = field(default_factory=list)
    error: str | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


class _RecognizeWorker:
    """单工作线程识别器

    串行处理提交的图像，处理中丢弃新提交（skip-latest 策略）。
    通过 result_queue（maxsize=1）传递结果，旧结果自动丢弃。
    """

    def __init__(self, engine: RecognitionEngine | None, pipeline: CapturePipeline) -> None:
        self._engine_ref = engine
        self._pipeline_ref = pipeline
        self._task: np.ndarray | None = None
        self._result_queue: queue.Queue[_WorkerResult] = queue.Queue(maxsize=1)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update_engine(self, engine: RecognitionEngine | None) -> None:
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
                state = engine.recognize(frame.zones) if (engine and frame.is_static) else None
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
