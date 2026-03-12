# Chat-Derived Plan: MP Healing Execution

**Extracted**: 2026-03-08 20:00:00 UTC
**Source**: Orchestrator Protocol invocation on MP-00..MP-16 healing taskcards
**Slug**: mp-healing-execution

## Context

The previous assistant turn created 16 healing taskcards (MP-01..MP-16) targeting gaps
in `plans/twinkly-puzzling-minsky.md` (the v2 architecture plan). This plan materializes
the execution of those taskcards as an orchestrated sequence of file edits, spec file
creations, and infrastructure updates.

## Goals

1. Patch `plans/twinkly-puzzling-minsky.md` with all 16 MP gap fixes.
2. Update `CLAUDE.md` for the phase count fix (MP-09).
3. Create 6 new spec files under `specs/` (non-schema, non-protected path).
4. Update all infrastructure files (PLAN_SOURCES, PLAN_INDEX, TASK_BACKLOG, STATUS).
5. Achieve self-review score ≥ 4/5 on all 12 dimensions.

## Assumptions (UNVERIFIED until verified)

- [VERIFIED] `plans/twinkly-puzzling-minsky.md` is 1416 lines (confirmed by wc -l)
- [VERIFIED] `reports/` directory exists with PLAN_SOURCES.md, PLAN_INDEX.md
- [VERIFIED] `specs/` directory exists (unprotected path, no taskcard needed)
- [UNVERIFIED] All 6 spec files listed in the plan do not yet exist under `specs/`
- [UNVERIFIED] The string "Worker 1:" currently appears in the plan file

## Steps

1. Write infrastructure files (PLAN_SOURCES, PLAN_INDEX, TASK_BACKLOG, from_chat plan)
2. Execute MP-07+08+09+10+16 — consistency fixes (plan + CLAUDE.md)
3. Execute MP-01+02+03+04+05+06 — architecture definitions (plan + spec files)
4. Execute MP-11+12+13+14+15 — implementation guidance (plan + toolchain spec)
5. Update taskcard statuses in healing plan files to "Done"
6. Self-review, update STATUS.md + CHANGELOG.md

## Acceptance Criteria

- `grep "Worker [1-4]" plans/twinkly-puzzling-minsky.md | grep -v "v1\|W1\|W2\|W3\|W4"` → 0 results
- `grep '"understanding\.json"' plans/twinkly-puzzling-minsky.md` → 0 results
- `grep "Canonical Naming Reference" plans/twinkly-puzzling-minsky.md` → 1 result
- `grep "SelfReviewResult" plans/twinkly-puzzling-minsky.md | wc -l` → ≥ 3
- `grep "PipelineState" plans/twinkly-puzzling-minsky.md | wc -l` → ≥ 2
- `grep "4 internal phases" CLAUDE.md` → 0 results
- `ls specs/*.md | wc -l` → ≥ 6 spec files exist
- `grep "escalation.json" plans/twinkly-puzzling-minsky.md | wc -l` → ≥ 3
- `grep "UNDERSTAND_CLONE_FAILED" plans/twinkly-puzzling-minsky.md` → 1 result

## Risks + Rollback

- Risk: Large file edits to twinkly-puzzling-minsky.md may corrupt sections.
  Rollback: `git checkout HEAD -- plans/twinkly-puzzling-minsky.md`
- Risk: Spec files may conflict with future actual implementations.
  Mitigation: All spec files are `specs/*.md` (non-schema, non-protected).

## Evidence Commands

```bash
# After all edits:
grep -c "understanding_bundle\.json" plans/twinkly-puzzling-minsky.md
grep -c "Canonical Naming Reference" plans/twinkly-puzzling-minsky.md
grep -c "SelfReviewResult" plans/twinkly-puzzling-minsky.md
grep -c "PipelineState" plans/twinkly-puzzling-minsky.md
grep "4 internal phases" CLAUDE.md | wc -l
ls specs/*.md
grep -c "escalation.json" plans/twinkly-puzzling-minsky.md
grep -c "UNDERSTAND_CLONE_FAILED" plans/twinkly-puzzling-minsky.md
grep "Worker [1-4]" plans/twinkly-puzzling-minsky.md | grep -v "v1\|W1\|W2\|W3\|W4" | wc -l
```

## Open Questions

(none — all gaps have concrete fixes in MP taskcards)
