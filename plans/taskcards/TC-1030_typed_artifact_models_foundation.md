---
id: TC-1030
title: "Typed Artifact Models -- Foundation"
status: In-Progress
owner: agent-f
updated: "2026-02-07"
tags: [infrastructure, models, phase-3]
depends_on: [TC-250]
allowed_paths:
  - "src/launch/models/repo_inventory.py"
  - "src/launch/models/site_context.py"
  - "src/launch/models/frontmatter.py"
  - "src/launch/models/hugo_facts.py"
  - "src/launch/models/truth_lock.py"
  - "src/launch/models/ruleset.py"
  - "src/launch/models/__init__.py"
  - "tests/unit/models/**"
  - "plans/taskcards/TC-1030_*"
  - "reports/agents/agent_f/TC-1030/**"
evidence_required:
  - reports/agents/agent_f/TC-1030/evidence.md
  - reports/agents/agent_f/TC-1030/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-1030: Typed Artifact Models -- Foundation

## Objective

Create typed Python models for W1/W2 artifacts: RepoInventory, SiteContext, FrontmatterContract, HugoFacts, TruthLockReport, and Ruleset. These models provide typed containers with validation, deterministic serialization, and from_dict/to_dict round-trip support following the existing Artifact base class pattern.

## Required spec references

- specs/01_system_contract.md (Artifact contracts)
- specs/10_determinism_and_caching.md (Deterministic serialization)
- specs/schemas/repo_inventory.schema.json
- specs/schemas/site_context.schema.json
- specs/schemas/frontmatter_contract.schema.json
- specs/schemas/hugo_facts.schema.json
- specs/schemas/truth_lock_report.schema.json
- specs/schemas/ruleset.schema.json

## Scope

### In scope

- Create typed model classes for RepoInventory, SiteContext, FrontmatterContract, HugoFacts, TruthLockReport, Ruleset
- Follow existing Artifact base class pattern from base.py
- Implement from_dict(), to_dict(), validate() for each model
- Add load_from_yaml() for Ruleset model
- Update __init__.py to export new models
- Create comprehensive unit tests

### Out of scope

- Modifying existing model files (base.py, run_config.py, product_facts.py, etc.)
- Adding business logic to models
- Modifying worker code to use new models (separate taskcard)
- Schema modifications

## Inputs

- Existing base.py, Artifact class pattern
- JSON schemas in specs/schemas/
- W1/W2 worker code for artifact structure understanding

## Outputs

- src/launch/models/repo_inventory.py
- src/launch/models/site_context.py
- src/launch/models/frontmatter.py
- src/launch/models/hugo_facts.py
- src/launch/models/truth_lock.py
- src/launch/models/ruleset.py
- Updated src/launch/models/__init__.py
- tests/unit/models/test_repo_inventory.py
- tests/unit/models/test_site_context.py
- tests/unit/models/test_frontmatter.py
- tests/unit/models/test_hugo_facts.py
- tests/unit/models/test_truth_lock.py
- tests/unit/models/test_ruleset.py

## Allowed paths

- src/launch/models/repo_inventory.py
- src/launch/models/site_context.py
- src/launch/models/frontmatter.py
- src/launch/models/hugo_facts.py
- src/launch/models/truth_lock.py
- src/launch/models/ruleset.py
- src/launch/models/__init__.py
- tests/unit/models/**
- plans/taskcards/TC-1030_*
- reports/agents/agent_f/TC-1030/**

### Allowed paths rationale

All new files in src/launch/models/ are permitted by TC-1030 governance (creating new files, not modifying existing). Test files and evidence/taskcard paths are standard.

## Implementation steps

1. Read existing patterns (base.py, run_config.py, product_facts.py)
2. Read JSON schemas for all target artifacts
3. Create RepoInventory model matching repo_inventory.schema.json
4. Create SiteContext model matching site_context.schema.json
5. Create FrontmatterContract model matching frontmatter_contract.schema.json
6. Create HugoFacts model matching hugo_facts.schema.json
7. Create TruthLockReport model matching truth_lock_report.schema.json
8. Create Ruleset model matching ruleset.schema.json with YAML loading
9. Update __init__.py with new exports
10. Create unit tests for all models
11. Run full test suite to verify no regressions

## Failure modes

1. **Schema mismatch**: Model fields do not match schema definition
   - Detection: Unit tests fail on round-trip or schema validation
   - Resolution: Compare model fields against schema required/optional properties
   - Spec link: specs/schemas/*.schema.json

2. **Non-deterministic serialization**: to_dict() produces unstable output
   - Detection: Repeated serialization produces different results
   - Resolution: Ensure sorted keys, stable field ordering
   - Spec link: specs/10_determinism_and_caching.md

3. **Import cycle**: New models create circular import
   - Detection: ImportError at runtime
   - Resolution: Models only import from base.py, no worker imports
   - Spec link: specs/01_system_contract.md

## Task-specific review checklist

1. All model fields match their corresponding JSON schema
2. from_dict() handles missing optional fields gracefully (no KeyError)
3. to_dict() produces deterministic output (sorted keys)
4. Round-trip: from_dict(m.to_dict()) == original for all models
5. No business logic in model classes (pure data containers)
6. Ruleset.load_from_yaml() correctly handles YAML parsing
7. All models inherit from Artifact base class
8. No imports from worker modules (no coupling)

## Deliverables

- 6 new model files in src/launch/models/
- 6 new test files in tests/unit/models/
- Updated __init__.py
- reports/agents/agent_f/TC-1030/evidence.md
- reports/agents/agent_f/TC-1030/self_review.md

## Acceptance checks

- [ ] All 6 models created with from_dict/to_dict/validate
- [ ] All models follow Artifact base class pattern
- [ ] __init__.py exports all new models
- [ ] Unit tests pass for all models
- [ ] Full test suite passes with no regressions
- [ ] Evidence and self-review written

## Self-review

See reports/agents/agent_f/TC-1030/self_review.md

## E2E verification

```bash
# TODO: Add concrete verification command
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_*.py -x
```

**Expected artifacts:**
- TODO: Specify expected output files/results

**Expected results:**
- TODO: Define success criteria

## Integration boundary proven

**Upstream:** TODO: Describe what provides input to this taskcard's work

**Downstream:** TODO: Describe what consumes output from this taskcard's work

**Boundary contract:** TODO: Specify input/output contract
