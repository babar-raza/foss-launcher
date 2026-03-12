---
id: TC-3848
title: "Section Prompt Heal Directive Injection (H3.1)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [heal, section-prompt, generate]
depends_on: [TC-3841, TC-3843]
allowed_paths:
  - plans/taskcards/TC-3848_section_prompt_heal_injection.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/prompts/section_writer.txt
  - tests/unit/workers/test_section_prompt.py
evidence_required:
  - reports/TC-3848/evidence.md
---

# Taskcard TC-3848 — Section Prompt Heal Directive Injection (H3.1)

## Objective

Inject a "HEAL DIRECTIVES" block into `build_section_prompt()` in `section_prompt.py`
so that when the heal CLI re-runs generation, worker-specific repair instructions from
`context.heal_metadata` are included in the LLM prompt.

## Required spec references

- `specs/heal.md` (heal directive injection contract)

## Scope

### In scope
- `_build_heal_directives_block(heal_metadata: dict, section_heading: str) -> str` in section_prompt.py
- Wire `heal_directives_block` into `build_section_prompt()` AFTER `golden_reference_block`
- Add `{heal_directives_block}` placeholder to `section_writer.txt`
- Build directives block from `heal_metadata.get("section_directives", {}).get(section_heading, [])`
  and `heal_metadata.get("page_directives", [])`

### Out of scope
- Workers acting on heal directives (TC-3849, TC-3850)
- Heal CLI generating the heal_metadata (TC-3851)

## Inputs

- `src/launcher/workers/generate/section_prompt.py` (TC-3843 Done — golden_reference_block present)
- `src/launcher/prompts/section_writer.txt` (TC-3843 Done — {golden_reference_block} placeholder present)
- `context.heal_metadata` dict from WorkerContext (TC-3841 Done)

## Outputs

- `section_prompt.py` with `_build_heal_directives_block()` and wiring
- `section_writer.txt` with `{heal_directives_block}` placeholder
- Empty string returned when heal_metadata is empty (normal mode)

## Allowed paths

- plans/taskcards/TC-3848_section_prompt_heal_injection.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/prompts/section_writer.txt
- tests/unit/workers/test_section_prompt.py

### Allowed paths rationale

section_prompt.py touched second time (after TC-3843); section_writer.txt updated; tests extended.

## Implementation steps

### Step 1: Add _build_heal_directives_block() to section_prompt.py

Add near `_build_golden_reference_block()`:
```python
def _build_heal_directives_block(
    heal_metadata: dict,
    section_heading: str,
) -> str:
    """Return a formatted heal directives block for the section prompt.

    Returns empty string when heal_metadata is empty (normal generation mode).

    Directives are sourced from:
    - heal_metadata["page_directives"]: list of str (apply to every section)
    - heal_metadata["section_directives"][section_heading]: list of str (section-specific)
    """
    if not heal_metadata:
        return ""

    directives: list[str] = []

    # Page-level directives (apply to every section)
    page_directives = heal_metadata.get("page_directives") or []
    directives.extend(str(d) for d in page_directives)

    # Section-specific directives (keyed by heading)
    section_directives_map = heal_metadata.get("section_directives") or {}
    section_specific = section_directives_map.get(section_heading) or []
    directives.extend(str(d) for d in section_specific)

    if not directives:
        return ""

    lines = "\n".join(f"- {d}" for d in directives)
    return (
        "\n## HEAL DIRECTIVES\n"
        "The previous generation had quality issues. Apply these specific corrections:\n\n"
        f"{lines}\n"
        "## END HEAL DIRECTIVES\n"
    )
```

### Step 2: Wire into build_section_prompt()

In `build_section_prompt()`, after `golden_reference_block = _build_golden_reference_block(...)`:
```python
heal_directives_block = _build_heal_directives_block(
    heal_metadata=getattr(context, "heal_metadata", {}) or {},
    section_heading=getattr(section, "heading", "") or "",
)
```

Add `heal_directives_block=heal_directives_block` to the `template.format(...)` call.

### Step 3: Add {heal_directives_block} to section_writer.txt

Find `{golden_reference_block}` in section_writer.txt and add AFTER it:
```
{heal_directives_block}
```

### Step 4: Add tests

Extend `tests/unit/workers/test_section_prompt.py`:
- Empty heal_metadata → heal_directives_block is ""
- heal_metadata with page_directives → "HEAL DIRECTIVES" in block
- heal_metadata with section_directives for matching heading → directive in block
- heal_metadata with section_directives for non-matching heading → empty string
- heal_metadata has both page and section directives → both in block

## Failure modes

### Failure mode 1: {heal_directives_block} placeholder missing from section_writer.txt

**Detection**: `KeyError: 'heal_directives_block'` in `str.format()` call
**Resolution**: Add placeholder to section_writer.txt AFTER `{golden_reference_block}`
**Gate**: Unit test with mocked template

### Failure mode 2: context.heal_metadata not available

**Detection**: `AttributeError: 'WorkerContext' has no attribute 'heal_metadata'`
**Resolution**: Use `getattr(context, "heal_metadata", {}) or {}` — safe default
**Gate**: Unit test with context that has no heal_metadata

### Failure mode 3: section_directives keys don't match section headings

**Detection**: Expected directives not appearing in prompt despite heal_metadata set
**Resolution**: Keys in section_directives must match exact section heading string.
Document that heal CLI must use exact headings from skeleton.
**Gate**: Unit test verifying exact heading key match

## Task-specific review checklist

1. [ ] `_build_heal_directives_block({}, "any")` returns ""
2. [ ] `_build_heal_directives_block({"page_directives": ["fix x"]}, "h")` returns non-empty
3. [ ] `{heal_directives_block}` added to section_writer.txt AFTER `{golden_reference_block}`
4. [ ] `build_section_prompt()` passes heal_directives_block from context.heal_metadata
5. [ ] No crash when context.heal_metadata is {} (normal mode)
6. [ ] All 5 new tests pass

## Deliverables

1. `src/launcher/workers/generate/section_prompt.py` — `_build_heal_directives_block()` + wiring
2. `src/launcher/prompts/section_writer.txt` — `{heal_directives_block}` placeholder
3. `tests/unit/workers/test_section_prompt.py` — 5 new test cases
4. `reports/TC-3848/evidence.md` — actual test output

## Acceptance checks

1. [x] `pytest tests/unit/workers/test_section_prompt.py -v` — all PASS (8/8)
2. [x] `_build_heal_directives_block({}, "h") == ""`
3. [x] `pytest tests/ -q` — 0 failures (2478 passed)

## Self-review

### Verification results
- [x] Tests: 8/8 PASS (3 existing + 5 new in TestBuildHealDirectivesBlock)
- [x] Validation: heal directives block empty in normal mode, present in heal mode
- [x] Evidence file: `reports/TC-3848/evidence.md`
- [x] Full suite: 2478 passed, 0 failed

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_section_prompt.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All section_prompt tests pass (existing + 5 new)
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: `context.heal_metadata` from WorkerContext (TC-3841); `golden_reference_block` from TC-3843
**Downstream**: Heal CLI (TC-3851) sets heal_metadata before re-running generate worker
**Contract**: `_build_heal_directives_block(heal_metadata: dict, section_heading: str) -> str`;
empty string when no directives; "HEAL DIRECTIVES" block when directives present
