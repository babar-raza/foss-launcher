# Plans (LLM-ready)

These plans are meant to be pasted directly into an implementation agent (Codex/Sonnet).

## Two different "reports" folders
- **Implementation-time**: agents write reviews/evidence to `./reports/` (this repo).
- **Runtime**: the launcher writes run artifacts under `./runs/<run_id>/...` (binding; see `specs/29_project_repo_structure.md`).

## Plan validation
Before implementation, validate the spec+plan pack:
- `python scripts/validate_spec_pack.py`
- `python scripts/validate_plans.py`

## Traceability (reduce guessing)
- `plans/traceability_matrix.md` maps each spec area to the taskcards that implement/validate it.

## Start here
1) `plans/00_orchestrator_master_prompt.md`
2) Read `plans/taskcards/00_TASKCARD_CONTRACT.md`
3) Execute taskcards in `plans/taskcards/` in order (see INDEX.md).
