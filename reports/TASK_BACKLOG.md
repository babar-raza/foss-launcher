# Task Backlog - SOP Violation Prevention
**Generated**: 2026-01-30 23:05 PKT
**Primary Plan**: C:\Users\prora\.claude\plans\toasty-jumping-trinket.md

## Workstream 1: Validation Gate (Agent B - Implementation)

**ID**: WS1-GATE-B+1
**Scope**: Create new validation gate to block unauthorized taskcard work
**Owner**: Agent B (Implementation)
**Priority**: HIGH
**Effort**: Medium (1-2 days)

**Impacted Paths**:
- tools/validate_taskcard_readiness.py (NEW)
- tests/unit/tools/test_validate_taskcard_readiness.py (NEW)
- tools/validate_swarm_ready.py (MODIFY - add Gate B+1)

**Acceptance Criteria**:
- [ ] Gate B+1 fails if referenced taskcard doesn't exist
- [ ] Gate B+1 fails if taskcard status is "Draft" or "Blocked"
- [ ] Gate B+1 fails if dependency chain is broken
- [ ] Gate B+1 passes for all existing pilots with Done taskcards
- [ ] All tests pass (100% coverage)

**Tests Required**:
- test_taskcard_exists_pass()
- test_taskcard_missing_fail()
- test_dependency_chain_satisfied()
- test_dependency_missing_fail()
- test_circular_dependency_fail()
- test_draft_status_blocked()

**Docs Required**:
- Update tools/README.md with Gate B+1 documentation
- Add validation logic documentation

**Risk**: Medium (could break existing workflows if not backward compatible)

---

## Workstream 2: Schema Update (Agent B - Implementation)

**ID**: WS2-SCHEMA-UPDATE
**Scope**: Add optional taskcard_id field to run_config schema
**Owner**: Agent B (Implementation)
**Priority**: HIGH
**Effort**: Small (<1 day)

**Impacted Paths**:
- specs/schemas/run_config.schema.json (MODIFY)

**Acceptance Criteria**:
- [ ] Schema validates configs with taskcard_id field
- [ ] Schema validates configs without taskcard_id (backward compatible)
- [ ] Existing pilot configs still validate

**Tests Required**:
- test_run_config_with_taskcard_id()
- test_run_config_without_taskcard_id()
- test_backward_compatibility()

**Docs Required**:
- Update specs/01_system_contract.md with taskcard_id field description

**Risk**: Low (optional field, backward compatible)

---

## Workstream 3: Emergency Procedures (Agent D - Docs)

**ID**: WS3-EMERGENCY-DOCS
**Scope**: Document when/how emergency bypass is acceptable
**Owner**: Agent D (Docs & Specs)
**Priority**: MEDIUM
**Effort**: Medium (2-3 days)

**Impacted Paths**:
- plans/policies/emergency_hotfix_procedure.md (NEW)

**Acceptance Criteria**:
- [ ] Policy clearly defines allowed emergency scenarios
- [ ] Step-by-step workflow documented
- [ ] Retroactive formalization timeline (24/48h)
- [ ] Examples of valid vs invalid emergencies

**Docs Required**:
- Complete policy document (~400 lines)
- Examples and decision tree
- Integration with existing emergency mode (allow_manual_edits)

**Risk**: Low (documentation only)

---

## Workstream 4: Approval Tracking (Agent B - Implementation + Agent D - Docs)

**ID**: WS4-APPROVAL-TRACKING
**Scope**: Add orchestrator approval tracking to taskcards
**Owner**: Agent B (Implementation) + Agent D (Docs)
**Priority**: MEDIUM
**Effort**: Medium (2-3 days)

**Impacted Paths**:
- plans/taskcards/00_TASKCARD_CONTRACT.md (MODIFY - add approval section)
- plans/_templates/taskcard.md (MODIFY - add approval fields)
- tools/validate_taskcards.py (MODIFY - validate approval)

**Acceptance Criteria**:
- [ ] All new taskcards require approval fields
- [ ] Validation enforces approval for Ready/Done status
- [ ] Emergency override tracked with justification
- [ ] STATUS_BOARD displays approval status

**Tests Required**:
- test_approval_required_for_ready_status()
- test_emergency_override_requires_notes()
- test_grandfathered_old_taskcards()

**Docs Required**:
- Update taskcard contract with approval requirements
- Document approval workflow

**Risk**: Medium (requires updating existing taskcards or grandfathering)

---

## Workstream 5: Evidence Audit (Agent C - Tests & Verification)

**ID**: WS5-EVIDENCE-AUDIT
**Scope**: Create script to audit taskcard evidence completeness
**Owner**: Agent C (Tests & Verification)
**Priority**: MEDIUM
**Effort**: Small-Medium (1-2 days)

**Impacted Paths**:
- tools/audit_taskcard_evidence.py (NEW)
- tests/unit/tools/test_audit_taskcard_evidence.py (NEW)

**Acceptance Criteria**:
- [ ] Script detects missing evidence for Done taskcards
- [ ] Script detects orphaned evidence directories
- [ ] Clear report with actionable findings
- [ ] Exit code 0 if complete, 1 otherwise

**Tests Required**:
- test_detect_missing_evidence()
- test_detect_orphaned_evidence()
- test_complete_evidence_passes()

**Docs Required**:
- Add to tools/README.md
- Document audit output format

**Risk**: Low (audit tool, no enforcement)

---

## Parallel Execution Plan

**Phase 1 (HIGH Priority - Week 1)**:
- WS1 (Agent B) + WS2 (Agent B) + WS5 (Agent C) → Execute in parallel
- Expected completion: 3 days
- Blocking: None (independent workstreams)

**Phase 2 (MEDIUM Priority - Week 2)**:
- WS3 (Agent D) + WS4 (Agent B + Agent D) → Execute in parallel
- Expected completion: 3 days
- Blocking: None (can start after Phase 1 or in parallel)

**Total Estimated Time**: 1-2 weeks for Phases 1-2
**Long-term (Phase 3)**: Deferred pending Phase 1-2 completion

---

## Dependencies

WS1 → WS2: Schema update should align with Gate B+1 validation logic
WS4 → WS3: Approval tracking references emergency procedures
WS5: Independent (can run anytime)

---

## Open Questions (User Input Required)

1. **Priority**: Implement all phases, or focus on Phase 1 only?
2. **Emergency threshold**: What qualifies as legitimate emergency?
3. **Approval authority**: Who can approve taskcards?
4. **Backward compatibility**: Grandfather existing Done taskcards?
5. **Long-term architecture**: Is task queue worth the effort?

---

## Status

**Current State**: Backlog created, awaiting agent spawn
**Next Step**: Spawn agents for WS1, WS2, WS5 (Phase 1 - HIGH priority)
