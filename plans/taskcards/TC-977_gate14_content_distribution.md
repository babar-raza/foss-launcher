---
id: TC-977
title: "Fix Gate 14 (Content Distribution) - Forbidden Topic and Claim Quota Violations"
status: Draft
priority: High
owner: "Agent-B (Implementation)"
updated: "2026-02-05"
tags: ["gate-14", "content-distribution", "claims", "forbidden-topics"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-977_gate14_content_distribution.md
  - src/launch/workers/w4_ia_planner/worker.py
  - src/launch/workers/w5_section_writer/worker.py
evidence_required:
  - runs/vfv_tc971-975_iter10/vfv_3d_report.json
  - reports/agents/agent-b/TC-977/evidence.md
spec_ref: "3e91498d6b9dbda85744df6bf8d5f3774ca39c60"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-977 — Fix Gate 14 (Content Distribution)

## Objective
Fix Gate 14 content distribution violations by (1) resolving forbidden topic error in FAQ page and (2) adding claim markers to fallback-generated content to meet minimum claim quotas.

## Problem Statement
Gate 14 fails with two types of errors:
1. FAQ page contains "installation" but troubleshooting role forbids this topic
2. Fallback-generated pages have 0 claims, violating minimum claim quota requirements

## Required spec references
- specs/08_content_distribution_strategy.md (Content distribution rules, page roles, forbidden topics)
- specs/09_validation_gates.md (Gate 14 validation requirements)
- C:\Users\prora\.claude\plans\magical-prancing-fountain.md (Investigation results)

## Scope

### In scope
- Fix forbidden topic violation: Change FAQ page role from "troubleshooting" to role that allows installation
- Fix claim quota underflow: Add claim markers to _generate_fallback_content()
- Ensure Gate 14 passes or shows only acceptable warnings
- Verify generated content includes proper claim markers

### Out of scope
- Modifying content distribution strategy rules
- Changing other page roles
- Implementing new content generators
- Modifying Gate 14 validation logic

## Inputs
- W4 page role assignment: src/launch/workers/w4_ia_planner/worker.py:88
- W5 fallback generator: src/launch/workers/w5_section_writer/worker.py:873-949
- Gate 14 validation: src/launch/workers/w7_validator/worker.py:632-854
- Content distribution spec: specs/08_content_distribution_strategy.md

## Outputs
- Modified assign_page_role() to return different role for FAQ pages
- Modified _generate_fallback_content() to include claim markers
- Gate 14 validation passes or shows only warnings
- Generated markdown contains claim markers

## Allowed paths
- plans/taskcards/TC-977_gate14_content_distribution.md
- src/launch/workers/w4_ia_planner/worker.py
- src/launch/workers/w5_section_writer/worker.py

### Allowed paths rationale
TC-977 modifies W4 page role assignment and W5 fallback content generation to comply with Gate 14 content distribution validation rules.

## Implementation steps

### Step 1: Fix forbidden topic violation (W4)
Modify assign_page_role() to return non-troubleshooting role for FAQ pages.

### Step 2: Fix claim quota underflow (W5)
Modify _generate_fallback_content() to add claim markers from required_claim_ids parameter.

### Step 3: Update function call site
Pass required_claim_ids to _generate_fallback_content() function.

### Step 4: Test with pilot run
Run pilot iteration 10 to verify fixes.

### Step 5: Verify claim markers in generated content
Check generated markdown contains claim markers.

### Step 6: Confirm Gate 14 passes
Verify validation report shows gate_14_content_distribution passes or has only warnings.

## Failure modes

### Failure 1: FAQ still contains forbidden topics
**Symptom**: Gate 14 error "contains forbidden topic: installation"
**Mitigation**: Change FAQ page role assignment in W4
**Rollback**: Revert assign_page_role() change

### Failure 2: Claim markers not added correctly
**Symptom**: Gate 14 warning "0 claims, below minimum"
**Mitigation**: Verify _generate_fallback_content receives required_claim_ids
**Rollback**: Revert _generate_fallback_content() change

### Failure 3: Claim markers break content formatting
**Symptom**: Markdown rendering issues
**Mitigation**: Ensure claim markers use correct format per Gate 2 specification
**Rollback**: Revert to simple text without markers

## Task-specific review checklist

- [ ] assign_page_role() modified for FAQ
- [ ] _generate_fallback_content() adds claim markers
- [ ] Function call site updated with required_claim_ids
- [ ] Generated markdown contains claim markers
- [ ] FAQ page no longer has forbidden topic violations
- [ ] Gate 14 passes or shows only acceptable warnings
- [ ] No regression in other gates
- [ ] Evidence collected

## Deliverables

1. Modified W4 assign_page_role() function
2. Modified W5 _generate_fallback_content() function
3. Gate 14 passing validation report
4. Sample generated content showing claim markers
5. Self-review.md with scores >= 4/5

## Acceptance checks

**MUST ALL PASS**:
- [ ] FAQ page role changed
- [ ] Generated markdown includes claim markers
- [ ] Gate 14 validation passes or warnings only
- [ ] No forbidden topic violations
- [ ] Evidence files created in reports/agents/agent-b/TC-977/

## Self-review

**Scores** (filled after execution):
- Coverage: ___/5
- Correctness: ___/5
- Evidence: ___/5
- Test Quality: ___/5
- Maintainability: ___/5
- Safety: ___/5
- Security: ___/5
- Reliability: ___/5
- Observability: ___/5
- Performance: ___/5
- Compatibility: ___/5
- Docs/Specs Fidelity: ___/5

**Known gaps**: (Must be empty to pass)

## E2E verification

Run full pilot with fixes, verify Gate 14 passes, check claim markers in generated content, verify FAQ page role.

## Integration boundary proven

**Upstream dependencies**: W4 IAPlanner (page role assignment)
**Downstream consumers**: W5 SectionWriter, W7 Validator (Gate 14)

**Evidence of integration**: Validation report showing gate_14_content_distribution passes
