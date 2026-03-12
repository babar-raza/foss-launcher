# Healing Plan: SQP Observability and Maintainability

**Source gap index**: `plans/healing/SQP-00-gap-index.md`
**Covers gaps**: SQP-G05, SQP-G06

---

## Taskcard SQP-H5 — Add observability for SharedFacts enrichment and Go/C++ extraction

**Status**: Not Started
**Gap linkage**: SQP-G05
**Role**: Senior engineer. Drop-in, production-ready.

### Problem

Two silent code paths were introduced by TC-4030 and TC-4031:

1. **Scout (`scout.py`)**: `_extract_shared_facts()` populates 4 new fields (`description`,
   `python_requires`, `dependencies`, `entrypoints`) from `pyproject.toml` but emits **no log
   output** indicating that enrichment occurred or what values were found. In production, if
   `SharedFacts.package_name` is populated but `dependencies` is empty (e.g., Poetry path bug),
   there is zero signal in the logs to diagnose the cause.

2. **Tree-sitter analyzer (`ts_analyzer.py`)**: `_extract_go_iota_enums()` runs silently after
   normal class extraction. When it finds and emits a synthetic enum — or when it finds a const
   block but skips it — there is no debug log. Similarly, the C++ `field_declaration_list`
   traversal path inside `_extract_class()` has no trace output, making it impossible to
   distinguish "C++ grammar unavailable" from "C++ grammar loaded but struct has no public
   members" from "C++ grammar loaded and fields extracted".

3. **`_cpp.py` adapter**: The fallback log level is `debug` — too low for a fallback path that
   represents degraded behavior. Should be `warning`.

### Scope

**Fix**:
- In `src/launcher/workers/understand/scout.py`, inside `_extract_shared_facts()`, add a
  `logger.debug` after the `SharedFacts` object is constructed, emitting the count of
  dependencies, entrypoints, and presence of description/python_requires.
- In `src/launcher/shared/ts_analyzer.py`, inside `_add_go_iota_enums()`, add a `logger.debug`
  for each synthetic enum emitted, and a separate `logger.debug` when a const block is skipped
  (type mismatch or no iota). Inside `_extract_class()`, add a `logger.debug` at the entry to
  the `field_declaration_list` traversal block for C++.
- In `src/launcher/workers/understand/adapters/_cpp.py`, raise the fallback log from
  `logger.debug` to `logger.warning`.

**Allowed paths**:
- `src/launcher/workers/understand/scout.py`
- `src/launcher/shared/ts_analyzer.py`
- `src/launcher/workers/understand/adapters/_cpp.py`

**Forbidden**: any other file or path.

### Implementation

#### scout.py — `_extract_shared_facts()`

```python
# AFTER constructing shared_facts object, BEFORE returning it:
logger.debug(
    "shared_facts_enriched: package=%s version=%s deps=%d entrypoints=%d"
    " python_requires=%r description_present=%s",
    shared_facts.package_name,
    shared_facts.version,
    len(shared_facts.dependencies),
    len(shared_facts.entrypoints),
    shared_facts.python_requires,
    bool(shared_facts.description),
)
```

#### ts_analyzer.py — `_add_go_iota_enums()`

```python
# Inside the loop where a synthetic enum is appended:
logger.debug(
    "go_iota_enum_found: type=%s members=%d file=%s",
    type_name, len(member_names), rel_path,
)

# After the break on type_mismatch OR at the end of the outer loop when skipping:
logger.debug(
    "go_iota_enum_skipped: reason=type_mismatch file=%s", rel_path
)
```

#### ts_analyzer.py — `_extract_class()` C++ body block

```python
# At the entry to the field_declaration_list block for C++:
logger.debug(
    "cpp_field_extraction_start: class=%s access_default=%s file=%s",
    class_name, access, rel_path,
)
# After extraction loop:
logger.debug(
    "cpp_field_extraction_done: class=%s properties=%d methods=%d file=%s",
    class_name, len(property_details), len(method_details), rel_path,
)
```

#### _cpp.py — fallback log level

```python
# BEFORE (in extract_class_details except block):
logger.debug("cpp_ts_analyzer_failed, falling back to code_analyzer", exc_info=True)

# AFTER:
logger.warning("cpp_ts_analyzer_failed, falling back to code_analyzer", exc_info=True)
```

### Acceptance checks

**CLI**: Run a understand-worker pass against a Python repo with `pyproject.toml` at `DEBUG`
log level. Confirm that `shared_facts_enriched` appears in stdout/stderr with non-zero dep count.

**UI/Web/API**: N/A — logging change only.

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout_facts.py \
  tests/unit/workers/understand/ \
  tests/unit/shared/ \
  -x -q
```
All existing tests pass. No new tests required for log statements (log content is not part of
the public contract; asserting log output is fragile and not project convention).

**Config respected end-to-end**: `logger.debug` lines are no-ops unless DEBUG level enabled;
no production performance impact.

**No mock data in production paths**: changes are pure log additions; no logic changes.

### Deliverables

1. Modified `src/launcher/workers/understand/scout.py` — one `logger.debug` added to
   `_extract_shared_facts()`.
2. Modified `src/launcher/shared/ts_analyzer.py` — debug logs added to
   `_add_go_iota_enums()` and the C++ body extraction block in `_extract_class()`.
3. Modified `src/launcher/workers/understand/adapters/_cpp.py` — one log level change
   (`debug` → `warning` in the fallback except block).

### Hard rules

- No new deps.
- Log messages must be machine-parseable (`key=value` format).
- Do NOT add `logger.info` for hot paths (called per file in a repo); use `logger.debug` only.
- The `_cpp.py` fallback change is the only `warning` (appropriate: degraded behavior).
- No logic changes. No new branches. No restructuring.

### Review dimensions — what "5/5" means for this taskcard

| Dimension | 5/5 criterion |
|-----------|---------------|
| Observability coverage | All three silent paths now emit debug output: SharedFacts enrichment, iota enum detection, C++ field extraction |
| Signal quality | Log messages use `key=value` format; include counts + names, not just booleans |
| Performance | All new logs are `logger.debug` guarded by level check; zero overhead unless DEBUG enabled |
| Scope adherence | Exactly 3 files changed; no logic changes |
| C++ fallback severity | `logger.warning` now matches the "degraded behavior" semantic |

### Now (runbook)

```bash
# 1. Add logger.debug to scout.py _extract_shared_facts()
# 2. Add logger.debug to ts_analyzer.py _add_go_iota_enums() + C++ block
# 3. Change logger.debug → logger.warning in _cpp.py fallback
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout_facts.py \
  tests/unit/workers/understand/ \
  tests/unit/shared/ \
  -x -q
```

---

## Taskcard SQP-H6 — Refactor `_extract_class()` — extract Go/C++ helper methods + fix stale docstrings

**Status**: Not Started
**Gap linkage**: SQP-G06
**Role**: Senior engineer. Drop-in, production-ready.

### Problem

`_extract_class()` in `ts_analyzer.py` has grown to approximately 230 lines. TC-4031 added two
large inline blocks at the bottom — Go struct field extraction and C++ `field_declaration_list`
traversal — both directly inside the method body. This creates three problems:

1. **Readability**: The method handles 4 distinct code paths (generic class, Go struct, C++
   class, property/method extraction) with no named subroutine boundaries.
2. **Testability**: Go and C++ blocks cannot be unit-tested in isolation; tests must provide
   full class AST nodes.
3. **Stale docstrings**: `_extract_class()` docstring still describes the pre-TC-4031 contract
   ("Java, TypeScript, C# body containers"). `_add_go_iota_enums()` has no docstring.
   `_extract_method_params()` docstring does not mention `parameter_declaration` (Go typed params).

### Scope

**Fix**:
- Extract the Go struct field extraction block from `_extract_class()` into a new private
  method `_extract_go_struct_fields(self, body_node, class_name, property_details)`.
- Extract the C++ `field_declaration_list` traversal block into a new private method
  `_extract_cpp_class_body(self, body_node, class_name, node_type, property_details, method_details)`.
- Update `_extract_class()` to call these two helpers.
- Update docstrings for `_extract_class()`, `_add_go_iota_enums()`, `_extract_method_params()`.

**Allowed paths**:
- `src/launcher/shared/ts_analyzer.py`

**Forbidden**: any other file or path. No behavior changes — pure refactor.

### Implementation

#### New helper: `_extract_go_struct_fields()`

```python
def _extract_go_struct_fields(
    self,
    body_node,
    class_name: str,
    property_details: list[dict],
) -> None:
    """TC-4031: Extract exported fields from a Go struct_type or interface_type body.

    Appends to `property_details` in-place. Only exported (uppercase-initial) fields
    are included. Unexported (lowercase-initial) fields are silently skipped.
    """
    for field_decl in body_node.children:
        if field_decl.type != "field_declaration":
            continue
        fname = ""
        ftype = ""
        for sub in field_decl.children:
            if sub.type in ("field_identifier", "identifier") and not fname:
                fname = sub.text.decode()
            elif fname and sub.is_named and sub.type not in ("comment",):
                ftype = sub.text.decode().strip()
        if fname and fname[0].isupper():
            property_details.append({
                "name": fname,
                "type_annotation": ftype,
                "is_readonly": False,
                "docstring_snippet": "",
            })
```

#### New helper: `_extract_cpp_class_body()`

```python
def _extract_cpp_class_body(
    self,
    body_node,
    class_name: str,
    node_type: str,
    property_details: list[dict],
    method_details: list[dict],
) -> None:
    """TC-4031: Extract public members from a C++ field_declaration_list.

    Tracks access_specifier nodes to maintain visibility state. Only `public:`
    members are emitted. Template parameters are stripped from type strings.
    Appends to `property_details` and `method_details` in-place.
    """
    _TMPL_RE = re.compile(r"<[^>]*>")
    access = "public" if node_type == "struct_specifier" else "private"
    for member in body_node.children:
        if member.type == "access_specifier":
            raw = member.text.decode().strip().rstrip(":")
            access = raw.lower()
            continue
        if access != "public":
            continue
        # ... rest of extraction logic
```

#### Updated `_extract_class()` — replace inline blocks with calls

```python
# Go struct/interface body:
elif lang_resolved == "go" and child.type in ("struct_type", "interface_type"):
    for sub_body in child.children:
        if sub_body.type == "field_declaration_list":
            self._extract_go_struct_fields(sub_body, class_name, property_details)

# C++ field_declaration_list:
elif lang_resolved == "cpp" and child.type == "field_declaration_list":
    self._extract_cpp_class_body(
        child, class_name, node.type, property_details, method_details
    )
```

#### Updated docstrings

```python
def _extract_class(self, node, language: str, rel_path: str) -> dict | None:
    """Extract class/struct metadata from a class-like AST node.

    Handles body containers for Java (`class_body`), C# (`declaration_list`),
    TypeScript/JavaScript (`class_body`), Go (`struct_type`, `interface_type`
    via field_declaration_list), and C++ (`field_declaration_list` with
    access_specifier tracking). Delegates Go and C++ body extraction to
    `_extract_go_struct_fields()` and `_extract_cpp_class_body()` respectively.
    """

def _add_go_iota_enums(self, root, result: AnalysisResult, rel_path: str) -> None:
    """Post-pass: detect Go iota const blocks and emit synthetic enum class entries.

    Walks top-level const_declaration nodes. If all const_spec children in a block
    share a single type annotation, emits a synthetic dict with is_enum=True and
    enum_members listing all spec names. Deduplicates against existing class names.
    Called from analyze_file() after normal extraction when language is Go.
    """

def _extract_method_params(self, param_list_node, language: str) -> list[dict]:
    """Extract typed parameters from a parameter list node.

    Recognizes: required_parameter, optional_parameter (TypeScript/JavaScript),
    formal_parameter (Java), parameter (C#), and parameter_declaration (Go —
    TC-4031: identifier + type siblings). Returns list of
    {"name": str, "type_annotation": str} dicts.
    """
```

### Acceptance checks

**CLI**: N/A — pure refactor; behavior unchanged.

**UI/Web/API**: N/A.

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/ \
  tests/unit/workers/understand/ \
  -x -q
```
All existing tests pass. No new tests required (helpers are tested indirectly via
`_extract_class()` and `analyze_file()` in existing + SQP-H4 tests).

**No behavior change**: The refactor must produce identical output to the pre-refactor version
for all inputs. Verify by running the ts_analyzer smoke test from TC-4031 runbook against the
same Go and C++ snippets.

**No mock data in production paths**: no change to production logic.

### Deliverables

1. Modified `src/launcher/shared/ts_analyzer.py`:
   - New `_extract_go_struct_fields()` method
   - New `_extract_cpp_class_body()` method
   - `_extract_class()` reduced by ~60 lines; calls two new helpers
   - Updated docstrings for `_extract_class()`, `_add_go_iota_enums()`, `_extract_method_params()`

### Hard rules

- No behavior changes. If the output of `analyze_file()` changes for ANY input, the refactor is wrong.
- Do not move `_TMPL_RE` regex compile out of the helper into module scope unless it was already there.
- Keep `_extract_go_struct_fields` and `_extract_cpp_class_body` as private methods (leading underscore).
- No new deps.
- Helper method signatures must accept only primitive types or AST nodes — no new model imports.

### Review dimensions — what "5/5" means for this taskcard

| Dimension | 5/5 criterion |
|-----------|---------------|
| Behavior parity | `analyze_file()` output byte-for-byte identical before and after refactor for Go and C++ inputs |
| Readability | `_extract_class()` reduced to ≤170 lines; no inline block >40 lines |
| Docstring accuracy | All three updated docstrings enumerate every handled node type |
| Minimality | Exactly 1 file changed; no logic change, only restructuring |
| Test pass | 100% of tests/unit/shared/ and tests/unit/workers/understand/ pass unchanged |

### Now (runbook)

```bash
# 1. Read the current _extract_class() method in full
# 2. Extract _extract_go_struct_fields() and _extract_cpp_class_body() as new methods
# 3. Replace inline blocks with calls to new helpers
# 4. Update 3 docstrings
# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/ \
  tests/unit/workers/understand/ \
  -x -q
# 6. Run smoke test (same snippet as TC-4031 runbook) to verify behavior parity
```
