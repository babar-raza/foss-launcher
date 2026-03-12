# Quality Sprint Self-Review — Gap Index
# Source: Self-review of TC-4040/4041/4042/4043 (Understand/Generate Quality Sprint)
# Date: 2026-03-11

## Gap Table

| Gap ID | Severity | Description | Taskcard(s) | File |
|--------|----------|-------------|-------------|------|
| G-01 | CRITICAL | Zero new tests for TC-4040: `supported_formats` wiring has no unit coverage | QSR-01 | QSR-test-coverage.md |
| G-02 | CRITICAL | Zero new tests for TC-4041: workflow_examples + format_matrix injection has no unit coverage | QSR-02 | QSR-test-coverage.md |
| G-03 | HIGH | No integration test for 5-hop evidence chain (_format_matrix → ProductEvidence → merge → generate → prompt) | QSR-03 | QSR-test-coverage.md |
| G-04 | HIGH | `_FORMAT_ELIGIBLE_ROLES` set defined inside `build_section_prompt()` — evaluated on every call; not a module-level constant | QSR-04 | QSR-code-quality.md |
| G-05 | HIGH | No telemetry when workflow_examples/format_matrix injection fires — undebuggable in production | QSR-05 | QSR-code-quality.md |
| G-06 | MEDIUM | `supported_formats` passed as plain `dict[str, list[str]]`; all other evidence types are typed Pydantic models — breaks type system | QSR-06 | QSR-code-quality.md |
| G-07 | MEDIUM | TASK_BACKLOG.md TC-4040–4043 still show ACTIVE/NEXT/QUEUED; taskcard self-review sections unfilled; CHANGELOG.md not updated | QSR-07 | QSR-compliance.md |
| G-08 | HIGH | Pre-Flight Checks 1–3 never run: heal loop config unverified, FK backtick stripping unverified — could silently neutralize TC-4043 | QSR-08 | QSR-compliance.md |
| G-09 | MEDIUM | TC-4042 allowed_paths lists wrong test file path (test_api_surface.py vs test_extract.py); TS import fix decision undocumented | QSR-09 | QSR-compliance.md |

## Priority Order

1. QSR-01 (G-01) + QSR-02 (G-02) — test coverage: no safety net for new code paths
2. QSR-08 (G-08) — pre-flight: unverified assumptions may silently block grade improvement
3. QSR-05 (G-05) — telemetry: required for production debugging
4. QSR-04 (G-04) — code quality: perf/maintainability
5. QSR-03 (G-03) — integration test: valuable but lower urgency once unit tests pass
6. QSR-06 (G-06) — type consistency: important but non-breaking
7. QSR-07 (G-07) + QSR-09 (G-09) — compliance: bookkeeping, no functional risk

## Files

- `plans/healing/QSR-test-coverage.md` — QSR-01, QSR-02, QSR-03
- `plans/healing/QSR-code-quality.md` — QSR-04, QSR-05, QSR-06
- `plans/healing/QSR-compliance.md` — QSR-07, QSR-08, QSR-09
