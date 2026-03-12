---
id: HC-TIER-01
title: "Wire richness_tier into check_density and check_structure calls"
status: Done
priority: High
owner: "agent"
updated: "2026-03-12"
tags: [evaluate, tier-aware, healing]
depends_on: [TC-HO-08]
allowed_paths:
  - plans/healing/HC-TIER-01_richness_tier_wiring.md
  - src/launcher/workers/evaluate/worker.py
evidence_required:
  - reports/HC-TIER-01/evidence.md
---

# Taskcard HC-TIER-01 — Wire richness_tier into check_density and check_structure

## Objective

TC-HO-08B/C added tier-aware thresholds to `check_density()` and `check_structure()`,
but `evaluate/worker.py` never passes `richness_tier` to either call — the new
`_TIER_DENSITY` and `_TIER_HEADING` dicts are dead code. This taskcard wires the tier
so Tier C pages use appropriate lower thresholds (50/10 words vs 100/20) and avoid
false-positive density/structure failures.

## Root cause

In `_run_deterministic_checks()` (evaluate/worker.py line 604-606):
```python
findings.extend(check_structure(content, slug))
findings.extend(check_density(content, slug, page_role=page_role))
```
Both `check_structure` and `check_density` accept `richness_tier: str = "A"` but
neither call passes it, so all pages are evaluated as Tier A regardless of actual
richness.

## Source of richness_tier in Evaluate context

`richness_tier` is NOT on `GeneratedPage` or `ContentManifest`. It must be loaded
from the understand checkpoint via `_load_understand_checkpoint(context)` which is
already present (TC-HO-03). Extract `checkpoint.get("richness_tier", {}).get("tier", "A")`.

This is loaded once per evaluate run (not per page), since richness_tier is a
repo-level property. Cache in a local variable before the per-page loop.

## Required spec references

- `specs/worker_evaluate.md` (Section: Tier-aware thresholds)
- `src/launcher/workers/evaluate/checks/density.py` (TC-HO-08B: _TIER_DENSITY)
- `src/launcher/workers/evaluate/checks/structure.py` (TC-HO-08C: _TIER_HEADING)

## Scope

### In scope
- Load `richness_tier.tier` from understand checkpoint in `evaluate/worker.py`
- Pass `richness_tier` to `_run_deterministic_checks()`
- Thread `richness_tier` into `check_density()` and `check_structure()` calls

### Out of scope
- Adding `richness_tier` to `GeneratedPage` or `ContentManifest` models (not needed)
- Modifying density.py or structure.py (already correct from TC-HO-08B/C)

## Inputs

- `src/launcher/workers/evaluate/worker.py`
- `src/launcher/workers/evaluate/checks/density.py` (unchanged — already accepts tier)
- `src/launcher/workers/evaluate/checks/structure.py` (unchanged — already accepts tier)

## Outputs

- Updated `src/launcher/workers/evaluate/worker.py` with tier wired through

## Allowed paths

- plans/healing/HC-TIER-01_richness_tier_wiring.md
- src/launcher/workers/evaluate/worker.py

### Allowed paths rationale
- `worker.py`: the only file that needs to change — the tier loading and call-site wiring

## Implementation steps

### Step 1: Add richness_tier loading in execute()

In `evaluate/worker.py`, in the `execute()` method, before the per-page evaluation
loop, load the repo-level richness_tier from the understand checkpoint:

```python
# HC-TIER-01: Load repo-level richness_tier for tier-aware density/structure checks.
_richness_tier_str: str = "A"
try:
    _cp = _load_understand_checkpoint(context)
    _rt = _cp.get("richness_tier", {})
    _richness_tier_str = _rt.get("tier", "A") if isinstance(_rt, dict) else "A"
except Exception:
    pass  # Default to Tier A on checkpoint absence (conservative — no false negatives)
```

### Step 2: Thread richness_tier into _run_deterministic_checks signature

Add `richness_tier: str = "A"` parameter to `_run_deterministic_checks()` and
pass it to both check calls:

```python
# In _run_deterministic_checks signature:
richness_tier: str = "A",  # HC-TIER-01: repo-level tier for calibrated thresholds

# Replace:
findings.extend(check_structure(content, slug))
findings.extend(check_density(content, slug, page_role=page_role))

# With:
findings.extend(check_structure(content, slug, richness_tier=richness_tier))
findings.extend(check_density(content, slug, page_role=page_role, richness_tier=richness_tier))
```

### Step 3: Pass _richness_tier_str at call site

At the `_run_deterministic_checks(...)` call (line ~253), add:

```python
richness_tier=_richness_tier_str,  # HC-TIER-01: tier-aware density/structure
```

## Failure modes

### Failure mode 1: Checkpoint absent before evaluate runs

**Detection**: `_load_understand_checkpoint` raises ValueError/Exception
**Resolution**: `except Exception: pass` — default to `"A"` (conservative: no false negatives, some false positives for Tier C repos until checkpoint is present)
**Gate**: density, structure checks

### Failure mode 2: richness_tier key missing from checkpoint dict

**Detection**: `_cp.get("richness_tier", {})` returns empty dict or non-dict
**Resolution**: `_rt.get("tier", "A") if isinstance(_rt, dict) else "A"` handles both
**Gate**: density, structure checks

### Failure mode 3: tier value unexpected (not A/B/C)

**Detection**: check_density / check_structure use `_TIER_DENSITY.get(richness_tier, (100, 20))` — unrecognized tier falls back to Tier A thresholds
**Resolution**: Already handled in density.py and structure.py via dict.get() with default
**Gate**: density, structure checks

## Task-specific review checklist

1. [ ] `check_density` call in `_run_deterministic_checks` passes `richness_tier=richness_tier`
2. [ ] `check_structure` call in `_run_deterministic_checks` passes `richness_tier=richness_tier`
3. [ ] `_run_deterministic_checks` signature accepts `richness_tier: str = "A"`
4. [ ] `_richness_tier_str` is loaded from checkpoint before the per-page loop
5. [ ] Exception handling defaults to `"A"` (no false negatives)
6. [ ] All existing tests still pass (PYTHONHASHSEED=0)
7. [ ] Docstrings updated for `_run_deterministic_checks`
8. [ ] Spec file confirmed no new drift (density/structure tier logic already specced in TC-HO-08)
9. [ ] Schema: no schema changes needed
10. [ ] Checked docs/README.md — no ownership trigger for this internal wiring fix
11. [ ] If new docs/guides/ file added: docs/README.md index updated (N/A)

## Deliverables

1. Updated `src/launcher/workers/evaluate/worker.py` with richness_tier wired
2. Evidence: `reports/HC-TIER-01/evidence.md` with grep confirming new call sites

## Acceptance checks

1. [ ] `grep "richness_tier=richness_tier" src/launcher/workers/evaluate/worker.py` returns 2 hits (density + structure)
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -q` — all pass
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q` — no regressions

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: evaluate unit tests PASS
- [ ] Evidence captured: reports/HC-TIER-01/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
```

**Expected results**:
- All existing evaluate tests pass
- `_TIER_DENSITY["C"]` thresholds (50, 10) are now reachable for Tier C repos

## Integration boundary proven

**Upstream**: `_load_understand_checkpoint(context)` provides `richness_tier.tier` string
**Downstream**: `check_density()` and `check_structure()` consume `richness_tier` parameter
**Contract**: `richness_tier` is `"A"` | `"B"` | `"C"`; both checks use `dict.get(tier, default)` for safe fallback
