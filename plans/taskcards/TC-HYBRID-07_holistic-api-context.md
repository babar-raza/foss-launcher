---
id: TC-HYBRID-07
title: "Holistic API context injection: use typed signatures in section prompts"
status: Done
priority: Normal
owner: "Claude Code (Sonnet 4.6)"
updated: "2026-03-10"
tags: [generate, api-surface, section-prompt, hybrid-plan]
depends_on: [TC-HYBRID-02]
allowed_paths:
  - plans/taskcards/TC-HYBRID-07_holistic-api-context.md
  - src/launcher/workers/generate/section_prompt.py
  - tests/unit/workers/generate/
  - tests/unit/workers/test_generate.py
evidence_required:
  - reports/TC-HYBRID-07/evidence.md
---

# Taskcard TC-HYBRID-07 — Holistic API context injection

## Objective

Extend `_format_api_surface()` in `section_prompt.py` to emit typed method
signatures (`MethodSignature.parameters`, `return_type`), typed property
annotations (`PropertyRecord.type_annotation`), and enum members
(`EnumRecord.members`) from TC-HYBRID-02's new fields. This gives the LLM
accurate, complete API context instead of bare method names, reducing
hallucinated parameter types, wrong return types, and incorrect enum casing.

## Required spec references

- `specs/07_section_templates.md` (Section: LLM prompt contracts)
- `plans/taskcards/TC-HYBRID-02_typed-api-surface.md` (source of typed fields)
- `plans/taskcards/abundant-wibbling-wadler.md` Phase 4 / Agent-4A-CONTEXT

## Scope

### In scope
- Extend `_format_api_surface()` to use `typed_methods`, `typed_properties`, and `enums` from `ClassBrief` when available
- Add `_build_typed_method_sig()` helper to format one MethodSignature as a compact string
- Add token-cap: if the formatted API block exceeds ~1000 tokens (≈4000 chars), truncate with a note
- Add enum context block for `ApiSurface.enums` (top-level enums, not per-class) injected after class list
- Include `enums: list[EnumRecord]` parameter to `_format_api_surface` (from ApiSurface.enums)

### Out of scope
- Changing `build_section_prompt()` public signature (backwards compatible only)
- Changing how `class_briefs` are passed in from the generate worker (already wired)
- Adding new parameters to `build_section_prompt()` for enums (derive from existing class_briefs)
- Cross-page consistency (TC-HYBRID-08)

## Inputs

- `src/launcher/workers/generate/section_prompt.py` — current `_format_api_surface()`
- `src/launcher/models/product.py` — `ClassBrief`, `MethodSignature`, `MethodParam`, `PropertyRecord`, `EnumRecord`, `EnumMember`
- TC-HYBRID-02 changes (new fields on `ClassBrief`: `typed_methods`, `typed_properties`, `enums`)

## Outputs

- Extended `_format_api_surface()` that emits, for each class:
  ```
  - `Scene`: 3D scene container
    Methods: load(path: str) -> Scene, save(path: str, fmt: FileFormat) -> None, merge(other: Scene) -> None
    Properties: root_node: Node (read-only), unit_scale: float
    Enums: FileFormat (FBX, OBJ, GLTF, STL)
  ```
- Helper `_build_typed_method_sig(sig: MethodSignature) -> str` — formats as `name(p1: T1, p2: T2) -> RetType`
- Token cap: if total block > 4000 chars, trim to first N classes that fit
- Top-level enum block at the end of the API surface block

## Allowed paths

- plans/taskcards/TC-HYBRID-07_holistic-api-context.md
- src/launcher/workers/generate/section_prompt.py
- tests/unit/workers/generate/
- tests/unit/workers/test_generate.py

### Allowed paths rationale
- `section_prompt.py`: contains `_format_api_surface` — only file to modify
- `tests/unit/workers/generate/`: test files for generate worker
- `tests/unit/workers/test_generate.py`: existing tests to extend

## Implementation steps

### Step 1: Read current state

Read `src/launcher/workers/generate/section_prompt.py` fully to understand:
1. The exact imports already at top (`ClassBrief` is already imported)
2. The current `_format_api_surface` signature and body (around line 843)
3. What other models are already imported from `launcher.models.product`

### Step 2: Add imports

In the imports at the top of `section_prompt.py`, extend the `ClassBrief, ProductIdentity` import
to include the new typed models:

```python
from launcher.models.product import (
    ClassBrief,
    EnumMember,
    EnumRecord,
    MethodSignature,
    ProductIdentity,
    PropertyRecord,
)
```

### Step 3: Add _build_typed_method_sig() helper

After the `_REFERENCE_DIRECTIVE_OVERRIDES` dict (around line 46) or just before `_format_api_surface`, add:

```python
def _build_typed_method_sig(sig: "MethodSignature") -> str:
    """Format a MethodSignature as a compact readable string.

    Example: 'load(path: str, options: LoadOptions) -> Scene'
    Falls back to bare name() when parameter/return info is absent.
    """
    params = ", ".join(
        f"{p.name}: {p.type_annotation}" if p.type_annotation else p.name
        for p in sig.parameters
    )
    result = f"{sig.name}({params})"
    if sig.return_type:
        result += f" -> {sig.return_type}"
    if sig.is_static:
        result = f"[static] {result}"
    return result


_API_BLOCK_MAX_CHARS: int = 4000  # ~1000 tokens; hard cap to avoid context overload
```

### Step 4: Extend _format_api_surface() with typed context

Replace the "Rich mode" block in `_format_api_surface()` (the `if class_briefs:` branch, lines 879-906)
with an extended version that uses typed fields:

```python
    # Rich mode: use class_briefs for detailed context
    if class_briefs:
        lines = []
        # Build brief lookup
        brief_map = {b.name: b for b in class_briefs}
        _mentioned = claim_mentioned_classes or set()
        # Prioritize classes that have briefs, cap at 15
        shown = 0
        for cls in public_classes:
            if shown >= 15:
                break
            brief = brief_map.get(cls)
            if brief:
                parts = [f"- `{brief.name}`"]
                if brief.docstring_snippet:
                    parts.append(f": {brief.docstring_snippet}")
                # TC-3882 (Gap6): Claim-mentioned classes get deeper depth
                _is_mentioned = cls in _mentioned
                _method_cap = 10 if _is_mentioned else 5
                _prop_cap = 8 if _is_mentioned else 5

                # TC-HYBRID-07: Use typed signatures when available
                if brief.typed_methods:
                    sigs = [_build_typed_method_sig(m) for m in brief.typed_methods[:_method_cap]]
                    parts.append(f"\n  Methods: {', '.join(sigs)}.")
                elif brief.methods:
                    parts.append(f" Methods: {', '.join(brief.methods[:_method_cap])}.")

                if brief.typed_properties:
                    prop_strs = []
                    for p in brief.typed_properties[:_prop_cap]:
                        ps = p.name
                        if p.type_annotation:
                            ps += f": {p.type_annotation}"
                        if p.is_readonly:
                            ps += " (read-only)"
                        prop_strs.append(ps)
                    parts.append(f"\n  Properties: {', '.join(prop_strs)}.")
                elif brief.properties:
                    parts.append(f" Properties: {', '.join(brief.properties[:_prop_cap])}.")

                # TC-HYBRID-07: Include per-class enums
                if brief.enums:
                    for enum in brief.enums[:3]:  # cap at 3 enums per class
                        member_names = [m.name for m in enum.members[:8]]
                        if member_names:
                            parts.append(f"\n  Enum {enum.name}: {', '.join(member_names)}.")

                lines.append("".join(parts))
            else:
                lines.append(f"- `{cls}`")
            shown += 1

        # TC-HYBRID-07: Add top-level enums block
        if enums:
            lines.append("")
            lines.append("Top-level enums:")
            for enum in enums[:5]:  # cap at 5 top-level enums
                member_names = [m.name for m in enum.members[:10]]
                if member_names:
                    lines.append(f"  {enum.name}: {', '.join(member_names)}")

        result = "\n".join(lines)
        # TC-HYBRID-07: Hard cap to ~1000 tokens
        if len(result) > _API_BLOCK_MAX_CHARS:
            result = result[:_API_BLOCK_MAX_CHARS] + "\n  ... (API surface truncated)"
        return result
```

Note: this requires adding `enums: list[EnumRecord] | None = None` to the `_format_api_surface` signature.

### Step 5: Update _format_api_surface() signature and call site

Add `enums: list[EnumRecord] | None = None` parameter to `_format_api_surface()`.

Find the call site of `_format_api_surface` in `build_section_prompt()` (around line 611-615) and extend it:

```python
    api_surface_block = _format_api_surface(
        public_classes or [],
        class_briefs=class_briefs,
        has_snippets=bool(section_snippets),
        claim_mentioned_classes=_claim_mentioned,
        enums=_get_top_level_enums(class_briefs),
    )
```

Add helper before `_format_api_surface`:

```python
def _get_top_level_enums(class_briefs: list[ClassBrief] | None) -> list[EnumRecord]:
    """Collect all unique enums from class_briefs for the top-level enum block."""
    if not class_briefs:
        return []
    seen: set[str] = set()
    result: list[EnumRecord] = []
    for brief in class_briefs:
        for enum in brief.enums:
            if enum.name not in seen:
                seen.add(enum.name)
                result.append(enum)
    return result
```

### Step 6: Write tests

Add to `tests/unit/workers/generate/` a new file `test_api_context_injection.py` or extend `tests/unit/workers/test_generate.py`:

Test cases:
1. `test_typed_method_sig_with_params_and_return` — `_build_typed_method_sig` formats correctly
2. `test_typed_method_sig_no_return` — no return type: `"load(path: str)"`
3. `test_typed_method_sig_static` — static: `"[static] create() -> Scene"`
4. `test_typed_method_sig_no_params` — empty params: `"close()"`
5. `test_format_api_surface_uses_typed_methods` — when `typed_methods` present, output contains param types
6. `test_format_api_surface_falls_back_to_methods` — when `typed_methods` empty, uses plain `methods`
7. `test_format_api_surface_includes_typed_properties` — `type_annotation` appears in output
8. `test_format_api_surface_includes_enum_members` — class enum members appear in output
9. `test_format_api_surface_top_level_enums` — top-level enums block appears when `enums` passed
10. `test_format_api_surface_hard_cap` — output > 4000 chars gets truncated with "... (API surface truncated)"

### Step 7: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -x -q --timeout=60
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --timeout=60
```

## Failure modes

### Failure mode 1: AttributeError on brief.typed_methods when ClassBrief is from old data

**Detection**: `AttributeError: 'ClassBrief' object has no attribute 'typed_methods'`
**Resolution**: All new fields have `default_factory=list` in the Pydantic model (TC-HYBRID-02). This should never fail. If it does, use `getattr(brief, "typed_methods", [])` as safeguard.
**Gate**: Unit tests with ClassBrief constructed without typed_methods still pass

### Failure mode 2: Token cap truncates mid-method causing malformed output

**Detection**: Output ends with `Methods: load(path: str), sa` (cut mid-word)
**Resolution**: Cap is applied after building the full lines list — it truncates the final joined string. This is acceptable as the LLM will still see the most important classes. Could refine to truncate at a line boundary but not required for initial implementation.
**Gate**: `test_format_api_surface_hard_cap` verifies truncation happens and "truncated" marker is present

### Failure mode 3: Existing section prompt tests fail due to changed output format

**Detection**: `test_generate.py` assertions on prompt content fail (e.g., checking for "Methods: method_a")
**Resolution**: Existing tests use plain `ClassBrief(name=..., methods=["m1", "m2"], typed_methods=[])`. When `typed_methods` is empty, the code falls back to `brief.methods` — existing tests should pass unchanged.
**Gate**: Full test suite green after change

### Failure mode 4: Circular import when importing EnumRecord etc. at module level

**Detection**: `ImportError` at `from launcher.models.product import EnumRecord`
**Resolution**: `section_prompt.py` already imports from `launcher.models.product`. Adding more names to the same import should not cause circular imports. Verify by running `python -c "from launcher.workers.generate.section_prompt import build_section_prompt"`.
**Gate**: Import test passes

## Task-specific review checklist

1. [ ] `_build_typed_method_sig` formats `"load(path: str) -> Scene"` correctly
2. [ ] When `typed_methods` is non-empty, output uses typed sigs (not plain method names)
3. [ ] When `typed_methods` is empty, falls back gracefully to `brief.methods`
4. [ ] `typed_properties` with `type_annotation` and `is_readonly` renders correctly
5. [ ] Per-class enum members appear in output (capped at 3 enums, 8 members each)
6. [ ] Top-level enums block appears when non-empty enums passed
7. [ ] Output exceeding 4000 chars is truncated with "... (API surface truncated)" marker
8. [ ] `_get_top_level_enums` deduplicates enums by name across class_briefs
9. [ ] All 10 new tests pass
10. [ ] Existing generate/test_generate.py tests still pass (no regression)
11. [ ] Docstrings updated for `_format_api_surface`, `_build_typed_method_sig`

## Deliverables

1. `src/launcher/workers/generate/section_prompt.py` — extended `_format_api_surface`, new helpers
2. `tests/unit/workers/generate/test_api_context_injection.py` (or extended test_generate.py) — 10 tests
3. `reports/TC-HYBRID-07/evidence.md` — test run output

## Acceptance checks

1. [x] `_build_typed_method_sig(MethodSignature(name="load", parameters=[MethodParam(name="path", type_annotation="str")], return_type="Scene"))` == `"load(path: str) -> Scene"`
2. [x] ClassBrief with typed_methods produces method signatures in prompt output
3. [x] ClassBrief with empty typed_methods but non-empty methods still produces output (fallback)
4. [x] All 15 new tests pass (10 required + 5 bonus)
5. [x] Full test suite passes without regression (3386 passed)

## Self-review

### Verification results
- [x] Tests: 15/15 PASS (new) + 3386 PASS (full suite, no regression)
- [x] Integration: section prompts contain typed signatures when ClassBrief has typed_methods
- [x] Evidence captured: reports/TC-HYBRID-07/evidence.md
- [x] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -x -q --timeout=60
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --timeout=60
```

**Expected results**:
- 10 new tests pass
- No regression in existing tests

## Integration boundary proven

**Upstream**: `ClassBrief.typed_methods: list[MethodSignature]`, `ClassBrief.typed_properties: list[PropertyRecord]`, `ClassBrief.enums: list[EnumRecord]` (from TC-HYBRID-02 extraction)
**Downstream**: Section prompt text fed to LLM for content generation
**Contract**: `_format_api_surface` receives `class_briefs: list[ClassBrief]` with new optional typed fields; output is a formatted string block injected into the LLM prompt
