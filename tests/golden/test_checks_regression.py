"""
Golden corpus regression suite — TC-3876b.

Every grade-A golden page must produce zero high/critical findings
from content-quality checks. Every grade-B page must produce zero
critical findings.

Checks excluded from content-quality assertions (meta/infrastructure):
  - seo          : golden files lack seoTitle, robots, canonical, keywords
                   (these are SEO metadata fields, not content quality)
  - frontmatter  : golden files lack slug, url (low severity only — acceptable)
  - claim_leakage: no claim IDs in golden by design (trivially passes anyway)
  - slug_safety  : not called by _run_deterministic_checks

Initial run will reveal KNOWN FAILURES before TC-3877/3878/3879 fix thresholds.
Each known failure is documented below with the TC that will resolve it.
"""
import pytest
from pathlib import Path
from launcher.shared.golden_loader import GoldenIndex
from launcher.workers.evaluate.worker import _run_deterministic_checks

GOLDEN_DIR = Path(__file__).parent.parent.parent / "golden"

# Checks that measure CONTENT quality — golden pages must satisfy these.
# Excludes meta/infrastructure checks that golden files deliberately omit.
_CONTENT_QUALITY_CHECKS = frozenset({
    "density",
    "readability",
    "repetition",
    "structure",
    "artifacts",
    "product_names",
    "safety",
    "spec_leakage",
    "semantic_structure",
    "code",
    "reference_completeness",
})

# Placeholder matching the __FAMILY__/__PLATFORM__ template variables in golden files.
# Prevents product_name checks from firing on literal template variable strings.
_PLACEHOLDER_PRODUCT = "Aspose.__FAMILY__ for __PLATFORM__"
_PLACEHOLDER_IMPORT = "aspose_family_foss"


def _load_grade_a_pages() -> list:
    if not GOLDEN_DIR.exists():
        return []
    index = GoldenIndex.load(GOLDEN_DIR)
    return [p for p in index.all_pages() if p.grade_letter == "A"]


def _load_grade_b_pages() -> list:
    if not GOLDEN_DIR.exists():
        return []
    index = GoldenIndex.load(GOLDEN_DIR)
    return [p for p in index.all_pages() if p.grade_letter == "B"]


def _fmt_failures(page, findings) -> str:
    lines = [
        f"Golden page '{page.source_path.name}' "
        f"(grade={page.grade}, role={page.page_role}, variant={page.variant}) failed:"
    ]
    for f in findings:
        lines.append(
            f"  [{f.severity.upper()}] check={f.check} | {f.message} | location={f.location}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Grade-A: zero high/critical findings from content checks
# ---------------------------------------------------------------------------

# KNOWN FAILURES (pre-fix baseline — remove entry when its TC resolves it):
#
#   installation.md (grade=A, role=installation):
#     [HIGH] safety — Commercial domain link: https://releases.aspose.com
#     Root cause: safety check flags aspose.com links as commercial.
#     Installation pages legitimately reference download sources.
#     Fix needed: exempt installation/license pages from commercial-link rule,
#     OR update golden file to use aspose.net release URL.
#     → Fixed by: future TC (safety role exemption for installation pages)
#
#   reference.variant-standard.md (grade=A, role=api_reference):
#     [HIGH] repetition — Found 16 exact duplicate sentences
#     Root cause: API reference pages repeat property descriptions by design
#     (e.g. "The type of barcode to read." appears once per property).
#     The threshold=10 for reference roles is still too strict.
#     → Fixed by: TC-3879 (raise exact-duplicate threshold for api_reference)
#
#   _index.md (grade=A, role=section_index):
#     [HIGH] density — Page has 49 words (minimum 100)
#     Root cause: section_index nav pages have sparse prose by design.
#     density.py exempts "toc" and reference roles but not "section_index".
#     → Fixed by: TC-3877 (add section_index to density exempt roles)

_KNOWN_FAILURES_HIGH_CRITICAL: dict[str, str] = {
    "installation.md": (
        "safety fires on commercial link (releases.aspose.com) — "
        "installation pages need safety exemption for download URLs"
    ),
    "reference.variant-standard.md": (
        "repetition fires (16 exact duplicate sentences > threshold=10) — "
        "TC-3879 will raise threshold for api_reference"
    ),
    "_index.md": (
        "density fires (49 words < 100) — "
        "TC-3877 will exempt section_index from word-count minimum"
    ),
}


@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
@pytest.mark.parametrize("page", _load_grade_a_pages(), ids=lambda p: p.source_path.name)
def test_no_high_critical_on_grade_a(page):
    """Grade-A golden pages must produce zero high/critical content-quality findings."""
    reason = _KNOWN_FAILURES_HIGH_CRITICAL.get(page.source_path.name)
    if reason:
        pytest.xfail(reason=reason)

    findings = _run_deterministic_checks(
        page.content, page.source_path.stem,
        page_role=page.page_role,
        product_name=_PLACEHOLDER_PRODUCT,
        canonical_import=_PLACEHOLDER_IMPORT,
        golden_dir=GOLDEN_DIR,
    )
    blockers = [
        f for f in findings
        if f.check in _CONTENT_QUALITY_CHECKS
        and f.severity in ("critical", "high")
    ]
    assert not blockers, _fmt_failures(page, blockers)


# ---------------------------------------------------------------------------
# Grade-B: zero critical findings from content checks
# ---------------------------------------------------------------------------

@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
@pytest.mark.parametrize("page", _load_grade_b_pages(), ids=lambda p: p.source_path.name)
def test_no_critical_on_grade_b(page):
    """Grade-B golden pages must produce zero critical content-quality findings."""
    findings = _run_deterministic_checks(
        page.content, page.source_path.stem,
        page_role=page.page_role,
        product_name=_PLACEHOLDER_PRODUCT,
        canonical_import=_PLACEHOLDER_IMPORT,
        golden_dir=GOLDEN_DIR,
    )
    critical = [
        f for f in findings
        if f.check in _CONTENT_QUALITY_CHECKS
        and f.severity == "critical"
    ]
    assert not critical, _fmt_failures(page, critical)


# ---------------------------------------------------------------------------
# Smoke tests: suite can collect and load pages (independent of grade assertions)
# ---------------------------------------------------------------------------

@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
def test_grade_a_pages_exist():
    """Sanity: golden corpus contains at least one grade-A page."""
    pages = _load_grade_a_pages()
    assert len(pages) >= 1, "Expected at least one grade-A golden page in golden/"


@pytest.mark.golden
@pytest.mark.skipif(not GOLDEN_DIR.exists(), reason="golden/ directory not present")
def test_all_pages_have_content():
    """All pages loaded by all_pages() must have non-empty content field (TC-3876a)."""
    index = GoldenIndex.load(GOLDEN_DIR)
    for page in index.all_pages():
        assert page.content, (
            f"Empty content on {page.source_path} — "
            "TC-3876a did not store content correctly"
        )
