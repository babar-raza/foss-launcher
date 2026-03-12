---
id: TC-3842
title: "Golden Loader Heal Wrapper — _load_golden_for_role() (H2.4)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [heal, golden, section-prompt]
depends_on: [TC-3833]
allowed_paths:
  - plans/taskcards/TC-3842_golden_loader_heal_wrapper.md
  - src/launcher/shared/golden_loader.py
  - tests/shared/test_golden_loader.py
evidence_required:
  - reports/TC-3842/evidence.md
---

# Taskcard TC-3842 — Golden Loader Heal Wrapper (H2.4)

## Objective

Add `_load_golden_for_role(page_role, golden_dir)` to `golden_loader.py` — a
thin wrapper around `GoldenIndex.get_section()` that returns a truncated
(≤500-word) golden excerpt or `None` when the role is absent.

## Required spec references

- `specs/golden.md` (golden reference contract)

## Scope

### In scope
- Add `_load_golden_for_role(page_role: str, golden_dir: Path, section_heading: str = "") -> str | None`
- Loads GoldenIndex from `golden_dir`; calls `.get(page_role)` or `.get_section(page_role, "standard", section_heading)`
- Truncates result to 500 words before returning
- Returns `None` if dir missing, role not found, or section not found

### Out of scope
- Caching GoldenIndex across calls — callers should cache the index themselves
- Tier classification (select_for_tier) — already implemented in TC-3833

## Inputs

- `src/launcher/shared/golden_loader.py` (from TC-3833)

## Outputs

- `_load_golden_for_role()` function accessible from golden_loader.py

## Allowed paths

- plans/taskcards/TC-3842_golden_loader_heal_wrapper.md
- src/launcher/shared/golden_loader.py
- tests/shared/test_golden_loader.py

### Allowed paths rationale

Only `golden_loader.py` extended; test file extended.

## Implementation steps

### Step 1: Add `_load_golden_for_role()` function

Append to `golden_loader.py`:
```python
def _load_golden_for_role(
    page_role: str,
    golden_dir: Path,
    section_heading: str = "",
    *,
    max_words: int = 500,
) -> str | None:
    """Load a golden excerpt for *page_role*, truncated to *max_words*.

    Returns ``None`` when:
    - *golden_dir* does not exist
    - the role is not indexed
    - *section_heading* is given but no matching section is found

    Parameters
    ----------
    page_role:
        Page role string (e.g. "workflow_page", "api_reference").
    golden_dir:
        Directory containing golden .md files.
    section_heading:
        If given, return the matching section body only.
        If empty, return the full page body.
    max_words:
        Truncate output to this many whitespace-separated tokens.
    """
    try:
        index = GoldenIndex.load(golden_dir)
        if section_heading:
            section = index.get_section(page_role, "standard", section_heading)
            if section is None:
                return None
            text = section.body
        else:
            page = index.get(page_role)
            if page is None:
                return None
            text = page.raw_body
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words]) + " …"
        return text if text.strip() else None
    except Exception:
        return None
```

### Step 2: Ensure `raw_body` is accessible on GoldenPage

If `GoldenPage` does not have a `raw_body` field storing the full page markdown
body (after frontmatter strip), add it. Check existing `GoldenPage` dataclass definition.

### Step 3: Add tests

In `tests/shared/test_golden_loader.py`:
```python
def test_load_golden_for_role_returns_text():
    from src.launcher.shared.golden_loader import _load_golden_for_role
    result = _load_golden_for_role("workflow_page", Path("golden/"))
    assert result is not None
    assert len(result.split()) <= 500

def test_load_golden_for_role_missing_dir():
    from src.launcher.shared.golden_loader import _load_golden_for_role
    assert _load_golden_for_role("workflow_page", Path("nonexistent/")) is None

def test_load_golden_for_role_unknown_role():
    from src.launcher.shared.golden_loader import _load_golden_for_role
    assert _load_golden_for_role("no_such_role", Path("golden/")) is None

def test_load_golden_for_role_truncates():
    from src.launcher.shared.golden_loader import _load_golden_for_role
    result = _load_golden_for_role("workflow_page", Path("golden/"), max_words=5)
    if result is not None:
        assert len(result.split()) <= 6  # 5 words + ellipsis token
```

## Failure modes

### Failure mode 1: `GoldenPage` has no `raw_body` attribute

**Detection**: `AttributeError: 'GoldenPage' object has no attribute 'raw_body'`
**Resolution**: Check TC-3833's GoldenPage dataclass — if raw_body is absent, use
the concatenation of all section bodies as fallback, or add `raw_body: str = ""` field
and populate it in `_parse_golden_file()`.
**Gate**: Unit test `test_load_golden_for_role_returns_text`

### Failure mode 2: All exceptions silently return None (masking bugs)

**Detection**: Function returns None unexpectedly; no log output
**Resolution**: Add `logger.debug("_load_golden_for_role failed for %s: %s", page_role, exc)`
before `return None` in the except block.
**Gate**: Logging verification test

### Failure mode 3: GoldenIndex.load() called on every `_load_golden_for_role()` call (performance)

**Detection**: Slow section prompt builds when golden/ has many files
**Resolution**: Document that callers should cache the GoldenIndex. The heal CLI
and generate worker instantiate GoldenIndex once per session. This function is for
one-off lookups (e.g., diagnostic tools).
**Gate**: Performance expectation documented in docstring

## Task-specific review checklist

1. [ ] `_load_golden_for_role()` handles missing dir → None (no exception)
2. [ ] Unknown role → None (not an exception)
3. [ ] section_heading="" → full page body returned
4. [ ] Truncation at exactly 500 words + ellipsis verified
5. [ ] Exception in GoldenIndex.load() → None returned (no crash)
6. [ ] 4 new tests added to `tests/shared/test_golden_loader.py`

## Deliverables

1. `src/launcher/shared/golden_loader.py` — `_load_golden_for_role()` function
2. `tests/shared/test_golden_loader.py` — 4 new test cases

## Acceptance checks

1. [ ] `pytest tests/shared/test_golden_loader.py -v` — all PASS (7 existing + 4 new)
2. [ ] `_load_golden_for_role("workflow_page", Path("golden/"))` returns a non-None string
3. [ ] `pytest tests/ -x -q` — 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: truncation at 500 words verified
- [ ] Evidence file: `reports/TC-3842/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_golden_loader.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All golden loader tests pass (7 + 4 = 11 total)
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: `GoldenIndex.load(golden_dir)` from TC-3833
**Downstream**: TC-3843 (G002) calls `_load_golden_for_role()` from section_prompt.py to build golden reference block
**Contract**: Returns `str | None`; callers must handle None (missing golden → skip injection)
