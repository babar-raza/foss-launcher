---
id: TC-HYBRID-06
title: "Contradiction + Format Truth Gates — verify format claims against FormatRecord matrix"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-10"
tags: [evaluate, gate, contradiction, format-truth, hallucination]
depends_on: [TC-HYBRID-03, TC-HYBRID-05]
allowed_paths:
  - plans/taskcards/TC-HYBRID-06_contradiction-format-truth.md
  - src/launcher/workers/evaluate/checks/contradiction.py
  - src/launcher/workers/evaluate/checks/format_truth.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/workers/evaluate/worker.py
  - tests/unit/workers/test_evaluate.py
  - reports/TC-HYBRID-06/evidence.md
  - reports/agents/B/TC-HYBRID-06/self_review.md
  - reports/agents/B/TC-HYBRID-06/plan.md
evidence_required:
  - reports/TC-HYBRID-06/evidence.md
---

# Taskcard TC-HYBRID-06 — Contradiction + Format Truth Gates

## Objective

Add two new gates to catch format capability hallucinations:
1. `check_contradiction(content, slug, *, api_surface=None)` — fires when generated text claims a
   format "can be exported/imported" but `FormatRecord.can_export/can_import == False`
2. `check_format_truth(content, slug, *, api_surface=None)` — fires when generated text references
   a format name that exists in the format_matrix but with wrong capabilities (e.g. "OBJ export
   supported" when `can_export=False`)

Both gates skip gracefully when `api_surface` is None or `api_surface.format_matrix` is empty.

## Required spec references

- `specs/worker_evaluate.md` (Phase A gates, finding severity)
- `specs/product_model.md` (FormatRecord — TC-HYBRID-03 additions)

## Scope

### In scope
- New `src/launcher/workers/evaluate/checks/contradiction.py` — `check_contradiction()`
- New `src/launcher/workers/evaluate/checks/format_truth.py` — `check_format_truth()`
- Export both from `checks/__init__.py`
- Add calls to both gates in `_run_deterministic_checks()` in `worker.py`

### Out of scope
- API identifier verification (TC-HYBRID-05 — already done)
- Cross-page consistency review (TC-HYBRID-08)

## Inputs

- `ApiSurface.format_matrix: list[FormatRecord]` (TC-HYBRID-03)
- Generated markdown content
- `api_surface` param already in `_run_deterministic_checks()` (TC-HYBRID-05 added it)

## Outputs

- `check_contradiction(content, slug, *, api_surface=None)` — finding when format capability contradicted
- `check_format_truth(content, slug, *, api_surface=None)` — finding when format name claimed but not in matrix
- Both exported and called in evaluation pipeline

## Allowed paths

- plans/taskcards/TC-HYBRID-06_contradiction-format-truth.md
- src/launcher/workers/evaluate/checks/contradiction.py
- src/launcher/workers/evaluate/checks/format_truth.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/workers/evaluate/worker.py
- tests/unit/workers/test_evaluate.py
- reports/TC-HYBRID-06/evidence.md
- reports/agents/B/TC-HYBRID-06/self_review.md
- reports/agents/B/TC-HYBRID-06/plan.md

### Allowed paths rationale
- Two new gate files, __init__.py export, worker.py wiring, tests, reports

## Implementation steps

### Step 1: Read key files first

Read before writing:
- `src/launcher/workers/evaluate/checks/code.py` (gate module structure reference)
- `src/launcher/workers/evaluate/worker.py` lines 454-485 — `_run_deterministic_checks()` current state after TC-HYBRID-05
- `src/launcher/workers/evaluate/checks/__init__.py` — current exports
- `src/launcher/models/product.py` — `FormatRecord` model (from TC-HYBRID-03)

### Step 2: Create contradiction.py

Create `src/launcher/workers/evaluate/checks/contradiction.py`:

```python
"""Format contradiction gate (TC-HYBRID-06).

Scans generated text for format capability claims and cross-references
against the FormatRecord matrix from ApiSurface.
"""
from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.product import ApiSurface

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)

# Patterns that claim export capability
_EXPORT_CLAIM_PATTERNS = [
    re.compile(r'\b(?:can|supports?|allows?|enables?)\s+(?:export(?:ing)?|sav(?:e|ing))\s+(?:to\s+)?(\w+)', re.IGNORECASE),
    re.compile(r'\bexport(?:ing)?\s+(?:to\s+)?(\w+)\s+(?:is\s+)?supported', re.IGNORECASE),
    re.compile(r'(\w+)\s+(?:format\s+)?(?:can\s+be\s+)?export(?:ed)?', re.IGNORECASE),
]

# Patterns that claim import capability
_IMPORT_CLAIM_PATTERNS = [
    re.compile(r'\b(?:can|supports?|allows?|enables?)\s+(?:import(?:ing)?|load(?:ing)?|read(?:ing)?)\s+(?:from\s+)?(\w+)', re.IGNORECASE),
    re.compile(r'\bimport(?:ing)?\s+(?:from\s+)?(\w+)\s+(?:is\s+)?supported', re.IGNORECASE),
    re.compile(r'(\w+)\s+(?:format\s+)?(?:can\s+be\s+)?(?:import|load|read)(?:ed)?', re.IGNORECASE),
]


def check_contradiction(
    content: str,
    slug: str,
    *,
    api_surface: "ApiSurface | None" = None,
) -> "list[Finding]":
    """Check for format capability claims that contradict the FormatRecord matrix.

    For each format in api_surface.format_matrix, scans the generated content
    for explicit capability claims and flags contradictions.

    Args:
        content: Generated markdown content.
        slug: Page slug for Finding location.
        api_surface: ApiSurface with format_matrix from TC-HYBRID-03.

    Returns:
        List of Findings. MEDIUM severity when text contradicts format matrix.
        Returns [] when api_surface is None or format_matrix is empty.
    """
    if api_surface is None:
        return []

    format_matrix = getattr(api_surface, "format_matrix", [])
    if not format_matrix:
        return []

    # Build format name → FormatRecord lookup
    fmt_lookup: dict[str, object] = {}
    for fr in format_matrix:
        fmt_lookup[fr.name.upper()] = fr
        # Also add extension without dot: "OBJ", "FBX"
        if fr.extension:
            ext_upper = fr.extension.lstrip(".").upper()
            fmt_lookup[ext_upper] = fr

    findings: list[Finding] = []

    # Check each paragraph line for format claims
    for line in content.split("\n"):
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#"):
            continue
        # Skip code block lines
        if line_stripped.startswith("```") or line_stripped.startswith("    "):
            continue

        line_upper = line.upper()

        for fmt_name, fmt_record in fmt_lookup.items():
            if fmt_name not in line_upper:
                continue

            # Check for export contradiction
            if not fmt_record.can_export:
                for pat in _EXPORT_CLAIM_PATTERNS:
                    m = pat.search(line)
                    if m:
                        captured = m.group(1).upper() if m.lastindex else ""
                        if fmt_name in captured or fmt_name in line_upper:
                            findings.append(Finding(
                                check="format_contradiction_export",
                                message=(
                                    f"Content claims {fmt_name} can be exported, "
                                    f"but FormatRecord.can_export=False"
                                ),
                                severity="medium",
                                location=slug,
                            ))

            # Check for import contradiction
            if not fmt_record.can_import:
                for pat in _IMPORT_CLAIM_PATTERNS:
                    m = pat.search(line)
                    if m:
                        captured = m.group(1).upper() if m.lastindex else ""
                        if fmt_name in captured or fmt_name in line_upper:
                            findings.append(Finding(
                                check="format_contradiction_import",
                                message=(
                                    f"Content claims {fmt_name} can be imported/loaded, "
                                    f"but FormatRecord.can_import=False"
                                ),
                                severity="medium",
                                location=slug,
                            ))

    # Deduplicate
    seen: set[str] = set()
    unique: list[Finding] = []
    for f in findings:
        key = f"{f.check}:{f.message}"
        if key not in seen:
            seen.add(key)
            unique.append(f)

    if unique:
        logger.info("format_contradiction: slug=%s findings=%d", slug, len(unique))

    return unique
```

### Step 3: Create format_truth.py

Create `src/launcher/workers/evaluate/checks/format_truth.py`:

```python
"""Format truth gate (TC-HYBRID-06).

Verifies that format names mentioned in generated content are present in the
FormatRecord matrix. Flags formats that are mentioned but have zero evidence
(test_count=0 and not from README).
"""
from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.product import ApiSurface

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)

# Pattern to detect format-like words in prose (all-caps short words, or
# known format names in any case)
_FORMAT_MENTION_RE = re.compile(
    r'\b(OBJ|FBX|GLTF|GLB|STL|DAE|USD|USDZ|DXF|PLY|'
    r'PDF|DOCX|XLSX|PPTX|HTML|RTF|CSV|ODS|PNG|JPEG|JPG|BMP|TIFF|SVG|WEBP|'
    r'ONE|ONETOC2|IGES|STEP|IFC|DWG)\b',
    re.IGNORECASE,
)


def check_format_truth(
    content: str,
    slug: str,
    *,
    api_surface: "ApiSurface | None" = None,
) -> "list[Finding]":
    """Check that format names mentioned in content are supported by extracted evidence.

    Only fires when a format is prominently mentioned (≥2 times in prose, outside
    code blocks) and has test_count=0 in the format matrix AND is NOT in readme_caps
    (i.e., zero evidence). The intent is to catch formats claimed without any basis.

    Args:
        content: Generated markdown content.
        slug: Page slug for Finding location.
        api_surface: ApiSurface with format_matrix from TC-HYBRID-03.

    Returns:
        List of LOW-severity Findings for mentioned-but-unsupported formats.
        Returns [] when api_surface is None or format_matrix empty.
    """
    if api_surface is None:
        return []

    format_matrix = getattr(api_surface, "format_matrix", [])
    if not format_matrix:
        return []

    # Build set of formats with any evidence
    known_formats: set[str] = set()
    zero_evidence_formats: set[str] = set()
    for fr in format_matrix:
        known_formats.add(fr.name.upper())
        if fr.extension:
            known_formats.add(fr.extension.lstrip(".").upper())
        if fr.test_count == 0 and not fr.can_import and not fr.can_export:
            zero_evidence_formats.add(fr.name.upper())

    # Count format mentions in prose (outside code blocks)
    prose_lines: list[str] = []
    in_code_block = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block and not stripped.startswith("    "):
            prose_lines.append(stripped)

    prose = "\n".join(prose_lines)
    format_mention_counts: dict[str, int] = {}
    for m in _FORMAT_MENTION_RE.finditer(prose):
        fmt = m.group(1).upper()
        format_mention_counts[fmt] = format_mention_counts.get(fmt, 0) + 1

    findings: list[Finding] = []
    for fmt, count in format_mention_counts.items():
        if count < 2:
            continue  # Only flag prominently mentioned formats
        if fmt not in zero_evidence_formats:
            continue  # Format has evidence — OK
        findings.append(Finding(
            check="format_unsupported_claim",
            message=(
                f"Format {fmt} mentioned {count} times in prose "
                f"but has zero test evidence in extracted format matrix"
            ),
            severity="low",
            location=slug,
        ))

    if findings:
        logger.info("format_truth: slug=%s low_evidence_formats=%d", slug, len(findings))

    return findings
```

### Step 4: Update checks/__init__.py

In `src/launcher/workers/evaluate/checks/__init__.py`, add:
```python
from .contradiction import check_contradiction  # TC-HYBRID-06
from .format_truth import check_format_truth    # TC-HYBRID-06
```

And add both to `__all__`.

### Step 5: Update _run_deterministic_checks in worker.py

In `src/launcher/workers/evaluate/worker.py`:

1. Add imports at the top (in the existing `from launcher.workers.evaluate.checks import (...)` block):
```python
    check_contradiction,   # TC-HYBRID-06
    check_format_truth,    # TC-HYBRID-06
```

2. Add calls inside `_run_deterministic_checks()` at the end (before `return findings`):
```python
    # TC-HYBRID-06: Format contradiction + truth checks (skip when no format_matrix)
    findings.extend(check_contradiction(content, slug, api_surface=api_surface))
    findings.extend(check_format_truth(content, slug, api_surface=api_surface))
```

**IMPORTANT**: TC-HYBRID-05 already added `api_surface: Any | None = None` to `_run_deterministic_checks()`. DO NOT add it again. Just add the gate calls.

### Step 6: Write unit tests

In `tests/unit/workers/test_evaluate.py`, add `TestContradictionGate` and `TestFormatTruthGate` classes:

```python
class TestContradictionGate:
    def _make_surface_with_formats(self, can_import=True, can_export=True):
        from launcher.models.product import ApiSurface, FormatRecord
        return ApiSurface(
            public_classes=[], import_allowlist=[], confidence="high",
            format_matrix=[
                FormatRecord(name="OBJ", can_import=can_import, can_export=can_export, test_count=1),
            ]
        )

    def test_skip_when_no_api_surface(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        assert check_contradiction("OBJ can be exported", "slug") == []

    def test_skip_when_format_matrix_empty(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        from launcher.models.product import ApiSurface
        surface = ApiSurface(public_classes=[], import_allowlist=[], confidence="high")
        assert check_contradiction("OBJ can be exported", "slug", api_surface=surface) == []

    def test_export_contradiction_fires(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        surface = self._make_surface_with_formats(can_export=False)
        content = "OBJ format can be exported to files."
        findings = check_contradiction(content, "slug", api_surface=surface)
        assert any(f.check == "format_contradiction_export" for f in findings)

    def test_no_contradiction_when_capability_true(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        surface = self._make_surface_with_formats(can_export=True)
        content = "OBJ format can be exported to files."
        findings = check_contradiction(content, "slug", api_surface=surface)
        export_findings = [f for f in findings if f.check == "format_contradiction_export"]
        assert export_findings == []


class TestFormatTruthGate:
    def test_skip_when_no_api_surface(self):
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        assert check_format_truth("OBJ is supported", "slug") == []

    def test_skip_when_format_matrix_empty(self):
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface
        surface = ApiSurface(public_classes=[], import_allowlist=[], confidence="high")
        assert check_format_truth("OBJ is supported", "slug", api_surface=surface) == []

    def test_zero_evidence_format_mentioned_prominently_fires(self):
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface, FormatRecord
        # Format with zero evidence
        surface = ApiSurface(
            public_classes=[], import_allowlist=[], confidence="high",
            format_matrix=[
                FormatRecord(name="OBJ", can_import=False, can_export=False, test_count=0),
            ]
        )
        content = "OBJ format is supported. You can use OBJ files with this library."
        findings = check_format_truth(content, "slug", api_surface=surface)
        assert any(f.check == "format_unsupported_claim" for f in findings)

    def test_format_with_evidence_does_not_fire(self):
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface, FormatRecord
        surface = ApiSurface(
            public_classes=[], import_allowlist=[], confidence="high",
            format_matrix=[
                FormatRecord(name="OBJ", can_import=True, can_export=True, test_count=5),
            ]
        )
        content = "OBJ format is supported. You can use OBJ files with this library."
        findings = check_format_truth(content, "slug", api_surface=surface)
        assert findings == []
```

### Step 7: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v -k "Contradiction or FormatTruth" --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

All existing tests must pass. New tests must pass.

### Step 8: Write evidence and self-review

Create `reports/TC-HYBRID-06/evidence.md` and `reports/agents/B/TC-HYBRID-06/self_review.md`.
Mark taskcard Done.

## Failure modes

### Failure mode 1: _run_deterministic_checks already has api_surface param (TC-HYBRID-05)

**Detection**: `api_surface` already in the function signature — DO NOT add again
**Resolution**: Read `worker.py` first. If `api_surface` is already a param, skip the signature change — just add gate calls at the end.
**Gate**: Check existing signature before writing any changes to worker.py

### Failure mode 2: Format contradiction regex too broad — false positives

**Detection**: Common English words like "export" match unexpectedly
**Resolution**: Patterns require format name AND capability keyword on same line. Test with prose that mentions export without format names — should not fire.
**Gate**: `test_no_contradiction_when_capability_true` verifies precision

### Failure mode 3: contradiction.py and format_truth.py both import Finding from same path

**Detection**: ImportError
**Resolution**: `from launcher.models.evaluation import Finding` — standard import, no circular dependency issue.
**Gate**: Import test at module level

## Task-specific review checklist

1. [ ] `check_contradiction()` implemented in `contradiction.py` — skips when no format_matrix
2. [ ] `check_format_truth()` implemented in `format_truth.py` — skips when no format_matrix
3. [ ] Both exported from `checks/__init__.py`
4. [ ] Both called in `_run_deterministic_checks()` — NOT adding duplicate `api_surface` param
5. [ ] Export contradiction fires MEDIUM when `can_export=False` but text claims export
6. [ ] Format truth fires LOW when format mentioned ≥2 times with zero test evidence
7. [ ] Both gate tests: 8 tests total pass
8. [ ] Docstrings complete on both functions
9. [ ] No circular imports (TYPE_CHECKING guard for ApiSurface)
10. [ ] Full suite passes with no new failures

## Deliverables

1. `src/launcher/workers/evaluate/checks/contradiction.py` — new
2. `src/launcher/workers/evaluate/checks/format_truth.py` — new
3. `src/launcher/workers/evaluate/checks/__init__.py` — exports
4. `src/launcher/workers/evaluate/worker.py` — gate calls added
5. `tests/unit/workers/test_evaluate.py` — 8 new tests
6. `reports/TC-HYBRID-06/evidence.md`
7. `reports/agents/B/TC-HYBRID-06/self_review.md`

## Acceptance checks

1. [ ] `check_contradiction` returns MEDIUM finding when `can_export=False` and text claims export
2. [ ] `check_format_truth` returns LOW finding for 2+ prose mentions of zero-evidence format
3. [ ] Both return `[]` when `api_surface=None` or `format_matrix=[]`
4. [ ] Gate calls added to `_run_deterministic_checks()` (no duplicate api_surface param)
5. [ ] All 8 new tests pass
6. [ ] Full suite passes: 3354+ total, no new failures

## Self-review

### Verification results
- [x] Tests: 12/12 PASS (183 total in test_evaluate.py)
- [x] Contradiction gate fires correctly on fixture
- [x] Evidence captured: reports/TC-HYBRID-06/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v -k "Contradiction or FormatTruth" --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

## Integration boundary proven

**Upstream**: `ApiSurface.format_matrix` (TC-HYBRID-03) → passed as `api_surface` param → gates consume `format_matrix`
**Downstream**: Gate findings in `PageEvaluation.findings` → affect grade → surface in report
**Contract**: Both functions `check_*(content, slug, *, api_surface=None) -> list[Finding]` — never raises; always returns list
