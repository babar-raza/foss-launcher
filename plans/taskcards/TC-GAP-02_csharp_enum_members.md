---
id: TC-GAP-02
title: "Fix C# enum member extraction in ts_analyzer"
status: Done
priority: High
owner: "agent-B"
updated: "2026-03-12"
tags: [ts_analyzer, dotnet, enum, adapter, understand]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-GAP-02_csharp_enum_members.md
  - src/launcher/shared/ts_analyzer.py
  - tests/unit/workers/understand/test_dotnet_adapter.py
evidence_required:
  - reports/agents/TC-GAP-02/evidence.md
---

# Taskcard TC-GAP-02 — Fix C# enum member extraction in ts_analyzer

## Objective

C# tree-sitter grammar uses `enum_member_declaration_list` as the enum body node
type, but ts_analyzer only handles `enum_body` (TypeScript). This leaves C# enum
members always empty despite `is_enum=True` being correctly set. Closing this gap
provides complete C# API surface data for generate/evaluate consumers.

## Required spec references

- `specs/worker_understand.md` (Section: Output Field Reference — api_surface.class_briefs[].enums)

## Root cause

In `src/launcher/shared/ts_analyzer.py` (line ~983):
```python
if is_enum and body.type == "enum_body":
    # only TypeScript enum body handled
```

C# enum body node: `enum_member_declaration_list`
C# enum member node: `enum_member_declaration` (child: `identifier`, optionally `equals_value_clause`)

## Scope

### In scope
- Add `elif body.type == "enum_member_declaration_list"` branch in ts_analyzer.py
- Extract `identifier` child as member name, `equals_value_clause` as value
- Update `test_dotnet_adapter.py` to assert C# enum members are now populated

### Out of scope
- Fixing Java enum extraction (Java uses `enum_body` like TypeScript — already works)
- Changing TypeScript enum extraction logic

## Inputs

- `src/launcher/shared/ts_analyzer.py` — enum extraction at line ~983
- `tests/unit/workers/understand/test_dotnet_adapter.py` — existing C# enum test

## Outputs

- Updated `ts_analyzer.py` with C# enum member branch
- Updated C# enum test asserting members populated

## Allowed paths

- plans/taskcards/TC-GAP-02_csharp_enum_members.md
- src/launcher/shared/ts_analyzer.py
- tests/unit/workers/understand/test_dotnet_adapter.py

### Allowed paths rationale

`ts_analyzer.py` is in `src/launcher/shared/` (protected). Test file updated to
match new behavior.

## Implementation steps

### Step 1: Read ts_analyzer.py enum extraction block

Read lines 975-1020 to confirm exact indentation and surrounding context.
Find the `if is_enum and body.type == "enum_body":` block.

### Step 2: Add C# enum branch

After the closing of the `if is_enum and body.type == "enum_body":` block,
add:

```python
elif is_enum and body.type == "enum_member_declaration_list":
    # TC-GAP-02: C# enum member extraction.
    # C# grammar uses enum_member_declaration_list as body; each member
    # is an enum_member_declaration with an identifier child.
    for member in body.children:
        if member.type != "enum_member_declaration":
            continue
        ename = ""
        evalue = ""
        for sub in member.children:
            if sub.type == "identifier":
                ename = sub.text.decode()
            elif sub.type == "equals_value_clause":
                raw = sub.text.decode().strip()
                if raw.startswith("="):
                    evalue = raw[1:].strip()
        if ename and not any(em["name"] == ename for em in enum_members):
            enum_members.append({"name": ename, "value": evalue})
```

### Step 3: Update C# enum test

In `tests/unit/workers/understand/test_dotnet_adapter.py`, find
`test_enum_class_extracted`. Update the assertion from:
```python
assert isinstance(enum_class.get("enum_members", []), list), "enum_members must be a list"
```
To verify actual members are present. The test fixture C# enum should have
known members — add assertions like:
```python
member_names = [m["name"] for m in enum_class.get("enum_members", [])]
assert len(member_names) > 0, "C# enum_members must be populated after TC-GAP-02"
```

Check what enum members are in the test fixture and assert them by name.

## Failure modes

### Failure mode 1: C# tree-sitter grammar not loaded

**Detection**: `analyze_file()` returns empty classes for .cs files
**Resolution**: Check `_LANG_PACK_ALIASES["csharp"]` → `_c_sharp_separate` sentinel
is handled in `_get_language()`. Verify `tree_sitter_c_sharp` is installed.
**Gate**: test_dotnet_adapter tests

### Failure mode 2: C# enum body node name differs from expectation

**Detection**: members still empty; add debug print of `body.type` in test
**Resolution**: Parse a .cs file with tree-sitter directly to inspect node tree:
```python
lang = Language(tree_sitter_c_sharp.language())
parser = Parser(lang)
tree = parser.parse(b"enum Foo { A = 1, B = 2 }")
# Walk tree to find actual node types
```
**Gate**: test_dotnet_adapter tests

### Failure mode 3: equals_value_clause format differs

**Detection**: `evalue` is empty even for members with explicit values
**Resolution**: The value inside `equals_value_clause` is a sub-expression node;
`sub.text.decode()` includes the full `= 1` text. The `lstrip("=").strip()` pattern
handles this correctly. If sub-expression is nested (e.g. `integer_literal`),
the full text approach still works.
**Gate**: test_dotnet_adapter enum value assertions

## Task-specific review checklist

1. [x] `elif body.type == "enum_member_declaration_list"` branch added after TypeScript `if` block
2. [x] Member node type guard: `if member.type != "enum_member_declaration": continue`
3. [x] Duplicate guard: `if not any(em["name"] == ename for em in enum_members)` preserved
4. [x] Test `test_enum_class_extracted` asserts `len(enum_members) > 0`
5. [x] Test asserts at least one known member name from the fixture (Xlsx, Csv, Pdf all asserted)
6. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_dotnet_adapter.py -v` — 5/5 pass
7. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q` — 3816 passed, 0 failures
8. [x] TC-GAP-02 comment added in ts_analyzer elif branch
9. [x] `specs/worker_understand.md` confirmed — no new field, existing `enums` field now populated for C#
10. [x] Schema: no changes (enum_members already in ClassBrief schema)
11. [x] docs/README.md: no ownership trigger

## Deliverables

1. Updated `src/launcher/shared/ts_analyzer.py` with C# enum branch
2. Updated C# enum test asserting members populated
3. Evidence at `reports/agents/TC-GAP-02/evidence.md`

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_dotnet_adapter.py -v` — `test_enum_class_extracted` PASS with member assertions
2. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q` — 3816 passed, 0 failures
3. [x] Grep confirms the new `elif` branch is in ts_analyzer.py (lines 927, 1012, 1014)

## Self-review

### Verification results
- [x] Tests: 3816/3816 PASS (0 failures, 0 regressions)
- [x] Evidence captured: reports/agents/TC-GAP-02/evidence.md
- [x] Self-review captured: reports/agents/TC-GAP-02/self_review.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_dotnet_adapter.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q
```

## Integration boundary proven

**Upstream**: `_dotnet.py` adapter calls `ts_analyzer.analyze_file(path, language="csharp")`
**Downstream**: `ClassBrief.enums[].enum_members` consumed by evaluate/generate workers
**Contract**: `enum_members: list[dict[str, str]]` — each entry has `name` + `value` keys
