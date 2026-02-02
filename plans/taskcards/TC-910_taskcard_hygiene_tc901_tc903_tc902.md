---
id: "TC-910"
title: "Taskcard Hygiene: Fix TC-901, TC-902, TC-903"
status: In-Progress
owner: agent-1
updated: "2026-02-01"
depends_on:
  - TC-901
  - TC-902
  - TC-903
allowed_paths:
  - plans/taskcards/TC-910_taskcard_hygiene_tc901_tc903_tc902.md
  - plans/taskcards/TC-901_ruleset_max_pages_and_section_style.md
  - plans/taskcards/TC-902_w4_template_enumeration_with_quotas.md
  - plans/taskcards/TC-903_vfv_harness_strict_2run_goldenize.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - reports/agents/**/TC-910/**
evidence_required:
  - reports/agents/agent-1/TC-910/report.md
  - reports/agents/agent-1/TC-910/self_review.md
  - runs/agent1_hygiene_*/tc910_hygiene_evidence.zip
spec_ref: d1d440f4b809781c9bf78516deac8168c54f22a6
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-910 — Taskcard Hygiene: Fix TC-901, TC-902, TC-903

## Objective

Fix all Gate A2/B/P failures in taskcards TC-901, TC-902, and TC-903 to ensure compliance with taskcard contract requirements. This includes correcting frontmatter formatting, adding missing required sections, fixing spec references to existing files, and ensuring all YAML is valid and complete.

## Scope

### In scope

1. **TC-901 fixes**:
   - Fix status: "InProgress" → "In-Progress"
   - Fix spec_ref: "main" → d1d440f4b809781c9bf78516deac8168c54f22a6
   - Ensure all required frontmatter keys exist

2. **TC-902 fixes** (currently has NO YAML frontmatter):
   - Add complete YAML frontmatter with all required keys
   - Add required H1 heading matching taskcard pattern
   - Add all required sections per taskcard contract
   - Fix spec references to point to existing files only
   - Ensure allowed_paths matches frontmatter

3. **TC-903 fixes**:
   - Add missing frontmatter key: id: 903
   - Fix evidence_required[3] if it's a dict (convert to string)
   - Fix body ## Allowed paths section to match frontmatter
   - Add missing sections: ## E2E verification, ## Integration boundary proven (if not present)
   - Fix broken spec references (replace with existing files)

4. **INDEX.md update**:
   - Add TC-910 to index under appropriate section

### Out of scope

- Implementation of features described in taskcards
- Running pytest tests (Agent 2 responsibility)
- Changing allowed_paths beyond what's required for compliance
- Modifying actual implementation code

## Required spec references

- plans/taskcards/00_TASKCARD_CONTRACT.md (taskcard requirements)
- specs/06_page_planning.md (referenced by TC-901)
- specs/07_section_templates.md (referenced by TC-901)
- specs/10_determinism_and_caching.md (referenced by TC-903)
- specs/13_pilots.md (referenced by TC-903)
- specs/20_rulesets_and_templates_registry.md (referenced by TC-901, TC-902)
- specs/34_strict_compliance_guarantees.md (referenced by TC-903)

## Inputs

- plans/taskcards/TC-901_ruleset_max_pages_and_section_style.md (current state)
- plans/taskcards/TC-902_w4_template_enumeration_with_quotas.md (current state)
- plans/taskcards/TC-903_vfv_harness_strict_2run_goldenize.md (current state)
- plans/taskcards/INDEX.md (current state)
- tools/validate_swarm_ready.py (validation script)

## Outputs

- Fixed taskcards with compliant frontmatter and structure
- Updated INDEX.md with TC-910 entry
- Evidence bundle: runs/agent1_hygiene_<timestamp>/tc910_hygiene_evidence.zip
- validate_swarm_ready.py passes with Gates A2/B/P GREEN

## Allowed paths

- plans/taskcards/TC-910_taskcard_hygiene_tc901_tc903_tc902.md
- plans/taskcards/TC-901_ruleset_max_pages_and_section_style.md
- plans/taskcards/TC-902_w4_template_enumeration_with_quotas.md
- plans/taskcards/TC-903_vfv_harness_strict_2run_goldenize.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- reports/agents/**/TC-910/**

### Allowed paths rationale

This task fixes taskcard metadata and structure only, requiring edits to the taskcard files themselves, the INDEX, and evidence reports. No implementation code changes are needed.

## Implementation steps

1. Fix TC-901:
   - Change status from "InProgress" to "In-Progress"
   - Change spec_ref from "main" to "d1d440f4b809781c9bf78516deac8168c54f22a6"

2. Fix TC-902:
   - Add complete YAML frontmatter with all required keys
   - Replace H1 with: # Taskcard TC-902: W4 Template Enumeration with Quotas
   - Add all required sections:
     - ## Objective
     - ## Scope
     - ## Inputs
     - ## Outputs
     - ## Allowed paths
     - ## Required spec references (verify paths exist)
     - ## Implementation steps
     - ## Deliverables
     - ## Acceptance checks
     - ## Self-review
   - Verify all spec references point to existing files

3. Fix TC-903:
   - Add id: 903 to frontmatter
   - Fix evidence_required[3] if it's a dict (make it string)
   - Fix spec references:
     - specs/30_determinism_harness.md → specs/10_determinism_and_caching.md
     - specs/31_pilots_and_regression.md → specs/13_pilots.md
   - Verify body ## Allowed paths matches frontmatter

4. Update INDEX.md:
   - Add TC-910 under "## Additional critical hardening" section

5. Run validation:
   - Execute tools/validate_swarm_ready.py
   - Verify Gates A2/B/P PASS

6. Create evidence bundle:
   - Create runs/agent1_hygiene_<timestamp>/ directory
   - Copy logs, diffs, updated taskcards
   - Create ZIP: tc910_hygiene_evidence.zip

## Test plan

- Validation: Run validate_swarm_ready.py and verify all gates pass
- YAML parsing: Verify all frontmatter parses as valid YAML
- Spec references: Verify all referenced spec files exist
- Frontmatter completeness: Verify all required keys present

## E2E verification

**Concrete command(s) to run:**
```bash
# Activate .venv
.venv/Scripts/activate

# Validate swarm readiness
python tools/validate_swarm_ready.py

# Expected: Gates A2, B, P all PASS
```

**Expected artifacts:**
- Fixed taskcards in plans/taskcards/
- Updated INDEX.md
- Evidence bundle ZIP

**Success criteria:**
- [ ] TC-901 frontmatter has status: "In-Progress" and spec_ref: d1d440f4b809781c9bf78516deac8168c54f22a6
- [ ] TC-902 has complete YAML frontmatter with all required keys
- [ ] TC-902 has all required sections
- [ ] TC-903 has id: 903 in frontmatter
- [ ] TC-903 evidence_required is all strings (no dicts)
- [ ] TC-903 spec references point to existing files only
- [ ] INDEX.md includes TC-910
- [ ] validate_swarm_ready.py Gates A2/B/P all PASS
- [ ] Evidence bundle created with absolute path

## Integration boundary proven

What upstream/downstream wiring was validated:
- Upstream: TC-901, TC-902, TC-903 (taskcard definitions)
- Downstream: validate_swarm_ready.py (validation harness)
- Contracts: YAML frontmatter structure, taskcard contract compliance

## Failure modes

1. **Failure**: YAML frontmatter parsing fails
   - **Detection**: validate_swarm_ready.py reports YAML errors
   - **Fix**: Verify YAML syntax, proper indentation, no tabs
   - **Spec/Gate**: Gate A2 (YAML parsing)

2. **Failure**: Missing required frontmatter keys
   - **Detection**: validate_swarm_ready.py reports missing keys
   - **Fix**: Add all required keys per taskcard contract
   - **Spec/Gate**: Gate B (frontmatter completeness)

3. **Failure**: Spec references point to non-existent files
   - **Detection**: Manual verification or file read errors
   - **Fix**: Replace with existing spec files
   - **Spec/Gate**: Gate P (spec reference validity)

## Task-specific review checklist

Beyond the standard acceptance checks, verify:
- [ ] All frontmatter parses as valid YAML
- [ ] No placeholder values (PIN_ME, TODO, FIXME) in frontmatter
- [ ] All spec references verified to exist
- [ ] Status values use "In-Progress" not "InProgress"
- [ ] spec_ref uses commit SHA not branch name
- [ ] evidence_required contains only strings, no dicts

## Deliverables

- Code:
  - plans/taskcards/TC-901_ruleset_max_pages_and_section_style.md (fixed)
  - plans/taskcards/TC-902_w4_template_enumeration_with_quotas.md (fixed)
  - plans/taskcards/TC-903_vfv_harness_strict_2run_goldenize.md (fixed)
  - plans/taskcards/INDEX.md (updated)
- Reports (required):
  - reports/agents/agent-1/TC-910/report.md
  - reports/agents/agent-1/TC-910/self_review.md
  - runs/agent1_hygiene_<timestamp>/tc910_hygiene_evidence.zip

## Acceptance checks

- [ ] TC-910 taskcard created with complete frontmatter
- [ ] TC-901 status fixed to "In-Progress"
- [ ] TC-901 spec_ref fixed to d1d440f4b809781c9bf78516deac8168c54f22a6
- [ ] TC-902 has complete YAML frontmatter
- [ ] TC-902 has all required sections
- [ ] TC-902 spec references verified
- [ ] TC-903 has id: 903
- [ ] TC-903 evidence_required fixed (all strings)
- [ ] TC-903 spec references fixed
- [ ] INDEX.md updated with TC-910
- [ ] validate_swarm_ready.py passes
- [ ] Evidence bundle created
- [ ] No write fence violations

## Self-review

Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
