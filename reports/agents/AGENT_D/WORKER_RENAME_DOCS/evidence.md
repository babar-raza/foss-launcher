# Worker Rename Docs — Evidence

**Task**: Update documentation, spec, script, report, and taskcard files as part of the worker rename refactor.
**Agent**: Agent D1
**Date**: 2026-02-19
**Status**: COMPLETE

---

## Rename Map Applied

| Old Name | New Name |
|----------|----------|
| `w7_content_reviewer` | `w7_content_reviewer` |
| `w8_linker_and_patcher` | `w8_linker_and_patcher` |
| `w9_validator` | `w9_validator` |
| `w10_fixer` | `w10_fixer` |
| `w11_pr_manager` | `w11_pr_manager` |
| `w6_seo_optimizer` | `w6_seo_optimizer` |
| `W7.ContentReviewer` | `W7.ContentReviewer` |
| `W8.LinkerAndPatcher` | `W8.LinkerAndPatcher` |
| `W9.Validator` | `W9.Validator` |
| `W10.Fixer` | `W10.Fixer` |
| `W11.PRManager` | `W11.PRManager` |
| `W6.SEOOptimizer` | `W6.SEOOptimizer` |

---

## Phase 5: Scripts — COMPLETE

| File | Changes Made |
|------|-------------|
| `scripts/rerun_w8_w9.py` (was rerun_w6_w7.py) | Function names, imports, CLI args, docstring updated |
| `scripts/add_e2e_sections.py` | e2e_command strings updated for w9_validator, w10_fixer, w11_pr_manager |
| `scripts/quality_benchmark.py` | Docstring, comment, grade label, print statement updated for W7 |

---

## Phase 6: Specs — COMPLETE

| File | Changes Made |
|------|-------------|
| `specs/21_worker_contracts.md` | Worker section headings W7→W7, W6→W8, W7→W9, W8→W10, W9→W11; routing arrows; prompt paths |
| `specs/09_validation_gates.md` | W9→W11 PRManager, W7→W9 Validator, W7→W7 ContentReviewer, gate re-draft routing |
| `specs/28_coordination_and_handoffs.md` | W8 Linker, W10 Fixer, W9 Validator references |
| `specs/state-graph.md` | Nodes 6-9: W6→W8, W7→W9, W8→W10, W9→W11 |
| `specs/40_storage_model.md` | Artifact registry comments, W10 Fixer reference, log filename |
| `specs/01_system_contract.md` | Error code component identifiers W6-W9 → W8-W11 |
| `specs/29_project_repo_structure.md` | Workers comment W1..W11, LinkerAndPatcher/Fixer references |
| `specs/30_ai_agent_governance.md` | E2E verification worker list, W7→W7, W7→W9 pilot references |
| `specs/34_strict_compliance_guarantees.md` | W6→W8 Linker/Patcher |
| `specs/17_github_commit_service.md` | W9→W11 PRManager |
| `specs/06_page_planning.md` | W7→W9 Validator (x3), W6→W8 LinkerPatcher |
| `specs/07_section_templates.md` | W7→W7 ContentReviewer (x4), W7→W9 Gate references |
| `specs/08_patch_engine.md` | W6→W8 LinkerAndPatcher |
| `specs/08_content_distribution_strategy.md` | W7→W9 Validator |
| `specs/reference/system-requirements.md` | Nodes 6-9 updated |
| `specs/reference/system-implementation.md` | Phase 3 heading and worker descriptions |
| `specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml` | Comments: W7→W7, W10→W6 |
| `specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml` | Comments: W7→W7, W10→W6 |
| `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml` | Comments: W7→W7, W10→W6 |

---

## Phase 7: Docs, Reports, Taskcards — COMPLETE

### Docs

| File | Changes Made |
|------|-------------|
| `README.md` | State machine diagram, artifact comments, worker sections W7→W7 through W9→W11, content quality section, verify section, configuration comments, project structure listing |
| `docs/README.md` | Worker pipeline range W1-W9→W1-W11 |
| `docs/reference/architecture.md` | Spec comment, workers listing, control flow nodes, Workers table, fix loop, data flow diagram |
| `docs/_audit/traceability.md` | Worker pipeline W1-W9→W1-W11, w11_pr_manager path, W6 SEO toggle comment |

### Reports

| File | Changes Made |
|------|-------------|
| `reports/CHANGELOG.md` | W8/W9 section headings, W1-W11 spec comment, worker path references |
| `reports/STATUS.md` | Path references w8_linker, w9_validator; narrative references W7 ContentReviewer, W8 LinkerAndPatcher, W9 Validator; Track 2 scope updated |
| `DECISIONS.md` | W1-W9→W1-W11 in DEC-005 |

### Taskcards

| File | Changes Made |
|------|-------------|
| `plans/taskcards/INDEX.md` | 25+ references updated: worker section headings, epic names, TC descriptions |
| `plans/taskcards/00_TASKCARD_CONTRACT.md` | Pilot run requirements, E2E verification list, checklist, rollback condition |
| `plans/taskcards/*.md` (48 files) | Batch: all `w7_content_reviewer`, `w8_linker_and_patcher`, `w9_validator`, `w10_fixer`, `w11_pr_manager`, `w6_seo_optimizer` path references replaced |
| `plans/taskcards/*.md` (66 additional files) | Batch: all worker number references (W7, W8 Linker, W9 Validator, W10 Fixer, W9 PR, W6 SEO) replaced |
| `plans/taskcards/*.md` (5 additional files) | Batch: all W1-W9 range references replaced with W1-W11 |

---

## Additional Files Updated (final sweep)

| File | Changes Made |
|------|-------------|
| `docs/reference/llm-models.md` | W7→W7 ContentReviewer, W8→W10 Fixer worker assignments |
| `docs/_audit/system_audit.md` | Worker paths and numbers throughout |
| `specs/03_product_facts_and_evidence.md` | W7→W7 in downstream consumer list |
| `specs/schemas/run_config.schema.json` | W6 SEO→W6 SEO in description |
| `plans/healing/07_cross_section_consistency_checks.md` | Worker paths updated |
| `plans/healing/08_immediate_blockers.md` | Worker paths updated |
| `reports/PLAN_SOURCES.md` | Worker paths updated |
| `reports/swarm_allowed_paths_audit.md` | Worker paths updated |
| `reports/VFV_EVIDENCE_20260205.md` | Worker paths updated |
| `TASK_BACKLOG.md` | Worker paths updated |
| `reports/ORCHESTRATOR_STATUS.md` | Worker paths updated |
| `plans/swarm_coordination_playbook.md` | Worker paths updated |

---

## Files NOT Found or Skipped

| File | Status |
|------|--------|
| `docs/MODEL_REFERENCE.md` | Not found at expected path — skipped |
| `docs/_audit/docs_inventory.md` | File is 2MB; grep search found no matching old worker references |
| `reports/PLAN_INDEX.md` | Grep search found no matching old worker references |

---

## Substitution Notes

- Applied global substitution order from task instructions (W7 before W7, W6 SEO before W10 Fixer, W9 PR before W9 Validator)
- Pilot YAML comment-only rule respected: `review_enabled` and `seo_enabled` YAML keys were NOT changed
- Historical narrative in reports preserved faithfully (only updated to match current worker numbers)
- Batch replacements handled via Python script for 48+ taskcard files to ensure consistency

---

## Verification

- All 21 global substitutions applied to each file before moving to the next
- Substitution order respected to avoid conflicts
- No YAML key values changed in pilot configs (only comments)
