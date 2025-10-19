from __future__ import annotations
from aidungeon.markov_names import MarkovNameGenerator, MINECRAFT_MONSTERS

import argparse
import json
import random
from pathlib import Path

from .config import load_config
from .content import ContentGenerator
from .dungeon import DungeonBuilder
from .evaluation import score_dungeon
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


def _generate_candidate(config, iterations_override: int | None, seed: int, describe: bool = True):
    iterations = iterations_override if iterations_override is not None else config.dungeon.iterations
    lsystem = LSystem(config.dungeon.axiom, config.dungeon.rules, seed=seed)
    expanded = lsystem.expand(iterations)

    builder = DungeonBuilder()
    dungeon = builder.build(expanded, config.dungeon.symbols)

    content_generator = ContentGenerator(
        config.content, config.ollama, config.narrative, base_seed=seed, enable_descriptions=describe,
    )
    dungeon = content_generator.enrich(dungeon)
    return dungeon


def _select_best_dungeon(config, iterations_override: int | None, candidate_count: int, rng: random.Random):
    best_dungeon = None
    best_score = float("-inf")
    best_metrics = None
    best_seed = None

    for _ in range(max(candidate_count, 1)):
        seed = rng.getrandbits(32)
        candidate = _generate_candidate(config, iterations_override, seed, describe=False)
        score, metrics = score_dungeon(candidate, config.evaluation)
        if score > best_score:
            best_score = score
            best_dungeon = candidate
            best_metrics = metrics
            best_seed = seed

    if best_dungeon is None:
        raise RuntimeError("Failed to generate any dungeon candidates.")
    return best_dungeon, best_seed, best_score, best_metrics

def _apply_markov_names(config):
    """Подменяет имена монстров на сгенерированные через цепи Маркова."""
    gen = MarkovNameGenerator(MINECRAFT_MONSTERS, n=3)
    new_symbols = {}
    for key, sym in config.content.monsters.symbols.items():
        random_name = gen.generate()
        new_symbols[key] = type(sym)(label=random_name, tags=sym.tags)
    config.content.monsters.symbols = new_symbols


def build_dungeon(
    config_path: Path,
    iterations_override: int | None = None,
    candidate_count: int | None = None,
):
    config = load_config(config_path)
    _apply_markov_names(config)
    effective_candidates = candidate_count if candidate_count is not None else config.evaluation.candidate_count

    rng = random.Random()
    _, best_seed, _, _ = _select_best_dungeon(config, iterations_override, effective_candidates, rng)
    described = _generate_candidate(config, iterations_override, best_seed, describe=True)

    narrator = NarrativeGenerator(config.ollama, config.narrative)
    return narrator.annotate(described)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an L-system dungeon and narrate it with Ollama.")
    parser.add_argument("--config", type=Path, default=Path("config/default_config.toml"),
                        help="Path to config file.")
    parser.add_argument("--iterations", type=int, default=None,
                        help="Override the number of L-system iterations from the config.")
    parser.add_argument("--format", choices=("json", "ascii"), default="json",
                        help="Choose the output format.")
    parser.add_argument("--candidates", type=int, default=None,
                        help="Number of dungeon candidates to sample before picking the best.")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    candidate_count = args.candidates if args.candidates is not None else config.evaluation.candidate_count

    rng = random.Random()
    _, best_seed, best_score, best_metrics = _select_best_dungeon(
        config, args.iterations, candidate_count, rng
    )
    best_dungeon = _generate_candidate(config, args.iterations, best_seed, describe=True)

    narrator = NarrativeGenerator(config.ollama, config.narrative)
    dungeon = narrator.annotate(best_dungeon)

    if args.format == "json":
        payload = dungeon.to_dict()
        if best_metrics is not None:
            payload.setdefault("evaluation", {})
            payload["evaluation"].update(
                {
                    "score": best_score,
                    "room_diversity": best_metrics.room_diversity,
                    "branching_factor": best_metrics.branching_factor,
                    "loot_presence": best_metrics.loot_presence,
                    "monster_presence": best_metrics.monster_presence,
                    "dead_end_ratio": best_metrics.dead_end_ratio,
                    "room_count": best_metrics.raw_room_count,
                }
            )
        print(json.dumps(payload, indent=2))
    else:
        # ASCII карта
        print(_render_ascii(dungeon))

        # Список всех возможных предметов (подтягиваем из конфига)
        all_item_names = [cfg.label for cfg in config.content.items.symbols.values()]

        # Детализация по комнатам
        for room in sorted(dungeon.rooms.values(), key=lambda r: r.id):
            if room.symbol == "S":
                continue

            print(f"\nRoom {room.id} ({room.label})")
            print(room.description or "")

            directions = dungeon.directions.get(room.id, {}) if hasattr(dungeon, "directions") else {}
            adjacency = dungeon.adjacency.get(room.id, [])
            if adjacency:
                print(" Paths:")
                for neighbor_id in adjacency:
                    direction = directions.get(neighbor_id, "").upper()
                    neighbor = dungeon.rooms.get(neighbor_id)
                    label = neighbor.label if neighbor else f"Room {neighbor_id}"
                    direction_note = f"{direction} " if direction else ""
                    print(f" - {direction_note}to {label} (#{neighbor_id})")

            if room.items:
                print(" Items:")
                for item in room.items:
                    qty_suffix = f" (x{item.quantity})" if item.quantity > 1 else ""
                    print(f" - {item.label}{qty_suffix}: {item.description or ''}")

            if room.monsters:
                print(" Monsters:")
                for monster in room.monsters:
                    qty_suffix = f" (x{monster.quantity})" if monster.quantity > 1 else ""
                    print(f" - {monster.label}{qty_suffix}: {monster.description or ''}")

            # >>> Торговый пост Villager: офферы и «украсть»
            if room.symbol == "V" and all_item_names:
                print(" Trader Offers:")
                offers = rng.sample(all_item_names, k=min(3, len(all_item_names)))
                for idx, name in enumerate(offers, start=1):
                    print(f"  {idx}. {name}")

                try:
                    choice = input("Choose 1-3 to take an item (or press Enter to skip): ").strip()
                except EOFError:
                    choice = ""

                if choice in {"1", "2", "3"} and int(choice) <= len(offers):
                    picked = offers[int(choice) - 1]
                    print(f'You are not worthy "{picked}"!!!')
                else:
                    print("You leave the trader be.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
