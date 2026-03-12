---
id: SNP-05
title: "Promote _dedup_key to module level + fix encoding safety in _snippets.py"
status: Done
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [understand, snippets, code-quality, TC-4063]
depends_on: [TC-4063]
allowed_paths:
  - plans/healing/SNP-05-dedup-key-promotion.md
  - src/launcher/workers/understand/extract/_snippets.py
evidence_required:
  - reports/SNP-05/evidence.md
---

# SNP-05 — Promote `_dedup_key` to module level + fix encoding safety

## Objective

TC-4063 added `_dedup_key()` as a nested function inside `_extract_snippets()`. Nested
helper functions:
1. Cannot be unit-tested in isolation
2. Are redefined on every call to the outer function (minor but unnecessary overhead)
3. May shadow module-level names unexpectedly

Additionally, `code.encode()` without an encoding argument defaults to UTF-8 but raises
`UnicodeEncodeError` on non-UTF-8 content (e.g. snippets with Windows-1252 bytes from
vendored files). This is latent breakage that surfaces only on repos with non-ASCII source.

## Required spec references

- `specs/worker_understand.md` (Phase B.3: snippet extraction correctness)

## Scope

### In scope
- Move `_dedup_key(code: str) -> str` from inside `_extract_snippets()` to module level
  in `_snippets.py`, immediately after the `import hashlib` line (or near the top of the
  private helpers section)
- Fix the encoding: change `code.encode()` to `code.encode("utf-8", errors="replace")`
- Add a one-line docstring to `_dedup_key` (it is now a module-level private function)
- Re-export `_dedup_key` from `extract/__init__.py` only if tests need it — prefer NOT
  re-exporting private helpers unless required

### Out of scope
- Changing the hash algorithm or prefix length (sha256[:16] stays)
- Adding `_dedup_key` to the public API surface
- Test changes (SNP-01 tests exercise dedup behavior end-to-end, which is sufficient)

## Inputs

- `src/launcher/workers/understand/extract/_snippets.py` (current state with nested function)

## Outputs

- `_snippets.py` with `_dedup_key` at module level, `errors="replace"` encoding fix

## Allowed paths

- plans/healing/SNP-05-dedup-key-promotion.md
- src/launcher/workers/understand/extract/_snippets.py

### Allowed paths rationale
Only `_snippets.py` needs the refactor. `__init__.py` is not changed unless tests explicitly
require the helper to be importable.

## Implementation steps

### Step 1: Locate `_dedup_key` inside `_extract_snippets()`

Find the nested definition:
```python
def _dedup_key(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()[:16]
```

### Step 2: Move to module level

Remove the nested definition from inside `_extract_snippets()`.
Add at module level (after imports, before the first class or function definition):
```python
def _dedup_key(code: str) -> str:
    """Return a 16-char hex content hash used to deduplicate identical snippets."""
    return hashlib.sha256(code.encode("utf-8", errors="replace")).hexdigest()[:16]
```

### Step 3: Verify `_extract_snippets()` still calls it correctly

The call site inside `_extract_snippets()` uses `_dedup_key(code.strip())` — this call
is unchanged; the function is now resolved at module scope instead of local scope.

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q --tb=short
```

## Failure modes

### Failure mode 1: Name conflict with existing module-level `_dedup_key`

**Detection**: `SyntaxError` or silent shadowing if another `_dedup_key` exists at module level
**Resolution**: `grep "_dedup_key" src/launcher/workers/understand/extract/_snippets.py`
before moving — there should be exactly 0 module-level occurrences currently
**Gate**: Grep check before edit

### Failure mode 2: `errors="replace"` changes hash for ASCII-only content

**Detection**: Dedup tests produce unexpected hash values after change
**Resolution**: `errors="replace"` only affects non-UTF-8 bytes; pure ASCII and valid UTF-8
strings produce identical output to `.encode()` with default args. Hash is on
`code.strip()` content, unchanged.
**Gate**: Unit tests (SNP-01 dedup tests still pass)

### Failure mode 3: `hashlib` not imported at module level

**Detection**: `NameError: name 'hashlib' is not defined` at module-level function definition
**Resolution**: Confirm `import hashlib` is at the top of `_snippets.py` (it was added
in TC-4063). If not, add it.
**Gate**: Module import check

## Task-specific review checklist

1. [ ] `_dedup_key` defined at module level (not nested inside `_extract_snippets`)
2. [ ] `code.encode("utf-8", errors="replace")` used (not bare `.encode()`)
3. [ ] One-line docstring present on `_dedup_key`
4. [ ] `_dedup_key` NOT added to `extract/__init__.py` re-exports (private helper)
5. [ ] All dedup call sites inside `_extract_snippets()` still use `_dedup_key(code.strip())`
6. [ ] No change to hash algorithm or prefix length
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — no guide trigger from internal refactor
11. [ ] N/A — no new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/understand/extract/_snippets.py` with module-level `_dedup_key`
2. `reports/SNP-05/evidence.md` with grep showing module-level placement

## Acceptance checks

1. [ ] `grep -n "_dedup_key" src/launcher/workers/understand/extract/_snippets.py` shows definition at module level (low line number, before `_extract_snippets`)
2. [ ] `grep "errors=\"replace\"" src/launcher/workers/understand/extract/_snippets.py` → matches
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q` passes

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/SNP-05/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -q
```

**Expected results**:
- All dedup tests pass with module-level `_dedup_key`
- Full unit suite passes

## Integration boundary proven

**Upstream**: `_extract_snippets()` calls `_dedup_key(code.strip())`
**Downstream**: SHA-256 prefix used to filter duplicates in `seen_hashes` set
**Contract**: `_dedup_key(code: str) -> str` — 16-char hex; deterministic; collision probability negligible for typical snippet counts (<100 per repo)
