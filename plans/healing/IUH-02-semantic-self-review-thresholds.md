---
id: IUH-02
title: "Implement TC-B06 semantic self-review thresholds in UnderstandWorker"
status: Done
priority: Critical
owner: Refactor Engineer
updated: "2026-03-11"
tags: [self-review, tc-b06, phase2-stop-gate, quality]
depends_on: []
allowed_paths:
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/understand/test_self_review_thresholds.py
  - plans/healing/IUH-02-semantic-self-review-thresholds.md
evidence_required:
  - reports/IUH-02/evidence.md
---

# Taskcard IUH-02 — Implement TC-B06 semantic self-review thresholds in UnderstandWorker

## Objective

The Phase 2 stop gate "self-review still passes Tier A with 0 claims" was never addressed. `UnderstandWorker.self_review()` currently checks only snippet syntax and internal claim visibility — it has no semantic thresholds. This means a Tier A bundle with 0–4 claims, or a bundle with an API surface but zero snippets, passes downstream and produces low-quality generated content. Add the three minimum thresholds specified in TC-B06.

## Required spec references

- `plans/reflective-finding-lark.md` — TC-B06: semantic self-review thresholds
- `specs/worker_understand.md` — self_review contract

## Scope

### In scope
- Add to `UnderstandWorker.self_review()`:
  1. Tier A: `len(claims) < 5` → HIGH-severity finding, `passed=False`
  2. Any tier: `len(snippets) == 0 and len(api_surface.public_classes) > 0` → HIGH-severity finding, `passed=False`
  3. Any tier: `claim_provenance_counts.llm + claim_provenance_counts.docstring < total_claims * 0.3` → WARNING finding (not blocking)
- `passed` must be `False` if any HIGH-severity finding is present

### Out of scope
- TC-B06's contradiction detection extensions (thread-safety, version claim) — deferred to separate taskcard
- Changes to the `SelfReviewResult` model
- Changes to `self_review()` for IntakeWorker (separate contract)

## Inputs

- `src/launcher/workers/understand/worker.py` — `UnderstandWorker.self_review()` current implementation
- `src/launcher/models/understanding.py` — `RichnessTier` enum, `UnderstandingBundle`
- `src/launcher/models/claims.py` — `Claim.claim_source`

## Outputs

- `src/launcher/workers/understand/worker.py` — updated `self_review()` with three semantic checks
- `tests/unit/workers/understand/test_self_review_thresholds.py` — new test file

## Allowed paths

- `src/launcher/workers/understand/worker.py`
- `tests/unit/workers/understand/test_self_review_thresholds.py`
- `plans/healing/IUH-02-semantic-self-review-thresholds.md`

### Allowed paths rationale
`self_review()` lives in `worker.py`. Tests are isolated in a new file to avoid polluting existing understand worker tests.

## Implementation steps

### Step 1: Read current self_review() implementation

Read `src/launcher/workers/understand/worker.py` from line 194 onward to understand the current `self_review()` structure. Identify:
- Where `findings` list is built
- Where `passed` bool is set
- Where `SelfReviewResult` is returned

### Step 2: Read RichnessTier enum

Read `src/launcher/models/understanding.py` and confirm the `RichnessTier` enum values. The relevant value is `RichnessTier.A` (or `"A"` if it's a string enum). Confirm how `bundle.richness_tier.tier` is typed.

### Step 3: Add semantic thresholds to self_review()

Insert after the existing syntax checks in `self_review()`, before the final `return SelfReviewResult(...)`:

```python
# -- TC-B06: Semantic thresholds ------------------------------------------

# Check 3: Tier A minimum claim count
from launcher.models.understanding import RichnessTier as _RT
tier_value = getattr(bundle.richness_tier, "tier", None)
if tier_value is not None and tier_value == _RT.A:
    if len(bundle.claims) < 5:
        findings.append({
            "category": "claims",
            "message": (
                f"Tier A bundle has only {len(bundle.claims)} claims "
                "(minimum 5 required for Tier A)"
            ),
            "severity": "high",
        })

# Check 4: No snippets despite non-empty API surface
if (
    not bundle.snippets
    and bundle.api_surface is not None
    and len(bundle.api_surface.public_classes) > 0
):
    findings.append({
        "category": "snippets",
        "message": (
            f"No snippets produced for bundle with "
            f"{len(bundle.api_surface.public_classes)} public API classes"
        ),
        "severity": "high",
    })

# Check 5: Most claims are deterministic fallback (warning, not blocking)
if bundle.claims:
    llm_count = sum(
        1 for c in bundle.claims
        if getattr(c, "claim_source", "llm") in ("llm", "docstring")
    )
    if llm_count < len(bundle.claims) * 0.3:
        findings.append({
            "category": "claims",
            "message": (
                f"Only {llm_count}/{len(bundle.claims)} claims from LLM/docstring sources "
                "(most are deterministic fallback) — verify LLM is reachable"
            ),
            "severity": "warning",
        })
```

Then ensure `passed` accounts for high-severity findings:

```python
# After all checks, before building SelfReviewResult:
passed = not any(f.get("severity") == "high" for f in findings)
```

Note: confirm whether `passed` is already set via a similar pattern. If it is already computed from `findings`, ensure the `"high"` severity check is included in its computation, replacing any simpler logic.

### Step 4: Write tests

Create `tests/unit/workers/understand/test_self_review_thresholds.py`:

```python
"""Tests for TC-B06 semantic self-review thresholds in UnderstandWorker — IUH-02."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, AsyncMock
from launcher.workers.understand.worker import UnderstandWorker


def _make_bundle(
    tier_value,
    claim_count: int = 10,
    snippet_count: int = 2,
    public_class_count: int = 3,
    llm_claim_fraction: float = 1.0,
):
    """Build a minimal UnderstandingBundle mock for self_review testing."""
    from launcher.models.claims import Claim
    from launcher.models.understanding import RichnessTier

    bundle = MagicMock()
    bundle.richness_tier.tier = tier_value

    # Build mock claims with appropriate claim_source
    claims = []
    for i in range(claim_count):
        c = MagicMock(spec=Claim)
        c.visibility = "public"
        c.claim_source = "llm" if i < int(claim_count * llm_claim_fraction) else "llm_fallback"
        c.text = f"Claim {i}"
        c.language = "python"
        c.code = "print('hello')"
        claims.append(c)
    bundle.claims = claims

    # Build mock snippets
    snippets = []
    for i in range(snippet_count):
        s = MagicMock()
        s.language = "python"
        s.code = "print('hello')"
        s.source_type = "extracted"
        snippets.append(s)
    bundle.snippets = snippets

    # Build mock API surface
    bundle.api_surface = MagicMock()
    bundle.api_surface.public_classes = [MagicMock() for _ in range(public_class_count)]

    return bundle


class TestTierAMinimumClaimCount:
    @pytest.mark.asyncio
    async def test_tier_a_with_4_claims_fails(self):
        from launcher.models.understanding import RichnessTier
        bundle = _make_bundle(tier_value=RichnessTier.A, claim_count=4, snippet_count=1)
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        assert result.passed is False
        assert any(
            f.get("category") == "claims" and "Tier A" in f.get("message", "")
            for f in result.findings
        )

    @pytest.mark.asyncio
    async def test_tier_a_with_5_claims_passes_this_check(self):
        from launcher.models.understanding import RichnessTier
        bundle = _make_bundle(tier_value=RichnessTier.A, claim_count=5, snippet_count=1)
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        # Should not fail due to claim count (may fail for other reasons)
        assert not any(
            "Tier A" in f.get("message", "") and f.get("severity") == "high"
            for f in result.findings
        )

    @pytest.mark.asyncio
    async def test_tier_c_with_1_claim_is_not_flagged(self):
        from launcher.models.understanding import RichnessTier
        bundle = _make_bundle(tier_value=RichnessTier.C, claim_count=1, snippet_count=1,
                              public_class_count=0)
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        assert not any("Tier A" in f.get("message", "") for f in result.findings)


class TestNoSnippetsWithApiSurface:
    @pytest.mark.asyncio
    async def test_zero_snippets_with_api_surface_fails(self):
        from launcher.models.understanding import RichnessTier
        bundle = _make_bundle(
            tier_value=RichnessTier.B, claim_count=10,
            snippet_count=0, public_class_count=3
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        assert result.passed is False
        assert any(
            f.get("category") == "snippets" and f.get("severity") == "high"
            for f in result.findings
        )

    @pytest.mark.asyncio
    async def test_zero_snippets_no_api_surface_passes_this_check(self):
        from launcher.models.understanding import RichnessTier
        bundle = _make_bundle(
            tier_value=RichnessTier.C, claim_count=5,
            snippet_count=0, public_class_count=0
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        assert not any(
            f.get("category") == "snippets" and f.get("severity") == "high"
            for f in result.findings
        )


class TestFallbackClaimWarning:
    @pytest.mark.asyncio
    async def test_mostly_fallback_claims_emits_warning_not_fail(self):
        from launcher.models.understanding import RichnessTier
        bundle = _make_bundle(
            tier_value=RichnessTier.B, claim_count=10,
            snippet_count=1, llm_claim_fraction=0.1  # 10% LLM, 90% fallback
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        # Warning should appear but passed should not be False solely due to this
        warning_findings = [
            f for f in result.findings
            if "deterministic fallback" in f.get("message", "")
        ]
        assert warning_findings, "Expected a warning finding for mostly-fallback claims"
        for f in warning_findings:
            assert f.get("severity") == "warning", "Fallback warning must not block (severity=warning)"
```

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_self_review_thresholds.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

## Failure modes

### Failure mode 1: RichnessTier import path or enum value name differs

**Detection**: `ImportError` or `AttributeError: RichnessTier has no attribute A` in test.
**Resolution**: Read `src/launcher/models/understanding.py` and find the actual enum class name and member names. Adjust import path and enum member reference in both `worker.py` and test.
**Gate**: G-02 — Phase 2 stop gate

### Failure mode 2: self_review() already computes passed in a way that ignores new findings

**Detection**: Test `test_tier_a_with_4_claims_fails` passes finding check but `result.passed` is still `True`.
**Resolution**: Read the current `passed` computation in `self_review()`. Change it to `passed = not any(f.get("severity") == "high" for f in findings)` instead of any ad-hoc boolean.
**Gate**: G-02 — self_review must gate on HIGH-severity findings

### Failure mode 3: bundle.api_surface is None in some code paths

**Detection**: `AttributeError: NoneType has no attribute public_classes` in snippet check.
**Resolution**: The guard `bundle.api_surface is not None` is already in the template above. Confirm it's in place.
**Gate**: Robustness — bundles without API surface should not crash self_review

## Task-specific review checklist

1. [ ] Tier A with 4 claims → `self_review()` returns `passed=False` with `"category": "claims"` finding
2. [ ] Tier A with 5+ claims → no Tier A claim-count finding
3. [ ] Any tier with 0 snippets and non-empty `api_surface.public_classes` → `passed=False` with `"category": "snippets"` finding
4. [ ] Any tier with 0 snippets and empty `api_surface.public_classes` → snippets check does NOT fire
5. [ ] Mostly-fallback claims → `severity="warning"` finding, `passed` still True (not blocked by this alone)
6. [ ] Full unit suite passes with no regressions
7. [ ] Docstring on `self_review()` updated to describe new semantic checks
8. [ ] `specs/worker_understand.md` confirmed consistent with new behavior (or updated)

## Deliverables

1. `src/launcher/workers/understand/worker.py` — three new semantic checks in `self_review()`
2. `tests/unit/workers/understand/test_self_review_thresholds.py` — 7 new tests
3. `reports/IUH-02/evidence.md` — test run output showing all 7 pass

## Acceptance checks

1. [ ] `test_tier_a_with_4_claims_fails` PASS
2. [ ] `test_zero_snippets_with_api_surface_fails` PASS
3. [ ] `test_mostly_fallback_claims_emits_warning_not_fail` PASS — warning exists, passed still True
4. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q` — no new failures
5. [ ] Phase 2 stop gate "self_review still passes Tier A with 0 claims" → now CLOSED

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: Phase 2 stop gate verified PASS
- [ ] Evidence captured: `reports/IUH-02/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_self_review_thresholds.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

**Expected results**:
- 7 new tests PASS
- No regressions in full suite

## Integration boundary proven

**Upstream**: `UnderstandWorker.run()` produces `UnderstandingBundle` → `self_review()` validates it
**Downstream**: `WorkerContract` stops pipeline propagation if `self_review().passed is False`; downstream Generate worker never receives a Tier A bundle with <5 claims
**Contract**: `SelfReviewResult.passed=False` iff any finding has `severity="high"`

---

## Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | Tier A <5 claims always fails; zero-snippet with API always fails; fallback-heavy warns but doesn't block |
| Robustness | `api_surface=None` doesn't crash; empty claims list doesn't crash |
| Testability | Each threshold tested independently; mock bundle construction is reusable across test classes |
| Integration fit | Uses existing `findings` + `passed` pattern already in `self_review()`; no new model fields |
| Observability | Finding messages are human-readable and include counts for debugging |

## Now (runbook)

```bash
# 1. Read current self_review()
# Use Read tool on src/launcher/workers/understand/worker.py offset=194

# 2. Find where passed is computed and where SelfReviewResult is returned
grep -n "passed" src/launcher/workers/understand/worker.py | head -20

# 3. Read RichnessTier enum
grep -n "class RichnessTier" src/launcher/models/understanding.py

# 4. Add the three checks using Edit tool

# 5. Write test file using Write tool

# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_self_review_thresholds.py -v

# 7. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```
