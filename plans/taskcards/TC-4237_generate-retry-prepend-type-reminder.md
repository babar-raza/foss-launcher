---
id: TC-4237
title: "G-5: Add type-field reminder to generate retry prepend"
status: Done
priority: High
owner: "agent-B"
updated: "2026-03-12"
tags: [generate, retry, block-type, l1-validator]
depends_on: [TC-4228]
allowed_paths:
  - plans/taskcards/TC-4237_generate-retry-prepend-type-reminder.md
  - src/launcher/workers/generate/worker.py
evidence_required:
  - reports/agents/B_implementation/TC-4237/evidence.md
---

# Taskcard TC-4237 — G-5: Add type-field reminder to generate retry prepend

## Objective

Reduce residual `L1_VALIDATOR_FAIL` events by adding an explicit `type`-field reminder to both retry paths in the generate worker, ensuring the LLM cannot miss the requirement when retrying a section.

## Required spec references

- `specs/worker_generate.md` (Section: Post-LLM validation — L1 validator, retry logic)

## Scope

### In scope
- Add type-field reminder to `_retry_additions` in the section quality check retry loop (`worker.py:1100-1128`)
- Add type-field violation to `violations` list in `enforce_block_spec` Pass 2 (`worker.py:1517-1532`)
- Raise `prepend` hard cap from 300 → 500 chars (`worker.py:1542`)

### Out of scope
- Advisor confidence thresholds / circuit breaker (separate concern)
- `max_re_runs` configuration (content quality issue, not a bug)
- Further edits to `section_writer.txt` (base CRITICAL note already present at line 76)
- Schema or model changes
- `section_validator.py` (coercion already done by TC-4228)

## Inputs

- `src/launcher/workers/generate/worker.py` (lines 1100-1128: section quality check retry; lines 1517-1542: enforce_block_spec Pass 2)

## Outputs

- Modified `src/launcher/workers/generate/worker.py` with type-field reminder in both retry paths and raised prepend cap

## Allowed paths

- plans/taskcards/TC-4237_generate-retry-prepend-type-reminder.md
- src/launcher/workers/generate/worker.py

### Allowed paths rationale
Only worker.py needs changes. section_validator.py (TC-4228) and section_writer.txt are already correct.

## Implementation steps

### Step 1: Add type reminder to section quality check retry

In `worker.py` in the section quality check retry block, just before:
```python
_retry_prompt = prompt + "\n\n" + "\n".join(_retry_additions)
```
Add:
```python
_retry_additions.append(
    "CRITICAL: Every block in your JSON array MUST include a \"type\" field"
    " (paragraph, code, list, heading, table, callout). Missing type = invalid block."
)
```

### Step 2: Add type reminder to enforce_block_spec Pass 2 violations

In `enforce_block_spec`, after the existing violations are populated (after line 1532), add:
```python
violations.append(
    "- CRITICAL: Every block MUST include a \"type\" field"
    " (paragraph, code, list, heading, table, callout)"
)
```

### Step 3: Raise prepend cap from 300 to 500

Change:
```python
prepend = prepend[:300]  # hard cap
```
To:
```python
prepend = prepend[:500]  # raised from 300 — type-reminder + violations can now fit
```

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ tests/unit/workers/test_generate.py -x -q
```

## Failure modes

### Failure mode 1: Test asserts exact retry prompt content

**Detection**: Test failure with mismatch on retry prompt string content.
**Resolution**: Update test expectations to include the new type-field reminder in `_retry_additions`.
**Gate**: `tests/unit/workers/generate/` test suite.

### Failure mode 2: Prepend cap still too small

**Detection**: "REQUIRED FOR THIS RETRY" instruction gets truncated in long violation lists.
**Resolution**: Increase cap further (e.g., 600) or restructure to always put the closing instruction outside the cap.
**Gate**: Manual inspection of the prepend string in test output.

### Failure mode 3: Double type reminder (coercion + prepend)

**Detection**: Verbose DEBUG logs show type coercion AND type reminder both firing for same block.
**Resolution**: This is intentional — coercion fixes the block silently, prepend prevents future omissions. No conflict.
**Gate**: No test failure expected; behavior is additive and complementary.

## Task-specific review checklist

1. [ ] `_retry_additions` in quality check retry includes type reminder unconditionally
2. [ ] `violations` in `enforce_block_spec` Pass 2 includes type reminder unconditionally
3. [ ] `prepend[:300]` raised to `prepend[:500]` and comment updated
4. [ ] Existing tests pass without modification (or test expectations updated for new reminder text)
5. [ ] `section_validator.py` NOT modified (TC-4228 coercion untouched)
6. [ ] `section_writer.txt` NOT modified (base CRITICAL note untouched)
7. [ ] Docstrings for `_generate_section` and `enforce_block_spec` updated to note type reminder
8. [ ] Spec `specs/worker_generate.md` confirmed — no behavioral drift (retry logic enhancement, not new gate)
9. [ ] Schema description fields: no new schema fields added
10. [ ] `docs/README.md` ownership map: no guide update needed (internal retry logic)
11. [ ] No new `docs/guides/` file created

## Deliverables

1. Modified `src/launcher/workers/generate/worker.py` (3 changes)
2. `reports/agents/B_implementation/TC-4237/evidence.md`

## Acceptance checks

1. [ ] `_retry_additions` always contains type-field reminder when quality check retry fires
2. [ ] `violations` always contains type-field reminder in `enforce_block_spec` Pass 2
3. [ ] All generate worker tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ tests/unit/workers/test_generate.py -x -q`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/B_implementation/TC-4237/evidence.md
- [ ] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ tests/unit/workers/test_generate.py -x -q
```

**Expected results**:
- All tests pass
- Both retry paths now contain explicit type-field reminder

## Integration boundary proven

**Upstream**: LLM returns JSON array — may omit `type` field
**Downstream**: `parse_and_validate_blocks` → `_validate_block` (TC-4228 coercion handles missing type)
**Contract**: Retry prepend is prepended/appended to original prompt before re-calling LLM; type reminder increases LLM compliance
