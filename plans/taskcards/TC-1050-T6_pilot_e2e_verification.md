# TC-1050-T6: Run Both Pilots E2E for Verification

**Status**: Complete
**Owner**: Agent-C
**Created**: 2026-02-08
**Parent**: TC-1050 W2 Intelligence Refinements
**Depends on**: TC-1050-T1, TC-1050-T2, TC-1050-T3, TC-1050-T4, TC-1050-T5

## Objective
Run both pilots end-to-end to verify no regression and all features working after TC-1050 intelligence refinements.

## Scope
- Pilots: pilot-aspose-3d-foss-python, pilot-aspose-note-foss-python
- Full test suite execution
- Quality metrics verification
- Performance benchmarking

## Acceptance Criteria
- [x] pilot-aspose-3d-foss-python: PASS, exit code 0
- [x] pilot-aspose-note-foss-python: PASS, exit code 0
- [x] Full test suite: 2582+ passed, 0 failed
- [x] Performance: Note ~7.3 min, 3D ~6 min (no regression)
- [x] Quality: 96+ classes, 357+ functions, enriched claims
- [x] Evidence bundle with timing, outputs, validation reports

## Evidence Required
- [x] Pilot execution logs with timing
- [x] Validation reports (PASS/FAIL)
- [x] Quality metrics comparison
- [x] Test suite results
- [x] 12D self-review (all dimensions >= 4/5)

## Evidence Location
- Evidence bundle: `reports/agents/agent_c/TC-1050-T6/evidence.md`
- 12D self-review: `reports/agents/agent_c/TC-1050-T6/self_review.md`
- 3D pilot run: `runs/r_20260208T113451Z_launch_pilot-aspose-3d-foss-python_3711472_default_9c5fc3b9`
- Note pilot run: `runs/r_20260208T114155Z_launch_pilot-aspose-note-foss-python_ec274a7_default_3489bec8`

## Allowed Paths
```yaml
allowed_paths:
  - scripts/run_pilot.py
  - output/**
  - runs/**
  - tests/**
  - plans/taskcards/TC-1050-T6_pilot_e2e_verification.md
  - plans/taskcards/INDEX.md
  - reports/agents/agent_c/TC-1050-T6/**
```

## Spec References
- specs/02_repo_ingestion.md
- specs/03_product_facts_and_evidence.md
- specs/30_ai_agent_governance.md

## Ruleset Version
v1.0 (specs/rulesets/ruleset.v1.yaml)
