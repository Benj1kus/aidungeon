# AI Dungeon-Style Prototype

This project sketches a lightweight, offline-friendly workflow for generating dungeon layouts with an L-system grammar and narrating each location with an [Ollama](https://ollama.ai) model.

## Features
- Expandable L-system grammar for branching dungeon graphs.
- Configurable mapping from grammar symbols to gameplay concepts.
- Prompt-driven narrative generation powered by an Ollama-compatible endpoint (local or remote).
- Per-room grammars for loot and monsters, each described on demand by the same narrator pipeline, using weighted stochastic rules for extra variety.
- Simple CLI to inspect the generated dungeon as JSON or a quick ASCII overview.

## Prerequisites
- Python 3.10 or newer (3.11+ recommended).
- `git` for cloning the repository.
- Optional but strongly recommended: a local [Ollama](https://ollama.ai) installation or access to a compatible HTTP endpoint.
- macOS/Linux shell or Windows PowerShell (the commands below are POSIX-flavoured; adapt paths as needed).

## Installation
1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-org>/aidungeon-lsystem.git
   cd aidungeon-lsystem
   ```
2. **Create and activate a virtual environment**
- macOS/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     py -3 -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
     > If script execution is disabled, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` once before activating.
3. **Install the package in editable mode**
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```
   > Windows + Python 3.10: install the TOML backport once (`pip install tomli`) before running the CLI.
4. **Point the project at an Ollama endpoint**
   - The default configuration (`config/default_config.toml`) references a sample remote endpoint. Replace `ollama.endpoint` with your own server or `http://127.0.0.1:11434` if Ollama is running locally.
   - Update `ollama.model`, `ollama.options`, or prompt settings in `config/prompts/default_prompts.toml` to suit your lesson.

## First Run
1. **Generate and narrate a dungeon (CLI)**
   ```bash
   aidungeon --config config/default_config.toml --candidates 10
   ```
   - The `--candidates` flag controls how many layouts are sampled before narration. Increase it for higher-quality selection at the cost of compute time.
2. **Inspect the output**
   - Use `--format ascii` for a text map and per-room breakdown.
   - Use `--format json` to pipe structured data into other tools.

If Ollama is unavailable, the CLI falls back to placeholder text so you can still iterate on the grammar design.

## Web Explorer
- Launch the interactive web UI:
  ```bash
  aidungeon-web --config config/default_config.toml --host 127.0.0.1 --port 8000
  ```
- Open `http://127.0.0.1:8000` to explore the dungeon. Click room cards or use `W/A/S/D` to move between connections, and regenerate an entirely new layout using the button in the header.

## Configuration
The configuration file governs both the grammar expansion and the narrative prompts. See `config/default_config.toml` for a documented example.
- Room layout grammars live under `config/grammars`, while per-room loot and monster grammars live under their respective `items/` and `monsters/` subdirectories. Update `config/prompts/default_prompts.toml` to change how rooms, items, and monsters are described.
- Automatic scoring samples multiple dungeons (default 10) and keeps the most "enjoyable" layout based on heuristic weights in `config/default_config.toml` (`[evaluation]` section). Adjust weights for `room_diversity`, `branching_factor`, `loot_presence`, `monster_presence`, `dead_end_penalty`, and `room_count` to bias the selector.
- Grammar files can define weighted rules with TOML arrays of tables. Example:
  ```toml
  [grammar]
  axiom = "F"

  [[grammar.rules.F]]
  value = "F[+K]F[-M]F"
  weight = 3

  [[grammar.rules.F]]
  value = "FF"
  ```

## Development
- Run the CLI with `python -m aidungeon.main --config config/default_config.toml`.
- Extend `aidungeon/lsystem.py` for richer grammars or translation to tilemaps.
- Update `aidungeon/narrative.py` to tweak prompt templates or integrate additional metadata.
 - See `docs/generative_pipeline.md` for a step-by-step explanation of how the generative components interact (useful for classroom walkthroughs).

## License
MIT
