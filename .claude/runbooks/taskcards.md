# runbooks/taskcards.md (FOSS Launcher)

Use this **before** making changes to app core / production paths.

This is aligned to:
- `specs/30_ai_agent_governance.md` (required taskcard sections + frontmatter format)
- `specs/09_validation_gates.md` (Gate U naming + allowed_paths semantics)
- `specs/34_strict_compliance_guarantees.md` (version-lock fields)

## 1) Decide if a taskcard is required
Taskcard is REQUIRED if you will edit any of:
- `src/launch/**`
- `src/launch/validators/**`
- `src/launch/workers/w7_validator/**`
- `config/**`
- any gate/CI enforcement scripts if present

If you will only edit docs outside production paths, taskcard is optional (unless you choose to track work formally).

## 2) Create the taskcard file
Target path + naming:
- `plans/taskcards/TC-<id>_<slug>.md`

If `plans/taskcards/` does not exist, create it.

Start from template:
- `.claude/templates/taskcards/TC-000_template.md`

## 3) Fill frontmatter correctly (MUST)
- `status`: Draft / In-Progress / Done
- `updated`: quoted string `"YYYY-MM-DD"`
- `evidence_required`: list of repo-relative paths (NOT boolean)
- `allowed_paths`: list of glob patterns
  - MUST match the body section exactly
  - Keep minimal scope (least privilege)

Version locks (per specs/34):
- `spec_ref`: commit SHA (use `git rev-parse HEAD`)
- `ruleset_version`: `ruleset.v1`
- `templates_version`: `templates.v1`

## 4) Set status to In-Progress before core edits
Draft status is not authorized for writes (see `src/launch/util/taskcard_validation.py`).

## 5) Allowed paths guidance (Gate U semantics)
Examples:
- Exact file: `config/network_allowlist.yaml`
- Recursive: `src/launch/util/**`
- Patterned worker: `src/launch/workers/w7_validator/**`

All files you modify MUST match at least one pattern.

## 6) Completion

### Pre-Completion Validation Checklist

Before updating status from "In-Progress" to "Done", **YOU MUST** verify ALL of the following:

#### A. Acceptance Checks State
- [ ] Open taskcard file, locate `## Acceptance checks` section
- [ ] Verify every acceptance item is marked `[x]` or ✅ (not `[ ]`)
- [ ] Search for pending markers: `⏳`, `📋`, "Pending", "Deferred", "TODO"
  - Command: `grep -E "(⏳|📋|Pending|Deferred|TODO)" plans/taskcards/TC-XXX.md`
  - Result must be: **No matches** (exit code 1)
- [ ] If any item unchecked or pending: **CANNOT mark Done**

#### B. Evidence Files Existence
- [ ] Open taskcard frontmatter, locate `evidence_required:` list
- [ ] Verify every evidence file exists on disk:
  - Command: `ls -la reports/agents/agent_X/TC-XXX/evidence.md`
  - Result must be: File exists, size ≥100 bytes
- [ ] Verify no evidence file contains "Pending", "TODO", "Not executed":
  - Command: `grep -i "pending\|todo\|not executed" reports/agents/agent_X/TC-XXX/*.md`
  - Result must be: **No matches** (exit code 1)
- [ ] If any evidence missing or incomplete: **CANNOT mark Done**

#### C. E2E Verification Execution (Critical Workers Only)

If taskcard modifies W2, W4, W5, W5.5, or W7:

- [ ] Verify `## E2E verification` section contains:
  - Concrete pilot commands (not "Will run...", "Expected:")
  - Actual exit codes (not "Should be 0")
  - Real metrics (not "~2455 expected")
  - Run directory paths (not placeholders)
- [ ] Verify both pilots executed:
  - Command: `ls -la runs/tc-XXX-3d/validation_report.json runs/tc-XXX-note/validation_report.json`
  - Result must be: Both files exist
- [ ] Verify pilots passed:
  - Command: `jq '.status' runs/tc-XXX-{3d,note}/validation_report.json`
  - Result must be: "PASS" for both
- [ ] If pilots not executed or failed: **CANNOT mark Done**

#### D. Self-Review Complete
- [ ] Open `reports/agents/agent_X/TC-XXX/self_review.md`
- [ ] Verify all 12 dimensions scored (1-5)
- [ ] Verify no dimension <4 without fix plan
- [ ] Verify "Known Gaps" section exists (empty = "None" stated explicitly)
- [ ] If self-review incomplete: **CANNOT mark Done**

#### E. Automated Validation
- [ ] Run taskcard validator:
  ```bash
  python tools/validate_taskcards.py plans/taskcards/TC-XXX.md --check-evidence
  ```
- [ ] Verify exit code 0 (validation passed)
- [ ] If validation fails: **CANNOT mark Done**

### Valid Completion Example

```markdown
# Taskcard frontmatter
status: Done  ← ONLY AFTER all checks above verified
updated: "2026-02-12"

# Acceptance checks section
## Acceptance checks
- [x] All tests pass (3008/3008) - see reports/test_results.txt
- [x] Pilot 3D passed (claim count 2455→2485, exit 0) - see runs/tc-XXX-3d/
- [x] Pilot Note passed (claim count 6551→6571, exit 0) - see runs/tc-XXX-note/
- [x] W5.5 scores maintained (CQ≥5, TA≥5, U≥5) - see review_report.json
- [x] Self-review complete (12D, all ≥4) - see reports/agents/agent_X/TC-XXX/self_review.md
```

### Invalid Completion Example (VIOLATION)

```markdown
# Taskcard frontmatter
status: Done  ← VIOLATION: Acceptance criterion #2 is pending

# Acceptance checks section
## Acceptance checks
- [x] All tests pass (102/102)
- [ ] Pilot runs ⏳ PENDING (unit tests validate, deferred to TC-1408)  ← UNCHECKED + PENDING
- [x] Self-review complete (12D, all 5/5)
```

**Why this is invalid**:
1. Acceptance item #2 is unchecked `[ ]`
2. Contains pending marker `⏳ PENDING`
3. Contains deferral excuse "(deferred to TC-1408)"
4. Violates specs/30_ai_agent_governance.md §2.5

### Consequences of Invalid Completion

If you mark status="Done" with incomplete acceptance:

1. **Pre-push hook blocks**: `git push` will fail with validation error
2. **CI/CD blocks**: PR cannot merge until fixed
3. **Status rollback**: Taskcard will be reverted to "In-Progress"
4. **Accountability**: Violation logged with agent ID and timestamp
5. **Corrective action required**: Must complete acceptance criteria before re-marking Done

### Summary: "Completed" Means "Executed"

**"E2E verification section completed"** means:
- ✅ Pilot commands **EXECUTED** (not just documented)
- ✅ Results **CAPTURED** (exit codes, metrics, logs)
- ✅ Artifacts **COMMITTED** (run directories, reports)
- ❌ NOT "section exists with example commands"
- ❌ NOT "will run in TC-XXXX later"

**"Acceptance checks satisfied"** means:
- ✅ All items **CHECKED** `[x]`
- ✅ Evidence **EXISTS** and is complete
- ✅ Zero **PENDING** markers
- ❌ NOT "section exists and some items satisfied"
- ❌ NOT "unit tests prove it works"

When in doubt: **RUN THE PILOTS**. 6-7 minutes of verification prevents 8+ hours of debugging.
