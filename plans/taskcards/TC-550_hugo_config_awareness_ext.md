---
id: TC-550
title: "Hugo Config Awareness (derive build constraints + language matrix)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-400
allowed_paths:
  - src/launch/resolvers/hugo_config.py
  - src/launch/schemas/hugo_facts.schema.json
  - tests/unit/resolvers/test_tc_550_hugo_config.py
  - reports/agents/**/TC-550/**
evidence_required:
  - reports/agents/<agent>/TC-550/report.md
  - reports/agents/<agent>/TC-550/self_review.md
---

# Taskcard TC-550 — Hugo Config Awareness (derive build constraints + language matrix)

## Objective
Implement a deterministic **Hugo Config Analyzer** that loads Hugo configuration from the site repo and derives the minimal build constraints needed by planning, writing, and validation.

## Required spec references
- specs/31_hugo_config_awareness.md
- specs/33_public_url_mapping.md (hugo_facts fields for URL mapping)
- specs/18_site_repo_layout.md
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md
- specs/09_validation_gates.md
- specs/schemas/hugo_facts.schema.json

## Scope
### In scope
- Load Hugo config from `configs/**` and root config files
- Support TOML and YAML (JSON optional if present)
- Derive:
  - language list and default language
  - default_language_in_subdir (for URL mapping, per specs/33)
  - permalinks and section rules (if present)
  - outputs and output formats
  - taxonomies (if present)
- Produce stable, normalized artifact used by:
  - planner target generation (W4)
  - public URL resolver (specs/33_public_url_mapping.md)
  - path resolver (TC-540)
  - validation gates (TC-570)
- Unit tests with small fixture configs

### Out of scope
- Running a full Hugo build (TC-570)
- Content authoring

## Inputs
- `RUN_DIR/work/site/` cloned site repo

## Outputs
- `RUN_DIR/artifacts/hugo_facts.json` (new)
- `site_context.json` updated with `hugo_facts_digest` (sha256)
- Event: `HUGO_FACTS_WRITTEN`

## Allowed paths
- src/launch/resolvers/hugo_config.py
- src/launch/schemas/hugo_facts.schema.json
- tests/unit/resolvers/test_tc_550_hugo_config.py
- reports/agents/**/TC-550/**
## Implementation steps
1) Discover config files deterministically:
   - prefer `configs/_default/**`
   - then `config.toml|yaml|yml|json`
2) Parse TOML with stdlib `tomllib`; parse YAML with `PyYAML` (per deps).
3) Normalize results:
   - sorted keys, stable lists, no comments
4) Derive `language_matrix`:
   - explicit languages if configured
   - else default to `["en"]`
5) Extract minimal constraint maps:
   - `permalinks`, `outputs`, `taxonomies`
6) Validate and write `hugo_facts.json` atomically.
7) Add fixtures and tests:
   - TOML only, YAML only, split configs, missing configs defaults.

## E2E verification
**Concrete command(s) to run:**
```bash
python -c "from launch.resolvers.hugo_config import parse_hugo_config; print('OK')"
```

**Expected artifacts:**
- src/launch/resolvers/hugo_config.py

**Success criteria:**
- [ ] Hugo config parsed
- [ ] Build constraints extracted

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-404 (Hugo scan)
- Downstream: TC-570 (Hugo smoke gate)
- Contracts: specs/31_hugo_config_awareness.md

## Deliverables
- Code + schema
- Tests + fixtures
- Report and self review under repo-root reports/

## Acceptance checks
- [ ] `hugo_facts.json` validates against schema
- [ ] Two runs produce identical bytes
- [ ] Language derivation matches fixtures
- [ ] default_language_in_subdir derived from config (default: false)
- [ ] Missing configs do not crash and yield safe defaults
- [ ] Artifact includes all required fields per specs/33_public_url_mapping.md

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
