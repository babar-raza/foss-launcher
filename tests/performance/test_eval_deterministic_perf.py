"""ICS-03 — Performance benchmark for _run_deterministic_checks().

Establishes a baseline timing after TC-EVAL-500 added 17+ checks.
No assertions are made on per-check timing (informational only).
The end-to-end assertion: full check suite < 2.0s on a 3000-word page.

Mark: pytest -m performance  (skipped in normal CI runs)
"""
from __future__ import annotations

import textwrap
import time

import pytest

from launcher.workers.evaluate.worker import _run_deterministic_checks
from launcher.workers.evaluate.checks import (
    check_forbidden_content,
    check_code_platform,
    check_unsourced_metrics,
    check_content_viability,
    check_heading_echo,
    check_prose_lead,
    check_sentence_openings,
    check_paragraph_monotony,
    check_explanation_gap,
    check_low_specificity,
    check_link_validity,
    check_faq_structure,
    check_contract_compliance,
    check_golden_conformance,
    check_content_utility,
    check_code_completeness_workflow,
)

pytestmark = pytest.mark.slow  # skip in fast CI with: pytest -m "not slow"


# ---------------------------------------------------------------------------
# Synthetic realistic page (~3000 words)
# ---------------------------------------------------------------------------

_SECTION_TEMPLATE = textwrap.dedent("""\
    ## {title}

    Aspose.Cells for Python via Java enables developers to create, manipulate,
    and convert spreadsheet files programmatically. The API exposes a rich set
    of classes for working with workbooks, worksheets, cells, styles, charts,
    pivot tables, and data validation rules.

    Use the `Workbook` class to open an existing file or create a new one.
    The `Worksheet` collection provides indexed access to each sheet. The
    `Cells` property on a `Worksheet` returns a `Cells` object that supports
    both index-based and named-range access. Setting a cell value is a single
    property assignment:

    ```python
    workbook = Workbook()
    sheet = workbook.worksheets[0]
    sheet.cells["A1"].value = "Hello"
    workbook.save("output.xlsx")
    ```

    Style objects control number formats, fonts, borders, and fill patterns.
    Conditional formatting rules can highlight ranges based on cell values or
    formula results. PivotTable objects summarize large datasets with drag-and-
    drop field placement. The charting engine supports 50+ chart types including
    bar, line, scatter, area, doughnut, radar, and waterfall charts.

    For files larger than 100 MB, use the `LoadOptions.memory_preference`
    property to reduce peak heap usage during parse. The streaming API
    (`LightCells`) can process rows one at a time without loading the full
    workbook into memory.

""")

_PAGE_BODY = "".join(
    _SECTION_TEMPLATE.format(title=title)
    for title in [
        "Overview",
        "Installation",
        "Creating a Workbook",
        "Working With Cells",
        "Applying Styles",
        "Charts and Visualizations",
        "Pivot Tables",
        "Data Validation",
        "Converting Files",
        "Performance Tuning",
    ]
)

_REALISTIC_PAGE = textwrap.dedent("""\
    ---
    title: "Aspose.Cells for Python — Developer Guide"
    platform: python
    page_role: guide
    product: Aspose.Cells
    description: "Comprehensive guide to Aspose.Cells for Python via Java"
    slug: cells/python/guide
    type: docs
    url: /cells/python/guide/
    ---
    """) + _PAGE_BODY


def _word_count(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------------------
# ICS-03-B1: end-to-end latency < 2.0s
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_deterministic_checks_latency():
    """Full _run_deterministic_checks() on a realistic 3000-word page must complete in < 2.0s."""
    wc = _word_count(_REALISTIC_PAGE)
    assert wc >= 1500, f"Synthetic page too short: {wc} words — beef up _SECTION_TEMPLATE"

    t0 = time.perf_counter()
    findings = _run_deterministic_checks(
        _REALISTIC_PAGE,
        "cells/python/guide",
        page_role="guide",
        product_name="Aspose.Cells",
    )
    elapsed = time.perf_counter() - t0

    print(f"\n[ICS-03] word_count={wc} elapsed={elapsed:.3f}s findings={len(findings)}")
    assert elapsed < 2.0, (
        f"_run_deterministic_checks took {elapsed:.3f}s on {wc}-word page — "
        f"exceeds 2.0s budget. Profile the slowest checks."
    )
    assert isinstance(findings, list)


# ---------------------------------------------------------------------------
# ICS-03-B2: per-check timing (informational, no assertion)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_per_check_timing(capsys):
    """Report per-check timing for the slowest checks (informational only)."""
    checks = [
        ("forbidden_content",         lambda: check_forbidden_content(_REALISTIC_PAGE, "slug")),
        ("code_platform",             lambda: check_code_platform(_REALISTIC_PAGE, "slug")),
        ("unsourced_metrics",         lambda: check_unsourced_metrics(_REALISTIC_PAGE, "slug")),
        ("content_viability",         lambda: check_content_viability(_REALISTIC_PAGE, "slug")),
        ("heading_echo",              lambda: check_heading_echo(_REALISTIC_PAGE, "slug")),
        ("prose_lead",                lambda: check_prose_lead(_REALISTIC_PAGE, "slug")),
        ("sentence_openings",         lambda: check_sentence_openings(_REALISTIC_PAGE, "slug")),
        ("paragraph_monotony",        lambda: check_paragraph_monotony(_REALISTIC_PAGE, "slug")),
        ("explanation_gap",           lambda: check_explanation_gap(_REALISTIC_PAGE, "slug")),
        ("low_specificity",           lambda: check_low_specificity(_REALISTIC_PAGE, "slug")),
        ("link_validity",             lambda: check_link_validity(_REALISTIC_PAGE, "slug")),
        ("faq_structure",             lambda: check_faq_structure(_REALISTIC_PAGE, "slug")),
        ("contract_compliance",       lambda: check_contract_compliance(_REALISTIC_PAGE, "slug")),
        ("content_utility",           lambda: check_content_utility(_REALISTIC_PAGE, "slug")),
        ("code_completeness_workflow",lambda: check_code_completeness_workflow(_REALISTIC_PAGE, "slug")),
        ("golden_conformance",        lambda: check_golden_conformance(_REALISTIC_PAGE, "slug")),
    ]

    results: list[tuple[str, float, int]] = []
    for name, fn in checks:
        t0 = time.perf_counter()
        found = fn()
        elapsed = time.perf_counter() - t0
        results.append((name, elapsed, len(found)))

    results.sort(key=lambda r: r[1], reverse=True)

    with capsys.disabled():
        print("\n[ICS-03] Per-check timing (sorted by slowest):")
        print(f"  {'Check':<35} {'ms':>8}  {'findings':>8}")
        print("  " + "-" * 55)
        for name, elapsed, count in results:
            print(f"  {name:<35} {elapsed*1000:>8.2f}  {count:>8}")

    # Informational only — all checks must complete in < 500ms individually
    for name, elapsed, _ in results:
        assert elapsed < 0.5, (
            f"check_{name} took {elapsed*1000:.1f}ms on a 3000-word page — "
            f"likely O(n²); investigate and optimize."
        )
