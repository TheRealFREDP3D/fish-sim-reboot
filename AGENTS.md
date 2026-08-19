# AGENTS.md

## Codebase shape
- Single Python package: `src/fish_sim/` (installed layout via `setup.py` + `pyproject.toml`).
- Real entrypoint: `src/fish_sim/main.py`. Root `main.py` is a thin launcher that mutates `sys.path` so `python main.py` works from repo root.
- All tunable constants live in `src/fish_sim/config.py`. Prefer updating constants there over adding magic numbers.

## Verify / run
- **Run the simulation:** `python main.py` (from repo root)
- **Run tests:** `pytest tests/` — tests exist in `tests/test_core.py` (neural net, time system, plant lifecycle, fish traits)
- **Lint:** `ruff check src/` (config in `pyproject.toml`: line-length 100, target py38)
- **Typecheck:** `mypy src/` (config in `pyproject.toml`)
- Prefer incremental edits under `src/fish_sim/`; do not add executables alongside the package.

## Repo hygiene
- **CRITICAL: `_DEV_/` is protected — never modify, delete, or commit its contents.**
- `.codeviz/`, `.sourcetrail/`, `.mypy_cache/`, `.pytest_cache/` are local dev-state — do not commit.
- `*.pdf` and `project_review_report.md` in root are review artifacts, not source code.
- Run `git add -A && git status` before committing to ensure no dev artifacts sneak in.

## Architecture notes
- **NeuralFish** (`src/fish_sim/fish/fish_base.py`, ~1360 lines). Prefer tracing the update loop in `fish_system.py` over reading it linearly.
- **Neural network:** 30 inputs → 14 hidden → 8 hidden (recurrent) → 12 outputs. All defined in `config.py` (`NN_INPUT_COUNT`, etc.) and implemented in `neural_net.py`.
- **Output layout** (from `neural_net.py`): `[0]` steer, `[1]` thrust, `[2]` hide_drive, `[3]` sprint_drive, `[4]` clean_drive, `[5]` ambush_drive, `[6]` dash_drive, `[7:12]` state softmax.
- **Stale config.py constants:** `OUTPUT_STEER` through `OUTPUT_STATE_START` (lines 421-428) define a legacy 9-output layout. The actual code uses hardcoded indices `[0:12]`. These constants are unused — ignore them.
- **Stale README:** `README.md` claims 27 inputs / 9 outputs. The real architecture is 30 inputs / 12 outputs (per `config.py` and `neural_net.py`). Trust `config.py` over README.
- **Time system** (`time_system.py`): drives seasonal modifiers — metabolism, mating drive, seed dispersal, photosynthesis rate, predator activity.
- **Cleaner** (`cleaner_fish.py`) and **Predator** (`predator_fish.py`) are subclasses of `NeuralFish` that override `update()` for species-specific behaviors.
- **Simulation flow** (`src/fish_sim/main.py`): `TimeSystem` → `SoilGrid` → `ParticleSystem` → `PlantManager` → `FishSystem` → `Camera`. Each system receives `dt` and (where relevant) `time_system` for seasonal modulation.

## Existing tooling rule (Codacy)
- `.github/instructions/codacy.instructions.md` applies. After any file edit, if Codacy MCP tooling is available, run `codacy_cli_analyze` against the changed file. Do not skip this step.