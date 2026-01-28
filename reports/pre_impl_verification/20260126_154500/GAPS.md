# Pre-Implementation Verification - Unified Gaps

**Session ID:** 20260126_154500
**Date:** 2026-01-26
**Status:** 176 gaps identified across 7 agents

---

## Gap Summary

| Severity | Count | Description |
|----------|-------|-------------|
| **BLOCKER** | **30** | Must fix before implementation (stop-the-line) |
| **MAJOR** | **71** | Should fix before implementation (high risk) |
| **MINOR** | **75** | Quality enhancements (can defer) |
| **TOTAL** | **176** | |

---

## Gap Format

`GAP-XXX | AGENT | SEVERITY | Description | Evidence | Proposed Fix`

---

## BLOCKER Gaps (30)

### Priority 1: Links (Highest Impact)

#### GAP-001 | AGENT_L | BLOCKER | 184 broken internal links
**Evidence:** 335 markdown files scanned, 892 internal links analyzed, 184 broken (20.6% failure rate)
- 129 absolute path links (70%): Using `/specs/file.md` instead of relative paths
- 40 directory links (22%): Linking to directories instead of files
- 8 broken anchors (4%): Heading format mismatches
- 4 line number anchors (2%): GitHub-style `#L123` (non-standard)
- 3 missing relative files (2%): Legitimate broken links

**Proposed Fix:**
1. Run automated link fixer: Convert absolute paths to relative paths (129 links)
2. Add file targets to directory links (40 links) - e.g., `/specs/` → `/specs/README.md`
3. Fix broken anchors: Match exact heading formats (8 links)
4. Remove line number anchors or replace with section links (4 links)
5. Fix missing relative files or remove links (3 links)

**Validation:** Run `python temp_link_checker.py` (created by AGENT_L) → expect 0 broken links
**Estimated Fix Time:** 9-15 hours
**Acceptance Criteria:** Link health = 100% (0 broken links)

---

### Priority 2: Validators (Implementation Blocking)

#### GAP-002 | AGENT_G | BLOCKER | Hugo build gate (B) validator missing
**Evidence:** specs/09_validation_gates.md:41-60 requires Hugo build check but no validator found
**Proposed Fix:** Create src/launch/validators/hugo_build.py with entry point, exit 2 on failure, deterministic output
**Acceptance Criteria:** Gate B validator exists, documented, passes determinism test

#### GAP-003 | AGENT_G | BLOCKER | TruthLock gate (C) validator missing
**Evidence:** specs/04_claims_compiler_truth_lock.md:32-51 requires TruthLock enforcement but unclear if implemented
**Proposed Fix:** Verify or create TruthLock validator in src/launch/validators/truth_lock.py
**Acceptance Criteria:** Gate C validator exists, enforces no uncited claims, exits 2 on violation

#### GAP-004 | AGENT_G | BLOCKER | Internal links gate (D) validator missing
**Evidence:** specs/09_validation_gates.md:61-80 requires internal link validation but no validator found
**Proposed Fix:** Create src/launch/validators/internal_links.py (can leverage AGENT_L's temp_link_checker.py)
**Acceptance Criteria:** Gate D validator exists, checks all internal markdown links, exits 2 on broken links

#### GAP-005 | AGENT_G | BLOCKER | Hugo config gate validator missing
**Evidence:** specs/31_hugo_config_awareness.md requires Hugo config validation but no validator found
**Proposed Fix:** Create src/launch/validators/hugo_config.py to validate Hugo config discovery
**Acceptance Criteria:** Validator exists, checks for config.toml/config.yaml, exits 2 on missing

#### GAP-006 | AGENT_G | BLOCKER | Snippets syntax gate validator missing
**Evidence:** specs/05_example_curation.md requires snippet syntax validation but no validator found
**Proposed Fix:** Create src/launch/validators/snippets_syntax.py to validate snippet code blocks
**Acceptance Criteria:** Validator exists, checks snippet syntax per language, exits 2 on invalid syntax

---

### Priority 3: Schemas (Quick Wins)

#### GAP-007 | AGENT_C | BLOCKER | Missing `who_it_is_for` in ProductFacts schema
**Evidence:** specs/03_product_facts_and_evidence.md:78-85 requires `positioning.who_it_is_for` but specs/schemas/product_facts.schema.json:45 doesn't include it
**Proposed Fix:** Edit specs/schemas/product_facts.schema.json, add to `positioning` object: `"who_it_is_for": {"type": "string", "description": "Target audience description"}`
**Acceptance Criteria:** ProductFacts schema includes `who_it_is_for`, validates against spec examples
**Estimated Fix Time:** 5 minutes

---

### Priority 4: Requirements/Exit Codes (Coordination)

#### GAP-008 | AGENT_R | BLOCKER | Validator determinism not specified
**Evidence:** specs/09_validation_gates.md lacks requirement: "Validator outputs shall have stable issue IDs and ordering"
**Proposed Fix:** Add to specs/09_validation_gates.md section "## Determinism Requirements for Validators": Issue IDs MUST be stable (derived from gate_name+location+issue_type), ordering MUST follow severity ranking, timestamps MUST use run start time
**Acceptance Criteria:** Spec explicitly defines validator determinism requirements

#### GAP-009 | AGENT_R | BLOCKER | Exit code contract incomplete
**Evidence:** specs/01_system_contract.md:141-146 defines "recommended" exit codes but not mandatory
**Proposed Fix:** Change "recommended" to "MUST" in specs/01_system_contract.md:141, specify which components must honor (validators, orchestrator, workers)
**Acceptance Criteria:** Exit code contract is binding, components specified

---

### Priority 5: Features (Architecture)

#### GAP-010 | AGENT_F | BLOCKER | Batch execution feature missing
**Evidence:** specs/00_overview.md:13-17 requires "queue many runs" but no feature/taskcard implements this
**Proposed Fix:** Create spec specs/35_batch_execution.md + taskcard TC-610_batch_orchestrator.md + MCP tools for batch submission
**Acceptance Criteria:** Batch execution spec exists, taskcard exists, MCP tools defined

#### GAP-011 | AGENT_F | BLOCKER | No LLM nondeterminism fallback strategy
**Evidence:** specs/10_determinism_and_caching.md:5 sets temp=0 but doesn't address provider-specific nondeterminism
**Proposed Fix:** Add to specs/10_determinism_and_caching.md section "## LLM Nondeterminism Tolerance": Define acceptable variance threshold, fallback strategy (retry vs manual review), test harness
**Acceptance Criteria:** Spec defines LLM nondeterminism tolerance policy

#### GAP-012 | AGENT_F | BLOCKER | Batch execution completion criteria undefined
**Evidence:** specs/35_batch_execution.md doesn't exist (see GAP-010)
**Proposed Fix:** In new specs/35_batch_execution.md, define: "Batch complete when all runs reach done/failed state, batch success = all runs success, batch failure = any run failure (configurable)"
**Acceptance Criteria:** Batch completion criteria defined in spec

---

### Priority 6: Specs (Missing Algorithms) - 19 gaps

#### GAP-013 | AGENT_S | BLOCKER | Patch engine conflict resolution algorithm missing
**Evidence:** specs/08_patch_engine.md:30-35 says "conflicts detected" but no resolution algorithm
**Proposed Fix:** Add to specs/08_patch_engine.md section "## Conflict Resolution": Define algorithm (e.g., last-write-wins with marker, reject with error, manual merge)
**Acceptance Criteria:** Conflict resolution algorithm specified in spec

#### GAP-014 | AGENT_S | BLOCKER | State replay algorithm unspecified
**Evidence:** specs/11_state_and_events.md:50-60 mentions replay but no algorithm
**Proposed Fix:** Add to specs/11_state_and_events.md section "## Replay Algorithm": Step-by-step replay process (load snapshot, apply events in order, rebuild state)
**Acceptance Criteria:** Replay algorithm specified with pseudocode

#### GAP-015 | AGENT_S | BLOCKER | MCP endpoint specifications missing
**Evidence:** specs/14_mcp_endpoints.md:1-26 lists tools but no HTTP endpoints
**Proposed Fix:** Add to specs/14_mcp_endpoints.md section "## Endpoint Specifications": HTTP method, path, request/response schemas for each tool
**Acceptance Criteria:** All 11 MCP tools have HTTP endpoint specs

#### GAP-016 to GAP-031 | AGENT_S | BLOCKER | (16 more missing algorithms/specs)
**Summary:** AGENT_S identified 19 total BLOCKER gaps for missing algorithms/specifications:
- MCP tool error handling (2 gaps)
- Adapter interface undefined (1 gap)
- Pilot execution contract missing (1 gap)
- Telemetry failure handling incomplete (1 gap)
- Tool version verification missing (1 gap)
- Navigation update algorithm missing (1 gap)
- Handoff failure recovery missing (1 gap)
- And 8 more (see agents/AGENT_S/GAPS.md for full details)

**Consolidated Fix:** Add missing algorithms/specs to respective spec files
**Estimated Effort:** 2-4 days
**Acceptance Criteria:** All 19 BLOCKER gaps in AGENT_S/GAPS.md resolved

---

## MAJOR Gaps (71)

### Exit Code / Determinism (6 gaps)

#### GAP-032 | AGENT_G | MAJOR | Validator exit codes inconsistent with spec
**Evidence:** specs/01_system_contract.md:141-146 defines exit codes but validators use wrong codes
**Proposed Fix:** Update all validators to use exit 2 for validation failures (not exit 1)
**Acceptance Criteria:** All validators use correct exit codes per spec

#### GAP-033 | AGENT_G | MAJOR | Validation report issue ordering non-deterministic
**Evidence:** specs/10_determinism_and_caching.md:51 requires deterministic ordering but validators don't sort
**Proposed Fix:** Update validators to sort issues by (severity DESC, gate_name ASC, location.path ASC, location.line ASC)
**Acceptance Criteria:** validation_report.json issues are deterministically ordered

#### GAP-034 | AGENT_G | MAJOR | Validation report timestamps not controlled
**Evidence:** specs/10_determinism_and_caching.md requires stable timestamps but validators use wall-clock time
**Proposed Fix:** Update validators to use run_start_time from context (not datetime.now())
**Acceptance Criteria:** validation_report.json timestamps are stable across runs

#### GAP-035 | AGENT_G | MAJOR | Validation report issue IDs hardcoded
**Evidence:** Validators use hardcoded or random issue IDs instead of deriving from (gate_name, location, issue_type)
**Proposed Fix:** Update validators to derive issue_id = hash(gate_name + location.path + location.line + issue_type)
**Acceptance Criteria:** Issue IDs are stable and deterministic

#### GAP-036 | AGENT_G | MAJOR | External links validator missing
**Evidence:** specs/09_validation_gates.md requires external link validation but not implemented
**Proposed Fix:** Create src/launch/validators/external_links.py (or mark as WONT_FIX if external links optional)
**Acceptance Criteria:** External links validator exists OR spec updated to mark external links as optional

#### GAP-037 | AGENT_G | MAJOR | Frontmatter validator incomplete
**Evidence:** specs/09_validation_gates.md requires frontmatter validation but coverage unclear
**Proposed Fix:** Verify frontmatter validator covers all fields from frontmatter_contract.schema.json
**Acceptance Criteria:** Frontmatter validator covers 100% of schema fields

---

### Schemas (2 gaps)

#### GAP-038 | AGENT_C | MAJOR | Missing `retryable` field in ApiError schema
**Evidence:** specs/17_github_commit_service.md:85-90 requires `retryable` boolean but specs/schemas/api_error.schema.json doesn't include it
**Proposed Fix:** Add to api_error.schema.json: `"retryable": {"type": "boolean", "description": "Whether this error is retryable"}`
**Acceptance Criteria:** ApiError schema includes `retryable` field
**Estimated Fix Time:** 5 minutes

#### GAP-039 | AGENT_C | MAJOR | Field name mismatch (`audience` vs `who_it_is_for`)
**Evidence:** Spec uses `who_it_is_for`, schema might use `audience` (verify and harmonize)
**Proposed Fix:** Deprecate `audience` field, use `who_it_is_for` everywhere
**Acceptance Criteria:** Consistent field naming across specs and schemas
**Estimated Fix Time:** 2 minutes

---

### Features (18 gaps)

#### GAP-040 to GAP-057 | AGENT_F | MAJOR | (18 feature gaps)
**Summary:** AGENT_F identified 18 MAJOR feature gaps:
- Missing compliance gates N/O/Q/R implementations (4 gaps)
- Caching incomplete (no storage/invalidation/completion) (3 gaps)
- Missing E2E tests for resume, telemetry buffering, conflict resolution (3 gaps)
- Rollback metadata collected but not actionable (1 gap)
- And 7 more (see agents/AGENT_F/GAPS.md for full details)

**Consolidated Fix:** Implement missing features per feature inventory
**Estimated Effort:** 1-2 weeks
**Acceptance Criteria:** All 18 MAJOR gaps in AGENT_F/GAPS.md resolved

---

### Specs (38 gaps)

#### GAP-058 to GAP-095 | AGENT_S | MAJOR | (38 spec quality gaps)
**Summary:** AGENT_S identified 38 MAJOR spec quality gaps:
- Vague language ("should/may" without SHALL/MUST alternatives) (7 gaps)
- Missing edge case handling in worker specs (12 gaps)
- Incomplete failure mode specifications (10 gaps)
- Missing best practices (auth, toolchain verification, adapter guide) (9 gaps)

**Consolidated Fix:** Address all MAJOR gaps in AGENT_S/GAPS.md
**Estimated Effort:** 1-2 weeks
**Acceptance Criteria:** All 38 MAJOR gaps in AGENT_S/GAPS.md resolved

---

### Docs/Links (5 gaps)

#### GAP-096 | AGENT_L | MAJOR | Exit code conflict (specs vs docs)
**Evidence:** specs/01_system_contract.md:143 says exit 2 for validation failure BUT docs/cli_usage.md:50 says exit 1
**Proposed Fix:** Update docs/cli_usage.md:50 to match specs/01_system_contract.md:143 (specs are authority)
**Acceptance Criteria:** Docs match specs
**Estimated Fix Time:** 30 minutes

#### GAP-097 | AGENT_L | MAJOR | Missing schemas/README.md
**Evidence:** No guidance on where to add new schemas
**Proposed Fix:** Create specs/schemas/README.md with: schema naming convention, where to add new schemas, how to validate schemas
**Acceptance Criteria:** schemas/README.md exists
**Estimated Fix Time:** 1-2 hours

#### GAP-098 | AGENT_L | MAJOR | Missing reports/README.md
**Evidence:** No guidance on evidence storage structure
**Proposed Fix:** Create reports/README.md with: directory structure, naming conventions, what goes where
**Acceptance Criteria:** reports/README.md exists
**Estimated Fix Time:** 1-2 hours

#### GAP-099 | AGENT_L | MAJOR | CONTRIBUTING.md is minimal
**Evidence:** CONTRIBUTING.md has only 3 lines, no detailed guidance
**Proposed Fix:** Expand CONTRIBUTING.md with: how to add specs, how to add taskcards, how to run validators, PR process
**Acceptance Criteria:** CONTRIBUTING.md has comprehensive guidance
**Estimated Fix Time:** 2-3 hours

#### GAP-100 | AGENT_L | MAJOR | Missing docs/README.md
**Evidence:** No index for docs/ directory
**Proposed Fix:** Create docs/README.md with: index of all docs, when to use each doc, how to add new docs
**Acceptance Criteria:** docs/README.md exists
**Estimated Fix Time:** 30 minutes

---

### Requirements (5 gaps)

#### GAP-101 to GAP-105 | AGENT_R | ERROR/WARN | (5 requirement gaps)
**Summary:** AGENT_R identified 5 ERROR/WARN gaps:
- Grounding threshold unspecified (ERROR)
- Launch tiers undefined (ERROR)
- Timeout strategy missing (ERROR)
- Change budgets unspecified (ERROR)
- Confidence threshold missing (ERROR)

**Consolidated Fix:** Add missing requirements to specs
**Estimated Effort:** 2-3 days
**Acceptance Criteria:** All ERROR gaps in AGENT_R/GAPS.md resolved

---

## MINOR Gaps (75)

### Taskcards (14 gaps)

#### GAP-106 to GAP-119 | AGENT_P | MINOR | (14 taskcard gaps)
**Summary:** AGENT_P identified 14 MINOR gaps:
- All are "add explicit 'do not invent' reminders" to taskcards
- Non-blocking (taskcards inherit no-invention rules from 00_TASKCARD_CONTRACT.md)
- Quality enhancements only

**Consolidated Fix:** Add explicit "do not invent" section to 14 taskcards
**Estimated Effort:** 1-2 hours
**Acceptance Criteria:** All 14 taskcards have explicit no-invention boundaries

---

### Specs (16 gaps)

#### GAP-120 to GAP-135 | AGENT_S | MINOR | (16 spec quality gaps)
**Summary:** AGENT_S identified 16 MINOR spec quality gaps:
- Missing examples (5 gaps)
- No rationale documented (4 gaps)
- Minor terminology inconsistencies (7 gaps)

**Consolidated Fix:** Address all MINOR gaps in AGENT_S/GAPS.md
**Estimated Effort:** 3-5 days
**Acceptance Criteria:** All 16 MINOR gaps in AGENT_S/GAPS.md resolved

---

### Features (6 gaps)

#### GAP-136 to GAP-141 | AGENT_F | MINOR | (6 feature gaps)
**Summary:** AGENT_F identified 6 MINOR feature gaps:
- Validator timeout profiles unclear (1 gap)
- Telemetry buffering edge cases (1 gap)
- Pilot metadata completeness (1 gap)
- And 3 more (see agents/AGENT_F/GAPS.md)

**Consolidated Fix:** Address all MINOR gaps in AGENT_F/GAPS.md
**Estimated Effort:** 2-3 days
**Acceptance Criteria:** All 6 MINOR gaps in AGENT_F/GAPS.md resolved

---

### Schemas (1 gap)

#### GAP-142 | AGENT_C | MINOR | Missing `schema_version` in embedded objects
**Evidence:** Some embedded objects lack `schema_version` field
**Proposed Fix:** Add `schema_version` to all embedded objects OR clarify policy (only top-level objects need version)
**Acceptance Criteria:** Schema versioning policy is clear and enforced
**Estimated Fix Time:** 10 minutes (if adding fields) OR 5 minutes (if clarifying policy)

---

### Validators (2 gaps)

#### GAP-143 | AGENT_G | MINOR | Markdownlint validator missing
**Evidence:** No markdownlint validator found
**Proposed Fix:** Create src/launch/validators/markdownlint.py OR mark as WONT_FIX if not required
**Acceptance Criteria:** Markdownlint validator exists OR spec updated to mark as optional

#### GAP-144 | AGENT_G | MINOR | Template token lint validator missing
**Evidence:** No template token validator found
**Proposed Fix:** Create src/launch/validators/template_tokens.py OR mark as WONT_FIX if not required
**Acceptance Criteria:** Template token validator exists OR spec updated to mark as optional

---

### Links (2 gaps)

#### GAP-145 | AGENT_L | MINOR | AGENT_G placeholder links
**Evidence:** AGENT_G report has placeholder links (not actual broken links, just TODO placeholders)
**Proposed Fix:** Replace placeholder links with actual links OR mark as "(link TBD)"
**Acceptance Criteria:** No placeholder links in final reports
**Estimated Fix Time:** 5 minutes

#### GAP-146 | AGENT_L | MINOR | Self-referential link
**Evidence:** One file links to itself (harmless but confusing)
**Proposed Fix:** Remove self-referential link OR change to anchor link
**Acceptance Criteria:** No self-referential links
**Estimated Fix Time:** 5 minutes

---

### Requirements (11 gaps)

#### GAP-147 to GAP-157 | AGENT_R | WARN/INFO | (11 requirement gaps)
**Summary:** AGENT_R identified 11 WARN/INFO gaps:
- Near-identical diffs handling (WARN)
- Snippet priority tie-breaking (WARN)
- Concurrency limits unspecified (WARN)
- Sampling strategy missing (WARN)
- Retry policy undefined (WARN)
- Cache invalidation rules (INFO)
- Section ordering strategy (INFO)
- Patch conflicts handling (INFO)
- Phantom paths handling (INFO)
- Binary assets handling (INFO)
- Fix loops prevention (INFO)

**Consolidated Fix:** Add missing requirements to specs
**Estimated Effort:** 1-2 weeks
**Acceptance Criteria:** All WARN/INFO gaps in AGENT_R/GAPS.md resolved

---

## Gap Resolution Priority Order

### Phase 1: BLOCKER Gaps (Must Fix First)
**Goal:** Unblock implementation start
**Estimated Effort:** 2-3 weeks

1. **Week 1:** Links + Quick Wins (GAP-001, GAP-007, GAP-008, GAP-009)
2. **Week 2-3:** Validators + Specs (GAP-002 to GAP-006, GAP-013 to GAP-031)
3. **Week 2-3:** Features (GAP-010 to GAP-012)

### Phase 2: MAJOR Gaps (Should Fix Before Implementation)
**Goal:** Reduce implementation risk
**Estimated Effort:** 1-2 weeks

1. Exit codes / Determinism (GAP-032 to GAP-037)
2. Schemas (GAP-038 to GAP-039)
3. Features (GAP-040 to GAP-057)
4. Specs (GAP-058 to GAP-095)
5. Docs/Links (GAP-096 to GAP-100)
6. Requirements (GAP-101 to GAP-105)

### Phase 3: MINOR Gaps (Can Defer)
**Goal:** Quality enhancements
**Estimated Effort:** 1-2 weeks

1. Taskcards (GAP-106 to GAP-119)
2. Specs (GAP-120 to GAP-135)
3. Features (GAP-136 to GAP-141)
4. Schemas (GAP-142)
5. Validators (GAP-143 to GAP-144)
6. Links (GAP-145 to GAP-146)
7. Requirements (GAP-147 to GAP-157)

---

## Gap Resolution Tracking

To track gap resolution progress:
1. Mark resolved gaps with ✅ in this file
2. Update agent-specific GAPS.md files with resolution evidence
3. Re-run verification after major gap resolution to ensure no regressions
4. Use HEALING_PROMPT.md to spawn healing agents for mechanical fixes

---

## References

- **Agent Gap Reports:**
  - [agents/AGENT_R/GAPS.md](agents/AGENT_R/GAPS.md)
  - [agents/AGENT_F/GAPS.md](agents/AGENT_F/GAPS.md)
  - [agents/AGENT_S/GAPS.md](agents/AGENT_S/GAPS.md)
  - [agents/AGENT_C/GAPS.md](agents/AGENT_C/GAPS.md)
  - [agents/AGENT_G/GAPS.md](agents/AGENT_G/GAPS.md)
  - [agents/AGENT_P/GAPS.md](agents/AGENT_P/GAPS.md)
  - [agents/AGENT_L/GAPS.md](agents/AGENT_L/GAPS.md)

- **INDEX:** [INDEX.md](INDEX.md)
- **HEALING_PROMPT:** [HEALING_PROMPT.md](HEALING_PROMPT.md)
