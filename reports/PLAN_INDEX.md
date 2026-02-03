# Plan Index

**Purpose:** Track all execution plans (chat-derived and repo-based) for orchestrator runs

**Last Updated:** 2026-02-03

---

## Active Plans

| Path | Type | Why Selected | Key Sections | Selected As Primary | Status |
|------|------|--------------|--------------|---------------------|--------|
| `plans/healing/url_generation_and_cross_links_fix.md` | Healing plan (architectural fixes) | User approved execution of 4 critical bug fixes blocking pilot validation | Bug Analysis (4 bugs), Implementation Strategy (6 phases), Test Plans | ✅ YES | IN_PROGRESS |
| `C:\Users\prora\.claude\plans\linear-beaming-plum.md` | Plan mode approved plan | User approved after 5-agent analysis (3 Explore + 2 Plan agents) - strengthens 3 governance gates | Executive Summary, 3 Phases, Implementation Sequence, Verification Steps | ⏸️ PAUSED | PAUSED |

---

## Taskcard Traceability

**Healing Sprint (2026-02-03):**

| Taskcard | Plan Source | Status | Evidence | Agent | Quality |
|----------|-------------|--------|----------|-------|---------|
| TC-957 | plans/healing (Bug #4) | ✅ COMPLETE | reports/agents/AGENT_B/HEAL-BUG4/run_20260203_215544/ | Agent B | 5.0/5 |
| TC-958 | plans/healing (Bug #1) | ✅ COMPLETE | reports/agents/AGENT_B/HEAL-BUG1/run_20260203_215837/ | Agent B | 4.92/5 |
| TC-959 | plans/healing (Bug #2) | ✅ COMPLETE | reports/agents/AGENT_B/HEAL-BUG2/run_20260203_220814/ | Agent B | 5.0/5 |
| TC-960 | plans/healing (Bug #3) | ✅ COMPLETE | reports/agents/AGENT_B/HEAL-BUG3/run_20260203_215617/ | Agent B | 5.0/5 |

---

## Secondary Sources

| Path | Type | Purpose | Used By Plan |
|------|------|---------|--------------|
| `reports/pre_impl_verification/20260127-1724/HEALING_PROMPT.md` | Verification report | Gap remediation guidance with detailed proposed fixes | 20260127_preimpl_hardening_spec_gaps |
| `reports/pre_impl_verification/20260127-1724/GAPS.md` | Gap catalog | Full gap details with file:line citations | 20260127_preimpl_hardening_spec_gaps |
| `reports/pre_impl_verification/20260127-1724/INDEX.md` | Navigation index | Links to all verification outputs | 20260127_preimpl_hardening_spec_gaps |

---

## Historical Plans

| Path | Type | Completed | Outcome | Key Results |
|------|------|-----------|---------|-------------|
| `plans/from_chat/20260127_preimpl_hardening_spec_gaps.md` | Chat-derived hardening plan | 2026-01-27 | ✅ SUCCESS | Fixed 12 spec-level BLOCKER gaps without implementation |
| `plans/from_chat/20260203_taskcard_validation_prevention.md` | Chat-derived prevention system | 2026-02-03 | ✅ SUCCESS | 4-layer defense system deployed (WS1-WS5 complete, all agents scored 4.65-5.0/5.0) |
| `plans/from_chat/20260203_taskcard_remediation_74_incomplete.md` | Chat-derived remediation plan | 2026-02-03 | ✅ SUCCESS | Fixed 79 taskcards via 4 agents in parallel, achieved 100% validation compliance (8/82 → 86/86, overall score 4.46/5.0) |

---

## Notes

- Chat-derived plans are created in `plans/from_chat/` when user messages contain substantial actionable content
- Repo-based plans are existing files in `plans/` directory
- Primary plan is the main execution source; secondary sources provide supporting detail
- Plans must have: Context, Goals, Steps, Acceptance Criteria, Evidence Commands
- Incomplete plans should be hardened before execution
