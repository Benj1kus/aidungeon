from __future__ import annotations

from dataclasses import replace
import sys
import threading
import time

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
        self._timeout = config.timeout

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
        stop_event = threading.Event()
        last_message = ""

        def emit(message: str) -> None:
            nonlocal last_message
            last_message = message
            print(message, file=sys.stderr, end="\r", flush=True)

        def ticker() -> None:
            remaining = int(self._timeout)
            if remaining <= 0:
                remaining = 1
            while not stop_event.is_set() and remaining >= 0:
                emit(f"Waiting for Ollama response... {remaining:3d}s remaining")
                time.sleep(1)
                remaining -= 1
            if not stop_event.is_set():
                emit("Waiting for Ollama response... still working, please stand by")

        start_time = time.time()
        ticker_thread = threading.Thread(target=ticker, daemon=True)
        ticker_thread.start()
        success = False
        text = ""
        data = {}
        try:
            try:
                response = requests.post(self._url, json=payload, timeout=self._timeout)
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
            success = True
        finally:
            stop_event.set()
            ticker_thread.join()
            if last_message:
                clear_line = " " * len(last_message)
                print(clear_line, file=sys.stderr, end="\r", flush=True)
            duration = time.time() - start_time
            summary = (
                f"Ollama response received in {duration:.1f}s"
                if success
                else f"Ollama request ended after {duration:.1f}s"
            )
            print(summary, file=sys.stderr, flush=True)
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
