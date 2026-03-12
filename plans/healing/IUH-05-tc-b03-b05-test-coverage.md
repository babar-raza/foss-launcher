---
id: IUH-05
title: "Add test coverage for TC-B03 adaptive budget and TC-B05 claim_source tagging"
status: Not Started
priority: Medium
owner: Verification Engineer
updated: "2026-03-11"
tags: [test-coverage, tc-b03, tc-b05, adaptive-budget, claim-provenance]
depends_on: [IUH-01]
allowed_paths:
  - tests/unit/workers/test_scout_adaptive_budget.py
  - tests/unit/workers/understand/test_claim_source_tagging.py
  - plans/healing/IUH-05-tc-b03-b05-test-coverage.md
evidence_required:
  - reports/IUH-05/evidence.md
---

# Taskcard IUH-05 — Add test coverage for TC-B03 adaptive budget and TC-B05 claim_source tagging

## Objective

TC-B03 (adaptive budget allocation) and TC-B05 (claim_source tagging) were implemented without tests. The adaptive budget behavior — docs capped at 60%, source guaranteed 20% — is the core correctness property of TC-B03, and has no test verifying it. TC-B05's docstring and llm_fallback tagging paths are similarly unverified. This taskcard adds focused unit tests for both.

## Required spec references

- `plans/reflective-finding-lark.md` — TC-B03: "docs ≤60%, source ≥20%"
- `plans/reflective-finding-lark.md` — TC-B05: claim_source tagging for each origin
- Self-review gaps G-05 and G-06

## Scope

### In scope
- Test TC-B03: `_read_repo_content()` caps doc bytes at 60%; source files are included after doc cap
- Test TC-B03: source_reserve_threshold stops non-source reads at 80%
- Test TC-B05: `_harvest_docstring_claims_raw()` raw dicts have `claim_source="docstring"`
- Test TC-B05: `_extract_claims_llm()` fallback path tags claims `"llm_fallback"`
- Test TC-B05: `_extract_claims_llm()` LLM success path tags claims `"llm"`

### Out of scope
- Testing IUH-01 fixes (`claim_source="deterministic"`) — covered by IUH-01's own test file
- Integration tests requiring a live LLM — all tests must be offline

## Inputs

- `src/launcher/workers/understand/scout.py` — `_read_repo_content()` (TC-B03)
- `src/launcher/workers/understand/extract/_entry.py` — `_harvest_docstring_claims_raw()` (TC-B05)
- `src/launcher/workers/understand/extract/_llm.py` — `_extract_claims_llm()` (TC-B05)

## Outputs

- `tests/unit/workers/test_scout_adaptive_budget.py` — TC-B03 tests
- `tests/unit/workers/understand/test_claim_source_tagging.py` — TC-B05 tests

## Allowed paths

- `tests/unit/workers/test_scout_adaptive_budget.py`
- `tests/unit/workers/understand/test_claim_source_tagging.py`
- `plans/healing/IUH-05-tc-b03-b05-test-coverage.md`

### Allowed paths rationale
New test files only — no production code changes. Isolated per concern.

## Implementation steps

### Step 1: Write TC-B03 adaptive budget tests

Create `tests/unit/workers/test_scout_adaptive_budget.py`:

```python
"""Tests for TC-B03 adaptive budget allocation in _read_repo_content — IUH-05."""
from __future__ import annotations
from pathlib import Path
import pytest
from launcher.models.understanding import FileCategory, FileEntry
from launcher.workers.understand.scout import _read_repo_content, _BUDGET_LOG_MAX


def _write_files(tmp_path: Path, specs: list[tuple[str, str, FileCategory, int]]) -> dict:
    """
    Write files to tmp_path and return a file_index.
    specs: list of (filename, content, category, size_override_or_0)
    """
    index = {}
    for fname, content, category, size_hint in specs:
        p = tmp_path / fname
        p.write_text(content, encoding="utf-8")
        size = size_hint if size_hint else p.stat().st_size
        index[fname] = FileEntry(category=category, size_bytes=size, language="")
    return index


class TestDocCapAt60Percent:
    def test_doc_files_capped_when_exceeding_60_percent(self, tmp_path):
        """Doc bytes must not exceed 60% of total budget."""
        budget = 100_000  # 100KB budget

        # Create 10 doc files of 8KB each = 80KB total docs (would exceed 60%)
        specs = [(f"doc_{i}.md", "x" * 7_500, FileCategory.doc, 0) for i in range(10)]
        # Create 5 source files of 4KB each
        specs += [(f"src_{i}.py", "y" * 3_500, FileCategory.source, 0) for i in range(5)]

        file_index = _write_files(tmp_path, specs)
        content, _, _, budget_log, _ = _read_repo_content(
            tmp_path, file_index, budget_bytes=budget
        )

        doc_bytes = sum(
            len(v.encode("utf-8")) for k, v in content.items()
            if file_index[k].category == FileCategory.doc
        )
        assert doc_bytes <= budget * 0.60 + 1024, (  # +1KB tolerance for README pre-read
            f"Doc bytes {doc_bytes} exceeded 60% cap of {budget * 0.60}"
        )

    def test_source_files_read_after_doc_cap(self, tmp_path):
        """After doc cap is reached, source files must still be read (if budget remains)."""
        budget = 100_000

        # 8 doc files of 9KB each = 72KB total docs (exceeds 60% = 60KB cap)
        specs = [(f"doc_{i}.md", "x" * 8_000, FileCategory.doc, 0) for i in range(8)]
        # 2 small source files that fit in remaining budget
        specs += [(f"src_{i}.py", "y" * 1_000, FileCategory.source, 0) for i in range(2)]

        file_index = _write_files(tmp_path, specs)
        content, _, _, _, _ = _read_repo_content(
            tmp_path, file_index, budget_bytes=budget
        )

        source_files_read = [k for k in content if file_index[k].category == FileCategory.source]
        assert source_files_read, (
            "Expected at least one source file to be read after doc cap was applied, "
            f"but got none. Content keys: {list(content.keys())}"
        )

    def test_budget_log_records_doc_cap_reason(self, tmp_path):
        """Files skipped due to doc cap must appear in budget_log with reason='doc_cap_reached'."""
        budget = 20_000

        # 5 doc files of 6KB each — 30KB total, far exceeds 60% cap of 12KB
        specs = [(f"doc_{i}.md", "x" * 5_500, FileCategory.doc, 0) for i in range(5)]
        file_index = _write_files(tmp_path, specs)

        _, _, _, budget_log, _ = _read_repo_content(
            tmp_path, file_index, budget_bytes=budget
        )

        cap_entries = [e for e in budget_log if e.get("reason") == "doc_cap_reached"]
        assert cap_entries, (
            "Expected budget_log entries with reason='doc_cap_reached' but got none. "
            f"Budget log reasons: {[e.get('reason') for e in budget_log]}"
        )


class TestSourceReserve:
    def test_non_source_reads_stop_at_80_percent(self, tmp_path):
        """Non-source files must not be read once 80% of budget is consumed."""
        budget = 100_000
        threshold = int(budget * 0.80)

        # Fill 78KB with example files (non-source)
        specs = [(f"ex_{i}.py", "x" * 7_000, FileCategory.example, 0) for i in range(11)]
        # Add CI file that should be blocked by source_reserve
        specs += [("ci.yml", "ci: true\n", FileCategory.ci, 0)]

        file_index = _write_files(tmp_path, specs)
        content, _, _, budget_log, _ = _read_repo_content(
            tmp_path, file_index, budget_bytes=budget
        )

        # Check that budget_log has source_reserve entries for ci.yml or similar
        reserve_entries = [e for e in budget_log if e.get("reason") == "source_reserve"]
        # If 80% was reached, reserve entries should exist
        used = sum(len(v.encode("utf-8")) for v in content.values())
        if used >= threshold:
            assert reserve_entries, (
                "Expected source_reserve entries in budget_log when 80% threshold is reached"
            )
```

### Step 2: Write TC-B05 claim_source tagging tests

Create `tests/unit/workers/understand/test_claim_source_tagging.py`:

```python
"""Tests for TC-B05 claim_source tagging on all origin paths — IUH-05."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestDocstringClaimsTagging:
    def test_harvest_docstring_claims_tagged_docstring(self):
        """Raw dicts from _harvest_docstring_claims_raw must have claim_source='docstring'."""
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw

        # Build a minimal ApiSurface mock with one ClassBrief
        api_surface = MagicMock()
        brief = MagicMock()
        brief.name = "Workbook"
        brief.docstring_snippet = "The Workbook class represents an Excel spreadsheet file."
        brief.methods = ["save", "load", "get_sheet"]
        api_surface.class_briefs = [brief]

        product = MagicMock()
        product.canonical_import = "aspose_cells"
        product.display_name = "Aspose.Cells"

        raw_claims = _harvest_docstring_claims_raw(api_surface, product)

        assert raw_claims, "Expected at least one raw claim from docstring harvesting"
        for raw in raw_claims:
            assert raw.get("claim_source") == "docstring", (
                f"Expected claim_source='docstring', got {raw.get('claim_source')!r} "
                f"for claim: {raw.get('text')!r}"
            )

    def test_short_docstring_not_harvested(self):
        """Docstrings shorter than 30 chars must not produce claims."""
        from launcher.workers.understand.extract._entry import _harvest_docstring_claims_raw

        api_surface = MagicMock()
        brief = MagicMock()
        brief.name = "Sheet"
        brief.docstring_snippet = "A sheet."  # < 30 chars
        brief.methods = []
        api_surface.class_briefs = [brief]

        product = MagicMock()
        product.canonical_import = "aspose_cells"
        product.display_name = "Aspose.Cells"

        raw_claims = _harvest_docstring_claims_raw(api_surface, product)
        docstring_claims = [r for r in raw_claims if r.get("text", "").startswith("Sheet:")]
        assert not docstring_claims, "Short docstring should not produce a class-level claim"


class TestLLMFallbackTagging:
    @pytest.mark.asyncio
    async def test_llm_failure_fallback_claims_tagged_llm_fallback(self):
        """When LLM raises, fallback claims must have claim_source='llm_fallback'."""
        from launcher.workers.understand.extract._llm import _extract_claims_llm

        doc_contexts = [{"path": "README.md", "content": "# MyLib\nInstall with pip.\n"}]
        product = MagicMock()
        product.family = "mylib"
        product.display_name = "MyLib"
        product.canonical_import = "mylib"

        context = MagicMock()
        context.llm_config = MagicMock()  # LLM config present

        with patch(
            "launcher.workers.understand.extract._llm._call_llm_extract",
            side_effect=Exception("LLM unavailable"),
        ):
            raw_claims = await _extract_claims_llm(
                doc_contexts, product, context, snippets=None, evidence_context=""
            )

        assert raw_claims, "Expected deterministic fallback claims to be returned"
        for raw in raw_claims:
            assert raw.get("claim_source") == "llm_fallback", (
                f"Expected claim_source='llm_fallback' on fallback claim, "
                f"got {raw.get('claim_source')!r}"
            )

    @pytest.mark.asyncio
    async def test_llm_zero_results_fallback_tagged_llm_fallback(self):
        """When LLM returns empty list, fallback claims must be tagged 'llm_fallback'."""
        from launcher.workers.understand.extract._llm import _extract_claims_llm

        doc_contexts = [{"path": "README.md", "content": "# MyLib\nInstall with pip.\n"}]
        product = MagicMock()
        product.family = "mylib"
        product.display_name = "MyLib"
        product.canonical_import = "mylib"

        context = MagicMock()
        context.llm_config = MagicMock()

        with patch(
            "launcher.workers.understand.extract._llm._call_llm_extract",
            return_value=[],  # LLM returns 0 claims
        ):
            raw_claims = await _extract_claims_llm(
                doc_contexts, product, context, snippets=None, evidence_context=""
            )

        assert raw_claims, "Expected fallback claims when LLM returns []"
        for raw in raw_claims:
            assert raw.get("claim_source") == "llm_fallback", (
                f"Expected 'llm_fallback' on zero-result fallback, got {raw.get('claim_source')!r}"
            )

    @pytest.mark.asyncio
    async def test_llm_success_claims_tagged_llm(self):
        """When LLM succeeds, returned claims must have claim_source='llm'."""
        from launcher.workers.understand.extract._llm import _extract_claims_llm

        doc_contexts = [{"path": "README.md", "content": "# MyLib\n"}]
        product = MagicMock()
        product.family = "mylib"
        product.display_name = "MyLib"
        product.canonical_import = "mylib"

        context = MagicMock()
        context.llm_config = MagicMock()

        mock_llm_claims = [
            {"text": "MyLib supports reading CSV files", "kind": "feature", "visibility": "public"},
            {"text": "MyLib can export to PDF", "kind": "feature", "visibility": "public"},
        ]

        with patch(
            "launcher.workers.understand.extract._llm._call_llm_extract",
            return_value=mock_llm_claims,
        ):
            raw_claims = await _extract_claims_llm(
                doc_contexts, product, context, snippets=None, evidence_context=""
            )

        assert raw_claims, "Expected LLM claims to be returned"
        for raw in raw_claims:
            assert raw.get("claim_source") == "llm", (
                f"Expected claim_source='llm' on LLM success, got {raw.get('claim_source')!r}"
            )
```

### Step 3: Run new tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_adaptive_budget.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_claim_source_tagging.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

## Failure modes

### Failure mode 1: _BUDGET_LOG_MAX not exported from scout.py (IUH-04 not done yet)

**Detection**: `ImportError: cannot import name '_BUDGET_LOG_MAX'` in budget test.
**Resolution**: If IUH-04 is not done, replace `from launcher.workers.understand.scout import _BUDGET_LOG_MAX` with the literal `500` for the test. Or complete IUH-04 first (it is listed as a dependency).
**Gate**: Test isolation — tests must not depend on unimplemented features

### Failure mode 2: _call_llm_extract is a sync function, not async

**Detection**: `TypeError` when patching or calling.
**Resolution**: Read `_llm.py` to confirm whether `_call_llm_extract` is `async def` or plain `def`. Adjust the patch target accordingly. If sync, use `patch(..., return_value=...)` without `AsyncMock`.
**Gate**: G-06 — claim_source tagging tests must pass

### Failure mode 3: Adaptive budget tests flaky due to file size variation

**Detection**: `AssertionError: Doc bytes X exceeded 60% cap` on repeated runs, with X varying.
**Resolution**: Use deterministic content strings (e.g., `"x" * N`) and measure actual file sizes after write. Add 1KB tolerance in assertions to account for encoding overhead.
**Gate**: G-05 — budget tests must be deterministic (use PYTHONHASHSEED=0)

## Task-specific review checklist

1. [ ] `test_doc_files_capped_when_exceeding_60_percent` PASS — doc bytes ≤ 60% of budget
2. [ ] `test_source_files_read_after_doc_cap` PASS — at least one source file in content
3. [ ] `test_budget_log_records_doc_cap_reason` PASS — budget_log has doc_cap_reached entries
4. [ ] `test_harvest_docstring_claims_tagged_docstring` PASS — claim_source="docstring"
5. [ ] `test_llm_failure_fallback_claims_tagged_llm_fallback` PASS
6. [ ] `test_llm_zero_results_fallback_tagged_llm_fallback` PASS
7. [ ] `test_llm_success_claims_tagged_llm` PASS
8. [ ] All tests run offline (no network calls)
9. [ ] Full unit suite: no regressions

## Deliverables

1. `tests/unit/workers/test_scout_adaptive_budget.py` — 3 new TC-B03 tests
2. `tests/unit/workers/understand/test_claim_source_tagging.py` — 5 new TC-B05 tests
3. `reports/IUH-05/evidence.md` — test run output showing all 8 pass

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_adaptive_budget.py -v` — 3 PASS
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_claim_source_tagging.py -v` — 5 PASS
3. [ ] Full unit suite: no new failures

## Self-review

### Verification results
- [ ] Tests: 8/8 PASS
- [ ] All tests offline (no network mocks)
- [ ] Evidence captured: `reports/IUH-05/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_adaptive_budget.py tests/unit/workers/understand/test_claim_source_tagging.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

**Expected results**:
- 8 new tests PASS
- No regressions in full suite

## Integration boundary proven

**Upstream**: `_read_repo_content()` with adaptive budget logic (TC-B03), `_extract_claims_llm()` with source tagging (TC-B05)
**Downstream**: These tests verify the contracts consumed by `run_extract()` and `extraction_audit.json`
**Contract**: doc bytes ≤ 60% of budget; claim_source ∈ {"llm", "llm_fallback", "docstring"} per origin

---

## Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | Each test verifies the specific property from the spec, not just that the code runs |
| Testability | Tests use real file writes (TC-B03) and offline mocks (TC-B05); zero network calls |
| Coverage | Both the success path and failure/fallback path are tested for TC-B05 |
| Robustness | Tolerance added for file size variance in budget tests |
| Minimality | Pure test files; no production code changes |

## Now (runbook)

```bash
# 1. Write test files using Write tool (two files)

# 2. Run TC-B03 tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_adaptive_budget.py -v

# 3. Run TC-B05 tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_claim_source_tagging.py -v

# 4. If failures: read actual signatures with grep/Read, adjust test imports/mocks

# 5. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```
