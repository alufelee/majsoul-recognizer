"""识别引擎统一入口"""

import logging
import time

import numpy as np

from majsoul_recognizer.recognition.config import RecognitionConfig
from majsoul_recognizer.recognition.pattern_matcher import PatternMatcher
from majsoul_recognizer.recognition.state_builder import GameStateBuilder, Validator
from majsoul_recognizer.recognition.text_recognizer import TextRecognizer
from majsoul_recognizer.types import BBox, Detection, GameState, ZoneName

logger = logging.getLogger(__name__)

# 检查 onnxruntime 是否可用
try:
    import onnxruntime  # noqa: F401
    _HAS_ORT = True
except ImportError:
    _HAS_ORT = False

# 检查 ultralytics 是否可用
try:
    from ultralytics import YOLO  # noqa: F401
    _HAS_ULTRALYTICS = True
except ImportError:
    _HAS_ULTRALYTICS = False


def _assign_detections_to_zones(
    detections: list[Detection],
    zone_rects: dict[str, tuple[int, int, int, int]],
) -> dict[str, list[Detection]]:
    """将全图检测结果按中心点分配到区域，保留全图坐标以保证排序一致性"""
    result: dict[str, list[Detection]] = {name: [] for name in zone_rects}
    for det in detections:
        cx = det.bbox.x + det.bbox.width // 2
        cy = det.bbox.y + det.bbox.height // 2
        for name, (zx, zy, zw, zh) in zone_rects.items():
            if zx <= cx <= zx + zw and zy <= cy <= zy + zh:
                result[name].append(det)
                break
    return result


class _StubDetector:
    """检测器不可用时的降级检测器"""

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
        self._classifier: "TileClassifier | None" = None
        self._classifier_attempted: bool = False
        self._builder = GameStateBuilder(self._config)
        self._validator = Validator(self._config)

    def _ensure_detector(self):
        if self._detector is None:
            # 优先使用 ultralytics 预训练模型（真实画面效果更好）
            pt_path = self._config.get_ultralytics_model_path()
            if pt_path is not None and _HAS_ULTRALYTICS:
                from majsoul_recognizer.recognition.ultralytics_detector import (
                    UltralyticsTileDetector,
                )
                self._detector = UltralyticsTileDetector(pt_path)
                logger.info("Using ultralytics detector: %s", pt_path)
            elif _HAS_ORT:
                from majsoul_recognizer.recognition.tile_detector import TileDetector
                model_path = self._config.get_model_path()
                self._detector = TileDetector(
                    str(model_path),
                    nms_iou=self._config.nms_iou_threshold,
                )
            else:
                logger.warning("No detector available, using stub")
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

    def _ensure_classifier(self):
        if self._classifier is not None:
            return self._classifier
        if not self._config.enable_vit_classifier:
            return None
        if self._classifier_attempted:
            return None
        self._classifier_attempted = True
        try:
            from majsoul_recognizer.recognition.tile_classifier import TileClassifier
            self._classifier = TileClassifier(self._config.vit_model_name)
            logger.info("ViT classifier loaded")
        except ImportError:
            logger.debug("ViT classifier unavailable (torch/transformers not installed)")
        except Exception as e:
            logger.warning("ViT classifier init failed: %s", e)
        return self._classifier

    def recognize(
        self,
        zones: dict[str, np.ndarray],
        full_image: np.ndarray | None = None,
        zone_rects: dict[str, tuple[int, int, int, int]] | None = None,
    ) -> GameState:
        """识别完整的游戏状态

        Args:
            zones: 区域名 -> 区域图像
            full_image: 完整游戏截图（可选，用于全图检测模式）
            zone_rects: 区域名 -> (x, y, w, h) 像素矩形（可选）
        """
        if not zones:
            return GameState(warnings=["empty_zones"])

        logger.info("Recognition started, %d zones received", len(zones))
        t_start = time.perf_counter()

        if not self._warmed_up:
            self.warmup()

        # 1. 牌面检测
        tile_zone_names = ["hand", "dora", "discards_self", "discards_right",
                           "discards_opposite", "discards_left", "calls_self"]

        confidence = self._config.detection_confidence
        detector = self._ensure_detector()

        scaled_rects: dict[str, tuple[int, int, int, int]] = {}

        # 优先全图检测模式：检测全图所有牌，再按位置分配到区域
        if full_image is not None and zone_rects is not None:
            tile_rects = {name: zone_rects[name] for name in tile_zone_names
                         if name in zone_rects}

            if hasattr(detector, "detect_full_image"):
                # Ultralytics 检测器的专用接口
                from majsoul_recognizer.recognition.ultralytics_detector import (
                    UltralyticsTileDetector,
                )
                assert isinstance(detector, UltralyticsTileDetector)
                img_h, img_w = full_image.shape[:2]
                scale_x = img_w / 1920.0
                scale_y = img_h / 1080.0
                for name, (x, y, w, h) in tile_rects.items():
                    scaled_rects[name] = (
                        int(x * scale_x), int(y * scale_y),
                        int(w * scale_x), int(h * scale_y),
                    )
                detections = detector.detect_full_image(full_image, scaled_rects, confidence)
            else:
                # ONNX 检测器：全图检测 → 按 zone_rect 分配
                all_dets = detector.detect(full_image, confidence)
                detections = _assign_detections_to_zones(all_dets, tile_rects)
                logger.info("Full-image detection: %d total, assigned to %d zones",
                            len(all_dets), sum(len(v) for v in detections.values()))
        else:
            tile_images = [(name, zones[name]) for name in tile_zone_names if name in zones]
            if self._config.enable_batch_detection and len(tile_images) > 1:
                detections = detector.detect_batch(tile_images, confidence)
            else:
                detections = {name: detector.detect(img, confidence) for name, img in tile_images}

        # ViT 二次分类
        _NON_TILE_CLASSES = {"back", "rotated", "dora_frame"}
        classifier = self._ensure_classifier()
        if classifier is not None and detections:
            for zone_name, dets in detections.items():
                if not dets:
                    continue
                # 分离牌面和非牌面检测，仅对牌面使用 ViT
                tile_indices = [i for i, d in enumerate(dets) if d.tile_code not in _NON_TILE_CLASSES]
                if not tile_indices:
                    continue
                if scaled_rects and zone_name in scaled_rects:
                    source = full_image
                    ox, oy = scaled_rects[zone_name][0], scaled_rects[zone_name][1]
                elif zone_name in zones:
                    source = zones[zone_name]
                    ox, oy = 0, 0
                else:
                    continue
                h_img, w_img = source.shape[:2]
                crops = [
                    source[
                        max(0, oy + dets[i].bbox.y):min(h_img, oy + dets[i].bbox.y + dets[i].bbox.height),
                        max(0, ox + dets[i].bbox.x):min(w_img, ox + dets[i].bbox.x + dets[i].bbox.width),
                    ]
                    for i in tile_indices
                ]
                vit_results = classifier.classify_batch(crops)
                for j, (tile_code, conf) in enumerate(vit_results):
                    if tile_code and conf >= self._config.vit_classifier_threshold:
                        orig_i = tile_indices[j]
                        dets[orig_i] = dets[orig_i].model_copy(update={
                            "tile_code": tile_code,
                            "confidence": conf,
                        })

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

        # 2.5: 将 calls_self 中不合理的检测结果合并到 hand
        # 当玩家没有副露时，手牌可能溢出到 calls_self 区域
        calls_dets = detections.get("calls_self", [])
        if calls_dets and "hand" in detections:
            tiles = [d.tile_code for d in calls_dets]
            suits = set()
            for t in tiles:
                if t[-1] in ("m", "p", "s"):
                    suits.add(t[-1])
            # chi 需要 3 张同花色连续牌, pon 需要 3 张相同
            n = len(tiles)
            valid_chi = n == 3 and len(suits) == 1 and len(set(tiles)) >= 2
            valid_pon = n == 3 and len(set(tiles)) == 1
            valid_kan = n == 4 and len(set(tiles)) == 1
            if not (valid_chi or valid_pon or valid_kan):
                logger.debug("Merging calls_self into hand: %s", tiles)
                detections["hand"] = list(detections["hand"]) + calls_dets
                detections["calls_self"] = []

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
                # 同步 prev_state 到修正后的 state
                self._validator.update_prev_state(state)

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
        self._classifier = None
        self._classifier_attempted = False
        self._validator.reset()
