"""识别工作线程测试

[S2 修复] 使用 _poll_result 替代脆弱的 time.sleep 同步。
[M3 修复] _make_frame_result 使用参数化时间戳。
"""

import time
from unittest.mock import MagicMock

import numpy as np

from majsoul_recognizer.gui.worker import _RecognizeWorker, _WorkerResult
from majsoul_recognizer.types import FrameResult


def _make_image(h=100, w=100):
    return np.zeros((h, w, 3), dtype=np.uint8)


def _make_frame_result(is_static=True, frame_id=1, timestamp="2026-05-09T00:00:00Z"):
    """[M3] 参数化 timestamp 和 frame_id"""
    return FrameResult(
        frame_id=frame_id,
        timestamp=timestamp,
        zones={"hand": _make_image()} if is_static else {},
        is_static=is_static,
    )


def _poll_result(worker, timeout=2.0, interval=0.01):
    """[S2] 轮询等待结果，替代脆弱的 time.sleep"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = worker.get_result()
        if result is not None:
            return result
        time.sleep(interval)
    raise TimeoutError(f"Worker did not produce result within {timeout}s")


class TestWorkerResult:
    def test_normal_result(self):
        r = _WorkerResult(image=_make_image(), frame=_make_frame_result(), state=None)
        assert not r.is_error
        assert r.image is not None
        assert r.frame is not None

    def test_error_result(self):
        r = _WorkerResult(error="boom")
        assert r.is_error
        assert r.error == "boom"
        assert r.image is None


class TestRecognizeWorker:
    def _make_worker(self, process_returns=None, recognize_returns=None):
        """创建 Worker，mock pipeline 和 engine"""
        pipeline = MagicMock()
        engine = MagicMock()

        if process_returns is not None:
            pipeline.process_image.return_value = process_returns
        else:
            pipeline.process_image.return_value = _make_frame_result()

        if recognize_returns is not None:
            engine.recognize.return_value = recognize_returns

        worker = _RecognizeWorker(engine, pipeline)
        return worker, engine, pipeline

    def test_submit_and_get_result(self):
        frame = _make_frame_result(is_static=True)
        state = MagicMock()
        worker, engine, _ = self._make_worker(process_returns=frame, recognize_returns=state)

        image = _make_image()
        assert worker.submit(image) is True

        result = _poll_result(worker)
        assert not result.is_error
        assert result.frame is frame
        assert result.state is state

        worker.stop()

    def test_submit_drops_when_busy(self):
        """上一帧未处理完时丢弃新提交"""
        def slow_process(img):
            time.sleep(1.0)
            return _make_frame_result()

        worker, _, pipeline = self._make_worker()
        pipeline.process_image.side_effect = slow_process

        image1 = _make_image()
        assert worker.submit(image1) is True

        # 立即提交第二帧，应被丢弃
        image2 = _make_image()
        assert worker.submit(image2) is False

        worker.stop()

    def test_non_static_frame_skips_recognition(self):
        """非静态帧跳过 engine.recognize"""
        frame = _make_frame_result(is_static=False)
        worker, engine, pipeline = self._make_worker(process_returns=frame)

        worker.submit(_make_image())
        result = _poll_result(worker)

        assert result.state is None  # 非静态帧不识别
        engine.recognize.assert_not_called()

        worker.stop()

    def test_exception_becomes_error_result(self):
        """pipeline 异常转为 error 结果"""
        worker, _, pipeline = self._make_worker()
        pipeline.process_image.side_effect = RuntimeError("model not found")

        worker.submit(_make_image())
        result = _poll_result(worker)

        assert result.is_error
        assert "model not found" in result.error

        worker.stop()

    def test_stop_terminates_thread(self):
        worker, _, _ = self._make_worker()
        assert worker._thread.is_alive()
        worker.stop()
        assert not worker._thread.is_alive()

    def test_get_result_empty_when_nothing_submitted(self):
        worker, _, _ = self._make_worker()
        result = worker.get_result()
        assert result is None
        worker.stop()

    def test_update_engine(self):
        """引擎引用可被更新"""
        worker, old_engine, _ = self._make_worker()
        new_engine = MagicMock()
        worker.update_engine(new_engine)
        # 引用已更新（内部 _engine_ref 指向 new_engine）
        assert worker._engine_ref is new_engine
        worker.stop()

    def test_engine_none_does_not_crash(self):
        """[C2] engine=None 降级模式不崩溃，state 返回 None"""
        pipeline = MagicMock()
        pipeline.process_image.return_value = _make_frame_result(is_static=True)
        worker = _RecognizeWorker(None, pipeline)

        worker.submit(_make_image())
        result = _poll_result(worker)

        assert not result.is_error
        assert result.state is None  # engine 为 None，跳过识别
        worker.stop()

    def test_engine_none_update_to_valid(self):
        """[C2] engine=None 可热更新为有效引擎"""
        pipeline = MagicMock()
        pipeline.process_image.return_value = _make_frame_result(is_static=True)
        worker = _RecognizeWorker(None, pipeline)

        state = MagicMock()
        new_engine = MagicMock()
        new_engine.recognize.return_value = state
        worker.update_engine(new_engine)

        worker.submit(_make_image())
        result = _poll_result(worker)

        assert result.state is state
        worker.stop()

    def test_engine_none_non_static_frame(self):
        """[LOW] engine=None + 非静态帧：state 应为 None"""
        pipeline = MagicMock()
        pipeline.process_image.return_value = _make_frame_result(is_static=False)
        worker = _RecognizeWorker(None, pipeline)

        worker.submit(_make_image())
        result = _poll_result(worker)

        assert not result.is_error
        assert result.state is None
        worker.stop()
