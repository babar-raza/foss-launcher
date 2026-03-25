# TC-2880 Evidence — W10 auto-fix for gate_scaffold_leak / SCAFFOLD_*

## Summary
Closed the W10 healing loop: W10 can now auto-fix all 5 SCAFFOLD_* error code categories emitted by gate 24 (gate_scaffold_leak). All fixes are deterministic (no LLM calls), fence-aware, and idempotent.

## Changes Made

### 1. Routing (worker.py)
Added `elif error_code.startswith("SCAFFOLD_"):` in `apply_fix()` routing table, dispatching to `fix_scaffold_leak()`.

### 2. Fix Function (worker.py)
- `fix_scaffold_leak(issue, run_dir, llm_client)` — scans ALL `.md` files under `work/site/`, applies 6 sequential deterministic passes, collapses triple+ blank lines
- `_strip_all_scaffold(content)` — composition of 6 passes returning (cleaned_content, removal_count)
- `_strip_prompt_xml_blocks(content)` — NOT fence-aware (PROMPT_LEAK never legitimate)
- `_strip_llm_meta_lines(content)` — fence-aware line removal
- `_strip_pipeline_json_keys(content)` — fence-aware line removal
- `_strip_pipeline_diagnostics(content)` — fence-aware line removal
- Reuses existing `strip_llm_scaffolding()` and `strip_pipeline_comments()` from content_sanitizer

### 3. Prompt Update (draft_generator.txt)
Added "Output Purity Rules" section with explicit anti-echo rules for all 5 leak categories.

### 4. Module-level Constants (worker.py)
- `_SCAFFOLD_XML_TAG_RE` — paired XML tag blocks
- `_SCAFFOLD_XML_ORPHAN_RE` — orphaned opening/closing XML tags
- `_SCAFFOLD_LLM_META_PATTERNS` — 7 compiled regexes for LLM meta/scaffold lines
- `_SCAFFOLD_PIPELINE_JSON_RE` — 6 pipeline JSON key patterns
- `_SCAFFOLD_PIPELINE_DIAG_PATTERNS` — 3 diagnostic patterns

## Test Results

### New Tests: 50 passed
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w10_scaffold_fix.py -v
50 passed in 0.87s
```

### Full Suite: 6751 passed, 0 failed
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
6751 passed, 13 skipped, 3 xfailed, 9 xpassed in 137.31s
```

## Test Coverage by Category

| Category | Tests | Key Verifications |
|----------|-------|-------------------|
| SCAFFOLD_LLM_SCAFFOLD | 4 | "You now have a complete/working/full", "Here's/Here is a complete" |
| SCAFFOLD_LLM_META | 6 | "As an AI", "I'll/I will help you", "Let me explain/show/demonstrate" |
| SCAFFOLD_PIPELINE_DIAGNOSTIC | 4 | claim_id, evidence_score, claim comments; fence preservation |
| SCAFFOLD_PROMPT_LEAK | 11 | Headings+body, bold/plain labels, W_REVIEW, XML tags, System:, fence non-demotion |
| SCAFFOLD_PIPELINE_JSON | 4 | "claims"/"page_plan"/"shared_facts" keys; fence preservation |
| Fence Safety | 3 | Normal code preserved, mixed prose/fence, toggle tracking |
| Multi-file + Idempotency | 4 | All-file scan, second-run no-op, missing site_dir, clean content |
| Routing | 5 | apply_fix routes all 5 SCAFFOLD_* codes |
| End-to-end | 1 | Multi-category file fully cleaned |
| Helper unit tests | 8 | Direct tests for _strip_* private functions |

## Files Modified
- `src/launch/workers/w10_fixer/worker.py` — +165 lines (routing, function, helpers, constants)
- `src/launch/prompts/system/draft_generator.txt` — +10 lines (Output Purity Rules)
- `tests/unit/workers/test_w10_scaffold_fix.py` — NEW, 50 tests
- `plans/taskcards/TC-2880.md` — NEW
- `plans/taskcards/INDEX.md` — +3 lines
