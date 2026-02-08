# Agent B Implementation Plan: Enhanced Validator (Layer 1)

**Workstream:** Workstream 1 - Enhanced Validator
**Agent:** Agent B (Implementation)
**Created:** 2026-02-03
**Status:** In Progress

---

## Objective

Enhance `tools/validate_taskcards.py` to validate ALL 14 mandatory sections defined in `plans/taskcards/00_TASKCARD_CONTRACT.md`, preventing incomplete taskcards from being merged.

## Current State Analysis

**Validator Status:**
- Current validator: `tools/validate_taskcards.py` (482 lines)
- Checks: 4 sections (E2E verification, Integration boundary, Allowed paths match, frontmatter)
- Missing: 10 of 14 mandatory sections

**Taskcard Contract Requirements (14 sections):**
1. Objective
2. Required spec references
3. Scope (with "In scope" and "Out of scope" subsections)
4. Inputs
5. Outputs
6. Allowed paths
7. Implementation steps
8. Failure modes (minimum 3 failure modes)
9. Task-specific review checklist (minimum 6 items)
10. Deliverables
11. Acceptance checks
12. Self-review
13. E2E verification (already validated)
14. Integration boundary proven (already validated)

**Current Taskcards:**
- Total: 82 taskcards
- TC-935 and TC-936: NOW COMPLETE (fixed by TC-937)

---

## Implementation Order

### Phase 1: Add Constants and Core Validation (PREVENT-1.1, PREVENT-1.2)
**Time Estimate:** 45 minutes

1. **PREVENT-1.1**: Add MANDATORY_BODY_SECTIONS constant
   - Location: After line 228 (after VAGUE_E2E_PHRASES)
   - Define 14 section names as list
   - Add comment: TC-PREVENT-INCOMPLETE

2. **PREVENT-1.2**: Implement validate_mandatory_sections() function
   - Location: After validate_integration_boundary_section() (~line 228)
   - Validation logic:
     - Check all 14 sections exist (regex match)
     - Validate Scope subsections (In scope / Out of scope)
     - Count Failure modes (minimum 3 ### headers)
     - Count Review checklist items (minimum 6 items)
   - Return: List of error messages (empty if valid)

### Phase 2: Integration (PREVENT-1.3)
**Time Estimate:** 15 minutes

3. **PREVENT-1.3**: Update validate_taskcard_file()
   - Location: Around line 410, before E2E validation
   - Add call to validate_mandatory_sections(body)
   - Extend errors list
   - Add comment: TC-PREVENT-INCOMPLETE

### Phase 3: CLI Enhancement (PREVENT-1.4)
**Time Estimate:** 30 minutes

4. **PREVENT-1.4**: Add --staged-only argument parsing
   - Import argparse at top of file
   - In main() function:
     - Create ArgumentParser
     - Add --staged-only flag
     - If --staged-only: Use `git diff --cached --name-only`
     - Filter to taskcard files (plans/taskcards/TC-*.md)
     - Otherwise: Use existing find_taskcards()

### Phase 4: Testing and Evidence (PREVENT-1.5)
**Time Estimate:** 30 minutes

5. **PREVENT-1.5**: Test enhanced validator
   - Run on all 82 taskcards
   - Verify TC-935 and TC-936 PASS
   - Document any taskcards that fail
   - Capture all outputs for evidence

---

## Expected Outcomes

### Success Metrics
- Validator runs without crashes on all 82 taskcards
- TC-935 and TC-936 PASS (no regression)
- Missing sections detected in incomplete taskcards
- Execution time <5 seconds for all 82 taskcards

### Error Reporting
Validator should report:
- Missing section: "## [Section name]"
- Missing subsections: "### In scope", "### Out of scope"
- Insufficient failure modes: "must have at least 3 (found X)"
- Insufficient checklist items: "must have at least 6 (found X)"

---

## Code Patterns to Follow

### Pattern 1: Section Existence Check
```python
pattern = rf"^## {re.escape(section)}\n"
if not re.search(pattern, body, re.MULTILINE):
    errors.append(f"Missing required section: '## {section}'")
```

### Pattern 2: Section Content Extraction
```python
match = re.search(r"^## Section\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
if match:
    content = match.group(1)
    # Process content
```

### Pattern 3: Item Counting
```python
# Count ### headers
item_count = len(re.findall(r"^### ", content, re.MULTILINE))

# Count list items
item_count = len(re.findall(r"^[\d\-\*]\.", content, re.MULTILINE))
```

---

## Risk Mitigation

### Risk 1: Existing Taskcards May Fail
**Mitigation:**
- This is expected and acceptable (discovery phase)
- Document which taskcards fail
- TC-935 and TC-936 should PASS (they're fixed)
- Other failures indicate legitimate gaps

### Risk 2: Regex Matching Issues
**Mitigation:**
- Use re.escape() for literal section names
- Test against multiple taskcard formats
- Follow existing validator patterns

### Risk 3: Performance Degradation
**Mitigation:**
- Use efficient regex patterns
- Validate in single pass where possible
- Measure execution time

---

## Evidence Artifacts to Create

1. **plan.md** (this file) - Implementation plan
2. **changes.md** - Detailed line-by-line changes
3. **evidence.md** - Commands run and outputs
4. **commands.sh** - All commands executed
5. **self_review.md** - 12D self-review with scores

---

## Next Steps

1. Read current validator implementation (line 228 context)
2. Implement PREVENT-1.1 (constant)
3. Implement PREVENT-1.2 (validation function)
4. Implement PREVENT-1.3 (integration)
5. Implement PREVENT-1.4 (CLI argument)
6. Test and capture evidence
7. Create all evidence artifacts
8. Write self-review

---

## Dependencies

**Required Files:**
- `tools/validate_taskcards.py` (exists, will modify)
- `plans/taskcards/00_TASKCARD_CONTRACT.md` (exists, reference)

**Required Tools:**
- Python 3.x (available in .venv)
- git (for --staged-only mode)

**External Dependencies:**
- None (uses existing stdlib: sys, re, pathlib, yaml, argparse, subprocess)

---

## Completion Checklist

- [ ] PREVENT-1.1: MANDATORY_BODY_SECTIONS constant added
- [ ] PREVENT-1.2: validate_mandatory_sections() function implemented
- [ ] PREVENT-1.3: validate_taskcard_file() updated
- [ ] PREVENT-1.4: --staged-only argument implemented
- [ ] PREVENT-1.5: Validator tested on all 82 taskcards
- [ ] TC-935 and TC-936 PASS verification
- [ ] All evidence artifacts created
- [ ] Self-review completed with all dimensions ≥4
