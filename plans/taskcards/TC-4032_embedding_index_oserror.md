---
id: TC-4032
title: "_build_embedding_index OSError not handled"
status: In-Progress
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [understand, resilience, error-handling]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4032_embedding_index_oserror.md
  - src/launcher/workers/understand/extract/_snippets.py
evidence_required:
  - reports/TC-4032/evidence.md
---

# Taskcard TC-4032 — _build_embedding_index OSError not handled

## Objective

Wrap the disk-write blocks in `_build_embedding_index()` with `except (OSError, IOError)` so that a full disk, read-only mount, or permission error does not crash the entire Understand worker for a non-critical side artifact.

## Required spec references

- `specs/worker_understand.md` (extraction phase outputs — embedding_index.json is a side artifact)

## Scope

### In scope
- Wrap two disk-write blocks (~lines 537-549, ~551-561) in `_snippets.py` with specific `OSError`/`IOError` handler
- Add `logger.warning` on failure, `logger.info` on success (else-branch)

### Out of scope
- Modifying `embed_texts()` or TF-IDF fallback (already robust)
- Adding retry logic or circuit-breaker around embedding calls
- Modifying the call site in `_entry.py` (function handles its own disk failures)

## Inputs

- `src/launcher/workers/understand/extract/_snippets.py` — contains `_build_embedding_index()` with unguarded disk writes

## Outputs

- Same file with targeted `except (OSError, IOError)` on both write paths
- No change to function signature or caller contract

## Allowed paths

- plans/taskcards/TC-4032_embedding_index_oserror.md
- src/launcher/workers/understand/extract/_snippets.py

### Allowed paths rationale
Single-file fix. Only `_snippets.py` requires modification.

## Implementation steps

### Step 1: Read _snippets.py to locate exact write blocks

Locate `_build_embedding_index()` and identify the two write paths (primary store path and run_dir fallback path).

### Step 2: Wrap primary path write in except (OSError, IOError)

```python
try:
    embedding_index.save(out)
except (OSError, IOError) as exc:
    logger.warning(
        "Phase B.6: could not write embedding_index.json (disk error) — "
        "pipeline continues without embedding artifact: %s", exc,
    )
else:
    logger.info(
        "Phase B.6: embedding index saved (%d vectors) -> %s",
        len(embedding_index), out,
    )
return  # unconditional — fallback only when store is absent
```

### Step 3: Wrap fallback path (run_dir) in except (OSError, IOError)

Apply same pattern to the mkdir + save block on the fallback path.

### Step 4: Run unit tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ tests/integration/test_extract_embeddings.py -x -q
```

## Failure modes

### Failure mode 1: except clause too broad — swallows programming errors

**Detection**: A `ValueError` or `AttributeError` from `save()` is silently swallowed.
**Resolution**: Catch only `(OSError, IOError)`. Do NOT use `except Exception`.
**Gate**: Root-cause fix policy AG-016.

### Failure mode 2: return placement removes fallback path

**Detection**: Even when `context.store` is None, the function returns after the (now-guarded) primary-path block.
**Resolution**: Ensure `return` only executes inside the `if store is not None` / `if artifacts_dir is not None` branch, preserving the fallback path for when store is absent.
**Gate**: Logic correctness.

### Failure mode 3: logger not available in function scope

**Detection**: `NameError: name 'logger'` at runtime.
**Resolution**: Confirm `logger = logging.getLogger(__name__)` exists at module level in `_snippets.py`.
**Gate**: Import correctness.

## Task-specific review checklist

1. [ ] Only `(OSError, IOError)` caught — no blanket `except Exception`
2. [ ] `return` placement preserves fallback path when store is absent
3. [ ] Both write paths (primary and run_dir fallback) are wrapped
4. [ ] `logger.warning` fires on failure; `logger.info` fires on success (else-branch)
5. [ ] Non-OSError exceptions (ValueError, AttributeError) still propagate
6. [ ] No change to function signature or caller (`_entry.py` line 221)
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/workers/understand/extract/_snippets.py` — modified with OSError guards
2. `reports/TC-4032/evidence.md` — test output showing success

## Acceptance checks

1. [ ] All pre-existing tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`
2. [ ] `integration/test_extract_embeddings.py` success path writes artifact (else-branch fires)
3. [ ] Mocking `EmbeddingIndex.save` to raise `OSError` — function returns without raising
4. [ ] Mocking `EmbeddingIndex.save` to raise `ValueError` — ValueError propagates

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: OSError guard confirmed by test
- [ ] Evidence captured: reports/TC-4032/evidence.md
- [ ] Doc freshness: no spec drift (embedding_index.json is already documented as side artifact)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ tests/integration/test_extract_embeddings.py -x -q
```

**Expected results**:
- All tests pass
- embedding_index.json written on success path
- OSError on disk write does not propagate

## Integration boundary proven

**Upstream**: `_entry.py:run_extract()` calls `_build_embedding_index()` at Phase B.6
**Downstream**: `embedding_index.json` consumed by evaluate worker for semantic checks
**Contract**: Function returns None; artifact written as side-effect; pipeline continues whether or not artifact was written
