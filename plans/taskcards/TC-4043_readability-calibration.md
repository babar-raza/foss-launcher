---
id: TC-4043
title: "Readability calibration: FK 12-16 section in section_writer.txt"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [generate, readability, prompts, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4043_readability-calibration.md
  - src/launcher/prompts/section_writer.txt
evidence_required:
  - reports/TC-4043/evidence.md
---

# Taskcard TC-4043 — Readability calibration: FK 12-16 section in section_writer.txt

## Objective

Add explicit Flesch-Kincaid readability constraints to `section_writer.txt`. LLMs at
temperature 0.0 produce nominalization-heavy, clause-stacked prose that systematically
scores FK > 18-22. A single prompt section fixes the readability pattern across all pages
simultaneously.

Note: Pre-flight check 3 is required first — verify whether `readability.py` strips
backtick code spans before FK computation. If not, this TC should also patch readability.py.

## Required spec references

- `specs/worker_generate.md` (section generation prompt)

## Scope

### In scope
- `section_writer.txt`: add READABILITY REQUIREMENTS section

### Out of scope
- `readability.py` FK computation (conditional — only if pre-flight check 3 fails)

## Inputs

- `src/launcher/prompts/section_writer.txt` (current content)

## Outputs

- Modified `section_writer.txt` with FK 12-16 target, sentence-length guidance, active voice

## Allowed paths

- `plans/taskcards/TC-4043_readability-calibration.md`
- `src/launcher/prompts/section_writer.txt`

### Allowed paths rationale
Prompt-only change. No code modified.

## Implementation steps

### Step 1: Verify current state

Read `src/launcher/prompts/section_writer.txt`. Confirm no readability section exists.

### Step 2: Add readability section before the final output format instructions

Append to the prompt file (before the output format block if one exists, otherwise at end):

```
## Readability Requirements

Target Flesch-Kincaid grade level: 12–16 (college freshman to sophomore).
This is enforced by automated testing — non-compliance fails publication.

- Prefer short sentences: 15–25 words. Split compound sentences at conjunctions (and, but, so, because).
- Use active voice: "Call save() to write the file" not "The file is written by calling save()".
- Avoid nominalizations: write "configure" not "configuration of"; "convert" not "conversion of".
- One idea per sentence. Lead with the subject and verb.
- Technical terms (class names, method names, package names) are exempt from simplification.
- Do not pad content to meet word counts — quality over length.
```

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/unit/workers/test_publish.py
```

## Failure modes

### Failure mode 1: Prompt change causes existing tests to fail

**Detection**: Tests that assert specific prompt content fail
**Resolution**: The readability section is appended — it doesn't change existing content. Investigate which test asserts exact prompt text and update the expected string if needed.
**Gate**: Full test suite run.

### Failure mode 2: FK inflation from backtick technical terms persists

**Detection**: Readability check still reports HIGH on pages with dense API identifiers
**Resolution**: This TC adds readability TARGET to the prompt, instructing the LLM. If readability.py doesn't strip backtick spans, the measured FK will still be inflated by technical terms. Requires separate fix to readability.py (outside scope of this TC).
**Gate**: Pre-flight check 3 output.

### Failure mode 3: Prompt file uses CRLF on Windows and linter changes formatting

**Detection**: Git diff shows unexpected CRLF changes throughout file
**Resolution**: Use .gitattributes to normalize; or accept CRLF on Windows. Content is correct regardless.
**Gate**: Verify content, not line endings.

## Task-specific review checklist

1. [ ] `section_writer.txt` contains "Readability Requirements" heading
2. [ ] FK target 12-16 explicitly stated
3. [ ] Active voice instruction present
4. [ ] Sentence length guidance (15-25 words) present
5. [ ] Technical terms exemption clause present
6. [ ] Existing prompt content unchanged (section APPENDED, not replacing)
7. [ ] Full test suite passes
8. [ ] Docstring: N/A (prompt file, not code)
9. [ ] Spec: no spec drift
10. [ ] Docs: no trigger
11. [ ] Section does not contradict any existing instruction in the prompt

## Deliverables

1. Modified `src/launcher/prompts/section_writer.txt`
2. `reports/TC-4043/evidence.md`

## Acceptance checks

1. [ ] `grep "Readability Requirements" src/launcher/prompts/section_writer.txt` — present
2. [ ] `grep "12–16\|12-16" src/launcher/prompts/section_writer.txt` — present
3. [ ] Full test suite: 0 regressions

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: `reports/TC-4043/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/unit/workers/test_publish.py
```

## Integration boundary proven

**Upstream**: N/A (prompt file read by LLM call in generate worker)
**Downstream**: LLM sections produced with FK 12-16 target
**Contract**: section_writer.txt is the base system prompt for all section generation calls
