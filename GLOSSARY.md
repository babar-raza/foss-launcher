# Glossary

This file defines terminology used throughout specs, plans, and taskcards to ensure consistent understanding.

## Core Terms

### Agent / Worker
- **Worker (W1-W9)**: Specialized agents in the pipeline (e.g., W1=RepoScout, W2=FactsBuilder)
- **Orchestrator**: Master agent coordinating the workflow via LangGraph state machine
- **Implementation Agent**: Agent executing a specific taskcard

### Artifacts & Outputs

- **Artifact**: JSON or structured output files written to `runs/<run_id>/artifacts/` (e.g., `repo_inventory.json`, `page_plan.json`)
- **RUN_DIR**: The isolated directory for a single execution: `runs/<run_id>/`
- **PatchBundle**: Collection of deterministic file modifications (`patch_bundle.json`)
- **ValidationReport**: Output of validation gates (`validation_report.json`)

### Evidence & Facts

- **ProductFacts**: Structured JSON containing verified information about the product (features, formats, APIs)
- **EvidenceMap**: JSON linking claims to source files and line ranges with citations
- **TruthLock**: Claim verification system ensuring all published content traces to evidence
- **Claim**: Factual statement about the product that must be backed by evidence
- **Claim Marker**: Inline attribution in generated content linking to evidence

### Repository Concepts

- **Product Repo**: The public GitHub repository being launched (e.g., `Aspose/aspose-note-foss-python`)
- **Site Repo**: The Hugo website repository (e.g., `aspose.org`)
- **Workflow Repo**: Repository containing GitHub Actions (if separate from site repo)
- **Repo Profile**: Detected metadata about repository structure (`platform_family`, `repo_archetype`, etc.)
- **Repo Archetype**: Stable label for repository layout pattern (e.g., `python_src_pyproject`, `python_flat_setup_py`)

### Templates & Content

- **Section Template**: Hugo template for a specific content section (blog/docs/kb/products/reference)
- **Ruleset**: YAML file defining template selection rules and content requirements
- **Frontmatter**: YAML metadata at the top of Hugo markdown files
- **Launch Tier**: Quality/richness level for generated content (`minimal` | `standard` | `rich`)

### Validation & Quality

- **Gate**: Validation check (e.g., markdownlint, lychee link checker, Hugo build, truth-lock)
- **Profile**: Validation strictness level (`local` | `ci` | `prod`)
- **Issue**: Structured validation failure (`issue.schema.json`)
- **Blocker**: Critical issue preventing progress (severity=BLOCKER)

### Operations

- **Idempotency**: Running the same operation multiple times produces the same result
- **Determinism**: Same inputs produce identical outputs
- **Phantom Path**: Path mentioned in docs but not present in repository
- **Emergency Mode**: Special flag (`allow_manual_edits`) permitting manual content adjustments (exceptional cases only)

### Plans & Execution

- **Taskcard**: Implementation instruction for a specific cohesive task (e.g., `TC-100_bootstrap_repo.md`)
- **Master Plan**: Top-level orchestration plan sequencing all taskcards
- **Self-Review**: 12-dimension quality assessment required for each taskcard
- **Allowed Paths**: Explicit list of file paths an agent may modify

### Standards

- **Binding Spec**: Specification that implementation MUST follow (non-negotiable)
- **Non-negotiable**: Requirement that cannot be omitted or substituted
- **MCP**: Model Context Protocol - interface for exposing tools to LLMs
- **OpenAI-compatible**: LLM provider that implements OpenAI API format

## Platform-Specific Terms

- **FOSS**: "Free and Open Source Software" - used in pilot product naming (e.g., "Aspose.Note FOSS for Python")
  - Note: Refers to product distribution naming, not the license of this launcher repo

## Platform-Aware Layout Terms (V2)

- **target_platform**: The directory segment representing the target platform in content paths (e.g., `python`, `typescript`, `go`)
- **platform_family**: The adapter/tooling family identifier for repo detection (e.g., `node` for typescript/javascript, `python`, `go`)
- **layout_mode**: Configuration field controlling path resolution: `auto` (detect), `v1` (legacy), `v2` (platform-aware)
- **V1 Layout**: Legacy content layout without platform directory segment: `{subdomain}/{family}/{locale}/`
- **V2 Layout**: Platform-aware layout with platform directory: `{subdomain}/{family}/{locale}/{platform}/` (non-blog) or `{subdomain}/{family}/{platform}/` (blog)
- **Platform Root**: The base directory for platform-specific content in V2 layout (e.g., `content/docs.aspose.org/cells/en/python/`)
- **Auto-detection**: Deterministic algorithm to detect V2 layout by checking filesystem for platform directories

## Schema Terms

- **JSON Schema**: Schema definitions in `specs/schemas/` validating artifact structure
- **Schema Version**: Version identifier in schemas enabling evolution

## Workflow States

States from `specs/11_state_and_events.md`:
- **INIT**: Initial state
- **INGESTING**: Repository analysis in progress
- **PLANNING**: Page plan creation
- **DRAFTING**: Content generation
- **PATCHING**: Applying changes
- **VALIDATING**: Running quality gates
- **FIXING**: Addressing validation failures
- **READY**: Passed all gates, ready for PR
- **RELEASED**: PR opened/merged
- **FAILED**: Unrecoverable error

## Abbreviations

- **IA**: Information Architecture (in W4 IA Planner)
- **LLM**: Large Language Model
- **SHA**: Git commit hash identifier
- **CI**: Continuous Integration
- **PR**: Pull Request
- **TC**: Taskcard (prefix for taskcard IDs)
- **RUN_ID**: Unique identifier for a launcher execution

---

*This glossary will be expanded during spec/plan hardening as new terms are clarified.*
