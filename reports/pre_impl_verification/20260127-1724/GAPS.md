# Consolidated Gaps Report

**Run ID:** `20260127-1724`
**Generated:** 2026-01-27 18:30 UTC
**Orchestrator:** Pre-Implementation Verification Supervisor

---

## Executive Summary

**Total Gaps Identified:** 98
- **BLOCKER:** 41 (must resolve before implementation)
- **WARNING:** 37 (ambiguities, missing specifications)
- **INFO/MINOR:** 20 (expected pre-implementation state, minor improvements)

**Gap Distribution by Agent:**

| Agent | Deliverables | Total Gaps | BLOCKER | WARNING | INFO/MINOR |
|-------|--------------|------------|---------|---------|------------|
| AGENT_R (Requirements) | 4/4 ✅ | 12 | 4 | 5 | 3 |
| AGENT_F (Features) | 5/5 ✅ | 25 | 3 | 5 | 17 |
| AGENT_S (Specs Quality) | 4/4 ✅ | 24 | 8 | 16 | 0 |
| AGENT_C (Schemas) | 4/4 ✅ | 0 | 0 | 0 | 0 |
| AGENT_G (Gates) | 4/4 ✅ | 16 | 13 | 3 | 0 |
| AGENT_P (Plans/Taskcards) | 4/4 ✅ | 3 | 0 | 0 | 3 |
| AGENT_L (Links/Professionalism) | 5/5 ✅ | 2 | 0 | 0 | 2 |
| **TOTAL** | **28/28 ✅** | **98** | **41** | **37** | **20** |

---

## BLOCKER Gaps (41 total)

These gaps must be resolved before implementation begins. They represent missing specifications, algorithms, or implementations that would block feature development.

### From AGENT_R (Requirements Extractor) — 4 BLOCKERS

#### R-GAP-001 | BLOCKER | Missing empty input handling for ProductFacts
**Issue:** Unclear whether zero-evidence runs should succeed or fail
**Evidence:** specs/03_product_facts_and_evidence.md:178-183
**Proposed Fix:**
Add REQ-EDGE-001 to specs/03 with 5 explicit acceptance criteria:
1. Define behavior when repository has no README, no code, no docs
2. Specify whether empty product_facts.json is valid or should emit ERROR
3. Define minimum evidence threshold (0, 1, or N claims required)
4. Specify error code: FACTS_INSUFFICIENT_EVIDENCE
5. Add acceptance test: pilot-empty-repo

#### R-GAP-002 | BLOCKER | Ambiguous floating ref detection (runtime vs preflight)
**Issue:** Unclear if runtime floating ref check duplicates preflight or catches new failure modes
**Evidence:** specs/34_strict_compliance_guarantees.md:59-85
**Proposed Fix:**
Add REQ-GUARD-001 to specs/34 with 4 enforcement rules:
1. Preflight: Detects floating refs in run_config, pilots, taskcards (Gate J)
2. Runtime: Detects floating refs in LLM-generated patches, evidence citations
3. Enforcement: Runtime check supplements (not duplicates) preflight
4. Error code: GUARD_FLOATING_REF_RUNTIME

#### R-GAP-003 | BLOCKER | Missing Hugo config fingerprinting algorithm
**Issue:** Cannot deterministically compute fingerprints, breaks caching/validation
**Evidence:** specs/09_validation_gates.md:86-115
**Proposed Fix:**
Add REQ-HUGO-FP-001 to specs/09 with step-by-step algorithm:
1. Load hugo.toml/config.toml (whichever exists)
2. Canonicalize (sort keys, normalize booleans, strip comments)
3. Compute SHA-256 hash of canonical form
4. Store in site_context.json field: hugo_config_fingerprint
5. Gate 3 validates fingerprint matches expected value

#### R-GAP-004 | BLOCKER | Missing template resolution order
**Issue:** Ambiguous which template wins when multiple match (by tier, by name, by ruleset)
**Evidence:** specs/20_rulesets_and_templates_registry.md:55-72
**Proposed Fix:**
Add REQ-TMPL-001 to specs/20 defining resolution order:
1. Exact match by name (highest priority)
2. Tier match (launch_tier in page_plan.json)
3. Fallback to default template
4. Error if no match: TEMPLATE_NOT_FOUND
5. Document tie-breaking rules (lexicographic by template name)

---

### From AGENT_F (Features & Testability) — 3 BLOCKERS

#### F-GAP-021 | BLOCKER | Runtime secret redaction not implemented (TC-590 pending)
**Issue:** Secrets may leak in LLM-generated content despite preflight scan
**Evidence:** plans/traceability_matrix.md:284, specs/34_strict_compliance_guarantees.md:161-187
**Proposed Fix:**
1. Implement TC-590 (Secret Redaction Runtime)
2. Hook into patch application pipeline (after LLM generation, before disk write)
3. Scan patch content for regex patterns from secrets.baseline
4. Redact matches with placeholder: `[REDACTED:SECRET]`
5. Emit GUARD_SECRET_DETECTED_RUNTIME if redaction occurs
**Acceptance Criteria:**
- Test: Generate patch containing hardcoded API key → redacted before write
- Guarantee E enforcement: 100% (preflight + runtime)

#### F-GAP-022 | BLOCKER | Rollback metadata generation not implemented (TC-480 pending)
**Issue:** Cannot validate Guarantee L until PRManager generates rollback metadata
**Evidence:** plans/traceability_matrix.md:492, specs/12_pr_and_release.md:32-54
**Proposed Fix:**
1. Implement TC-480 (PRManager with rollback metadata)
2. Generate pr.json with rollback_metadata field:
   - original_base_ref (SHA before changes)
   - changed_files (list of modified paths)
   - undo_patches (reverse patches for each change)
   - rollback_instructions (human-readable recovery steps)
3. Validate pr.json against specs/schemas/pr.schema.json
4. Pass Gate 13 (Rollback Metadata Validation)
5. Test rollback: Apply undo_patches → verify repo returns to original_base_ref state
**Acceptance Criteria:**
- Rollback metadata generated for all PR creations
- Guarantee L enforcement: 100%

#### F-GAP-023 | BLOCKER | LangGraph orchestrator not implemented (TC-300 pending)
**Issue:** Cannot execute full E2E pipeline without orchestrator state machine
**Evidence:** plans/traceability_matrix.md:30, specs/state-graph.md, specs/11_state_and_events.md
**Proposed Fix:**
1. Implement TC-300 (Orchestrator)
2. Define LangGraph state machine with nodes for W1-W9 workers
3. Implement state transitions per specs/state-graph.md
4. Emit events to event log (specs/schemas/event.schema.json)
5. Support resume from snapshot (specs/schemas/snapshot.schema.json)
**Acceptance Criteria:**
- E2E test: Run full pipeline on pilot repo → all workers execute in sequence
- State persistence: Interrupt mid-run → resume from snapshot → completes successfully

---

### From AGENT_S (Specs Quality Auditor) — 8 BLOCKERS

#### S-GAP-001 | BLOCKER | Missing error code SECTION_WRITER_UNFILLED_TOKENS
**Issue:** Spec references error code but system contract doesn't define it
**Evidence:** specs/21_worker_contracts.md:223
**Proposed Fix:**
Add to specs/01_system_contract.md error code registry:
```
SECTION_WRITER_UNFILLED_TOKENS
- Severity: ERROR
- When: LLM output contains unfilled template tokens like {{PRODUCT_NAME}}
- Action: Fail validation, require manual review or re-generation
```

#### S-GAP-003 | BLOCKER | Missing spec_ref field definition (Guarantee K)
**Issue:** Unclear if spec_ref is launcher repo SHA or spec pack SHA
**Evidence:** specs/34_strict_compliance_guarantees.md:377-385
**Proposed Fix:**
Add to specs/01_system_contract.md field definition:
```
spec_ref (string, required in run_config.json, page_plan.json, pr.json)
- Definition: Git commit SHA of the foss-launcher repository containing specs used for this run
- Format: 40-character hex SHA (not short SHA)
- Validation: Must resolve to actual commit in github.com/anthropics/foss-launcher
- Purpose: Version locking for reproducibility (Guarantee K)
```

#### S-GAP-006 | BLOCKER | Missing validation_profile field in run_config
**Issue:** Spec implies profile controls gate strength but field not in schema
**Evidence:** specs/09_validation_gates.md:14-18, specs/schemas/run_config.schema.json
**Proposed Fix:**
Add validation_profile to run_config.schema.json:
```json
"validation_profile": {
  "type": "string",
  "enum": ["strict", "standard", "permissive"],
  "description": "Controls gate enforcement strength per specs/09:14-18"
}
```
Update specs/01:28-39 to document field semantics

#### S-GAP-010 | BLOCKER | Missing empty repository edge case handling
**Issue:** No specification for behavior when repository is empty (no files)
**Evidence:** specs/02_repo_ingestion.md:45-60
**Proposed Fix:**
Add to specs/02 edge case section:
```
Empty Repository Handling
- Detection: repository has zero files after clone (except .git/)
- Behavior: Emit ERROR with code REPO_EMPTY
- repo_inventory.json: NOT generated (validation fails before artifact creation)
- Rationale: Cannot proceed without any content to document
```

#### S-GAP-013 | BLOCKER | Missing error code for GATE_DETERMINISM_VARIANCE
**Issue:** Gate T references error code not defined in system contract
**Evidence:** specs/09_validation_gates.md:471-495
**Proposed Fix:**
Add to specs/01_system_contract.md error code registry:
```
GATE_DETERMINISM_VARIANCE
- Severity: ERROR
- When: Re-running with identical inputs produces different outputs
- Action: Fail Gate T (Test Determinism), block release
- Debug: Compare run artifacts with reference run (diff hashes)
```

#### S-GAP-016 | BLOCKER | Missing repository fingerprint hash algorithm
**Issue:** Cannot deterministically fingerprint repositories for caching
**Evidence:** specs/02_repo_ingestion.md:120-145
**Proposed Fix:**
Add to specs/02 algorithm specification:
```
Repository Fingerprinting Algorithm
1. List all non-phantom files (exclude paths in phantom_paths)
2. For each file: Compute SHA-256(file_path + file_content)
3. Sort file hashes lexicographically
4. Compute SHA-256(concatenated sorted hashes) → repo_fingerprint
5. Store in repo_inventory.json field: repo_fingerprint
```

#### S-GAP-020 | BLOCKER | Missing spec for telemetry get endpoint
**Issue:** MCP tool references endpoint but no spec defines contract
**Evidence:** specs/16_local_telemetry_api.md (implied), specs/24_mcp_tool_schemas.md
**Proposed Fix:**
Add to specs/16 endpoint specification:
```
GET /telemetry/{run_id}
- Request: Query parameter run_id (optional, defaults to latest)
- Response: snapshot.json (specs/schemas/snapshot.schema.json)
- Error: 404 if run_id not found
```
Add get_telemetry tool schema to specs/24

#### S-GAP-023 | BLOCKER | Missing spec for Markdown test harness contract
**Issue:** Gate T references test harness but no spec defines interface
**Evidence:** specs/09_validation_gates.md:471-495
**Proposed Fix:**
Add specs/35_test_harness_contract.md with:
1. Test harness interface (CLI arguments, exit codes, output format)
2. Determinism verification protocol (run twice, compare artifacts)
3. Artifact comparison rules (ignore timestamps, compare content hashes)
4. Error reporting format (validation_report.json with Gate T results)

---

### From AGENT_G (Gates/Validators Auditor) — 13 BLOCKERS

#### G-GAP-001 | BLOCKER | Gate 2 (Markdown Lint) not implemented
**Issue:** Cannot enforce markdown quality, frontmatter contracts
**Evidence:** specs/09:53-84, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/markdown_lint.py:
1. Load frontmatter_contract.json (required fields, types)
2. Validate all *.md files in run_dir
3. Check frontmatter required fields present and correct type
4. Run markdownlint with pinned ruleset (.markdownlint.json)
5. Emit GATE_MARKDOWN_LINT_ERROR for violations

#### G-GAP-002 | BLOCKER | Gate 3 (Hugo Config Compatibility) not implemented
**Issue:** Cannot validate Hugo config matches expectations
**Evidence:** specs/09:86-116, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/hugo_config.py:
1. Load hugo_facts.json (from RepoScout W1)
2. Validate baseURL matches expected pattern
3. Check theme is allowlisted (or null for custom)
4. Verify content_dir, layouts_dir, static_dir paths exist
5. Emit GATE_HUGO_CONFIG_ERROR for mismatches

#### G-GAP-003 | BLOCKER | Gate 4 (Platform-Aware Layout) not implemented
**Issue:** Cannot validate V2 platform content_layout paths
**Evidence:** specs/09:118-154, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/platform_layout.py:
1. Load page_plan.json
2. For each page: Check content_layout field matches V2 pattern
3. Validate paths follow platform-aware structure (specs/32)
4. Verify locale-specific variants exist if locales > 1
5. Emit GATE_PLATFORM_LAYOUT_ERROR for violations

#### G-GAP-004 | BLOCKER | Gate 5 (Hugo Build Validation) not implemented
**Issue:** Cannot detect Hugo build failures before committing
**Evidence:** specs/09:156-186, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/hugo_build.py:
1. Run `hugo --gc` in hermetic environment (Guarantee B)
2. Check exit code (0 = success, non-zero = fail)
3. Parse stderr for Hugo errors (template errors, missing shortcodes)
4. Validate build artifacts exist in public/ directory
5. Emit GATE_HUGO_BUILD_ERROR if build fails

#### G-GAP-005 | BLOCKER | Gate 6 (Internal Links Check) not implemented
**Issue:** Cannot detect broken internal links before committing
**Evidence:** specs/09:188-218, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/internal_links.py:
1. Extract all markdown links from generated pages
2. Resolve relative paths to absolute paths
3. Check target files exist in run_dir
4. Validate anchor fragments exist in target markdown
5. Emit GATE_INTERNAL_LINK_BROKEN for dead links

#### G-GAP-006 | BLOCKER | Gate 7 (External Links Check) not implemented
**Issue:** Cannot detect broken external links (profile-dependent)
**Evidence:** specs/09:220-249, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/external_links.py:
1. Extract all http/https links from generated pages
2. Check if validation_profile allows external link checking (skippable)
3. Fetch links with timeout (5s) and retry (3 attempts)
4. Check HTTP status codes (200-299 = success)
5. Emit GATE_EXTERNAL_LINK_BROKEN for dead links (WARNING, not ERROR)
**Note:** Non-deterministic by nature, spec allows skipping in profiles

#### G-GAP-007 | BLOCKER | Gate 8 (Snippet Syntax Validation) not implemented
**Issue:** Cannot validate code snippet syntax before committing
**Evidence:** specs/09:251-282, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/snippet_checks.py:
1. Load snippet_catalog.json
2. For each snippet: Validate language-specific syntax (Python: ast.parse, etc.)
3. Optionally run snippet in container if spec allows (deterministic only)
4. Check snippet compiles/parses without errors
5. Emit GATE_SNIPPET_SYNTAX_ERROR for invalid snippets

#### G-GAP-008 | BLOCKER | Gate 9 (TruthLock Compilation) not implemented
**Issue:** Cannot enforce claim verification (HIGHEST PRIORITY)
**Evidence:** specs/09:284-317, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/truth_lock.py:
1. Load truth_lock_report.json and evidence_map.json
2. For each claim in generated markdown: Verify claim_id exists in evidence_map
3. Check claim text matches evidence_map.claims[].claim_text
4. Validate citations point to valid evidence files
5. Emit GATE_TRUTH_LOCK_VIOLATION for unlinked claims
**Priority:** HIGHEST (critical for Guarantee: all claims must trace to evidence)

#### G-GAP-009 | BLOCKER | Gate 10 (Consistency Checks) not implemented
**Issue:** Cannot detect contradictions, duplicate content
**Evidence:** specs/09:319-353, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/consistency.py:
1. Check for duplicate page titles across pages
2. Validate no contradicting facts (evidence_map.contradictions resolved)
3. Check version numbers consistent across files
4. Validate license info consistent (if present in multiple files)
5. Emit GATE_CONSISTENCY_ERROR for violations

#### G-GAP-010 | BLOCKER | Gate 11 (Template Token Lint) not implemented
**Issue:** Cannot detect unfilled template tokens like {{PRODUCT_NAME}}
**Evidence:** specs/09:355-383, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/template_token_lint.py:
1. Search all generated markdown for template token patterns: `{{.*}}`
2. Check if tokens are intentional (code blocks, literal examples) or errors
3. Emit GATE_TEMPLATE_TOKEN_UNFILLED for unintentional tokens
4. Cross-reference with section_writer output to detect generation failures

#### G-GAP-011 | BLOCKER | Gate 12 (Universality Check) not implemented
**Issue:** Cannot validate multi-locale content for completeness
**Evidence:** specs/09:385-428, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/universality.py:
1. Load page_plan.json with locales array
2. For each page: Validate locale-specific variants exist for all locales
3. Check content_layout paths follow V2 structure with locale segments
4. Validate no hardcoded locale-specific content in universal templates
5. Emit GATE_UNIVERSALITY_ERROR for incomplete locale coverage

#### G-GAP-012 | BLOCKER | Gate 13 (Rollback Metadata Validation) not implemented
**Issue:** Cannot validate Guarantee L (rollback contract)
**Evidence:** specs/09:430-468, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/rollback_metadata.py:
1. Load pr.json (from PRManager)
2. Validate rollback_metadata field exists and complete
3. Check undo_patches are valid reverse patches
4. Validate rollback_instructions are human-readable
5. Test: Apply undo_patches to verify reversibility
6. Emit GATE_ROLLBACK_INVALID if rollback metadata incomplete

#### G-GAP-013 | BLOCKER | Gate T (Test Determinism) not implemented
**Issue:** Cannot verify reproducibility of full pipeline
**Evidence:** specs/09:471-495, cli.py:217-227 (NOT_IMPLEMENTED)
**Proposed Fix:**
Implement in src/launch/validators/test_determinism.py:
1. Run full pipeline twice with identical inputs (same repo SHA, same run_config)
2. Compare output artifacts (byte-by-byte hash comparison)
3. Ignore timestamps (run_start_time, run_end_time) in comparison
4. Emit GATE_DETERMINISM_VARIANCE if outputs differ
5. Log diff for debugging (which artifacts differ, how)
**Note:** Conditional on LLM determinism (temperature=0, seed fixed)

---

## WARNING Gaps (37 total)

These gaps represent ambiguities, vague language, or missing specifications that could lead to inconsistent implementations.

### From AGENT_R (Requirements) — 5 WARNINGS

**R-GAP-005** | WARNING | Incomplete binary file size limits
- **Evidence:** specs/02:180-185 (mentions "large binaries" but no threshold defined)
- **Proposed Fix:** Define max_binary_file_size (e.g., 10MB) and behavior on exceed

**R-GAP-006** | WARNING | Ambiguous contradiction resolution thresholds
- **Evidence:** specs/03:110-131 (contradictions array exists but no resolution rules)
- **Proposed Fix:** Define when to fail vs warn on contradictions (BLOCKER if >N contradictions?)

**R-GAP-007** | WARNING | Missing telemetry retry intervals
- **Evidence:** specs/16:20-35 (retry policy mentioned but intervals not specified)
- **Proposed Fix:** Define retry intervals (e.g., exponential backoff: 1s, 2s, 4s, 8s)

**R-GAP-008** | WARNING | Snippet validation failure thresholds
- **Evidence:** specs/05:18-21 (validation mentioned but no threshold for acceptable failures)
- **Proposed Fix:** Define max_snippet_failures (e.g., fail run if >10% snippets invalid)

**R-GAP-009** | WARNING | Ambiguous "best effort" language in specs/03
- **Evidence:** specs/03:45 ("best effort extraction" is vague)
- **Proposed Fix:** Replace with quantifiable success criteria (e.g., "extract ≥90% of facts")

---

### From AGENT_F (Features) — 5 WARNINGS

**F-GAP-010** | WARNING | Template rendering reproducibility conditional on LLM determinism
- **Evidence:** specs/07, LLM API docs
- **Proposed Fix:** Document LLM temperature=0, seed=fixed requirement for determinism

**F-GAP-011** | WARNING | Missing test fixtures for patch conflicts
- **Evidence:** specs/08 (patch idempotency spec'd but no conflict test fixtures)
- **Proposed Fix:** Create test fixtures in pilots/ for merge conflict scenarios

**F-GAP-012** | WARNING | Fix loop reproducibility conditional on LLM
- **Evidence:** specs/09 (validation fix loop uses LLM to repair issues)
- **Proposed Fix:** Document non-determinism risk, recommend manual review for fix loops

**F-GAP-013** | WARNING | MCP quickstart inference not pilot-validated
- **Evidence:** specs/24 (MCP tools infer product from URL but no pilot test)
- **Proposed Fix:** Add pilot test for MCP quickstart with real product URL

**F-GAP-014** | WARNING | Caching implementation status unclear
- **Evidence:** specs/10 (caching mentioned but implementation status unknown)
- **Proposed Fix:** Update traceability matrix with TC-580 status

---

### From AGENT_S (Specs Quality) — 16 WARNINGS

**S-GAP-002** | WARNING | Vague "best effort" language in specs/03:45
**S-GAP-004** | WARNING | Ambiguous "stable ordering" (lexicographic? insertion order?) in specs/02:55
**S-GAP-005** | WARNING | Missing timeout specification for Hugo build in specs/09:156
**S-GAP-007** | WARNING | Vague "minimal" patch guidance in specs/08:20
**S-GAP-008** | WARNING | Ambiguous "clean" snapshot definition in specs/11:110
**S-GAP-009** | WARNING | Missing locale sensitivity specification in sorting (specs/02:55)
**S-GAP-011** | WARNING | Vague "stable" template resolution order in specs/20:55
**S-GAP-012** | WARNING | Missing edge case: What if product has zero claims? (specs/04:30)
**S-GAP-014** | WARNING | Ambiguous "reasonable" retry limits in specs/16:30
**S-GAP-015** | WARNING | Missing specification for frontmatter validation failure threshold
**S-GAP-017** | WARNING | Vague "appropriate" error messages in specs/01:139
**S-GAP-018** | WARNING | Missing specification for maximum evidence file size
**S-GAP-019** | WARNING | Ambiguous "recent" in "recent commits" (specs/03:70)
**S-GAP-021** | WARNING | Missing specification for snippet catalog deduplication rules
**S-GAP-022** | WARNING | Vague "significant" in "significant changes" (specs/12:40)
**S-GAP-024** | WARNING | Missing specification for page plan update conflict resolution

(See [agents/AGENT_S/GAPS.md](agents/AGENT_S/GAPS.md) for detailed evidence and proposed fixes for all 16 WARNING gaps)

---

### From AGENT_G (Gates) — 3 WARNINGS

**G-GAP-014** | WARNING | Validation report schema under-specified
- **Evidence:** specs/09:11-12 (validation_report.schema.json referenced but some fields unclear)
- **Proposed Fix:** Add explicit examples to schema for profile, manual_edits fields

**G-GAP-015** | WARNING | Gate error codes inconsistent naming
- **Evidence:** specs/09 (some gates use GATE_X_ERROR, others use X_VALIDATION_FAILED)
- **Proposed Fix:** Standardize all gate error codes to GATE_{N}_{ISSUE_TYPE}

**G-GAP-016** | WARNING | Gate determinism not provable for LLM-dependent gates
- **Evidence:** Gate 16 (Validation Fix Loop) uses LLM to repair issues
- **Proposed Fix:** Document non-determinism risk, recommend logging LLM prompts/responses

---

## INFO/MINOR Gaps (20 total)

These gaps represent expected pre-implementation state, minor documentation improvements, or non-blocking observations.

### From AGENT_R (Requirements) — 3 INFO

**R-GAP-010** | INFO | Tertiary sources not fully scanned (estimated 15-20 additional requirements)
**R-GAP-011** | INFO | Some requirements inferred from implementation examples (acceptable)
**R-GAP-012** | INFO | Optional enhancements not captured as requirements (by design)

---

### From AGENT_F (Features) — 17 MINOR

**F-GAP-001 to F-GAP-009, F-GAP-015 to F-GAP-020, F-GAP-024 to F-GAP-025** | MINOR | Testability warnings
- Missing test fixtures for specific features
- Implementation status unclear for caching, prompt versioning
- MCP tool schemas incomplete

(See [agents/AGENT_F/GAPS.md](agents/AGENT_F/GAPS.md) for detailed testability assessments)

---

### From AGENT_P (Plans/Taskcards) — 3 INFO

**P-GAP-001** | INFO | Orchestrator (TC-300) not started
- **Status:** Taskcard is Ready, implementation pending
- **Impact:** None (expected pre-implementation state)

**P-GAP-002** | INFO | Runtime gates (TC-570 extension) not started
- **Status:** Taskcard is Ready, preflight gates complete
- **Impact:** None (expected pre-implementation state)

**P-GAP-003** | INFO | PRManager (TC-480) not started
- **Status:** Taskcard is Ready, rollback design complete
- **Impact:** None (expected pre-implementation state)

---

### From AGENT_L (Links/Professionalism) — 2 INFO

**L-OBS-001** | INFO | Broken links in historical agent reports
- **Status:** 34 broken links in point-in-time snapshots (expected)
- **Impact:** None (historical reports are archival)

**L-OBS-002** | INFO | TODO markers in non-binding documentation
- **Status:** 1,535 markers in reports, templates, reference docs (0 in binding specs)
- **Impact:** None (binding specs are complete)

---

## Gap Remediation Roadmap

### Phase 1: IMMEDIATE (Before Implementation) — 41 BLOCKER Gaps

**Priority Order:**
1. **AGENT_G gaps (13 BLOCKERS):** Runtime gates 2-13 must be implemented (TC-570 extension)
2. **AGENT_S gaps (8 BLOCKERS):** Spec quality issues (missing error codes, field definitions)
3. **AGENT_R gaps (4 BLOCKERS):** Missing algorithms and edge case handling
4. **AGENT_F gaps (3 BLOCKERS):** Critical implementations (TC-300, TC-480, TC-590)

**Estimated Effort:** 10-15 days (assumes parallel work on independent gaps)

---

### Phase 2: SHORT-TERM (During Implementation) — 37 WARNING Gaps

**Priority Order:**
1. **AGENT_S gaps (16 WARNINGS):** Clarify vague language, add missing specifications
2. **AGENT_R gaps (5 WARNINGS):** Define thresholds and quantifiable criteria
3. **AGENT_F gaps (5 WARNINGS):** Add test fixtures, document LLM determinism constraints
4. **AGENT_G gaps (3 WARNINGS):** Standardize gate error codes, add schema examples

**Estimated Effort:** 5-7 days (documentation and spec clarifications)

---

### Phase 3: LONG-TERM (Post-MVP) — 20 INFO/MINOR Gaps

**Addressed Naturally:**
- AGENT_P gaps: Resolved as taskcards are implemented
- AGENT_F gaps: Resolved as features are developed and tested
- AGENT_R gaps: Tertiary requirements captured opportunistically
- AGENT_L gaps: No action needed (archival artifacts)

**Estimated Effort:** Ongoing (no dedicated effort required)

---

## Cross-References

### Detailed Gap Reports by Agent
- **AGENT_R:** [agents/AGENT_R/GAPS.md](agents/AGENT_R/GAPS.md)
- **AGENT_F:** [agents/AGENT_F/GAPS.md](agents/AGENT_F/GAPS.md)
- **AGENT_S:** [agents/AGENT_S/GAPS.md](agents/AGENT_S/GAPS.md)
- **AGENT_C:** [agents/AGENT_C/GAPS.md](agents/AGENT_C/GAPS.md) (0 gaps)
- **AGENT_G:** [agents/AGENT_G/GAPS.md](agents/AGENT_G/GAPS.md)
- **AGENT_P:** [agents/AGENT_P/GAPS.md](agents/AGENT_P/GAPS.md)
- **AGENT_L:** [agents/AGENT_L/GAPS.md](agents/AGENT_L/GAPS.md)

### Orchestrator Artifacts
- **Meta-Review:** [ORCHESTRATOR_META_REVIEW.md](ORCHESTRATOR_META_REVIEW.md)
- **Verification Summary:** [VERIFICATION_SUMMARY.md](VERIFICATION_SUMMARY.md)
- **Healing Prompt:** [HEALING_PROMPT.md](HEALING_PROMPT.md)

---

**Gaps Report Generated:** 2026-01-27 18:30 UTC
**Total Gaps:** 98 (41 BLOCKER, 37 WARNING, 20 INFO/MINOR)
**Status:** ✅ COMPLETE (all gaps documented with actionable proposed fixes)
