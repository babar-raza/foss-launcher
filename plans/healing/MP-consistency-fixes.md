# MP — Consistency Fixes Healing Plan

## Context

Five gaps in `plans/twinkly-puzzling-minsky.md` where existing content is internally
contradictory or has duplicate/conflicting definitions. Unlike G-01 through G-06, these
gaps do not require new spec sections — they require edits to text that already exists.
Left unresolved, they will cause implementers to make incompatible choices silently.

Source plan: `plans/twinkly-puzzling-minsky.md`
Review origin: MP-00 (G-07, G-08, G-09, G-10, G-11)

---

## Gap → Taskcard Map

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-07 | Canonical naming conflicts — 4 active inconsistencies across the plan | MP-07 |
| G-08 | Pipeline.yaml location conflict — two different paths stated | MP-08 |
| G-09 | Understand phase count conflict — CLAUDE.md says 4, plan says 3 | MP-09 |
| G-10 | Gate count conflict — Evaluate says "8 quality checks" but 13 gate files listed | MP-10 |
| G-11 | Cherry-pick rename steps missing — no import-rewrite command after cherry-pick | MP-11 |

---

## Taskcard MP-07 — Add Canonical Naming Reference Table

**Status**: Done
**Gap linkage**: G-07
**Role**: Senior engineer. Drop-in, production-ready. This is the single most important
consistency fix because all other taskcards depend on having one unambiguous vocabulary.

### Scope

**Fix**:
1. Add a "Canonical Naming Reference" table to `plans/twinkly-puzzling-minsky.md`
   immediately after the "Technical Decisions" section (before the Architecture section).
2. In the same edit pass, fix all 4 in-place inconsistencies:
   - Rename `understanding.json` → `understanding_bundle.json` everywhere in the plan.
   - Standardize worker references to use named labels (Intake, Understand, Generate,
     Evaluate, Publish) — remove "Worker 1/2/3/4" numbered references.
   - Add a cross-reference note wherever A/B/C appears that it maps to full/core/minimal
     (pending the canonical mapping from MP-03).
3. Also fix in `CLAUDE.md` the reference to "4 internal phases" (coordinated with MP-09).

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`
- `CLAUDE.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "Worker 1\|Worker 2\|Worker 3\|Worker 4" plans/twinkly-puzzling-minsky.md | wc -l` returns 0
- **CLI**: `grep '"understanding\.json"' plans/twinkly-puzzling-minsky.md | wc -l` returns 0 (all replaced with understanding_bundle.json)
- **CLI**: `grep "Canonical Naming Reference" plans/twinkly-puzzling-minsky.md` finds the table
- **CLI**: `grep "understanding_bundle\.json" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 5
- **Tests**: N/A (plan document)
- **Config respected**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Insert the following table immediately
   after the "Technical Decisions" section:

```markdown
---

## Canonical Naming Reference

This table is the single source of truth. Every other reference in this document and
in all spec files must match it. Aliases listed in the "Aliases to avoid" column must
not appear anywhere.

| Concept | Canonical Name | Aliases to Avoid |
|---------|---------------|-----------------|
| Pipeline workers (all 5) | Intake, Understand, Generate, Evaluate, Publish | W1/W2/W3/W4/W5, Worker 1/2/3/4 |
| Artifact: Understand output | `understanding_bundle.json` | `understanding.json` |
| Artifact: Generate output (dir) | `content_bundle/` | `drafts/`, `pages/` (as a top-level alias) |
| Tier identifiers (classifier) | `A`, `B`, `C` | Use only inside `surface_classifier.py`; translate to effective_tier before any other use |
| Tier identifiers (run_config) | `full`, `core`, `minimal`, `auto` | A, B, C |
| Tier identifiers (IntakeBundle) | `full`, `core`, `minimal` | auto, A, B, C |
| Pipeline config file | `configs/pipeline.yaml` | `src/launcher/orchestrator/pipeline.yaml` |
| Package name (Python) | `launcher` | `launch` |
| Self-review output type | `SelfReviewResult` | `ReviewResult`, `WorkerReview`, `self_review_result` |
| Re-run state key | `re_run_target` | `rerun_target`, `re_run_worker`, `target_worker` |

---
```

2. **In-place fixes to `plans/twinkly-puzzling-minsky.md`**:
   - Replace every occurrence of `"understanding.json"` with `"understanding_bundle.json"`.
   - Replace every occurrence of `Worker 1:`, `Worker 2:`, `Worker 3:`, `Worker 4:` with
     `Understand:`, `Generate:`, `Evaluate:`, `Publish:` respectively.
   - Replace the v1→v2 worker mapping table's "Worker 1/2/3/4" column labels to use
     named worker labels.
   - Replace `src/launcher/orchestrator/pipeline.yaml` in the repo structure tree with
     a comment note: `# topology defined in configs/pipeline.yaml (project root)`.

3. **Fix `CLAUDE.md`**: Change "4 internal phases" to "3 internal phases (A Scout,
   B Extract, C Plan)" in the Architecture section. (Coordinate with MP-09.)

### Hard Rules

- After this taskcard: zero occurrences of `"understanding.json"` (without `_bundle`) in `plans/twinkly-puzzling-minsky.md`
- After this taskcard: zero occurrences of `Worker 1`, `Worker 2`, `Worker 3`, `Worker 4` in `plans/twinkly-puzzling-minsky.md`
- The "Canonical Naming Reference" table must appear before the Architecture section so it can be found without scrolling past worker details

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Consistency | `grep "understanding\.json\b"` returns 0 (only `understanding_bundle.json` found) |
| Maintainability | One table to update when a name changes; no hunting through the document |
| Minimality | No new concepts introduced; purely editorial |
| Correctness | CLAUDE.md is in sync with the plan after this edit |

### Now (Runbook)

```bash
# 1. Insert the Canonical Naming Reference table
code plans/twinkly-puzzling-minsky.md
# Add the table immediately after "## Technical Decisions" section

# 2. Fix "understanding.json" occurrences
grep -n '"understanding\.json"' plans/twinkly-puzzling-minsky.md
# Note every line number, replace each with "understanding_bundle.json"

# 3. Fix Worker 1/2/3/4 references
grep -n "Worker [1-4]" plans/twinkly-puzzling-minsky.md
# Note every occurrence, replace with named worker

# 4. Fix pipeline.yaml duplicate location
grep -n "src/launcher/orchestrator/pipeline.yaml" plans/twinkly-puzzling-minsky.md
# Replace with canonical configs/pipeline.yaml reference

# 5. Fix CLAUDE.md
grep -n "4 internal phases\|4 phases" CLAUDE.md
# Replace with "3 internal phases (A Scout, B Extract, C Plan)"

# 6. Validate all fixes
grep "Worker [1-4]" plans/twinkly-puzzling-minsky.md | wc -l
# Expected: 0

grep '"understanding\.json"' plans/twinkly-puzzling-minsky.md | wc -l
# Expected: 0

grep "understanding_bundle\.json" plans/twinkly-puzzling-minsky.md | wc -l
# Expected: ≥ 5

grep "Canonical Naming Reference" plans/twinkly-puzzling-minsky.md
# Expected: 1 match (the table header)
```

---

## Taskcard MP-08 — Resolve Pipeline.yaml Location Conflict

**Status**: Done
**Gap linkage**: G-08
**Role**: Senior engineer. Drop-in, production-ready. After this taskcard, there is
exactly one path where `pipeline.yaml` lives and it is referenced consistently everywhere.

### Scope

**Fix**: Audit every reference to `pipeline.yaml` in `plans/twinkly-puzzling-minsky.md`
and resolve all of them to `configs/pipeline.yaml`. The file at
`src/launcher/orchestrator/pipeline.yaml` must be removed from the repo structure tree
and replaced with a comment explaining the canonical location.

**Canonical decision**: `configs/pipeline.yaml` (project root `configs/` directory).
**Rationale**: Config-driven topology belongs in `configs/` alongside `families.yaml`
and `intake_config.yaml` — not buried in source code. The orchestrator reads it from there.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "src/launcher/orchestrator/pipeline.yaml" plans/twinkly-puzzling-minsky.md | wc -l` returns 0
- **CLI**: `grep "configs/pipeline.yaml" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 3
- **CLI**: `grep "pipeline.yaml" plans/twinkly-puzzling-minsky.md | grep -v "configs/"` returns 0
- **Tests**: N/A
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**:
   - In the repo structure tree: remove the line `│   ├── pipeline.yaml        # config-driven pipeline topology`
     from `src/launcher/orchestrator/` and add a comment `# reads configs/pipeline.yaml at startup`.
   - Every reference to `pipeline.yaml` outside the `configs/` section must be updated
     to include the full canonical path `configs/pipeline.yaml`.

2. **Add a "Location Decision" note** to the "Config-Driven Pipeline" rule subsection:

```markdown
> **Canonical location**: `configs/pipeline.yaml` — not under `src/launcher/`.
> The orchestrator reads it from `{project_root}/configs/pipeline.yaml` at startup.
> Moving it would require updating `graph_builder.py`'s config loader only.
```

### Hard Rules

- After this fix: the string `"orchestrator/pipeline.yaml"` must not appear in the plan
- `graph_builder.py` must be documented to read from `configs/pipeline.yaml` (not from its own package directory)

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Consistency | All 3+ references to pipeline.yaml point to `configs/pipeline.yaml` |
| Correctness | The repo structure tree matches the stated canonical location |
| Minimality | One-line rationale provided; no over-explanation |

### Now (Runbook)

```bash
# 1. Count all pipeline.yaml references
grep -n "pipeline.yaml" plans/twinkly-puzzling-minsky.md

# 2. For each reference not already showing configs/pipeline.yaml, fix it
# (Use editor; grep output shows line numbers)

# 3. Validate
grep "src/launcher/orchestrator/pipeline.yaml" plans/twinkly-puzzling-minsky.md | wc -l
# Expected: 0

grep "configs/pipeline.yaml" plans/twinkly-puzzling-minsky.md | wc -l
# Expected: ≥ 3

grep "pipeline.yaml" plans/twinkly-puzzling-minsky.md | grep -v "configs/"
# Expected: no output
```

---

## Taskcard MP-09 — Fix Understand Phase Count Conflict

**Status**: Done
**Gap linkage**: G-09
**Role**: Senior engineer. Drop-in, production-ready. After this taskcard, every reference
to the number of Understand worker phases is consistent and correct.

### Scope

**Fix**: The Understand worker has **3 internal phases**: A (Scout), B (Extract), C (Plan).
CLAUDE.md currently says "4 internal phases" — this is wrong. The fix is:
1. Change "4 internal phases" to "3 internal phases" in CLAUDE.md.
2. Verify the plan itself says 3 phases and is correct (it is).
3. Search for any other "4 phases" references and fix them.

**Allowed paths**:
- `CLAUDE.md`
- `plans/twinkly-puzzling-minsky.md` (verification only; may need a minor fix)

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "4 internal phases\|4 phases" CLAUDE.md | wc -l` returns 0
- **CLI**: `grep "3 internal phases\|phases A.*B.*C\|Phase A\|Phase B\|Phase C" CLAUDE.md` finds the corrected reference
- **CLI**: `grep -n "phases" plans/twinkly-puzzling-minsky.md | grep "[^3] internal phases"` returns 0
- **Tests**: N/A
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Edit `CLAUDE.md`**: Find the line containing "4 internal phases" in the Understand
   worker description and replace:

   Before:
   ```
   - Each worker has a clear, singular purpose
   ```
   (or wherever "4 internal phases" appears — the exact context)

   After: Change "4 internal phases" to "3 internal phases (A Scout, B Extract, C Plan)".

2. **Verify `plans/twinkly-puzzling-minsky.md`**: Run grep to confirm the plan already
   says "3 phases" or lists exactly 3 phases. No edit needed if already correct.

3. **Add a phase count note** to the plan's Understand worker section header:

```markdown
**Internal phases**: 3 (A Scout → B Extract → C Plan). Sequential, each feeds the next.
```

### Hard Rules

- The authoritative phase count is 3. If a fourth phase was ever planned and removed,
  there must be no orphaned references to it
- CLAUDE.md and the plan must agree exactly

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Consistency | `grep "4 internal phases"` in both files returns 0 |
| Correctness | Phase list in plan matches: exactly A, B, C |
| Minimality | One-character change ("4" → "3") plus a clarifying parenthetical |

### Now (Runbook)

```bash
# 1. Find the location in CLAUDE.md
grep -n "internal phases\|4 phases" CLAUDE.md

# 2. Edit
code CLAUDE.md
# Change "4 internal phases" to "3 internal phases (A Scout, B Extract, C Plan)"

# 3. Verify the plan is already correct
grep -n "phases" plans/twinkly-puzzling-minsky.md | grep "internal"
# Expected: "3 internal phases" or just listing of Phases A, B, C (no "4")

# 4. Validate
grep "4 internal phases" CLAUDE.md | wc -l
# Expected: 0

grep "3 internal phases\|Phase A\|Phase B\|Phase C" CLAUDE.md | wc -l
# Expected: ≥ 1
```

---

## Taskcard MP-10 — Reconcile Gate Count Conflict (8 Checks vs 13 Gate Files)

**Status**: Done
**Gap linkage**: G-10
**Role**: Senior engineer. Drop-in, production-ready. After this taskcard, an implementer
reading the plan knows exactly how 8 check categories map to 13 gate file implementations.

### Scope

**Fix**: Add a "Check-to-Gate Mapping" subsection to the Evaluate worker section of
`plans/twinkly-puzzling-minsky.md` that explicitly shows:
1. The 8 check _categories_ (what the Evaluate worker runs).
2. The gate _files_ that implement each category (from the Layer 7 carry-over list).
3. The rule that check categories are the API surface; gate files are the implementation detail.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "Check-to-Gate Mapping\|check.*gate\|gate.*check" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 1
- **CLI**: `grep -A30 "Check-to-Gate" plans/twinkly-puzzling-minsky.md` shows 8 check categories
- **Tests**: N/A
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Add the following immediately after
   the 8-check table in the Evaluate worker section:

```markdown
#### Check-to-Gate Implementation Mapping

The 8 check categories above are the **API surface** of the Evaluate worker.
Each category is implemented by one or more gate files from the carry-over inventory.
This mapping explains why there are 13 gate files for 8 categories.

| Check Category | Implementing Gate File(s) | Notes |
|---------------|--------------------------|-------|
| 1. Frontmatter validation | `gate_frontmatter_schema.py` | Single gate |
| 2. Heading structure | `gate_heading_hierarchy.py`, `gate_template_heading_substitution.py` | Two gates: hierarchy + placeholder detection |
| 3. Code examples | `gate_code_syntax_valid.py`, `gate_code_fence_api_validity.py`, `gate_import_allowlist.py` | Three gates: syntax + API validity + import path |
| 4. Content density | `gate_content_density.py`, `gate_intra_page_repetition.py` | Two gates: word count + within-page dedup |
| 5. Spec leakage | `gate_spec_leakage.py`, `gate_api_hallucination.py` | Two gates: internal terms + invented API names |
| 6. LLM artifacts | `gate_llm_artifact_phrases.py`, `gate_scaffold_leak.py` | Two gates: boilerplate + scaffold text |
| 7. Safety gates | `gate_xss_prevention.py`, `gate_sensitive_data_leak.py` | Two gates: XSS + PII (CRITICAL severity) |
| 8. SEO quality | `gate_markdown_lint.py` + inline SEO checks in `seo.py` | One gate + inline check (no separate gate file) |

**Total**: 8 categories → 13 gate files + 1 inline check.
Safety gates (check 7) are always CRITICAL severity — they cannot be downgraded by tier.
```

### Hard Rules

- The mapping table must not introduce any new gate file names not already in the Layer 7 list
- The count must be accurate: after the patch, `8 categories`, `13 gate files`, `1 inline check`

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Consistency | 8-row check table + 8-row mapping table — same categories, same order |
| Correctness | Every gate file in the mapping exists in the Layer 7 carry-over inventory |
| Maintainability | One place to update when gate files are added or removed |

### Now (Runbook)

```bash
# 1. Verify the 8 check categories exist in the plan
grep -A20 "Phase A — Deterministic checks" plans/twinkly-puzzling-minsky.md | head -25
# Expected: table with 8 numbered rows

# 2. Verify the 13 gate files exist in Layer 7
grep -c "gate_" plans/twinkly-puzzling-minsky.md
# Expected: ≥ 13 distinct gate file names in the Layer 7 section

# 3. Insert the mapping table after the 8-check table
code plans/twinkly-puzzling-minsky.md
# Add the "Check-to-Gate Implementation Mapping" immediately after the 8-check table

# 4. Validate
grep "Check-to-Gate" plans/twinkly-puzzling-minsky.md
# Expected: 1 section header found

grep -A30 "Check-to-Gate" plans/twinkly-puzzling-minsky.md | grep "^| [0-9]" | wc -l
# Expected: 8 (one row per check category)
```

---

## Taskcard MP-11 — Document Cherry-Pick Rename Procedure

**Status**: Done
**Gap linkage**: G-11
**Role**: Senior engineer. Drop-in, production-ready. A developer running Phase 1 of the
implementation must be able to execute the cherry-pick + rename steps from this document
alone, without consulting the v1 codebase.

### Scope

**Fix**: Replace the existing Phase 1 Step 8 ("Cherry-pick from v1") bullet in
`plans/twinkly-puzzling-minsky.md` with a fully detailed procedure including:
1. The exact `git checkout main -- <path>` commands for each layer.
2. The immediate import-rename step after cherry-pick (before any `git add`).
3. The validation step (run `python -c "import launcher.io.hashing"` to verify).
4. A note on which files need additional adaptation beyond import renaming.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "from launch\b\|import launch\b" plans/twinkly-puzzling-minsky.md | wc -l` returns 0 after the fix (old import form is not left as guidance)
- **CLI**: `grep "sed.*launch.*launcher\|s/launch\./launcher\." plans/twinkly-puzzling-minsky.md` finds the rename command
- **CLI**: `grep "git checkout main -- src/" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 5
- **Tests**: N/A
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Replace Phase 1 Step 8** in `plans/twinkly-puzzling-minsky.md` with:

```markdown
8. **Cherry-pick from v1 and rename imports** (in the v2 worktree):

   **Step 8a — Cherry-pick each layer** (run from `foss-launcher-v2/` directory):
   ```bash
   # Layer 1: Core Infrastructure
   git checkout main -- src/launch/io/hashing.py src/launch/io/yamlio.py \
     src/launch/io/schema_validation.py src/launch/io/run_config.py \
     src/launch/io/atomic.py src/launch/io/run_layout.py \
     src/launch/io/run_lock.py src/launch/io/artifact_store.py
   git checkout main -- src/launch/util/errors.py src/launch/util/logging.py \
     src/launch/util/run_id.py src/launch/util/budget_tracker.py \
     src/launch/util/diff_analyzer.py src/launch/util/path_validation.py \
     src/launch/util/subprocess.py
   git checkout main -- src/launch/provenance/provenance.py

   # Layer 2: Clients & Resilience
   git checkout main -- src/launch/clients/llm_provider.py \
     src/launch/clients/llm_cache.py src/launch/clients/llm_telemetry.py \
     src/launch/clients/llm_mock_provider.py src/launch/clients/http.py \
     src/launch/clients/commit_service.py
   git checkout main -- src/launch/resilience/circuit_breaker.py \
     src/launch/resilience/retry_policy.py src/launch/resilience/checkpoint.py

   # Layer 3: State & Events
   git checkout main -- src/launch/state/event_log.py \
     src/launch/state/snapshot_manager.py

   # Layer 6: Validation Engine
   git checkout main -- src/launch/validation_engine/runner.py \
     src/launch/validation_engine/gate_types.py \
     src/launch/validation_engine/registry_loader.py \
     src/launch/validation_engine/adapters.py
   ```

   **Step 8b — Move files from `src/launch/` to `src/launcher/`**:
   ```bash
   # Git places files at their v1 paths; move them to v2 paths
   mkdir -p src/launcher/{io,util,provenance,clients,resilience,state,validation_engine}
   cp -r src/launch/io/* src/launcher/io/
   cp -r src/launch/util/* src/launcher/util/
   cp -r src/launch/provenance/* src/launcher/provenance/
   cp -r src/launch/clients/* src/launcher/clients/
   cp -r src/launch/resilience/* src/launcher/resilience/
   cp -r src/launch/state/* src/launcher/state/
   cp -r src/launch/validation_engine/* src/launcher/validation_engine/
   rm -rf src/launch/   # remove the temporary v1 path
   ```

   **Step 8c — Rewrite imports** (from `launcher` root, in `src/launcher/`):
   ```bash
   # Replace all internal imports: "from launcher.launch." → "from launcher.launcher."
   # NOTE: the package is "launcher" not "launch" in v2
   find src/launcher/ -name "*.py" -exec \
     sed -i 's/from launch\./from launcher./g' {} \;
   find src/launcher/ -name "*.py" -exec \
     sed -i 's/import launch\./import launcher./g' {} \;
   ```

   **Step 8d — Validate imports**:
   ```bash
   cd foss-launcher-v2/
   .venv/Scripts/python.exe -c "
   import launcher.io.hashing
   import launcher.io.yamlio
   import launcher.util.errors
   import launcher.clients.llm_provider
   import launcher.resilience.circuit_breaker
   import launcher.state.event_log
   print('All carry-over imports OK')
   "
   # Expected: "All carry-over imports OK" with no ImportError
   ```

   **Step 8e — Files requiring additional adaptation** (beyond import renaming):
   - `io/atomic.py`: Strip v1 taskcard-layer checks (search for "taskcard" in file).
   - `clients/llm_provider.py`: Update endpoint constants from v1 env vars to v2 env vars.
   - `validation_engine/gates_registry.yaml`: Trim to ~20 gates (see Layer 7 carry-over list).
   - `models/*.py`: Rebuild from scratch using v2 pydantic schemas (do not carry over v1 models directly).
```

### Hard Rules

- The `sed` commands in Step 8c must be verified safe before running (dry-run with `--dry-run` or use `perl` for in-place sed on Windows)
- On Windows (this repo): replace `sed -i` with the PowerShell equivalent:
  `Get-ChildItem -Recurse -Filter *.py | ForEach-Object { (Get-Content $_) -replace 'from launch\.','from launcher.' | Set-Content $_ }`
- Do NOT cherry-pick v1 model files — they must be rewritten for v2 schemas

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Thoroughness | All 3 layers' cherry-pick commands listed; import rename; validation step |
| Correctness | Commands are syntactically correct for bash on the v2 worktree |
| Robustness | Windows alternative for `sed -i` provided |
| Minimality | No unnecessary file copies; models explicitly excluded |

### Now (Runbook)

```bash
# 1. Find Phase 1 Step 8 in the plan
grep -n "Cherry-pick from v1" plans/twinkly-puzzling-minsky.md

# 2. Replace with the detailed procedure
code plans/twinkly-puzzling-minsky.md
# Navigate to Phase 1 Step 8, replace the bullet with the full procedure

# 3. Validate the new procedure
grep "sed.*launch.*launcher\|sed.*s\/launch" plans/twinkly-puzzling-minsky.md
# Expected: the sed command from Step 8c

grep "git checkout main -- src/launch/io" plans/twinkly-puzzling-minsky.md
# Expected: the Layer 1 cherry-pick command

grep "Step 8e\|additional adaptation" plans/twinkly-puzzling-minsky.md
# Expected: the adaptation notes section
```
