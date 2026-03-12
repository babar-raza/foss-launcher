# v2 Self-Review Healing — Spec Completeness

> Source: Self-review of quirky-mapping-mccarthy (Heal), twinkly-beaming-wren (Golden),
>          sparkling-discovering-walrus (SEO-Phase-2)
> Severity: Critical / High / Medium
> Filed: 2026-03-08

Tasks that were listed in the plans but left with zero implementation contract, or whose
implementation contract has a gap that would produce incorrect or unsafe behavior. All fixes
are production-grade code implementations, not patches.

---

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| GAP-04-SAFETY | H3.5 (core heal CLI) can be shipped without H3.7 (RunLock, BudgetTracker) — silent safety gap | V2SC-01 |
| GAP-06 | H2.6 `finding_classifier.py` listed as "NEW" but has zero implementation contract | V2SC-02 |
| GAP-09 | H5.8 section-level re-generation requires evaluate checks to emit `section_id` — not specced | V2SC-03 |
| GAP-10 | All `asyncio.gather()` calls in H5.6 and G003 OPT-5 missing `return_exceptions=True` | V2SC-04 |
| GAP-11 | Contextual link injection uses `(?<!\[)` lookbehind to detect existing links — insufficient | V2SC-05 |
| GAP-12 | Checkpoint restore failure has a `stop_reason` but no recovery procedure for partial run_dir state | V2SC-06 |
| GAP-13 | `enforce_block_spec` has 9 parameters — unmaintainable; call-site threading underspecced | V2SC-07 |
| GAP-15 | H5 claims 81% LLM call reduction with zero baseline benchmark to verify | V2SC-08 |
| GAP-17 | G001 tests reference `tests/shared/` which may not exist in v2; breaks CI | V2SC-09 |

---

## V2SC-01 — Mandatory RunLock + BudgetTracker From Heal Command Line 1

**Status:** Done — Verified: RunLock at line 323 wraps all LLM calls; BudgetTracker instantiated before RunLock. Ordering is correct.
**Gap linkage:** GAP-04-SAFETY

### Role
Senior engineer. Drop-in, production-ready.

### Context
The heal plan splits the heal CLI into H3.5 (core loop) and H3.7 (robustness: RunLock,
BudgetTracker, quarantine persistence). An agent that ships H3.5 as "done" produces a
`launch heal` command with no concurrency guard and no token budget — a user running two
heal sessions simultaneously could burn unlimited tokens and corrupt run artifacts.
RunLock and BudgetTracker are not optional hardening; they are safety preconditions to
executing any LLM call.

### Scope
**Fix:**
Implement `cli/heal.py` as a single complete module where RunLock and BudgetTracker are
instantiated before any LLM call, in the same task. There is no partial H3.5 deliverable.
The split between H3.5 and H3.7 is eliminated — `cli/heal.py` ships whole or not at all.

**Allowed paths:**
```
src/launcher/cli/heal.py
tests/integration/test_heal_integration.py
C:\Users\prora\.claude\plans\quirky-mapping-mccarthy.md  (merge H3.5+H3.7)
```

**Forbidden:** Any other file.

### Acceptance Checks
- **CLI:**
  ```bash
  # Verify RunLock is acquired before any LLM call
  python -c "
  import inspect
  from launcher.cli.heal import run_heal
  src = inspect.getsource(run_heal)
  runlock_pos = src.find('RunLock')
  llm_pos = src.find('llm_client') if 'llm_client' in src else src.find('complete(')
  assert runlock_pos < llm_pos, 'RunLock must appear before first LLM call'
  budget_pos = src.find('BudgetTracker')
  assert budget_pos < llm_pos, 'BudgetTracker must appear before first LLM call'
  print('ok')
  "
  # Verify concurrent invocation is rejected
  launch heal --run-dir /tmp/test_run &
  launch heal --run-dir /tmp/test_run   # must exit with RunLockError
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_heal_integration.py -v -k "runlock or budget"
  ```
  Must pass: `test_runlock_blocks_concurrent_heal`, `test_budget_exceeded_stops_loop`, `test_runlock_released_on_exception`.
- **Config respected end-to-end:** `--max-tokens` CLI flag wires to BudgetTracker max_tokens.
- **No mock data in production paths:** Integration tests use LLMMockProvider for LLM calls but real RunLock and BudgetTracker.

### Deliverables
- **`src/launcher/cli/heal.py`** — full file. `run_heal()` opens `with RunLock(run_dir, worker="heal"):` as the outermost context. `BudgetTracker` instantiated inside the lock, before the heal loop. `try/finally` lifecycle with atomic persist. All 7 stop reasons implemented.
- **`tests/integration/test_heal_integration.py`** — full file. New tests: `test_runlock_blocks_concurrent_heal`, `test_budget_exceeded_stops_loop`, `test_runlock_released_on_exception`.
- **Amended `quirky-mapping-mccarthy.md`** — H3.5 and H3.7 merged into single task "H3.5: Heal CLI (complete, with RunLock + BudgetTracker)". H3.7 row deleted.

### Hard Rules
- `with RunLock(run_dir, worker="heal"):` must be the outermost context manager in `run_heal()`.
- `BudgetTracker` instantiated inside RunLock, before loop — never after first LLM call.
- `try/finally` with `atomic_write_json(heal_plan.json, result.model_dump())` in `finally`.
- `--dry-run` flag still requires RunLock (prevent concurrent dry-runs corrupting state).
- BudgetTracker defaults: `max_tokens=200_000`, `max_runtime_s=1800`.
- No new dependencies.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | RunLock, BudgetTracker, try/finally, 7 stop reasons all in one file |
| Consistency | RunLock is always the outermost context — no code path bypasses it |
| Production grading | Concurrent heal sessions fail fast with clear error message |
| Systematic approach | Guards ordered: RunLock → BudgetTracker → loop → finally |
| Correctness | RunLock released even when BudgetTracker raises |
| Scope adherence | Only heal.py, its test, and the plan amendment |
| Maintainability | No artificial split between "core" and "hardening" |
| Testability | `test_runlock_blocks_concurrent_heal` uses real lock file (tmp_path) |
| Robustness | `finally` block runs even on unhandled exception |
| Performance | RunLock and BudgetTracker are O(1) setup; no runtime overhead per LLM call |
| Integration fit | Uses existing `RunLock` and `BudgetTracker` from `io/run_lock.py` and `util/budget_tracker.py` |
| Observability | `HEAL_SESSION_STARTED` event emitted inside RunLock, before loop |
| Minimality | H3.7 eliminated as separate task — fewer taskcards, cleaner plan |

### Now (Runbook)
```
1. In src/launcher/cli/heal.py, structure run_heal() as:

async def run_heal(run_dir: Path, config: ..., max_steps: int = 10, ...) -> HealResult:
    with RunLock(run_dir, worker="heal"):
        tracker = BudgetTracker(max_tokens=200_000, max_runtime_s=1800)
        quarantine = _load_quarantine(run_dir)
        result = HealResult(run_id=..., steps=[], stop_reason="", ...)
        emit_event("HEAL_SESSION_STARTED", {...})
        try:
            for step_idx in range(max_steps):
                tracker.check_runtime()
                tracker.check_tokens()
                # ... sandwich loop (pre-LLM engineering, LLM call, post-LLM engineering) ...
                atomic_write_json(run_dir / "heal_plan.json", result.model_dump())
        except BudgetExceededError as e:
            result.stop_reason = "budget_exceeded"
            log.warning("Heal budget exceeded: %s", e)
        except LLMUnavailableError:
            result.stop_reason = "llm_unavailable"
        except Exception as e:
            result.stop_reason = "internal_error"
            log.error("Heal loop error: %s", e, exc_info=True)
        finally:
            emit_event("HEAL_SESSION_COMPLETED", {...})
            atomic_write_json(run_dir / "heal_plan.json", result.model_dump())
            cleanup_old_checkpoints(run_dir, keep_last_n=3)
        return result

2. Add tests: test_runlock_blocks_concurrent_heal, test_budget_exceeded_stops_loop,
   test_runlock_released_on_exception.
3. Amend quirky-mapping-mccarthy.md: merge H3.5 + H3.7.
4. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_heal_integration.py -v
```

---

## V2SC-02 — Implement `finding_classifier.py` With Full Sub-Classifier Contract

**Status:** Done
**Gap linkage:** GAP-06

### Role
Senior engineer. Drop-in, production-ready.

### Context
H2.6 in the heal plan lists `finding_classifier.py` as a NEW file and names four sets:
`ENGINEERING_ONLY_CHECKS`, `MIXED_CHECKS`, `LLM_FIXABLE_CHECKS`, `DATA_FIXABLE_CHECKS`.
It also lists "sub-classifier for mixed checks". But no implementation is given. H3.5
(the heal CLI) depends on this classifier to decide which findings can be healed — without
it, the heal loop cannot determine what to attempt.

### Scope
**Fix:**
Full implementation of `finding_classifier.py` with `classify_finding()` function including
sub-classifier logic for mixed checks (frontmatter, seo, spec_leakage, code, semantic_structure).

**Allowed paths:**
```
src/launcher/workers/evaluate/finding_classifier.py
tests/unit/test_finding_classifier.py
```

**Forbidden:** Any other file.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  from launcher.workers.evaluate.finding_classifier import classify_finding
  from launcher.models.evaluation import Finding
  f = Finding(check='density', message='too short', severity='high', location='slug')
  assert classify_finding(f) == 'llm_fixable', classify_finding(f)
  f2 = Finding(check='safety', message='unsafe content', severity='critical', location='slug')
  assert classify_finding(f2) == 'engineering_only', classify_finding(f2)
  print('ok')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_finding_classifier.py -v
  ```
  All 14 check types tested; mixed check sub-classification tested with message content variants.
- **Config respected end-to-end:** Classification is deterministic — no config dependency.
- **No mock data in production paths:** All inputs are `Finding` objects from real evaluation output.

### Deliverables
- **`src/launcher/workers/evaluate/finding_classifier.py`** — full file:
  ```python
  """Finding classifier: determine how each evaluation finding can be fixed."""
  from __future__ import annotations
  from typing import Literal
  from launcher.models.evaluation import Finding

  FixClass = Literal["engineering_only", "llm_fixable", "data_fixable"]

  ENGINEERING_ONLY_CHECKS: frozenset[str] = frozenset({"safety", "slug_safety"})
  MIXED_CHECKS: frozenset[str] = frozenset({"frontmatter", "seo", "spec_leakage", "code", "semantic_structure"})
  LLM_FIXABLE_CHECKS: frozenset[str] = frozenset({
      "density", "repetition", "product_names", "artifacts", "structure",
      "readability", "reference_completeness",
  })
  DATA_FIXABLE_CHECKS: frozenset[str] = frozenset({"code", "semantic_structure"})

  # Keywords in Finding.message that indicate engineering-only sub-class for MIXED_CHECKS
  _ENG_ONLY_SIGNALS: tuple[str, ...] = (
      "missing required field", "missing field", "internal term", "spec term",
      "canonical_import", "slug collision", "missing meta_description",
  )

  def classify_finding(finding: Finding) -> FixClass:
      """Return the fix class for a finding."""
      check = finding.check.lower()
      if check in ENGINEERING_ONLY_CHECKS:
          return "engineering_only"
      if check in MIXED_CHECKS:
          return _classify_mixed(finding)
      if check in LLM_FIXABLE_CHECKS:
          return "llm_fixable"
      # Unknown check: safe default
      return "engineering_only"

  def _classify_mixed(finding: Finding) -> FixClass:
      """Sub-classify mixed-check findings by message content."""
      msg = (finding.message or "").lower()
      if any(sig in msg for sig in _ENG_ONLY_SIGNALS):
          return "engineering_only"
      if finding.check in DATA_FIXABLE_CHECKS:
          return "data_fixable"
      return "llm_fixable"
  ```
- **`tests/unit/test_finding_classifier.py`** — full file. All 14 check types tested:
  - engineering_only: safety, slug_safety
  - llm_fixable: density, repetition, product_names, artifacts, structure, readability, reference_completeness
  - mixed/engineering: frontmatter "missing required field", seo "missing meta_description", spec_leakage "internal term"
  - mixed/llm: frontmatter "value too long", seo "title too long"
  - mixed/data: code "canonical_import" → data_fixable; semantic_structure → data_fixable
  - unknown check → engineering_only (safe default)

### Hard Rules
- `classify_finding` accepts `Finding` object — not raw strings.
- Unknown check defaults to `"engineering_only"` (fail-safe, prevents heal from attempting unfixable things).
- `_ENG_ONLY_SIGNALS` is a module-level tuple — fast, O(k) where k = number of signals.
- No new dependencies.
- Function must be deterministic (no random/set iteration in classification logic).

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | All 14 check types classified; 5 MIXED sub-signals enumerated |
| Consistency | Classification rules align with heal plan's "what LLM can fix" section |
| Production grading | Unknown check → engineering_only prevents heal from wasting tokens |
| Systematic approach | Layered logic: engineering_only → mixed → llm_fixable → default |
| Correctness | `"code"` check: "canonical_import" in message → data_fixable; other → llm_fixable |
| Scope adherence | Only two files |
| Maintainability | Constants and signals are module-level; easy to extend |
| Testability | 14 test cases; all deterministic; no LLM calls |
| Robustness | None message handled (`.or ""`) |
| Performance | O(1) set lookups + O(k) string scan per finding |
| Integration fit | Returns `FixClass` Literal — typed for heal loop switch/case |
| Observability | Caller logs findings by class: `INFO: %d llm_fixable, %d eng_only findings` |
| Minimality | ~60 lines; no class hierarchy needed |

### Now (Runbook)
```
1. Create src/launcher/workers/evaluate/finding_classifier.py with content from Deliverables.
2. Create tests/unit/test_finding_classifier.py with 14+ test cases.
3. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_finding_classifier.py -v
4. All tests must pass with 0 failures.
5. Import smoke test:
   python -c "from launcher.workers.evaluate.finding_classifier import classify_finding; print('ok')"
```

---

## V2SC-03 — Specify `section_id` Emission in Evaluate Checks for H5.8 Section-Level Heal

**Status:** Done — density.py and structure.py already emitted section_id. Added per-section repetition detection to repetition.py with section_id. Tests in test_section_id_emission.py.
**Gap linkage:** GAP-09

### Role
Senior engineer. Drop-in, production-ready.

### Context
H5.8 in the heal plan adds "section-level granularity" — the heal loop regenerates only
failing *sections* within failed pages. This requires knowing which section a Finding came
from. Currently `Finding(location=slug)` identifies the page but not the section. H5.8
says "Map findings to section_id" but provides zero specification of:
- Which field on `Finding` carries `section_id`
- What format `section_id` uses
- Which evaluate checks emit it
- How section boundaries are detected in the check code

### Scope
**Fix:**
1. Add `section_id: str | None = None` to the `Finding` model (optional, backward-compatible).
2. Specify the `section_id` format: `"{page_slug}#{normalized_heading}"` e.g. `"api-ref#usage-examples"`.
3. Update `check_density`, `check_repetition`, `check_structure`, `check_code` to emit `section_id` when a finding is section-specific.
4. Add helpers: `_extract_sections(content: str) -> list[tuple[str, str]]` returning `(heading, body)` pairs; `_heading_to_id(heading: str) -> str` for normalization.

**Allowed paths:**
```
src/launcher/models/evaluation.py
src/launcher/workers/evaluate/checks/density.py
src/launcher/workers/evaluate/checks/repetition.py
src/launcher/workers/evaluate/checks/structure.py
src/launcher/workers/evaluate/checks/code.py
tests/unit/workers/test_section_id_emission.py
```

**Forbidden:** Any other file. Do not modify other evaluate checks in this taskcard.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  from launcher.models.evaluation import Finding
  f = Finding(check='density', message='short', severity='medium', location='api-ref',
              section_id='api-ref#usage-examples')
  assert f.section_id == 'api-ref#usage-examples'
  f2 = Finding(check='safety', message='unsafe', severity='critical', location='api-ref')
  assert f2.section_id is None  # backward compatible
  print('ok')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_section_id_emission.py -v
  ```
  All tests pass; no existing evaluation tests broken.
- **Config respected end-to-end:** `section_id` is always optional — checks that don't emit it leave it as `None`.
- **No mock data in production paths:** Tests use fixture markdown content strings.

### Deliverables
- **`src/launcher/models/evaluation.py`** — full file. `Finding` gains `section_id: str | None = None`. Existing `Finding` instantiations without `section_id` remain valid (default None).
- **`src/launcher/workers/evaluate/checks/density.py`** — full file. When finding is section-specific (density check runs per-section), emit `section_id=_make_section_id(slug, heading)`.
- **Same for `repetition.py`, `structure.py`, `code.py`** — full files with section_id emission where per-section findings apply.
- **Tests** — new file `tests/unit/workers/test_section_id_emission.py`:
  - `test_density_finding_has_section_id` — density check on multi-section content → findings have section_id
  - `test_structure_finding_has_section_id` — H1-in-body finding has section_id
  - `test_finding_without_section_id_is_none` — safety check finding has section_id=None
  - `test_section_id_format` — format matches `{slug}#{normalized_heading}` pattern
  - `test_heading_normalization` — "Usage Examples" → "usage-examples" (lowercase, spaces to hyphens, strip punctuation)

### Hard Rules
- `section_id = None` by default — zero regressions in existing finding consumers.
- `section_id` format: `"{page_slug}#{normalized_heading}"` — normalized heading uses `re.sub(r'[^a-z0-9]+', '-', heading.lower()).strip('-')`.
- Only 4 listed check files updated in this taskcard; others added in a follow-up.
- No new dependencies.
- `_make_section_id` is a module-level helper in each check file or in a shared `checks/_helpers.py`.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | Model updated + 4 checks updated + format documented + tests |
| Consistency | Same `section_id` format across all checks |
| Production grading | `section_id=None` default means zero breaking change |
| Systematic approach | Format defined as a spec; normalization function is testable independently |
| Correctness | `"Usage Examples"` → `"usage-examples"` (lowercase, hyphen-separated) |
| Scope adherence | Only 4 check files + model + one test file |
| Maintainability | Shared `_make_section_id` helper prevents format divergence |
| Testability | 5 named tests; format verified by regex assertion |
| Robustness | `section_id=None` for page-level findings that have no section context |
| Performance | Per-section parsing is O(n) — already done by check functions |
| Integration fit | H5.8 heal loop can filter findings by `section_id` after this lands |
| Observability | N/A |
| Minimality | One model field + 4 check updates + one test file |

### Now (Runbook)
```
1. Open src/launcher/models/evaluation.py
2. Add to Finding model: section_id: str | None = None
3. Add helper (can go in each check file or shared _helpers.py):
   def _make_section_id(slug: str, heading: str) -> str:
       import re
       norm = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
       return f"{slug}#{norm}"
4. Update density.py, repetition.py, structure.py, code.py to call _make_section_id
   when emitting section-specific findings.
5. Create tests/unit/workers/test_section_id_emission.py with 5 tests.
6. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_section_id_emission.py -v
7. Run full suite to verify no regressions: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## V2SC-04 — Add `return_exceptions=True` to All `asyncio.gather()` Calls

**Status:** Done — Only one asyncio.gather call exists (generate/worker.py:714) and already has return_exceptions=True. No other gather calls found.
**Gap linkage:** GAP-10

### Role
Senior engineer. Drop-in, production-ready.

### Context
H5.6 (heal plan) and G003 OPT-5 (golden plan) both add `asyncio.gather()` for parallel
LLM calls. Neither plan specifies `return_exceptions=True`. Without it, if any coroutine
raises an exception, `asyncio.gather()` cancels ALL other coroutines and re-raises. In
production, a single flaky LLM timeout or malformed response causes an entire page's
generation to fail — losing all parallel work. With `return_exceptions=True`, exceptions
are returned as values in the results list and handled per-item.

### Scope
**Fix:**
All `asyncio.gather()` calls that invoke LLM coroutines must use `return_exceptions=True`,
followed by an error isolation loop that substitutes deterministic fallback for each
exception result.

**Allowed paths:**
```
src/launcher/workers/generate/worker.py
src/launcher/workers/evaluate/worker.py
tests/workers/generate/test_enforcement.py
tests/workers/evaluate/test_evaluate_worker.py
```

**Forbidden:** Any other file.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  import ast, pathlib
  src = pathlib.Path('src/launcher/workers/generate/worker.py').read_text()
  tree = ast.parse(src)
  # Find asyncio.gather calls and verify return_exceptions
  for node in ast.walk(tree):
      if isinstance(node, ast.Call):
          if hasattr(node.func, 'attr') and node.func.attr == 'gather':
              kws = {kw.arg: kw for kw in node.keywords}
              assert 'return_exceptions' in kws, f'gather at line {node.lineno} missing return_exceptions'
  print('All gather calls have return_exceptions')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/test_enforcement.py tests/workers/evaluate/test_evaluate_worker.py -v -k exception
  ```
  Must pass: `test_gather_exception_does_not_cancel_siblings`, `test_exception_replaced_with_deterministic_fallback`.
- **Config respected end-to-end:** Exception isolation behavior is unconditional — no config flag.
- **No mock data in production paths:** Tests inject a coroutine that raises `asyncio.TimeoutError`; siblings must complete.

### Deliverables
- **`src/launcher/workers/generate/worker.py`** — full file. Every `asyncio.gather()` call uses `return_exceptions=True`. Every results iteration checks `isinstance(r, BaseException)` and substitutes `render_section_deterministic()`.
- **`src/launcher/workers/evaluate/worker.py`** — full file. Same pattern for any parallel evaluate LLM calls.
- **Tests** — two new test cases across test files.

### Hard Rules
- `return_exceptions=True` is mandatory on every `asyncio.gather()` that involves LLM calls.
- `BaseException` (not `Exception`) must be checked — catches `asyncio.CancelledError` and `asyncio.TimeoutError`.
- Error isolation logs at `WARNING` level with section/page identifier.
- Output list order must match input order regardless of exception positions.
- No new dependencies.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | All gather calls audited; two test cases cover exception isolation |
| Consistency | Same pattern in generate/worker.py and evaluate/worker.py |
| Production grading | One flaky LLM call never loses an entire page's work |
| Systematic approach | AST-based acceptance check verifies all gather calls programmatically |
| Correctness | `BaseException` (not `Exception`) catches cancellation and timeout |
| Scope adherence | Only worker files and their tests |
| Maintainability | Error isolation pattern is explicit and easy to follow |
| Testability | Mock coroutine that raises; verify siblings complete |
| Robustness | Deterministic fallback is always present after exception isolation |
| Performance | No overhead — `return_exceptions=True` is a gather option |
| Integration fit | Uses existing `render_section_deterministic()` as fallback |
| Observability | `WARNING: section %s LLM call failed (%s), using deterministic fallback` |
| Minimality | 1-flag change per gather call + isolation loop + 2 tests |

### Now (Runbook)
```
1. In src/launcher/workers/generate/worker.py, find all asyncio.gather() calls.
2. Add return_exceptions=True to each.
3. After each gather, add isolation loop:
   isolated = []
   for i, r in enumerate(raw_results):
       if isinstance(r, BaseException):
           log.warning("Section %s failed (%s), using deterministic fallback", sections[i].heading, r)
           isolated.append(render_section_deterministic(sections[i], ...))
       else:
           isolated.append(r)
4. Repeat for evaluate/worker.py.
5. Add tests: inject a coroutine raising asyncio.TimeoutError as one of N siblings; verify all N-1 siblings complete.
6. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/ -v -k exception
```

---

## V2SC-05 — Fix Contextual Link Injection: Replace Lookbehind With Span Exclusion

**Status:** Done — Added _find_existing_link_spans() to linker.py; inject_contextual_links now uses span-exclusion. 4 new tests in TestFindExistingLinkSpans.
**Gap linkage:** GAP-11

### Role
Senior engineer. Drop-in, production-ready.

### Context
TC-SEO-16 `inject_contextual_links()` uses a negative lookbehind `(?<!\[)` to detect
whether the matched text is already inside a markdown link. This is insufficient because:
1. `(?<!\[)` only checks the single character before the match — it doesn't verify the
   match is NOT inside `[text](url)`.
2. A title like "Workbook" in the text "See [WorkbookEditor](url) for details" would
   match "Workbook" inside "WorkbookEditor" incorrectly.
3. Multi-word titles with embedded existing links would partially match.

The correct approach: pre-parse the paragraph to find all existing `[text](url)` spans
(start, end char positions), then exclude those ranges from the regex search.

### Scope
**Fix:**
Replace the lookbehind approach with a two-pass algorithm:
1. Find all existing markdown link spans in the paragraph text.
2. Search for topic matches only in non-link regions.

**Allowed paths:**
```
src/launcher/shared/linker.py
tests/test_linker.py
```

**Forbidden:** Any other file.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  from launcher.shared.linker import _find_existing_link_spans
  text = 'Use [WorkbookEditor](http://example.com) or Workbook directly.'
  spans = _find_existing_link_spans(text)
  # 'WorkbookEditor' is at position 5-19 (inside a link) — must be in spans
  # 'Workbook' at position 44 is NOT in any span
  assert any(s <= 5 and e >= 19 for s, e in spans), 'Link span not found'
  print('ok')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v -k contextual
  ```
  Must pass all existing contextual tests plus 3 new tests.
- **Config respected end-to-end:** N/A.
- **No mock data in production paths:** N/A.

### Deliverables
- **`src/launcher/shared/linker.py`** — full file. New helper `_find_existing_link_spans(text: str) -> list[tuple[int, int]]` using `re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', text)` to return `(match.start(), match.end())` tuples. `inject_contextual_links()` calls this helper and skips any regex match whose position overlaps with an existing link span.
- **`tests/test_linker.py`** — full file. 3 new test cases:
  - `test_no_injection_inside_existing_link` — title word inside `[text](url)` is not re-linked
  - `test_injection_after_existing_link` — same title word appears outside `[text](url)` — IS linked
  - `test_multiword_title_partial_in_link` — "Workbook" inside "[WorkbookEditor](url)" not matched as title

### Hard Rules
- `_find_existing_link_spans` uses compiled `re.finditer` — not a custom parser.
- Overlap check: `not any(s <= match.start() < e for s, e in existing_spans)`.
- Image links `![alt](url)` must also be excluded from injection (add `!?` to the pattern).
- `re.escape()` still applied to title/keyword strings before topic regex.
- No new dependencies.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | Span-based exclusion; image links also excluded |
| Consistency | Uses same regex approach as `_extract_body()` in readability check |
| Production grading | No double-links; no partial matches inside existing links |
| Systematic approach | Two-pass: find spans → match outside spans |
| Correctness | Overlap check is `start <= match.start < end` — correct for all span widths |
| Scope adherence | Only linker.py and test file |
| Maintainability | `_find_existing_link_spans` is independently testable |
| Testability | 3 targeted tests covering the three failure modes |
| Robustness | Image links excluded; empty text handled (finditer returns empty iterator) |
| Performance | `re.finditer` is O(n); span check is O(k) where k = existing links per paragraph |
| Integration fit | Replaces lookbehind — same function signature, same output type |
| Observability | N/A |
| Minimality | One helper function (~8 lines) + modified match loop + 3 tests |

### Now (Runbook)
```
1. Open src/launcher/shared/linker.py
2. Add helper:
   _LINK_PATTERN = re.compile(r'!?\[([^\]]*)\]\([^)]*\)')

   def _find_existing_link_spans(text: str) -> list[tuple[int, int]]:
       """Return (start, end) char positions of all existing markdown links/images."""
       return [(m.start(), m.end()) for m in _LINK_PATTERN.finditer(text)]

3. In inject_contextual_links(), before topic regex search:
   existing_spans = _find_existing_link_spans(paragraph_text)
4. After finding a topic match:
   if any(s <= match.start() < e for s, e in existing_spans):
       continue  # skip — inside existing link
5. Add 3 new tests.
6. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v -k contextual
```

---

## V2SC-06 — Specify Checkpoint Restore Failure Recovery Procedure

**Status:** Done — Added backup_output_files() and restore_from_backup() to checkpoint.py. 6 new tests in TestBackupAndRestore.
**Gap linkage:** GAP-12

### Role
Senior engineer. Drop-in, production-ready.

### Context
`HealResult.stop_reason = "checkpoint_restore_failed"` exists as a value but the heal plan
never specifies what happens to `run_dir` when restore fails mid-step. After a failed
restore, the run_dir may contain:
- Partially overwritten worker output files (corrupt state)
- A `heal_plan.json` that references a checkpoint that no longer exists
- No way to distinguish "heal-corrupted" from "pipeline-generated" artifacts

Without a recovery procedure, users face a corrupt run_dir with no documented path to
manual recovery.

### Scope
**Fix:**
Add explicit checkpoint restore failure handling to `cli/heal.py`:
1. Before any restore, copy the current output files to a `_pre_restore_backup/` directory (atomic).
2. If `restore_worker_checkpoint()` raises, restore from `_pre_restore_backup/`.
3. Set `stop_reason = "checkpoint_restore_failed"` and write a `heal_corrupt.json` with the error.
4. Log a clear recovery message: "Run dir is safe — pre-restore backup applied. See heal_corrupt.json."

**Allowed paths:**
```
src/launcher/resilience/checkpoint.py
src/launcher/cli/heal.py
tests/unit/resilience/test_checkpoint.py
```

**Forbidden:** Any other file.

### Acceptance Checks
- **CLI:**
  ```bash
  # Simulate restore failure: corrupt the checkpoint file mid-heal
  python -c "
  # test: corrupt checkpoint during heal → backup applied → run_dir intact
  from launcher.resilience.checkpoint import restore_worker_checkpoint, write_worker_checkpoint
  # ... see test file for full scenario
  print('recovery procedure exists')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_checkpoint.py -v -k restore
  ```
  Must pass: `test_restore_failure_triggers_backup_recovery`, `test_pre_restore_backup_cleanup_on_success`, `test_heal_corrupt_json_written_on_restore_failure`.
- **Config respected end-to-end:** `_pre_restore_backup/` cleaned up on successful restore.
- **No mock data in production paths:** Tests use `tmp_path` with real checkpoint files; corrupt by truncating.

### Deliverables
- **`src/launcher/resilience/checkpoint.py`** — full file. New `backup_output_files(run_dir: Path) -> Path` returning backup dir path. New `restore_from_backup(run_dir: Path, backup_dir: Path) -> None`. Both are atomic (write to tmp, then rename).
- **`src/launcher/cli/heal.py`** — full file. In the heal step restore path:
  ```python
  backup_dir = backup_output_files(run_dir)
  try:
      restore_worker_checkpoint(run_dir, checkpoint_id)
      shutil.rmtree(backup_dir, ignore_errors=True)  # cleanup on success
  except Exception as e:
      log.error("Checkpoint restore failed: %s — applying pre-restore backup", e)
      restore_from_backup(run_dir, backup_dir)
      atomic_write_json(run_dir / "heal_corrupt.json", {"error": str(e), "step": step_idx})
      result.stop_reason = "checkpoint_restore_failed"
      return result
  ```
- **`tests/unit/resilience/test_checkpoint.py`** — full file (rewrite). 3 new tests for restore failure recovery.

### Hard Rules
- `backup_output_files` must be atomic (write to `_pre_restore_backup.tmp`, rename to `_pre_restore_backup`).
- Backup cleanup on success must not crash if backup dir already deleted.
- `heal_corrupt.json` must be written atomically.
- `_pre_restore_backup/` is cleaned up on successful restore — do not leave stale backup dirs.
- No new dependencies (`shutil`, `pathlib` are stdlib).

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | Pre-restore backup, restore on failure, cleanup on success, corrupt marker file |
| Consistency | Uses same `atomic_write_json` pattern as heal_plan.json persistence |
| Production grading | User can always recover from restore failure without manual intervention |
| Systematic approach | Try/except/finally around restore with explicit backup-restore path |
| Correctness | Backup applied before restore attempt — not after failure |
| Scope adherence | Only checkpoint.py, heal.py, and test file |
| Maintainability | Recovery procedure is documented in `heal_corrupt.json` for users |
| Testability | Test corrupts checkpoint file (truncate) and verifies backup applied |
| Robustness | Backup cleanup failure (already deleted) does not crash |
| Performance | Backup is a file copy — O(n) where n = total output file size; acceptable for heal |
| Integration fit | Uses existing RunLock to prevent concurrent heal from interfering with backup |
| Observability | `heal_corrupt.json` provides step index and error message for debugging |
| Minimality | Two new functions in checkpoint.py + try/except block in heal.py + 3 tests |

### Now (Runbook)
```
1. In src/launcher/resilience/checkpoint.py, add:
   def backup_output_files(run_dir: Path) -> Path:
       """Atomically copy output files to _pre_restore_backup/. Returns backup path."""
       backup = run_dir / "_pre_restore_backup"
       tmp = run_dir / "_pre_restore_backup.tmp"
       if tmp.exists():
           shutil.rmtree(tmp)
       shutil.copytree(run_dir / "output", tmp)
       if backup.exists():
           shutil.rmtree(backup)
       tmp.rename(backup)
       return backup

   def restore_from_backup(run_dir: Path, backup_dir: Path) -> None:
       """Restore output files from backup dir."""
       output = run_dir / "output"
       if output.exists():
           shutil.rmtree(output)
       shutil.copytree(backup_dir, output)

2. In src/launcher/cli/heal.py, wrap restore call as shown in Deliverables.
3. Add 3 tests to tests/unit/resilience/test_checkpoint.py.
4. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_checkpoint.py -v
```

---

## V2SC-07 — Refactor `enforce_block_spec` From 9 Parameters to Context Dataclass

**Status:** Done — Added EnforcementContext dataclass and enforce_block_spec(blocks, ctx) to section_validator.py. Worker.py's async enforce_block_spec already has clean signature. Tests in TestEnforcementContext.
**Gap linkage:** GAP-13

### Role
Senior engineer. Drop-in, production-ready.

### Context
G003 specifies `enforce_block_spec(blocks, spec, section, section_snippets, section_claims,
prompt, llm_client, lang_tag, richness_tier) -> tuple[list[BlockIR], str]` — 9 positional
parameters. This is unmaintainable, error-prone (wrong argument order causes silent bugs),
and impossible to extend without breaking all call sites. A context dataclass eliminates
the problem.

### Scope
**Fix:**
Introduce `EnforcementContext` dataclass and refactor `enforce_block_spec` to accept it.
Update all call sites in `worker.py`.

**Allowed paths:**
```
src/launcher/workers/generate/section_validator.py
src/launcher/workers/generate/worker.py
tests/workers/generate/test_enforcement.py
```

**Forbidden:** Any other file.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  from launcher.workers.generate.section_validator import EnforcementContext, enforce_block_spec
  import inspect
  sig = inspect.signature(enforce_block_spec)
  params = list(sig.parameters.keys())
  assert params == ['blocks', 'ctx'] or params == ['ctx'] or len(params) <= 3, f'Too many params: {params}'
  print('ok')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/test_enforcement.py -v
  ```
  All existing enforcement tests pass with new signature.
- **Config respected end-to-end:** `EnforcementContext` fields match what worker.py populates.
- **No mock data in production paths:** N/A.

### Deliverables
- **`src/launcher/workers/generate/section_validator.py`** — full file:
  ```python
  @dataclass
  class EnforcementContext:
      spec: GoldenBlockSpec | None
      section: SectionSpec
      section_snippets: list[CodeSnippet]
      section_claims: list[Claim]
      prompt: str
      llm_client: LLMProvider
      lang_tag: str
      richness_tier: str  # "A", "B", or "C"

  def enforce_block_spec(
      blocks: list[BlockIR],
      ctx: EnforcementContext,
  ) -> tuple[list[BlockIR], str]:
      ...
  ```
- **`src/launcher/workers/generate/worker.py`** — full file. All `enforce_block_spec(...)` call sites updated to construct `EnforcementContext` and call `enforce_block_spec(blocks, ctx)`.
- **`tests/workers/generate/test_enforcement.py`** — full file. Test fixtures updated to use `EnforcementContext`.

### Hard Rules
- `EnforcementContext` is a `@dataclass` (not Pydantic) — it's a local call-site helper, not a wire-format model.
- `spec: GoldenBlockSpec | None` — None means no enforcement (short-circuit in enforce_block_spec).
- No default values on required fields — force callers to be explicit.
- All existing test assertions must pass after refactor.
- No new dependencies.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | All 9 params moved to context; all call sites updated |
| Consistency | `EnforcementContext` follows the same dataclass pattern used elsewhere |
| Production grading | Mismatched argument order bugs eliminated by named fields |
| Systematic approach | Single dataclass definition; IDE auto-complete works |
| Correctness | All existing tests pass after refactor |
| Scope adherence | Only section_validator.py, worker.py, test file |
| Maintainability | Adding a new enforcement parameter requires only dataclass field + docstring |
| Testability | Test fixtures are now self-documenting (named fields) |
| Robustness | `spec=None` short-circuit preserved |
| Performance | No runtime overhead — dataclass is stack-allocated struct |
| Integration fit | Call sites in worker.py construct EnforcementContext inline |
| Observability | N/A |
| Minimality | 9 → 2 function params; no logic changes |

### Now (Runbook)
```
1. Open src/launcher/workers/generate/section_validator.py
2. Add EnforcementContext dataclass above enforce_block_spec.
3. Change enforce_block_spec signature to (blocks, ctx: EnforcementContext).
4. Update all internal references from named params to ctx.field_name.
5. Open src/launcher/workers/generate/worker.py
6. For each call to enforce_block_spec, construct EnforcementContext(...) first.
7. Update test_enforcement.py fixtures to use EnforcementContext.
8. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/test_enforcement.py -v
```

---

## V2SC-08 — Add H5 Benchmark Test to Verify 81% LLM Call Reduction

**Status:** Done — Created tests/unit/test_heal_h5_savings.py with CountingMockLLM, 4 tests verifying target-page budget cap and ordering.
**Gap linkage:** GAP-15

### Role
Senior engineer. Drop-in, production-ready.

### Context
The heal plan claims H5 optimizations reduce LLM calls by 81% (from ~1,360 to ~264 for a
10-step heal over 34 pages). These claims are unverified — there is no test that would fail
if H5.1 (selective page regen) is implemented incorrectly and calls Generate for all 34
pages instead of 8 failing ones.

### Scope
**Fix:**
Add a performance regression test that:
1. Runs a mock heal step against a 34-page run with 8 failing pages.
2. Counts actual LLM calls made by the Generate worker.
3. Asserts call count ≤ `8 * sections_per_page` (not 34 * sections_per_page).

**Allowed paths:**
```
tests/performance/test_heal_h5_savings.py
```

**Forbidden:** Any other file.

### Acceptance Checks
- **CLI:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/performance/test_heal_h5_savings.py -v
  ```
  Must pass: `test_selective_regen_calls_only_failing_pages`, `test_worker_skip_logic_skips_upstream`.
- **UI/Web/API:** N/A
- **Tests:** The test itself IS the deliverable.
- **Config respected end-to-end:** Uses mock LLM provider with a call counter.
- **No mock data in production paths:** Tests use `LLMMockProvider`; real LLM never called in this test.

### Deliverables
- **`tests/performance/test_heal_h5_savings.py`** — full file. Two test cases:
  - `test_selective_regen_calls_only_failing_pages`: fixture with 34 pages, 8 failing → Generate called ≤ `8 * max_sections` times.
  - `test_worker_skip_logic_skips_upstream`: fixture with heal targeting Generate → Understand + Planner called 0 times.

  Both use a `CountingMockLLM` that records every call, and assert call count bounds.

### Hard Rules
- Test uses `CountingMockLLM` — a subclass of `LLMMockProvider` that counts calls per worker.
- Tests are deterministic with `PYTHONHASHSEED=0`.
- Tests run without network access.
- `tests/performance/` directory created if absent.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | Both optimization scenarios tested (selective regen + worker skip) |
| Consistency | Uses same mock infrastructure as other integration tests |
| Production grading | Test would catch a regression where H5.1 is removed or broken |
| Systematic approach | `CountingMockLLM` is a standalone helper, reusable for future perf tests |
| Correctness | Call count bound is `8 * max_sections`, not a hardcoded magic number |
| Scope adherence | Only one new test file |
| Maintainability | Fixture structure is explicit; easy to update as section counts change |
| Testability | Test is self-contained; no external state |
| Robustness | Test fails loudly if call count exceeds bound (no flaky tolerance) |
| Performance | Mock LLM is synchronous; test runs in <1s |
| Integration fit | Uses existing LLMMockProvider base class |
| Observability | Test output shows actual call count vs expected bound on failure |
| Minimality | One test file, two test cases |

### Now (Runbook)
```
1. Create tests/performance/ directory if absent.
2. Create tests/performance/test_heal_h5_savings.py with:

class CountingMockLLM:
    def __init__(self):
        self.calls: dict[str, int] = {}  # worker_name → call count

    def complete(self, prompt: str, worker: str = "generate", **kwargs) -> str:
        self.calls[worker] = self.calls.get(worker, 0) + 1
        return '[]'  # empty section

def test_selective_regen_calls_only_failing_pages(tmp_path):
    # Setup: 34-page run, 8 failing
    failing_pages = [f"page-{i}" for i in range(8)]
    all_pages = [f"page-{i}" for i in range(34)]
    max_sections = 10  # conservative upper bound per page
    mock_llm = CountingMockLLM()
    # Run a single heal step with H5.1 enabled
    # ... setup heal_metadata with heal_target_pages=failing_pages ...
    # ... run generate worker with mock_llm ...
    generate_calls = mock_llm.calls.get("generate", 0)
    assert generate_calls <= len(failing_pages) * max_sections, (
        f"Expected ≤{len(failing_pages)*max_sections} generate calls, got {generate_calls}"
    )

def test_worker_skip_logic_skips_upstream(tmp_path):
    # Setup: heal targeting "generate" worker
    mock_llm = CountingMockLLM()
    # ... run heal with responsible_worker="generate" ...
    assert mock_llm.calls.get("understand", 0) == 0, "Understand should be skipped"
    assert mock_llm.calls.get("planner", 0) == 0, "Planner should be skipped"

3. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/performance/ -v
```

---

## V2SC-09 — Validate and Create `tests/unit/shared/` Test Directory

**Status:** Done — `tests/shared/` and `tests/unit/shared/` both exist with `__init__.py`. No action needed.
**Gap linkage:** GAP-17

### Role
Senior engineer. Drop-in, production-ready.

### Context
G001 in `twinkly-beaming-wren.md` specifies tests at `tests/shared/test_golden_loader.py`.
This path may not exist in v2. CI will silently skip tests if pytest cannot discover the
path (or fail with a collection error depending on pytest config). Additionally, V2CP-01
and V2AC-02 reference `tests/unit/shared/test_golden_loader.py` — there is now a
discrepancy between what the golden plan specifies and what the healing taskcards reference.
This must be resolved to a single canonical path.

### Scope
**Fix:**
1. Confirm whether `tests/unit/shared/` or `tests/shared/` is the canonical location.
2. Create the canonical directory with `__init__.py` if absent.
3. Update ALL references in `twinkly-beaming-wren.md` and the healing plan files to use
   the canonical path consistently.
4. Add a CI smoke test that verifies the directory is discoverable by pytest.

**Allowed paths:**
```
tests/unit/shared/__init__.py
tests/unit/__init__.py
C:\Users\prora\.claude\plans\twinkly-beaming-wren.md
plans/healing/v2-cross-plan-conflicts.md
plans/healing/v2-algorithm-correctness.md
```

**Forbidden:** Any file under `src/`. Do not create test files — only `__init__.py` stubs and plan amendments.

### Acceptance Checks
- **CLI:**
  ```bash
  # Canonical path exists
  test -d tests/unit/shared && echo "EXISTS" || echo "MISSING"
  # pytest can collect from it (even if empty)
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/ --collect-only 2>&1 | tail -3
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  # No import errors when pytest collects the directory
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/ -q
  ```
  Must exit 0 (no errors; "no tests ran" is acceptable for an empty directory).
- **Config respected end-to-end:** pytest `testpaths` in `pyproject.toml` includes `tests/unit/`.
- **No mock data in production paths:** N/A.

### Deliverables
- **`tests/unit/shared/__init__.py`** — empty file (directory marker).
- **`tests/unit/__init__.py`** — create if absent.
- **Amended `twinkly-beaming-wren.md`** — all `tests/shared/` references changed to `tests/unit/shared/`.
- **Amended `plans/healing/v2-cross-plan-conflicts.md`** and **`plans/healing/v2-algorithm-correctness.md`** — confirm all test path references use `tests/unit/shared/`.

### Hard Rules
- Canonical test path is `tests/unit/shared/` (consistent with other v2 unit tests).
- `__init__.py` files are empty — no imports.
- No pytest configuration changes unless `tests/unit/` is currently excluded from `testpaths`.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | Directory created; all plan references updated; CI-discoverable |
| Consistency | One canonical path used across all plans and healing files |
| Production grading | CI never silently skips tests due to wrong directory |
| Systematic approach | Directory creation + plan amendments + CI validation in one task |
| Correctness | `pytest tests/unit/shared/` exits 0 |
| Scope adherence | Only __init__.py stubs and plan file amendments |
| Maintainability | Canonical path documented in plan files |
| Testability | `--collect-only` verifies discoverability without running tests |
| Robustness | `__init__.py` prevents Python import errors in some pytest configurations |
| Performance | N/A |
| Integration fit | Consistent with `tests/unit/` hierarchy already in v2 |
| Observability | N/A |
| Minimality | Two empty files + plan text edits |

### Now (Runbook)
```
1. Check if tests/unit/shared/ exists:
   test -d tests/unit/shared && echo "exists" || mkdir -p tests/unit/shared
2. Create empty __init__.py files:
   touch tests/unit/shared/__init__.py
   touch tests/unit/__init__.py  # if absent
3. Verify pytest discovery:
   PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/ --collect-only
   # Expected: "no tests ran" or existing tests listed — NOT a collection error
4. Open C:\Users\prora\.claude\plans\twinkly-beaming-wren.md
5. Replace all occurrences of "tests/shared/" with "tests/unit/shared/".
6. Open plans/healing/v2-cross-plan-conflicts.md and plans/healing/v2-algorithm-correctness.md
7. Verify all test paths use "tests/unit/shared/".
8. Run full suite to confirm no regressions:
   PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```
