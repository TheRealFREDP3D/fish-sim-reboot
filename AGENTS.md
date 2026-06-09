# AGENTS.md

## Codebase shape
- Single Python package: `src/fish_sim/` (installed layout via `setup.py` + `requirements.txt`).
- Real simulation entrypoint is `src/fish_sim/main.py`; root `main.py` is a thin launcher and mutates `sys.path` so `python main.py` still works from the repo root.
- All tunable constants live in `src/fish_sim/config.py`. When behaviour changes, prefer updating constants there before adding new magic numbers.

## Verify / run
- No formal test suite exists. Functional changes should be verified by running the simulation:
  - `python main.py` - Run from repo root
- Tests can be run via: `pytest tests/` (if added)
- Prefer incremental edits under `src/fish_sim/`; do not add executables or scripts alongside the package.

## Repo hygiene
- Generated / transient docs and reports in the repo root (`*.pdf`, `project_review_report.md`) are review artifacts, not source code.
- **CRITICAL: `_DEV_/` directory is protected - NEVER modify, delete, or commit its contents.** This is the user's local development workspace.
- Treat `.codeviz/`, `.sourcetrail/`, `.mypy_cache/`, `.pytest_cache/` as local dev-state—do not commit changes.
- Run `git add -A && git status` before committing to ensure no dev artifacts are included.

## Convenience export
- Key files: `main.py`, `setup.py`, `pyproject.toml`, `requirements.txt`, `src/fish_sim/config.py`, `src/fish_sim/main.py`.

## Architecture notes
- `NeuralFish` in `fish/fish_base.py` is large (~1000 lines). When editing, prefer understanding the flow via `fish_system.py` update loop rather than reading it linearly.
- Recurrent neural network: 30 inputs → 14 hidden → 8 hidden (recurrent) → 12 outputs
- Time system drives seasonal modifiers: metabolism, mating drive, seed dispersal, photosynthesis rate
- Cleaner and Predator are subclasses that override `update()` for species-specific behaviors

## Existing tooling rule (Codacy)
- `.github/instructions/codacy.instructions.md` applies. After any file edit, if the relevant tooling is available, you are expected to run analysis against the changed file. Do not skip this step.