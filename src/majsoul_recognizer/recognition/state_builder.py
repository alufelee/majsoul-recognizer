"""游戏状态构建与规则校验"""

import logging
from statistics import median

from majsoul_recognizer.recognition.config import RecognitionConfig
from majsoul_recognizer.recognition.tile_detector import _resolve_rotated_tiles
from majsoul_recognizer.types import (
    ActionMatch, BBox, CallGroup, Detection, GameState, RoundInfo,
)

logger = logging.getLogger(__name__)

# 辅助类别集合
_AUXILIARY_CODES = frozenset(["back", "rotated", "dora_frame"])

# 赤宝牌合并映射
_RED_DORA_MERGE = {"5mr": "5m", "5pr": "5p", "5sr": "5s"}

# rotated_index → from_player 映射 (spec §8.2)
_ROTATED_INDEX_TO_PLAYER = {
    (0, "chi"): "right",
    (1, "chi"): "opposite",
    (2, "chi"): "left",
    (0, "pon"): "right",
    (1, "pon"): "opposite",
    (2, "pon"): "left",
    (0, "kan"): "right",
    (1, "kan"): "opposite",
    (2, "kan"): "left",
    (3, "kan"): "left",
}

# zone_name 前缀 → GameState 字典键
_ZONE_KEY_MAP = {
    "score_self": "self", "score_right": "right",
    "score_opposite": "opposite", "score_left": "left",
    "discards_self": "self", "discards_right": "right",
    "discards_opposite": "opposite", "discards_left": "left",
    "calls_self": "self",
}


def _median_value(dets: list[Detection], attr: str) -> float:
    """计算检测框某属性的中位值"""
    values = sorted(getattr(d.bbox, attr) for d in dets)
    return values[len(values) // 2] if values else 0


def _sort_horizontal_grid(dets: list[Detection]) -> list[Detection]:
    """水平网格排序（自家/对家牌河）"""
    if len(dets) <= 1:
        return dets
    median_h = _median_value(dets, "height")
    threshold = median_h * 0.5

    sorted_by_y = sorted(dets, key=lambda d: d.bbox.y)
    rows: list[list[Detection]] = []
    current_row = [sorted_by_y[0]]
    for d in sorted_by_y[1:]:
        if abs(d.bbox.y - current_row[0].bbox.y) < threshold:
            current_row.append(d)
        else:
            rows.append(sorted(current_row, key=lambda d: d.bbox.x))
            current_row = [d]
    rows.append(sorted(current_row, key=lambda d: d.bbox.x))
    return [d for row in rows for d in row]


def _sort_vertical_grid(dets: list[Detection], ascending_x: bool) -> list[Detection]:
    """垂直网格排序（左/右家牌河）"""
    if len(dets) <= 1:
        return dets
    median_w = _median_value(dets, "width")
    threshold = median_w * 0.5

    sorted_by_x = sorted(dets, key=lambda d: d.bbox.x, reverse=not ascending_x)
    cols: list[list[Detection]] = []
    current_col = [sorted_by_x[0]]
    for d in sorted_by_x[1:]:
        if abs(d.bbox.x - current_col[0].bbox.x) < threshold:
            current_col.append(d)
        else:
            cols.append(sorted(current_col, key=lambda d: d.bbox.y))
            current_col = [d]
    cols.append(sorted(current_col, key=lambda d: d.bbox.y))
    return [d for col in cols for d in col]


def _sort_discards(detections: list[Detection], zone_name: str) -> list[Detection]:
    """对牌河检测结果排序"""
    if not detections:
        return []
    if zone_name in ("discards_self", "discards_opposite"):
        return _sort_horizontal_grid(detections)
    elif zone_name == "discards_right":
        return _sort_vertical_grid(detections, ascending_x=True)
    else:  # discards_left
        return _sort_vertical_grid(detections, ascending_x=False)


class GameStateBuilder:
    """将子模块原始结果组装为 GameState"""

    def __init__(self, config: RecognitionConfig):
        self._config = config

    def _zone_key(self, zone_name: str) -> str:
        return _ZONE_KEY_MAP.get(zone_name, zone_name)

    def build(
        self,
        detections: dict[str, list[Detection]],
        scores: dict[str, int | None],
        round_info: RoundInfo | None,
        timer: int | None,
        actions: list[ActionMatch],
        prev_state: GameState | None = None,
    ) -> GameState:
        hand, drawn_tile = self._build_hand(detections.get("hand", []), prev_state)
        dora_indicators = self._build_dora(detections.get("dora", []))
        state_scores = self._build_scores(scores)
        discards = self._build_discards(detections)
        calls, call_warnings = self._build_calls(detections.get("calls_self", []), prev_state)
        state_actions = [a.name for a in actions]

        return GameState(
            round_info=round_info,
            dora_indicators=dora_indicators,
            scores=state_scores,
            hand=hand,
            drawn_tile=drawn_tile,
            calls=calls,
            discards=discards,
            actions=state_actions,
            timer_remaining=timer,
            warnings=call_warnings,
        )

    def _build_hand(self, dets: list[Detection], prev_state: GameState | None = None) -> tuple[list[str], str | None]:
        """构建手牌，返回 (hand_list, drawn_tile)"""
        valid = [d for d in dets if d.tile_code not in _AUXILIARY_CODES]
        if not valid:
            return [], None

        sorted_dets = sorted(valid, key=lambda d: d.bbox.x)

        if len(sorted_dets) <= 1:
            codes = [d.tile_code for d in sorted_dets]
            return codes, None

        # 计算间距
        gaps = []
        for i in range(len(sorted_dets) - 1):
            gap = sorted_dets[i + 1].bbox.x - (sorted_dets[i].bbox.x + sorted_dets[i].bbox.width)
            gaps.append(gap)

        if not gaps:
            return [d.tile_code for d in sorted_dets], None

        median_gap = float(median(gaps))
        threshold = median_gap * self._config.drawn_tile_gap_multiplier

        # 查找第一个大间距
        drawn_tile_idx = -1
        for i in range(len(gaps)):
            if gaps[i] > threshold:
                drawn_tile_idx = i + 1
                break

        if drawn_tile_idx >= 0:
            hand_codes = [d.tile_code for d in sorted_dets[:drawn_tile_idx]]
            hand_codes.extend(d.tile_code for d in sorted_dets[drawn_tile_idx + 1:])
            drawn_tile = sorted_dets[drawn_tile_idx].tile_code
            return hand_codes, drawn_tile

        # 无大间距: 14 张时最后一张为 drawn_tile
        if len(sorted_dets) == 14:
            return [d.tile_code for d in sorted_dets[:-1]], sorted_dets[-1].tile_code

        # 13 张无间距: 根据 prev_state 判断
        if len(sorted_dets) == 13 and prev_state is not None:
            prev_hand_len = len(prev_state.hand)
            if prev_hand_len == 13 and prev_state.drawn_tile is None:
                # 上一帧也在等摸牌，当前帧正常 13 张
                return [d.tile_code for d in sorted_dets], None
            elif prev_hand_len == 12 or (prev_hand_len == 13 and prev_state.drawn_tile is not None):
                # 上一帧 12 张 或 上一帧 13+drawn（摸牌后丢弃一张），
                # 当前帧应有 drawn_tile 但无法定位
                return [d.tile_code for d in sorted_dets], None
                # 注意: 此处应添加 warning，但 _build_hand 无法直接添加。
                # drawn_tile 不可定位的情况由 Validator 的 hand_count 校验覆盖。

        return [d.tile_code for d in sorted_dets], None

    def _build_dora(self, dets: list[Detection]) -> list[str]:
        """构建宝牌指示器"""
        return [d.tile_code for d in sorted(dets, key=lambda d: d.bbox.x)
                if d.tile_code not in _AUXILIARY_CODES]

    def _build_scores(self, scores: dict[str, int | None]) -> dict[str, int]:
        """构建分数"""
        result = {}
        for zone_name, score in scores.items():
            if score is not None:
                key = self._zone_key(zone_name)
                result[key] = score
        return result

    def _build_discards(self, detections: dict[str, list[Detection]]) -> dict[str, list[str]]:
        """构建牌河"""
        result = {}
        discard_zones = ["discards_self", "discards_right", "discards_opposite", "discards_left"]
        for zone_name in discard_zones:
            if zone_name not in detections:
                continue
            dets = [d for d in detections[zone_name] if d.tile_code not in _AUXILIARY_CODES]
            sorted_dets = _sort_discards(dets, zone_name)
            key = self._zone_key(zone_name)
            result[key] = [d.tile_code for d in sorted_dets]
        return result

    def _build_calls(self, dets: list[Detection], prev_state: GameState | None) -> tuple[dict[str, list[CallGroup]], list[str]]:
        """构建副露 (spec §8.2)，返回 (calls_dict, warnings)"""
        if not dets:
            return {}, []

        sorted_all = sorted(dets, key=lambda d: d.bbox.x)
        filtered = [d for d in sorted_all if d.tile_code != "dora_frame"]
        if not filtered:
            return {}, []

        rotated_map = _resolve_rotated_tiles(filtered)

        normals = [d for d in filtered if d.tile_code not in ("back", "rotated")]
        if not normals:
            return {}, []
        if len(normals) <= 1:
            return {}, []

        gaps = []
        for i in range(len(normals) - 1):
            gap = normals[i + 1].bbox.x - (normals[i].bbox.x + normals[i].bbox.width)
            gaps.append(gap)

        median_gap = float(median(gaps)) if gaps else 0
        threshold = median_gap * self._config.call_group_gap_multiplier

        groups: list[list[Detection]] = []
        current_group = [normals[0]]
        for i in range(len(gaps)):
            if gaps[i] > threshold:
                groups.append(current_group)
                current_group = [normals[i + 1]]
            else:
                current_group.append(normals[i + 1])
        groups.append(current_group)

        # Build call groups
        calls: list[CallGroup] = []
        call_warnings: list[str] = []
        for gi, group in enumerate(groups):
            tiles = [d.tile_code for d in group]
            n = len(tiles)

            # Check rotated_map for this group
            rotated_idx_in_group: int | None = None
            for pi, det in enumerate(group):
                # 在 filtered 中找到此 detection 的索引，然后查找 rotated_map
                for fi, fd in enumerate(filtered):
                    if fd is det and fi in rotated_map and rotated_map[fi] is not None:
                        rotated_idx_in_group = pi
                        break
                if rotated_idx_in_group is not None:
                    break

            # Check for ankan: 统计当前 group x 范围内的 back 数量
            group_x_min = min(d.bbox.x for d in group)
            group_x_max = max(d.bbox.x + d.bbox.width for d in group)
            back_count = sum(
                1 for d in filtered
                if d.tile_code == "back" and d.bbox.x >= group_x_min - 5 and d.bbox.x <= group_x_max + 5
            )

            if n == 4 and back_count >= 2:
                call = CallGroup(type="ankan", tiles=tiles, rotated_index=None, from_player=None)
                calls.append(call)
            elif n == 4:
                call, kan_warnings = self._infer_kan_call(tiles, rotated_idx_in_group, prev_state)
                if call:
                    calls.append(call)
                call_warnings.extend(kan_warnings)
            elif n == 3:
                call_type = "pon" if len(set(tiles)) == 1 else "chi"
                from_player = _ROTATED_INDEX_TO_PLAYER.get(
                    (rotated_idx_in_group, call_type)
                ) if rotated_idx_in_group is not None else None
                call = CallGroup(
                    type=call_type, tiles=tiles,
                    rotated_index=rotated_idx_in_group,
                    from_player=from_player,
                )
                calls.append(call)

        if calls:
            return {"self": calls}, call_warnings
        return {}, call_warnings

    def _infer_kan_call(
        self, tiles: list[str], rotated_index: int | None,
        prev_state: GameState | None,
    ) -> tuple[CallGroup | None, list[str]]:
        """推断 4 张牌的杠类型 (kan/kakan)，返回 (call, warnings)"""
        warnings: list[str] = []

        if prev_state is not None:
            for prev_call in prev_state.calls.get("self", []):
                if prev_call.type == "pon":
                    prev_normalized = {_RED_DORA_MERGE.get(t, t) for t in prev_call.tiles}
                    curr_normalized = {_RED_DORA_MERGE.get(t, t) for t in tiles}
                    if prev_normalized == curr_normalized:
                        return CallGroup(
                            type="kakan", tiles=tiles,
                            rotated_index=rotated_index,
                            from_player=prev_call.from_player,
                        ), []

        # 无 prev_state 匹配: 默认 kan，但如果有 rotated 可能是 kakan
        if rotated_index is not None and len(set(_RED_DORA_MERGE.get(t, t) for t in tiles)) == 1:
            # 4 张相同牌 + rotated，可能是 kakan 但无法确认
            warnings.append("kakan_unknown_source: no prev_state match, treating as kan")

        from_player = _ROTATED_INDEX_TO_PLAYER.get(
            (rotated_index, "kan")
        ) if rotated_index is not None else None
        return CallGroup(
            type="kan", tiles=tiles,
            rotated_index=rotated_index,
            from_player=from_player,
        ), warnings


class Validator:
    """规则校验与 Detection 级帧间融合"""

    def __init__(self, config: RecognitionConfig):
        self._config = config
        self._prev_state: GameState | None = None
        self._detection_window: list[dict[str, list[Detection]]] = []
        self._empty_frame_count: int = 0

    @property
    def prev_state(self) -> GameState | None:
        return self._prev_state

    def validate(self, state: GameState) -> GameState:
        """校验当前状态，返回带 warnings 的新实例"""
        warnings: list[str] = list(state.warnings)

        # 规则 1: 手牌数量
        kan_count = sum(
            1 for group in state.calls.values()
            for c in group if c.type in ("kan", "ankan", "kakan")
        )
        expected = 13 - kan_count
        actual = len(state.hand)
        if actual != expected:
            warnings.append(f"hand_count_mismatch: got {actual}, expected {expected}")

        # 规则 2: 牌数上限
        tile_counter: dict[str, int] = {}
        all_tiles = list(state.hand)
        if state.drawn_tile:
            all_tiles.append(state.drawn_tile)
        for group_list in state.calls.values():
            for call in group_list:
                all_tiles.extend(call.tiles)
        for zone_tiles in state.discards.values():
            all_tiles.extend(zone_tiles)
        all_tiles.extend(state.dora_indicators)

        for tile in all_tiles:
            key = _RED_DORA_MERGE.get(tile, tile)
            tile_counter[key] = tile_counter.get(key, 0) + 1
        for tile, count in tile_counter.items():
            if count > 4:
                warnings.append(f"tile_overflow: {tile} appears {count} times")

        # 规则 3: 牌河连续性
        if self._prev_state is not None:
            for player in ["self", "right", "opposite", "left"]:
                prev_len = len(self._prev_state.discards.get(player, []))
                curr_len = len(state.discards.get(player, []))
                diff = curr_len - prev_len
                if diff < 0 or diff > 1:
                    warnings.append(f"discard_jump: {player} diff={diff}")

        # 规则 4: 分数合理性
        for player, score in state.scores.items():
            if score < self._config.score_min or score > self._config.score_max:
                warnings.append(f"score_anomaly: {player}={score}")

        # 规则 5: 连续无检测结果 (spec §12)
        if self._empty_frame_count >= 5:
            warnings.append("no_detection_5_frames")

        self._prev_state = state
        return state.model_copy(update={"warnings": warnings})

    def fuse_detections(self, current: dict[str, list[Detection]]) -> dict[str, list[Detection]]:
        """Detection 级帧间融合"""
        self._detection_window.append(current)
        # 更新连续空检测计数
        total_dets = sum(len(d) for d in current.values())
        if total_dets == 0:
            self._empty_frame_count += 1
        else:
            self._empty_frame_count = 0
        window_size = self._config.fusion_window_size
        if len(self._detection_window) > window_size:
            self._detection_window = self._detection_window[-window_size:]

        if len(self._detection_window) == 1:
            return current

        result: dict[str, list[Detection]] = {}
        for zone_name, dets in current.items():
            fused: list[Detection] = []
            for det in dets:
                cx, cy = det.bbox.center
                votes: dict[str, list[float]] = {}

                for frame in self._detection_window:
                    for hist_det in frame.get(zone_name, []):
                        hcx, hcy = hist_det.bbox.center
                        dist = ((cx - hcx) ** 2 + (cy - hcy) ** 2) ** 0.5
                        median_w = _median_value(dets, "width")
                        if dist < median_w * 0.5:
                            votes.setdefault(hist_det.tile_code, []).append(hist_det.confidence)

                if votes:
                    # 多数投票
                    best_code = max(votes.keys(), key=lambda k: len(votes[k]))
                    avg_conf = sum(votes[best_code]) / len(votes[best_code])
                    # 不一致时降低置信度
                    if len(votes) > 1:
                        total_votes = sum(len(v) for v in votes.values())
                        if len(votes[best_code]) < total_votes:
                            avg_conf *= 0.8
                    fused.append(det.model_copy(update={
                        "tile_code": best_code,
                        "confidence": round(avg_conf, 4),
                    }))
                else:
                    fused.append(det)
            result[zone_name] = fused
        return result

    def reset(self):
        """重置历史状态"""
        self._prev_state = None
        self._detection_window = []
        self._empty_frame_count = 0
