---
id: TC-1034
title: "W1 Stub Artifact Enrichment"
status: Done
owner: agent_g
updated: "2026-02-07"
tags: [phase4, w1, enrichment, frontmatter, site-context, hugo-facts]
depends_on: [TC-1022, TC-1024]
allowed_paths:
  - "src/launch/workers/w1_repo_scout/frontmatter_discovery.py"
  - "src/launch/workers/w1_repo_scout/site_context_builder.py"
  - "src/launch/workers/w1_repo_scout/hugo_facts_builder.py"
  - "src/launch/workers/w1_repo_scout/worker.py"
  - "tests/unit/workers/test_w1_*.py"
evidence_required:
  - reports/agents/agent_g/TC-1034/evidence.md
  - reports/agents/agent_g/TC-1034/self_review.md
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-1034: W1 Stub Artifact Enrichment

## Objective

Replace 3 minimal stubs in `w1_repo_scout/worker.py` (frontmatter_contract.json, site_context.json, hugo_facts.json) with real builder implementations that produce enriched artifacts.

## Required spec references

- `specs/21_worker_contracts.md:54-95` — W1 RepoScout contract
- `specs/schemas/frontmatter_contract.schema.json` — Frontmatter contract schema
- `specs/10_determinism_and_caching.md` — Deterministic serialization

## Scope

### In scope
- Create `frontmatter_discovery.py` — scans markdown for YAML frontmatter, builds section contracts
- Create `site_context_builder.py` — builds SiteContext from run_config + repo_inventory
- Create `hugo_facts_builder.py` — parses Hugo TOML/YAML configs
- Update `worker.py` to call new builders instead of stubs
- Handle both string and dict entry formats in doc_entrypoints

### Out of scope
- External YAML library dependencies (uses simple line-based parser)
- Modifying shared libraries

## Inputs
- `discovered_docs.json` — doc_entrypoints (strings) and doc_entrypoint_details (dicts)
- `run_config` — site_layout, resolved metadata
- Hugo config files (config.toml, config.yaml) in site worktree

## Outputs
- `frontmatter_contract.json` — enriched with real section contracts
- `site_context.json` — enriched with real site context data
- `hugo_facts.json` — enriched with parsed Hugo configuration

## Allowed paths
- src/launch/workers/w1_repo_scout/frontmatter_discovery.py
- src/launch/workers/w1_repo_scout/site_context_builder.py
- src/launch/workers/w1_repo_scout/hugo_facts_builder.py
- src/launch/workers/w1_repo_scout/worker.py
- tests/unit/workers/test_w1_*.py

## Implementation steps
1. Create `frontmatter_discovery.py` with simple YAML parser and section classification
2. Create `site_context_builder.py` with SiteContext builder from run_config
3. Create `hugo_facts_builder.py` with Hugo TOML/YAML config parser
4. Update `worker.py` to call new builders instead of stubs
5. Fix doc_entrypoints format handling (string vs dict entries)

## Failure modes

### Failure mode 1: doc_entrypoints format mismatch
**Detection:** AttributeError on `.get()` when entry is a string not a dict
**Resolution:** Handle both formats with isinstance check; use doc_entrypoint_details (dicts) with fallback to doc_entrypoints (strings)
**Spec/Gate:** specs/21_worker_contracts.md (W1 output format)

### Failure mode 2: Missing Hugo config
**Detection:** FileNotFoundError when reading config.toml/yaml from site dir
**Resolution:** Return empty config dict gracefully; log debug message
**Spec/Gate:** specs/04_hugo_site_config.md

### Failure mode 3: Malformed frontmatter
**Detection:** YAML parse returns None for files with invalid frontmatter syntax
**Resolution:** Skip file, log debug message, continue processing remaining files
**Spec/Gate:** specs/schemas/frontmatter_contract.schema.json

## Task-specific review checklist
1. [ ] frontmatter_discovery.py handles both string and dict entries
2. [ ] site_context_builder.py builds from run_config without external deps
3. [ ] hugo_facts_builder.py handles TOML and YAML configs
4. [ ] worker.py calls new builders at correct pipeline step
5. [ ] All existing tests pass after changes
6. [ ] New builders produce deterministic output (sorted keys)

## Deliverables
- 3 new builder modules created
- worker.py updated to use builders
- Bug fix for doc_entrypoints format handling
- `reports/agents/agent_g/TC-1034/evidence.md`
- `reports/agents/agent_g/TC-1034/self_review.md`

## Acceptance checks
- All tests pass (2392 passed, 12 skipped)
- frontmatter_contract.json produced by real builder
- site_context.json produced by real builder
- hugo_facts.json produced by real builder
- No stub content in production artifacts

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output output/tc1034-3d
```

**Expected artifacts:**
- **frontmatter_contract.json** — enriched with real section contracts (not stubs)
- **site_context.json** — enriched with real site context data
- **hugo_facts.json** — enriched with parsed Hugo configuration

## Integration boundary proven

**Upstream:** TC-1022 (exhaustive docs discovery), TC-1024 (.gitignore support)
**Downstream:** W4-W7 consume enriched artifacts for planning and validation
**Contract:** All 2392 tests pass; enriched artifacts conform to schemas

## Self-review
See `reports/agents/agent_g/TC-1034/self_review.md`
