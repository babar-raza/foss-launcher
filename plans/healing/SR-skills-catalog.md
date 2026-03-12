# Healing Plan: Skills Catalog Self-Review Gaps

**Context**: Self-review of `skills_catalog.md` + `docs/usage/skills.md` identified
six dimensions below 4/5. The root causes are three concrete gaps: dangling file
references, missing escalation rules in operator skill definitions, and unverified
cross-references.

---

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| GAP-01 | `skills/prompts/` directory and operator skill prompt files do not exist; referenced in Migration Step 3 | SR-01 |
| GAP-02 | 8 of 10 operator skills are missing "Escalation Rules" subsections despite catalog format claiming it is required | SR-02 |
| GAP-03 | Cross-references in catalog and usage guide not verified; some cited paths may not exist | SR-03 |

---

## SR-01 — Create operator skill prompt files

**Status**: Done
**Gap linkage**: GAP-01
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

Fix: Create `skills/prompts/` directory and one prompt file per operator skill
(SKL-201 through SKL-210). Each file is a reusable agent prompt template derived
from the skill definitions in `skills_catalog.md`.

Allowed paths:
- `skills/prompts/skl201_understand_audit.md`
- `skills/prompts/skl202_understand_flow_audit.md`
- `skills/prompts/skl203_multi_plan_consolidate.md`
- `skills/prompts/skl204_content_complete.md`
- `skills/prompts/skl205_pipeline_concern_reverify.md`
- `skills/prompts/skl206_phase_store_diagnose.md`
- `skills/prompts/skl207_hallucination_reduce.md`
- `skills/prompts/skl208_cache_rename_backfill.md`
- `skills/prompts/skl209_concern_resolve.md`
- `skills/prompts/skl210_thin_family_expand.md`

Forbidden paths: any file under `src/launcher/`, `configs/`, `specs/schemas/`

### Acceptance checks

- [ ] All 10 prompt files exist under `skills/prompts/`
- [ ] Each file can be used as a standalone agent prompt (contains all required inputs, expected outputs, constraints, and verification steps)
- [ ] `skills_catalog.md` migration step 3 cross-reference resolves to an existing file
- [ ] Each file name matches the pattern `skl{NNN}_{slug}.md`

### Deliverables

One `.md` prompt file per operator skill. Each file contains:
1. Skill ID and name at the top
2. Context block (what this skill does, which pipeline phase it serves)
3. Required inputs (copy from catalog definition)
4. Optional inputs (copy from catalog definition)
5. Constraint block (all hard rules, verbatim from catalog)
6. Escalation rules (when to stop, when to re-run a prior phase)
7. Verification checklist (copy from catalog definition)
8. Output format (what the agent should produce)

### Hard rules

- These are prompt templates, not code — no imports, no function signatures
- Each template must be usable without reading the catalog (self-contained)
- Do not reference non-existent paths inside the templates

### Review dimensions — what 5/5 means here

- Correctness: every constraint and verification step matches the catalog definition
- Completeness: all 10 skills have files; no skill is missing
- Usability: an agent can invoke a skill by reading only its prompt file

### Runbook

```
mkdir -p skills/prompts/
# Create one file per skill (see Execute phase)
ls skills/prompts/ | wc -l   # must be 10
```

---

## SR-02 — Add escalation rules to all operator skills

**Status**: Done
**Gap linkage**: GAP-02
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

Fix: Add explicit "Escalation Rules" subsections to the 8 operator skills in
`skills_catalog.md` that currently lack them (SKL-201, SKL-202, SKL-203, SKL-204,
SKL-205, SKL-206, SKL-207, SKL-208 — SKL-209 and SKL-210 also need review).

Allowed paths: `skills_catalog.md`, `docs/usage/skills.md`

Forbidden paths: any protected path

### Acceptance checks

- [ ] Every operator skill (SKL-201 through SKL-210) has an "Escalation Rules" subsection
- [ ] Each escalation rule specifies: when to stop, when to invoke a prior phase, and what to do if output is still insufficient
- [ ] The format description in Part 3 of the catalog matches the actual skill format used

### Deliverables

Updated `skills_catalog.md` with escalation rules added to all operator skills
that lack them.

### Hard rules

- Do not remove or weaken any existing failure conditions
- Escalation rules must be specific — "re-run the skill" is not sufficient; name which earlier skill to invoke

### Review dimensions — what 5/5 means here

- Correctness: escalation rules are consistent with the pipeline's phase order
- Completeness: all 10 operator skills have the section

### Runbook

```
# Count operator skills with escalation rules before
grep -c "Escalation" skills_catalog.md

# After edits, re-count
grep -c "Escalation" skills_catalog.md   # must be >= 10
```

---

## SR-03 — Verify and fix cross-references

**Status**: Done
**Gap linkage**: GAP-03
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

Fix: Verify that every path referenced in `skills_catalog.md` and
`docs/usage/skills.md` resolves to an existing file or directory. Fix any
reference that points to a file that does not exist yet (excluding `skills/prompts/`
files, which are handled by SR-01).

Allowed paths: `skills_catalog.md`, `docs/usage/skills.md`

Forbidden paths: any protected path

### Acceptance checks

- [ ] Every path in backtick or link syntax in both files exists on disk (after SR-01 completes)
- [ ] No reference points to a hash-based path or an outdated file name
- [ ] `skills_loader.py` path claim verified by reading the actual file

### Deliverables

- Verified cross-reference list with status (exists / fixed / N/A)
- Corrected paths in `skills_catalog.md` and `docs/usage/skills.md` where needed

### Runbook

```
# Extract all backtick paths from catalog
grep -oP '`[^`]+\.(?:py|yaml|json|txt|md)`' skills_catalog.md | sort -u

# Check each against the file tree
# Verify skills_loader.py exists and check what it reads
cat src/launcher/shared/skills_loader.py | head -60
```
