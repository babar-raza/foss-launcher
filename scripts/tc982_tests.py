


class TestGenerateFallbackContent:
    """TC-982: Tests for _generate_fallback_content() claim distribution and snippet matching."""

    def test_fallback_distributes_claims_evenly_across_headings(self):
        """TC-982 test 1: 10 claims across 4 headings -> ~2-3 claims per heading, no overlap."""
        claims = [
            {"claim_id": f"claim_{i}", "claim_text": f"Claim text {i}"}
            for i in range(10)
        ]
        headings = ["Overview", "Installation", "Key Features", "FAQ"]

        content = _generate_fallback_content(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=headings,
            product_name="TestProduct",
            claims=claims,
            snippets=[],
            url_path="/docs/test/",
        )

        # Each heading gets different claims (10/4=2 each)
        assert "[claim: claim_0]" in content
        assert "[claim: claim_1]" in content
        assert "[claim: claim_2]" in content
        assert "[claim: claim_3]" in content

        # Claims appear under different headings
        sections = content.split("## ")
        assert len(sections) >= 5, f"Expected 5+ sections, got {len(sections)}"

        # First heading (Overview) has claim_0 but NOT claim_4
        overview_section = sections[1]
        assert "[claim: claim_0]" in overview_section
        assert "[claim: claim_4]" not in overview_section

        # Third heading (Key Features) has claim_4 but NOT claim_0
        features_section = sections[3]
        assert "[claim: claim_4]" in features_section
        assert "[claim: claim_0]" not in features_section