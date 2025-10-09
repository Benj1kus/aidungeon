from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
from typing import Dict, Mapping, Sequence

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from .config import ContentConfig, ContentGroupConfig, NarrativeConfig, OllamaConfig, SymbolConfig
from .dungeon import Dungeon, Entity, Room
from .lsystem import LSystem
from .narrative import OllamaClient, OllamaError


class ContentGenerator:
    def __init__(self, content: ContentConfig, ollama: OllamaConfig, narrative: NarrativeConfig) -> None:
        self._content = content
        self._client = OllamaClient(ollama)
        self._item_prompt = ollama.item_prompt
        self._monster_prompt = ollama.monster_prompt
        self._global_cues = narrative.global_cues
        self._item_fallback = narrative.item_fallback or "A {entity_label} imbued with {entity_tags} qualities rests here."
        self._monster_fallback = (
            narrative.monster_fallback or "A {entity_label} exuding {entity_tags} menace stalks the edges of the room."
        )
        self._grammar_cache: Dict[Path, tuple[LSystem, int]] = {}
        self._sequence_cache: Dict[tuple[str, str], str] = {}
        self._description_cache: Dict[tuple[str, str], str] = {}
        self._think_pattern = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

    def enrich(self, dungeon: Dungeon) -> Dungeon:
        updated_rooms: Dict[int, Room] = {}
        for room in dungeon.rooms.values():
            if room.symbol == "S":
                updated_rooms[room.id] = room
                continue
            items = self._generate_entities(room, self._content.items, "item")
            monsters = self._generate_entities(room, self._content.monsters, "monster")
            updated_rooms[room.id] = replace(room, items=tuple(items), monsters=tuple(monsters))
        return Dungeon(rooms=updated_rooms, adjacency=dungeon.adjacency)

    def _generate_entities(self, room: Room, group: ContentGroupConfig, kind: str) -> Sequence[Entity]:
        grammar_path = group.grammars.get(room.symbol)
        if grammar_path is None:
            return ()
        sequence = self._expand_sequence(grammar_path, room.symbol)
        counts: Dict[str, int] = {}
        order: list[str] = []
        for symbol in sequence:
            if symbol not in group.symbols:
                continue
            if symbol not in counts:
                counts[symbol] = 0
                order.append(symbol)
            counts[symbol] += 1
        entities: list[Entity] = []
        for symbol in order:
            config = group.symbols[symbol]
            description = self._describe_entity(kind, symbol, config, room)
            entities.append(
                Entity(
                    symbol=symbol,
                    label=config.label,
                    tags=config.tags,
                    description=description,
                    quantity=counts[symbol],
                )
            )
        return entities

    def _expand_sequence(self, grammar_path: Path, room_symbol: str) -> str:
        cache_key = (str(grammar_path), room_symbol)
        cached = self._sequence_cache.get(cache_key)
        if cached is not None:
            return cached
        cache_entry = self._grammar_cache.get(grammar_path)
        if cache_entry is None:
            axiom, rules, iterations = self._load_grammar(grammar_path)
            lsystem = LSystem(axiom=axiom, rules=rules)
            cache_entry = (lsystem, iterations)
            self._grammar_cache[grammar_path] = cache_entry
        lsystem, iterations = cache_entry
        expanded = lsystem.expand(iterations)
        self._sequence_cache[cache_key] = expanded
        return expanded

    def _load_grammar(self, path: Path) -> tuple[str, Mapping[str, str], int]:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        grammar_raw = data.get("grammar")
        if not isinstance(grammar_raw, Mapping):
            raise ValueError(f"Grammar file missing [grammar] section: {path}")
        axiom = str(grammar_raw.get("axiom", "")).strip()
        if not axiom:
            raise ValueError(f"Grammar file missing axiom: {path}")
        rules_raw = grammar_raw.get("rules", {})
        if not isinstance(rules_raw, Mapping) or not rules_raw:
            raise ValueError(f"Grammar file missing rules: {path}")
        rules = {str(k): str(v) for k, v in rules_raw.items()}
        iterations = int(grammar_raw.get("iterations", 2))
        iterations = max(iterations, 1)
        return axiom, rules, iterations

    def _describe_entity(self, kind: str, symbol: str, config: SymbolConfig, room: Room) -> str:
        cache_key = (kind, symbol)
        cached = self._description_cache.get(cache_key)
        if cached is not None:
            return cached
        prompt_config = self._item_prompt if kind == "item" else self._monster_prompt
        fallback_template = self._item_fallback if kind == "item" else self._monster_fallback
        tags_text = " ".join(config.tags[:2 if kind == "item" else 3])
        prompt = prompt_config.template.format(
            global_cues=self._global_cues,
            room_label=room.label,
            room_symbol=room.symbol,
            entity_label=config.label,
            entity_symbol=symbol,
            entity_tags=tags_text,
        )
        try:
            description = self._client.generate(prompt=prompt.strip(), system=prompt_config.system.strip())
        except OllamaError:
            description = ""
        if not description:
            description = fallback_template.format(
                global_cues=self._global_cues,
                room_label=room.label,
                room_symbol=room.symbol,
                entity_label=config.label,
                entity_symbol=symbol,
                entity_tags=tags_text,
            )
        description = self._clean_entity_response(description, 3 if kind == "item" else 4)
        self._description_cache[cache_key] = description
        return description

    def _clean_entity_response(self, text: str, max_words: int) -> str:
        cleaned = self._think_pattern.sub("", text)
        cleaned = " ".join(cleaned.split())
        if not cleaned:
            return ""
        words = cleaned.split()
        return " ".join(words[:max_words])
