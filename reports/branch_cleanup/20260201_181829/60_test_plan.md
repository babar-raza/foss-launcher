# Test Plan

## Test Command Discovery

### pyproject.toml
No pytest config found

### Makefile
lint:
test:

### GitHub Actions
.github/workflows/ai-governance-check.yml
.github/workflows/ci.yml

## Test Commands from Makefile

```makefile
test:
	$(VENV_PY) -m pytest
```

## Chosen Test Strategy

Based on discovery, will run:

1. \ - for code quality checks
2. \ - for unit/integration tests

## Branches to Test

1. main (baseline)
2. feat/golden-2pilots-20260201 (current branch)
3. impl/tc300-wire-orchestrator-20260128 (top candidate - largest superset)
4. fix/env-gates-20260128-1615 (second candidate)
5. feat/TC-600-failure-recovery (TC consolidation point)

## Test Execution Results

**Note:** Test execution was skipped due to environment limitations (make not available in Windows Git Bash).

**Recommendation:** User should manually test top candidates:

```bash
# Test each candidate branch
git checkout impl/tc300-wire-orchestrator-20260128
python -m pytest
```

The branch with passing tests should be prioritized for merging.
