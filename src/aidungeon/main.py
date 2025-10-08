from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .dungeon import DungeonBuilder
from .lsystem import LSystem
from .narrative import NarrativeGenerator


def _render_ascii(dungeon) -> str:
    positions = {room.position for room in dungeon.rooms.values()}
    min_x = min(x for x, _ in positions)
    max_x = max(x for x, _ in positions)
    min_y = min(y for _, y in positions)
    max_y = max(y for _, y in positions)
    width = max_x - min_x + 1
    height = max_y - min_y + 1
    grid = [["." for _ in range(width)] for _ in range(height)]
    for room in dungeon.rooms.values():
        x, y = room.position
        grid[max_y - y][x - min_x] = "S" if room.symbol == "S" else room.symbol
    lines = [" ".join(row) for row in grid]
    return "\n".join(lines)


def build_dungeon(config_path: Path, iterations_override: int | None = None):
    config = load_config(config_path)
    iterations = iterations_override if iterations_override is not None else config.dungeon.iterations
    lsystem = LSystem(config.dungeon.axiom, config.dungeon.rules)
    expanded = lsystem.expand(iterations)
    builder = DungeonBuilder()
    dungeon = builder.build(expanded, config.dungeon.symbols)
    narrator = NarrativeGenerator(config.ollama, config.narrative)
    dungeon = narrator.annotate(dungeon)
    return dungeon


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an L-system dungeon and narrate it with Ollama.")
    parser.add_argument("--config", type=Path, default=Path("config/default_config.toml"), help="Path to config file.")
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Override the number of L-system iterations from the config.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "ascii"),
        default="json",
        help="Choose the output format.",
    )
    args = parser.parse_args(argv)

    dungeon = build_dungeon(args.config, args.iterations)
    if args.format == "json":
        print(json.dumps(dungeon.to_dict(), indent=2))
    else:
        print(_render_ascii(dungeon))
        for room in sorted(dungeon.rooms.values(), key=lambda r: r.id):
            if room.symbol == "S":
                continue
            print(f"\nRoom {room.id} ({room.label})")
            print(room.description or "<no description>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
