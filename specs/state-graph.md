# State Graph (authoritative, implementation-oriented)

This document is the single authoritative workflow definition for the orchestrator.
It MUST remain consistent with:
- `specs/11_state_and_events.md` (events)
- `specs/21_worker_contracts.md` (worker I/O)
- `specs/28_coordination_and_handoffs.md` (handoffs + loops)

## Conventions
- `RUN_DIR = runs/<run_id>/` (see `specs/29_project_repo_structure.md`)

## Run states (authoritative)
CREATED → CLONED_INPUTS → INGESTED → FACTS_READY → PLAN_READY → DRAFTING
→ DRAFT_READY → LINKING → VALIDATING → (FIXING → VALIDATING)* → READY_FOR_PR
→ PR_OPENED → DONE

Failure: any state → FAILED  
Cancel: any state → CANCELLED (optional; see MCP tools)

## Required artifacts by state
- CLONED_INPUTS:
  - resolved repo_sha and site_sha recorded in `repo_inventory.json`
  - `RUN_DIR/artifacts/frontmatter_contract.json`
- INGESTED:
  - `RUN_DIR/artifacts/repo_inventory.json`
- FACTS_READY:
  - `RUN_DIR/artifacts/product_facts.json`
  - `RUN_DIR/artifacts/evidence_map.json`
  - `RUN_DIR/artifacts/snippet_catalog.json`
- PLAN_READY:
  - `RUN_DIR/artifacts/page_plan.json`
- DRAFT_READY:
  - drafts exist for all required sections under `RUN_DIR/drafts/<section>/`
- LINKING:
  - `RUN_DIR/artifacts/patch_bundle.json` exists
  - `RUN_DIR/reports/diff_report.md` exists
- VALIDATING:
  - `RUN_DIR/artifacts/validation_report.json` exists
- READY_FOR_PR:
  - last `validation_report.json` has `ok=true`

## Orchestrator nodes (graph nodes)
Each node corresponds to (one or more) workers and emits `RUN_STATE_CHANGED` on transition.

### Node 1: clone_inputs
**Entry state:** CREATED  
**Worker:** W1 RepoScout  
**Outputs:** `RUN_DIR/artifacts/repo_inventory.json`, `RUN_DIR/artifacts/frontmatter_contract.json`, `RUN_DIR/artifacts/site_context.json`, `RUN_DIR/artifacts/hugo_facts.json`  
**Exit state:** CLONED_INPUTS

**Failure:** missing config → FAILED (blocker)

---

### Node 2: ingest_repo
**Entry state:** CLONED_INPUTS  
**Worker:** none (optional placeholder)  
**Purpose:** reserved for future steps that materialize extra sources (e.g., download external docs).  
**Exit state:** INGESTED

**Binding rule:** if unused, this node is a no-op that still records state transition deterministically.

---

### Node 3: build_facts
**Entry state:** INGESTED  
**Workers:** W2 FactsBuilder → W3 SnippetCurator (ordered)  
**Outputs:** `RUN_DIR/artifacts/product_facts.json`, `RUN_DIR/artifacts/evidence_map.json`, `RUN_DIR/artifacts/snippet_catalog.json`  
**Exit state:** FACTS_READY

**Failure rules:**
- missing evidence for required claims with `allow_inference=false` → FAILED (blocker)

---

### Node 4: build_plan
**Entry state:** FACTS_READY  
**Worker:** W4 IAPlanner  
**Outputs:** `RUN_DIR/artifacts/page_plan.json`  
**Exit state:** PLAN_READY

---

### Node 5: draft_sections (fan-out)
**Entry state:** PLAN_READY  
**Workers:** W5 SectionWriter per section (parallel)  
**Outputs:** drafts under `RUN_DIR/drafts/<section>/...`  
**Exit state:** DRAFT_READY

**Parallel safety rule (binding):**
- writers write only to `drafts/<section>/`
- writers never touch the site worktree

---

### Node 6: merge_and_link
**Entry state:** DRAFT_READY  
**Worker:** W6 LinkerAndPatcher  
**Outputs:** `RUN_DIR/artifacts/patch_bundle.json`, `RUN_DIR/reports/diff_report.md`  
**Exit state:** LINKING

---

### Node 7: validate
**Entry state:** LINKING or FIXING  
**Worker:** W7 Validator  
**Outputs:** `RUN_DIR/artifacts/validation_report.json`  
**Exit state:** VALIDATING

---

### Node 8: fix_next (single-issue)
**Entry state:** VALIDATING  
**Condition:** `validation_report.ok == false`  
**Worker:** W8 Fixer  
**Exit state:** FIXING

**Selection rule (binding):**
- the Orchestrator selects exactly one issue:
  - first by stable ordering in `specs/10_determinism_and_caching.md`
  - must be severity blocker/error (warning-only does not enter fix loop)

**Stop rules (binding):**
- attempts >= `run_config.max_fix_attempts` → FAILED
- FixNoOp → FAILED
- AllowedPathsViolation → FAILED

After FIXING, the graph MUST route to Node 7 validate.

---

### Node 9: open_pr
**Entry state:** VALIDATING  
**Condition:** `validation_report.ok == true`  
**Worker:** W9 PRManager  
**Exit state:** PR_OPENED → DONE

---

### Node 10: finalize
**Entry state:** DONE  
**Worker:** none  
**Outputs:** optional summary report under `reports/`  
**Exit state:** DONE (idempotent)

## Deterministic routing rules (binding)
- Sections order: products, docs, reference, kb, blog
- Pages order: `(section_order, output_path)`
- Issues order: `(severity, gate, path, line, issue_id)`
- Fix loop always selects the first issue under the above ordering.

## Acceptance
- Every node maps cleanly to a worker contract with explicit inputs/outputs.
- The fan-out drafting node is parallel-safe by construction.
- The fix loop is explicit and capped, with deterministic issue selection.
