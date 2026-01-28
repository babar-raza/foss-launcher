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
