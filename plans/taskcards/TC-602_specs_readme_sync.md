---
id: TC-602
title: Specs README Navigation Update
status: Done
owner: docs-agent
updated: "2026-01-24"
depends_on: []
allowed_paths:
  - specs/README.md
  - reports/agents/docs-agent/**
evidence_required:
  - reports/agents/docs-agent/H3_SPECS_README_SYNC/report.md
  - reports/agents/docs-agent/H3_SPECS_README_SYNC/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-602 — Specs README Navigation Update

## Objective

Update `specs/README.md` to include all existing spec files, ensuring complete and accurate navigation for all specification documents (specs 00-34).

## Required spec references
- specs/README.md

## Scope
### In scope
- Add 5 missing specs to specs/README.md navigation tables
- Extract accurate descriptions from spec files
- Maintain existing table structure and formatting
- Validate link integrity via Gate D

### Out of scope
- Modifying existing spec content
- Reordering existing navigation entries
- Creating new specs
- Implementing automated drift detection gate (noted as suggestion only)

## Inputs
- All spec files in specs/ directory (00-34)
- Existing specs/README.md structure

## Outputs
- Updated specs/README.md with complete spec navigation (00-34)
- All markdown links valid (passes Gate D)

## Allowed paths

- specs/README.md
- reports/agents/docs-agent/**

### Allowed paths rationale

This taskcard only modifies the specs README navigation file to sync it with existing spec documents.

## Implementation steps
1. Read first 10-20 lines of each missing spec to extract title/purpose
2. Identify correct section placement based on content
3. Insert missing specs in numerical order within appropriate sections
4. Validate link integrity using Gate D

## Failure modes
1. **Failure**: Schema validation fails for output artifacts
   - **Detection**: `validate_swarm_ready.py` or pytest fails with JSON schema errors
   - **Fix**: Review artifact structure against schema files in `specs/schemas/`; ensure all required fields are present and types match
   - **Spec/Gate**: specs/11_state_and_events.md, specs/09_validation_gates.md (Gate C)

2. **Failure**: Nondeterministic output detected
   - **Detection**: Running task twice produces different artifact bytes or ordering
   - **Fix**: Review specs/10_determinism_and_caching.md; ensure stable JSON serialization, stable sorting of lists, no timestamps/UUIDs in outputs
   - **Spec/Gate**: specs/10_determinism_and_caching.md, tools/validate_swarm_ready.py (Gate H)

3. **Failure**: Write fence violation (modified files outside allowed_paths)
   - **Detection**: `git status` shows changes outside allowed_paths, or Gate E fails
   - **Fix**: Revert unauthorized changes; if shared library modification needed, escalate to owning taskcard
   - **Spec/Gate**: plans/taskcards/00_TASKCARD_CONTRACT.md (Write fence rule), tools/validate_taskcards.py

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code: specs/README.md (updated navigation)
- Reports:
  - reports/agents/docs-agent/H3_SPECS_README_SYNC/report.md
  - reports/agents/docs-agent/H3_SPECS_README_SYNC/self_review.md

## E2E verification
**Concrete command(s) to run:**
```bash
# Validate link integrity
python tools/validate_swarm_ready.py
```

**Expected artifacts:**
- specs/README.md with all specs 00-34 listed

**Success criteria:**
- [ ] Gate D (markdown link integrity) passes
- [ ] All 5 missing specs added to navigation
- [ ] No broken links introduced

## Integration boundary proven
- Upstream: Existing spec files (00-34) provide source content
- Downstream: Gate D validates markdown links in updated README
- Contracts: specs/README.md navigation structure

## Acceptance checks
- [ ] All specs 00-34 listed in README navigation
- [ ] Descriptions match spec content
- [ ] Gate D passes (no broken links)
- [ ] Table formatting consistent
- [ ] Evidence reports created

## Self-review
Agent must complete 12-dimension self-review using reports/templates/self_review_12d.md
