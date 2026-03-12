---
id: TC-3864
title: "Wire golden block-spec compliance check into evaluate worker"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [golden, evaluate, structure, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3864_golden_compliance_evaluate_wiring.md
  - src/launcher/workers/evaluate/checks/structure.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/workers/evaluate/worker.py
  - tests/unit/workers/test_structure_check.py
evidence_required:
  - reports/TC-3864/evidence.md
---

# Taskcard TC-3864 — Wire golden block-spec compliance check into evaluate worker

## Objective

`check_block_spec_compliance()` exists in structure.py but is never called during evaluation
because it requires a PageIR object while the evaluate worker uses raw markdown strings.
This TC adds a markdown-based counterpart and wires it into `_run_deterministic_checks` so
golden structural contracts actually enforce content quality grades.

## Required spec references

- `specs/` (content quality spec — golden block spec enforcement)
- Plan: `twinkly-beaming-wren.md` (G004 gate requirement)

## Scope

### In scope
- Add `check_golden_spec_from_markdown(content, slug, page_role, golden_dir)` to structure.py
- Export from checks/__init__.py
- Add `golden_dir: Path | None` param to `_run_deterministic_checks` in worker.py
- Pass golden_dir from worker config in `_evaluate_page_llm` closure
- Add tests for the new function

### Out of scope
- Registering a gate in gates_registry.yaml (the check runs via evaluate worker directly)
- Modifying check_block_spec_compliance (IR-based version stays unchanged)
- Heal execution wiring (separate TC)

## Inputs

- `src/launcher/workers/evaluate/checks/structure.py` (add new function)
- `src/launcher/workers/evaluate/worker.py` (wire call)
- `configs/pipeline.yaml` (golden.enabled, golden.dir config)

## Outputs

- Golden block-spec findings (check="structure", severity high/medium) produced during evaluate
- Failing pages get D grade if any section is missing a required code block
- New tests pass

## Allowed paths

- plans/taskcards/TC-3864_golden_compliance_evaluate_wiring.md
- src/launcher/workers/evaluate/checks/structure.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/workers/evaluate/worker.py
- tests/unit/workers/test_structure_check.py

### Allowed paths rationale
- structure.py: new function added here
- __init__.py: export new function
- worker.py: wire call into _run_deterministic_checks
- test_structure_check.py: add tests for the new function

## Implementation steps

### Step 1: Add check_golden_spec_from_markdown to structure.py

Add after `check_block_spec_compliance()`:

```python
def check_golden_spec_from_markdown(
    content: str,
    slug: str,
    page_role: str,
    golden_dir: object,  # Path | None
    variant: str = "standard",
) -> list[Finding]:
    """Check markdown content against GoldenBlockSpec requirements.

    Markdown-native version of check_block_spec_compliance for use in the
    evaluate worker which operates on raw markdown, not PageIR objects.

    Returns findings for missing code blocks (high) and under-length
    pages (medium). Returns [] if golden_dir is None/missing or any
    exception occurs.
    """
    if golden_dir is None:
        return []
    try:
        from pathlib import Path as _Path
        gdir = _Path(golden_dir) if not isinstance(golden_dir, _Path) else golden_dir
        if not gdir.exists():
            return []
        from launcher.shared.golden_loader import GoldenIndex
        index = GoldenIndex.load(gdir)
        golden_page = index.get(page_role, variant) or index.get(page_role, "minimal")
        if golden_page is None:
            return []
    except Exception:
        return []

    findings: list[Finding] = []

    # Strip frontmatter for body analysis
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)

    # Determine if ANY golden section requires a code block
    needs_code = False
    total_min_words = 0
    for section in golden_page.sections:
        spec = index.get_spec(page_role, golden_page.variant, section.heading)
        if spec is None:
            continue
        rbt = getattr(spec, "required_block_types", []) or []
        if "code" in rbt:
            needs_code = True
        mw = getattr(spec, "min_words", 0) or 0
        total_min_words += mw

    # Check code block presence
    has_code = bool(re.search(r"```", body))
    if needs_code and not has_code:
        findings.append(Finding(
            check="structure",
            message=(
                f"Page role '{page_role}' requires a code block per golden spec"
                " but none found in body."
            ),
            severity="high",
            location=slug,
        ))

    # Check overall word count vs golden minimum
    if total_min_words > 0:
        prose = re.sub(r"```[^\n]*\n.*?```", "", body, flags=re.DOTALL)
        word_count = len(prose.split())
        if word_count < total_min_words:
            findings.append(Finding(
                check="structure",
                message=(
                    f"Page body has {word_count} prose words; "
                    f"golden spec requires ≥{total_min_words}."
                ),
                severity="medium",
                location=slug,
            ))

    return findings
```

### Step 2: Export from checks/__init__.py

Add to imports and __all__:
```python
from .structure import check_structure, check_golden_spec_from_markdown
```

### Step 3: Wire into _run_deterministic_checks in worker.py

Extend signature:
```python
def _run_deterministic_checks(
    content: str, slug: str, *, page_role: str = "", product_name: str = "",
    canonical_import: str = "", golden_dir: "Path | None" = None,
) -> list[Finding]:
```

Add call after existing checks:
```python
from launcher.workers.evaluate.checks import check_golden_spec_from_markdown
findings.extend(check_golden_spec_from_markdown(content, slug, page_role, golden_dir))
```

### Step 4: Pass golden_dir in worker's _evaluate_page_llm closure

In `run()`, resolve golden_dir once before the closure:
```python
_golden_cfg = getattr(context.config, "golden", {}) or {}
_golden_dir = None
if _golden_cfg.get("enabled"):
    from pathlib import Path as _Path
    _golden_dir = _Path(_golden_cfg.get("dir", "golden/"))
```

Pass it to `_run_deterministic_checks`:
```python
findings = _run_deterministic_checks(
    content, gen_page.slug,
    page_role=gen_page.page_role,
    product_name=product_name,
    canonical_import=context.config.canonical_import or "",
    golden_dir=_golden_dir,
)
```

### Step 5: Add tests

In `tests/unit/workers/test_structure_check.py`, add:
- `test_golden_spec_none_dir_returns_empty`
- `test_golden_spec_missing_code_block_high_severity`
- `test_golden_spec_code_block_present_no_finding`
- `test_golden_spec_unknown_role_no_finding`
- `test_golden_spec_word_count_below_minimum`

## Failure modes

### Failure mode 1: GoldenIndex.load fails on corrupt golden file
**Detection**: Function returns [] (try-except) — no crash
**Resolution**: Fix the corrupt golden file; graceful degradation is correct
**Gate**: Check that no exception propagates from check_golden_spec_from_markdown

### Failure mode 2: Config golden.enabled is True but dir doesn't resolve
**Detection**: gdir.exists() returns False → returns []
**Resolution**: Verify golden.dir in pipeline.yaml points to existing directory
**Gate**: Test `test_golden_spec_missing_code_block_high_severity` uses actual golden dir

### Failure mode 3: page_role has no golden entry
**Detection**: `index.get(page_role, variant)` returns None → returns []
**Resolution**: Add golden file for this page_role, or accept no enforcement for unknown roles
**Gate**: `test_golden_spec_unknown_role_no_finding` asserts [] returned

## Task-specific review checklist

1. [ ] check_golden_spec_from_markdown returns Finding objects (not dicts)
2. [ ] check_golden_spec_from_markdown never raises — all errors caught and return []
3. [ ] _run_deterministic_checks signature change is backward-compatible (golden_dir defaults None)
4. [ ] Worker passes golden_dir=None when golden.enabled is False
5. [ ] Baseline test count does not drop after this change
6. [ ] New tests cover: None dir, missing dir, unknown role, code found, code missing, word count
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/workers/evaluate/checks/structure.py` — new function added
2. `src/launcher/workers/evaluate/worker.py` — golden_dir wired
3. `tests/unit/workers/test_structure_check.py` — new tests passing

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_structure_check.py -v` — all pass
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no` — count >= 2878
3. [ ] A page missing a required code block (for a role with golden spec) gets grade D or lower

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: structure check wired PASS
- [ ] Evidence captured: reports/TC-3864/evidence.md
- [ ] Doc freshness: clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_structure_check.py tests/unit/workers/test_evaluate.py -v
```

**Expected results**:
- All new golden spec tests pass
- No existing tests broken

## Integration boundary proven

**Upstream**: pipeline.yaml golden.enabled + golden.dir config
**Downstream**: grade_page() assigns D for high-severity structure findings
**Contract**: check_golden_spec_from_markdown returns list[Finding] with check="structure"
