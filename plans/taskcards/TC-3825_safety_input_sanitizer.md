---
id: TC-3825
title: "Safety input sanitization layer: XSS removal, secret redaction, size enforcement"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-08"
tags: [safety, sanitization, understand-worker, engineering-fix]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3825_safety_input_sanitizer.md
  - src/launcher/shared/input_sanitizer.py
  - src/launcher/workers/understand/scout.py
  - src/launcher/workers/understand/extract.py
  - tests/unit/shared/test_input_sanitizer.py
evidence_required:
  - reports/TC-3825/evidence.md
---

# Taskcard TC-3825 — Safety input sanitization layer

## Objective

Add a single-pass sanitization boundary at the pipeline input boundary (repo file reading and
claim text storage) so that XSS patterns, credential secrets, and oversized content cannot
propagate into LLM prompts or generated output. The evaluate safety check remains as a
post-generation defense-in-depth gate; this fix eliminates engineering-origin failures.

## Required spec references

- `specs/08_quality_gates.md` (Section: safety gate — XSS, secrets, oversized)

## Scope

### In scope
- New `src/launcher/shared/input_sanitizer.py` with `sanitize_input()` function
- Integration in `scout.py:_read_repo_content()` after each file read
- Integration in `extract.py` after claim normalization
- Full unit test coverage including idempotency property test

### Out of scope
- HTML escaping in ir_renderer (outputs Markdown, not HTML — escaping would corrupt output)
- Sanitizing LLM prompts themselves (they contain deliberate code examples)
- Commercial URL stripping (handled separately by generate worker)

## Inputs

- External repo file content (arbitrary text from untrusted repos)
- LLM-extracted claim text (may echo back injected content from repo)

## Outputs

- `SanitizationResult` dataclass documenting what was changed
- Sanitized text with XSS removed, secrets redacted, oversized content truncated
- Per-run sanitization stats logged and (aggregated) emittable via event

## Allowed paths

- plans/taskcards/TC-3825_safety_input_sanitizer.md
- src/launcher/shared/input_sanitizer.py
- src/launcher/workers/understand/scout.py
- src/launcher/workers/understand/extract.py
- tests/unit/shared/test_input_sanitizer.py

### Allowed paths rationale
All paths are either new files or the two understand-worker files where external content enters.

## Implementation steps

### Step 1: Create input_sanitizer.py

Rules applied in order:
1. Code block passthrough via line-by-line state machine (``` and ~~~ fence tracking)
2. XSS removal in prose regions
3. Secret redaction with negative lookbehind
4. Oversized truncation at word boundary

### Step 2: Integrate in scout.py _read_repo_content

After each `text = path.read_text(...)` call, apply `sanitize_input(text, max_chars=100_000)`.

### Step 3: Integrate in extract.py after filter_claims

After `claims = filter_claims(claims)`, sanitize each claim's text field.

### Step 4: Write tests

## Failure modes

### Failure mode 1: Code example with <script> tag is incorrectly stripped

**Detection**: Test `test_script_in_code_block_preserved` fails
**Resolution**: Verify the fence state machine correctly identifies ``` open/close;
  check that the sanitization functions only run on prose segments, not code segments
**Gate**: safety check on security documentation pages

### Failure mode 2: Idempotency broken — second pass changes content

**Detection**: `test_idempotent_*` tests fail
**Resolution**: Ensure XSS patterns don't reintroduce themselves (they should replace with "");
  verify secret replacement `[REDACTED]` doesn't match the secret pattern
**Gate**: pytest -x

### Failure mode 3: Legitimate short hex/base64 strings falsely redacted

**Detection**: `test_short_key_not_redacted` fails
**Resolution**: Verify negative lookbehind + minimum length 20+ chars in secret regex
**Gate**: pytest -x

## Task-specific review checklist

1. [ ] Code blocks (``` and ~~~) are exempt from XSS removal
2. [ ] `<script>` in prose is removed; `<script>` in code block is preserved
3. [ ] Secret pattern uses negative lookbehind to avoid mid-word matches
4. [ ] Truncation preserves last complete word before `max_chars`
5. [ ] `[REDACTED]` sentinel does not itself match the secret pattern (idempotency)
6. [ ] `sanitize_input(sanitize_input(t).text, ...).text == sanitize_input(t).text`
7. [ ] scout.py and extract.py log at WARNING when redaction_count > 0
8. [ ] All tests pass with PYTHONHASHSEED=0

## Deliverables

1. New `src/launcher/shared/input_sanitizer.py`
2. Modified `src/launcher/workers/understand/scout.py`
3. Modified `src/launcher/workers/understand/extract.py`
4. New `tests/unit/shared/test_input_sanitizer.py`

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_input_sanitizer.py -v` — all pass
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — 0 failures
3. [ ] `<script>` in repo content → removed before claim extraction
4. [ ] `sk-XXXXXXXX...` (20+ chars) in repo content → `[REDACTED]` before claim extraction

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: safety gate PASS
- [ ] Evidence captured: reports/TC-3825/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_input_sanitizer.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- 0 safety findings from engineering-origin XSS/secret inputs

## Integration boundary proven

**Upstream**: External repo files read by `scout.py`, LLM claim text in `extract.py`
**Downstream**: Claims passed to Planner, content context passed to Generate worker
**Contract**: All text stored in `repo_content` dict and `Claim.text` is free of XSS
  patterns, credentials, and oversized content before entering the LLM pipeline
