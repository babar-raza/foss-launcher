# Self Review (12-D)

> Agent: agent_b
> Taskcard: TC-3641
> Date: 2026-03-03

## Summary
- What I changed: Added selective gate execution to the heal loop — during heal iterations, only previously-failing gates plus 7 safety gates are run instead of all 42+. A final full validation confirms zero failures before declaring `all_gates_pass`. Implemented across 3 source files (runner.py, w9 worker.py, heal.py), 2 schemas, and 2 specs. Post-implementation hardening added config template field (TM-01), transient key docs (TM-02), progressive narrowing tests (TM-03), and TC-ID dedup fix (SR-02).
- How to run verification (exact commands):
  - `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short` (full suite)
  - `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_validation_engine.py tests/unit/workers/w9/test_partial_report.py tests/unit/cli/test_heal.py -v` (TC-3641 files only)
- Key risks / follow-ups: None blocking. All 5 post-implementation gaps (GAP-01 through GAP-05) are resolved.

## Evidence
- Diff summary (high level):
  - `runner.py:37-50` — gate filter check + skip-result generation (5 lines logic)
  - `w9_validator/worker.py:1587-1593` — partial report marking (6 lines)
  - `heal.py:63-74` — `_HEAL_SAFETY_GATES` constant (7 gates)
  - `heal.py:816-818` — `heal_fast_validation` opt-out + `_needs_final_full` flag
  - `heal.py:833-836` — top-of-iteration partial-zero deferral
  - `heal.py:969-972` — filter injection into `_rc2`
  - `heal.py:1117-1120` — exception-handler partial-zero deferral
  - `heal.py:1135-1139` — final full validation post-loop
  - `specs/50_healing_cost_reduction.md` §5 — new BINDING section
  - `specs/28_coordination_and_handoffs.md` §Partial report disk truth — amendment
  - `specs/schemas/validation_report.schema.json` — `partial`, `gate_filter`, `skipped` fields
  - `specs/schemas/run_config.schema.json` — `heal_fast_validation` field
  - Post-hardening: config_generator.py template, run_loop.py guard comment, spec §5.8 transient keys
- Tests run (commands + results):
  - Full suite: `8369 passed, 13 skipped, 3 xfailed` (PYTHONHASHSEED=0)
  - TC-3641 files: `137 passed` (test_validation_engine.py:47, test_heal.py:87, test_partial_report.py:3)
  - Baseline: 8168 passed (before TC-3641 + hardening)
  - Net new TC-3641 core tests: 20 (6 runner, 3 partial report, 11 heal)
  - Net new hardening tests: 8 (TM-02: 2 transient key, TM-03: 4 progressive/resume, TM-01: 1 config template)
- Logs/artifacts written (paths):
  - `reports/agents/agent_b/TC-3641/self_review.md` (this file)
  - `reports/agents/agent_b/TC-3641/evidence.md`
  - `plans/healing/26_tc3641_fast_inner_loop_hardening.md` (hardening plan, 5 taskcards all Done)

## 13 Quality Dimensions (score 1-5)

### 1) Correctness
Score: 5/5
- Gate filter in `runner.py:48-50`: exact `gate_id not in gate_filter` check — no off-by-one, no type coercion
- Skipped gates produce `{"name": gate_id, "ok": True, "skipped": True}` — no issues appended (verified by `test_skipped_gate_no_issues`)
- Safety gates `_HEAL_SAFETY_GATES` (7 gates) match spec §5.3 exactly: schema, truth-layer, frontmatter, template-lint, hugo-build, xss, sensitive-data
- Partial-zero triggers final full validation at both convergence points (`heal.py:833-836`, `heal.py:1117-1120`)
- Final full validation (`heal.py:1135-1139`) runs without `_heal_gate_filter` — all gates executed
- `heal_fast_validation=False` disables all filtering (verified by `test_fast_validation_false_disables`)
- Config generator template includes `heal_fast_validation: True` (TM-01)

### 2) Completeness vs spec
Score: 5/5
- `specs/50_healing_cost_reduction.md` §5 defines all 7 subsections (§5.1-§5.7); all implemented
- §5.1 Filter injection: `heal.py:969-972` builds filter from `metrics_before.failed_gate_ids | _HEAL_SAFETY_GATES`
- §5.2 Progressive narrowing: `metrics_before` updated each iteration → filter shrinks (verified by `test_progressive_narrowing_across_iterations`)
- §5.3 Safety gates: 7 gates in `_HEAL_SAFETY_GATES` constant
- §5.4 Skip-group cascade: `runner.py:52-58` — cascade runs AFTER filter check (order preserved)
- §5.5 Partial report: `w9_validator/worker.py:1587-1593` sets `partial` + `gate_filter` fields
- §5.6 Partial-zero rule: two sites in heal.py + post-loop final full run
- §5.7 Opt-out: `heal_fast_validation` config key, defaults `True`
- §5.8 Transient keys: documented convention (TM-02)
- `specs/28_coordination_and_handoffs.md` §Partial report disk truth: amended to cover partial reports

### 3) Determinism / reproducibility
Score: 5/5
- Gate filter is `frozenset` (immutable, order-independent) in `runner.py:41`
- Safety gates constant is `frozenset` — no mutation possible
- All tests pass with `PYTHONHASHSEED=0` — no dict-ordering sensitivity
- `_heal_gate_filter` in `_rc2` is `sorted()` list for JSON serialization (`heal.py:972`)
- No randomness in filter construction or gate selection
- `gate_filter` field in report is sorted by gate execution order (deterministic registry traversal)

### 4) Robustness / error handling
Score: 5/5
- `_filter_raw = run_config.get("_heal_gate_filter")` — graceful `None` when absent (`runner.py:40`)
- `gate_filter: frozenset | None` — explicit None branch runs all gates (no crash on missing key)
- `heal_fast_validation` uses `.get("heal_fast_validation", True)` — missing key defaults safely
- Partial-zero handled at both normal convergence AND exception-handler paths
- Final full validation is a separate W9 invocation — isolated from partial loop state
- Resume without `_heal_gate_filter` runs all gates (verified by `test_resume_without_filter_runs_all_gates`)
- Transient keys survive orchestrator transit (verified by `TestTransientKeySurvival`)

### 5) Test quality & coverage
Score: 5/5
- 28 total TC-3641-related tests across 5 test files:
  - `TestGateFilter` (6 tests): filter skips, None runs all, from run_config, no issues, cascade, result shape
  - `TestPartialReport` (3 tests): partial flag set, absent on full run, gate_filter matches executed
  - `TestSelectiveGateExecution` (8 tests): inject filter, safety gates, disable, partial-zero, final full finds regression, final full confirms green, disk sync defers, metrics comparison
  - `TestProgressiveNarrowing` (2 tests): filter shrinks across iterations, safety gates always present
  - `TestResumeWithoutFilter` (2 tests): all gates run, no partial flag
  - `TestTransientKeySurvival` (2 tests): keys reach OrchestratorState, shallow copy preserves
  - Config template test (1 test): `heal_fast_validation` in generated config
  - Hardening tests (4 more): progressive narrowing + resume fallback edge cases
- All happy paths AND failure paths covered (regression detection, partial-zero deferral, opt-out)
- Tests use standard mock patterns — no network, no disk I/O beyond tmp_path

### 6) Maintainability
Score: 5/5
- Filter logic is 5 lines in `runner.py` — single choke point, minimal surface area
- Safety gates are a named `frozenset` constant — easy to update when new safety gates are added
- `_HEAL_SAFETY_GATES` is co-located with other heal constants in `heal.py:63-74`
- Partial report marking is 6 lines in W9 worker — co-located with report construction
- Transient key convention documented in spec §5.8 with guard comment in `run_loop.py:601-606`
- All TC-3641 changes are tagged with `# TC-3641:` comments for traceability

### 7) Readability / clarity
Score: 5/5
- Every code block has a `# TC-3641:` tag explaining intent
- Variable names are self-documenting: `gate_filter`, `_needs_final_full`, `_has_skipped`, `_fast_validation`
- Spec §5 is organized into 7 numbered subsections with clear contracts
- Safety gate constant uses full gate IDs (not abbreviations)
- Test names describe exact scenario: `test_partial_zero_triggers_final_full`, `test_fast_validation_false_disables`

### 8) Performance
Score: 5/5
- Primary goal achieved: heal iterations skip ~35 of ~42 gates when only a few are failing
- `frozenset` membership check is O(1) per gate — negligible overhead vs gate execution cost
- No additional disk I/O for filtering — filter is in-memory only
- Final full validation is a single additional W9 invocation — only when needed (partial-zero)
- Safety gates (7) are a fixed overhead regardless of failure count — bounded cost

### 9) Security / safety
Score: 5/5
- Safety gates include `gate_s1_xss_prevention` and `gate_s2_sensitive_data_leak` — always executed
- `_heal_gate_filter` is transient (underscore prefix) — never persisted to config YAML on disk
- No new external inputs — filter is derived entirely from internal `metrics_before`
- `additionalProperties: false` in schema prevents `_heal_gate_filter` from being injected via user config
- Schema validation happens at load time, before transient key injection

### 10) Observability (logging + telemetry)
Score: 4/5
- `logger.info("[Heal] Disk report green but partial — deferring to final full validation.")` at both deferral sites
- `_print("[blue]Running final full 42-gate validation...[/blue]")` for CLI feedback
- Partial reports include `gate_filter` field — auditable which gates were actually run
- `skipped: true` on carry-forward results — visible in report JSON
- Minor gap: no structured telemetry event for "heal iteration used selective gates" (acceptable — report metadata serves this purpose)

### 11) Integration (CLI/MCP parity, run_dir contracts)
Score: 5/5
- Call chain verified end-to-end: `heal.py → run_loop.py → graph.py → worker_invoker.py → w9_validator.py → runner.py`
- `run_config` passes by reference through all layers — no deep copy, no stripping
- Return path: `runner.py → w9_validator.py → disk → heal.py` preserves `partial` and `gate_filter`
- `launch validate` and `launch run` unaffected — no `_heal_gate_filter` injected outside heal loop
- MCP `handle_launch_validate()` not affected (uses canonical engine, not heal path)
- Transient key guard documented in `run_loop.py:601-606`

### 12) Minimality (no bloat, no hacks)
Score: 5/5
- Core implementation: ~20 lines across 3 files (5 in runner, 6 in W9, 9 in heal filter injection)
- No new dependencies, no new classes, no new files (source code)
- Safety gates are a literal `frozenset` — no over-engineered registry
- Opt-out is a single boolean config key — no feature flags framework
- No backward-compatibility shims — all new schema fields are optional

### 13) Root cause addressed
Score: 5/5
- Root cause: each heal iteration ran all 42+ gates via W9, even when most were already passing — this was the largest cost driver in the heal loop
- Documented in `specs/50_healing_cost_reduction.md` §5 BEFORE implementation
- Spec was cited in taskcard `## Required spec references` section
- Three approaches considered and documented in taskcard `## Approaches considered` table:
  1. Filter in runner.py (chosen) — minimal, central choke point
  2. Filter in W9 worker.py (rejected) — violates SRP
  3. Cache gate results (rejected) — complexity too high
- Feature taskcard, not a bug fix — "root cause" is cost analysis grounded in spec

## Final verdict
- Ship
- All 13 dimensions >= 4/5 (observability at 4/5 is acceptable — report metadata provides auditability)
- Total score: 64/65
- No follow-up taskcards needed — all 5 hardening gaps (GAP-01 through GAP-05) resolved
