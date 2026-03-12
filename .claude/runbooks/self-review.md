# runbooks/self-review.md (FOSS Launcher v2)

Run this **after completing any task** in this repository.

Aligned to: `.claude_code_rules` (AG-020), `CLAUDE.md` (Self-Review After Every Task)

---

## Phase 1 — Self-Review

You are reviewing your own last output. Be honest and critical. Assume a senior
engineer will read this review to decide whether to trust your outputs in production.

### Review dimensions (score each 1–5)

| # | Dimension | 1 = very poor → 5 = excellent |
|---|-----------|-------------------------------|
| 1 | Thoroughness | All requirements, edge cases, and details covered |
| 2 | Consistency | Internally consistent; aligned with prior constraints |
| 3 | Production grading | Suitable for real-world production use as-is |
| 4 | Systematic approach | Methodical and structured reasoning and output |
| 5 | Correctness & spec alignment | Matches spec and examples exactly |
| 6 | Scope & constraints adherence | Stayed within allowed scope and paths |
| 7 | Maintainability & readability | Another engineer can understand and maintain this |
| 8 | Testability & coverage | Key paths are clearly testable; tests exist or are specified |
| 9 | Robustness & failure modes | Handles bad inputs, errors, and edge cases |
| 10 | Performance & efficiency | No obvious performance pitfalls for realistic workloads |
| 11 | Integration & architectural fit | Fits existing architecture, patterns, and helpers |
| 12 | Observability & telemetry | Logs/metrics sufficient for production debugging |
| 13 | Minimality & diff quality | Change is focused, tidy, free of unnecessary noise |
| 14 | Documentation completeness | Relevant guide in `docs/guides/` updated per ownership map in `docs/README.md` |

### Required output format

```
## Self-Review

### Brief Recap
[3–5 sentences: what you did, the main deliverable, and who it is for]

### Dimension Scores
| Dimension | Score | Why |
|-----------|:-----:|-----|
| Thoroughness | N/5 | [1–2 sentences] |
| Consistency | N/5 | ... |
| Production grading | N/5 | ... |
| Systematic approach | N/5 | ... |
| Correctness & spec alignment | N/5 | ... |
| Scope & constraints adherence | N/5 | ... |
| Maintainability & readability | N/5 | ... |
| Testability & coverage | N/5 | ... |
| Robustness & failure modes | N/5 | ... |
| Performance & efficiency | N/5 | ... |
| Integration & architectural fit | N/5 | ... |
| Observability & telemetry | N/5 | ... |
| Minimality & diff quality | N/5 | ... |
| Documentation completeness | N/5 | ... |

### Gaps and Risks
- [Bullet: requirement partially met, missing edge case, or production risk]

### Top 5 Improvements
1. [What to change + which dimension(s) it improves]
2. ...

### Final Verdict
[2–4 sentences: safe to use as-is, OR draft that needs revision before real use?]
```

---

## Phase 2 — Healing Plan

Convert EVERY meaningful gap/blocker from Phase 1 into executable taskcards.
Write the plan to `plans/healing/<slug>.md`.

### File format

```markdown
# Healing Plan: <descriptive title>

Generated: <date>
Source task: <brief description>

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-01 | [Gap from self-review] | SR-01 |

---

## Taskcards

### SR-01 — <title>

**Status**: Not Started
**Gap linkage**: G-01
**Role**: Senior engineer. Drop-in, production-ready.

#### Scope
- Fix: [exactly what to fix]
- Allowed paths: [specific files/dirs — not wildcards]
- Forbidden: any file/path not listed above

#### Acceptance checks
- [ ] CLI: [command + expected output]
- [ ] Tests: [test file + expected pass count]
- [ ] Config respected end-to-end
- [ ] No mock data in production paths
- [ ] Regression path covered

#### Deliverables
- Full file replacements for changed files (no stubs, no TODOs)
- New/updated tests: happy path + at least one failure/regression path
- If contracts/schemas change: forward-compatible migration included

#### Hard rules
- Keep public signatures unless justified; update all call sites
- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0) where needed
- No new deps without explicit justification
- Keep code/docs/tests in sync

#### Review dimensions (what 5/5 means for this taskcard)
| Dimension | 5/5 criterion |
|-----------|--------------|
| Correctness & spec alignment | [specific criterion] |
| Robustness & failure modes | [specific criterion] |
| Testability & coverage | [specific criterion] |

#### Now (runbook)
1. [Step 1 command]
2. [Step 2 command]
3. [Validation command]
```

### Taskcard ID prefixes

| Prefix | Gap type |
|--------|----------|
| `SR-NN` | Self-review / general quality gap |
| `TM-NN` | Testability / coverage gap |
| `OB-NN` | Observability / telemetry gap |
| `PF-NN` | Performance gap |
| `RB-NN` | Robustness / failure-mode gap |
| `SC-NN` | Scope / constraint violation |

### Gate still applies

Healing plan taskcards are **proposals only**. Before writing any code to
protected paths (`src/launcher/**`, `configs/**`, `specs/schemas/**`), you
MUST still create a proper `plans/taskcards/TC-NNNN_*.md` per AG-002.
The healing plan fast-tracks gap identification; the taskcard gate stands.

### Machine-readable footer (must be last in your Phase 2 output)

```yaml
plan_files:
  - path: plans/healing/<file>.md
    taskcards: [SR-01, SR-02]
```

---

## Phase 3 — Execute

Parse the `plan_files:` YAML from Phase 2. Execute 1–3 highest-impact
taskcards. Respect dependencies (do not start a taskcard whose upstream is
Not Started).

### Execution rules

- Set `Status: In Progress` in the healing plan file before starting each item
- Implement exactly what the taskcard says — no scope creep
- Add/update tests per taskcard requirements
- Set `Status: Done` or `Status: Blocked` (with 1-line reason) when finished
- Tick checklist items in the file as you complete them

### Per-taskcard output

```
### [ID] <title> — EXECUTED
Files changed: [brief list]
Runbook: [1–3 commands]
Mini self-check: [1–3 lines on correctness, scope, tests]
```

### End-of-pass summary

- List all taskcards touched with final status (Done / Blocked)
- Confirm healing plan files were updated on disk
- If ALL gaps Done → declare Phase 3 complete; proceed to marking the original
  taskcard Done (if one is active)
- If any gaps Blocked → surface the blocker to the user before proceeding

---

## Decision tree

```
Task complete
  |
  +-- Phase 1: Self-Review
  |     Score all 14 dimensions
  |     Identify gaps and risks
  |
  +-- Any gaps? ─── NO ──> note "No healing items" and stop
  |
  +-- YES
  |
  +-- Phase 2: Healing Plan
  |     Write plans/healing/<slug>.md
  |     Output plan_files: YAML block
  |
  +-- Phase 3: Execute
        Select 1–3 highest-impact taskcards
        Implement + test + update status in plan file
        Report outcomes
```
