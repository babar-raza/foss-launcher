---
id: TC-3902
title: "SKIP markers: conditional evidence-absent instruction for code-required sections"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-09"
tags: [section_prompt, generate, thin-repo, evidence, hallucination-prevention]
depends_on: [TC-3903]
allowed_paths:
  - plans/taskcards/TC-3902_skip_markers_evidence_absent.md
  - src/launcher/workers/generate/section_prompt.py
  - tests/test_section_prompt.py
evidence_required:
  - reports/agents/B/TC-3902/evidence.md
---

# Taskcard TC-3902 — SKIP markers: evidence-absent instruction

## Objective

When a page section requires code (role in `_CODE_REQUIRED_ROLES`) but the repo has no
executable snippets (`section_snippets` empty), inject a hard "write prose only" instruction
into the section prompt. This prevents the LLM from fabricating code blocks, which causes
11 code_correctness + 9 factual_accuracy HIGH severity findings in the 3D TypeScript run.

## Required spec references

- `specs/worker_generate.md` (Section: Section prompt construction)

## Scope

### In scope
- Add `skip_instruction` conditional in `section_prompt.py` (in `build_section_prompt()`)
- Inject instruction only when `section_snippets == []` AND `page.page_role in _CODE_REQUIRED_ROLES` AND (optionally) `code_evidence_sparse=True` from TC-3903
- Add `{skip_instruction}` placeholder to `section_writer.txt` prompt template

### Out of scope
- Adding `[SKIP]` block type to BlockIR (not needed — instruction says "write prose only")
- Changes to evaluate worker (no new finding type)
- Changing behavior when snippets exist (rich repos never affected)

## Inputs

- `src/launcher/workers/generate/section_prompt.py:682-730` — `build_section_prompt()`
- `src/launcher/prompts/section_writer.txt` — prompt template
- `_CODE_REQUIRED_ROLES` frozenset in `src/launcher/workers/generate/worker.py:53`

## Outputs

- Updated `section_prompt.py` with conditional instruction injection
- Updated `section_writer.txt` with `{skip_instruction}` placeholder
- Tests verifying injection fires only for evidence-absent + code-required cases

## Allowed paths

- plans/taskcards/TC-3902_skip_markers_evidence_absent.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/prompts/section_writer.txt
- tests/test_section_prompt.py

### Allowed paths rationale
- `section_prompt.py`: where `build_section_prompt()` constructs the prompt
- `section_writer.txt`: prompt template that needs the placeholder
- `tests/test_section_prompt.py`: verification

## Implementation steps

### Step 1: Add `{skip_instruction}` to `section_writer.txt`

Add a `{skip_instruction}` slot immediately before `STRICT RULES:`, so:
```
{skip_instruction}STRICT RULES:
```

When `skip_instruction=""` (rich repos), this renders as blank → no change to prompt.
When populated, the instruction appears before the rules, giving it highest weight.

### Step 2: Update `section_prompt.py` in `build_section_prompt()`

Import `_CODE_REQUIRED_ROLES` (or pass it as a parameter; it's in worker.py):

```python
# Dynamically import to avoid circular — _CODE_REQUIRED_ROLES is a frozenset constant
from launcher.workers.generate.worker import _CODE_REQUIRED_ROLES
```

In `build_section_prompt()`, after `snippets_block` is computed (line ~592):

```python
# Inject evidence-absent instruction only when:
# 1. This section role requires code blocks, AND
# 2. No executable snippets are available for this section
_code_evidence_sparse = getattr(
    getattr(page, "richness_tier", None), "code_evidence_sparse", False
)
_no_snippets = not section_snippets
_code_role = getattr(page, "page_role", "") in _CODE_REQUIRED_ROLES

if _no_snippets and (_code_role or _code_evidence_sparse):
    skip_instruction = (
        "EVIDENCE ABSENT: The CODE EXAMPLES section above is empty — "
        "no working snippets were extracted from this repository. "
        "Write prose only for this section. "
        "Do NOT generate any code block. "
        "Omit any fenced code block entirely rather than fabricating one.\n\n"
    )
else:
    skip_instruction = ""
```

Pass `skip_instruction=skip_instruction` to the template `format()` call.

### Step 3: Tests in `tests/test_section_prompt.py`

1. Rich repo (section_snippets non-empty, code_required_role) → `skip_instruction == ""`
2. Thin repo (section_snippets empty, code_required_role) → `"EVIDENCE ABSENT"` in prompt
3. Thin repo (section_snippets empty, non-code role) → `skip_instruction == ""`
4. Rich repo with code_evidence_sparse=False → `skip_instruction == ""`

## Failure modes

### Failure mode 1: Circular import of `_CODE_REQUIRED_ROLES`

**Detection**: `ImportError` on `from launcher.workers.generate.worker import _CODE_REQUIRED_ROLES`
**Resolution**: Move `_CODE_REQUIRED_ROLES` to `section_prompt.py` or a shared constants module. It's a frozenset of strings — no dependencies.
**Gate**: Test suite import check

### Failure mode 2: `section_writer.txt` has `{skip_instruction}` but `build_section_prompt()` doesn't pass it

**Detection**: `KeyError: 'skip_instruction'` in `template.format(...)`
**Resolution**: Always pass `skip_instruction=""` as default — never omit the key from format().
**Gate**: Unit test with rich repo (skip_instruction="")

### Failure mode 3: LLM ignores the instruction and generates code anyway

**Detection**: code_correctness findings still appear in evaluate output
**Resolution**: This is a known LLM compliance issue. The instruction is a best-effort guard. The existing HALLUCINATION PREVENTION rules (section_writer.txt:52-58) remain. The downstream _validate_identifiers + _sanitize_code_blocks provide additional safety nets.
**Gate**: Not a hard gate — reduce HIGH findings, not eliminate them

## Task-specific review checklist

1. [ ] `{skip_instruction}` placeholder added to `section_writer.txt` before STRICT RULES
2. [ ] `skip_instruction` always passed to `template.format()` (never omitted)
3. [ ] Condition: `not section_snippets AND (code_role OR code_evidence_sparse)`
4. [ ] Rich repo with snippets: `skip_instruction == ""`
5. [ ] Thin code-required role with no snippets: `"EVIDENCE ABSENT"` in rendered prompt
6. [ ] Non-code role with no snippets: `skip_instruction == ""`
7. [ ] Docstrings updated for changed function
8. [ ] Spec file updated if worker behavior changed
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map
11. [ ] If new docs guide added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/workers/generate/section_prompt.py` — conditional skip_instruction logic
2. `src/launcher/prompts/section_writer.txt` — `{skip_instruction}` placeholder
3. `tests/test_section_prompt.py` — 4 new test cases
4. `reports/agents/B/TC-3902/evidence.md`

## Acceptance checks

1. [ ] Prompt for thin-repo code-required section contains "EVIDENCE ABSENT"
2. [ ] Prompt for rich-repo code-required section does NOT contain "EVIDENCE ABSENT"
3. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/B/TC-3902/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_section_prompt.py -v -k "skip or evidence_absent"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -5
```

## Integration boundary proven

**Upstream**: `build_section_prompt()` receives `page` (PlannedPage with richness_tier) + `section_snippets`
**Downstream**: LLM sees the instruction and (ideally) omits code blocks
**Contract**: `skip_instruction=""` for rich repos — zero behavioral change
