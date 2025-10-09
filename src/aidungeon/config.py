from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for 3.10
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass(frozen=True)
class SymbolConfig:
    label: str
    tags: List[str]


@dataclass(frozen=True)
class DungeonConfig:
    grammar_path: Path
    axiom: str
    iterations: int
    rules: Mapping[str, str]
    symbols: Mapping[str, SymbolConfig]


@dataclass(frozen=True)
class PromptConfig:
    system: str
    template: str


@dataclass(frozen=True)
class OllamaConfig:
    endpoint: str
    model: str
    options: Mapping[str, Any]
    completion_path: str
    timeout: float
    room_prompt: PromptConfig
    item_prompt: PromptConfig
    monster_prompt: PromptConfig


@dataclass(frozen=True)
class NarrativeConfig:
    global_cues: str
    room_fallback: str
    item_fallback: str
    monster_fallback: str


@dataclass(frozen=True)
class ContentGroupConfig:
    symbols: Mapping[str, SymbolConfig]
    grammars: Mapping[str, Path]


@dataclass(frozen=True)
class ContentConfig:
    items: ContentGroupConfig
    monsters: ContentGroupConfig


@dataclass(frozen=True)
class Config:
    dungeon: DungeonConfig
    ollama: OllamaConfig
    narrative: NarrativeConfig
    content: ContentConfig


def _ensure_symbol_config(symbols: MutableMapping[str, Any]) -> Dict[str, SymbolConfig]:
    parsed: Dict[str, SymbolConfig] = {}
    for key, value in symbols.items():
        if not isinstance(value, Mapping):
            raise ValueError(f"Symbol {key} must map to a table.")
        label = str(value.get("label", key))
        tags_raw = value.get("tags", [])
        if isinstance(tags_raw, str):
            tags = [tags_raw]
        else:
            tags = [str(tag) for tag in tags_raw]
        parsed[key] = SymbolConfig(label=label, tags=tags)
    return parsed


def load_config(path: str | Path) -> Config:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    dungeon_raw = raw.get("dungeon")
    if not isinstance(dungeon_raw, Mapping):
        raise ValueError("Missing [dungeon] section.")
    grammar_file = dungeon_raw.get("grammar_file")
    if not isinstance(grammar_file, str) or not grammar_file.strip():
        raise ValueError("Missing dungeon.grammar_file entry.")
    grammar_path = Path(grammar_file)
    if not grammar_path.is_absolute():
        grammar_path = (config_path.parent / grammar_path).resolve()
    if not grammar_path.exists():
        raise FileNotFoundError(f"Grammar file not found: {grammar_path}")
    with grammar_path.open("rb") as grammar_handle:
        grammar_raw = tomllib.load(grammar_handle)
    grammar_section = grammar_raw.get("grammar")
    if not isinstance(grammar_section, Mapping):
        raise ValueError("Grammar file must contain a [grammar] table.")
    axiom = str(grammar_section.get("axiom", "")).strip()
    if not axiom:
        raise ValueError("Grammar file missing 'axiom' entry.")
    rules_raw = grammar_section.get("rules", {})
    if not isinstance(rules_raw, Mapping) or not rules_raw:
        raise ValueError("Grammar file missing [grammar.rules] table.")
    symbols = dungeon_raw.get("symbols", {})
    if not isinstance(symbols, MutableMapping) or not symbols:
        raise ValueError("No symbol definitions found under [dungeon.symbols].")
    iterations = int(dungeon_raw.get("iterations", 1))
    dungeon_config = DungeonConfig(
        grammar_path=grammar_path,
        axiom=axiom,
        iterations=iterations,
        rules={str(k): str(v) for k, v in rules_raw.items()},
        symbols=_ensure_symbol_config(symbols),
    )

    ollama_raw = raw.get("ollama")
    if not isinstance(ollama_raw, Mapping):
        raise ValueError("Missing [ollama] section.")
    prompt_file = ollama_raw.get("prompt_file")
    prompt_raw: Optional[Mapping[str, Any]] = None
    narrative_from_prompt: Optional[Mapping[str, Any]] = None
    if isinstance(prompt_file, str) and prompt_file.strip():
        prompt_path = Path(prompt_file)
        if not prompt_path.is_absolute():
            prompt_path = (config_path.parent / prompt_path).resolve()
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        with prompt_path.open("rb") as handle:
            prompt_doc = tomllib.load(handle)
        prompt_raw = prompt_doc.get("prompt")
        if not isinstance(prompt_raw, Mapping):
            raise ValueError("Prompt file missing [prompt] table.")
        narrative_candidate = prompt_doc.get("narrative")
        if isinstance(narrative_candidate, Mapping):
            narrative_from_prompt = narrative_candidate
    else:
        prompt_raw = raw.get("ollama", {}).get("prompt")
        if not isinstance(prompt_raw, Mapping):
            raise ValueError("Missing [ollama.prompt] section or prompt_file.")

    def parse_prompt_section(mapping: Mapping[str, Any], key: str, fallback: Optional[Mapping[str, Any]] = None) -> PromptConfig:
        section = mapping.get(key)
        if section is None and fallback is not None:
            section = fallback
        if section is None and key == "room":
            section = mapping
        if section is None and {"system", "template"}.issubset(mapping.keys()):
            section = mapping
        if not isinstance(section, Mapping):
            raise ValueError(f"Prompt section '{key}' missing.")
        return PromptConfig(
            system=str(section.get("system", "")).strip(),
            template=str(section.get("template", "")).strip(),
        )

    room_prompt = parse_prompt_section(prompt_raw, "room")
    item_prompt = parse_prompt_section(prompt_raw, "item", fallback=prompt_raw.get("room") if isinstance(prompt_raw.get("room"), Mapping) else None)
    monster_prompt = parse_prompt_section(prompt_raw, "monster", fallback=prompt_raw.get("room") if isinstance(prompt_raw.get("room"), Mapping) else None)

    options_raw = raw.get("ollama", {}).get("options", {})
    if not isinstance(options_raw, Mapping):
        raise ValueError("[ollama.options] must be a table.")
    endpoint = str(ollama_raw.get("endpoint", "http://127.0.0.1:11434"))
    model = str(ollama_raw.get("model", "llama3"))
    completion_path = str(ollama_raw.get("completion_path", "/api/generate"))
    timeout = float(ollama_raw.get("timeout", 60))
    ollama_config = OllamaConfig(
        endpoint=endpoint.rstrip("/"),
        model=model,
        options=dict(options_raw),
        completion_path=completion_path,
        timeout=timeout,
        room_prompt=room_prompt,
        item_prompt=item_prompt,
        monster_prompt=monster_prompt,
    )

    narrative_raw = raw.get("narrative")
    if narrative_raw is None and narrative_from_prompt is not None:
        narrative_raw = narrative_from_prompt
    if not isinstance(narrative_raw, Mapping):
        raise ValueError("Missing [narrative] section (either in config or prompt file).")
    room_fallback = narrative_raw.get("room_fallback", narrative_raw.get("fallback", ""))
    item_fallback = narrative_raw.get("item_fallback", narrative_raw.get("fallback", ""))
    monster_fallback = narrative_raw.get("monster_fallback", narrative_raw.get("fallback", ""))
    narrative = NarrativeConfig(
        global_cues=str(narrative_raw.get("global_cues", "")).strip(),
        room_fallback=str(room_fallback).strip(),
        item_fallback=str(item_fallback).strip(),
        monster_fallback=str(monster_fallback).strip(),
    )

    content_raw = raw.get("content")
    if not isinstance(content_raw, Mapping):
        raise ValueError("Missing [content] section.")

    def parse_content_group(name: str, group_raw: Any) -> ContentGroupConfig:
        if not isinstance(group_raw, Mapping):
            raise ValueError(f"[content.{name}] must be a table.")
        symbols_raw = group_raw.get("symbols")
        if not isinstance(symbols_raw, Mapping):
            raise ValueError(f"[content.{name}.symbols] must be a table.")
        symbols = _ensure_symbol_config(dict(symbols_raw))
        grammars_raw = group_raw.get("grammars", {})
        if not isinstance(grammars_raw, Mapping):
            raise ValueError(f"[content.{name}.grammars] must be a table.")
        grammars: Dict[str, Path] = {}
        for room_symbol, path_value in grammars_raw.items():
            path_str = str(path_value)
            path = Path(path_str)
            if not path.is_absolute():
                path = (config_path.parent / path).resolve()
            if not path.exists():
                raise FileNotFoundError(f"Content grammar not found for {name} symbol '{room_symbol}': {path}")
            grammars[str(room_symbol)] = path
        return ContentGroupConfig(symbols=symbols, grammars=grammars)

    items_group = parse_content_group("items", content_raw.get("items"))
    monsters_group = parse_content_group("monsters", content_raw.get("monsters"))
    content_config = ContentConfig(items=items_group, monsters=monsters_group)

    return Config(dungeon=dungeon_config, ollama=ollama_config, narrative=narrative, content=content_config)
