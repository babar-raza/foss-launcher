# TC-3799 Post-Implementation Healing Plan

## Context

TC-3799 added topic-aware skeleton differentiation to the planner. Self-review identified several gaps ranging from unused imports to missing integration tests. Investigation confirmed that heading-gate and `get_required_headings()` concerns were false alarms (no downstream code references skeletons). This plan addresses the **real** remaining gaps.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-01 | Unused `PAGE_ROLE_SKELETONS` import in `section_prompt.py` and `worker.py` | Low | SR-01 |
| G-02 | `ENGINE_VERSION` not bumped; cached plans won't pick up variants | Medium | SR-02 |
| G-03 | `resolve_skeleton` doesn't guard against empty variant lists | Low | SR-03 |
| G-04 | Overly broad slug patterns: `rendering` matches `server-side-rendering`, `install` matches `uninstall` | Medium | SR-04 |
| G-05 | `getting-started` mapped to `install` variant — semantically broader | Medium | SR-04 |
| G-06 | No end-to-end `run_plan()` integration test verifying variant propagation | Medium | SR-05 |
| G-07 | Taskcard TC-3799 not marked Done, no evidence file | Low | SR-06 |

---

## Taskcard SR-01 — Remove unused PAGE_ROLE_SKELETONS imports

**Status:** Done
**Gap linkage:** G-01
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Remove unused `PAGE_ROLE_SKELETONS` from import lines in `section_prompt.py` and `worker.py`. In `worker.py` the symbol was used in the old fallback path that was replaced by `resolve_skeleton()`. In `section_prompt.py` it was never used — only `SkeletonSection` is used.

**Allowed paths:**
- `src/launcher/workers/generate/section_prompt.py`
- `src/launcher/workers/generate/worker.py`

**Forbidden:** Any other file/path.

### Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short` — all tests pass
- **Tests:** No new tests needed (import cleanup only)
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** N/A

### Deliverables

- `section_prompt.py` line 12: `from launcher.shared.page_skeletons import SkeletonSection` (remove `PAGE_ROLE_SKELETONS`)
- `worker.py` line 39: `from launcher.shared.page_skeletons import SkeletonSection` (remove `PAGE_ROLE_SKELETONS`)

### Hard rules

- Keep public signatures unchanged
- No new deps
- Verify no other reference to `PAGE_ROLE_SKELETONS` exists in either file before removing

### Review dimensions (5/5 targets)

- **Minimality:** Single-line import cleanup, zero functional change
- **Correctness:** Grep confirms symbol unused in both files beyond import
- **Testability:** Existing tests validate no import breakage

### Now (runbook)

```bash
# 1. Verify PAGE_ROLE_SKELETONS is unused in section_prompt.py
grep -n "PAGE_ROLE_SKELETONS" src/launcher/workers/generate/section_prompt.py
# Should show only line 12 (the import)

# 2. Verify PAGE_ROLE_SKELETONS is unused in worker.py beyond import
grep -n "PAGE_ROLE_SKELETONS" src/launcher/workers/generate/worker.py
# Should show only line 39 (the import)

# 3. Edit both files to remove PAGE_ROLE_SKELETONS from imports

# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

---

## Taskcard SR-02 — Bump ENGINE_VERSION for skeleton variant cache invalidation

**Status:** Done
**Gap linkage:** G-02
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Bump `ENGINE_VERSION` from `"2.0.0"` to `"2.1.0"` in `provenance.py`. This invalidates the LLM cache so that plans generated with the old flat-skeleton logic are regenerated with variant-aware skeletons. Without this bump, cached `PlanBundle` artifacts from prior runs would be reused, and the new variant skeletons would never take effect.

**Allowed paths:**
- `src/launcher/provenance/provenance.py`

**Forbidden:** Any other file/path.

### Acceptance checks

- **CLI:** `python -c "from launcher.provenance import ENGINE_VERSION; assert ENGINE_VERSION == '2.1.0'"`
- **Tests:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short` — all pass
- **Config respected end-to-end:** Next pipeline run must regenerate plan (not use cached version)
- **No mock data in production paths:** Confirmed

### Deliverables

- `src/launcher/provenance/provenance.py` line 24: `ENGINE_VERSION = "2.1.0"`

### Hard rules

- Semantic versioning: minor bump (new feature, backward-compatible)
- No new deps
- Keep code/docs/tests in sync — check if any test asserts `ENGINE_VERSION == "2.0.0"`

### Review dimensions (5/5 targets)

- **Correctness:** Cache key includes ENGINE_VERSION; bump guarantees regeneration
- **Production grading:** Essential for the variant feature to actually take effect on next run
- **Minimality:** One-line change

### Now (runbook)

```bash
# 1. Check current version
grep ENGINE_VERSION src/launcher/provenance/provenance.py

# 2. Check if any test asserts the version string
grep -r "2.0.0" tests/ --include="*.py"

# 3. Edit provenance.py: ENGINE_VERSION = "2.1.0"

# 4. Update any version-asserting tests if found

# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

---

## Taskcard SR-03 — Guard resolve_skeleton against empty variant lists

**Status:** Done
**Gap linkage:** G-03
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** In `resolve_skeleton()`, change `if variant is not None` to `if variant` so that an accidentally empty list `[]` in `SKELETON_VARIANTS` falls through to the default skeleton instead of returning an empty list. An empty skeleton causes division by zero in the generator's round-robin claim distribution (`j % len(skeleton)`).

**Allowed paths:**
- `src/launcher/shared/page_skeletons.py`
- `tests/unit/shared/test_skeleton_variants.py`

**Forbidden:** Any other file/path.

### Acceptance checks

- **Tests:** New test `test_empty_variant_falls_back_to_default` added and passing
- **CLI:** Full suite passes
- **No mock data in production paths:** N/A

### Deliverables

- `page_skeletons.py` `resolve_skeleton()`: change `if variant is not None:` to `if variant:`
- New test in `test_skeleton_variants.py`:
  ```python
  def test_empty_variant_falls_back_to_default(self):
      """Empty variant list should fall back to default, not return []."""
      # Temporarily inject empty variant
      from launcher.shared.page_skeletons import SKELETON_VARIANTS, PAGE_ROLE_SKELETONS
      key = ("workflow_page", "_test_empty")
      SKELETON_VARIANTS[key] = []
      try:
          result = resolve_skeleton("workflow_page", "_test_empty")
          default = PAGE_ROLE_SKELETONS["workflow_page"]
          assert [s.heading for s in result] == [s.heading for s in default]
      finally:
          del SKELETON_VARIANTS[key]
  ```

### Hard rules

- Keep public signature unchanged
- Deterministic behavior — empty list is treated as "not found"
- No new deps

### Review dimensions (5/5 targets)

- **Robustness:** Prevents division-by-zero crash in generator
- **Correctness:** Empty list is functionally equivalent to "no variant"
- **Testability:** Covered by explicit test with cleanup

### Now (runbook)

```bash
# 1. Edit resolve_skeleton: change `if variant is not None:` to `if variant:`
# 2. Add test_empty_variant_falls_back_to_default
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_skeleton_variants.py -v
```

---

## Taskcard SR-04 — Tighten slug pattern matching and fix getting-started mapping

**Status:** Done
**Gap linkage:** G-04, G-05
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. Change `resolve_topic_tag` slug matching from substring (`pattern in slug_lower`) to segment-boundary matching. A pattern should match when it equals the full slug or appears as a complete hyphenated segment. This prevents `"install"` matching `"uninstall"` and `"rendering"` matching `"server-side-rendering"`.
2. Create a separate `getting-started` variant for `workflow_page` that is semantically appropriate for a first-use/onboarding page (not an installation-focused skeleton). The getting-started page should have: Overview, Prerequisites, Quick Start, Next Steps, See Also.

**Allowed paths:**
- `src/launcher/shared/page_skeletons.py`
- `tests/unit/shared/test_skeleton_variants.py`
- `tests/unit/workers/test_plan_skeleton_differentiation.py`

**Forbidden:** Any other file/path.

### Acceptance checks

- **Tests:** New tests:
  - `test_uninstall_does_not_match_install` — `slug="uninstall-guide"` returns `"default"`
  - `test_server_side_rendering_does_not_match` — `slug="server-side-rendering"` returns `"default"`
  - `test_getting_started_has_own_variant` — `slug="getting-started"` returns `"getting_started"` (not `"install"`)
  - `test_getting_started_skeleton_differs_from_install` — headings differ
- **CLI:** Full suite passes
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** N/A

### Deliverables

1. New matching function `_slug_matches_pattern(slug: str, pattern: str) -> bool` that checks segment boundaries
2. Updated `resolve_topic_tag` to use the new matching function
3. New `("workflow_page", "getting_started")` skeleton variant with: Overview, Prerequisites, Quick Start, Next Steps, See Also
4. Updated `SLUG_TOPIC_PATTERNS`: `("getting-started", "getting_started")` instead of `("getting-started", "install")`
5. New/updated tests covering negative cases and the new variant
6. Update `test_all_family_override_slugs_resolved` if getting-started is tested there

### Hard rules

- Keep public signatures unchanged
- Deterministic matching — no regex, simple string ops
- No new deps
- Update existing test assertions that expect getting-started → install

### Review dimensions (5/5 targets)

- **Correctness:** Prevents false-positive slug matches that produce wrong skeletons
- **Robustness:** Segment-boundary matching is future-proof against new slug patterns
- **Testability:** Negative test cases explicitly verify non-matching
- **Production grading:** Prevents content pages getting wrong section structure

### Now (runbook)

```bash
# 1. Add _slug_matches_pattern helper
# 2. Update resolve_topic_tag to use it
# 3. Add ("workflow_page", "getting_started") variant skeleton
# 4. Change SLUG_TOPIC_PATTERNS getting-started mapping
# 5. Update tests
# 6. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_skeleton_variants.py tests/unit/workers/test_plan_skeleton_differentiation.py -v
# 7. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

---

## Taskcard SR-05 — Add end-to-end run_plan integration test

**Status:** Done
**Gap linkage:** G-06
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Add an integration test that calls `run_plan()` with realistic inputs (ProductIdentity, RichnessResult, claims, snippets) and verifies that the output PlannedPages have:
1. Different `skeleton_variant` values for pages with different slugs/topic_categories
2. Different `skeleton` heading lists for differentiated pages
3. `skeleton_variant` is propagated through frontmatter construction
4. All mandatory pages have non-empty skeletons

This test calls the real `run_plan()` function — not mocked resolution functions.

**Allowed paths:**
- `tests/unit/workers/test_plan_skeleton_differentiation.py`

**Forbidden:** Any other file/path.

### Acceptance checks

- **Tests:** New test class `TestRunPlanSkeletonIntegration` with 4+ tests, all passing
- **CLI:** Full suite passes
- **No mock data in production paths:** Test uses minimal but realistic model objects
- **Deterministic:** Fixed claim IDs and PYTHONHASHSEED=0

### Deliverables

- New test class in `test_plan_skeleton_differentiation.py`:
  ```python
  class TestRunPlanSkeletonIntegration:
      def test_run_plan_produces_variant_skeletons(self):
          """run_plan() output has different variants for install vs data_ops pages."""
      def test_run_plan_all_pages_have_skeleton(self):
          """Every page in run_plan() output has a non-empty skeleton."""
      def test_run_plan_howto_variants_from_topic_category(self):
          """howto_article pages with topic_category get correct variant."""
      def test_run_plan_variant_survives_frontmatter_build(self):
          """skeleton_variant persists after _build_frontmatter and _refine_page_slugs."""
  ```

### Hard rules

- No network calls — test uses local ruleset.yaml
- Deterministic: fixed claim IDs, PYTHONHASHSEED=0
- Uses real `run_plan()` — not mocked internals
- No new deps

### Review dimensions (5/5 targets)

- **Testability:** Tests the actual contract, not implementation details
- **Thoroughness:** Covers the full planner pipeline including frontmatter rebuild
- **Robustness:** Verifies no data loss during frozen-model reconstructions
- **Production grading:** Catches regressions that unit tests on resolve functions would miss

### Now (runbook)

```bash
# 1. Add TestRunPlanSkeletonIntegration class
# 2. Create minimal ProductIdentity, RichnessResult, claims, snippets fixtures
# 3. Call run_plan() and assert variant fields on output
# 4. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_skeleton_differentiation.py -v
```

---

## Taskcard SR-06 — Close TC-3799: mark Done and create evidence

**Status:** Done
**Gap linkage:** G-07
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** After all SR-01 through SR-05 are complete:
1. Update TC-3799 taskcard status from `In-Progress` to `Done`
2. Check all acceptance checks as `[x]`
3. Create evidence file at `reports/TC-3799/evidence.md` with test results and variant examples
4. Fill in self-review verification results

**Allowed paths:**
- `plans/taskcards/TC-3799_skeleton_differentiation.md`
- `reports/TC-3799/evidence.md`

**Forbidden:** Any other file/path.

### Acceptance checks

- **CLI:** N/A (documentation only)
- **Tests:** N/A
- **Config respected end-to-end:** Taskcard status reflects actual completion state

### Deliverables

- Updated taskcard with status `Done` and all checks marked `[x]`
- Evidence file with:
  - Test output (40+ tests passing)
  - Example variant resolution: slug → variant → headings for 3+ pages
  - Diff summary of changed files

### Hard rules

- Only mark Done after SR-01..SR-05 are all Done
- Evidence must include actual test output, not fabricated results

### Review dimensions (5/5 targets)

- **Scope adherence:** Taskcard protocol compliance (AG-002)
- **Thoroughness:** Evidence captures both test results and functional verification

### Now (runbook)

```bash
# 1. Run full test suite and capture output
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short > reports/TC-3799/test_output.txt 2>&1

# 2. Create evidence.md with results

# 3. Update taskcard frontmatter: status: Done

# 4. Mark all acceptance checks [x]
```
