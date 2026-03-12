---
id: GS-03
title: "Create .claude/runbooks/self-review.md — referenced by AG-020 but missing"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [healing, governance, AG-020, self-review, runbook]
depends_on: []
allowed_paths:
  - plans/healing/GS-03_create_self_review_runbook.md
  - .claude/runbooks/self-review.md
evidence_required:
  - "test -f .claude/runbooks/self-review.md && echo EXISTS"
  - "grep '13 dimensions' .claude/runbooks/self-review.md returns a match"
  - "grep 'plans/healing/' .claude/runbooks/self-review.md returns a match"
---

# Taskcard GS-03 — Create `.claude/runbooks/self-review.md`

## Gap linkage

- GS-03: `CLAUDE.md` AG-020 block references `.claude/runbooks/self-review.md`
  as its runbook, but the file does not exist. A missing runbook reference is
  a broken contract — agents that follow AG-020 will hit a dead link.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

Create `.claude/runbooks/self-review.md` with the full three-phase self-review
protocol. The file must be actionable enough that an agent reading it cold can
execute the protocol correctly without consulting any other document.

**Required content**:

```markdown
# Self-Review Protocol Runbook (AG-020)

## When to Run

After completing ANY task — code changes, documentation edits, config changes,
planning files, or analysis responses. There are no exceptions.

## Three Phases

### Phase 1: Self-Review

Score your output across 13 dimensions. For each dimension:
- Give a score 1–5 (1 = very poor, 5 = excellent and production-ready)
- Explain WHY you gave that score
- List 3–5 concrete strengths
- List 3–5 concrete weaknesses or gaps

**The 13 dimensions**:
1. Thoroughness
2. Consistency
3. Production grading
4. Systematic approach
5. Correctness & spec alignment
6. Scope & constraints adherence
7. Maintainability & readability
8. Testability & coverage
9. Robustness & failure modes
10. Performance & efficiency
11. Integration & architectural fit
12. Observability & telemetry
13. Minimality & diff quality

**Output format**: Prose with headers, or structured YAML block.
Any score < 4 on a dimension MUST generate at least one healing taskcard.

---

### Phase 2: Healing Plan

Convert every gap/blocker identified in Phase 1 into an executable taskcard.

Rules:
- Every gap maps to ≥1 taskcard (no orphaned gaps)
- Write taskcards to `plans/healing/` using a stable ID prefix
  (e.g., DM-01 for doc maintenance, GS-01 for governance structure, etc.)
- If a gap index file does not exist for this series, create one
  (`GS-00-...gap-index.md`, `DM-00-...gap-index.md`)
- Each taskcard must include: Status, Gap linkage, Role, Scope, Acceptance
  checks, Deliverables, Hard rules, Review dimensions, Now (runbook)
- Protected paths (src/launcher/**, configs/**, specs/schemas/**,
  CLAUDE.md, specs/governance.md, .claude_code_rules) require explicit
  user authorization — mark those taskcards Blocked until authorized

**Severity triage**:
| Score | Action |
|-------|--------|
| 1–2 | Immediate taskcard; execute in current session if possible |
| 3 | Taskcard required; execute if scope is small |
| 4 | Taskcard optional; execute only if blocking future work |
| 5 | No taskcard needed |

---

### Phase 3: Execute

Run the highest-priority healing taskcards in the current session.

Priority order:
1. Correctness bugs (exit-code wrong, data lost, security hole)
2. Structural breaks (section structure, import errors, schema violations)
3. Missing required artifacts (runbooks, governance propagation)
4. Coverage gaps (missing tests for new code)
5. Process improvements (tooling, observability)

**After execution**:
- Set each completed taskcard to `status: Done`
- Update the gap index Status Summary table
- Run a final verification command per taskcard

---

## Verification After Phase 3

Before declaring the self-review cycle complete:
```bash
# Confirm all executed taskcards are Done
grep "^status:" plans/healing/GS-*.md plans/healing/DM-*.md 2>/dev/null | grep -v "Done\|Not Started\|Blocked"
# Expected: no output (no In-Progress tasks left)
```

---

## Common Mistakes

- **Skipping Phase 2 when all scores are ≥4**: Still required if any score is
  exactly 4 and the gap blocks future work.
- **Writing taskcards to plans/taskcards/ instead of plans/healing/**: Healing
  taskcards go to `plans/healing/`. Project taskcards go to `plans/taskcards/`.
- **Creating healing taskcards for out-of-scope improvements**: A healing
  taskcard fixes a defect in the work just completed. It is not a feature backlog.
- **Marking a taskcard Done without running the acceptance checks**: The CLI
  verification commands in the `Acceptance checks` section are mandatory.
- **Re-reading the plan file instead of the actual output**: Phase 1 reviews
  what was *delivered* (the files on disk), not what was *planned*.
```

### Allowed paths

- `.claude/runbooks/self-review.md` (new file)

### Forbidden

Any file outside `.claude/runbooks/self-review.md` and this plan file.

---

## Acceptance checks

### CLI

```bash
# File exists
test -f .claude/runbooks/self-review.md && echo "EXISTS" || echo "MISSING"
# Expected: EXISTS

# Contains the 13 dimensions
grep -c "Thoroughness\|Consistency\|Production grading\|Systematic approach\|Correctness\|Scope.*constraints\|Maintainability\|Testability\|Robustness\|Performance\|Integration.*architectural\|Observability\|Minimality" .claude/runbooks/self-review.md
# Expected: 13

# References plans/healing/
grep "plans/healing/" .claude/runbooks/self-review.md
# Expected: at least 2 matches

# References protected paths warning
grep "protected" .claude/runbooks/self-review.md
# Expected: at least 1 match (the Blocked authorization note)
```

### UI/Web/API

N/A — runbook file only.

### Tests

No automated tests. CLI checks above are the verification mechanism.

### Config respected end-to-end

After this taskcard, the reference chain is complete:
`CLAUDE.md` → `.claude/runbooks/self-review.md` (exists) → `plans/healing/` (exists).

### No mock data in production paths

N/A.

---

## Deliverables

1. **New file `.claude/runbooks/self-review.md`** — fully written, actionable
   runbook covering all three phases with concrete instructions, severity triage
   table, and common-mistakes section. No stubs, no TODOs.

---

## Hard rules

- The 13 dimension names must exactly match those used in the self-review
  prompts in this codebase (as established by repeated use in this session)
- The three phases must be named exactly: Self-Review, Healing Plan, Execute
- The runbook must not reference any external URLs
- The runbook must be self-contained — an agent reading it without prior
  context must be able to execute the protocol

---

## Review dimensions (what 5/5 means for GS-03)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Completeness | All three phases documented with concrete action steps |
| Correctness | 13 dimensions listed match exactly the names used in session |
| Actionability | An agent reading cold can execute Phase 1 without consulting other docs |
| Scope adherence | Only `.claude/runbooks/self-review.md` created |
| Broken-link closure | `CLAUDE.md` reference to this file now resolves |

---

## Now (runbook)

```bash
# Step 1: Confirm .claude/runbooks/ directory exists
ls .claude/runbooks/
# Expected: taskcards.md (and possibly others)

# Step 2: Confirm the file doesn't already exist
test -f .claude/runbooks/self-review.md && echo "EXISTS" || echo "MISSING"
# Expected: MISSING

# Step 3: Write .claude/runbooks/self-review.md with full content per Deliverables above

# Step 4: Verify
grep -c "Thoroughness\|Consistency\|Production grading" .claude/runbooks/self-review.md
# Expected: >= 3 (confirming dimension names present)

test -f .claude/runbooks/self-review.md && echo "EXISTS"
# Expected: EXISTS
```
