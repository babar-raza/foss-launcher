---
id: TC-3875
title: "Wave 2: Sandwich Architecture Audit — All LLM Call Sites"
status: In-Progress
priority: High
owner: "Agent-A"
updated: "2026-03-09"
tags: [wave-2, sandwich, audit, llm-calls]
depends_on: [TC-3872, TC-3873, TC-3874]
allowed_paths:
  - plans/taskcards/TC-3875_w2_sandwich_audit.md
  - reports/TC-3875/evidence.md
  - reports/TC-3875/sandwich_audit_table.md
evidence_required:
  - reports/TC-3875/evidence.md
---

# Taskcard TC-3875 — Wave 2: Sandwich Architecture Audit

## Objective

Audit every LLM call site in the pipeline to verify sandwich compliance:
`Engineering (structured input) → LLM (typed JSON output) → Engineering (validate/normalize)`.
Document violations and fix any calls that skip pre or post-engineering phases.

## Required spec references

- `specs/system_overview.md` (Section: Sandwich Model)
- `agents.md` (Section: Sandwich principle)

## Scope

### In scope
- Read all LLM call sites across the codebase
- Verify each has: structured pre-engineering input, typed JSON output spec, post-engineering validation/normalization
- Fix any violations found (add pre/post engineering wrappers)
- Produce sandwich_audit_table.md (one row per call site)
- Add `tools/check_sandwich.py` static analysis helper (optional, if time allows)

### Out of scope
- Changes to the LLM routing or model selection
- Changes to prompts (TC-3872 scope)
- Changes to generation worker flow (TC-3876/3877 scope)

## Inputs

- All `_call_llm` / `call_llm` / similar invocations across `src/launcher/`
- Prompt files in `src/launcher/prompts/`
- Worker files: understand/extract.py, generate/worker.py, generate/seo_metadata.py,
  evaluate/llm_review.py, heal/diagnostician (or similar)

## Outputs

- `reports/TC-3875/sandwich_audit_table.md` — one row per LLM call site
- `reports/TC-3875/evidence.md` — summary of violations found and fixed
- Any code fixes to non-compliant call sites

## Allowed paths

- plans/taskcards/TC-3875_w2_sandwich_audit.md
- reports/TC-3875/evidence.md
- reports/TC-3875/sandwich_audit_table.md
- src/launcher/workers/understand/extract.py (if violation found)
- src/launcher/workers/generate/seo_metadata.py (if violation found)
- src/launcher/workers/evaluate/llm_review.py (if violation found)
- src/launcher/clients/llm_provider.py (read only for audit)

## Implementation steps

### Step 1: Find all LLM call sites
```bash
grep -r "_call_llm\|call_llm\|LLMProvider\|llm_client\|llm_provider" src/launcher/ --include="*.py" -l
```
For each file found, identify all call sites.

### Step 2: For each call site, verify sandwich compliance
Check: (1) Is there structured pre-engineering input preparation? (2) Does the prompt specify typed JSON output? (3) Is output parsed + validated after the call?

### Step 3: Document in sandwich_audit_table.md
Format:
| Call Site | File:Line | Pre-Engineering | Typed Output | Post-Engineering | Status |
|-----------|-----------|----------------|--------------|-----------------|--------|
| Claim extraction | extract.py:L123 | ✓ structured claims_context | ✓ JSON array | ✓ validate + normalize | PASS |

### Step 4: Fix violations
For each FAIL entry: add the missing engineering layer.

## Failure modes

### Failure mode 1: LLM call has no structured input (raw text only)
**Detection**: Call site passes string concatenation without schema
**Resolution**: Extract facts into structured dict; pass as template vars to prompt
**Gate**: sandwich_audit_table row shows ✓ for Pre-Engineering

### Failure mode 2: LLM output is parsed but not validated against schema
**Detection**: JSON parsed but no pydantic/schema validation
**Resolution**: Add pydantic model validation after JSON parse
**Gate**: sandwich_audit_table row shows ✓ for Post-Engineering

### Failure mode 3: No violations found — audit reveals full compliance
**Detection**: All rows in audit table show PASS
**Resolution**: Document as complete. TC-3875 closes as "audit confirmed — no fixes needed"
**Gate**: Audit table complete and documented

## Task-specific review checklist

1. [ ] All LLM call sites identified (grep result documented)
2. [ ] Each call site evaluated for pre-engineering completeness
3. [ ] Each call site evaluated for typed JSON output requirement in prompt
4. [ ] Each call site evaluated for post-engineering validation
5. [ ] Violations fixed (if any)
6. [ ] sandwich_audit_table.md written with all rows
7. [ ] evidence.md summarizes findings
8. [ ] Docs/Specs updated if any structural changes made
9. [ ] Tests pass after any fixes

## Deliverables

1. `reports/TC-3875/sandwich_audit_table.md`
2. `reports/TC-3875/evidence.md`
3. Code fixes (if violations found)

## Acceptance checks

1. [ ] Audit table covers all LLM call sites (no gaps)
2. [ ] All violations fixed or documented with justification
3. [ ] All 3118+ tests pass

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```
