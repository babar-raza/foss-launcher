---
id: TC-1301
title: "W7 LLM Agent Implementation — Replace Stubs with Real Enhancement Agents"
status: Draft
priority: Critical
owner: "Agent B (Backend/Workers)"
updated: "2026-02-11"
tags: ["w5.5", "content-reviewer", "llm", "agent-regen", "pipeline-hardening"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1301_w5_5_llm_agent_implementation.md
  - src/launch/workers/w7_content_reviewer/worker.py
  - src/launch/workers/w7_content_reviewer/fixes/llm_regen.py
  - tests/unit/workers/w7_content_reviewer/test_llm_regen.py
  - tests/unit/workers/w7_content_reviewer/test_worker.py
evidence_required:
  - reports/agents/AGENT_B/TC-1301/evidence.md
  - reports/agents/AGENT_B/TC-1301/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1301 — W7 LLM Agent Implementation

## Objective
Replace the 3 stub agent functions in `llm_regen.py` with real implementations that read draft files, call the LLM with enhancement prompts, validate the output, and write improved content back. This completes the W7 ContentReviewer's intended capability: deterministic auto-fixes for simple issues, LLM regeneration for complex issues.

### Why this matters
Currently `_spawn_content_enhancer()`, `_spawn_technical_fixer()`, and `_spawn_usability_improver()` return dummy success dicts (`"status": "success"`, `"files_modified": []`) without reading drafts, calling LLM, or writing any changes. The review pipeline detects issues, scores them, and routes to agents — but the agents do nothing. This means error/blocker severity issues that cannot be auto-fixed are silently ignored.

## Required spec references
- W7 ContentReviewer implementation plan (abstract-hugging-kite.md)
- src/launch/workers/w7_content_reviewer/fixes/llm_regen.py (current stubs)
- src/launch/workers/w7_content_reviewer/worker.py (current invocation flow)
- src/launch/workers/w7_content_reviewer/fixes/auto_fixes.py (auto-fix pattern for reference)
- src/launch/clients/llm_provider.py (LLMProviderClient interface — read-only reference)
- Agent prompt templates in `src/launch/workers/w7_content_reviewer/agents/*.md`

## Scope

### In scope
1. **Wire LLM client into W7 worker** — Create LLM client from `run_config` in `execute_content_reviewer()`, pass to `spawn_enhancement_agents()`
2. **Update `spawn_enhancement_agents()` signature** — Accept `llm_client` and `drafts_dir` parameters
3. **Implement all 3 agent functions** — Each reads draft(s), calls LLM, validates output, writes back
4. **Output validation guardrails** — Claim marker preservation, frontmatter integrity, size bounds
5. **Move agent invocation before review_report.json** — Agents must modify files BEFORE final scoring
6. **Re-check after agent modifications** — Re-run all checks and re-score after LLM changes
7. **Graceful degradation** — If `llm_client is None`, skip LLM agents (current behavior preserved)
8. **Unit tests** — Mock LLM calls, test validation, test integration flow

### Out of scope
- Modifying auto-fix functions (deterministic fixes unchanged)
- Modifying check modules (content_quality, technical_accuracy, usability unchanged)
- Modifying scoring logic
- Modifying prompt template files (agents/*.md — existing prompts are sufficient)
- Changes to LLM provider client (`src/launch/clients/**` — shared library, read-only)

## Inputs
- Draft markdown files in `{run_dir}/drafts/` (produced by W5)
- `product_facts.json`, `snippet_catalog.json`, `evidence_map.json`, `page_plan.json` (context for prompts)
- `run_config` (LLM configuration for client creation)
- Agent prompt templates from `agents/` directory

## Outputs
- `llm_regen.py` (UPDATED — 3 real agent implementations, ~200 lines added)
- `worker.py` (UPDATED — LLM client creation + agent invocation reorder, ~40 lines changed)
- `tests/unit/workers/w7_content_reviewer/test_llm_regen.py` (UPDATED — new tests, ~100 lines added)
- Modified draft files (at runtime — agents write improved content)
- Evidence bundle

## Allowed paths
- plans/taskcards/TC-1301_w5_5_llm_agent_implementation.md
- src/launch/workers/w7_content_reviewer/worker.py
- src/launch/workers/w7_content_reviewer/fixes/llm_regen.py
- tests/unit/workers/w7_content_reviewer/test_llm_regen.py
- tests/unit/workers/w7_content_reviewer/test_worker.py

### Allowed paths rationale
All changes are within the W7 worker package and its tests. The LLM client from `src/launch/clients/` is imported and used (read-only) — no modifications to shared libraries. Prompt templates in `agents/*.md` are read-only inputs.

## Implementation steps

### Step 1: Read current state of all target files
Read `worker.py`, `llm_regen.py`, existing tests, and at least one agent prompt template. Understand:
- How `execute_content_reviewer()` flows (checks → auto-fixes → re-check → scoring → agents → report)
- How `spawn_enhancement_agents()` is called and what it returns
- What `build_enhancement_prompt()` produces
- What `_load_agent_template()` returns

**Resilience note**: The worker may have additional fix passes or re-check cycles added by other taskcards. Do NOT assume the exact structure — adapt to what exists. The key insertion point is where `spawn_enhancement_agents()` is called.

### Step 2: Add LLM client creation to worker.py
In `execute_content_reviewer()`, after loading artifacts and before the checks loop, add LLM client creation:

```python
from launch.clients.llm_provider import create_llm_client_from_config

# Create LLM client for agent enhancement (optional — degrades gracefully)
llm_client = None
try:
    llm_client = create_llm_client_from_config(
        run_config=run_config,
        run_dir=run_dir,
    )
except Exception:
    pass  # No LLM client available — agents will skip
```

**Resilience note**: Check if `create_llm_client_from_config` exists at execution time. Its signature may have additional parameters (telemetry_client, etc.). Match the actual signature. If it requires parameters not available in W7 context, pass `None` for optional ones.

### Step 3: Update spawn_enhancement_agents() signature in llm_regen.py
Change the function signature from:
```python
def spawn_enhancement_agents(issues, run_dir, run_config)
```
To:
```python
def spawn_enhancement_agents(issues, run_dir, run_config, llm_client=None, drafts_dir=None)
```

Pass both new parameters down to `_spawn_content_enhancer()`, `_spawn_technical_fixer()`, and `_spawn_usability_improver()`.

**Resilience note**: The function may already have been extended by another taskcard. If `llm_client` is already a parameter, skip this change.

### Step 4: Implement shared helper `_enhance_draft_with_llm()`
Add a new private function that all 3 agents share:

```python
def _enhance_draft_with_llm(
    agent_type: str,
    issues: List[Dict],
    drafts_dir: Path,
    run_dir: Path,
    run_config: Dict,
    llm_client: Any,
) -> Dict:
    """Enhance draft file(s) using LLM agent.

    1. Groups issues by file path
    2. For each affected file:
       a. Reads draft content
       b. Builds enhancement prompt via build_enhancement_prompt()
       c. Calls llm_client.chat_completion()
       d. Validates output (claim markers, frontmatter, size)
       e. Writes improved content back if valid
    3. Returns result dict with files_modified list
    """
```

**Key implementation details:**

a. **Group issues by file path** — Each file gets a single LLM call with all its issues
b. **Read draft** — `Path(drafts_dir / relative_path).read_text(encoding="utf-8")`
c. **Build prompt** — Call existing `build_enhancement_prompt(agent_type, issues, content, context)` where context includes product name and page role
d. **Call LLM** — `llm_client.chat_completion(messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}], call_id=f"w5_5_{agent_type}_{file_slug}")`
e. **Validate output** — See Step 5 below
f. **Write back** — Only if validation passes; otherwise keep original
g. **Return result** — `{"agent_type": agent_type, "status": "success", "issues_addressed": N, "files_modified": [paths]}`

### Step 5: Implement output validation function `_validate_enhancement()`
Add a validation function that checks LLM output before writing:

```python
def _validate_enhancement(
    original: str,
    enhanced: str,
    agent_type: str,
) -> tuple:
    """Validate LLM-enhanced content against safety guardrails.

    Returns:
        (is_valid: bool, rejection_reason: Optional[str])
    """
```

**Guardrails:**
1. **Claim marker preservation** — Count `[claim: ...]` markers in original vs enhanced. Enhanced must have >= 90% of original markers (allows minor restructuring).
2. **Frontmatter integrity** — If original starts with `---`, enhanced must also start with `---` and have a closing `---`.
3. **Size bounds** — Enhanced length must be between 50% and 200% of original length. Prevents both content removal and hallucination bloat.
4. **Non-empty** — Enhanced must be non-empty and not just whitespace.
5. **No `<think>` tags** — Strip any model reasoning leaks (reuse W5 post-processing pattern).

### Step 6: Replace the 3 stub functions
Replace each stub with a call to `_enhance_draft_with_llm()`:

```python
def _spawn_content_enhancer(issues, run_dir, run_config, llm_client=None, drafts_dir=None):
    if not llm_client or not drafts_dir:
        return {"agent_type": "content_enhancer", "status": "skipped",
                "issues_addressed": 0, "files_modified": [],
                "error": "No LLM client or drafts_dir — skipping enhancement"}
    return _enhance_draft_with_llm("content_enhancer", issues, drafts_dir, run_dir, run_config, llm_client)
```

Same pattern for `_spawn_technical_fixer` and `_spawn_usability_improver`.

**Resilience note**: If additional parameters were added to the stub signatures by another taskcard, preserve them. The key change is calling `_enhance_draft_with_llm()` instead of returning a dummy dict.

### Step 7: Reorder agent invocation in worker.py
Find where `spawn_enhancement_agents()` is called. Currently it's called AFTER `review_report.json` is written. Move it to BEFORE the report, and add a re-check:

**New flow:**
```
1. Initial checks (3 dimensions)
2. Auto-fixes (deterministic)
3. Re-check after auto-fixes
4. Score and route
5. IF status in (NEEDS_CHANGES, REJECT):
   a. Call spawn_enhancement_agents(all_issues, run_dir, run_config, llm_client, drafts_dir)
   b. IF any files_modified:
      i. Re-run all checks (3 dimensions)
      ii. Re-calculate scores
      iii. Re-route
6. Build review_report with FINAL scores
7. Write review_report.json
```

**Resilience note**: The worker may already have multiple check/fix/re-check cycles. Insert the agent call after the last auto-fix cycle and before the report is written. Use the pattern of the existing re-check cycles as a template.

### Step 8: Pass LLM client and drafts_dir to spawn_enhancement_agents()
Update the call site in `worker.py`:

```python
agent_results = spawn_enhancement_agents(
    all_issues, run_dir, run_config,
    llm_client=llm_client,
    drafts_dir=drafts_dir,
)
```

### Step 9: Write unit tests
Update `tests/unit/workers/w7_content_reviewer/test_llm_regen.py`:

**New test cases:**

1. **test_enhance_draft_calls_llm** — Mock LLM client, verify `chat_completion()` is called with correct prompt structure. Verify draft file is updated. (Tag: "Testing: mocked")
2. **test_enhance_draft_validates_output** — Mock LLM returning content with missing claim markers → verify original is preserved, file NOT modified.
3. **test_enhance_draft_validates_frontmatter** — Mock LLM returning content without frontmatter → verify rejection.
4. **test_enhance_draft_validates_size_bounds** — Mock LLM returning 3x content → verify rejection (>200%).
5. **test_enhance_draft_strips_think_tags** — Mock LLM returning `<think>...</think>` prefix → verify stripped before validation.
6. **test_spawn_skips_without_llm_client** — `llm_client=None` → returns `"status": "skipped"` (backward compat).
7. **test_spawn_skips_without_drafts_dir** — `drafts_dir=None` → returns `"status": "skipped"`.
8. **test_integration_agents_modify_scores** — End-to-end: create a draft with known issues, mock LLM returning fixed content, verify scores improve after agent pass.

Also update `test_worker.py` if needed to account for `llm_client` in `execute_content_reviewer` flow.

### Step 10: Run all W7 tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/w7_content_reviewer/ -v
```

Ensure zero regressions in existing tests.

## Failure modes

### Failure mode 1: LLM returns invalid/hallucinated content
**Detection**: `_validate_enhancement()` catches claim marker loss, missing frontmatter, or size violation.
**Resolution**: Keep original draft file unchanged. Log validation failure reason. Return `"status": "failed"` for that file but continue with other files. This is the primary safety net.
**Spec/Gate**: W7 spec — content must not degrade through review pipeline

### Failure mode 2: LLM client creation fails in worker.py
**Detection**: `try/except` around `create_llm_client_from_config()` catches the exception.
**Resolution**: `llm_client = None` → agents return `"status": "skipped"`. Pipeline continues with auto-fixes only. Zero degradation vs current behavior.
**Spec/Gate**: specs/21_worker_contracts.md — workers must be fault-tolerant

### Failure mode 3: Agent prompt template not found
**Detection**: `_load_agent_template()` already has fallback to generic template (existing code).
**Resolution**: Generic template is sufficient for basic enhancement. No new failure path.
**Spec/Gate**: llm_regen.py line 156 (existing fallback)

### Failure mode 4: Re-check after agent modifications reveals new issues
**Detection**: Post-agent score is lower than pre-agent score.
**Resolution**: This is possible (LLM changes may introduce style issues). The pipeline does not roll back — the final score is the truth. If this becomes systematic, the prompts should be refined (out of scope for this taskcard).
**Spec/Gate**: W7 scoring contract — score reflects actual state

## Task-specific review checklist
1. [ ] `_enhance_draft_with_llm()` reads draft, calls LLM, validates, writes back
2. [ ] `_validate_enhancement()` checks claim markers (>=90%), frontmatter, size bounds
3. [ ] All 3 stub functions replaced with real implementations calling `_enhance_draft_with_llm()`
4. [ ] Graceful degradation: `llm_client=None` → agents skip (backward compat)
5. [ ] Agent invocation happens BEFORE `review_report.json` is written
6. [ ] Re-check + re-score happens after agent modifications
7. [ ] `<think>` tags stripped from LLM output
8. [ ] Issues grouped by file path (one LLM call per file, not per issue)
9. [ ] 8 unit tests covering LLM calls, validation, skipping, and integration
10. [ ] Zero regressions in existing W7 tests
11. [ ] LLM call evidence saved (via llm_provider evidence capture)
12. [ ] `call_id` uses descriptive format: `w5_5_{agent_type}_{file_slug}`

## Deliverables
- src/launch/workers/w7_content_reviewer/fixes/llm_regen.py (UPDATED — real agents)
- src/launch/workers/w7_content_reviewer/worker.py (UPDATED — LLM client + reorder)
- tests/unit/workers/w7_content_reviewer/test_llm_regen.py (UPDATED — 8 new tests)
- tests/unit/workers/w7_content_reviewer/test_worker.py (UPDATED — if needed)
- reports/agents/AGENT_B/TC-1301/evidence.md
- reports/agents/AGENT_B/TC-1301/self_review.md

## Acceptance checks
1. [ ] 3 stub functions replaced with real LLM-calling implementations
2. [ ] Mock LLM test: enhanced content written to draft file
3. [ ] Validation test: invalid LLM output → original preserved (no degradation)
4. [ ] Backward compat: no LLM client → identical behavior to current stubs
5. [ ] Worker flow: agents run BEFORE review_report, scores reflect agent changes
6. [ ] All W7 unit tests pass (new + existing)
7. [ ] Claim markers preserved in enhanced output (>=90% retention)

## Preconditions / dependencies
- None — this taskcard is independent of TC-1300 (W2 changes)
- Existing `build_enhancement_prompt()` function is already implemented and tested
- Existing agent prompt templates in `agents/*.md` are available
- `create_llm_client_from_config` exists in `src/launch/clients/llm_provider.py` (read-only import)

## Test plan
1. Unit tests: 8 new tests in `test_llm_regen.py`
2. Regression: All existing W7 tests must pass (`test_worker.py`, `test_checks.py`, `test_auto_fixes.py`)
3. Integration: Pilot dry run with `review_enabled=true` should show agent invocation logs

## Self-review
[To be completed by Agent B after implementation]
