# Taskcard Validation Prevention System

**Created:** 2026-02-03
**Source:** Chat-derived (user prevention plan + assistant gap analysis)
**Status:** Ready for execution
**Estimated Effort:** 6-8 hours

---

## Context

TC-935 and TC-936 were merged without complete taskcard sections (missing "Failure modes" and "Task-specific review checklist"). This occurred because the validator only checks 4 sections, not all 14 mandatory sections defined in `plans/taskcards/00_TASKCARD_CONTRACT.md`.

**Current State (Verified 2026-02-03):**
- ✅ TC-935 and TC-936 NOW PASS validation (fixed by TC-937)
- ❌ Validator incomplete: Only checks 4/14 mandatory sections
- ❌ No pre-commit hook for local enforcement
- ❌ No developer tools (creation script, complete template)

**Root Cause:** Validator incompleteness allowed incomplete taskcards to pass CI/CD

---

## Goals

### Primary Goal
Prevent incomplete taskcards from being merged to main by implementing 4-layer defense-in-depth system.

### Success Criteria (Immediate)
1. Enhanced validator checks all 14 mandatory sections
2. Pre-commit hook blocks incomplete taskcards locally
3. CI continues to validate (with improved coverage)

### Success Criteria (3 months post-rollout)
1. Zero incomplete taskcards merged to main
2. Pre-commit prevention rate >95%
3. Mean validation time <5 seconds
4. Developer feedback positive

---

## Assumptions

### VERIFIED Assumptions ✅
- TC-935 and TC-936 now have complete sections (verified via file read)
- Current validator exists at `tools/validate_taskcards.py` (verified)
- Contract defines 14 mandatory sections in `00_TASKCARD_CONTRACT.md` (verified)
- 82 taskcards currently exist, 76 pass validation (verified via validator run)
- Pre-commit hook does NOT exist (verified via `hooks/` directory check)

### UNVERIFIED Assumptions ⚠️
- All 76 passing taskcards have all 14 sections (NOT verified - validator doesn't check all)
- Enhanced validator won't break existing taskcards (needs testing)
- Pre-commit hook execution time will be <5 seconds (needs measurement)

---

## Implementation Steps

### Layer 1: Enhanced Validator (HIGH PRIORITY)
**Owner:** Agent B (Implementation)
**Estimated Time:** 2 hours

#### Step 1.1: Add MANDATORY_BODY_SECTIONS constant
**File:** `tools/validate_taskcards.py`
**Location:** After line 228 (after VAGUE_E2E_PHRASES definition)

```python
# Mandatory body sections per 00_TASKCARD_CONTRACT.md (TC-PREVENT-INCOMPLETE)
MANDATORY_BODY_SECTIONS = [
    "Objective",
    "Required spec references",
    "Scope",  # Will check for "### In scope" and "### Out of scope" subsections
    "Inputs",
    "Outputs",
    "Allowed paths",
    "Implementation steps",
    "Failure modes",  # Must have >= 3 failure modes with detection/resolution/spec
    "Task-specific review checklist",  # Must have >= 6 task-specific items
    "Deliverables",
    "Acceptance checks",
    "Self-review",
    "E2E verification",  # Already validated by existing function
    "Integration boundary proven",  # Already validated by existing function
]
```

#### Step 1.2: Add validate_mandatory_sections() function
**File:** `tools/validate_taskcards.py`
**Location:** After validate_integration_boundary_section() function (after line 228)

```python
def validate_mandatory_sections(body: str) -> List[str]:
    """
    Validate all mandatory sections exist per 00_TASKCARD_CONTRACT.md.
    Returns list of error messages (empty if valid).

    TC-PREVENT-INCOMPLETE: Ensures taskcards have all 14 required sections.
    """
    errors = []

    for section in MANDATORY_BODY_SECTIONS:
        # Skip sections already validated by dedicated functions
        if section in ["E2E verification", "Integration boundary proven"]:
            continue

        pattern = rf"^## {re.escape(section)}\n"
        if not re.search(pattern, body, re.MULTILINE):
            errors.append(f"Missing required section: '## {section}'")

    # Check for subsections in "## Scope"
    if "## Scope" in body:
        if "### In scope" not in body:
            errors.append("'## Scope' section must have '### In scope' subsection")
        if "### Out of scope" not in body:
            errors.append("'## Scope' section must have '### Out of scope' subsection")

    # Check minimum items in failure modes
    failure_modes_match = re.search(r"^## Failure modes\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    if failure_modes_match:
        failure_modes_content = failure_modes_match.group(1)
        # Count ### headers (each failure mode should be a subsection)
        failure_mode_count = len(re.findall(r"^### ", failure_modes_content, re.MULTILINE))
        if failure_mode_count < 3:
            errors.append(f"'## Failure modes' must have at least 3 failure modes (found {failure_mode_count})")

    # Check minimum items in task-specific review checklist
    checklist_match = re.search(r"^## Task-specific review checklist\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    if checklist_match:
        checklist_content = checklist_match.group(1)
        # Count numbered or bulleted items
        checklist_items = len(re.findall(r"^[\d\-\*]\.", checklist_content, re.MULTILINE))
        if checklist_items < 6:
            errors.append(f"'## Task-specific review checklist' must have at least 6 items (found {checklist_items})")

    return errors
```

#### Step 1.3: Update validate_taskcard_file() to call new validator
**File:** `tools/validate_taskcards.py`
**Location:** In validate_taskcard_file() function (around line 410)

```python
def validate_taskcard_file(filepath: Path) -> Tuple[bool, List[str]]:
    """
    Validate a single taskcard file.
    Returns (is_valid, list_of_errors)
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    # Extract frontmatter and body
    frontmatter, body, error = extract_frontmatter(content)
    if error:
        return False, [error]

    # Validate frontmatter
    errors = validate_frontmatter(frontmatter, filepath)

    # Validate body allowed paths match frontmatter
    body_errors = validate_body_allowed_paths_match(frontmatter, body)
    errors.extend(body_errors)

    # TC-PREVENT-INCOMPLETE: Validate all mandatory sections exist
    section_errors = validate_mandatory_sections(body)
    errors.extend(section_errors)

    # Validate E2E verification section exists and is concrete
    e2e_errors = validate_e2e_verification_section(body)
    errors.extend(e2e_errors)

    # Validate integration boundary section exists
    int_errors = validate_integration_boundary_section(body)
    errors.extend(int_errors)

    return len(errors) == 0, errors
```

#### Step 1.4: Add --staged-only mode for pre-commit hook
**File:** `tools/validate_taskcards.py`
**Location:** In main() function, add argument parsing

```python
import argparse

def main():
    """Main validation routine."""
    parser = argparse.ArgumentParser(description="Validate taskcard files")
    parser.add_argument(
        "--staged-only",
        action="store_true",
        help="Only validate staged taskcard files (for pre-commit hook)"
    )
    args = parser.parse_args()

    # Determine repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"Validating taskcards in: {repo_root}")
    print()

    # Find taskcards to validate
    if args.staged_only:
        # Get staged taskcard files from git
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        staged_files = result.stdout.strip().split('\n')
        taskcards = [
            repo_root / f for f in staged_files
            if f.startswith("plans/taskcards/TC-") and f.endswith(".md")
        ]
        print(f"Found {len(taskcards)} staged taskcard(s) to validate")
    else:
        # Find all taskcards
        taskcards = find_taskcards(repo_root)
        print(f"Found {len(taskcards)} taskcard(s) to validate")

    if not taskcards:
        print("No taskcards to validate")
        return 0

    print()

    # ... rest of validation logic unchanged ...
```

#### Step 1.5: Test enhanced validator
**Commands:**
```bash
# Test against all taskcards
.venv\Scripts\python.exe tools\validate_taskcards.py

# Expected: May fail on some existing taskcards if they're missing sections
# This is EXPECTED and shows the validator is working correctly
```

**Acceptance:**
- Validator runs without crashes
- Reports missing sections for any incomplete taskcards
- TC-935 and TC-936 PASS (they're now complete)

---

### Layer 2: Pre-Commit Hook (HIGH PRIORITY)
**Owner:** Agent B (Implementation)
**Estimated Time:** 1 hour

#### Step 2.1: Create hooks/pre-commit script
**File:** `hooks/pre-commit` (NEW)

```bash
#!/usr/bin/env bash
# Pre-commit hook for taskcard validation
# TC-PREVENT-INCOMPLETE: Enforce complete taskcards before commit
set -e

# Only check staged taskcards
STAGED_TASKCARDS=$(git diff --cached --name-only --diff-filter=ACM | grep "^plans/taskcards/TC-.*\.md$" || true)

if [ -z "$STAGED_TASKCARDS" ]; then
    # No taskcards staged, skip validation
    exit 0
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 TASKCARD VALIDATION (Pre-Commit)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Validating staged taskcards..."
echo ""

# Run validator with --staged-only flag
if python tools/validate_taskcards.py --staged-only; then
    echo ""
    echo "✅ Taskcard validation PASSED"
    echo ""
    exit 0
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⛔ TASKCARD VALIDATION FAILED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Fix format errors above before committing."
    echo ""
    echo "See: plans/taskcards/00_TASKCARD_CONTRACT.md"
    echo ""
    echo "TO BYPASS (not recommended):"
    echo "  git commit --no-verify"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    exit 1
fi
```

#### Step 2.2: Update scripts/install_hooks.py
**File:** `scripts/install_hooks.py`
**Location:** Add pre-commit to hooks list

```python
# Add to HOOKS list
HOOKS = [
    'pre-commit',  # TC-PREVENT-INCOMPLETE: Taskcard validation
    'pre-push',
    'prepare-commit-msg',
]
```

#### Step 2.3: Test pre-commit hook
**Commands:**
```bash
# Install hooks
.venv\Scripts\python.exe scripts\install_hooks.py

# Create test incomplete taskcard
echo "---
id: TC-999
title: Test
status: Draft
owner: test
updated: 2026-02-03
depends_on: []
allowed_paths: [\"test\"]
evidence_required: [\"test\"]
spec_ref: abc123
ruleset_version: ruleset.v1
templates_version: templates.v1
---
## Objective
Test" > plans\taskcards\TC-999_test.md

# Try to commit (should block)
git add plans\taskcards\TC-999_test.md
git commit -m "test: incomplete taskcard"
# Expected: Hook blocks with validation errors

# Clean up
git reset HEAD plans\taskcards\TC-999_test.md
rm plans\taskcards\TC-999_test.md
```

**Acceptance:**
- Hook blocks commit with clear error message
- Hook lists missing sections
- Hook execution time <5 seconds

---

### Layer 3: Developer Tools (MEDIUM PRIORITY)
**Owner:** Agent B (Implementation)
**Estimated Time:** 2 hours

#### Step 3.1: Create complete template
**File:** `plans/taskcards/00_TEMPLATE.md` (NEW)

Template should include:
- Complete YAML frontmatter with all required fields
- All 14 mandatory sections with guidance comments
- Examples for each section
- Checklist format for review sections

**Content:**
```markdown
---
id: TC-XXX
title: "[Brief title describing the taskcard]"
status: Draft
priority: Normal
owner: "[agent or team name]"
updated: "YYYY-MM-DD"
tags: ["tag1", "tag2"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-XXX_[slug].md
  # Add specific paths you will modify
evidence_required:
  - runs/[run_id]/evidence.zip
  - reports/agents/<agent>/TC-XXX/report.md
spec_ref: "[git rev-parse HEAD]"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-XXX — [Title]

## Objective
[1-2 sentence statement of what this taskcard achieves. Be specific.]

## Problem Statement
[Optional: Describe the problem being solved, current state, pain points]

## Required spec references
[List specs that justify this work with section numbers:]
- specs/XX_[name].md (Section Y: [what it defines])
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard format)

## Scope

### In scope
[Bulleted list of what WILL be done in this taskcard]
- Item 1
- Item 2

### Out of scope
[Bulleted list of what will NOT be done, to avoid scope creep]
- Item 1
- Item 2

## Inputs
[What does this taskcard consume/require?]
- File/data/configuration X
- Output from TC-YYY
- User input Z

## Outputs
[What artifacts/files/data does this taskcard produce?]
- File/artifact A
- Modified file B
- Evidence bundle C

## Allowed paths
[Mirror the frontmatter allowed_paths list EXACTLY]
- plans/taskcards/TC-XXX_[slug].md
- [other paths]

### Allowed paths rationale
[Optional: Explain why these paths are needed]

## Implementation steps

### Step 1: [First step name]
[Detailed instructions with commands, code snippets, expected outputs]

```bash
# Example command
command --arg value
```

### Step 2: [Second step name]
[Continue with numbered steps]

## Failure modes

### Failure mode 1: [Name of failure scenario]
**Detection:** [How to detect this failure - command, log message, error code]
**Resolution:** [Step-by-step fix procedure]
**Spec/Gate:** [Which spec or gate this relates to]

### Failure mode 2: [Name of failure scenario]
[Minimum 3 failure modes required]

### Failure mode 3: [Name of failure scenario]
[Include failure modes for: validation failures, missing dependencies, edge cases]

## Task-specific review checklist
[Minimum 6 task-specific items beyond standard acceptance checks]
1. [ ] Item 1 specific to this task
2. [ ] Item 2 specific to this task
3. [ ] Item 3 specific to this task
4. [ ] Item 4 specific to this task
5. [ ] Item 5 specific to this task
6. [ ] Item 6 specific to this task

## Deliverables
[List of concrete outputs required for task completion]
- File/artifact A at path X
- Report at reports/agents/<agent>/TC-XXX/report.md
- Evidence bundle with validation outputs
- Updated documentation in specs/ or docs/

## Acceptance checks
[Measurable criteria that must ALL be true for task to be considered done]
1. [ ] Criterion 1 (e.g., tests pass)
2. [ ] Criterion 2 (e.g., validator passes)
3. [ ] Criterion 3 (e.g., specific file exists with expected content)

## Preconditions / dependencies
[Optional: What must be true before starting this taskcard]
- TC-YYY must be complete
- Environment Z must be set up
- File A must exist

## Test plan
[Optional: How to test this implementation]
1. Test case 1: [description and expected result]
2. Test case 2: [description and expected result]

## Self-review

### 12D Checklist
[Review across 12 dimensions - see reports/templates/self_review_12d.md]

1. **Determinism:** [How is determinism ensured?]
2. **Dependencies:** [What dependencies were added/changed?]
3. **Documentation:** [What docs were updated?]
4. **Data preservation:** [How is data integrity maintained?]
5. **Deliberate design:** [What design decisions were made and why?]
6. **Detection:** [How are errors/issues detected?]
7. **Diagnostics:** [What logging/observability added?]
8. **Defensive coding:** [What validation/error handling added?]
9. **Direct testing:** [What tests verify this works?]
10. **Deployment safety:** [How is safe rollout ensured?]
11. **Delta tracking:** [What changed and how is it tracked?]
12. **Downstream impact:** [What systems/users are affected?]

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: Gate Y PASS
- [ ] Evidence captured: [location]

## E2E verification
[Concrete command(s) to verify end-to-end functionality]

```bash
# Run the complete workflow
.venv\Scripts\python.exe [script] [args]
```

**Expected artifacts:**
- **[file path]** - [what it should contain]
- **[file path]** - [what it should contain]

**Expected results:**
- [Measurable outcome 1]
- [Measurable outcome 2]

## Integration boundary proven
**Upstream:** [What component/system provides input to this work?]

**Downstream:** [What component/system consumes output from this work?]

**Contract:** [What interface/API/data format is guaranteed between them?]

## Evidence Location
`runs/[run_id]/[evidence_files]`
```

#### Step 3.2: Create taskcard creation script
**File:** `scripts/create_taskcard.py` (NEW)

Script should:
- Prompt for TC number, title, owner
- Generate YAML frontmatter with current date, git SHA
- Copy template with substitutions
- Validate created taskcard
- Offer to open in editor

**Commands:**
```bash
# Test creation script
.venv\Scripts\python.exe scripts\create_taskcard.py

# Should prompt for:
# - TC number (e.g., 950)
# - Title
# - Owner
# - Tags
# Then create plans/taskcards/TC-950_[slug].md
```

**Acceptance:**
- Script creates valid taskcard file
- Created taskcard passes validator
- File opened in default editor

---

### Layer 4: Documentation (LOW PRIORITY)
**Owner:** Agent D (Docs & Specs)
**Estimated Time:** 1 hour

#### Step 4.1: Update AI Governance spec
**File:** `specs/30_ai_agent_governance.md`
**Location:** After AG-001, renumber existing AG-002 to AG-003

**Content:**
```markdown
### 3.2 Taskcard Completeness Gate

**Rule ID**: `AG-002`
**Severity**: BLOCKER

**Rule Statement**:
> AI agents MUST NOT commit taskcard files that are missing required sections per `plans/taskcards/00_TASKCARD_CONTRACT.md`.

**Rationale**:
- Incomplete taskcards create ambiguity for implementation agents
- Missing sections (Failure modes, Review checklists) reduce quality
- Prevention system ensures all 14 mandatory sections exist

**Enforcement**:
1. **Pre-commit Hook**: `hooks/pre-commit` validates staged taskcards
2. **CI Validation**: `tools/validate_taskcards.py` runs in CI
3. **Developer Tools**: Templates and creation scripts prevent omissions

**Required Sections** (14 total):
1. Objective
2. Required spec references
3. Scope (In scope / Out of scope)
4. Inputs
5. Outputs
6. Allowed paths
7. Implementation steps
8. Failure modes (minimum 3)
9. Task-specific review checklist (minimum 6 items)
10. Deliverables
11. Acceptance checks
12. Self-review
13. E2E verification
14. Integration boundary proven

**Bypass**:
- `git commit --no-verify` (not recommended)
- Only use for emergency fixes documented in commit message
```

#### Step 4.2: Create quickstart guide
**File:** `docs/creating_taskcards.md` (NEW or UPDATE existing)

Guide should cover:
- Using the template
- Using the creation script
- Running validator locally
- Common validation errors and fixes
- Best practices

---

## Verification Plan

### V1: Enhanced Validator Catches Missing Sections
**Command:**
```bash
# After implementing enhanced validator
.venv\Scripts\python.exe tools\validate_taskcards.py
```

**Expected Output:**
- All 82 taskcards validated
- TC-935 and TC-936 PASS (they're now complete)
- If any taskcards fail, they should show specific missing sections

**If taskcards fail:**
- Document which taskcards are incomplete (this is discovery, not a blocker)
- These can be fixed separately or grandfathered if status is "Done"

### V2: Test Against Intentionally Incomplete Taskcard
**Command:**
```bash
# Create incomplete test taskcard
cat > plans\taskcards\TC-999_test.md <<'EOF'
---
id: TC-999
title: "Test"
status: Draft
owner: "test"
updated: "2026-02-03"
depends_on: []
allowed_paths: ["test"]
evidence_required: ["test"]
spec_ref: "abc123"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---
## Objective
Test taskcard
EOF

# Run validator
.venv\Scripts\python.exe tools\validate_taskcards.py

# Clean up
rm plans\taskcards\TC-999_test.md
```

**Expected Output:**
- Validator reports multiple "Missing required section" errors
- Should report missing: Required spec references, Scope, Inputs, Outputs, etc.

### V3: Pre-Commit Hook Blocks Invalid Commits
**Command:**
```bash
# Install hooks
.venv\Scripts\python.exe scripts\install_hooks.py

# Create incomplete taskcard
echo "# TC-999" > plans\taskcards\TC-999_test.md

# Try to commit
git add plans\taskcards\TC-999_test.md
git commit -m "test: incomplete taskcard"

# Clean up
git reset HEAD plans\taskcards\TC-999_test.md
rm plans\taskcards\TC-999_test.md
```

**Expected Output:**
- Hook blocks commit with validation errors
- Error message shows missing sections
- Execution time <5 seconds

---

## Risks and Rollback

### Risk 1: Enhanced Validator Breaks Existing Taskcards
**Likelihood:** Low (76/82 taskcards currently pass)
**Impact:** High (could block all taskcard commits)

**Mitigation:**
- Test against all 82 taskcards before committing
- If failures found, decide: fix taskcards or grandfather them
- Grandfathering option: Skip validation for taskcards with status="Done"

**Rollback:**
- Revert changes to `tools/validate_taskcards.py`
- Remove enhanced validation function calls

### Risk 2: Pre-Commit Hook Too Slow
**Likelihood:** Low (validator runs in ~2 seconds on 82 taskcards)
**Impact:** Medium (developer friction)

**Mitigation:**
- `--staged-only` mode only validates changed taskcards
- Target <5 seconds for single taskcard validation
- Provide `git commit --no-verify` bypass option

**Rollback:**
- Remove hook: `rm .git/hooks/pre-commit`
- Uninstall via `scripts/install_hooks.py --uninstall` (if implemented)

### Risk 3: Developers Bypass Hooks
**Likelihood:** Medium (always possible with --no-verify)
**Impact:** Medium (incomplete taskcards could still be committed)

**Mitigation:**
- CI always validates (final safety net)
- Document hook purpose in AI governance spec
- Make `scripts/install_hooks.py` run automatically in setup

**Rollback:**
- N/A (CI validation always active)

---

## Open Questions

### Q1: Should we grandfather existing "Done" taskcards?
**Investigation Steps:**
1. Run enhanced validator on all taskcards
2. Identify which "Done" taskcards fail
3. Decide: fix them or skip validation for status="Done"

**Decision Point:** After V1 verification
**Stakeholder:** Project lead

### Q2: Should validation time budget be configurable?
**Investigation Steps:**
1. Measure validator execution time for 1, 10, 82 taskcards
2. Determine if timeout/budget needed

**Decision Point:** After V1 verification
**Default:** No timeout (but measure and document)

---

## Evidence Commands

### Validation Commands
```bash
# Full validator run (all taskcards)
.venv\Scripts\python.exe tools\validate_taskcards.py

# Staged-only mode (for pre-commit hook)
.venv\Scripts\python.exe tools\validate_taskcards.py --staged-only

# Test creation script
.venv\Scripts\python.exe scripts\create_taskcard.py
```

### Hook Commands
```bash
# Install hooks
.venv\Scripts\python.exe scripts\install_hooks.py

# Test pre-commit hook
git add plans\taskcards\TC-XXX_*.md
git commit -m "test"
# Should run validation automatically

# Bypass hook (emergency only)
git commit --no-verify -m "emergency fix"
```

### CI/CD Commands
```bash
# Validate swarm readiness (includes taskcard validation)
.venv\Scripts\python.exe tools\validate_swarm_ready.py

# Run full test suite
.venv\Scripts\python.exe -m pytest
```

---

## Success Metrics

### Immediate (Post-Implementation)
- ✅ Enhanced validator checks all 14 mandatory sections
- ✅ Pre-commit hook blocks incomplete taskcards
- ✅ Validation time <5 seconds per taskcard
- ✅ V1, V2, V3 verification tests pass

### Short-Term (1 month)
- Zero incomplete taskcards merged to main
- >95% of prevention happens at pre-commit (not CI)
- Developer feedback: "helpful" or "neutral" (not "annoying")

### Long-Term (3 months)
- Zero incomplete taskcards in repository
- Mean pre-commit validation time <3 seconds
- No false positives reported
- Template/script usage >50% for new taskcards

---

## File Modifications Summary

### Files to Modify
1. `tools/validate_taskcards.py` (~150 lines added)
   - Add MANDATORY_BODY_SECTIONS
   - Add validate_mandatory_sections()
   - Update validate_taskcard_file()
   - Add --staged-only argument parsing

2. `scripts/install_hooks.py` (~5 lines)
   - Add 'pre-commit' to HOOKS list

3. `specs/30_ai_agent_governance.md` (~30 lines)
   - Add AG-002 gate
   - Renumber existing gates

### Files to Create
1. `hooks/pre-commit` (~40 lines bash)
   - Validate staged taskcards
   - Block commits on validation failure

2. `plans/taskcards/00_TEMPLATE.md` (~250 lines)
   - Complete template with all 14 sections
   - Guidance comments and examples

3. `scripts/create_taskcard.py` (~100 lines Python)
   - Interactive taskcard creation
   - Validation and editor integration

4. `docs/creating_taskcards.md` (~100 lines) [Optional]
   - Quickstart guide
   - Best practices

---

## Acceptance Criteria

### Layer 1: Enhanced Validator
- [ ] MANDATORY_BODY_SECTIONS defined (14 sections)
- [ ] validate_mandatory_sections() implemented
- [ ] Scope subsections validated (In scope / Out of scope)
- [ ] Failure modes count validated (minimum 3)
- [ ] Review checklist count validated (minimum 6)
- [ ] --staged-only mode implemented
- [ ] validate_taskcard_file() calls new validator
- [ ] V1 verification passes

### Layer 2: Pre-Commit Hook
- [ ] hooks/pre-commit created and executable
- [ ] Hook validates staged taskcards only
- [ ] Hook blocks commits on validation failure
- [ ] Hook execution time <5 seconds
- [ ] scripts/install_hooks.py updated
- [ ] V3 verification passes

### Layer 3: Developer Tools
- [ ] 00_TEMPLATE.md created with all 14 sections
- [ ] Template includes guidance comments
- [ ] scripts/create_taskcard.py created
- [ ] Creation script prompts for required fields
- [ ] Created taskcards pass validation
- [ ] Script offers to open in editor

### Layer 4: Documentation
- [ ] AG-002 added to specs/30_ai_agent_governance.md
- [ ] 14 required sections documented
- [ ] Enforcement mechanisms documented
- [ ] Quickstart guide created or updated

### Overall
- [ ] V1, V2, V3 verifications pass
- [ ] All 82 taskcards validated (may find legitimate gaps)
- [ ] No regressions in existing validation
- [ ] Evidence bundle created with all outputs
