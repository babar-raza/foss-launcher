# Self Review (12-D)

> Agent: agent_b
> Taskcard: TC-3642
> Date: 2026-03-03

## Summary
- What I changed: Added `.git` existence check to PhaseSelector (phase_selector.py:142-146) and `work/repo/.git` to RESUME_NODE_MAP W2/ingest entries (run_loop.py:100, 147). Amended specs 43 and 48. Updated test fixtures and added 2 new tests.
- How to run verification: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/autopilot/test_phase_selector.py tests/unit/orchestrator/test_resume_from_node.py -v`
- Key risks / follow-ups: None. Pure safety hardening with no behavior change for valid runs.

## Evidence
- Diff summary: 5 lines in phase_selector.py, 2 lines in run_loop.py (W2 + ingest entries), ~10 lines in spec amendments, ~15 lines in test fixtures/new tests
- Tests run: 44 passed, 0 failed (phase_selector: 26, resume_from_node: 18)
- Full suite: 8174 passed, 13 skipped, 3 xfailed, 0 failed
- Logs/artifacts written: specs/43_resumable_pipeline.md, specs/48_autopilot_phase_selection.md

## 13 Quality Dimensions (score 1-5)

1) Correctness
   - Score: 5/5
   - `.git` check at phase_selector.py:143 returns `REPO_NOT_CLONED` when work/repo/ exists but `.git` absent
   - RESUME_NODE_MAP W2 entry uses `work/repo/.git` — `_validate_resume_artifacts()` calls `.exists()` which works on directories
   - Both short alias `W2` and full name `ingest` entries updated consistently
   - No behavior change for valid runs (`.git` always present after real clone)

2) Completeness vs spec
   - Score: 5/5
   - specs/43_resumable_pipeline.md §Artifact Pre-validation W2 row updated with `.git` requirement
   - specs/48_autopilot_phase_selection.md §Baseline Algorithm documents REPO_NOT_CLONED reason
   - Code matches spec exactly

3) Determinism / reproducibility
   - Score: 5/5
   - `.git` existence is a filesystem check — fully deterministic
   - No randomness, timestamps, or environment-dependent behavior

4) Robustness / error handling
   - Score: 5/5
   - `.git` check is a simple `(repo_dir / ".git").exists()` — cannot throw
   - Symlinks followed correctly by default (`exists()` resolves symlinks)
   - Empty skeleton from `create_run_skeleton()` correctly detected

5) Test quality & coverage
   - Score: 5/5
   - `test_repo_dir_exists_but_no_git_returns_w1`: verifies REPO_NOT_CLONED for empty skeleton
   - `test_repo_dir_with_git_passes_checkpoint`: verifies `.git` present proceeds past checkpoint 1
   - All `_setup_w1()` fixtures updated to create `.git` dir
   - 44 tests passing, 0 failures

6) Maintainability
   - Score: 5/5
   - Single 5-line check in PhaseSelector — easy to understand and modify
   - Follows existing pattern (check dir exists, return early with reason)
   - Clear reason code `REPO_NOT_CLONED` with human-readable detail

7) Readability / clarity
   - Score: 5/5
   - Comment `# TC-3642: Verify actual clone (not empty skeleton from create_run_skeleton)`
   - Reason code is self-documenting
   - Detail message explains what happened: "work/repo/.git not found"

8) Performance
   - Score: 5/5
   - Single `Path.exists()` call — O(1) filesystem stat
   - No impact on pipeline performance

9) Security / safety
   - Score: 5/5
   - Pure safety hardening — prevents phantom resume past W1
   - No user input, no shell commands, no file writes

10) Observability (logging + telemetry)
    - Score: 5/5
    - `REPO_NOT_CLONED` reason is machine-readable (in PhaseDecision.reasons tuple)
    - Detail message logged/returned for human inspection
    - Existing PhaseDecision logging in main.py captures the decision

11) Integration (CLI/MCP parity, run_dir contracts)
    - Score: 5/5
    - PhaseSelector called from main.py Step 5 — `.git` check fires correctly
    - RESUME_NODE_MAP validated by `_validate_resume_artifacts()` at run start
    - No CLI/MCP parity issue (selector is backend-only)

12) Minimality (no bloat, no hacks)
    - Score: 5/5
    - 5 lines of code in phase_selector.py, 2 line changes in run_loop.py
    - No new abstractions, no new dependencies, no workarounds

13) Root cause addressed
    - Score: 5/5
    - Root cause: `create_run_skeleton()` creates `work/repo/` (empty), and both `_validate_resume_artifacts()` and `select_phase()` accepted empty dirs as "cloned"
    - Spec 48 §Baseline Algorithm said "IF repo missing -> return W1" but didn't define "missing" to require `.git`
    - Fix addresses the root cause directly — `.git` check distinguishes skeleton from clone
    - Documented in taskcard before implementation

## Final verdict
- Ship / Needs changes: **Ship**
- All 13 dimensions scored 5/5 — 65/65
- No follow-ups needed. Pure safety hardening, zero behavior change for valid runs.
