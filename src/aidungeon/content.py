from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
from typing import Dict, Optional, Sequence, Tuple

from .config import (
    ContentConfig,
    ContentGroupConfig,
    NarrativeConfig,
    OllamaConfig,
    SymbolConfig,
    parse_grammar_file,
    Rule,
)
from .dungeon import Dungeon, Entity, Room
from .lsystem import LSystem
from .narrative import OllamaClient, OllamaError


class ContentGenerator:
    def __init__(
        self,
        content: ContentConfig,
        ollama: OllamaConfig,
        narrative: NarrativeConfig,
        base_seed: int = 0,
        enable_descriptions: bool = True,
    ) -> None:
        self._content = content
        self._enable_descriptions = enable_descriptions
        self._client: Optional[OllamaClient] = OllamaClient(ollama) if enable_descriptions else None
        self._item_prompt = ollama.item_prompt
        self._monster_prompt = ollama.monster_prompt
        self._global_cues = narrative.global_cues
        self._item_fallback = narrative.item_fallback or "A {entity_label} imbued with {entity_tags} qualities rests here."
        self._monster_fallback = (
            narrative.monster_fallback or "A {entity_label} exuding {entity_tags} menace stalks the edges of the room."
        )
        self._base_seed = base_seed
        self._grammar_cache: Dict[Path, Tuple[str, Dict[str, Sequence[Rule]], int]] = {}
        self._description_cache: Dict[tuple[str, str, int], str] = {}
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
        return Dungeon(rooms=updated_rooms, adjacency=dungeon.adjacency, directions=dungeon.directions)

    def _generate_entities(self, room: Room, group: ContentGroupConfig, kind: str) -> Sequence[Entity]:
        grammar_path = group.grammars.get(room.symbol)
        if grammar_path is None:
            return ()
        sequence = self._expand_sequence(grammar_path, room.id, room.symbol)
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

    def _expand_sequence(self, grammar_path: Path, room_id: int, room_symbol: str) -> str:
        cache_entry = self._grammar_cache.get(grammar_path)
        if cache_entry is None:
            cache_entry = parse_grammar_file(grammar_path)
            self._grammar_cache[grammar_path] = cache_entry
        axiom, rules, iterations = cache_entry
        seed = hash((self._base_seed, grammar_path, room_id, room_symbol)) & 0xFFFFFFFF
        lsystem = LSystem(axiom=axiom, rules=rules, seed=seed)
        return lsystem.expand(iterations)

    def _describe_entity(self, kind: str, symbol: str, config: SymbolConfig, room: Room) -> str:
        cache_key = (kind, symbol, room.id)
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
        description = ""
        if self._enable_descriptions and self._client is not None:
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
        description = self._clean_entity_response(description, 4)
        self._description_cache[cache_key] = description
        return description

    def _clean_entity_response(self, text: str, max_words: int) -> str:
        cleaned = self._think_pattern.sub("", text)
        cleaned = " ".join(cleaned.split())
        if not cleaned:
            return ""
        words = cleaned.split()
        return " ".join(words[:max_words])
