# STRICT IMPLEMENTATION PROMPT FOR CLAUDE CODE IN VS CODE

**Status**: 🟢 READY FOR IMPLEMENTATION (All gaps filled, specifications complete)

**Mode**: STRICT COMPLIANCE — No improvisation, No guessing, No plan changes

---

## CRITICAL PREAMBLE: READ FIRST

This prompt authorizes you to implement the FOSS Launcher system **precisely as specified**. The project is:
- ✅ Fully specified (33 binding specs)
- ✅ Fully planned (39 Ready taskcards)
- ✅ Fully decided (7 active decisions, 0 open questions)
- ✅ Swarm-ready (infrastructure verified)

**Your role**: Execute taskcards, not improve them. Ambiguities that arise must be escalated as blocker issues, not resolved via guess-work.

---

## PHASE 0: MANDATORY PREFLIGHT (Do this first, every time)

Before you start ANY work:

### Step 0.1: Activate Virtual Environment
```bash
# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```
**Verify**: `which python` (or `where python` on Windows) must show `.venv` in path.

### Step 0.2: Validate Repository Readiness
```bash
python tools/validate_dotvenv_policy.py
```
**Expected output**: "✅ .venv policy enforced" (0 violations)

### Step 0.3: Validate Swarm Configuration
```bash
python tools/validate_swarm_ready.py
```
**Expected output**: All gates PASS, "🟢 SWARM READY"
- Gate A: Taskcard schema validation ✅
- Gate B: Frontmatter consistency ✅
- Gate C: Dependency graph ✅
- Gate D: Markdown link integrity ✅
- Gate E: Allowed paths (zero shared-lib violations) ✅

**If any gate fails**: STOP. Do not proceed. The repository is not ready.

### Step 0.4: Regenerate Status Board (Optional but Recommended)
```bash
python tools/generate_status_board.py
```
This ensures you have the latest STATUS_BOARD view.

### Step 0.5: Understand Your Taskcard
Pick ONE taskcard from `plans/taskcards/` that is marked "Ready" and unassigned in STATUS_BOARD:
```markdown
# Example: TC-200 (Schemas and IO foundations)
```
Read the ENTIRE taskcard file carefully, including:
- YAML frontmatter (id, title, status, depends_on, allowed_paths, evidence_required)
- Objective
- Required spec references (read these specs first)
- Scope (in scope / out of scope)
- Inputs and Outputs
- Implementation steps (step by step)
- Allowed paths (write fence — you may ONLY edit these)
- E2E verification
- Deliverables
- Acceptance checks
- Self-review template

---

## PHASE 1: IMPLEMENTATION WORKFLOW (Per Taskcard)

### Step 1.1: Create Feature Branch
```bash
git checkout -b feat/<taskcard-id>-<slug>
# Example: feat/TC-200-schemas-and-io
```

### Step 1.2: Update Taskcard Status (in plans/taskcards/<TASKCARD_FILE>.md)
YAML frontmatter only:
```yaml
---
id: TC-200
title: "Schemas and IO foundations"
status: In-Progress          # ← Change from "Ready" to "In-Progress"
owner: "<your-agent-name>"  # ← Assign yourself
updated: "2026-01-23"       # ← Update date
depends_on: [TC-100]
allowed_paths: [...]
evidence_required: [...]
---
```

### Step 1.3: Regenerate Status Board
```bash
python tools/generate_status_board.py
```
Verify your taskcard now shows as "In-Progress" with your name.

### Step 1.4: Read Required Specs
BEFORE ANY CODE WORK, read every spec referenced in the taskcard's "Required spec references" section.

**Why**: Specs are binding. Implementation must follow spec contracts exactly.

**Example for TC-200**:
- specs/29_project_repo_structure.md
- specs/25_frameworks_and_dependencies.md
- specs/01_system_contract.md
- specs/10_determinism_and_caching.md

Take notes on:
- What schemas are required
- What contracts must be honored
- What determinism rules apply
- What I/O formats are binding

### Step 1.5: Follow Implementation Steps
Execute each step in the taskcard's "## Implementation steps" section sequentially.

**Golden rule**: Each step should be a discrete, testable unit. Do NOT combine steps.

**Example from TC-200**:
1. Create `src/launch/schemas/` package structure
2. Implement Pydantic models for `run_config.schema.json`
3. Implement JSON I/O helpers (load/dump with deterministic formatting)
4. Wire validators into `src/launch/io/schema_validation.py`
5. Add tests proving schema validation works
6. Document allowed exceptions (if any) per specs

### Step 1.6: Respect the Write Fence (allowed_paths)
Your taskcard's `allowed_paths` list defines the ONLY files you may create or modify.

**READ CAREFULLY**:
- `allowed_paths` = WRITE FENCE (modification/creation only)
- You may ALWAYS read and import from anywhere (reading is not modification)
- You may NOT modify files outside allowed_paths
- SHARED LIBRARIES (no write violations):
  - `src/launch/io/**` → TC-200 only
  - `src/launch/util/**` → TC-200 only
  - `src/launch/models/**` → TC-250 only
  - `src/launch/clients/**` → TC-500 only

**Example**: If TC-401 needs to import `src/launch/io/write_json()`:
- ✅ ALLOWED: `from src.launch.io import write_json`
- ❌ FORBIDDEN: Adding code to `src/launch/io/write_json()` (only TC-200 owns this)

**Validation**: Before committing, run:
```bash
python tools/validate_swarm_ready.py
```
Gate E will reject any shared-lib violations.

### Step 1.7: Write Tests (Not Optional)
For every feature implemented:
1. Create a test file under `tests/unit/<module>/` (or `tests/e2e/` for end-to-end)
2. Test the feature thoroughly (happy path + error cases)
3. Run tests: `python -m pytest tests/unit/<new_test>.py -v`
4. Ensure ALL tests pass before proceeding

**Test naming**: `test_tc_<taskcard_id>_<module>.py`  
**Example**: `test_tc_200_schema_validation.py`

### Step 1.8: Verify Determinism (If Applicable)
If your taskcard touches file I/O, JSON generation, or ordering:

1. Run the same operation twice (e.g., generate a JSON artifact)
2. Compare byte-for-byte: `diff -u run1.json run2.json`
3. They must be IDENTICAL (no timestamps, no random ordering)
4. Document this verification in your agent report

**Determinism checklist**:
- [ ] No `datetime.now()` in code (only when explicitly spec-allowed)
- [ ] No `random` module (only when explicitly spec-allowed)
- [ ] JSON keys sorted: `json.dumps(..., sort_keys=True)`
- [ ] Python imports sorted alphabetically
- [ ] Lists/dicts sorted by stable key before serialization

### Step 1.9: Document What You Did
Create agent report: `reports/agents/<your-name>/<taskcard-id>/report.md`

**Report structure** (use as template):
```markdown
# Agent Report: <TASKCARD_ID> - <Title>

**Agent**: <Your Name>  
**Date**: 2026-01-23  
**Task**: <Taskcard ID + Title>

## Summary
[1-2 sentence summary of what was implemented]

## Files Changed / Created
- `src/launch/schemas/__init__.py` (new)
- `src/launch/schemas/run_config.py` (new, 150 lines)
- `src/launch/io/schema_validation.py` (modified, +50 lines)
- `tests/unit/test_tc_200_schema_validation.py` (new, 120 lines)

## Commands Run (Copy/Paste)
```bash
python -m pytest tests/unit/test_tc_200_schema_validation.py -v
# Output:
# tests/unit/test_tc_200_schema_validation.py::test_run_config_valid ✓
# tests/unit/test_tc_200_schema_validation.py::test_run_config_invalid ✓
# 2 passed in 0.45s
```

## Spec Compliance Checklist
- [x] Implements all required schemas from `specs/01_system_contract.md`
- [x] Uses Pydantic per `specs/25_frameworks_and_dependencies.md`
- [x] JSON deterministically formatted per `specs/10_determinism_and_caching.md`
- [x] No `PIN_ME`, `TODO`, or `NotImplemented` in production code

## Determinism Verification
Run twice and verify identical output:
```bash
python -c "from src.launch.schemas import RunConfig; print(RunConfig.model_json_schema())" > run1.json
python -c "from src.launch.schemas import RunConfig; print(RunConfig.model_json_schema())" > run2.json
diff -u run1.json run2.json
# Output: (no differences)
```

## Known Issues / Blockers
[None. If you encounter ambiguity, write a blocker issue instead of guessing.]

## Self-Review Dimensions (See reports/templates/self_review_12d.md)
[Use the 12-dimension template. Every dimension must be 1-5. Any < 4 requires a concrete fix plan.]
```

### Step 1.10: Write Self-Review
Create: `reports/agents/<your-name>/<taskcard-id>/self_review.md`

Use template: `reports/templates/self_review_12d.md`

**12 dimensions** (each scored 1-5):
1. **Specification Compliance**: Does the implementation follow all binding specs?
2. **Taskcard Contract**: Are all acceptance checks satisfied?
3. **Determinism**: Are outputs byte-for-byte reproducible?
4. **Test Coverage**: Are all code paths tested?
5. **Error Handling**: Are exceptions caught and reported gracefully?
6. **Documentation**: Is the code clear and well-commented?
7. **Code Quality**: Is the code idiomatic, maintainable, and performant?
8. **Integration**: Does the code integrate cleanly with existing modules?
9. **Evidence**: Are all required artifacts present (report, tests, etc.)?
10. **Security**: Are there any obvious vulnerabilities or secrets in the code?
11. **Deterministic Verification**: Did you verify reproducibility (if applicable)?
12. **Blockers**: Are there any unresolved issues that block acceptance?

**Scoring**:
- 5: Fully met, no issues
- 4: Met with minor non-blocking issues (document them)
- 3: Partially met, has identifiable gaps (describe fix plan)
- 2: Significantly incomplete, major gaps (describe fix plan)
- 1: Not started or fundamentally broken (describe fix plan)

**Rule**: If ANY dimension is <4, you MUST include a concrete fix plan (not vague). If a dimension is truly 1-2, the task is not ready for acceptance.

### Step 1.11: Run Acceptance Checks
Go through each acceptance check in the taskcard:

```markdown
## Acceptance Checks (from TC-200)
- [ ] All Pydantic models validated against actual schema files
- [ ] JSON serialization is deterministic (keys sorted)
- [ ] Validation gates reject invalid inputs
- [ ] Agent report + self-review written
- [ ] All tests pass
```

For each check:
1. Read the check carefully
2. Verify it's satisfied
3. Document how (copy/paste test output, command run, etc.)
4. Check the box

If ANY check fails, fix it before proceeding.

### Step 1.12: Commit and Open PR
```bash
git add -A
git commit -m "feat(TC-200): Implement schemas and IO foundations

- Add Pydantic models for run_config, repo_inventory, product_facts
- Implement deterministic JSON I/O (sorted keys)
- Wire validation gates into schema_validation.py
- Add 15 unit tests proving validation behavior
- 100% determinism verified (byte-for-byte reproducible)

Fixes #TC-200
Evidence: reports/agents/<name>/TC-200/report.md"

git push origin feat/TC-200-schemas-and-io
```

Then open a PR on GitHub with:
- Title: `feat(TC-200): Implement schemas and IO foundations`
- Description: Link to your agent report + self-review
- Attach test output
- Include acceptance checklist (copy from taskcard)

### Step 1.13: Mark Taskcard Done
Once PR is merged, update the taskcard frontmatter:
```yaml
---
id: TC-200
status: Done           # ← Change from "In-Progress"
owner: "<your-name>"
updated: "2026-01-23"
---
```

Then regenerate status board:
```bash
python tools/generate_status_board.py
git commit -m "chore: TC-200 marked Done" && git push
```

---

## PHASE 2: HANDLING AMBIGUITIES (Stop and Escalate)

**If you encounter an ambiguous requirement**:

1. **DO NOT GUESS**. Guessing violates the taskcard contract.
2. **Write a blocker issue** in JSON format:

```bash
mkdir -p reports/agents/<your-name>/<taskcard-id>/blockers
# Create file with ISO timestamp: 20260123T143022_<slug>.issue.json
cat > reports/agents/<your-name>/<taskcard-id>/blockers/20260123T143022_clarify-schema-field.issue.json << 'EOF'
{
  "schema_version": "1.0",
  "issue_id": "BLK-TC-200-001",
  "severity": "BLOCKER",
  "component": "TC-200 (Schemas and IO)",
  "title": "Ambiguity: run_config.product.type field constraints",
  "description": "The taskcard requires ProductFacts extraction, but specs/03_product_facts_and_evidence.md does not specify constraints on the 'type' field. Should it be an enum (CLI|LIBRARY|SERVICE|...)? Or a free-form string with validation rules?",
  "affected_steps": [1, 2],
  "impact": "Cannot implement Pydantic model without knowing valid values and constraints",
  "repro_steps": [
    "Read specs/03_product_facts_and_evidence.md (no constraints on 'type' found)",
    "Check run_config.schema.json (only lists 'type' as string, no enum)",
    "Attempt to implement ProductFacts Pydantic model (cannot proceed)"
  ],
  "proposed_resolution": "Update specs/03_product_facts_and_evidence.md to explicitly define: 'The product.type field MUST be one of: {cli, library, service, plugin, other}' OR 'The product.type field is free-form but must match regex: ^[a-z_]+$'",
  "references": [
    "specs/03_product_facts_and_evidence.md (vague on 'type' constraints)",
    "TC-200 (Schemas and IO foundations)"
  ]
}
EOF
```

3. **Add note to your agent report**:
```markdown
## Blockers
- BLK-TC-200-001: Ambiguity on ProductFacts.type field constraints (filed in reports/agents/<name>/TC-200/blockers/20260123T143022_clarify-schema-field.issue.json)

**Status**: Awaiting spec clarification. Implementation of step 2 is blocked pending resolution.
```

4. **Pause that taskcard**. Switch to a different taskcard that doesn't have blockers.

5. **When spec is clarified**, resolve the issue in the JSON (update "status" field) and continue.

---

## PHASE 3: VALIDATION COMMANDS (Run Frequently)

### Before Every Commit
```bash
python tools/validate_swarm_ready.py
```
Ensures no shared-lib violations were introduced.

### After Modifying Tests
```bash
python -m pytest -q
```
Ensure all tests pass.

### After Modifying Code
```bash
python -m ruff check src/launch/
python -m ruff format src/launch/
```
Ensure code follows project style.

### Before Marking Taskcard Done
```bash
python -m pytest tests/unit/<your_test>.py -v
python tools/validate_taskcards.py
```
Ensure your implementation passes both functional and metadata validation.

---

## PHASE 4: ORCHESTRATOR HANDOFF (For agents implementing TC-300+)

Once core infrastructure (TC-100–TC-300) is done, orchestrator agents must:

1. **Verify all worker stubs exist** (W1-W9 as packages with `__main__.py`)
2. **Implement LangGraph state machine** per `specs/28_coordination_and_handoffs.md`
3. **Wire worker invocation** (orchestrator calls `python -m launch.workers.wX`)
4. **Implement event logging** per `specs/16_local_telemetry_api.md`
5. **Handle state transitions** and error propagation

See TC-300 taskcard for detailed steps.

---

## PHASE 5: FINAL ORCHESTRATOR REVIEW (After All Taskcards Done)

The Orchestrator (coordinator agent) must:

1. **Read all agent self-reviews** (39 of them)
2. **Verify no dimension < 4 without fix plan**
3. **Verify all acceptance checks satisfied**
4. **Run end-to-end dry run**: `python -m pytest tests/e2e/ -v`
5. **Run full validation**: `launch_validate --run_dir runs/<sample_run> --profile ci`
6. **Check for `PIN_ME`, `TODO`, `NotImplemented` in code**:
```bash
grep -r "PIN_ME\|TODO\|NotImplemented" src/launch/ --include="*.py" | grep -v "test_" | grep -v "__pycache__"
```
Should return 0 results.

7. **Publish orchestrator master review**:
```markdown
# Orchestrator Master Review

**Date**: 2026-01-25  
**Status**: [GO | NO-GO]

## Summary
[Overall assessment]

## Agent Scorecard
| Agent | Tasks | Status | Min Dimension |
|-------|-------|--------|---------------|
| Agent A | TC-100 | DONE | 5 |
| Agent B | TC-200, TC-201, TC-250 | DONE | 4 (with fix) |
| ... | ... | ... | ... |

## Go/No-Go Criteria
- [ ] All 39 taskcards marked Done
- [ ] All agent self-reviews written
- [ ] No dimension < 4 (or all < 4 have fix plans)
- [ ] All tests pass: `python -m pytest -q` (0 failures)
- [ ] E2E dry run passes: `launch_run --config configs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml`
- [ ] Full validation passes: `launch_validate --run_dir runs/<sample_run> --profile ci`
- [ ] No `PIN_ME`, `TODO`, `NotImplemented` in production code
- [ ] All determinism verifications documented

## Recommendations
[Any follow-up tasks for production, monitoring, etc.]

## FINAL VERDICT: 🟢 GO
```

---

## QUICK REFERENCE: Key Files to Know

| File | Purpose |
|------|---------|
| `plans/taskcards/STATUS_BOARD.md` | Your taskcard queue + status |
| `plans/taskcards/00_TASKCARD_CONTRACT.md` | Binding rules (read this first) |
| `plans/swarm_coordination_playbook.md` | Parallel execution rules |
| `DECISIONS.md` | All 7 architectural decisions |
| `specs/29_project_repo_structure.md` | Repo layout contract |
| `specs/01_system_contract.md` | Binding system guarantees |
| `specs/25_frameworks_and_dependencies.md` | Tech stack (LangGraph, Pydantic, etc.) |
| `specs/10_determinism_and_caching.md` | Reproducibility rules |
| `.github/workflows/ci.yml` | CI/testing pipeline |
| `Makefile` | Build targets |

---

## GLOSSARY (Key Terms)

- **Taskcard**: Implementation instruction covering one cohesive outcome. Binding contract.
- **Spec**: Architectural/system requirement. Binding reference.
- **Allowed paths**: Write fence. Files a taskcard may modify/create.
- **Blocker issue**: JSON artifact for unresolved ambiguities (file + stop, don't guess).
- **Self-review**: 12-dimension evaluation of your work (every dimension 1-5).
- **W1-W9**: Workers (worker processes in orchestration graph). W1=RepoScout, W2=FactsBuilder, ... W9=PRManager.
- **RUN_DIR**: Runtime working directory for a single launch run (under `runs/<run_id>/`).
- **Determinism**: Byte-for-byte reproducibility (no timestamps, no randomness).
- **Shared library**: Code module owned by specific taskcard (no write violations permitted).

---

## NO GUESS-WORK PLEDGE

By following this prompt, you pledge:

✅ I will read specs and taskcards completely before coding.  
✅ I will respect the write fence (allowed_paths).  
✅ I will write tests for every feature.  
✅ I will verify determinism (if applicable).  
✅ I will document everything (report + self-review).  
✅ I will escalate ambiguities as blockers (not guess-work).  
✅ I will follow the 12-dimension self-review template.  
✅ I will not modify files outside allowed_paths.  
✅ I will not touch shared libraries (unless I own them).  
✅ I will run validation gates before committing.  

**Result**: Systematic, consistent, thoroughly documented implementation.

---

## START HERE (Copy/Paste These Commands)

```bash
# 1. Activate .venv
source .venv/bin/activate

# 2. Validate readiness
python tools/validate_dotvenv_policy.py
python tools/validate_swarm_ready.py

# 3. Regenerate status board
python tools/generate_status_board.py

# 4. View taskcard queue (find Ready, unassigned tasks)
cat plans/taskcards/STATUS_BOARD.md | grep "Ready"

# 5. Pick a taskcard (example: TC-100)
less plans/taskcards/TC-100_bootstrap_repo.md

# 6. Create feature branch
git checkout -b feat/TC-100-bootstrap-repo

# 7. Follow taskcard steps (starting from Step 1.2)
```

---

## READY TO BEGIN IMPLEMENTATION

All prerequisites are met. All specs are complete. All tasks are planned.

**Pick a taskcard from STATUS_BOARD marked "Ready" and "unassigned", and follow Phase 1 (Implementation Workflow) step by step.**

No guessing. No improvisation. Just execute the plan.

🟢 **GO.**

---

**Document**: STRICT IMPLEMENTATION PROMPT FOR CLAUDE CODE  
**Version**: 1.0  
**Generated**: 2026-01-23  
**Status**: ACTIVE — Ready for agent deployment
