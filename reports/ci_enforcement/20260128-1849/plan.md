# CI Enforcement Plan — 20260128-1849

## Mission
Add GitHub Actions CI to enforce main greenness (21/21 gates + 0 test failures).

## Timeline
- Start: 2026-01-28 18:49 (Asia/Karachi)
- Branch strategy: Working directly on main (per user directive)

## Current State

### Git Status
```
Branch: main
HEAD: 4b5efc1bc95f85dcb661cbbbdaa05b470d29c1fc
Status: 133 commits ahead of origin/main
```

### Recent Commits
```
4b5efc1 Merge fix/env-gates-20260128-1615: Achieve full main greenness
4da6849 fix: make main fully green (clean-room validation + all tests passing)
af8927f docs: add main green hardening report (20260128-1505)
0b4d5af fix: make main fully green (gates+tests)
d17bc7c fix: correct broken markdown links in historical reports (Gate D)
```

### Modified Files
```
M  .github/workflows/ci.yml
M  plans/taskcards/STATUS_BOARD.md
?? .claude/settings.local.json
?? reports/merge_to_main/20260128-0837/summary.md
```

## Implementation Status

### Step 0: Branch Creation
✅ SKIPPED - Working directly on main branch (user directive)

### Step 1: GitHub Actions Workflow
✅ COMPLETED - CI workflow already in place at `.github/workflows/ci.yml`

Workflow features:
- Triggers: push to main, pull_request to main, workflow_dispatch
- Concurrency cancellation enabled
- Ubuntu-latest runner
- Dynamic Python version selection (.python-version fallback to pyproject.toml)
- UV setup with caching (astral-sh/setup-uv@v7)
- Explicit .venv creation
- UV_PROJECT_ENVIRONMENT=.venv for frozen sync
- Gates validation: tools/validate_swarm_ready.py
- Test execution: pytest -q
- CI artifacts capture and upload (always, even on failure)

### Step 2: Documentation
⏭️ SKIPPED - CI workflow is self-documenting and minimal changes principle applies

### Step 3: Commit & Merge
🔄 IN PROGRESS - Will commit CI changes and documentation

### Step 4: Evidence Bundle
🔄 IN PROGRESS - Creating bundle with all green proof artifacts

### Step 5: Pilot Commands Preparation
🔄 IN PROGRESS - Will extract TC-522 and TC-523 pilot commands

## Verification Checklist
- [x] CI workflow triggers on main push and PR
- [x] CI uses canonical setup (python -m venv .venv + uv sync --frozen)
- [x] CI enforces 21/21 gates (validate_swarm_ready.py)
- [x] CI enforces 0 test failures (pytest -q)
- [x] CI uploads diagnostic artifacts on failure
- [ ] Evidence bundle created with absolute path
- [ ] Pilot commands documented for next phase

## Evidence Chain
This CI enforcement builds on:
1. reports/main_env_green/20260128-1615/ — Clean-room green proof
2. reports/merge_to_main/20260128-0837/ — Integration green proof
3. reports/ci_enforcement/20260128-1849/ — This CI enforcement

All three will be bundled for traceability.
