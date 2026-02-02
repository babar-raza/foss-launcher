# System Contract

## System-wide non-negotiables (binding)
1) **Scale**: designed to launch and maintain hundreds of products with diverse repo structures.
2) **LLM provider**: MUST use OpenAI-compatible APIs (example: Ollama OpenAI-compatible endpoint).
3) **MCP**: MUST expose MCP endpoints/tools for all features (not CLI-only).
4) **Telemetry**: MUST use centralized local-telemetry via HTTP API for all run events and all LLM operations.
5) **Commits**: MUST commit to aspose.org via a centralized GitHub commit service with configurable message/body templates.
6) **Adaptation**: MUST adapt to different repo structures and product platform/language via repo profiling and adapters.
7) **Change control + versioning**:
   - Every run MUST pin `ruleset_version` and `templates_version`.
   - Schema versions MUST be explicit in every artifact (`schema_version` fields).
   - Any behavior change MUST be recorded by bumping either the ruleset version, templates version, or schema version (no silent drift).

## Inputs
### 1) GitHub repo input
- `github_repo_url` (public)
  - **MUST** match allowed repository patterns per `specs/36_repository_url_policy.md` (Guarantee M)
  - **Standard pattern**: `https://github.com/{org}/aspose-{family}-foss-{platform}`
  - Valid families: 3d, barcode, cad, cells, diagram, email, finance, font, gis, html, imaging, note, ocr, page, pdf, psd, slides, svg, tasks, tex, words, zip
  - Valid platforms: android, cpp, dotnet, go, java, javascript, net, nodejs, php, python, ruby, rust, swift, typescript
- `github_ref` (branch, tag, or commit SHA). Required for determinism.

### 2) Site repo input
- `site_repo_url` (default: https://github.com/Aspose/aspose.org; see `specs/30_site_and_workflow_repos.md`)
  - **MUST** be exactly `https://github.com/Aspose/aspose.org` per `specs/36_repository_url_policy.md`
- `site_ref` (branch, tag, or commit SHA)

### 3) Workflow repo input
- `workflows_repo_url` (default: https://github.com/Aspose/aspose.org-workflows; see `specs/30_site_and_workflow_repos.md`)
  - **MUST** be exactly `https://github.com/Aspose/aspose.org-workflows` per `specs/36_repository_url_policy.md`
- `workflows_ref` (branch, tag, or commit SHA)

### 4) Launch config (run_config)
Must validate against `specs/schemas/run_config.schema.json` and include:
Note (binding):
- `run_config.locales` is the authoritative field for locale targeting.
- `run_config.locale` is a convenience alias for single-locale runs.
- If both are present, `locale` MUST equal `locales[0]` and `locales` MUST have length 1.

- product identity (slug, name, family)
- required sections (products/docs/reference/kb/blog)
- allowed_paths (write fence)
- ruleset_version, templates_version
- LLM provider params (temperature MUST default to 0.0)

## Outputs (authoritative artifacts)
A run MUST produce (at minimum) under `RUN_DIR` (see `specs/29_project_repo_structure.md`):
- `RUN_DIR/artifacts/repo_inventory.json`
- `RUN_DIR/artifacts/frontmatter_contract.json`
- `RUN_DIR/artifacts/site_context.json`
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- `RUN_DIR/artifacts/truth_lock_report.json`
- `RUN_DIR/artifacts/snippet_catalog.json`
- `RUN_DIR/artifacts/page_plan.json`
- `RUN_DIR/artifacts/patch_bundle.json`
- `RUN_DIR/artifacts/validation_report.json`
- `RUN_DIR/reports/diff_report.md`
- `RUN_DIR/events.ndjson` + `RUN_DIR/snapshot.json`
- PR metadata (when PR opened)

All JSON outputs MUST validate. Unknown keys are forbidden.

## Safety and scope (binding)
- **Allowed paths**:
  - The system MUST refuse to edit outside `run_config.allowed_paths`.
  - Any attempt to patch outside allowed_paths MUST fail the run with a blocker.
- **No direct commits in production mode**:
  - Direct `git commit` from orchestrator is forbidden in production mode.
  - Use the GitHub commit service contract in `specs/17_github_commit_service.md`.
- **No uncited claims**:
  - All factual statements in generated content MUST map to claim IDs and evidence anchors.

- **Emergency mode (manual content edits)**:
  - By default, `run_config.allow_manual_edits` MUST be **false** (or omitted).
  - If set to **true**, the system MAY accept manual edits **only** if:
    - every manually-edited file is explicitly listed in the orchestrator master review with rationale, and
    - each file has a patch/evidence record (before/after diff + validator context), and
    - the final validation report records `manual_edits=true` and enumerates the affected files.
  - This is an escape hatch for emergencies only and must never be used for routine runs.


## Error handling and operational semantics (binding)

### Failure classes
A run MUST classify outcomes into one of:
- **OK**: gate passed; `validation_report.ok=true`
- **FAILED**: deterministic failure that cannot be auto-fixed (e.g., missing required input)
- **BLOCKED**: failed due to policy, governance, or external dependency (e.g., commit service rejected)

### Error taxonomy
All raised errors MUST be mapped to a stable `error_code` (string) and MUST be written to:
- `RUN_DIR/events.ndjson` as an `ERROR` event
- `RUN_DIR/snapshot.json` (latest state)
- `RUN_DIR/artifacts/validation_report.json` as a **BLOCKER** issue when applicable

#### Error Code Format (binding)
Error codes MUST follow the pattern: `{COMPONENT}_{ERROR_TYPE}_{SPECIFIC}`

**Component identifiers**:
- `REPO_SCOUT` - W1 RepoScout
- `FACTS_BUILDER` - W2 FactsBuilder
- `SNIPPET_CURATOR` - W3 SnippetCurator
- `IA_PLANNER` - W4 IA Planner
- `SECTION_WRITER` - W5 SectionWriter
- `LINKER_PATCHER` - W6 Linker/Patcher
- `VALIDATOR` - W7 Validator
- `FIXER` - W8 Fixer
- `PR_MANAGER` - W9 PR Manager
- `ORCHESTRATOR` - Main orchestrator
- `SCHEMA` - Schema validation
- `GATE` - Validation gates
- `TELEMETRY` - Telemetry client
- `COMMIT_SERVICE` - GitHub commit service client
- `LLM` - LLM provider client

**Error types**:
- `CLONE` - Git clone/checkout errors
- `PARSE` - Parsing errors (YAML, JSON, TOML, etc.)
- `VALIDATION` - Schema validation errors
- `TIMEOUT` - Operation timeout
- `CONFLICT` - Merge/patch conflict
- `MISSING` - Required resource missing
- `NETWORK` - Network/transport errors
- `AUTH` - Authentication/authorization errors
- `POLICY` - Policy violation
- `INVARIANT` - Invariant violation (internal error)

**Examples**:
- `COMMIT_SERVICE_AUTH_FAILED` - GitHub commit service authentication failed
- `GATE_DETERMINISM_VARIANCE` - Re-running with identical inputs produces different outputs
- `GATE_TIMEOUT` - Validation gate exceeded timeout
- `LINKER_PATCHER_CONFLICT_UNRESOLVABLE` - Patch conflict cannot be auto-resolved
- `LLM_NETWORK_TIMEOUT` - LLM API call timed out
- `REPO_EMPTY` - Repository has zero files after clone (excluding .git/ directory)
- `REPO_SCOUT_CLONE_FAILED` - Failed to clone product repo
- `SCHEMA_VALIDATION_FAILED` - Artifact failed schema validation
- `SECTION_WRITER_UNFILLED_TOKENS` - LLM output contains unfilled template tokens like {{PRODUCT_NAME}}
- `SPEC_REF_INVALID` - spec_ref field is not a valid 40-character Git SHA
- `SPEC_REF_MISSING` - spec_ref field is required but not present in run_config/page_plan/pr
- `VALIDATOR_TRUTHLOCK_VIOLATION` - Uncited claim detected

#### Error Code Stability
Error codes MUST be stable across versions (do not rename without major version bump).
Error codes MUST be logged to telemetry for tracking and analysis.

**Related schemas**:
- [specs/schemas/issue.schema.json](schemas/issue.schema.json) - Issue schema includes error_code field
- [specs/schemas/validation_report.schema.json](schemas/validation_report.schema.json) - Validation report includes issues

### Exit codes (recommended)
- `0` success
- `2` validation/spec/schema failure
- `3` policy violation (allowed_paths, governance)
- `4` external dependency failure (commit service, telemetry API)
- `5` unexpected internal error

### Telemetry transport resilience
Telemetry MUST be treated as **required**, but transport failures MUST be handled safely:
- If telemetry POST fails, append the payload to `RUN_DIR/telemetry_outbox.jsonl`
- Retry outbox flush with bounded backoff
- Do not drop telemetry silently


## Determinism (binding)
- Temperature MUST default to 0.0.
- Artifact ordering MUST follow `specs/10_determinism_and_caching.md`.
- Fix loops MUST be single-issue-at-a-time and capped by `max_fix_attempts`.
- Runs MUST be replayable/resumable via event sourcing (see `specs/state-management.md`).

## Acceptance criteria
A run is successful when:
- All required artifacts exist and validate.
- All gates pass (`validation_report.ok=true`).
- Telemetry includes a complete event trail and LLM call logs.
- The PR includes:
  - summary of pages created/updated
  - evidence summary (facts and citations)
  - checklist results and validation report

## Field Definitions

This section defines critical fields used across configuration and artifact schemas.

### spec_ref Field

**Type:** string (required in run_config.json, page_plan.json, pr.json)

**Definition:** Git commit SHA (40-character hex) of the foss-launcher repository containing specs used for this run.

**Validation:**
- Must be exactly 40 hexadecimal characters
- Must resolve to actual commit in github.com/anthropics/foss-launcher
- Enforced by error codes: SPEC_REF_MISSING, SPEC_REF_INVALID (see error registry)

**Purpose:** Version locking for reproducibility (Guarantee K per specs/34:377-385)

**Example:** `"spec_ref": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"`

**Schema Enforcement:** Defined in run_config.schema.json, page_plan.schema.json, pr.schema.json

### validation_profile Field

**Type:** string (enum: "strict", "standard", "permissive") (optional in run_config.json, default: "standard")

**Definition:** Controls gate enforcement strength per specs/09:14-18

**Values:**
- **strict**: All gates must pass, warnings treated as errors
- **standard**: All gates must pass, warnings are warnings (default)
- **permissive**: Only BLOCKER-severity gates must pass, warnings ignored

**Validation:**
- Must be one of: "strict", "standard", "permissive"
- Enforced by run_config.schema.json enum constraint

**Purpose:** Allows flexible enforcement for different contexts (CI vs local dev vs experimentation)

**Example:** `"validation_profile": "strict"`

**Schema Enforcement:** Defined in run_config.schema.json:458 (already implemented)
