from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .config import EvaluationConfig
from .dungeon import Dungeon


@dataclass
class DungeonMetrics:
    room_diversity: float
    branching_factor: float
    loot_presence: float
    monster_presence: float
    dead_end_ratio: float
    room_count: float
    raw_room_count: int


def _compute_metrics(dungeon: Dungeon, evaluation: EvaluationConfig) -> DungeonMetrics:
    rooms = dungeon.rooms
    total_rooms = max(len(rooms), 1)
    unique_symbols = {room.symbol for room in rooms.values()}
    room_diversity = len(unique_symbols) / total_rooms

    adjacency = dungeon.adjacency
    branching_rooms = 0
    dead_ends = 0
    loot_rooms = 0
    monster_rooms = 0

    for room_id, room in rooms.items():
        degree = len(adjacency.get(room_id, ()))
        if room_id != 0 and degree <= 1:
            dead_ends += 1
        if degree >= 3:
            branching_rooms += 1
        if room.items:
            loot_rooms += 1
        if room.monsters:
            monster_rooms += 1

    branching_factor = branching_rooms / total_rooms
    loot_presence = loot_rooms / total_rooms
    monster_presence = monster_rooms / total_rooms
    dead_end_ratio = dead_ends / total_rooms
    room_count_score = min(total_rooms, evaluation.target_room_count) / evaluation.target_room_count

    return DungeonMetrics(
        room_diversity=room_diversity,
        branching_factor=branching_factor,
        loot_presence=loot_presence,
        monster_presence=monster_presence,
        dead_end_ratio=dead_end_ratio,
        room_count=room_count_score,
        raw_room_count=total_rooms,
    )


def score_dungeon(dungeon: Dungeon, evaluation: EvaluationConfig) -> tuple[float, DungeonMetrics]:
    metrics = _compute_metrics(dungeon, evaluation)
    weights = evaluation.weights

    score = 0.0
    score += weights.get("room_diversity", 0.0) * metrics.room_diversity
    score += weights.get("branching_factor", 0.0) * metrics.branching_factor
    score += weights.get("loot_presence", 0.0) * metrics.loot_presence
    score += weights.get("monster_presence", 0.0) * metrics.monster_presence
    score += weights.get("dead_end_penalty", 0.0) * metrics.dead_end_ratio
    score += weights.get("room_count", 0.0) * metrics.room_count

    return score, metrics
