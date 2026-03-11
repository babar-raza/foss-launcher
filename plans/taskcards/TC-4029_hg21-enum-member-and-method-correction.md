---
id: TC-4029
title: "HG-21: Enum member access validation + method name correction in code blocks"
status: Done
priority: High
owner: "generate"
updated: "2026-03-11"
tags: [humming-greeting-kay, generate, hallucination, post-generation-repair, bugfix]
depends_on: [TC-4028]
ruleset_version: "1.0"
spec_ref: "d0f708ac"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4029_hg21-enum-member-and-method-correction.md
  - src/launcher/workers/generate/section_validator.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/test_section_validator.py
evidence_required:
  - phase_store/pilot_quality_report.md
---

# Taskcard TC-4029 — HG-21: Enum Member Access Validation + Method Name Correction

## Objective

HG-20 pilot (27% A+B, 0% D+F) shows two remaining hallucination patterns:
1. **Enum member access**: `FileFormat.OBJ`, `FileFormat.STLASCII`, `FileFormat.STLBINARY` — the LLM
   uses ALL-CAPS enum member names not in the API surface (e.g., `OBJ` instead of `WAVEFRONT_OBJ`,
   `STLASCII`/`STLBINARY` which don't exist). Code blocks with these are `factual_accuracy/high`.
2. **Method name wrong**: `create_child_node` used instead of `add_child_node` on `Node` class —
   causing `factual_accuracy/high` and `api_consistency/high` on 5+ pages.

HG-21 adds two new post-generation repair passes:
- `_strip_hallucinated_enum_member_access`: removes code blocks using invalid ALL-CAPS class members
- `_correct_method_names_in_code`: corrects known-wrong method names using suffix-matching against typed_methods

## Required spec references

- `phase_store/pilot_quality_report.md` — HG-20 pilot showing FileFormat.OBJ, STLASCII, create_child_node as blockers

## Scope

### In scope

- New `_ENUM_ACCESS_RE` regex in `section_validator.py`
- New `_strip_hallucinated_enum_member_access(blocks, class_enum_members)` in `section_validator.py`
- New `_correct_method_names_in_code(blocks, corrections)` in `section_validator.py`
- Build `class_enum_members` and `method_corrections` in `worker.py` from `class_briefs`
- Call both new functions in the post-generation repair pipeline
- Unit tests for both functions

### Out of scope

- Changing `_CLASS_USAGE_RE` (HG-18/20)
- Changing `_strip_hallucinated_code_blocks` (HG-16/17/18/20)
- Non-Python code block handling

## Inputs

- `src/launcher/workers/generate/section_validator.py` — existing repair functions
- `src/launcher/workers/generate/worker.py` — HG-16 call site (lines ~851-860)
- `class_briefs: list[ClassBrief]` — available in `_generate_page` scope

## Outputs

- Two new functions in `section_validator.py`
- Updated `worker.py` with lookup table building and new repair calls
- 4+ new unit tests

## Allowed paths

- plans/taskcards/TC-4029_hg21-enum-member-and-method-correction.md
- src/launcher/workers/generate/section_validator.py
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/test_section_validator.py

### Allowed paths rationale

`section_validator.py` contains all repair functions. `worker.py` builds lookup tables from class_briefs
and calls the repair functions. `test_section_validator.py` has the HG-16 test class.

## Implementation steps

### Step 1: Add enum member validation to `section_validator.py`

Add after `_CLASS_USAGE_RE` definition:

```python
# HG-21: Detect ClassName.ALL_CAPS_MEMBER patterns (enum-like access)
_ENUM_ACCESS_RE = re.compile(r'\b([A-Z][A-Za-z0-9]+)\.([A-Z][A-Z0-9_]{2,})\b')


def _strip_hallucinated_enum_member_access(
    blocks: list[BlockIR],
    class_enum_members: dict[str, set[str]],
) -> list[BlockIR]:
    """Remove Python code blocks that access invalid ALL-CAPS enum members on known classes.

    HG-21: Detects patterns like FileFormat.STLASCII or FileFormat.OBJ where FileFormat
    is a known API class but STLASCII / OBJ are not in its documented members. Such blocks
    are removed because they will cause factual_accuracy/api_consistency review failures.

    Parameters
    ----------
    blocks:
        BlockIR list from post-generate parsing.
    class_enum_members:
        dict mapping class name → set of valid ALL-CAPS member names.
        Built from class_briefs.typed_methods where name.upper() == name.
        If empty, the repair pass is skipped.
    """
    if not class_enum_members:
        return blocks

    result: list[BlockIR] = []
    for block in blocks:
        if block.type != BlockType.code or (block.language or "").lower() != "python":
            result.append(block)
            continue

        code = block.content or ""
        # Strip comment content before scanning (HG-17)
        code_for_scanning = "\n".join(line.split("#")[0] for line in code.split("\n"))
        if not code_for_scanning.strip():
            result.append(block)
            continue

        hallucinated: list[str] = []
        for m in _ENUM_ACCESS_RE.finditer(code_for_scanning):
            class_name = m.group(1)
            member_name = m.group(2)
            if class_name not in class_enum_members:
                continue  # Unknown class → no opinion
            if member_name in class_enum_members[class_name]:
                continue  # Valid member → keep
            hallucinated.append(f"{class_name}.{member_name}")

        if hallucinated:
            logger.debug(
                "[HG-21] Removing code block with invalid enum member(s): %s", hallucinated,
            )
        else:
            result.append(block)

    return result
```

### Step 2: Add method name correction to `section_validator.py`

Add after `_strip_hallucinated_enum_member_access`:

```python
_METHOD_CALL_RE = re.compile(r'\b(\w+)\s*\(')


def _correct_method_names_in_code(
    blocks: list[BlockIR],
    corrections: dict[str, str],
) -> list[BlockIR]:
    """Replace known-wrong method names in Python code blocks.

    HG-21: LLM hallucinates method names that are similar to real API methods
    (e.g., create_child_node instead of add_child_node). This function applies
    data-driven corrections derived from typed_methods suffix matching.

    Parameters
    ----------
    blocks:
        BlockIR list.
    corrections:
        dict mapping wrong_name → right_name.
        Computed in worker.py from api_identifiers vs typed_methods comparison.
        If empty, skipped.
    """
    if not corrections:
        return blocks

    result: list[BlockIR] = []
    for block in blocks:
        if block.type != BlockType.code or (block.language or "").lower() != "python":
            result.append(block)
            continue

        code = block.content or ""
        corrected = code
        applied: list[str] = []
        for wrong, right in corrections.items():
            # Only replace as method call (followed by open paren with optional whitespace)
            pattern = re.compile(r'\b' + re.escape(wrong) + r'\b')
            if pattern.search(corrected):
                corrected = pattern.sub(right, corrected)
                applied.append(f"{wrong}→{right}")

        if applied:
            logger.debug("[HG-21] Corrected method names in code block: %s", applied)
            result.append(block.model_copy(update={"content": corrected}))
        else:
            result.append(block)

    return result
```

### Step 3: Build lookup tables and call new functions in `worker.py`

In `_generate_page`, after the existing HG-16 block (around line 858):

```python
# HG-21: Enum member access validation
class_enum_members: dict[str, set[str]] = {}
if class_briefs:
    for brief in class_briefs:
        caps = {
            m.name for m in (brief.typed_methods or [])
            if m.name == m.name.upper() and len(m.name) >= 3
        }
        if caps:
            class_enum_members[brief.name] = caps

# HG-21: Method name correction (data-driven from suffix matching)
method_corrections: dict[str, str] = {}
if class_briefs and api_identifiers:
    typed_methods_set = {
        m.name for b in class_briefs for m in (b.typed_methods or [])
    }
    for ident in api_identifiers:
        if "_" not in ident or ident not in ident.lower():  # only snake_case
            continue
        if ident in typed_methods_set:
            continue  # Valid method, skip
        parts = ident.split("_", 1)
        if len(parts) < 2 or len(parts[1]) < 8:
            continue  # Suffix too short → too many false positives
        suffix = parts[1]
        matches = [m for m in typed_methods_set if m.endswith("_" + suffix)]
        if len(matches) == 1:
            method_corrections[ident] = matches[0]

if blocks:
    if class_enum_members:
        from launcher.workers.generate.section_validator import (
            _strip_hallucinated_enum_member_access,
        )
        blocks = _strip_hallucinated_enum_member_access(blocks, class_enum_members)
    if method_corrections:
        from launcher.workers.generate.section_validator import (
            _correct_method_names_in_code,
        )
        blocks = _correct_method_names_in_code(blocks, method_corrections)
```

### Step 4: Add unit tests

Add to `tests/unit/workers/generate/test_section_validator.py`:

```python
# HG-21: Enum member access tests

class TestHG21EnumMemberAccess:
    """HG-21: _strip_hallucinated_enum_member_access."""

    def _make_code_block(self, code: str, lang: str = "python") -> "BlockIR":
        return BlockIR(type=BlockType.code, content=code, language=lang, claim_ids=[])

    def test_invalid_enum_member_removed(self):
        from launcher.workers.generate.section_validator import _strip_hallucinated_enum_member_access
        class_enum_members = {"FileFormat": {"WAVEFRONT_OBJ", "GLTF2", "FBX7400ASCII"}}
        code = "scene.save('out.obj', FileFormat.OBJ)"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_enum_member_access(blocks, class_enum_members)
        assert len(result) == 0, "FileFormat.OBJ (invalid) must remove block"

    def test_valid_enum_member_preserved(self):
        from launcher.workers.generate.section_validator import _strip_hallucinated_enum_member_access
        class_enum_members = {"FileFormat": {"WAVEFRONT_OBJ", "GLTF2", "FBX7400ASCII"}}
        code = "scene.save('out.obj', FileFormat.WAVEFRONT_OBJ)"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_enum_member_access(blocks, class_enum_members)
        assert len(result) == 1, "FileFormat.WAVEFRONT_OBJ (valid) must preserve block"

    def test_unknown_class_enum_access_not_checked(self):
        from launcher.workers.generate.section_validator import _strip_hallucinated_enum_member_access
        class_enum_members = {"FileFormat": {"WAVEFRONT_OBJ"}}
        # os.DEVNULL — 'os' is not in class_enum_members
        code = "import os\ndevnull = os.DEVNULL"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_enum_member_access(blocks, class_enum_members)
        assert len(result) == 1, "Unknown class enum access must not be checked"

    def test_empty_class_enum_members_skips_repair(self):
        from launcher.workers.generate.section_validator import _strip_hallucinated_enum_member_access
        code = "scene.save('out.obj', FileFormat.OBJ)"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_enum_member_access(blocks, {})
        assert len(result) == 1, "Empty class_enum_members must skip repair"


class TestHG21MethodCorrection:
    """HG-21: _correct_method_names_in_code."""

    def _make_code_block(self, code: str, lang: str = "python") -> "BlockIR":
        return BlockIR(type=BlockType.code, content=code, language=lang, claim_ids=[])

    def test_wrong_method_corrected(self):
        from launcher.workers.generate.section_validator import _correct_method_names_in_code
        corrections = {"create_child_node": "add_child_node"}
        code = "node = root.create_child_node('child')"
        blocks = [self._make_code_block(code)]
        result = _correct_method_names_in_code(blocks, corrections)
        assert len(result) == 1
        assert "add_child_node" in result[0].content
        assert "create_child_node" not in result[0].content

    def test_no_correction_needed_unchanged(self):
        from launcher.workers.generate.section_validator import _correct_method_names_in_code
        corrections = {"create_child_node": "add_child_node"}
        code = "node = root.add_child_node('child')"
        blocks = [self._make_code_block(code)]
        result = _correct_method_names_in_code(blocks, corrections)
        assert len(result) == 1
        assert result[0].content == code

    def test_empty_corrections_unchanged(self):
        from launcher.workers.generate.section_validator import _correct_method_names_in_code
        code = "node = root.create_child_node('child')"
        blocks = [self._make_code_block(code)]
        result = _correct_method_names_in_code(blocks, {})
        assert len(result) == 1
        assert result[0].content == code
```

## Failure modes

### Failure mode 1: Valid ALL-CAPS identifier on non-enum class is wrongly removed

**Detection**: A test shows a code block removed because `SomeClass.SOME_CONSTANT` flagged.
**Assessment**: Only applies when `SomeClass` is in `class_enum_members` (built from classes with
ALL-CAPS typed_methods). If the class has no ALL-CAPS typed_methods, it's not in the dict.
**Gate**: `test_unknown_class_enum_access_not_checked` verifies unknown classes are skipped.

### Failure mode 2: Method correction causes semantic breakage

**Detection**: `set_rotation(val)` corrected to `rotation(val)` — wrong syntax.
**Assessment**: The suffix matching requires suffix length ≥ 8 chars. `set_rotation` suffix is
`rotation` (8 chars). `rotation` IS a typed_method but would have 3+ matches (pre_rotation,
post_rotation, rotation). Since `matches` requires len==1, ambiguous suffixes are skipped.
**Gate**: Implementation requires `len(matches) == 1` — multiple matches prevent correction.

### Failure mode 3: Method correction modifies correct code

**Detection**: Code using `add_child_node` has it replaced.
**Assessment**: `add_child_node` IS in typed_methods_set so it's never added to `method_corrections`
(only identifiers NOT in typed_methods_set are candidates). Cannot happen.
**Gate**: `test_no_correction_needed_unchanged` verifies code with correct names is unchanged.

## Task-specific review checklist

1. [ ] `_ENUM_ACCESS_RE` matches `FileFormat.OBJ` and `FileFormat.STLASCII`
2. [ ] `_ENUM_ACCESS_RE` does NOT match `FileFormat.WAVEFRONT_OBJ` as invalid (it's in the dict)
3. [ ] Comment stripping applied before enum member scanning (reuse HG-17 logic)
4. [ ] `_correct_method_names_in_code` replaces `create_child_node` → `add_child_node` via corrections dict
5. [ ] Suffix matching requires ≥8 char suffix AND exactly 1 match in typed_methods_set
6. [ ] 7 new unit tests pass (4 enum + 3 method)
7. [ ] All existing 12 HG-16 tests still pass
8. [ ] Docstrings updated for all new functions
9. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
10. [ ] Schema `"description"` fields present for all new/changed properties
11. [ ] Checked `docs/README.md` ownership map — trigger events apply? No
12. [ ] No new `docs/guides/` files added

## Deliverables

1. 2 new functions in `src/launcher/workers/generate/section_validator.py`
2. Updated `src/launcher/workers/generate/worker.py` — lookup table building + repair calls
3. 7 new tests in `tests/unit/workers/generate/test_section_validator.py`

## Acceptance checks

- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_validator.py -v` — 22/22 pass
- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q` — no new failures (3590 passed)
- [x] `FileFormat.OBJ` code block removed in test; `FileFormat.WAVEFRONT_OBJ` preserved
- [x] `create_child_node(` → `add_child_node(` in code blocks via corrections dict

## Self-review

### Verification results
- [x] `_strip_hallucinated_enum_member_access` implemented with comment stripping
- [x] `_correct_method_names_in_code` implemented with word-boundary regex replacement
- [x] worker.py builds both lookup tables from class_briefs + api_identifiers
- [x] 22/22 section_validator tests pass; 3590 passed overall, 6 pre-existing failures only

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_validator.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `section_validator.py` — 2 new repair functions + `_ENUM_ACCESS_RE`
- `worker.py` — lookup table building + 2 new repair calls after HG-16 block
- `test_section_validator.py` — 7 new tests (4 enum + 3 method correction)
- Full suite: 3590 passed (7 new), 6 pre-existing failures only

## Integration boundary proven

**Upstream**: `_generate_page()` receives `class_briefs` from UnderstandingBundle
**Fix**: Enum member access validated against class_briefs.typed_methods; method names corrected
**Downstream**: Code blocks with invalid enum members removed; wrong method names replaced before SectionIR assembly
