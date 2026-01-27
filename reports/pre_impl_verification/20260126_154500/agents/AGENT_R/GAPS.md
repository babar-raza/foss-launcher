# AGENT_R: Requirements Gaps & Ambiguities

**Purpose**: Document all identified gaps, ambiguities, and implied-but-undocumented requirements discovered during requirements extraction.

**Format**: `GAP-ID | SEVERITY | Description | Evidence | Proposed Fix`

**Severity Levels**:
- **BLOCKER**: Must be resolved before implementation
- **ERROR**: Significant gap that will cause implementation problems
- **WARN**: Ambiguity that should be clarified
- **INFO**: Minor gap or enhancement opportunity

---

## Identified Gaps (18 total)

### R-GAP-001 | BLOCKER | Validator determinism not specified

**Description**: Validation gates must be deterministic, but stability requirements for validator outputs are not explicitly defined.

**Evidence**:
- specs/09_validation_gates.md defines gates but lacks requirement: "Validator outputs (validation_report.json) shall have stable issue IDs and ordering across runs with identical inputs"
- specs/10_determinism_and_caching.md:51 requires "byte-identical artifacts" but does not explicitly list validation_report.json

**Impact**: Without this, validation_report.json may have non-deterministic timestamp variance, event ordering differences, or unstable issue IDs, breaking determinism acceptance criteria.

**Proposed Fix**:
Add to specs/09_validation_gates.md:
```markdown
## Determinism Requirements for Validators

Validators MUST produce deterministic outputs:
- Issue IDs MUST be stable: derived from (gate_name, location.path, location.line, issue_type)
- Issue ordering MUST follow specs/10_determinism_and_caching.md severity ranking
- Timestamps in validation_report MUST use run start time (not wall-clock during validation)
- Tool output parsing MUST normalize timestamps and non-deterministic fields
```

---

### R-GAP-002 | BLOCKER | Exit code contract incomplete

**Description**: specs/01_system_contract.md:141-146 defines "recommended" exit codes but does not specify whether they are mandatory or which components must honor them.

**Evidence**:
```
141 ### Exit codes (recommended)
142 - `0` success
143 - `2` validation/spec/schema failure
144 - `3` policy violation (allowed_paths, governance)
145 - `4` external dependency failure (commit service, telemetry API)
146 - `5` unexpected internal error
```

Word "recommended" conflicts with determinism requirement.

**Impact**: Without binding exit codes, CI/orchestration cannot distinguish failure types. Scripts will use inconsistent exit codes.

**Proposed Fix**:
Change specs/01_system_contract.md:141 to:
```markdown
### Exit codes (binding)
All launcher commands MUST use these exit codes:
```
Add enforcement: "Orchestrator and workers MUST map error classes to these exit codes."

---

### R-GAP-003 | ERROR | "Grounding" threshold undefined

**Description**: Multiple specs require claims to be "grounded" but do not define what constitutes sufficient evidence.

**Evidence**:
- specs/06_page_planning.md:51: "All required sections have at least minimum pages" (what is "minimum"?)
- specs/07_section_templates.md:61: "All limitations must be grounded claims." (what makes a claim grounded?)
- specs/09_validation_gates.md:175: "pages MUST demonstrate grounding" (no metric defined)

**Impact**: TruthLock gate cannot enforce grounding without quantitative criteria. Agents will guess.

**Proposed Fix**:
Add to specs/04_claims_compiler_truth_lock.md:
```markdown
## Grounding Criteria

A claim is grounded if:
1. EvidenceMap entry exists with truth_status=direct OR inferred_with_evidence
2. At least one citation exists with path + line_range
3. Citation source is repo_sha-locked (not external URL without archive)

A claim is NOT grounded if:
- truth_status=inference_only AND allow_inference=false
- citations array is empty
- citation source is URL-only without snapshot
```

---

### R-GAP-004 | ERROR | "Minimal" vs "Rich" launch tier undefined

**Description**: specs/09_validation_gates.md:175 references launch_tier but tier definitions are missing.

**Evidence**:
```
175 - If `launch_tier=minimal`, pages MUST NOT include exhaustive API lists or ungrounded workflow claims.
176 - If `launch_tier=rich`, pages MUST demonstrate grounding (claim_groups -> snippets) before expanding page count.
```

**Impact**: run_config schema does not define launch_tier enum. Workers cannot check tier. Gate cannot enforce.

**Proposed Fix**:
1. Add to specs/schemas/run_config.schema.json:
```json
"launch_tier": {
  "type": "string",
  "enum": ["minimal", "rich"],
  "description": "Content depth strategy"
}
```
2. Add tier definitions to specs/06_page_planning.md:
```markdown
## Launch Tiers

- **minimal**: Quickstart + top 3 features + install. Max 10 pages total. No exhaustive API lists.
- **rich**: Full feature coverage + workflows + API reference. Requires claim_groups and snippet grounding for all workflows.
```

---

### R-GAP-005 | ERROR | Timeout values lack rationale

**Description**: specs/09_validation_gates.md:90-113 defines gate timeout values (e.g., "Schema validation: 30s") but does not explain derivation or allow customization.

**Evidence**:
```
90 **local profile** (development):
91 - Schema validation: 30s per artifact
```

**Impact**: 30s may be too short for large artifact files. No guidance on when to adjust. No config override.

**Proposed Fix**:
Add to specs/09_validation_gates.md:
```markdown
### Timeout Customization

Default timeout values assume:
- Artifact files < 10MB
- Modern CPU (4+ cores)
- Hugo site < 10k pages

Override via run_config.gate_timeouts:
```yaml
gate_timeouts:
  schema_validation_s: 60  # override default 30s
```
Orchestrator MUST merge run_config overrides with profile defaults.
```

---

### R-GAP-006 | ERROR | Change budget thresholds lack context

**Description**: specs/34_strict_compliance_guarantees.md:202-204 defines change budget policy with hardcoded limits but no rationale.

**Evidence**:
```
202 **Change budget policy** (binding):
203 - Maximum lines changed per file: 500 (configurable in `run_config.budgets.max_lines_per_file`)
204 - Maximum files changed per run: 100 (configurable in `run_config.budgets.max_files_changed`)
```

**Impact**: 500 lines/file may be too restrictive for initial product launch (creating many new files). Agents don't know when to request exception.

**Proposed Fix**:
Add context to specs/34_strict_compliance_guarantees.md:
```markdown
**Rationale**:
- 500 lines/file: Limit based on reviewability (one screen of diff context)
- 100 files/run: Prevents mass-edit accidents, keeps PRs focused

**Exceptions**:
- Initial product launch: Request increase to 1000 lines/file, 200 files
- Formatting-only changes: Separate PR, requires explicit approval
```

---

### R-GAP-007 | WARN | "Near-identical diffs" too vague

**Description**: specs/00_overview.md:22 states "Same inputs -> same plan -> near-identical diffs" but "near-identical" is not quantified.

**Evidence**:
```
22 - Same inputs -> same plan -> near-identical diffs.
```

**Impact**: Cannot measure determinism if "near" is undefined. What variance is acceptable?

**Proposed Fix**:
Replace "near-identical" with:
```markdown
- Same inputs -> same plan -> byte-identical diffs (PagePlan, PatchBundle, drafts)
- Allowed variance: timestamps in events.ndjson only
```
Update specs/10_determinism_and_caching.md to specify exactly which files must be byte-identical.

---

### R-GAP-008 | WARN | Snippet "priority" undefined

**Description**: specs/05_example_curation.md lists 5 snippet sources with implicit priority (1-5) but does not define selection algorithm when multiple candidates exist.

**Evidence**:
```
61 5) Generated minimal snippets (only when 1-4 yield nothing for a required workflow)
```

**Impact**: SnippetCurator may select suboptimal snippets. Different runs may pick different candidates.

**Proposed Fix**:
Add to specs/05_example_curation.md:
```markdown
## Selection Algorithm

When multiple snippets match a required tag:
1. Filter by source priority (repo_file > docs_example > test_adapted > llm_validated > llm_minimal)
2. If multiple remain, prefer shortest (line count)
3. If tie, prefer lexicographically first path
4. Record selection rationale in snippet_catalog.selection_notes
```

---

### R-GAP-009 | WARN | "Bounded concurrency" unspecified

**Description**: specs/00_overview.md:16 requires "bounded concurrency" but does not define the bound or configuration.

**Evidence**:
```
16 - The system must support batch execution (queue many runs) with bounded concurrency.
```

**Impact**: Orchestrator cannot implement without concurrency limit. Risk of unbounded parallelism.

**Proposed Fix**:
Add to specs/01_system_contract.md:
```markdown
### Concurrency Control

run_config.concurrency (required for batch mode):
- max_parallel_workers: Maximum W5 SectionWriters running simultaneously (default: 5)
- max_parallel_runs: Maximum concurrent runs (default: 1, increase for batch)
```

---

### R-GAP-010 | WARN | FrontmatterContract sampling not fully deterministic

**Description**: specs/examples/frontmatter_models.md:29 requires "intersection of keys across sampled set" but does not specify sample size or file selection order.

**Evidence**:
```
29 - required_keys = intersection of keys across the sampled set (excluding obviously variable keys like "date" unless present in >= 90% of samples)
```

**Impact**: Different agents may sample different files, yielding different required_keys.

**Proposed Fix**:
Add to specs/examples/frontmatter_models.md:
```markdown
## Deterministic Sampling

Sample selection:
1. Discover all *.md files in section
2. Sort paths lexicographically
3. Sample every Nth file (N = total_files / 20, min N=1)
4. Take first 20 samples (or all if < 20 files)

Sample size MUST be recorded in frontmatter_contract.sample_metadata.
```

---

### R-GAP-011 | WARN | Retry policy undefined for external dependencies

**Description**: specs/01_system_contract.md:149-152 defines telemetry retry but does not specify retry count, backoff strategy, or max duration.

**Evidence**:
```
150 - If telemetry POST fails, append the payload to `RUN_DIR/telemetry_outbox.jsonl`
151 - Retry outbox flush with bounded backoff
```

**Impact**: "Bounded backoff" is ambiguous. Agents will implement different strategies.

**Proposed Fix**:
Add to specs/16_local_telemetry_api.md:
```markdown
## Retry Policy (Binding)

On telemetry POST failure:
1. Append to telemetry_outbox.jsonl
2. Retry with exponential backoff: 1s, 2s, 4s, 8s, 16s (max 5 attempts)
3. If all retries fail, continue run (telemetry is non-fatal)
4. Emit warning event: TELEMETRY_TRANSPORT_FAILED

Same policy applies to commit service calls.
```

---

### R-GAP-012 | INFO | Platform detection confidence threshold unspecified

**Description**: specs/24_mcp_tool_schemas.md:231 states "both family and platform must exceed 80% confidence" but does not define how confidence is calculated.

**Evidence**:
```
231 - Confidence threshold: both family and platform must exceed 80% confidence
```

**Impact**: RepoScout cannot compute confidence without algorithm. Different adapters may calculate differently.

**Proposed Fix**:
Add to specs/02_repo_ingestion.md:
```markdown
## Platform Detection Confidence

Confidence = (primary_manifest_count + secondary_manifest_count * 0.5 + doc_keyword_matches * 0.1) / 3.0

Example (Python):
- pyproject.toml found: +1.0
- requirements.txt found: +0.5
- README mentions "pip install": +0.1
- Confidence = (1.0 + 0.5 + 0.1) / 3.0 = 53%

If confidence < 80%, set platform_family = "unknown"
```

---

### R-GAP-013 | INFO | Cache invalidation strategy missing

**Description**: specs/10_determinism_and_caching.md defines cache keys but does not specify when to invalidate or how to handle stale cache.

**Evidence**:
```
31 cache_key = sha256(model_id + "|" + prompt_hash + "|" + inputs_hash)
```

**Impact**: Workers may use stale cached artifacts after spec changes. No cache TTL defined.

**Proposed Fix**:
Add to specs/10_determinism_and_caching.md:
```markdown
## Cache Invalidation

Cache entry is invalid if:
1. ruleset_version changed since cache write
2. templates_version changed
3. Schema version of cached artifact != current schema version
4. Cache entry age > 30 days (configurable)

Orchestrator MUST validate cache before use.
```

---

### R-GAP-014 | INFO | "Stable ordering" for sections not defined

**Description**: specs/10_determinism_and_caching.md:42 requires "sections in config order" but config order is not specified.

**Evidence**:
```
42 - sections in config order
```

**Impact**: If run_config.required_sections is a set (not ordered list), sorting is ambiguous.

**Proposed Fix**:
Update specs/schemas/run_config.schema.json:
```json
"required_sections": {
  "type": "array",
  "description": "Ordered list of sections (order is binding for determinism)",
  "items": {"type": "string"}
}
```

Clarify in specs/10_determinism_and_caching.md: "Section order MUST match array order in run_config.required_sections"

---

### R-GAP-015 | INFO | Patch conflict resolution strategy undefined

**Description**: specs/08_patch_engine.md:37 forbids writes outside allowed_paths but does not specify behavior when patch conflicts occur.

**Evidence**:
- specs/08_patch_engine.md:26: "Patch apply must be idempotent"
- No conflict resolution algorithm defined

**Impact**: If two patches modify same line, patch engine behavior is undefined. May fail or corrupt.

**Proposed Fix**:
Add to specs/08_patch_engine.md:
```markdown
## Conflict Resolution

On patch conflict (same file, overlapping line ranges):
1. Fail immediately with blocker: LINKER_PATCHER_CONFLICT_UNRESOLVABLE
2. Record conflicting patch IDs in issue details
3. Do NOT attempt automatic merge
4. Orchestrator MAY retry with conflict-aware planning
```

---

### R-GAP-016 | INFO | Phantom path handling incomplete

**Description**: specs/02_repo_ingestion.md:91-100 defines phantom path detection but does not specify how to handle phantom paths in later stages.

**Evidence**:
```
98 - If the phantom path was claimed as an examples source, mark related claims with `confidence: low`
```

**Impact**: What happens to low-confidence claims? Are they skipped? Labeled? No downstream behavior defined.

**Proposed Fix**:
Add to specs/03_product_facts_and_evidence.md:
```markdown
## Low-Confidence Claims

Claims with confidence=low (from phantom paths):
- MUST be labeled in content with "(unverified)" suffix
- MUST NOT be used for Key Features section
- MAY be used for "Planned Features" section if allow_inference=true
```

---

### R-GAP-017 | INFO | Binary asset size limit undefined

**Description**: specs/02_repo_ingestion.md:114 requires recording binary assets but does not define size threshold for "large artifacts".

**Evidence**:
```
114 Binary and large artifacts (e.g., `testfiles/`, `assets/`, `.pdf`, `.one`, `.png`, `.zip`) MUST be recorded
```

**Impact**: What size is "large"? Should 1KB PNG be recorded same as 100MB ZIP?

**Proposed Fix**:
Add to specs/02_repo_ingestion.md:
```markdown
## Binary Asset Classification

Record binary assets with:
- Path
- File size
- SHA256 (for files < 10MB only)
- Asset type (image, document, archive, other)

Skip recording if:
- File size > 100MB (note as oversized_asset in repo_inventory.warnings)
- File in .git/ or node_modules/ (ignore)
```

---

### R-GAP-018 | INFO | Fix loop termination criteria ambiguous

**Description**: specs/01_system_contract.md:158 requires "Fix loops MUST be single-issue-at-a-time and capped by max_fix_attempts" but does not define what happens when cap is reached.

**Evidence**:
```
158 - Fix loops MUST be single-issue-at-a-time and capped by `max_fix_attempts`.
```

**Impact**: If max_fix_attempts reached with issues remaining, does run fail? Continue with warnings?

**Proposed Fix**:
Add to specs/21_worker_contracts.md (W8 Fixer section):
```markdown
## Fix Loop Termination

If max_fix_attempts reached:
1. Stop fix loop
2. Emit final validation_report with remaining issues
3. Set validation_report.ok = false
4. Run status = FAILED (not BLOCKED, unless all remaining issues are blockers)
5. Orchestrator MUST NOT open PR
```

---

## Summary Statistics

- **Total gaps identified**: 18
- **BLOCKER severity**: 2
- **ERROR severity**: 5
- **WARN severity**: 5
- **INFO severity**: 6

---

## Recommended Resolution Priority

### Phase 1 (Before implementation start)
1. R-GAP-001: Validator determinism (critical for acceptance)
2. R-GAP-002: Exit code contract (critical for CI/orchestration)
3. R-GAP-003: Grounding threshold (critical for TruthLock gate)
4. R-GAP-004: Launch tier definitions (critical for planning)

### Phase 2 (During worker implementation)
5. R-GAP-005: Timeout customization
6. R-GAP-006: Change budget context
7. R-GAP-008: Snippet selection algorithm
8. R-GAP-011: Retry policy
9. R-GAP-015: Patch conflict resolution

### Phase 3 (Polish)
10. R-GAP-007: Determinism quantification
11. R-GAP-009: Concurrency bounds
12. R-GAP-010: Sampling determinism
13. R-GAP-012: Confidence calculation
14. R-GAP-013: Cache invalidation
15. R-GAP-014: Section ordering
16. R-GAP-016: Low-confidence claim handling
17. R-GAP-017: Binary asset size limits
18. R-GAP-018: Fix loop termination

---

## Gaps NOT Created (Explicit Decisions)

The following were considered but NOT logged as gaps:

1. **"Recommend" vs "Should"**: Some specs use "recommend" (e.g., exit codes, toolchain containers). Interpreted as non-binding suggestions, not requirements. If these should be mandatory, gaps would exist.

2. **Implicit schema requirements**: JSON schemas have "required" fields. These were treated as requirements (e.g., REQ-CFG-001 to REQ-CFG-011) but not logged as gaps because schema is the specification.

3. **Worker implementation details**: Specs define what workers produce, not how. Internal implementation decisions (e.g., "use httpx vs requests") were not logged as gaps.

4. **Test coverage levels**: No spec defines % code coverage required. Assumed this is implementation decision, not requirement gap.

---

**End of Gaps Report**
