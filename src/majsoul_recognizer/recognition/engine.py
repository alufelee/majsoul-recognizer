"""识别引擎统一入口"""

import logging
import time

import numpy as np

from majsoul_recognizer.recognition.config import RecognitionConfig
from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
from majsoul_recognizer.recognition.state_builder import GameStateBuilder, Validator
from majsoul_recognizer.recognition.text_recognizer import TextRecognizer
from majsoul_recognizer.types import Detection, GameState, ZoneName

logger = logging.getLogger(__name__)

# 检查 onnxruntime 是否可用
try:
    import onnxruntime  # noqa: F401
    _HAS_ORT = True
except ImportError:
    _HAS_ORT = False


class _StubDetector:
    """onnxruntime 不可用时的降级检测器"""

    def detect(self, image: np.ndarray, confidence: float = 0.7) -> list[Detection]:
        return []

    def detect_batch(
        self,
        images: list[tuple[str, np.ndarray]],
        confidence: float = 0.7,
    ) -> dict[str, list[Detection]]:
        if not images:
            return {}
        return {name: [] for name, _ in images}


class RecognitionEngine:
    """识别引擎统一入口"""

    def __init__(self, config: RecognitionConfig | None = None):
        self._config = config or RecognitionConfig()
        self._warmed_up = False

        # 延迟初始化重型资源
        self._detector: TileDetector | None = None
        self._ocr: TextRecognizer | None = None
        self._matcher: PatternMatcher | None = None
        self._builder = GameStateBuilder(self._config)
        self._validator = Validator(self._config)

    def _ensure_detector(self):
        if self._detector is None:
            if _HAS_ORT:
                from majsoul_recognizer.recognition.tile_detector import TileDetector
                model_path = self._config.get_model_path()
                self._detector = TileDetector(
                    str(model_path),
                    nms_iou=self._config.nms_iou_threshold,
                )
            else:
                logger.warning("onnxruntime not available, using stub detector")
                self._detector = _StubDetector()
        return self._detector

    def _ensure_ocr(self) -> TextRecognizer:
        if self._ocr is None:
            self._ocr = TextRecognizer(
                str(self._config.ocr_model_dir) if self._config.ocr_model_dir else None
            )
        return self._ocr

    def _ensure_matcher(self) -> PatternMatcher:
        if self._matcher is None:
            self._matcher = PatternMatcher(self._config.get_template_dir())
        return self._matcher

    def recognize(self, zones: dict[str, np.ndarray]) -> GameState:
        """识别完整的游戏状态"""
        if not zones:
            return GameState(warnings=["empty_zones"])

        logger.info("Recognition started, %d zones received", len(zones))
        t_start = time.perf_counter()

        if not self._warmed_up:
            self.warmup()

        # 1. 牌面检测
        tile_zone_names = ["hand", "dora", "discards_self", "discards_right",
                           "discards_opposite", "discards_left", "calls_self"]
        tile_images = [(name, zones[name]) for name in tile_zone_names if name in zones]

        confidence = self._config.detection_confidence
        detector = self._ensure_detector()

        if self._config.enable_batch_detection and len(tile_images) > 1:
            detections = detector.detect_batch(tile_images, confidence)
        else:
            detections = {name: detector.detect(img, confidence) for name, img in tile_images}

        # 设置 zone_name
        for zone_name_str, dets in detections.items():
            try:
                zn = ZoneName(zone_name_str)
            except ValueError:
                logger.warning("Unknown zone name: %s, skipping", zone_name_str)
                continue
            detections[zone_name_str] = [
                d.model_copy(update={"zone_name": zn}) for d in dets
            ]

        # 2. Detection 级帧间融合
        detections = self._validator.fuse_detections(detections)

        # 3. 文字识别
        ocr = self._ensure_ocr()
        scores: dict[str, int | None] = {}
        for prefix in ["score_self", "score_right", "score_opposite", "score_left"]:
            if prefix in zones and zones[prefix].size > 0:
                scores[prefix] = ocr.recognize_score(zones[prefix])

        round_info = None
        if "round_info" in zones and zones["round_info"].size > 0:
            round_info = ocr.recognize_round(zones["round_info"])

        timer = None
        if "timer" in zones and zones["timer"].size > 0:
            timer = ocr.recognize_timer(zones["timer"])

        # 4. 模板匹配
        actions = []
        if "actions" in zones and zones["actions"].size > 0:
            matcher = self._ensure_matcher()
            actions = matcher.match(zones["actions"])

        # 5. 组装 + 校验
        state = self._builder.build(
            detections, scores, round_info, timer, actions,
            prev_state=self._validator.prev_state,
        )
        state = self._validator.validate(state)

        # 分数异常沿用上一帧 (spec §12)
        if self._validator.prev_state is not None:
            prev = self._validator.prev_state
            updates: dict[str, int] = {}
            extra_warnings: list[str] = []
            for player, score in state.scores.items():
                if (score < self._config.score_min or score > self._config.score_max):
                    prev_score = prev.scores.get(player)
                    if prev_score is not None:
                        updates[player] = prev_score
                        extra_warnings.append(f"score_fallback: {player} using prev={prev_score}")
            if updates:
                state = state.model_copy(update={
                    "scores": {**state.scores, **updates},
                    "warnings": state.warnings + extra_warnings,
                })

        elapsed = (time.perf_counter() - t_start) * 1000
        logger.info("Recognition done: hand=%d, warnings=%d, %.1fms",
                    len(state.hand), len(state.warnings), elapsed)
        return state

    def warmup(self) -> None:
        """预热引擎"""
        if self._warmed_up:
            return
        try:
            detector = self._ensure_detector()
            dummy = np.zeros((100, 100, 3), dtype=np.uint8)
            detector.detect(dummy, confidence=0.99)
            self._warmed_up = True
            logger.info("Engine warmup complete")
        except Exception as e:
            logger.warning("Warmup failed: %s", e)
            self._warmed_up = True  # 避免反复尝试

    def reset(self):
        """重置引擎状态"""
        self._validator.reset()

    def __enter__(self) -> "RecognitionEngine":
        return self

    def __exit__(self, *args) -> None:
        self._detector = None
        self._ocr = None
        self._matcher = None
        self._validator.reset()
