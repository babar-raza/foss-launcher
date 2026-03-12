---
id: TC-3878
title: "Wave 0: Threshold & Severity Calibration (G3, E2, E3, Gap3)"
status: Done
priority: Critical
owner: agent
updated: "2026-03-09"
tags: [wave0, grading, readability, seo, golden]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3878_W0_threshold-calibration.md
  - plans/baseline_metrics.json
  - src/launcher/shared/golden_loader.py
  - src/launcher/workers/evaluate/checks/readability.py
  - src/launcher/workers/evaluate/checks/seo.py
  - src/launcher/workers/generate/worker.py
evidence_required:
  - reports/TC-3878/evidence.md
---

# Taskcard TC-3878 — Wave 0: Threshold & Severity Calibration

## Objective

Apply 4 zero-logic-change calibrations to constants and severity labels that
immediately reduce false MEDIUM/HIGH findings, raise the grade ceiling from D
to B/C for structurally clean pages, and fix false-positive golden exemplar
injection. No new functions, no dependencies on other waves.

## Required spec references

- Forensic analysis plan: `C:\Users\prora\.claude\plans\compiled-discovering-panda.md` (Wave 0 section)
- Tasks: G3 (Jaccard threshold), E2 (FK thresholds), E3 (SEO MEDIUM→LOW), Gap3 (skills log level)

## Scope

### In scope
- Change `_SECTION_JACCARD_THRESHOLD` 0.3 → 0.5 + add 2-token minimum guard (G3)
- Add `page_role` param + `_REFERENCE_ROLES` to `check_readability_from_markdown`; raise MEDIUM 16→18, HIGH 20→22 (E2)
- Downgrade `missing seoTitle` and `missing canonical URL` from MEDIUM to LOW in `check_seo` (E3)
- Upgrade skills load exception from DEBUG log to WARNING; emit `"skills_load_failed"` event (Gap3)

### Out of scope
- New functions, abstractions, or logic beyond threshold/severity changes
- Any Wave 1+ changes (grading model, fallback renderer, heal context)

## Inputs

- `src/launcher/shared/golden_loader.py` — Jaccard threshold constant and Level 3 match logic
- `src/launcher/workers/evaluate/checks/readability.py` — FK threshold constants
- `src/launcher/workers/evaluate/checks/seo.py` — severity labels for seoTitle and canonical
- `src/launcher/workers/generate/worker.py` — skills load exception handler

## Outputs

- 4 modified source files with calibrated constants/severities
- Test suite green (PYTHONHASHSEED=0 pytest)
- Wave 0 pilot run with ab_rate ≥ baseline (0%) and df_rate ≤ 100% (any improvement or no regression)

## Allowed paths

- plans/taskcards/TC-3878_W0_threshold-calibration.md
- plans/baseline_metrics.json
- src/launcher/shared/golden_loader.py
- src/launcher/workers/evaluate/checks/readability.py
- src/launcher/workers/evaluate/checks/seo.py
- src/launcher/workers/generate/worker.py

### Allowed paths rationale
All 4 source files are direct targets of Wave 0 changes. Taskcard and baseline are plan artifacts.

## Implementation steps

### Step 1: G3 — Raise Jaccard threshold and add token guard (golden_loader.py)

Change `_SECTION_JACCARD_THRESHOLD` from `0.3` to `0.5`.
In `get_section` Level 3 block: skip Jaccard if `len(needle_words) < 2 or len(hay_words) < 2`.

### Step 2: E2 — FK threshold calibration (readability.py)

Add `_REFERENCE_ROLES` frozenset. Add `page_role: str = ""` to `check_readability_from_markdown`.
Reference roles skip FK (return only long-sentence LOW). Other roles: MEDIUM 16→18, HIGH 20→22.
Update docstrings and message threshold numbers.

### Step 3: E3 — SEO severity downgrade (seo.py)

Change `"Missing seoTitle"` finding severity from `"medium"` to `"low"`.
Change `"Missing canonical URL"` finding severity from `"medium"` to `"low"`.
Leave `"Canonical URL not HTTPS"` severity as `"high"`.

### Step 4: Gap3 — Skills load logging (worker.py)

Change `context.log.debug("[Generate] Skills load skipped: %s", _e)` to
`context.log.warning("[Generate] Skills load failed (%s): %s", type(_e).__name__, _e)`.
Add `_skills_failed` bool; when True emit separate `"skills_load_failed"` event before the normal emit.

## Failure modes

### Failure mode 1: Jaccard guard breaks existing golden tests

**Detection**: `pytest tests/ -k golden` fails — golden section matching returns None where expected
**Resolution**: Check test fixtures for headings with <2 meaningful tokens; those should have an exact match at Level 1 or 2 before reaching Level 3. Verify fixture headings have ≥2 content words.
**Gate**: golden_loader tests

### Failure mode 2: Reference role FK skip causes false ALL-PASS on bad content

**Detection**: Reference pages with truly bad prose (FK > 22) no longer emit HIGH
**Resolution**: Confirm _REFERENCE_ROLES only includes `api_reference` and `class_reference`; these legitimately have high FK from code-heavy content
**Gate**: readability tests

### Failure mode 3: SEO LOW downgrade masks missing metadata from operators

**Detection**: Operators can't distinguish "missing seoTitle" from "minor SEO issue"
**Resolution**: The finding message is unchanged; only severity is different. Operators filter by message content. Acceptable trade-off documented in plan.
**Gate**: seo tests

## Task-specific review checklist

1. [ ] `_SECTION_JACCARD_THRESHOLD` is `0.5` in golden_loader.py
2. [ ] Level 3 Jaccard skipped when `len(needle_words) < 2 or len(hay_words) < 2`
3. [ ] `check_readability_from_markdown` accepts `page_role` param
4. [ ] FK MEDIUM threshold is `18.0`, HIGH threshold is `22.0` in readability.py
5. [ ] `_REFERENCE_ROLES` frozenset defined and used to skip FK for reference pages
6. [ ] `missing seoTitle` severity is `"low"` in seo.py
7. [ ] `missing canonical URL` severity is `"low"` in seo.py
8. [ ] `canonical URL not HTTPS` severity is still `"high"` in seo.py
9. [ ] Skills load failure logs at WARNING level (not DEBUG)
10. [ ] `"skills_load_failed"` event emitted on exception (distinct from `"skills_inactive"`)
11. [ ] Docstrings updated for all changed public functions

## Deliverables

1. 4 modified source files with Wave 0 calibrations
2. pytest suite green under PYTHONHASHSEED=0
3. Wave 0 pilot run output (evaluate_checkpoint.json) in runs/wave0-*/

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/` — zero failures
2. [ ] `grep -n "_SECTION_JACCARD_THRESHOLD" src/launcher/shared/golden_loader.py` shows `0.5`
3. [ ] `grep -n "fk_grade > 16" src/launcher/workers/evaluate/checks/readability.py` — no matches
4. [ ] `grep -n "Missing seoTitle" src/launcher/workers/evaluate/checks/seo.py` — shows `"low"`
5. [ ] Wave 0 pilot ab_rate ≥ 0% (baseline), df_rate ≤ 100% (no regression)
6. [ ] Zero new CRITICAL findings introduced by threshold changes

## Self-review

### Verification results

- [ ] Tests: ?/? PASS
- [ ] Validation: pytest PASS
- [ ] Evidence captured: reports/TC-3878/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v --tb=short 2>&1 | tail -20

# Pilot run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run \
  configs/pilots/aspose-cells-foss-python.yaml \
  --run-dir runs/wave0-20260309
```

**Expected results**:
- pytest: all pass, zero failures
- Pilot: ab_rate ≥ 0.0 (any improvement or no regression from 0% baseline)
- Pilot: No new CRITICAL findings beyond the 1 in baseline

## Integration boundary proven

**Upstream**: `check_readability_from_markdown` called from evaluate/worker.py with page content
**Downstream**: `Finding` objects consumed by grader.py and go_criteria.py
**Contract**: Severity labels ("low"/"medium"/"high"/"critical") are the grading inputs
