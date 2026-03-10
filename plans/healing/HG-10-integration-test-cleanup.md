# HG-10 — Integration Test Unused Imports Cleanup

**Status**: Done
**Gap linkage**: G10 (unused imports in test_understand_pipeline.py)
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: Low

## Context

`tests/integration/test_understand_pipeline.py` contains unused imports:

```python
import asyncio                           # never used
from typing import Any                   # never used
from unittest.mock import AsyncMock, MagicMock, patch  # never used
```

These were left from a template/draft that was pared back. They increase import time
slightly and signal incomplete review to future maintainers.

## Scope

### Fix

Remove the 3 unused import lines.

### Allowed paths

```
tests/integration/test_understand_pipeline.py
plans/taskcards/TC-4016_integration_test_cleanup.md
```

### Forbidden

All other paths.

## Acceptance checks

### CLI
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_understand_pipeline.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
# Verify no unused import warnings:
.venv/Scripts/python.exe -m py_compile tests/integration/test_understand_pipeline.py && echo OK
```
41 tests still pass. Zero new failures.

### Tests
No new tests needed — this is a cleanup.

### No mock data in production paths
N/A

## Deliverables

1. Updated `tests/integration/test_understand_pipeline.py` (remove 3 import lines)
2. `plans/taskcards/TC-4016_integration_test_cleanup.md`

## Hard rules

- Remove ONLY the 3 identified unused imports
- Do NOT reorder remaining imports
- Do NOT add linting configuration

## Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Minimality | Only 3 lines removed; nothing else changed |
| Correctness | All 41 tests still pass |
| Readability | No dead imports confusing future readers |

## Now (runbook)

```
1. Read tests/integration/test_understand_pipeline.py (import section)
2. Remove: import asyncio
3. Remove: from typing import Any
4. Remove: from unittest.mock import AsyncMock, MagicMock, patch
5. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_understand_pipeline.py -v
6. Run full suite
```
