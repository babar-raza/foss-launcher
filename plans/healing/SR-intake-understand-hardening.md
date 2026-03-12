# Healing Plan: Intake + Understand Phase Hardening

Generated from self-review of TC-4057 + TC-4058 (2026-03-11)

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-01 | `_FAMILIES_YAML` relative path breaks when CWD ≠ repo root | SR-01 |
| G-02 | Test file `test_understand.py` has duplicate class definitions from append-mode bug | SR-02 |
| G-03 | `TestExtractProductEvidenceErrorHandling` patches wrong module namespace | SR-02 |
| G-04 | `_resolve_identity()` returns bare 4-tuple instead of typed NamedTuple | SR-03 |
| G-05 | families.yaml re-read on every `_resolve_identity()` call — no caching | SR-04 |
| G-06 | Phase B.5 ERROR log lacks `family`/`platform`/`repo_url` structured fields | SR-05 |
| G-07 | No actual pipeline run on fixture repos — manual verification was function-level only | SR-06 |
| G-08 | Scout integration test missing — no test runs real `run_scout()` on temp directory | SR-07 |

---

## SR-01 — Fix `_FAMILIES_YAML` relative path

**Status:** Not Started
**Gap linkage:** G-01
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Change `_FAMILIES_YAML = Path("configs/families.yaml")` in `worker.py` to be resolved
relative to the source file's `__file__` location so the path is correct regardless of the
working directory when the pipeline is invoked.

**Allowed paths:**
- `src/launcher/workers/intake/worker.py`
- `tests/unit/workers/test_intake.py`

**Forbidden:** Any other file or path.

### Acceptance checks

- **CLI:** `cd /tmp && python -c "from launcher.workers.intake.worker import _resolve_identity; r = _resolve_identity('cells', 'python'); print(r[3])"` returns `{'display_name': 'families_yaml', ...}` (not all `'inferred_default'`)
- **Tests:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v` — all 45 pass
- **Config respected end-to-end:** families.yaml still loads correctly when invoked from repo root (existing behavior unchanged)
- **No mock data in production paths:** `_FAMILIES_YAML` resolution is live path, not hardcoded stub

### Deliverables

- Full replacement of `src/launcher/workers/intake/worker.py` with `__file__`-relative path
- Add test `test_resolve_identity_from_arbitrary_cwd` that temporarily changes CWD to a tmp dir and asserts provenance is `families_yaml` (not `inferred_default`)
- No new dependencies

### Hard rules

- Do not change `IntakeBundle` model or any downstream contract
- `_resolve_identity()` signature must remain identical (same 4-tuple return)
- No network in tests
- All 45 existing tests must still pass

### Review dimensions (5/5 means)

- **Correctness:** `_resolve_identity()` returns `families_yaml` provenance for known family+platform regardless of invocation CWD
- **Robustness:** Path resolution does not depend on runtime CWD; no silent fallback to inferred_default in production
- **Testability:** New test explicitly changes CWD and verifies behavior
- **Minimality:** Single line change to `_FAMILIES_YAML` + one new test

### Now (runbook)

```bash
# 1. Replace the module-level constant
# In src/launcher/workers/intake/worker.py, find the _FAMILIES_YAML line:
# OLD: _FAMILIES_YAML = Path("configs/families.yaml")
# NEW: _FAMILIES_YAML = Path(__file__).resolve().parent.parent.parent.parent.parent / "configs" / "families.yaml"
# (parent chain: worker.py -> intake/ -> workers/ -> launcher/ -> src/ -> repo_root/)

# 2. Add test to tests/unit/workers/test_intake.py in TestResolveIdentity:
#   def test_resolve_identity_from_arbitrary_cwd(self, tmp_path):
#       import os
#       old_cwd = os.getcwd()
#       try:
#           os.chdir(tmp_path)
#           _, _, _, provenance = _resolve_identity("cells", "python")
#           assert provenance["display_name"] == "families_yaml"
#       finally:
#           os.chdir(old_cwd)

# 3. Verify
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v
```

---

## SR-02 — Fix test file corruption in `test_understand.py`

**Status:** Not Started
**Gap linkage:** G-02, G-03
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. Read `tests/unit/workers/test_understand.py` in full and identify all duplicate class definitions introduced by the append-mode bug
2. Remove all duplicate class definitions, keeping only the correct (second) versions
3. Replace `TestExtractProductEvidenceErrorHandling` with tests that use correct patch targets:
   - For import error: use `patch.dict("sys.modules", {"launcher.shared.code_analyzer": None})`
   - For analysis error: patch `"launcher.shared.code_analyzer.analyze_repository_code"`

**Allowed paths:**
- `tests/unit/workers/test_understand.py`

**Forbidden:** Any other file or path.

### Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v` — all tests pass, no duplicates
- **Dedup check:** `grep -c "class TestSelfReviewProductEvidence" tests/unit/workers/test_understand.py` returns `1` (not 2)
- **Dedup check:** `grep -c "class TestExtractProductEvidenceErrorHandling" tests/unit/workers/test_understand.py` returns `1` (correct version only)
- **Tests:** `test_analysis_error_returns_empty_with_failed_flag` actually exercises the function (not just a mock of itself)
- **No mock data in production paths:** Tests test real behavior, not mocks-testing-mocks

### Deliverables

- Full replacement of `tests/unit/workers/test_understand.py` with deduplicated, correct test classes
- `TestExtractProductEvidenceErrorHandling` with two tests:
  - `test_analysis_error_returns_empty_with_failed_flag` — patches `launcher.shared.code_analyzer.analyze_repository_code` with side_effect `ValueError`, asserts `(ProductEvidence(), True)` returned and `ctx.log.error` called
  - `test_import_error_propagates` — patches `sys.modules` to make `launcher.shared.code_analyzer` unavailable, asserts `ImportError` propagates out of `_extract_product_evidence`

### Hard rules

- All existing passing tests must remain passing
- Do not change implementation files
- No new dependencies
- Deterministic: `PYTHONHASHSEED=0` must produce identical results across runs

### Review dimensions (5/5 means)

- **Correctness:** Each test actually exercises the implementation path it claims to test
- **Testability:** Tests are self-contained, no reliance on external state
- **Robustness:** `TestExtractProductEvidenceErrorHandling` tests both ImportError (hard stop) and ValueError (soft failure) paths

### Now (runbook)

```bash
# 1. Count duplicates
python -c "
content = open('tests/unit/workers/test_understand.py').read()
classes = ['TestSelfReviewProductEvidence', 'TestScoutInventorySkipReasonCounts', 'TestExtractProductEvidenceErrorHandling']
for c in classes:
    print(c, content.count('class ' + c))
"

# 2. Read full file, locate duplicate sections, write clean version using Write tool

# 3. Verify
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v --tb=short
```

---

## SR-03 — Replace bare 4-tuple from `_resolve_identity()` with NamedTuple

**Status:** Not Started
**Gap linkage:** G-04
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Define `IdentityResolution(NamedTuple)` with fields `display_name`, `canonical_import`,
`runtime_import`, `provenance`. Return it from `_resolve_identity()`. Update all call sites
in `worker.py` and `test_intake.py`.

**Allowed paths:**
- `src/launcher/workers/intake/worker.py`
- `tests/unit/workers/test_intake.py`

**Forbidden:** Any other file or path.

### Acceptance checks

- **CLI:** `python -c "from launcher.workers.intake.worker import _resolve_identity; r = _resolve_identity('cells','python'); print(r.display_name, r.provenance)"` — works via attribute access
- **Tests:** All 46 intake tests (45 + 1 new NamedTuple test) pass
- **Backward compat:** `display_name, canonical_import, runtime_import, provenance = _resolve_identity(...)` still works (NamedTuple supports positional unpacking)
- **No mock data in production paths:** `IdentityResolution` is a real data type, not a stub

### Deliverables

- `IdentityResolution` NamedTuple defined in `worker.py`
- `_resolve_identity()` return type annotation updated to `IdentityResolution`
- All call sites in `worker.py` updated to use attribute access: `resolution.display_name`, etc.
- All test call sites updated to use attribute access or verified to still work with positional unpacking
- One new test: `test_resolve_identity_returns_named_tuple` verifying attribute access works

### Hard rules

- `IdentityResolution` must be backward-compatible with positional unpacking (NamedTuple supports both)
- Do not change `IntakeBundle` model
- No new external dependencies

### Review dimensions (5/5 means)

- **Maintainability:** Call sites read `resolution.canonical_import` not `result[1]`
- **Correctness:** NamedTuple enforces field order at definition; no positional confusion
- **Minimality:** Only NamedTuple definition + return statement changes needed

### Now (runbook)

```bash
# 1. Add NamedTuple definition after imports in worker.py:
#   class IdentityResolution(NamedTuple):
#       display_name: str
#       canonical_import: str
#       runtime_import: str
#       provenance: dict[str, str]

# 2. Update _resolve_identity() return statements to IdentityResolution(...)

# 3. Update run() to use:
#   resolution = _resolve_identity(family, platform)
#   display_name = resolution.display_name
#   canonical_import = resolution.canonical_import
#   ...

# 4. Update tests (positional unpacking still works, no test changes required unless
#    tests use index access like result[0] — change those to attribute access)

# 5. Add new test:
#   def test_resolve_identity_returns_named_tuple(self):
#       result = _resolve_identity("cells", "python")
#       assert result.display_name == result[0]
#       assert result.canonical_import == result[1]

# 6. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v
```

---

## SR-04 — Cache families.yaml reads in `_resolve_identity()`

**Status:** Not Started
**Gap linkage:** G-05
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Add module-level `_families_cache: dict | None = None` and `_load_families_data()`
function that reads families.yaml once and caches the result. `_resolve_identity()` calls
`_load_families_data()` instead of reading the file directly. Provide a `_clear_families_cache()`
function for tests.

**Allowed paths:**
- `src/launcher/workers/intake/worker.py`
- `tests/unit/workers/test_intake.py`

**Forbidden:** Any other file or path.

### Acceptance checks

- **CLI:** Running `_resolve_identity("cells", "python")` twice in the same process does not open families.yaml a second time (verifiable with `unittest.mock.patch("builtins.open")` call count)
- **Tests:** New test `test_families_yaml_read_once_per_process` patches `open` and asserts call count ≤ 1 across two `_resolve_identity` calls
- **Test isolation:** Cache is cleared between test runs via `_clear_families_cache()` in teardown
- **No mock data in production paths:** Cache stores live YAML data, not hardcoded values

### Deliverables

- `_families_cache: dict | None = None` at module level in `worker.py`
- `_load_families_data() -> dict` function that reads+caches families.yaml
- `_clear_families_cache() -> None` function that resets `_families_cache` to `None`
- `_resolve_identity()` calls `_load_families_data()` instead of `yaml.safe_load(open(...))`
- Test fixture calling `_clear_families_cache()` in teardown (autouse or explicit)
- New test verifying single file read per process

### Hard rules

- Cache must be cleared between test cases (use autouse fixture or explicit teardown)
- No threading concerns needed (single-process pipeline)
- No new external dependencies (`functools.lru_cache` is acceptable stdlib alternative)

### Review dimensions (5/5 means)

- **Performance:** One file read per process lifetime, not one per identity resolution call
- **Testability:** `_clear_families_cache()` allows complete test isolation without file mocking
- **Minimality:** No new classes; just a module-level variable and two small functions

### Now (runbook)

```bash
# 1. Add at module level in worker.py (after _FAMILIES_YAML):
#   _families_cache: dict | None = None
#
#   def _load_families_data() -> dict:
#       global _families_cache
#       if _families_cache is None:
#           if _FAMILIES_YAML.exists():
#               _families_cache = yaml.safe_load(_FAMILIES_YAML.read_text()) or {}
#           else:
#               _families_cache = {}
#       return _families_cache
#
#   def _clear_families_cache() -> None:
#       global _families_cache
#       _families_cache = None

# 2. Replace yaml.safe_load(open(...)) in _resolve_identity with _load_families_data()

# 3. In test_intake.py, add autouse fixture:
#   @pytest.fixture(autouse=True)
#   def clear_cache(self):
#       _clear_families_cache()
#       yield
#       _clear_families_cache()

# 4. Add test:
#   def test_families_yaml_read_once_per_process(self):
#       with patch("builtins.open", wraps=open) as mock_open:
#           _resolve_identity("cells", "python")
#           _resolve_identity("note", "java")
#           yaml_opens = [c for c in mock_open.call_args_list if "families" in str(c)]
#           assert len(yaml_opens) <= 1

# 5. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v
```

---

## SR-05 — Add structured context fields to Phase B.5 ERROR log

**Status:** Not Started
**Gap linkage:** G-06
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Add `family`, `platform`, and `repo_url` to the ERROR log message in
`_extract_product_evidence()` when an analysis-level exception is caught. This enables
log correlation in production monitoring.

**Allowed paths:**
- `src/launcher/workers/understand/worker.py`
- `tests/unit/workers/test_understand.py`

**Forbidden:** Any other file or path.

### Acceptance checks

- **CLI:** Triggering a Phase B.5 failure produces a log message containing the family, platform, and repo_url
- **Tests:** New test `test_b5_error_log_includes_structured_fields` patches code_analyzer to raise ValueError, asserts `ctx.log.error` was called with message containing the product's family and platform
- **Log format:** Consistent with other workers' ERROR patterns (uses `%s` args, not f-string concatenation)
- **No mock data in production paths:** Structured fields come from the live `product` argument, not hardcoded strings

### Deliverables

- Updated `_extract_product_evidence()` ERROR log call to include family/platform/repo_url
- One new test `test_b5_error_log_includes_structured_fields` in `TestExtractProductEvidenceErrorHandling`

### Hard rules

- Do not change function signature or return type
- ERROR level must be preserved (not downgraded back to WARNING)
- Log format must use `%s` args (not f-string) for compatibility with logging infrastructure

### Review dimensions (5/5 means)

- **Observability:** Every Phase B.5 failure log entry contains correlation fields for triage
- **Minimality:** Single line change to the existing `ctx.log.error(...)` call

### Now (runbook)

```bash
# Change the ctx.log.error call in _extract_product_evidence to:
# ctx.log.error(
#     "[Understand] Phase B.5 code_analyzer failed for %s/%s repo=%s — returning empty ProductEvidence.",
#     product.family, product.platform, getattr(product, "repo_url", "unknown"),
#     exc_info=True,
# )

# Then add test in TestExtractProductEvidenceErrorHandling:
#   def test_b5_error_log_includes_structured_fields(self):
#       # patch code_analyzer to raise ValueError
#       # call _extract_product_evidence(bundle, ctx)
#       # assert "cells" in ctx.log.error.call_args[0][0] or args
#       # assert "python" in str(ctx.log.error.call_args)

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v -k "b5_error"
```

---

## SR-06 — Add Scout integration test against real temp fixture repo

**Status:** Not Started
**Gap linkage:** G-08
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Add a pytest test that creates a minimal temp repo directory (pyproject.toml, README.md,
one .py source file), runs `run_scout()` directly (no network, no LLM), and asserts that the
produced `RepoInfo`, `budget_log`, and `skip_reason_counts` computation are correct.

**Allowed paths:**
- `tests/unit/workers/understand/test_scout.py`

**Forbidden:** Any other file or path.

### Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_scout.py -v` — passes
- **Python fixture test:** `test_scout_on_python_fixture` asserts `shared_facts.primary_language == "python"`, `len(file_tree) >= 2`, `skip_reason_counts` is a dict (even if empty for tiny repo), `content_files_read >= 1`
- **Non-Python fixture test:** `test_scout_on_js_fixture` asserts `shared_facts.primary_language == "javascript"`
- **No network:** All files are created in `tmp_path`; no cloning

### Deliverables

- New/updated `tests/unit/workers/understand/test_scout.py` with integration test class `TestScoutOnFixtureRepo`
- Python fixture: `pyproject.toml` with `[project] name = "test-pkg"`, `README.md`, `src/test_module.py`
- Non-Python fixture: `package.json` + `index.js` — asserts `shared_facts.primary_language == "javascript"`
- Both tests use `asyncio.run()` to call `run_scout(tmp_path, budget=50_000)`

### Hard rules

- No network calls in test
- Deterministic: `PYTHONHASHSEED=0` must produce same results across runs
- Do not change `scout.py` implementation
- Must not import from LLM client modules (test must work offline)

### Review dimensions (5/5 means)

- **Thoroughness:** Covers Python and non-Python fixture repos
- **Testability:** Tests real Scout behavior on real filesystem, not mocked
- **Correctness:** Asserts structural properties of produced RepoInfo, not just that it doesn't crash

### Now (runbook)

```bash
# 1. Write test file tests/unit/workers/understand/test_scout.py
# 2. Python fixture: tmp_path/pyproject.toml, tmp_path/README.md, tmp_path/src/core.py
# 3. Non-Python fixture: tmp_path/package.json, tmp_path/index.js

# Fixture content examples:
# pyproject.toml: "[project]\nname = \"test-pkg\"\nversion = \"0.1.0\""
# README.md: "# Test Package\nA test fixture."
# src/core.py: "class Processor:\n    def run(self): pass"
# package.json: '{"name": "test-js", "version": "1.0.0"}'
# index.js: "function main() { return 42; }\nmodule.exports = { main };"

# 4. Call: repo_info, repo_content, budget_log, overflow = asyncio.run(run_scout(tmp_path))
# 5. Assert shared_facts.primary_language, file counts, budget_log structure

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_scout.py -v
```

---

## SR-07 — End-to-end pipeline verification on fixture repos (non-LLM)

**Status:** Not Started
**Gap linkage:** G-07
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:** Create a pytest integration test (not requiring network or LLM) that:
1. Creates a minimal Python fixture repo in `tmp_path` with enough structure to exercise Intake + Understand
2. Runs `IntakeWorker.run()` with a mocked clone (returns the fixture dir)
3. Runs `UnderstandWorker.run()` with the resulting `IntakeBundle`
4. Asserts that `intake_bundle.json` contains `field_provenance`
5. Asserts that `scout_inventory.json` contains `skip_reason_counts`
6. Asserts that `UnderstandingBundle.product_evidence` is not `None` (or `phase_b5_failed` flag is present in scout_inventory)

**Allowed paths:**
- `tests/integration/test_intake_understand_flow.py`

**Forbidden:** Any other file or path.

### Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_intake_understand_flow.py -v` — passes
- **Artifact test:** `test_intake_then_understand_python_fixture` reads both JSON artifact files and asserts keys are present
- **Provenance test:** `test_intake_field_provenance_in_artifact` asserts `field_provenance["display_name"] == "families_yaml"` for cells/python
- **No network:** Clone is mocked; LLM calls are mocked with empty deterministic responses
- **Real artifacts:** Uses real `WorkerContext` with real `ArtifactStore` writing to `tmp_path`

### Deliverables

- Updated `tests/integration/test_intake_understand_flow.py` with class `TestIntakeUnderstandFlow`
- Two integration tests:
  - `test_intake_then_understand_python_fixture`: end-to-end chain, asserts both artifacts produced
  - `test_intake_field_provenance_in_artifact`: narrow assertion on provenance in intake artifact
- Python fixture directory created inline in `tmp_path`
- LLM mock returning `{"claims": [], "evidence": []}` (deterministic fallback)

### Hard rules

- No actual network calls (git clone mocked, LLM client mocked)
- Must use `PYTHONHASHSEED=0` for determinism
- Do not change worker implementation files
- Test must run in under 10 seconds (no real I/O beyond tmp filesystem)

### Review dimensions (5/5 means)

- **Thoroughness:** Exercises the full Intake→Understand chain end-to-end in a test
- **Production grading:** Produces and inspects actual on-disk artifacts, not just return values
- **Correctness:** Asserts structural correctness of artifact JSON, not just absence of exceptions

### Now (runbook)

```bash
# 1. Create minimal Python fixture in fixture_dir:
#    fixture_dir/pyproject.toml (name = "aspose-cells-foss")
#    fixture_dir/README.md ("# Aspose.Cells FOSS\nSpreadsheet library.")
#    fixture_dir/aspose_cells_foss/__init__.py ("class Workbook: pass")

# 2. Mock clone_repo_cached to return (fixture_dir, "abc123sha", True)
# 3. Mock LLM client to return empty claims list
# 4. Create RunConfig with family="cells", platform="python"
# 5. Run: bundle = await IntakeWorker(ctx).run(run_config)
# 6. Run: understanding = await UnderstandWorker(ctx).run(bundle)
# 7. Read artifact files from ctx.store:
#    intake_json = json.loads(ctx.store.read("intake_bundle.json"))
#    scout_json = json.loads(ctx.store.read("scout_inventory.json"))
# 8. Assert:
#    assert "field_provenance" in intake_json
#    assert "skip_reason_counts" in scout_json
#    assert understanding.product_evidence is not None

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_intake_understand_flow.py -v
```

---

## Execution Order

Priority order for working through these taskcards:

1. **SR-02** (test file corruption) — Blocks accurate test counts; fix first before running any other verify commands
2. **SR-01** (families path) — Production correctness risk; high priority
3. **SR-05** (ERROR log fields) — Low effort, high observability value
4. **SR-03** (NamedTuple) — Code quality; low risk
5. **SR-04** (cache) — Performance; low urgency for small runs
6. **SR-06** (Scout integration) — Closes the test coverage gap
7. **SR-07** (E2E integration) — Highest effort; tackle after individual fixes are stable

---

```yaml
plan_files:
  - path: plans/healing/SR-intake-understand-hardening.md
    taskcards: [SR-01, SR-02, SR-03, SR-04, SR-05, SR-06, SR-07]
    gaps: [G-01, G-02, G-03, G-04, G-05, G-06, G-07, G-08]
    source_taskcards: [TC-4057, TC-4058]
    generated: "2026-03-11"
```
