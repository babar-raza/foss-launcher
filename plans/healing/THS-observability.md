# tender-hugging-shamir — Observability & Scalability Gaps Plan

## Context

Self-review of `tender-hugging-shamir.md` identified four gaps in the Scout
worker and supporting infrastructure. ScoutWorker does not emit any structured
pipeline events — `worker.completed`, `worker.self_review_failed`, etc. — making
it invisible in the events log. ScoutBundle serializes the full `file_index` from
RepoInfo without any size cap, so a repo with 10K+ files produces a ~1MB checkpoint
file that could slow serialization and cloud storage. TC-4087 introduced a
line-count heuristic for detecting non-Python workflow examples, but any 3+ line
block in a `.ts`/`.java` file becomes an "example" — this false-positive rate is
high enough to pollute the evidence context. Finally, tree-sitter is a hard
dependency for TypeScript/Java/C# API extraction but is not declared anywhere in
`pyproject.toml`, causing silent `ImportError` failures with no clear install hint.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-THS-11 | ScoutWorker emits no structured pipeline events — invisible in events.ndjson | Observability/High | THS-11 |
| G-THS-12 | ScoutBundle `file_index` has no size cap — large repos produce multi-MB checkpoint files | Scalability/Medium | THS-12 |
| G-THS-13 | TC-4087 line-count heuristic for non-Python workflow examples produces false positives — any 3-line block in a .ts/.java file becomes an "example" | Production/Medium | THS-13 |
| G-THS-14 | tree-sitter not declared in `pyproject.toml` optional dependencies — silent ImportError with no install hint | Production/Medium | THS-14 |

---

## THS-11 — Add Structured Event Emission to ScoutWorker

### Status: Not Started

### Gap Linkage
- G-THS-11: ScoutWorker emits no structured pipeline events

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
Add structured event emission to `src/launcher/workers/scout/worker.py`
following the same pattern used by UnderstandWorker and GenerateWorker.

**Events to emit:**

1. `scout.started` — at the top of `ScoutWorker.run()`, before file walk:
```python
context.emit_event("scout.started", {
    "repo_dir": str(repo_dir),
    "family": intake.family,
    "platform": intake.platform,
})
```

2. `scout.completed` — after successful ScoutBundle production:
```python
context.emit_event("scout.completed", {
    "files_enumerated": bundle.repo_info.files_enumerated,
    "content_files_read": bundle.repo_info.content_files_read,
    "budget_log_overflow_count": bundle.budget_log_overflow_count,
    "package_name": bundle.repo_info.shared_facts.package_name,
    "primary_language": bundle.repo_info.shared_facts.primary_language,
    "self_review_passed": True,  # updated after self_review call
})
```

3. `scout.self_review_failed` — after `self_review()` if `not result.passed`:
```python
if not review_result.passed:
    context.emit_event("scout.self_review_failed", {
        "findings": [f for f in review_result.findings if f["severity"] == "high"],
        "total_findings": len(review_result.findings),
    })
```

**Verify** that `context.emit_event` is the correct method name by checking
how existing workers call it:
```bash
grep -n "emit_event\|context\.emit" src/launcher/workers/understand/worker.py | head -10
grep -n "emit_event\|context\.emit" src/launcher/workers/generate/worker.py | head -10
```
Use the exact same method name and signature found there.

**Add test `test_scout_emits_started_event`:**
- Arrange: mock context with an event capture list
- Act: run ScoutWorker on a fixture repo
- Assert: `"scout.started"` is in captured events

**Add test `test_scout_emits_completed_event_with_counts`:**
- Arrange: same mock context
- Assert: `"scout.completed"` event has `files_enumerated > 0`

**Add test `test_scout_emits_self_review_failed_event`:**
- Arrange: empty repo dir → self_review fails (0 files)
- Assert: `"scout.self_review_failed"` emitted with `findings` list

#### Allowed paths
```
src/launcher/workers/scout/worker.py
tests/unit/workers/test_scout.py
```

#### Forbidden
Any other file. Do NOT change the event schema files or the
orchestrator event handling — only the emit calls.

### Acceptance Checks

#### CLI
```bash
# Emit calls present
grep -n "emit_event\|context\.emit" src/launcher/workers/scout/worker.py
# Expected: ≥3 matches (started, completed, self_review_failed)

# Event names match the correct prefix
grep "scout\." src/launcher/workers/scout/worker.py | grep "emit"
# Expected: scout.started, scout.completed, scout.self_review_failed
```

#### UI/Web/API
After a real pipeline run, `events.ndjson` must contain:
```json
{"event": "scout.started", ...}
{"event": "scout.completed", ...}
```

#### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout.py \
  -k "emits_started or emits_completed or emits_self_review" -v
# Expected: 3 new tests pass

# Existing scout tests still pass
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout.py -v
```

#### Config respected end-to-end
Events must appear in `events.ndjson` when pipeline runs with standard config.
The `scout.completed` event must include `files_enumerated` and `package_name`
fields (these are the key observability signals for the Scout phase).

#### No mock data in production paths
Event payloads must contain real values from the Scout run, not hardcoded test data.

### Deliverables
- 3 `context.emit_event()` calls in `ScoutWorker.run()` / `self_review()`
- 3 new test functions in `tests/unit/workers/test_scout.py`

### Hard Rules
- Use the exact same `emit_event` method signature as other workers
- Event names must use `scout.` prefix
- `scout.completed` must include both `files_enumerated` and `package_name`
- No network in tests
- PYTHONHASHSEED=0

### Review Dimensions — what 5/5 means for THS-11

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | 3 events: started, completed, self_review_failed; all key payload fields included |
| Consistency | Same emit_event() pattern as UnderstandWorker and GenerateWorker |
| Production grading | events.ndjson shows scout.started + scout.completed after a real run |
| Systematic approach | Started → completed → failure path, in order |
| Correctness | test_scout_emits_completed_event_with_counts verifies payload fields |
| Scope adherence | 2 files only |
| Maintainability | Event names follow existing `{worker}.{event}` convention |
| Testability | 3 tests, one per event type |
| Robustness | self_review_failed event includes severity=high findings only (not all findings) |
| Performance | 3 emit calls — negligible |
| Integration fit | Same pattern as all other workers in the pipeline |
| Observability | files_enumerated + package_name in completed event are the two key debug signals |
| Minimality | 3 emit calls + 3 tests — nothing else |

### Now (Runbook)

```bash
# Step 1: Verify emit_event pattern
grep -n "emit_event\|context\.emit" src/launcher/workers/understand/worker.py | head -10

# Step 2: Add 3 emit_event calls to ScoutWorker.run() and self_review()

# Step 3: Add 3 tests to test_scout.py

# Step 4: Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout.py -v

# Step 5: Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## THS-12 — Add `file_index` Size Cap to ScoutBundle Serialization

### Status: Not Started

### Gap Linkage
- G-THS-12: ScoutBundle `file_index` has no size cap for large repos

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
ScoutBundle serializes `repo_info: RepoInfo` which contains `file_index: list[FileEntry]`.
For repos with 10K+ files, this list serializes to ~1MB. The fix has two parts:

**Part A — Cap `file_index` before serialization in ScoutWorker**

Add a constant and a truncation step in `src/launcher/workers/scout/worker.py`:

```python
_MAX_FILE_INDEX_ENTRIES = 2000  # ~200KB serialized; sufficient for resume path

# Before constructing ScoutBundle:
if len(repo_info.file_index) > _MAX_FILE_INDEX_ENTRIES:
    logger.warning(
        "[Scout] file_index capped at %d entries (repo has %d files). "
        "Resume path will use capped index — files beyond cap will not be "
        "re-read on resume. This is acceptable for large repos.",
        _MAX_FILE_INDEX_ENTRIES,
        len(repo_info.file_index),
    )
    capped_file_index = repo_info.file_index[:_MAX_FILE_INDEX_ENTRIES]
    repo_info = repo_info.model_copy(update={"file_index": capped_file_index})
    # Note: The full content dict (context.repo_content) is NOT capped —
    # all files that were read in the Scout run are still available in memory.
```

**Part B — Add `file_index_capped: bool` field to ScoutBundle**

In `src/launcher/models/scout.py`:
```python
file_index_capped: bool = False  # True if file_index was truncated for serialization
file_index_original_count: int = 0  # Total files before capping (0 if not capped)
```

Set these in ScoutWorker when capping occurs.

**Add test `test_scout_caps_file_index_at_max`:**
- Arrange: mock repo_info with 3000 file_index entries
- Act: run ScoutWorker (or the capping logic directly)
- Assert: bundle.repo_info.file_index length ≤ `_MAX_FILE_INDEX_ENTRIES`
- Assert: bundle.file_index_capped == True
- Assert: bundle.file_index_original_count == 3000

**Add test `test_scout_does_not_cap_small_file_index`:**
- Arrange: repo_info with 500 file_index entries
- Assert: bundle.file_index_capped == False
- Assert: bundle.repo_info.file_index length == 500

#### Allowed paths
```
src/launcher/workers/scout/worker.py
src/launcher/models/scout.py
tests/unit/workers/test_scout.py
```

#### Forbidden
`src/launcher/workers/understand/worker.py` — the resume path already handles
`file_index` access from ScoutBundle; it will naturally use the capped index.
Do not add extra logic there for this taskcard.

### Acceptance Checks

#### CLI
```bash
# Cap constant defined
grep "_MAX_FILE_INDEX_ENTRIES" src/launcher/workers/scout/worker.py
# Expected: 1 match with value 2000

# New fields in ScoutBundle
grep "file_index_capped\|file_index_original_count" src/launcher/models/scout.py
# Expected: 2 matches

# Cap logic present
grep "file_index.*cap\|capped_file_index" src/launcher/workers/scout/worker.py
# Expected: ≥2 matches
```

#### UI/Web/API
For a large repo run (≥2000 files): `scout_bundle.json` size must be ≤ 250KB.
`scout_bundle.json` must include `"file_index_capped": true` and
`"file_index_original_count": N`.

#### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout.py \
  -k "caps_file_index or not_cap_small" -v
# Expected: 2 new tests pass
```

#### Config respected end-to-end
`_MAX_FILE_INDEX_ENTRIES = 2000` is an internal constant, not user-configurable.
The cap only affects the serialized checkpoint, not the in-memory content dict.

#### No mock data in production paths
Test must use a programmatically constructed `repo_info` with N FileEntry
objects — not a real large repo.

### Deliverables
- `_MAX_FILE_INDEX_ENTRIES = 2000` constant in `worker.py`
- Cap + warning log in `ScoutWorker.run()` before ScoutBundle construction
- `file_index_capped: bool` and `file_index_original_count: int` in `ScoutBundle`
- 2 new tests in `test_scout.py`

### Hard Rules
- Cap applies to serialization only — `context.repo_content` is never capped
- Warning log must be WARNING level (not INFO) — operators must see it
- `file_index_original_count` must be set to 0 when not capped (not N)
- No network in tests
- PYTHONHASHSEED=0

### Review Dimensions — what 5/5 means for THS-12

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Cap constant; cap logic; warning log; 2 new ScoutBundle fields; 2 tests |
| Consistency | Cap is documented in bundle (`file_index_capped`); not a silent truncation |
| Production grading | Large repo checkpoint ≤ 250KB; warning visible in logs |
| Systematic approach | Constant → cap logic → warning → bundle fields → tests |
| Correctness | test_scout_caps_file_index_at_max verifies capped=True and len cap |
| Scope adherence | 3 files |
| Maintainability | Named constant + warning log + bundle fields make the cap discoverable |
| Testability | 2 tests: capped path + uncapped path |
| Robustness | In-memory content not capped — resume reads as many files as were actually read |
| Performance | list slice O(n) — negligible; checkpoint size controlled |
| Integration fit | `file_index_capped` field follows existing `_overflow_count` pattern in ScoutBundle |
| Observability | WARNING log includes original count + cap threshold |
| Minimality | 3 files, 1 constant, 1 cap block, 2 fields, 2 tests |

### Now (Runbook)

```bash
# Step 1: Confirm file_index location
grep -n "file_index" src/launcher/models/scout.py
grep -n "file_index" src/launcher/workers/scout/worker.py | head -20

# Step 2: Add constant + cap logic to worker.py

# Step 3: Add 2 fields to ScoutBundle in models/scout.py

# Step 4: Add 2 tests to test_scout.py
# (programmatically create a RepoInfo with 3000 FileEntry objects)

# Step 5: Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout.py -v

# Step 6: Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## THS-13 — Add Quality Gate to Non-Python Workflow Example Extraction

### Status: Not Started

### Gap Linkage
- G-THS-13: TC-4087 line-count heuristic for non-Python workflow examples produces false positives

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
TC-4087 added a doc-scan and line-count heuristic strategy to
`extract_workflow_examples()` for non-Python repos. The line-count strategy
flags any function body ≥3 lines in `.ts`/`.java`/`.cs`/`.go`/`.rs` files
as a "workflow example." This is too broad — short utility methods and
boilerplate code are not workflow examples.

**Apply 3 quality gates to the non-Python line-count heuristic:**

1. **Minimum line count raised to 6** (from 3): A workflow example should
   show a meaningful sequence of operations, not a 3-line getter.

2. **Require at least 2 distinct API object references**: The extracted
   code block must reference ≥2 different identifiers that look like
   product API objects (capitalized names, not built-in keywords). Use
   a simple heuristic: count unique `[A-Z][a-z]+` tokens that appear
   in the code block and are ≥5 characters long. If count < 2, skip.

3. **Require at least one assignment or method-call chain**: The block
   must contain `=` (assignment) or `.` (method call) to be considered
   a usage example rather than a definition.

**Gate implementation location**: `src/launcher/workers/understand/extract/_deterministic.py`

Add a private function:
```python
_MIN_WORKFLOW_LINES = 6
_MIN_WORKFLOW_API_REFS = 2

def _is_quality_workflow_example(
    code_block: str,
    platform: str,
) -> bool:
    """Return True if a non-Python code block is worth including as a workflow example.

    Applies 3 gates:
    1. Block has ≥ _MIN_WORKFLOW_LINES non-blank lines
    2. Block references ≥ _MIN_WORKFLOW_API_REFS distinct capitalized identifiers
    3. Block contains at least one assignment (=) or method call (.)
    """
    lines = [ln for ln in code_block.splitlines() if ln.strip()]
    if len(lines) < _MIN_WORKFLOW_LINES:
        return False
    api_refs = set(re.findall(r'\b[A-Z][a-z][A-Za-z]{3,}\b', code_block))
    if len(api_refs) < _MIN_WORKFLOW_API_REFS:
        return False
    if "=" not in code_block and "." not in code_block:
        return False
    return True
```

Apply this gate in the non-Python workflow example extraction loop.

**Add tests in `tests/unit/workers/understand/test_extract.py`:**

`test_short_non_python_block_filtered`:
- A 4-line TypeScript function with 1 capitalized name → not a workflow example

`test_quality_non_python_block_kept`:
- An 8-line TypeScript block with `Workbook`, `Worksheet`, `.save()` calls → kept

`test_no_api_refs_non_python_filtered`:
- A 7-line block with only lowercase identifiers → filtered (< 2 API refs)

#### Allowed paths
```
src/launcher/workers/understand/extract/_deterministic.py
tests/unit/workers/understand/test_extract.py
```

#### Forbidden
Any other file.

### Acceptance Checks

#### CLI
```bash
# Constants defined
grep "_MIN_WORKFLOW_LINES\|_MIN_WORKFLOW_API_REFS" \
  src/launcher/workers/understand/extract/_deterministic.py
# Expected: 2 matches

# Gate function defined
grep "_is_quality_workflow_example" \
  src/launcher/workers/understand/extract/_deterministic.py
# Expected: ≥2 matches (definition + usage)
```

#### UI/Web/API
N/A.

#### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_extract.py \
  -k "non_python_block or workflow_quality" -v
# Expected: 3 new tests pass

# Regression: existing Python workflow extraction tests still pass
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_extract.py -v
```

#### Config respected end-to-end
`_MIN_WORKFLOW_LINES = 6` is a named constant — easy to adjust if the bar
proves too high/low during pilot runs.

#### No mock data in production paths
Test code blocks must be literal strings in the test — no network.

### Deliverables
- `_is_quality_workflow_example()` function in `_deterministic.py`
- `_MIN_WORKFLOW_LINES = 6` and `_MIN_WORKFLOW_API_REFS = 2` constants
- Gate applied in the non-Python extraction loop (TC-4087 code path)
- 3 new tests in `test_extract.py`

### Hard Rules
- Gate applies ONLY to the non-Python heuristic path — Python AST extraction unchanged
- `_MIN_WORKFLOW_LINES` must be a named constant, not a magic number
- `_is_quality_workflow_example` must be deterministic (no random)
- No network in tests; PYTHONHASHSEED=0

### Review Dimensions — what 5/5 means for THS-13

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | 3 gates (length, API refs, assignment); all 3 tested |
| Consistency | Gate function is a named predicate, consistent with `_is_trivial_docstring` pattern (THS-07) |
| Production grading | False-positive rate reduced; line-count-only heuristic eliminated |
| Systematic approach | Constants → predicate → application → 3 tests |
| Correctness | test_no_api_refs_non_python_filtered verifies the API ref gate specifically |
| Scope adherence | 2 files |
| Maintainability | Named constants make threshold tuning explicit |
| Testability | 3 tests: 2 filter paths + 1 keep path |
| Robustness | Gate handles empty code blocks (line count 0 < 6) without error |
| Performance | Pre-compiled `_CAPITALIZED_RE` regex; O(n) where n = code block chars |
| Integration fit | Gate is a private function in the same module as the extraction logic |
| Observability | DEBUG log: "[deterministic] non-Python example filtered: {reason}" |
| Minimality | 1 function + 2 constants + 1 application site + 3 tests |

### Now (Runbook)

```bash
# Step 1: Find TC-4087 extraction code in _deterministic.py
grep -n "workflow_example\|non_python\|doc.scan\|line.count" \
  src/launcher/workers/understand/extract/_deterministic.py | head -20

# Step 2: Add _MIN_WORKFLOW_LINES, _MIN_WORKFLOW_API_REFS constants
# Step 3: Add _is_quality_workflow_example() function
# Step 4: Apply gate in the extraction loop (wrap existing yield/append in if gate)

# Step 5: Add 3 tests to test_extract.py
# Step 6: Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_extract.py -v

# Step 7: Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## THS-14 — Declare tree-sitter as Optional Dependency in pyproject.toml

### Status: Not Started

### Gap Linkage
- G-THS-14: tree-sitter not declared in `pyproject.toml` optional dependencies

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
Add tree-sitter to `pyproject.toml` as an optional extras group so that:
1. Installing without the extra (default) is safe — tree-sitter is not required
2. The correct install command is documented and discoverable
3. The ImportError in the code that tries to import tree-sitter becomes
   a more helpful error with an install hint

**Step 1 — Add to `pyproject.toml`:**
```toml
[project.optional-dependencies]
tree-sitter = [
    "tree-sitter>=0.23,<1.0",
    "tree-sitter-python>=0.23,<1.0",
    "tree-sitter-typescript>=0.23,<1.0",
    "tree-sitter-java>=0.23,<1.0",
    "tree-sitter-c-sharp>=0.23,<1.0",
]
```

Verify the exact version constraints are compatible with the project's Python
version requirement before committing.

**Step 2 — Improve the ImportError in the tree-sitter loader:**

Find where tree-sitter is imported in the codebase:
```bash
grep -rn "import tree_sitter\|from tree_sitter" src/
```

Wrap the import in a try/except that provides the install hint:
```python
try:
    import tree_sitter
    from tree_sitter import Language, Parser
    _TREE_SITTER_AVAILABLE = True
except ImportError:
    _TREE_SITTER_AVAILABLE = False
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "tree-sitter not installed — TypeScript/Java/C# API extraction disabled. "
        "Install with: pip install 'foss-launcher[tree-sitter]'"
    )
```

This pattern already exists in the codebase for optional deps (check other
optional dep handling for the exact style).

**Step 3 — Update `self_review()` in TC-4085** to use the install hint:
The diagnostic message should already say:
`"run: pip install 'foss-launcher[tree-sitter]'"`
Verify the message uses this exact extras syntax after Step 1.

#### Allowed paths
```
pyproject.toml
```
Plus the file(s) found by the Step 2 grep (tree-sitter import location).
If the ImportError is already wrapped with a helpful message, Step 2 may be
a no-op — verify before writing.

#### Forbidden
`src/launcher/workers/understand/worker.py` for anything beyond the
install hint message update (Step 3 is a message update only).

### Acceptance Checks

#### CLI
```bash
# Optional dep declared
grep "tree-sitter" pyproject.toml
# Expected: ≥2 matches (extras section + package names)

# Install command verifiable
python -c "
import tomllib
data = tomllib.load(open('pyproject.toml', 'rb'))
assert 'tree-sitter' in data['project']['optional-dependencies']
print('OK')
"

# ImportError message includes install hint
grep -rn "pip install.*tree-sitter\|foss-launcher\[tree" src/
# Expected: ≥1 match in the tree-sitter import wrapper
```

#### UI/Web/API
After `pip install 'foss-launcher[tree-sitter]'`:
TypeScript extraction must work (verified by running Scout on a TS fixture).

#### Tests
```bash
# Existing tests still pass (tree-sitter optional means tests without it pass)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q

# Test that _TREE_SITTER_AVAILABLE=False when not installed
# (this test should mock the import failure)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/ -k "tree_sitter" -v
```

#### Config respected end-to-end
Standard `pip install foss-launcher` (without extras) must not fail due to
tree-sitter. All non-TypeScript/Java/C# pipeline runs must work without it.

#### No mock data in production paths
The `_TREE_SITTER_AVAILABLE` flag is checked at runtime — no hardcoded True/False.

### Deliverables
- `[project.optional-dependencies]` tree-sitter group in `pyproject.toml`
- ImportError wrapper with install hint in the tree-sitter import location
- Version constraints verified against current Python environment

### Hard Rules
- `pip install foss-launcher` (no extras) MUST NOT install tree-sitter automatically
- Version constraints must use `>=X,<Y` (not `latest` or unpinned)
- ImportError wrapper must log at WARNING (not raise — tree-sitter is optional)
- If an existing ImportError wrapper already exists, update the message only;
  do not create a duplicate try/except

### Review Dimensions — what 5/5 means for THS-14

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | pyproject.toml updated; ImportError wrapper has install hint; self_review message uses extras syntax |
| Consistency | Same optional-dep extras pattern as other optional dependencies in the project |
| Production grading | `pip install foss-launcher` does not pull in tree-sitter; users get a clear install hint |
| Systematic approach | grep to find import → wrap → declare → verify |
| Correctness | test verifies `_TREE_SITTER_AVAILABLE=False` path is safe |
| Scope adherence | pyproject.toml + tree-sitter import file + (optionally) self_review message |
| Maintainability | Extras group name `tree-sitter` matches the package name — easy to remember |
| Testability | `_TREE_SITTER_AVAILABLE` flag makes the ImportError path testable via mocking |
| Robustness | WARNING log emitted when tree-sitter absent — not a silent failure |
| Performance | N/A |
| Integration fit | Optional dep extras pattern is standard Python packaging |
| Observability | WARNING visible at pipeline startup when tree-sitter is absent |
| Minimality | 1–2 files changed; no new feature code |

### Now (Runbook)

```bash
# Step 1: Find tree-sitter import location
grep -rn "import tree_sitter\|from tree_sitter" src/

# Step 2: Verify if ImportError is already wrapped
# Step 3: Update pyproject.toml
# (Add [project.optional-dependencies] tree-sitter group)

# Step 4: Verify TOML is valid
python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('OK')"

# Step 5: If ImportError not yet wrapped — add wrapper
# If already wrapped — update message to include extras syntax

# Step 6: Full suite (tree-sitter NOT installed — standard CI path)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
