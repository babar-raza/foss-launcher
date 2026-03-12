---
id: TC-4056
title: "Intake + Understand phase hardening — 8 root-cause fixes"
status: Done
priority: High
owner: "claude-sonnet-4-6"
updated: "2026-03-11"
tags: [intake, understand, scout, self-review, hardening]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4056_intake_understand_hardening.md
  - src/launcher/workers/intake/worker.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/understand/scout.py
  - src/launcher/workers/understand/extract/_snippets.py
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/models/understanding.py
  - specs/schemas/understanding_bundle.schema.json
evidence_required:
  - reports/TC-4056/evidence.md
---

# Taskcard TC-4056 — Intake + Understand phase hardening — 8 root-cause fixes

## Objective

Fix 8 confirmed root-cause defects in the Intake and Understand workers that cause
the pipeline to produce wrong-looking valid output (empty claims, empty api_surface,
unsanitized LLM context) while passing self_review. These are not cosmetic fixes —
each one closes a silent failure path that misleads downstream workers.

## Required spec references

- `specs/worker_understand.md` (self-review criteria, Phase A/B contract)
- `specs/system_overview.md` (Rule 1: every worker reviews its own work; Rule 5: sandwich model)

## Scope

### In scope
- Fix 1 (GAP-1): Raise on clone failure in `intake/worker.py` — never swallow
- Fix 2 (GAP-2): Add high-severity self_review checks in `understand/worker.py`
- Fix 3 (GAP-5): Sanitize disk fallback reads in `extract/_snippets.py`
- Fix 4 (GAP-7): SEO offline default when seo_config is None
- Fix 5 (GAP-8): Guard dict-valued `version` field from pyproject.toml
- Fix 6 (GAP-6): Importance-based file sort within budget tiers in scout
- Fix 7 (GAP-4): Expose `skipped_paths` in `RepoInfo` + schema update
- Fix 8 (GAP-3): Synthetic snippet safety gate in self_review

### Out of scope
- Platform identity for non-Python repos (separate taskcard warranted after this sweep)
- org_scanner / repo_classifier subsystem (different boundary — pipeline worker vs CLI intake)
- Phase C (planning) — not in scope for this taskcard

## Inputs

- `src/launcher/workers/intake/worker.py` (current: swallows clone failure)
- `src/launcher/workers/understand/worker.py` (current: self_review always passes)
- `src/launcher/workers/understand/scout.py` (current: smallest-first sort, dict version bug)
- `src/launcher/workers/understand/extract/_snippets.py` (current: unsanitized disk fallback)
- `src/launcher/workers/understand/extract/_entry.py` (current: unrestricted synthetic snippets)
- `src/launcher/models/understanding.py` (current: RepoInfo has no skipped_paths field)
- `specs/schemas/understanding_bundle.schema.json` (must be kept in sync with model)

## Outputs

- All 8 files modified (protected paths listed in allowed_paths)
- All existing tests pass (PYTHONHASHSEED=0)
- `reports/TC-4056/evidence.md` written after final test run

## Allowed paths

- plans/taskcards/TC-4056_intake_understand_hardening.md
- src/launcher/workers/intake/worker.py
- src/launcher/workers/understand/worker.py
- src/launcher/workers/understand/scout.py
- src/launcher/workers/understand/extract/_snippets.py
- src/launcher/workers/understand/extract/_entry.py
- src/launcher/models/understanding.py
- specs/schemas/understanding_bundle.schema.json

### Allowed paths rationale
Each path is directly required by one or more of the 8 fixes. No file is touched
speculatively. The schema file is included because Fix 7 adds a new field to `RepoInfo`
which is serialized to `understanding_bundle.json` and validated against this schema.

## Implementation steps

### Fix 1: Raise on clone failure (intake/worker.py:54-61)

**What**: Remove the broad exception catch around `clone_repo_cached()`. Re-raise as
a `RuntimeError` with a clear message. A missing repo_dir means nothing downstream
can run — this must be a hard stop, not a degraded bundle.

**Before**: `except Exception: ... repo_dir, repo_sha, is_fresh_clone = Path(""), "", False`
**After**: `except Exception as exc: raise RuntimeError(f"[Intake] Clone failed for {config.repo_url}: {exc}") from exc`

**Verification**: `pytest tests/unit/workers/test_clone.py -x -q` passes. Manual test
with invalid URL raises `RuntimeError` (not a silent bundle with empty repo_dir).

### Fix 2: High-severity self_review checks (understand/worker.py:243-293)

**What**: Add three `severity="high"` findings to `UnderstandWorker.self_review`:
1. `len(bundle.claims) == 0` → "No claims extracted — phase produced empty evidence"
2. `len(bundle.api_surface.public_classes) == 0` → "api_surface has no public classes"
3. `bundle.api_surface.confidence == "low"` → "api_surface confidence is low — AST extraction likely failed"

These findings make `passed=False` so the graph_builder treats the output as failed.

**Verification**: A test fixture that returns an empty `UnderstandingBundle` must get
`self_review().passed == False`.

### Fix 3: Sanitize disk fallback reads (_snippets.py:156-166)

**What**: In `_read_content()`, wrap the disk-read path in `sanitize_input(raw, max_chars=100_000)`.
The scout path already sanitizes; the fallback path must too, especially for heal re-runs.

**Verification**: Code review confirms `sanitize_input` is called on disk-read path.
The `test_extract.py` suite passes without regressions.

### Fix 4: SEO offline default (understand/worker.py:152-153)

**What**: Change `seo_offline = getattr(seo_config, "offline_mode", False) if seo_config else False`
to `seo_offline = getattr(seo_config, "offline_mode", True) if seo_config else True`.
When no SEO config is provided, default to offline. Network calls only happen when
explicitly configured.

**Verification**: In tests where `config.seo is None`, `research_keywords` is called
with `offline=True`. No network attempt in offline test environments.

### Fix 5: Dict-valued version guard (scout.py:_parse_pyproject)

**What**: After `version = project.get("version", "") or ...`, add:
`if not isinstance(version, str): version = ""`
Same guard for `name` (defensive — it could also be a dict in edge cases).

**Verification**: Test with a fixture pyproject.toml containing `version = {attr = "pkg.__version__"}`.
`SharedFacts.version` must be `""`, not `"{}"` or a stringified dict.

### Fix 6: Importance-based file sort within tiers (scout.py:257)

**What**: Replace `tier_files.sort(key=lambda x: x[1].size_bytes)` with a composite
sort key: `(importance_rank DESC, size_bytes ASC)` where `importance_rank` is derived
from known-important filename stems (README, API, REFERENCE, GUIDE, TUTORIAL for docs;
`__init__`, core module name for source). Unknown names get rank 0 (lowest priority).

**Verification**: In a test with a mix of small junk docs and large API reference docs,
the API reference is read first (appears in repo_content) before the small junk doc.

### Fix 7: Expose skipped_paths in RepoInfo (model + scout + worker)

**What**:
1. Add `skipped_paths: list[str] = Field(default_factory=list)` to `RepoInfo` in `models/understanding.py`.
2. In `scout.py`, collect entries from `budget_log` where reason != "per_file_cap" (truly skipped, not just truncated) into `skipped_paths` and populate `RepoInfo`.
3. Update `specs/schemas/understanding_bundle.schema.json` to add `skipped_paths` as an optional array of strings in the `repo` object.
4. In `understand/worker.py` self_review, add to metrics: `"skipped_paths_count": len(bundle.repo.skipped_paths)`.

**Verification**: After running on a budget-constrained fixture, `bundle.repo.skipped_paths`
is non-empty and `scout_inventory.json` lists the same files.

### Fix 8: Synthetic snippet safety gate (understand/worker.py self_review)

**What**: In `self_review()`, add a `severity="medium"` finding if:
`synthetic_count / max(1, len(bundle.snippets)) > 0.5`
(i.e., more than half of all snippets are synthetic). This makes the weak evidence
visible to humans inspecting the self_review result — it doesn't block the pipeline
(medium, not high) but surfaces the signal.

Also: in `_generate_synthetic_snippets()` in `_entry.py`, check `typed_methods` for
required parameters. Skip methods that have required positional params (any param
without a default). This prevents generating `obj.load()` when `load` takes a required `path`.

**Verification**: A fixture class with `def load(self, path: str)` (required arg) must
NOT appear in synthetic snippets. A fixture class with `def render(self)` (no required args)
MUST appear.

## Failure modes

### Failure mode 1: Raising on clone failure breaks existing tests that mock clone

**Detection**: `pytest tests/unit/workers/test_clone.py` or `test_intake.py` fails
with `RuntimeError` being unexpected.
**Resolution**: Update mock to raise on invalid URL and expect `RuntimeError` in the test.
**Gate**: Fix 1 contract — tests must pass with the new raise behavior.

### Failure mode 2: RepoInfo schema change breaks existing snapshot tests

**Detection**: Tests comparing serialized `UnderstandingBundle` to golden snapshots
fail because `skipped_paths` is a new field.
**Resolution**: Update golden snapshots. The field has `default_factory=list` so
existing bundles without the field will deserialize with `skipped_paths=[]`.
**Gate**: Fix 7 — all existing deserialization tests must pass.

### Failure mode 3: Self_review high-severity checks fail on valid but sparse repos

**Detection**: A real repo with no public Python classes (e.g., a repo with only
TypeScript or config files) triggers `api_surface.public_classes == 0` high finding.
**Resolution**: Scope the `public_classes == 0` check to repos where the primary
language is Python (where AST extraction is expected to work). For non-Python repos,
downgrade to `severity="medium"` or use `confidence=="low"` as the sole blocker.
**Gate**: Fix 2 — checks must not cause false positives on legitimately minimal repos.

## Task-specific review checklist

1. [x] Fix 1: `clone_repo_cached` exception re-raised as `RuntimeError` with URL in message
2. [x] Fix 2: self_review returns `passed=False` for bundle with `claims=[]`
3. [x] Fix 2: self_review returns `passed=False` for bundle with `api_surface.public_classes=[]` and `confidence="low"` (when primary_language is python)
4. [x] Fix 3: `_read_content` disk fallback path calls `sanitize_input`
5. [x] Fix 4: `seo_offline` defaults to `True` when `seo_config is None`
6. [x] Fix 5: `SharedFacts.version` is `""` when pyproject.toml has dict-valued version
7. [x] Fix 6: Large API reference doc is read before small junk doc in same category
8. [x] Fix 7: `RepoInfo.skipped_paths` populated from budget_log; schema updated
9. [x] Fix 8: `_generate_synthetic_snippets` skips methods with required positional args
10. [x] Fix 8: self_review emits medium finding when >50% snippets are synthetic
11. [x] Docstrings updated for all new/changed public functions
12. [x] Spec file updated if worker behavior changed (or confirmed no spec drift)
13. [x] Schema `"description"` fields present for all new/changed properties
14. [x] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
15. [x] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. All 8 source files modified (listed in allowed_paths)
2. `reports/TC-4056/evidence.md` with test results and key observable outputs

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q` — all pass (3310 passed)
2. [x] `IntakeWorker` raises `RuntimeError` on clone failure (not silent bundle)
3. [x] `UnderstandWorker.self_review` returns `passed=False` for bundle with zero claims
4. [x] `_read_content` disk path calls `sanitize_input`
5. [x] `RepoInfo.skipped_paths` is populated when budget is exceeded
6. [x] `understanding_bundle.schema.json` includes `skipped_paths` in `repo` object

## Self-review

### Verification results
- [x] Tests: 3310/3310 PASS (9 deselected pre-existing flaky TestDeployIntegration)
- [x] Validation: TC-4056 acceptance checks PASS
- [x] Evidence captured: reports/TC-4056/evidence.md
- [x] Doc freshness: No spec drift — all changes tighten existing contract; no new docs required

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -x -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -x -q
```

**Expected results**:
- All unit tests pass with no regressions
- `test_clone.py` passes with updated raise-on-failure behavior
- `test_extract.py` passes with sanitizer and synthetic snippet changes

## Integration boundary proven

**Upstream**: `IntakeBundle` → `UnderstandWorker.run()`
**Downstream**: `UnderstandingBundle` → Generate worker (claims, snippets, api_surface)
**Contract**: `UnderstandingBundle` with `len(claims) > 0`, `api_surface.confidence != "low"`,
`repo.skipped_paths` populated, all snippets either extracted or clearly marked synthetic
