# Evidence: TC-2434 — Content Policy Engine

## Files Modified
- `src/launch/workers/w4_ia_planner/content_policy.py` — created; ContentPolicy, PolicyDecision, load_policy_config
- `tests/unit/workers/test_w4_content_policy.py` — created; 25 tests

## Test Results
- 25 tests written covering: evaluation, scoring, normalization, dry-run mode, load_policy_config, to_artifact output
- All 25 pass (56 total in combined run)

## Key Decisions
- `load_policy_config({})` returns `None` (no key = no change)
- `load_policy_config({"policy": {}})` returns `ContentPolicy` with defaults (key present = policy active)
- `load_policy_config({"policy": None})` returns `None` (explicit null opt-out)
- Empty dict fix: changed `if not policy_cfg` to explicit `"policy" not in run_config` + `is None` checks
