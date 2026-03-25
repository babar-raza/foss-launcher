# TC-2930 Report — Operator Triage Document

## Summary
Created `docs/OPERATOR_TRIAGE.md` — a ~2-page operator reference for fast triage of pipeline quality regressions.

## Files Changed
- **Created**: `docs/OPERATOR_TRIAGE.md` (new file)
- **Created**: `plans/taskcards/TC-2930_operator_triage_doc.md` (taskcard)
- **Created**: `reports/agents/agent_e/TC-2930/report.md` (this file)
- **Created**: `reports/agents/agent_e/TC-2930/self_review.md`

## No Code Changes
This is a documentation-only deliverable. Zero source files, tests, gates, or workers were modified.

## Document Sections
1. **Golden Invariants** — 5 rules with enforcing gates
2. **Run Directory Map** — tree view of `runs/<run_id>/`
3. **Symptom → Artifact Triage** — 10 common failures with gate, artifact, and root cause
4. **Self-Heal Loop** — W9→W10→W9 cycle with fixable/unfixable code lists
5. **Profile Severity** — local/ci/prod escalation cheat sheet

## Verification
- Artifact names cross-checked against worker source code
- Gate names cross-checked against `gates_registry.yaml`
- Worker numbering verified against `src/launch/workers/` subdirectories
- Self-heal loop description verified against `w10_fixer/worker.py`

## Commands Run
```bash
git diff --stat  # Verify only docs + taskcard + evidence files changed
```
