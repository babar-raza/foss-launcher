# Healing Plan: SQP Code Correctness Bugs

**Source gap index**: `plans/healing/SQP-00-gap-index.md`
**Covers gaps**: SQP-G01, SQP-G02, SQP-G03

---

## Taskcard SQP-H1 — Fix missed `shared_facts` pass in `worker.py`

**Status**: Not Started
**Gap linkage**: SQP-G01
**Role**: Senior engineer. Drop-in, production-ready.

### Problem

`_extract_product_evidence()` in `worker.py` contains a **second** call to
`extract_install_recipe()` at the `# TC-HYBRID-04` block (lines 507-518). This call uses
the old two-argument signature `_extract_recipe(repo_dir, product)` without the `shared_facts`
optional argument added by TC-4030. On any Python repo with `pyproject.toml`, this triggers
Strategy 1 (disk read) every single run, meaning the true reduction is **4 → 3 reads**, not
the claimed **4 → 2**.

The fix is a single keyword argument addition. `repo_info` is already available in scope.

### Scope

**Fix**:
- In `src/launcher/workers/understand/worker.py`, inside `_extract_product_evidence()`,
  change the `_extract_recipe(repo_dir, product)` call to
  `_extract_recipe(repo_dir, product, shared_facts=repo_info.shared_facts)`.
- No other logic changes.

**Allowed paths**:
- `src/launcher/workers/understand/worker.py`

**Forbidden**: any other file or path.

### Implementation

Locate the `# TC-HYBRID-04` comment block in `_extract_product_evidence()`:

```python
# BEFORE (line ~511):
_recipe = _extract_recipe(repo_dir, product)

# AFTER:
_recipe = _extract_recipe(repo_dir, product, shared_facts=repo_info.shared_facts)
```

`repo_info` is already a parameter of `_extract_product_evidence(repo_dir, repo_info, product, context)`.
No import changes needed; `shared_facts` is an attribute of `RepoInfo`.

### Acceptance checks

**CLI**: Run a understand-worker pass against a Python repo with `pyproject.toml`.
Confirm that `extract_install_recipe` log line shows `source_file=pyproject.toml (cached)`
and that no second `pyproject.toml` read appears in a trace/debug log.

**UI/Web/API**: N/A — internal worker change.

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_understand_product_evidence.py \
  tests/unit/workers/understand/ \
  -x -q
```
All existing tests pass. The dedicated test (SQP-H4 deliverable) asserts
`_extract_recipe` is called with `shared_facts` in `_extract_product_evidence`.

**Config respected end-to-end**: `shared_facts.package_name` must be non-empty for the
cache bypass to activate. Repos without `pyproject.toml` correctly fall through to
Strategy 2+ unchanged.

**No mock data in production paths**: the change relies only on `repo_info.shared_facts`
which is always populated by Scout (Phase A) before Phase B begins.

### Deliverables

1. **Full file replacement** for `src/launcher/workers/understand/worker.py` with the
   single argument addition — no other lines touched.
2. Updated test asserting `shared_facts` is forwarded (delivered by SQP-H4).

### Hard rules

- Keep public signatures unless justified; update all call sites — `_extract_recipe` is
  imported locally inside the try block; its signature already has `shared_facts=None`
  (added by TC-4030), so no signature change is needed here.
- No network in offline tests.
- Deterministic: `shared_facts` is deterministically populated by Scout; no non-determinism introduced.
- No new deps.

### Review dimensions — what "5/5" means for this taskcard

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | `worker.py` call forwards `shared_facts`; pyproject.toml not re-opened on Python repos when Scout already ran |
| Thoroughness | Single-site change; verified no other call sites of `extract_install_recipe` are missing `shared_facts` |
| Scope adherence | Exactly one line changed in exactly one file |
| Testability | Dedicated test mocks `builtins.open` to assert pyproject.toml not opened in this code path |
| Minimality | Diff is ≤ 3 lines |

### Now (runbook)

```bash
# 1. Read the current file to confirm the line
grep -n "_extract_recipe(repo_dir, product)" \
  src/launcher/workers/understand/worker.py

# 2. Edit: add shared_facts= kwarg to that call

# 3. Verify tests pass
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_understand_product_evidence.py -x -q

# 4. Verify no regression in understand tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/ -x -q
```

---

## Taskcard SQP-H2 — Fix Poetry "python" dep key not excluded in `_parse_pyproject()`

**Status**: Not Started
**Gap linkage**: SQP-G02
**Role**: Senior engineer. Drop-in, production-ready.

### Problem

In `_parse_pyproject()` inside `scout.py`, the line that extracts Poetry dependencies is:

```python
raw_deps = project.get("dependencies", []) or list(poetry.get("dependencies", {}).keys())
```

When `project.dependencies` is empty/absent and the repo uses Poetry, this produces a **list**
from `.keys()` — so the `elif isinstance(raw_deps, dict)` branch that filters `"python"` is
**never reached** (the value is already a list, not a dict, at that point). The result:
`SharedFacts.dependencies` includes `"python"` as a dependency for every Poetry repo,
polluting the field with a version-constraint key rather than a real package name.

### Scope

**Fix**:
- In `src/launcher/workers/understand/scout.py`, change the Poetry deps extraction line
  to exclude `"python"` at the point of key extraction.
- Remove the now-unreachable `elif isinstance(raw_deps, dict)` branch (dead code).
- Keep the `isinstance(raw_deps, list)` guard for the `project.dependencies` path (list
  is the correct TOML type per PEP 517/518).

**Allowed paths**:
- `src/launcher/workers/understand/scout.py`

**Forbidden**: any other file or path.

### Implementation

```python
# BEFORE (in the tomllib branch of _parse_pyproject()):
raw_deps = project.get("dependencies", []) or list(poetry.get("dependencies", {}).keys())
if isinstance(raw_deps, list):
    dependencies = [str(d) for d in raw_deps if isinstance(d, str)]
elif isinstance(raw_deps, dict):
    # Poetry-style dict: {requests: "^2.0", ...} — exclude "python" key
    dependencies = [k for k in raw_deps if k != "python"]
else:
    dependencies = []

# AFTER:
raw_project_deps = project.get("dependencies", [])
if isinstance(raw_project_deps, list) and raw_project_deps:
    # PEP 508 list format: ["requests>=2.0", ...]
    dependencies = [str(d).split(">=")[0].split("==")[0].split("[")[0].strip()
                    for d in raw_project_deps if isinstance(d, str)]
elif isinstance(raw_project_deps, dict):
    # Unusual: dict-format project deps — filter non-package keys
    dependencies = [k for k in raw_project_deps if k != "python"]
else:
    # Fall back to Poetry-style: {requests: "^2.0", python: "^3.9", ...}
    poetry_deps = poetry.get("dependencies", {})
    dependencies = [k for k in poetry_deps if k != "python"]
```

Note: the `raw_deps` variable is eliminated; the logic is made explicit per source.

### Acceptance checks

**CLI**: Parse a Poetry `pyproject.toml` with `[tool.poetry.dependencies]` containing
`python = "^3.9"` and `requests = "^2.28"`. Assert `SharedFacts.dependencies == ["requests"]`.

**UI/Web/API**: N/A.

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout_facts.py -x -q -k "poetry or deps"
```
New test (SQP-H4 deliverable) covers:
- Poetry format: `"python"` not in `SharedFacts.dependencies`
- PEP 508 list format: dependency names extracted correctly
- Empty `[project]` + empty `[tool.poetry]`: `dependencies == []`

**Config respected end-to-end**: repos without either format return `dependencies == []`
(both branches fall to empty list).

**No mock data in production paths**: test uses `tmp_path` with real TOML content,
no mock of tomllib.

### Deliverables

1. **Full file replacement** for `src/launcher/workers/understand/scout.py` with the
   corrected deps extraction logic in `_parse_pyproject()` and dead `elif isinstance(raw_deps, dict)`
   branch removed.
2. New test cases in `tests/unit/workers/test_scout_facts.py` (delivered by SQP-H4).

### Hard rules

- No new deps (tomllib is stdlib Python 3.11+; already in use).
- Keep the regex-fallback path returning `[]` for dependencies — no change there.
- Deterministic: sorted dep list output (optional improvement, not required).

### Review dimensions — what "5/5" means for this taskcard

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | `"python"` never appears in `SharedFacts.dependencies` for any supported TOML format |
| Robustness | Empty, dict, list, and None values for `dependencies` all handled without raising |
| Testability | Three distinct TOML formats tested: PEP 508 list, Poetry dict, absent field |
| Minimality | Only `_parse_pyproject()` modified; diff is < 15 lines |
| Spec alignment | `SharedFacts.dependencies` contains only installable package names, consistent with the field description |

### Now (runbook)

```bash
# 1. Read the current _parse_pyproject() function
grep -n "raw_deps\|dependencies" src/launcher/workers/understand/scout.py | head -20

# 2. Edit the deps extraction block as shown above

# 3. Quick smoke test
python -c "
import tomllib, pathlib, sys
sys.path.insert(0, 'src')
from launcher.workers.understand.scout import _parse_pyproject
import tempfile, pathlib
with tempfile.NamedTemporaryFile(suffix='.toml', delete=False, mode='wb') as f:
    f.write(b'''
[tool.poetry.dependencies]
python = \"^3.9\"
requests = \"^2.28\"
''')
    p = pathlib.Path(f.name)
result = _parse_pyproject(p)
print('deps:', result[5])  # index 5 = dependencies
assert 'python' not in result[5], 'python key leaked!'
print('OK')
"

# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout_facts.py -x -q
```

---

## Taskcard SQP-H3 — Fix `specs.index()` O(N²) and break logic in `_add_go_iota_enums()`

**Status**: Not Started
**Gap linkage**: SQP-G03
**Role**: Senior engineer. Drop-in, production-ready.

### Problem

`_add_go_iota_enums()` in `ts_analyzer.py` contains:

```python
for spec in specs:
    for child in spec.children:
        if child.type == "type_identifier":
            candidate = child.text.decode()
            if not type_name:
                type_name = candidate
            elif type_name != candidate:
                type_name = ""
                break
    if not type_name and specs.index(spec) > 0:
        break
```

Two problems:
1. `specs.index(spec)` is O(N) per spec → O(N²) total for a const block with N specs.
   For generated Go code (e.g., protobuf enums with 200+ values), this is measurable.
2. The break condition `if not type_name and specs.index(spec) > 0` fires when the
   CURRENT spec has no type_identifier AND it is not the first spec. But `type_name`
   can be `""` for two reasons: (a) the first spec never had a type (never set), or
   (b) a mismatch was detected in an earlier spec. In case (a) for the second spec,
   the break exits prematurely even if later specs have a consistent type — incorrect
   for iota blocks where only the first const specifies the type.

The fix replaces `specs.index(spec)` with `enumerate` and tightens the break logic
to: "exit early only if a type mismatch was detected (type was non-empty then cleared)".

### Scope

**Fix**:
- In `src/launcher/shared/ts_analyzer.py`, in `_add_go_iota_enums()`,
  replace the `for spec in specs` loop with `for i, spec in enumerate(specs)`,
  and replace `specs.index(spec) > 0` with `i > 0`.
- Introduce a `type_mismatch` sentinel boolean to distinguish "never set" from
  "was set then cleared", and only `break` on actual type mismatch.

**Allowed paths**:
- `src/launcher/shared/ts_analyzer.py`

**Forbidden**: any other file or path.

### Implementation

```python
# BEFORE:
type_name = ""
for spec in specs:
    for child in spec.children:
        if child.type == "type_identifier":
            candidate = child.text.decode()
            if not type_name:
                type_name = candidate
            elif type_name != candidate:
                type_name = ""
                break
    if not type_name and specs.index(spec) > 0:
        break

# AFTER:
type_name = ""
type_mismatch = False
for i, spec in enumerate(specs):
    for child in spec.children:
        if child.type == "type_identifier":
            candidate = child.text.decode()
            if not type_name:
                type_name = candidate
            elif type_name != candidate:
                type_name = ""
                type_mismatch = True
                break
    if type_mismatch:
        break
```

This also fixes the case where the first spec has no `type_identifier` but later specs
do — now we won't prematurely break and will correctly detect the consistent type.

### Acceptance checks

**CLI**: Parse a Go file with a 3-spec iota const block where only the first spec
has a type annotation. Assert a synthetic enum entry is returned with all 3 members.

**UI/Web/API**: N/A.

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/test_ts_analyzer.py -x -q -k "iota or go_enum"
```
New test (SQP-H4 deliverable) covers:
- Standard iota block (first spec has type, rest inherit) → enum returned
- Mixed-type iota block → no enum returned (type_mismatch fires)
- 200-spec iota block → completes without O(N²) slowdown (timing assertion or just correctness)

**Config respected end-to-end**: no configuration change; behaviour is purely
in-process tree-sitter traversal.

**No mock data in production paths**: tests use real Go source snippets parsed
via `ts_analyzer.analyze_file()` against a `tmp_path` file.

### Deliverables

1. **Full file replacement** for `src/launcher/shared/ts_analyzer.py` — only
   the `_add_go_iota_enums()` method body changes; everything else is identical.
2. New test cases in `tests/unit/shared/test_ts_analyzer.py` (delivered by SQP-H4).

### Hard rules

- No new deps.
- Deterministic: tree-sitter parsing is deterministic given the same source; no
  change to ordering or hashing.
- Keep the deduplication guard `if type_name in existing_names: continue` —
  it remains correct and unchanged.

### Review dimensions — what "5/5" means for this taskcard

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | Standard Go iota const block (`type WeekDay int` + 7 day constants) produces one synthetic enum with 7 members |
| Performance | O(N) loop (single pass via enumerate); no `list.index()` calls |
| Robustness | Mixed-type const block → no enum emitted; empty const block → no crash |
| Testability | Go source fragment parsed from `tmp_path`; no mocking required |
| Minimality | Only `_add_go_iota_enums()` method body changed; diff < 10 lines |

### Now (runbook)

```bash
# 1. Locate the method
grep -n "specs.index\|for spec in specs" src/launcher/shared/ts_analyzer.py

# 2. Apply the enumerate + type_mismatch patch

# 3. Smoke test (requires tree-sitter-language-pack with Go grammar)
python -c "
import sys, tempfile, pathlib
sys.path.insert(0, 'src')
from launcher.shared.ts_analyzer import analyzer
go_src = '''
package example
type Direction int
const (
    North Direction = iota
    South
    East
    West
)
'''
with tempfile.NamedTemporaryFile(suffix='.go', delete=False, mode='w') as f:
    f.write(go_src)
    p = pathlib.Path(f.name)
result = analyzer.analyze_file(p, language='go')
enums = [c for c in result.classes if c.get('is_enum')]
print('enums:', enums)
assert len(enums) == 1
assert enums[0]['name'] == 'Direction'
print('OK')
"

# 4. Run ts_analyzer tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/test_ts_analyzer.py -x -q
```
