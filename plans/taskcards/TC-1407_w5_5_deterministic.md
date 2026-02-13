---
taskcard_id: TC-1407
title: W5.5 Deterministic Defense-in-Depth
status: Done
priority: P1
created: "2026-02-12"
updated: "2026-02-12"
assigned_agent: Agent-B
depends_on: []
spec_ref: "0cd4ce327b97b36f870adf2909707cf560b7e50c"
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py
  - src/launch/workers/w5_5_content_reviewer/checks/content_quality.py
  - src/launch/workers/w5_5_content_reviewer/fixes/auto_fixes.py
  - tests/unit/workers/w5_5_content_reviewer/test_checks.py
  - tests/unit/workers/w5_5_content_reviewer/test_auto_fixes.py
  - reports/agents/agent_b/TC-1407/**
evidence_required:
  - Implementation changes with severity bumps
  - Test results showing checks fire correctly
  - Evidence of auto-fix routing integration
  - Self-review with 12D scoring
---

# TC-1407: W5.5 Deterministic Defense-in-Depth

## Objective

Add deterministic checks and auto-fixes as fallback for issues that survive LLM layers. This enhances W5.5 ContentReviewer with defense-in-depth by:
1. Bumping TA-3 api_reference_validation severity to make it visible to scoring
2. Bumping TA-14 foss_licensing_compliance severity to make it visible to scoring
3. Ensuring collapsed frontmatter detection is properly implemented in CQ-11
4. Verifying auto-fix routing handles all new check types

## Required spec references

- Plan: `C:\Users\prora\.claude\plans\virtual-scribbling-sifakis.md` lines 238-271 (TC-1407 specification)
- Spec: `specs/30_ai_agent_governance.md` (W5.5 ContentReviewer design)
- Existing implementation: TC-1100 (W5.5 ContentReviewer base implementation)

## Scope

### In scope

1. **TA-3 severity bump**: Change `api_reference_validation` from `"info"` to `"warn"`, cap from 3 to 8
2. **TA-14 severity bump**: Change `foss_licensing_compliance` from `"info"` to `"warn"`
3. **Collapsed frontmatter verification**: Ensure `_check_11_frontmatter_completeness()` properly detects 2+ YAML keys on same line
4. **Auto-fix routing verification**: Confirm `fix_foss_licensing()` and `fix_collapsed_frontmatter()` are properly routed
5. **Testing**: Run existing unit tests to verify no regressions

### Out of scope

- Adding new checks beyond severity adjustments
- Modifying auto-fix logic (already implemented)
- LLM-based fixes (this is deterministic layer only)
- Pilot verification (deferred to TC-1408)

## Inputs

- `src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py` (lines 163-189 for TA-3, lines 700-762 for TA-14)
- `src/launch/workers/w5_5_content_reviewer/checks/content_quality.py` (lines 648-683 for CQ-11 collapsed frontmatter)
- `src/launch/workers/w5_5_content_reviewer/fixes/auto_fixes.py` (lines 108-111 for routing, lines 1643-1815 for fix functions)
- Plan document: `C:\Users\prora\.claude\plans\virtual-scribbling-sifakis.md`

## Outputs

- Updated `technical_accuracy.py` with TA-3 severity `"warn"` and cap 8, TA-14 severity `"warn"`
- Verified `content_quality.py` collapsed frontmatter detection
- Verified `auto_fixes.py` routing logic
- Test results showing all tests pass
- Evidence report in `reports/agents/agent_b/TC-1407/evidence.md`
- Self-review in `reports/agents/agent_b/TC-1407/self_review.md`

## Allowed paths

- src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py
- src/launch/workers/w5_5_content_reviewer/checks/content_quality.py
- src/launch/workers/w5_5_content_reviewer/fixes/auto_fixes.py
- tests/unit/workers/w5_5_content_reviewer/test_checks.py
- tests/unit/workers/w5_5_content_reviewer/test_auto_fixes.py
- reports/agents/agent_b/TC-1407/**

### Allowed paths rationale

These are the exact files needed to implement severity bumps and verify routing. Tests are included for verification. No shared library changes required.

## Preconditions / dependencies

- TC-1100 completed (W5.5 ContentReviewer base implementation with checks and auto-fixes)
- Repository at commit: 0cd4ce327b97b36f870adf2909707cf560b7e50c

## Implementation steps

1. **Update TA-3 severity and cap** (technical_accuracy.py lines 163-189)
   - Change severity from `"info"` to `"warn"` (line ~755 in check 14 or similar pattern)
   - Change max_per_page from 3 to 8 (line ~183)
   - Verify docstring reflects defense-in-depth rationale

2. **Update TA-14 severity** (technical_accuracy.py lines 700-762)
   - Change severity from `"info"` to `"warn"` (line ~755)
   - Verify docstring reflects defense-in-depth rationale

3. **Verify CQ-11 collapsed frontmatter** (content_quality.py lines 648-683)
   - Confirm detection logic exists for 2+ YAML keys on same line
   - Verify severity is `"error"` and `auto_fixable=True`
   - Check quote-masking logic is present to avoid false positives

4. **Verify auto-fix routing** (auto_fixes.py lines 108-111)
   - Confirm `foss_licensing` check routes to `fix_foss_licensing()`
   - Confirm `frontmatter_completeness` with "collapsed" message routes to `fix_collapsed_frontmatter()`

5. **Run unit tests**
   - Execute: `.venv/Scripts/python.exe -m pytest tests/unit/workers/w5_5_content_reviewer/ -x`
   - Verify all tests pass
   - Check no regressions in check/fix behavior

6. **Create evidence reports**
   - Document changes in `reports/agents/agent_b/TC-1407/plan.md`
   - Record implementation in `reports/agents/agent_b/TC-1407/changes.md`
   - Write evidence in `reports/agents/agent_b/TC-1407/evidence.md`
   - Complete self-review in `reports/agents/agent_b/TC-1407/self_review.md`

## Failure modes

### FM-1: Severity change breaks pilot scoring
**Detection**: Pilots that previously PASS now REJECT or NEEDS_CHANGES
**Resolution**:
1. Review pilot output logs for new warnings
2. If warnings are false positives, tune check patterns
3. If warnings are legitimate, verify auto-fixes resolve them
4. Document in evidence report
**Spec/Gate**: Plan line 264-266 (Regression guards)

### FM-2: Cap increase causes false positive flood
**Detection**: Pages with many API references trigger excessive warnings
**Resolution**:
1. Review check logic for pattern over-matching
2. Verify cap of 8 is per-page, not global
3. Consider if pages are genuinely over-documenting APIs
4. Document in evidence report
**Spec/Gate**: Plan line 252 (TA-3 severity bump)

### FM-3: Auto-fix routing missing or incorrect
**Detection**: Issues marked auto_fixable but no fix applied
**Resolution**:
1. Check `apply_auto_fixes()` routing logic matches check names
2. Verify message text matching is correct (e.g., "collapsed" for frontmatter)
3. Add missing routing if needed
4. Document in evidence report
**Spec/Gate**: Plan line 262 (Routing section)

## Task-specific review checklist

1. TA-3 api_reference_validation severity changed from `"info"` to `"warn"`
2. TA-3 max_per_page cap changed from 3 to 8
3. TA-14 foss_licensing_compliance severity changed from `"info"` to `"warn"`
4. CQ-11 collapsed frontmatter detection verified (lines 648-683)
5. Auto-fix routing for `foss_licensing` verified (line ~108)
6. Auto-fix routing for `collapsed_frontmatter` verified (line ~110)
7. All unit tests pass with no regressions
8. Evidence report documents all changes with line numbers

## Deliverables

1. Updated `technical_accuracy.py` with TA-3 and TA-14 severity changes
2. Verified `content_quality.py` collapsed frontmatter logic
3. Verified `auto_fixes.py` routing logic
4. Test results: `pytest tests/unit/workers/w5_5_content_reviewer/ -x` output
5. Evidence report: `reports/agents/agent_b/TC-1407/evidence.md`
6. Self-review: `reports/agents/agent_b/TC-1407/self_review.md` (12D format)

## Acceptance checks

- [ ] TA-3 severity is `"warn"` in technical_accuracy.py
- [ ] TA-3 max_per_page cap is 8 in technical_accuracy.py
- [ ] TA-14 severity is `"warn"` in technical_accuracy.py
- [ ] CQ-11 collapsed frontmatter detection exists and is correct
- [ ] Auto-fix routing includes `foss_licensing` → `fix_foss_licensing()`
- [ ] Auto-fix routing includes `frontmatter_completeness` + "collapsed" → `fix_collapsed_frontmatter()`
- [ ] All tests in `tests/unit/workers/w5_5_content_reviewer/` pass
- [ ] Evidence report documents changes with line numbers
- [ ] Self-review shows 12D scores ≥4/5 with no unresolved gaps

## Test plan

### Unit tests (existing)
Run existing W5.5 test suite to verify no regressions:
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/w5_5_content_reviewer/ -x
```

### Verification tests
1. **TA-3 severity**: Check that `_check_3_api_reference_validation()` returns issues with `severity: "warn"`
2. **TA-14 severity**: Check that `_check_14_foss_licensing_compliance()` returns issues with `severity: "warn"`
3. **CQ-11 collapsed**: Check that `_check_11_frontmatter_completeness()` detects `title: "Foo" description: "Bar"` as collapsed
4. **Auto-fix routing**: Check that issues with check name `foss_licensing_compliance` route to `fix_foss_licensing()`

## Self-review

*(To be completed after implementation - use reports/templates/self_review_12d.md)*
