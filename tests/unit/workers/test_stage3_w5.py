"""Stage 3 W5 hardening tests.

Covers:
  T3.1  _slug_to_readable strips 'how-to-' prefix
  T3.2  _slug_to_readable preserves readable title with spaces
  T3.3  _slug_to_readable handles 'how_to_' underscore prefix
  T3.4  Slug guard in _build_deterministic_howto_article produces body free of raw slug
  T3.5  Slug guard detects hyphenated slug pattern (no spaces) and converts hyphens to spaces
  T3.6  worker.py emits '<!-- claim: {id} -->' not the legacy '<!-- claim_id: {id} -->'
  T3.7  _slug_to_readable never returns an empty string for degenerate input
"""

import pathlib
import re

import pytest

# ---------------------------------------------------------------------------
# Import target
# ---------------------------------------------------------------------------

from src.launch.workers.w5_section_writer.generators.content_generators import (
    _slug_to_readable,
    _build_deterministic_howto_article,
)


# ---------------------------------------------------------------------------
# T3.1 — strips "how-to-" prefix
# ---------------------------------------------------------------------------


def test_slug_to_readable_strips_howto_prefix():
    """T3.1: 'how-to-mesh-operations' -> 'mesh operations'."""
    assert _slug_to_readable("how-to-mesh-operations") == "mesh operations"


# ---------------------------------------------------------------------------
# T3.2 — preserves readable title that already has spaces
# ---------------------------------------------------------------------------


def test_slug_to_readable_preserves_readable_title():
    """T3.2: A title with spaces is NOT treated as a slug and is returned unchanged."""
    assert _slug_to_readable("3D Mesh Operations") == "3D Mesh Operations"


# ---------------------------------------------------------------------------
# T3.3 — handles underscore variant "how_to_"
# ---------------------------------------------------------------------------


def test_slug_to_readable_handles_underscore_prefix():
    """T3.3: 'how_to_format_cells' -> 'format cells' (underscores, not hyphens)."""
    assert _slug_to_readable("how_to_format_cells") == "format cells"


# ---------------------------------------------------------------------------
# T3.4 — _build_deterministic_howto_article body must not leak the raw slug
# ---------------------------------------------------------------------------

def _minimal_product_facts(product_name: str = "Aspose.3D") -> dict:
    """Minimal product_facts structure accepted by the generator."""
    return {
        "product_name": product_name,
        "claims": [],
        "claim_groups": {},
    }


def _minimal_snippet_catalog() -> dict:
    """Minimal snippet_catalog accepted by the generator."""
    return {"snippets": []}


def test_deterministic_howto_no_slug_in_body():
    """T3.4: When page title is a raw slug like 'how-to-mesh-operations',
    the generated body must not contain the literal prefix 'how-to-'.
    """
    page = {
        "slug": "how-to-mesh-operations",
        # deliberately omit 'title' so the generator falls back to the slug
        "required_claim_ids": [],
        "required_snippet_tags": [],
        "required_headings": [],
        "page_role": "how_to",
        "purpose": "test page",
    }

    body = _build_deterministic_howto_article(
        page,
        _minimal_product_facts(),
        _minimal_snippet_catalog(),
    )

    # The slug guard should have converted "how-to-mesh-operations" -> "mesh operations"
    # before embedding it in the text.  Verify the raw prefix is absent.
    assert "how-to-" not in body, (
        f"Expected 'how-to-' to be stripped from body, but found it.\n"
        f"Body excerpt:\n{body[:400]}"
    )
    # And the cleaned text should appear somewhere in the body
    assert "mesh operations" in body.lower(), (
        f"Expected 'mesh operations' in body after slug sanitisation.\n"
        f"Body excerpt:\n{body[:400]}"
    )


# ---------------------------------------------------------------------------
# T3.5 — slug guard correctly identifies hyphenated-slug vs readable-title
# ---------------------------------------------------------------------------


def test_slug_guard_detects_slug_pattern():
    """T3.5: A hyphenated token with no spaces is treated as a slug —
    _slug_to_readable converts hyphens to spaces and strips 'how-to-' if present.
    """
    result = _slug_to_readable("convert-obj-to-stl")

    # Hyphens must be gone
    assert "-" not in result, f"Hyphens should have been replaced; got: {repr(result)}"
    # The first meaningful word should be present
    assert "convert" in result, f"Expected 'convert' in result; got: {repr(result)}"
    # Confirm it's human-readable (spaces where hyphens were)
    assert result == "convert obj to stl", f"Unexpected result: {repr(result)}"


# ---------------------------------------------------------------------------
# T3.6 — worker.py must use '<!-- claim: id -->' not '<!-- claim_id: id -->'
# ---------------------------------------------------------------------------

_WORKER_PY = (
    pathlib.Path(__file__).parents[3]
    / "src"
    / "launch"
    / "workers"
    / "w5_section_writer"
    / "worker.py"
)


def test_claim_marker_uses_claim_colon():
    """T3.6: worker.py must emit '<!-- claim: {id} -->' format.

    Scans the source for any f-string or string literal that would produce
    the LEGACY '<!-- claim_id: ...' format.  The only allowed occurrence of
    the text 'claim_id:' in worker.py is inside comments that describe the
    OLD format (e.g., a code comment 'Fix inline HTML claim markers
    (<!-- claim_id: UUID -->)').

    The test verifies that no Python *string* (single- or double-quoted,
    f-string or plain) contains the 'claim_id:' token, because that would
    mean the code is emitting the legacy format at runtime.
    """
    source = _WORKER_PY.read_text(encoding="utf-8")

    # Find all lines that contain 'claim_id:' INSIDE a Python string literal.
    # We look for the pattern inside f-strings / regular strings.
    # Strategy: find 'claim_id:' occurrences in quoted contexts by checking
    # whether the line contains it inside quotes (f"..." or "...").
    string_literal_re = re.compile(
        r"""(?:[fF]?(?:"[^"]*claim_id:[^"]*"|'[^']*claim_id:[^']*'))"""
    )

    violations = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        # Skip pure comment lines — those are just documentation of the old format.
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if string_literal_re.search(line):
            violations.append((lineno, line.rstrip()))

    assert not violations, (
        "worker.py contains string literals emitting the legacy 'claim_id:' format "
        "(should use 'claim:' instead).\n"
        "Offending lines:\n"
        + "\n".join(f"  L{ln}: {text}" for ln, text in violations)
    )


# ---------------------------------------------------------------------------
# T3.7 — _slug_to_readable never returns an empty string
# ---------------------------------------------------------------------------


def test_slug_to_readable_handles_edge_cases():
    """T3.7: Degenerate input 'how-to-' strips the prefix, leaving nothing —
    the function must fall back to the original string rather than returning ''.
    """
    result = _slug_to_readable("how-to-")
    assert len(result) > 0, (
        "_slug_to_readable must never return an empty string. "
        f"Got: {repr(result)}"
    )
    # The implementation's contract: return original when stripped result is empty
    assert result == "how-to-", (
        f"Expected fallback to original 'how-to-', got: {repr(result)}"
    )
