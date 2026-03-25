# TC-2890 Self-Review (12D)

> Agent: agent_b
> Taskcard: TC-2890
> Date: 2026-02-27

## Summary
- What I changed: Added 5 missing scaffold prompt-leak patterns to all 4 detection/stripping systems (content_sanitizer, gate_scaffold_leak, deterministic review, W7 auto-fixes) with 53 new tests.
- How to run verification:
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_content_sanitizer.py::TestStripLlmScaffoldingExpanded -v
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/w9/test_gate_scaffold_leak.py::TestPromptLeak -v
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/w7_content_reviewer/test_auto_fixes.py::TestFixPromptScaffoldLeak -v
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
  ```
- Key risks / follow-ups: None. Static regex patterns with zero LLM dependence.

## Evidence
- Diff summary: 5 compiled regex patterns added to each of 4 production files; 53 new unit tests across 3 test files
- Tests run: 53 targeted tests passed (19 + 19 + 15); full suite green
- Logs/artifacts: `reports/agents/agent_b/TC-2890/report.md`

## 12 Quality Dimensions (score 1-5)

### 1) Correctness — 5/5
- All 53 targeted tests pass with exit code 0
- Pattern regex matches confirmed via direct file inspection (lines 73-78, 30-34, 321-325, 2240-2244)
- `Available Claims` correctly uses `\b` word boundary for parenthetical variants
- Gate `PROMPT_LEAK` severity never demoted in fences (tested)
- Full test suite passes with 0 failures

### 2) Completeness vs spec — 5/5
- All 5 patterns added to all 4 sources (content_sanitizer, gate_scaffold_leak, deterministic, auto_fixes)
- Pattern conventions match each system: `#{1,2}` (sanitizer/deterministic), `#{1,3}` (gate/W7)
- Fence-aware behavior inherited from existing infrastructure (specs/21_worker_contracts.md Shared.1)
- Exceeds taskcard estimate of 20 tests (delivered 53)

### 3) Determinism / reproducibility — 5/5
- All patterns are compiled regexes — no LLM calls, no time-based behavior
- Stable ordering within lists (appended at end, TC-2890 comment block)
- `PYTHONHASHSEED=0` used for all test runs
- Idempotent: `fix_prompt_scaffold_leak()` running twice produces identical output

### 4) Robustness / error handling — 5/5
- Fence-aware: patterns inside code fences are not stripped by sanitizer or W7 fixer
- `PROMPT_LEAK` in fences: gate still flags as error (never demoted — verified by tests)
- `Available Claims` uses `\b` not `$` to handle parenthetical suffixes
- W7 `fix_prompt_scaffold_leak()` handles missing files gracefully

### 5) Test quality & coverage — 5/5
- 19 sanitizer tests covering all 5 patterns + edge cases (parenthetical variants, heading preservation)
- 19 gate tests covering all 5 patterns + severity rules + fence non-demotion
- 15 W7 auto-fix tests covering scaffold removal + fence safety + idempotency
- Each test verifies both removal of scaffold AND preservation of legitimate content

### 6) Maintainability — 5/5
- Patterns follow existing list conventions in each file
- TC-2890 comment blocks clearly mark the additions
- No new abstractions or indirection — direct pattern list extensions
- Future patterns can be added by appending to the same lists

### 7) Readability / clarity — 5/5
- Consistent formatting with existing patterns in each file
- Comment headers: `# TC-2890: claims/API/issues/content ...`
- Pattern regex follows same style as neighboring entries
- Test names are descriptive: `test_available_claims_heading_detected`, etc.

### 8) Performance — 5/5
- All patterns are pre-compiled regexes (`re.compile()` at module level)
- No new I/O, network calls, or LLM invocations
- Pattern matching is O(n) per line, same as existing gate/sanitizer behavior
- No measurable performance impact

### 9) Security / safety — 5/5
- Patterns prevent prompt leaks (security improvement)
- No new attack surface introduced
- No user input processed — patterns match against LLM-generated content only
- Fence-aware logic prevents false stripping of legitimate code examples

### 10) Observability (logging + telemetry) — 4/5
- Gate issues include `error_code`, `severity`, `location` (file + line) for all findings
- W7 fix results include `files_changed` list and `success` boolean
- No new telemetry added (not needed for static pattern matching)
- Minor: no explicit log line for pattern list version/count

### 11) Integration (CLI/MCP parity, run_dir contracts) — 5/5
- All 4 systems updated in lockstep (no gap between detection and removal)
- Gate severity rules consistent with existing PROMPT_LEAK behavior
- W7 auto-fix integrates via existing `apply_auto_fixes()` dispatcher
- Content sanitizer integration unchanged (Phase 4 Strip pipeline)

### 12) Minimality (no bloat, no hacks) — 5/5
- Only pattern list extensions — no new functions in sanitizer, gate, or deterministic
- W7 `fix_prompt_scaffold_leak()` is the only new function (required for W7 fix integration)
- No backwards-compatibility shims or unused code
- Write fence respected: only files in `allowed_paths` modified

## Final verdict
- **Ship**
- All 12 dimensions >= 4/5
- Known Gaps: **empty**
- 53 targeted tests passing, full suite green
