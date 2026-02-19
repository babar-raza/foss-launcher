# Documentation IA Proposal

> **Status**: Draft - Ready for review  
> **Date**: 2026-02-18  
> **Purpose**: Propose a clean, non-duplicative documentation structure for the FOSS Launcher project

---

## 1. Proposed Documentation Tree

```
docs/
├── README.md                          # Docs home and navigation (ONLY file in root)
├── _audit/                            # Audit outputs (kept here)
│   ├── README_IA_PROPOSAL.md         # This file
│   ├── docs_inventory.md
│   ├── docs_migration_plan.md
│   ├── root_orphans.md
│   ├── style_guide.md
│   └── system_audit.md
├── _archive/                          # Archived docs with notes
│   └── telemetry_integration_20260208.md
├── overview/                          # What it is, concepts
│   ├── index.md                      # Overview home
│   ├── concepts.md                   # Core concepts
│   └── architecture.md               # System architecture (moved from reference)
├── getting-started/                   # Quickstarts per persona
│   ├── index.md                      # Getting started home
│   ├── for-users.md                  # User quickstart
│   ├── for-operators.md              # Operator quickstart
│   └── for-contributors.md           # Contributor quickstart
├── guides/                            # Scenario-driven, step-by-step
│   ├── index.md                      # Guides home
│   ├── ai-governance.md              # AI governance rules (moved from root)
│   ├── creating-taskcards.md         # Taskcard creation guide (moved from root)
│   ├── running-pilots.md             # Running pilot workflows
│   ├── debugging.md                  # Debugging guide
│   └── troubleshooting.md            # Troubleshooting guide
├── reference/                         # Canonical, exhaustive
│   ├── index.md                      # Reference home
│   ├── cli.md                        # CLI reference (merged from cli_usage.md)
│   ├── config.md                     # Config reference (run_config schema)
│   ├── mcp.md                        # MCP server reference
│   ├── telemetry.md                  # Telemetry API reference (merged)
│   ├── llm-models.md                 # LLM model reference (renamed from MODEL_REFERENCE.md)
│   └── file-contracts.md             # File contracts and schemas
├── architecture/                      # System design, diagrams, decisions
│   ├── index.md                      # Architecture home
│   ├── system-design.md              # System design overview
│   ├── worker-pipeline.md            # Worker pipeline details
│   ├── state-management.md           # State management approach
│   └── decisions/                    # Architecture decisions (ADR)
│       └── index.md
├── operations/                        # Runbooks, troubleshooting, telemetry, deployment
│   ├── index.md                      # Operations home
│   ├── deployment.md                 # Deployment guide
│   ├── runbooks.md                   # Runbooks
│   ├── telemetry.md                  # Telemetry configuration
│   └── troubleshooting.md            # Troubleshooting (detailed)
└── development/                       # Contributing, testing, repo structure
    ├── index.md                      # Development home
    ├── contributing.md               # Contribution guide
    ├── testing.md                    # Testing guide
    └── repo-structure.md             # Repository structure
```

---

## 2. Personas and Their Needs

### User Persona
**Who**: End users who want to generate documentation for their repositories  
**Needs**:
- Quick start guide to run the launcher
- Understanding of what the system produces
- Common use cases and examples
- How to configure for their repo

**Target docs**:
- `getting-started/for-users.md` - User onboarding
- `guides/running-pilots.md` - Running your first documentation run
- `reference/cli.md` - CLI command reference
- `reference/config.md` - Configuration options

---

### Operator Persona
**Who**: CI/CD operators, platform engineers running the launcher at scale  
**Needs**:
- Deployment and configuration
- Monitoring and observability
- Troubleshooting common issues
- Understanding the worker pipeline

**Target docs**:
- `getting-started/for-operators.md` - Operator onboarding
- `operations/deployment.md` - Deployment guide
- `operations/runbooks.md` - Operational runbooks
- `reference/telemetry.md` - Telemetry configuration
- `reference/mcp.md` - MCP server for CI integration

---

### Contributor Persona
**Who**: Developers contributing to the launcher codebase  
**Needs**:
- How to set up development environment
- How to add new workers
- How to write tests
- Understanding the architecture

**Target docs**:
- `getting-started/for-contributors.md` - Contributor onboarding
- `development/contributing.md` - Contribution guide
- `development/testing.md` - Testing guide
- `architecture/system-design.md` - System design
- `reference/file-contracts.md` - Worker contracts

---

## 3. Where Does This Go? Rules

### Guides vs Reference

| Criteria | Belongs in **Guides** | Belongs in **Reference** |
|----------|----------------------|-------------------------|
| **Purpose** | How-to, step-by-step scenarios | What-it-is, exhaustive catalog |
| **Audience** | Users learning to use the system | Operators needing precise details |
| **Content Type** | Tutorials, workflows, examples | API specs, schemas, config tables |
| **Updates** | Updated when workflows change | Updated when contracts change |
| **Length** | Moderate, focused on one scenario | Can be long, comprehensive |
| **Examples** | "How to run a pilot" | "All CLI flags and options" |

### Key Rule: Link, Don't Repeat

**Reference docs are the single source of truth.** Guides must link to reference instead of duplicating content.

**Bad** (duplicative):
```markdown
# In guides/running-pilots.md

The `--verbose` flag enables verbose output. The `--dry-run` flag simulates without making changes.

Usage:
  launch run --config config.yaml --verbose --dry-run
```

**Good** (links to reference):
```markdown
# In guides/running-pilots.md

For full CLI options, see [CLI Reference](../reference/cli.md#flags).

Usage:
  launch run --config config.yaml --verbose --dry-run
```

---

## 4. Docs Root Allowed Items

**Hard Rule**: The `docs/` root directory may contain **only**:

1. `README.md` - Docs home and navigation
2. `_audit/` - Audit outputs (this folder)
3. `_archive/` - Archived docs with notes

**No other files or folders are allowed in `docs/` root.**

**Rationale**:
- Prevents documentation sprawl
- Makes navigation predictable
- Ensures every doc has a clear home
- Simplifies CI checks (e.g., `find docs/ -maxdepth 1 -type f` should only find `README.md`)

---

## 5. Migration Principles

| Principle | Description |
|-----------|-------------|
| **Single Source of Truth** | Each piece of information lives in exactly one place |
| **Canonical References** | Config, CLI, APIs live in `reference/` only |
| **Scenario-Driven Guides** | Guides are organized by user scenario, not by component |
| **Personas First** | Content organized by who needs it, not by how it's built |
| **Archive, Don't Delete** | Historical docs go to `_archive/` with notes |

---

## 6. Implementation Phases

| Phase | Goal | Deliverables |
|-------|------|-------------|
| 1. Root Cleanup | Move root orphans to proper locations | `AI_GOVERNANCE_QUICK_REFERENCE.md` → `guides/ai-governance.md` |
| 2. Reference Consolidation | Merge duplicate references | `cli_usage.md` + `local-telemetry*.md` → `reference/cli.md`, `reference/telemetry.md` |
| 3. Guide Creation | Create scenario-driven guides | `guides/running-pilots.md`, `guides/debugging.md` |
| 4. Architecture Reorganization | Move architecture to dedicated folder | `reference/architecture.md` → `overview/architecture.md` |
| 5. Archive Historical Docs | Move completion reports to archive | `telemetry_integration_completion.md` → `_archive/` |

---

## 7. Next Steps

1. **Review this proposal** - Does the structure meet the hard rules?
2. **Approve migration plan** - Does the mapping in `docs_migration_plan.md` make sense?
3. **Execute migration** - Move files according to plan
4. **Update CI checks** - Add root-orphans check to CI
5. **Update cross-links** - Fix all links to new paths

---

*This proposal is a living document. Update as the documentation structure evolves.*
