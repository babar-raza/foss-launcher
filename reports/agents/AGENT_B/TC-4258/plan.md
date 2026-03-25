# AGENT_B Plan: TC-4258

## Phase

Understand only, after Scout is resolved.

## Assumptions To Verify

- Orphaned snippet linkage remains reproducible on Note.
- Evidence sufficiency still overstates weak page inputs.
- Targeted non-Python extractor tests still fail.

## Steps

1. Reconfirm Understand defects in code, tests, and baseline artifacts.
2. Implement root-cause fixes under TC-4258 authorization.
3. Add or update regression tests for each repaired defect.
4. Rerun Understand pilots on Cells and Note.
5. Manually inspect checkpoint, bundle, summary, audit files, and logs.
6. Repeat until Understand is sufficient or further work is not justified.

## Rollback

Reject any round that weakens self-review, hides bad evidence, or relies on prompt-only suppression instead of evidence-pipeline fixes.

## Tests

- `$env:PYTHONHASHSEED='0'; .venv\\Scripts\\python.exe -m pytest tests\\unit\\workers\\test_understand.py -q`
- Additional focused tests added under TC-4258

## Acceptance Checklist

- [ ] Orphaned snippet rate is justified or eliminated
- [ ] Evidence richness/sufficiency is credible
- [ ] Targeted extractor regressions pass
- [ ] Fresh Cells Understand output manually inspected
- [ ] Fresh Note Understand output manually inspected
- [ ] Self-review passes for the right reasons
