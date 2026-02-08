# Creating Taskcards - Developer Quickstart

**Document**: Quickstart guide for developing taskcards in FOSS Launcher
**Last Updated**: 2026-02-03
**Related**: `plans/taskcards/00_TASKCARD_CONTRACT.md`, `specs/30_ai_agent_governance.md` (Gate AG-002)

---

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start (3 methods)](#quick-start-3-methods)
3. [The 14 Mandatory Sections](#the-14-mandatory-sections)
4. [Running Validation Locally](#running-validation-locally)
5. [Common Validation Errors](#common-validation-errors)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Introduction

### Why Taskcards?

Taskcards are the **binding contract** between planners and implementation agents. They ensure:
- **Clarity**: No ambiguity about what should be done
- **Quality**: All 14 mandatory sections prevent incomplete work
- **Determinism**: Exact specifications enable reproducible execution
- **Accountability**: Clear evidence of what was completed

### What is a Taskcard?

A taskcard is a single markdown file that specifies **one cohesive outcome**. It includes:
- **Frontmatter** (YAML): Metadata, dependencies, allowed file modifications
- **Body Sections** (Markdown): 14 mandatory sections describing the work
- **Evidence** (JSON/MD): Reports proving completion

**Location**: `plans/taskcards/TC-NNN_[slug].md`

**Example**:
```
plans/taskcards/TC-935_goldenize_pilot_one.md
plans/taskcards/TC-940_integrate_taskcard_validation.md
```

---

## Quick Start (3 Methods)

### Method 1: Using the Creation Script (EASIEST)

The creation script interactively generates a complete, valid taskcard:

```bash
.venv\Scripts\python.exe scripts\create_taskcard.py
```

**What happens**:
1. Script prompts for TC number, title, owner, tags
2. Generates YAML frontmatter with current date and git SHA
3. Creates file from template with all 14 sections
4. Validates the created taskcard
5. Offers to open in your default editor

**Time**: ~30 seconds

---

### Method 2: Using the Template (RECOMMENDED FOR EDITING)

If you prefer manual creation with a template:

1. **Copy the template**:
   ```bash
   copy plans\taskcards\00_TEMPLATE.md plans\taskcards\TC-950_[your-slug].md
   ```

2. **Edit in your editor**:
   ```bash
   code plans\taskcards\TC-950_[your-slug].md
   ```

3. **Replace template placeholders**:
   - `TC-XXX` → your TC number (e.g., `TC-950`)
   - `[Brief title]` → your title
   - `[agent or team name]` → owner
   - Fill in all 14 sections (see [The 14 Mandatory Sections](#the-14-mandatory-sections))

4. **Validate locally**:
   ```bash
   .venv\Scripts\python.exe tools\validate_taskcards.py
   ```

---

### Method 3: Manual Creation from Scratch

If neither script nor template is available:

1. **Create the file**:
   ```bash
   # File must start with plans/taskcards/TC-NNN_[slug].md
   echo. > plans\taskcards\TC-950_my-feature.md
   ```

2. **Add YAML frontmatter** (required):
   ```yaml
   ---
   id: TC-950
   title: "Your taskcard title"
   status: Draft
   priority: Normal
   owner: "Your Name or Team"
   updated: "2026-02-03"
   tags: ["tag1", "tag2"]
   depends_on: []
   allowed_paths:
     - plans/taskcards/TC-950_my-feature.md
     # Add other paths you'll modify
   evidence_required:
     - reports/agents/<agent>/TC-950/report.md
   spec_ref: "[get from: git rev-parse HEAD]"
   ruleset_version: "ruleset.v1"
   templates_version: "templates.v1"
   ---
   ```

3. **Add all 14 mandatory sections** (see next section)

4. **Run validation**:
   ```bash
   .venv\Scripts\python.exe tools\validate_taskcards.py
   ```

---

## The 14 Mandatory Sections

Every taskcard MUST contain these sections in order. Here's what each requires:

### 1. Objective

**What**: 1-2 sentence statement of what this taskcard achieves

**Template**:
```markdown
## Objective

[1-2 sentences describing the specific outcome this taskcard achieves]
```

**Example**:
```markdown
## Objective

Implement goldenization of Pilot One taskcards to enable deterministic,
reproducible test execution with full traceability of all state changes.
```

---

### 2. Required spec references

**What**: List specs that justify this work, with specific sections

**Template**:
```markdown
## Required spec references

- specs/XX_[name].md (Section Y: [what it defines])
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard format and validation rules)
```

**Example**:
```markdown
## Required spec references

- specs/30_ai_agent_governance.md (Section 3.2: Taskcard Completeness Gate AG-002)
- specs/34_strict_compliance_guarantees.md (Guarantee K: Version locking)
- plans/taskcards/00_TASKCARD_CONTRACT.md (14 mandatory sections)
```

**Why important**: Grounds your work in documented decision-making

---

### 3. Scope

**What**: Clear boundaries of what WILL and WON'T be done

**Template**:
```markdown
## Scope

### In scope
- Item 1
- Item 2

### Out of scope
- Item 1 (clearly NOT being done here)
- Item 2 (will be handled in TC-XXX)
```

**Example**:
```markdown
## Scope

### In scope
- Validate all 14 mandatory sections exist
- Check minimum items in Failure modes (3) and Review checklist (6)
- Enforce frontmatter/body allowed_paths matching
- Provide clear error messages for missing sections

### Out of scope
- Validating section content quality (scope creep)
- Integration with other CI/CD systems
- Automated fixing of validation failures
- Performance optimization of validator
```

---

### 4. Inputs

**What**: What files, data, or configuration this taskcard consumes

**Template**:
```markdown
## Inputs

- File/data/configuration X
- Output from TC-YYY
- User input Z
```

**Example**:
```markdown
## Inputs

- All taskcard files in `plans/taskcards/TC-*.md`
- Template file at `plans/taskcards/00_TEMPLATE.md`
- Current git SHA (from `git rev-parse HEAD`)
```

---

### 5. Outputs

**What**: What files, data, or artifacts this taskcard produces

**Template**:
```markdown
## Outputs

- File/artifact A at path X
- Modified file B
- Evidence bundle C
```

**Example**:
```markdown
## Outputs

- Enhanced `tools/validate_taskcards.py` with new validation function
- Updated `specs/30_ai_agent_governance.md` with AG-002 gate
- Created `docs/creating_taskcards.md` quickstart guide
- Evidence bundle at `reports/agents/AGENT_D/WS4_DOCUMENTATION/`
```

---

### 6. Allowed paths

**What**: Exact list of files you will modify or create (MUST match frontmatter)

**Template**:
```markdown
## Allowed paths

- plans/taskcards/TC-XXX_[slug].md
- [other paths]

### Allowed paths rationale
[Optional: Explain WHY these paths are needed]
```

**CRITICAL**: Must match `allowed_paths` in YAML frontmatter EXACTLY (same order)

**Example**:
```markdown
## Allowed paths

- plans/taskcards/TC-940_integration.md
- specs/30_ai_agent_governance.md
- docs/creating_taskcards.md
- tools/validate_taskcards.py
- hooks/pre-commit

### Allowed paths rationale

- TC-940 file: Taskcard definition itself
- specs file: Adding new AG-002 gate (required by Gate AG-002)
- docs file: Developer quickstart guide (required by PREVENT-4.4)
- validate_taskcards.py: Enhanced validator (required by Layer 1)
- pre-commit hook: Automated local validation (required by Layer 2)
```

---

### 7. Implementation steps

**What**: Numbered, detailed steps with commands and expected outputs

**Template**:
```markdown
## Implementation steps

### Step 1: [First step name]

[Detailed instructions, commands, and expected output]

```bash
# Command example
command --arg value
```

### Step 2: [Second step name]

[Continue with numbered steps]
```

**Example**:
```markdown
## Implementation steps

### Step 1: Read existing AG-002 gate

```bash
grep -A 20 "^### 3.2" specs/30_ai_agent_governance.md
```

**Expected output**: Current Branch Switching Gate (AG-002)

### Step 2: Renumber existing AG-002 to AG-003

Use edit tool to change Rule ID from AG-002 to AG-003 in Branch Switching Gate section

### Step 3: Insert new AG-002 (Taskcard Completeness Gate)

After AG-001 section, insert new gate with rule statement, rationale, enforcement, etc.
```

---

### 8. Failure modes

**What**: At least 3 possible ways the taskcard could fail, with detection and resolution

**Template**:
```markdown
## Failure modes

### Failure mode 1: [Name of failure scenario]

**Detection**: How to detect this failure (command, log message, error code)
**Resolution**: Step-by-step fix procedure
**Spec/Gate**: Which spec or gate this relates to

### Failure mode 2: [Name of failure scenario]
[Include at least 3 failure modes]

### Failure mode 3: [Name of failure scenario]
[Validation failures, missing dependencies, edge cases]
```

**Example**:
```markdown
## Failure modes

### Failure mode 1: Existing AG-002 not properly renumbered

**Detection**:
```bash
grep "AG-002" specs/30_ai_agent_governance.md
# Should show exactly 1 match (new gate only)
```

**Resolution**:
1. Search for all "AG-002" mentions
2. Verify new gate is AG-002, old Branch Switching is now AG-003
3. Check Appendix A table is updated

**Spec/Gate**: Section 3 of 30_ai_agent_governance.md, Gate AG-002

### Failure mode 2: Validator doesn't reject incomplete taskcards

**Detection**: Create test incomplete taskcard and run validator
**Resolution**: Check validate_mandatory_sections() function is called in validate_taskcard_file()
**Spec/Gate**: Gate AG-002, PREVENT-1.2 validation requirement

### Failure mode 3: Quickstart guide references non-existent files

**Detection**: Run validation on example commands in guide
**Resolution**: Test each code example locally before including
**Spec/Gate**: Documentation completeness requirement
```

---

### 9. Task-specific review checklist

**What**: At least 6 task-specific items (beyond standard acceptance checks)

**Template**:
```markdown
## Task-specific review checklist

[Minimum 6 items specific to THIS task]

1. [ ] Item 1 specific to this task
2. [ ] Item 2 specific to this task
3. [ ] Item 3 specific to this task
4. [ ] Item 4 specific to this task
5. [ ] Item 5 specific to this task
6. [ ] Item 6 specific to this task
```

**Example**:
```markdown
## Task-specific review checklist

1. [ ] AG-002 gate added with all required fields (Rule Statement, Rationale, Enforcement, Required Sections, Bypass)
2. [ ] Existing AG-002 (Branch Switching) renumbered to AG-003
3. [ ] All subsequent gates (AG-003→AG-004, etc.) renumbered sequentially
4. [ ] Appendix A table updated with new gate order
5. [ ] Quickstart guide covers all 14 mandatory sections with examples
6. [ ] Quickstart guide includes troubleshooting section with 5+ common errors
7. [ ] All code examples in guide tested and verified to work
8. [ ] Validator output matches expected errors from examples
```

---

### 10. Deliverables

**What**: Concrete files/artifacts required for task completion

**Template**:
```markdown
## Deliverables

- File/artifact A at path X
- Report at reports/agents/<agent>/TC-XXX/report.md
- Evidence bundle with validation outputs
- Updated documentation in specs/ or docs/
```

**Example**:
```markdown
## Deliverables

1. **Updated spec**: `specs/30_ai_agent_governance.md`
   - New AG-002 gate (Taskcard Completeness)
   - Renumbered gates AG-003 through AG-008
   - Updated Appendix A table

2. **New guide**: `docs/creating_taskcards.md`
   - 3 methods for taskcard creation
   - All 14 mandatory sections explained
   - Common validation errors and fixes
   - Troubleshooting section

3. **Evidence bundle**: `reports/agents/AGENT_D/WS4_DOCUMENTATION/`
   - plan.md (documentation plan)
   - changes.md (files modified, sections added)
   - evidence.md (verification of completeness)
   - self_review.md (12D self-review)
```

---

### 11. Acceptance checks

**What**: Measurable criteria that must ALL be true for task completion

**Template**:
```markdown
## Acceptance checks

1. [ ] Criterion 1 (e.g., tests pass)
2. [ ] Criterion 2 (e.g., validator passes)
3. [ ] Criterion 3 (e.g., specific file exists with expected content)
```

**Example**:
```markdown
## Acceptance checks

1. [ ] `specs/30_ai_agent_governance.md` updated with AG-002 gate
2. [ ] All existing gates renumbered (AG-002→AG-003, AG-003→AG-004, etc.)
3. [ ] `docs/creating_taskcards.md` created with 3 creation methods
4. [ ] All 14 mandatory sections documented with examples
5. [ ] Troubleshooting section includes at least 5 common validation errors
6. [ ] All code examples in guide are tested and working
7. [ ] Validator runs without errors on updated taskcards
8. [ ] Evidence artifacts created in reports/agents/AGENT_D/WS4_DOCUMENTATION/
```

---

### 12. Self-review

**What**: Evaluation across 12 dimensions (see `reports/templates/self_review_12d.md`)

**Template**:
```markdown
## Self-review

### 12D Checklist

1. **Determinism**: How is determinism ensured?
2. **Dependencies**: What dependencies were added/changed?
3. **Documentation**: What docs were updated?
4. **Data preservation**: How is data integrity maintained?
5. **Deliberate design**: What design decisions were made and why?
6. **Detection**: How are errors/issues detected?
7. **Diagnostics**: What logging/observability added?
8. **Defensive coding**: What validation/error handling added?
9. **Direct testing**: What tests verify this works?
10. **Deployment safety**: How is safe rollout ensured?
11. **Delta tracking**: What changed and how is it tracked?
12. **Downstream impact**: What systems/users are affected?

### Verification results

- [ ] Tests: X/X PASS
- [ ] Validation: Gate Y PASS
- [ ] Evidence captured: [location]
```

---

### 13. E2E verification

**What**: Concrete command(s) to verify end-to-end functionality

**Template**:
```markdown
## E2E verification

[Concrete command(s) to verify the complete workflow]

```bash
# Run the complete workflow
.venv\Scripts\python.exe [script] [args]
```

**Expected artifacts**:
- **[file path]** - [what it should contain]
- **[file path]** - [what it should contain]

**Expected results**:
- [Measurable outcome 1]
- [Measurable outcome 2]
```

**Example**:
```markdown
## E2E verification

Run the validator on all taskcards to verify completeness gate works:

```bash
.venv\Scripts\python.exe tools\validate_taskcards.py
```

**Expected artifacts**:
- **specs/30_ai_agent_governance.md** - Contains new AG-002 gate section
- **docs/creating_taskcards.md** - Contains quickstart guide with 14 sections explained
- **Validation output** - No errors for taskcards with all 14 sections

**Expected results**:
- Validator passes on all existing complete taskcards
- Validator reports missing sections for any incomplete taskcards
- Guide examples create valid taskcards
```

---

### 14. Integration boundary proven

**What**: Define upstream/downstream contracts

**Template**:
```markdown
## Integration boundary proven

**Upstream**: [What component/system provides input to this work?]

**Downstream**: [What component/system consumes output from this work?]

**Contract**: [What interface/API/data format is guaranteed between them?]
```

**Example**:
```markdown
## Integration boundary proven

**Upstream**:
- Existing taskcards (read-only)
- Spec pack (defines validation rules)
- Git repository (provides status, history)

**Downstream**:
- AI agents creating taskcards
- CI/CD system validating taskcards
- Developer tools (pre-commit hook, validation script)

**Contract**:
- Input: Taskcard markdown files in `plans/taskcards/TC-*.md`
- Output: Validation success/failure with detailed error messages
- Format: YAML frontmatter + 14 markdown sections
- Validation: All 14 sections required; failure modes min 3; checklist min 6
```

---

## Running Validation Locally

### Before committing, always validate:

```bash
# Validate all taskcards
.venv\Scripts\python.exe tools\validate_taskcards.py

# Validate only staged taskcards (used by pre-commit hook)
.venv\Scripts\python.exe tools\validate_taskcards.py --staged-only
```

### Expected output for VALID taskcards:

```
Validating taskcards in: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

Found 82 taskcard(s) to validate

✅ TC-935_goldenize_pilot_one.md PASS
✅ TC-936_goldenize_pilot_two.md PASS
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ All taskcards valid (82/82 PASS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### If validation fails:

```
❌ TC-950_incomplete.md FAIL
   - Missing required section: '## Objective'
   - Missing required section: '## Scope'
   - '## Failure modes' must have at least 3 failure modes (found 1)
```

---

## Common Validation Errors

### Error: Missing required section

**Message**: `Missing required section: '## Objective'`

**Cause**: A mandatory section is not present in the taskcard

**Solution**:
1. Open the taskcard in your editor
2. Find the section name in [The 14 Mandatory Sections](#the-14-mandatory-sections) above
3. Add it with appropriate content
4. Re-run validation

**Example**:
```markdown
## Objective

Implement the feature to enable X capability and solve Y problem.
```

---

### Error: Scope subsection missing

**Message**: `'## Scope' section must have '### In scope' subsection`

**Cause**: Scope section exists but lacks required subsections

**Solution**:
Add both `### In scope` and `### Out of scope` subsections:

```markdown
## Scope

### In scope
- Item 1
- Item 2

### Out of scope
- Item 1 (will be handled separately)
```

---

### Error: Insufficient failure modes

**Message**: `'## Failure modes' must have at least 3 failure modes (found 1)`

**Cause**: Failure modes section has fewer than 3 failure scenarios

**Solution**:
Add at least 3 failure modes with detection, resolution, and spec reference:

```markdown
## Failure modes

### Failure mode 1: Database connection fails

**Detection**: Connection timeout after 30 seconds
**Resolution**: Check database credentials and network connectivity
**Spec/Gate**: specs/XX_database.md, Gate Y

### Failure mode 2: Missing configuration file

**Detection**: FileNotFoundError on startup
**Resolution**: Run `python setup.py init` to create default config
**Spec/Gate**: specs/XX_config.md, Section Z

### Failure mode 3: Validation timeout

**Detection**: Validation takes >60 seconds
**Resolution**: Optimize regex patterns or split work into smaller taskcards
**Spec/Gate**: PREVENT-1.1 Performance requirement
```

---

### Error: Insufficient review checklist items

**Message**: `'## Task-specific review checklist' must have at least 6 items (found 3)`

**Cause**: Review checklist has fewer than 6 items

**Solution**:
Add task-specific items (not generic). Use format `- [ ]` or numbered list:

```markdown
## Task-specific review checklist

1. [ ] Feature implements expected behavior per spec section Y
2. [ ] Error messages are user-friendly and actionable
3. [ ] Performance meets <5 second target for typical use cases
4. [ ] Database queries use prepared statements (no SQL injection risk)
5. [ ] Logging captures all error paths for debugging
6. [ ] Documentation updated with examples
```

---

### Error: Allowed paths mismatch

**Message**: `Frontmatter and body allowed_paths mismatch`

**Cause**: The `allowed_paths` list in YAML frontmatter doesn't match the body section

**Solution**:
1. Find your YAML frontmatter at the top:
   ```yaml
   ---
   allowed_paths:
     - plans/taskcards/TC-950_myfile.md
     - specs/30_myspec.md
   ---
   ```

2. Find the `## Allowed paths` section in the body

3. Make them EXACTLY the same (same entries, same order):
   ```markdown
   ## Allowed paths

   - plans/taskcards/TC-950_myfile.md
   - specs/30_myspec.md
   ```

---

### Error: No YAML frontmatter found

**Message**: `No YAML frontmatter found`

**Cause**: File doesn't start with `---` delimiter

**Solution**:
Add YAML frontmatter at the very start of the file:

```yaml
---
id: TC-950
title: "Your taskcard title"
status: Draft
priority: Normal
owner: "Your Name"
updated: "2026-02-03"
tags: ["tag1"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-950_myfile.md
evidence_required:
  - reports/agents/<agent>/TC-950/report.md
spec_ref: "abc123def456"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

## Objective
[content starts here]
```

---

## Best Practices

### 1. Start with the creation script

```bash
.venv\Scripts\python.exe scripts\create_taskcard.py
```

This automatically creates a valid template with all 14 sections, saving time and preventing validation errors.

### 2. Write concrete implementation steps

❌ Bad:
```markdown
### Step 1: Implement validation

Implement a validation function that checks taskcards.
```

✅ Good:
```markdown
### Step 1: Add validate_mandatory_sections() function

Edit `tools/validate_taskcards.py` and add this function after line 228:

```python
def validate_mandatory_sections(body: str) -> List[str]:
    """Validate all 14 mandatory sections exist."""
    errors = []
    for section in MANDATORY_BODY_SECTIONS:
        pattern = rf"^## {re.escape(section)}\n"
        if not re.search(pattern, body, re.MULTILINE):
            errors.append(f"Missing required section: '## {section}'")
    return errors
```

Then add this line in validate_taskcard_file() after line 410:
```python
section_errors = validate_mandatory_sections(body)
errors.extend(section_errors)
```
```

### 3. Document failure modes realistically

❌ Bad:
```markdown
### Failure mode 1: Implementation fails

**Detection**: Something goes wrong
**Resolution**: Fix it
**Spec/Gate**: specs/XX.md
```

✅ Good:
```markdown
### Failure mode 1: Validator crashes on malformed YAML

**Detection**: YAML parsing error in logs, validation exits with code 1
**Resolution**:
1. Check YAML syntax (use online YAML validator)
2. Ensure all quotes are matched
3. Verify indentation is consistent (2 spaces)
4. Rerun validator
**Spec/Gate**: Gate AG-002 section 3.2
```

### 4. Match frontmatter and body allowed_paths exactly

✅ Correct:
```yaml
# Frontmatter
allowed_paths:
  - specs/30_myspec.md
  - tools/mytool.py
```

```markdown
# Body
## Allowed paths

- specs/30_myspec.md
- tools/mytool.py
```

### 5. Include spec references with sections

✅ Good:
```markdown
## Required spec references

- specs/30_ai_agent_governance.md (Section 3.2: Taskcard Completeness Gate)
- specs/34_strict_compliance_guarantees.md (Guarantee K: Version locking)
```

---

## Troubleshooting

### Problem: Pre-commit hook blocks my commit

**Cause**: Staged taskcard files have validation errors

**Solution**:
1. Run validator locally to see errors:
   ```bash
   .venv\Scripts\python.exe tools\validate_taskcards.py --staged-only
   ```

2. Fix errors using the [Common Validation Errors](#common-validation-errors) guide above

3. Stage changes and try committing again:
   ```bash
   git add plans\taskcards\TC-950_*.md
   git commit -m "fix: complete missing taskcard sections"
   ```

**Emergency bypass** (only for critical fixes):
```bash
git commit --no-verify -m "EMERGENCY FIX: [reason documented here]"
```

### Problem: Can't find git SHA for spec_ref

**Solution**: Get current commit SHA:
```bash
git rev-parse HEAD
# Output: abc123def456789...

# Use first 7 characters
git rev-parse HEAD | head -c 7
```

### Problem: Taskcard creation script not found

**Cause**: Agent B hasn't created it yet (it's being built in parallel)

**Solution**: Use the template method instead:
```bash
copy plans\taskcards\00_TEMPLATE.md plans\taskcards\TC-950_myfile.md
# Edit and fill in the template
```

### Problem: Multiple validation errors at once

**Solution**: Fix errors in order:
1. Missing sections (add them)
2. Subsection errors (add subsections like `### In scope`)
3. Count errors (add minimum items to Failure modes, checklist)
4. Mismatch errors (sync frontmatter and body)
5. Rerun validator to confirm

---

## Resources

- **Taskcard Contract**: `plans/taskcards/00_TASKCARD_CONTRACT.md` - Binding rules for all taskcards
- **AI Governance**: `specs/30_ai_agent_governance.md` - Gate AG-002 requirements
- **Self-Review Template**: `reports/templates/self_review_12d.md` - 12D evaluation checklist
- **Validator Code**: `tools/validate_taskcards.py` - See what validator checks
- **Example Taskcards**: `plans/taskcards/TC-935_*.md`, `TC-936_*.md` - Complete, passing taskcards

---

**Last Updated**: 2026-02-03
**Maintained By**: Agent D (Documentation & Specs)
