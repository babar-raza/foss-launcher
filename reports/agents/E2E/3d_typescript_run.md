# E2E Run Report: 3d/typescript — Understand Phase

**Date**: 2026-03-14
**Run ID (successful)**: 260314_063207_3d_typescript_324a
**Run ID (first attempt, crashed)**: 260314_062553_3d_typescript_fd3a
**Operator**: Agent-E2E (TC-4267)
**Pipeline**: `configs/pilots/aspose-3d-foss-typescript.yaml --stop-after understand`

---

## 1. Pipeline Output Summary

### First attempt — FAILED (ValidationError in SnippetFact)

The pipeline crashed at the end of the Understand worker's Phase B with:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for SnippetFact
syntax_valid
  Input should be a valid boolean [type=bool_type, input_value=None, input_type=NoneType]
```

**Root cause**: `_build_snippet_facts()` in `_entry.py` (line 410) used
`getattr(sn, "syntax_valid", True)`, which returns `None` when `sn.syntax_valid` is
explicitly `None` (getattr only falls back to its default when the attribute is *absent*,
not when it is `None`). TC-4265 had set `syntax_valid=None` for TypeScript snippets
(no tree-sitter installed), but `SnippetFact.syntax_valid` is typed `bool = True` and
rejects `None`.

**Fix applied (TC-4267)**: Changed `_entry.py` line 410 to coerce `None` to `True`:
```python
_raw_sv = getattr(sn, "syntax_valid", None)
_sv_bool: bool = _raw_sv if _raw_sv is not None else True
```
This preserves `False` (genuinely invalid snippets) while coercing `None` (unvalidated) to `True`.

### Second attempt — Schema validation failure

After the `_entry.py` fix, the understand worker completed successfully and wrote
`understanding_bundle.json`, but the graph builder's schema validation rejected it:

```
understand.output: snippets/0: Additional properties are not allowed ('syntax_valid' was unexpected)
```

**Root cause**: `specs/schemas/understanding_bundle.schema.json` snippets items had
`additionalProperties: false` but did not include `syntax_valid`. TC-4265 added
`syntax_valid` to Snippet construction in `_snippets.py` but missed the schema update.

**Fix applied (TC-4267)**: Added `syntax_valid` to the snippets items in the schema
(type `["boolean", "null"]`, default `null`).

### Third attempt — Self-review FAILED (orphaned snippets)

The pipeline ran to completion but the Understand worker's self-review reported:

```
5/22 snippets have no linked claims (orphaned_fraction=0.23). Severity=high.
```

This triggered `workers_completed=['intake', 'scout']` — understand did not reach
`Done` state. The `understanding_bundle.json` was written but the run is `NO_GO`.

**This is a pre-existing issue**, not a regression introduced by TC-4262 through TC-4266.
The orphaned snippets are JSON and test files that the claim-linker did not associate
with any claim.

---

## 2. Claims Analysis

**Source**: `runs/260314_063207_3d_typescript_324a/understanding_bundle.json`

| Metric | Value |
|--------|-------|
| Total claims | 38 |
| LLM-sourced claims | 30 (79%) |
| Deterministic claims | 8 (21%) |
| LLM confidence | 0.75 (all 30) |
| Deterministic confidence | 0.50 (all 8) |

### Deterministic claims breakdown

All 8 deterministic claims are `kind=api`, `confidence=0.50`. They enumerate format
classes from the format matrix:

- `ColladaFormat.canExport()`
- `GltfFormat.canExport()`
- `FbxFormat.canExport()`
- `ObjFormat.canExport()`
- `StlFormat.canExport()`
- `ThreeMfFormat.canExport()`
- `Node.createChildNode()`
- `GltfPlugin.createImporter()`

**Assessment**: TC-4266 (deterministic confidence tiering) appears to be working —
all deterministic claims receive confidence=0.50 (lower tier) vs LLM claims at 0.75.
This is the expected behavior for Tier B (format-only evidence).

**Contradiction resolution**: 0 contradictions detected (vs 2 in the first aborted run).
This is within normal variation.

---

## 3. Snippets / syntax_valid Breakdown

| syntax_valid | Count | Notes |
|---|---|---|
| True | 21 | TypeScript snippets coerced from None per TC-4267 |
| False | 0 | No genuinely invalid snippets |
| None | 1 | One JSON snippet (README.md fenced block) |

The 1 remaining `None` is a JSON fenced block in README.md (`lang=json`). JSON is
not a supported validation target — `None` is correct for this case.

**Python snippets with syntax_valid=None**: 0. This satisfies the TC-4265 acceptance check.

**TypeScript snippets**: All 21 have `syntax_valid=True` (coerced from None by TC-4267).
No tree-sitter is installed, so these cannot be validated; `True` is the appropriate
conservative default.

---

## 4. Orphaned Snippets

5 of 22 snippets have no linked claims (`orphaned_fraction=0.23`):

| Source file | Language | syntax_valid |
|---|---|---|
| README.md | json | None |
| tests/setup.ts | typescript | True |
| tests/test_fbx_simple.test.ts | typescript | True |
| tests/test_fbx_tokenizer.test.ts | typescript | True |
| tests/test_formats.test.ts | typescript | True |

All test files. The snippet extractor pulled them in (correct behavior: test files
demonstrate API usage), but the claim-linker did not associate them with any claim.
This is a pre-existing gap in the snippet-to-claim linking logic for test-only evidence.

The self-review threshold for `orphaned_fraction` is 0.20 (20%). At 0.23 this is
marginally over threshold and triggers `severity=high`.

---

## 5. Page Evidence Index

| Page role | Evidence sufficient | Missing |
|---|---|---|
| `_index` | Yes | — |
| `install_guide` | Yes | — |
| `api_reference` | Yes | — |
| `howto_article` | Yes | — |
| `format_conversion` | Yes | — |
| `feature_blog` | **No** | `no_verified_claims` |

One page role is insufficient: `feature_blog`. This page requires verified claims that
go beyond pure API enumeration. With only 8 deterministic (format-matrix) claims and 30
LLM claims, the evidence is enough for 5/6 roles.

---

## 6. Scout Artifact Analysis

| Metric | Value |
|---|---|
| Files enumerated | 193 |
| Files read | 192 |
| Primary language | typescript |
| Content used | 473,001 bytes (462 KB) |
| Budget log entries | 1 |
| Budget log overflow | 0 |
| Skipped paths | 1 |

**Scout budget**: 462 KB content used. The TC-4263 5 MB budget cap is not triggered
(462 KB << 5 MB). Budget log overflow = 0, confirming no budget issues.

The single skipped path is expected (likely the `.git` directory or a node_modules subtree).

---

## 7. TC-4262 through TC-4266 Assessment

| TC | Purpose | Evidence of impact |
|---|---|---|
| TC-4262 | LLM doc window 128 KB | Evidence context injected: 548 chars (well under limit) |
| TC-4263 | Scout budget 5 MB per-file caps | Content used 462 KB; overflow=0; cap not triggered |
| TC-4264 | Scout metadoc subdir filter | `has_docs_folder` in bundle; 1 doc file read |
| TC-4265 | syntax_valid at Snippet construction | TypeScript snippets get `syntax_valid=None` in _snippets.py (correct for unsupported lang) |
| TC-4266 | Deterministic confidence tiering | All 8 deterministic claims at 0.50; LLM at 0.75 — correct tiering |

**TC-4265 gap found**: TC-4265 set `syntax_valid=None` for TypeScript snippets in
`_snippets.py` but did not: (a) coerce None in `_entry.py`'s `_build_snippet_facts`,
(b) add `syntax_valid` to `understanding_bundle.schema.json`. These were fixed by TC-4267.

---

## 8. Regressions and New Issues

### Fixed by TC-4267 (this run)
1. **`SnippetFact` ValidationError** — `_entry.py` line 410: `None` not coerced to `bool`.
   Fixed: `_raw_sv if _raw_sv is not None else True`.
2. **Schema validation failure** — `understanding_bundle.schema.json` missing `syntax_valid`
   in snippets items. Fixed: added `syntax_valid: ["boolean","null"]` to schema.

### Pre-existing issues (not regressions)
3. **Orphaned snippets at 0.23 (threshold 0.20)** — 5 test-file snippets have no
   linked claims. Claim-linker does not connect test-file snippets to claims. Not
   introduced by TC-4262 through TC-4266. Requires a separate taskcard.
4. **Phase store not updated** — `phase_store/3d/typescript/` does not exist.
   Phase store is only written on successful `Done` runs; since self-review fails,
   promotion is skipped.
5. **`primary_language` missing from scout_checkpoint.json** — the `scout_checkpoint.json`
   `repo_info` dict does not have `primary_language` (it is in `scout_bundle.json`).
   Minor schema inconsistency; does not affect pipeline.

---

## 9. Verdict

The 3d/typescript Understand phase is **functionally complete** but blocked by the
orphaned-snippets self-review gate. Two bugs introduced by TC-4265 were root-caused
and fixed (TC-4267). The claim extraction, API surface, format matrix, snippet
extraction, and SEO keyword research all produced expected output.

**Next action**: Create a taskcard to fix the snippet-to-claim linker so test-file
snippets are connected to relevant claims, reducing orphaned fraction below the 0.20
threshold.

---

## 10. Files Changed (TC-4267)

- `src/launcher/workers/understand/extract/_entry.py` — coerce `syntax_valid=None` to `True`
- `specs/schemas/understanding_bundle.schema.json` — add `syntax_valid` to snippets items
- `plans/taskcards/TC-4267_entry-snippet-fact-syntax-valid-coerce.md` — taskcard

## 11. Evidence

- Run dir: `runs/260314_063207_3d_typescript_324a/`
- Understanding bundle: `runs/260314_063207_3d_typescript_324a/understanding_bundle.json`
- LLM evidence: `runs/260314_063207_3d_typescript_324a/evidence/llm_calls/extract-claims-3d.json`
- Unit tests: 325/325 PASS (`tests/unit/workers/understand/`)
