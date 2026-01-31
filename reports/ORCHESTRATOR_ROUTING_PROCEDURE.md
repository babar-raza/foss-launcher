# Orchestrator Routing Procedure
**Purpose**: Define how to route completed agent work (PASS/REWORK)

---

## Step 6: Orchestrator Routing (When Agents Complete)

### 6.1. Collect Self-Reviews

For each completed agent:
1. Read `reports/agents/<agent>/<workstream>/self_review.md`
2. Extract scores for 12 dimensions:
   - Coverage, Correctness, Evidence, Test Quality
   - Maintainability, Safety, Security, Reliability
   - Observability, Performance, Compatibility, Docs/Specs Fidelity
3. Check Known Gaps section (MUST be empty to pass)

### 6.2. Routing Decision Matrix

**PASS Criteria** (all must be true):
- ✅ ALL 12 dimensions scored ≥4/5
- ✅ Known Gaps section is EMPTY
- ✅ All acceptance criteria checked
- ✅ All tests passing (in evidence.md)
- ✅ Evidence links valid (can verify claims)

**REWORK Triggers** (any triggers rework):
- ❌ ANY dimension scored <4/5
- ❌ Known Gaps section has items
- ❌ Acceptance criteria unchecked
- ❌ Tests failing
- ❌ Missing evidence links

### 6.3. PASS Route Actions

If workstream PASSES:
1. ✅ Mark workstream COMPLETE in STATUS.md
2. ✅ Copy deliverables to final locations
3. ✅ Update CHANGELOG.md with changes
4. ✅ Run integration tests if required
5. ✅ Prepare for merge/commit

### 6.4. REWORK Route Actions

If workstream needs REWORK:
1. ❌ Create `reports/HARDENING_TICKETS/<workstream>.md`:
   ```markdown
   # Hardening Ticket: <workstream>
   **Agent**: <agent_name>
   **Attempt**: <N>
   **Trigger**: <dimension(s) <4 OR Known Gaps OR Failed tests>

   ## Failing Dimensions
   - Dimension: <score>/5
   - Why: <excerpt from self-review>

   ## Missing Evidence
   - <list from self-review>

   ## Concrete Actions Required
   1. <specific fix>
   2. <specific test>
   3. <specific evidence>

   ## Owner
   Route back to: <same agent OR escalate if stuck>
   ```

2. ❌ Route ticket back to agent with hardening instructions
3. ❌ If stuck twice: Escalate to orchestrator to re-scope

### 6.5. Integration Check (After All PASS)

When ALL workstreams in phase PASS:
1. Run integration tests:
   ```bash
   # Verify Gate B+1 works
   python tools/validate_swarm_ready.py

   # Verify schema validation
   python -c "import jsonschema, yaml, json; ..."

   # Verify audit script
   python tools/audit_taskcard_evidence.py
   ```

2. Check for conflicts between workstreams
3. Update STATUS.md → Phase 1 COMPLETE
4. Prepare final deliverables

---

## Self-Review Rubric (Reference)

**5**: Excellent + concrete evidence + no risks
**4**: Good + concrete evidence + minor issues documented
**3**: Partial/weak evidence/missing edge cases
**2**: Major gaps/test failures
**1**: Broken/unsafe

**Pass Threshold**: ≥4/5 on ALL dimensions

---

## Escalation Criteria

**When to escalate to orchestrator**:
- Agent stuck on rework twice (same issues)
- Scope too large (should split into smaller PRs)
- Conflicting requirements discovered
- Blocking dependencies on other work

**Escalation Actions**:
- Re-scope into smaller units
- Clarify requirements
- Adjust acceptance criteria
- Assign to different agent if needed

---

## Final Merge Checklist

Before declaring Phase 1 COMPLETE:
- [ ] All 3 workstreams (WS1, WS2, WS5) scored ≥4/5
- [ ] All tests green
- [ ] All evidence validated
- [ ] CHANGELOG.md updated
- [ ] Integration tests pass
- [ ] No merge conflicts
- [ ] Ready for commit
