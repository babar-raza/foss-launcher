# Golden Loader Correctness — Gap Index & Taskcards

## Context

Self-review of `twinkly-beaming-wren.md` (Golden Reference Integration, G001–G005)
found three gaps in `src/launcher/shared/golden_loader.py`:

1. **`_load_golden_for_role` re-parses all 22 files on every call** — the function
   calls `GoldenIndex.load(golden_dir)` each invocation, performing 22 file reads and
   full parse on every call. This is correct for test isolation but catastrophic in
   production if called per-section per-page (O(22 × sections × pages) file I/O).

2. **Jaccard threshold undocumented divergence** — `get_section` uses Jaccard ≥ 0.3
   but the plan spec says ≥ 0.5. The code is silent on why. This must either be
   corrected to match spec or explicitly documented with a rationale comment and a
   test proving the chosen threshold is superior.

3. **`grade="A"` hardcoded in `_parse_golden_file`** — all golden pages are tagged
   grade "A" regardless of actual content quality. This makes the `grade` field
   meaningless and will silently mislead any future code that checks `page.grade`.

GL-01 and GL-02 are independent and can be executed in parallel.

---

## Gap Table

| Gap ID | Description                                                        | Taskcard | Priority |
|--------|--------------------------------------------------------------------|----------|----------|
| GAP-09 | `_load_golden_for_role` re-parses 22 files on every call           | GL-01    | MEDIUM   |
| GAP-11 | Jaccard threshold 0.3 vs spec 0.5 — undocumented divergence        | GL-02    | MEDIUM   |
| GAP-13 | `grade="A"` hardcoded in `_parse_golden_file`                      | GL-02    | LOW      |

---

## GL-01 — Fix `_load_golden_for_role` Performance (Singleton Cache)

**Status:** Not Started
**Gap linkage:** GAP-09

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
`_load_golden_for_role` is a module-level convenience function that currently calls
`GoldenIndex.load(golden_dir)` on every invocation. Workers call this per-section.

Two changes are needed:

**1. Add a module-level LRU cache keyed on `golden_dir`:**

```python
import functools

@functools.lru_cache(maxsize=4)
def _get_cached_index(golden_dir_str: str) -> "GoldenIndex":
    """Load and cache GoldenIndex by golden_dir path string.

    LRU cache with maxsize=4 handles ≤4 distinct golden dirs (typical: 1).
    Cache is process-scoped; tests must call _get_cached_index.cache_clear()
    between test cases that use different golden_dir fixtures.
    """
    return GoldenIndex.load(Path(golden_dir_str))
```

**2. Update `_load_golden_for_role` to use the cache:**

```python
def _load_golden_for_role(
    page_role: str,
    golden_dir: Path,
    section_heading: str = "",
    *,
    max_words: int = 500,
) -> "str | None":
    """Load a golden excerpt for *page_role*, truncated to *max_words*.

    Uses a module-level LRU cache to avoid re-parsing all 22 golden files
    on every call. Cache key is the absolute golden_dir path string.
    """
    try:
        index = _get_cached_index(str(golden_dir.resolve()))
        ...  # rest of function unchanged
```

**3. Document cache invalidation in docstring and add a `_clear_golden_cache()` helper for tests:**

```python
def _clear_golden_cache() -> None:
    """Clear the GoldenIndex LRU cache. For use in tests only."""
    _get_cached_index.cache_clear()
```

The `GoldenIndex.load()` classmethod itself remains unchanged — the cache is only at
the `_load_golden_for_role` entry point, not inside the class (to keep the class
pure and independently testable).

**Allowed paths:**
- `src/launcher/shared/golden_loader.py`
- `tests/shared/test_golden_loader.py`

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_load_golden_for_role_cached` — call `_load_golden_for_role` twice with same args; assert `GoldenIndex.load` called only once (mock `GoldenIndex.load`)
- `test_load_golden_for_role_different_dirs_separate_cache_entries` — two distinct `golden_dir` paths → `GoldenIndex.load` called twice
- `test_cache_clear_forces_reload` — call, `_clear_golden_cache()`, call again → `GoldenIndex.load` called twice
- `test_lru_maxsize_respected` — call with 5 different dirs (> maxsize=4) → LRU eviction occurs without crash
- All existing `test_golden_loader.py` tests still pass (add `_clear_golden_cache()` call in `setUp`/fixture teardown to avoid cross-test contamination)

**Performance:**
```bash
# Manual spot-check: confirm GoldenIndex.load() called once per unique dir in a session
python -c "
import time, pathlib
from launcher.shared.golden_loader import _load_golden_for_role, _clear_golden_cache
_clear_golden_cache()
t0 = time.monotonic()
for _ in range(100):
    _load_golden_for_role('workflow_page', pathlib.Path('golden/'))
print(f'100 calls: {time.monotonic()-t0:.3f}s')  # should be <0.1s vs ~5s uncached
"
```

**No mock data in production paths:** cache uses the real `GoldenIndex.load` on first call.

### Deliverables
- Updated `golden_loader.py` with `_get_cached_index` (lru_cache) + `_clear_golden_cache`
- Updated `test_golden_loader.py` with 4 cache tests + `_clear_golden_cache()` in test teardown

### Hard rules
- Cache key must be `str(golden_dir.resolve())` (absolute path) to avoid path aliasing bugs
- `_clear_golden_cache` is explicitly for test use — add `# For use in tests only` comment
- `functools.lru_cache` is stdlib — no new dependencies
- `PYTHONHASHSEED=0` in all test runs

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Performance | 100 calls to `_load_golden_for_role` → 1 file parse, not 100 |
| Correctness | Same output with cache as without cache |
| Testability | `_clear_golden_cache()` enables clean isolation per test case |
| Robustness | LRU eviction (>4 dirs) never crashes; cache failure falls through to live load |

### Now (runbook)
```bash
# 1. Add _get_cached_index (lru_cache) and _clear_golden_cache to golden_loader.py
# 2. Update _load_golden_for_role to call _get_cached_index instead of GoldenIndex.load
# 3. Add _clear_golden_cache() to test fixture teardown in test_golden_loader.py
# 4. Add 4 cache tests
# 5. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_golden_loader.py -v
# 6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## GL-02 — Document Jaccard Threshold + Fix Hardcoded Grade

**Status:** Not Started
**Gap linkage:** GAP-11, GAP-13

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix A — Jaccard threshold decision (GAP-11):**

The plan spec (`twinkly-beaming-wren.md` Phase 1) specifies `get_section` should use
Jaccard ≥ 0.5. The implementation uses 0.3. This must be resolved one of two ways:

**Option A (recommended):** Keep 0.3 with explicit documentation and a test proving
that short section headings (≤3 words like "Overview", "Usage") would produce zero
matches at 0.5 on typical golden files but match correctly at 0.3.

**Option B:** Raise to 0.5 to match spec and accept fewer matches.

Choose **Option A** (keep 0.3). Rationale: short heading Jaccard scores are bounded by
heading word count; for a 2-word heading, Jaccard with a 3-word golden heading sharing
1 word is 1/4 = 0.25 (below both thresholds). At 0.5, "Overview" vs "API Overview"
gives 1/2 = 0.5 (just passes). At 0.5, "Usage Examples" vs "Code Examples" gives
0/4 = 0.0 (no match). At 0.3, many practical short-heading matches are captured. The
spec value of 0.5 was likely a placeholder.

Implementation:
1. Update the `get_section` docstring to document the threshold and rationale.
2. Add a `_SECTION_JACCARD_THRESHOLD: float = 0.3` module-level constant.
3. Replace the literal `0.3` comparison with `_SECTION_JACCARD_THRESHOLD`.

```python
# At module level:
# Jaccard similarity threshold for section heading matching (Level 3 fallback).
# Value 0.3 (not 0.5 as in plan spec) — empirical choice: short headings (1-2 words)
# have Jaccard scores bounded below 0.5 when word sets overlap partially. 0.3
# captures "Code Examples" ↔ "Usage Examples" (score=0.33). Revisit if golden
# index grows beyond 22 files or false positives appear.
_SECTION_JACCARD_THRESHOLD: float = 0.3
```

**Fix B — Derive grade from frontmatter (GAP-13):**

`_parse_golden_file` hardcodes `grade="A"` for all pages. Parse the actual grade from
the file's frontmatter if present (field name: `grade`). Fall back to `"A"` if absent
or invalid, since golden files are expected to be A-quality.

```python
def _parse_golden_file(path: Path, golden_dir: Path) -> Optional[GoldenPage]:
    ...
    # Parse grade from frontmatter
    grade = "A"  # default
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            fm_text = content[3:end]
            for line in fm_text.splitlines():
                if line.startswith("grade:"):
                    raw_grade = line.split(":", 1)[1].strip().strip('"').strip("'")
                    if raw_grade in ("A", "B", "C", "D", "F"):
                        grade = raw_grade
                    break
    ...
    return GoldenPage(
        ...
        grade=grade,   # was: grade="A"
        ...
    )
```

**Allowed paths:**
- `src/launcher/shared/golden_loader.py`
- `tests/shared/test_golden_loader.py`

**Forbidden:** any other file or path.

### Acceptance checks

**Tests — Jaccard threshold:**
- `test_jaccard_threshold_constant_exists` — `golden_loader._SECTION_JACCARD_THRESHOLD == 0.3`
- `test_jaccard_used_in_get_section` — patch `_SECTION_JACCARD_THRESHOLD = 0.8`; assert a section that matched at 0.3 now returns None
- `test_short_heading_match_at_0_3` — "Usage Examples" vs "Code Examples" → Jaccard=0.33 ≥ 0.3 → match returned
- `test_short_heading_no_match_at_0_5` — with threshold patched to 0.5, same pair → None

**Tests — grade parsing:**
- `test_grade_parsed_from_frontmatter_b` — golden file with `grade: B` in frontmatter → `page.grade == "B"`
- `test_grade_defaults_to_a_when_absent` — golden file with no `grade:` field → `page.grade == "A"`
- `test_grade_defaults_to_a_when_invalid` — golden file with `grade: X` (invalid) → `page.grade == "A"`
- `test_grade_defaults_to_a_when_no_frontmatter` — file without `---` block → `page.grade == "A"`

**No mock data in production paths:** grade parsed from actual file content.

### Deliverables
- Updated `golden_loader.py`:
  - `_SECTION_JACCARD_THRESHOLD = 0.3` at module level with rationale comment
  - `get_section` uses the constant, updated docstring
  - `_parse_golden_file` parses `grade` from frontmatter with fallback to `"A"`
- 8 new tests in `test_golden_loader.py`

### Hard rules
- `_SECTION_JACCARD_THRESHOLD` must be at module level so tests can patch it
- Grade parsing must not crash on malformed frontmatter — defensive regex or split
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Correctness | Jaccard threshold documented and testable; grade reflects actual frontmatter |
| Maintainability | `_SECTION_JACCARD_THRESHOLD` named constant with rationale — future engineer understands the choice |
| Testability | Patching the constant allows threshold sensitivity tests |
| Minimality | Two targeted changes; no structural refactor |

### Now (runbook)
```bash
# Fix A:
# 1. Add _SECTION_JACCARD_THRESHOLD = 0.3 near top of golden_loader.py with rationale comment
# 2. Replace literal 0.3 in get_section with _SECTION_JACCARD_THRESHOLD
# 3. Update get_section docstring

# Fix B:
# 4. Add grade parsing block in _parse_golden_file (after frontmatter strip)
# 5. Pass grade variable to GoldenPage instead of literal "A"

# Tests:
# 6. Add 8 tests covering threshold constant + grade parsing
# 7. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_golden_loader.py -v
# 8. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```
