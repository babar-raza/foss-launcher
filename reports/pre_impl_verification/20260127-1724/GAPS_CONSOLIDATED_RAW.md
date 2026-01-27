# Requirements Gaps

**Agent**: AGENT_R
**Date**: 2026-01-27
**Total Gaps**: 12
**Classification**: 4 BLOCKER, 5 WARNING, 3 INFO

---

## Gap Classification

- **BLOCKER**: Missing requirement prevents implementation or causes ambiguity that could lead to incorrect implementation
- **WARNING**: Requirement exists but is ambiguous, incomplete, or conflicts with other requirements
- **INFO**: Minor clarification needed but implementation can proceed with reasonable assumptions

---

## BLOCKER Gaps

### R-GAP-001 | BLOCKER | Missing: Empty Input Handling for ProductFacts
**Evidence:** Implied by `specs/03_product_facts_and_evidence.md:178-183` but not explicitly stated
**Context:**
> **Zero evidence sources detected**:
> - If no README, docs, or code evidence can be extracted, emit telemetry warning `ZERO_EVIDENCE_SOURCES`
> - Proceed with minimal ProductFacts containing only:
>   - `product_name` (from repo name)
>   - `repo_url`, `repo_sha`
>   - `positioning.tagline`: "No documentation found"
>   - Empty `claims` array

**Gap:** The spec describes what to do when zero evidence is detected, but does NOT explicitly state whether this is a valid success state or should fail validation gates. Gate 9 (TruthLock) might fail with zero claims.

**Impact:** Uncertainty whether runs with zero evidence should succeed (with warnings) or fail. This affects launch tier selection and gate pass/fail logic.

**Proposed Fix:**
Add explicit requirement to `specs/03_product_facts_and_evidence.md`:
> **REQ-EDGE-001: Empty Evidence Acceptance Criteria**
> When zero evidence sources are detected:
> 1. The run MUST proceed (not fail immediately)
> 2. `launch_tier` MUST be forced to `minimal`
> 3. Gate 9 (TruthLock) MUST pass with zero claims (special case)
> 4. Gate 12 (Universality) MUST validate that only essential pages are planned (index + quickstart minimum)
> 5. Validation report MUST include MAJOR issue with error_code `FACTS_BUILDER_INSUFFICIENT_EVIDENCE`

---

### R-GAP-002 | BLOCKER | Ambiguous: Floating Ref Detection at Runtime vs Preflight
**Evidence:** `specs/34_strict_compliance_guarantees.md:59-85` describes runtime enforcement, but interaction with preflight Gate J is unclear
**Context:**
> **Gate**: `launch_validate` runtime check (in addition to Gate J preflight)
> **Purpose**: Reject runs that use floating refs at runtime (defense in depth)

**Gap:** Spec states runtime check is "in addition to Gate J preflight" but does NOT clarify:
1. If Gate J passes at preflight, can runtime check still fail?
2. If yes, what is the scenario (race condition? config tampering?)?
3. Should runtime check re-validate ALL *_ref fields or only validate final resolved refs?

**Impact:** Unclear whether runtime check duplicates preflight or catches new failure modes. Risk of redundant validation or missed edge cases.

**Proposed Fix:**
Add explicit requirement to `specs/34_strict_compliance_guarantees.md`:
> **REQ-GUARD-001: Runtime Floating Ref Check Scope**
> Runtime floating ref check (Guarantee A enforcement) SHALL:
> 1. Re-validate ALL `*_ref` fields in `run_config` at start of `launch_validate` call
> 2. Detect floating refs that may have been introduced via:
>    - Config file modification after preflight
>    - Run config passed directly to CLI/MCP (bypassing preflight)
>    - Race conditions in config loading
> 3. If floating ref detected: Terminate run immediately with error_code `POLICY_FLOATING_REF_DETECTED`
> 4. This is defense-in-depth; preflight Gate J remains primary enforcement point

---

### R-GAP-003 | BLOCKER | Missing: Hugo Config Fingerprinting Algorithm
**Evidence:** `specs/09_validation_gates.md:86-115` mentions "Hugo config fingerprints" but does NOT define how fingerprints are computed
**Context:**
> ### Gate 3: Hugo Config Compatibility
> **Validation Rules**:
> 1. All planned `(subdomain, family)` pairs MUST be enabled by Hugo configs
> 2. Every planned `output_path` MUST match content root contract
> 3. Hugo config MUST exist for all required sections
> 4. Content roots MUST match `site_layout.subdomain_roots` from run_config

**Gap:** Gate 3 validates Hugo config compatibility, and `site_context.json` stores "config fingerprints", but the spec does NOT define:
1. What fields are included in the fingerprint?
2. What hashing algorithm is used (sha256? md5?)?
3. How are multiple Hugo config files combined into a single fingerprint?
4. Are fingerprints stored per-subdomain or global?

**Impact:** Implementation cannot deterministically compute or validate Hugo config fingerprints. This breaks determinism for cache invalidation and validation.

**Proposed Fix:**
Add explicit requirement to `specs/31_hugo_config_awareness.md` (or create if missing):
> **REQ-HUGO-FP-001: Hugo Config Fingerprint Algorithm**
> Hugo config fingerprints SHALL be computed as follows:
> 1. For each Hugo config file in the site repo (hugo.toml, hugo.yaml, config.toml):
>    a. Read file contents as UTF-8 text
>    b. Normalize: strip comments, sort keys alphabetically, collapse whitespace
>    c. Compute `sha256(normalized_contents)`
> 2. Combine per-file hashes: `global_fingerprint = sha256(sorted([hash1, hash2, ...]))`
> 3. Store in `site_context.json` as:
>    - `hugo_config_fingerprint`: global fingerprint (string)
>    - `hugo_config_files[]`: array of {path, sha256} for each config file
> 4. Use fingerprint for cache invalidation: if fingerprint changes, invalidate all cached artifacts

---

### R-GAP-004 | BLOCKER | Missing: Max Fix Attempts Default Value
**Evidence:** Multiple specs mention `max_fix_attempts` but no spec defines the default value
**Context:**
- `specs/01_system_contract.md:158` states "capped by `max_fix_attempts`"
- `specs/08_patch_engine.md:110` states "bounded by `run_config.max_fix_attempts` (default 3)"
- `specs/09_validation_gates.md:505` mentions "Fix attempts must be capped (config)"

**Gap:** Two specs claim default is 3, but this is NOT stated in the authoritative run_config schema or system contract. Specs should not define defaults in examples; defaults belong in schemas or system contract.

**Impact:** Unclear whether default=3 is binding or just a suggestion. Could lead to inconsistent behavior if different workers use different defaults.

**Proposed Fix:**
Add explicit requirement to `specs/schemas/run_config.schema.json`:
```json
"max_fix_attempts": {
  "type": "integer",
  "default": 3,
  "minimum": 1,
  "maximum": 10,
  "description": "Maximum number of fix attempts per validation failure"
}
```

And add to `specs/01_system_contract.md`:
> **REQ-FIX-001: Fix Loop Attempts**
> Fix loops SHALL be capped at `run_config.max_fix_attempts` (default: 3, range: 1-10).
> After max attempts, the run MUST fail with error_code `FIXER_MAX_ATTEMPTS_EXCEEDED`.

---

## WARNING Gaps

### R-GAP-005 | WARNING | Ambiguous: "SHOULD" Requirements Without Enforcement
**Evidence:** Multiple specs use "SHOULD" but do NOT clarify enforcement or consequences of non-compliance
**Context:**
- `specs/10_determinism_and_caching.md:106` states "SHOULD implement pagination"
- `specs/14_mcp_endpoints.md:110` states "SHOULD implement request timeout"
- `specs/16_local_telemetry_api.md:133` states "SHOULD cache frequently accessed artifacts"

**Gap:** "SHOULD" is defined as "recommended" but specs do NOT clarify:
1. Are SHOULD requirements validated by gates?
2. Do violations produce warnings or are they silently ignored?
3. Are SHOULD requirements tracked in validation reports?

**Impact:** Implementers may skip SHOULD requirements without consequence, leading to degraded quality. Or implementers may treat SHOULD as MUST, leading to over-engineering.

**Proposed Fix:**
Add clarification to `specs/README.md` or `GLOSSARY.md`:
> **SHOULD Requirements Policy**
> - SHOULD = Recommended but not enforced by validation gates
> - Violations of SHOULD requirements MAY produce INFO-level issues in validation reports
> - SHOULD requirements MAY be upgraded to MUST in future spec versions if proven essential
> - Implementers SHOULD document why SHOULD requirements are not implemented (in code comments or design docs)

---

### R-GAP-006 | WARNING | Incomplete: Binary File Size Limits
**Evidence:** `specs/08_patch_engine.md:131` mentions "max_file_size (from ruleset)" but no ruleset defines this value
**Context:**
> **Large file handling**: If target file exceeds max_file_size (from ruleset), emit error_code `PATCH_ENGINE_FILE_TOO_LARGE`, open MAJOR issue, allow skip or fail per config.

**Gap:** Spec references `max_file_size` as coming "from ruleset", but:
1. No ruleset schema defines this field
2. No spec defines what constitutes a "large file" (1MB? 10MB? 100MB?)
3. No default value is provided

**Impact:** Implementation cannot enforce large file limits without arbitrary value choices.

**Proposed Fix:**
Add to `specs/schemas/ruleset.schema.json`:
```json
"max_file_size_bytes": {
  "type": "integer",
  "default": 10485760,
  "description": "Maximum size (bytes) for files that can be patched. Default: 10MB"
}
```

---

### R-GAP-007 | WARNING | Ambiguous: Contradiction Resolution Priority Difference Threshold
**Evidence:** `specs/03_product_facts_and_evidence.md:135-157` defines resolution algorithm but threshold logic is unclear
**Context:**
> 2. **Apply resolution rules**:
>    - If `priority_diff >= 2`: Automatically prefer higher-priority source
>    - If `priority_diff == 1`: Flag for manual review
>    - If `priority_diff == 0`: Cannot resolve automatically

**Gap:** The algorithm uses `priority_diff >= 2` for automatic resolution, but does NOT clarify:
1. Why is threshold 2 (not 1 or 3)?
2. Is this threshold configurable via run_config?
3. Can threshold vary by claim_kind (e.g., stricter for security claims)?

**Impact:** Fixed threshold may be too rigid for some contradiction scenarios. May lead to excessive manual reviews or incorrect auto-resolutions.

**Proposed Fix:**
Add to `specs/03_product_facts_and_evidence.md`:
> **REQ-CONTRA-001: Contradiction Resolution Threshold**
> Priority difference threshold for automatic resolution SHALL default to 2.
> Rationale: Priority diff >=2 ensures clear evidence superiority (e.g., manifest vs marketing text).
> The threshold is NOT configurable to maintain determinism across runs.

---

### R-GAP-008 | WARNING | Missing: Telemetry Outbox Maximum Retry Interval
**Evidence:** `specs/16_local_telemetry_api.md:149-154` defines retry policy but does NOT specify maximum backoff interval
**Context:**
> Retry telemetry POSTs with exponential backoff:
> - Max attempts: 3 per payload
> - Backoff: 1s, 2s, 4s (no jitter needed for non-critical path)
> - Timeout: 10s per POST attempt

**Gap:** Backoff sequence is 1s, 2s, 4s, but spec does NOT clarify:
1. Is this the complete sequence for 3 attempts (total wait: 7s)?
2. Or should backoff continue exponentially (1s, 2s, 4s, 8s, 16s...)?
3. Is there a maximum backoff cap (e.g., 60s)?

**Impact:** Ambiguity could lead to unbounded wait times if implementer misinterprets as "exponential to infinity".

**Proposed Fix:**
Clarify in `specs/16_local_telemetry_api.md`:
> **REQ-TELEM-001: Retry Backoff Sequence**
> Retry backoff SHALL be: 1s before attempt 2, 2s before attempt 3.
> Total retry time: 3s (1s + 2s) for 3 attempts.
> No additional backoff after attempt 3; payload remains in outbox.

---

### R-GAP-009 | WARNING | Incomplete: Snippet Validation Failure Thresholds
**Evidence:** `specs/05_example_curation.md:42-48` defines syntax validation failure handling but no threshold for "too many failures"
**Context:**
> On syntax validation failure:
> 1. Mark snippet with `validation.syntax_ok=false`
> 2. Write validation error output to `validation_log_path`
> 3. Do NOT include snippet in catalog if `forbid_invalid_snippets=true`
> 4. If `forbid_invalid_snippets=false`, include snippet with clear warning annotation

**Gap:** Spec does NOT define:
1. If 50% of snippets fail syntax validation, should the run fail?
2. Is there a minimum viable snippet count (e.g., must have at least 1 valid snippet)?
3. Does high snippet failure rate affect launch_tier selection?

**Impact:** Runs might succeed with zero valid snippets, producing low-quality pages.

**Proposed Fix:**
Add to `specs/05_example_curation.md`:
> **REQ-SNIP-001: Snippet Validation Thresholds**
> If snippet syntax validation fails for >80% of discovered snippets:
> 1. Emit telemetry warning `SNIPPET_VALIDATION_MOSTLY_FAILED`
> 2. Force `launch_tier=minimal`
> 3. Open MAJOR issue with error_code `SNIPPET_CURATOR_HIGH_FAILURE_RATE`
> If ALL snippets fail validation:
> 1. Emit telemetry warning `SNIPPET_VALIDATION_ALL_FAILED`
> 2. Proceed with zero snippets (generated snippets may be used if allowed)

---

## INFO Gaps

### R-GAP-010 | INFO | Missing: RUN_ID Format Specification
**Evidence:** `specs/16_local_telemetry_api.md:69-74` recommends run_id format but does NOT make it binding
**Context:**
> Recommended:
> - `run_id = <utc_start_iso>-launch-<product_slug>-<github_ref_short>-<site_ref_short>`
> - child run_id = `<parent_run_id>-<work_kind>-<stable_work_id>`

**Gap:** Format is recommended but NOT required. Spec does NOT define:
1. Maximum run_id length (filesystem constraints)?
2. Allowed characters (alphanumeric + hyphens only)?
3. Is the format binding or can implementers choose different formats?

**Impact:** Minor. Different run_id formats could complicate log analysis but won't break functionality.

**Proposed Fix:**
Add to `specs/16_local_telemetry_api.md`:
> **REQ-RUNID-001: Run ID Format (Binding)**
> `run_id` SHALL match pattern: `^[a-zA-Z0-9_-]{8,128}$`
> Recommended format: `<utc_start_iso>-launch-<product_slug>-<github_ref_short>-<site_ref_short>`
> Maximum length: 128 characters (filesystem + database compatibility)

---

### R-GAP-011 | INFO | Clarification Needed: "Stable Prompts" Definition
**Evidence:** `specs/10_determinism_and_caching.md:7` mentions "stable prompts and prompt hashing" but does NOT define stability requirements
**Context:**
> - stable prompts and prompt hashing

**Gap:** Spec does NOT clarify:
1. What makes a prompt "stable" (immutable text? versioned templates? locked dependencies?)?
2. Are prompt templates allowed to use dynamic variables (product name, date)?
3. If prompt text changes, must prompt_version be updated?

**Impact:** Minor. Implementers may create non-deterministic prompts without realizing it.

**Proposed Fix:**
Add to `specs/10_determinism_and_caching.md`:
> **REQ-PROMPT-001: Stable Prompt Definition**
> A prompt is "stable" when:
> 1. Template text is versioned (locked to ruleset_version/templates_version)
> 2. Dynamic variables are limited to: product_name, locale, platform (no timestamps, random values)
> 3. Prompt hash includes: template text + schema version + worker version
> 4. Prompt text changes require prompt_version increment

---

### R-GAP-012 | INFO | Missing: Network Allowlist Example Entries
**Evidence:** `specs/34_strict_compliance_guarantees.md:144` requires `config/network_allowlist.yaml` but does NOT provide example entries
**Context:**
> **Allowlist file**: `config/network_allowlist.yaml`

**Gap:** Spec does NOT provide:
1. Example allowlist entries (github.com, api.openai.com, localhost)?
2. Format of allowlist file (YAML array of strings? regex patterns?)?
3. Wildcard support (*.github.com)?

**Impact:** Minor. Implementers must infer allowlist format from context.

**Proposed Fix:**
Add example to `specs/34_strict_compliance_guarantees.md`:
```yaml
# config/network_allowlist.yaml (example)
allowed_hosts:
  - "localhost"
  - "127.0.0.1"
  - "api.openai.com"
  - "github.com"
  - "*.github.com"  # wildcard for subdomains
  - "aspose.org"
```

---

## Summary

**Total Gaps**: 12
- **BLOCKER**: 4 (prevent implementation without clarification)
- **WARNING**: 5 (ambiguities that could lead to incorrect implementation)
- **INFO**: 3 (minor clarifications to improve spec quality)

**Recommended Action**:
1. Address BLOCKER gaps before implementation proceeds
2. Clarify WARNING gaps in spec updates or implementation notes
3. INFO gaps can be resolved opportunistically during implementation

---

## Gap Resolution Tracking

| Gap ID | Status | Assigned To | Resolution ETA |
|--------|--------|-------------|----------------|
| R-GAP-001 | OPEN | TBD | TBD |
| R-GAP-002 | OPEN | TBD | TBD |
| R-GAP-003 | OPEN | TBD | TBD |
| R-GAP-004 | OPEN | TBD | TBD |
| R-GAP-005 | OPEN | TBD | TBD |
| R-GAP-006 | OPEN | TBD | TBD |
| R-GAP-007 | OPEN | TBD | TBD |
| R-GAP-008 | OPEN | TBD | TBD |
| R-GAP-009 | OPEN | TBD | TBD |
| R-GAP-010 | OPEN | TBD | TBD |
| R-GAP-011 | OPEN | TBD | TBD |
| R-GAP-012 | OPEN | TBD | TBD |

---

**Gap Analysis Completed**: 2026-01-27 17:24 UTC
**Confidence**: High (8/10)
**Next Steps**: Triage gaps with spec authors and update binding specs
# Feature Validation Gaps

This document catalogs all gaps identified during AGENT_F feature validation.

**Generation Date**: 2026-01-27
**Agent**: AGENT_F
**Total Gaps Identified**: 25

**Severity Breakdown:**
- **BLOCKER**: 3 (implementation blockers preventing full validation)
- **WARNING**: 5 (testability or reproducibility concerns)
- **MINOR**: 17 (documentation gaps, missing ADRs, or missing test fixtures)

---

## BLOCKER Gaps

### F-GAP-021 | BLOCKER | Runtime Secret Redaction Not Implemented
**Feature:** FEAT-030 (Secret Redaction - Guarantee E)
**Evidence:** `plans/traceability_matrix.md:284` states "Gate L implemented preflight scan only; runtime redaction PENDING"
**Impact:** Secrets may leak in runtime logs/artifacts/reports despite preflight scan passing
**Root Cause:** TC-590 (security and secrets) not started
**Proposed Fix:**
1. Implement runtime redaction utilities in `src/launch/util/redaction.py` or `src/launch/util/logging.py`
2. Integrate redaction into all logging statements (use logging filters)
3. Scan `runs/**/logs/**` and `runs/**/reports/**` post-run
4. Add tests in `tests/unit/util/test_redaction.py`
5. Evidence: `specs/34_strict_compliance_guarantees.md:173-187` (secret patterns, redaction rules)

**Acceptance Criteria:**
- All secret patterns redacted to `***REDACTED***` in logs
- Post-run scan detects zero leaked secrets
- Tests verify redaction for all patterns in `specs/34_strict_compliance_guarantees.md:173-178`

---

### F-GAP-022 | BLOCKER | Rollback Metadata Generation Not Implemented
**Feature:** FEAT-036 (Rollback Metadata Validation - Guarantee L)
**Evidence:** `plans/traceability_matrix.md:492` states "TC-480 not started"
**Impact:** Cannot validate Guarantee L (rollback contract) until PRManager implemented
**Root Cause:** TC-480 (PRManager W9) not started
**Proposed Fix:**
1. Implement TC-480 PRManager per `specs/21_worker_contracts.md:322-351`
2. Generate `pr.json` with rollback fields: `base_ref`, `run_id`, `rollback_steps`, `affected_paths`
3. Validate `pr.json` against `specs/schemas/pr.schema.json`
4. Integrate Gate 13 runtime validation per `specs/09_validation_gates.md:430-468`
5. Add tests in `tests/integration/test_pr_manager.py`

**Acceptance Criteria:**
- `pr.json` artifact exists with all required rollback fields
- Gate 13 passes in prod profile
- Rollback steps are executable and accurate

---

### F-GAP-023 | BLOCKER | LangGraph Orchestrator Not Implemented
**Feature:** FEAT-038 (LangGraph Orchestrator State Machine)
**Evidence:** `plans/traceability_matrix.md:30` states "TC-300 not started"
**Impact:** Cannot execute full pipeline end-to-end; all MCP tools depend on orchestrator
**Root Cause:** TC-300 (orchestrator) not started
**Proposed Fix:**
1. Implement TC-300 orchestrator per `specs/state-graph.md:1-150`
2. Define LangGraph state machine with nodes for W1-W9
3. Implement state transitions per `specs/28_coordination_and_handoffs.md:1-100`
4. Integrate with MCP tools per `specs/14_mcp_endpoints.md:8-17`
5. Add orchestrator integration tests per `plans/traceability_matrix.md:30`

**Acceptance Criteria:**
- Orchestrator executes full W1→W9 pipeline
- State transitions deterministic per `specs/10_determinism_and_caching.md:39-46`
- MCP tools invoke orchestrator successfully
- Integration tests pass (graph smoke tests, transition determinism)

---

## WARNING Gaps

### F-GAP-008 | WARNING | Template Rendering Reproducibility Conditional on LLM Determinism
**Feature:** FEAT-011 (Section Template Rendering)
**Evidence:** `specs/10_determinism_and_caching.md:4-9` enforces temperature=0.0, but LLM-based rendering may have variance
**Impact:** Byte-identical outputs not guaranteed across LLM providers
**Proposed Fix:**
1. Add determinism tests in TC-560 harness comparing outputs across runs
2. If variance detected, implement stricter prompt templates or structured output constraints
3. Document LLM provider compatibility matrix (which providers support byte-identical outputs)
4. Evidence: `specs/10_determinism_and_caching.md:80-106` (prompt versioning helps detect drift)

**Acceptance Criteria:**
- TC-560 determinism harness validates template rendering produces byte-identical outputs
- If variance > 0%, document which LLM providers are deterministic
- Prompt versioning tracks all template prompts

---

### F-GAP-011 | WARNING | Missing Test Fixtures for Patch Conflict Scenarios
**Feature:** FEAT-014 (Patch Idempotency and Conflict Detection)
**Evidence:** `specs/08_patch_engine.md:71-144` documents conflict detection algorithm, but no explicit test fixtures found
**Impact:** Cannot validate conflict detection logic without test cases
**Proposed Fix:**
1. Create test fixtures in `tests/fixtures/patch_conflicts/`
2. Test cases:
   - Anchor not found: file missing target heading
   - Line range out of bounds: patch targets line 100 in 50-line file
   - Content mismatch: expected content hash doesn't match actual
   - Path outside allowed_paths: patch targets forbidden path
3. Add tests in `tests/unit/patch_engine/test_conflict_detection.py`

**Acceptance Criteria:**
- All 5 conflict categories have test fixtures
- Conflict detection tests pass
- Edge cases documented in `specs/08_patch_engine.md:119-139`

---

### F-GAP-012 | WARNING | Fix Loop Reproducibility Conditional on LLM Determinism
**Feature:** FEAT-016 (Validation Fix Loop)
**Evidence:** `specs/21_worker_contracts.md:309-310` requires no new factual claims, but LLM-based fixes may vary
**Impact:** Fix attempts may produce different patches across runs
**Proposed Fix:**
1. Add fix loop tests in TC-560 determinism harness
2. If variance detected, implement stricter fix templates (similar to FEAT-011 solution)
3. Document which fix types are deterministic vs LLM-dependent
4. Evidence: `specs/08_patch_engine.md:98-107` (three-way merge with manual review fallback)

**Acceptance Criteria:**
- TC-560 validates fix loop produces consistent patches
- If variance > 0%, document non-deterministic fix scenarios
- Max fix attempts prevent infinite loops per `specs/01_system_contract.md:158`

---

### F-GAP-017 | WARNING | MCP Inference Algorithm Not Pilot-Validated
**Feature:** FEAT-020 (MCP Quickstart from GitHub Repo URL)
**Evidence:** `specs/adr/001_inference_confidence_threshold.md:21-30` pilot validation plan not yet executed
**Impact:** 80% confidence threshold may produce false positives (incorrect inference) or false negatives (unnecessary ambiguity)
**Proposed Fix:**
1. Execute ADR-001 pilot validation plan per `specs/adr/001_inference_confidence_threshold.md:21-30`
2. Test with 20+ representative repos (Python, .NET, Node, Java, multi-product)
3. Measure false positive rate (<5% target) and false negative rate
4. Tune threshold (80% → 85% or 90%) if false positive rate >5%
5. Document validated threshold in ADR-001

**Acceptance Criteria:**
- 20+ repos tested
- False positive rate <5%
- False negative rate documented
- Threshold validated or tuned

---

### F-GAP-024 | WARNING | Caching Implementation Status Unclear
**Feature:** FEAT-039 (Caching with Content Hashing)
**Evidence:** `specs/10_determinism_and_caching.md:30-38` defines caching strategy, but no taskcard references found
**Impact:** Unclear if caching is implemented; may impact performance and determinism validation
**Proposed Fix:**
1. Verify caching implementation status (search for cache_key usage in codebase)
2. If not implemented, create taskcard for caching implementation
3. If implemented, document in traceability matrix
4. Add caching tests in TC-560 (cache hits/misses, key computation)

**Acceptance Criteria:**
- Caching implementation status documented
- If implemented: tests verify cache_key formula `sha256(model_id + "|" + prompt_hash + "|" + inputs_hash)`
- If not implemented: taskcard created

---

## MINOR Gaps (Documentation/ADR/Fixtures)

### F-GAP-001 | MINOR | Missing Fixtures for .NET/Node/Java Adapters
**Feature:** FEAT-002 (Repository Adapter Selection)
**Evidence:** `specs/pilots/` contains only Python pilots (pilot-aspose-3d-foss-python, pilot-aspose-note-foss-python)
**Impact:** Adapter selection logic for .NET/Node/Java untested
**Proposed Fix:** Add pilot configs for .NET, Node, Java repos in `specs/pilots/`

---

### F-GAP-002 | MINOR | No Explicit Acceptance Tests for Adapter Selection Logic
**Feature:** FEAT-002 (Repository Adapter Selection)
**Evidence:** `plans/acceptance_test_matrix.md:37` covers deterministic fingerprints, but no explicit adapter selection tests
**Impact:** Adapter selection implicitly tested, but not explicitly validated
**Proposed Fix:** Add adapter selection tests to `plans/acceptance_test_matrix.md` or TC-520 pilots

---

### F-GAP-003 | MINOR | Missing Explicit Test Fixtures with Known Frontmatter Patterns
**Feature:** FEAT-003 (Frontmatter Contract Discovery)
**Evidence:** `specs/templates/` contain frontmatter examples, but no explicit test fixtures with known expected contracts
**Impact:** Frontmatter discovery implicitly tested via pilots, but edge cases not validated
**Proposed Fix:** Create test fixtures in `tests/fixtures/frontmatter_discovery/` with known schemas

---

### F-GAP-004 | MINOR | No ADR for Facts Extraction Methodology (LLM vs Rule-Based)
**Feature:** FEAT-005 (Product Facts Extraction)
**Evidence:** No ADR found documenting why LLM-based extraction vs rule-based parsing
**Impact:** Design rationale not documented; future implementers may question approach
**Proposed Fix:** Create ADR documenting LLM-based extraction choice (likely: universality, adaptability)

---

### F-GAP-005 | MINOR | No ADR for Snippet Extraction Methodology (Parse-Only vs Execute)
**Feature:** FEAT-008 (Snippet Extraction and Curation)
**Evidence:** No ADR found documenting why parse-only vs execution-based extraction
**Impact:** Design rationale implicit in Guarantee J (untrusted code), but not explicit ADR
**Proposed Fix:** Create ADR linking snippet extraction to Guarantee J (security rationale)

---

### F-GAP-006 | MINOR | No ADR for Page Planning Methodology (Plan-First vs Incremental)
**Feature:** FEAT-009 (Page Planning with Template Selection)
**Evidence:** No ADR found documenting why plan-first vs incremental page generation
**Impact:** Design rationale implicit in `specs/06_page_planning.md:10-25`, but not explicit ADR
**Proposed Fix:** Create ADR documenting plan-first benefits (validation before writing, parallelization)

---

### F-GAP-007 | MINOR | No ADR for V2 Layout Design Rationale
**Feature:** FEAT-010 (Platform-Aware Content Layout V2)
**Evidence:** No ADR found documenting why `/{locale}/{platform}/` path structure vs alternatives
**Impact:** Design rationale implicit in existing Aspose sites, but not documented
**Proposed Fix:** Create ADR documenting V2 layout benefits (cross-platform consistency, Hugo config alignment)

---

### F-GAP-009 | MINOR | No Explicit Acceptance Tests for Template Rendering
**Feature:** FEAT-011 (Section Template Rendering)
**Evidence:** `plans/acceptance_test_matrix.md:49-50` covers W5/W6 patches, but no explicit template rendering tests
**Impact:** Template rendering implicitly tested, but not explicitly validated
**Proposed Fix:** Add template rendering tests to acceptance matrix or TC-560

---

### F-GAP-010 | MINOR | Missing Explicit Test Fixtures with Claim Markers
**Feature:** FEAT-012 (Claim Marker Insertion)
**Evidence:** `specs/23_claim_markers.md` defines format, but no explicit test fixtures with expected claim markers
**Impact:** Claim marker insertion implicitly tested via Gate 9, but edge cases not validated
**Proposed Fix:** Create test fixtures in `tests/fixtures/claim_markers/` with expected markers

---

### F-GAP-013 | MINOR | Missing Explicit Test Fixtures for Fix Scenarios
**Feature:** FEAT-016 (Validation Fix Loop)
**Evidence:** `specs/08_patch_engine.md:98-114` documents fix strategies, but no explicit test fixtures
**Impact:** Fix loop implicitly tested, but specific fix scenarios not validated
**Proposed Fix:** Create test fixtures in `tests/fixtures/fix_scenarios/` (markdown lint fixes, frontmatter fixes, etc.)

---

### F-GAP-014 | MINOR | Missing Explicit Test Fixtures for PR Creation
**Feature:** FEAT-017 (PR Creation with Rollback Metadata)
**Evidence:** `specs/12_pr_and_release.md` defines PR template, but no explicit test fixtures
**Impact:** PR creation implicitly tested via pilots, but edge cases not validated
**Proposed Fix:** Create test fixtures in `tests/fixtures/pr_creation/` with expected PR bodies

---

### F-GAP-015 | MINOR | No ADR for MCP vs Other API Protocols
**Feature:** FEAT-018 (MCP Server with 10+ Tools)
**Evidence:** No ADR found documenting why MCP vs REST API vs gRPC
**Impact:** Design rationale implicit in MCP being agent-standard, but not documented
**Proposed Fix:** Create ADR documenting MCP choice (agent ecosystem, tool calling standard)

---

### F-GAP-016 | MINOR | Missing Explicit Acceptance Tests for URL Parsing Logic
**Feature:** FEAT-019 (MCP Quickstart from Product URL)
**Evidence:** `specs/24_mcp_tool_schemas.md:138-143` defines URL patterns, but no explicit parsing tests
**Impact:** URL parsing implicitly tested via MCP E2E (TC-523), but pattern edge cases not validated
**Proposed Fix:** Add URL parsing tests to TC-523 or create unit tests in `tests/unit/mcp/test_url_parsing.py`

---

### F-GAP-018 | MINOR | No ADR for LLM Provider Abstraction Approach
**Feature:** FEAT-022 (LLM Provider Abstraction)
**Evidence:** No ADR found documenting why OpenAI-compatible vs multi-provider SDKs
**Impact:** Design rationale implicit in LangChain usage, but not explicit ADR
**Proposed Fix:** Create ADR documenting OpenAI-compatible choice (may be implicit in LangChain)

---

### F-GAP-019 | MINOR | get_telemetry MCP Tool Schema Missing
**Feature:** FEAT-023 (Local Telemetry API)
**Evidence:** `specs/14_mcp_endpoints.md:92` mentions get_telemetry tool, but schema not in `specs/24_mcp_tool_schemas.md`
**Impact:** MCP callability incomplete (tool mentioned but not schema-defined)
**Proposed Fix:** Add get_telemetry schema to `specs/24_mcp_tool_schemas.md`

---

### F-GAP-020 | MINOR | Missing Explicit Test Fixtures for Commit Service Calls
**Feature:** FEAT-024 (GitHub Commit Service)
**Evidence:** `specs/17_github_commit_service.md` defines request/response, but no explicit test fixtures
**Impact:** Commit service implicitly tested via pilots, but edge cases not validated
**Proposed Fix:** Create test fixtures in `tests/fixtures/commit_service/` with mock requests/responses

---

### F-GAP-025 | MINOR | Prompt Versioning Implementation Status Unclear
**Feature:** FEAT-040 (Prompt Versioning for Determinism)
**Evidence:** `specs/10_determinism_and_caching.md:80-106` defines requirement, but no taskcard references found
**Impact:** Unclear if prompt versioning is implemented; critical for determinism validation
**Proposed Fix:**
1. Verify prompt versioning implementation (search for prompt_version in codebase)
2. If not implemented, create taskcard for prompt versioning
3. If implemented, document in traceability matrix
4. Add prompt versioning tests in TC-560

---

## Gap Summary by Category

### Implementation Gaps (BLOCKER)
- **F-GAP-021**: Runtime secret redaction (TC-590)
- **F-GAP-022**: Rollback metadata generation (TC-480)
- **F-GAP-023**: LangGraph orchestrator (TC-300)

### Testability Gaps (WARNING)
- **F-GAP-008**: Template rendering reproducibility (LLM determinism)
- **F-GAP-011**: Patch conflict test fixtures
- **F-GAP-012**: Fix loop reproducibility (LLM determinism)
- **F-GAP-017**: MCP inference algorithm pilot validation
- **F-GAP-024**: Caching implementation status

### Documentation Gaps (MINOR)
- **ADR Gaps**: F-GAP-004, F-GAP-005, F-GAP-006, F-GAP-007, F-GAP-015, F-GAP-018 (6 missing ADRs)
- **Test Fixture Gaps**: F-GAP-001, F-GAP-003, F-GAP-010, F-GAP-011, F-GAP-013, F-GAP-014, F-GAP-020 (7 missing fixtures)
- **Acceptance Test Gaps**: F-GAP-002, F-GAP-009, F-GAP-016 (3 implicit tests needing explicit coverage)
- **Schema Gaps**: F-GAP-019 (1 missing MCP tool schema)
- **Status Unclear**: F-GAP-024, F-GAP-025 (2 features with unclear implementation status)

---

## Prioritized Remediation Plan

### Phase 1: Blockers (Required for Implementation)
1. **F-GAP-023**: Implement TC-300 orchestrator (highest priority)
2. **F-GAP-022**: Implement TC-480 PRManager with rollback metadata
3. **F-GAP-021**: Implement TC-590 runtime secret redaction

### Phase 2: Testability Warnings (Required for Validation)
1. **F-GAP-024**: Verify caching implementation status
2. **F-GAP-025**: Verify prompt versioning implementation status
3. **F-GAP-017**: Execute ADR-001 pilot validation for MCP inference
4. **F-GAP-011**: Create patch conflict test fixtures
5. **F-GAP-008, F-GAP-012**: Add LLM determinism tests to TC-560

### Phase 3: Documentation Gaps (Quality Improvements)
1. Create 6 missing ADRs (F-GAP-004/005/006/007/015/018)
2. Create 7 missing test fixture sets
3. Add 3 explicit acceptance tests
4. Add get_telemetry MCP tool schema (F-GAP-019)

---

## Overall Gap Assessment

**Critical Path Blockers:** 3 (TC-300, TC-480, TC-590)
**Testability Concerns:** 5 (LLM determinism, pilot validation, implementation status)
**Quality Improvements:** 17 (ADRs, test fixtures, explicit tests)

**Pre-Implementation Readiness:** ⚠ **CONDITIONAL**
- **Specs are sufficient:** ✅ Yes (all features well-defined)
- **Features are testable:** ⚠ Mostly (3 BLOCKER implementation gaps, 5 WARNING testability concerns)
- **Design rationale documented:** ⚠ Partial (6 missing ADRs)
- **Implementation can proceed:** ⚠ Yes, but blockers (TC-300, TC-480, TC-590) must be addressed first

**Recommendation:** Address 3 BLOCKER implementation gaps before full implementation. Testability warnings can be addressed in parallel. Documentation gaps are lower priority.
# Specs Quality Gaps

This document records all spec quality issues discovered during the AGENT_S audit of binding specifications.

## Summary

- **Total Gaps Identified**: 24
- **BLOCKER**: 8
- **WARNING**: 16
- **Specs Audited**: 34 binding specs

---

## S-GAP-001 | BLOCKER | Missing Error Code: Unfilled Template Tokens

**Spec File:** `specs/21_worker_contracts.md:223`
**Issue:** W5 SectionWriter specifies "emit error_code `SECTION_WRITER_UNFILLED_TOKENS`" but this error code is not defined in the error code registry in specs/01_system_contract.md
**Evidence:**
> If draft contains unreplaced `__TOKEN__` after rendering, emit error_code `SECTION_WRITER_UNFILLED_TOKENS`, open BLOCKER issue, halt run

**Impact:** Implementers cannot determine the correct error code format. System contract requires all error codes to follow `{COMPONENT}_{ERROR_TYPE}_{SPECIFIC}` pattern, but `SECTION_WRITER_UNFILLED_TOKENS` does not match any defined ERROR_TYPE.

**Proposed Fix:** Add to specs/01_system_contract.md error types section:
- `TOKEN` - Template token or placeholder errors
Or update error code to: `SECTION_WRITER_INVARIANT_UNFILLED_TOKENS`

---

## S-GAP-002 | WARNING | Vague Language: "Best effort" in Adapter Contract

**Spec File:** `specs/26_repo_adapters_and_variability.md:50-59`
**Issue:** Spec uses vague language "best effort, without guessing" when describing adapter outputs
**Evidence:**
> Each adapter MUST produce (best effort, without guessing):
> - ProductFacts.distribution
> - ProductFacts.runtime_requirements
> ...
> If any field cannot be determined, omit it or leave it empty rather than fabricate it.

**Impact:** "Best effort" is not operationally clear - implementers cannot determine when they have tried "hard enough" vs when to give up. This breaks determinism (two implementers may interpret differently).

**Proposed Fix:** Replace with:
> Each adapter MUST attempt to extract the following fields using deterministic heuristics defined in the adapter implementation guide. If extraction fails after applying all defined heuristics, the adapter MUST omit the field or set it to null with a note explaining why extraction failed.

---

## S-GAP-003 | BLOCKER | Missing Spec: spec_ref Field Definition

**Spec File:** `specs/34_strict_compliance_guarantees.md:377-385`
**Issue:** Guarantee K requires `spec_ref` field in taskcards and run configs but no spec defines what this field means or how to compute it
**Evidence:**
> **Required fields**:
> - Taskcards: `spec_ref` (commit SHA of spec pack), `ruleset_version`, `templates_version`
> - Run configs: `ruleset_version`, `templates_version`
>
> **Canonical values**:
> - `spec_ref: "<commit_sha>"` (obtained via `git rev-parse HEAD`)

**Impact:** Unclear if `spec_ref` is the commit SHA of the launcher repo, the spec pack folder, or something else. "obtained via `git rev-parse HEAD`" is ambiguous (HEAD of which repo?).

**Proposed Fix:** Add to specs/01_system_contract.md or specs/34_strict_compliance_guarantees.md:
> `spec_ref` SHALL be the commit SHA of the launcher implementation repository at the time the run config or taskcard was created. It MUST be obtained via `git rev-parse HEAD` executed from the launcher repository root.

---

## S-GAP-004 | WARNING | Ambiguous Term: "Stable ordering everywhere"

**Spec File:** `specs/10_determinism_and_caching.md:39-46`
**Issue:** Spec uses "stable ordering everywhere" but does not define "stable" precisely
**Evidence:**
> ## Stable ordering rules
> - Sort all lists deterministically:
>   - paths lexicographically
>   - sections in config order
>   - pages by `(section_order, output_path)`
>   - issues by `(severity_rank, gate, location.path, location.line, issue_id)`
>   - claims by `claim_id`
>   - snippets by `(language, tag, snippet_id)`

**Impact:** "Lexicographically" is ambiguous (case-sensitive? locale-sensitive? ASCII vs UTF-8?). Different implementations may sort differently.

**Proposed Fix:** Add precision:
> - paths: lexicographically using Python `sorted()` with default locale (case-sensitive ASCII ordering)
> - All sorting MUST use deterministic, locale-independent comparison (no `locale.strcoll()`)

---

## S-GAP-005 | BLOCKER | Missing Timeout: Fixer Worker Timeout

**Spec File:** `specs/21_worker_contracts.md:290-320`
**Issue:** W8 Fixer worker contract does not specify timeout value, but specs/28_coordination_and_handoffs.md requires all workers to have timeouts
**Evidence:**
> **Binding requirements**:
> - MUST fix exactly one issue: the issue_id supplied by the Orchestrator.
> - MUST obey gate-specific fix rules in `specs/08_patch_engine.md`.
> (no timeout mentioned)

**Impact:** Implementers cannot determine when to abort a fixer worker that hangs. This violates the resource limits requirement in specs/28_coordination_and_handoffs.md.

**Proposed Fix:** Add to W8 Fixer binding requirements:
> - Timeout: 300s (5 minutes) per fix attempt
> - If timeout exceeded, emit error_code `FIXER_TIMEOUT`, mark as retryable

---

## S-GAP-006 | WARNING | Contradicting Evidence Priority

**Spec File:** `specs/03_product_facts_and_evidence.md:97-110` vs `specs/03_product_facts_and_evidence.md:57-65`
**Issue:** Two different evidence priority orderings exist in the same spec
**Evidence (first):**
> When the same fact appears in multiple places, prefer evidence in this order:
> 1) Machine-readable manifests
> 2) Source code
> 3) Tests
> 4) Docs and implementation notes
> 5) README/marketing text

**Evidence (second):**
> For precise contradiction resolution, use this fine-grained ranking (1 = highest):
> | Priority | Source Type |
> | 1 | **Manifests** |
> | 2 | **Source code constants** |
> | 3 | **Test assertions** |
> | 4 | **Implementation docs** |
> | 5 | **API docstrings** |
> | 6 | **README technical** |
> | 7 | **README marketing** |

**Impact:** The fine-grained table splits "README" into two levels and adds "API docstrings" which is not in the first list. Implementers cannot determine which to use.

**Proposed Fix:** Remove the first (coarse) list and keep only the fine-grained table, or clearly state that the table is the authoritative expansion of the first list.

---

## S-GAP-007 | WARNING | Missing Failure Mode: Hugo Config Missing

**Spec File:** `specs/09_validation_gates.md:86-115` (Gate 3: Hugo Config Compatibility)
**Issue:** Gate 3 specifies error codes for config mismatches but not for when Hugo config files are completely missing
**Evidence:**
> **Error Codes**:
> - `GATE_HUGO_CONFIG_MISSING`: Hugo config missing for section
> - `GATE_HUGO_CONFIG_PATH_MISMATCH`: Output path doesn't match contract
> - `GATE_HUGO_CONFIG_SUBDOMAIN_NOT_ENABLED`: Subdomain not enabled in config

**Impact:** `GATE_HUGO_CONFIG_MISSING` is defined but the validation rules don't specify what happens when NO Hugo config files exist (e.g., corrupted site repo clone).

**Proposed Fix:** Add to Validation Rules:
> 0. If NO Hugo config files found in `RUN_DIR/work/site/configs/`, fail immediately with error_code `GATE_HUGO_CONFIG_NOT_FOUND` (BLOCKER)

---

## S-GAP-008 | BLOCKER | Missing Determinism: URL Collision Tie-Breaking

**Spec File:** `specs/33_public_url_mapping.md:249-256`
**Issue:** URL collision detection specifies to open a BLOCKER but does not specify tie-breaking rules if collision is intentional (e.g., index.md and _index.md)
**Evidence:**
> ### Collision Detection
> After computing all `url_path` values in `page_plan.pages[]`:
> 1. Build map: `url_path → [output_path]`
> 2. If any `url_path` has multiple `output_path` entries:
>    - Open BLOCKER issue with error_code `IA_PLANNER_URL_COLLISION`

**Impact:** Hugo allows both `_index.md` and `index.md` in some cases (section index vs leaf bundle). Spec does not define which to prefer or how to detect intentional vs accidental collisions.

**Proposed Fix:** Add collision resolution algorithm:
> 3. Collision resolution order (prefer first match):
>    a. If one path is `_index.md` and other is `<slug>/index.md`, prefer `_index.md` (section index)
>    b. If both are `_index.md` at different depths, prefer shallower path
>    c. Otherwise, fail with BLOCKER (unresolvable collision)

---

## S-GAP-009 | WARNING | Vague Language: "Minimal change" in Fixer Contract

**Spec File:** `specs/21_worker_contracts.md:291`
**Issue:** W8 Fixer goal uses vague language "minimal change"
**Evidence:**
> **Goal:** apply the minimal change required to fix exactly one selected issue.

**Impact:** "Minimal" is not operationally defined. Implementers cannot determine if a 5-line fix is "minimal" compared to a 50-line fix if both resolve the issue.

**Proposed Fix:** Replace with:
> **Goal:** apply the smallest diff (by line count) required to fix exactly one selected issue. If multiple solutions exist, prefer the solution with fewest lines changed.

---

## S-GAP-010 | WARNING | Missing Edge Case: Empty RepoInventory

**Spec File:** `specs/02_repo_ingestion.md:1-295`
**Issue:** Spec does not define behavior when `repo_inventory.file_tree` is empty (zero files in repo)
**Evidence:**
(specs/21_worker_contracts.md:86 mentions "Empty repository" edge case for W1 RepoScout, but base spec 02 does not define it)

**Impact:** Unclear if empty repo_inventory should proceed to facts building or fail immediately. Different workers may handle differently.

**Proposed Fix:** Add to specs/02_repo_ingestion.md section 1 (Clone and fingerprint):
> - If cloned repo contains zero files (empty repo), emit telemetry `REPO_SCOUT_EMPTY_REPO`, proceed with minimal repo_inventory containing only repo_url and repo_sha, and open MAJOR issue with error_code `REPO_SCOUT_EMPTY_REPOSITORY`.

---

## S-GAP-011 | BLOCKER | Missing Schema Version Compatibility Policy

**Spec File:** `specs/28_coordination_and_handoffs.md:184-191`
**Issue:** Schema version compatibility section defines version checking but does not define the version format (semver? date-based?)
**Evidence:**
> All artifacts MUST include `schema_version` field.
> Workers MUST check `schema_version` compatibility before consuming artifacts:
> - If major version mismatch (e.g., "1.x" vs "2.x"): fail with schema_invalid
> - If minor version mismatch (e.g., "1.0" vs "1.1"): attempt migration
> - If patch version mismatch (e.g., "1.0.0" vs "1.0.1"): proceed

**Impact:** Example uses three-part semver ("1.0.0") but JSON schemas in `specs/schemas/` use simple strings like "1.0". Unclear if "1.0" means "1.0.0" or if patch version is omitted.

**Proposed Fix:** Add to specs/28_coordination_and_handoffs.md:
> **Schema version format**: MUST use semantic versioning (MAJOR.MINOR.PATCH) as defined by semver.org. Omitting PATCH is permitted (e.g., "1.0" is equivalent to "1.0.0").

---

## S-GAP-012 | WARNING | Ambiguous: "Reasonable default" in Run Config

**Spec File:** (referenced in multiple specs, e.g., specs/01_system_contract.md:39)
**Issue:** Spec mentions "temperature MUST default to 0.0" but does not specify where this default is applied (schema? code?)
**Evidence:**
> - LLM provider params (temperature MUST default to 0.0)

**Impact:** Unclear if schema should include `"default": 0.0` or if runtime code should fill it in. Different implementations may place defaults differently.

**Proposed Fix:** Clarify in specs/01_system_contract.md:
> - LLM provider params: `temperature` field MUST have schema default of 0.0. If omitted from run_config, runtime MUST use 0.0.

---

## S-GAP-013 | BLOCKER | Missing Validation: Schema Version in Artifacts

**Spec File:** `specs/01_system_contract.md:42-56`
**Issue:** System contract requires all JSON artifacts but does not require validation of `schema_version` field existence
**Evidence:**
> All JSON outputs MUST validate. Unknown keys are forbidden.

**Impact:** Specs require artifacts to include `schema_version` (specs/28_coordination_and_handoffs.md:186) but validation spec does not enforce this. Artifacts could be written without schema_version and pass validation.

**Proposed Fix:** Add to specs/09_validation_gates.md Gate 1 validation rules:
> 5. All JSON artifacts MUST include `schema_version` field. If missing, fail with error_code `GATE_SCHEMA_VERSION_MISSING`.

---

## S-GAP-014 | WARNING | Vague Language: "Clean PR" in PR Manager Goal

**Spec File:** `specs/12_pr_and_release.md:3-4`
**Issue:** Spec uses vague language "clean PR"
**Evidence:**
> ## Goal
> Open a clean PR that is easy for humans to review, with evidence and checklists.

**Impact:** "Clean" and "easy for humans to review" are subjective. Implementers cannot verify this requirement deterministically.

**Proposed Fix:** Replace with objective criteria:
> Open a PR that includes: (1) atomic commits with descriptive messages, (2) PR body with evidence summary and validation checklist, (3) diff report attachment, (4) no merge conflicts with base branch.

---

## S-GAP-015 | WARNING | Missing Failure Mode: Telemetry API Completely Unavailable

**Spec File:** `specs/16_local_telemetry_api.md:123-182`
**Issue:** Outbox pattern handles transient failures but does not define behavior when telemetry API is completely unreachable for entire run
**Evidence:**
> When telemetry API is consistently unreachable:
> - After 10 consecutive failures across multiple runs, emit system-level WARNING
> - Write diagnostic report to `reports/telemetry_unavailable.md`

**Impact:** "10 consecutive failures across multiple runs" is unclear - does this mean 10 runs must fail, or 10 POST attempts within one run? Unclear if run should fail or proceed.

**Proposed Fix:** Clarify:
> - After 10 consecutive POST failures within a single run, emit system-level WARNING
> - Run MAY proceed but MUST mark parent telemetry run as `partial` status
> - If telemetry is required by policy, fail run with error_code `TELEMETRY_UNAVAILABLE`

---

## S-GAP-016 | BLOCKER | Missing Operational Clarity: Prompt Hash Computation

**Spec File:** `specs/10_determinism_and_caching.md:25-29`
**Issue:** Prompt hash requirement does not specify hash algorithm or exact input format
**Evidence:**
> prompt_hash must include:
> - full prompt text
> - schema reference id/version
> - worker name and version

**Impact:** Implementers cannot determine if prompt_hash is sha256, md5, or other. Unclear if "full prompt text" includes system message, user message, or both. Unclear if formatting (whitespace, newlines) affects hash.

**Proposed Fix:** Replace with:
> prompt_hash computation (binding):
> - Algorithm: SHA-256
> - Input: `{system_message}\n\n{user_message}\n\nschema:{schema_id}:{schema_version}\nworker:{worker_name}:{worker_version}`
> - Whitespace normalization: Trim leading/trailing whitespace, collapse multiple spaces to single space

---

## S-GAP-017 | WARNING | Ambiguous: "Rarely" in Patch Type Selection

**Spec File:** `specs/08_patch_engine.md:14`
**Issue:** Spec uses ambiguous language "rare" when describing delete_file patches
**Evidence:**
> - delete_file (rare, only if allowed)

**Impact:** "Rare" is subjective. Implementers cannot determine when deletion is permitted vs forbidden.

**Proposed Fix:** Replace with:
> - delete_file (MUST be explicitly allowed in run_config.allow_file_deletion, default: false)

---

## S-GAP-018 | WARNING | Missing Failure Mode: All Adapters Score Zero

**Spec File:** `specs/02_repo_ingestion.md:249-257`
**Issue:** Adapter selection failure handling specifies "no adapter available" but does not specify behavior when universal fallback also fails
**Evidence:**
> If adapter selection fails (no exact match, no platform fallback, and universal fallback is not available):
> ...
> The universal fallback adapter MUST always exist and be registered as "universal:best_effort".

**Impact:** Spec requires universal fallback to "always exist" but does not define failure handling if universal adapter fails (e.g., crashes, times out).

**Proposed Fix:** Add to Adapter Selection Failure Handling:
> If universal adapter execution fails, emit error_code `REPO_SCOUT_ADAPTER_FAILED`, open BLOCKER issue, fail the run with exit code 5.

---

## S-GAP-019 | WARNING | Vague Language: "Minimal viable launch" in Page Planning

**Spec File:** `specs/06_page_planning.md:42-49`
**Issue:** Spec uses vague language "minimum viable launch" without defining "viable"
**Evidence:**
> ## Content quotas (minimum viable launch)
> Minimum pages per section (configurable):
> - products: 1 landing page
> - docs: 2 to 5 how-to guides (based on workflows)

**Impact:** "Minimum viable launch" and "based on workflows" are subjective. Unclear if 2 or 5 guides is the minimum for docs section.

**Proposed Fix:** Replace with:
> ## Content quotas (minimum page counts)
> Minimum pages per section (from run_config.min_pages or defaults):
> - products: 1 (landing page)
> - docs: max(2, min(5, workflow_count))

---

## S-GAP-020 | BLOCKER | Missing Contradiction: Telemetry Required vs Transport Failures

**Spec File:** `specs/16_local_telemetry_api.md:12-16` vs `specs/16_local_telemetry_api.md:149-153`
**Issue:** Spec states telemetry is "required" but also states transport failures "MUST NOT crash the run"
**Evidence:**
> ## Binding requirements
> 1) **Always-on**: Telemetry emission is required for every run.
> ...
> ### Telemetry transport resilience
> Telemetry MUST be treated as **required**, but transport failures MUST be handled safely:
> - If telemetry POST fails, append the payload to `RUN_DIR/telemetry_outbox.jsonl`
> - Do not drop telemetry silently

**Impact:** Unclear if "required" means runs MUST fail when telemetry is unavailable, or if "required" only means "must attempt". This contradicts failure handling guidance.

**Proposed Fix:** Clarify in binding requirements:
> 1) **Always-on**: Telemetry emission MUST be attempted for every run. Runs MAY proceed if telemetry transport fails (using outbox buffering), but MUST mark run as `partial` status.

---

## S-GAP-021 | WARNING | Missing Edge Case: Zero Snippets in Catalog

**Spec File:** `specs/05_example_curation.md:56-59`
**Issue:** Acceptance criteria requires "at least one quickstart snippet exists" but does not define behavior when zero snippets can be extracted
**Evidence:**
> ## Acceptance
> - snippet_catalog.json validates schema
> - At least one quickstart snippet exists (repo_file preferred)

**Impact:** Unclear if run should fail or proceed with empty snippet catalog when no snippets found. Acceptance criteria says "at least one" but edge case handling in specs/21_worker_contracts.md:148 says "proceed with empty catalog".

**Proposed Fix:** Update acceptance to match edge case handling:
> - At least one quickstart snippet exists (repo_file preferred), OR snippet_catalog is empty with note explaining why no snippets were found

---

## S-GAP-022 | WARNING | Ambiguous: "Allowed when" in Template Sourcing

**Spec File:** `specs/20_rulesets_and_templates_registry.md:145-148`
**Issue:** Spec uses ambiguous language "may be maintained" and "acceptable approaches"
**Evidence:**
> ## Templates sourcing (allowed)
> Templates may be maintained outside the launcher repo, but they MUST be materialized into `specs/templates/` before planning or writing.
> Acceptable approaches include a git submodule, bootstrap clone, or CI artifact download.

**Impact:** "May be" suggests optional, but "MUST be materialized" suggests required. Unclear if external sourcing is allowed or discouraged.

**Proposed Fix:** Clarify:
> Templates MAY be sourced from external repositories. If externally sourced, they MUST be materialized into `specs/templates/` before planning or writing (via git submodule, bootstrap clone, or CI artifact download).

---

## S-GAP-023 | WARNING | Missing Operational Clarity: Cache Key Collision Handling

**Spec File:** `specs/10_determinism_and_caching.md:30-32`
**Issue:** Cache key computation is defined but collision handling is not specified
**Evidence:**
> ## Cache keys
> cache_key = sha256(model_id + "|" + prompt_hash + "|" + inputs_hash)

**Impact:** Unclear what happens when two different prompts produce the same cache_key (hash collision). Should cache entry be overwritten, or should worker fail?

**Proposed Fix:** Add cache collision policy:
> Cache collision handling: If cache_key exists with different content, log WARNING, invalidate old cache entry, write new entry. Cache hits require exact content match (not just key match).

---

## S-GAP-024 | WARNING | Missing Timeout: Replay Algorithm Timeout

**Spec File:** `specs/11_state_and_events.md:118-167`
**Issue:** Replay and resume algorithms do not specify timeout limits
**Evidence:**
> ### Algorithm Steps
> 1. **Load Events**: Read all events from `events.ndjson` in append order
> 2. **Validate Chain**: For each event, verify:
>    - `event_hash = sha256(event_id + ts + type + payload + prev_hash)`

**Impact:** Large event logs could cause replay to hang indefinitely. No timeout specified.

**Proposed Fix:** Add to Replay Algorithm section:
> **Timeout**: Replay MUST complete within 60 seconds. If timeout exceeded, fail with error_code `REPLAY_TIMEOUT`.

---

## Summary by Severity

### BLOCKER (8)
- S-GAP-001: Missing error code definition
- S-GAP-003: Missing spec_ref field definition
- S-GAP-005: Missing fixer worker timeout
- S-GAP-008: Missing URL collision tie-breaking
- S-GAP-011: Missing schema version format
- S-GAP-013: Missing schema_version validation
- S-GAP-016: Missing prompt hash computation details
- S-GAP-020: Contradicting telemetry requirements

### WARNING (16)
- S-GAP-002: Vague "best effort" language
- S-GAP-004: Ambiguous "stable ordering"
- S-GAP-006: Contradicting evidence priorities
- S-GAP-007: Missing Hugo config failure mode
- S-GAP-009: Vague "minimal change" language
- S-GAP-010: Missing empty repo edge case
- S-GAP-012: Ambiguous default application
- S-GAP-014: Vague "clean PR" language
- S-GAP-015: Missing telemetry unavailable handling
- S-GAP-017: Ambiguous "rare" language
- S-GAP-018: Missing adapter failure handling
- S-GAP-019: Vague "minimal viable launch"
- S-GAP-021: Missing zero snippets edge case
- S-GAP-022: Ambiguous template sourcing
- S-GAP-023: Missing cache collision handling
- S-GAP-024: Missing replay timeout

---

**Audit Completed**: 2026-01-27
**Auditor**: AGENT_S (Specs Quality Auditor)
# Gates/Validators Gaps

**Audit Date**: 2026-01-27
**Auditor**: AGENT_G (Gates/Validators Auditor)
**Scope**: Validation gates and validators gap analysis

---

## Summary

**Total Gaps Identified**: 16
- **BLOCKER**: 13 (missing runtime gates)
- **WARN**: 3 (incomplete implementations)

**Impact**: Runtime validation is 87% incomplete. The launcher cannot validate generated content quality, Hugo compatibility, TruthLock compliance, or rollback metadata.

---

## G-GAP-001 | BLOCKER | Gate 2 (Markdown Lint) Not Implemented

**Gate**: Gate 2: Markdown Lint and Frontmatter Validation
**Spec Authority**: `specs/09_validation_gates.md:53-84`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:53-84):
```
### Gate 2: Markdown Lint and Frontmatter Validation

**Purpose**: Validate markdown quality and frontmatter compliance

**Validation Rules**:
1. All markdown files MUST pass markdownlint with pinned ruleset
2. No new lint errors allowed (compared to baseline if exists)
3. All required frontmatter fields MUST be present (per frontmatter_contract)
4. All frontmatter field types MUST match contract
```

Implementation status (src/launch/validators/cli.py:216-227):
```python
not_impl = [
    "frontmatter",
    "markdownlint",
    ...
]
for gate_name in not_impl:
    sev = "blocker" if profile == "prod" else "warn"
    issues.append(
        _issue(
            issue_id=f"iss_not_implemented_{gate_name}",
            gate=gate_name,
            severity=sev,
            error_code=f"GATE_NOT_IMPLEMENTED" if sev == "blocker" else None,
            message=f"Gate not implemented (no false pass: marked as FAILED per Guarantee E)",
            ...
        )
    )
```

**Impact**: Cannot enforce markdown quality or frontmatter contracts. Generated content may have:
- Broken markdown syntax
- Missing required frontmatter fields
- Type mismatches in frontmatter
- Lint errors that break Hugo rendering

**Proposed Fix**: Implement gate in `src/launch/validators/markdown_lint.py`:
1. Integrate markdownlint-cli2 or equivalent
2. Load frontmatter_contract.json from RUN_DIR/artifacts/
3. Validate all *.md files under RUN_DIR/work/site/
4. Emit GATE_MARKDOWN_LINT_ERROR and GATE_FRONTMATTER_* error codes
5. Respect profile-specific timeout (local: 60s, ci/prod: 120s)

**Related Specs**: specs/18_site_repo_layout.md (content roots), specs/02_repo_ingestion.md (frontmatter contracts)

---

## G-GAP-002 | BLOCKER | Gate 3 (Hugo Config) Not Implemented

**Gate**: Gate 3: Hugo Config Compatibility
**Spec Authority**: `specs/09_validation_gates.md:86-116`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:86-116):
```
### Gate 3: Hugo Config Compatibility

**Purpose**: Validate Hugo config coverage for planned content

**Validation Rules**:
1. All planned `(subdomain, family)` pairs MUST be enabled by Hugo configs
2. Every planned `output_path` MUST match content root contract
3. Hugo config MUST exist for all required sections
4. Content roots MUST match `site_layout.subdomain_roots` from run_config
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:220)

**Impact**: Cannot enforce Hugo config compatibility. Risks:
- Planned content without Hugo config → Hugo build fails
- Output paths mismatch content roots → broken links
- Subdomain/family pairs not enabled → 404s on deployed site

**Proposed Fix**: Implement gate in `src/launch/validators/hugo_config.py`:
1. Load page_plan.json and site_context.json from RUN_DIR/artifacts/
2. Parse Hugo config files from site repo
3. Validate all (subdomain, family) pairs have config coverage
4. Validate output_path matches content root contract
5. Emit GATE_HUGO_CONFIG_* error codes

**Related Specs**: specs/31_hugo_config_awareness.md, specs/18_site_repo_layout.md

---

## G-GAP-003 | BLOCKER | Gate 4 (Platform Layout) Runtime Validation Missing

**Gate**: Gate 4: Platform Layout Compliance
**Spec Authority**: `specs/09_validation_gates.md:118-154`
**Issue**: Runtime validation of generated content not implemented

**Evidence**:

Spec requirement (specs/09:118-154):
```
### Gate 4: Platform Layout Compliance

**Purpose**: Validate V2 platform-aware content layout compliance

**Validation Rules**:
1. When `layout_mode=v2` for a section:
   - Non-blog sections MUST contain `/{locale}/{platform}/` in output paths
   - Blog section MUST contain `/{platform}/` at correct depth
   - Products section MUST use `/{locale}/{platform}/` (NOT `/{platform}/` alone)
2. All planned writes MUST be within taskcard `allowed_paths`
3. `allowed_paths` MUST include platform-level roots for V2 sections
4. Generated content MUST NOT contain unresolved `__PLATFORM__` tokens
5. Resolved `layout_mode` per section MUST be consistent across artifacts
```

Implementation: NOT_IMPLEMENTED (cli.py does not list platform_layout in not_impl, but gate does not exist)

**Preflight Coverage**: tools/validate_platform_layout.py validates taskcards, but NOT generated content

**Impact**: Cannot enforce V2 platform layout in generated content. Risks:
- Unresolved `__PLATFORM__` tokens in content
- Output paths missing /{locale}/{platform}/ segments
- Writes outside allowed_paths
- layout_mode inconsistencies between artifacts

**Proposed Fix**: Implement runtime gate in `src/launch/validators/platform_layout.py`:
1. Load page_plan.json and patch_bundle.json
2. For each page with layout_mode=v2, validate path segments
3. Scan generated content for unresolved `__PLATFORM__` tokens
4. Validate all writes in allowed_paths
5. Emit GATE_PLATFORM_* error codes

**Related Specs**: specs/26_repo_adapters_and_variability.md, specs/18_site_repo_layout.md

---

## G-GAP-004 | BLOCKER | Gate 5 (Hugo Build) Not Implemented

**Gate**: Gate 5: Hugo Build
**Spec Authority**: `specs/09_validation_gates.md:156-186`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:156-186):
```
### Gate 5: Hugo Build

**Purpose**: Validate Hugo site builds successfully in production mode

**Validation Rules**:
1. Hugo build MUST succeed in production mode
2. Build MUST complete without errors
3. Build warnings MAY be allowed (profile-dependent)
4. Build MUST produce output in expected locations
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:221)

**Impact**: Cannot validate Hugo build succeeds. Risks:
- Content deployed that breaks Hugo build
- Template syntax errors not caught before PR
- Missing dependencies or broken shortcodes
- Build errors discovered only in CI/production

**Proposed Fix**: Implement gate in `src/launch/validators/hugo_build.py`:
1. Run `hugo --environment production` in RUN_DIR/work/site/
2. Capture stdout/stderr
3. Check exit code (must be 0)
4. Validate output directory created
5. Respect profile timeout (local: 300s, ci/prod: 600s)
6. Emit GATE_HUGO_BUILD_* error codes

**Related Specs**: specs/31_hugo_config_awareness.md, specs/19_toolchain_and_ci.md

---

## G-GAP-005 | BLOCKER | Gate 6 (Internal Links) Not Implemented

**Gate**: Gate 6: Internal Links
**Spec Authority**: `specs/09_validation_gates.md:188-218`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:188-218):
```
### Gate 6: Internal Links

**Purpose**: Validate no broken internal links or anchors

**Validation Rules**:
1. All internal markdown links MUST resolve to existing files
2. All anchor references (`#heading`) MUST resolve to existing headings
3. All cross-references between pages MUST be valid
4. No broken relative links allowed
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:222)

**Impact**: Cannot detect broken internal links before PR. Risks:
- Broken navigation between docs pages
- Invalid anchor links to non-existent headings
- 404s from cross-references
- Poor user experience on deployed site

**Proposed Fix**: Implement gate in `src/launch/validators/internal_links.py`:
1. Parse all *.md files in RUN_DIR/work/site/
2. Extract internal links (relative paths, anchors)
3. Validate link targets exist
4. Validate anchors match existing headings (after slug conversion)
5. Respect profile timeout (local: 120s, ci/prod: 180s)
6. Emit GATE_LINK_BROKEN_* error codes

**Related Specs**: specs/22_navigation_and_existing_content_update.md

---

## G-GAP-006 | BLOCKER | Gate 7 (External Links) Not Implemented

**Gate**: Gate 7: External Links
**Spec Authority**: `specs/09_validation_gates.md:220-249`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:220-249):
```
### Gate 7: External Links

**Purpose**: Validate external links are reachable (optional by config)

**Validation Rules**:
1. All external HTTP/HTTPS links SHOULD be reachable (HTTP 200-399)
2. Links to allowlisted domains always checked
3. Redirects (3xx) are acceptable
4. Rate limiting and timeouts handled gracefully
```

**Behavior by Profile** (specs/09:244-247):
- local: Skip by default (override with --check-external-links)
- ci: Run when enabled
- prod: Run all checks

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:223)

**Impact**: Cannot detect broken external links. Risks:
- Broken documentation references to upstream projects
- Dead links to GitHub issues/PRs
- 404s to external API docs
- Poor SEO from broken outbound links

**Proposed Fix**: Implement gate in `src/launch/validators/external_links.py`:
1. Parse all *.md files for external links
2. Check HTTP status codes (with timeout)
3. Handle rate limiting with exponential backoff
4. Support profile-based skipping
5. Respect profile timeout (local: 300s, ci/prod: 600s)
6. Emit GATE_LINK_EXTERNAL_* error codes

**Related Specs**: specs/34_strict_compliance_guarantees.md (Network Allowlist)

---

## G-GAP-007 | BLOCKER | Gate 8 (Snippet Checks) Not Implemented

**Gate**: Gate 8: Snippet Checks
**Spec Authority**: `specs/09_validation_gates.md:251-282`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:251-282):
```
### Gate 8: Snippet Checks

**Purpose**: Validate code snippet syntax and optionally execution

**Validation Rules**:
1. All code snippets MUST pass syntax validation for their language
2. Snippets MUST match language declared in code fence
3. Optional: Runnable snippets executed in container (ci/prod only)
4. Snippet sources MUST exist in snippet catalog
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:224)

**Impact**: Cannot validate snippet quality. Risks:
- Syntax errors in code examples
- Language mismatch (python code in bash fence)
- Broken snippets that don't execute
- Snippets not grounded in snippet_catalog.json

**Proposed Fix**: Implement gate in `src/launch/validators/snippet_checks.py`:
1. Load snippet_catalog.json from RUN_DIR/artifacts/
2. Parse code fences from all *.md files
3. Run syntax validators (python -m py_compile, shellcheck, etc.)
4. Validate language matches fence declaration
5. Check snippet sources exist in catalog
6. Optional: Execute snippets in container (ci/prod)
7. Emit GATE_SNIPPET_* error codes

**Related Specs**: specs/05_example_curation.md

---

## G-GAP-008 | BLOCKER | Gate 9 (TruthLock) Not Implemented

**Gate**: Gate 9: TruthLock
**Spec Authority**: `specs/09_validation_gates.md:284-317`
**Issue**: Spec defines gate but no validator exists — CRITICAL for evidence grounding

**Evidence**:

Spec requirement (specs/09:284-317):
```
### Gate 9: TruthLock

**Purpose**: Enforce claim stability and evidence grounding requirements

**Validation Rules**:
1. All claims in content MUST link to EvidenceMap entries
2. No uncited facts allowed (unless allow_inference=true with constraints)
3. Claim IDs MUST be stable (match truth_lock_report)
4. Evidence sources MUST be traceable to repo artifacts
5. Contradictions MUST be resolved (per priority rules)
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:225)

**Impact**: **CRITICAL** — Cannot enforce evidence grounding. Risks:
- Uncited claims in documentation (hallucinations)
- Unresolved contradictions between evidence sources
- Unstable claim IDs (breaks reproducibility)
- Evidence sources not traceable to repo
- Violations of allow_inference constraints

**Proposed Fix**: Implement gate in `src/launch/validators/truthlock.py`:
1. Load truth_lock_report.json and evidence_map.json from RUN_DIR/artifacts/
2. Parse generated content for claim markers
3. Validate all claims link to EvidenceMap entries
4. Validate claim IDs stable (match truth_lock_report)
5. Validate evidence sources exist in repo
6. Check contradictions resolved per priority rules
7. Emit GATE_TRUTHLOCK_* error codes

**Related Specs**: specs/04_claims_compiler_truth_lock.md (TruthLock rules), specs/03_product_facts_and_evidence.md

**Priority**: HIGHEST — TruthLock is core to foss-launcher's value proposition

---

## G-GAP-009 | BLOCKER | Gate 10 (Consistency) Not Implemented

**Gate**: Gate 10: Consistency
**Spec Authority**: `specs/09_validation_gates.md:319-353`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:319-353):
```
### Gate 10: Consistency

**Purpose**: Validate cross-artifact consistency and required content presence

**Validation Rules**:
1. `product_name` MUST be consistent across all artifacts and content
2. `repo_url` MUST match across ProductFacts and page frontmatter
3. Canonical URLs MUST match run_config canonical_urls
4. Required headings MUST be present (per page type)
5. Required sections MUST be present (per required_sections)
```

Implementation: NOT_IMPLEMENTED (not in cli.py not_impl list, but gate does not exist)

**Impact**: Cannot detect cross-artifact inconsistencies. Risks:
- product_name mismatches (e.g., "MyProject" vs "my-project")
- repo_url inconsistencies between artifacts
- canonical_url mismatches causing SEO issues
- Missing required headings/sections per page type

**Proposed Fix**: Implement gate in `src/launch/validators/consistency.py`:
1. Load all artifacts (product_facts.json, page_plan.json, site_context.json)
2. Validate product_name consistent across all
3. Validate repo_url matches everywhere
4. Validate canonical_urls match run_config
5. Check required headings per page type
6. Emit GATE_CONSISTENCY_* error codes

**Related Specs**: specs/03_product_facts_and_evidence.md, specs/06_page_planning.md

---

## G-GAP-010 | BLOCKER | Gate 11 (Template Token Lint) Not Implemented

**Gate**: Gate 11: Template Token Lint
**Spec Authority**: `specs/09_validation_gates.md:355-383`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:355-383):
```
### Gate 11: Template Token Lint

**Purpose**: Validate no unresolved template tokens remain in generated content

**Validation Rules**:
1. No unresolved `__UPPER_SNAKE__` tokens allowed in content
2. No unresolved `__PLATFORM__` tokens allowed
3. No unresolved `{{template_var}}` tokens allowed
4. Template tokens in code blocks are allowed (not evaluated)
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:219)

**Impact**: Cannot detect unresolved tokens. Risks:
- `__PRODUCT_NAME__` appearing in published docs
- `__PLATFORM__` tokens in V2 platform content
- `{{repo_url}}` not replaced in links
- Template syntax visible to end users

**Proposed Fix**: Implement gate in `src/launch/validators/template_token_lint.py`:
1. Parse all *.md files and *.json artifacts
2. Scan for patterns: `__[A-Z_]+__`, `{{[a-z_]+}}`
3. Exclude code blocks from scanning
4. Emit GATE_TEMPLATE_TOKEN_UNRESOLVED error for each match
5. Respect profile timeout (local: 30s, ci/prod: 60s)

**Related Specs**: specs/08_patch_engine.md (template expansion), specs/20_rulesets_and_templates_registry.md

---

## G-GAP-011 | BLOCKER | Gate 12 (Universality) Not Implemented

**Gate**: Gate 12: Universality Gates
**Spec Authority**: `specs/09_validation_gates.md:385-428`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:385-428):
```
### Gate 12: Universality Gates

**Purpose**: Validate content meets universality requirements

**Validation Rules**:

1. **Tier Compliance**:
   - If `launch_tier=minimal`: Pages MUST NOT include exhaustive API lists or ungrounded workflow claims
   - If `launch_tier=rich`: Pages MUST demonstrate grounding (claim_groups -> snippets) before expanding page count

2. **Limitations Honesty**:
   - If `ProductFacts.limitations` is non-empty: docs + reference MUST include Limitations section
   - Limitations content MUST come from ProductFacts only

3. **Distribution Correctness**:
   - If `ProductFacts.distribution` is present: Install commands MUST match `distribution.install_commands` exactly
   - No invented package names allowed

4. **No Hidden Inference**:
   - Even with `allow_inference=true`: Capabilities must be grounded in EvidenceMap
   - Only page structure decisions may be inferred, not product capabilities
```

Implementation: NOT_IMPLEMENTED (not in cli.py not_impl list, but gate does not exist)

**Impact**: Cannot enforce universality guarantees. Risks:
- Exhaustive API lists in minimal tier launches
- Missing Limitations section when required
- Invented install commands (hallucinations)
- Hidden inference of capabilities without evidence

**Proposed Fix**: Implement gate in `src/launch/validators/universality.py`:
1. Load product_facts.json, page_plan.json, run_config
2. Validate tier compliance (minimal vs rich)
3. Check Limitations section presence/content
4. Validate install commands match ProductFacts.distribution
5. Check inference constraints (capabilities grounded)
6. Emit GATE_UNIVERSALITY_* error codes

**Related Specs**: specs/03_product_facts_and_evidence.md, specs/06_page_planning.md

---

## G-GAP-012 | BLOCKER | Gate 13 (Rollback Metadata) Not Implemented

**Gate**: Gate 13: Rollback Metadata Validation (Guarantee L)
**Spec Authority**: `specs/09_validation_gates.md:430-468`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:430-468):
```
### Gate 13: Rollback Metadata Validation (Guarantee L)

**Purpose**: Validate PR artifacts include rollback metadata (prod profile only)

**Validation Rules** (only in prod profile):
1. `pr.json` MUST exist
2. `pr.json` MUST validate against `specs/schemas/pr.schema.json`
3. Required fields MUST be present: `base_ref`, `run_id`, `rollback_steps`, `affected_paths`
4. `base_ref` MUST match pattern `^[a-f0-9]{40}$` (40-char SHA)
5. `rollback_steps` array MUST have minItems: 1
6. `affected_paths` array MUST have minItems: 1
7. All paths in `affected_paths` MUST appear in PR diff
```

**Behavior by Profile**:
- prod: BLOCKER if validation fails
- ci: WARN if validation fails
- local: SKIP (not run)

Implementation: NOT_IMPLEMENTED (not in cli.py not_impl list, but gate does not exist)

**Impact**: Cannot enforce rollback contract in production. Risks:
- PRs without rollback metadata
- Invalid base_ref (not a commit SHA)
- Empty rollback_steps (cannot revert)
- Missing affected_paths (cannot assess impact)

**Proposed Fix**: Implement gate in `src/launch/validators/rollback.py`:
1. Check profile (skip if local, warn if ci, BLOCKER if prod)
2. Load pr.json from RUN_DIR/artifacts/
3. Validate against specs/schemas/pr.schema.json
4. Validate base_ref is 40-char SHA
5. Validate rollback_steps non-empty
6. Validate affected_paths non-empty
7. Emit PR_MISSING_ROLLBACK_METADATA and related error codes

**Related Specs**: specs/12_pr_and_release.md, specs/34_strict_compliance_guarantees.md (Guarantee L)

---

## G-GAP-013 | BLOCKER | Gate T (Test Determinism) Not Implemented

**Gate**: Gate T: Test Determinism Configuration (Guarantee I)
**Spec Authority**: `specs/09_validation_gates.md:471-495`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:471-495):
```
### Gate T: Test Determinism Configuration (Guarantee I)

**Purpose**: Validate test configuration enforces determinism (PYTHONHASHSEED=0)

**Validation Rules**:
1. One of the following MUST be true:
   - `pyproject.toml` contains `[tool.pytest.ini_options]` with `env = ["PYTHONHASHSEED=0"]`
   - `pytest.ini` contains `[pytest]` section with `env = PYTHONHASHSEED=0`
   - All CI workflow test commands set `PYTHONHASHSEED=0` before running pytest
```

Implementation: NOT_IMPLEMENTED (not in cli.py not_impl list, but gate does not exist)

**Impact**: Cannot enforce test determinism. Risks:
- Flaky tests due to hash randomization
- Non-reproducible test failures
- Test results vary between runs
- Debugging intermittent failures difficult

**Proposed Fix**: Implement gate in `src/launch/validators/test_determinism.py`:
1. Check pyproject.toml for PYTHONHASHSEED in pytest env
2. Check pytest.ini for PYTHONHASHSEED
3. Check .github/workflows/*.yml for PYTHONHASHSEED in test commands
4. Pass if ANY of the above is true
5. Emit TEST_MISSING_PYTHONHASHSEED or TEST_DETERMINISM_NOT_ENFORCED

**Related Specs**: specs/34_strict_compliance_guarantees.md (Guarantee I)

---

## G-GAP-014 | WARN | Schema Validation Incomplete (Frontmatter Not Validated)

**Gate**: Gate 1: Schema Validation
**Spec Authority**: `specs/09_validation_gates.md:21-50`
**Issue**: Gate only validates JSON artifacts, not frontmatter

**Evidence**:

Spec requirement (specs/09:26-34):
```
**Inputs**:
- All `*.json` files under `RUN_DIR/artifacts/`
- All schemas under `specs/schemas/`
- All page frontmatter in `*.md` files under `RUN_DIR/work/site/`

**Validation Rules**:
1. All JSON artifacts MUST validate against their respective schemas
2. Schema validation MUST use JSON Schema Draft 2020-12
3. All page frontmatter MUST be valid YAML
4. If `frontmatter_contract.json` exists, all frontmatter MUST validate against it
```

Implementation (src/launch/validators/cli.py:177-211):
```python
# Gate 3: artifact schema validation for any present JSON artifacts
artifacts_dir = run_dir / "artifacts"
schema_log = run_dir / "logs" / "gate_schema_validation.log"

artifacts = sorted(p for p in artifacts_dir.glob("*.json") if p.is_file())
artifact_ok = True
errors: List[str] = []

for artifact in artifacts:
    schema_path = _infer_schema_path(repo_root, artifact)
    if not schema_path.exists():
        artifact_ok = False
        errors.append(f"No schema for {artifact.name} (expected {schema_path.name})")
        continue
    try:
        validate_json_file(artifact, schema_path)
    except Exception as e:
        artifact_ok = False
        errors.append(f"{artifact.name}: {e}")
```

**Coverage**:
- ✅ JSON artifact validation
- ❌ Frontmatter YAML validation
- ❌ Frontmatter contract validation

**Impact**: Cannot detect:
- Invalid YAML in frontmatter
- Missing required frontmatter fields
- Type mismatches in frontmatter

**Proposed Fix**: Extend cli.py Gate 1 to:
1. Glob all *.md files in RUN_DIR/work/site/
2. Parse frontmatter (YAML)
3. Validate YAML syntax
4. If frontmatter_contract.json exists, validate against it
5. Emit GATE_FRONTMATTER_* error codes

**Related Gaps**: G-GAP-001 (Gate 2 covers frontmatter validation, so overlap exists)

---

## G-GAP-015 | WARN | Profile-Specific Timeouts Not Implemented

**Gate**: All Gates
**Spec Authority**: `specs/09_validation_gates.md:511-547`
**Issue**: Timeout values hardcoded, not profile-dependent

**Evidence**:

Spec requirement (specs/09:515-542):
```
### Gate Timeouts by Profile

**local profile** (development):
- Schema validation: 30s per artifact
- Markdown lint: 60s
- Hugo config check: 10s
- Hugo build: 300s (5 minutes)
- Internal links: 120s
- ...

**ci profile** (continuous integration):
- Schema validation: 60s per artifact
- Markdown lint: 120s
- Hugo config check: 20s
- Hugo build: 600s (10 minutes)
- Internal links: 180s
- ...

**prod profile** (not typically used for gating, reference only):
- Same as CI profile but may include additional checks
```

**Timeout Behavior** (specs/09:542-547):
```
- On timeout: emit BLOCKER issue with `error_code: GATE_TIMEOUT`
- Record which gate timed out in validation_report.json
- Do NOT retry timed-out gates automatically (orchestrator decides)
- Log timeout events to telemetry with gate name and elapsed time
```

**Preflight Implementation** (tools/validate_swarm_ready.py:113):
```python
result = subprocess.run(
    [sys.executable, str(full_path)],
    cwd=str(self.repo_root),
    capture_output=True,
    text=True,
    timeout=60  # Hardcoded 60s
)
```

**Runtime Implementation** (src/launch/validators/cli.py):
- ❌ No timeout enforcement found
- ❌ No GATE_TIMEOUT error code emission
- ❌ No profile-specific timeout configuration

**Impact**:
- Gates can hang indefinitely (runtime)
- Timeout values not optimized per profile (preflight)
- No telemetry for timeout events
- Cannot distinguish timeout from other failures

**Proposed Fix**:
1. **Preflight**: Add profile parameter to validate_swarm_ready.py, use profile-specific timeouts
2. **Runtime**: Wrap gate execution in timeout handlers (signal.alarm or threading.Timer)
3. Emit GATE_TIMEOUT error code per spec
4. Log timeout events to telemetry (run_dir/telemetry_outbox.jsonl)

**Related Specs**: specs/16_local_telemetry_api.md (telemetry logging)

---

## G-GAP-016 | WARN | Gate Execution Order Not Enforced

**Gate**: All Runtime Gates
**Spec Authority**: `specs/09_validation_gates.md:598`
**Issue**: Spec defines execution order but implementation does not enforce it

**Evidence**:

Spec requirement (specs/09:598):
```
- Gate execution order is: schema → lint → hugo_config → content_layout_platform → hugo_build → links → snippets → truthlock → consistency
```

**Implementation Order** (src/launch/validators/cli.py:116-250):
1. Gate 0: run_layout
2. Gate 1: toolchain_lock
3. Gate 2: run_config_schema
4. Gate 3: artifact_schema
5. Gates (NOT_IMPLEMENTED): frontmatter, markdownlint, template_token_lint, hugo_config, hugo_build, internal_links, external_links, snippets, truthlock

**Gap**: Implementation order does not match spec order:
- Spec order: schema → lint → hugo_config → content_layout_platform → hugo_build → links → snippets → truthlock → consistency
- Implementation order: run_layout → toolchain_lock → run_config_schema → artifact_schema → (all NOT_IMPLEMENTED)

**Impact**:
- Dependency between gates not respected (e.g., hugo_config should run before hugo_build)
- Schema validation should run first (currently does, but by accident not design)
- TruthLock should run near end (after content generation validated)

**Proposed Fix**:
1. Refactor cli.py validate() to enforce spec-defined order
2. Run gates in sequence: schema → lint → hugo_config → platform_layout → hugo_build → links → snippets → truthlock → consistency
3. Short-circuit on BLOCKER issues (if profile=prod and blocker found, stop execution)
4. Document execution order in code comments

**Rationale**: Execution order matters for:
- Early failure (schema errors should fail before hugo build)
- Dependency (hugo_config must pass before hugo_build)
- Performance (cheap gates first)

---

## Gap Priority Summary

**BLOCKER Gaps** (must fix before production):
1. G-GAP-008 (TruthLock) — HIGHEST PRIORITY (core value proposition)
2. G-GAP-002 (Hugo Config) — HIGH (prevents broken builds)
3. G-GAP-004 (Hugo Build) — HIGH (validates site generation)
4. G-GAP-005 (Internal Links) — HIGH (prevents 404s)
5. G-GAP-009 (Consistency) — HIGH (prevents artifact mismatches)
6. G-GAP-010 (Template Tokens) — HIGH (prevents unresolved tokens in production)
7. G-GAP-001 (Markdown Lint) — MEDIUM (quality gates)
8. G-GAP-003 (Platform Layout Runtime) — MEDIUM (V2 compliance)
9. G-GAP-007 (Snippet Checks) — MEDIUM (code example quality)
10. G-GAP-011 (Universality) — MEDIUM (launch tier compliance)
11. G-GAP-012 (Rollback Metadata) — MEDIUM (prod profile only)
12. G-GAP-006 (External Links) — LOW (optional by profile)
13. G-GAP-013 (Test Determinism) — LOW (test infrastructure)

**WARN Gaps** (quality improvements):
1. G-GAP-015 (Timeouts) — MEDIUM (prevents hangs)
2. G-GAP-014 (Schema Frontmatter) — LOW (overlap with Gate 2)
3. G-GAP-016 (Execution Order) — LOW (optimization)

---

## Compliance Impact

**Guarantees Affected by Gaps**:
- **Guarantee A** (Pinned Refs): ✅ Preflight enforced, ⚠ Runtime check missing (should exist per specs/34:59-84)
- **Guarantee E** (No Placeholders): ⚠ Template tokens not validated at runtime (G-GAP-010)
- **Guarantee I** (Test Determinism): ❌ Gate T not implemented (G-GAP-013)
- **Guarantee L** (Rollback): ❌ Gate 13 not implemented (G-GAP-012)

**Spec Compliance**:
- specs/09_validation_gates.md: 13/15 runtime gates missing (87% gap)
- specs/34_strict_compliance_guarantees.md: 3/12 guarantees not fully enforced

**Risk Assessment**:
- **Critical Risk**: TruthLock (G-GAP-008) — Cannot validate evidence grounding
- **High Risk**: Hugo gates (G-GAP-002, G-GAP-004) — Cannot validate site builds
- **Medium Risk**: Content quality gates (G-GAP-001, G-GAP-005, G-GAP-010) — Content quality not enforced
- **Low Risk**: Optional gates (G-GAP-006, G-GAP-013) — Not blocking for basic launches

---

## Recommendations

1. **Immediate Actions** (before any production runs):
   - Implement G-GAP-008 (TruthLock) — blocking for evidence grounding
   - Implement G-GAP-002 (Hugo Config) — blocking for site generation
   - Implement G-GAP-004 (Hugo Build) — blocking for deployment readiness

2. **Short-term Actions** (before Phase 6):
   - Implement G-GAP-005 (Internal Links) — blocking for link integrity
   - Implement G-GAP-009 (Consistency) — blocking for artifact consistency
   - Implement G-GAP-010 (Template Tokens) — blocking for clean content
   - Fix G-GAP-015 (Timeouts) — blocking for robustness

3. **Medium-term Actions** (Phase 6-7):
   - Implement remaining content quality gates (G-GAP-001, G-GAP-003, G-GAP-007, G-GAP-011)
   - Implement G-GAP-012 (Rollback) — blocking for prod profile
   - Fix G-GAP-014, G-GAP-016 (quality improvements)

4. **Long-term Actions** (post-launch):
   - Implement G-GAP-006 (External Links) — optional by profile
   - Implement G-GAP-013 (Test Determinism) — test infrastructure improvement

---

## Evidence Summary

All gaps documented with:
- ✅ Spec authority (specs/09:line-range)
- ✅ Implementation evidence (path:line or "NOT_IMPLEMENTED")
- ✅ Impact assessment
- ✅ Proposed fix with specific implementation guidance
- ✅ Related specs cross-referenced
# Plans/Taskcards Gaps Report

**Generated**: 2026-01-27
**Auditor**: AGENT_P (Plans/Taskcards & Swarm Readiness Auditor)
**Purpose**: Document all planning and taskcard gaps requiring attention

---

## Gap Summary

**Total Gaps Identified**: 3
**Severity Breakdown**:
- BLOCKER: 0
- WARNING: 0
- INFO: 3 (all expected in pre-implementation phase)

**Overall Assessment**: ✅ **NO BLOCKING GAPS**

All identified gaps are **INFO-level** and reflect the expected state of pre-implementation readiness. No plan deficiencies detected.

---

## P-GAP-001 | INFO | Orchestrator Implementation Not Started (Expected)

**Taskcard**: TC-300 (Orchestrator graph wiring and run loop)
**Spec Authority**:
- `specs/state-graph.md:1-end` (LangGraph state machine transitions)
- `specs/state-management.md:1-end` (state persistence, snapshots, event sourcing)
- `specs/28_coordination_and_handoffs.md:1-end` (orchestrator-to-worker handoff contracts)
- `specs/11_state_and_events.md:1-end` (event log structure)
- `specs/21_worker_contracts.md:1-end` (W1-W9 IO contracts)

**Issue**: Critical orchestrator spec has no implementation artifacts yet

**Evidence**:
- `plans/traceability_matrix.md:22-36`:
  ```markdown
  - specs/state-graph.md
    - **Purpose**: Defines LangGraph state machine transitions for orchestrator
    - **Implement**: TC-300 (Orchestrator graph definition, node transitions, edge conditions)
    - **Validate**: TC-300 (graph smoke tests, transition determinism tests)
    - **Status**: Spec complete, TC-300 not started

  - specs/state-management.md
    - **Purpose**: Defines state persistence, snapshot updates, event log structure
    - **Implement**: TC-300 (state serialization, snapshot creation, event sourcing)
    - **Validate**: TC-300 (determinism tests for state serialization)
    - **Status**: Spec complete, TC-300 not started

  - specs/28_coordination_and_handoffs.md
    - **Purpose**: Defines orchestrator-to-worker handoff contracts and coordination patterns
    - **Implement**: TC-300 (worker orchestration, handoff logic, state transitions)
    - **Validate**: TC-300 (orchestrator integration tests)
    - **Status**: Spec complete, TC-300 not started
  ```

- `plans/taskcards/STATUS_BOARD.md:25`:
  ```markdown
  | TC-300 | Orchestrator graph wiring and run loop | Ready | unassigned | TC-200 | 5 paths | ... |
  ```

- `plans/taskcards/TC-300_orchestrator_langgraph.md:1-21` (YAML frontmatter):
  ```yaml
  id: TC-300
  title: "Orchestrator graph wiring and run loop"
  status: Ready
  owner: "unassigned"
  depends_on:
    - TC-200
  allowed_paths:
    - src/launch/orchestrator/**
    - src/launch/state/**
    - tests/unit/orchestrator/test_tc_300_graph.py
    - tests/integration/test_tc_300_run_loop.py
    - reports/agents/**/TC-300/**
  ```

**Impact**:
- **Cannot execute full pipeline** without orchestrator
- **All workers (W1-W9) depend on TC-300** for state machine integration
- **Critical path blocker** for implementation

**Why This Is INFO (Not BLOCKER)**:
- This is **pre-implementation phase** — taskcards being "Ready" is the **correct state**
- TC-300 has **comprehensive taskcard** with:
  - Clear objective (orchestrator graph + run loop)
  - 6 spec references (binding authority)
  - Implementation steps (graph definition, run lifecycle, worker invocation, stop-the-line)
  - E2E verification commands
  - Acceptance checks (transitions match spec, events/snapshot produced, stop-the-line works)
  - Version locks (spec_ref, ruleset_version, templates_version)
- **No plan gap** — only **missing implementation** (expected)

**Proposed Fix**:
1. Assign TC-300 to implementation agent (prerequisite for all workers)
2. Implement per taskcard spec:
   - Graph definition per `specs/state-graph.md`
   - RUN_DIR creation + snapshot/event log initialization
   - Worker invocation with (RUN_DIR, run_config, snapshot) contract
   - Stop-the-line on BLOCKER/FAILED condition
3. Run tests: `tests/unit/orchestrator/test_tc_300_graph.py`, `tests/integration/test_tc_300_run_loop.py`
4. Verify determinism: same inputs → identical event bytes
5. Write evidence: `reports/agents/<agent>/TC-300/report.md`, `reports/agents/<agent>/TC-300/self_review.md`

**Dependencies**:
- **Upstream**: TC-200 (schemas + IO foundations) must be Done
- **Downstream**: All workers (TC-400..480) blocked until TC-300 Done

**Acceptance Criteria** (from taskcard):
- [ ] Orchestrator transitions match `specs/state-graph.md`
- [ ] `events.ndjson` and `snapshot.json` produced and update over time
- [ ] Stop-the-line behavior triggers correctly on BLOCKER/FAILED
- [ ] Tests pass and show deterministic ordering
- [ ] Agent reports written

**Severity**: INFO
**Action Required**: Implement TC-300 (assign to agent, follow taskcard contract)

---

## P-GAP-002 | INFO | Runtime Validation Gates Not Started (Expected)

**Taskcard**: TC-460 (W7 Validator), TC-570 (Validation gates extensions)
**Spec Authority**:
- `specs/09_validation_gates.md:1-end` (all runtime gates 1-10, universality gates)
- `specs/04_claims_compiler_truth_lock.md:1-end` (TruthLock gate)
- `specs/19_toolchain_and_ci.md:172` (TemplateTokenLint gate)
- `specs/31_hugo_config_awareness.md:1-end` (Hugo config gate)
- `specs/32_platform_aware_content_layout.md:1-end` (platform layout gate)

**Issue**: Runtime validation gates not implemented (all gates listed as "NOT YET IMPLEMENTED")

**Evidence**:
- `plans/traceability_matrix.md:322-430` (Runtime Gates section):
  ```markdown
  **Runtime Gates** (run during validation phase):

  - **Gate 1**: Schema validation
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 2**: Markdown lint + frontmatter validation
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 3**: Hugo config compatibility
    - Status: NOT YET IMPLEMENTED (See TC-550)

  - **Gate 4**: Platform layout compliance (content_layout_platform)
    - Status: ✅ IMPLEMENTED (preflight tool exists; runtime gate integration PENDING - See TC-570)

  - **Gate 5**: Hugo build
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 6**: Internal links
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 7**: External links (optional by config)
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 8**: Snippet checks
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 9**: TruthLock
    - Status: NOT YET IMPLEMENTED (See TC-413, TC-460)

  - **Gate 10**: Consistency
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate: TemplateTokenLint** (required per specs/19_toolchain_and_ci.md)
    - Status: NOT YET IMPLEMENTED (See TC-570)

  - **Gate: Tier compliance** (universality gate)
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate: Limitations honesty** (universality gate)
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate: Distribution correctness** (universality gate)
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate: No hidden inference** (universality gate)
    - Status: NOT YET IMPLEMENTED (See TC-413)
  ```

- `plans/taskcards/STATUS_BOARD.md:41,55`:
  ```markdown
  | TC-460 | W7 Validator (all gates → validation_report.json) | Ready | unassigned | TC-450 | 4 paths | ... |
  | TC-570 | Validation Gates (schema, links, Hugo smoke, policy) | Ready | unassigned | TC-460, TC-550 | 8 paths | ... |
  ```

**Impact**:
- **Cannot validate artifacts** until TC-460/TC-570 implemented
- **Cannot produce validation_report.json** (required by W8/W9)
- **Cannot run gates 1-10** (schema, lint, hugo, links, snippets, truthlock, consistency)
- **Cannot enforce platform layout** (V2 path validation pending TC-570 integration)

**Why This Is INFO (Not BLOCKER)**:
- This is **pre-implementation phase** — runtime gates being "not started" is **expected**
- **ALL PREFLIGHT GATES ARE IMPLEMENTED** (per `plans/traceability_matrix.md:242-315`):
  - Gate 0, A1, B, E, J, K, L, M, N, O, P, Q, R — ✅ ALL IMPLEMENTED
  - Preflight validation is **complete** and **ready to use**
- TC-460 and TC-570 have **comprehensive taskcards** with:
  - Clear objectives (gate runner orchestration, stable issue normalization)
  - Spec references (09_validation_gates, schemas, etc.)
  - Implementation steps (per-gate functions, stable normalization, timeout enforcement, platform gate)
  - E2E verification (canonical interface: `launch_validate --run_dir --profile`)
  - Acceptance checks (validation_report validates against schema, stable ordering, gates run)
  - Version locks (spec_ref, ruleset_version, templates_version)
- **No plan gap** — only **missing implementation** (expected)

**Proposed Fix**:
1. **TC-460** (W7 Validator):
   - Implement gate runner orchestration
   - Implement per-gate functions (schema, lint, hugo, links, snippets, truthlock, consistency)
   - Produce `validation_report.json` (schema: specs/schemas/validation_report.schema.json)
   - Ensure stable issue normalization (deterministic issue_id, stable ordering)
   - Validator is read-only (must not modify site)

2. **TC-570** (Validation gates extensions):
   - Implement `launch_validate` CLI with all gates
   - Implement **content_layout_platform gate** (V2 path validation per specs/32)
   - Implement **TemplateTokenLint gate** (unresolved token detection per specs/19:172)
   - Implement **gate timeout enforcement** (per specs/09:84-120)
   - Exit non-zero on required gate failure

3. Write evidence: `reports/agents/<agent>/TC-460/report.md`, `reports/agents/<agent>/TC-570/report.md`

**Dependencies**:
- **TC-460 depends on**: TC-450 (patched site available)
- **TC-570 depends on**: TC-460 (validator orchestration), TC-550 (Hugo awareness)
- **Downstream**: TC-470 (fixer), TC-480 (PRManager) depend on TC-460 output (validation_report.json)

**Acceptance Criteria** (from taskcards):
- [ ] `validation_report.json` validates against schema
- [ ] Stable ordering: same inputs → identical report bytes
- [ ] All gates listed in specs are represented
- [ ] Validator does not modify site worktree
- [ ] Exits non-zero on required gate failure
- [ ] Platform layout gate enforces V2 path structure
- [ ] TemplateTokenLint detects unresolved tokens
- [ ] Gate timeouts enforced per specs/09

**Severity**: INFO
**Action Required**: Implement TC-460, TC-570 (assign to agents, follow taskcard contracts)

---

## P-GAP-003 | INFO | PRManager Rollback Metadata Not Implemented (Expected)

**Taskcard**: TC-480 (W9 PRManager)
**Spec Authority**:
- `specs/12_pr_and_release.md:1-end` (PR creation, rollback requirements)
- `specs/34_strict_compliance_guarantees.md` (Guarantee L: rollback + recovery)
- `specs/17_github_commit_service.md:1-end` (commit service client)
- `specs/schemas/pr.schema.json:1-end` (PR artifact schema with rollback fields)

**Issue**: TC-480 not started, so no PR artifacts with rollback metadata yet

**Evidence**:
- `plans/traceability_matrix.md:487-493`:
  ```markdown
  - **Rollback metadata validation (runtime)**
    - Enforcer: Integrated into launch_validate
    - Spec: specs/34_strict_compliance_guarantees.md (Guarantee L), specs/12_pr_and_release.md
    - Enforces: PR artifacts include rollback metadata in prod profile (base_ref, run_id, rollback_steps, affected_paths)
    - Taskcards: TC-480 (PRManager)
    - Status: PENDING IMPLEMENTATION (See TC-480 - TC not started)
  ```

- `plans/taskcards/TC-480_pr_manager_w9.md:36-41`:
  ```markdown
  ### In scope
  - W9 worker implementation
  - Deterministic branch name and PR title/body templates
  - Commit service client calls in production mode
  - Persist **REQUIRED** `RUN_DIR/artifacts/pr.json` in prod profile (optional in local/ci) with:
    - PR URL and commit SHA
    - Rollback metadata per Guarantee L (base_ref, run_id, rollback_steps, affected_paths)
  - Associate commit SHA to telemetry outbox/client
  ```

- `plans/taskcards/TC-480_pr_manager_w9.md:135-138` (Acceptance checks):
  ```markdown
  ## Acceptance checks
  - [ ] PR payload is deterministic given same run_dir artifacts
  - [ ] `pr.json` validates against specs/schemas/pr.schema.json
  - [ ] pr.json includes rollback fields: base_ref, run_id, rollback_steps, affected_paths (Guarantee L)
  - [ ] Telemetry association of commit SHA recorded
  - [ ] Prod profile validation fails if pr.json missing rollback metadata
  ```

- `plans/taskcards/STATUS_BOARD.md:43`:
  ```markdown
  | TC-480 | W9 PRManager (commit service → PR) | Ready | unassigned | TC-470 | 3 paths | ... |
  ```

**Impact**:
- **Cannot create PRs** with rollback metadata until TC-480 implemented
- **Cannot satisfy Guarantee L** (rollback + recovery) in prod profile
- **Prod profile validation will fail** if pr.json missing rollback metadata

**Why This Is INFO (Not BLOCKER)**:
- This is **pre-implementation phase** — TC-480 being "Ready" is **expected**
- TC-480 **already includes rollback requirements** in taskcard spec:
  - Lines 36-41: "Persist **REQUIRED** pr.json with rollback metadata per Guarantee L"
  - Lines 135-138: Acceptance check for rollback fields present
- **No plan gap** — rollback fields are **already designed** in taskcard
- Only **missing implementation** (expected in pre-implementation phase)

**Proposed Fix**:
1. Implement TC-480 per taskcard spec:
   - Deterministic branch name from run_id + product_slug
   - Build PR body (gates summary, pages created/updated, TruthLock summary, resolved SHAs)
   - Call commit service (create branch, commit changes, open PR)
   - Write `pr.json` with **REQUIRED** rollback fields:
     - `base_ref` (branch PR targets)
     - `run_id` (link to run artifacts)
     - `rollback_steps` (instructions to revert)
     - `affected_paths` (files changed by run)
   - Emit telemetry association event

2. Validate pr.json against `specs/schemas/pr.schema.json`

3. Write evidence: `reports/agents/<agent>/TC-480/report.md`, `reports/agents/<agent>/TC-480/self_review.md`

**Dependencies**:
- **Upstream**: TC-470 (W8 Fixer) must be Done (validation_report.ok=true)
- **Downstream**: PRs can be created (final step of pipeline)

**Acceptance Criteria** (from taskcard):
- [ ] PR payload is deterministic given same run_dir artifacts
- [ ] `pr.json` validates against specs/schemas/pr.schema.json
- [ ] **pr.json includes rollback fields**: base_ref, run_id, rollback_steps, affected_paths (Guarantee L)
- [ ] Telemetry association of commit SHA recorded
- [ ] **Prod profile validation fails** if pr.json missing rollback metadata

**Severity**: INFO
**Action Required**: Implement TC-480 (assign to agent, follow taskcard contract with rollback fields)

---

## Additional Observations (No Gaps)

### ✅ All Preflight Gates Implemented

**Evidence**: `plans/traceability_matrix.md:242-315`

All preflight gates are ✅ **IMPLEMENTED** and **ready to use**:
- Gate 0: .venv policy validation (`tools/validate_dotvenv_policy.py`)
- Gate A1: Spec pack validation (`scripts/validate_spec_pack.py`)
- Gate B: Taskcard contract validation (`tools/validate_taskcards.py`)
- Gate E: Allowed paths overlap detection (`tools/audit_allowed_paths.py`)
- Gate J: Pinned refs policy (`tools/validate_pinned_refs.py`)
- Gate K: Supply chain pinning (`tools/validate_supply_chain_pinning.py`)
- Gate L: Secrets hygiene (`tools/validate_secrets_hygiene.py`)
- Gate M: No placeholders in production paths (`tools/validate_no_placeholders_production.py`)
- Gate N: Network allowlist validation (`tools/validate_network_allowlist.py`)
- Gate O: Budget validation (`tools/validate_budgets_config.py`)
- Gate P: Taskcard version locks (`tools/validate_taskcard_version_locks.py`)
- Gate Q: CI parity (`tools/validate_ci_parity.py`)
- Gate R: Untrusted code non-execution (`tools/validate_untrusted_code_policy.py`)

**Impact**: Swarm readiness can be validated **immediately** with:
```bash
python tools/validate_swarm_ready.py
```

No blocking issues for starting implementation.

### ✅ All Runtime Enforcers Implemented

**Evidence**: `plans/traceability_matrix.md:432-493`

All runtime enforcers are ✅ **IMPLEMENTED** and **ready for integration**:
- Path validation runtime enforcer (`src/launch/util/path_validation.py`) + tests
- Budget tracking runtime enforcer (`src/launch/util/budget_tracker.py`) + tests
- Diff analyzer runtime enforcer (`src/launch/util/diff_analyzer.py`) + tests
- Network allowlist runtime enforcer (`src/launch/clients/http.py`) + tests
- Subprocess execution blocker (`src/launch/util/subprocess.py`) + tests

**Pending**:
- Secret redaction runtime enforcer (TC-590, status: Ready)
- Floating ref rejection (runtime) — integration into TC-300 orchestrator + TC-460 validator
- Rollback metadata validation (runtime) — integration into TC-480 PRManager

**Impact**: Core compliance guarantees (B, D, F, G, J) are **already enforced** at runtime.

### ✅ Comprehensive Spec-to-Taskcard Mapping

**Evidence**: `plans/traceability_matrix.md:7-543`

All 35+ binding specs mapped to implementing taskcards:
- Core contracts: 6 specs → 5 taskcards (TC-100, TC-200, TC-300, etc.)
- Worker contracts: 1 spec → 9 taskcards (TC-400..480)
- Schemas: 20+ schemas → mapped to governing specs + validating gates
- Gates: 13 preflight + 14+ runtime → all mapped to validators/enforcers

**No orphaned specs detected.**

### ✅ Zero Write Fence Violations (By Design)

**Evidence**: `plans/swarm_coordination_playbook.md:54-76`, `plans/taskcards/00_TASKCARD_CONTRACT.md:22-31`

Shared library ownership enforced:
- `src/launch/io/**` → TC-200 (exclusive owner)
- `src/launch/util/**` → TC-200 (exclusive owner)
- `src/launch/models/**` → TC-250 (exclusive owner)
- `src/launch/clients/**` → TC-500 (exclusive owner)

Worker isolation guaranteed:
- Each worker (W1-W9) has exclusive ownership of implementation directory
- No path overlaps by design
- Validated by Gate E (`tools/audit_allowed_paths.py`)

**Impact**: Parallel agent swarms can execute without merge conflicts.

### ✅ All Taskcards Include Version Locks

**Evidence**: All sampled taskcards (TC-100, TC-200, TC-300, TC-400, TC-460, TC-480, TC-530, TC-570)

All taskcards include version lock fields:
```yaml
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323  # Commit SHA
ruleset_version: ruleset.v1
templates_version: templates.v1
```

**Validated by**: Gate B (`tools/validate_taskcards.py`), Gate P (`tools/validate_taskcard_version_locks.py`)

**Impact**: Reproducible builds, version traceability, compliance with Guarantee K.

---

## Gap Remediation Plan

### Phase 1: Foundation (No Gaps)
- ✅ All planning documents complete
- ✅ All taskcards have comprehensive specs
- ✅ All preflight gates implemented
- ✅ All runtime enforcers implemented (core guarantees)

### Phase 2: Implementation (Address INFO Gaps)

**P-GAP-001**: Implement TC-300 (Orchestrator)
- **Priority**: CRITICAL (prerequisite for all workers)
- **Assignee**: Implementation agent
- **Timeline**: Phase 1 implementation
- **Evidence**: `reports/agents/<agent>/TC-300/report.md`, `reports/agents/<agent>/TC-300/self_review.md`

**P-GAP-002**: Implement TC-460 (Validator) + TC-570 (Gates)
- **Priority**: HIGH (required for validation pipeline)
- **Assignee**: Implementation agent
- **Timeline**: Phase 5 implementation (after workers)
- **Evidence**: `reports/agents/<agent>/TC-460/report.md`, `reports/agents/<agent>/TC-570/report.md`

**P-GAP-003**: Implement TC-480 (PRManager with rollback)
- **Priority**: HIGH (required for PR creation)
- **Assignee**: Implementation agent
- **Timeline**: Phase 6 implementation (after validator)
- **Evidence**: `reports/agents/<agent>/TC-480/report.md` with rollback fields verification

### Phase 3: Validation (No Gaps Expected)

After all taskcards implemented:
- Run E2E pilots (TC-522 CLI, TC-523 MCP)
- Verify determinism (golden runs)
- Orchestrator master review (GO/NO-GO decision)

---

## Conclusion

**Total Gaps**: 3 (all INFO-level, non-blocking)

**Gap Assessment**:
- **P-GAP-001**: Orchestrator not started (expected, taskcard Ready)
- **P-GAP-002**: Runtime gates not started (expected, preflight gates all implemented)
- **P-GAP-003**: PRManager not started (expected, rollback fields already designed)

**Root Cause**: All gaps are due to **pre-implementation phase** (taskcards Ready, waiting for assignment), NOT plan deficiencies.

**Blocking Issues**: **ZERO**

**Action Required**:
1. Run preflight validation: `python tools/validate_swarm_ready.py`
2. Assign taskcards to agents (update YAML frontmatter: `owner`, `status: In-Progress`)
3. Regenerate STATUS_BOARD: `python tools/generate_status_board.py`
4. Begin implementation following Taskcards Contract

**Readiness**: ✅ **PLANS AND TASKCARDS ARE READY FOR IMPLEMENTATION**

No plan modifications required. All gaps will be resolved through taskcard execution.

---

**Gaps Report Generated**: 2026-01-27
**Auditor**: AGENT_P (Plans/Taskcards & Swarm Readiness Auditor)
**Gaps Identified**: 3 INFO-level (0 blocking)
**Remediation Plan**: Execute taskcards per contract (no plan changes needed)
# Repository Professionalism Gaps

**Agent:** AGENT_L
**Generated:** 2026-01-27
**Verification Run:** 20260127-1724

## Summary

**BLOCKER Gaps:** 0
**WARNING Gaps:** 0
**INFO Observations:** 2

**GO/NO-GO Impact:** ✅ GO (No blocking issues)

## Assessment

The repository documentation passes all professionalism checks. No broken links exist in binding documentation (specs, plans, root docs). All detected issues are informational observations about historical reports and non-binding reference material.

---

## INFO Observations

These are informational observations that do not block implementation. They document expected artifacts in historical reports and reference documentation.

### L-OBS-001 | INFO | Broken Links in Historical Agent Reports

**Category:** Historical Snapshot Artifacts
**File Locations:**
- `reports/agents/AGENT_D/WAVE2_LINKS_READMES/run_20260127_131045/`
- `reports/agents/AGENT_D/WAVE3_TRACEABILITY/run_20260127_133950/`
- `reports/pre_impl_verification/20260127-1518/agents/AGENT_L/`

**Issue:** Historical agent reports contain links to files that no longer exist or were part of transient work.

**Evidence:**
- 34 broken links detected in historical agent reports
- Examples:
  ```
  reports/agents/AGENT_D/WAVE2_LINKS_READMES/run_20260127_131045/changes.md:404
    Link: [self_review.md](self_review.md)

  reports/agents/AGENT_D/WAVE3_TRACEABILITY/run_20260127_133950/evidence.md:554
    Link: [specs/XX_name.md](XX_name.md) [placeholder example]
  ```

**Analysis:**
1. These reports are **point-in-time snapshots** documenting agent work
2. Links referenced transient files or work-in-progress structure
3. Reports serve as historical record, not active navigation
4. This is **expected behavior** for archived agent reports

**Impact:**
- **User Navigation:** None (historical reports are not primary navigation)
- **Implementation:** None (does not affect binding documentation)
- **Onboarding:** None (users navigate via root README → specs → plans)

**Proposed Action:**
- **Option 1:** Document in report README that historical reports may contain broken links (point-in-time snapshots)
- **Option 2:** Accept as-is (expected behavior for archived work)
- **Option 3:** Add archive notice to old verification run directories

**Recommendation:** Accept as-is. Historical agent reports are archival and self-documenting. Adding per-directory README files explaining "this is a snapshot" would add clutter without meaningful benefit.

---

### L-OBS-002 | INFO | TODO Markers in Non-Binding Documentation

**Category:** Reference Documentation and Templates
**File Locations:**
- `reports/**/*.md` (1,200+ markers in historical reports)
- `docs/**/*.md` (50+ markers in reference docs)
- `specs/templates/**/*.md` (100+ markers in template examples)

**Issue:** 1,535 TODO/TBD markers found in non-binding documentation.

**Evidence:**

**By Location:**
| Location | Count | Notes |
|----------|-------|-------|
| `/reports/` | ~1,200 | Historical agent reports, snapshots |
| `/specs/templates/` | ~100 | Template placeholders (intentional) |
| `/docs/` | ~50 | Reference documentation notes |
| Other | ~185 | Scattered across examples, prompts |

**Analysis:**
1. **Zero TODOs in binding specs** (`/specs/*.md`) ✅
2. **Zero TODOs in plans** (`/plans/*.md`) ✅
3. All detected markers are in:
   - Historical reports (documenting future work at time of writing)
   - Template examples (intentional placeholders showing example usage)
   - Reference documentation (improvement notes, not blocking)

**Example Contexts:**
```markdown
# In template example (intentional placeholder):
<!-- TODO: Replace with actual product name -->

# In historical report (point-in-time snapshot):
## Future Work
- TODO: Extend validation gates for X

# In reference docs (improvement note):
## Performance
Current implementation is adequate. TODO: Consider caching for scale.
```

**Impact:**
- **Spec Completeness:** None (0 TODOs in binding specs)
- **Implementation:** None (no incomplete work in binding docs)
- **Professionalism:** Low (markers are in non-binding, historical, or example content)

**Proposed Action:**
- **Binding Docs:** No action needed (already at 0 TODOs) ✅
- **Historical Reports:** Accept as-is (point-in-time snapshots document past state)
- **Templates:** Accept as-is (intentional placeholder examples)
- **Reference Docs:** Optional periodic review to:
  - Convert actionable items to tracked issues
  - Remove stale markers
  - Clarify improvement notes vs. blockers

**Recommendation:** No action required for implementation unblock. All TODOs are appropriately scoped to non-binding documentation.

---

## Detailed Breakdown: Broken Links

### By Category

| Category | Count | Severity | Notes |
|----------|-------|----------|-------|
| Broken links in repo files | 0 | N/A | ✅ All repo documentation links valid |
| Broken links in historical reports | 34 | INFO | Expected for point-in-time snapshots |
| Broken links in templates | 0 | N/A | ✅ All template links valid |

### Broken Link Patterns (Historical Reports)

1. **Self-referential links** (8 instances)
   - Example: `[self_review.md](self_review.md)` in directory without that file
   - Cause: Agent documented planned output that wasn't generated

2. **Cross-verification-run links** (9 instances)
   - Example: Links between `20260127-1518/` and `20260126_154500/` runs
   - Cause: Reports referenced other verification runs, directory structure changed

3. **Placeholder examples** (8 instances)
   - Example: `[specs/XX_name.md](XX_name.md)`
   - Cause: Documentation showing example link format

4. **Transient work references** (9 instances)
   - Example: Links to `WAVE1_QUICK_WINS` directories
   - Cause: Documented work that was reorganized or completed

---

## Traceability

**Contract Requirements:**
1. ✅ Broken internal links → BLOCKER: **0 found in repo files**
2. ✅ TODOs in binding specs → BLOCKER: **0 found**
3. ✅ Documentation professionalism → PASS: **Links navigable, no placeholders in binding docs**

**Evidence Files:**
- `audit_data.json` - Raw scan results (440 files, 1,829 links)
- `REPORT.md` - Detailed audit narrative
- `SELF_REVIEW.md` - 12-dimension self-assessment

**Files Scanned:**
- Binding specs: `/specs/*.md` (35 files) ✅
- Plans: `/plans/**/*.md` (80+ files) ✅
- Root docs: `/*.md` (16 files) ✅
- Reference docs: `/docs/*.md` (5 files) ✅
- Reports: `/reports/**/*.md` (250+ files) ℹ️
- Templates: `/specs/templates/**/*.md` (100+ files) ℹ️

---

## Conclusion

**No blocking gaps.** Repository documentation is professional, navigable, and complete. Observations document expected artifacts in historical reports (point-in-time snapshots with broken links) and informational TODO markers in non-binding documentation.

**Recommendation:** ✅ PROCEED with implementation. No remediation required.

---

**End of Gap Report**

*Generated by AGENT_L - Repository Professionalism Auditor*
