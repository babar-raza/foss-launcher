# FOSS Launcher System Architecture

This document provides a comprehensive overview of how the foss-launcher system works.

**Note**: This is a **non-binding reference document** for engineers and contributors. The binding contract is defined in the `specs/` folder.

---

## Table of Contents

1. [System Purpose](#system-purpose)
2. [Directory Structure](#directory-structure)
3. [Core Execution Flow](#core-execution-flow)
4. [Main Components](#main-components)
5. [Pilots: Golden Runs for Regression Detection](#pilots-golden-runs-for-regression-detection)
6. [How Pilots Work vs Real Products](#how-pilots-work-vs-real-products)
7. [Validation & Gate System](#validation--gate-system)
8. [Safety & Scope Enforcement](#safety--scope-enforcement)
9. [Determinism Requirements](#determinism-requirements)
10. [Artifact Model (RUN_DIR)](#artifact-model-run_dir)
11. [Observability & Telemetry](#observability--telemetry)
12. [System-Wide Non-Negotiables](#system-wide-non-negotiables)
13. [High-Level Data Flow](#high-level-data-flow)

---

## System Purpose

The foss-launcher is an **AI-agent-powered content generation pipeline** that takes a GitHub repository for a software product and automatically generates comprehensive technical documentation for the Hugo-based aspose.org website, creating/updating content across multiple sections: **products**, **docs**, **reference**, **kb** (knowledge base), and **blog**.

**High-level goal**: Given a public GitHub repository, produce a validated patch bundle with markdown documentation and open a PR against the site repo, ensuring all content is grounded in evidence, passes validation gates, and adheres to quality standards.

---

## Directory Structure

```
foss-launcher/
├── specs/                    # Binding specification documents (27 specs + schemas)
│   ├── 00_overview.md       # System-wide goals
│   ├── 01_system_contract.md # Contract + error codes (CRITICAL)
│   ├── 02_repo_ingestion.md
│   ├── 03_product_facts_and_evidence.md
│   ├── 06_page_planning.md
│   ├── 09_validation_gates.md (13 validation gates)
│   ├── 13_pilots.md         # Golden runs for regression detection
│   ├── 21_worker_contracts.md (W1-W9 workers)
│   └── schemas/             # JSON Schema definitions (.schema.json files)
│
├── src/launch/              # Python implementation (~20 modules)
│   ├── orchestrator/        # LangGraph state machine
│   │   ├── graph.py        # Core state transitions
│   │   ├── run_loop.py     # Run execution and event handling
│   │   └── worker_invoker.py
│   ├── workers/            # 9 worker implementations
│   │   ├── w1_repo_scout/   # Repo ingestion & profiling
│   │   ├── w2_facts_builder/
│   │   ├── w3_snippet_curator/
│   │   ├── w4_ia_planner/
│   │   ├── w5_section_writer/
│   │   ├── w6_linker_and_patcher/
│   │   ├── w7_validator/    # 13 validation gates
│   │   ├── w8_fixer/
│   │   └── w9_pr_manager/
│   ├── state/              # Event sourcing & snapshots
│   ├── models/             # Schema-aligned data models
│   ├── validators/         # Gate implementations
│   └── [other modules]     # inference, clients, observability, security...
│
├── configs/                # Run configurations
│   ├── pilots/            # Pinned pilot configs (deterministic regression tests)
│   └── products/          # Product-specific configs (one per product)
│
├── plans/                 # Implementation taskcards & coordination
│   ├── taskcards/        # TC-300, TC-400, etc. (actual work units)
│   ├── prompts/          # Agent coordination prompts
│   └── policies/         # No manual content edits, etc.
│
├── docs/                 # Architecture docs & references (this file!)
│
└── runs/                 # Runtime artifacts (created during execution)
    └── <run_id>/        # One per run
        ├── artifacts/  # JSON artifacts (repo_inventory, product_facts, etc.)
        ├── drafts/    # .md drafts per section
        ├── work/      # Cloned repos (product, site, workflows)
        ├── reports/   # Human-readable reports
        ├── events.ndjson  # Append-only event log (event sourcing)
        └── snapshot.json  # Materialized state snapshot
```

---

## Core Execution Flow

### Inputs

1. **GitHub Repo** (`github_repo_url`, `github_ref` - SHA pinned for determinism)
2. **Site Repo** (`site_repo_url`, `site_ref` - default: aspose.org)
3. **Workflows Repo** (`workflows_repo_url`, `workflows_ref`)
4. **Run Config** (`run_config.yaml` - validated against schema):
   - Product identity (slug, name, family)
   - Required sections (products/docs/reference/kb/blog)
   - `allowed_paths` (write fence - prevents unauthorized writes)
   - `ruleset_version`, `templates_version` (for determinism)
   - `validation_profile` (local/ci/prod - affects gate strictness)
   - LLM provider params (temperature defaults to 0.0)

### Control Flow (Binding State Machine)

```
CREATED
   ↓
CLONE_INPUTS (W1 RepoScout) → CLONED_INPUTS
   ↓
INGESTED (reserved for future)
   ↓
BUILD_FACTS (W2 FactsBuilder + W3 SnippetCurator) → FACTS_READY
   ↓
PLAN_PAGES (W4 IAPlanner) → PLAN_READY
   ↓
DRAFT_SECTIONS (W5 SectionWriter) → DRAFT_READY
   ↓
LINK_AND_PATCH (W6 LinkerAndPatcher) → LINKING
   ↓
VALIDATE (W7 Validator) ──→ VALIDATING ──┐
   ↓                                       ├─ 13 gates
   ├─ no issues ────────────→ READY_FOR_PR
   │
   ├─ blocker issues + attempts left ──→ FIX (W8 Fixer) ──┐
   │                                                        └─ loops back to VALIDATE
   │
   └─ blocker issues + max attempts ──→ FAILED

READY_FOR_PR
   ↓
OPEN_PR (W9 PRManager) → PR_OPENED
   ↓
FINALIZE → DONE
```

---

## Main Components

### Orchestrator (LangGraph State Machine)

Located in `src/launch/orchestrator/`:

- **graph.py**: Defines the state graph with 11 nodes
  - Uses LangGraph StateGraph for deterministic execution
  - Nodes map 1:1 to orchestrator states
  - Conditional edges for validation → fix or PR decision

- **run_loop.py**: Single-run execution engine
  - Creates RUN_DIR structure
  - Emits events (RUN_CREATED, RUN_STATE_CHANGED, etc.)
  - Manages event sourcing & snapshots

- **worker_invoker.py**: Invokes workers deterministically
  - Passes worker inputs/outputs
  - Generates trace_id/span_id for observability
  - Manages worker failure handling

### Workers (9 Specialized Components)

Each worker is a **deterministic, contract-driven step** with defined inputs/outputs:

| Worker | Purpose | Key Inputs | Key Outputs |
|--------|---------|-----------|------------|
| **W1: RepoScout** | Clone repos, fingerprint, discover structure | `run_config.yaml` | `repo_inventory.json`, `frontmatter_contract.json`, `site_context.json`, `hugo_facts.json` |
| **W2: FactsBuilder** | Extract claims + evidence from repo | `repo_inventory.json` | `product_facts.json`, `evidence_map.json` |
| **W3: SnippetCurator** | Extract + tag code snippets | `product_facts.json` | `snippet_catalog.json` |
| **W4: IAPlanner** | Plan pages before writing (IA = Information Architecture) | `product_facts.json`, `evidence_map.json`, `snippet_catalog.json` | `page_plan.json` |
| **W5: SectionWriter** | Draft markdown for pages (fan-out per section) | `page_plan.json`, product facts | `drafts/<section>/*.md` |
| **W6: LinkerAndPatcher** | Apply patches to site worktree, generate patch bundle | `drafts/`, `page_plan.json` | `patch_bundle.json`, `diff_report.md` |
| **W7: Validator** | Run 13 validation gates | `patch_bundle.json` | `validation_report.json` |
| **W8: Fixer** | Fix one issue deterministically | `validation_report.json` | Updated `patch_bundle.json` |
| **W9: PRManager** | Open PR via commit service | `patch_bundle.json` | `pr_request_bundle.json` (or pr.json) |

**Global Worker Rules**:
- Only read declared inputs, only write declared outputs
- Idempotent: same inputs → same outputs
- All output JSON MUST validate against schemas
- Fail with **blocker** issue if input missing
- Deterministic ordering per `specs/10_determinism_and_caching.md`

### Validation Gates (13 total - Stop the Line)

Located in `specs/09_validation_gates.md` and `src/launch/validators/`:

1. **Schema Validation** - All JSON artifacts validate against schemas
2. **Markdown Lint + Frontmatter** - Quality + contract compliance
3. **Hugo Config Compatibility** - Planned content enabled in Hugo
4. **Platform Layout Compliance** - V2 platform-aware content layout
5. **Hugo Build** - Production Hugo build succeeds
6. **Internal Links** - No broken internal markdown links
7. **External Links** - External URLs reachable (profile-dependent)
8. **Snippet Checks** - Code snippet syntax + optional execution
9. **TruthLock** - All claims grounded in evidence
10. **Consistency** - product_name, repo_url, canonical URLs consistent
11. **Template Token Lint** - No unresolved `__TOKENS__`
12. **Universality Gates** - Tier compliance, limitations honesty, distribution correctness
13. **Rollback Metadata** - PR includes rollback info (prod profile only)

**Plus Gate T & compliance gates (J-R)** for determinism, frozen deps, secrets scan, etc.

### State Management (Event Sourcing)

Located in `src/launch/state/`:

- **Event Log** (`events.ndjson` - append-only):
  - One JSON object per line
  - Schema: `specs/schemas/event.schema.json`
  - Event types: RUN_CREATED, ARTIFACT_WRITTEN, WORK_ITEM_STARTED/FINISHED, GATE_RUN_STARTED/FINISHED, ISSUE_OPENED/RESOLVED, RUN_STATE_CHANGED, LLM_CALL_STARTED/FINISHED, etc.
  - Each event includes: `trace_id`, `span_id`, `parent_span_id` (for distributed tracing)

- **Snapshot** (`snapshot.json`):
  - Materialized state after each state transition
  - Contains: run_state, artifacts[], work_items[], issues[], section_states{}
  - **Replay Algorithm**: Reconstruct snapshot deterministically from event log
  - **Resume Algorithm**: Continue from last stable state without re-executing completed work

---

## Pilots: Golden Runs for Regression Detection

### Pilot Contract (Binding)

Located in `specs/13_pilots.md` and `configs/pilots/`:

Each pilot must include:
- **pilot_id**: Unique identifier (e.g., `pilot_aspose_note_python`)
- **github_ref**: Pinned commit SHA (NOT branch/tag)
- **site_ref**, **workflows_ref**: Pinned SHAs for determinism
- **run_config_path**: Path to pinned run config
- **golden_artifacts_dir**: Path to golden artifacts (page_plan.json, validation_report.json, patch_bundle.json, diff_summary.md, fingerprints.json)

### Regression Detection Algorithm

1. Run pilot with new system version
2. Compare generated artifacts to golden artifacts:
   - **Exact match**: page_plan.json (after removing timestamps), validation_report.ok
   - **Semantic equivalence**: patch_bundle.json (allow ±5 line shifts), issues[] (any new BLOCKER = regression)
   - **Computed metrics**: Page count delta, claim count delta, issue count delta
3. Regression thresholds:
   - Page count delta > 2 → WARN
   - New BLOCKER issue → FAIL
   - validation_report.ok changed from true to false → FAIL

### Current Pilots

- **Pilot 1**: `pilot_aspose_note_python` (planned, larger repo with rich README)
- **Pilot 2**: `pilot_aspose_3d_python` (planned, smaller repo with flatter layout)

---

## How Pilots Work vs Real Products

| Aspect | Pilots | Real Products |
|--------|--------|---------------|
| **Config Location** | `configs/pilots/pilot-*.resolved.yaml` | `configs/products/*.run_config.yaml` |
| **Ref Pinning** | All refs MUST be pinned to SHAs | Can use branch/tag references |
| **Golden Artifacts** | Stored in `specs/pilots/{id}/golden/` | N/A |
| **Regression Testing** | Fingerprints compared per regression algorithm | N/A |
| **Purpose** | Catch determinism regressions + test infrastructure | Launch real products to aspose.org |
| **Validation Profile** | ci (comprehensive) | prod (maximum rigor) |
| **Allowed Uses** | Development, CI testing, regression detection | Production PR opens |

---

## Validation & Gate System

### Profile-Based Gating

Three profiles determine gate strictness:

| Profile | Use Case | Gate Behavior | Timeouts |
|---------|----------|---------------|----------|
| **local** | Developer feedback (fast) | Skip external links by default, warnings don't fail | Relaxed (e.g., Hugo build: 300s) |
| **ci** | Continuous integration (comprehensive) | All gates including external links, stricter timeouts | Moderate (e.g., Hugo build: 600s) |
| **prod** | Maximum rigor (production PR) | All gates enabled, zero tolerance for warnings | Longest (e.g., 600s+) |

### Fix Loop (Deterministic Single-Issue)

```
VALIDATING → issues found?
   ↓
   NO → READY_FOR_PR
   ↓
   YES
   ├─ fix_attempts < max_fix_attempts?
   │  ├─ YES → Select first BLOCKER by deterministic ordering
   │  │         Invoke W8 Fixer → back to VALIDATING
   │  └─ NO → FAILED
```

**Key constraint**: Fix attempts capped by `run_config.max_fix_attempts` (default: 3)

### Error Taxonomy (Binding)

Error codes follow pattern: `{COMPONENT}_{ERROR_TYPE}_{SPECIFIC}`

Examples:
- `REPO_SCOUT_CLONE_FAILED`
- `GATE_SCHEMA_VALIDATION_FAILED`
- `PAGE_PLANNER_INSUFFICIENT_EVIDENCE`
- `VALIDATOR_TRUTHLOCK_VIOLATION`

All errors must be:
- Logged to `RUN_DIR/events.ndjson` as ERROR events
- Written to `RUN_DIR/snapshot.json`
- Added to `RUN_DIR/artifacts/validation_report.json` as BLOCKER issues (when applicable)

---

## Safety & Scope Enforcement

### Write Fence (`allowed_paths`)

- System MUST refuse to edit outside `run_config.allowed_paths`
- Attempt to patch outside allowed_paths → **blocker failure**
- Examples:
  ```yaml
  allowed_paths:
    - content/products.aspose.org/3d/en/python/
    - content/docs.aspose.org/3d/en/python/
    - content/reference.aspose.org/3d/en/python/
  ```

### No Direct Commits in Production

- Direct `git commit` from orchestrator **FORBIDDEN** in production mode
- ALL commits must go through **GitHub Commit Service** (`specs/17_github_commit_service.md`)
  - Centralized, auditable, enforces allowed_paths
  - Returns commit SHA for telemetry association

### No Uncited Claims

- All factual statements MUST map to claim IDs + evidence anchors
- **TruthLock** gate enforces: every claim → evidence → repo path + line range or URL + fragment
- Uncited facts open `GATE_TRUTHLOCK_UNCITED_FACT` BLOCKER

---

## Determinism Requirements

### Temperature = 0.0
- LLM temperature MUST default to 0.0 (greedy selection, no sampling)
- Same inputs → identical LLM outputs (for replay consistency)

### Stable Ordering
- Outputs MUST sort deterministically (e.g., alphabetical for claim lists)
- Snippet IDs derived from `{path, line_range, sha256(content)}`
- Page order: section order from config, then by slug

### Pin Inputs
- `github_ref`: Commit SHA (not branch/tag in production)
- `site_ref`: Commit SHA
- `ruleset_version`, `templates_version`: Explicit version locks
- No silent drift across versions

### Replayable/Resumable via Event Sourcing
- Replay: Reconstruct snapshot from event log without re-executing workers
- Resume: Continue from last stable state, skip completed work (but cache allows LLM call skips)
- Forces fast, deterministic reruns

---

## Artifact Model (RUN_DIR)

Each run produces schema-validated artifacts under `RUN_DIR = runs/<run_id>/`:

```
runs/<run_id>/
├── artifacts/
│   ├── repo_inventory.json          # Repo structure + profiling
│   ├── frontmatter_contract.json    # Required page fields
│   ├── site_context.json            # Site layout + Hugo facts
│   ├── hugo_facts.json              # Hugo config fingerprint, build matrix
│   ├── product_facts.json           # Features, workflows, limitations, distribution
│   ├── evidence_map.json            # Claims → repo paths + line ranges
│   ├── truth_lock_report.json       # Claim stability + evidence grounding
│   ├── snippet_catalog.json         # Reusable code samples + tags
│   ├── page_plan.json               # Pages to create: section, slug, output_path, url_path, required_claims
│   ├── patch_bundle.json            # All file modifications (create/update/delete operations)
│   └── validation_report.json       # Gate results + issues + exit codes
├── drafts/
│   ├── products/
│   ├── docs/
│   ├── reference/
│   ├── kb/
│   └── blog/
├── reports/
│   ├── diff_report.md               # Human-readable patch summary
│   └── pilot_regression_report.md   # (if pilot run)
├── work/
│   ├── product/                     # Cloned product repo
│   ├── site/                        # Cloned site repo (patch target)
│   └── workflows/                   # Cloned workflows repo
├── events.ndjson                    # Append-only event log (event sourcing)
├── snapshot.json                    # Materialized state (reconstructible from events)
├── run_config.json                  # Copy of validated config (binding)
└── pr.json                          # PR metadata (when PR opened, for rollback)
```

**Key constraint**: A run is successful only when:
1. All required artifacts exist and validate
2. All gates pass (`validation_report.ok=true`)
3. Telemetry includes complete event trail + LLM call logs
4. PR includes: summary of pages, evidence summary, checklist results

---

## Observability & Telemetry

### Local Telemetry API (Centralized, Binding)

- **Non-negotiable requirement**: ALL run events and LLM operations logged via HTTP API
- Creates parent TelemetryRun per launch + child TelemetryRun per node/worker/gate/LLM call
- All events include `trace_id`, `span_id`, `parent_span_id` (distributed tracing)
- Failure mode: If telemetry POST fails → buffer to `RUN_DIR/telemetry_outbox.jsonl` + retry with bounded backoff

### Local Event Log (for replay/resume)

- `runs/<run_id>/events.ndjson` (append-only, one JSON per line)
- Event chain validation: `event_hash = sha256(event_id + ts + type + payload + prev_hash)`
- Supports deterministic replay without re-executing workers

---

## System-Wide Non-Negotiables

1. **Scale**: Designed to launch 100s of products with diverse repo structures
2. **LLM Provider**: MUST use OpenAI-compatible APIs (e.g., Ollama endpoint)
3. **MCP**: MUST expose MCP endpoints/tools for all features (not CLI-only)
4. **Telemetry**: MUST use centralized local-telemetry HTTP API for all run events + LLM calls
5. **Commits**: MUST commit to aspose.org via centralized GitHub Commit Service (auditable, config-driven)
6. **Adaptation**: MUST adapt to different repo structures via profiling + adapters
7. **Change Control**: Every run pins `ruleset_version`, `templates_version`, schema versions (no silent drift)

---

## High-Level Data Flow

```
┌─────────────────┐
│   Run Config    │
│ (YAML + SHA)    │
└────────┬────────┘
         │
         v
    ┌────────────┐
    │ Orchestrator │ LangGraph State Machine
    └────────────┘
         │
         v
    ┌────────────┐
    │  W1 RepoScout     │ Clone repos, profile structure
    └────────────┘
         │ Outputs: repo_inventory, site_context
         v
    ┌────────────┐
    │ W2 FactsBuilder   │ Extract claims + evidence
    └────────────┘
         │ Outputs: product_facts, evidence_map
         v
    ┌────────────┐
    │ W3 SnippetCurator │ Extract code samples
    └────────────┘
         │ Outputs: snippet_catalog
         v
    ┌────────────┐
    │ W4 IAPlanner      │ Plan pages (what to write)
    └────────────┘
         │ Outputs: page_plan
         v
    ┌────────────┐
    │ W5 SectionWriter  │ Draft markdown (fan-out per section)
    └────────────┘
         │ Outputs: drafts/
         v
    ┌────────────┐
    │ W6 Linker  │ Apply patches to site worktree
    └────────────┘
         │ Outputs: patch_bundle, diff_report
         v
    ┌────────────┐
    │ W7 Validator      │ Run 13 validation gates (stop the line)
    └────────────┘
         │ Outputs: validation_report
         v
    ┌─────────────────────┐
    │ Issues Found?       │
    └──────────┬──────────┘
         │
    ├────┴────┬───────────┐
    │         │           │
    NO      YES+attempts  MAX attempts
    │      left            │
    │         │            v
    │         v        ┌────────────┐
    │     ┌────────────┐│  FAILED    │
    │     │ W8 Fixer   │└────────────┘
    │     └────────────┘
    │         │ (Fix 1 issue)
    │         └─→ back to W7 Validator
    │
    v
┌────────────┐
│ W9 PRManager │ Open PR via Commit Service
└────────────┘
     │ Outputs: pr.json
     v
 ┌──────────┐
 │   DONE   │
 └──────────┘
```

---

## Quick Reference: Simplified Flow

For newcomers, here's the simplified execution flow:

1. **You provide**: GitHub repo URL + run config
2. **System clones**: Repos and analyzes structure (W1)
3. **Extracts facts**: Product features/workflows with evidence links (W2, W3)
4. **Plans pages**: Decides what content to create (W4)
5. **Generates markdown**: Drafts content for all sections (W5)
6. **Creates patches**: Prepares modifications to site repo (W6)
7. **Validates everything**: Runs 13 quality gates (W7)
8. **Fixes issues**: If needed, with retry limit (W8)
9. **Opens PR**: With all changes and metadata (W9)

---

## Where the Scaffold Stops

The Python code under `src/launch/**` only provides a minimal foundation:
- Schema validation
- RUN_DIR scaffolding
- A validator that marks unimplemented gates as NOT_IMPLEMENTED (no false positives)

The full orchestrator and worker implementation is driven by the LLM taskcards in `plans/`.

---

## URL Generation and Link Transformation (Added 2026-02-03)

### Subdomain Architecture and URL Format

The foss-launcher uses a **subdomain-based architecture** where each section has its own subdomain:
- **blog.aspose.org** - Blog posts and announcements
- **docs.aspose.org** - Documentation and tutorials
- **reference.aspose.org** - API reference
- **kb.aspose.org** - Knowledge base (FAQ, troubleshooting)
- **products.aspose.org** - Product landing pages

**Critical principle**: Section name is implicit in the subdomain and NEVER appears in URL paths.

### URL Path Computation

**File**: `src/launch/workers/w4_ia_planner/worker.py::compute_url_path()` (lines 376-416)

**URL Format** (V2 layout, default language):
```
/{family}/{platform}/{slug}/
```

**Examples**:
- Blog post: `blog.aspose.org/3d/python/announcement/` (NOT `/3d/python/blog/announcement/`)
- Docs page: `docs.aspose.org/cells/python/getting-started/` (NOT `/cells/python/docs/getting-started/`)
- KB article: `kb.aspose.org/words/python/faq/` (NOT `/words/python/kb/faq/`)

**Algorithm**:
1. Extract page metadata: section, slug, product_slug, platform, locale
2. Build path components: `[product_slug, platform, slug]`
3. Join with slashes: `"/" + "/".join(parts) + "/"`
4. Note: Section is NOT included in path (it's implicit in subdomain)

**Subdomain Mapping**:
```python
def get_subdomain_for_section(section: str) -> str:
    return f"{section}.aspose.org"
```

**Related spec**: `specs/33_public_url_mapping.md` (lines 83-86, 106)

### Cross-Section Link Transformation

**Problem**: Relative links that cross section boundaries break in subdomain architecture because they resolve on the wrong subdomain.

**Example of broken link**:
```markdown
<!-- From blog.aspose.org page -->
See [Guide](../../docs/3d/python/guide/)
<!-- Browser resolves to: blog.aspose.org/docs/3d/python/guide/ ❌ 404 -->
```

**Solution**: W5 SectionWriter transforms cross-section links to absolute URLs during draft generation.

**File**: `src/launch/workers/w5_section_writer/link_transformer.py`

**Transformation Rules**:
- **Cross-section links**: Transform to absolute URLs with scheme + subdomain
  - Blog → Docs: `../../docs/3d/python/guide/` → `https://docs.aspose.org/3d/python/guide/`
  - Docs → Reference: `../../reference/cells/python/api/` → `https://reference.aspose.org/cells/python/api/`
- **Same-section links**: Keep relative (e.g., `./next-page/`)
- **Internal anchors**: Keep as-is (e.g., `#installation`)
- **External links**: Keep as-is (already absolute)

**Algorithm**:
1. Parse markdown content using regex: `\[([^\]]+)\]\(([^\)]+)\)`
2. For each link:
   - Skip if already absolute (starts with `http://` or `https://`)
   - Skip if internal anchor (starts with `#`)
   - Detect target section from URL pattern (e.g., `../../docs/` → section="docs")
   - Skip if target section == current section (same-section link)
   - Parse URL components (family, platform, subsections, slug)
   - Build absolute URL using `build_absolute_public_url()` (from TC-938)
   - Replace link with absolute URL
3. Return transformed markdown content

**Integration Point**: W5 SectionWriter calls `transform_cross_section_links()` after LLM generates content, before writing to `drafts/` directory.

**Graceful Degradation**: If transformation fails (parsing error, invalid URL), keep original link and log warning. Never break existing links.

**Related spec**: `specs/06_page_planning.md` (cross-link requirements section, added 2026-02-03)

### Template Discovery and Filtering

**File**: `src/launch/workers/w4_ia_planner/worker.py::enumerate_templates()` (lines 830-938)

**Blog Template Structure** (special case):
- Blog uses **filename-based i18n** (no locale folder in content structure)
- Content: `content/blog.aspose.org/{family}/{platform}/post.md`, `post.fr.md`
- Templates must match: `specs/templates/blog.aspose.org/{family}/__PLATFORM__/__POST_SLUG__/...`

**Filtering Rules**:
1. **Blog section**: Exclude templates with `__LOCALE__` in path (obsolete structure)
2. **Non-blog sections**: Allow `__LOCALE__` (they use locale folders)
3. **Index pages**: De-duplicate `_index.md` variants per section (only keep first alphabetically)

**Why Filtering is Critical**:
- Obsolete templates with wrong structure cause URL collisions
- Multiple index page variants map to same URL
- Blog templates with `__LOCALE__` don't match actual content structure

**Related spec**: `specs/07_section_templates.md` (template discovery section, added 2026-02-03)

---

## Further Reading

- `specs/README.md` - Binding specification overview
- `specs/01_system_contract.md` - Core contract & error codes
- `specs/21_worker_contracts.md` - Worker definitions
- `specs/33_public_url_mapping.md` - URL format specification
- `specs/06_page_planning.md` - Page planning and cross-links
- `specs/07_section_templates.md` - Template structure and filtering
- `plans/00_orchestrator_master_prompt.md` - Implementation workflow
- `src/launch/orchestrator/graph.py` - State machine implementation
