---
id: TC-4063
title: "Snippet source provenance + deduplication"
status: In-Progress
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [understand, snippets, models, schema]
depends_on: [TC-4062]
allowed_paths:
  - plans/taskcards/TC-4063_snippet-provenance-and-dedup.md
  - src/launcher/models/claims.py
  - src/launcher/workers/understand/extract/_snippets.py
  - specs/schemas/understanding_bundle.schema.json
  - tests/unit/workers/understand/test_extract.py
  - tests/unit/models/test_claims.py
evidence_required:
  - reports/TC-4063/evidence.md
---

# Taskcard TC-4063 — Snippet source provenance + deduplication

## Objective

Add source file/line tracking to `Snippet` (parity with `EvidenceAnchor` on `Claim`),
and deduplicate snippets by content hash within `_extract_snippets()` to prevent the
same code block appearing multiple times (README + docs/ + examples/).

## Required spec references

- `specs/claims_evidence.md` (Snippet model structure, EvidenceAnchor parity)
- `specs/worker_understand.md` (Phase B.3: snippet extraction)

## Scope

### In scope
- Add `source_file: str = ""`, `line_start: int | None = None`, `line_end: int | None = None` to `Snippet`
- Populate `source_file` from `rel_path` at all `Snippet(...)` construction sites in `_snippets.py`
- Add content-hash deduplication in `_extract_snippets()` using `sha256(code)[:16]`
- Update `understanding_bundle.schema.json` to add optional provenance fields to snippet items

### Out of scope
- Stable snippet IDs exposed externally (not needed for dedup; internal hash only)
- Planner changes (separate concern, lower priority)
- `line_start`/`line_end` for fenced blocks — approximate only; only exact for whole-file examples

## Inputs

- `src/launcher/models/claims.py` (current `Snippet` model)
- `src/launcher/workers/understand/extract/_snippets.py` (extraction logic)
- `specs/schemas/understanding_bundle.schema.json` (snippet schema items)

## Outputs

- `Snippet` model with 3 new optional fields
- `_extract_snippets()` that populates `source_file` and deduplicates
- Updated schema with optional provenance fields

## Allowed paths

- plans/taskcards/TC-4063_snippet-provenance-and-dedup.md
- src/launcher/models/claims.py
- src/launcher/workers/understand/extract/_snippets.py
- specs/schemas/understanding_bundle.schema.json
- tests/unit/workers/understand/test_extract.py
- tests/unit/models/test_claims.py

### Allowed paths rationale
Model change (claims.py), extraction logic (_snippets.py), schema (understanding_bundle),
and their corresponding tests.

## Implementation steps

### Step 1: Extend `Snippet` model in `claims.py`

Add three optional fields after `source_type`:
```python
source_file: str = ""
line_start: int | None = None
line_end: int | None = None
```

All have defaults so existing `Snippet(code=..., language=...)` calls remain valid.

### Step 2: Add deduplication + source tracking to `_extract_snippets()` in `_snippets.py`

At the top of `_extract_snippets()`:
```python
import hashlib
seen_hashes: set[str] = set()
```

Helper inline function:
```python
def _dedup_key(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()[:16]
```

Before each `snippets.append(Snippet(...))`:
```python
h = _dedup_key(code.strip())
if h in seen_hashes:
    continue
seen_hashes.add(h)
```

For fenced block snippets: pass `source_file=rel_path`.
For whole-file source examples: pass `source_file=rel_path`.
`line_start`/`line_end` are left as `None` for fenced blocks (position in file is
not tracked during extraction). For whole-file examples they default to `None` too
(whole file means 1..N which is obvious from the file itself).

### Step 3: Update `understanding_bundle.schema.json`

In the `snippets` array item definition, add optional properties:
```json
"source_file": {
  "type": "string",
  "default": "",
  "description": "TC-4063: Relative repo path where this snippet was found."
},
"line_start": {
  "type": ["integer", "null"],
  "default": null,
  "description": "TC-4063: Approximate start line (best-effort, null for fenced blocks)."
},
"line_end": {
  "type": ["integer", "null"],
  "default": null,
  "description": "TC-4063: Approximate end line (best-effort, null for fenced blocks)."
}
```

## Failure modes

### Failure mode 1: Existing tests construct `Snippet` without new fields

**Detection**: Tests pass because all fields have defaults — no action needed
**Resolution**: N/A — backward compatible
**Gate**: Unit tests

### Failure mode 2: Schema validation rejects old bundles missing provenance fields

**Detection**: `_validate_bundle()` raises for bundles that lack `source_file`
**Resolution**: Ensure all new schema fields are `"required": false` or simply absent
from the `required` array in the schema
**Gate**: Schema validation in `io/schema_validation.py`

### Failure mode 3: Dedup hash too aggressive — removes legitimately distinct snippets

**Detection**: `_extract_snippets` returns fewer snippets than expected in tests
**Resolution**: Hash is on `code.strip()` content only — two identical code blocks
in different files are genuinely redundant. Distinct code → distinct hash → kept.
**Gate**: Unit tests for extraction count

## Task-specific review checklist

1. [ ] `Snippet(code="x")` still constructs without error (backward compat)
2. [ ] `Snippet(code="x", source_file="README.md")` works
3. [ ] Two identical snippets from different files result in exactly one in output
4. [ ] Two distinct snippets from same file are both kept
5. [ ] `source_file` is populated in extracted snippets (not empty string)
6. [ ] Schema properties `source_file`, `line_start`, `line_end` are NOT in `required` array
7. Docstrings updated for all new/changed public functions
8. Spec file updated if worker behavior changed (or confirmed no spec drift)
9. Schema `"description"` fields present for all new/changed properties
10. Checked `docs/README.md` ownership map — no guide trigger from this change
11. N/A — no new docs/guides/ file added

## Deliverables

1. `src/launcher/models/claims.py` with 3 new fields on `Snippet`
2. `src/launcher/workers/understand/extract/_snippets.py` with dedup + source_file wiring
3. `specs/schemas/understanding_bundle.schema.json` with provenance fields added

## Acceptance checks

1. [ ] `Snippet.model_fields` contains `source_file`, `line_start`, `line_end`
2. [ ] `_extract_snippets()` with a README and identical snippet in docs/ → 1 snippet, not 2
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q` passes

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-4063/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -k "snippet"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q --tb=short
```

**Expected results**:
- Snippet extraction tests pass with source_file populated
- Dedup test (if added) verifies no duplicate code blocks
- Full unit suite passes

## Integration boundary proven

**Upstream**: `_extract_snippets()` takes `repo_dir`, `repo_info`, `product`, `api_surface`, `claims`
**Downstream**: `UnderstandingBundle.snippets` — each snippet now has `source_file` set
**Contract**: `Snippet` model; `understanding_bundle.schema.json` — new fields optional, backward compatible
