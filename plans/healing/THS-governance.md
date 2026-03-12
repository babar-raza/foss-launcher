# tender-hugging-shamir — Governance Repair Plan

## Context

Self-review of `C:\Users\prora\.claude\plans\tender-hugging-shamir.md` identified
three governance violations. TC-4075–4078 were implemented under protected paths
(`src/launcher/**`, `configs/**`) without materialized `In-Progress` taskcard files
in `plans/taskcards/` — a direct AG-002 violation. TC-4070–4074 have implementations
on disk but acceptance checks are unchecked and statuses are still `In-Progress`.
The plan itself is still `Ready for approval` despite execution having proceeded.
None of these affect runtime correctness, but all three break the governance audit
trail that downstream reviewers depend on to trust the work.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-THS-01 | TC-4075, TC-4076, TC-4077, TC-4078 have no `plans/taskcards/` files — code was written to protected paths without In-Progress taskcards | Governance/Critical | THS-01 |
| G-THS-02 | TC-4070–4074 acceptance checks are all unchecked `[ ]` and status is `In-Progress` despite implementations existing on disk | Governance/High | THS-02 |
| G-THS-03 | Plan `tender-hugging-shamir.md` status is `Ready for approval` — never transitioned to an approved/executing state despite execution proceeding | Governance/Medium | THS-03 |

---

## THS-01 — Retroactive Taskcards for TC-4075–4078

### Status: Done

### Gap Linkage
- G-THS-01: TC-4075, TC-4076, TC-4077, TC-4078 implemented without taskcards

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
Create four retroactive taskcard files documenting the Scout phase
implementation. Each taskcard must describe what was actually implemented
(verified against disk), set status to `Done`, and list evidence that the
implementation is complete.

Taskcards to create:
1. `TC-4075_scout_worker_implementation.md` — ScoutWorker (`src/launcher/workers/scout/worker.py`, `__init__.py`)
2. `TC-4076_move_scout_update_understand.md` — scout.py relocation + UnderstandWorker input change
3. `TC-4077_pipeline_yaml_scout_step.md` — `configs/pipeline.yaml` scout step addition
4. `TC-4078_graph_builder_scout.md` — `src/launcher/orchestrator/graph_builder.py` ScoutWorker registration

Each taskcard must include:
- Accurate `allowed_paths` listing the actual files that were changed
- At least 5 acceptance checks verified against the current codebase
- `evidence_required` block pointing to `reports/TC-407x/evidence.md`
- Status: `Done` (retroactive — implementations verified)
- A `retroactive: true` field in frontmatter to mark it as post-hoc documentation

#### Allowed paths
```
plans/taskcards/TC-4075_scout_worker_implementation.md
plans/taskcards/TC-4076_move_scout_update_understand.md
plans/taskcards/TC-4077_pipeline_yaml_scout_step.md
plans/taskcards/TC-4078_graph_builder_scout.md
reports/TC-4075/evidence.md
reports/TC-4076/evidence.md
reports/TC-4077/evidence.md
reports/TC-4078/evidence.md
```

#### Forbidden
Any file under `src/`, `configs/`, `specs/`, `tests/`, or any other path.

### Acceptance Checks

#### CLI
```bash
# All 4 taskcard files exist
ls plans/taskcards/TC-4075*.md plans/taskcards/TC-4076*.md plans/taskcards/TC-4077*.md plans/taskcards/TC-4078*.md

# All are marked Done
grep "^status: Done" plans/taskcards/TC-4075*.md plans/taskcards/TC-4076*.md plans/taskcards/TC-4077*.md plans/taskcards/TC-4078*.md

# All have retroactive flag
grep "retroactive: true" plans/taskcards/TC-4075*.md plans/taskcards/TC-4076*.md plans/taskcards/TC-4077*.md plans/taskcards/TC-4078*.md

# Evidence files exist
ls reports/TC-4075/evidence.md reports/TC-4076/evidence.md reports/TC-4077/evidence.md reports/TC-4078/evidence.md
```

#### UI/Web/API
N/A — governance-only change.

#### Tests
No test changes required. The taskcards document work already tested.

#### Config respected end-to-end
The `allowed_paths` in each retroactive taskcard must list the files
that were actually modified — verified by cross-referencing with `git log`.

#### No mock data in production paths
N/A.

### Deliverables
- 4 taskcard files under `plans/taskcards/`
- 4 evidence files under `reports/TC-407x/evidence.md`, each containing:
  - What was implemented
  - How acceptance checks were verified (output of `ls`/`grep` commands)
  - Date completed

### Hard Rules
- Do NOT modify any source code, configs, or tests
- Retroactive taskcards must reflect what was actually implemented, not what was planned
- Status must be `Done`, not `In-Progress` or `Draft`
- No new deps

### Review Dimensions — what 5/5 means for THS-01

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | All 4 taskcards created, all acceptance checks verified, all evidence files written |
| Consistency | `allowed_paths` in each TC matches actual files on disk |
| Production grading | Audit trail complete: someone can trace every protected-path change to a taskcard |
| Systematic approach | One taskcard per original TC, evidence per TC, no orphan implementations |
| Correctness | Taskcard `allowed_paths` verified against `git log` for each file |
| Scope adherence | Only `plans/taskcards/` and `reports/` written |
| Maintainability | Future agents can audit: implementation → TC → evidence |
| Testability | Acceptance checks are CLI-verifiable (`ls`, `grep`) |
| Robustness | Each TC has a `retroactive: true` flag so it is never confused with a pre-work TC |
| Performance | N/A |
| Integration fit | Uses same taskcard frontmatter schema as all other TCs |
| Observability | Evidence files provide audit record |
| Minimality | 8 files, no unnecessary content |

### Now (Runbook)

```bash
# Step 1: Verify what was actually implemented
ls src/launcher/workers/scout/
grep "ScoutWorker\|ScoutBundle" src/launcher/orchestrator/graph_builder.py | head -10
grep "scout" configs/pipeline.yaml
grep "input_schema.*scout\|output_schema.*scout" src/launcher/workers/understand/worker.py 2>/dev/null | head -5

# Step 2: Create TC-4075 (ScoutWorker)
# Write plans/taskcards/TC-4075_scout_worker_implementation.md
# with allowed_paths: src/launcher/workers/scout/__init__.py, src/launcher/workers/scout/worker.py
# Status: Done, retroactive: true

# Step 3: Create TC-4076 (scout.py move + Understand update)
# Write plans/taskcards/TC-4076_move_scout_update_understand.md
# with allowed_paths: src/launcher/workers/scout/scout.py,
#   src/launcher/workers/understand/scout.py (shim),
#   src/launcher/workers/understand/worker.py

# Step 4: Create TC-4077 (pipeline.yaml)
# Write plans/taskcards/TC-4077_pipeline_yaml_scout_step.md
# with allowed_paths: configs/pipeline.yaml, specs/schemas/scout_bundle.schema.json

# Step 5: Create TC-4078 (graph builder)
# Write plans/taskcards/TC-4078_graph_builder_scout.md
# with allowed_paths: src/launcher/orchestrator/graph_builder.py

# Step 6: Create evidence files for each
mkdir -p reports/TC-4075 reports/TC-4076 reports/TC-4077 reports/TC-4078

# Step 7: Verify all 4 taskcards are Done
grep "^status:" plans/taskcards/TC-407[5-8]*.md
```

---

## THS-02 — Mark TC-4070–4074 Done and Produce Evidence

### Status: Done

### Gap Linkage
- G-THS-02: TC-4070–4074 acceptance checks unchecked, status still In-Progress

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
For each of TC-4070, TC-4071, TC-4072, TC-4073, TC-4074:
1. Run each acceptance check CLI command verbatim
2. Tick all `[ ]` boxes where the check passes (change to `[x]`)
3. Note any check that FAILS — do not tick it; open a new gap instead
4. Change status from `In-Progress` → `Done`
5. Create `reports/TC-407x/evidence.md` containing command outputs

Acceptance check verification commands per TC:

**TC-4070** (shared identity module):
```bash
grep -rn "_resolve_identity" src/ | wc -l          # expect 0
grep -rn "from launcher.shared.identity" src/launcher/workers/intake/worker.py | wc -l  # expect ≥1
grep -rn "from launcher.shared.identity" src/launcher/intake/config_generator.py | wc -l # expect ≥1
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_identity.py tests/unit/workers/test_intake.py -v 2>&1 | tail -20
```

**TC-4071** (remove python defaults):
```bash
grep "require_python.*=.*True" src/launcher/intake/repo_classifier.py  # expect no default True
grep "require_python.*=.*True" src/launcher/intake/config_loader.py    # expect no default True
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/ -v 2>&1 | tail -20
```

**TC-4072** (intake self_review hardening):
```bash
grep "python_shaped\|python-shaped\|_foss.*platform" src/launcher/workers/intake/worker.py | head -5
grep "detected_manifest_files\|inferred_language" src/launcher/workers/intake/worker.py | head -5
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v -k "self_review or repo_signals" 2>&1 | tail -20
```

**TC-4073** (force_rescan):
```bash
grep "force_rescan" src/launcher/intake/org_scanner.py | head -5
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/test_org_scanner.py -v 2>&1 | tail -20
```

**TC-4074** (ScoutBundle model):
```bash
python -c "from launcher.models.scout import ScoutBundle; print('OK')"
grep "budget_log\|budget_log_overflow_count" src/launcher/models/scout.py | head -5
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ -v 2>&1 | tail -20
```

#### Allowed paths
```
plans/taskcards/TC-4070_shared_identity_module.md
plans/taskcards/TC-4071_remove_python_defaults.md
plans/taskcards/TC-4072_intake_self_review_hardening.md
plans/taskcards/TC-4073_force_rescan_org_scanner.md
plans/taskcards/TC-4074_scout_bundle_model.md
reports/TC-4070/evidence.md
reports/TC-4071/evidence.md
reports/TC-4072/evidence.md
reports/TC-4073/evidence.md
reports/TC-4074/evidence.md
```

#### Forbidden
Any file under `src/`, `configs/`, `specs/`, `tests/`, or any other path.

### Acceptance Checks

#### CLI
```bash
# All 5 taskcards are Done
grep "^status:" plans/taskcards/TC-4070*.md plans/taskcards/TC-4071*.md \
  plans/taskcards/TC-4072*.md plans/taskcards/TC-4073*.md plans/taskcards/TC-4074*.md
# Expected: all show "status: Done"

# No unchecked boxes remain
grep "\- \[ \]" plans/taskcards/TC-4070*.md plans/taskcards/TC-4071*.md \
  plans/taskcards/TC-4072*.md plans/taskcards/TC-4073*.md plans/taskcards/TC-4074*.md
# Expected: 0 results (all boxes ticked or explicitly marked N/A)

# Evidence files exist and are non-empty
for tc in 4070 4071 4072 4073 4074; do
  wc -l reports/TC-$tc/evidence.md
done
```

#### UI/Web/API
N/A.

#### Tests
No new tests. The existing test suite must already pass for these TCs
to be marked Done.

#### Config respected end-to-end
Each evidence file must include actual test output (PASSED/FAILED lines),
not assumed results.

#### No mock data in production paths
N/A.

### Deliverables
- 5 updated taskcard files with `status: Done` and all `[x]` boxes
- 5 evidence files under `reports/TC-407x/evidence.md`

### Hard Rules
- Do NOT tick a check that fails — open a new gap taskcard instead
- Evidence files must contain real command outputs, not expected outputs
- No source code changes

### Review Dimensions — what 5/5 means for THS-02

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | All 5 TCs updated, all acceptance checks verified with real output |
| Consistency | Evidence matches actual state of code on disk |
| Production grading | Audit trail is verifiable: anyone can re-run the CLI commands |
| Systematic approach | One evidence file per TC, commands run verbatim |
| Correctness | Only passing checks ticked; failing checks become new gaps |
| Scope adherence | Only taskcard and reports files modified |
| Maintainability | Evidence format is human-readable and reproducible |
| Testability | All checks are CLI commands — reproducible by any reviewer |
| Robustness | Failing checks not silently ticked — they become new gaps |
| Performance | N/A |
| Integration fit | Same evidence file convention as other Done TCs |
| Observability | Evidence files act as audit log |
| Minimality | 10 files (5 TC updates + 5 evidence files), nothing else |

### Now (Runbook)

```bash
# Run verification commands per TC (see Scope above)
# For each TC: if command output shows the code is in place → tick the box
# If a command fails → DO NOT tick; log the failure in a new gap

# Example for TC-4070:
grep -rn "_resolve_identity" src/
# If 0 results: tick "grep -r "_resolve_identity" src/ returns 0 results"
# If ≥1 results: do NOT tick — open new gap G-THS-02a

# After all checks:
# Edit each TC file: change "status: In-Progress" → "status: Done"
# Change "- [ ]" → "- [x]" for each verified check
# Create reports/TC-407x/evidence.md with command output

# Final verification:
grep "^status:" plans/taskcards/TC-407{0,1,2,3,4}*.md
```

---

## THS-03 — Update Plan Status

### Status: Done

### Gap Linkage
- G-THS-03: Plan status "Ready for approval" stale

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
Update `tender-hugging-shamir.md` header from:
```
**Status**: Ready for approval
```
to:
```
**Status**: Executing — Phase 1 (TC-4070–4074) pending Done mark; Phase 2 TC-4075–4078 retroactive taskcards pending; Phase 3–4 Done
```

Add an execution log section at the bottom of the plan:
```markdown
## Execution Log

| Date | Event |
|------|-------|
| 2026-03-11 | Plan created, status set Ready for approval |
| 2026-03-11 | Phases 3–4 (TC-4079–4087) executed and marked Done |
| 2026-03-11 | Phase 2 Scout worker implemented (TC-4075–4078, retroactive taskcards pending — G-THS-01) |
| 2026-03-11 | Phase 1 implementations exist but TCs not marked Done (G-THS-02) |
| TBD | THS-01 (retroactive TCs) complete |
| TBD | THS-02 (mark TC-4070–4074 Done) complete |
| TBD | Full plan marked Complete |
```

#### Allowed paths
```
C:\Users\prora\.claude\plans\tender-hugging-shamir.md
```

#### Forbidden
Any file under `src/`, `configs/`, `specs/`, `tests/`, or `plans/taskcards/`.

### Acceptance Checks

#### CLI
```bash
grep "^\\*\\*Status\\*\\*" "C:\Users\prora\.claude\plans\tender-hugging-shamir.md"
# Expected: "**Status**: Executing — ..."

grep "Execution Log" "C:\Users\prora\.claude\plans\tender-hugging-shamir.md"
# Expected: 1 match
```

#### UI/Web/API
N/A.

#### Tests
N/A.

#### Config respected end-to-end
N/A.

#### No mock data in production paths
N/A.

### Deliverables
- Updated `tender-hugging-shamir.md` with current status and execution log

### Hard Rules
- Do not change any implementation sections of the plan
- Only the Status header and the new Execution Log section are modified

### Review Dimensions — what 5/5 means for THS-03

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Status line updated, execution log lists all known events |
| Consistency | Status accurately reflects current execution state |
| Production grading | Anyone reading the plan knows what phase it is in |
| Systematic approach | Execution log is chronological and fact-based |
| Correctness | Status does not claim Complete until THS-01 and THS-02 are Done |
| Scope adherence | One file changed |
| Maintainability | Execution log is append-only — future entries just added at bottom |
| Testability | Grep-verifiable |
| Robustness | Status is explicit about what is pending |
| Performance | N/A |
| Integration fit | Same plan file format as other plans in `C:\Users\prora\.claude\plans\` |
| Observability | Execution log provides audit history |
| Minimality | Minimal change — only status + log section |

### Now (Runbook)

```bash
# 1. Open the plan file
# 2. Change **Status** line
# 3. Add Execution Log section at bottom
# 4. Verify
grep "^\*\*Status\*\*" "C:\Users\prora\.claude\plans\tender-hugging-shamir.md"
```
