---
id: DM-02
title: "Expand CODE_TO_SPEC coverage to ~100% of codebase + add retroactive scope disclaimer"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [healing, doc-maintenance, AG-019, scripts, skills]
depends_on: [DM-01]
allowed_paths:
  - plans/healing/DM-02_expand_code_to_spec.md
  - scripts/check_doc_freshness.py
  - skills.md
evidence_required:
  - "grep -c 'shared/' scripts/check_doc_freshness.py shows >= 1 mapping"
  - "grep -c 'clients/' scripts/check_doc_freshness.py shows >= 1 mapping"
  - "grep -c 'state/' scripts/check_doc_freshness.py shows >= 1 mapping"
  - "grep 'retroactive' skills.md returns the scope disclaimer line"
  - "python scripts/check_doc_freshness.py --since HEAD~1 exits 1 when only shared/** changed and its spec was not touched"
---

# Taskcard DM-02 — Expand `CODE_TO_SPEC` + Scope Disclaimer

## Gap linkage

- GR-03: `CODE_TO_SPEC` covers only ~40% of the codebase; large areas
  produce false-clean exits
- GR-07: `skills.md` TECHNICAL DOCUMENTATION STANDARDS lacks a retroactive
  scope disclaimer; agents may treat it as an immediate audit requirement

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

#### 1. GR-03 — Expand `CODE_TO_SPEC` in `scripts/check_doc_freshness.py`

Add the following mappings **after** the existing entries. Ordering within
the list does not affect correctness (first match wins per file), but keep
more-specific patterns before less-specific ones for the same subtree.

New entries to add:

```python
# Shared utilities — govern system-level behaviour across multiple specs
("src/launcher/shared/**",         "specs/system_overview.md"),
# LLM client layer — governs provider contract
("src/launcher/clients/**",        "specs/llm_provider.md"),
# State, events, checkpoints
("src/launcher/state/**",          "specs/state_events_checkpoints.md"),
# Resilience (retry, circuit-breaker, checkpoint)
("src/launcher/resilience/**",     "specs/state_events_checkpoints.md"),
# Provenance tracking
("src/launcher/provenance/**",     "specs/state_events_checkpoints.md"),
# CLI layer
("src/launcher/cli/**",            "specs/system_overview.md"),
# IO utilities (artifact store, run layout, etc.)
("src/launcher/io/**",             "specs/run_configuration.md"),
# Intake worker
("src/launcher/intake/**",         "specs/github_intake.md"),
# Content templates
("src/launcher/content/**",        "specs/site_model_hugo.md"),
```

Note: `src/launcher/util/**` is intentionally excluded — utility helpers
(logging, errors, path_validation) do not have a 1:1 spec mapping and are
low-risk for behavioral drift. Add a comment in the file documenting this.

Also add the `extend_mapping` comment above the table:

```python
# To add a new mapping: append a (glob_pattern, spec_path) tuple.
# More-specific patterns should precede less-specific ones for the same tree.
# Paths intentionally excluded: src/launcher/util/** (cross-cutting utilities,
# no single governing spec).
```

#### 2. GR-07 — Add scope disclaimer to `skills.md`

At the very start of the `## TECHNICAL DOCUMENTATION STANDARDS` section
(immediately after the introductory paragraph and before the first `###`
subsection), insert:

```markdown
> **Scope**: These standards apply to code **written or changed in new
> taskcards going forward**. They are not a retroactive audit requirement.
> Existing files are brought into compliance opportunistically when a
> taskcard modifies them. An agent working on TC-NNNN should apply these
> standards to the files that TC-NNNN touches — not to the entire codebase.
```

### Allowed paths

- `scripts/check_doc_freshness.py` (targeted edit to `CODE_TO_SPEC` and its comment block)
- `skills.md` (targeted insertion of one blockquote)

### Forbidden

Any file outside the two allowed paths above (plus this plan file).

---

## Acceptance checks

### CLI

```bash
# Verify new mappings are present
grep "src/launcher/shared" scripts/check_doc_freshness.py
# Expected: ("src/launcher/shared/**", "specs/system_overview.md"),

grep "src/launcher/clients" scripts/check_doc_freshness.py
# Expected: ("src/launcher/clients/**", "specs/llm_provider.md"),

# Verify scope disclaimer is in skills.md
grep "retroactive" skills.md
# Expected: the disclaimer blockquote line

# Functional test: simulate a change to a shared file only
# (Requires a scratch commit — skip if disruptive; use --verbose instead)
python scripts/check_doc_freshness.py --since HEAD~1 --verbose
# If last commit touched src/launcher/shared/** but not specs/system_overview.md:
# Expected: exit 1, DRIFT DETECTED with the shared file listed
```

### UI/Web/API

N/A.

### Tests

Covered by DM-04. DM-04 must add test cases for the new mappings:
- `find_governing_spec("src/launcher/clients/llm_provider.py")` → `"specs/llm_provider.md"`
- `find_governing_spec("src/launcher/state/event_log.py")` → `"specs/state_events_checkpoints.md"`
- `find_governing_spec("src/launcher/util/logging.py")` → `None` (intentionally excluded)

### Config respected end-to-end

All new mappings must be in `CODE_TO_SPEC` (the in-file config table), not
hardcoded anywhere else in the logic.

### No mock data in production paths

N/A.

---

## Deliverables

1. **Targeted edit to `scripts/check_doc_freshness.py`**: add 9 new tuples
   to `CODE_TO_SPEC`, add exclusion comment, add `extend_mapping` comment.
   File remains fully runnable.

2. **Targeted edit to `skills.md`**: insert the retroactive scope disclaimer
   blockquote at the start of `## TECHNICAL DOCUMENTATION STANDARDS` body,
   between the introductory paragraph and the first `###` subsection.

---

## Hard rules

- `CODE_TO_SPEC` order: more-specific before less-specific for the same subtree
- No new runtime dependencies
- The `src/launcher/util/**` exclusion must be commented in the source, not
  silently omitted
- `skills.md` disclaimer must be a blockquote (`>`), not a comment or plain
  paragraph, so it stands out visually

---

## Review dimensions (what 5/5 means for DM-02)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | Every `src/launcher/**` subdirectory either has a mapping or has a documented exclusion reason |
| Correctness | `find_governing_spec` returns the right spec for all new paths |
| Minimality | Only `CODE_TO_SPEC` table + one comment block + one blockquote are changed |
| Clarity | The `util/**` exclusion is explicitly documented; no silent gaps |
| Production grading | After this TC, drift detection coverage ≥ 90% of modified files in typical taskcards |

---

## Now (runbook)

```bash
# Step 1: Confirm existing CODE_TO_SPEC entries (know what's already there)
grep -A 20 "CODE_TO_SPEC" scripts/check_doc_freshness.py

# Step 2: Confirm src/launcher subdirectory list
ls src/launcher/

# Step 3: Edit scripts/check_doc_freshness.py
#   - Add 9 new tuples after the existing entries
#   - Add comment block above the table

# Step 4: Edit skills.md
#   - Insert blockquote immediately after the introductory paragraph
#     of ## TECHNICAL DOCUMENTATION STANDARDS

# Step 5: Verify mappings
grep "shared\|clients\|state\|resilience\|provenance\|cli\|io\|intake\|content" \
  scripts/check_doc_freshness.py | grep "src/launcher"
# Expected: 9+ lines of new mappings

# Step 6: Verify scope disclaimer
grep -A 5 "retroactive" skills.md
```
