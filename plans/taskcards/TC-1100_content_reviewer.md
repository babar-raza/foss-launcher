---
id: TC-1100
title: "W5.5 ContentReviewer Implementation"
status: Done
priority: P1
owner: orchestrator
created: "2026-02-09"
updated: "2026-02-09"
spec_ref: "482eb69"
depends_on: []
ruleset_version: "v1"
templates_version: "v1"
allowed_paths:
  - "src/launch/workers/w5_5_content_reviewer/**"
  - "src/launch/orchestrator/graph.py"
  - "src/launch/orchestrator/worker_invoker.py"
  - "specs/schemas/review_report.schema.json"
  - "specs/21_worker_contracts.md"
  - "specs/schemas/run_config.schema.json"
  - "tests/unit/workers/w5_5_content_reviewer/**"
  - "reports/agents/**"
evidence_required:
  - "Unit tests pass (95%+ coverage)"
  - "Both pilots complete with review enabled"
  - "review_report.json schema-compliant"
  - "12D self-review all dimensions >=4/5"
---

# TC-1100: W5.5 ContentReviewer Implementation

## Objective
Implement W5.5 ContentReviewer - a quality gate between W5 (SectionWriter) and W6 (LinkerPatcher) that reviews content across 3 dimensions (Content Quality, Technical Accuracy, Usability) and applies auto-fixes or delegates to specialist agents for complex issues.

## Problem Statement
Generated markdown content from W5 SectionWriter may contain quality issues (readability, paragraph structure), technical inaccuracies (hallucinated APIs, wrong install commands), and usability problems (missing CTAs, poor navigation). Without a review step, these issues propagate to the final PR. W5.5 acts as an automated quality gate to catch and fix issues before W6 patching.

## Required spec references
- specs/21_worker_contracts.md (W5.5 ContentReviewer contract)
- specs/schemas/review_report.schema.json (review report artifact schema)
- specs/schemas/run_config.schema.json (review_enabled flag)
- specs/07_section_templates.md (template structure)
- specs/23_claim_markers.md (claim marker format)

## Scope

### In scope
- 36 checks across 3 dimensions (12 per dimension)
- 9 auto-fix functions for common issues
- LLM regeneration with agent delegation (3 specialist agents)
- Pipeline integration (graph.py, worker_invoker.py)
- review_report.schema.json artifact
- review_enabled flag in run_config
- Unit tests with 95%+ coverage

### Out of scope
- Changing W5 SectionWriter logic
- Modifying W6 LinkerPatcher behavior
- Adding new validation gates to W7
- Changing claim marker format

## Inputs
- `RUN_DIR/drafts/**/*.md` (generated markdown from W5)
- `RUN_DIR/artifacts/product_facts.json` (product context)
- `RUN_DIR/artifacts/snippet_catalog.json` (code snippets)
- `RUN_DIR/artifacts/page_plan.json` (planned pages)
- `RUN_DIR/artifacts/evidence_map.json` (evidence citations)
- `run_config.review_enabled` (feature flag)

## Outputs
- `RUN_DIR/artifacts/review_report.json` (schema: review_report.schema.json)
- `RUN_DIR/drafts/**/*.md` (enhanced markdown, same paths)
- `RUN_DIR/artifacts/review_iterations.json` (iteration history)

## Allowed paths
- src/launch/workers/w5_5_content_reviewer/**
- src/launch/orchestrator/graph.py
- src/launch/orchestrator/worker_invoker.py
- specs/schemas/review_report.schema.json
- specs/21_worker_contracts.md
- specs/schemas/run_config.schema.json
- tests/unit/workers/w5_5_content_reviewer/**
- reports/agents/**

### Allowed paths rationale
TC-1100 implements a new worker (W5.5) in the pipeline. It requires creating the worker code, updating the orchestrator to invoke it, defining the schema for its output artifact, updating the worker contracts spec, and adding the feature flag to run_config.

## Phases
- Phase 1: Core Review Logic (6 files, 2,226 LOC) -- DONE
- Phase 2: Auto-Fix Capabilities (3 files, 1,087 LOC) -- DONE
- Phase 3: Agent Delegation (4 files) -- DONE
- Phase 4: Pipeline Integration (10 files) -- DONE
- Phase 5: Testing + Verification -- DONE

## Implementation steps

### Step 1: Agent Prompt Templates (Phase 3)
Create 3 specialist agent prompts in `src/launch/workers/w5_5_content_reviewer/agents/`:
- `content_enhancer_agent.md` - Content quality fixes
- `technical_fixer_agent.md` - Technical accuracy fixes
- `usability_improver_agent.md` - Usability improvements

### Step 2: Review Report Schema (Phase 4)
Create `specs/schemas/review_report.schema.json` with required fields: review_id, run_dir, timestamp, overall_status, dimension_scores, severity_counts, pages_reviewed/passed/failed, issues array.

### Step 3: Worker Contract Update (Phase 4)
Add W5.5 ContentReviewer section to `specs/21_worker_contracts.md` between W5 and W6, documenting inputs, outputs, review dimensions, routing, timeouts, and events.

### Step 4: Run Config Schema Update (Phase 4)
Add `review_enabled` boolean flag to `specs/schemas/run_config.schema.json` near other boolean flags (allow_inference, allow_manual_edits).

### Step 5: Pipeline Integration (Phase 4)
Wire W5.5 into the orchestrator graph between W5 and W6, conditional on `review_enabled` flag.

### Step 6: Testing (Phase 5)
Write unit tests covering all 36 checks, auto-fix functions, agent delegation, and routing logic.

## Failure modes

### Failure mode 1: Review timeout exceeds budget
**Detection:** Worker execution exceeds configured timeout (300s local, 600s ci/prod)
**Resolution:** Implement early termination with partial review_report; reduce check complexity
**Spec/Gate:** specs/21_worker_contracts.md W5.5 Timeout section

### Failure mode 2: Agent LLM call fails
**Detection:** LLM provider returns error (429, 500, timeout) during agent delegation
**Resolution:** Fall back to auto-fix only (no LLM regeneration); mark affected pages in review_report
**Spec/Gate:** specs/21_worker_contracts.md W5.5 Edge cases

### Failure mode 3: Auto-fix introduces new issues
**Detection:** Re-review after auto-fix shows higher issue count or new blockers
**Resolution:** Revert to pre-fix content; increment iteration counter; route to REJECT after max iterations
**Spec/Gate:** specs/21_worker_contracts.md W5.5 Routing (NEEDS_CHANGES -> REJECT)

## Task-specific review checklist
1. [x] All 36 checks implemented (12 per dimension)
2. [x] 9 auto-fix functions working correctly
3. [x] 3 agent prompt templates created with proper placeholders
4. [x] review_report.schema.json validates against JSON Schema draft 2020-12
5. [x] W5.5 section in worker contracts complete with all subsections
6. [x] review_enabled flag added to run_config schema
7. [x] Pipeline integration is conditional on review_enabled
8. [x] Routing logic handles PASS/NEEDS_CHANGES/REJECT correctly

## Acceptance checks
- [x] 36 checks implemented (12 per dimension)
- [x] 9 auto-fix functions working
- [x] LLM regeneration with agent delegation
- [x] Pipeline integration (graph.py, worker_invoker.py)
- [x] review_report.schema.json validated
- [x] Unit tests pass (95%+ coverage)
- [x] Both pilots PASS with review enabled

## Deliverables
- `src/launch/workers/w5_5_content_reviewer/agents/content_enhancer_agent.md`
- `src/launch/workers/w5_5_content_reviewer/agents/technical_fixer_agent.md`
- `src/launch/workers/w5_5_content_reviewer/agents/usability_improver_agent.md`
- `specs/schemas/review_report.schema.json`
- `specs/21_worker_contracts.md` (updated with W5.5 section)
- `specs/schemas/run_config.schema.json` (updated with review_enabled)
- `plans/taskcards/TC-1100_content_reviewer.md`
- `reports/agents/agent_d/TC-1100-P3-prompts/` (evidence)
- `reports/agents/agent_d/TC-1100-P4-specs/` (evidence)

## Preconditions / dependencies
- W5.5 Phase 1 (Core Review Logic) complete
- W5.5 Phase 2 (Auto-Fix Capabilities) complete
- specs/21_worker_contracts.md exists with W5 and W6 sections

## Test plan
1. Validate review_report.schema.json against a sample report
2. Verify agent prompt templates contain all required placeholders ({issues}, {content}, {context})
3. Verify W5.5 section in worker contracts is between W5 and W6
4. Verify review_enabled field in run_config schema has correct type and default
5. Run both pilots with review_enabled: true and verify review_report.json artifact

## E2E verification
Run both pilots with `review_enabled: true` and verify review_report.json artifact.

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/tc1100_3d
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output runs/tc1100_note
```

**Expected artifacts:**
- `runs/tc1100_3d/artifacts/review_report.json` - Schema-compliant review report
- `runs/tc1100_note/artifacts/review_report.json` - Schema-compliant review report

**Expected results:**
- Both pilots complete end-to-end with exit code 0
- review_report.json validates against review_report.schema.json
- All dimension scores >= 4/5

## Integration boundary proven
**Upstream:** W5 SectionWriter produces `RUN_DIR/drafts/**/*.md` files. W5.5 reads these as input along with artifact JSONs.

**Downstream:** W5.5 enhances drafts in-place (same file paths). W6 LinkerAndPatcher reads the enhanced drafts transparently -- no interface change needed.

**Contract:**
- W5.5 is transparent to W6 -- it enhances drafts in-place before patching
- review_report.json is a new artifact (does not replace any existing artifact)
- review_enabled=false means W5.5 is skipped entirely (passthrough)

## Self-review

### 12D Checklist
1. **Determinism:** Review checks are deterministic (no random sampling, stable ordering)
2. **Dependencies:** No new external dependencies; uses existing LLM client
3. **Documentation:** Worker contracts spec updated, schema created, agent prompts documented
4. **Data preservation:** Drafts enhanced in-place; original content preserved in review_iterations.json
5. **Deliberate design:** 3 dimensions chosen to cover content, technical, and UX quality
6. **Detection:** review_report.json captures all issues with severity and auto_fixable flags
7. **Diagnostics:** Telemetry events for REVIEW_STARTED, PAGE_REVIEWED, FIX_APPLIED, REVIEW_COMPLETED
8. **Defensive coding:** Timeout handling, max iterations, graceful LLM failure fallback
9. **Direct testing:** Unit tests for all 36 checks, auto-fix functions, routing logic
10. **Deployment safety:** review_enabled defaults to false; opt-in only
11. **Delta tracking:** Taskcard TC-1100 tracks all phases; evidence in reports/agents/agent_d/
12. **Downstream impact:** W6 is unaffected (reads same draft paths); new review_report.json artifact added

### Verification results
- [x] Tests: 2660+ passed, 0 failed
- [x] Validation: review_report.schema.json created and updated
- [x] Evidence captured: reports/agents/ directories

## Evidence Location
`reports/agents/agent_d/TC-1100-P3-prompts/` and `reports/agents/agent_d/TC-1100-P4-specs/`
