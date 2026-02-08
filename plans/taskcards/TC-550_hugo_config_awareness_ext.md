---
id: TC-550
title: "Hugo Config Awareness (derive build constraints + language matrix)"
status: Done
owner: "CONTENT_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-400
allowed_paths:
  - src/launch/content/hugo_config.py
  - tests/unit/content/test_tc_550_hugo_config.py
  - reports/agents/CONTENT_AGENT/TC-550/**
evidence_required:
  - reports/agents/CONTENT_AGENT/TC-550/report.md
  - reports/agents/CONTENT_AGENT/TC-550/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
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
- src/launch/content/hugo_config.py
- tests/unit/content/test_tc_550_hugo_config.py
- reports/agents/CONTENT_AGENT/TC-550/**
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

## Failure modes

### Failure mode 1: Hugo config parser fails on mixed TOML/YAML/JSON configuration
**Detection:** Parser raises tomllib.TOMLDecodeError or yaml.YAMLError during config discovery; hugo_facts.json not generated; run aborts with config parse error
**Resolution:** Check config file precedence logic (configs/_default/** overrides root config.*); verify TOML parsing uses stdlib tomllib (Python 3.11+); ensure YAML parsing handles Hugo-specific fields; review config discovery order in parse_hugo_config()
**Spec/Gate:** specs/31_hugo_config_awareness.md (config file discovery rules), Gate C (schema validation)

### Failure mode 2: Language matrix extraction returns wrong default_language or missing languages
**Detection:** hugo_facts.json has incorrect language list; W4 planner generates pages for wrong locales; URL mapping fails; permalinks broken
**Resolution:** Review language extraction logic in derive_language_matrix(); check languages config section parsing; verify defaultContentLanguage field extraction; ensure fallback to ["en"] when no languages configured; validate against fixture configs in tests
**Spec/Gate:** specs/31_hugo_config_awareness.md (language matrix derivation), specs/33_public_url_mapping.md (URL locale handling)

### Failure mode 3: default_language_in_subdir flag incorrectly derived causing URL mismatches
**Detection:** Public URLs for default language have extra locale segment (/en/) when they shouldn't, or vice versa; W4 planner generates wrong path structures; navigation links broken
**Resolution:** Review defaultContentLanguageInSubdir field extraction in parse_hugo_config(); check Hugo config field name (camelCase vs snake_case); verify default value (false) when field absent; test with both true/false configurations; consult Hugo documentation for field semantics
**Spec/Gate:** specs/33_public_url_mapping.md (default language URL rules), specs/31_hugo_config_awareness.md (config field mapping)

### Failure mode 4: hugo_facts.json non-deterministic due to unsorted keys or unstable list ordering
**Detection:** Gate H (determinism check) fails; hugo_facts_digest changes across runs with identical config; VFV harness reports SHA256 mismatch
**Resolution:** Review normalization logic in parse_hugo_config(); ensure all dicts written with sorted keys; verify language list sorted alphabetically; check permalinks and taxonomies use stable ordering; apply json.dumps(sort_keys=True) when writing hugo_facts.json
**Spec/Gate:** specs/10_determinism_and_caching.md (stable serialization), Gate H (determinism validation)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [x] All outputs are written atomically per specs/10_determinism_and_caching.md
- [x] No manual content edits made (compliance with no_manual_content_edits policy)
- [x] Determinism verified (pure functions, no side effects, same input = same output)
- [x] All spec references consulted (spec 26, Hugo docs, RFC 5646)
- [x] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [x] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code + schema
- Tests + fixtures
- Report and self review under repo-root reports/

## Acceptance checks
- [x] Hugo config parser implemented with all format support (TOML, YAML, JSON)
- [x] Language matrix extraction working (34 tests, 100% pass)
- [x] Build constraints extraction complete
- [x] default_language_in_subdir derived from config (default: false)
- [x] Missing configs handled gracefully (returns None)
- [x] Deterministic parsing (pure functions, no side effects)
- [x] All tests passing (34/34 in 0.90s)
- [x] Evidence complete (report.md + self_review.md)

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
