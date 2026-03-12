---
id: SNP-02
title: "Add dedup_skipped counter to _extract_snippets() log output"
status: Done
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [understand, snippets, observability, TC-4063]
depends_on: [TC-4063, SNP-05]
allowed_paths:
  - plans/healing/SNP-02-dedup-observability.md
  - src/launcher/workers/understand/extract/_snippets.py
evidence_required:
  - reports/SNP-02/evidence.md
---

# SNP-02 — Add dedup_skipped counter to `_extract_snippets()` log output

## Objective

`_extract_snippets()` silently drops duplicate snippets via the dedup hash check added in
TC-4063. Without a counter in the log output, operators cannot tell how many duplicates were
removed, making it impossible to diagnose token-budget or quality issues that might stem from
over-aggressive deduplication.

## Required spec references

- `specs/worker_understand.md` (Phase B.3: snippet extraction contract + structured log output)

## Scope

### In scope
- Add `dedup_skipped: int = 0` counter in `_extract_snippets()`, incremented on each skip
- Add `logger.info("snippet_extraction: extracted=%d dedup_skipped=%d", len(snippets), dedup_skipped)`
  at the end of the function (before the return statement)
- Change the existing `logger.debug(...)` inside the dedup branch to use the counter:
  `logger.debug("Skipping duplicate snippet from %s (hash=%s)", rel_path, h)`

### Out of scope
- Emitting this data as a structured telemetry event (that is SNP-03)
- Changing the dedup algorithm or threshold

## Inputs

- `src/launcher/workers/understand/extract/_snippets.py` (function to modify)

## Outputs

- `_extract_snippets()` that logs `extracted` and `dedup_skipped` counts at INFO level

## Allowed paths

- plans/healing/SNP-02-dedup-observability.md
- src/launcher/workers/understand/extract/_snippets.py

### Allowed paths rationale
Only `_snippets.py` needs the counter and log line.

## Implementation steps

### Step 1: Add `dedup_skipped` counter

Inside `_extract_snippets()`, immediately after the `seen_hashes: set[str] = set()` line:
```python
dedup_skipped: int = 0
```

### Step 2: Increment in the dedup skip branch

Where the existing `continue` skips duplicate snippets, increment before the continue:
```python
h = _dedup_key(code.strip())
if h in seen_hashes:
    logger.debug("Skipping duplicate snippet from %s (hash=%s)", rel_path, h)
    dedup_skipped += 1
    continue
seen_hashes.add(h)
```

Apply the same pattern to the whole-file examples loop if it also has a dedup check.

### Step 3: Add info-level summary at end of function

Immediately before `return snippets`:
```python
logger.info(
    "snippet_extraction: extracted=%d dedup_skipped=%d",
    len(snippets),
    dedup_skipped,
)
```

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -q
```

## Failure modes

### Failure mode 1: `dedup_skipped` incremented in wrong branch

**Detection**: Log shows `dedup_skipped=0` even when duplicates are present in test
**Resolution**: Verify `dedup_skipped += 1` is INSIDE the `if h in seen_hashes:` block,
before the `continue` statement
**Gate**: SNP-01 dedup test (will catch if dedup isn't firing at all)

### Failure mode 2: Counter not reset between function calls

**Detection**: Second call to `_extract_snippets()` accumulates counts from previous call
**Resolution**: `dedup_skipped` is a local variable initialized at function entry — this
cannot happen; confirm the initialization is at the function body level, not module level
**Gate**: Unit test isolation

### Failure mode 3: Missing increment in whole-file examples loop

**Detection**: Duplicate whole-file snippets not counted in `dedup_skipped`
**Resolution**: Locate both dedup `continue` branches in `_extract_snippets()` and add the
increment to each one
**Gate**: Code review of `_snippets.py` showing two increment sites

## Task-specific review checklist

1. [ ] `dedup_skipped` initialized as local variable at top of `_extract_snippets()`
2. [ ] `dedup_skipped += 1` incremented in ALL dedup skip branches (fenced blocks + whole-file)
3. [ ] `logger.info("snippet_extraction: extracted=%d dedup_skipped=%d", ...)` present before return
4. [ ] Existing `logger.debug` in dedup branch updated to include `hash=%s`
5. [ ] No changes to dedup algorithm or thresholds
6. [ ] Unit tests still pass with the counter present
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — no guide trigger from log-only change
11. [ ] N/A — no new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/understand/extract/_snippets.py` with counter + info log
2. `reports/SNP-02/evidence.md` with grep output showing the new log line

## Acceptance checks

1. [ ] `grep "dedup_skipped" src/launcher/workers/understand/extract/_snippets.py` → matches
2. [ ] `grep "snippet_extraction:" src/launcher/workers/understand/extract/_snippets.py` → matches
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q` passes

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/SNP-02/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -q
```

**Expected results**:
- All existing tests pass
- SNP-01 dedup test passes (counter logic consistent with dedup logic)

## Integration boundary proven

**Upstream**: Dedup hash check in `_extract_snippets()` extraction loops
**Downstream**: Log output (INFO level) consumed by structured logging pipeline
**Contract**: `snippet_extraction: extracted=N dedup_skipped=M` log line at INFO level at function exit
