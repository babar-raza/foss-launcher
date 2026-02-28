"""Tests for W7 evidence bundle building and evidence grounding.

TC-3500: Validates that build_page_evidence_bundles() correctly loads,
caps, and indexes claim evidence chunks for per-page grounding.

SR-02: Also validates that evidence excerpts flow through the LLM regen
chain: _format_grounding_excerpts → build_enhancement_prompt → spawners.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from launch.workers.w7_content_reviewer.worker import build_page_evidence_bundles
from launch.workers.w7_content_reviewer.page_resolver import PageResolver
from launch.workers.w7_content_reviewer.fixes.llm_regen import (
    _format_grounding_excerpts,
    build_enhancement_prompt,
    spawn_enhancement_agents,
)


def _make_resolver(tmp_path, pages):
    """Create a PageResolver with draft files matching the page slugs."""
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir(parents=True)
    for page in pages:
        slug = page.get("slug", "")
        (drafts_dir / f"{slug}.md").write_text(f"# {slug}", encoding="utf-8")
    return PageResolver({"pages": pages}, drafts_dir)


class TestBuildPageEvidenceBundles:
    """build_page_evidence_bundles() tests."""

    def test_empty_claim_evidence_returns_empty(self, tmp_path):
        """No claim_evidence → empty bundles dict."""
        resolver = _make_resolver(tmp_path, [{"slug": "a", "claim_ids": ["c1"]}])
        result = build_page_evidence_bundles(resolver, {})
        assert result == {}

    def test_evidence_excerpts_loaded_when_present(self, tmp_path):
        """Valid claim_evidence produces excerpts for pages with matching claim_ids."""
        pages = [{"slug": "feature", "claim_ids": ["c1", "c2"]}]
        resolver = _make_resolver(tmp_path, pages)
        claim_evidence = {
            "chunks": {
                "c1": [
                    {"source": "README.md", "score": 0.9, "text": "Feature does X."},
                    {"source": "docs.md", "score": 0.5, "text": "Feature also Y."},
                ],
                "c2": [
                    {"source": "api.py", "score": 0.8, "text": "API provides Z."},
                ],
            }
        }
        bundles = build_page_evidence_bundles(resolver, claim_evidence)
        assert "feature.md" in bundles
        excerpts = bundles["feature.md"]
        # c1 has 2 chunks, c2 has 1 → 3 total (all within max_per_page=9)
        assert len(excerpts) == 3
        # Sorted by score within each claim → highest first
        assert excerpts[0]["score"] == 0.9
        assert excerpts[0]["claim_id"] == "c1"

    def test_excerpts_capped_at_max_per_page(self, tmp_path):
        """Excerpts are capped at max_per_page (default 9)."""
        pages = [{"slug": "big", "claim_ids": [f"c{i}" for i in range(20)]}]
        resolver = _make_resolver(tmp_path, pages)
        chunks = {
            f"c{i}": [{"source": f"s{i}", "score": 0.5, "text": f"chunk {i}"}]
            for i in range(20)
        }
        claim_evidence = {"chunks": chunks}
        bundles = build_page_evidence_bundles(resolver, claim_evidence, max_per_page=9)
        assert len(bundles.get("big.md", [])) <= 9

    def test_excerpts_truncated_at_300_chars(self, tmp_path):
        """Long excerpt text is truncated to max_excerpt_chars."""
        pages = [{"slug": "long", "claim_ids": ["c1"]}]
        resolver = _make_resolver(tmp_path, pages)
        long_text = "A" * 500
        claim_evidence = {
            "chunks": {
                "c1": [{"source": "src.py", "score": 0.9, "text": long_text}],
            }
        }
        bundles = build_page_evidence_bundles(resolver, claim_evidence, max_excerpt_chars=300)
        assert len(bundles["long.md"][0]["excerpt"]) == 300

    def test_pages_without_claims_skipped(self, tmp_path):
        """Pages with no claim_ids produce no bundles."""
        pages = [
            {"slug": "with", "claim_ids": ["c1"]},
            {"slug": "without", "claim_ids": []},
        ]
        resolver = _make_resolver(tmp_path, pages)
        claim_evidence = {
            "chunks": {"c1": [{"source": "s", "score": 0.5, "text": "t"}]},
        }
        bundles = build_page_evidence_bundles(resolver, claim_evidence)
        assert "with.md" in bundles
        assert "without.md" not in bundles

    def test_missing_chunk_for_claim_graceful(self, tmp_path):
        """Claims with no matching chunks in claim_evidence are skipped gracefully."""
        pages = [{"slug": "missing", "claim_ids": ["c_missing"]}]
        resolver = _make_resolver(tmp_path, pages)
        claim_evidence = {"chunks": {}}  # no chunks at all
        bundles = build_page_evidence_bundles(resolver, claim_evidence)
        # No excerpts found → page excluded from bundles
        assert "missing.md" not in bundles


class TestFormatGroundingExcerpts:
    """SR-02/TC-3500: _format_grounding_excerpts() unit tests."""

    def test_none_returns_empty(self):
        """None excerpts → empty string."""
        assert _format_grounding_excerpts(None) == ""

    def test_empty_list_returns_empty(self):
        """Empty list → empty string."""
        assert _format_grounding_excerpts([]) == ""

    def test_formats_excerpts_correctly(self):
        """Excerpts are formatted as [claim_id] (src: ..., score: ...) lines."""
        excerpts = [
            {"claim_id": "c1", "source": "README.md", "score": 0.92, "excerpt": "Feature X works."},
            {"claim_id": "c2", "source": "api.py", "score": 0.75, "excerpt": "Method Y returns Z."},
        ]
        result = _format_grounding_excerpts(excerpts)
        assert '[c1] (src: README.md, score: 0.92): "Feature X works."' in result
        assert '[c2] (src: api.py, score: 0.75): "Method Y returns Z."' in result
        # Two lines
        assert len(result.strip().split("\n")) == 2


class TestBuildEnhancementPromptEvidence:
    """SR-02/TC-3500: Evidence excerpt injection into build_enhancement_prompt."""

    def test_prompt_includes_grounding_block(self):
        """When evidence_excerpts are provided, prompt contains grounding section."""
        excerpts = [
            {"claim_id": "c1", "source": "src.py", "score": 0.88, "excerpt": "Foo bar."},
        ]
        prompt = build_enhancement_prompt(
            agent_type="technical_fixer",
            issues=[{"severity": "error", "check": "ta.api", "message": "API mismatch", "location": {"line": 10}}],
            draft_content="# Test\nSome content.",
            context={"product_name": "TestLib"},
            evidence_excerpts=excerpts,
        )
        assert "Grounding Excerpts" in prompt
        assert "do NOT invent facts beyond these" in prompt
        assert '[c1] (src: src.py, score: 0.88): "Foo bar."' in prompt

    def test_prompt_omits_grounding_when_no_excerpts(self):
        """When evidence_excerpts is None, no grounding section in prompt."""
        prompt = build_enhancement_prompt(
            agent_type="content_enhancer",
            issues=[{"severity": "error", "check": "cq.x", "message": "bad", "location": {"line": 1}}],
            draft_content="# Test",
            context={},
            evidence_excerpts=None,
        )
        assert "Grounding Excerpts" not in prompt


class TestSpawnerEvidenceThreading:
    """SR-02/TC-3500: evidence_bundles threads through spawners to _run_agent_on_files."""

    def test_evidence_bundles_reaches_run_agent(self, tmp_path):
        """evidence_bundles passed to spawn_enhancement_agents reaches _run_agent_on_files."""
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        # Write minimal artifacts that _load_artifact expects
        for name in ("product_facts.json", "snippet_catalog.json"):
            (run_dir / "artifacts" / name).write_text("{}", encoding="utf-8")

        bundles = {"tutorial.md": [{"claim_id": "c1", "source": "s", "score": 0.5, "excerpt": "e"}]}
        issues = [
            {
                "check": "technical_accuracy.api",
                "severity": "error",
                "message": "Wrong API",
                "location": {"path": "tutorial.md", "line": 5},
                "auto_fixable": False,
            },
        ]
        config = {"offline_mode": False, "review_enabled": True}

        # Patch _run_agent_on_files to capture kwargs
        captured = {}
        original_run = MagicMock(return_value={"agent_type": "technical_fixer", "status": "skipped",
                                                "issues_addressed": 1, "files_modified": []})

        with patch(
            "launch.workers.w7_content_reviewer.fixes.llm_regen._run_agent_on_files",
            side_effect=lambda *a, **kw: (captured.update(kw), original_run(*a, **kw))[1],
        ):
            spawn_enhancement_agents(
                issues, run_dir, config,
                llm_client=None, drafts_dir=tmp_path / "drafts",
                evidence_bundles=bundles,
            )

        # _run_agent_on_files should have received evidence_bundles
        assert "evidence_bundles" in captured
        assert captured["evidence_bundles"] is bundles
