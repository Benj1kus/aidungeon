from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from ..config import load_config
from ..dungeon import Dungeon
from ..main import build_dungeon

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


class DungeonManager:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._current_dungeon: Optional[Dungeon] = None

    def get_dungeon(self, reload: bool = False) -> Dungeon:
        if reload or self._current_dungeon is None:
            # Validate configuration (raises on error) before building.
            load_config(self._config_path)
            self._current_dungeon = build_dungeon(self._config_path, None)
        return self._current_dungeon


def create_app(config_path: Path) -> FastAPI:
    manager = DungeonManager(config_path)

    app = FastAPI(title="AI Dungeon Explorer", version="0.1.0")

    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.get("/", response_class=HTMLResponse)
    async def serve_index() -> HTMLResponse:
        index_path = ASSETS_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=500, detail="Index file missing.")
        return HTMLResponse(index_path.read_text(encoding="utf-8"))

    @app.get("/api/dungeon")
    async def get_dungeon(reload: Optional[int] = None) -> JSONResponse:
        dungeon = manager.get_dungeon(reload=bool(reload))
        return JSONResponse(dungeon.to_dict())

    return app


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run the AI Dungeon web explorer.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/default_config.toml"),
        help="Path to the dungeon configuration file.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    args = parser.parse_args(argv)

    config_path = args.config.resolve()
    app = create_app(config_path)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
