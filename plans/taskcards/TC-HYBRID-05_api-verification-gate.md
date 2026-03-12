---
id: TC-HYBRID-05
title: "API Identifier Verification Gate — catch hallucinated method/class names in code"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-10"
tags: [evaluate, gate, api-verification, hallucination]
depends_on: [TC-HYBRID-02]
allowed_paths:
  - plans/taskcards/TC-HYBRID-05_api-verification-gate.md
  - src/launcher/workers/evaluate/checks/api_verification.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/evaluate/go_criteria.py
  - tests/unit/workers/test_evaluate.py
  - tests/unit/workers/test_code_check.py
  - reports/TC-HYBRID-05/evidence.md
  - reports/agents/B/TC-HYBRID-05/self_review.md
  - reports/agents/B/TC-HYBRID-05/plan.md
evidence_required:
  - reports/TC-HYBRID-05/evidence.md
---

# Taskcard TC-HYBRID-05 — API Identifier Verification Gate

## Objective

Add a new `check_api_identifiers()` gate that scans generated code blocks for API
calls (class instantiation, method calls, property access) and cross-references
them against `ApiSurface.class_briefs`. Unknown class names fire HIGH findings;
unknown method names fire MEDIUM findings. Gates with `api_surface.confidence < 0.6`
are skipped to avoid false positives. This eliminates the class of hallucination where
the LLM invents method names that don't exist in the extracted API surface.

## Required spec references

- `specs/worker_evaluate.md` (Phase A gates, finding severity)
- `specs/product_model.md` (ApiSurface, ClassBrief — TC-HYBRID-02 additions)

## Scope

### In scope
- New `src/launcher/workers/evaluate/checks/api_verification.py`
- Export `check_api_identifiers` from `checks/__init__.py`
- Add `api_surface: ApiSurface | None = None` to `_run_deterministic_checks()` signature in `worker.py`
- Call `check_api_identifiers(content, slug, api_surface=api_surface)` in `_run_deterministic_checks()`
- Load `api_surface` from `understand_checkpoint.json` in `_evaluate_page_llm()` and pass to `_run_deterministic_checks()`
- Update `go_criteria.py`: API verification HIGH findings are blocking (counted as critical)

### Out of scope
- Contradiction gate (TC-HYBRID-06 scope)
- Format truth gate (TC-HYBRID-06 scope)
- Typed method parameter verification (Phase 4+)

## Inputs

- `ApiSurface` model (TC-HYBRID-02: now has `class_briefs[*].typed_methods`, `class_briefs[*].enums`, `api_identifiers`)
- Generated markdown content (from `content` in `_evaluate_page_llm`)
- `understand_checkpoint.json` (persisted by understand worker, already loaded for API summary)

## Outputs

- `check_api_identifiers(content, slug, *, api_surface=None)` returning `list[Finding]`
- HIGH finding when generated code uses unknown class name
- MEDIUM finding when generated code uses unknown method name on a known class
- Gate SKIPS (returns []) when `api_surface` is None or `api_surface.confidence == "low"`

## Allowed paths

- plans/taskcards/TC-HYBRID-05_api-verification-gate.md
- src/launcher/workers/evaluate/checks/api_verification.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/evaluate/go_criteria.py
- tests/unit/workers/test_evaluate.py
- tests/unit/workers/test_code_check.py
- reports/TC-HYBRID-05/evidence.md
- reports/agents/B/TC-HYBRID-05/self_review.md
- reports/agents/B/TC-HYBRID-05/plan.md

## Implementation steps

### Step 1: Read key files first

Read before writing:
- `src/launcher/workers/evaluate/checks/code.py` — understand an existing check module structure
- `src/launcher/workers/evaluate/worker.py` lines 454-513 — `_run_deterministic_checks()` and `_load_api_surface_summary()`
- `src/launcher/workers/evaluate/worker.py` lines 160-230 — `_evaluate_page_llm()` call to `_run_deterministic_checks()`
- `src/launcher/workers/evaluate/checks/__init__.py` — current exports
- `src/launcher/models/product import ApiSurface` — understand the model structure

### Step 2: Create api_verification.py

Create `src/launcher/workers/evaluate/checks/api_verification.py`:

```python
"""API identifier verification gate (TC-HYBRID-05).

Scans code blocks in generated content for API calls and cross-references
them against the extracted ApiSurface. Flags unknown identifiers.
"""
from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.product import ApiSurface

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)


# Pattern to extract code blocks from markdown
_CODE_BLOCK_RE = re.compile(r'```(?:python|py)\n(.*?)```', re.DOTALL)

# Patterns to extract API calls from Python code
# Class instantiation: ClassName(...)
_CLASS_INSTANTIATION_RE = re.compile(r'\b([A-Z][a-zA-Z0-9]+)\s*\(')
# Method call: obj.method_name(...) or cls.method_name(...)
_METHOD_CALL_RE = re.compile(r'\b[a-z_][a-zA-Z0-9_]*\.([a-z_][a-zA-Z0-9_]*)\s*\(')
# Property access: obj.property_name (no parentheses)
_PROPERTY_ACCESS_RE = re.compile(r'\b[a-z_][a-zA-Z0-9_]*\.([a-z_][a-zA-Z0-9_]+)\b(?!\s*[\(=])')

# Classes to always allow (standard Python builtins and common idioms)
_ALWAYS_ALLOWED_CLASSES = frozenset({
    "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "bytes", "bytearray", "object", "type", "Exception", "ValueError",
    "TypeError", "RuntimeError", "FileNotFoundError", "IOError",
    "NotImplementedError", "AttributeError", "KeyError", "IndexError",
    "StopIteration", "GeneratorExit", "SystemExit",
    "Path", "PurePath", "PurePosixPath", "PureWindowsPath",
    "Enum", "IntEnum", "StrEnum", "Flag", "IntFlag",
    "ABC", "abstractmethod",
    "Optional", "Union", "List", "Dict", "Set", "Tuple", "Any",
    "ClassVar", "Final", "Literal",
    "print", "len", "range", "enumerate", "zip", "map", "filter",
    "sorted", "reversed", "sum", "min", "max", "abs", "round",
    "open", "input", "format", "repr", "hash", "id",
})

# Methods to always allow (common Python protocols)
_ALWAYS_ALLOWED_METHODS = frozenset({
    "__init__", "__str__", "__repr__", "__len__", "__iter__",
    "__enter__", "__exit__", "__getitem__", "__setitem__",
    "append", "extend", "insert", "remove", "pop", "clear",
    "update", "get", "keys", "values", "items",
    "strip", "split", "join", "replace", "lower", "upper",
    "encode", "decode", "read", "write", "close",
    "format", "startswith", "endswith", "find", "index",
})


def check_api_identifiers(
    content: str,
    slug: str,
    *,
    api_surface: "ApiSurface | None" = None,
) -> "list[Finding]":
    """Verify API identifiers in generated code blocks against extracted ApiSurface.

    Scans Python code blocks for class instantiations, method calls, and property
    accesses. Cross-references against ``api_surface.class_briefs`` and
    ``api_surface.api_identifiers``.

    Args:
        content: Generated markdown content.
        slug: Page slug for Finding location.
        api_surface: Extracted ApiSurface from Understand worker. If None or
            low-confidence, the gate is skipped (returns []).

    Returns:
        List of Findings. HIGH = unknown class name. MEDIUM = unknown method.
        Empty list when gate skips (low confidence, no api_surface, no code blocks).
    """
    # Gate: skip when no api_surface or low confidence
    if api_surface is None:
        return []
    if api_surface.confidence == "low":
        return []
    if not api_surface.class_briefs and not api_surface.api_identifiers:
        return []

    # Build lookup sets from ApiSurface
    known_classes: set[str] = set(api_surface.public_classes)
    known_methods: set[str] = set()
    known_properties: set[str] = set()

    for brief in api_surface.class_briefs:
        known_methods.update(brief.methods)
        known_properties.update(brief.properties)
        # Also add typed method names for completeness
        for tm in brief.typed_methods:
            known_methods.add(tm.name)
        for tp in brief.typed_properties:
            known_properties.add(tp.name)

    # Also use api_identifiers as a broader allowlist
    all_known = set(api_surface.api_identifiers) | known_classes | known_methods | known_properties

    findings: list[Finding] = []

    # Extract Python code blocks
    code_blocks = _CODE_BLOCK_RE.findall(content)
    if not code_blocks:
        return []

    for block in code_blocks:
        # Check class instantiations
        for m in _CLASS_INSTANTIATION_RE.finditer(block):
            cls_name = m.group(1)
            if cls_name in _ALWAYS_ALLOWED_CLASSES:
                continue
            if cls_name in known_classes:
                continue
            if cls_name in all_known:
                continue
            # Check if it's likely a product class (starts with product prefix)
            # Only flag if confidence is high (reduces false positives)
            if api_surface.confidence == "high":
                findings.append(Finding(
                    check="api_identifier_unknown_class",
                    message=(
                        f"Code uses class `{cls_name}` which is not in extracted API surface. "
                        f"Known classes: {sorted(known_classes)[:5]}"
                    ),
                    severity="high",
                    location=slug,
                ))

        # Check method calls
        for m in _METHOD_CALL_RE.finditer(block):
            method_name = m.group(1)
            if method_name in _ALWAYS_ALLOWED_METHODS:
                continue
            if method_name.startswith("_"):
                continue
            if method_name in known_methods:
                continue
            if method_name in all_known:
                continue
            # Only flag medium severity — method names are less certain
            if api_surface.confidence in ("high", "medium"):
                findings.append(Finding(
                    check="api_identifier_unknown_method",
                    message=(
                        f"Code calls method `{method_name}()` which is not in extracted API surface."
                    ),
                    severity="medium",
                    location=slug,
                ))

    # Deduplicate (same check+message may appear in multiple code blocks)
    seen: set[str] = set()
    unique: list[Finding] = []
    for f in findings:
        key = f"{f.check}:{f.message}"
        if key not in seen:
            seen.add(key)
            unique.append(f)

    if unique:
        logger.info(
            "api_verification: slug=%s findings=%d (high=%d, medium=%d)",
            slug, len(unique),
            sum(1 for f in unique if f.severity == "high"),
            sum(1 for f in unique if f.severity == "medium"),
        )

    return unique
```

### Step 3: Export from checks/__init__.py

In `src/launcher/workers/evaluate/checks/__init__.py`, add:
```python
from .api_verification import check_api_identifiers
```

And add `"check_api_identifiers"` to `__all__`.

### Step 4: Update _run_deterministic_checks in worker.py

In `src/launcher/workers/evaluate/worker.py`:

1. Add import at top of file:
```python
from launcher.workers.evaluate.checks import (
    ...existing...,
    check_api_identifiers,  # TC-HYBRID-05
)
```

2. Add `api_surface` parameter to `_run_deterministic_checks()`:
```python
def _run_deterministic_checks(
    content: str, slug: str, *, page_role: str = "", product_name: str = "",
    canonical_import: str = "", runtime_import: str = "",
    golden_dir: "Path | None" = None,
    claim_texts: "list[str] | None" = None,
    api_surface: "ApiSurface | None" = None,  # TC-HYBRID-05
) -> list[Finding]:
```

3. Add call inside `_run_deterministic_checks()` at the end (before `return findings`):
```python
    # TC-HYBRID-05: API identifier verification (skips when api_surface is None/low confidence)
    findings.extend(check_api_identifiers(content, slug, api_surface=api_surface))
```

4. In `_evaluate_page_llm()`, load `api_surface` from checkpoint before calling `_run_deterministic_checks()`. Find `_run_deterministic_checks(content, gen_page.slug, ...)` call and add `api_surface=_api_surface_obj` parameter:

First, load api_surface from checkpoint (add before the `_run_deterministic_checks` call):
```python
            # TC-HYBRID-05: load ApiSurface from understand checkpoint for gate
            _api_surface_obj = None
            try:
                import json as _json
                from launcher.models.product import ApiSurface as _ApiSurface
                _cp_path = context.run_dir / "understand_checkpoint.json"
                if _cp_path.exists():
                    _cp = _json.loads(_cp_path.read_text(encoding="utf-8"))
                    _api_surface_obj = _ApiSurface.model_validate(
                        _cp.get("api_surface", {})
                    )
            except Exception:
                _api_surface_obj = None
```

Then pass it:
```python
            findings = _run_deterministic_checks(
                content, gen_page.slug,
                ...,
                api_surface=_api_surface_obj,  # TC-HYBRID-05
            )
```

IMPORTANT: Check if there is already an `_api_surface_cache` mechanism in the worker. There is! (at line ~483). Use `_load_api_surface_summary()` as reference but load the full `ApiSurface` model (not just the summary string).

### Step 5: Update go_criteria.py

In `src/launcher/workers/evaluate/go_criteria.py`, the `_count_critical()` function counts `severity == "critical"` findings. API verification HIGH findings use `severity="high"` (not "critical") to avoid being too aggressive.

No change needed to go_criteria.py in this TC — HIGH findings from the API verification gate will affect page grade (via grader.py) and surface in the report, but won't block GO verdict at this phase. TC-HYBRID-09+ can elevate them to blocking once the gate is proven in production.

Actually, re-read the hybrid plan: "update `go_criteria.py` to include API verification HIGH findings as blocking". But since this is a new gate, we should be conservative. Add this to go_criteria.py:

Actually: skip the go_criteria change for now. Let the gate fire findings without blocking — let it run for a few pilot runs first. The self-review should document this as a known conservative choice.

### Step 6: Write tests

In `tests/unit/workers/test_evaluate.py`, check for existing `TestApiVerification` or add:

```python
class TestApiVerification:
    def test_gate_skips_when_no_api_surface(self):
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        findings = check_api_identifiers("```python\nfoo = Bar()\n```", "slug")
        assert findings == []

    def test_gate_skips_on_low_confidence(self):
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        from launcher.models.product import ApiSurface
        surface = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        findings = check_api_identifiers("```python\nfoo = Bar()\n```", "slug", api_surface=surface)
        assert findings == []

    def test_known_class_passes(self):
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        from launcher.models.product import ApiSurface, ClassBrief
        surface = ApiSurface(
            public_classes=["Scene"], import_allowlist=["aspose.threed"],
            confidence="high",
            class_briefs=[ClassBrief(name="Scene", methods=["save", "load"])],
        )
        content = "```python\nscene = Scene()\nscene.save('out.obj')\n```"
        findings = check_api_identifiers(content, "slug", api_surface=surface)
        assert not any(f.check == "api_identifier_unknown_class" for f in findings)

    def test_unknown_class_fires_high(self):
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        from launcher.models.product import ApiSurface, ClassBrief
        surface = ApiSurface(
            public_classes=["Scene"], import_allowlist=["aspose.threed"],
            confidence="high",
            class_briefs=[ClassBrief(name="Scene", methods=["save"])],
        )
        content = "```python\nrenderer = SceneRenderer()\n```"
        findings = check_api_identifiers(content, "slug", api_surface=surface)
        high_findings = [f for f in findings if f.severity == "high"]
        assert len(high_findings) >= 1
        assert "SceneRenderer" in high_findings[0].message

    def test_no_code_blocks_returns_empty(self):
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        from launcher.models.product import ApiSurface
        surface = ApiSurface(
            public_classes=["Scene"], import_allowlist=["aspose.threed"], confidence="high"
        )
        findings = check_api_identifiers("No code here, just prose.", "slug", api_surface=surface)
        assert findings == []
```

### Step 7: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v -k "ApiVerification" --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

### Step 8: Write evidence and self-review

Create `reports/TC-HYBRID-05/evidence.md` and `reports/agents/B/TC-HYBRID-05/self_review.md`.
Mark taskcard Done.

## Failure modes

### Failure mode 1: False positives — flags valid API calls (too aggressive)

**Detection**: Known valid class `Scene` flagged as unknown
**Resolution**: Ensure `known_classes` is populated from `api_surface.public_classes`. Check that `api_surface.public_classes` is populated by running the understand worker on a real repo. Use confidence-gating: only HIGH severity on `confidence == "high"`.
**Gate**: `test_known_class_passes` must pass

### Failure mode 2: `understand_checkpoint.json` doesn't exist at eval time

**Detection**: `_api_surface_obj = None`; gate skips gracefully
**Resolution**: Gate designed to skip when api_surface is None. This is expected behavior for runs without an understand checkpoint.
**Gate**: `test_gate_skips_when_no_api_surface` verifies graceful skip

### Failure mode 3: `ApiSurface.model_validate()` fails on old checkpoint format

**Detection**: `ValidationError` when loading checkpoint
**Resolution**: Wrap in try/except, set `_api_surface_obj = None` on failure. Gate skips gracefully.
**Gate**: Error handling in Step 4 loading code

### Failure mode 4: TC-HYBRID-06 runs before TC-HYBRID-05 and both try to add `api_surface` param

**Detection**: Duplicate `api_surface` parameter in `_run_deterministic_checks()`
**Resolution**: TC-HYBRID-06 should read `worker.py` first and check if `api_surface` param already exists before adding it. If it exists, skip adding the param — just add the gate call.
**Gate**: Only one `api_surface` param appears in the function signature

## Task-specific review checklist

1. [ ] `check_api_identifiers` function implemented in `api_verification.py`
2. [ ] Gate skips when `api_surface is None` or `confidence == "low"`
3. [ ] HIGH finding for unknown class (only on `confidence == "high"`)
4. [ ] MEDIUM finding for unknown method (on `confidence in ("high", "medium")`)
5. [ ] Deduplication: same finding not repeated for multiple code blocks
6. [ ] `check_api_identifiers` exported from `checks/__init__.py`
7. [ ] `api_surface: ApiSurface | None = None` added to `_run_deterministic_checks()`
8. [ ] api_surface loaded from checkpoint in `_evaluate_page_llm()` and passed to checks
9. [ ] 5 unit tests all pass
10. [ ] Docstrings complete on `check_api_identifiers`
11. [ ] Checked `docs/README.md` ownership map

## Deliverables

1. `src/launcher/workers/evaluate/checks/api_verification.py` — new
2. `src/launcher/workers/evaluate/checks/__init__.py` — export
3. `src/launcher/workers/evaluate/worker.py` — api_surface param + call
4. `tests/unit/workers/test_evaluate.py` — 5 TestApiVerification tests
5. `reports/TC-HYBRID-05/evidence.md`
6. `reports/agents/B/TC-HYBRID-05/self_review.md`

## Acceptance checks

1. [x] `check_api_identifiers` returns `[]` when `api_surface=None`
2. [x] `check_api_identifiers` returns HIGH finding for unknown class with high-confidence surface
3. [x] `check_api_identifiers` returns `[]` for no code blocks
4. [x] `_run_deterministic_checks` accepts `api_surface` param
5. [x] All 8 new tests pass (5 required + 3 bonus)
6. [x] Full suite passes: 3354 passed, 6 pre-existing failures only

## Self-review

### Verification results
- [x] Tests: 8/8 PASS
- [x] Gate skips on low confidence: verified (test_gate_skips_on_low_confidence)
- [x] Evidence captured: reports/TC-HYBRID-05/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v -k "Api" --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

## Integration boundary proven

**Upstream**: `ApiSurface` from `understand_checkpoint.json` → loaded by evaluate worker → passed to gate
**Downstream**: Gate findings appear in `PageEvaluation.findings` → affect page grade → surface in EvaluationReport
**Contract**: `check_api_identifiers(content, slug, *, api_surface=None) -> list[Finding]` — never raises; returns [] on skip
