"""Unit tests for check_limitations_contradiction (TC-HO-01)."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.limitations import check_limitations_contradiction


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_evidence(limitations: list[dict]) -> dict:
    return {"limitations": limitations}


def _lim(feature: str, status: str) -> dict:
    return {"feature": feature, "status": status, "constraint": "not supported"}


# ---------------------------------------------------------------------------
# Test A: affirmative content about an unsupported feature → LIMITATION_VIOLATED
# ---------------------------------------------------------------------------

def test_a_affirmed_unsupported_feature_emits_finding():
    """Content 'fully supports async operations' + limitation async=unsupported → violation."""
    content = (
        "---\ntitle: Async Guide\n---\n\n"
        "The library fully supports async operations for all API calls.\n"
    )
    evidence = _make_evidence([_lim("async", "unsupported")])
    findings = check_limitations_contradiction(content, "async-guide", product_evidence=evidence)
    assert len(findings) == 1
    f = findings[0]
    assert f.check == "limitation_violated"
    assert f.severity == "high"
    assert "async" in f.message
    assert f.location == "async-guide"


# ---------------------------------------------------------------------------
# Test B: negation guard — "does not support async" must not emit finding
# ---------------------------------------------------------------------------

def test_b_negation_prevents_false_positive():
    """Content 'does not support async' with async=unsupported → no finding."""
    content = (
        "---\ntitle: Async Limits\n---\n\n"
        "This library does not support async operations at this time.\n"
    )
    evidence = _make_evidence([_lim("async", "unsupported")])
    findings = check_limitations_contradiction(content, "async-limits", product_evidence=evidence)
    assert findings == []


# ---------------------------------------------------------------------------
# Test C: limitation with non-blocking status ("warning") → no finding
# ---------------------------------------------------------------------------

def test_c_non_blocking_status_ignored():
    """Content 'you can batch process files' + limitation batch=warning → no finding."""
    content = (
        "---\ntitle: Batch Processing\n---\n\n"
        "You can batch process files efficiently with this library.\n"
    )
    evidence = _make_evidence([{"feature": "batch", "status": "warning", "constraint": "slow"}])
    findings = check_limitations_contradiction(content, "batch-guide", product_evidence=evidence)
    assert findings == []


# ---------------------------------------------------------------------------
# Test D: no limitations in product_evidence → empty findings list
# ---------------------------------------------------------------------------

def test_d_no_limitations_returns_empty():
    """product_evidence with empty limitations list → no findings."""
    content = "---\ntitle: Page\n---\n\nThis library supports streaming.\n"
    evidence = _make_evidence([])
    findings = check_limitations_contradiction(content, "some-page", product_evidence=evidence)
    assert findings == []


# ---------------------------------------------------------------------------
# Additional tests
# ---------------------------------------------------------------------------

def test_none_product_evidence_returns_empty():
    """None product_evidence → no findings, no exception."""
    content = "The library supports async operations.\n"
    findings = check_limitations_contradiction(content, "page", product_evidence=None)
    assert findings == []


def test_empty_product_evidence_returns_empty():
    """Empty dict product_evidence → no findings, no exception."""
    findings = check_limitations_contradiction("content", "page", product_evidence={})
    assert findings == []


def test_deprecated_status_also_triggers():
    """feature with status=deprecated and affirmative content → finding emitted."""
    content = "The library supports OBJ export for all 3D scenes.\n"
    evidence = _make_evidence([_lim("OBJ export", "deprecated")])
    findings = check_limitations_contradiction(content, "obj-page", product_evidence=evidence)
    assert len(findings) >= 1
    assert findings[0].check == "limitation_violated"


def test_code_blocks_are_excluded_from_scan():
    """Affirmative text inside code block should not trigger finding."""
    content = (
        "---\ntitle: Code Demo\n---\n\n"
        "The following example shows usage:\n\n"
        "```python\n"
        "# The library supports async operations here\n"
        "result = client.async_call()\n"
        "```\n\n"
        "No async support in production.\n"
    )
    evidence = _make_evidence([_lim("async", "unsupported")])
    findings = check_limitations_contradiction(content, "demo", product_evidence=evidence)
    # "No async support" line has negation ("No"), so no finding expected
    assert findings == []


def test_experimental_status_ignored():
    """Status=experimental is not in blocked statuses → no finding."""
    content = "You can use the streaming API for real-time processing.\n"
    evidence = _make_evidence([{"feature": "streaming", "status": "experimental", "constraint": "unstable"}])
    findings = check_limitations_contradiction(content, "streaming-page", product_evidence=evidence)
    assert findings == []
