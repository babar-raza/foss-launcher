---
id: TC-3843
title: "Section Prompt Golden Injection + LLM Response Validator (G002)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [golden, section-prompt, llm-validator, generate]
depends_on: [TC-3842]
allowed_paths:
  - plans/taskcards/TC-3843_section_prompt_golden_injection.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/prompts/section_writer.txt
  - src/launcher/shared/llm_response_validator.py
  - tests/unit/workers/test_section_prompt.py
  - tests/unit/shared/test_llm_response_validator.py
evidence_required:
  - reports/TC-3843/evidence.md
---

# Taskcard TC-3843 — Section Prompt Golden Injection + LLM Response Validator (G002)

## Objective

Add a golden reference block to `build_section_prompt()` in `section_prompt.py`
and implement a real `validate_llm_response()` in `llm_response_validator.py`
(replacing the always-True stub) so that non-JSON and non-array LLM responses
are rejected before being processed.

## Required spec references

- `specs/golden.md` (golden reference injection contract)
- `specs/sandwich_model.md` (LLM response validation gate)

## Scope

### In scope
- **OPT-G**: `_build_golden_reference_block()` in section_prompt.py that calls `_load_golden_for_role()`
  and formats it as a markdown block
- Add `{golden_reference_block}` placeholder to `prompts/section_writer.txt`
- **OPT-3**: Implement `validate_llm_response()` in `llm_response_validator.py`:
  JSON parseable check → list check → element "type" key check
- **OPT-2**: Compute `max_tokens = max(512, section.max_words * 3)` and pass to LLM call
- **OPT-4**: Prune `api_surface_block` when golden spec has no "code" requirement

### Out of scope
- OPT-1 (json_schema from page_ir.schema.json) — complex schema derivation, deferred to Tier 3
- Heal directives injection — TC-3848 (Tier 2)
- Section parallelism — TC-3847 (Tier 2)

## Inputs

- `src/launcher/workers/generate/section_prompt.py` (636 lines)
- `src/launcher/shared/llm_response_validator.py` (23-line stub)
- `src/launcher/prompts/section_writer.txt` (existing prompt)
- `_load_golden_for_role()` from TC-3842

## Outputs

- `section_prompt.py` with `_build_golden_reference_block()` + golden injection
- `llm_response_validator.py` with real validation logic (JSON + list + type key checks)
- `section_writer.txt` with `{golden_reference_block}` placeholder
- Gate: LLM responses that are not JSON arrays are now caught before processing

## Allowed paths

- plans/taskcards/TC-3843_section_prompt_golden_injection.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/prompts/section_writer.txt
- src/launcher/shared/llm_response_validator.py
- tests/unit/workers/test_section_prompt.py
- tests/unit/shared/test_llm_response_validator.py

### Allowed paths rationale

Only these files need to change. `llm_response_validator.py` is the stub being replaced.

## Implementation steps

### Step 1: Implement validate_llm_response() in llm_response_validator.py

Replace the stub with:
```python
"""LLM response validation — checks JSON parseability, array structure, element type keys."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Result of LLM response validation."""
    is_valid: bool = True
    issues: list[str] = field(default_factory=list)


def validate_llm_response(response: str, **kwargs: Any) -> ValidationResult:
    """Validate that *response* is a JSON array of objects with a 'type' key.

    Three-layer check:
    1. JSON parseable
    2. Top-level value is a list
    3. Every element has a "type" key
    """
    issues: list[str] = []
    # Layer 1: JSON parseability
    try:
        parsed = json.loads(response)
    except (json.JSONDecodeError, ValueError) as exc:
        return ValidationResult(is_valid=False, issues=[f"Not valid JSON: {exc}"])

    # Layer 2: must be a list
    if not isinstance(parsed, list):
        return ValidationResult(
            is_valid=False,
            issues=[f"Expected JSON array, got {type(parsed).__name__}"],
        )

    # Layer 3: each element must have 'type' key
    for i, element in enumerate(parsed):
        if not isinstance(element, dict) or "type" not in element:
            issues.append(f"Element {i} missing 'type' key")

    return ValidationResult(is_valid=len(issues) == 0, issues=issues)


def enhance_prompt_for_retry(prompt: str, issues: list[str], **kwargs: Any) -> str:
    """Append validation failure context to retry prompt."""
    if not issues:
        return prompt
    issue_text = "\n".join(f"- {issue}" for issue in issues)
    return (
        prompt
        + f"\n\nPREVIOUS RESPONSE FAILED VALIDATION:\n{issue_text}\n"
        + "Return a valid JSON array where every element has a 'type' key."
    )
```

### Step 2: Add _build_golden_reference_block() to section_prompt.py

Add function near the other `_build_*_block()` helpers:
```python
def _build_golden_reference_block(
    page_role: str,
    section_heading: str,
    golden_dir: Path | None,
) -> str:
    """Return a formatted golden reference block for the section prompt.

    Returns empty string when golden reference is unavailable.
    """
    if golden_dir is None or not golden_dir.exists():
        return ""
    try:
        from launcher.shared.golden_loader import _load_golden_for_role
        excerpt = _load_golden_for_role(page_role, golden_dir, section_heading)
        if excerpt is None:
            return ""
        return (
            "\n## GOLDEN REFERENCE EXAMPLE\n"
            "The following is an A-grade example of this section type. "
            "Match its depth, tone, and structure:\n\n"
            f"{excerpt}\n"
            "## END GOLDEN REFERENCE\n"
        )
    except Exception:
        return ""
```

### Step 3: Wire golden block into build_section_prompt()

Locate the `build_section_prompt()` function. After building existing blocks,
add:
```python
golden_dir = getattr(context.config, "golden_dir", None)
if golden_dir is None:
    # Check pipeline config golden setting
    golden_cfg = getattr(context.config, "golden", {}) or {}
    if golden_cfg.get("enabled"):
        golden_dir = Path(golden_cfg.get("dir", "golden/"))
golden_reference_block = _build_golden_reference_block(
    page_role=page_plan.page_role,
    section_heading=section.heading,
    golden_dir=golden_dir,
)
```

Pass `golden_reference_block` into the prompt template format dict.

### Step 4: Add {golden_reference_block} to section_writer.txt

Find an appropriate location (after the context block, before instructions) and add:
```
{golden_reference_block}
```

### Step 5: Add tests

`tests/unit/shared/test_llm_response_validator.py`:
- Valid JSON array with type keys → `is_valid=True`
- Non-JSON string → `is_valid=False`, issue contains "Not valid JSON"
- JSON object (not array) → `is_valid=False`
- Array element missing 'type' key → `is_valid=False`
- Empty array → `is_valid=True` (no elements to check)

`tests/unit/workers/test_section_prompt.py`:
- golden_dir=None → golden_reference_block is empty string
- golden_dir missing → golden_reference_block is empty string
- Golden available → golden_reference_block contains "GOLDEN REFERENCE EXAMPLE"

## Failure modes

### Failure mode 1: {golden_reference_block} placeholder absent from section_writer.txt

**Detection**: `KeyError: 'golden_reference_block'` in `str.format()` call
**Resolution**: Ensure placeholder is added to section_writer.txt in Step 4; or use
`.format_map(defaultdict(str, ...))` which returns empty string for missing keys
**Gate**: Unit test with mocked prompt template

### Failure mode 2: _load_golden_for_role import fails in section_prompt.py

**Detection**: `ImportError` when building golden reference block
**Resolution**: Wrapped in `try/except Exception: return ""` — returns empty string on error
**Gate**: Unit test with import mocked to fail

### Failure mode 3: validate_llm_response rejects valid responses

**Detection**: Valid section blocks (JSON array with type keys) rejected
**Resolution**: Test with real section_prompt output before wiring validation into generate worker
Note: generate worker wiring is in TC-3847 — this TC only implements the validator
**Gate**: Unit test: real section JSON → `is_valid=True`

## Task-specific review checklist

1. [ ] `validate_llm_response()` returns `is_valid=False` for non-JSON string
2. [ ] `validate_llm_response()` returns `is_valid=False` for JSON object (not array)
3. [ ] `validate_llm_response()` returns `is_valid=False` for array element missing 'type'
4. [ ] `validate_llm_response()` returns `is_valid=True` for valid array with type keys
5. [ ] `_build_golden_reference_block()` returns "" when golden_dir is None
6. [ ] `{golden_reference_block}` added to section_writer.txt

## Deliverables

1. `src/launcher/shared/llm_response_validator.py` — real validation logic
2. `src/launcher/workers/generate/section_prompt.py` — _build_golden_reference_block + wiring
3. `src/launcher/prompts/section_writer.txt` — {golden_reference_block} placeholder
4. `tests/unit/shared/test_llm_response_validator.py` — 5+ test cases
5. `tests/unit/workers/test_section_prompt.py` — golden reference block tests

## Acceptance checks

1. [ ] `pytest tests/unit/shared/test_llm_response_validator.py -v` — all PASS
2. [ ] `validate_llm_response('not json').is_valid == False`
3. [ ] `validate_llm_response('[{"type": "paragraph"}]').is_valid == True`
4. [ ] `pytest tests/ -x -q` — 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: llm_response_validator no longer returns always-True
- [ ] Evidence file: `reports/TC-3843/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_llm_response_validator.py tests/unit/workers/test_section_prompt.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All llm_response_validator tests pass (new file)
- All section_prompt tests pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: `_load_golden_for_role()` from TC-3842
**Downstream**: Generate worker calls `build_section_prompt()` → golden block injected into prompt; `validate_llm_response()` called post-LLM in generate worker (TC-3847)
**Contract**: `validate_llm_response(response: str) -> ValidationResult`; golden block is optional (empty string when unavailable)
