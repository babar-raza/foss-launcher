# AH-06 — Process Safeguard: Read Before Overwrite

**Context**: G-12 — During the original `agents.md` authoring session, the
file already existed as an untracked file (`??` in git status) but was
overwritten without being read first. This is a data safety violation.
The `agents.md` file itself is the correct place to document this
read-before-overwrite discipline so that future agents apply it consistently.

Additionally, the "Common Mistakes" section (Section 13) should be updated
to include this pattern, and the mental model (Section 0) should note that
untracked files may carry pre-existing content.

This taskcard also addresses the missing guidance on **how to verify a file
is truly new vs. pre-existing untracked** before writing — a gap that affects
any file, not just `agents.md`.

---

## Taskcard AH-06

**Status**: Done
**Gap linkage**: G-12 (read-before-overwrite not documented)
**Role**: Senior engineer. Drop-in, production-ready additions to `agents.md`.

---

### Scope

**Fix**:
1. Add a "Pre-write checklist" to Section 1 ("Before Writing Any Code")
   that applies to ALL file writes — not just protected-path writes.
2. Add one entry to the "Common Mistakes" list in Section 13.
3. Add a short note to the mental model (Section 0) about untracked files.

**Allowed paths**:
- `agents.md`
- `plans/healing/AH-06-process-safeguard.md`

**Forbidden**: any file under `src/launcher/**`, `configs/**`, `specs/**`,
`tests/**`.

---

### Acceptance checks

**CLI**:
```bash
# Verify the new checklist appears in Section 1
grep -n "untracked\|read before\|git status\|??" agents.md

# Verify Common Mistakes updated
grep -n "overwrite\|pre-existing" agents.md
```

**UI/Web/API**: N/A.

**Tests**:
- Manual: follow the "Pre-write checklist" for a file that appears as `??`
  in `git status` — the checklist correctly directs the agent to read the
  file before writing.
- `python scripts/check_doc_freshness.py --since HEAD~1` exits 0.

**Config respected end-to-end**: N/A.

**No mock data**: All examples use real git commands.

---

### Deliverables

**1. Pre-write checklist addition to Section 1**

After the existing "**Checklist (run mentally before every file write):**"
block in Section 1, add:

```markdown
**Pre-write safety check (applies to ALL files, not just protected paths):**

Before creating or overwriting ANY file:
1. Check `git status` — does the file appear as `??` (untracked)?
   If yes, it may have pre-existing content from a prior session or tool.
2. If `??` — **read the file first** before writing. Never overwrite a
   `??` file without reading it.
3. If the file exists but you were not the one who created it — inspect
   it and preserve relevant content.

```bash
# Check if a file is new vs. pre-existing untracked
git status agents.md
# "?? agents.md"  → pre-existing untracked — READ FIRST
# nothing shown   → tracked and unmodified — safe to write

# Read it before writing
cat agents.md         # or use the Read tool
```

This prevents silent data loss when a file exists untracked in the
working tree (e.g., created by a previous conversation session, a
scaffold script, or a manual edit that was never committed).
```

**2. Common Mistakes entry (Section 13)**

Add as the last bullet in Section 13:

```markdown
- Overwriting an untracked file (`??` in `git status`) without reading
  it first — always `git status` + read before any file write, not just
  for protected paths (see Section 1 Pre-write safety check)
```

**3. Mental model note (Section 0)**

After the mental model diagram in Section 0, add:

```markdown
> **Note on untracked files**: Files listed as `??` in `git status` are
> untracked but may contain pre-existing content from previous sessions,
> scaffold scripts, or manual work. Always read `??` files before writing
> to them — never assume they are empty.
```

---

### Hard rules

- No new deps — N/A.
- Keep code/docs/tests in sync — this is the sync step for the process gap.
- Deterministic — N/A.

---

### Review dimensions (5/5 criteria)

| Dimension | 5/5 means for AH-06 |
|-----------|---------------------|
| Thoroughness | All three insertion points addressed (Section 0, Section 1, Section 13); git status command provided |
| Consistency | Consistent with Section 1's existing "protected path checklist" pattern — same visual style, same mental model |
| Production grading | Prevents the exact data-loss scenario that occurred during the original authoring session |
| Systematic approach | Placed at the earliest possible point in the agent's decision flow (Section 0 = first thing read) |
| Correctness & spec alignment | `git status` `??` notation is the standard git untracked file marker — accurate |
| Scope & constraints adherence | Only three targeted additions to agents.md |
| Maintainability & readability | Pre-write checklist uses same numbered-list format as the existing protected-paths checklist |
| Testability & coverage | The checklist is procedurally testable: run `git status` on any `??` file and follow the steps |
| Robustness & failure modes | Explicitly handles the "file appears empty but has content" case (untracked files are silent) |
| Performance & efficiency | N/A — one `git status` call, negligible cost |
| Integration & architectural fit | Placed in Section 1 (the "before writing" section) — exactly the right location |
| Observability & telemetry | N/A |
| Minimality & diff quality | Three small additions; no changes to existing content |

---

### Now (runbook)

```bash
# 1. Verify agents.md is the correct file to add process guidance to
#    (it is — CLAUDE.md points to agents.md for operational guidance)
grep -n "agents.md" CLAUDE.md

# 2. Find the exact insertion points in agents.md
grep -n "## 0. Mental Model\|Before Writing Any Code\|## 13\." agents.md

# 3. Insert the three content blocks at their insertion points

# 4. Verify all three insertions appear
grep -n "untracked\|Pre-write\|??\|overwriting an untracked" agents.md

# 5. Run freshness check
python scripts/check_doc_freshness.py --since HEAD~1

# 6. Commit
git add agents.md
git commit -m "docs(AH-06): add read-before-overwrite process safeguard"
```
