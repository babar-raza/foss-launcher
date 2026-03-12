# tender-hugging-shamir — Test Coverage Gaps Plan

## Context

Self-review of `tender-hugging-shamir.md` identified three test coverage gaps
that leave Phase 3 verification incomplete. The `python-docs-heavy` fixture was
specified in the plan but never created, leaving the TC-4081 "thin API + docs-heavy"
scenario untested. The `_read_files_for_resume` helper required for UnderstandWorker
resume is described in TC-4076 prose but has no function signature, no assigned file
path, and no test. The `budget_log` dict entries in ScoutBundle are `list[dict]`
with no schema — any code consuming the log makes undocumented assumptions.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-THS-04 | `tests/fixtures/python-docs-heavy/` missing — Phase 3 TC-4081 test scenario (thin API + rich docs → ≥8 claims) has no fixture | Testability/High | THS-04 |
| G-THS-05 | `_read_files_for_resume` is described in TC-4076 but has no confirmed function signature, file location, or test — resume path is untested | Testability/High | THS-05 |
| G-THS-06 | `budget_log: list[dict]` in ScoutBundle has no per-entry schema — consumers make undocumented dict-key assumptions | Maintainability/Medium | THS-06 |

---

## THS-04 — Create `tests/fixtures/python-docs-heavy/` Fixture

### Status: Not Started

### Gap Linkage
- G-THS-04: `tests/fixtures/python-docs-heavy/` missing

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
Create the `tests/fixtures/python-docs-heavy/` directory tree with all files
specified in tender-hugging-shamir.md Phase 3. The fixture must simulate a
real Python repo that has:
- Thin API surface (2 public classes, minimal method docstrings)
- Rich documentation (README with ≥3 fenced Python code blocks, docs/ with
  step-by-step guide and API reference markdown files)

This is the canonical test case for TC-4081: when `public_class_count < 3`,
the evidence context must inject ≥2000 chars of README content so the LLM
can produce ≥8 claims even with sparse API surface.

**Fixture structure to create:**
```
tests/fixtures/python-docs-heavy/
  pyproject.toml               # project name, version, dependencies
  README.md                    # ≥400 lines; ≥3 fenced python code blocks;
                               # install instructions; feature overview
  docs/
    getting-started.md         # step-by-step guide with ≥2 code blocks
    api-reference.md           # method signatures and usage examples
  src/
    mylib/
      __init__.py              # from .core import Processor; from .utils import Formatter
      core.py                  # class Processor — 2 public methods, short docstrings
      utils.py                 # class Formatter — 2 public methods, short docstrings
```

**pyproject.toml content** (exact):
```toml
[project]
name = "mylib-foss"
version = "1.0.0"
description = "A Python library for document processing"
requires-python = ">=3.8"
dependencies = []

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.backends.legacy:build"
```

**README.md must include** (for TC-4081 evidence injection test):
- An install block: ` ```python\nimport mylib\nprocessor = mylib.Processor()\n``` `
- A usage block: ` ```python\nresult = processor.process("hello")\nprint(result)\n``` `
- A format block: ` ```python\nfmt = mylib.Formatter()\noutput = fmt.format(result)\n``` `
- At least 300 words of English prose describing features

Add a test in `tests/unit/workers/understand/test_python_hardening.py`:
- `test_docs_heavy_fixture_produces_sufficient_claims` — runs Scout + Understand
  extraction on the fixture, asserts `len(claims) >= 8` and
  `any(c.source == "llm" for c in claims)` (LLM used README for evidence)
- `test_docs_heavy_readme_injected_in_evidence` — when `public_class_count < 3`,
  evidence context string contains ≥500 chars of README content (not just class name)

#### Allowed paths
```
tests/fixtures/python-docs-heavy/pyproject.toml
tests/fixtures/python-docs-heavy/README.md
tests/fixtures/python-docs-heavy/docs/getting-started.md
tests/fixtures/python-docs-heavy/docs/api-reference.md
tests/fixtures/python-docs-heavy/src/mylib/__init__.py
tests/fixtures/python-docs-heavy/src/mylib/core.py
tests/fixtures/python-docs-heavy/src/mylib/utils.py
tests/unit/workers/understand/test_python_hardening.py
```

#### Forbidden
Any file outside `tests/fixtures/python-docs-heavy/` and
`tests/unit/workers/understand/test_python_hardening.py`.

### Acceptance Checks

#### CLI
```bash
# Fixture directory and all files exist
ls tests/fixtures/python-docs-heavy/
ls tests/fixtures/python-docs-heavy/src/mylib/
ls tests/fixtures/python-docs-heavy/docs/

# README has ≥3 fenced code blocks
grep -c '```python' tests/fixtures/python-docs-heavy/README.md
# Expected: ≥3

# pyproject.toml is valid TOML (python can parse it)
python -c "import tomllib; tomllib.load(open('tests/fixtures/python-docs-heavy/pyproject.toml','rb'))"
# Expected: no exception
```

#### UI/Web/API
N/A.

#### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_python_hardening.py \
  -k "docs_heavy" -v
# Expected: 2 new tests pass

# Full hardening suite still passes
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_python_hardening.py -v
```

#### Config respected end-to-end
The fixture must work in offline mode (no network, no LLM) for the unit test.
The evidence injection test must mock the LLM call and inspect the prompt,
not make a real LLM request.

#### No mock data in production paths
Fixture files are test-only under `tests/fixtures/` — no production path impact.

### Deliverables
- Full fixture tree under `tests/fixtures/python-docs-heavy/` (7 files)
- 2 new test functions in `test_python_hardening.py` (happy path + evidence injection)
- Both new tests green

### Hard Rules
- Fixture README must have ≥3 fenced Python code blocks — do not reduce
- No network in tests — LLM call must be mocked
- PYTHONHASHSEED=0 for deterministic test runs
- Fixture files must be valid (parseable) Python/TOML

### Review Dimensions — what 5/5 means for THS-04

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | All 7 fixture files created; both test functions written |
| Consistency | Fixture matches Phase 3 spec in tender-hugging-shamir.md exactly |
| Production grading | Fixture is realistic — resembles actual thin-API Python library |
| Systematic approach | pyproject.toml valid, README has correct structure, imports are correct |
| Correctness | `test_docs_heavy_readme_injected_in_evidence` verifies the TC-4081 fix actually works |
| Scope adherence | Only 8 files changed (7 fixture + 1 test update) |
| Maintainability | Fixture is self-contained — no external deps |
| Testability | 2 new tests: claim count (happy path) + evidence injection (regression) |
| Robustness | LLM mocked — test passes offline |
| Performance | Small fixture — fast to read |
| Integration fit | Follows same fixture convention as `python-cells` and `python-sparse` |
| Observability | Test failure message must include actual claim count |
| Minimality | No extra fixture files beyond what is needed |

### Now (Runbook)

```bash
# 1. Create fixture directory structure
mkdir -p tests/fixtures/python-docs-heavy/docs
mkdir -p tests/fixtures/python-docs-heavy/src/mylib

# 2. Write pyproject.toml
# 3. Write README.md (≥3 fenced python blocks, ≥300 words prose)
# 4. Write docs/getting-started.md (2 code blocks)
# 5. Write docs/api-reference.md (method signatures)
# 6. Write src/mylib/__init__.py, core.py, utils.py
# 7. Add 2 test functions to test_python_hardening.py

# 8. Verify fixture
python -c "import tomllib; tomllib.load(open('tests/fixtures/python-docs-heavy/pyproject.toml','rb')); print('TOML OK')"
grep -c '```python' tests/fixtures/python-docs-heavy/README.md

# 9. Run new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_python_hardening.py -k "docs_heavy" -v
```

---

## THS-05 — Specify and Test `_read_files_for_resume`

### Status: Not Started

### Gap Linkage
- G-THS-05: `_read_files_for_resume` underspecified — no confirmed signature, file path, or test

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
Locate (or create) `_read_files_for_resume` in the Understand worker, confirm its
exact signature and behavior, and add a dedicated test covering the resume path.

**Step 1 — Locate the function:**
```bash
grep -rn "_read_files_for_resume\|read_files_for_resume" src/
```
If it exists: confirm signature and document it (proceed to Step 3).
If it does NOT exist: it is a missing implementation — create it in
`src/launcher/workers/understand/worker.py` per the TC-4076 spec:
```python
async def _read_files_for_resume(
    repo_dir: Path,
    file_index: list[FileEntry],
) -> dict[str, str]:
    """Re-read file content for resume path when context.repo_content is None.

    Uses the file_index from ScoutBundle to reconstruct the content dict
    without re-running full Scout phase. Applies same sanitization as
    _read_repo_content() in the Scout module.

    Args:
        repo_dir: Absolute path to the cloned repository.
        file_index: FileEntry list from ScoutBundle.repo_info.file_index.

    Returns:
        Mapping of relative path string → file content string.
        Files that no longer exist on disk are silently skipped (resume safety).
    """
```

**Step 2 — Confirm UnderstandWorker uses it correctly:**
```bash
grep -n "repo_content is None\|context.repo_content" src/launcher/workers/understand/worker.py
```
The resume guard should read:
```python
if context.repo_content is None:
    repo_content = await _read_files_for_resume(
        repo_dir, input_data.repo_info.file_index
    )
else:
    repo_content = context.repo_content
```

**Step 3 — Add test `test_understand_resume_path_reads_from_disk`:**
- Arrange: ScoutBundle with known file_index; `context.repo_content = None`
- Act: call `UnderstandWorker.run()` with the bundle
- Assert: UnderstandWorker proceeds without error; extraction uses content
  from disk files, not from context

**Step 4 — Add test `test_understand_resume_skips_missing_files`:**
- Arrange: file_index contains a path that does not exist on disk
- Act: call `_read_files_for_resume(repo_dir, file_index)`
- Assert: missing file is silently skipped; no FileNotFoundError raised

#### Allowed paths
```
src/launcher/workers/understand/worker.py
tests/unit/workers/test_understand.py
```
(Only if `_read_files_for_resume` does not yet exist in worker.py. If it
already exists in another file, add that file to allowed_paths and open
a scope amendment.)

#### Forbidden
Any other file.

### Acceptance Checks

#### CLI
```bash
# Function exists somewhere in understand module
grep -rn "_read_files_for_resume" src/launcher/workers/understand/
# Expected: ≥1 result with function definition

# Resume guard is present
grep -n "repo_content is None" src/launcher/workers/understand/worker.py
# Expected: ≥1 result
```

#### UI/Web/API
N/A.

#### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_understand.py \
  -k "resume" -v
# Expected: 2 new resume tests pass

# Full understand test suite still passes
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_understand.py -v
```

#### Config respected end-to-end
Resume path must not require any LLM calls — pure disk I/O.

#### No mock data in production paths
`_read_files_for_resume` must read actual fixture files, not hardcoded strings.

### Deliverables
- Confirmed (or created) `_read_files_for_resume` with complete docstring in
  `src/launcher/workers/understand/worker.py`
- Resume guard in `UnderstandWorker.run()` explicitly handling `context.repo_content is None`
- 2 new test functions in `tests/unit/workers/test_understand.py`
  (resume path + missing file skip)

### Hard Rules
- `_read_files_for_resume` must be async (consistent with the rest of the worker)
- Must apply same sanitization as Scout's `_read_repo_content`
- No network in tests
- Missing files must be skipped silently — no exception propagation

### Review Dimensions — what 5/5 means for THS-05

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Function exists, docstring complete, resume guard present, 2 tests covering resume |
| Consistency | Signature matches TC-4076 spec; behavior matches Scout's read pattern |
| Production grading | Resume path does not crash on missing files; no silent data loss |
| Systematic approach | Step 1 locates function; Step 2 verifies guard; Steps 3–4 add tests |
| Correctness | `_read_files_for_resume` returns same-shaped dict as `context.repo_content` |
| Scope adherence | At most 2 files changed |
| Maintainability | Complete docstring explains resume semantics |
| Testability | Two tests: happy path + missing file regression |
| Robustness | Missing files skipped silently (resume safety) |
| Performance | Only reads files listed in file_index — no directory walk |
| Integration fit | Called from the `context.repo_content is None` guard in worker.py |
| Observability | Log at INFO when resume path is taken: "[Understand] resume: re-reading N files from disk" |
| Minimality | 2 files at most |

### Now (Runbook)

```bash
# Step 1: Find existing implementation
grep -rn "_read_files_for_resume" src/

# Step 2: If missing — add to worker.py after existing helpers
# Step 3: Verify resume guard in UnderstandWorker.run()
grep -n "repo_content is None\|context.repo_content" src/launcher/workers/understand/worker.py

# Step 4: Add 2 tests to test_understand.py
# Step 5: Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_understand.py -k "resume" -v

# Step 6: Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -x -q
```

---

## THS-06 — Specify `budget_log` Entry Schema in ScoutBundle

### Status: Not Started

### Gap Linkage
- G-THS-06: `budget_log: list[dict]` in ScoutBundle has no per-entry schema

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
Replace the untyped `budget_log: list[dict]` in ScoutBundle with a typed
`list[BudgetLogEntry]` where `BudgetLogEntry` is a Pydantic model defined
in the same file.

**BudgetLogEntry fields** (inferred from Scout implementation):
```python
class BudgetLogEntry(LauncherBaseModel):
    """One entry in the per-file budget log from the Scout phase.

    Records what was read, how many bytes were consumed, which category
    the file was classified into, and whether the file was capped.
    """
    file: str            # Relative path from repo root (e.g. "src/main.py")
    bytes_read: int      # Actual bytes consumed (after cap, if applied)
    category: str        # File category (e.g. "source", "doc", "test", "config")
    capped: bool         # True if file was truncated to budget cap
```

Verify that the Scout implementation (`src/launcher/workers/scout/scout.py`
or `src/launcher/workers/understand/scout.py`) actually appends dicts matching
these fields. If the keys differ, use the actual keys from the implementation —
do NOT change the Scout implementation in this taskcard.

Update `ScoutBundle` in `src/launcher/models/scout.py`:
```python
budget_log: list[BudgetLogEntry] = Field(default_factory=list)
```

Update `specs/schemas/scout_bundle.schema.json` to add a `budget_log_entry`
definition with the 4 fields.

#### Allowed paths
```
src/launcher/models/scout.py
specs/schemas/scout_bundle.schema.json
tests/unit/models/test_scout_bundle.py   (create if not exists)
```

#### Forbidden
`src/launcher/workers/scout/scout.py` — do NOT change the Scout implementation
in this taskcard. Only the model and schema.

### Acceptance Checks

#### CLI
```bash
# BudgetLogEntry importable
python -c "from launcher.models.scout import BudgetLogEntry, ScoutBundle; print('OK')"

# budget_log field is typed list
python -c "
import inspect
from launcher.models.scout import ScoutBundle
ann = ScoutBundle.model_fields['budget_log'].annotation
print(ann)
" # Expected: list[BudgetLogEntry] or similar

# Schema updated
python -c "
import json
s = json.load(open('specs/schemas/scout_bundle.schema.json'))
assert 'budget_log' in str(s), 'budget_log not in schema'
print('Schema OK')
"
```

#### UI/Web/API
N/A.

#### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/models/ -v -k "scout"
# Expected: existing + new tests pass

# Test BudgetLogEntry round-trip
# tests/unit/models/test_scout_bundle.py must include:
# test_budget_log_entry_roundtrip: BudgetLogEntry(file="a.py", bytes_read=100, category="source", capped=False)
# test_scout_bundle_with_budget_log: ScoutBundle with budget_log entries validates correctly
# test_budget_log_entry_rejects_missing_fields: BudgetLogEntry({}) raises ValidationError
```

#### Config respected end-to-end
ScoutBundle with old `list[dict]` entries must still validate (backward compat
via Pydantic coercion from dict → BudgetLogEntry).

#### No mock data in production paths
N/A.

### Deliverables
- `BudgetLogEntry` Pydantic model in `src/launcher/models/scout.py`
- `ScoutBundle.budget_log` field typed as `list[BudgetLogEntry]`
- Updated `specs/schemas/scout_bundle.schema.json` with entry definition
- `tests/unit/models/test_scout_bundle.py` with 3 tests (round-trip, full bundle, missing-fields validation)

### Hard Rules
- Do NOT change Scout implementation — only the model and schema
- `BudgetLogEntry` fields must match the actual keys used in the Scout implementation (verify first)
- Pydantic must coerce `dict → BudgetLogEntry` automatically (so existing pipeline code that appends raw dicts still works)
- Keep public signature of `ScoutBundle` — `budget_log` field stays at same position

### Review Dimensions — what 5/5 means for THS-06

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | BudgetLogEntry has all 4 fields; schema updated; 3 tests written |
| Consistency | Fields match actual Scout implementation output (verified before writing) |
| Production grading | Pydantic coercion means existing pipeline code continues to work |
| Systematic approach | Model → schema → test, in that order |
| Correctness | test_budget_log_entry_rejects_missing_fields confirms validation works |
| Scope adherence | 3 files changed |
| Maintainability | BudgetLogEntry docstring explains each field |
| Testability | Round-trip, full bundle, validation error — 3 paths |
| Robustness | Old dict entries still parse via Pydantic coercion |
| Performance | N/A |
| Integration fit | Follows same LauncherBaseModel pattern as all other models |
| Observability | Type annotation makes budget_log introspectable at debug time |
| Minimality | 3 files, 1 new model class, no regressions |

### Now (Runbook)

```bash
# Step 1: Verify actual keys Scout appends to budget_log
grep -n "budget_log\|append" src/launcher/workers/scout/scout.py | head -20
# OR
grep -n "budget_log\|append" src/launcher/workers/understand/scout.py | head -20

# Step 2: If keys match {file, bytes_read, category, capped} — proceed
# If keys differ — use actual keys, update this spec

# Step 3: Add BudgetLogEntry to src/launcher/models/scout.py
# Step 4: Change budget_log field type
# Step 5: Update specs/schemas/scout_bundle.schema.json
# Step 6: Create/update tests/unit/models/test_scout_bundle.py

# Step 7: Verify
python -c "from launcher.models.scout import BudgetLogEntry, ScoutBundle; print('OK')"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ -v -k "scout"

# Step 8: Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
