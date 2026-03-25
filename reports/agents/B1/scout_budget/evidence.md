# Agent B1 — Evidence

## TC-4262: _MAX_SOURCE_CHARS value after change

```
_MAX_SOURCE_CHARS = 128_000
```
File: `src/launcher/workers/understand/extract/_llm.py`, line 19

## TC-4263: _DEFAULT_BUDGET_BYTES value after change

```
_DEFAULT_BUDGET_BYTES = 5_000_000
```
File: `src/launcher/workers/scout/scout.py`, line 267

## TC-4263: Per-file caps dict values

```python
_PER_FILE_MAX_CHARS: dict[str, int] = {
    "doc": 500_000,
    "source": 300_000,
}
_PER_FILE_MAX_CHARS_DEFAULT = 100_000
```
File: `src/launcher/workers/scout/scout.py` (inserted after line 267)

## TC-4264: _doc_skip_reason("docs/implementation_status.md") behavior

`_doc_skip_reason("docs/implementation_status.md")` returns `"doc_ineligible_meta"`.

Reasoning: `stem = _normalized_stem("docs/implementation_status.md")` → `"implementationstatus"`.
The keyword `"implementation"` is in `_META_DOC_ROOT_KEYWORDS`. `stem != "readme"` is True.
Therefore the third guard fires and returns `"doc_ineligible_meta"`.

No root-level path guard (`"/" not in lower`) was present in the code — the function already
applies keyword filtering at all depths.

## Test run output

```
tests/unit/workers/test_scout.py tests/unit/workers/test_scout_budget_log_cap.py tests/unit/workers/test_understand.py

........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 58%]
........................................................................ [ 78%]
........................................................................ [ 97%]
.........                                                                [100%]
369 passed in 28.17s
```

All 369 tests pass. No regressions.

## Specific new tests executed

```
tests/unit/workers/test_scout.py::TestScoutBudgetConstants::test_default_budget_bytes_5mb PASSED
tests/unit/workers/test_scout.py::TestScoutBudgetConstants::test_per_file_cap_doc_500kb PASSED
tests/unit/workers/test_scout.py::TestScoutBudgetConstants::test_per_file_cap_source_300kb PASSED
tests/unit/workers/test_scout.py::TestMetaDocSubdirFiltering::test_metadoc_subdir_filtered PASSED
tests/unit/workers/test_scout.py::TestMetaDocSubdirFiltering::test_metadoc_roadmap_subdir_filtered PASSED
tests/unit/workers/test_scout.py::TestMetaDocSubdirFiltering::test_quickstart_not_filtered PASSED
tests/unit/workers/test_scout.py::TestMetaDocSubdirFiltering::test_readme_subdir_not_filtered PASSED
tests/unit/workers/test_understand.py::TestLLMDocWindowConstant::test_max_source_chars_128k PASSED
```
