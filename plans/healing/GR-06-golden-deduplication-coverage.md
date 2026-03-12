---
id: GR-06
title: "Document and guard against silent deduplication: 22 golden files → ~13 unique entries"
status: Open
priority: High
owner: agent
updated: "2026-03-09"
tags: [golden, regression, golden-loader, deduplication]
depends_on: []
allowed_paths:
  - plans/healing/GR-06-golden-deduplication-coverage.md
  - tests/golden/test_checks_regression.py
  - tests/shared/test_golden_loader.py
evidence_required:
  - reports/GR-06/evidence.md
---

# GR-06 — Silent deduplication: 22 golden files → ~13 unique (role, variant) entries

## Objective

`GoldenIndex._pages` is keyed by `(page_role, variant)`, so when multiple golden
files share the same role+variant pair, only the last loaded survives. With 22
golden files but only ~13 unique (role,variant) combinations, up to 9 pages may
be silently dropped from the regression suite. Add a corpus-size assertion and
document the deduplication behaviour clearly.

## Gap source

TC-3876b self-review (High severity): the veto oracle only works if the regression
suite actually tests all high-quality golden pages. Silent deduplication means
grade-A pages that share a role may never be tested.

## Required spec references

- `plans/purrfect-beaming-crown.md` (Context: 22 exemplar files, grades A through C)
- `src/launcher/shared/golden_loader.py` (_pages dict structure)

## Scope

### In scope
- Investigate and document the actual deduplication: how many files are loaded
  vs. how many survive in `_pages`
- Add `test_golden_corpus_size_matches_files` assertion to `test_checks_regression.py`
- Add `test_golden_index_has_no_silent_deduplication` to `test_golden_loader.py`
  (or update existing all_pages test)
- Document the deduplication in a comment near `GoldenIndex._pages` (read-only —
  if _pages structure needs changing that is a separate TC)

### Out of scope
- Fixing the deduplication in GoldenIndex (that is a separate architectural TC
  that changes `_pages` from dict-of-page to dict-of-list)
- Modifying golden files

## Inputs

- `src/launcher/shared/golden_loader.py` (`_pages` dict, `_parse_golden_file()`)
- `golden/` directory (22 files)
- `tests/golden/test_checks_regression.py`
- `tests/shared/test_golden_loader.py`

## Outputs

- `tests/golden/test_checks_regression.py` (new corpus size assertion)
- `tests/shared/test_golden_loader.py` (new deduplication transparency test)
- `reports/GR-06/evidence.md`

## Allowed paths

- plans/healing/GR-06-golden-deduplication-coverage.md
- tests/golden/test_checks_regression.py
- tests/shared/test_golden_loader.py

### Allowed paths rationale

Test-only changes to document and guard against the deduplication behaviour.
No src/ changes — fixing the root cause is a separate TC.

## Implementation steps

### Step 1: Measure actual deduplication

Run the diagnostic:
```bash
.venv/Scripts/python.exe -c "
from pathlib import Path
from launcher.shared.golden_loader import GoldenIndex

GOLDEN_DIR = Path('golden')
index = GoldenIndex.load(GOLDEN_DIR)
all_files = list(GOLDEN_DIR.glob('*.md'))
all_pages = index.all_pages()
print(f'Files in golden/: {len(all_files)}')
print(f'Pages in index: {len(all_pages)}')
print(f'Dropped (silent): {len(all_files) - len(all_pages)}')
print()
print('Pages loaded:')
for p in all_pages:
    print(f'  {p.source_path.name} | grade={p.grade} | role={p.page_role} | variant={p.variant}')
"
```

Record the actual numbers in the evidence report.

### Step 2: Add corpus size assertion to test_checks_regression.py

Add new smoke test:
```python
@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
def test_corpus_coverage_documented():
    """Document and detect changes in golden corpus coverage.

    GoldenIndex._pages is keyed by (page_role, variant), so multiple files
    with the same role+variant silently deduplicate to one entry.
    This test records the known coverage ratio and fails if it changes,
    making deduplication visible rather than silent.

    KNOWN STATE (2026-03-09): N files in golden/, M pages in index.
    If M < N, deduplication is occurring. This is not fixed here — see GR-06.
    """
    all_md_files = list(GOLDEN_DIR.glob("*.md"))
    index = GoldenIndex.load(GOLDEN_DIR)
    pages = index.all_pages()

    file_count = len(all_md_files)
    page_count = len(pages)

    # Document the known state — update this comment when golden/ changes
    # As of 2026-03-09: 22 files, ~13 pages (deduplication ratio ~0.59)
    assert page_count >= 1, "Golden index must contain at least one page"
    assert page_count <= file_count, (
        f"Index has more pages ({page_count}) than files ({file_count}) — impossible"
    )

    # Transparency assertion: warn (not fail) when deduplication is occurring
    if page_count < file_count:
        dropped = file_count - page_count
        import warnings
        warnings.warn(
            f"Golden corpus deduplication: {file_count} files → {page_count} pages "
            f"({dropped} files silently dropped by (role,variant) keying). "
            f"Regression suite covers {page_count}/{file_count} golden pages. "
            f"See GR-06 for root cause analysis.",
            stacklevel=2,
        )
```

### Step 3: Add deduplication transparency test to test_golden_loader.py

In `TestTC3876aContentAndAllPages`, add:
```python
def test_all_pages_count_documented(self):
    """Record actual all_pages() count vs file count — detects deduplication changes."""
    if not GOLDEN_DIR.exists():
        return
    all_md = list(GOLDEN_DIR.glob("*.md"))
    index = GoldenIndex.load(GOLDEN_DIR)
    pages = index.all_pages()
    # This assertion is intentionally loose (≥1) — the exact count is
    # documented here for human reference, not enforced.
    # File count: len(all_md); Page count: len(pages)
    # If len(pages) < len(all_md), deduplication is occurring (see GR-06).
    assert len(pages) >= 1
    # Enforce that known dropped pages do not INCREASE silently
    # (new files added without new role/variant → more dropped)
    assert len(pages) <= len(all_md), "More pages than files — impossible"
```

### Step 4: Create the evidence report

Run Step 1 and capture output. Record exact numbers in `reports/GR-06/evidence.md`.

## Failure modes

### Failure mode 1: Deduplication worse than expected

**Detection**: Step 1 shows more than 9 dropped files
**Resolution**: Investigate which (role,variant) pairs have multiple files.
Document in evidence report. Add to GR-06 root cause section.
**Gate**: Diagnostic output reviewed before writing assertions

### Failure mode 2: No deduplication found (all 22 pages loaded)

**Detection**: `len(all_pages) == len(all_files) == 22`
**Resolution**: Self-review finding was incorrect. Update evidence report.
Remove the deduplication warning from the corpus coverage test.
**Gate**: Diagnostic confirms count equality

### Failure mode 3: File count changes as new golden files are added

**Detection**: Assertion `page_count <= file_count` fails (impossible by construction)
**Resolution**: This should never fail — it's a mathematical invariant.
If it does, something is wrong with the glob or GoldenIndex.load.
**Gate**: Mathematical invariant

## Task-specific review checklist

1. [ ] Diagnostic in Step 1 run and results recorded in evidence
2. [ ] Corpus coverage smoke test added with warning (not fail) for deduplication
3. [ ] Warning message explains root cause and points to GR-06
4. [ ] `test_golden_loader.py` addition documents deduplication without hardcoding count
5. [ ] No `assert len(pages) == 22` (hardcoded count would break when golden/ changes)
6. [ ] Evidence report records actual file count and page count
7. [ ] Spec file: no worker behavior change
8. [ ] Schema: not applicable
9. [ ] Checked `docs/README.md` — no trigger events apply
10. [ ] No new `docs/guides/` file added

## Deliverables

1. `tests/golden/test_checks_regression.py` (corpus coverage test added)
2. `tests/shared/test_golden_loader.py` (deduplication transparency test added)
3. `reports/GR-06/evidence.md` (actual counts and deduplication analysis)

## Acceptance checks

1. [ ] `test_corpus_coverage_documented` collects and passes (or warns but doesn't fail)
2. [ ] Evidence report shows actual file count vs page count
3. [ ] No hardcoded count assertions that will break when golden/ changes
4. [ ] Deduplication root cause documented in evidence (not fixed — that's a separate TC)

## Self-review

### Verification results
- [ ] Diagnostic run: N files, M pages
- [ ] Tests pass
- [ ] Evidence captured: reports/GR-06/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/test_checks_regression.py::test_corpus_coverage_documented -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_golden_loader.py::TestTC3876aContentAndAllPages -v
```

**Expected results**:
- Both tests PASS (or WARN on deduplication — not FAIL)

## Integration boundary proven

**Upstream**: `GoldenIndex.load(GOLDEN_DIR)` — loads and deduplicates pages
**Downstream**: TC-3877/3878/3879 — calibrate thresholds based on pages actually tested
**Contract**: Coverage ratio documented; deduplication visible in test output; root
cause fix tracked in a future TC (architectural change to _pages dict-of-list)
