---
id: TC-4036
title: "Wave 3A: Fix keyword density contradiction in section_writer.txt"
status: Done
priority: Normal
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-3]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4036_wave3a-prompt-keyword-density-fix.md
  - src/launcher/prompts/section_writer.txt
evidence_required:
  - reports/TC-4036/evidence.md
---

# Taskcard TC-4036 — Wave 3A: Fix keyword density contradiction in section_writer.txt

## Objective
Line 45 of `section_writer.txt` contains "aim for 1-2 keyword appearances per 100 words of prose, never more" which directly contradicts "Do NOT add 'When working with ...' patterns" on the same line. With 8 SEO keywords, hitting 1-2/100 words forces keyword stuffing. Remove the per-100-words metric, keeping only the "incorporate naturally" instruction.

## Required spec references
- `crispy-growing-pebble.md` Wave 3A

## Scope
### In scope
- Remove "aim for 1-2 keyword appearances per 100 words of prose, never more" metric from line 45
- Keep "incorporate naturally" and the prohibition on keyword-stuffing patterns

### Out of scope
- Other prompt sections (claims, API surface, skills blocks)
- Removing the SEO keywords block entirely (Wave 2E covers that)

## Inputs
- `src/launcher/prompts/section_writer.txt` line 45

## Outputs
- Updated `section_writer.txt` without the contradictory density metric

## Allowed paths
- plans/taskcards/TC-4036_wave3a-prompt-keyword-density-fix.md
- src/launcher/prompts/section_writer.txt

## Implementation steps
### Step 1: Edit line 45 in section_writer.txt
Change:
```
- Incorporate SEO keywords naturally — aim for 1-2 keyword appearances per 100 words of prose, never more. Do NOT add "When working with ..." keyword-stuffing phrases
```
To:
```
- Incorporate SEO keywords naturally — aim for at most 1-2 appearances per section total. Do NOT add "When working with ..." keyword-stuffing phrases
```

## Failure modes
### Failure mode 1: LLM ignores keywords entirely
**Detection**: Generated content has 0 keyword occurrences in SEO check
**Resolution**: The instruction still says "incorporate naturally" — 0 occurrences is an LLM choice, not a prompt error
**Gate**: Not a regression from this change; existing seo check still fires if 0 keywords

### Failure mode 2: Test fixture hardcodes prompt line content
**Detection**: test_section_prompt.py fixture match fails
**Resolution**: Update fixture to match new line
**Gate**: All tests pass

### Failure mode 3: Other lines reference the 100-words metric
**Detection**: Grep for "100 words" in prompts/
**Resolution**: Remove all occurrences
**Gate**: No remaining "per 100 words" in prompts/

## Task-specific review checklist
1. [ ] "per 100 words of prose, never more" removed from line 45
2. [ ] "incorporate naturally" instruction preserved
3. [ ] "Do NOT add 'When working with'" prohibition preserved
4. [ ] No other "per 100 words" metrics remain in prompts/
5. [ ] Tests pass
6. [ ] Diff is ≤ 2 lines changed

## Deliverables
1. Updated `src/launcher/prompts/section_writer.txt`

## Acceptance checks
1. [ ] "per 100 words" not present in section_writer.txt
2. [ ] Tests pass

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "section_prompt or generate" --tb=short -q
```

## Integration boundary proven
**Upstream**: section_writer.txt is read by section_prompt.py and injected as system prompt
**Downstream**: LLM receives the prompt and generates section content
**Contract**: Prompt text is plain string; this change removes a contradictory instruction
