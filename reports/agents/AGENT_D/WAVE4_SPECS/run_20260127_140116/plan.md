# AGENT_D Wave 4 Execution Plan

**Mission**: Address 57 gaps (19 BLOCKER + 38 MAJOR) in spec pack for production readiness

**Start Time**: 2026-01-27 14:01:16

---

## Task Breakdown

### Phase 1: BLOCKER Gaps (19) - P0
Priority: These MUST be addressed before implementation can proceed.

**Group A: Core Algorithms (8 gaps)**
1. S-GAP-008-001: Patch engine conflict resolution algorithm (specs/08_patch_engine.md)
2. S-GAP-008-002: Patch engine idempotency mechanism (specs/08_patch_engine.md)
3. S-GAP-011-001: State replay algorithm (specs/11_state_and_events.md)
4. S-GAP-004-001: Claims compilation algorithm (specs/04_claims_compiler_truth_lock.md)
5. S-GAP-022-001: Navigation update algorithm (specs/22_navigation_and_existing_content_update.md)
6. S-GAP-033-001: URL resolution algorithm (specs/33_public_url_mapping.md)
7. S-GAP-002-001: Adapter fallback when no match (specs/02_repo_ingestion.md)
8. S-GAP-002-002: Phantom path detection algorithm (specs/02_repo_ingestion.md)

**Group B: Failure Modes & Recovery (5 gaps)**
9. S-GAP-006-001: Planning failure modes (specs/06_page_planning.md)
10. S-GAP-028-001: Handoff failure recovery (specs/28_coordination_and_handoffs.md)
11. S-GAP-016-001: Telemetry failure handling (specs/16_local_telemetry_api.md)
12. S-GAP-019-001: Tool version lock enforcement (specs/19_toolchain_and_ci.md)
13. S-GAP-SM-001: State transition validation (specs/state-management.md)

**Group C: MCP & Integration (4 gaps)**
14. S-GAP-014-001: MCP endpoint specifications (specs/14_mcp_endpoints.md)
15. S-GAP-014-002: MCP auth specification (covered in 014-001)
16. S-GAP-024-001: MCP tool error handling (specs/24_mcp_tool_schemas.md)
17. S-GAP-024-002: Schema validation failure handling (covered in 024-001)

**Group D: Interfaces & Contracts (2 gaps)**
18. S-GAP-026-001: Adapter interface undefined (specs/26_repo_adapters_and_variability.md)
19. S-GAP-013-001: Pilot execution contract (specs/13_pilots.md)

### Phase 2: MAJOR Gaps (38) - P1
Priority: Address after BLOCKERS to improve spec quality.

**Category 1: Vague Language (7 gaps)**
- Replace "should/may" with SHALL/MUST in binding specs
- Files: 05_example_curation.md, 06_page_planning.md, others

**Category 2: Missing Edge Cases (12 gaps)**
- Add edge case handling to worker specs (W1-W9)
- Add fallback behavior specifications
- Files: 02_repo_ingestion.md, 04_claims_compiler_truth_lock.md, 05_example_curation.md, 06_page_planning.md

**Category 3: Incomplete Failure Modes (10 gaps)**
- Add failure mode specifications where missing
- Add error codes and recovery strategies
- Files: Multiple worker specs

**Category 4: Missing Best Practices (9 gaps)**
- Add auth best practices sections
- Add toolchain verification guides
- Add adapter development guides
- Files: Multiple specs

---

## Execution Order (by file to minimize context switching)

### Batch 1: Core Ingestion & Adapters
- specs/02_repo_ingestion.md (S-GAP-002-001, S-GAP-002-002, S-GAP-002-003, S-GAP-002-004)
- specs/26_repo_adapters_and_variability.md (S-GAP-026-001)

### Batch 2: Claims & Facts
- specs/04_claims_compiler_truth_lock.md (S-GAP-004-001, S-GAP-004-002, S-GAP-004-003)
- specs/03_product_facts_and_evidence.md (S-GAP-003-001)

### Batch 3: Planning & Drafting
- specs/05_example_curation.md (S-GAP-005-001, S-GAP-005-002)
- specs/06_page_planning.md (S-GAP-006-001, S-GAP-006-002, S-GAP-006-003)

### Batch 4: Patch Engine
- specs/08_patch_engine.md (S-GAP-008-001, S-GAP-008-002)

### Batch 5: State & Events
- specs/11_state_and_events.md (S-GAP-011-001)
- specs/state-management.md (S-GAP-SM-001)

### Batch 6: MCP & APIs
- specs/14_mcp_endpoints.md (S-GAP-014-001, S-GAP-014-002)
- specs/24_mcp_tool_schemas.md (S-GAP-024-001, S-GAP-024-002)
- specs/16_local_telemetry_api.md (S-GAP-016-001)

### Batch 7: Validation & Toolchain
- specs/19_toolchain_and_ci.md (S-GAP-019-001)
- specs/13_pilots.md (S-GAP-013-001)

### Batch 8: Navigation & URLs
- specs/22_navigation_and_existing_content_update.md (S-GAP-022-001)
- specs/33_public_url_mapping.md (S-GAP-033-001)

### Batch 9: Coordination
- specs/28_coordination_and_handoffs.md (S-GAP-028-001)

---

## Risk Assessment

### High Risk Areas
1. **Breaking existing specs**: Adding new sections might conflict with existing content
   - Mitigation: Always read files first, use Edit tool (not Write), preserve structure

2. **Introducing contradictions**: New algorithms might contradict existing specs
   - Mitigation: Cross-reference related specs, maintain consistent terminology

3. **Placeholders**: Adding incomplete content violates Gate M
   - Mitigation: Every algorithm must be complete with all steps, no TBD/TODO

4. **Validation failures**: Schema changes might break validation
   - Mitigation: Run validate_spec_pack.py after each batch

### Medium Risk Areas
1. **Style inconsistency**: Different writing styles across batches
   - Mitigation: Review existing spec style before editing each file

2. **Over-specification**: Adding too much detail reduces flexibility
   - Mitigation: Focus on binding requirements, allow implementation choices where appropriate

### Low Risk Areas
1. **File operations**: Well-defined protocol (read → edit → validate)
2. **Evidence collection**: Clear commands and outputs to capture
3. **Self-review**: Structured 12-dimension template to follow

---

## Rollback Strategy

**If validation fails or contradictions introduced:**

1. **Per-file rollback**: Git restore individual files
   ```bash
   git restore specs/{filename}.md
   ```

2. **Batch rollback**: Git reset to start of batch
   ```bash
   git diff --stat  # Review changes
   git restore specs/*.md  # Restore all specs
   ```

3. **Full rollback**: Start from clean state
   ```bash
   cd C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
   git status
   git restore specs/
   ```

**Recovery process:**
1. Document what went wrong in `rollback_reason.md`
2. Restore files to clean state
3. Re-read specs to understand root cause
4. Apply smaller, more targeted edits
5. Validate frequently (after each file, not each batch)

---

## Validation Checkpoints

**After each file edit:**
```bash
python scripts/validate_spec_pack.py
```

**After each batch (every 3-5 files):**
```bash
# Full validation
python scripts/validate_spec_pack.py

# Check for vague language
grep -r "should\|may" specs/*.md | grep -v "MUST\|SHALL"

# Check for placeholders
grep -r "TBD\|TODO\|FIXME\|placeholder" specs/*.md
```

**Final validation (end of Phase 1 and Phase 2):**
```bash
# Schema validation
python scripts/validate_spec_pack.py

# Vague language audit
grep -r "should\|may" specs/*.md | grep -v "MUST\|SHALL" > artifacts/vague_language_audit.txt

# Placeholder audit
grep -r "TBD\|TODO\|FIXME\|placeholder" specs/*.md > artifacts/placeholder_audit.txt

# Gap verification (ensure all 57 gaps addressed)
# Manual review of GAPS.md against changes.md
```

---

## Success Criteria

**Phase 1 Complete (BLOCKERS):**
- [ ] All 19 BLOCKER gaps addressed
- [ ] All algorithms have clear step-by-step descriptions OR pseudocode
- [ ] No placeholders (TBD/TODO) in BLOCKER sections
- [ ] validate_spec_pack.py exits 0
- [ ] All BLOCKER gap sections findable via grep

**Phase 2 Complete (MAJOR):**
- [ ] All 38 MAJOR gaps addressed
- [ ] Vague language replaced with SHALL/MUST where binding
- [ ] Edge cases documented for all worker specs
- [ ] Failure modes complete for all critical paths
- [ ] validate_spec_pack.py exits 0
- [ ] No placeholders remain in spec pack

**Overall Complete:**
- [ ] All 57 gaps (19 BLOCKER + 38 MAJOR) addressed
- [ ] All spec files validate against schemas
- [ ] changes.md documents all modifications
- [ ] evidence.md shows all validation results
- [ ] self_review.md scores ≥4/5 on all 12 dimensions
- [ ] PASS criteria met

---

## Time Estimates

**Phase 1 (BLOCKER gaps)**: 4-6 hours
- Group A (algorithms): 2-3 hours (complex algorithms, pseudocode)
- Group B (failure modes): 1-2 hours (error codes, recovery strategies)
- Group C (MCP): 0.5-1 hour (endpoint specs, error handling)
- Group D (interfaces): 0.5-1 hour (adapter interface, pilot contract)

**Phase 2 (MAJOR gaps)**: 3-5 hours
- Category 1 (vague language): 1 hour (find & replace, context check)
- Category 2 (edge cases): 1-2 hours (add edge case sections)
- Category 3 (failure modes): 1-1.5 hours (add error codes)
- Category 4 (best practices): 0.5-1 hour (add guidance sections)

**Documentation & Review**: 1-2 hours
- changes.md: 30 min
- evidence.md: 30 min
- self_review.md: 30-60 min

**Total Estimated Time**: 8-13 hours (2-3 work sessions)

---

## Notes

- This is the critical pre-implementation hardening wave
- Quality over speed - take time to write clear, unambiguous specs
- Use examples and pseudocode liberally for complex algorithms
- Maintain consistency with existing spec tone and style
- Evidence everything - every command, every validation, every grep result

**Ready to execute.** Starting with Batch 1 (Core Ingestion & Adapters).
