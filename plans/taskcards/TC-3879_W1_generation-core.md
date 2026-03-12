---
id: TC-3879
title: "Wave 1: Core Generation & Grading Fixes (F1, Gap1, F3, E1, H3)"
status: Done
priority: Critical
owner: agent
updated: "2026-03-09"
tags: [wave1, generation, grading, fallback, heal]
depends_on: [TC-3878]
allowed_paths:
  - plans/taskcards/TC-3879_W1_generation-core.md
  - plans/wave0_metrics.json
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/evaluate/grader.py
  - src/launcher/models/evaluation.py
  - src/launcher/orchestrator/run_loop.py
  - src/launcher/cli/heal.py
evidence_required:
  - reports/TC-3879/evidence.md
---

# Taskcard TC-3879 — Wave 1: Core Generation & Grading Fixes

## Objective

Eliminate the #1 D-grade source (fallback renderer discarding claims), fix the grading
cliff (any HIGH = D regardless of safety criticality), expand section directive matching
to cover ~20% of mismatched headings, and thread heal_metadata through execute_run.

## Scope

### In scope
- F1: outer fallback passes reconstructed claims/snippets (not empty lists)
- Gap1: _distribute_claims returns all claims when claims < sections (not round-robin)
- F3: 4-tier directive lookup with prefix map + keyword categories + generic fallback
- E1: safety-critical/non-safety-critical HIGH split in grader.py + numeric_score field
- H3: heal_metadata threaded through execute_run + _execute_worker_rerun gets decision param

### Out of scope
- Wave 2+ changes (claim_coverage check, heal visibility, convergence detection)

## Implementation steps

### Step 1: F1 — Fix outer fallback to reconstruct claims
In generate/worker.py outer `for skel_section, result in zip(skeleton, raw_results)`:
- Change to `for idx, (skel_section, result) in enumerate(zip(skeleton, raw_results))`
- Reconstruct `skel_claims` and `skel_snippets` in BaseException branch
- Pass to `render_section_deterministic` instead of empty lists

### Step 2: Gap1 — All claims to under-provisioned sections
In section_prompt.py `_distribute_claims`:
- When `len(claims) < total_sections`: return `list(claims)` instead of single round-robin pick

### Step 3: F3 — 4-tier directive lookup
In section_prompt.py `_get_structure_directive`:
- Add `_HEADING_PREFIX_MAP` with 20 entries
- Add `_GENERIC_STRUCTURAL_DIRECTIVE` constant
- Extend to 4-tier: exact → alias → prefix map/keyword category → generic fallback
- Downgrade "No directive" warning to debug

### Step 4: E1 — Grading cliff fix
In grader.py:
- Add `SAFETY_CRITICAL_CHECKS` frozenset
- Add `_is_safety_critical(finding) -> bool`
- Rewrite `grade_page()` with new table
In models/evaluation.py:
- Add `numeric_score: float = 0.0` to PageEvaluation

### Step 5: H3 — heal_metadata threading
In run_loop.py:
- Add `heal_metadata: dict | None = None` to `execute_run()`
- Thread into both PipelineGraphState initializations (resume + fresh)
In heal.py `_execute_worker_rerun`:
- Add `decision: HealDecision | None = None` param
- Build and pass `heal_metadata` dict to `execute_run()`
- Update the call site to pass `decision=decision`

## Failure modes

### Failure mode 1: Claim reconstruction produces wrong claims for a section

**Detection**: Sections get wrong claims → worse content → new HIGH findings
**Resolution**: `skel_claims` uses same round-robin as `_generate_section` — same formula `j % len_skeleton == idx`. Verify by checking `sec_claims` in `_generate_section` uses same pattern.
**Gate**: generate worker unit tests

### Failure mode 2: E1 grading change introduces test failures

**Detection**: `pytest tests/ -k grader` fails with unexpected grade values
**Resolution**: Check SAFETY_CRITICAL_CHECKS matches the checks that emit safety-related HIGHs; update test expectations for non-safety HIGHs now yielding B instead of D.
**Gate**: grader tests

### Failure mode 3: H3 breaks existing heal mode

**Detection**: Heal re-runs fail to load RunConfig or heal_metadata is ignored
**Resolution**: `heal_metadata` defaults to `None` → coerced to `{}` — backward compatible. Check that PipelineGraphState accepts the value.
**Gate**: heal integration tests

## Task-specific review checklist

1. [ ] Outer fallback uses `enumerate(zip(...))` and `skel_claims` correctly
2. [ ] `render_section_deterministic` outer call passes non-empty claims
3. [ ] `_distribute_claims` returns `list(claims)` when `len(claims) < total_sections`
4. [ ] `_HEADING_PREFIX_MAP` has ≥ 15 entries
5. [ ] `_get_structure_directive` has 4-tier lookup (exact → alias → prefix → generic)
6. [ ] `SAFETY_CRITICAL_CHECKS` frozenset contains safety, slug_safety, claim_leakage, spec_leakage
7. [ ] `grade_page` produces B for 1 non-safety HIGH finding (not D)
8. [ ] `numeric_score` field present in PageEvaluation model
9. [ ] `execute_run` accepts `heal_metadata: dict | None = None`
10. [ ] `_execute_worker_rerun` passes `heal_metadata` to `execute_run`
11. [ ] Tests green under PYTHONHASHSEED=0

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/` — zero failures
2. [ ] grade_page test: 1 `density=HIGH` finding → Grade B (not D)
3. [ ] grade_page test: 1 `safety=HIGH` finding → Grade D (safety-critical unchanged)
4. [ ] Wave 1 pilot `ab_rate` ≥ Wave 0 `ab_rate` (0%)
5. [ ] Wave 1 pilot `df_rate` ≤ Wave 0 `df_rate` (100%)
6. [ ] Wave 1 pilot total D+F pages DECREASES vs Wave 0

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v --tb=short 2>&1 | tail -20
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml
```

## Integration boundary proven

**Upstream**: generate worker `_generate_section` provides PageIR sections
**Downstream**: evaluate worker grades pages; heal CLI passes decisions to execute_run
**Contract**: fallback renderer signature unchanged; PipelineGraphState.heal_metadata is dict
