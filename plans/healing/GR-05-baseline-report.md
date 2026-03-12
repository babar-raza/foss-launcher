---
id: GR-05
title: "Generate reports/golden_regression_baseline.md — missing plan deliverable"
status: Open
priority: Low
owner: agent
updated: "2026-03-09"
tags: [golden, regression, reporting]
depends_on: [GR-01, GR-04]
allowed_paths:
  - plans/healing/GR-05-baseline-report.md
  - reports/golden_regression_baseline.md
evidence_required:
  - reports/GR-05/evidence.md
---

# GR-05 — Generate golden regression baseline report

## Objective

`reports/golden_regression_baseline.md` was a deliverable implied by the
purrfect-beaming-crown plan (regression suite exists to create an evidence base
for TC-3877/3878/3879 threshold fixes). Create this report now, capturing the
full baseline state: all pages tested, findings per page, KNOWN_FAILURES, and
the authoritative list of miscalibrated thresholds.

## Gap source

TC-3876b self-review: the plan says "The failures must be documented", and
`reports/TC-3876b/evidence.md` exists but is minimal (summary counts only).
The downstream TCs (TC-3877, 3878, 3879) need a precise reference showing
WHICH page/check/severity combination triggered each false positive.

## Required spec references

- `plans/purrfect-beaming-crown.md` (Integration boundary: failures in regression
  suite are the authoritative list of miscalibrated thresholds)

## Scope

### In scope
- Generate `reports/golden_regression_baseline.md` by running the regression
  suite with verbose output and capturing per-page findings
- Include: corpus composition, check coverage, KNOWN_FAILURES table,
  threshold fix roadmap

### Out of scope
- Modifying test files (run as-is, GR-01/GR-04 should complete first)
- Any source code changes

## Inputs

- `tests/golden/test_checks_regression.py` (after GR-01 fixes)
- `golden/` directory (22 files)
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v` output

## Outputs

- `reports/golden_regression_baseline.md`
- `reports/GR-05/evidence.md`

## Allowed paths

- plans/healing/GR-05-baseline-report.md
- reports/golden_regression_baseline.md

### Allowed paths rationale

Report generation only — no source or test files modified.

## Implementation steps

### Step 1: Run full regression suite with capture

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v \
  --tb=short 2>&1 > /tmp/golden_baseline_run.txt
```

### Step 2: Run with per-page finding detail

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -c "
from pathlib import Path
from launcher.shared.golden_loader import GoldenIndex
from launcher.workers.evaluate.worker import _run_deterministic_checks

GOLDEN_DIR = Path('golden')
index = GoldenIndex.load(GOLDEN_DIR)
pages = index.all_pages()

print(f'Corpus: {len(pages)} pages')
print()

_CONTENT_QUALITY_CHECKS = frozenset({
    'density', 'readability', 'repetition', 'structure', 'artifacts',
    'product_names', 'safety', 'spec_leakage', 'semantic_structure',
    'code', 'reference_completeness',
})

for page in sorted(pages, key=lambda p: p.source_path.name):
    findings = _run_deterministic_checks(
        page.content, page.source_path.stem,
        page_role=page.page_role,
        product_name='Aspose.__FAMILY__ for __PLATFORM__',
        canonical_import='aspose_family_foss',
        golden_dir=GOLDEN_DIR,
    )
    content_findings = [f for f in findings if f.check in _CONTENT_QUALITY_CHECKS]
    if content_findings:
        print(f'--- {page.source_path.name} (grade={page.grade}, role={page.page_role}) ---')
        for f in sorted(content_findings, key=lambda x: (x.severity, x.check)):
            print(f'  [{f.severity.upper()}] {f.check}: {f.message}')
    else:
        print(f'--- {page.source_path.name} (grade={page.grade}) --- CLEAN')
" 2>&1
```

### Step 3: Write the baseline report

Create `reports/golden_regression_baseline.md` with these sections:

```markdown
# Golden Regression Baseline
**Date:** 2026-03-09
**Corpus:** N pages across M roles
**Suite:** tests/golden/test_checks_regression.py (TC-3876b)

## Corpus composition

| Page | Grade | Role | Variant | Content checks: findings |
|------|-------|------|---------|--------------------------|
| ... | A | installation | standard | [HIGH] safety: commercial link |
| ... | A | api_reference | standard | [HIGH] repetition: 16 duplicates |
| ... | A | section_index | standard | [HIGH] density: 49 words |
| ... | A | workflow_page | standard | CLEAN |
...

## Summary: findings by check

| Check | HIGH | MEDIUM | LOW | Pages affected |
|-------|------|--------|-----|----------------|
| safety | 1 | 0 | 0 | installation.md |
| repetition | 1 | 0 | 0 | reference.variant-standard.md |
| density | 1 | 0 | 0 | _index.md |
| [all others] | 0 | 0 | 0 | — |

## Threshold fix roadmap

| Check | Finding | Page | Fix TC | Approach |
|-------|---------|------|--------|----------|
| density | 49 words < 100 minimum | _index.md | TC-3877 | Add section_index to exempt roles |
| safety | commercial domain link | installation.md | GOLDEN FILE FIX | Update golden/installation.md |
| repetition | 16 exact dups > threshold=10 | reference.variant-standard.md | TC-3879 | Raise threshold for api_reference |

## KNOWN_FAILURES classification

- **Gate miscalibration** (threshold fix needed): density (_index.md), repetition (reference.variant-standard.md)
- **Golden file defect** (golden file fix needed): safety (installation.md)
- **Not miscalibration**: safety gate is correct; golden file contains commercial URL

## Authoritative list for TC-3877/3878/3879

TC-3877 (density): Fix `_index.md` failure → add `section_index` to exempt roles
TC-3879 (repetition): Fix `reference.variant-standard.md` failure → raise exact-dup threshold for api_reference
TC-3878 (readability): No failures observed — TC-3878 may be skippable
```

## Failure modes

### Failure mode 1: Script raises import error

**Detection**: `ModuleNotFoundError` or `AttributeError`
**Resolution**: Run from project root with `.venv/Scripts/python.exe`; ensure
golden_loader exports `all_pages()` (TC-3876a must be done)
**Gate**: TC-3876a Done status confirmed before running

### Failure mode 2: No grade-B pages → empty table rows

**Detection**: No B entries in corpus composition table
**Resolution**: Document explicitly: "No grade-B pages in corpus as of 2026-03-09"
**Gate**: Note in the report header

### Failure mode 3: Report content is stale after GR-01/GR-04 changes

**Detection**: Test results in report don't match current run
**Resolution**: Regenerate report after GR-01 and GR-04 are applied
**Gate**: Report date matches last run date

## Task-specific review checklist

1. [ ] Report includes corpus composition table (all pages, grades, roles)
2. [ ] Report includes per-check finding summary table
3. [ ] Report distinguishes gate miscalibrations from golden file defects
4. [ ] Threshold fix roadmap is actionable (which TC, which approach)
5. [ ] TC-3878 (readability) is explicitly addressed — "no failures" or "N failures"
6. [ ] Report date matches actual run date
7. [ ] Spec file: not applicable (report only)
8. [ ] Schema: not applicable
9. [ ] Checked `docs/README.md` — no trigger events apply
10. [ ] No new `docs/guides/` file added

## Deliverables

1. `reports/golden_regression_baseline.md` (comprehensive baseline)
2. `reports/GR-05/evidence.md`

## Acceptance checks

1. [ ] `reports/golden_regression_baseline.md` exists and is non-empty
2. [ ] Report contains corpus composition table with all pages
3. [ ] Report distinguishes "gate miscalibration" from "golden file defect"
4. [ ] TC-3877, TC-3878, TC-3879 sections reference specific pages and findings

## Self-review

### Verification results
- [ ] Report generated from actual run (not hand-written)
- [ ] Evidence captured: reports/GR-05/evidence.md

## E2E verification

```bash
test -f reports/golden_regression_baseline.md && \
  grep "TC-3877\|TC-3878\|TC-3879" reports/golden_regression_baseline.md && \
  echo "PASS: baseline report exists with threshold fix references"
```

**Expected results**:
- `PASS: baseline report exists with threshold fix references`

## Integration boundary proven

**Upstream**: TC-3876b regression suite (provides the test data)
**Downstream**: TC-3877, TC-3878, TC-3879 (consume this report as authoritative input)
**Contract**: Report is generated from actual pytest run, not manually authored
