# EV-06 — Observability + Docstring Fixes

**Status:** Done (pre-existing)
**Gap linkage:** G-EV-10, G-EV-11
**Role:** Senior engineer. Drop-in, production-ready.

## Context

**G-EV-10:** None of the 3 new check functions (`check_repetition`, `check_product_names`, `check_semantic_structure`) emit any log messages. In production, when a check silently produces zero findings due to an edge case (e.g., empty product_name, no headings), there's no way to confirm the check ran vs was skipped.

**G-EV-11:** Worker docstring (worker.py:3) says "Run 8 deterministic checks" — should say 11 after TC-3777.

## Scope

### Fix

**Logging (G-EV-10):**
1. Add `import logging` + `logger = logging.getLogger(__name__)` to each new check file.
2. Add `logger.debug` at entry point of each check: `"[check_name] Evaluating %s", slug`
3. Add `logger.debug` when returning early: `"[product_names] No product_name provided, skipping for %s", slug`
4. Add `logger.debug` when findings are produced: `"[repetition] Found %d findings for %s", len(findings), slug`
5. Match existing check style (check_artifacts doesn't log either, but this is a good opportunity to set a pattern).

**Docstring (G-EV-11):**
1. Update `worker.py` module docstring: "Phase A: Run 8 deterministic checks" → "Phase A: Run 11 deterministic checks"

### Allowed paths
- `src/launcher/workers/evaluate/checks/repetition.py`
- `src/launcher/workers/evaluate/checks/product_names.py`
- `src/launcher/workers/evaluate/checks/semantic_structure.py`
- `src/launcher/workers/evaluate/worker.py` (docstring only)

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v` — all 78+ tests pass
- **Tests:** No new tests needed (logging is debug-level; docstring is documentation)
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** N/A

## Deliverables

- Modified `repetition.py`, `product_names.py`, `semantic_structure.py` with debug logging
- Modified `worker.py` docstring (1 line change)
- All existing tests still pass

## Hard rules

- Logging at `debug` level only — no info/warning for normal operation
- Only add `warning` level for actual skip conditions (empty product_name, no headings)
- No new deps
- Keep log format consistent: `[check_name] Message`
- No behavior change — logging only

## Review dimensions — what 5/5 means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Observability | Every check entry/exit/skip is logged at debug level; operators can trace check execution |
| Minimality | Only logging + docstring; no other changes |
| Correctness | Docstring accurately reflects 11 checks |
| Maintainability | Log format matches existing codebase patterns |
| Performance | Debug logging has no measurable overhead (not evaluated unless enabled) |

## Now (runbook)

```bash
# 1. Add logging to each file (3 files)
#    import logging
#    logger = logging.getLogger(__name__)
#    logger.debug("[check_name] ...") at key points

# 2. Update worker.py docstring line 3:
#    "Phase A: Run 11 deterministic checks on each generated page."

# 3. Run tests to confirm no breakage
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v

# 4. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```
