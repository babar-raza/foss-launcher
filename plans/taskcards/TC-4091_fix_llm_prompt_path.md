---
id: TC-4091
title: "Fix LLM prompt path: parents[2] → parents[3] in _llm.py"
status: Done
priority: High
owner: "agent"
updated: "2026-03-11"
tags: [bug, understand, llm, claims]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4091_fix_llm_prompt_path.md
  - src/launcher/workers/understand/extract/_llm.py
  - tests/unit/workers/understand/test_extract.py
  - reports/TC-4091/evidence.md
evidence_required:
  - reports/TC-4091/evidence.md
---

# Taskcard TC-4091 — Fix LLM prompt path: parents[2] → parents[3] in _llm.py

## Objective

Fix a wrong parent-directory depth in `_llm.py` that causes LLM claim extraction to
silently fall back to deterministic mode on every run, degrading 66% of claims from
LLM-reasoned API facts to generic README bullets.

## Required spec references

- `specs/worker_understand.md` (Section: LLM claim extraction — prompt loading)

## Scope

### In scope
- One-character fix in `src/launcher/workers/understand/extract/_llm.py` line 133
- Three regression-guard tests in `tests/unit/workers/understand/test_extract.py`
- Evidence file at `reports/TC-4091/evidence.md`

### Out of scope
- Changing the prompt content in `claim_extractor.txt` (separate concern)
- Refactoring how prompts are discovered (future improvement)
- Any other workers or extraction paths

## Inputs

- `src/launcher/workers/understand/extract/_llm.py` — file containing the wrong path
- `src/launcher/prompts/claim_extractor.txt` — the prompt file that should be found

## Outputs

- Fixed `_llm.py` using `parents[3]` so `claim_extractor.txt` resolves correctly
- Three new tests guarding the correct path
- Evidence file with test output confirming the fix

## Allowed paths

- plans/taskcards/TC-4091_fix_llm_prompt_path.md
- src/launcher/workers/understand/extract/_llm.py
- tests/unit/workers/understand/test_extract.py
- reports/TC-4091/evidence.md

### Allowed paths rationale
- Taskcard itself must be in allowed paths per AG-002
- `_llm.py` is the file containing the bug
- `test_extract.py` is the existing test file for understand/extract
- `reports/TC-4091/evidence.md` holds the evidence bundle

## Implementation steps

### Step 1: Fix the wrong parent depth

In `src/launcher/workers/understand/extract/_llm.py` line 133, change:
```python
prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "claim_extractor.txt"
```
to:
```python
prompt_path = Path(__file__).resolve().parents[3] / "prompts" / "claim_extractor.txt"
```

Root cause: `__file__` is `src/launcher/workers/understand/extract/_llm.py`.
- `parents[0]` = `src/launcher/workers/understand/extract/`
- `parents[1]` = `src/launcher/workers/understand/`
- `parents[2]` = `src/launcher/workers/`   ← no `prompts/` here
- `parents[3]` = `src/launcher/`           ← `prompts/` lives here

### Step 2: Add regression-guard tests

Add class `TestTC4091LLMPromptPath` to `tests/unit/workers/understand/test_extract.py` with:
1. `test_llm_prompt_path_resolves_to_existing_file` — asserts `parents[3] / "prompts" / "claim_extractor.txt"` exists
2. `test_llm_prompt_path_parents3_is_launcher_root` — asserts `parents[3]` ends with `src/launcher` or `src\\launcher`
3. `test_prompt_path_does_not_use_old_parents2` — reads `_llm.py` source and asserts the prompt path line uses `parents[3]` not `parents[2]`

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py::TestTC4091LLMPromptPath -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --ignore=tests/unit/workers/test_publish.py
```

### Step 4: Capture evidence

Create `reports/TC-4091/evidence.md` with test output and confirmation that the prompt file exists.

## Failure modes

### Failure mode 1: parents[3] still wrong on some installs

**Detection**: `test_llm_prompt_path_resolves_to_existing_file` fails — file not found
**Resolution**: Check if the repo root has a non-standard layout; verify `src/launcher/prompts/claim_extractor.txt` is present
**Gate**: Test assertion

### Failure mode 2: Other callers still use wrong path

**Detection**: Pilot log still shows `[WARNING] LLM claim extraction failed, falling back to deterministic`
**Resolution**: `grep -r "parents\[2\]" src/launcher/` to find any other occurrences
**Gate**: Manual grep check before marking Done

### Failure mode 3: Test file import errors after edit

**Detection**: pytest collection error — ImportError or SyntaxError
**Resolution**: Verify the new test class doesn't shadow existing symbols; check indentation
**Gate**: `pytest --collect-only tests/unit/workers/understand/test_extract.py` runs clean

## Task-specific review checklist

1. [x] `_llm.py` line 133 uses `parents[3]` — confirmed by reading file after edit
2. [x] `src/launcher/prompts/claim_extractor.txt` confirmed to exist before writing tests
3. [x] All 3 new tests PASS with PYTHONHASHSEED=0
4. [x] Regression guard test reads actual source text of `_llm.py` (not a mock)
5. [x] Full test suite passes (ignoring test_publish.py per project convention)
6. [x] No other occurrences of `parents[2]` used for prompt loading elsewhere
7. [x] Docstrings updated for all new/changed public functions (no public signatures changed)
8. [x] Spec file updated if worker behavior changed (confirmed no spec drift — this is a path bug fix)
9. [x] Schema `"description"` fields present for all new/changed properties (no schema changes)
10. [x] Checked `docs/README.md` ownership map — no trigger event applies
11. [x] No new `docs/guides/` file added

## Deliverables

1. `src/launcher/workers/understand/extract/_llm.py` — with `parents[3]` fix on line 133
2. `tests/unit/workers/understand/test_extract.py` — with `TestTC4091LLMPromptPath` class (3 tests)
3. `reports/TC-4091/evidence.md` — test run output confirming all pass

## Acceptance checks

1. [x] `_llm.py:133` uses `parents[3]` not `parents[2]`
2. [x] All 3 new `TestTC4091LLMPromptPath` tests PASS
3. [x] Full test suite passes: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --ignore=tests/unit/workers/test_publish.py` — 3839 passed, 1 skipped, 3 xfailed
4. [x] Taskcard status set to `Done` with all acceptance checks marked [x]
5. [x] `reports/TC-4091/evidence.md` exists with test output

## Self-review

### Verification results
- [x] Tests: 3/3 PASS (TC-4091 tests)
- [x] Full suite: 3839 passed, 1 skipped, 3 xfailed — PASS
- [x] Evidence captured: reports/TC-4091/evidence.md
- [x] Doc freshness: confirmed no spec drift — this is a one-line path bug fix, no spec behavior change

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py::TestTC4091LLMPromptPath -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --ignore=tests/unit/workers/test_publish.py
```

**Expected results**:
- 3 new tests collected and all PASS
- Full test suite passes with no regressions

## Integration boundary proven

**Upstream**: `WorkerContext.llm_config` — provides LLM configuration to `_call_llm_extract`
**Downstream**: `_parse_claims_json` / LLM response — consumes the rendered prompt
**Contract**: `claim_extractor.txt` prompt template must be loadable at `src/launcher/prompts/claim_extractor.txt`; after fix, `Path(__file__).resolve().parents[3] / "prompts" / "claim_extractor.txt"` resolves to that file
