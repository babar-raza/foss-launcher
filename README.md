# FOSS Launcher

An AI-agent-powered documentation generation and deployment system that transforms GitHub repositories into comprehensive, evidence-grounded technical documentation for Hugo-based websites.

> **Naming note**: "FOSS" refers to the product distribution naming used by pilot repositories (e.g., "Aspose.Note FOSS for Python"), not the license of this launcher.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Worker Pipeline](#worker-pipeline)
- [Adaptation and Tiering](#adaptation-and-tiering)
- [Validation Gates](#validation-gates)
- [Content Quality System](#content-quality-system)
- [Evidence and TruthLock](#evidence-and-truthlock)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [MCP Server](#mcp-server)
- [Quick Start](#quick-start)
- [Running Pilots](#running-pilots)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Specification Pack](#specification-pack)
- [Security Model](#security-model)
- [Governance and Compliance](#governance-and-compliance)
- [Tooling Reference](#tooling-reference)
- [Documentation Navigation](#documentation-navigation)

---

## Overview

FOSS Launcher takes a public GitHub repository as input and produces a complete set of Hugo-compatible documentation pages across five website sections (products, docs, reference, knowledge base, blog), then opens a pull request against the target site repository.

### What the system does

1. **Clones and fingerprints** the source repository, detecting language, structure, manifests, CI signals, test coverage, and documentation roots
2. **Extracts product facts** as atomic claims from documentation and source code, enriches them with metadata, and maps each claim to source evidence
3. **Curates code snippets** from examples and documentation with full provenance tracking
4. **Plans page inventory** based on evidence density, selecting a launch tier (minimal, standard, or rich) and computing page quotas per section
5. **Generates markdown content** via LLM with inline claim markers tracing every factual statement back to source evidence
6. **Reviews content quality** through 36 automated checks across content quality, technical accuracy, and usability dimensions
7. **Applies patches** to the site repository worktree with security-fenced write scope
8. **Validates output** through 13 quality gates covering schema compliance, link integrity, Hugo build, claim attribution, and more
9. **Opens a pull request** via a centralized commit service with full traceability metadata

### Design principles

- **Deterministic**: Same inputs produce identical outputs (pinned SHAs, `PYTHONHASHSEED=0`, temperature 0.0, stable hashing)
- **Evidence-grounded**: Every factual statement traces to source code or documentation via TruthLock claim markers
- **Schema-validated**: All 23 artifact types are validated against JSON schemas at every pipeline handoff
- **Security-fenced**: All write operations confined to declared `allowed_paths` per run configuration
- **Event-sourced**: Append-only event log (`events.ndjson`) for full audit trail, replay, and resume
- **LLM-agnostic**: Uses OpenAI-compatible APIs (works with Ollama, Azure OpenAI, or any compatible provider)
- **Scalable**: Isolated run directories with no shared state, designed for hundreds of products

---

## Architecture

The system is built as a **LangGraph state machine** that orchestrates 10 specialized workers (W1 through W9, plus W5.5) in a sequential pipeline with a conditional fix loop.

### State Machine

```
CREATED
  |
  v
W1: RepoScout ------> CLONED_INPUTS
  |
  v
W2: FactsBuilder ---> FACTS_READY
  |
  v
W3: SnippetCurator --> FACTS_READY
  |
  v
W4: IAPlanner -------> PLAN_READY
  |
  v
W5: SectionWriter ---> DRAFT_READY
  |
  v
W5.5: ContentReviewer -> DRAFT_READY  (optional, configurable)
  |
  v
W6: LinkerPatcher ---> LINKING
  |
  v
W7: Validator -------> VALIDATING
  |                       |
  |  +----- fix loop -----+
  |  |                    |
  |  v                    v
  | W8: Fixer         READY_FOR_PR
  |  |                    |
  |  +-----> W7           v
  |                   W9: PRManager -> PR_OPENED -> DONE
  |
  +---> FAILED (if fix attempts exhausted)
  +---> CANCELLED (on user cancellation)
```

### Run Directory Layout

Each run produces an isolated `RUN_DIR` with this structure:

```
runs/<run_id>/
  run_config.yaml           # Pinned configuration
  snapshot.json              # Current state snapshot
  events.ndjson              # Append-only event log
  artifacts/                 # Schema-validated JSON artifacts
    repo_inventory.json      # W1: repository fingerprint
    frontmatter_contract.json# W1: frontmatter schema
    site_context.json        # W1: site repo metadata
    hugo_facts.json          # W1: Hugo configuration
    product_facts.json       # W2: extracted claims and metadata
    evidence_map.json        # W2: claim-to-evidence mappings
    snippet_catalog.json     # W3: curated code samples
    page_plan.json           # W4: page inventory and tiers
    review_report.json       # W5.5: quality review results
    patch_bundle.json        # W6: file modification operations
    validation_report.json   # W7: gate results
    pr.json                  # W9: PR metadata
  drafts/                    # W5: generated markdown by section
    products/
    docs/
    reference/
    kb/
    blog/
  reports/                   # Human-readable summaries
  work/                      # Temporary working files
    repo/                    # Cloned source repository
    site/                    # Patched site worktree
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | LangGraph (v0.2+) | State machine and workflow control |
| LLM abstraction | LangChain (v0.3+) | Provider-agnostic LLM integration |
| Data validation | Pydantic (v2.7+) | Runtime type checking and models |
| Schema validation | jsonschema (v4.22+) | Artifact contract enforcement |
| CLI | Typer (v0.12+) | Command-line interface |
| MCP server | FastAPI (v0.111+) + MCP (v1.0+) | Tool interface for LLM agents |
| HTTP client | httpx (v0.27+) | Async HTTP for external services |
| Retry logic | tenacity (v8.3+) | Resilient external calls |
| Logging | structlog (v24.1+) | Structured logging |
| Terminal UI | Rich (v13+) | Formatted CLI output |

---

## Worker Pipeline

### W1: RepoScout

Clones the source repository, profiles its structure, and generates an inventory.

- **Language detection**: Weights code files 3x over config/docs; covers Python, C#, Java, JavaScript, TypeScript, Go, Rust, PHP, Ruby, C++
- **Manifest discovery**: Locates `pyproject.toml`, `setup.py`, `package.json`, `Cargo.toml` and other build system files
- **Health signal detection**: CI presence (GitHub Actions, Travis), test directories, documentation roots, example directories
- **Phantom path detection**: Scans markdown for broken `[text](path)` references indicating poor documentation quality
- **Deterministic SHA resolution**: Pins exact commit hashes for reproducibility

**Outputs**: `repo_inventory.json`, `frontmatter_contract.json`, `site_context.json`, `hugo_facts.json`

### W2: FactsBuilder

Extracts product facts as atomic claims, enriches them with metadata, and maps evidence.

**Sub-modules**:

| Module | Purpose |
|--------|---------|
| `extract_claims.py` | Extract atomic claims from docs with code-like content filtering (12 indicators, threshold 3) and prose quality validation |
| `code_analyzer.py` | Python AST parsing, JavaScript/C# regex patterns, manifest extraction, API surface analysis |
| `enrich_claims.py` | LLM batch enrichment with automatic offline heuristic fallback when claims exceed 500 |
| `enrich_workflows.py` | Step ordering, complexity estimation, time estimates for workflow claims |
| `enrich_examples.py` | Description extraction, audience level inference from example content |
| `map_evidence.py` | Jaccard word-overlap similarity scoring (72x faster than TF-IDF for hot path) with 4-tuple document cache |
| `detect_contradictions.py` | Pre-tokenized pairwise comparison with Jaccard pre-filter (threshold 0.3) for cross-kind contradiction detection |
| `embeddings.py` | TF-IDF cosine similarity (stdlib-only, no numpy) for non-hot-path contexts |

**Outputs**: `product_facts.json`, `evidence_map.json`

### W3: SnippetCurator

Extracts and deduplicates code snippets from documentation and source code.

- Parses markdown/RST code blocks from documentation files
- Scans example directories with AST-based function/class extraction for Python
- Deduplicates across sources, preserving provenance (file, line range, SHA)
- Deterministic ordering by language, tags, and snippet ID

**Output**: `snippet_catalog.json`

### W4: IAPlanner

Plans the page inventory based on evidence density and repository quality signals.

- Computes evidence volume score: `(claims x 2) + (snippets x 3) + (API symbols x 1)`
- Selects launch tier (minimal, standard, rich) based on repository health signals
- Applies tier-scaled quotas: minimal 0.3x, standard 0.7x, rich 1.0x
- Assigns page roles: TOC, landing, comprehensive guide, workflow page, feature showcase, troubleshooting, API reference
- Supports mandatory pages (config-driven) and optional pages (evidence-driven)

**Output**: `page_plan.json`

### W5: SectionWriter

Generates markdown content via LLM with claim markers for evidence traceability.

- Selects templates by tier variant (minimal, standard, rich) from `specs/templates/{subdomain}/{family}/__LOCALE__/`
- Grounds all content in product facts with inline claim markers: `[claim: claim_id]`
- Post-processing: strips `<think>` tokens, normalizes markdown fences, truncates bullets over 200 characters via first-sentence extraction
- Specialized generators for TOC, comprehensive guide, FAQ, and other page roles
- Cross-section link transformation (relative within section, absolute across subdomains)

**Outputs**: `drafts/<page_id>_<section_id>.md`, `draft_manifest.json`

### W5.5: ContentReviewer

Quality gate between drafting and linking. Optional (controlled by `review_enabled` in run config, defaults to false).

- **36 automated checks** across 3 dimensions (12 each): content quality, technical accuracy, usability
- **Scoring**: 1-5 per dimension with routing: PASS (>=4), NEEDS_CHANGES (=3), REJECT (<=2)
- **9 deterministic auto-fix functions**: markdown normalization, heading fixes, list formatting, code block fixes, link standardization, deduplication, claim marker correction, terminology normalization
- **3 LLM specialist agents** for rejected content: content enhancer, technical fixer, usability improver
- **Readability exemptions** for navigation/FAQ pages

**Output**: `review_report.json`

### W6: LinkerAndPatcher

Converts drafts to patches and applies them to the site repository worktree.

- Generates patch operations (`create_file`, `update_by_anchor`, `update_frontmatter_keys`)
- Enforces `allowed_paths` security fence (raises `LinkerAllowedPathsViolationError` on violation)
- Generates navigation files (`_data/navigation.yml`, `_data/products.yml`)
- Detects patch conflicts before application

**Outputs**: `patch_bundle.json`, `diff_report.md`

### W7: Validator

Runs 13 validation gates on generated content with configurable strictness profiles.

See [Validation Gates](#validation-gates) for the complete gate reference.

**Output**: `validation_report.json`

### W8: Fixer

Resolves validation issues iteratively.

- Fixes exactly one issue per invocation, then returns to W7 for re-validation
- Maximum 20 iterations before abort (configurable via `max_fix_attempts`)
- Strategies: link rewrites, claim marker corrections, frontmatter repairs, LLM-based rewrites for complex issues

**Output**: Updated `patch_bundle.json`

### W9: PRManager

Creates pull requests with deterministic branching.

- Branch naming: `launch/{product_slug}/{ref_short}/{run_id_short}`
- PR body includes validation summary, diff highlights, and evidence trail
- Creates commits via centralized GitHub commit service (no direct git in production)
- Records rollback metadata for recovery

**Output**: `pr.json`

---

## Adaptation and Tiering

The system automatically adapts to repositories with different structures, feature density, and metadata richness.

### Repository Fingerprinting (W1)

W1 detects these signals to characterize a repository:

| Signal | Detection Method | Downstream Effect |
|--------|-----------------|-------------------|
| Primary language | File extension analysis (code files weighted 3x) | Template selection, snippet extraction strategy |
| Build system | Manifest file discovery | Version detection, dependency analysis |
| CI presence | GitHub Actions, Travis, etc. | Tier elevation signal |
| Test coverage | Test directory detection, file count | Tier elevation signal |
| Documentation roots | Structured docs directories | Evidence volume, tier elevation |
| Example directories | Configurable example paths | Snippet catalog richness |
| Phantom paths | Broken markdown link detection | Tier reduction signal |

### Launch Tiers

W4 selects a launch tier based on accumulated signals:

| Tier | Trigger | Page Quota | Content Depth |
|------|---------|-----------|---------------|
| **Minimal** | CI and tests both absent, or unresolved contradictions | 0.3x maximum | Landing + essential pages only, no troubleshooting |
| **Standard** | CI or tests present, no contradictions | 0.7x maximum | Full mandatory pages + some optional |
| **Rich** | Multiple elevation signals (CI + tests + examples + docs) | 1.0x maximum | All optional pages, deep-dives, comprehensive coverage |

**Elevation signals** (each adds +1): CI with passing badge, test files >10, validated examples, structured documentation.
**Reduction signals**: CI and tests both absent (-1), phantom paths detected (-1), unresolved contradictions (force minimal).

### Adaptation Flow

```
Sparse Repo                          Rich Repo
  Few files, no CI/tests               100+ files, CI, tests, examples
    |                                     |
  Few claims extracted (42)             Many claims (6500+)
    |                                     |
  Heuristic enrichment (offline)        LLM batch enrichment
    |                                     |
  Minimal tier (0.3x quota)             Standard/Rich tier (0.7-1.0x)
    |                                     |
  13-18 pages, ~2 min runtime           16-25+ pages, ~7 min runtime
```

### Per-Page Content Adaptation

| Page Role | Claim Quota | Snippets | Behavior |
|-----------|------------|----------|----------|
| TOC | 0-2 | None | Navigation hub, lists child pages |
| Landing | 5-10 | Optional | Positioning, key features |
| Comprehensive Guide | 1 per workflow | All workflows | All workflows mandatory |
| Workflow Page | 3-8 | 1 per workflow | Single workflow depth |
| Feature Showcase | 3-8 | 1-2 | Deep-dive on notable features |
| Troubleshooting | 1-5 | Optional | Problem-solution format (standard/rich only) |
| API Reference | Varies | Per-class | Module/class documentation |

---

## Validation Gates

13 quality gates enforce output correctness. Gates run in configurable profiles with increasing strictness:

| Gate | Name | What It Validates |
|------|------|------------------|
| 1 | Schema Validation | All JSON artifacts validate against their JSON schemas |
| 2 | Markdown Lint & Frontmatter | markdownlint compliance + YAML frontmatter schema |
| 3 | Hugo Config Compatibility | Content builds with configured Hugo settings |
| 5 | Hugo Build | Site builds successfully in production mode |
| 6 | Internal Links | No broken markdown or anchor references |
| 7 | External Links | External URLs reachable (profile-gated, optional in local) |
| 8 | Snippet Checks | Code syntax validation and optional execution |
| 9 | TruthLock | All claims trace to evidence, no uncited facts |
| 10 | Consistency | Product name, repo URL, canonical URLs consistent across artifacts |
| 11 | Template Token Lint | No unresolved `__TOKEN__` placeholders; V2 platform tokens blocklisted |
| 12 | Universality Gates | Launch tier compliance, limitations honesty, distribution correctness |
| 13 | Rollback Metadata | PR includes rollback steps, base ref, affected paths (prod profile) |
| 14 | Content Distribution | Pages follow strategy, mandatory pages present, claim quotas met |

### Validation Profiles

| Profile | Use Case | Strictness |
|---------|----------|-----------|
| `local` | Development | Fast feedback, external links skipped |
| `ci` | Continuous integration | Comprehensive, balanced timeouts |
| `prod` | Production deployment | Maximum rigor, rollback metadata required |

### Issue Severities

- **WARNING**: Noted but does not block
- **ERROR**: Must be addressed before PR
- **BLOCKER**: Immediately fails the pipeline

---

## Content Quality System

### W5.5 ContentReviewer Checks (36 total)

**Content Quality (12 checks)**: Readability, coherence, spelling, grammar, flow, structure, clarity, engagement, consistency, citation quality, information density, tone.

**Technical Accuracy (12 checks)**: Factual correctness, completeness, precision, terminology, API compatibility, framework compatibility, version accuracy, platform compatibility, security accuracy, performance accuracy, limitation accuracy, deprecation handling.

**Usability (12 checks)**: Navigation, organization, accessibility, searchability, mobile-friendliness, information architecture, cross-linking, metadata, audience appropriateness, example quality, prerequisite clarity, follow-up links.

### W5 Post-Processing

- Strips `<think>` tokens from LLM output
- Removes markdown fences inside code blocks
- Truncates bullet points over 200 characters via first-sentence extraction
- Validates output structure before writing

---

## Evidence and TruthLock

Every factual statement in generated content must trace to source evidence.

### Claim Lifecycle

1. **Extraction** (W2): Atomic claims extracted from documentation and source code with stable IDs via `SHA256(normalized_text | claim_kind)`
2. **Enrichment** (W2): Claims enriched with usage context, limitations, compatibility notes via LLM or heuristic fallback
3. **Evidence mapping** (W2): Each claim linked to source files and line ranges with priority-weighted scoring
4. **Inline attribution** (W5): Claims embedded in generated markdown as `[claim: claim_id]` markers
5. **Verification** (W7, Gate 9): TruthLock validates all claims trace to evidence with no uncited facts

### Claim Groups

Claims are organized into top-level groups in `product_facts.json`:

```json
{
  "claims": [{"claim_id": "...", "claim_text": "...", "claim_kind": "..."}],
  "claim_groups": {
    "key_features": ["claim_id_1", "claim_id_2"],
    "install_steps": ["claim_id_3"],
    "workflows": ["claim_id_4", "claim_id_5"],
    "limitations": ["claim_id_6"]
  }
}
```

### Evidence Scoring

```
score = (0.3 x priority) + (0.4 x jaccard_similarity) + (0.3 x keyword_match)
```

---

## Configuration

Runs are configured via YAML files validated against `specs/schemas/run_config.schema.json`.

### Run Config Structure

```yaml
schema_version: "1.2"
product_slug: "aspose-note-foss-python"
product_name: "Aspose.Note FOSS for Python"
family: "note"
locales: ["en"]

# Repository references (pinned by SHA for determinism)
github_repo_url: "https://github.com/aspose/aspose-note-foss-python"
github_ref: "<commit_sha>"
site_repo_url: "https://github.com/Aspose/aspose.org"
site_ref: "<commit_sha>"

# Sections to generate
required_sections: ["products", "docs", "reference", "kb", "blog"]

# Site layout mapping
site_layout:
  content_root: "content"
  subdomain_roots:
    products: "content/products.aspose.org"
    docs: "content/docs.aspose.org"
    reference: "content/reference.aspose.org"
    kb: "content/kb.aspose.org"
    blog: "content/blog.aspose.org"

# Write scope (security fence)
allowed_paths:
  - "content/*/note/*"
  - "themes/*/exampleSidebar.md"

# LLM provider (OpenAI-compatible)
llm:
  api_base_url: "http://127.0.0.1:11434/v1"
  model: "gemma3:12b"
  request_timeout_s: 300
  max_concurrency: 4
  decoding:
    temperature: 0.0
    max_tokens: 6000

# External services
telemetry:
  endpoint_url: "http://127.0.0.1:8765"
commit_service:
  endpoint_url: "http://127.0.0.1:4320/v1"
mcp:
  enabled: true
  listen_port: 8787

# Pipeline controls
review_enabled: false        # Enable W5.5 ContentReviewer
max_fix_attempts: 3          # W7-W8 fix loop iterations
templates_version: "templates.v1"
ruleset_version: "ruleset.v1"
```

### Key Configuration Options

| Option | Effect |
|--------|--------|
| `launch_tier` | Override automatic tier detection (minimal, standard, rich) |
| `review_enabled` | Enable W5.5 content quality review (default: false) |
| `max_fix_attempts` | Maximum W7-W8 fix loop iterations (default: 3) |
| `allowed_paths` | Security-fenced write scope for W6 patching |
| `example_directories` | Additional directories to scan for code examples |
| `exclude_patterns` | Glob patterns to skip during repo ingestion |
| `detect_phantom_paths` | Toggle broken link detection in source repo |

---

## CLI Reference

The CLI is built with Typer and provides these commands:

### `launch run`

Start a new documentation generation run.

```bash
launch run --config <path/to/run_config.yaml> [--run_dir <output_dir>] [--dry-run] [--verbose]
```

### `launch status`

Check the status of a run.

```bash
launch status <run_id> [--verbose]
```

### `launch list`

List all runs sorted by modification time.

```bash
launch list [--limit N] [--all]
```

### `launch validate`

Run validation gates on a completed run.

```bash
launch validate <run_id> --profile {local|ci|prod}
```

### `launch cancel`

Cancel a running task.

```bash
launch cancel <run_id> [--force]
```

### `launch mcp serve`

Start the MCP (Model Context Protocol) server.

```bash
launch mcp serve [--port 8787]
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Validation failure |
| 2 | Execution failure |

---

## MCP Server

All launcher capabilities are exposed as MCP tools for integration with LLM agents (Claude Desktop, etc.).

### Available Tools

| Tool | Description |
|------|-------------|
| `launch_start_run` | Start a run from a run config |
| `launch_start_run_from_product_url` | Start a run from a product URL |
| `launch_start_run_from_github_repo_url` | Start a run from a GitHub repo URL |
| `launch_get_status` | Get run state, section states, issues, artifacts |
| `launch_get_artifact` | Retrieve a specific artifact with SHA-256 hash |
| `launch_validate` | Run validation gates |
| `launch_fix_next` | Apply next fix and report remaining issues |
| `launch_resume` | Resume a paused or failed run |
| `launch_cancel` | Cancel a running task |
| `launch_open_pr` | Open a pull request |
| `launch_list_runs` | List all runs with optional filtering |

### Transport

STDIO-based JSON-RPC (standard MCP transport). Server name: `foss-launcher-mcp`.

---

## Quick Start

### Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) (preferred for deterministic installs)
- An OpenAI-compatible LLM API endpoint (e.g., Ollama with `gemma3:12b`)

### Virtual Environment Policy

This repository enforces a **strict `.venv` policy** ([specs/00_environment_policy.md](specs/00_environment_policy.md)):

- **MUST use**: `.venv/` at repository root
- **FORBIDDEN**: Any other virtual environment name (`venv/`, `env/`, `.tox/`, etc.)
- **FORBIDDEN**: Using global/system Python for development or testing
- **Enforcement**: Gate 0 in validation tools fails if policy is violated

### Installation

**Preferred (deterministic with uv):**

```bash
# Install uv: https://docs.astral.sh/uv/getting-started/installation/
make install-uv

# Activate
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

**Fallback (pip):**

```bash
make install

# Activate
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### Running a Launch

```bash
# Start a run from a config file
launch run --config configs/pilots/pilot-aspose-note-foss-python.yaml

# Check status
launch status <run_id>

# Validate results
launch validate <run_id> --profile local

# List all runs
launch list
```

---

## Running Pilots

Three golden pilot runs serve as regression baselines:

| Pilot | Repository Type | Expected Tier | Claims | Runtime |
|-------|----------------|---------------|--------|---------|
| `pilot-aspose-3d-foss-python` | Sparse, flat layout, no CI | Minimal | ~42 | ~2 min |
| `pilot-aspose-note-foss-python` | Rich, src-layout, CI signals | Standard | ~6,500 | ~7 min |
| `pilot-aspose-cells-foss-python` | Additional validation | Varies | Varies | Varies |

### Execute a Pilot

```bash
# Run a pilot
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-note-foss-python \
  --output runs/<run_id>

# Run pilot verification (VFV)
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot_vfv.py \
  --pilot pilot-aspose-note-foss-python
```

Each pilot has pinned configs in both `specs/pilots/` and `configs/pilots/` with:
- `run_config.pinned.yaml` (pinned repo SHA, site SHA)
- `notes.md` documenting quirks and assumptions
- Golden artifacts for regression comparison

---

## Testing

### Running Tests

```bash
# Run all tests (from activated .venv)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x

# Or via Makefile
make test

# Run specific test file
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_411_extract_claims.py -x

# Skip slow tests
.venv/Scripts/python.exe -m pytest tests/ -m "not slow"
```

### Test Configuration

- **Determinism**: `PYTHONHASHSEED=0` enforced via `pyproject.toml`
- **Markers**: `slow`, `integration`, `asyncio`
- **Options**: `-q --strict-markers --tb=short`
- **Current status**: 2,766 passed, 9 skipped (environment-gated: 2 E2E, 7 integration)

### Test Organization

```
tests/
  unit/                    # Deterministic unit tests by module
    cli/
    orchestrator/
    workers/               # Per-worker test files
      test_tc_411_extract_claims.py
      test_w5_specialized_generators.py
      w5_5_content_reviewer/
      ...
  integration/             # Pipeline integration tests
  e2e/                     # End-to-end tests (env-gated)
  fixtures/                # Test data and mock repos
```

---

## Project Structure

```
foss-launcher/
  src/launch/              # Python implementation
    cli/                   # Typer CLI application
    orchestrator/          # LangGraph state machine, run loop, worker invoker
    workers/               # 10 specialized workers (W1-W9, W5.5)
      w1_repo_scout/       # Clone, fingerprint, discover
      w2_facts_builder/    # Claims, enrichment, evidence, contradictions
      w3_snippet_curator/  # Code sample extraction
      w4_ia_planner/       # Page planning, tiering
      w5_section_writer/   # LLM content generation
      w5_5_content_reviewer/ # Quality checks, auto-fixes
      w6_linker_and_patcher/ # Safe patching
      w7_validator/        # 13 validation gates
      w8_fixer/            # Issue resolution
      w9_pr_manager/       # PR creation
    models/                # Pydantic data models (state, events, artifacts)
    clients/               # HTTP clients (LLM, commit service, telemetry)
    io/                    # Artifact store, config loading, JSON schemas
    state/                 # Event log, snapshot manager
    security/              # Secret detection, allowed_paths enforcement
    mcp/                   # MCP server implementation
    validators/            # Validation gate implementations
    determinism/           # Hashing, stable ordering
    resilience/            # Retry logic, error handling
    resolvers/             # Path resolution, URL mapping
    observability/         # Logging, run summaries
    content/               # Content transformation utilities
    inference/             # LLM inference utilities
    telemetry_api/         # Telemetry HTTP server

  specs/                   # Binding specifications (36+ documents)
    schemas/               # 23 JSON schemas for all artifact types
    templates/             # Section templates by subdomain/family/locale
    pilots/                # Pinned pilot configurations and golden artifacts

  configs/                 # Run configurations
    pilots/                # Pilot configs
    products/              # Real product configs

  plans/                   # Agent coordination
    taskcards/             # Implementation taskcards (TC-300+)
    prompts/               # Agent kickoff, self-review prompts
    policies/              # Operational policies

  tests/                   # 2,766+ tests
  scripts/                 # Operational scripts (pilots, forensics, hooks)
  tools/                   # Validation and audit tools
  docs/                    # Reference documentation (non-binding)
  reports/                 # Agent work artifacts and reviews
  runs/                    # Runtime artifacts (created during execution)
```

---

## Specification Pack

The `specs/` directory contains 36+ binding specifications that define the system contract.

### Core System

| Spec | Title |
|------|-------|
| [00_overview.md](specs/00_overview.md) | System goals, scale, architecture |
| [00_environment_policy.md](specs/00_environment_policy.md) | Virtual environment policy |
| [01_system_contract.md](specs/01_system_contract.md) | Binding contracts, error codes, guarantees A-L |
| [02_repo_ingestion.md](specs/02_repo_ingestion.md) | Clone, fingerprinting, phantom path detection |
| [03_product_facts_and_evidence.md](specs/03_product_facts_and_evidence.md) | Claim extraction, evidence ranking |
| [04_claims_compiler_truth_lock.md](specs/04_claims_compiler_truth_lock.md) | Stable claim IDs, verification |
| [05_example_curation.md](specs/05_example_curation.md) | Code snippet extraction |
| [06_page_planning.md](specs/06_page_planning.md) | Page inventory, launch tiers |
| [07_section_templates.md](specs/07_section_templates.md) | Template selection by tier |
| [08_patch_engine.md](specs/08_patch_engine.md) | Safe file modification |

### Validation and Quality

| Spec | Title |
|------|-------|
| [09_validation_gates.md](specs/09_validation_gates.md) | 13 quality gates, profiles |
| [10_determinism_and_caching.md](specs/10_determinism_and_caching.md) | Reproducibility rules |
| [11_state_and_events.md](specs/11_state_and_events.md) | State machine, event sourcing |
| [12_pr_and_release.md](specs/12_pr_and_release.md) | PR creation, deployment |

### Infrastructure

| Spec | Title |
|------|-------|
| [13_pilots.md](specs/13_pilots.md) | Golden pilot runs for regression |
| [14_mcp_endpoints.md](specs/14_mcp_endpoints.md) | MCP tool interface |
| [15_llm_providers.md](specs/15_llm_providers.md) | OpenAI-compatible LLM APIs |
| [16_local_telemetry_api.md](specs/16_local_telemetry_api.md) | Event logging API |
| [17_github_commit_service.md](specs/17_github_commit_service.md) | Centralized commit service |
| [21_worker_contracts.md](specs/21_worker_contracts.md) | Worker I/O definitions |
| [25_frameworks_and_dependencies.md](specs/25_frameworks_and_dependencies.md) | LangChain, LangGraph |
| [29_project_repo_structure.md](specs/29_project_repo_structure.md) | Repository and RUN_DIR layout |

### Governance

| Spec | Title |
|------|-------|
| [30_ai_agent_governance.md](specs/30_ai_agent_governance.md) | 4-layer defense, 9 governance rules |
| [34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md) | 12 binding guarantees (A-L) |

### JSON Schemas (23)

All artifact types are validated against schemas in `specs/schemas/`:

`api_error`, `commit_request`, `commit_response`, `event`, `evidence_map`, `frontmatter_contract`, `hugo_facts`, `issue`, `open_pr_request`, `open_pr_response`, `page_plan`, `patch_bundle`, `pr`, `product_facts`, `repo_inventory`, `review_report`, `ruleset`, `run_config`, `site_context`, `snapshot`, `snippet_catalog`, `truth_lock_report`, `validation_report`

---

## Security Model

### Allowed Paths Fence

All write operations are confined to paths declared in `run_config.allowed_paths`. W6 (LinkerAndPatcher) enforces this boundary and raises `LinkerAllowedPathsViolationError` on any violation.

### Secret Detection

The security module scans generated content for leaked credentials, API keys, and other sensitive data. Gate 7 (Security Scanning) enforces this at validation time.

### Hermetic Execution

Each run is isolated in its own `RUN_DIR` with no shared mutable state between runs. All external interactions go through declared service endpoints.

### Network Allowlist

Only whitelisted hosts may be contacted during execution (Guarantee D).

---

## Governance and Compliance

### 12 Binding Guarantees (A-L)

Defined in [specs/34_strict_compliance_guarantees.md](specs/34_strict_compliance_guarantees.md):

| ID | Guarantee |
|----|-----------|
| A | Input immutability (pinned SHAs, no floating branches) |
| B | Hermetic execution (confined to RUN_DIR) |
| C | Supply-chain pinning (frozen `uv.lock`) |
| D | Network allowlist (only whitelisted hosts) |
| E | Secret hygiene (no secrets in logs or artifacts) |
| F | Budget controls (runtime, LLM tokens, file churn) |
| G | Change budget (minimal diffs only) |
| H | CI parity (same commands locally and in CI) |
| I | Non-flaky tests (`PYTHONHASHSEED=0`) |
| J | No untrusted execution (repo is parse-only, never executed) |
| K | Version locking (all taskcards pinned) |
| L | Rollback and recovery (PR includes rollback metadata) |

### 4-Layer Taskcard Validation Defense

Defined in [specs/30_ai_agent_governance.md](specs/30_ai_agent_governance.md):

```
Layer 1: Creation Script    -> Validates and DELETES invalid taskcards
Layer 2: Pre-Commit Hook    -> Validates staged taskcards (bypassable)
Layer 3: Pre-Push Hook      -> Validates ALL taskcards (bypassable, tracked)
Layer 4: CI/CD Blocking     -> UNBYPASSABLE final gate, blocks PR merge
```

### Agent Governance Rules (AG-001 through AG-009)

| Rule | Gate | Severity |
|------|------|----------|
| AG-001 | Branch creation | BLOCKER |
| AG-002 | LLM claim enrichment (prod) | BLOCKER |
| AG-003 | Taskcard validation | BLOCKER |
| AG-004 | Branch switching (dirty working directory) | ERROR |
| AG-005 | Destructive git operations | BLOCKER |
| AG-006 | Remote push (new branch) | WARNING |
| AG-007 | PR creation | WARNING |
| AG-008 | Configuration changes | ERROR |
| AG-009 | Dependency installation | WARNING |

---

## Tooling Reference

### Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `run_pilot.py` | Execute a pilot run end-to-end |
| `run_pilot_vfv.py` | Pilot verification flow |
| `run_pilot_e2e.py` | End-to-end pilot testing |
| `create_taskcard.py` | Create a new taskcard with validation |
| `remediate_taskcards.py` | Batch-fix invalid taskcard YAML |
| `monitor_bypass_usage.py` | Track `--no-verify` hook bypass frequency |
| `install_hooks.py` | Install git hooks (pre-commit, pre-push) |
| `validate_spec_pack.py` | Spec pack integrity check |
| `validate_schemas.py` | JSON schema validation |
| `forensics_catalog.py` | Auditable file catalog with SHA hashes |
| `verify_determinism.py` | Verify deterministic output |
| `profile_tc412.py` | Performance profiling for evidence mapping |

### Tools (`tools/`)

| Tool | Purpose |
|------|---------|
| `validate_swarm_ready.py` | Preflight validation (20+ checks) |
| `validate_taskcards.py` | Taskcard YAML frontmatter validation |
| `generate_status_board.py` | Regenerate STATUS_BOARD from taskcards |
| `check_markdown_links.py` | Markdown link integrity |
| `audit_allowed_paths.py` | Detect allowed_paths conflicts |
| `validate_dotvenv_policy.py` | .venv policy enforcement |
| `validate_ci_parity.py` | CI/local command parity |
| `validate_supply_chain_pinning.py` | Dependency pinning verification |
| `validate_secrets_hygiene.py` | Secret leakage detection |
| `validate_pinned_refs.py` | Pinned reference verification |
| `validate_budgets_config.py` | Budget controls validation |
| `validate_no_placeholders_production.py` | Placeholder detection |

---

## Documentation Navigation

### New to this repository?

1. Read [specs/README.md](specs/README.md) for the spec overview
2. Read [GLOSSARY.md](GLOSSARY.md) for terminology
3. Read [docs/architecture.md](docs/architecture.md) for system architecture
4. Read [DECISIONS.md](DECISIONS.md) for architectural decisions

### For implementation agents

- [plans/00_orchestrator_master_prompt.md](plans/00_orchestrator_master_prompt.md) - Orchestration workflow
- [plans/taskcards/00_TASKCARD_CONTRACT.md](plans/taskcards/00_TASKCARD_CONTRACT.md) - Binding taskcard rules
- [plans/taskcards/INDEX.md](plans/taskcards/INDEX.md) - Taskcard registry
- [plans/swarm_coordination_playbook.md](plans/swarm_coordination_playbook.md) - Parallel agent coordination
- [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) - Requirement tracing

### Reference

- [ASSUMPTIONS.md](ASSUMPTIONS.md) - Documented assumptions
- [DECISIONS.md](DECISIONS.md) - Design decisions
- [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) - Unresolved questions

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `PYTHONHASHSEED` | Must be `0` for deterministic execution |
| `OPENAI_API_KEY` | LLM provider authentication |
| `GITHUB_TOKEN` | GitHub operations |
| `TELEMETRY_API_AUTH_TOKEN` | Telemetry service authentication |
| `LAUNCH_MCP_TOKEN` | MCP server authentication |
| `W2_MAX_FILE_SIZE_MB` | Evidence mapping file size cap (default: 5) |
