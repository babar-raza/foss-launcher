---
id: TC-4223
title: "Prepend retry hint in enhance_prompt_for_retry instead of appending"
status: Done
priority: Medium
owner: "orchestrator"
updated: "2026-03-12"
tags: [generate, l1-validator, llm]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4223_l1-validator-prepend.md
  - src/launcher/shared/llm_response_validator.py
  - tests/unit/shared/
evidence_required:
  - reports/agents/B/TC-4223/evidence.md
---

# Taskcard TC-4223 — Prepend retry hint in enhance_prompt_for_retry instead of appending

## Objective

The generate worker fails with `L1_VALIDATOR_FAIL` on approximately 50% of
LLM calls. The model produces output that does not satisfy the L1 format
check (e.g., missing required JSON envelope, wrong top-level structure), the
validator retries with an "enhanced" prompt, but the retry fails at the same
rate as the first attempt.

Root cause: `enhance_prompt_for_retry()` in `llm_response_validator.py`
appends the format correction hint to the END of the prompt string. Modern
LLMs with long-context attention give substantially less weight to instructions
at the tail of a multi-thousand-token prompt. The retry hint lands in a "lost
in the middle" (or rather, "lost at the end") zone where the model is unlikely
to register it.

Fix: restructure `enhance_prompt_for_retry()` to prepend a `CRITICAL:`
notice BEFORE the original prompt body. The format instruction must be the
first thing the model reads, not the last. This aligns with standard
prompt-engineering practice for instruction-following models.

## Required spec references

- `src/launcher/shared/llm_response_validator.py` — function
  `enhance_prompt_for_retry`, the only file requiring change
- `specs/system_overview.md` — sandwich model: engineering wraps every LLM
  call; the L1 validator is the post-call engineering layer; the retry prompt
  is the corrective engineering wrapper

## Scope

### In scope

- Change `enhance_prompt_for_retry()` to prepend the format hint rather than
  append it
- The prepended block must start with a `CRITICAL:` or `IMPORTANT:` marker
  that is visually distinct from the main prompt body
- Update unit tests in `tests/unit/shared/` to assert the hint appears at the
  start of the returned string

### Out of scope

- Changes to the L1 validator check logic itself
- Changes to the generate worker's retry loop invocation
- Changes to the LLM client or provider
- Adding new retry attempts (the fix is about hint placement, not retry count)

## Inputs

- `src/launcher/shared/llm_response_validator.py` (current, appends hint)
- Existing unit tests in `tests/unit/shared/` covering
  `enhance_prompt_for_retry`

## Outputs

- `src/launcher/shared/llm_response_validator.py` with the hint prepended
- Unit tests updated to assert prepend behaviour

## Allowed paths

- plans/taskcards/TC-4223_l1-validator-prepend.md
- src/launcher/shared/llm_response_validator.py
- tests/unit/shared/

### Allowed paths rationale

The change is localised to one function in one shared utility file. The only
other change is to the corresponding unit tests. No worker, client, or
schema file needs to be touched.

## Implementation steps

### Step 1: Locate `enhance_prompt_for_retry`

Open `src/launcher/shared/llm_response_validator.py`. Find the
`enhance_prompt_for_retry` function. Read the current append pattern, which
likely looks similar to:

```python
def enhance_prompt_for_retry(prompt: str, failure_reason: str) -> str:
    hint = _build_format_hint(failure_reason)
    return prompt + "\n\n" + hint
```

Note the exact variable names and the hint construction logic — these must be
preserved; only the concatenation order changes.

### Step 2: Apply the prepend fix

Restructure the return statement so the CRITICAL block comes first:

```python
def enhance_prompt_for_retry(prompt: str, failure_reason: str) -> str:
    hint = _build_format_hint(failure_reason)
    critical_prefix = (
        "CRITICAL — FORMAT REQUIREMENT (read before everything else):\n"
        f"{hint}\n\n"
        "--- Original prompt follows ---\n\n"
    )
    return critical_prefix + prompt
```

Key requirements for the prepended block:
- Must begin with `CRITICAL` or `IMPORTANT` (uppercase, prominent).
- Must include the full `hint` text (do not truncate).
- Must include a visual separator (`---`) so the model can distinguish the
  correction notice from the original task instruction.
- Must not duplicate the hint at the end — remove any existing append.

### Step 3: Verify `_build_format_hint` is unchanged

Confirm that `_build_format_hint` (or the inline hint text) still produces the
same correction guidance as before. This step is a no-op unless the hint
construction was entangled with the append logic.

### Step 4: Update unit tests

In `tests/unit/shared/` (in the existing test file for
`llm_response_validator`):

1. Add a test that calls `enhance_prompt_for_retry("original prompt", reason)`
   and asserts `result.startswith("CRITICAL")`.
2. Add a test that asserts the original prompt text appears AFTER the CRITICAL
   block: `assert "original prompt" in result` and
   `result.index("CRITICAL") < result.index("original prompt")`.
3. Update any existing test that asserts the hint appears at the end — change
   it to assert the hint appears at the start.

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q 2>&1 | tail -10
```

Confirm all pass with 0 new failures.

## Failure modes

### Failure mode 1: Hint duplicated at both start and end

**Symptom**: The prepend is added but the original append is not removed;
the model receives two copies of the hint, which can increase prompt length
and trigger max_tokens truncation.
**Detection**: Unit test asserting `result.count(hint_fragment) == 1` fails.
**Resolution**: Remove the append from the return statement; keep only the
prepend.
**Gate**: Deduplication unit test.

### Failure mode 2: `_build_format_hint` returns empty string for some failure codes

**Symptom**: The CRITICAL prefix is prepended but the hint body is empty;
the model sees only the separator with no actionable instruction.
**Detection**: Unit test calling `enhance_prompt_for_retry` with each known
`failure_reason` enum value and asserting `len(hint) > 0`.
**Resolution**: Add a fallback in `_build_format_hint` that produces a generic
format reminder when no specific hint is registered for the reason code.
**Gate**: Per-failure-reason unit tests.

### Failure mode 3: Separator line confuses the model's instruction parsing

**Symptom**: After the fix, the model starts including the separator text
(`--- Original prompt follows ---`) verbatim in its output.
**Detection**: Live pipeline run shows `---` artifacts in generated content;
L1 validator check for structural contamination fires.
**Resolution**: Change the separator to a format the model is less likely to
reproduce (e.g., XML-style `<original_prompt>` tag); re-run a short pilot.
**Gate**: Content review of 3+ generated pages after the fix.

### Failure mode 4: Test for "hint at end" still passes because hint text appears in both positions

**Symptom**: An existing test that asserts `result.endswith(hint)` passes even
after the refactor because the hint string also happens to appear at the very
end of the original prompt.
**Detection**: Manual inspection of the test; assert
`not result.endswith(hint_fragment)` to catch this.
**Resolution**: Use `result.index(hint_fragment) < len(critical_prefix) + 10`
to assert the hint is near the start, not just somewhere in the string.
**Gate**: Improved positional assertion in test.

## Task-specific review checklist

1. [ ] `enhance_prompt_for_retry` return value starts with `CRITICAL` or
       `IMPORTANT` keyword
2. [ ] The original prompt body appears AFTER the CRITICAL block in the
       returned string
3. [ ] The original `append` of the hint has been removed (no duplicate)
4. [ ] A visual separator (`---` or equivalent) separates the critical block
       from the original prompt
5. [ ] Unit test asserts `result.startswith("CRITICAL")` (or `"IMPORTANT"`)
6. [ ] Unit test asserts `result.index("CRITICAL") < result.index(original_prompt_fragment)`
7. [ ] All pre-existing tests in `tests/unit/shared/` pass
8. [ ] Evidence file created at `reports/agents/B/TC-4223/evidence.md`

## Deliverables

1. Updated `src/launcher/shared/llm_response_validator.py` with prepend logic
2. New or updated unit tests in `tests/unit/shared/`
3. Evidence at `reports/agents/B/TC-4223/evidence.md`

## Acceptance checks

- [ ] `pytest tests/unit/shared/ -v` — all pass
- [ ] `pytest -x -q` — 0 new failures
- [ ] Code inspection confirms hint is prepended, not appended, in
      `enhance_prompt_for_retry`
- [ ] (Stretch) Live generate run shows reduced L1_VALIDATOR_FAIL rate
      compared to baseline

## Self-review

### Verification results

- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/B/TC-4223/evidence.md
- [ ] Prepend confirmed via code inspection: no residual append in function
- [ ] CRITICAL keyword confirmed present in prepended block

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q 2>&1 | tail -10
# Optional: run generate for 1 page to measure L1 retry rate:
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml \
  --resume-from generate --stop-after generate \
  --run-id 260311_190711_cells_python_6882 2>&1 | grep -i "L1_VALIDATOR"
```

**Expected results**:
- All shared unit tests pass
- Full suite: 0 new failures
- Live run (if executed): `L1_VALIDATOR_FAIL` messages significantly reduced
  or eliminated

## Integration boundary proven

**Upstream**: Generate worker calls the LLM client; the response fails L1
validation; the retry path calls `enhance_prompt_for_retry(original_prompt,
reason)` to produce an enhanced prompt for the second attempt.
**Downstream**: The enhanced prompt is passed back to the LLM client as the
`messages[0].content` (or equivalent); the model reads it top-to-bottom, so
instructions at the top receive maximum attention.
**Contract**: `enhance_prompt_for_retry` must return a string where the format
correction notice is positioned before the original task body, so the model
cannot ignore it due to attention decay over long prompts.
