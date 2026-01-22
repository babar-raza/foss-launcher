# Worker Contracts (I/O, determinism, and handoffs)

## Purpose
Workers must be executable without guessing:
- what to read
- what to write
- what decisions they are allowed to make
- how they hand off to the next step

This document defines the minimum worker set and the binding artifact contracts.
Coordination and decision loops are defined in `specs/28_coordination_and_handoffs.md`.

## Global worker rules (binding)
- Workers MUST only read declared inputs.
- Workers MUST only write declared outputs.
- Workers MUST be idempotent: re-running with the same inputs MUST reproduce the same outputs.
- Every JSON artifact output MUST validate against its schema under `specs/schemas/`.
- If an input artifact is missing, the worker MUST fail with a **blocker** issue (`issue.schema.json`).
- All ordering MUST follow `specs/10_determinism_and_caching.md`.

## Common conventions

### Paths (authoritative)
All workers operate inside a run folder:

- `RUN_DIR = runs/<run_id>/`

- `runs/<run_id>/artifacts/` — JSON artifacts (schema-validated)
- `runs/<run_id>/drafts/<section>/` — draft Markdown (writer-only)
- `runs/<run_id>/reports/` — human-readable reports (optional)
- `runs/<run_id>/events.ndjson` — local event log (append-only)

### Required events (per worker run)
Each worker execution MUST emit:
- `WORK_ITEM_STARTED`
- `WORK_ITEM_FINISHED` or `WORK_ITEM_FAILED`

Each artifact write MUST emit:
- `ARTIFACT_WRITTEN` with `{ name, path, sha256, schema_id }`

If a worker opens or resolves issues:
- `ISSUE_OPENED` / `ISSUE_RESOLVED`

### Failure handling (binding)
- If a worker fails due to a retryable external error (network, 429, timeout), it MUST return a normalized retryable error.
- The Orchestrator decides retries and attempts (workers do not self-retry except for short internal retries like HTTP idempotent POST).
- Workers MUST never partially write an output artifact. Write to a temp file and atomically rename.

---

## Workers

### W1: RepoScout
**Goal:** clone and fingerprint the GitHub repo and the target site repo, then build `repo_inventory.json` and `frontmatter_contract.json` (site discovery).

**Inputs**
- `RUN_DIR/run_config.yaml` (or JSON equivalent; validated against `run_config.schema.json`)

**Outputs**
- `RUN_DIR/artifacts/repo_inventory.json` (schema: `repo_inventory.schema.json`)
- `RUN_DIR/artifacts/frontmatter_contract.json` (schema: `frontmatter_contract.schema.json`)
- `RUN_DIR/artifacts/site_context.json` (schema: `site_context.schema.json`)
- `RUN_DIR/artifacts/hugo_facts.json` (schema: `hugo_facts.schema.json`)

**Binding requirements**
- MUST record resolved SHAs:
  - `repo_inventory.repo_sha` (for github_repo_url + github_ref)
  - `repo_inventory.site_sha` (for site_repo_url + site_ref)

- MUST clone workflows repo (see `specs/30_site_and_workflow_repos.md`) into `RUN_DIR/work/workflows/` and record resolved SHA:
  - `site_context.workflows.resolved_sha`
- MUST scan Hugo configs under `RUN_DIR/work/site/configs/` and record:
  - `site_context.hugo.config_files` + `site_context.hugo.build_matrix` (see `specs/31_hugo_config_awareness.md`)
  - `RUN_DIR/artifacts/hugo_facts.json` (normalized facts; schema: `hugo_facts.schema.json`)
- FrontmatterContract discovery (binding):
  - MUST follow `specs/examples/frontmatter_models.md` deterministic discovery algorithm.
  - Sampling MUST be deterministic (sorted paths, fixed N, pinned in config or run_config).
  - Output MUST be written before planning begins.
- MUST compute `repo_profile`:
  - language/platform hints (e.g., python/.NET/node/java)
  - doc roots, example roots, test roots, source roots
  - adapter_id (selected per `specs/26_repo_adapters_and_variability.md`)
- MUST record file tree fingerprints deterministically (stable ordering + stable hashing).

---

### W2: FactsBuilder
**Goal:** build ProductFacts and EvidenceMap with stable claim IDs.

**Inputs**
- `RUN_DIR/artifacts/repo_inventory.json`
- repo worktree (read-only)
- optional: extra evidence URLs from run_config

**Outputs**
- `RUN_DIR/artifacts/product_facts.json` (schema: `product_facts.schema.json`)
- `RUN_DIR/artifacts/evidence_map.json` (schema: `evidence_map.schema.json`)

**Binding requirements**
- Claim IDs MUST be stable:
  - `claim_id = sha256(normalized_claim_text + evidence_anchor + ruleset_version)`
- All factual statements MUST be represented as claims with evidence anchors (repo path + line range or URL + fragment).
- If `run_config.allow_inference=false`:
  - MUST NOT emit speculative claims (no “likely”, “probably”, “supports many formats”, etc.)
  - MUST open a blocker issue `EvidenceMissing` when a required claim cannot be evidenced.

---

### W3: SnippetCurator
**Goal:** extract, normalize, and tag reusable code snippets with provenance.

**Inputs**
- `RUN_DIR/artifacts/repo_inventory.json`
- `RUN_DIR/artifacts/product_facts.json`
- repo worktree (read-only)

**Outputs**
- `RUN_DIR/artifacts/snippet_catalog.json` (schema: `snippet_catalog.schema.json`)

**Binding requirements**
- Every snippet MUST include:
  - `source_path`, `start_line`, `end_line`, `language`
  - stable `snippet_id` derived from `{path, line_range, sha256(content)}`
- Snippets MUST be normalized deterministically:
  - line endings `\n`, trailing whitespace trimmed, no reformatting that changes meaning
- Tags MUST be stable and derived from the ruleset (not ad-hoc freeform).

---

### W4: IAPlanner
**Goal:** produce a complete PagePlan before any writing.

**Inputs**
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- `RUN_DIR/artifacts/snippet_catalog.json`
- run_config
- `RUN_DIR/artifacts/frontmatter_contract.json` (schema: `frontmatter_contract.schema.json`)
- site worktree (read-only, under allowed_paths)

**Outputs**
- `RUN_DIR/artifacts/page_plan.json` (schema: `page_plan.schema.json`)

**Binding requirements**
- MUST select templates deterministically from:
  - `specs/templates/<subdomain>/<family>/<locale>/...` (see `specs/20_rulesets_and_templates_registry.md`)
- MUST define for each planned page:
  - target path
  - template id + variant
  - required claim IDs
  - required snippet tags
  - internal link targets
- MUST respect `run_config.required_sections`:
  - if a required section cannot be planned, open a blocker issue `PlanIncomplete`.

---

### W5: SectionWriter (one per section)
**Goal:** draft Markdown for the pages assigned to that section.

**Inputs**
- `RUN_DIR/artifacts/page_plan.json`
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- `RUN_DIR/artifacts/snippet_catalog.json`
- `specs/templates/**` + ruleset (read-only)

**Outputs**
- `RUN_DIR/drafts/<section>/<output_path>` (mirrors `page_plan.pages[].output_path`; see `specs/29_project_repo_structure.md`)

**Binding requirements**
- MUST embed claim markers for every factual sentence/bullet (see `specs/23_claim_markers.md`).
- MUST only use snippets referenced by `required_snippet_tags` unless the plan explicitly allows extras.
- MUST fill and then remove all template tokens:
  - all `__UPPER_SNAKE__` placeholders
  - all `__BODY_*__` scaffolding placeholders
- MUST NOT:
  - modify the site worktree
  - write artifacts under `RUN_DIR/artifacts/` (writer only writes drafts)

---

### W6: LinkerAndPatcher
**Goal:** convert drafts into a PatchBundle and apply to the site worktree deterministically.

**Inputs**
- `RUN_DIR/drafts/**`
- `RUN_DIR/artifacts/page_plan.json`
- site worktree (writeable, restricted by allowed_paths)
- `specs/templates/**` registry + ruleset (read-only)

**Outputs**
- `RUN_DIR/artifacts/patch_bundle.json` (schema: `patch_bundle.schema.json`)
- `RUN_DIR/reports/diff_report.md` (human-readable)

**Binding requirements**
- MUST apply patches in deterministic order:
  - by section order, then by planned page path
- MUST ensure only allowed_paths are changed:
  - if a patch touches an out-of-scope path, open blocker `AllowedPathsViolation`
- MUST maintain stable frontmatter formatting per template contract.
- MUST not introduce unresolved template tokens.

---

### W7: Validator
**Goal:** run all validation gates and produce a single ValidationReport.

**Inputs**
- site worktree (current)
- `RUN_DIR/artifacts/page_plan.json`
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- `RUN_DIR/artifacts/patch_bundle.json` (if present)
- toolchain lock (see `specs/19_toolchain_and_ci.md`)

**Outputs**
- `RUN_DIR/artifacts/validation_report.json` (schema: `validation_report.schema.json`)

**Binding requirements**
- MUST run all required gates (see `specs/09_validation_gates.md`).
- MUST normalize tool outputs into stable issue objects:
  - stable ordering and stable IDs (see `specs/schemas/issue.schema.json`)
- MUST never “fix” issues (validator is read-only).

---

### W8: Fixer
**Goal:** apply the minimal change required to fix exactly one selected issue.

**Inputs**
- `RUN_DIR/artifacts/validation_report.json`
- `RUN_DIR/artifacts/page_plan.json`
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- site worktree (writeable, restricted by allowed_paths)
- toolchain lock + ruleset

**Outputs**
- One of:
  - updated draft(s) under `drafts/<section>/...` **and** a new `patch_bundle.json` via W6 rerun
  - or a direct patch delta: `RUN_DIR/artifacts/patch_bundle.delta.json` (optional strategy)
- a note in `reports/fix_<issue_id>.md` (optional)

**Binding requirements**
- MUST fix exactly one issue: the issue_id supplied by the Orchestrator.
- MUST obey gate-specific fix rules in `specs/08_patch_engine.md`.
- MUST NOT introduce new factual claims without evidence.
- MUST fail with blocker `FixNoOp` if it cannot produce a meaningful diff.

---

### W9: PRManager
**Goal:** open a PR via the commit service with deterministic branch naming and PR body.

**Inputs**
- site worktree diff (current)
- `RUN_DIR/reports/diff_report.md`
- `RUN_DIR/artifacts/validation_report.json`
- run_config (commit templates)

**Outputs**
- `RUN_DIR/artifacts/pr.json` (optional; includes pr_url, branch, commit_sha)

**Binding requirements**
- MUST call the GitHub commit service (`specs/17_github_commit_service.md`) in production mode.
- MUST associate the resulting commit_sha to telemetry (`specs/16_local_telemetry_api.md`).
- MUST include a PR checklist summary:
  - gates passed
  - pages created/updated
  - evidence summary / TruthLock summary

---

## Acceptance
- Every worker has a complete, non-overlapping responsibility.
- All handoffs are file-based and schema-validated.
- A full dependency chain exists from RepoScout → PRManager with no hidden inputs.
