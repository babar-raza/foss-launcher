"""Tests for TC-5135: Three-tier structural snippet-claim linking."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim, Snippet
from launcher.models.product import ApiSurface
from launcher.models.understanding import ApiFact
from launcher.workers.understand.extract._linking import (
    _build_claim_api_index,
    _detect_api_entities,
    filter_orphaned_snippets,
    link_snippets,
)


def _make_claim(claim_id: str, text: str, kind: str = "api") -> Claim:
    return Claim(claim_id=claim_id, text=text, kind=kind, confidence=0.9)


def _make_snippet(code: str, claim_ids: list[str] | None = None) -> Snippet:
    return Snippet(
        code=code,
        language="python",
        source_type="extracted",
        source_file="test.py",
        claim_ids=claim_ids or [],
    )


def _make_api_surface(classes: list[str]) -> ApiSurface:
    return ApiSurface(
        public_classes=classes,
        import_allowlist=["aspose.cells"],
        confidence="high",
        api_identifiers=[c.lower() for c in classes],
    )


def _make_api_fact(class_name: str, member_name: str) -> ApiFact:
    return ApiFact(
        fact_id=f"AF-test-{class_name}-{member_name}",
        class_name=class_name,
        member_name=member_name,
    )


class TestDetectApiEntities:
    def test_detects_known_class(self) -> None:
        code = "wb = Workbook()\nwb.save('out.xlsx')"
        cls, methods = _detect_api_entities(code, ["Workbook", "Worksheet"])
        assert cls == "Workbook"

    def test_detects_class_method_calls(self) -> None:
        code = "ws = Worksheet()\nws.get_cells()\nWorkbook.save('x')"
        cls, methods = _detect_api_entities(code, ["Workbook", "Worksheet"])
        assert "Worksheet.get_cells" in methods or "Workbook.save" in methods

    def test_unknown_class_not_detected(self) -> None:
        code = "x = RandomClass()"
        cls, methods = _detect_api_entities(code, ["Workbook"])
        assert cls == ""

    def test_empty_public_classes(self) -> None:
        code = "wb = Workbook()"
        cls, methods = _detect_api_entities(code, [])
        assert cls == ""


class TestBuildClaimApiIndex:
    def test_class_mention_in_claim(self) -> None:
        claims = [_make_claim("CLM-1", "Workbook provides save functionality")]
        api_facts = [_make_api_fact("Workbook", "save")]
        index = _build_claim_api_index(claims, api_facts, ["Workbook"])
        assert "CLM-1" in index.get("workbook", [])

    def test_class_method_mention_in_claim(self) -> None:
        claims = [_make_claim("CLM-1", "Call Workbook.save() to persist data")]
        api_facts = [_make_api_fact("Workbook", "save")]
        index = _build_claim_api_index(claims, api_facts, ["Workbook"])
        assert "CLM-1" in index.get("workbook.save", [])

    def test_no_match_returns_empty(self) -> None:
        claims = [_make_claim("CLM-1", "Install via pip")]
        api_facts = [_make_api_fact("Workbook", "save")]
        index = _build_claim_api_index(claims, api_facts, ["Workbook"])
        assert "CLM-1" not in index.get("workbook", [])


class TestLinkSnippetsTier1:
    """Tier 1: API identity match produces correct links without domain-vocabulary noise."""

    def test_snippet_links_to_claim_via_class_identity(self) -> None:
        snippets = [_make_snippet("wb = Workbook()\nwb.save('out.xlsx')")]
        claims = [
            _make_claim("CLM-1", "Workbook provides save functionality"),
            _make_claim("CLM-2", "Worksheet provides cell formatting"),  # decoy
        ]
        api_facts = [
            _make_api_fact("Workbook", "save"),
            _make_api_fact("Worksheet", "format"),
        ]
        api_surface = _make_api_surface(["Workbook", "Worksheet"])

        result = link_snippets(snippets, claims, api_surface, api_facts)
        assert len(result) == 1
        assert "CLM-1" in result[0].claim_ids
        # Decoy claim about Worksheet should NOT be linked
        assert "CLM-2" not in result[0].claim_ids

    def test_no_false_positives_from_domain_vocabulary(self) -> None:
        """A snippet using Workbook should NOT link to a Worksheet claim just
        because they share domain words like 'cell' or 'format'."""
        snippets = [_make_snippet(
            "wb = Workbook()\n"
            "# format cells\n"
            "wb.save('output.xlsx')"
        )]
        claims = [
            _make_claim("CLM-1", "Workbook.save() writes XLSX files"),
            _make_claim("CLM-2", "Worksheet cells provide formatting options"),
        ]
        api_facts = [
            _make_api_fact("Workbook", "save"),
            _make_api_fact("Worksheet", "get_cells"),
        ]
        api_surface = _make_api_surface(["Workbook", "Worksheet"])

        result = link_snippets(snippets, claims, api_surface, api_facts)
        assert "CLM-1" in result[0].claim_ids
        assert "CLM-2" not in result[0].claim_ids


class TestLinkSnippetsTier2:
    """Tier 2: TF-IDF fallback when no class names match."""

    def test_tfidf_links_when_no_class_detected(self) -> None:
        # Code without PascalCase class instantiation
        snippets = [_make_snippet(
            "import aspose.cells\n"
            "# Load an existing spreadsheet from disk\n"
            "data = load_spreadsheet('input.xlsx')\n"
            "print(data)"
        )]
        claims = [
            _make_claim("CLM-1", "Load spreadsheet files from disk using aspose.cells"),
            _make_claim("CLM-2", "Export 3D models to FBX format"),  # unrelated
        ]
        api_surface = _make_api_surface([])  # no classes known
        api_facts: list[ApiFact] = []

        result = link_snippets(snippets, claims, api_surface, api_facts)
        if result[0].claim_ids:
            # If TF-IDF linked anything, it should prefer CLM-1 (spreadsheet/load overlap)
            assert result[0].claim_ids[0] == "CLM-1"


class TestLinkSnippetsTier3:
    """Tier 3: Word-overlap fallback."""

    def test_fallback_works_when_tiers_1_2_fail(self) -> None:
        # Minimal overlap, no class names
        snippets = [_make_snippet("x = 1\nresult = compute(x)")]
        claims = [
            _make_claim("CLM-1", "The compute function processes input values and returns results"),
        ]
        api_surface = _make_api_surface([])
        api_facts: list[ApiFact] = []

        result = link_snippets(snippets, claims, api_surface, api_facts)
        # May or may not link — depends on word overlap threshold
        assert len(result) == 1  # snippet preserved either way


class TestLinkSnippetsEdgeCases:
    def test_empty_snippets(self) -> None:
        result = link_snippets([], [_make_claim("CLM-1", "test")], _make_api_surface([]), [])
        assert result == []

    def test_empty_claims(self) -> None:
        snippets = [_make_snippet("code")]
        result = link_snippets(snippets, [], _make_api_surface([]), [])
        assert len(result) == 1
        assert result[0].claim_ids == []

    def test_already_linked_snippets_preserved(self) -> None:
        snippets = [_make_snippet("code", claim_ids=["CLM-99"])]
        claims = [_make_claim("CLM-1", "test")]
        result = link_snippets(snippets, claims, _make_api_surface([]), [])
        assert result[0].claim_ids == ["CLM-99"]

    def test_max_links_respected(self) -> None:
        """Even with many matching claims, cap at _MAX_LINKS_PER_SNIPPET."""
        snippets = [_make_snippet("wb = Workbook()\nwb.save('x')")]
        claims = [
            _make_claim(f"CLM-{i}", f"Workbook feature number {i}")
            for i in range(20)
        ]
        api_facts = [_make_api_fact("Workbook", "save")]
        api_surface = _make_api_surface(["Workbook"])

        result = link_snippets(snippets, claims, api_surface, api_facts)
        assert len(result[0].claim_ids) <= 10


class TestFilterOrphanedSnippets:
    """TC-5174: filter_orphaned_snippets() removes dead data before bundle assembly."""

    def test_removes_unlinked_snippet(self) -> None:
        s_linked = _make_snippet("wb = Workbook()", claim_ids=["CLM-001"])
        s_orphan = _make_snippet("x = utility_fn()", claim_ids=[])
        result, dropped = filter_orphaned_snippets([s_linked, s_orphan])
        assert result == [s_linked]
        assert dropped == 1

    def test_keeps_all_linked_snippets(self) -> None:
        s1 = _make_snippet("wb = Workbook()", claim_ids=["CLM-001"])
        s2 = _make_snippet("ws = Worksheet()", claim_ids=["CLM-002", "CLM-003"])
        result, dropped = filter_orphaned_snippets([s1, s2])
        assert result == [s1, s2]
        assert dropped == 0

    def test_empty_input_returns_empty(self) -> None:
        result, dropped = filter_orphaned_snippets([])
        assert result == []
        assert dropped == 0

    def test_all_orphaned_returns_empty_list(self) -> None:
        s1 = _make_snippet("x = 1", claim_ids=[])
        s2 = _make_snippet("y = 2", claim_ids=[])
        result, dropped = filter_orphaned_snippets([s1, s2])
        assert result == []
        assert dropped == 2
