---
id: TC-3833
title: "golden_index_foundation"
status: Done
priority: Normal
owner: "claude-agent"
updated: "2026-03-08"
tags: [golden, shared, index]
depends_on: []
allowed_paths:
  - src/launcher/shared/golden_loader.py
  - src/launcher/shared/__init__.py
  - tests/shared/test_golden_loader.py
  - tests/shared/__init__.py
  - plans/taskcards/TC-3833_golden_index_foundation.md
evidence_required:
  - reports/TC-3833/evidence.md
---

# Taskcard TC-3833 — golden_index_foundation

## Objective

Create `GoldenIndex`, an in-memory index that loads curated A/B exemplar `.md` files
from `golden/` and exposes structured query APIs (get, get_section with 3-level fallback,
get_spec, select_for_tier). This index is the foundation for golden-assisted generation
and planner self-review introduced in TC-3834.

## Required spec references

- `golden/` directory (curated exemplar files, A-grade markdown, subdomain-organised)
- `src/launcher/shared/` (shared utility layer consumed by all workers)

## Scope

### In scope
- `GoldenIndex.load()` that parses all `.md` files under `golden/` recursively
- `GoldenPage`, `GoldenSection`, `GoldenBlockSpec` dataclasses
- `build_block_spec()` helper deriving structural contracts from a golden section
- `get_section()` with 3-level heading fallback: exact, substring, Jaccard >= 0.5
- `select_for_tier()` preferring "standard" for A/B tiers and "minimal" for C
- Export of public symbols from `src/launcher/shared/__init__.py`
- Unit tests in `tests/shared/test_golden_loader.py`

### Out of scope
- Actual usage of golden specs inside the Generate worker (TC-3835+)
- LLM-assisted heading matching (future work)
- Golden file authoring / editing tooling

## Inputs

- `golden/**/*.md` — curated A-grade exemplar files organized by subdomain
- Python 3.13 standard library (pathlib, re, dataclasses)

## Outputs

- `src/launcher/shared/golden_loader.py` — GoldenIndex implementation
- `src/launcher/shared/__init__.py` — updated to export golden symbols
- `tests/shared/test_golden_loader.py` — 7 unit tests, all passing

## Allowed paths

- src/launcher/shared/golden_loader.py
- src/launcher/shared/__init__.py
- tests/shared/test_golden_loader.py
- tests/shared/__init__.py
- plans/taskcards/TC-3833_golden_index_foundation.md

### Allowed paths rationale
- `golden_loader.py`: new module implementing the index
- `shared/__init__.py`: re-exports public API
- `tests/shared/`: new test directory for shared module tests
- `plans/taskcards/`: taskcard document itself

## Implementation steps

### Step 1: Explore golden/ directory

Listed all `.md` files in `golden/` recursively. Found 22 `.md` files organized under
5 subdomains: `blog.aspose.org`, `docs.aspose.org`, `kb.aspose.org`,
`products.aspose.org`, `reference.aspose.org`. Read sample files to understand frontmatter,
`## heading` structure, and variant naming convention (`.variant-minimal.md`, etc.).

### Step 2: Create src/launcher/shared/golden_loader.py

Implemented all dataclasses (`GoldenSection`, `GoldenBlockSpec`, `GoldenPage`),
`build_block_spec()`, `GoldenIndex` class with `load()`, `get()`, `get_section()`,
`get_spec()`, `select_for_tier()`, and private helpers `_infer_role_variant()`,
`_parse_golden_file()`, `_parse_sections()`.

### Step 3: Update src/launcher/shared/__init__.py

Added imports and `__all__` exporting `GoldenIndex`, `GoldenBlockSpec`, `GoldenSection`,
`GoldenPage`, `build_block_spec`.

### Step 4: Create tests/shared/__init__.py and test_golden_loader.py

Created `tests/shared/` directory with `__init__.py` and 7-test file covering:
empty-dir load, missing-dir load, get on empty index, get_section on empty index,
build_block_spec with code, tier-C min_words scaling, select_for_tier with empty index.

### Step 5: Run targeted tests

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_golden_loader.py -v
```
Result: 7 passed in 0.34s.

### Step 6: Run full test suite

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
Result: 2366 passed in 54.94s.

### Step 7: Smoke test

```python
from pathlib import Path
from launcher.shared.golden_loader import GoldenIndex
idx = GoldenIndex.load(Path("golden"))
print(f"Indexed {len(idx)} golden pages")
# Output: Indexed 7 golden pages
```

## Failure modes

### Failure mode 1: Corrupt or unreadable golden file

**Detection**: `_parse_golden_file` raises an exception during `rglob` iteration.
**Resolution**: The outer `try/except Exception: pass` in `GoldenIndex.load()` silently skips
the file — graceful degradation. Investigate the file encoding or syntax manually.
**Gate**: Graceful degradation policy (no crash on startup).

### Failure mode 2: Variant key collision (same page_role + variant from two files)

**Detection**: `index._pages` key `(page_role, variant)` is overwritten by the last file
in sorted order. The `section_index` role experiences this with 15 `_index.md` files.
**Resolution**: The last file in sorted order wins. This is intentional for `_index` files
(they share the same structural contract). For unique roles this is not a problem.
**Gate**: `len(index)` will be less than the number of `.md` files processed.

### Failure mode 3: Jaccard false positive for very short headings

**Detection**: Single-word headings may match unrelated sections at Jaccard >= 0.5
if both share one word.
**Resolution**: The 3-level fallback ensures exact and substring are tried first;
Jaccard is the last resort. Callers should treat results as approximate hints, not contracts.
**Gate**: `get_section()` returns `Optional[GoldenSection]`; callers must handle `None`.

### Failure mode 4: golden/ directory absent at runtime

**Detection**: `GoldenIndex.load(Path("golden"))` returns an empty index (len=0).
**Resolution**: Ensure the `golden/` directory is present in the working directory.
When running tests from `tests/shared/`, the test uses `@pytest.mark.skipif` if absent.
**Gate**: `test_load_missing_dir_returns_empty` covers this case.

## Task-specific review checklist

1. [x] `GoldenIndex.load()` handles missing `golden/` directory without raising exceptions
2. [x] `get_section()` implements all three levels: exact, substring, Jaccard >= 0.5
3. [x] `build_block_spec()` produces smaller `min_words` for tier C than tier B
4. [x] `_parse_sections()` correctly skips near-empty sections (word_count < 5)
5. [x] Frontmatter (YAML between `---`) is stripped before section parsing
6. [x] All 5 public symbols are exported from `src/launcher/shared/__init__.py`
7. [x] `tests/shared/__init__.py` created so pytest discovers the new package

## Deliverables

1. `src/launcher/shared/golden_loader.py` — full GoldenIndex implementation
2. `src/launcher/shared/__init__.py` — updated exports
3. `tests/shared/test_golden_loader.py` — 7 passing tests
4. `tests/shared/__init__.py` — package marker

## Acceptance checks

1. [x] `tests/shared/test_golden_loader.py` — 7/7 PASS
2. [x] Full suite `tests/` — 2366/2366 PASS (0 failures)
3. [x] Smoke test confirms `Indexed 7 golden pages` from real `golden/` directory
4. [x] `from launcher.shared import GoldenIndex` imports without error
5. [x] `golden_loader.py` exists at the correct path

## Self-review

### Verification results
- [x] Tests: 7/7 PASS (targeted), 2392/2392 PASS (full suite, run 2026-03-08)
- [x] GoldenIndex.load() loads 7 distinct (role, variant) pages from golden/ directory
- [x] Graceful degradation confirmed: missing dir returns empty index (test_load_missing_dir_returns_empty PASS)
- [x] Evidence file: `reports/TC-3833/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_golden_loader.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
tests/shared/test_golden_loader.py::test_load_indexes_files PASSED
tests/shared/test_golden_loader.py::test_load_missing_dir_returns_empty PASSED
tests/shared/test_golden_loader.py::test_get_returns_none_for_unknown_role PASSED
tests/shared/test_golden_loader.py::test_get_section_no_match_returns_none PASSED
tests/shared/test_golden_loader.py::test_build_block_spec_with_code PASSED
tests/shared/test_golden_loader.py::test_build_block_spec_tier_c_min_words PASSED
tests/shared/test_golden_loader.py::test_select_for_tier_c_prefers_minimal PASSED
7 passed in 0.34s

GoldenIndex pages indexed: 7
Page keys: [('feature_blog', 'standard'), ('section_index', 'standard'), ('workflow_page', 'standard'), ('installation', 'standard'), ('license', 'standard'), ('howto_article', 'standard'), ('api_reference', 'standard')]

2392 passed in 53.28s
```

## Integration boundary proven

**Upstream**: `golden/` directory — curated A-grade `.md` exemplar files authored by content team
**Downstream**: `TC-3834` planner self-review; future Generate worker golden-spec enforcement
**Contract**: `GoldenIndex.get(page_role, variant) -> Optional[GoldenPage]`;
`GoldenIndex.get_section(page_role, variant, heading) -> Optional[GoldenSection]`;
`GoldenIndex.get_spec(page_role, variant, heading) -> Optional[GoldenBlockSpec]`
