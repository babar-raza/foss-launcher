# AGENT D - Wave 2: Links & READMEs Execution Plan

**Created:** 2026-01-27T13:10:45 PKT
**Agent:** Agent D (Docs & Specs)
**Phase:** Pre-Implementation Hardening (NO IMPLEMENTATION)
**Tasks:** TASK-D3, TASK-D4

---

## Mission Summary

Execute Wave 2 pre-implementation hardening tasks:
- TASK-D3: Create missing READMEs (P1, 4-6h)
- TASK-D4: Fix 184 broken internal links (P0 BLOCKER, 9-15h)

**CRITICAL CONSTRAINTS:**
- NO IMPLEMENTATION (code changes)
- Documentation and specs only
- Read before edit (ALWAYS)
- Merge/patch existing content (NEVER overwrite)
- Idempotent operations

---

## Task Breakdown

### TASK-D3: Create missing READMEs
**Priority:** P1
**Estimated Time:** 4-6 hours
**Source:** LT-038, GAP-146, GAP-147, GAP-149, GAP-150

**Files to Create:**
1. `specs/schemas/README.md` - Schema validation and contracts
2. `reports/README.md` - Evidence structure
3. `docs/README.md` - Documentation structure
4. `CONTRIBUTING.md` - EXPAND (read first, merge)

**Acceptance Criteria:**
- [ ] All READMEs exist and have content
- [ ] Follow tone/style from main README.md
- [ ] No placeholders (violates Gate M)
- [ ] CONTRIBUTING.md expanded (not overwritten)
- [ ] All internal links validate

**Content Requirements:**
- schemas/README.md:
  - Schema naming convention
  - Where to add new schemas
  - How to validate schemas
- reports/README.md:
  - Directory structure explanation
  - Naming conventions
  - What goes where (evidence, self-reviews, artifacts)
- docs/README.md:
  - Index of all docs
  - When to use each doc
  - How to add new docs
- CONTRIBUTING.md:
  - Pull request checklist
  - Gate K details
  - How to add specs/taskcards
  - Validator usage

---

### TASK-D4: Fix 184 broken internal links
**Priority:** P0 BLOCKER
**Estimated Time:** 9-15 hours
**Source:** LT-030, GAP-001

**Strategy:**
1. Run `tools/check_markdown_links.py` to get baseline (184 broken links)
2. Fix broken links using strategies:
   - Update link target if file moved/renamed
   - Remove link if target no longer exists (update to plain text)
   - Create missing target file if it should exist (only for READMEs)
3. Re-run link checker until 0 broken links
4. Document all fixes in evidence.md

**Categories (from TASK_BACKLOG.md):**
- 129 absolute path links (70%): Convert to relative where appropriate
- 40 directory links (22%): Add file targets (e.g., /specs/ -> /specs/README.md)
- 8 broken anchors (4%): Fix heading format mismatches
- 4 line number anchors (2%): Remove #L123 or replace with section links
- 3 missing relative files (2%): Fix or remove links

**Acceptance Criteria:**
- [ ] `python tools/check_markdown_links.py` exits 0
- [ ] Link health = 100% (0 broken links)
- [ ] All 184 broken links resolved
- [ ] No new broken links introduced
- [ ] Link fix strategy documented

---

## Execution Order

**Rationale:** Execute TASK-D3 first to create READMEs, then TASK-D4 can fix links including new README references.

### Phase 1: TASK-D3 - Create READMEs (2-3 hours)
1. Read main README.md for style reference
2. Read existing CONTRIBUTING.md (MUST read before editing)
3. Create schemas/README.md
4. Create reports/README.md
5. Create docs/README.md
6. Expand CONTRIBUTING.md (merge, don't overwrite)
7. Run link checker on new files

### Phase 2: TASK-D4 - Fix 184 broken links (9-12 hours)
1. Run link checker to capture baseline
2. Categorize broken links by type
3. Fix links in batches:
   - Batch 1: Directory links to READMEs (40 links)
   - Batch 2: Broken anchors (8 links)
   - Batch 3: Line number anchors (4 links)
   - Batch 4: Missing relative files (3 links)
   - Batch 5: Absolute to relative conversions (129 links)
4. Run link checker after each batch
5. Final verification

---

## Risk Assessment

### High Risks
1. **Cascading Link Fixes:** Fixing one link may break others
   - **Mitigation:** Run link checker after each batch, not just at end
   - **Rollback:** Git reset if needed

2. **Broken Links in Generated Files:** Some files may be read-only or auto-generated
   - **Mitigation:** Document unfixable links with rationale
   - **Rollback:** Skip generated files, focus on hand-written markdown

3. **CONTRIBUTING.md Overwrite:** Accidentally overwriting instead of merging
   - **Mitigation:** Use Edit tool (not Write), read file first
   - **Rollback:** Git restore CONTRIBUTING.md

### Medium Risks
1. **README Style Inconsistency:** New READMEs don't match repository tone
   - **Mitigation:** Read main README.md first, follow style guide
   - **Rollback:** Revise READMEs based on self-review

2. **Link Checker False Positives:** Tool may report false broken links
   - **Mitigation:** Manually verify each broken link before fixing
   - **Rollback:** None needed (verification prevents bad fixes)

### Low Risks
1. **Spec Pack Breakage:** Editing markdown could break schema validation
   - **Mitigation:** Run `python scripts/validate_spec_pack.py` after changes
   - **Rollback:** Git reset affected files

---

## Rollback Strategy

### Immediate Rollback (per file)
```bash
# If Edit tool breaks a file
git restore <file_path>
```

### Batch Rollback (per task phase)
```bash
# If entire batch of link fixes breaks things
git restore specs/ plans/ docs/ reports/ *.md
```

### Full Rollback (entire Wave 2)
```bash
# If entire Wave 2 needs rollback
git restore .
```

**Verification After Rollback:**
- Run link checker: `python tools/check_markdown_links.py`
- Run spec pack validator: `python scripts/validate_spec_pack.py`
- Verify git status clean

---

## Validation Plan

### Per-Task Validation

**TASK-D3 (READMEs):**
- [ ] All 4 files exist (schemas/README.md, reports/README.md, docs/README.md, CONTRIBUTING.md expanded)
- [ ] No placeholders (search for "TODO", "TBD", "XXX")
- [ ] All internal links resolve (run link checker)
- [ ] CONTRIBUTING.md has new content appended (not overwritten)

**TASK-D4 (Links):**
- [ ] Baseline: `python tools/check_markdown_links.py` outputs 184 broken links
- [ ] After fix: `python tools/check_markdown_links.py` exits 0
- [ ] Link health = 100%
- [ ] No new broken links introduced

### Overall Validation
- [ ] Spec pack validates: `python scripts/validate_spec_pack.py` exits 0
- [ ] Link checker passes: `python tools/check_markdown_links.py` exits 0
- [ ] Git diff shows only intended changes
- [ ] All deliverables created (plan.md, changes.md, evidence.md, self_review.md, commands.sh)

---

## Deliverables Checklist

- [ ] plan.md (this file)
- [ ] changes.md (all files modified/created with excerpts)
- [ ] evidence.md (commands run, outputs captured)
- [ ] self_review.md (12-dimension assessment)
- [ ] commands.sh (all commands executed)
- [ ] artifacts/ (logs, outputs)

---

## Success Criteria

**PASS Criteria:**
- All acceptance criteria met for TASK-D3 and TASK-D4
- All 12 dimensions in self-review ≥ 4/5
- Spec pack validation passes
- Link checker exits 0
- No placeholders in new content
- CONTRIBUTING.md expanded (not overwritten)

**Evidence Required:**
- Link checker output before (184 broken)
- Link checker output after (0 broken)
- List of all link fixes with strategy used
- All README files with content
- CONTRIBUTING.md diff showing additions

---

## Assumptions

1. **Link Checker Accuracy:** tools/check_markdown_links.py accurately reports broken links
2. **Markdown Standards:** Repository follows standard markdown link syntax
3. **File Accessibility:** All markdown files are readable and writable
4. **Git Availability:** Git is available for rollback operations
5. **Schema Stability:** Creating READMEs won't affect schema validation
6. **Link Categories:** TASK_BACKLOG.md categorization is accurate
7. **README Requirements:** All 4 READMEs are truly needed (not duplicative)
8. **Style Consistency:** Main README.md style is appropriate for all READMEs

---

## Dependencies

**TASK-D3 Dependencies:**
- None (can start immediately)
- Requires: Read access to README.md and CONTRIBUTING.md

**TASK-D4 Dependencies:**
- TASK-D3 complete (READMEs exist for directory link fixes)
- Requires: Link checker tool functional

**External Dependencies:**
- Python 3.12+ (for link checker)
- Git (for rollback)
- File system write access

---

## Timeline Estimate

| Phase | Task | Estimated Time | Cumulative |
|-------|------|----------------|------------|
| 1 | Read reference materials | 30 min | 30 min |
| 2 | Create schemas/README.md | 45 min | 1h 15min |
| 3 | Create reports/README.md | 45 min | 2h |
| 4 | Create docs/README.md | 30 min | 2h 30min |
| 5 | Expand CONTRIBUTING.md | 1h | 3h 30min |
| 6 | Validate READMEs | 30 min | 4h |
| 7 | Run link checker baseline | 15 min | 4h 15min |
| 8 | Fix directory links (40) | 2h | 6h 15min |
| 9 | Fix broken anchors (8) | 1h | 7h 15min |
| 10 | Fix line anchors (4) | 30 min | 7h 45min |
| 11 | Fix missing files (3) | 30 min | 8h 15min |
| 12 | Fix absolute paths (129) | 4h | 12h 15min |
| 13 | Final validation | 1h | 13h 15min |
| 14 | Documentation & self-review | 2h | 15h 15min |

**Total Estimated Time:** 15 hours 15 minutes

---

## Agent Notes

- This is Wave 2 (depends on Wave 1 completion)
- Wave 1 completed 2026-01-27T17:15:00 PKT with 4.92/5 score
- TASK-D3 and TASK-D4 are now READY
- No implementation allowed (pre-implementation hardening only)
- All file modifications must be idempotent
- Evidence trail is mandatory for all operations

---

## Execution Log

**2026-01-27T13:10:45 PKT** - Plan created, ready to execute Phase 1
