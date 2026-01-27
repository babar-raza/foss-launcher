"""Validation gates package.

This package contains individual gate implementations for TC-570.
Each gate module exports a single execute_gate function.
"""

from __future__ import annotations

__all__ = [
    "gate_2_claim_marker_validity",
    "gate_3_snippet_references",
    "gate_4_frontmatter_required_fields",
    "gate_5_cross_page_link_validity",
    "gate_6_accessibility",
    "gate_7_content_quality",
    "gate_8_claim_coverage",
    "gate_9_navigation_integrity",
    "gate_12_patch_conflicts",
    "gate_13_hugo_build",
]
