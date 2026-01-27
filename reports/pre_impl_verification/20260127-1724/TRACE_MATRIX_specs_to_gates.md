# Specs-to-Gates Trace Matrix

**Run ID:** `20260127-1724`
**Source:** AGENT_G (Gates/Validators Auditor)
**Detailed Trace:** `agents/AGENT_G/TRACE.md`

---

## Summary

This matrix maps validation gates to their authoritative specifications and implementation status.

**Gate Statistics:**
- **Total Gates Defined:** 36 (15 runtime + 21 preflight)
- **Runtime Gates Implemented:** 2/15 (13%)
- **Preflight Gates Implemented:** 19/21 (90%)
- **Overall Implementation:** 21/36 (58%)

---

## Runtime Gates (specs/09_validation_gates.md)

These gates execute during runtime validation via `launch_validate` command.

| Gate ID | Gate Name | Spec | Enforcement | Status | Implementation Path |
|---------|-----------|------|-------------|--------|---------------------|
| Gate 0 | Run Layout | specs/09:116-134 | Strong | ✅ Implemented | src/launch/validators/cli.py:116-134 |
| Gate 1 | Schema Validation | specs/09:21-50 | Strong | ⚠ Partial | cli.py:177-211 (artifacts only, not frontmatter) |
| Gate 2 | Markdown Lint | specs/09:53-84 | Strong | ❌ Missing | NOT_IMPLEMENTED |
| Gate 3 | Hugo Config | specs/09:86-116 | Strong | ❌ Missing | NOT_IMPLEMENTED |
| Gate 4 | Platform Layout | specs/09:118-154 | Strong | ❌ Missing | NOT_IMPLEMENTED |
| Gate 5 | Hugo Build | specs/09:156-186 | Strong | ❌ Missing | NOT_IMPLEMENTED |
| Gate 6 | Internal Links | specs/09:188-218 | Strong | ❌ Missing | NOT_IMPLEMENTED |
| Gate 7 | External Links | specs/09:220-249 | Profile-dependent | ❌ Missing | NOT_IMPLEMENTED |
| Gate 8 | Snippet Checks | specs/09:251-282 | Strong | ❌ Missing | NOT_IMPLEMENTED |
| Gate 9 | TruthLock | specs/09:284-317 | Strong | ❌ Missing | NOT_IMPLEMENTED |
| Gate 10 | Consistency | specs/09:319-353 | Strong | ❌ Missing | NOT_IMPLEMENTED |
| Gate 11 | Template Token Lint | specs/09:355-383 | Strong | ❌ Missing | NOT_IMPLEMENTED |
| Gate 12 | Universality | specs/09:385-428 | Strong | ❌ Missing | NOT_IMPLEMENTED |
| Gate 13 | Rollback Metadata | specs/09:430-468 | Profile-dependent | ❌ Missing | NOT_IMPLEMENTED |
| Gate T | Test Determinism | specs/09:471-495 | Strong | ❌ Missing | NOT_IMPLEMENTED |

**Runtime Implementation Status:** 2/15 gates (13%)
- **Gap Impact:** 13 BLOCKER gaps (G-GAP-001 through G-GAP-013)
- **Expected State:** Pre-implementation phase (runtime gates pending TC-570 extension)

---

## Preflight Gates (specs/34_strict_compliance_guarantees.md)

These gates execute at preflight via `tools/validate_swarm_ready.py`.

| Gate ID | Gate Name | Spec | Guarantee | Status | Implementation Path |
|---------|-----------|------|-----------|--------|---------------------|
| Gate 0 | .venv Policy | specs/00 | N/A | ✅ Implemented | tools/validate_dotvenv_policy.py |
| Gate A1 | Spec Schemas | Internal | N/A | ✅ Implemented | scripts/validate_spec_pack.py |
| Gate A2 | Plans Integrity | Internal | N/A | ✅ Implemented | scripts/validate_plans.py |
| Gate B | Taskcards | Internal | K (partial) | ✅ Implemented | tools/validate_taskcards.py |
| Gate C | Status Board | Internal | N/A | ✅ Implemented | tools/generate_status_board.py |
| Gate D | Link Integrity | Internal | N/A | ✅ Implemented | tools/check_markdown_links.py |
| Gate E | Allowed Paths Audit | Internal | B (partial) | ✅ Implemented | tools/audit_allowed_paths.py |
| Gate F | Platform Layout | specs/26 | N/A | ✅ Implemented | tools/validate_platform_layout.py |
| Gate G | Pilots Contract | specs/13 | N/A | ✅ Implemented | tools/validate_pilots_contract.py |
| Gate H | MCP Contract | specs/14,24 | N/A | ✅ Implemented | tools/validate_mcp_contract.py |
| Gate I | Phase Reports | Internal | N/A | ✅ Implemented | tools/validate_phase_report_integrity.py |
| Gate J | Pinned Refs | specs/34:40-86 | A | ✅ Implemented | tools/validate_pinned_refs.py |
| Gate K | Supply Chain | specs/34:110-130 | C | ✅ Implemented | tools/validate_supply_chain_pinning.py |
| Gate L | Secrets Hygiene | specs/34:161-187 | E | 🔧 Stub (functional) | tools/validate_secrets_hygiene.py |
| Gate M | No Placeholders | specs/34:161-187 | E | ✅ Implemented | tools/validate_no_placeholders_production.py |
| Gate N | Network Allowlist | specs/34:132-158 | D | ✅ Implemented | tools/validate_network_allowlist.py |
| Gate O | Budget Config | specs/34:190-278 | F, G | ✅ Implemented | tools/validate_budgets_config.py |
| Gate P | Version Locks | specs/34:362-393 | K | ✅ Implemented | tools/validate_taskcard_version_locks.py |
| Gate Q | CI Parity | specs/34:280-303 | H | ✅ Implemented | tools/validate_ci_parity.py |
| Gate R | Untrusted Code | specs/34:333-361 | J | 🔧 Stub (basic) | tools/validate_untrusted_code_policy.py |
| Gate S | Windows Names | Internal | N/A | ✅ Implemented | tools/validate_windows_reserved_names.py |

**Preflight Implementation Status:** 19/21 gates (90%)
- 2 gates are functional stubs (Gates L, R)
- Preflight gates are production-ready

---

## Critical Gate Gaps

### HIGHEST Priority
- **G-GAP-008**: Gate 9 (TruthLock Compilation) — Cannot enforce claim verification

### HIGH Priority
- **G-GAP-002**: Gate 3 (Hugo Config Compatibility)
- **G-GAP-004**: Gate 5 (Hugo Build Validation)
- **G-GAP-005**: Gate 6 (Internal Links Check)
- **G-GAP-009**: Gate 10 (Consistency Checks)
- **G-GAP-010**: Gate 11 (Template Token Lint)

### MEDIUM Priority
- **G-GAP-001**: Gate 2 (Markdown Lint)
- **G-GAP-003**: Gate 4 (Platform-Aware Layout)
- **G-GAP-007**: Gate 8 (Snippet Syntax Validation)
- **G-GAP-011**: Gate 12 (Universality)
- **G-GAP-012**: Gate 13 (Rollback Contract)

### LOW Priority
- **G-GAP-006**: Gate 7 (External Links) — Profile-dependent, skippable
- **G-GAP-013**: Gate T (Test Determinism) — Optional test harness

---

## Gate-to-Guarantee Mapping

| Guarantee | Preflight Gates | Runtime Gates | Status |
|-----------|----------------|---------------|--------|
| A (Pinned Refs) | Gate J | Gate 1 (partial) | ✅ Preflight OK |
| B (Hermetic) | Gate E | Gate 0 | ✅ Preflight OK |
| C (Supply Chain) | Gate K | — | ✅ Preflight OK |
| D (Network) | Gate N | — | ✅ Preflight OK |
| E (Secrets) | Gates L, M | — | 🔧 Stub (functional) |
| F (Budget) | Gate O | — | ✅ Preflight OK |
| G (Change Budget) | Gate O | — | ✅ Preflight OK |
| H (CI Parity) | Gate Q | — | ✅ Preflight OK |
| I (Test Determinism) | Gate T (optional) | Gate T (runtime) | ❌ Runtime pending |
| J (Untrusted Code) | Gate R | — | 🔧 Stub (basic) |
| K (Version Locks) | Gates B, P | — | ✅ Preflight OK |
| L (Rollback) | — | Gate 13 | ❌ Runtime pending |

---

## Schema Compliance

**Validation Gates Enforce:**
- `validation_report.schema.json` (Gate outputs)
- `issue.schema.json` (Gate issue reporting)

**Compliance Status:** ✅ Gates correctly use schema-validated structures

---

## Determinism Analysis

**Implemented Gates:** ✅ All preflight gates are deterministic (pure functions, no timestamps, no random)

**Runtime Gates:** ⚠ Cannot assess (not yet implemented)

**Future Concerns:**
- Gate 7 (External Links): Non-deterministic by nature (mitigated: skippable)
- Gate 5 (Hugo Build): Timestamps in output (mitigated: checks exit code only)

---

## Detailed Trace Reference

For complete gate-to-spec mappings, implementation evidence, and gap analysis, see:

**[agents/AGENT_G/TRACE.md](agents/AGENT_G/TRACE.md)**

---

## Cross-References

- **Gate Gaps:** [agents/AGENT_G/GAPS.md](agents/AGENT_G/GAPS.md) (16 gaps)
- **Meta-Review:** [ORCHESTRATOR_META_REVIEW.md](ORCHESTRATOR_META_REVIEW.md) (Stage 4: AGENT_G)
- **Spec Quality:** [agents/AGENT_S/GAPS.md](agents/AGENT_S/GAPS.md)

---

**Trace Matrix Generated:** 2026-01-27 18:30 UTC
**Verification Status:** ⚠ PARTIAL (13 runtime gates pending implementation)
