# Generative Pipeline Overview

This project layers several procedural generation techniques to produce a playable, text-driven dungeon experience. The pipeline mixes deterministic L-systems, probabilistic grammars, heuristic evaluation, and LLM-based narration. This document summarizes the stages so students can trace how each method contributes to the final result.

## 1. Dungeon Layout (L-system + Turtle Interpretation)
- **Input**: `config/grammars/classic.toml` defines a base axiom and weighted production rules (e.g., `F = F[+K]F[-M]F(0.4), FF(0.3), …`).
- **Method**: We instantiate an L-system (`src/aidungeon/lsystem.py`) with stochastic rule selection. Each iteration expands the string while respecting rule weights.
- **Interpretation**: The resulting string is fed into the `DungeonBuilder` (`src/aidungeon/dungeon.py`). We treat the string like turtle graphics:
  - `F`, `K`, `M`, … move the “pen” forward and create rooms associated with a symbol.
  - `+` and `-` rotate the heading, `[`/`]` push/pop position/direction to form branches.
- **Output**: A graph of rooms with positions, adjacency, symbol labels, and direction metadata (north/east/…).

## 2. Candidate Sampling & Evaluation
- **Goal**: Generate multiple candidate dungeons and pick the most “enjoyable” before we spend time narrating.
- **Process**:
  1. For each candidate, run the same layout L-system with a different random seed.
  2. Populate loot and monsters *without* consulting Ollama to keep sampling fast (see Step 3).
  3. Score the dungeon using heuristic metrics in `src/aidungeon/evaluation.py`:
     - Room diversity, branching factor, dead-end ratio.
     - Fraction of rooms containing loot/monsters.
     - Room count relative to a target.
  4. Weights in `[evaluation.weights]` (`config/default_config.toml`) define “enjoyable” for the class.
- **Selection**: We keep the highest-scoring candidate and only then move on to narration.

## 3. Loot & Monsters (Per-Room Stochastic Grammars)
- **Source**: `config/grammars/items/` and `config/grammars/monsters/` provide weighted rules for each room symbol (corridor/shrine/lair).
- **Method**: For the chosen seed we re-run content generation using the same grammars but with descriptions enabled:
  - Each room uses its own deterministic seed (`hash(base_seed, room_id, symbol)`), ensuring repeatability.
  - Grammars intentionally bias toward empty productions so rooms can be empty, carry a single item, or host a specific monster.
- **Result**: Each room carries a small inventory (`Entity` objects) tagged with quantity and metadata.

## 4. Narration via Ollama (LLM Prompts)
- **Scope**: We only invoke Ollama for the final dungeon. Calls include:
  - One prompt per non-start room for environmental narration.
  - One prompt per unique item symbol present in the dungeon.
  - One prompt per unique monster symbol present in the dungeon.
- **Fallback**: If Ollama fails or the response is empty, we use templates defined in `config/prompts/default_prompts.toml`.
- **Cleanup**: Responses are filtered to remove `<think>…</think>` blocks and truncated to brief phrases.

## 5. Web Visualization & Interaction
- **Map Rendering**: The web UI (FastAPI + Vanilla JS) loads `/api/dungeon`, displays the graph with visited/hidden states, and shows loot/monster icons once discovered.
- **Navigation**: WASD keyboard controls and direction-labeled buttons move between rooms. Loot/monster details appear in panel sections.
- **Regeneration**: The “Regenerate Dungeon” button triggers the full pipeline, sampling afresh and narrating only the final result.

## Summary Sequence
1. Expand weighted L-system for layout.
2. Build graph with turtle interpretation.
3. Sample `N` candidates (grammar-driven loot/monsters sans Ollama).
4. Score each candidate; keep the best.
5. Rebuild best candidate w/ descriptions enabled.
6. Call Ollama for rooms, loot, monsters; apply fallbacks/cleanup.
7. Serve final dungeon to CLI and web interfaces.

Users can tweak grammar weights, evaluation heuristics, or prompt templates to see how each stage affects the overall experience.
