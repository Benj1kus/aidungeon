from __future__ import annotations

from dataclasses import replace

import requests

from .config import NarrativeConfig, OllamaConfig
from .dungeon import Dungeon, Room


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, config: OllamaConfig) -> None:
        path = config.completion_path.strip()
        if not path.startswith("/"):
            path = f"/{path}"
        self._url = f"{config.endpoint.rstrip('/')}{path}"
        self._model = config.model
        self._options = dict(config.options)

    def generate(self, prompt: str, system: str | None = None) -> str:
        merged_prompt = prompt.strip()
        if system:
            system_clean = system.strip()
            if system_clean:
                merged_prompt = f"{system_clean}\n\n{merged_prompt}"
        payload = {
            "model": self._model,
            "prompt": merged_prompt,
        }
        if self._options:
            payload.update(self._options)
        try:
            response = requests.post(self._url, json=payload, timeout=60)
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        if response.status_code >= 400:
            raise OllamaError(f"Ollama request returned status {response.status_code}: {response.text}")
        try:
            data = response.json()
        except ValueError as exc:
            raise OllamaError(f"Malformed response from Ollama: {response.text}") from exc
        if data.get("error"):
            raise OllamaError(str(data["error"]))
        text = ""
        if "response" in data:
            text = str(data.get("response") or "")
        elif "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            choice = data["choices"][0]
            if isinstance(choice, dict):
                text = choice.get("text") or ""
                if not text:
                    message = choice.get("message", {})
                    if isinstance(message, dict):
                        text = message.get("content") or ""
        elif "content" in data:
            text = str(data.get("content") or "")
        return text.strip()


class NarrativeGenerator:
    def __init__(self, ollama: OllamaConfig, narrative: NarrativeConfig) -> None:
        self._client = OllamaClient(ollama)
        self._template = ollama.prompt.template
        self._system_prompt = ollama.prompt.system
        self._fallback = narrative.fallback
        self._global_cues = narrative.global_cues

    def annotate(self, dungeon: Dungeon) -> Dungeon:
        updated_rooms = {}
        for room in dungeon.rooms.values():
            if room.symbol == "S":
                updated_rooms[room.id] = room
                continue
            description = self._describe_room(room)
            updated_rooms[room.id] = replace(room, description=description)
        return Dungeon(rooms=updated_rooms, adjacency=dungeon.adjacency)

    def _describe_room(self, room: Room) -> str:
        path_summary = "start"
        if room.trail:
            path_summary = "start -> " + " -> ".join(room.trail)
        prompt = self._template.format(
            room_id=room.id,
            symbol=room.symbol,
            label=room.label,
            tags=", ".join(room.tags),
            global_cues=self._global_cues,
            path_summary=path_summary,
        )
        try:
            output = self._client.generate(prompt=prompt.strip(), system=self._system_prompt)
        except OllamaError:
            output = ""
        if not output:
            fallback = self._fallback or "An indescribable place."
            output = fallback.format(
                room_id=room.id,
                symbol=room.symbol,
                label=room.label,
                tags=", ".join(room.tags),
                global_cues=self._global_cues,
                path_summary=path_summary,
            )
        return output.strip()
