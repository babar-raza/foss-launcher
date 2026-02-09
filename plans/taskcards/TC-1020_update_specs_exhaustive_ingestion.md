---
id: TC-1020
title: "Update Specs for Exhaustive Ingestion"
status: Done
priority: Normal
owner: agent-c
updated: "2026-02-07"
tags: ["specs", "exhaustive-ingestion", "phase-1"]
depends_on: []
allowed_paths:
  - specs/02_repo_ingestion.md
  - specs/03_product_facts_and_evidence.md
  - specs/05_example_curation.md
  - specs/21_worker_contracts.md
  - plans/taskcards/TC-1020_*
  - reports/agents/agent_c/TC-1020/**
evidence_required:
  - reports/agents/agent_c/TC-1020/evidence.md
  - reports/agents/agent_c/TC-1020/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1020 — Update Specs for Exhaustive Ingestion

## Objective
Update all binding specs (02, 03, 05, 21) to mandate exhaustive discovery and extraction with no artificial limits, ensuring W1 records all files regardless of extension and W2 processes all documents without count caps.

## Problem Statement
Current specs contain selective extension filters, implicit word-count thresholds, and narrow directory lists that cause the pipeline to miss valid files during ingestion. This leads to incomplete repo inventories and missed evidence. The specs must be updated to require exhaustive ingestion with configurable controls instead of hard filters.

## Required spec references
- specs/02_repo_ingestion.md (file discovery, phantom path detection)
- specs/03_product_facts_and_evidence.md (evidence extraction, priority ranking)
- specs/05_example_curation.md (example discovery directories)
- specs/21_worker_contracts.md (W1 and W2 binding contracts)
- plans/taskcards/00_TASKCARD_CONTRACT.md (taskcard format requirements)

## Scope

### In scope
- Replace selective extension filters with exhaustive file recording in spec 02
- Add configurable scan directories via `run_config.ingestion.scan_directories`
- Add `.gitignore` support requirement via `run_config.ingestion.gitignore_mode`
- Remove document processing caps from spec 03
- Add exhaustive processing mandate to W2
- Expand example discovery directories in spec 05 with configurable list
- Update W1 and W2 contracts in spec 21
- Ensure backward compatibility with sensible defaults

### Out of scope
- Schema file changes (separate taskcard)
- Worker implementation changes (separate taskcard)
- Test changes (separate taskcard)
- Changing existing scoring/prioritization logic (only changing filtering to scoring)

## Inputs
- Current spec files (02, 03, 05, 21)
- Healing plan requirements for exhaustive ingestion
- Existing run_config structure

## Outputs
- Updated specs/02_repo_ingestion.md with exhaustive file recording mandate
- Updated specs/03_product_facts_and_evidence.md with no-cap mandate
- Updated specs/05_example_curation.md with expanded discovery
- Updated specs/21_worker_contracts.md with W1/W2 exhaustive mandates
- Evidence report at reports/agents/agent_c/TC-1020/evidence.md
- Self-review at reports/agents/agent_c/TC-1020/self_review.md

## Allowed paths
- specs/02_repo_ingestion.md
- specs/03_product_facts_and_evidence.md
- specs/05_example_curation.md
- specs/21_worker_contracts.md
- plans/taskcards/TC-1020_*
- reports/agents/agent_c/TC-1020/**

### Allowed paths rationale
TC-1020 modifies 4 spec files to mandate exhaustive ingestion and the taskcard/evidence paths for documentation.

## Implementation steps

### Step 1: Update specs/02_repo_ingestion.md
- Replace selective extension filters with exhaustive file recording
- Add configurable scan directories section
- Add .gitignore support requirement
- Add phantom path detection for all file types

### Step 2: Update specs/03_product_facts_and_evidence.md
- Remove document processing caps
- Add exhaustive processing mandate
- Clarify priority ranking is for prioritization not filtering

### Step 3: Update specs/05_example_curation.md
- Expand discovery directories with configurable list
- Relax language-based filtering (unknown still recorded)

### Step 4: Update specs/21_worker_contracts.md
- Add exhaustive file inventory mandate to W1
- Add no-cap processing mandate to W2
- Add references to new config fields

### Step 5: Run tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

### Step 6: Write evidence and self-review

## Failure modes

### Failure mode 1: Spec inconsistency between files
**Detection:** Cross-reference check shows conflicting requirements between spec 02 and spec 21
**Resolution:** Ensure all four specs use identical terminology and cross-reference each other
**Spec/Gate:** All four spec files must be internally consistent

### Failure mode 2: Backward compatibility broken
**Detection:** Existing pilots fail because new mandatory fields have no defaults
**Resolution:** All new config fields must have sensible defaults (e.g., scan_directories defaults to repo root, gitignore_mode defaults to "respect")
**Spec/Gate:** specs/02_repo_ingestion.md backward compatibility requirement

### Failure mode 3: Tests fail after spec updates
**Detection:** pytest returns non-zero exit code
**Resolution:** Review test output; spec-only changes should not break tests; if they do, investigate test assumptions
**Spec/Gate:** Acceptance criteria testing requirements

## Task-specific review checklist
1. [ ] No selective extension filters remain as hard gates in spec 02
2. [ ] W2 processing has no count caps in spec 03
3. [ ] Priority ranking is clearly labeled as prioritization, not filtering in spec 03
4. [ ] Example discovery directories are configurable in spec 05
5. [ ] W1 contract includes exhaustive inventory mandate in spec 21
6. [ ] W2 contract includes no-cap mandate in spec 21
7. [ ] All new config fields have documented defaults
8. [ ] RFC-style language (MUST/SHOULD/MAY) used consistently
9. [ ] Cross-references between specs are consistent

## Deliverables
- Updated specs/02_repo_ingestion.md
- Updated specs/03_product_facts_and_evidence.md
- Updated specs/05_example_curation.md
- Updated specs/21_worker_contracts.md
- Evidence report at reports/agents/agent_c/TC-1020/evidence.md
- Self-review at reports/agents/agent_c/TC-1020/self_review.md

## Acceptance checks
1. [ ] All four spec files updated with exhaustive ingestion mandates
2. [ ] No extension-based filtering gates remain (scoring boosts allowed)
3. [ ] No document processing caps remain
4. [ ] All new config fields have sensible defaults
5. [ ] All tests pass (pytest exit code 0)
6. [ ] Evidence and self-review written

## Preconditions / dependencies
- None (this is a phase-1 spec-only taskcard)

## Test plan
1. Run full test suite to verify no regressions
2. Manual review of spec changes for internal consistency

## Self-review
See reports/agents/agent_c/TC-1020/self_review.md

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

## Integration boundary proven
**Upstream:** Healing plan provides requirements for exhaustive ingestion.
**Downstream:** Implementation taskcards (TC-1021+) will implement the spec changes in worker code.
**Contract:** Specs define binding requirements; implementations must comply.

## Evidence Location
`reports/agents/agent_c/TC-1020/evidence.md`
