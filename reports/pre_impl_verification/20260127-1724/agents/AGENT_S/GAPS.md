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
