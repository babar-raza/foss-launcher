# Agent D - Wave 1 Quick Wins - Execution Plan

**Agent:** AGENT_D (Docs & Specs)
**Run ID:** run_20260127_163000
**Created:** 2026-01-27T16:30:00 PKT

## Mission

Execute 5 pre-implementation hardening tasks focused on templates, documentation, and schema fixes.

**CRITICAL CONSTRAINTS:**
- NO IMPLEMENTATION: Only docs/specs/schemas
- FILE SAFETY: Read first, merge/patch, never overwrite
- EVIDENCE-BASED: Every claim must have proof
- 12-DIMENSION SELF-REVIEW: All ≥4/5 required for PASS

---

## Task Sequencing

Execute in this order (quick wins first):

1. **TASK-D8** (5 min) - ProductFacts schema: Add who_it_is_for field
2. **TASK-D9** (30 min) - TRACEABILITY_MATRIX: Rename duplicate REQ-011
3. **TASK-D1** (1-2h) - Create self_review_12d.md template
4. **TASK-D2** (2-3h) - Document .venv + uv flow
5. **TASK-D7** (2-3h) - Fix ruleset contract mismatch

---

## TASK-D8: Fix ProductFacts schema missing field

### Issue
specs/schemas/product_facts.schema.json is missing `who_it_is_for` field in positioning object. This field is referenced in specs/03_product_facts_and_evidence.md:17 but not in schema.

### Steps
1. Read specs/schemas/product_facts.schema.json (DONE - already read)
2. Edit positioning.properties to add who_it_is_for field
3. Run validation: `python scripts/validate_spec_pack.py`
4. Document change in changes.md

### Expected Change
```json
"positioning": {
  "type": "object",
  "additionalProperties": false,
  "required": ["tagline", "short_description"],
  "properties": {
    "tagline": {"type": "string"},
    "short_description": {"type": "string"},
    "audience": {"type": "string"},
    "who_it_is_for": {
      "type": "string",
      "description": "Target audience description"
    }
  }
}
```

### Acceptance
- [ ] Field added to schema
- [ ] Schema validates (validate_spec_pack.py exits 0)
- [ ] No schema validation errors

---

## TASK-D9: Eliminate duplicate REQ-011

### Issue
TRACEABILITY_MATRIX.md has two sections with heading "## REQ-011":
- Line 120: "REQ-011: Idempotent patch engine"
- Line 128: "REQ-011: Two pilot projects for regression" (DUPLICATE)

This breaks deterministic traceability and link anchors.

### Steps
1. Read TRACEABILITY_MATRIX.md (DONE - already read)
2. Edit line 128: Change "## REQ-011: Two pilot..." to "## REQ-011a: Two pilot..."
3. Verify no other references need updating (grep for "REQ-011" in repo)
4. Run link checker: `python tools/check_markdown_links.py`
5. Document change in changes.md

### Acceptance
- [ ] No duplicate REQ headings in TRACEABILITY_MATRIX.md
- [ ] REQ-011 = "Idempotent patch engine" (unchanged)
- [ ] REQ-011a = "Two pilot projects" (renamed)
- [ ] Link checker passes

---

## TASK-D1: Create self-review template

### Issue
Missing reports/templates/self_review_12d.md. This template is referenced by:
- plans/taskcards/00_TASKCARD_CONTRACT.md
- TRACEABILITY_MATRIX.md:295
- Gate D (link checker)

### Steps
1. Read plans/prompts/agent_self_review.md (DONE - already read)
2. Create reports/templates/ directory if missing
3. Write reports/templates/self_review_12d.md with:
   - All 12 dimensions (from agent_self_review.md)
   - Clear scoring rubric (1-5 scale)
   - Evidence fields for each dimension
   - Table format for scores
   - No placeholders (violates Gate M)
4. Run link checker: `python tools/check_markdown_links.py`
5. Document creation in changes.md

### 12 Dimensions (from agent_self_review.md)
1. Spec Adherence
2. Determinism
3. Test Coverage
4. Write Fence Compliance
5. Error Handling
6. Documentation
7. Code Quality
8. Security
9. Performance
10. Integration
11. Evidence Quality
12. Acceptance Criteria

### Acceptance
- [ ] File reports/templates/self_review_12d.md exists
- [ ] Contains all 12 dimensions
- [ ] No placeholders
- [ ] Link checker passes

---

## TASK-D2: Document .venv + uv flow

### Issue
Documentation doesn't clearly explain:
- How to set up .venv with uv
- How to run preflight validation
- What to expect when NOT in .venv (Gate 0, Gate K failures)

### Steps
1. Read README.md (DONE)
2. Read docs/cli_usage.md (DONE)
3. Update README.md:
   - Add "Quick Start" section with `make install-uv` instructions
   - Explain .venv activation
   - Add preflight command: `.venv/bin/python tools/validate_swarm_ready.py`
4. Create DEVELOPMENT.md (file doesn't exist):
   - Detailed setup instructions
   - Explain: .venv = runtime environment location
   - Explain: uv.lock = dependency lockfile for deterministic installs
   - Document expected failures when NOT in .venv (Gate 0, Gate K)
   - Troubleshooting section
5. Update docs/cli_usage.md:
   - Add preflight validation runbook
   - Link to DEVELOPMENT.md for setup
6. Run link checker: `python tools/check_markdown_links.py`
7. Document changes in changes.md

### README.md Changes (MERGE)
Add new section after "Quick start (local dev)" heading around line 45:

```markdown
## Quick Start

### 1. Install uv and create .venv

```bash
make install-uv
```

This command:
- Installs uv if not present
- Creates .venv/ at repository root
- Runs `uv sync` to install dependencies from uv.lock

### 2. Activate .venv

Windows:
```bash
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

### 3. Run preflight validation

```bash
# From .venv (activated):
python tools/validate_swarm_ready.py

# Or without activation (use .venv/bin/python explicitly):
.venv/bin/python tools/validate_swarm_ready.py
```

**Expected output:** All gates pass (exit code 0)

**Common failures if NOT in .venv:**
- Gate 0: Environment policy violation (must use .venv)
- Gate K: Supply chain pinning check fails
```

### DEVELOPMENT.md Creation (NEW FILE)
Create comprehensive developer guide covering:
- Prerequisites
- Installation (uv vs pip)
- .venv policy explanation
- Development workflow
- Testing
- Troubleshooting

### docs/cli_usage.md Changes (MERGE)
Add section after "Escalation" heading:

```markdown
## Preflight Validation

Before starting agent work, validate the repository is swarm-ready.

### Command

```bash
# From activated .venv:
python tools/validate_swarm_ready.py

# Or without activation:
.venv/bin/python tools/validate_swarm_ready.py
```

### What It Checks

See [specs/09_validation_gates.md](../../../../../specs/09_validation_gates.md) for full gate catalog.

Key gates:
- Gate 0: .venv policy compliance
- Gate A: Spec pack integrity
- Gate B: Taskcard frontmatter validity
- Gate D: Markdown link health
- Gate K: Supply chain pinning

### Expected Output

```
Running preflight validation...
[Gate 0] Environment policy: PASS
[Gate A] Spec pack integrity: PASS
...
All gates PASS. Repository is swarm-ready.
```

Exit code: 0

### Troubleshooting

See [DEVELOPMENT.md](../../../../../DEVELOPMENT.md) for detailed troubleshooting.
```

### Acceptance
- [ ] README.md has "Quick Start" section with make install-uv + preflight
- [ ] DEVELOPMENT.md exists with detailed setup
- [ ] docs/cli_usage.md has preflight runbook
- [ ] Fresh clone can follow docs and get green preflight run
- [ ] Link checker passes

---

## TASK-D7: Fix ruleset contract mismatch

### Issue
specs/schemas/ruleset.schema.json doesn't validate specs/rulesets/ruleset.v1.yaml. The schema is missing optional fields that exist in the YAML file.

### Analysis (from reading both files)

**Schema currently has (CORRECT - already present):**
- schema_version, style, truth, editing, sections (all required)
- hugo, claims (optional)

**YAML file has:**
- All required fields ✓
- All optional fields (hugo, claims) ✓

**Actual issue:** Schema appears complete. Need to verify with validation.

### Steps
1. Read specs/schemas/ruleset.schema.json (DONE)
2. Read specs/rulesets/ruleset.v1.yaml (DONE)
3. Read specs/20_rulesets_and_templates_registry.md (DONE)
4. Test current validation:
   ```bash
   python scripts/validate_spec_pack.py
   ```
5. If validation fails:
   - Identify missing/mismatched fields
   - Update schema to match YAML structure
   - Update spec doc if needed
6. Extend scripts/validate_spec_pack.py to validate rulesets (if not already done)
7. Run validation again: `python scripts/validate_spec_pack.py` (must exit 0)
8. Document changes in changes.md

### Potential Schema Updates (TBD based on validation)
- Verify all fields in ruleset.v1.yaml are in schema
- Ensure required/optional match between schema and spec doc
- Add any missing fields with proper types

### Acceptance
- [ ] specs/schemas/ruleset.schema.json validates ruleset.v1.yaml
- [ ] specs/20_rulesets_and_templates_registry.md defines all ruleset keys normatively
- [ ] scripts/validate_spec_pack.py validates rulesets
- [ ] `python scripts/validate_spec_pack.py` exits 0

---

## Verification Commands

All commands to run at the end:

```bash
# Schema validation
python scripts/validate_spec_pack.py

# Link health
python tools/check_markdown_links.py

# Duplicate REQ check
grep -E "^## REQ-[0-9]+" TRACEABILITY_MATRIX.md | sort | uniq -d
```

Expected outputs:
- validate_spec_pack.py: exit 0
- check_markdown_links.py: exit 0
- grep duplicate check: empty output

---

## Assumptions

1. **Tooling works:** validate_spec_pack.py and check_markdown_links.py are functional
2. **No conflicting changes:** No other agent is modifying these files concurrently
3. **Schema validation exists:** validate_spec_pack.py already validates JSON schemas
4. **.venv is active:** Running from .venv for all commands

**Verification of assumptions:**
- Assumption 1: Will verify by running commands
- Assumption 2: Check git status before starting
- Assumption 3: Will inspect validate_spec_pack.py if needed
- Assumption 4: Confirmed (working directory is in .venv context)

---

## Rollback Plan

If any task fails validation:

1. **Git status:** Check for unstaged/staged changes
2. **Git diff:** Review all changes
3. **Revert:** `git checkout -- <file>` for any failed file
4. **Document:** Record failure reason in evidence.md
5. **Create gap:** File issue in KNOWN_GAPS section of self_review.md

For each task:
- **TASK-D8:** Revert product_facts.schema.json
- **TASK-D9:** Revert TRACEABILITY_MATRIX.md
- **TASK-D1:** Delete reports/templates/self_review_12d.md
- **TASK-D2:** Revert README.md, docs/cli_usage.md, delete DEVELOPMENT.md
- **TASK-D7:** Revert ruleset.schema.json, 20_rulesets_and_templates_registry.md, validate_spec_pack.py

---

## Done Means

**Task is DONE when:**
- [ ] All acceptance criteria met
- [ ] All verification commands pass
- [ ] Changes documented in changes.md
- [ ] Evidence captured in evidence.md
- [ ] Commands logged in commands.sh
- [ ] No known gaps or blockers

**Wave 1 is DONE when:**
- [ ] All 5 tasks DONE
- [ ] Self-review scores all ≥4/5
- [ ] No placeholders in any artifact
- [ ] Link checker passes (0 broken links)
- [ ] Schema validator passes (0 errors)
- [ ] All evidence present and linked

---

## Risk Assessment

**Low Risk:**
- TASK-D8: Simple schema field addition (isolated change)
- TASK-D9: Simple heading rename (isolated change)

**Medium Risk:**
- TASK-D1: Template creation (new file, must match all references)
- TASK-D2: Doc updates (multiple files, must preserve existing content)

**High Risk:**
- TASK-D7: Schema validation extension (could affect existing validation logic)

**Mitigation:**
- Read all files before editing
- Use Edit tool (not Write) for existing files
- Verify after each change
- Keep rollback plan ready

---

## Next Steps

1. Execute TASK-D8 (5 min)
2. Execute TASK-D9 (30 min)
3. Execute TASK-D1 (1-2h)
4. Execute TASK-D2 (2-3h)
5. Execute TASK-D7 (2-3h)
6. Run all verification commands
7. Create evidence.md
8. Create changes.md
9. Create self_review.md
10. Report results
