# Healing Plan: Evaluate Check Defects — Post-Sprint Gaps

**Date**: 2026-03-08
**Source**: Self-review of TC-3857..TC-3863 (abstract-singing-honey.md)
**Prefix**: EH (Evaluate Healing)

## Context

TC-3857..TC-3863 fixed 33 root-cause defects across 14 deterministic evaluation checks.
The post-sprint self-review identified 6 residual gaps across correctness, testability,
observability, and governance. This healing plan converts each gap into an executable
taskcard. All gaps are low-blast-radius: no interface changes, no schema changes.

---

## Gap Table

| Gap ID | Severity | Description | Taskcard |
|--------|----------|-------------|----------|
| G-01 | Medium | `density.py` defines `placeholders` list twice — silent divergence risk | EH-01 |
| G-02 | Medium | `artifacts.py` uses two different code-stripping strategies in one function | EH-02 |
| G-03 | High | No behavioral tests for any of the 6 new reference exemptions or call-site fixes | EH-03 |
| G-04 | Low | No debug logging when reference role checks short-circuit | EH-04 |
| G-05 | Medium | TC-3863 taskcard & plan file still reference `claim_leakage.py` as in-scope; `PLAN_INDEX.md` not updated | EH-05 |
| G-06 | Low | `getattr(context.config, "canonical_import", "")` in `worker.py` bypasses model validation | EH-06 |

---

## Taskcard: EH-01 — Extract `_PLACEHOLDER_STRINGS` constant in `density.py`

**Status**: Done
**Gap linkage**: G-01
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: The `placeholders` list is defined twice in `density.py` — once inside the
`_SKIP_WORD_COUNT` early-return branch and again in the main flow. Extract to a
module-level `_PLACEHOLDER_STRINGS` constant; reference it from both branches.
This eliminates a silent divergence risk: if a new placeholder is added to one list
but not the other, reference pages will behave differently from prose pages.

**Allowed paths**:
- `src/launcher/workers/evaluate/checks/density.py`

**Forbidden**: any other file or path.

### Acceptance checks

**CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

**UI/Web/API**: N/A

**Tests**:
- All existing density tests pass unchanged
- New test: `test_reference_page_placeholder_detected()` — reference-role page with
  `[todo]` in body → 1 high finding (proves the reference-path list is the same)
- New test: `test_prose_page_placeholder_detected()` — prose page with `lorem ipsum` →
  1 high finding (proves main-path list unchanged)

**Config respected end-to-end**: `page_role="api_reference"` triggers reference path;
`page_role=""` triggers prose path; both detect all 5 placeholder strings.

**No mock data in production paths**: No mocks needed.

### Deliverables

1. **Full replacement**: `src/launcher/workers/evaluate/checks/density.py`
   - Module-level constant before `check_density()`:
     ```python
     _PLACEHOLDER_STRINGS: tuple[str, ...] = (
         "[content to be generated]",
         "[todo]",
         "[tbd]",
         "[placeholder]",
         "lorem ipsum",
     )
     ```
   - Both `placeholders = [...]` inline definitions replaced with `for ph in _PLACEHOLDER_STRINGS:`
   - `lower_body = body.lower()` hoisted before the `_SKIP_WORD_COUNT` branch so it is
     computed once regardless of path

2. **New/updated tests**: add to `tests/unit/workers/test_evaluate.py` under
   `TestCheckDensity` class (or new `TestCheckDensityReferenceRole`):
   - `test_reference_page_placeholder_detected` — happy path: placeholder on reference page
   - `test_reference_page_no_word_count_finding` — reference page with 5 words → 0 density findings
   - `test_prose_page_still_gets_word_count_finding` — prose page with 5 words → 1 density finding

3. **No contract/schema changes**.

### Hard rules

- Keep public signature `check_density(content, slug, *, page_role="")` unchanged
- `_PLACEHOLDER_STRINGS` must be a module-level constant (not inside the function)
- Use `tuple` not `list` for immutability
- Deterministic: no change to ordering or set of placeholder strings
- No new deps

### Review dimensions (what 5/5 means here)

| Dim | 5/5 criterion |
|-----|--------------|
| Correctness | Both branches iterate identical strings; no placeholder can be in one but not the other |
| Maintainability | One place to add/remove placeholders; constant name `_PLACEHOLDER_STRINGS` is self-documenting |
| Testability | New tests exercise BOTH the reference-path and prose-path for placeholder detection |
| Minimality | Only `density.py` touched; diff is a pure refactor with no logic change |

### Now (runbook)

```bash
# 1. Edit density.py: add _PLACEHOLDER_STRINGS constant before check_density()
# 2. Replace both inline `placeholders = [...]` with `for ph in _PLACEHOLDER_STRINGS:`
# 3. Hoist `lower_body = body.lower()` before the _SKIP_WORD_COUNT branch
# 4. Add 3 tests to test_evaluate.py
# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -x -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard: EH-02 — Unify code-stripping strategy in `artifacts.py`

**Status**: Done
**Gap linkage**: G-02
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: `artifacts.py` currently uses two different code-block stripping approaches:
- `strip_code_blocks(body)` from `launcher.shared.jaccard` for phrase/echo scanning
- `re.sub(r"(?ms)^```.*?^```", "", body)` for the keyword-stuffing section

These can produce different results for unclosed fences, nested backticks, or `~~~` fences.
Replace the ad-hoc regex in the keyword-stuffing section with `strip_code_blocks()`.
Reuse the already-computed `body_for_phrases` variable (it is the same strip applied to
the same `body`).

**Allowed paths**:
- `src/launcher/workers/evaluate/checks/artifacts.py`

**Forbidden**: any other file or path.

### Acceptance checks

**CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

**UI/Web/API**: N/A

**Tests**:
- All existing `TestCheckArtifacts` and `TestCheckArtifactsEnhanced` tests pass unchanged
- New test: `test_keyword_stuffing_ignores_code_block_mentions()` — product name repeated
  20× inside a fenced code block → 0 keyword-stuffing finding (proves strip is effective)
- New test: `test_keyword_stuffing_counts_prose_mentions()` — product name repeated 20×
  in prose → 1 keyword-stuffing finding (proves detection still works)

**Config respected end-to-end**: `product_name` kwarg drives the prose-density check.

**No mock data in production paths**: No mocks needed.

### Deliverables

1. **Full replacement**: `src/launcher/workers/evaluate/checks/artifacts.py`
   - In the keyword-stuffing section, replace:
     ```python
     prose = re.sub(r"(?ms)^```.*?^```", "", body)
     ```
     With:
     ```python
     prose = body_for_phrases  # already stripped by strip_code_blocks() above
     ```
   - Remove the now-unused ad-hoc `re.sub` call
   - Add a comment: `# body_for_phrases = strip_code_blocks(body) computed above; reuse here`

2. **New/updated tests**: add to `tests/unit/workers/test_evaluate.py` under
   `TestCheckArtifactsEnhanced`:
   - `test_keyword_stuffing_ignores_code_block_mentions` — 20× product name in code block → 0
   - `test_keyword_stuffing_counts_prose_mentions` — 20× in prose → 1 finding

3. **No contract/schema changes**.

### Hard rules

- Public signature `check_artifacts(content, slug, *, product_name="")` unchanged
- Do not introduce a new variable; reuse `body_for_phrases`
- `strip_code_blocks` import already present — no new deps
- Keyword-stuffing detection must still fire for prose mentions (regression test required)

### Review dimensions (what 5/5 means here)

| Dim | 5/5 criterion |
|-----|--------------|
| Consistency | Single code-stripping strategy used throughout `check_artifacts` |
| Correctness | Keyword-stuffing density computed on identical stripped body as phrase scan |
| Robustness | Unclosed fences, `~~~` fences, and backtick-nesting handled uniformly |
| Minimality | Diff is 2-line removal + 1-line comment; no behavior change for well-formed content |

### Now (runbook)

```bash
# 1. In artifacts.py keyword-stuffing block: replace re.sub(...) with prose = body_for_phrases
# 2. Add comment explaining the reuse
# 3. Add 2 tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -x -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard: EH-03 — Behavioral tests for new reference exemptions and call-site fixes

**Status**: Done
**Gap linkage**: G-03
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: TC-3857..TC-3862 added 6 new behavioral guarantees (reference exemptions +
call-site fixes) that are not covered by any dedicated test. The plan's verification
criteria specified concrete assertions that were stated but never implemented. Add
targeted tests for each new behavior.

**Allowed paths**:
- `tests/unit/workers/test_evaluate.py`

**Forbidden**: any other file or path. Do NOT change any source check files.

### Acceptance checks

**CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -x -v` — all pass

**UI/Web/API**: N/A

**Tests** (these ARE the deliverable — each must pass):

1. `test_reference_page_repetition_no_code_block_finding` — 15× identical code block,
   `page_role="api_reference"` → 0 `high` repetition findings
2. `test_prose_page_repetition_fires_code_block_finding` — same content,
   `page_role=""` → ≥1 `high` repetition finding
3. `test_reference_page_density_skips_word_count` — 5-word reference page,
   `page_role="api_reference"` → 0 findings (word count below threshold but exempted)
4. `test_reference_page_density_still_catches_placeholder` — reference page with `[todo]`,
   `page_role="api_reference"` → 1 `high` density finding
5. `test_is_index_with_path_prefix_skips_seo_checks` — slug `"getting-started/_index"` →
   `is_index=True`: no `seoTitle`, `canonical`, or `keywords` findings from `check_seo`
6. `test_is_index_exact_match_still_works` — slug `"_index"` → same 0 findings
7. `test_canonical_import_threaded_to_check_code` — `_run_deterministic_checks()` called
   with `canonical_import="import aspose.cells"`, content with `import numpy` → ≥1 `code`
   finding about non-canonical import
8. `test_product_name_threaded_to_check_seo` — `_run_deterministic_checks()` called with
   `product_name="Aspose.Cells"`, frontmatter title without "Aspose.Cells" →
   ≥1 `seo` finding about missing product name in title
9. `test_param_list_passes_reference_completeness` — reference page with only
   `` `paramName` TypeName `` lines (no `|` table rows), `page_role="api_reference"` →
   0 `high` reference_completeness findings
10. `test_no_table_no_param_list_fails_reference_completeness` — reference page with
    neither table nor param-list → 1 `high` reference_completeness finding

**Config respected end-to-end**: `page_role`, `product_name`, `canonical_import` all
exercised via `_run_deterministic_checks()` (the real call path).

**No mock data in production paths**: use real `check_*` functions directly or through
`_run_deterministic_checks`; no mocks.

### Deliverables

1. **New test cases** added to `tests/unit/workers/test_evaluate.py`:
   - New class `TestReferenceRoleExemptions` covering tests 1-4
   - New class `TestIsIndexDetection` covering tests 5-6
   - Add to `TestRunDeterministicChecks`: tests 7-8
   - New class `TestReferenceCompletenessParamList` covering tests 9-10
   - All test content must use proper frontmatter (`---\ntitle: T\n---\n`)
   - All test slugs must be realistic (e.g., `"aspose-barcode/barcodereader"`)

2. **No production file changes**.

3. **No contract/schema changes**.

### Hard rules

- No mocks of `check_*` functions — test the real implementations
- Tests must be deterministic: no randomness
- Each test must have a docstring explaining what guarantee it proves
- No network calls in any test

### Review dimensions (what 5/5 means here)

| Dim | 5/5 criterion |
|-----|--------------|
| Coverage | All 6 new behavioral guarantees have ≥1 happy-path and ≥1 regression/failure-path test |
| Correctness | Tests fail before the fix, pass after (verify by reverting change and running) |
| Test Quality | Each test has one assertion purpose; no multi-assert test with unclear failure mode |
| Maintainability | Class names `TestReferenceRoleExemptions` etc. are discoverable |

### Now (runbook)

```bash
# 1. Add TestReferenceRoleExemptions (4 tests) to test_evaluate.py
# 2. Add TestIsIndexDetection (2 tests)
# 3. Add 2 tests to TestRunDeterministicChecks
# 4. Add TestReferenceCompletenessParamList (2 tests)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -x -v -k "ReferenceRole or IsIndex or param_list or canonical_import or product_name"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard: EH-04 — Add reference role skip logging to 3 check files

**Status**: Done
**Gap linkage**: G-04
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: When `repetition.py`, `density.py`, and `semantic_structure.py` short-circuit
for reference pages, they do so silently. In production, a page that passes these checks
unexpectedly cannot be debugged — it is impossible to distinguish "check ran and found
nothing" from "check was skipped". Add a single `logger.debug(...)` call at each
skip/short-circuit point.

**Allowed paths**:
- `src/launcher/workers/evaluate/checks/repetition.py`
- `src/launcher/workers/evaluate/checks/density.py`
- `src/launcher/workers/evaluate/checks/semantic_structure.py`

**Forbidden**: any other file or path.

### Acceptance checks

**CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

**UI/Web/API**: N/A

**Tests**:
- All existing tests pass (log calls are side-effect only)
- Optional: add `caplog` assertion in one test confirming skip message appears (not
  required if it would create test-maintenance burden)

**Config respected end-to-end**: log output visible at DEBUG level; no behavioral change.

**No mock data in production paths**: N/A.

### Deliverables

1. **Full replacements** for all 3 check files with logging added:

   **`repetition.py`** — add at module level:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```
   Add inside the reference-role guard (where code-block duplication check is skipped):
   ```python
   if page_role in _REFERENCE_ROLES:
       logger.debug("[repetition] Skipping code-block/Jaccard checks for reference page: %s", slug)
   ```

   **`density.py`** — add at module level:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```
   Add immediately after `_SKIP_WORD_COUNT = ...`:
   ```python
   if _SKIP_WORD_COUNT:
       logger.debug("[density] Skipping word-count threshold for %s (page_role=%r)", slug, page_role)
   ```

   **`semantic_structure.py`** — already imports `logging` and has `logger`. Add inside
   the reference-role guard:
   ```python
   if page_role in _REFERENCE_ROLES:
       logger.debug("[semantic_structure] Skipping empty-section check for reference page: %s", slug)
   ```

2. **No new/changed tests** required (logging is observability-only).

3. **No contract/schema changes**.

### Hard rules

- Use `logger.debug` only — not `info`; not `warning`
- Format: `[check_name] Skipping X for page_role=Y: slug`
- `logging.getLogger(__name__)` pattern (matches `semantic_structure.py` existing pattern)
- No new deps beyond stdlib `logging`

### Review dimensions (what 5/5 means here)

| Dim | 5/5 criterion |
|-----|--------------|
| Observability | Running at DEBUG level shows exactly which checks were skipped and for which slug |
| Minimality | One line of log per skip point; zero behavior change |
| Consistency | All 3 files use identical `[check_name] Skipping...` format |
| Safety | `logger.debug` is never emitted in production unless DEBUG level is configured |

### Now (runbook)

```bash
# 1. Add `import logging; logger = logging.getLogger(__name__)` to repetition.py and density.py
# 2. Add logger.debug at each skip/short-circuit point in all 3 files
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard: EH-05 — Governance closure: annotate step 31, fix TC-3863 scope, update PLAN_INDEX.md

**Status**: Done
**Gap linkage**: G-05
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Three governance artifacts have stale or misleading content:

1. `abstract-singing-honey.md` (plan file) — STEP 31 still reads as an unexecuted
   requirement; needs an "INVESTIGATION RESULT" annotation explaining why it was
   intentionally NOT applied.

2. `plans/taskcards/TC-3863_artifacts_claim_seo_quality_fixes.md` — `allowed_paths`,
   `Deliverables`, and `Scope` sections still list `claim_leakage.py` as in-scope,
   but the file was deliberately not modified. Must be corrected so a future agent
   does not re-attempt this change.

3. `reports/PLAN_INDEX.md` — The `abstract-singing-honey.md` plan and its taskcards
   (TC-3857..TC-3863) are not indexed. Must append rows.

**Allowed paths**:
- `C:\Users\prora\.claude\plans\abstract-singing-honey.md`
- `plans/taskcards/TC-3863_artifacts_claim_seo_quality_fixes.md`
- `reports/PLAN_INDEX.md`

**Forbidden**: any other file or path.

### Acceptance checks

**CLI**: `grep "step 31" "C:\Users\prora\.claude\plans\abstract-singing-honey.md" | grep -i "investigation\|result\|intentional"` — must match

**UI/Web/API**: N/A

**Tests**: No automated tests — governance files only.

**Config respected end-to-end**: N/A.

**No mock data in production paths**: N/A.

### Deliverables

1. **`abstract-singing-honey.md`** — append after the STEP 31 bullet in the Atomic Step
   Summary section:
   ```
   STEP 31 · claim_leakage.py: Apply strip_code_blocks before CLM pattern scan
     INVESTIGATION RESULT (2026-03-08): NOT APPLIED.
     Pipeline metadata comments (# Claims: CLM-xxx) inside code blocks ARE leakage —
     they indicate internal annotations accidentally included in generated code.
     Stripping code blocks would suppress a critical finding. Test
     `test_comment_claim_detected` explicitly validates this contract. This step is
     closed as "rejected by test evidence". No code change required.
   ```

2. **`plans/taskcards/TC-3863_artifacts_claim_seo_quality_fixes.md`**:
   - Remove `src/launcher/workers/evaluate/checks/claim_leakage.py` from `allowed_paths`
   - Remove it from `Deliverables`
   - Replace "Step 4: Apply strip_code_blocks in claim_leakage.py" with:
     ```
     ### Step 4: claim_leakage.py — Investigation only, no change
     **Finding**: `# Claims: CLM-xxx` inside code blocks is valid leakage.
     Stripping code blocks would suppress critical findings. No modification.
     Test `test_comment_claim_detected` proves the correct existing behavior.
     ```

3. **`reports/PLAN_INDEX.md`** — append these rows:
   ```markdown
   | `C:\Users\prora\.claude\plans\abstract-singing-honey.md` | Chat-derived plan | Evaluation check defects full audit (33 steps, 7 TCs) | Gap table, Atomic steps, Taskcard plan | true |
   | `plans/taskcards/TC-3857_evaluate_repetition_reference_roles.md` | Taskcard | repetition.py reference role exemption | Steps, Acceptance, Evidence | false |
   | `plans/taskcards/TC-3858_spec_leakage_code_block_strip.md` | Taskcard | spec_leakage code block strip | Steps, Acceptance, Evidence | false |
   | `plans/taskcards/TC-3859_safety_code_block_scoping.md` | Taskcard | safety code block scoping | Steps, Acceptance, Evidence | false |
   | `plans/taskcards/TC-3860_reference_completeness_param_list.md` | Taskcard | reference_completeness param-list | Steps, Acceptance, Evidence | false |
   | `plans/taskcards/TC-3861_reference_page_structural_checks.md` | Taskcard | semantic_structure + structure + density | Steps, Acceptance, Evidence | false |
   | `plans/taskcards/TC-3862_worker_callsite_seo_code_canonical.md` | Taskcard | worker.py call-sites + code.py logic | Steps, Acceptance, Evidence | false |
   | `plans/taskcards/TC-3863_artifacts_claim_seo_quality_fixes.md` | Taskcard | artifacts + seo quality fixes | Steps, Acceptance, Evidence | false |
   | `plans/healing/EVAL_CHECKS_HEALING_2026_03_08.md` | Healing plan | 6 taskcards for post-sprint gaps EH-01..EH-06 | Gap table, Taskcards | true |
   ```

### Hard rules

- Do not alter any other section of `abstract-singing-honey.md`
- Do not change the TC-3863 taskcard `status` (it is already `Done`)
- `PLAN_INDEX.md` rows appended, never deleted
- Each PLAN_INDEX row must have all 5 columns

### Review dimensions (what 5/5 means here)

| Dim | 5/5 criterion |
|-----|--------------|
| Consistency | TC-3863 allowed_paths and deliverables match what was actually changed |
| Thoroughness | PLAN_INDEX.md lists all 8 TC-3857..3863 taskcards + healing plan |
| Maintainability | Future agent reading TC-3863 will not re-attempt claim_leakage.py modification |
| Docs/Specs Fidelity | Plan file and taskcard are the source of truth for what step 31 means |

### Now (runbook)

```bash
# 1. Edit abstract-singing-honey.md: append INVESTIGATION RESULT after STEP 31
# 2. Edit TC-3863 taskcard: remove claim_leakage.py from allowed_paths + deliverables + step 4
# 3. Append rows to reports/PLAN_INDEX.md
# Verify:
grep -i "investigation" "C:\Users\prora\.claude\plans\abstract-singing-honey.md"
grep "claim_leakage" "plans\taskcards\TC-3863_artifacts_claim_seo_quality_fixes.md"
```

---

## Taskcard: EH-06 — Replace `getattr` defensive access with direct RunConfig attribute in `worker.py`

**Status**: Done
**Gap linkage**: G-06
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: `worker.py` uses `getattr(context.config, "canonical_import", "") or ""`
when threading `canonical_import` to `_run_deterministic_checks()`. This bypasses
Pydantic/model validation and hides missing-field schema drift. Verify that `RunConfig`
already defines `canonical_import` (it does — the LLM review path accesses
`context.config.canonical_import or ""` directly at line 433). Replace the `getattr`
defensive access with direct attribute access matching the existing pattern.

**Allowed paths**:
- `src/launcher/workers/evaluate/worker.py`

**Forbidden**: any other file or path.

### Acceptance checks

**CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

**UI/Web/API**: N/A

**Tests**:
- All existing tests pass
- Confirm existing `TestProductNameThreading` tests still pass (same pattern)

**Config respected end-to-end**: `context.config.canonical_import` is the same field
accessed by the LLM review path — confirm parity.

**No mock data in production paths**: N/A.

### Deliverables

1. **Targeted edit** to `src/launcher/workers/evaluate/worker.py`:
   Replace:
   ```python
   canonical_import=getattr(context.config, "canonical_import", "") or "",
   ```
   With:
   ```python
   canonical_import=context.config.canonical_import or "",
   ```
   This matches the existing pattern at line 433 (`canonical_import=context.config.canonical_import or ""`).

2. **No new tests** needed (behavior identical; `getattr` was a defensive guard for a field
   that already exists on the model).

3. **No contract/schema changes**.

### Hard rules

- Verify `RunConfig` has `canonical_import` field before applying (grep the model)
- If `RunConfig` does NOT have the field: do NOT apply this change; instead create a
  follow-up taskcard to add it to the model first
- Pattern must match line 433 exactly (`context.config.canonical_import or ""`)

### Review dimensions (what 5/5 means here)

| Dim | 5/5 criterion |
|-----|--------------|
| Correctness | Direct attribute access surfaces schema drift as an error, not silent empty string |
| Consistency | Matches the existing pattern already used in `_run_llm_review()` at line 433 |
| Maintainability | No `getattr` magic; field existence is enforced by the model |
| Minimality | 1-line change, no behavioral difference if field exists (it does) |

### Now (runbook)

```bash
# 1. Verify RunConfig has canonical_import:
grep -r "canonical_import" src/launcher/models/run_config.py src/launcher/io/run_config.py 2>/dev/null
# 2. If confirmed: replace getattr with direct access in worker.py
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Execution Order

| Priority | Taskcard | Rationale |
|----------|----------|-----------|
| 1 | EH-05 | Governance closure unblocks clean audit trail; no code risk |
| 2 | EH-01 | Correctness: prevents placeholder list divergence; low risk |
| 3 | EH-02 | Consistency: unifies code-stripping; low risk |
| 4 | EH-03 | Testability: behavioral tests for all 6 new guarantees; adds confidence |
| 5 | EH-06 | Robustness: remove defensive getattr; verify model first |
| 6 | EH-04 | Observability: pure logging addition; zero risk |
