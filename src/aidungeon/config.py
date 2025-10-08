from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping

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
    prompt: PromptConfig


@dataclass(frozen=True)
class NarrativeConfig:
    global_cues: str
    fallback: str


@dataclass(frozen=True)
class Config:
    dungeon: DungeonConfig
    ollama: OllamaConfig
    narrative: NarrativeConfig


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
    rules = dungeon_raw.get("rules", {})
    if not isinstance(rules, Mapping) or not rules:
        raise ValueError("No production rules found under [dungeon.rules].")
    symbols = dungeon_raw.get("symbols", {})
    if not isinstance(symbols, MutableMapping) or not symbols:
        raise ValueError("No symbol definitions found under [dungeon.symbols].")
    iterations = int(dungeon_raw.get("iterations", 1))
    axiom = str(dungeon_raw.get("axiom", "F"))
    dungeon_config = DungeonConfig(
        axiom=axiom,
        iterations=iterations,
        rules={str(k): str(v) for k, v in rules.items()},
        symbols=_ensure_symbol_config(symbols),
    )

    ollama_raw = raw.get("ollama")
    if not isinstance(ollama_raw, Mapping):
        raise ValueError("Missing [ollama] section.")
    prompt_raw = raw.get("ollama", {}).get("prompt")
    if not isinstance(prompt_raw, Mapping):
        raise ValueError("Missing [ollama.prompt] section.")
    prompt = PromptConfig(
        system=str(prompt_raw.get("system", "")).strip(),
        template=str(prompt_raw.get("template", "")).strip(),
    )
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
        prompt=prompt,
    )

    narrative_raw = raw.get("narrative", {})
    if not isinstance(narrative_raw, Mapping):
        raise ValueError("Missing [narrative] section.")
    narrative = NarrativeConfig(
        global_cues=str(narrative_raw.get("global_cues", "")).strip(),
        fallback=str(narrative_raw.get("fallback", "")).strip(),
    )

    return Config(dungeon=dungeon_config, ollama=ollama_config, narrative=narrative)
