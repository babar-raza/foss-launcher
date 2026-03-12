---
id: TC-3880
title: "Wave 2 — Heal Visibility: Grade C pages, claim coverage, convergence detection"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: ["wave2", "heal", "evaluate", "grade-c"]
depends_on: ["TC-3879"]
allowed_paths:
  - plans/taskcards/TC-3880_W2_heal-visibility.md
  - plans/wave2_metrics.json
  - src/launcher/models/content.py
  - src/launcher/models/evaluation.py
  - src/launcher/workers/evaluate/checks/claim_coverage.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/evaluate/finding_classifier.py
  - src/launcher/workers/evaluate/diagnosis.py
  - src/launcher/cli/heal.py
  - specs/schemas/evaluation_report.schema.json
  - tests/unit/workers/evaluate/test_claim_coverage.py
  - tests/unit/workers/test_evaluate.py
evidence_required:
  - plans/wave2_metrics.json
---

# Taskcard TC-3880 — Wave 2: Heal Visibility & Claim Coverage

## Objective

Extend data models and evaluation to make Grade C pages (3+ MEDIUMs) visible to the
heal loop (previously invisible), add a deterministic claim-coverage check, add symmetric
improvement thresholds, and add convergence/oscillation detection to prevent infinite heal loops.

## Required spec references

- `specs/evaluate_worker.md` (evaluation pipeline phases)
- `plans/compiled-discovering-panda.md` (H8/H11, H5, H7, F4/E4 solution designs)

## Scope

### In scope
- F4/E4: Add `claim_texts` to `GeneratedPage`; new `claim_coverage` check
- H8/H11: Include MEDIUM findings in diagnosis; expose c_rate in ReportMetrics
- H5: Symmetric improvement threshold using `_min_meaningful_delta`
- H7: Convergence/oscillation/plateau detection in heal loop

### Out of scope
- H2 (section-level targeting) — Wave 3
- H9 (selective evaluate) — Wave 3
- H10 (eval_fast_path) — Wave 3

## Inputs

- Wave 1 pilot run: `runs/260308_205654_cells_python_83d5/evaluate_checkpoint.json`
- `src/launcher/models/evaluation.py` (ReportMetrics, RootCauseDiagnosis)
- `src/launcher/models/content.py` (GeneratedPage)

## Outputs

- New `src/launcher/workers/evaluate/checks/claim_coverage.py`
- Updated `ReportMetrics` with `medium_count`, `c_rate`, `total_pages`
- Updated `diagnosis.py` to include MEDIUM findings and Grade C pages
- Updated `heal.py` with symmetric delta and termination detection

## Allowed paths

- plans/taskcards/TC-3880_W2_heal-visibility.md
- plans/wave2_metrics.json
- src/launcher/models/content.py
- src/launcher/models/evaluation.py
- src/launcher/workers/evaluate/checks/claim_coverage.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/evaluate/finding_classifier.py
- src/launcher/workers/evaluate/diagnosis.py
- src/launcher/cli/heal.py
- specs/schemas/evaluation_report.schema.json
- tests/unit/workers/evaluate/test_claim_coverage.py
- tests/unit/workers/test_evaluate.py

### Allowed paths rationale
- New check file, model extensions, heal loop changes, and schema extension all required
- Tests required for new claim_coverage check

## Implementation steps

### Step 1: Add medium_count, c_rate, total_pages to ReportMetrics

In `src/launcher/models/evaluation.py`:
```python
class ReportMetrics(LauncherBaseModel):
    critical_count: int
    high_count: int
    medium_count: int = 0       # NEW TC-3880 Wave 2 (H8)
    grades: dict[str, int]
    ab_rate: float
    df_rate: float
    c_rate: float = 0.0          # NEW TC-3880 Wave 2 (H8)
    total_findings: int
    total_pages: int = 0         # NEW TC-3880 Wave 2 (H5)
```

Also add `severity_weight: float = 1.0` to `RootCauseDiagnosis`.

### Step 2: Add claim_texts to GeneratedPage

In `src/launcher/models/content.py`:
```python
class GeneratedPage(LauncherBaseModel):
    ...
    claim_texts: list[str] = Field(default_factory=list)  # TC-3880 Wave 2 (F4)
    assigned_claim_count: int = 0                           # TC-3880 Wave 2 (F4)
```

### Step 3: Create claim_coverage check

New file `src/launcher/workers/evaluate/checks/claim_coverage.py`:
- `check_claim_coverage(content, slug, claim_texts) -> list[Finding]`
- Term extraction: strip stopwords, keep tokens ≥4 chars, top 5 by length
- Coverage: 3-of-5 key terms present in body = claim covered
- Severities: all claims uncovered=CRITICAL; >50% uncovered=HIGH; 2-3=MEDIUM; 1=LOW
- Register in `checks/__init__.py`, wire into evaluate worker, add to diagnosis.py

### Step 4: Update diagnosis.py to include MEDIUM findings

- Add `min_severity: str = "medium"` parameter to `diagnose_root_causes()`
- Include medium findings (severity_weight=1.0) alongside high (2.0) and critical (3.0)
- Populate `medium_count`, `c_rate`, `total_pages` in `_extract_metrics()`

### Step 5: Expand diagnostician prompt to include Grade C pages

In `heal.py` (`_build_diagnostician_prompt`):
- Include Grade C pages in the failing pages list (cap at 15 total, F→D→C order)
- Add `c_rate` to metrics section

### Step 6: Add _min_meaningful_delta and symmetric thresholds

In `heal.py`:
```python
def _min_meaningful_delta(total_pages: int) -> float:
    return max(0.02, 1.0 / max(total_pages, 1))
```
- Apply symmetric delta in `_is_improved` and regression detection

### Step 7: Add convergence/oscillation detection

In `heal.py`, add `_detect_termination_condition(history, total_pages) -> str | None`:
- Oscillation: last 3 steps alternate df_rate direction → "oscillating"
- Convergence: max-min df_rate < delta in last 3 steps → "converged"
- Plateau: 5 consecutive "unchanged" outcomes → "plateau"
- Call after min_steps completed, before LLM call each iteration

## Failure modes

### Failure mode 1: claim_coverage emits too many false positives

**Detection**: Pages with thin content not getting MEDIUM/HIGH; or clean pages getting false positives
**Resolution**: Adjust key-term extraction (increase min char length from 4 to 5; cap at 4 terms)
**Gate**: Unit tests in test_claim_coverage.py

### Failure mode 2: Grade C pages overwhelm diagnostician prompt

**Detection**: Diagnostician prompt > 8000 chars; LLM times out or truncates
**Resolution**: Cap Grade C pages at 5 (not 15) in prompt; show only top findings per page
**Gate**: Prompt length check in heal.py

### Failure mode 3: Symmetric threshold causes false "unchanged" when metrics are improving

**Detection**: `_is_improved` returns "unchanged" when grades clearly improved on visual inspection
**Resolution**: Fall back to 1/total_pages delta; ensure at minimum 2% delta
**Gate**: Unit test `test_min_meaningful_delta`

## Task-specific review checklist

1. [ ] `check_claim_coverage` registered in `checks/__init__.py`
2. [ ] `check_claim_coverage` wired into `_run_deterministic_checks` in evaluate worker
3. [ ] `ReportMetrics.medium_count` and `c_rate` populated in `_extract_metrics`
4. [ ] `diagnose_root_causes` includes MEDIUM findings
5. [ ] `_detect_termination_condition` called in heal loop before LLM call
6. [ ] `_min_meaningful_delta` used symmetrically in both improvement and regression checks
7. [ ] Docstrings updated for `check_claim_coverage`, `_min_meaningful_delta`, `_detect_termination_condition`
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/workers/evaluate/checks/claim_coverage.py` (new)
2. Updated models, diagnosis, heal files
3. `plans/wave2_metrics.json` with pilot run results

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q` — all pass
2. [ ] `check_claim_coverage` unit test: page with 0 claim text coverage → CRITICAL finding
3. [ ] `diagnose_root_causes` unit test: page with 3 MEDIUM findings → produces diagnosis
4. [ ] `_detect_termination_condition` unit test: alternating [0.4, 0.3, 0.4] df_rates → "oscillating"
5. [ ] Wave 2 pilot: `claim_coverage` check appears in at least one page's findings
6. [ ] Wave 2 pilot: `heal_plan.json` stop_reason != always "max_steps" when metrics flat

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: claim_coverage check fires for pages with no claim coverage
- [ ] Evidence captured: plans/wave2_metrics.json

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main heal --run-dir runs/<wave2-run-id> --max-steps 3
```

**Expected results**:
- All tests pass
- claim_coverage findings appear in evaluate_checkpoint.json
- c_rate appears in heal_plan.json metrics

## Integration boundary proven

**Upstream**: evaluate worker (Phase A deterministic checks)
**Downstream**: heal CLI (diagnosis, diagnostician prompt, improvement detection)
**Contract**: `RootCauseDiagnosis` list from `diagnose_root_causes()` drives heal target selection
