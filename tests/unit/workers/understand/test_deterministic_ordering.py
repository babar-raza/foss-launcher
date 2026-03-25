"""TC-DFR-004: Tests for deterministic ordering of class_facts iteration.

Verifies that sorting class_facts.items() produces identical claim order
regardless of dict insertion order.
"""
from __future__ import annotations


def _build_claims_from_class_facts(class_facts: dict[str, list[str]], max_claims: int = 50) -> list[str]:
    """Simulate the claim-building loop from _entry.py with sorted iteration."""
    raw_claims: list[str] = []
    for cls_name, facts in sorted(class_facts.items()):
        if len(raw_claims) >= max_claims:
            break
        for fact in facts[:5]:
            if len(raw_claims) >= max_claims:
                break
            raw_claims.append(f"{cls_name}.{fact}")
    return raw_claims


class TestDeterministicOrdering:
    """TC-DFR-004: Dict iteration determinism."""

    def test_sorted_class_facts_same_regardless_of_insertion_order(self):
        """Claims must be identical regardless of dict insertion order."""
        # Build dict in order A, B, C
        d1: dict[str, list[str]] = {}
        d1["Alpha"] = ["method_a", "method_b"]
        d1["Beta"] = ["method_c"]
        d1["Gamma"] = ["method_d", "method_e", "method_f"]

        # Build same dict in order C, A, B
        d2: dict[str, list[str]] = {}
        d2["Gamma"] = ["method_d", "method_e", "method_f"]
        d2["Alpha"] = ["method_a", "method_b"]
        d2["Beta"] = ["method_c"]

        claims1 = _build_claims_from_class_facts(d1)
        claims2 = _build_claims_from_class_facts(d2)

        assert claims1 == claims2

    def test_sorted_order_is_alphabetical(self):
        """Sorted iteration must produce alphabetical class order."""
        d: dict[str, list[str]] = {}
        d["Zebra"] = ["z_method"]
        d["Apple"] = ["a_method"]
        d["Mango"] = ["m_method"]

        claims = _build_claims_from_class_facts(d)
        assert claims == ["Apple.a_method", "Mango.m_method", "Zebra.z_method"]

    def test_max_claims_cap_respected(self):
        """Cap on max_claims must still work with sorted iteration."""
        d = {f"Class{i:03d}": [f"method_{j}" for j in range(3)] for i in range(20)}
        claims = _build_claims_from_class_facts(d, max_claims=5)
        assert len(claims) == 5
        # First class alphabetically is Class000
        assert claims[0].startswith("Class000.")

    def test_empty_class_facts(self):
        """Empty dict must produce no claims."""
        assert _build_claims_from_class_facts({}) == []

    def test_single_class(self):
        """Single class produces deterministic output."""
        d = {"OnlyClass": ["do_thing", "do_other"]}
        claims = _build_claims_from_class_facts(d)
        assert claims == ["OnlyClass.do_thing", "OnlyClass.do_other"]
