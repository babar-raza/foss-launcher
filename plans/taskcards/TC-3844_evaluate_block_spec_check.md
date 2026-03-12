---
id: TC-3844
title: "Evaluate Block Spec Compliance Check (G004)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [golden, evaluate, structure, block-spec]
depends_on: [TC-3835, TC-3833]
allowed_paths:
  - plans/taskcards/TC-3844_evaluate_block_spec_check.md
  - src/launcher/workers/evaluate/checks/structure.py
  - tests/unit/workers/test_structure_check.py
evidence_required:
  - reports/TC-3844/evidence.md
---

# Taskcard TC-3844 — Evaluate Block Spec Compliance Check (G004)

## Objective

Add `check_block_spec_compliance()` to `evaluate/checks/structure.py` that
loads GoldenIndex and emits findings when generated page sections don't
meet the block spec requirements from golden exemplars.

## Required spec references

- `specs/golden.md` (GoldenBlockSpec contract)
- `specs/evaluate.md` (structure check interface)

## Scope

### In scope
- Add `check_block_spec_compliance(page_ir, page_role, golden_dir) -> list[Finding]`
  to `structure.py` (AFTER existing functions added by TC-3835)
- Load GoldenIndex once per call; for each section call `get_spec()`
- Emit `high` severity finding when a code block is required but absent
- Emit `medium` severity finding when section word count below `min_words`

### Out of scope
- Wiring into evaluate worker (already done via `_run_deterministic_checks`
  registration in `checks/__init__.py` — see implementation step)
- Golden index caching across multiple pages — caller should load once

## Inputs

- `src/launcher/workers/evaluate/checks/structure.py` (augmented by TC-3835)
- `src/launcher/shared/golden_loader.py` (GoldenIndex, GoldenBlockSpec from TC-3833)
- `page_ir` (PageIR model with sections)

## Outputs

- `check_block_spec_compliance()` function in structure.py
- Findings for code block gaps and word count violations

## Allowed paths

- plans/taskcards/TC-3844_evaluate_block_spec_check.md
- src/launcher/workers/evaluate/checks/structure.py
- tests/unit/workers/test_structure_check.py

### Allowed paths rationale

Only structure.py extended (TC-3835 Done first); new test file.

## Implementation steps

### Step 1: Add check_block_spec_compliance() to structure.py

```python
def check_block_spec_compliance(
    page_ir: Any,
    page_role: str,
    golden_dir: Path | None,
    variant: str = "standard",
) -> list[Any]:  # list[Finding]
    """Check page sections against GoldenBlockSpec requirements.

    Returns findings for missing code blocks (high) and
    under-length sections (medium).
    """
    if golden_dir is None or not golden_dir.exists():
        return []
    try:
        from launcher.shared.golden_loader import GoldenIndex
        index = GoldenIndex.load(golden_dir)
    except Exception:
        return []

    findings = []
    sections = getattr(page_ir, "sections", []) or []
    for section in sections:
        heading = getattr(section, "heading", "") or ""
        spec = index.get_spec(page_role, variant, heading)
        if spec is None:
            continue

        # Check code block requirement
        if spec.requires_code:
            has_code = any(
                getattr(block, "type", "") in ("code", "fence")
                for block in (getattr(section, "blocks", []) or [])
            )
            if not has_code:
                findings.append({
                    "check": "structure",
                    "message": (
                        f"Section '{heading}' requires a code block per golden spec"
                        " but none found."
                    ),
                    "severity": "high",
                    "location": heading,
                })

        # Check word count requirement
        word_count = len((getattr(section, "body", "") or "").split())
        if word_count < spec.min_words and spec.min_words > 0:
            findings.append({
                "check": "structure",
                "message": (
                    f"Section '{heading}' has {word_count} words "
                    f"(golden spec requires ≥{spec.min_words})."
                ),
                "severity": "medium",
                "location": heading,
            })

    return findings
```

### Step 2: Register in checks/__init__.py

Read `src/launcher/workers/evaluate/checks/__init__.py` and add
`check_block_spec_compliance` to the exported check functions
(only if the registration mechanism exists there; otherwise
wire into evaluate worker directly).

### Step 3: Add tests

`tests/unit/workers/test_structure_check.py`:
- Missing code block → high severity finding
- Sufficient words → no finding
- Below min_words → medium severity finding
- golden_dir=None → empty list (no crash)
- No golden spec for section → no finding
- Uses mock GoldenBlockSpec (requires_code=True, min_words=100)

## Failure modes

### Failure mode 1: GoldenIndex.load() raises exception

**Detection**: Exception during `GoldenIndex.load(golden_dir)`
**Resolution**: Wrapped in `try/except Exception: return []` — graceful degradation
**Gate**: Unit test with corrupted golden_dir

### Failure mode 2: section.blocks has no 'type' attribute

**Detection**: `AttributeError` when checking `block.type`
**Resolution**: Use `getattr(block, "type", "")` — defaults to empty string
**Gate**: Unit test with dict-style block representation

### Failure mode 3: check_block_spec_compliance not wired into evaluate worker

**Detection**: No block spec findings appear in evaluation report
**Resolution**: Verify registration in `checks/__init__.py`; if not registered,
add to `_run_deterministic_checks()` in `evaluate/worker.py` (must be in Tier 1 scope)
**Gate**: Integration test: evaluate with golden page → block spec findings present

## Task-specific review checklist

1. [ ] `check_block_spec_compliance()` function added AFTER TC-3835 heading checks
2. [ ] Missing code block → `severity="high"` finding with location=section heading
3. [ ] Below min_words → `severity="medium"` finding
4. [ ] golden_dir=None → returns [] immediately without any index load
5. [ ] No matching spec → no finding (correct skip behavior)
6. [ ] New tests cover missing code, below min_words, missing golden, no spec cases

## Deliverables

1. `src/launcher/workers/evaluate/checks/structure.py` — `check_block_spec_compliance()` appended
2. `tests/unit/workers/test_structure_check.py` — 6+ test cases

## Acceptance checks

1. [ ] `pytest tests/unit/workers/test_structure_check.py -v` — all PASS
2. [ ] Missing code block produces `severity="high"` finding
3. [ ] `pytest tests/ -x -q` — 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: code block and word count checks emit correct findings
- [ ] Evidence file: `reports/TC-3844/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_structure_check.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All structure check tests pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: GoldenIndex from TC-3833; PageIR from generate worker
**Downstream**: Evaluate worker aggregates findings from check_block_spec_compliance
**Contract**: Returns `list[dict]` (Finding-compatible); each has check, message, severity, location
