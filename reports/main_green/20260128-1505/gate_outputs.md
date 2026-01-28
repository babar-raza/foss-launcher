# Gate Outputs

## Baseline (before fixes)

See: `checkpoints/gates_baseline.txt`

### Summary
- Total gates: 21
- Passing: 17
- Failing: 4
  - Gate 0: .venv policy (environment issue)
  - Gate B: Taskcard validation (6 taskcards)
  - Gate D: Markdown link integrity (10 broken links)
  - Gate O: Budget config (environment issue)

## After Fixes (fix/main-green-20260128-1505)

See: `checkpoints/gates_after_fixes.txt`

### Summary
- Total gates: 21
- Passing: 19 ✅ (+2 from baseline)
- Failing: 2 ⚠️ (both environment issues, not code issues)
  - Gate 0: .venv policy (requires running from .venv)
  - Gate O: Budget config (requires jsonschema module installed)

### Status Changes
- Gate B: ❌ FAILED → ✅ PASSED (6 taskcards fixed)
- Gate D: ❌ FAILED → ✅ PASSED (10 broken links fixed)

### Code Issues Resolved
All code-level failures have been fixed. The remaining 2 failures are environment configuration issues:
- Gate 0 will pass when running validation from within activated .venv
- Gate O will pass when dependencies are installed (requires `uv sync` or `pip install -e .[dev]`)
