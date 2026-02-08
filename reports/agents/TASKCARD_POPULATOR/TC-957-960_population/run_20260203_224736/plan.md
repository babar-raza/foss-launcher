# Taskcard Population Plan - TC-957 through TC-960

## Objective
Populate 4 newly created taskcards (TC-957, TC-958, TC-959, TC-960) with comprehensive implementation details extracted from their corresponding agent evidence packages (HEAL-BUG4, HEAL-BUG1, HEAL-BUG2, HEAL-BUG3).

## Evidence Package Mapping

| Taskcard | Title | Evidence Package | Bug |
|----------|-------|------------------|-----|
| TC-957 | Fix Template Discovery - Exclude Obsolete __LOCALE__ Templates | reports/agents/AGENT_B/HEAL-BUG4/run_20260203_215544/ | Bug #4 |
| TC-958 | Fix URL Path Generation - Remove Section from URL | reports/agents/AGENT_B/HEAL-BUG1/run_20260203_215837/ | Bug #1 |
| TC-959 | Add Defensive Index Page De-duplication | reports/agents/AGENT_B/HEAL-BUG2/run_20260203_220814/ | Bug #2 |
| TC-960 | Integrate Cross-Section Link Transformation | reports/agents/AGENT_B/HEAL-BUG3/run_20260203_215617/ | Bug #3 |

## 14 Required Taskcard Sections

For each taskcard, populate these sections:

1. **Objective** - 2-3 sentence description from agent plan.md
2. **Required spec references** - Extract from agent evidence packages
3. **Scope** (In scope / Out of scope) - From agent changes.md
4. **Inputs** - Files that were read/analyzed
5. **Outputs** - Files that were created/modified
6. **Allowed paths** - List of files modified (update frontmatter too)
7. **Implementation steps** - From agent plan.md, numbered list
8. **Failure modes** (minimum 3) - Create realistic failure modes based on implementation
9. **Task-specific review checklist** (minimum 6 items) - From agent self_review.md
10. **Deliverables** - From agent evidence.md
11. **Acceptance checks** - From agent evidence.md test results
12. **Self-review** - Reference the agent's self_review.md location
13. **E2E verification** - Commands from evidence.md
14. **Integration boundary proven** - Test results showing integration

## Implementation Strategy

### Phase 1: TC-957 (HEAL-BUG4)
1. Read taskcard template TC-957
2. Extract information from HEAL-BUG4 evidence package:
   - plan.md - Implementation approach and steps
   - changes.md - Code changes, in/out scope
   - evidence.md - Test results, verification
   - self_review.md - Quality assessment, checklist items
3. Populate all 14 sections with specific details
4. Update frontmatter allowed_paths with actual modified files
5. Use Edit tool to preserve YAML frontmatter

### Phase 2: TC-958 (HEAL-BUG1)
1. Read taskcard template TC-958
2. Extract information from HEAL-BUG1 evidence package
3. Populate all 14 sections
4. Update frontmatter allowed_paths

### Phase 3: TC-959 (HEAL-BUG2)
1. Read taskcard template TC-959
2. Extract information from HEAL-BUG2 evidence package
3. Populate all 14 sections
4. Update frontmatter allowed_paths

### Phase 4: TC-960 (HEAL-BUG3)
1. Read taskcard template TC-960
2. Extract information from HEAL-BUG3 evidence package
3. Populate all 14 sections
4. Update frontmatter allowed_paths

### Phase 5: Validation & Evidence
1. Run taskcard validator on all 4 taskcards
2. Fix any validation errors
3. Create summary report documenting all changes
4. Create changes.md documenting what was populated
5. Create evidence.md with validation results

## File Safety Rules
- ALWAYS read taskcard before editing
- Use Edit tool (never Write on existing files)
- Preserve YAML frontmatter exactly
- Only update body sections below frontmatter
- Keep markdown formatting consistent

## Success Criteria
- [ ] All 4 taskcards populated with comprehensive information
- [ ] All 14 mandatory sections filled (no "TODO" placeholders)
- [ ] Information extracted from corresponding agent evidence packages
- [ ] Taskcards pass validation (run validator to check)
- [ ] Summary report created in evidence package

## Timeline
- TC-957 population: 20 minutes
- TC-958 population: 20 minutes
- TC-959 population: 20 minutes
- TC-960 population: 20 minutes
- Validation & fixes: 10 minutes
- Documentation: 10 minutes

**Total Estimated Time**: 100 minutes
