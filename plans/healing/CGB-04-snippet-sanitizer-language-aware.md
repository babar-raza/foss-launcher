---
id: CGB-04
title: "Language-aware System. stripping in _sanitize_snippet_code()"
status: Open
priority: Medium
gap: SNIP-BROAD
plan: crispy-growing-pebble
waves: [1D]
updated: "2026-03-11"
allowed_paths:
  - plans/healing/CGB-04-snippet-sanitizer-language-aware.md
  - src/launcher/workers/generate/section_prompt.py
  - tests/unit/workers/generate/test_section_prompt.py
  - plans/taskcards/TC-4046_snippet-sanitizer-language-aware.md
---

# CGB-04 — Language-Aware `System.` Stripping

## Gap linkage

**Gap**: SNIP-BROAD (MEDIUM)
**Origin**: Self-review of TC-4035 (`_sanitize_snippet_code()`)
**Effect**: `_ARTIFACT_LINE_PREFIXES` includes `"System."` as a stripped prefix. This
correctly removes C# `System.` namespace imports, but also strips valid Java calls like
`System.out.println(...)` and `System.err.println(...)`. Java snippets with these calls
lose their print statements, making code examples non-functional.

## Role

Engineering — generate worker (section_prompt.py)

## Scope

### Fix
Make the `System.` stripping conditional on the detected language:
- Strip `System.` lines ONLY when language is `csharp`, `cs`, `dotnet`, or unknown
- Preserve `System.` lines when language is `java`

The `Snippet` model already carries a `language` field (from the understand worker).
`_format_snippets()` already receives `Snippet` objects — pass language through to
`_sanitize_snippet_code()`.

### Allowed paths
- `src/launcher/workers/generate/section_prompt.py`
- `tests/unit/workers/generate/test_section_prompt.py`
- `plans/taskcards/TC-4046_snippet-sanitizer-language-aware.md` (required before coding)
- `plans/healing/CGB-04-snippet-sanitizer-language-aware.md`

### Forbidden
- `src/launcher/workers/understand/` — extractor is not the fix location
- `src/launcher/models/` — no model changes needed

## Pre-requisite

Create `plans/taskcards/TC-4046_snippet-sanitizer-language-aware.md` with status
`In-Progress` before any code changes (AG-002).

## Implementation steps

### Step 1: Update function signature

```python
# Before:
def _sanitize_snippet_code(code: str) -> str:
    ...
    lines = [ln for ln in code.splitlines()
             if not ln.lstrip().startswith(_ARTIFACT_LINE_PREFIXES)]

# After:
def _sanitize_snippet_code(code: str, language: str = "") -> str:
    import html as _html_mod
    code = _html_mod.unescape(code)
    _lang = language.lower()
    _is_java = _lang in {"java", "kotlin"}
    lines = []
    for ln in code.splitlines():
        stripped = ln.lstrip()
        if stripped.startswith("*/"):
            continue
        if stripped.startswith("using namespace"):
            continue
        if stripped.startswith("System.") and not _is_java:
            continue
        lines.append(ln)
    return "\n".join(lines)
```

### Step 2: Thread `language` from `_format_snippets()`

In `_format_snippets()`, pass the snippet's language field:
```python
code = _sanitize_snippet_code(s.code, language=getattr(s, "language", ""))
```

### Step 3: Add unit tests

In `tests/unit/workers/generate/test_section_prompt.py`:
- `test_sanitize_snippet_csharp_strips_system`: `System.Console.WriteLine` in C# → stripped
- `test_sanitize_snippet_java_keeps_system`: `System.out.println` in Java → preserved
- `test_sanitize_snippet_unknown_strips_system`: unknown language → `System.` stripped (safe default)

## Acceptance checks

- [ ] Java snippet with `System.out.println` passes through unmodified when language=`java`
- [ ] C# snippet with `System.Console.WriteLine` is stripped when language=`csharp`
- [ ] Unknown-language snippet strips `System.` (conservative default preserved)
- [ ] `*/` and `using namespace` still stripped for all languages
- [ ] HTML entity unescaping still applies for all languages
- [ ] 3 new unit tests pass (PYTHONHASHSEED=0)
- [ ] All existing section_prompt tests pass

## Deliverables

1. Updated `src/launcher/workers/generate/section_prompt.py`
2. New tests in `tests/unit/workers/generate/test_section_prompt.py`
3. Taskcard `plans/taskcards/TC-4046_snippet-sanitizer-language-aware.md` (Done)

## Hard rules

- Taskcard TC-4046 must exist In-Progress before code edit (AG-002)
- Java/Kotlin `System.` must be preserved — these are valid print statements
- Default (unknown language) must strip `System.` — conservative for non-Java snippets
- Do not break the existing `_format_snippets()` call contract

## Review dimensions

1. **Correctness**: Java snippets pass through; C# snippets stripped?
2. **Regression**: Existing sanitizer behavior preserved for non-Java?
3. **Test coverage**: All 3 language scenarios tested?
4. **Simplicity**: No over-engineering — language check is a simple 2-element frozenset

## Now (runbook)

```
1. Create TC-4046 → In-Progress
2. Read src/launcher/workers/generate/section_prompt.py (_sanitize_snippet_code, _format_snippets)
3. Update _sanitize_snippet_code signature to accept language=""
4. Add _is_java guard around System. stripping
5. Thread language= through _format_snippets call
6. Add 3 unit tests
7. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ --tb=short -q
8. Mark TC-4046 Done; mark CGB-04 Resolved
```
