from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from .config import SymbolConfig

Vec2 = Tuple[int, int]


@dataclass
class Room:
    id: int
    symbol: str
    label: str
    tags: Sequence[str]
    position: Vec2
    trail: Sequence[str]
    description: str = ""


@dataclass
class Dungeon:
    rooms: Mapping[int, Room]
    adjacency: Mapping[int, Sequence[int]]

    def to_dict(self) -> Dict[str, object]:
        return {
            "rooms": {
                room_id: {
                    "symbol": room.symbol,
                    "label": room.label,
                    "tags": list(room.tags),
                    "position": list(room.position),
                    "trail": list(room.trail),
                    "description": room.description,
                }
                for room_id, room in self.rooms.items()
            },
            "adjacency": {room_id: list(neighbors) for room_id, neighbors in self.adjacency.items()},
        }


class DungeonBuilder:
    _DIRECTIONS: List[Vec2] = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    _DIRECTION_NAMES: List[str] = ["north", "east", "south", "west"]

    def build(self, grammar: str, symbols: Mapping[str, SymbolConfig]) -> Dungeon:
        rooms: Dict[int, Room] = {}
        neighbors: Dict[int, List[int]] = {}
        rooms_by_position: Dict[Vec2, int] = {}
        trails: Dict[int, List[str]] = {}

        def ensure_room(room_id: int) -> None:
            neighbors.setdefault(room_id, [])

        start_room = Room(
            id=0,
            symbol="S",
            label="Entry point",
            tags=(),
            position=(0, 0),
            trail=[],
            description="",
        )
        rooms[start_room.id] = start_room
        trails[start_room.id] = []
        rooms_by_position[start_room.position] = start_room.id
        ensure_room(start_room.id)

        current_id = start_room.id
        current_position: Vec2 = start_room.position
        direction_idx = 0
        stack: List[Tuple[int, Vec2, int]] = []
        next_room_id = 1

        for symbol in grammar:
            if symbol in symbols:
                delta = self._DIRECTIONS[direction_idx]
                next_position = (current_position[0] + delta[0], current_position[1] + delta[1])
                existing_id = rooms_by_position.get(next_position)
                if existing_id is None:
                    symbol_cfg = symbols[symbol]
                    room_id = next_room_id
                    next_room_id += 1
                    trail = trails[current_id] + [self._DIRECTION_NAMES[direction_idx]]
                    room = Room(
                        id=room_id,
                        symbol=symbol,
                        label=symbol_cfg.label,
                        tags=symbol_cfg.tags,
                        position=next_position,
                        trail=trail,
                        description="",
                    )
                    rooms[room_id] = room
                    trails[room_id] = trail
                    rooms_by_position[next_position] = room_id
                    ensure_room(room_id)
                else:
                    room_id = existing_id
                if room_id not in neighbors[current_id]:
                    neighbors[current_id].append(room_id)
                if room_id not in neighbors:
                    neighbors[room_id] = []
                if current_id not in neighbors[room_id]:
                    neighbors[room_id].append(current_id)
                current_id = room_id
                current_position = next_position
            elif symbol == "+":
                direction_idx = (direction_idx + 1) % len(self._DIRECTIONS)
            elif symbol == "-":
                direction_idx = (direction_idx - 1) % len(self._DIRECTIONS)
            elif symbol == "[":
                stack.append((current_id, current_position, direction_idx))
            elif symbol == "]" and stack:
                state = stack.pop()
                current_id, current_position, direction_idx = state
            else:
                continue

        return Dungeon(rooms=rooms, adjacency={k: tuple(v) for k, v in neighbors.items()})
