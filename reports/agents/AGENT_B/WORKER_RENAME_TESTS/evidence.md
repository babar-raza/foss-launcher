# Agent B2 - Worker Rename Test File Evidence

**Date**: 2026-02-19
**Task**: Update import paths and string references in test files for worker rename refactor
**Agent**: B2

---

## Summary

All 25 test files specified in the task were successfully processed. Import paths and string
references were updated to reflect the worker rename map.

---

## Rename Map Applied

| Old Name | New Name |
|---|---|
| `w7_content_reviewer` | `w7_content_reviewer` |
| `W7.ContentReviewer` | `W7.ContentReviewer` |
| `w8_linker_and_patcher` | `w8_linker_and_patcher` |
| `W8.LinkerAndPatcher` | `W8.LinkerAndPatcher` |
| `w9_validator` | `w9_validator` |
| `W9.Validator` | `W9.Validator` |
| `w10_fixer` | `w10_fixer` |
| `W10.Fixer` | `W10.Fixer` |
| `w11_pr_manager` | `w11_pr_manager` |
| `W11.PRManager` | `W11.PRManager` |
| `w6_seo_optimizer` | `w6_seo_optimizer` |
| `W6.SEOOptimizer` | `W6.SEOOptimizer` |

---

## GROUP 1: Content Reviewer test files (in w7_content_reviewer/ dir)

### `tests/unit/workers/w7_content_reviewer/test_worker.py`
- REPLACED: `launch.workers.w7_content_reviewer` → `launch.workers.w7_content_reviewer` (1 occurrence)
- REPLACED: `W7 ContentReviewer` → `W7 ContentReviewer` in docstrings (2 occurrences)

### `tests/unit/workers/w7_content_reviewer/test_auto_fixes.py`
- REPLACED: `launch.workers.w7_content_reviewer` → `launch.workers.w7_content_reviewer` (2 occurrences, replace_all)
- REPLACED: `W7 ContentReviewer Phase 5` → `W7 ContentReviewer Phase 5` in docstring
- REPLACED: `"W7_REVIEW: low_content_density"` → `"W7_REVIEW: low_content_density"` (1 occurrence)

### `tests/unit/workers/w7_content_reviewer/test_checks.py`
- REPLACED: `launch.workers.w7_content_reviewer` → `launch.workers.w7_content_reviewer` (2 occurrences, replace_all)
- REPLACED: `W7 ContentReviewer` → `W7 ContentReviewer` in module docstring (3 occurrences)
- REPLACED: `TC-1504: W7 Detection Layer` → `TC-1504: W7 Detection Layer` (1 occurrence)

### `tests/unit/workers/w7_content_reviewer/test_semantic_checks.py`
- REPLACED: `launch.workers.w7_content_reviewer` → `launch.workers.w7_content_reviewer` (1 occurrence, replace_all)
- REPLACED: `W7 ContentReviewer` in module docstring → `W7 ContentReviewer`
- REPLACED: `issue format matches W7 schema` → `issue format matches W7 schema`

### `tests/unit/workers/w7_content_reviewer/test_llm_regen.py`
- REPLACED: `launch.workers.w7_content_reviewer` → `launch.workers.w7_content_reviewer` (1 occurrence, replace_all)
- REPLACED: `W7 ContentReviewer` → `W7 ContentReviewer` in module docstring (2 occurrences)

---

## GROUP 2: Top-level content reviewer tests

### `tests/unit/workers/test_content_reviewer_scoring.py`
- REPLACED: `launch.workers.w7_content_reviewer` → `launch.workers.w7_content_reviewer` (4 occurrences, replace_all)
- REPLACED: `W7 ContentReviewer` → `W7 ContentReviewer` in module docstring

### `tests/unit/workers/test_llm_format_fix.py`
- REPLACED: `launch.workers.w7_content_reviewer` → `launch.workers.w7_content_reviewer` (2 occurrences, replace_all)
- REPLACED: `W7 Phase 0` → `W7 Phase 0` in module docstring
- REPLACED: `TC-2360: W7` → `TC-2360: W7` in module docstring

### `tests/unit/workers/test_gate_17_formatting_quality.py`
- REPLACED: `launch.workers.w9_validator` → `launch.workers.w9_validator` (1 occurrence, replace_all)

---

## GROUP 3: Linker tests

### `tests/unit/workers/test_tc_450_linker_and_patcher.py`
- REPLACED: `src.launch.workers.w8_linker_and_patcher` → `src.launch.workers.w8_linker_and_patcher` (2 occurrences, replace_all)
- REPLACED: `TC-450: W8 LinkerAndPatcher` → `TC-450: W8 LinkerAndPatcher` (module docstring)
- REPLACED: `tests the W8 LinkerAndPatcher` → `tests the W8 LinkerAndPatcher` (module docstring)

### `tests/unit/workers/test_w6_content_export.py`
- REPLACED: `src.launch.workers.w8_linker_and_patcher` → `src.launch.workers.w8_linker_and_patcher` (1 occurrence, replace_all)
- REPLACED: `W8 LinkerAndPatcher` → `W8 LinkerAndPatcher` (2 occurrences in docstrings, replace_all)

### `tests/unit/workers/test_w6_linker_edge_cases.py`
- REPLACED: `src.launch.workers.w8_linker_and_patcher` → `src.launch.workers.w8_linker_and_patcher` (2 occurrences, replace_all)
- REPLACED: `W8 LinkerAndPatcher` → `W8 LinkerAndPatcher` (including `specs/21_worker_contracts.md:228-251 (W8 LinkerAndPatcher contract)`)

---

## GROUP 4: Validator tests

### `tests/unit/workers/test_tc_460_validator.py`
- REPLACED: `src.launch.workers.w9_validator` → `src.launch.workers.w9_validator` (2 occurrences, replace_all)

### `tests/unit/workers/test_w7_gate14.py`
- REPLACED: `src.launch.workers.w9_validator` → `src.launch.workers.w9_validator` (1 occurrence, replace_all)

### `tests/unit/workers/test_tc_570_extended_gates.py`
- REPLACED: `launch.workers.w9_validator` → `launch.workers.w9_validator` (3 occurrences, replace_all)

### `tests/unit/workers/test_tc_571_perf_security_gates.py`
- REPLACED: `launch.workers.w9_validator` → `launch.workers.w9_validator` (1 occurrence, replace_all)

### `tests/unit/workers/test_tc_935_validation_report_determinism.py`
- REPLACED: `src.launch.workers.w9_validator` → `src.launch.workers.w9_validator` (1 occurrence, replace_all)

### `tests/unit/workers/w9/gates/test_gate_u.py`
- REPLACED: `launch.workers.w9_validator` → `launch.workers.w9_validator` (1 occurrence, replace_all)

---

## GROUP 5: Fixer tests

### `tests/unit/workers/test_tc_470_fixer.py`
- REPLACED: `src.launch.workers.w10_fixer` → `src.launch.workers.w10_fixer` (2 occurrences, replace_all)

### `tests/unit/workers/test_w10_fixer_edge_cases.py`
- REPLACED: `src.launch.workers.w10_fixer` → `src.launch.workers.w10_fixer` (2 occurrences, replace_all)

---

## GROUP 6: PR Manager tests

### `tests/unit/workers/test_tc_480_pr_manager.py`
- REPLACED: `src.launch.workers.w11_pr_manager` → `src.launch.workers.w11_pr_manager` (multiple occurrences, replace_all)
- This also correctly updated `patch("src.launch.workers.w11_pr_manager.worker.CommitServiceClient")`

### `tests/unit/workers/test_w11_pr_manager_edge_cases.py`
- REPLACED: `src.launch.workers.w11_pr_manager` → `src.launch.workers.w11_pr_manager` (1 occurrence, replace_all)

---

## GROUP 7: SEO optimizer test

### `tests/unit/workers/test_w6_seo_optimizer.py`
- REPLACED: `"""Tests for W6 SEO Optimizer Worker.` → `"""Tests for W6 SEO Optimizer Worker.`
- REPLACED: `TC-2205: W6 SEO Optimizer Worker` → `TC-2205: W6 SEO Optimizer Worker`
- REPLACED: `launch.workers.w6_seo_optimizer` → `launch.workers.w6_seo_optimizer` (multiple occurrences, replace_all)
- REPLACED: `"W6.SEOOptimizer" in WORKER_DISPATCH` → `"W6.SEOOptimizer" in WORKER_DISPATCH`
- REPLACED: `def test_w10_in_dispatch_map` → `def test_w6_in_dispatch_map`
- REPLACED: `def test_w10_dispatch_order` → `def test_w6_dispatch_order`
- REPLACED: `"""W10 should be between W6 and W7` → `"""W6 should be between W5 and W7`
- REPLACED: `keys.index("W8.LinkerAndPatcher")` → `keys.index("W5.SectionWriter")` (with new var name `w5_idx`)
- REPLACED: `keys.index("W6.SEOOptimizer")` → `keys.index("W6.SEOOptimizer")` (with var renamed to `w6_idx`)
- REPLACED: `keys.index("W9.Validator")` → `keys.index("W7.ContentReviewer")` (var `w7_idx` unchanged)
- REPLACED: `assert w6_idx < w10_idx < w7_idx` → `assert w5_idx < w6_idx < w7_idx`
- NOTE: `TestW10Worker` class name and `"""Integration tests for W10 worker."""` were not in
  the specified replacement list and were left unchanged.

---

## GROUP 8: Multi-worker tests

### `tests/unit/workers/test_tc_1760_incremental.py`
- REPLACED: `launch.workers.w8_linker_and_patcher` → `launch.workers.w8_linker_and_patcher` (3 occurrences, replace_all)
- REPLACED: `launch.workers.w11_pr_manager` → `launch.workers.w11_pr_manager` (3 occurrences, replace_all)

### `tests/unit/workers/test_tc_1781_quality_distribution.py`
- REPLACED: `launch.workers.w7_content_reviewer` → `launch.workers.w7_content_reviewer` (multiple occurrences, replace_all)
- REPLACED: `launch.workers.w8_linker_and_patcher` → `launch.workers.w8_linker_and_patcher` (multiple occurrences, replace_all)
- REPLACED: `W7 Fixes` → `W7 Fixes` in module docstring

### `tests/unit/workers/test_w2_split.py`
- REPLACED: `"W7.ContentReviewer"` → `"W7.ContentReviewer"`
- REPLACED: `"W8.LinkerAndPatcher"` → `"W8.LinkerAndPatcher"`
- REPLACED: `"W9.Validator"` → `"W9.Validator"`
- REPLACED: `"W10.Fixer"` → `"W10.Fixer"`
- REPLACED: `"W11.PRManager"` → `"W11.PRManager"`

### `tests/unit/workers/test_llm_strategy.py`
- REPLACED: `Registry should have default strategies for W2, W5, W7.` → `Registry should have default strategies for W2, W5, W7.`
- REPLACED: `# At least W2 + W5 + W7 defaults` → `# At least W2 + W5 + W7 defaults`

---

## GROUP 9: Integration test

### `tests/integration/test_tc_300_run_loop_mocked.py`
- REPLACED: `"""Stub W8 LinkerAndPatcher:` → `"""Stub W8 LinkerAndPatcher:`
- REPLACED: `"""Stub W9 Validator:` → `"""Stub W9 Validator:`
- REPLACED: `"""Stub W10 Fixer."""` → `"""Stub W10 Fixer."""`
- REPLACED: `"""Stub W11 PRManager:` → `"""Stub W11 PRManager:`
- REPLACED: `"W8.LinkerAndPatcher": stub_linker_patcher,` → `"W8.LinkerAndPatcher": stub_linker_patcher,`
- REPLACED: `"W9.Validator": stub_validator,` → `"W9.Validator": stub_validator,`
- REPLACED: `"W10.Fixer": stub_fixer,` → `"W10.Fixer": stub_fixer,`
- REPLACED: `"W11.PRManager": stub_pr_manager,` → `"W11.PRManager": stub_pr_manager,`

---

## Additional Files Found (NOT in task specification)

The following 4 test files contain `w9_validator` references but were NOT listed in the
task specification. They were left unchanged, as the task only explicitly lists files to edit:

- `tests/unit/workers/test_gate_15_api_hallucination.py` - imports from `launch.workers.w9_validator.gates`
- `tests/unit/workers/test_gate_18_code_prose_balance.py` - imports from `launch.workers.w9_validator.gates`
- `tests/unit/workers/test_gate_19_redundancy.py` - imports from `launch.workers.w9_validator.gates`
- `tests/unit/workers/test_gate_20_cross_page_consistency.py` - imports from `src.launch.workers.w9_validator.gates`

These files may need to be updated in a follow-up pass if they were overlooked in the task
specification.

---

## Files Not Found

No files from the task specification were missing (all existed on disk).

---

## Replacements Not Applicable

- `launch.workers.w7_content_reviewer` replacement in test_auto_fixes.py: The `TC-1100-P5`
  prefix text replacement was handled separately since the replace_all on the module path covered
  only the import paths.
- `test_w6_linker_edge_cases.py`: The `specs/21_worker_contracts.md:228-251 (W6` replacement was
  handled by the replace_all on `W8 LinkerAndPatcher` which caught it.

---

## Verification

Post-edit grep confirms zero remaining old patterns in the specified task files:
- `w7_content_reviewer`: 0 matches in edited files
- `w8_linker_and_patcher` (as import path): 0 matches in edited files
- `w9_validator` (as import path): 0 matches in edited files (except 4 unspecified gate test files)
- `w10_fixer` (as import path): 0 matches in edited files
- `w11_pr_manager` (as import path): 0 matches in edited files
- `w6_seo_optimizer` (as import path): 0 matches in edited files
