# Plan Index

**Purpose:** Track all execution plans (chat-derived and repo-based) for orchestrator runs

**Last Updated:** 2026-01-27

---

## Active Plans

| Path | Type | Why Selected | Key Sections | Selected As Primary | Status |
|------|------|--------------|--------------|---------------------|--------|
| `plans/from_chat/20260127_preimpl_hardening_spec_gaps.md` | Chat-derived hardening plan | User requested "fix gaps that do not need implementation" - focuses on 12 spec-level BLOCKER gaps | Context, Goals, Steps (4 phases), Acceptance Criteria, Evidence Commands | ✅ YES | READY FOR EXECUTION |

---

## Secondary Sources

| Path | Type | Purpose | Used By Plan |
|------|------|---------|--------------|
| `reports/pre_impl_verification/20260127-1724/HEALING_PROMPT.md` | Verification report | Gap remediation guidance with detailed proposed fixes | 20260127_preimpl_hardening_spec_gaps |
| `reports/pre_impl_verification/20260127-1724/GAPS.md` | Gap catalog | Full gap details with file:line citations | 20260127_preimpl_hardening_spec_gaps |
| `reports/pre_impl_verification/20260127-1724/INDEX.md` | Navigation index | Links to all verification outputs | 20260127_preimpl_hardening_spec_gaps |

---

## Historical Plans

_(Plans will be archived here when completed)_

---

## Notes

- Chat-derived plans are created in `plans/from_chat/` when user messages contain substantial actionable content
- Repo-based plans are existing files in `plans/` directory
- Primary plan is the main execution source; secondary sources provide supporting detail
- Plans must have: Context, Goals, Steps, Acceptance Criteria, Evidence Commands
- Incomplete plans should be hardened before execution
