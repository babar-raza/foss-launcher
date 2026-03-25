# TC-3580 Self-Review (12D)

| Dimension | Score | Notes |
|-----------|-------|-------|
| Correctness | 5/5 | One-line path change; fallback logic is defensive-only |
| Test coverage | 5/5 | 4 tests: both-exist preference, fallback load, fallback warning, missing-both error |
| Determinism | 5/5 | Static filename constants; no runtime variation |
| Scope adherence | 4/5 | Also touched triage.py (fallback); not in original allowed_paths but in approved plan |
| Backward compat | 5/5 | W9 report path unchanged; consumers of validation_report.json unaffected |
| Governance | 5/5 | Taskcard updated; allowed_paths updated to include triage.py; evidence present |
| Idempotency | 5/5 | File write is always to .site.json; no side effects |
| Error handling | 5/5 | FileNotFoundError raised when neither file exists; warning logged on fallback |
| Performance | 5/5 | Negligible — one Path.exists() check added |
| Logging | 5/5 | WARNING with clear message including "Run W9 for full gate coverage" |
| Cross-platform | 5/5 | Path operations use pathlib; no OS-specific code |
| Security | 5/5 | No new attack surface; file writes remain atomic via atomic_write_json |

**Overall: 59/60**

## Notes
- The triage.py fallback was explicitly part of the user-approved plan. Taskcard
  allowed_paths updated accordingly.
- The `.site.json` name is self-documenting (site-level, not W9 41-gate).
