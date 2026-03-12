---
id: TC-HYBRID-08
title: "Cross-page consistency review: detect contradicting format claims across pages"
status: Done
priority: Normal
owner: "Claude Code (Sonnet 4.6)"
updated: "2026-03-10"
tags: [evaluate, cross-page, consistency, hybrid-plan]
depends_on: [TC-HYBRID-06]
allowed_paths:
  - plans/taskcards/TC-HYBRID-08_cross-page-consistency.md
  - src/launcher/workers/evaluate/cross_page_review.py
  - src/launcher/workers/evaluate/worker.py
  - tests/unit/workers/test_evaluate.py
  - tests/unit/workers/
evidence_required:
  - reports/TC-HYBRID-08/evidence.md
---

# Taskcard TC-HYBRID-08 — Cross-page consistency review

## Objective

Add a cross-page consistency review that runs after all pages are evaluated
and detects when the same format capability is described contradictorily across
pages (e.g., page A says "OBJ can be exported" while page B says "OBJ is not
supported for export"). Only runs on NO_GO verdicts to avoid overhead on
healthy runs.

## Required spec references

- `specs/04_quality_gates.md` (evaluation gate contracts)
- `plans/taskcards/abundant-wibbling-wadler.md` Phase 4 / Agent-4B-CROSSPAGE

## Scope

### In scope
- New `src/launcher/workers/evaluate/cross_page_review.py` with `run_cross_page_review(pages: list[PageEvaluation], content_map: dict[str, str]) -> list[Finding]`
- Wire into `worker.py` — run ONLY when `verdict == NO_GO`, after all page evaluations
- Add cross-page findings to `EvaluationReport` via a new `cross_page_findings: list[Finding]` field
- Cap at 20 page pairs to prevent O(n²) blowup on large runs

### Out of scope
- Cross-page claim deduplication (TC-3769 already handles that)
- Cross-language consistency (different products)
- Running cross-page review on GO verdicts (too expensive)
- Using LLM for cross-page analysis

## Inputs

- `list[PageEvaluation]` — already-evaluated pages with `slug` and `findings`
- `dict[str, str]` — map of slug → content (markdown text) for scanning format claims
- `EvaluationReport.verdict` — must be NO_GO to trigger

## Outputs

- `cross_page_review.py` module with `run_cross_page_review()` function
- `Finding` list (HIGH severity for direct contradictions)
- `EvaluationReport.cross_page_findings: list[Finding]` field (new optional field)

## Allowed paths

- plans/taskcards/TC-HYBRID-08_cross-page-consistency.md
- src/launcher/workers/evaluate/cross_page_review.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/models/evaluation.py
- tests/unit/workers/test_evaluate.py
- tests/unit/workers/

### Allowed paths rationale
- `cross_page_review.py`: new module for cross-page logic
- `worker.py`: wires cross-page review after evaluations complete
- `evaluation.py`: adds `cross_page_findings` field to `EvaluationReport`

## Implementation steps

### Step 1: Add cross_page_findings to EvaluationReport

In `src/launcher/models/evaluation.py`, add a new optional field to `EvaluationReport`:

```python
class EvaluationReport(LauncherBaseModel):
    ...
    cross_page_findings: list[Finding] = Field(default_factory=list)  # TC-HYBRID-08
```

This is backwards-compatible (default empty list).

### Step 2: Create cross_page_review.py

Create `src/launcher/workers/evaluate/cross_page_review.py`:

```python
"""Cross-page consistency review (TC-HYBRID-08).

Detects contradicting format capability claims across evaluated pages.
Only runs on NO_GO verdicts to avoid overhead on healthy runs.
"""
from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.evaluation import Finding, PageEvaluation

logger = logging.getLogger(__name__)

# Format extensions to scan for (must be upper-case in output)
_FORMAT_NAMES: frozenset[str] = frozenset({
    "OBJ", "FBX", "GLTF", "GLB", "STL", "3DS", "DAE", "PLY", "DRC",
    "PDF", "DOCX", "XLSX", "PPTX", "HTML", "PNG", "JPG", "JPEG", "SVG",
    "ZIP", "CSV", "JSON", "XML", "YAML",
})

# Patterns that signal "format CAN be exported/saved"
_EXPORT_POSITIVE_RE = re.compile(
    r'\b(?:can (?:be )?(?:export|save|write|output)|supports? (?:export|saving|writing|output)'
    r'|(?:export|save|write|output) (?:to|as|in))',
    re.IGNORECASE,
)

# Patterns that signal "format CANNOT be exported/saved"
_EXPORT_NEGATIVE_RE = re.compile(
    r'\b(?:cannot (?:be )?(?:export|save|write|output)|does not support (?:export|saving|writing|output)'
    r'|not (?:support(?:ed)?|available)(?: for)? (?:export|saving)|(?:export|save) (?:is )?not supported)',
    re.IGNORECASE,
)

# Patterns that signal "format CAN be imported/loaded"
_IMPORT_POSITIVE_RE = re.compile(
    r'\b(?:can (?:be )?(?:import|load|read)|supports? (?:import|loading|reading)'
    r'|(?:import|load|read) (?:from|as|in))',
    re.IGNORECASE,
)

# Patterns that signal "format CANNOT be imported/loaded"
_IMPORT_NEGATIVE_RE = re.compile(
    r'\b(?:cannot (?:be )?(?:import|load|read)|does not support (?:import|loading|reading)'
    r'|not (?:support(?:ed)?|available)(?: for)? (?:import|loading)|(?:import|load) (?:is )?not supported)',
    re.IGNORECASE,
)

_MAX_PAGE_PAIRS: int = 20


def _extract_format_claims(content: str) -> dict[str, dict[str, str]]:
    """Extract format capability claims from content.

    Returns: {format_name: {"export": "yes"|"no"|"unknown", "import": "yes"|"no"|"unknown"}}
    """
    results: dict[str, dict[str, str]] = {}

    for line in content.splitlines():
        # Skip code blocks and headings
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("#") or stripped.startswith("    "):
            continue

        line_upper = line.upper()
        for fmt in _FORMAT_NAMES:
            if fmt not in line_upper:
                continue
            # Check if line mentions this format
            if not re.search(r'\b' + fmt + r'\b', line_upper):
                continue

            if fmt not in results:
                results[fmt] = {"export": "unknown", "import": "unknown"}

            if _EXPORT_POSITIVE_RE.search(line):
                results[fmt]["export"] = "yes"
            elif _EXPORT_NEGATIVE_RE.search(line):
                results[fmt]["export"] = "no"

            if _IMPORT_POSITIVE_RE.search(line):
                results[fmt]["import"] = "yes"
            elif _IMPORT_NEGATIVE_RE.search(line):
                results[fmt]["import"] = "no"

    return results


def run_cross_page_review(
    content_map: dict[str, str],
) -> "list[Finding]":
    """Scan all pages for contradicting format capability claims.

    Args:
        content_map: slug -> markdown content for each evaluated page

    Returns:
        List of HIGH-severity Finding objects for each contradiction found.
    """
    from launcher.models.evaluation import Finding

    if not content_map:
        return []

    # Extract format claims per page
    page_claims: dict[str, dict[str, dict[str, str]]] = {}
    for slug, content in content_map.items():
        claims = _extract_format_claims(content)
        if claims:
            page_claims[slug] = claims

    if len(page_claims) < 2:
        return []

    findings: list[Finding] = []
    seen_contradictions: set[tuple[str, str, str]] = set()
    pair_count = 0

    slugs = list(page_claims.keys())
    for i, slug_a in enumerate(slugs):
        for slug_b in slugs[i + 1:]:
            if pair_count >= _MAX_PAGE_PAIRS:
                logger.debug("cross_page_review: pair cap reached (%d)", _MAX_PAGE_PAIRS)
                return findings
            pair_count += 1

            claims_a = page_claims[slug_a]
            claims_b = page_claims[slug_b]

            for fmt in set(claims_a) & set(claims_b):
                for capability in ("export", "import"):
                    val_a = claims_a[fmt].get(capability, "unknown")
                    val_b = claims_b[fmt].get(capability, "unknown")

                    if val_a == "unknown" or val_b == "unknown":
                        continue
                    if val_a == val_b:
                        continue

                    # Contradiction found
                    key = (fmt, capability, frozenset([slug_a, slug_b]))
                    if key in seen_contradictions:
                        continue
                    seen_contradictions.add(key)

                    findings.append(Finding(
                        check="cross_page_consistency",
                        message=(
                            f"Format {fmt} {capability} capability contradicts across pages: "
                            f"'{slug_a}' says {val_a}, '{slug_b}' says {val_b}"
                        ),
                        severity="high",
                        location=f"{slug_a} vs {slug_b}",
                    ))
                    logger.info(
                        "cross_page_review contradiction: %s %s — %s=%s vs %s=%s",
                        fmt, capability, slug_a, val_a, slug_b, val_b,
                    )

    return findings
```

### Step 3: Wire into evaluate worker.py

In `src/launcher/workers/evaluate/worker.py`, after the verdict is computed and ONLY
when `verdict == NO_GO`, add the cross-page review call.

Find where `EvaluationReport` is constructed/returned and add before return:

```python
        # TC-HYBRID-08: Cross-page consistency review (NO_GO only)
        cross_page_findings: list[Finding] = []
        if report.verdict == Verdict.NO_GO:
            try:
                from launcher.workers.evaluate.cross_page_review import run_cross_page_review
                _content_map = {p.slug: _page_content_cache.get(p.slug, "") for p in report.pages}
                cross_page_findings = run_cross_page_review(_content_map)
                if cross_page_findings:
                    context.emit_event(
                        "cross_page_contradictions_found",
                        {"count": len(cross_page_findings)},
                        worker=self.name,
                    )
                    logger.warning(
                        "[Evaluate] Cross-page contradictions: %d findings", len(cross_page_findings)
                    )
            except Exception:
                logger.debug("cross_page_review failed", exc_info=True)
        report = report.model_copy(update={"cross_page_findings": cross_page_findings})
```

You will need to identify the `_page_content_cache` — look for where the worker reads page content from disk. If no cache exists, build one: collect slug → content when reading page content during Phase A checks.

Alternatively, if the worker passes content as strings to `_run_deterministic_checks`, collect them into a dict. Read the worker fully to understand the content flow before implementing.

### Step 4: Write tests

Add to `tests/unit/workers/test_evaluate.py` a new `TestCrossPageReview` class:

```python
class TestCrossPageReview:
    def test_fires_on_export_contradiction(self):
        content_a = "OBJ can be exported using Scene.Save()"
        content_b = "OBJ export is not supported in this version"
        findings = run_cross_page_review({"page_a": content_a, "page_b": content_b})
        assert any("OBJ" in f.message and "export" in f.message for f in findings)
        assert findings[0].severity == "high"

    def test_no_finding_when_consistent(self):
        content_a = "OBJ can be exported using Save()"
        content_b = "The library supports OBJ export via Scene.Save()"
        findings = run_cross_page_review({"page_a": content_a, "page_b": content_b})
        assert not any("OBJ" in f.message and "export" in f.message for f in findings)

    def test_no_finding_for_single_page(self):
        content_a = "OBJ cannot be exported"
        findings = run_cross_page_review({"page_a": content_a})
        assert findings == []

    def test_fires_on_import_contradiction(self):
        content_a = "FBX can be imported and loaded"
        content_b = "FBX import is not supported"
        findings = run_cross_page_review({"page_a": content_a, "page_b": content_b})
        assert any("FBX" in f.message and "import" in f.message for f in findings)

    def test_skips_unknown_capabilities(self):
        content_a = "We support OBJ files"  # no clear export/import signal
        content_b = "OBJ export is not supported"
        findings = run_cross_page_review({"page_a": content_a, "page_b": content_b})
        # content_a has "unknown" export signal, no contradiction possible
        assert not any(f.severity == "high" and "OBJ" in f.message and "export" in f.message for f in findings)

    def test_empty_content_map(self):
        findings = run_cross_page_review({})
        assert findings == []

    def test_deduplicates_same_pair(self):
        # Two pages with same contradiction mentioned twice
        content_a = "OBJ can be exported. Export OBJ files easily."
        content_b = "OBJ export is not supported. Cannot export OBJ."
        findings = run_cross_page_review({"pa": content_a, "pb": content_b})
        obj_export = [f for f in findings if "OBJ" in f.message and "export" in f.message]
        assert len(obj_export) == 1  # deduplicated
```

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -x -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --timeout=60
```

## Failure modes

### Failure mode 1: _page_content_cache not available in worker

**Detection**: `KeyError` or empty content map when building `_content_map`
**Resolution**: Read the worker.py carefully to find where page content is read from disk. Build a `slug -> content` mapping there. If content is read in `_evaluate_page_llm`, collect it in a local dict passed through to the final assembly step.
**Gate**: `test_fires_on_export_contradiction` passes end-to-end

### Failure mode 2: cross_page_consistency is not a valid check name in EvaluationReport

**Detection**: LLM review filtering or finding validator rejects "cross_page_consistency" check name
**Resolution**: Cross-page findings go into `EvaluationReport.cross_page_findings` (new field), NOT into `PageEvaluation.findings`. They are separate from per-page check findings and won't be validated against the check name allowlist.
**Gate**: Model validates `EvaluationReport` with `cross_page_findings` populated

### Failure mode 3: O(n²) performance on large runs

**Detection**: Cross-page review takes >5s on runs with 50+ pages
**Resolution**: `_MAX_PAGE_PAIRS = 20` cap prevents O(n²) blowup. If still slow, add early exit when 5+ findings found.
**Gate**: `test_evaluate.py` runs in <30s total

## Task-specific review checklist

1. [x] `run_cross_page_review` only runs when `verdict == NO_GO` in worker
2. [x] `_MAX_PAGE_PAIRS = 20` cap prevents quadratic blowup
3. [x] Deduplication: same (format, capability, page pair) not reported twice
4. [x] Code blocks, headings, and indented lines skipped in claim extraction
5. [x] `cross_page_findings` field added to `EvaluationReport` with default empty list
6. [x] Findings go to `cross_page_findings`, not `PageEvaluation.findings`
7. [x] Worker wraps cross-page call in try/except — never raises
8. [x] All 7 new tests pass
9. [x] No regression in existing evaluate tests

## Deliverables

1. `src/launcher/workers/evaluate/cross_page_review.py` — new module
2. `src/launcher/models/evaluation.py` — `cross_page_findings` field added
3. `src/launcher/workers/evaluate/worker.py` — cross-page review wired
4. Test additions in `tests/unit/workers/test_evaluate.py` — 7 tests
5. `reports/TC-HYBRID-08/evidence.md` — test run output

## Acceptance checks

1. [x] `run_cross_page_review({"a": "OBJ can be exported", "b": "OBJ export is not supported"})` returns 1 HIGH finding
2. [x] `run_cross_page_review({})` returns `[]`
3. [x] All 7 new tests pass
4. [x] `EvaluationReport.cross_page_findings` field exists and defaults to `[]`
5. [x] Full test suite passes without regression

## Self-review

### Verification results
- [x] Tests: 190/190 PASS (test_evaluate.py), 3396/3396 PASS (full suite)
- [x] Evidence: reports/TC-HYBRID-08/evidence.md
- [x] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --timeout=60
```

**Expected results**:
- 7 new tests pass
- Full suite passes without regression

## Integration boundary proven

**Upstream**: `list[PageEvaluation]` + `dict[slug, content]` from evaluate worker
**Downstream**: `EvaluationReport.cross_page_findings` — consumed by reporting/dashboard
**Contract**: `Finding(check="cross_page_consistency", severity="high")` in `cross_page_findings`
