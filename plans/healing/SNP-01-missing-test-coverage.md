---
id: SNP-01
title: "Add dedup + source_file tests for _extract_snippets()"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [understand, snippets, tests, TC-4063]
depends_on: [TC-4063]
allowed_paths:
  - plans/healing/SNP-01-missing-test-coverage.md
  - tests/unit/workers/understand/test_extract.py
evidence_required:
  - reports/SNP-01/evidence.md
---

# SNP-01 — Add dedup + source_file tests for `_extract_snippets()`

## Objective

TC-4063 added content-hash deduplication and `source_file` provenance to `_extract_snippets()`,
but zero new tests were written to verify this behaviour. This is a blocker: untested code
that changes observable extraction behaviour is not shippable.

## Required spec references

- `specs/worker_understand.md` (Phase B.3: snippet extraction contract)
- `specs/claims_evidence.md` (Snippet model: source_file, deduplication)

## Scope

### In scope
- Add `TestSnippetDeduplication` class with at least two test methods:
  - `test_identical_code_in_two_files_yields_one_snippet` — same code block in README and docs/ → 1 snippet
  - `test_distinct_code_in_same_file_both_kept` — two different code blocks → 2 snippets
- Add `TestSnippetProvenance` class with at least one test method:
  - `test_source_file_populated_on_extracted_snippet` — extracted snippet has non-empty `source_file`

### Out of scope
- Testing `line_start`/`line_end` population (always None for fenced blocks — covered by SNP-06)
- Integration tests that require a live repo clone

## Inputs

- `src/launcher/workers/understand/extract/_snippets.py` (function under test)
- `tests/unit/workers/understand/test_extract.py` (existing test file)

## Outputs

- `tests/unit/workers/understand/test_extract.py` with two new test classes (min 3 test methods total)
- `reports/SNP-01/evidence.md` with pytest output

## Allowed paths

- plans/healing/SNP-01-missing-test-coverage.md
- tests/unit/workers/understand/test_extract.py

### Allowed paths rationale
Only the test file needs changing — source code is unchanged, schema is unchanged.

## Implementation steps

### Step 1: Locate the existing test file section markers

Read `tests/unit/workers/understand/test_extract.py` and identify the last section
(currently the tombstone comment for section 7). Append the new test classes after it.

### Step 2: Write `TestSnippetDeduplication`

```python
# ===========================================================================
# 8. Snippet deduplication (TC-4063)
# ===========================================================================
class TestSnippetDeduplication:
    """_extract_snippets() deduplicates by SHA-256 content hash."""

    def _make_repo(self, tmp_path, files: dict[str, str]) -> Path:
        """Create a minimal repo structure."""
        for rel, content in files.items():
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return tmp_path

    def test_identical_code_in_two_files_yields_one_snippet(self, tmp_path):
        """Same fenced code block in README and docs/ → exactly 1 snippet extracted."""
        code_block = "```python\nimport foo\nresult = foo.bar()\nprint(result)\n```"
        self._make_repo(tmp_path, {
            "README.md": f"# Intro\n\n{code_block}\n",
            "docs/guide.md": f"# Guide\n\n{code_block}\n",
        })
        repo_info = {"name": "myrepo", "description": "test", "topics": []}
        product = MagicMock()
        product.name = "myrepo"
        api_surface = {}
        claims = []
        snippets = _extract_snippets(tmp_path, repo_info, product, api_surface, claims)
        python_snippets = [s for s in snippets if s.language == "python"]
        assert len(python_snippets) == 1, (
            f"Expected 1 deduplicated snippet, got {len(python_snippets)}"
        )

    def test_distinct_code_in_same_file_both_kept(self, tmp_path):
        """Two different fenced code blocks in the same file are both kept."""
        self._make_repo(tmp_path, {
            "README.md": (
                "# Intro\n\n"
                "```python\nimport foo\nfoo.init()\n```\n\n"
                "```python\nimport bar\nbar.run()\n```\n"
            ),
        })
        repo_info = {"name": "myrepo", "description": "test", "topics": []}
        product = MagicMock()
        product.name = "myrepo"
        api_surface = {}
        claims = []
        snippets = _extract_snippets(tmp_path, repo_info, product, api_surface, claims)
        python_snippets = [s for s in snippets if s.language == "python"]
        assert len(python_snippets) >= 2, (
            f"Expected >=2 distinct snippets, got {len(python_snippets)}"
        )
```

### Step 3: Write `TestSnippetProvenance`

```python
# ===========================================================================
# 9. Snippet provenance — source_file populated (TC-4063)
# ===========================================================================
class TestSnippetProvenance:
    """_extract_snippets() populates source_file on each Snippet."""

    def test_source_file_populated_on_extracted_snippet(self, tmp_path):
        """Every extracted snippet must have a non-empty source_file."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "# MyLib\n\n```python\nimport mylib\nmylib.run()\n```\n",
            encoding="utf-8",
        )
        repo_info = {"name": "mylib", "description": "test", "topics": []}
        product = MagicMock()
        product.name = "mylib"
        api_surface = {}
        claims = []
        snippets = _extract_snippets(tmp_path, repo_info, product, api_surface, claims)
        assert snippets, "Expected at least one snippet"
        for s in snippets:
            assert s.source_file, (
                f"Snippet.source_file must be non-empty; got {s.source_file!r}"
            )
```

### Step 4: Verify imports at top of test file

Confirm `_extract_snippets` is imported (it should already be via the `__init__.py` re-export).
Add `MagicMock` import if not already present: `from unittest.mock import MagicMock`.
Add `Path` import from `pathlib` if not already present.

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -k "snippet"
```

Capture output to `reports/SNP-01/evidence.md`.

## Failure modes

### Failure mode 1: `_extract_snippets` import not available in test file

**Detection**: `ImportError: cannot import name '_extract_snippets'`
**Resolution**: Check `src/launcher/workers/understand/extract/__init__.py` — confirm
`_extract_snippets` is in the re-exports from `._snippets`. If not, add it.
**Gate**: Module import check

### Failure mode 2: Dedup test finds 2 snippets instead of 1

**Detection**: `AssertionError: Expected 1 deduplicated snippet, got 2`
**Resolution**: Verify the dedup hash is applied to `code.strip()` in `_snippets.py`.
Read the extraction loop and confirm `seen_hashes` is checked before appending.
**Gate**: Unit test

### Failure mode 3: source_file populated with absolute path instead of relative

**Detection**: `AssertionError: source_file contains absolute path /tmp/...`
**Resolution**: Confirm `rel_path = str(p.relative_to(repo_dir))` is used, not `str(p)`.
**Gate**: Unit test assertion on `source_file` content

## Task-specific review checklist

1. [ ] `TestSnippetDeduplication` class present with 2 test methods
2. [ ] `TestSnippetProvenance` class present with 1 test method
3. [ ] All 3 new test methods pass with `PYTHONHASHSEED=0`
4. [ ] No mock of `_extract_snippets` internals — tests exercise the real function
5. [ ] `source_file` assertion checks for non-empty string, not a specific value
6. [ ] Dedup test uses real content from two separate files, not mocked I/O
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — no guide trigger from test-only change
11. [ ] N/A — no new docs/guides/ file added

## Deliverables

1. `tests/unit/workers/understand/test_extract.py` with 2 new test classes (sections 8 and 9)
2. `reports/SNP-01/evidence.md` with full pytest `-v` output

## Acceptance checks

1. [ ] `grep -c "class TestSnippetDeduplication" tests/unit/workers/understand/test_extract.py` → 1
2. [ ] `grep -c "class TestSnippetProvenance" tests/unit/workers/understand/test_extract.py` → 1
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -k "snippet"` → all PASS

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/SNP-01/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -k "snippet"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q --tb=short
```

**Expected results**:
- 3 new tests (2 dedup + 1 provenance) pass
- Full unit suite passes

## Integration boundary proven

**Upstream**: `_extract_snippets()` in `_snippets.py` (unchanged)
**Downstream**: Test assertions on `Snippet.source_file` and dedup count
**Contract**: `Snippet.source_file: str` (non-empty for fenced blocks); dedup by sha256[:16] of `code.strip()`
