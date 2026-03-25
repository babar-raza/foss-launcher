"""Tests for prose contract loading and prompt integration (TC-PROSE-01, TC-PQ-CTR)."""
from __future__ import annotations

from pathlib import Path

import pytest

from launcher.workers.generate.section_prompt import (
    _load_prose_contract,
    _prose_contract_cache,
    _PROSE_CONTRACTS_DIR,
)


# TC-PQ-CTR: All roles that should have a dedicated prose contract file.
# installation removed (dead code — no page uses that role).
# toc, api_reference, feature_showcase added (roles with deployed pages).
_KNOWN_ROLES = [
    "blog_announcement",
    "feature_blog",
    "howto_article",
    "workflow_page",
    "faq",
    "troubleshooting",
    "reference_object_page",
    "landing",
    "toc",
    "api_reference",
    "feature_showcase",
]


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the prose contract cache before each test."""
    _prose_contract_cache.clear()
    yield
    _prose_contract_cache.clear()


class TestProseContractFiles:
    """Verify prose contract files exist and are non-empty."""

    @pytest.mark.parametrize("role", _KNOWN_ROLES)
    def test_contract_file_exists(self, role: str):
        path = _PROSE_CONTRACTS_DIR / f"{role}.txt"
        assert path.is_file(), f"Missing prose contract file for role {role!r}"

    def test_default_contract_exists(self):
        path = _PROSE_CONTRACTS_DIR / "_default.txt"
        assert path.is_file(), "Missing _default.txt fallback contract"

    def test_installation_contract_removed(self):
        """TC-PQ-CTR: installation.txt is dead code and must not exist."""
        path = _PROSE_CONTRACTS_DIR / "installation.txt"
        assert not path.is_file(), "installation.txt should be deleted (dead code — no page uses page_role: installation)"


class TestLoadProseContract:
    """Verify _load_prose_contract() returns correct content."""

    @pytest.mark.parametrize("role", _KNOWN_ROLES)
    def test_loads_known_role(self, role: str):
        contract = _load_prose_contract(role)
        assert contract, f"Prose contract for {role!r} is empty"
        assert len(contract) >= 100, f"Contract for {role!r} is too short ({len(contract)} chars)"

    def test_unknown_role_falls_back_to_default(self):
        contract = _load_prose_contract("unknown_role_xyz")
        default_contract = _load_prose_contract("_default")
        assert contract == default_contract
        assert contract, "Default contract is empty"

    def test_caching(self):
        c1 = _load_prose_contract("faq")
        c2 = _load_prose_contract("faq")
        assert c1 is c2, "Second call should return cached instance"

    def test_contract_contains_reader_goal(self):
        """Each contract should mention the reader's goal."""
        for role in _KNOWN_ROLES:
            contract = _load_prose_contract(role)
            has_goal = any(
                phrase in contract.lower()
                for phrase in ["reader goal", "reader's goal", "goal:"]
            )
            assert has_goal, f"Contract for {role!r} missing reader goal"

    def test_contract_contains_forbidden_patterns(self):
        """Each contract should specify forbidden prose patterns."""
        for role in _KNOWN_ROLES:
            contract = _load_prose_contract(role)
            assert "forbidden" in contract.lower() or "do not" in contract.lower(), (
                f"Contract for {role!r} missing forbidden patterns guidance"
            )

    def test_contract_contains_concrete_examples(self):
        """TC-PQ-CTR: Each contract should have GOOD/BAD examples for testable rules."""
        for role in _KNOWN_ROLES:
            contract = _load_prose_contract(role)
            has_good = "GOOD:" in contract or "good:" in contract.lower()
            has_bad = "BAD:" in contract or "bad:" in contract.lower()
            assert has_good and has_bad, (
                f"Contract for {role!r} missing concrete GOOD/BAD examples"
            )


class TestPromptTemplateIntegration:
    """Verify the restructured section_writer.txt has the prose_contract_block slot."""

    def test_template_has_prose_contract_slot(self):
        template_path = Path(__file__).resolve().parents[4] / "src" / "launcher" / "prompts" / "section_writer.txt"
        template = template_path.read_text(encoding="utf-8")
        assert "{prose_contract_block}" in template, "section_writer.txt missing {prose_contract_block} slot"

    def test_template_has_four_zones(self):
        template_path = Path(__file__).resolve().parents[4] / "src" / "launcher" / "prompts" / "section_writer.txt"
        template = template_path.read_text(encoding="utf-8")
        # Zone 1: Context
        assert "CONTEXT:" in template
        # Zone 2: Writing contract
        assert "WRITING CONTRACT:" in template
        # Zone 3: Claims material
        assert "CLAIMS TO USE" in template
        # Zone 4: Safety + format
        assert "HALLUCINATION PREVENTION" in template
        assert "OUTPUT FORMAT:" in template

    def test_writing_contract_before_claims(self):
        """Writing contract zone must appear before claims zone."""
        template_path = Path(__file__).resolve().parents[4] / "src" / "launcher" / "prompts" / "section_writer.txt"
        template = template_path.read_text(encoding="utf-8")
        contract_pos = template.index("WRITING CONTRACT:")
        claims_pos = template.index("CLAIMS TO USE")
        assert contract_pos < claims_pos, "Writing contract should appear before claims"

    def test_no_redundant_import_rules(self):
        """Import rule should appear at most twice (once in RULES, once in IMPORT RULE)."""
        template_path = Path(__file__).resolve().parents[4] / "src" / "launcher" / "prompts" / "section_writer.txt"
        template = template_path.read_text(encoding="utf-8")
        # Count occurrences of the key import rule phrase
        count = template.count("NEVER use any other import path")
        assert count <= 1, f"Redundant import rule appears {count} times (expected <= 1)"
