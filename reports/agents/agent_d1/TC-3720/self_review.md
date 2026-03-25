# Self Review (13-D)

> Agent: agent_d1
> Taskcard: TC-3720
> Date: 2026-03-04

## Summary
- What I changed: Created `llm_extractor.py` (new module for LLM-primary claim extraction), modified `worker.py` to wire it as the primary path with regex as fallback/supplement, modified `run_config.schema.json` to add the `w2_synthesis` configuration block, and created 21 unit tests (15 required + 6 additional helper tests).
- How to run verification: `PYTHONHASHSEED=0 .venv/Scripts/python -m pytest tests/unit/workers/w2_facts_builder/test_tc3720_llm_extraction.py -v`
- Key risks / follow-ups: The `_llm_client` injection pattern (putting client in run_config dict) is a workaround for the read-only client access constraint. A cleaner approach would be to pass the client as a direct parameter, but this would require changing the allowed_paths (worker.py already does this via TC-3720 scope).

## Evidence
- Diff summary: 2 files modified (+121 lines), 3 files created (519 + 495 + 0 lines)
- Tests run: `PYTHONHASHSEED=0 .venv/Scripts/python -m pytest tests/unit/workers/w2_facts_builder/test_tc3720_llm_extraction.py -v` → 21 passed; full suite → 8617 passed (12 pre-existing failures, 0 new failures)
- Logs/artifacts: `reports/agents/agent_d1/TC-3720/report.md`, `reports/agents/agent_d1/TC-3720/self_review.md`

## 13 Quality Dimensions (score 1–5)

### 1) Correctness
Score: 5/5
- `llm_extract_claims()` correctly implements all 4 post-LLM guards (source_file existence, low-confidence+no-source, fabricated metric, max_per_kind)
- `_merge_claims()` correctly places LLM claims first, regex claims supplemented without exact-text duplicates
- temperature=0 is enforced for determinism (C6 constraint)
- JSON parse retry is correctly implemented: first call fails → clarification message → retry on second call
- All 15 required test IDs pass with exactly the expected behavior

### 2) Completeness vs spec
Score: 5/5
- All components specified in TC-3720 are implemented: `build_extraction_bundle`, `llm_extract_claims`, `_verify_claim_source`, `_is_fabricated_metric`
- Schema `w2_synthesis` block has all 5 required properties with correct types and defaults
- All 4 source types included in bundle: README, module docstrings, CHANGELOG (last 3), examples (up to 5)
- Fallback contract: RuntimeError raised → worker.py catches and falls back to regex-only path
- `enabled=False` path correctly skips LLM extraction entirely (check in worker.py)

### 3) Determinism / reproducibility
Score: 5/5
- temperature=0 enforced for all LLM calls
- Bundle construction is deterministic: sorted file lists, consistent ordering
- claim_id assignment left to worker.py (existing deterministic path)
- `_extract_changelog_last_n_versions` uses `re.finditer` with consistent results

### 4) Robustness / error handling
Score: 5/5
- `llm_extract_claims` raises `RuntimeError` (not returns empty list) on LLM failure — allows caller to distinguish failure from 0 claims
- JSON parse retry on first failure with explicit retry message
- `build_extraction_bundle` handles `encoding errors` with `errors="replace"`
- Per-file read errors caught individually (one bad file doesn't kill the whole bundle)
- Worker.py `try/except RuntimeError` correctly falls back to regex-only path without crashing
- Budget enforcement prevents context window overflow

### 5) Test quality & coverage
Score: 5/5
- 21 tests covering all 15 required test IDs exactly
- All LLM calls mocked — no real LLM calls in any test
- Both positive and negative paths tested for each guard
- Retry behavior tested (test 11: first call invalid JSON, second call valid)
- Edge cases covered: empty source_file string, subdirectory paths, None source_file
- Budget truncation tested independently

### 6) Maintainability
Score: 4/5
- `llm_extractor.py` is a standalone module — easy to modify without touching worker.py
- `_llm_client` injection via dict key is somewhat implicit; could be cleaner with explicit parameter. Documented in code.
- `_merge_claims` helper is clear and testable separately
- Module docstring clearly attributes to TC-3720

### 7) Readability / clarity
Score: 5/5
- All public functions have docstrings with Args/Returns/Raises
- Helper functions (`_extract_module_docstring`, `_extract_changelog_last_n_versions`) are clearly named and documented
- Constants (`_BUNDLE_CHAR_BUDGET`, `_SYSTEM_PROMPT`, `_USER_PROMPT_TEMPLATE`) are at module top
- Code follows existing patterns from worker.py (same logging style, same error handling patterns)

### 8) Performance
Score: 5/5
- Bundle budget (32,000 chars) prevents context window overflow
- LLM is called only once (plus one retry on parse error) — not per-claim
- `build_extraction_bundle` reads files lazily, stopping when budget is exhausted
- Regex fallback path incurs no additional LLM calls

### 9) Security / safety
Score: 5/5
- Source file paths verified to exist in repo_dir (path traversal: paths are joined with repo_dir, not used directly)
- Fabricated metric guard prevents hallucinated numbers from reaching downstream content
- `require_source_citation` guard prevents low-confidence unanchored claims
- No shell commands, no subprocess calls

### 10) Observability (logging + telemetry)
Score: 5/5
- `tc3720_llm_extraction_success count=N` log on success
- `tc3720_llm_extraction_unavailable fallback_to_regex=true error=...` on fallback
- `tc3720_claims_merged llm=N regex=N merged=N` log after merge
- Per-guard rejection logged at DEBUG level with reason and claim text prefix
- `bundle_readme`, `bundle_changelog`, `bundle_example` debug logs for bundle construction
- `llm_extract_claims_start` and `llm_extract_claims_done` info logs

### 11) Integration (CLI/MCP parity, run_dir contracts)
Score: 4/5
- wired into `execute_facts_builder()` which is the standard W2 entry point
- Does not break existing extract_claims (TC-411) path — it runs after LLM extraction
- Schema addition is backward-compatible (no new required fields)
- `_llm_client` injection pattern is slightly non-standard compared to direct parameter passing; this is a constraint of allowed_paths scope

### 12) Minimality (no bloat, no hacks)
Score: 5/5
- New module is focused: only claim extraction, no assembly or merging beyond what's needed
- No new dependencies introduced
- `_merge_claims` is simple: O(n+m), set lookup
- No monkey-patching or module-level side effects

### 13) Root cause addressed
Score: 5/5
- TC-3720 root cause: regex-only extraction misses semantic facts visible only in README prose and CHANGELOG context
- LLM-primary path directly addresses this: it reads full documentation context rather than pattern-matching text fragments
- Fallback contract ensures no regression when LLM is unavailable (offline runs, test environments)

## Final verdict
- Ship: Ready to ship.
- Score: 63/65 (two dimensions scored 4 due to `_llm_client` injection pattern being slightly non-standard — acceptable for this implementation scope)
- Score exceeds threshold (55/65) to proceed.
