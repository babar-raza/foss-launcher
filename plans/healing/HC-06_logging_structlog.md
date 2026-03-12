---
id: HC-06
title: "ts_analyzer: switch from stdlib logging to project structlog"
status: Done
priority: Low
owner: "agent-B"
updated: "2026-03-07"
tags: [healing, observability, consistency]
depends_on: [TC-3790]
allowed_paths:
  - plans/healing/HC-06_logging_structlog.md
  - src/launcher/shared/ts_analyzer.py
evidence_required:
  - reports/healing/HC-06/evidence.md
---

# Taskcard HC-06 — Switch ts_analyzer to structlog

## Objective

`ts_analyzer.py` uses `import logging; logger = logging.getLogger(__name__)`
while the rest of the project uses `structlog`. Switch to the project's
logging convention for consistent observability.

## Required spec references

- `specs/observability.md` (Section: structured logging)

## Scope

### In scope
- Replace `import logging` with `import structlog` in ts_analyzer.py
- Replace `logger = logging.getLogger(__name__)` with `logger = structlog.get_logger(__name__)`
- Update all `logger.debug(...)` calls to use structlog kwargs style

### Out of scope
- Adding new log statements
- Changing log levels

## Inputs

- Existing `logger.debug()` calls in ts_analyzer.py

## Outputs

- ts_analyzer.py using structlog consistently

## Allowed paths

- plans/healing/HC-06_logging_structlog.md
- src/launcher/shared/ts_analyzer.py

### Allowed paths rationale
- ts_analyzer.py: only file needing the logging swap

## Implementation steps

### Step 1: Replace logging import

```python
# Before
import logging
logger = logging.getLogger(__name__)

# After
import structlog
logger = structlog.get_logger(__name__)
```

### Step 2: Update log call style

```python
# Before
logger.debug("Skipping snippet validation for %s", language)

# After
logger.debug("skipping_snippet_validation", language=language)
```

## Failure modes

### Failure mode 1: structlog not configured in test environment
**Detection**: Warning about unconfigured structlog
**Resolution**: Ensure test conftest configures structlog
**Gate**: Tests pass without warnings

### Failure mode 2: Log format change breaks log parsing
**Detection**: Downstream log aggregation stops matching
**Resolution**: Align with existing structlog format in other modules
**Gate**: Log output matches project convention

### Failure mode 3: structlog import fails
**Detection**: ImportError (should not happen — structlog is a project dependency)
**Resolution**: Verify structlog in pyproject.toml
**Gate**: Module loads successfully

## Task-specific review checklist

1. [ ] `import logging` replaced with `import structlog`
2. [ ] `logging.getLogger` replaced with `structlog.get_logger`
3. [ ] All `logger.debug` calls use structlog kwargs style
4. [ ] No stdlib logging references remain in ts_analyzer.py
5. [ ] Log messages match project conventions (lowercase, snake_case events)
6. [ ] All tests pass

## Deliverables

1. Updated `src/launcher/shared/ts_analyzer.py`
2. Evidence at `reports/healing/HC-06/evidence.md`

## Acceptance checks

1. [ ] No `import logging` in ts_analyzer.py
2. [ ] `structlog.get_logger` used
3. [ ] Full suite: 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/healing/HC-06/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ts_analyzer.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x
```

**Expected results**:
- All existing ts_analyzer tests pass
- No logging-related warnings

## Integration boundary proven

**Upstream**: structlog configuration in project setup
**Downstream**: Log aggregation and observability tools
**Contract**: structlog.get_logger() returns a bound logger with standard interface
