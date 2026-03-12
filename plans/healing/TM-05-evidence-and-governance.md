---
id: TM-05
title: "Telemetry API: Create evidence file for TC-3796"
status: Not Started
priority: Medium
owner: unassigned
updated: "2026-03-07"
tags: [healing, telemetry-api, governance]
depends_on: [TM-01, TM-03]
allowed_paths:
  - plans/healing/TM-05-evidence-and-governance.md
  - reports/agents/telemetry/TC-3796/evidence.md
evidence_required:
  - reports/healing/TM-05/evidence.md
---

# Taskcard TM-05 — Create Evidence File for TC-3796

## Status: Not Started

## Gap linkage
- **G-TM-14**: TC-3796 taskcard frontmatter declares `evidence_required: reports/agents/telemetry/TC-3796/evidence.md` but the file was never created. This violates the governance protocol requiring evidence artifacts for completed taskcards.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix:
Create `reports/agents/telemetry/TC-3796/evidence.md` containing:
1. Summary of what was ported (7 files, line counts)
2. Test results (22/22 pass, plus any additional from TM-03)
3. Full regression suite result (1545 passed, 0 failed)
4. Import rename verification (no remaining `launch.` references)
5. Endpoint inventory: list each endpoint, HTTP method, and test coverage status
6. Spec alignment notes (from TM-01 audit)
7. Known remaining limitations (if any)

### Allowed paths:
- `plans/healing/TM-05-evidence-and-governance.md`
- `reports/agents/telemetry/TC-3796/evidence.md`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
- File exists at `reports/agents/telemetry/TC-3796/evidence.md`
- File is valid Markdown

### UI/Web/API:
- N/A

### Tests:
- N/A (documentation artifact)

### Config respected end-to-end:
- Evidence path matches TC-3796 taskcard frontmatter `evidence_required` field exactly

### No mock data in production paths:
- Evidence contains actual test output, not fabricated numbers

## Deliverables
- `reports/agents/telemetry/TC-3796/evidence.md` — complete evidence file
- Full file (no stubs, no TODOs)

## Hard rules
- Evidence must reflect actual state of code at time of writing
- Test counts must come from actual `pytest` output (not guessed)
- Run `grep -r "from launch\." src/launcher/telemetry_api/` to prove no stale imports
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | All 7 sections listed above present |
| Consistency | Evidence format matches other evidence files in reports/ |
| Production grading | Auditor can verify claims by re-running listed commands |
| Systematic approach | Each claim backed by a command or file reference |
| Correctness & spec alignment | Spec audit section present and honest about gaps |
| Scope & constraints | Only evidence file created |
| Maintainability | Self-contained — doesn't reference transient state |
| Testability | Commands are copy-pasteable for verification |
| Robustness | N/A |
| Performance | N/A |
| Integration | Path matches taskcard frontmatter exactly |
| Observability | N/A |
| Minimality | Single file, no extras |

## Now (runbook)

```bash
# 1. Create directory
mkdir -p reports/agents/telemetry/TC-3796

# 2. Gather evidence data
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/ -v 2>&1 | tee /tmp/tm05_api_tests.txt
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q 2>&1 | tail -5
grep -r "from launch\." src/launcher/telemetry_api/ || echo "No stale imports found"
wc -l src/launcher/telemetry_api/*.py src/launcher/telemetry_api/routes/*.py

# 3. Write evidence.md with gathered data

# 4. Verify file exists and is valid
cat reports/agents/telemetry/TC-3796/evidence.md | head -5
```
