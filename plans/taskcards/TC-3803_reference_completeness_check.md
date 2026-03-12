---
id: TC-3803
title: "Reference Completeness Check"
status: Done
priority: Normal
owner: agent
updated: "2026-03-07"
tags: [evaluate, gate, api_reference]
depends_on: [TC-3802]
allowed_paths:
  - plans/taskcards/TC-3803_reference_completeness_check.md
  - src/launcher/workers/evaluate/checks/reference_completeness.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/workers/evaluate/worker.py
evidence_required:
  - reports/TC-3803/evidence.md
---

# Taskcard TC-3803 — Reference Completeness Check

## Objective

Add a deterministic evaluation check that flags reference pages missing markdown tables, containing raw JSON arrays, using HTML anchor tags, or lacking code fences. This provides ongoing quality enforcement for API reference pages.

## Required spec references

- `specs/content_model_pageir.md` (Section: table block type — pipe-delimited markdown)
- `specs/worker_evaluate.md` (Section: Phase A deterministic checks)

## Scope

### In scope
- Create `check_reference_completeness()` function
- Wire into `_run_deterministic_checks()` in evaluate worker
- Export from `checks/__init__.py`

### Out of scope
- Prompt changes (TC-3801)
- Post-LLM validation (TC-3802)
- Registry-based gate runner path (existing `gates_registry.yaml` entry)

## Inputs

- Rendered markdown content of each page
- Page slug and page_role metadata

## Outputs

- `src/launcher/workers/evaluate/checks/reference_completeness.py` — new file
- Modified `checks/__init__.py` with new import
- Modified `worker.py` with new check call

## Allowed paths

- plans/taskcards/TC-3803_reference_completeness_check.md
- src/launcher/workers/evaluate/checks/reference_completeness.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/workers/evaluate/worker.py

### Allowed paths rationale
- `reference_completeness.py`: New check module
- `__init__.py`: Must export the new check function
- `worker.py`: Must call the new check in `_run_deterministic_checks()`

## Implementation steps

### Step 1: Create reference_completeness.py

```python
"""Reference completeness check for API reference pages."""
from __future__ import annotations

import re
from typing import Any

from launcher.models.evaluation import Finding


_REFERENCE_ROLES: set[str] = {"api_reference", "reference_object_page"}


def check_reference_completeness(
    content: str, slug: str, *, page_role: str = "",
) -> list[Finding]:
    """Check that reference pages have required structural elements."""
    if page_role not in _REFERENCE_ROLES:
        return []

    findings: list[Finding] = []
    # Split off frontmatter
    parts = content.split("---", 2)
    body = parts[2] if len(parts) >= 3 else content

    # Check 1: At least one markdown table
    if not re.search(r"^\|.+\|$", body, re.MULTILINE):
        findings.append(Finding(
            check="reference_completeness",
            slug=slug,
            severity="high",
            message="Reference page has no markdown tables",
        ))

    # Check 2: At least one code fence
    if "```" not in body:
        findings.append(Finding(
            check="reference_completeness",
            slug=slug,
            severity="medium",
            message="Reference page has no code examples",
        ))

    # Check 3: No raw JSON arrays (malformed table content)
    if re.search(r"\[\s*\{['\"]", body):
        findings.append(Finding(
            check="reference_completeness",
            slug=slug,
            severity="high",
            message="Reference page contains raw JSON array (should be markdown table)",
        ))

    # Check 4: No HTML anchor tags
    if re.search(r"<a\s+href=", body, re.IGNORECASE):
        findings.append(Finding(
            check="reference_completeness",
            slug=slug,
            severity="medium",
            message="Reference page contains HTML anchor tags (should be markdown links)",
        ))

    # Check 5: Table has sufficient rows (at least 2 data rows)
    table_match = re.findall(r"^\|.+\|$", body, re.MULTILINE)
    if table_match:
        # Exclude header and separator rows
        data_rows = [r for r in table_match if not re.match(r"^\|\s*-+", r)]
        if len(data_rows) < 3:  # header + at least 2 data rows
            findings.append(Finding(
                check="reference_completeness",
                slug=slug,
                severity="low",
                message=f"Reference page tables have only {len(data_rows)} rows (expected >= 3)",
            ))

    return findings
```

### Step 2: Update checks/__init__.py

Add import and `__all__` entry for `check_reference_completeness`.

### Step 3: Wire into worker.py

In `_run_deterministic_checks()` (line 278), add:

```python
findings.extend(check_reference_completeness(content, slug, page_role=page_role))
```

## Failure modes

### Failure mode 1: False positives on non-reference pages

**Detection**: Check fires for blog/docs pages
**Resolution**: Early return if `page_role not in _REFERENCE_ROLES` — first line of the function
**Gate**: N/A

### Failure mode 2: JSON array regex matches legitimate code blocks

**Detection**: Code blocks containing JSON arrays trigger check 3
**Resolution**: The regex `\[\s*\{['"]` in the body will match code blocks too. Strip code fences before checking. Add fence-aware matching.
**Gate**: check_reference_completeness

### Failure mode 3: Finding model mismatch

**Detection**: Import error or field mismatch with Finding model
**Resolution**: Check the Finding model definition in `models/evaluation.py` for exact field names before implementing.
**Gate**: CI test suite

## Task-specific review checklist

1. [ ] Check only runs for `_REFERENCE_ROLES` page roles
2. [ ] JSON array detection regex is tested with actual malformed output
3. [ ] Frontmatter is properly stripped before body checks
4. [ ] Code fences are excluded from JSON array detection
5. [ ] Severity levels match existing check conventions
6. [ ] Finding constructor matches the model definition exactly

## Deliverables

1. New `src/launcher/workers/evaluate/checks/reference_completeness.py`
2. Modified `src/launcher/workers/evaluate/checks/__init__.py`
3. Modified `src/launcher/workers/evaluate/worker.py`
4. Evidence bundle at `reports/TC-3803/evidence.md`

## Acceptance checks

1. [ ] `check_reference_completeness()` returns empty list for non-reference page_roles
2. [ ] Detects missing tables with severity "high"
3. [ ] Detects raw JSON arrays with severity "high"
4. [ ] Detects HTML anchor tags with severity "medium"
5. [ ] All existing tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: check function PASS
- [ ] Evidence captured: reports/TC-3803/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
```

**Expected results**:
- All evaluate tests pass
- Reference completeness check produces findings for pages with known issues

## Integration boundary proven

**Upstream**: Generate worker produces rendered markdown content
**Downstream**: Evaluation report includes reference completeness findings in severity aggregation
**Contract**: `Finding(check="reference_completeness", slug=..., severity=..., message=...)` — standard Finding model
