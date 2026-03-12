---
id: TC-3881
title: "Wave 3 — Golden Hardening, Selective Evaluate, Artifact Rollback"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: ["wave3", "golden", "heal", "evaluate", "selective"]
depends_on: ["TC-3880"]
allowed_paths:
  - plans/taskcards/TC-3881_W3_golden-selective.md
  - plans/wave3_metrics.json
  - src/launcher/shared/golden_loader.py
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/evaluate/checks/structure.py
  - src/launcher/workers/planner/worker.py
  - src/launcher/models/plan.py
  - src/launcher/cli/heal.py
  - src/launcher/orchestrator/graph_builder.py
  - src/launcher/workers/evaluate/worker.py
  - specs/schemas/plan.schema.json
evidence_required:
  - plans/wave3_metrics.json
---

# Taskcard TC-3881 — Wave 3: Golden Hardening & Selective Evaluation

## Objective

Make the golden corpus structurally binding (G1, G2, G4, G5, G7), implement
artifact rollback to prevent heal regressions (H1), activate selective
evaluation to speed up heal (H9), and enable eval_fast_path to reduce token
cost (H10).

## Required spec references

- `specs/evaluate_worker.md` (golden compliance checking)
- `plans/compiled-discovering-panda.md` (G1-G7, H1, H9, H10 solution designs)

## Scope

### In scope
- G1: Golden section structural fingerprint in prompt
- G2: Tier-aware variant selection in section_prompt.py
- G4: Pass 2 LLM retry for Tier C
- G5: Section-level golden check in evaluate
- G7: Planner escalation for golden mismatches
- H1: Artifact rollback on heal regression
- H9: Selective evaluate (skip non-target pages in heal)
- H10: eval_fast_path activation from heal_metadata

### Out of scope
- H2 (section-level targeting) — Wave 4
- G6 (diff-aware golden) — Wave 4

## Allowed paths

- plans/taskcards/TC-3881_W3_golden-selective.md
- plans/wave3_metrics.json
- src/launcher/shared/golden_loader.py
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/evaluate/checks/structure.py
- src/launcher/workers/planner/worker.py
- src/launcher/models/plan.py
- src/launcher/cli/heal.py
- src/launcher/orchestrator/graph_builder.py
- src/launcher/workers/evaluate/worker.py
- specs/schemas/plan.schema.json

### Allowed paths rationale
- Golden loader and section_prompt changes for G1/G2/G4
- Structure check for G5
- Planner worker and plan model for G7
- Heal CLI for H1, H10
- Graph builder and evaluate worker for H9, H10

## Implementation steps

### Step 1: G1 — Golden structural fingerprint in section prompt

In `golden_loader.py`, add fields to `GoldenSection`:
- `code_block_count`, `list_block_count`, `table_count`, `heading_count` (int)
- `code_to_prose_ratio` (float)
Compute in `_parse_sections`.

Add `_summarize_section_structure(gs: GoldenSection) -> str` producing:
```
Block sequence: paragraph → code:python → list
Code blocks: 1 | Lists: 1 | Tables: 0
Min words: ~150 | Prose-to-code ratio: 0.6
Rule: produce ALL block types listed above.
```

In `section_prompt.py`, `_build_golden_reference_block`:
- Prepend `_summarize_section_structure` output before excerpt
- Change instruction to "Replicate these specific structural elements exactly."

### Step 2: G2 — Tier-aware variant selection

In `section_prompt.py` / `worker.py`:
- `build_section_prompt` and `_build_golden_reference_block` accept `variant: str = "standard"`.
- In `worker.py`, pass `variant="minimal"` for Tier C, `"standard"` for A/B.
- `_load_golden_for_role` also accepts `variant` parameter.

### Step 3: G4 — Pass 2 LLM retry for Tier C

In `worker.py`, `enforce_block_spec`:
- Remove `richness_tier != "C"` guard from Pass 2.
- For Tier C, cap retries at 1.

### Step 4: G5 — Section-level golden check in evaluate

In `checks/structure.py`:
- Add `_split_markdown_sections(body: str) -> list[tuple[str, str]]` helper.
- Rewrite `check_golden_spec_from_markdown` to loop per section, look up per-section
  golden spec, emit Finding with `section_id=heading`. Keep page-level as fallback.

### Step 5: G7 — Planner escalation for golden mismatches

In `planner/worker.py`:
- Replace inline Jaccard with `golden_index.get_section()` call.
- Three escalation tiers: 0-1 unmatched=log, 2-3=warning+emit event, ≥4=high severity event.
- Add `golden_unmatched_sections: list[str] = []` to `PlannedPage` in `models/plan.py`.

### Step 6: H1 — Artifact rollback

In `heal.py`, `_save_rollback_snapshot`:
- Before re-run: backup target page `.md` files and both checkpoint JSONs to `*.heal_bak_{step}`.
- On regression: restore all `.heal_bak_{step}` files to originals.
- On success/unchanged: delete `.heal_bak` files.

### Step 7: H9 — Selective evaluate

In `graph_builder.py`:
- Extract `heal_target_pages` from `heal_metadata["target_pages"]` → `WorkerContext`.

In `evaluate/worker.py`:
- When `context.heal_target_pages` set and `slug not in heal_target_pages`:
  load cached `PageEvaluation` from `evaluation/pages/{slug}.eval.json`.
  Emit `"evaluate_page_skipped"`. Skip LLM review.

### Step 8: H10 — eval_fast_path activation

In `graph_builder.py`:
- Read `eval_fast_path` from `heal_metadata` → `WorkerContext`.

In `heal.py`:
- Set `"eval_fast_path": step_idx < max_steps - 1` in `heal_metadata`.

## Failure modes

### Failure mode 1: Golden structural fingerprint too verbose → prompt overflow

**Detection**: Prompt length > 8000 chars; LLM truncates
**Resolution**: Cap fingerprint to 3 lines; drop code-to-prose ratio line
**Gate**: Prompt length test in test_generate.py

### Failure mode 2: Selective evaluate loads stale cached evaluation

**Detection**: A page with regenerated content gets an old cached grade
**Resolution**: Only load cache when `ir_path` or `md_path` hasn't changed (check mtime or hash)
**Gate**: Integration test verifying non-target pages re-use cache

### Failure mode 3: Artifact rollback overwrites in-progress files

**Detection**: `.heal_bak` files from previous step still present at start of next step
**Resolution**: Check for stale `.heal_bak` and warn; don't overwrite if present
**Gate**: Unit test for rollback file management

## Task-specific review checklist

1. [ ] `_summarize_section_structure` produces human-readable constraint list (≤4 lines)
2. [ ] `variant` param threads from `worker.py` through `build_section_prompt` to `_load_golden_for_role`
3. [ ] Pass 2 enabled for Tier C (verify by pilot run event log)
4. [ ] Section-level golden findings have `section_id` field populated
5. [ ] `golden_unmatched_sections` added to `PlannedPage` model and schema
6. [ ] `.heal_bak` files created before re-run, deleted after success
7. [ ] `evaluate_page_skipped` event fires for non-target pages during heal
8. [ ] `eval_fast_path=True` propagated to WorkerContext during non-final heal steps
9. [ ] Docstrings updated for all new/changed public functions
10. [ ] Spec file updated if worker behavior changed
11. [ ] Schema description fields present for new properties

## Deliverables

1. Updated `golden_loader.py`, `section_prompt.py`, `worker.py` (generate)
2. Updated `structure.py` (checks)
3. Updated `planner/worker.py`, `models/plan.py`
4. Updated `heal.py`, `graph_builder.py`, `evaluate/worker.py`
5. `plans/wave3_metrics.json`

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q`
2. [ ] Golden reference block in generated prompt contains `"Block sequence:"` line (G1)
3. [ ] `.heal_bak_0` files appear before heal re-run, deleted after success (H1)
4. [ ] `evaluate_page_skipped` events appear in heal session event log (H9)
5. [ ] Heal steps 0–N-1 have `eval_fast_path=True`, final step has False (H10)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Pilot: wave3_metrics.json captured
- [ ] Evidence: `.heal_bak` lifecycle verified

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main heal heal <run_dir> --max-steps 5
```

## Integration boundary proven

**Upstream**: generate worker (golden reference injection) → evaluate worker (golden compliance)
**Downstream**: heal CLI (rollback, selective eval, fast_path)
**Contract**: `WorkerContext.heal_target_pages`, `eval_fast_path` passed through graph_builder
