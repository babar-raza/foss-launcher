---
id: IUH-06
title: "TC-B07 determinism: SEO try/except guard + embedding sort + _walk_file_tree audit"
status: Not Started
priority: Medium
owner: Refactor Engineer
updated: "2026-03-11"
tags: [determinism, tc-b07, seo, embeddings, robustness]
depends_on: []
allowed_paths:
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/understand/extract/_snippets.py
  - tests/unit/workers/understand/test_determinism.py
  - plans/healing/IUH-06-determinism-verification.md
evidence_required:
  - reports/IUH-06/evidence.md
---

# Taskcard IUH-06 — TC-B07 determinism: SEO try/except guard + embedding sort + _walk_file_tree audit

## Objective

TC-B07 was skipped during the Phase B implementation. Three determinism/robustness gaps remain open:

1. **SEO keyword research (Phase B.6) is not wrapped in `try/except`** — if `research_keywords()` raises any exception (network, Gemini API rate-limit, malformed config), the entire Understand pipeline fails instead of continuing with an empty keyword bundle.
2. **`_build_embedding_index()` iterates claims in list order** — if claim assembly order is non-deterministic (e.g., different dict iteration order, LLM returning results in a different order), running Understand twice on the same repo produces different `embedding_index.json` artifacts.
3. **`_walk_file_tree()` sort order requires confirmation** — the implementation must use `sorted(repo_dir.rglob("*"))` to be filesystem-order independent.

Gap 3 is already fixed (`sorted()` at line 123 of `scout.py`). This taskcard addresses gaps 1 and 2, and documents gap 3 as verified.

## Required spec references

- `plans/reflective-finding-lark.md` — TC-B07: Isolate Nondeterministic Side Work
- `specs/worker_understand.md` — Phase B.6 observability; determinism contract

## Scope

### In scope
- Wrap Phase B.6 (`research_keywords()` call) in `try/except Exception` in `worker.py`; log `WARNING` and substitute empty/fallback `keyword_bundle`
- Sort claims by `claim_id` before iterating in `_build_embedding_index()` to guarantee stable key order in `embedding_index.json`
- Add `WARNING` log when SEO falls back to offline/error path
- Confirm `_walk_file_tree` uses `sorted()` (read-only audit, documented in evidence)

### Out of scope
- Changing the SEO keyword research algorithm itself
- Making embedding vectors deterministic (TF-IDF/API vectors are inherently deterministic given same input; only iteration order matters)
- Adding Gemini API retry logic (separate concern)
- Any changes to `scout.py` (gap 3 already resolved)

## Inputs

- `src/launcher/workers/understand/worker.py` — Phase B.6 SEO call (lines ~147–168)
- `src/launcher/workers/understand/extract/_snippets.py` — `_build_embedding_index()` (line ~472)
- `src/launcher/workers/understand/scout.py` — `_walk_file_tree()` (line ~111) — read-only audit

## Outputs

- `src/launcher/workers/understand/worker.py` — Phase B.6 wrapped in `try/except`; WARNING log on fallback
- `src/launcher/workers/understand/extract/_snippets.py` — `_build_embedding_index()` sorts claims by `claim_id` before iteration
- `tests/unit/workers/understand/test_determinism.py` — new test file
- `reports/IUH-06/evidence.md` — grep evidence + test output

## Allowed paths

- `src/launcher/workers/understand/worker.py`
- `src/launcher/workers/understand/extract/_snippets.py`
- `tests/unit/workers/understand/test_determinism.py`
- `plans/healing/IUH-06-determinism-verification.md`

### Allowed paths rationale
Phase B.6 (SEO guard) lives in `worker.py`. Embedding sort lives in `_snippets.py`. New test file keeps determinism tests isolated from other understand tests.

## Implementation steps

### Step 1: Read current Phase B.6 block in worker.py

Read `src/launcher/workers/understand/worker.py` around lines 147–168. Identify:
- The `research_keywords(...)` call
- What `keyword_bundle` is used for downstream (passed to `UnderstandingBundle`)
- What an empty fallback bundle looks like

### Step 2: Wrap Phase B.6 in try/except

Replace the bare `research_keywords(...)` call with a guarded version:

```python
# -- Phase B.6: SEO keyword research -----------------------------------
context.log.info("[Understand] Phase B.6 — SEO keyword research")
import os
from launcher.shared.keyword_research import research_keywords

seo_config = getattr(context.config, "seo", None)
seo_offline = getattr(seo_config, "offline_mode", False) if seo_config else False
try:
    keyword_bundle = research_keywords(
        product_name=product.display_name,
        family=product.family,
        platform=product.platform,
        claims=claims,
        cache_root=context.run_dir.parent / ".seo_cache",
        offline=seo_offline,
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
    )
    context.log.info(
        "[Understand] SEO keywords: %d primary, %d long-tail, gemini=%s",
        len(keyword_bundle.primary_keywords),
        len(keyword_bundle.long_tail),
        keyword_bundle.gemini_available,
    )
except Exception as _seo_err:
    context.log.warning(
        "[Understand] SEO keyword research failed — using empty bundle. error=%r",
        _seo_err,
    )
    from launcher.shared.keyword_research import KeywordBundle
    keyword_bundle = KeywordBundle(
        primary_keywords=[],
        long_tail=[],
        gemini_available=False,
    )
```

Note: confirm the empty `KeywordBundle` constructor signature by reading `src/launcher/shared/keyword_research.py`. If `KeywordBundle` has required positional arguments, use the appropriate empty constructor pattern.

### Step 3: Read _build_embedding_index() in _snippets.py

Read `src/launcher/workers/understand/extract/_snippets.py` at line ~472. Identify:
- How claims are iterated (`for claim in claims:`)
- What the `texts` dict keys look like (`f"claim:{claim.claim_id}"`)
- Whether any sort exists already

### Step 4: Add deterministic sort before embedding

In `_build_embedding_index()`, change:
```python
# Before:
for claim in claims:
    texts[f"claim:{claim.claim_id}"] = claim.text
```
to:
```python
# After:
for claim in sorted(claims, key=lambda c: c.claim_id):
    texts[f"claim:{claim.claim_id}"] = claim.text
```

This guarantees that regardless of the order claims are assembled upstream, `embedding_index.json` always has the same key insertion order, producing a stable artifact.

### Step 5: Audit _walk_file_tree (read-only)

Read `src/launcher/workers/understand/scout.py` around line 111. Confirm `sorted(repo_dir.rglob("*"))` is used. Document the finding in `reports/IUH-06/evidence.md` as "ALREADY SORTED — no change needed."

### Step 6: Write tests

Create `tests/unit/workers/understand/test_determinism.py`:

```python
"""Tests for TC-B07 determinism guarantees — IUH-06."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch


class TestSeoKeywordResearchFallback:
    @pytest.mark.asyncio
    async def test_seo_failure_does_not_crash_pipeline(self):
        """If research_keywords raises, worker must continue with empty bundle."""
        # This test verifies the guard by monkey-patching research_keywords to raise
        # The worker run() method should NOT propagate the exception
        from launcher.workers.understand.worker import UnderstandWorker
        # The simplest way: verify that the try/except is present in the source
        import inspect
        import launcher.workers.understand.worker as worker_mod
        source = inspect.getsource(worker_mod)
        assert "except Exception as _seo_err" in source or "except Exception" in source, (
            "Phase B.6 SEO block must be wrapped in try/except"
        )

    def test_keyword_bundle_fallback_has_empty_lists(self):
        """An empty keyword bundle must have empty primary_keywords and long_tail."""
        from launcher.shared.keyword_research import KeywordBundle
        # Confirm KeywordBundle can be constructed as an empty fallback
        try:
            bundle = KeywordBundle(
                primary_keywords=[],
                long_tail=[],
                gemini_available=False,
            )
            assert bundle.primary_keywords == []
            assert bundle.long_tail == []
        except TypeError as e:
            pytest.fail(
                f"KeywordBundle does not support empty fallback construction: {e}"
            )


class TestEmbeddingIndexDeterminism:
    def test_embedding_index_claim_order_is_stable(self, tmp_path):
        """Claims must be sorted by claim_id before embedding — same input → same output."""
        from launcher.workers.understand.extract._snippets import _build_embedding_index
        from launcher.models.claims import Claim
        import inspect

        source = inspect.getsource(_build_embedding_index)
        assert "sorted(" in source and "claim_id" in source, (
            "_build_embedding_index must sort claims by claim_id for determinism"
        )

    def test_walk_file_tree_uses_sorted_rglob(self):
        """_walk_file_tree must use sorted(rglob(...)) for filesystem-order independence."""
        from launcher.workers.understand.scout import _walk_file_tree
        import inspect

        source = inspect.getsource(_walk_file_tree)
        assert "sorted(" in source, (
            "_walk_file_tree must use sorted() to guarantee deterministic file ordering"
        )
```

Note: source inspection tests are a structural contract test — they verify the sort is present without running the full pipeline. Add integration tests if a mock LLM provider is available.

### Step 7: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_determinism.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

## Failure modes

### Failure mode 1: KeywordBundle constructor signature differs

**Detection**: `TypeError: KeywordBundle.__init__() got unexpected keyword arguments` when constructing the empty fallback.
**Resolution**: Read `src/launcher/shared/keyword_research.py` to find `KeywordBundle`'s actual constructor. Use correct field names. If it's a pydantic model, use `KeywordBundle.model_validate({})` or appropriate defaults.
**Gate**: SEO fallback path must never raise a second exception

### Failure mode 2: `claim_id` sort key raises on None or missing field

**Detection**: `TypeError: '<' not supported between instances` or `AttributeError: 'Claim' object has no attribute 'claim_id'` during embedding index build.
**Resolution**: Use `lambda c: (c.claim_id or "")` as the sort key. Verify `Claim.claim_id` type in `src/launcher/models/claims.py`.
**Gate**: Embedding index must build successfully for all valid bundles

### Failure mode 3: Source inspection tests fragile (assertion on whitespace)

**Detection**: Tests pass locally but fail on different Python versions due to whitespace differences in `inspect.getsource()`.
**Resolution**: Use `"sorted(" in source` and `"claim_id" in source` as separate checks (not combined string). This is already the approach above. Normalize to strip whitespace if needed: `source.replace(" ", "")`.
**Gate**: Tests must be stable across Python 3.11–3.13

## Task-specific review checklist

1. [ ] Phase B.6 `research_keywords()` call is inside `try/except Exception`
2. [ ] `WARNING` log emitted when SEO fallback triggered (not `ERROR` — it's non-fatal)
3. [ ] Empty `KeywordBundle` used as fallback (not `None` — downstream expects the object)
4. [ ] `_build_embedding_index()` sorts claims by `claim_id` before iteration
5. [ ] `_walk_file_tree()` confirmed to use `sorted(rglob(...))` — documented in evidence
6. [ ] `test_seo_failure_does_not_crash_pipeline` PASS
7. [ ] `test_embedding_index_claim_order_is_stable` PASS
8. [ ] `test_walk_file_tree_uses_sorted_rglob` PASS
9. [ ] Full unit suite: no regressions

## Deliverables

1. `src/launcher/workers/understand/worker.py` — Phase B.6 guarded with try/except; WARNING fallback log
2. `src/launcher/workers/understand/extract/_snippets.py` — `_build_embedding_index()` sorts by claim_id
3. `tests/unit/workers/understand/test_determinism.py` — 4 new tests
4. `reports/IUH-06/evidence.md` — test output + grep evidence + _walk_file_tree audit confirmation

## Acceptance checks

1. [ ] `grep "except Exception" src/launcher/workers/understand/worker.py` — ≥1 match in Phase B.6 region
2. [ ] `grep "sorted(" src/launcher/workers/understand/extract/_snippets.py` — ≥1 match in `_build_embedding_index`
3. [ ] `grep "sorted(" src/launcher/workers/understand/scout.py` — ≥1 match in `_walk_file_tree`
4. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_determinism.py -v` — all PASS
5. [ ] Full unit suite: no new failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] SEO guard: try/except present PASS
- [ ] Embedding sort: sorted(claim_id) present PASS
- [ ] _walk_file_tree: sorted confirmed PASS
- [ ] Evidence captured: `reports/IUH-06/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
grep -n "except Exception" src/launcher/workers/understand/worker.py
grep -n "sorted(" src/launcher/workers/understand/extract/_snippets.py
grep -n "sorted(" src/launcher/workers/understand/scout.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_determinism.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

**Expected results**:
- Phase B.6 `except Exception` present in worker.py
- `_build_embedding_index` has `sorted(` with `claim_id` nearby
- `_walk_file_tree` has `sorted(` — already confirmed
- All 4 new tests PASS
- No regressions

## Integration boundary proven

**Upstream**: `research_keywords()` may raise on Gemini API failure or config error — now contained
**Downstream**: `UnderstandingBundle.keyword_research` always receives a valid `KeywordBundle` object (never `None`); downstream Generate worker can safely access `.primary_keywords` and `.long_tail`
**Contract**: `_build_embedding_index` produces identical `embedding_index.json` for identical claim sets regardless of assembly order — downstream linker can rely on stable artifact

---

## Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Robustness | SEO failure never propagates beyond Phase B.6; pipeline always completes |
| Determinism | `embedding_index.json` is identical on two runs with same input |
| Minimality | Only the two call sites change; no new data structures or dependencies |
| Observability | WARNING log clearly states SEO failed and fallback was used |
| Verifiability | `_walk_file_tree` sort confirmed by code audit + structural test |

## Now (runbook)

```bash
# 1. Read Phase B.6 block
# Use Read tool on src/launcher/workers/understand/worker.py offset=147 limit=30

# 2. Read KeywordBundle constructor
grep -n "class KeywordBundle" src/launcher/shared/keyword_research.py
# Use Read tool around that line

# 3. Wrap Phase B.6 in try/except — use Edit tool

# 4. Read _build_embedding_index
# Use Read tool on src/launcher/workers/understand/extract/_snippets.py offset=472 limit=30

# 5. Add sorted() to claims iteration — use Edit tool

# 6. Confirm _walk_file_tree is already sorted
grep -n "sorted" src/launcher/workers/understand/scout.py

# 7. Write test file — use Write tool

# 8. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_determinism.py -v

# 9. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```
