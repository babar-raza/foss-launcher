---
id: TC-1303
title: "LLM Pipeline Hardening — E2E Verification with Both Pilots"
status: Draft
priority: Critical
owner: "Agent C (Testing & Verification)"
updated: "2026-02-11"
tags: ["verification", "e2e", "pilots", "pipeline-hardening", "w2", "w5.5"]
depends_on: ["TC-1300", "TC-1301", "TC-1302"]
allowed_paths:
  - plans/taskcards/TC-1303_llm_pipeline_verification.md
  - tests/unit/workers/test_w2_priority_enrichment.py
  - reports/agents/AGENT_C/TC-1303/evidence.md
  - reports/agents/AGENT_C/TC-1303/self_review.md
evidence_required:
  - reports/agents/AGENT_C/TC-1303/evidence.md
  - reports/agents/AGENT_C/TC-1303/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1303 — LLM Pipeline Hardening — E2E Verification

## Objective
Verify that all three hardening changes (TC-1300 W2 priority enrichment, TC-1301 W5.5 agent implementation, TC-1302 mandatory enforcement) work together end-to-end. Run both pilots and confirm: W2 LLM enrichment fires for high-value claims, W5.5 always runs with functional agents, and no regressions in page output or test suite.

## Required spec references
- TC-1300 evidence (W2 priority enrichment — must be complete)
- TC-1301 evidence (W5.5 agent implementation — must be complete)
- TC-1302 evidence (mandatory enforcement — must be complete)
- specs/08_semantic_claim_enrichment.md (enrichment contract)
- specs/21_worker_contracts.md (W5.5 contract)

## Scope

### In scope
1. **Full test suite run** — All unit + integration tests pass
2. **3D pilot E2E** — Run `pilot-aspose-3d-foss-python` end-to-end
3. **Note pilot E2E** — Run `pilot-aspose-note-foss-python` end-to-end
4. **W2 enrichment verification** — Confirm `enrichment_priority_split` event in logs, verify LLM-tier claims have non-empty `use_cases`
5. **W5.5 verification** — Confirm W5.5 runs (no `review_content_skipped` log), confirm scores in `review_report.json`
6. **Before/after comparison** — Document page count, enrichment quality, review scores
7. **Regression check** — No pages lost, no scores degraded vs pre-hardening baseline

### Out of scope
- Fixing any issues found (create new taskcards for fixes)
- Performance optimization
- Modifying source code (verification only — this is a read-only + run taskcard)

## Inputs
- Complete codebase with TC-1300, TC-1301, TC-1302 applied
- Pilot configs in `specs/pilots/` and `configs/pilots/`
- LLM endpoint (primary or fallback)

## Outputs
- Test results (pytest output)
- Pilot run artifacts (in `tmp/verify-*` output dirs)
- Verification report with before/after comparison
- Evidence bundle

## Allowed paths
- plans/taskcards/TC-1303_llm_pipeline_verification.md
- tests/unit/workers/test_w2_priority_enrichment.py
- reports/agents/AGENT_C/TC-1303/evidence.md
- reports/agents/AGENT_C/TC-1303/self_review.md

### Allowed paths rationale
This is a verification-only taskcard. It runs tests and pilots but does not modify source code. The only writable paths are the taskcard itself, evidence reports, and the new test file (in case minor test fixes are needed to make the suite green).

## Implementation steps

### Step 1: Run full test suite
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```

**Expected**: All tests pass (including new tests from TC-1300, TC-1301, TC-1302).

**Resilience note**: If tests fail, document the failures in the evidence report. Do NOT fix code — create a blocker issue. However, if the failure is in a test file listed in `allowed_paths` (e.g., a test that needs a minor assertion update), fix it.

### Step 2: Run 3D pilot end-to-end
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output tmp/verify-3d-hardened
```

**Verify in logs:**
- `enrichment_priority_split` event with `llm_tier_count > 0`
- NO `enrichment_auto_offline` event (the old threshold should be gone)
- NO `review_content_skipped` event (W5.5 is mandatory now)
- `review_content_completed` event with `overall_status`

**Verify in artifacts:**
- `tmp/verify-3d-hardened/artifacts/extracted_claims.json` — Check a sample of feature/api claims for non-empty `use_cases` and `prerequisites` (LLM-enriched tier)
- `tmp/verify-3d-hardened/artifacts/review_report.json` — Check dimension scores and overall status

### Step 3: Run Note pilot end-to-end
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output tmp/verify-note-hardened
```

Same verification checks as Step 2. Note pilot has 6551 claims — verify the priority split produces ~300 LLM + ~6251 heuristic.

### Step 4: Compare enrichment quality
For both pilots, examine `extracted_claims.json`:

**LLM-enriched claims (claim_kind: feature, api, workflow):**
- `audience_level`: Should be more nuanced (not just keyword-based)
- `complexity`: Should reflect actual claim complexity
- `use_cases`: Should be non-empty array with specific scenarios
- `prerequisites`: Should reference other claim_ids where applicable
- `target_persona`: Should be a descriptive sentence

**Heuristic-enriched claims (claim_kind: format, limitation, compatibility):**
- `audience_level`: Keyword-based (acceptable)
- `use_cases`: Empty array (acceptable for heuristic tier)

Document 5 example claims from each tier in the evidence report.

### Step 5: Compare review scores
Check `review_report.json` for both pilots:

| Dimension | Minimum expected | Pre-hardening baseline |
|-----------|-----------------|----------------------|
| Content Quality | >= 4 | 5 (3D), 5 (Note) |
| Technical Accuracy | >= 4 | 5 (3D), 4 (Note) |
| Usability | >= 4 | 5 (3D), 4 (Note) |

If any score drops below 4, investigate which checks failed and whether it's a regression or a new detection.

### Step 6: Document before/after comparison
Create a comparison table in the evidence report:

| Metric | Before (baseline) | After (hardened) | Delta |
|--------|-------------------|------------------|-------|
| 3D page count | N | N | 0 |
| Note page count | N | N | 0 |
| 3D LLM-enriched claims | 0 | ~300 | +300 |
| Note LLM-enriched claims | 0 | ~300 | +300 |
| 3D review CQ/TA/U scores | 5/5/5 | ≥4/≥4/≥4 | — |
| Note review CQ/TA/U scores | 5/4/4 | ≥4/≥4/≥4 | — |
| Test count | N | ≥N+20 | +20 |
| W2 duration (3D) | ~M min | ~M+5 min | +5 min (LLM enrichment) |

### Step 7: Final assessment
Write a PASS/FAIL verdict:
- **PASS** if: all tests green, both pilots complete with exit code 0, no score regressions below 4, LLM enrichment verified, W5.5 mandatory verified
- **FAIL** if: any test failure, pilot crash, score regression, or missing verification evidence. Create blocker issues for each failure.

## Failure modes

### Failure mode 1: LLM endpoint unavailable during pilot run
**Detection**: W2 logs show `w2_llm_client_init_failed` or LLM calls return timeout errors.
**Resolution**: Verify fallback is working (gemma3:12b on local Ollama). If no LLM is available at all, W2 falls back to full heuristic mode and W5.5 agents skip. Document this as a partial verification — enrichment quality cannot be assessed without LLM.
**Spec/Gate**: specs/08 section 6 (offline fallback)

### Failure mode 2: New tests from TC-1300/TC-1301 not present
**Detection**: `test_w2_priority_enrichment.py` or updated `test_llm_regen.py` don't exist.
**Resolution**: TC-1300 or TC-1301 was not completed. This is a blocker — document and stop. TC-1303 depends on all three predecessor taskcards.
**Spec/Gate**: Taskcard contract — depends_on

### Failure mode 3: Pilot exit code non-zero
**Detection**: `run_pilot.py` exits with code != 0.
**Resolution**: Check the last worker that ran. Common issues: W7 validation gate failures (may be pre-existing), W6 patching errors. Distinguish between pre-existing issues and regressions from TC-1300/1301/1302.
**Spec/Gate**: specs/21_worker_contracts.md (exit codes)

## Task-specific review checklist
1. [ ] Full test suite passes (all unit + integration)
2. [ ] 3D pilot completes with exit code 0
3. [ ] Note pilot completes with exit code 0
4. [ ] `enrichment_priority_split` event confirmed in both pilot logs
5. [ ] `enrichment_auto_offline` event does NOT appear in logs
6. [ ] `review_content_skipped` event does NOT appear in logs
7. [ ] W5.5 scores >= 4 in all dimensions for both pilots
8. [ ] LLM-enriched claims have non-empty `use_cases` (5 samples documented)
9. [ ] Heuristic-enriched claims have expected basic metadata
10. [ ] Before/after comparison table completed
11. [ ] Page count unchanged (no pages lost)
12. [ ] No new blocker/error severity issues in review_report.json

## Deliverables
- Test results output (copied to evidence)
- Pilot run logs and artifacts (in `tmp/verify-*`)
- Before/after comparison table
- PASS/FAIL verdict
- reports/agents/AGENT_C/TC-1303/evidence.md
- reports/agents/AGENT_C/TC-1303/self_review.md

## Acceptance checks
1. [ ] All tests pass
2. [ ] Both pilots complete E2E
3. [ ] W2 LLM enrichment active for high-value claims
4. [ ] W5.5 mandatory and operational
5. [ ] No score regressions below 4
6. [ ] Evidence report with before/after comparison

## Preconditions / dependencies
- TC-1300 (W2 priority enrichment) — completed
- TC-1301 (W5.5 agent implementation) — completed
- TC-1302 (mandatory enforcement) — completed
- LLM endpoint accessible (primary or fallback)

## Test plan
This IS the test plan. This taskcard's sole purpose is verification.

## Self-review
[To be completed by Agent C after verification]
