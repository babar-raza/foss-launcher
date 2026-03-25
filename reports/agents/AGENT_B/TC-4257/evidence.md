# AGENT_B Evidence: TC-4257

## Baseline

- Cells Scout checkpoint: `runs/260313_051354_cells_python_a359/scout_checkpoint.json`
- Note Scout checkpoint: `runs/260313_051458_note_python_0fc6/scout_checkpoint.json`
- Structural contract issue: missing `specs/schemas/scout_bundle.schema.json`
- Handoff issue: fresh Understand run logs showed `context.repo_content is empty`

## Changes Verified

- Declared Scout boundary now exists at `specs/schemas/scout_bundle.schema.json`
- `src/launcher/orchestrator/graph_builder.py` now hard-fails missing schemas instead of silently skipping validation
- `src/launcher/orchestrator/graph_builder.py` now preserves `repo_content` across the node boundary
- `src/launcher/workers/scout/scout.py` now filters meta docs and non-code example scaffolding more aggressively

## Test Evidence

- `$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m pytest tests\unit\orchestrator\test_graph_builder.py -q`
  - `18 passed`
- `$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m pytest tests\unit\workers\test_scout.py -q`
  - `45 passed`
- `$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m pytest tests\integration\test_intake_understand_flow.py -q`
  - `4 passed`

## Pilot Evidence

- `runs/260313_053450_cells_python_455b`
  - Understand no longer logs `context.repo_content is empty`
- `runs/260313_053450_note_python_840b`
  - Understand no longer logs disk fallback on a fresh run
- `runs/260313_054425_note_python_f402`
  - Scout reduced Note docs from 61 to 26 and examples from 8 noisy paths to 3 real scripts
- `runs/260313_054527_note_python_97b5`
  - Scout further removed `THIRD_PARTY_NOTICES.md`; final Note artifact is 25 docs and 3 examples

## Decision

Scout is sufficient for downstream use after this round. Remaining concerns are doc/spec freshness and downstream Understand quality, not Scout contract integrity.
