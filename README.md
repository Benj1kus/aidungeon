# AI Dungeon-Style Prototype

This project sketches a lightweight, offline-friendly workflow for generating dungeon layouts with an L-system grammar and narrating each location with an [Ollama](https://ollama.ai) model.

## Features
- Expandable L-system grammar for branching dungeon graphs.
- Configurable mapping from grammar symbols to gameplay concepts.
- Prompt-driven narrative generation powered by an Ollama-compatible endpoint (local or remote).
- Simple CLI to inspect the generated dungeon as JSON or a quick ASCII overview.

## Quick Start
1. Install Python 3.10+ (and `pip install tomli` if you are on 3.10).
2. Create and activate a virtual environment, then install the package in editable mode:
   ```bash
   pip install -e .
   ```
3. Adjust the configuration at `config/default_config.toml` or provide your own TOML file. The default points to a hosted Ollama-compatible endpoint at `https://341f48ced197.ngrok-free.app/v1/completions`; swap in your own URL if needed.
4. Generate a dungeon and descriptions:
   ```bash
   aidungeon --config config/default_config.toml
   ```

If Ollama is unavailable, the CLI falls back to placeholder text so you can still iterate on the grammar design.

## Configuration
The configuration file governs both the grammar expansion and the narrative prompts. See `config/default_config.toml` for a documented example.

## Development
- Run the CLI with `python -m aidungeon.main --config config/default_config.toml`.
- Extend `aidungeon/lsystem.py` for richer grammars or translation to tilemaps.
- Update `aidungeon/narrative.py` to tweak prompt templates or integrate additional metadata.

## License
MIT
