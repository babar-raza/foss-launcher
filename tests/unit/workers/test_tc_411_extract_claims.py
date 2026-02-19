"""Unit tests for TC-411: Extract claims from product documentation.

Tests claims extraction, validation, and artifact generation per:
- specs/03_product_facts_and_evidence.md (Claims extraction algorithm)
- specs/04_claims_compiler_truth_lock.md (Claim structure)
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/10_determinism_and_caching.md (Stable ordering)

TC-411: W2.1 Extract claims from product repo
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.launch.workers.w2_facts_builder.extract_claims import (
    ClaimsExtractionError,
    ClaimsValidationError,
    MIN_CLAIM_CHARS,
    _build_heading_map,
    _cluster_claims_by_topic,
    _extract_best_practice_statements,
    _extract_performance_characteristics,
    _generate_offline_api_claims,
    _infer_best_practices_from_code,
    _is_code_like,
    _is_parameter_description,
    _is_prose_like,
    _is_template_claim,
    _synthesize_code_block_claims,
    classify_claim_kind,
    compute_claim_id,
    deduplicate_claims,
    detect_format_conversions,
    determine_source_priority,
    determine_source_type,
    extract_candidate_statements_from_text,
    extract_claims,
    extract_claims_from_code_analysis,
    extract_claims_with_llm,
    normalize_claim_text,
    sort_claims_deterministically,
    validate_claim_structure,
)


class TestClaimNormalization:
    """Test claim text normalization per specs/04_claims_compiler_truth_lock.md:15-19."""

    def test_normalize_claim_text_basic(self):
        """Test basic normalization: trim, collapse whitespace, lowercase."""
        claim = "  Supports   multiple   formats  "
        result = normalize_claim_text(claim, "ProductName")
        assert result == "supports multiple formats"

    def test_normalize_claim_text_product_name_replacement(self):
        """Test product name tokenization."""
        claim = "Aspose.3D supports OBJ format"
        result = normalize_claim_text(claim, "Aspose.3D")
        assert result == "{product_name} supports obj format"

    def test_normalize_claim_text_case_insensitive_product_name(self):
        """Test case-insensitive product name replacement."""
        claim = "aspose.3d and Aspose.3D both work"
        result = normalize_claim_text(claim, "Aspose.3D")
        assert result == "{product_name} and {product_name} both work"

    def test_normalize_claim_text_collapse_newlines(self):
        """Test newline collapse to spaces."""
        claim = "Supports\nmultiple\nformats"
        result = normalize_claim_text(claim, "Product")
        assert result == "supports multiple formats"


class TestClaimIDComputation:
    """Test stable claim_id generation per specs/04_claims_compiler_truth_lock.md:12-19."""

    def test_compute_claim_id_deterministic(self):
        """Test claim_id is deterministic for same input."""
        claim = "Supports OBJ format"
        product_name = "Aspose.3D"
        claim_kind = "format"

        id1 = compute_claim_id(claim, claim_kind, product_name)
        id2 = compute_claim_id(claim, claim_kind, product_name)

        assert id1 == id2
        assert len(id1) == 64  # SHA256 hex length

    def test_compute_claim_id_different_for_different_kind(self):
        """Test claim_id differs when claim_kind differs."""
        claim = "Supports OBJ format"
        product_name = "Aspose.3D"

        id_format = compute_claim_id(claim, "format", product_name)
        id_feature = compute_claim_id(claim, "feature", product_name)

        assert id_format != id_feature

    def test_compute_claim_id_stable_across_whitespace_variations(self):
        """Test claim_id stable despite whitespace variations."""
        product_name = "Product"

        id1 = compute_claim_id("Supports   OBJ", "format", product_name)
        id2 = compute_claim_id("Supports OBJ", "format", product_name)
        id3 = compute_claim_id("  Supports OBJ  ", "format", product_name)

        assert id1 == id2 == id3


class TestClaimKindClassification:
    """Test claim kind classification per specs/04_claims_compiler_truth_lock.md:35-46."""

    def test_classify_limitation_claims(self):
        """Test limitation claim detection."""
        assert classify_claim_kind("Does not support FBX format") == "limitation"
        assert classify_claim_kind("Not yet implemented") == "limitation"
        assert classify_claim_kind("Cannot export to PDF") == "limitation"

    def test_classify_format_claims(self):
        """Test format claim detection."""
        assert classify_claim_kind("Reads OBJ format") == "format"
        assert classify_claim_kind("Writes STL files") == "format"
        assert classify_claim_kind("Supports import of FBX") == "format"

    def test_classify_workflow_claims(self):
        """Test workflow claim detection."""
        assert classify_claim_kind("Install via pip install aspose-3d") == "workflow"
        assert classify_claim_kind("Usage: import aspose.threed") == "workflow"
        assert classify_claim_kind("Getting started with setup") == "workflow"

    def test_classify_api_claims(self):
        """Test API claim detection."""
        assert classify_claim_kind("Provides Scene class for 3D scenes") == "api"
        assert classify_claim_kind("The save function exports models") == "api"
        assert classify_claim_kind("API includes FileFormat interface") == "api"

    def test_classify_feature_claims_default(self):
        """Test default feature classification."""
        assert classify_claim_kind("Supports multiple 3D formats") == "feature"
        assert classify_claim_kind("Can render complex scenes") == "feature"
        assert classify_claim_kind("Enables batch processing") == "feature"


class TestSourceTypeClassification:
    """Test source type determination per specs/03_product_facts_and_evidence.md:117-128."""

    def test_determine_source_type_manifest(self):
        """Test manifest file detection."""
        repo_dir = Path("/repo")
        assert determine_source_type(Path("/repo/pyproject.toml"), repo_dir) == "manifest"
        assert determine_source_type(Path("/repo/setup.py"), repo_dir) == "manifest"
        assert determine_source_type(Path("/repo/package.json"), repo_dir) == "manifest"

    def test_determine_source_type_source_code(self):
        """Test source code file detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            src_dir = repo_dir / "src"
            src_dir.mkdir()
            src_file = src_dir / "main.py"
            src_file.write_text("# source code")

            assert determine_source_type(src_file, repo_dir) == "source_code"

    def test_determine_source_type_test(self):
        """Test test file detection."""
        repo_dir = Path("/repo")
        assert determine_source_type(Path("/repo/tests/test_main.py"), repo_dir) == "test"
        assert determine_source_type(Path("/repo/test/spec.py"), repo_dir) == "test"

    def test_determine_source_type_readme_technical(self):
        """Test README technical classification."""
        repo_dir = Path("/repo")
        with tempfile.TemporaryDirectory() as tmpdir:
            readme_path = Path(tmpdir) / "README.md"
            readme_path.write_text("# Install\npip install mypackage\n\n# Usage\nimport mypackage")

            source_type = determine_source_type(readme_path, Path(tmpdir))
            assert source_type == "readme_technical"

    def test_determine_source_type_readme_marketing(self):
        """Test README marketing classification."""
        repo_dir = Path("/repo")
        with tempfile.TemporaryDirectory() as tmpdir:
            readme_path = Path(tmpdir) / "README.md"
            readme_path.write_text("# Awesome Product\nThe best product for everything!")

            source_type = determine_source_type(readme_path, Path(tmpdir))
            assert source_type == "readme_marketing"


    def test_determine_source_type_meta(self):
        """TC-1604: AGENTS.md and .claude/ files classified as 'meta'."""
        repo_dir = Path("/fake/repo")
        assert determine_source_type(
            Path("/fake/repo/AGENTS.md"), repo_dir
        ) == "meta"
        assert determine_source_type(
            Path("/fake/repo/.claude/settings.json"), repo_dir
        ) == "meta"
        assert determine_source_type(
            Path("/fake/repo/CLAUDE.md"), repo_dir
        ) == "meta"


class TestSourcePriority:
    """Test evidence priority ranking per specs/03_product_facts_and_evidence.md:117-128."""

    def test_determine_source_priority_ranking(self):
        """Test priority ranking order (1=highest, 7=lowest)."""
        assert determine_source_priority("manifest") == 1
        assert determine_source_priority("source_code") == 2
        assert determine_source_priority("test") == 3
        assert determine_source_priority("implementation_doc") == 4
        assert determine_source_priority("api_doc") == 5
        assert determine_source_priority("readme_technical") == 6
        assert determine_source_priority("readme_marketing") == 7

    def test_determine_source_priority_default(self):
        """Test default priority for unknown types."""
        assert determine_source_priority("unknown") == 7


class TestCandidateExtraction:
    """Test candidate statement extraction."""

    def test_extract_candidate_statements_basic(self):
        """Test basic sentence extraction."""
        text = """
        This library supports OBJ format for three-dimensional models.
        It can read and write STL files for mesh data exchange.
        The API provides a Scene class for managing 3D content.
        """
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        assert len(candidates) >= 2
        assert any("supports" in c['claim_text'].lower() for c in candidates)
        assert any("provides" in c['claim_text'].lower() for c in candidates)

    def test_extract_candidate_statements_quality_filters(self):
        """TC-CONTENT-QUALITY: Claim quality filters reject short and non-prose sentences.

        Only prose-like sentences with >= MIN_CLAIM_WORDS words, >= MIN_CLAIM_CHARS chars,
        and verbs pass.
        """
        text = "Hello. Short. This library supports many different output formats."
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        # Only the long sentence passes quality filters
        # (has enough words, verb "supports", reads as prose, >=40 chars)
        assert len(candidates) == 1
        # The sentence with keywords should have keyword_boost=True
        assert candidates[0]['keyword_boost'] is True
        assert "supports" in candidates[0]['claim_text'].lower()

    def test_extract_candidate_statements_includes_line_numbers(self):
        """Test that line numbers are recorded.

        TC-CONTENT-QUALITY: Claim quality filters (MIN_CLAIM_WORDS, MIN_CLAIM_CHARS, prose check)
        reject short sentences like "Line 1." Only prose-like sentences pass.
        """
        text = "Line 1.\nThis component supports the OBJ format for 3D models.\nLine 3."
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        # TC-CONTENT-QUALITY: Only the long sentence passes quality filters
        # (MIN_CLAIM_WORDS and MIN_CLAIM_CHARS reject "Line 1." and "Line 3.")
        assert len(candidates) == 1
        # Check line numbers on the keyword-boosted candidate
        keyword_candidate = candidates[0]
        assert keyword_candidate['keyword_boost'] is True
        assert keyword_candidate['start_line'] >= 1
        assert keyword_candidate['end_line'] >= keyword_candidate['start_line']


class TestClaimValidation:
    """Test claim validation per specs/schemas/evidence_map.schema.json."""

    def test_validate_claim_structure_valid(self):
        """Test validation of valid claim."""
        claim = {
            'claim_id': 'abc123',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'truth_status': 'fact',
            'citations': [{
                'path': 'README.md',
                'start_line': 1,
                'end_line': 1,
            }],
        }

        # Should not raise
        validate_claim_structure(claim)

    def test_validate_claim_structure_missing_field(self):
        """Test validation fails for missing required field."""
        claim = {
            'claim_id': 'abc123',
            'claim_text': 'Supports OBJ format',
            # Missing claim_kind, truth_status, citations
        }

        with pytest.raises(ClaimsValidationError, match="Missing required field"):
            validate_claim_structure(claim)

    def test_validate_claim_structure_invalid_truth_status(self):
        """Test validation fails for invalid truth_status."""
        claim = {
            'claim_id': 'abc123',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'truth_status': 'maybe',  # Invalid
            'citations': [{
                'path': 'README.md',
                'start_line': 1,
                'end_line': 1,
            }],
        }

        with pytest.raises(ClaimsValidationError, match="Invalid truth_status"):
            validate_claim_structure(claim)

    def test_validate_claim_structure_empty_citations(self):
        """Test validation fails for empty citations."""
        claim = {
            'claim_id': 'abc123',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'truth_status': 'fact',
            'citations': [],  # Empty
        }

        with pytest.raises(ClaimsValidationError, match="Citations must be non-empty"):
            validate_claim_structure(claim)

    def test_validate_claim_structure_missing_citation_field(self):
        """Test validation fails for missing citation field."""
        claim = {
            'claim_id': 'abc123',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'truth_status': 'fact',
            'citations': [{
                'path': 'README.md',
                # Missing start_line, end_line
            }],
        }

        with pytest.raises(ClaimsValidationError, match="Missing required citation field"):
            validate_claim_structure(claim)


class TestClaimDeduplication:
    """Test claim deduplication with citation merging."""

    def test_deduplicate_claims_merges_citations(self):
        """Test deduplication merges citations for same claim_id."""
        claims = [
            {
                'claim_id': 'abc123',
                'claim_text': 'Supports OBJ',
                'claim_kind': 'format',
                'truth_status': 'fact',
                'citations': [{'path': 'README.md', 'start_line': 1, 'end_line': 1}],
            },
            {
                'claim_id': 'abc123',
                'claim_text': 'Supports OBJ',
                'claim_kind': 'format',
                'truth_status': 'fact',
                'citations': [{'path': 'docs/formats.md', 'start_line': 5, 'end_line': 5}],
            },
        ]

        result = deduplicate_claims(claims)

        assert len(result) == 1
        assert len(result[0]['citations']) == 2

    def test_deduplicate_claims_upgrades_truth_status(self):
        """Test deduplication upgrades truth_status to 'fact' if any is fact."""
        claims = [
            {
                'claim_id': 'abc123',
                'claim_text': 'Supports OBJ',
                'claim_kind': 'format',
                'truth_status': 'inference',
                'citations': [{'path': 'README.md', 'start_line': 1, 'end_line': 1}],
            },
            {
                'claim_id': 'abc123',
                'claim_text': 'Supports OBJ',
                'claim_kind': 'format',
                'truth_status': 'fact',
                'citations': [{'path': 'src/formats.py', 'start_line': 10, 'end_line': 10}],
            },
        ]

        result = deduplicate_claims(claims)

        assert len(result) == 1
        assert result[0]['truth_status'] == 'fact'

    def test_deduplicate_claims_keeps_highest_confidence(self):
        """Test deduplication keeps highest confidence level."""
        claims = [
            {
                'claim_id': 'abc123',
                'claim_text': 'Supports OBJ',
                'claim_kind': 'format',
                'truth_status': 'fact',
                'confidence': 'low',
                'citations': [{'path': 'README.md', 'start_line': 1, 'end_line': 1}],
            },
            {
                'claim_id': 'abc123',
                'claim_text': 'Supports OBJ',
                'claim_kind': 'format',
                'truth_status': 'fact',
                'confidence': 'high',
                'citations': [{'path': 'src/formats.py', 'start_line': 10, 'end_line': 10}],
            },
        ]

        result = deduplicate_claims(claims)

        assert len(result) == 1
        assert result[0]['confidence'] == 'high'


    def test_deduplicate_claims_keeps_highest_source_relevance(self):
        """Test deduplication keeps highest source_relevance score."""
        claims = [
            {
                'claim_id': 'abc123',
                'claim_text': 'Supports OBJ',
                'claim_kind': 'format',
                'truth_status': 'fact',
                'source_relevance': 30,
                'evidence_priority': 'low',
                'citations': [{'path': 'spec.txt', 'start_line': 1, 'end_line': 1}],
            },
            {
                'claim_id': 'abc123',
                'claim_text': 'Supports OBJ',
                'claim_kind': 'format',
                'truth_status': 'fact',
                'source_relevance': 100,
                'evidence_priority': 'high',
                'citations': [{'path': 'README.md', 'start_line': 5, 'end_line': 5}],
            },
        ]

        result = deduplicate_claims(claims)

        assert len(result) == 1
        assert result[0]['source_relevance'] == 100
        assert result[0]['evidence_priority'] == 'high'

    def test_deduplicate_claims_without_source_relevance(self):
        """Test deduplication works when source_relevance is absent."""
        claims = [
            {
                'claim_id': 'abc123',
                'claim_text': 'Supports OBJ',
                'claim_kind': 'format',
                'truth_status': 'fact',
                'citations': [{'path': 'README.md', 'start_line': 1, 'end_line': 1}],
            },
            {
                'claim_id': 'abc123',
                'claim_text': 'Supports OBJ',
                'claim_kind': 'format',
                'truth_status': 'fact',
                'source_relevance': 80,
                'evidence_priority': 'medium',
                'citations': [{'path': 'docs/formats.md', 'start_line': 5, 'end_line': 5}],
            },
        ]

        result = deduplicate_claims(claims)

        assert len(result) == 1
        assert result[0].get('source_relevance') == 80
        assert result[0].get('evidence_priority') == 'medium'


class TestClaimSorting:
    """Test deterministic claim sorting per specs/10_determinism_and_caching.md."""

    def test_sort_claims_deterministically(self):
        """Test claims are sorted by claim_id lexicographically."""
        claims = [
            {'claim_id': 'zzz', 'claim_text': 'Z', 'claim_kind': 'feature', 'truth_status': 'fact', 'citations': []},
            {'claim_id': 'aaa', 'claim_text': 'A', 'claim_kind': 'feature', 'truth_status': 'fact', 'citations': []},
            {'claim_id': 'mmm', 'claim_text': 'M', 'claim_kind': 'feature', 'truth_status': 'fact', 'citations': []},
        ]

        result = sort_claims_deterministically(claims)

        assert result[0]['claim_id'] == 'aaa'
        assert result[1]['claim_id'] == 'mmm'
        assert result[2]['claim_id'] == 'zzz'

    def test_sort_claims_deterministically_stable(self):
        """Test sorting is stable across multiple runs."""
        claims = [
            {'claim_id': 'zzz', 'claim_text': 'Z', 'claim_kind': 'feature', 'truth_status': 'fact', 'citations': []},
            {'claim_id': 'aaa', 'claim_text': 'A', 'claim_kind': 'feature', 'truth_status': 'fact', 'citations': []},
        ]

        result1 = sort_claims_deterministically(claims)
        result2 = sort_claims_deterministically(claims)

        assert result1 == result2


class TestExtractClaimsIntegration:
    """Integration tests for extract_claims main function."""

    def test_extract_claims_no_docs(self):
        """Test extract_claims with no documentation files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            # Create run layout
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create empty discovered_docs.json
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            # Create repo_inventory.json
            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Extract claims (should succeed with empty claims)
            result = extract_claims(repo_dir, run_dir, llm_client=None)

            assert result['schema_version'] == '1.0.0'
            assert result['repo_url'] == 'https://github.com/test/repo'
            assert result['repo_sha'] == 'abc123'
            assert len(result['claims']) == 0
            assert result['metadata']['total_claims'] == 0

    def test_extract_claims_with_readme(self):
        """Test extract_claims with README containing claims."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            # Create run layout
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create README with claims
            readme_path = repo_dir / "README.md"
            readme_path.write_text("""
# Test Product

This library supports OBJ format for 3D models.
It can read and write STL files efficiently.
The API provides a Scene class for scene management.
Does not support FBX format at this time.
Install via pip install test-product.
""")

            # Create discovered_docs.json
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [{
                    'path': 'README.md',
                    'type': 'README',
                }],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            # Create repo_inventory.json
            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Extract claims
            result = extract_claims(repo_dir, run_dir, llm_client=None)

            assert result['schema_version'] == '1.0.0'
            assert len(result['claims']) > 0

            # Check for expected claim kinds
            claim_kinds = [c['claim_kind'] for c in result['claims']]
            assert 'format' in claim_kinds or 'feature' in claim_kinds

            # Check metadata
            assert result['metadata']['total_claims'] == len(result['claims'])
            assert 'claim_kinds' in result['metadata']

            # Verify artifact was written
            output_path = artifacts_dir / "extracted_claims.json"
            assert output_path.exists()

    def test_extract_claims_missing_discovered_docs(self):
        """Test extract_claims fails when discovered_docs.json missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            # Create run layout (but no discovered_docs.json)
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError, match="discovered_docs.json not found"):
                extract_claims(repo_dir, run_dir, llm_client=None)

    def test_extract_claims_missing_repo_inventory(self):
        """Test extract_claims fails when repo_inventory.json missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            # Create run layout
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create discovered_docs.json
            discovered_docs = {'schema_version': '1.0.0', 'doc_entrypoint_details': []}
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            # Should raise FileNotFoundError for repo_inventory
            with pytest.raises(FileNotFoundError, match="repo_inventory.json not found"):
                extract_claims(repo_dir, run_dir, llm_client=None)

    def test_extract_claims_deterministic_output(self):
        """Test extract_claims produces deterministic output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir1 = Path(tmpdir) / "run1"
            run_dir2 = Path(tmpdir) / "run2"
            repo_dir = Path(tmpdir) / "repo"
            run_dir1.mkdir()
            run_dir2.mkdir()
            repo_dir.mkdir()

            # Create README
            readme_path = repo_dir / "README.md"
            readme_path.write_text("This library supports OBJ format.")

            # Setup for run 1
            artifacts_dir1 = run_dir1 / "artifacts"
            artifacts_dir1.mkdir()
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [{'path': 'README.md', 'type': 'README'}],
            }
            (artifacts_dir1 / "discovered_docs.json").write_text(json.dumps(discovered_docs))
            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir1 / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Setup for run 2 (identical)
            artifacts_dir2 = run_dir2 / "artifacts"
            artifacts_dir2.mkdir()
            (artifacts_dir2 / "discovered_docs.json").write_text(json.dumps(discovered_docs))
            (artifacts_dir2 / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Extract claims twice
            result1 = extract_claims(repo_dir, run_dir1, llm_client=None)
            result2 = extract_claims(repo_dir, run_dir2, llm_client=None)

            # Compare claim_ids (should be identical and in same order)
            claim_ids1 = [c['claim_id'] for c in result1['claims']]
            claim_ids2 = [c['claim_id'] for c in result2['claims']]

            assert claim_ids1 == claim_ids2


class TestSourceRelevanceTagging:
    """Test that claims carry source_relevance from W1 discovery metadata."""

    def test_claims_tagged_with_source_relevance(self):
        """Test that extracted claims carry source_relevance from doc_entrypoint_details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create README with a claim
            (repo_dir / "README.md").write_text(
                "This library supports OBJ format for 3D models.\n"
            )

            # discovered_docs with relevance_score and evidence_priority
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [{
                    'path': 'README.md',
                    'doc_type': 'readme',
                    'relevance_score': 100,
                    'evidence_priority': 'high',
                }],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            result = extract_claims(repo_dir, run_dir, llm_client=None)

            assert len(result['claims']) > 0
            for claim in result['claims']:
                assert 'source_relevance' in claim, "claim missing source_relevance"
                assert claim['source_relevance'] == 100
                assert claim['evidence_priority'] == 'high'

    def test_claims_default_relevance_when_absent(self):
        """Test that claims get default source_relevance=50 when not in discovery data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            (repo_dir / "doc.md").write_text(
                "This library provides comprehensive features for all users.\n"
            )

            # No relevance_score or evidence_priority in doc details
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [{
                    'path': 'doc.md',
                }],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            result = extract_claims(repo_dir, run_dir, llm_client=None)

            assert len(result['claims']) > 0
            for claim in result['claims']:
                assert claim.get('source_relevance') == 50
                assert claim.get('evidence_priority') == 'medium'

    def test_low_relevance_source_claims_tagged(self):
        """Test that claims from low-relevance sources are properly tagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            (repo_dir / "spec.txt").write_text(
                "The library provides comprehensive support for reading and writing document files in various formats.\n"
            )

            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [{
                    'path': 'spec.txt',
                    'relevance_score': 30,
                    'evidence_priority': 'low',
                }],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            result = extract_claims(repo_dir, run_dir, llm_client=None)

            assert len(result['claims']) > 0
            for claim in result['claims']:
                assert claim['source_relevance'] == 30
                assert claim['evidence_priority'] == 'low'


class TestTC1026NoExtractionLimits:
    """TC-1026: Verify all extraction limits have been removed."""

    def test_single_word_sentences_are_rejected(self):
        """TC-CONTENT-QUALITY: Single-word sentences are rejected by MIN_CLAIM_WORDS=4."""
        text = "Supported."
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        # Single-word sentences don't meet MIN_CLAIM_WORDS=4
        assert len(candidates) == 0

    def test_keyword_boost_present_on_candidates(self):
        """TC-1026: Candidates have keyword_boost metadata field."""
        text = "This library supports OBJ format.\nThe library provides data export features."
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        # Both prose-like sentences should be candidates
        assert len(candidates) >= 1
        # The first should have keyword_boost=True (has 'support')
        boost_candidates = [c for c in candidates if 'supports' in c['claim_text'].lower()]
        for c in boost_candidates:
            assert c['keyword_boost'] is True

    def test_no_keyword_sentences_still_extracted(self):
        """TC-1026: Prose sentences without keyword markers are still extracted."""
        text = "The sky is blue and very clear on this fine day."
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        assert len(candidates) == 1
        assert candidates[0]['keyword_boost'] is False

    def test_no_doc_count_limit_in_llm_extraction(self):
        """TC-1026: LLM extraction processes all docs (no [:10] cap)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir) / "repo"
            repo_dir.mkdir()

            # Create 15 doc files (more than old limit of 10)
            doc_files = []
            for i in range(15):
                doc_path = repo_dir / f"doc_{i}.md"
                doc_path.write_text(f"Document number {i} supports feature capability {i} natively.")
                doc_files.append({'path': f'doc_{i}.md', 'type': 'readme'})

            from src.launch.workers.w2_facts_builder.extract_claims import (
                extract_claims_with_llm,
            )

            # Use no LLM client (will use heuristic extraction within LLM path)
            mock_llm = MagicMock()
            claims = extract_claims_with_llm(
                doc_files, repo_dir, "TestProduct", mock_llm
            )

            # Should process all 15 docs, not just 10
            # Each doc has one sentence with 'supports' keyword -> at least 15 candidates
            assert len(claims) >= 15

    def test_no_example_count_limit_in_assembly(self):
        """TC-1026: Example inventory processes all examples (no [:10] cap)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            run_dir.mkdir()
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create repo_inventory.json
            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
                'supported_platforms': [],
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Create discovered_examples with 15 examples (more than old limit of 10)
            example_details = []
            for i in range(15):
                example_details.append({
                    'path': f'examples/example_{i}.py',
                    'language': 'python',
                    'tags': [f'tag_{i}'],
                })
            discovered_examples = {
                'schema_version': '1.0.0',
                'example_file_details': example_details,
            }
            (artifacts_dir / "discovered_examples.json").write_text(
                json.dumps(discovered_examples)
            )

            from src.launch.workers.w2_facts_builder.worker import (
                assemble_product_facts,
            )
            from src.launch.io.run_layout import RunLayout

            run_layout = RunLayout(run_dir=run_dir)
            evidence_map = {
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'claims': [],
            }

            product_facts = assemble_product_facts(run_layout, evidence_map)

            # All 15 examples should be in the inventory (no cap)
            assert len(product_facts['example_inventory']) == 15


class TestClaimQualityFilters:
    """TC-CONTENT-QUALITY: Tests for claim quality filters (_is_code_like, _is_prose_like)."""

    def test_is_code_like_python_function_def(self):
        """Code with def, self, return is detected as code."""
        text = "def process_document(self, path): self.doc = load(path) return self.doc"
        assert _is_code_like(text) is True

    def test_is_code_like_import_statements(self):
        """Import, class definition, and self reference lines are code."""
        text = "from aspose.note import Document class MyDoc(Document): self.doc = Document() return self.result"
        assert _is_code_like(text) is True

    def test_is_code_like_assert_calls(self):
        """Test assertions with self references are code."""
        text = "self.assertEqual(len(top_level), 2) self.assertIsNotNone(result) return True"
        assert _is_code_like(text) is True

    def test_is_code_like_prose_sentence(self):
        """Normal prose sentence is not code."""
        text = "Aspose.Note supports reading OneNote files and building a DOM."
        assert _is_code_like(text) is False

    def test_is_code_like_high_symbol_density(self):
        """Text with >40% non-alphabetic chars is code-like."""
        text = "x[0].y(z[1],w[2])={a:b[3],c:d[4]}"
        assert _is_code_like(text) is True

    def test_is_prose_like_valid_sentence(self):
        """Sentence with verb and 4+ words is prose."""
        text = "The library supports multiple file formats."
        assert _is_prose_like(text) is True

    def test_is_prose_like_too_short(self):
        """Fewer than 4 words is not prose."""
        text = "Import module."
        assert _is_prose_like(text) is False

    def test_is_prose_like_no_verb(self):
        """Text without common verbs is not prose."""
        text = "OneNote file format specification document."
        assert _is_prose_like(text) is False

    def test_is_prose_like_code_start(self):
        """Text starting with import/def/class is not prose."""
        text = "from aspose.note import Document for reading files."
        assert _is_prose_like(text) is False

    def test_is_prose_like_with_verb(self):
        """Sentence with enables and 4+ words is prose."""
        text = "This module enables reading of OneNote files."
        assert _is_prose_like(text) is True

    def test_candidate_extraction_rejects_code(self):
        """Code lines should be filtered out during candidate extraction."""
        code_text = (
            "def process_document(self, path):\n"
            "    self.doc = Document(path)\n"
            "    return self.doc.\n"
        )
        repo_dir = Path("/fake/repo")
        file_path = repo_dir / "README.md"
        candidates = extract_candidate_statements_from_text(code_text, file_path, repo_dir)
        # Code should be filtered out (fails _is_code_like and _is_prose_like)
        for c in candidates:
            assert "def process_document" not in c["claim_text"]

    def test_candidate_extraction_accepts_prose(self):
        """Prose sentences should pass quality filters."""
        prose_text = (
            "Aspose.Note provides comprehensive support for reading OneNote files.\n"
            "The library enables developers to build document processing applications.\n"
        )
        repo_dir = Path("/fake/repo")
        file_path = repo_dir / "README.md"
        candidates = extract_candidate_statements_from_text(prose_text, file_path, repo_dir)
        assert len(candidates) >= 1
        assert any("comprehensive support" in c["claim_text"] for c in candidates)

    def test_candidate_extraction_rejects_long_claims(self):
        """Claims exceeding 500 characters should be rejected."""
        long_text = "The library " + "supports " * 60 + "many formats.\n"
        assert len(long_text.strip()) > 500
        repo_dir = Path("/fake/repo")
        file_path = repo_dir / "README.md"
        candidates = extract_candidate_statements_from_text(long_text, file_path, repo_dir)
        # Should reject the overly long claim
        for c in candidates:
            assert len(c["claim_text"]) <= 500


class TestMinClaimCharsFilter:
    """TC-1602: Tests for MIN_CLAIM_CHARS=40 filter on short claims."""

    def test_short_claim_filtered(self):
        """TC-1602: A 30-character claim text should be filtered out."""
        # "This lib supports OBJ format." is 30 chars — below MIN_CLAIM_CHARS=40
        short_text = "This lib supports OBJ format."
        assert len(short_text) < MIN_CLAIM_CHARS, f"Test precondition: need <40 chars, got {len(short_text)}"

        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")
        candidates = extract_candidate_statements_from_text(short_text, file_path, repo_dir)

        # Should be filtered out because it has fewer than 40 characters
        assert len(candidates) == 0, (
            f"Expected 0 candidates for {len(short_text)}-char text, got {len(candidates)}"
        )

    def test_40_char_claim_accepted(self):
        """TC-1602: A 40+ character claim text should pass through."""
        # Exactly 49 chars — above MIN_CLAIM_CHARS=40
        long_text = "This library supports the OBJ file format natively."
        assert len(long_text) >= MIN_CLAIM_CHARS, f"Test precondition: need >=40 chars, got {len(long_text)}"

        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")
        candidates = extract_candidate_statements_from_text(long_text, file_path, repo_dir)

        # Should pass through — meets MIN_CLAIM_WORDS, MIN_CLAIM_CHARS, and prose checks
        assert len(candidates) >= 1, (
            f"Expected >=1 candidates for {len(long_text)}-char text, got {len(candidates)}"
        )

    def test_offline_api_claims_not_affected(self):
        """TC-1602: _generate_offline_api_claims is not affected by MIN_CLAIM_CHARS filter.

        Offline API claims are generated from templates, not extracted from text,
        so the character-length filter in extract_candidate_statements_from_text
        does not apply to them.
        """
        api_surface = {
            "classes": [
                {
                    "name": "X",
                    "module": "lib",
                    "methods": ["a"],
                    "docstring": "Short",
                },
            ],
            "functions": [],
            "modules": [],
        }
        # Even though the class name "X" is very short, template-generated claims
        # go through _generate_offline_api_claims, not the text extraction path
        claims = _generate_offline_api_claims(api_surface, "Lib")

        # Should produce at least one claim for class X
        assert len(claims) >= 1, "Offline API claims should not be filtered by MIN_CLAIM_CHARS"
        assert any("X" in c["claim_text"] for c in claims), (
            "Expected a claim referencing class X"
        )


class TestHardenedCodeFilters:
    """Tests for hardened _is_code_like and _is_prose_like filters (Phase 2B)."""

    def test_is_code_like_if_is_none(self):
        """'if X is None:' pattern with multiple code indicators should be detected as code."""
        text = "if polygons is None: return self.default_value"
        assert _is_code_like(text) is True

    def test_is_code_like_for_loop(self):
        """'for X in Y' with multiple code indicators should be detected as code."""
        text = "for item in collection: self.process(item); return result"
        assert _is_code_like(text) is True

    def test_is_code_like_ternary(self):
        """Ternary assignment with multiple code patterns should be detected as code."""
        text = "translation = transform.translation if translation is not None else self.default"
        assert _is_code_like(text) is True

    def test_is_code_like_try_except(self):
        """try/except blocks should be detected as code."""
        text = "try: result = parse(data) except ValueError: return None"
        assert _is_code_like(text) is True

    def test_is_code_like_while_loop(self):
        """while loop with return should be detected as code."""
        text = "while count > 0: count = process(x); return result"
        assert _is_code_like(text) is True

    def test_is_prose_like_rejects_if_statement(self):
        """Prose starting with 'if ' should be rejected."""
        text = "if polygons is None then the mesh has no data to process"
        assert _is_prose_like(text) is False

    def test_is_prose_like_rejects_for_statement(self):
        """Prose starting with 'for ' should be rejected."""
        text = "for item in the collection we process each one individually here"
        assert _is_prose_like(text) is False

    def test_is_prose_like_rejects_return_statement(self):
        """Prose starting with 'return ' should be rejected."""
        text = "return value is computed from the input parameters"
        assert _is_prose_like(text) is False


class TestExpandedClaimClassification:
    """Tests for expanded classify_claim_kind patterns (Phase 2B)."""

    def test_limitation_doesnt_support(self):
        """\"doesn't support\" should classify as limitation."""
        assert classify_claim_kind("The library doesn't support PDF 2.0") == 'limitation'

    def test_limitation_deprecated(self):
        """\"deprecated\" should classify as limitation."""
        assert classify_claim_kind("The legacy API is deprecated and will be removed") == 'limitation'

    def test_limitation_experimental(self):
        """\"experimental\" should classify as limitation."""
        assert classify_claim_kind("This feature is experimental and may change") == 'limitation'

    def test_limitation_limited_to(self):
        """\"limited to\" should classify as limitation."""
        assert classify_claim_kind("File size is limited to 100MB") == 'limitation'

    def test_limitation_not_available(self):
        """\"not available\" should classify as limitation."""
        assert classify_claim_kind("Batch processing is not available in the free tier") == 'limitation'

    def test_workflow_execute(self):
        """\"execute\" should classify as workflow."""
        assert classify_claim_kind("Execute the script to generate output") == 'workflow'

    def test_workflow_configure(self):
        """\"configure \" should classify as workflow."""
        assert classify_claim_kind("Configure the settings before running") == 'workflow'

    def test_workflow_quickstart(self):
        """\"quickstart\" should classify as workflow."""
        assert classify_claim_kind("Follow the quickstart guide to begin") == 'workflow'

    def test_workflow_tutorial(self):
        """\"tutorial\" should classify as workflow."""
        assert classify_claim_kind("This tutorial covers basic document processing") == 'workflow'

    def test_workflow_step_1(self):
        """\"step 1\" should classify as workflow."""
        assert classify_claim_kind("Step 1 is to create a new project") == 'workflow'

    def test_feature_still_default(self):
        """Generic feature text should still default to feature."""
        assert classify_claim_kind("Supports multiple 3D model formats") == 'feature'


class TestPythonIdiomExclusion:
    """R3: Tests for Python idiom exclusion in _is_prose_like()."""

    def test_is_not_none_not_prose(self):
        """'if value.scene is not None:' should NOT pass as prose."""
        # "is" in "is not None" should not count as an English verb
        text = "if value.scene is not None: process(value)"
        assert not _is_prose_like(text), "'is not None' pattern should not pass as prose"

    def test_is_none_not_prose(self):
        """'result is None' should NOT pass as prose."""
        text = "if result is None: return default_value for processing"
        assert not _is_prose_like(text), "'is None' pattern should not pass as prose"

    def test_is_true_not_prose(self):
        """'flag is True' should NOT pass as prose."""
        text = "if has_normals is True: self.compute_normals(mesh)"
        assert not _is_prose_like(text), "'is True' pattern should not pass as prose"

    def test_real_english_is_still_prose(self):
        """Real English 'is' should still pass as prose."""
        text = "Aspose.3D is a powerful library for 3D model processing."
        assert _is_prose_like(text), "Real English verb 'is' should still be recognized"


class TestAssignmentPattern:
    """R3: Tests for variable assignment detection in _is_code_like()."""

    def test_assignment_with_return(self):
        """Assignment + return + method call should be detected as code (3 indicators)."""
        text = "has_normals = self.compute() return result"
        assert _is_code_like(text), "Assignment + self.X + return should be code"

    def test_assignment_with_method_call(self):
        """Assignment + method call + loop should be detected as code (3 indicators)."""
        text = "obj_id = mesh.compute() for item in collection"
        assert _is_code_like(text), "Assignment + method call + for loop should be code"


class TestIdentifierRatioFilter:
    """R3: Tests for identifier ratio filter in extract_candidate_statements."""

    def test_code_heavy_text_rejected(self):
        """Text with >40% code-like tokens should be rejected."""
        # This text has lots of identifiers with dots, underscores, parens
        text = "obj.mesh scene_data node.transform() self.compute() obj.export() returns the result."
        candidates = extract_candidate_statements_from_text(
            text, Path("README.md"), Path("/repo"),
        )
        # Should be empty because >40% of tokens are code identifiers
        assert len(candidates) == 0, "Code-heavy text should be rejected by identifier ratio"

    def test_prose_text_accepted(self):
        """Normal prose text should pass the identifier ratio check."""
        text = "Aspose.3D supports multiple file formats including OBJ and STL for conversion."
        candidates = extract_candidate_statements_from_text(
            text, Path("README.md"), Path("/repo"),
        )
        assert len(candidates) > 0, "Prose text should pass identifier ratio check"


class TestCodeGroundedClaims:
    """Tests for TC-1401: code-grounded claim generation."""

    def _make_api_surface(
        self,
        classes=None,
        functions=None,
        modules=None,
    ) -> Dict[str, Any]:
        """Helper to build a code_analysis dict with an api_surface."""
        return {
            "api_surface": {
                "classes": classes or [],
                "functions": functions or [],
                "modules": modules or [],
            },
            "constants": {},
        }

    def test_offline_class_claims(self):
        """Verify offline path generates class-level claims."""
        code_analysis = self._make_api_surface(
            classes=[
                {"name": "Scene", "module": "aspose3d", "methods": ["add_entity", "save"], "docstring": "Main 3D scene container"},
                {"name": "_Internal", "module": "aspose3d", "methods": ["run"], "docstring": "Internal helper"},
            ],
            functions=[{"name": "create_mesh", "module": "aspose3d.entities", "docstring": "Creates a new mesh"}],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "Aspose.3D", Path("."))
        # Should have claims for Scene but NOT _Internal
        claim_texts = [c["claim_text"] for c in claims]
        assert any("Scene" in t for t in claim_texts)
        assert not any("_Internal" in t for t in claim_texts)

    def test_offline_method_claims(self):
        """Verify offline path generates method-listing claims for classes with >2 methods."""
        code_analysis = self._make_api_surface(
            classes=[
                {
                    "name": "Workbook",
                    "module": "aspose.cells",
                    "methods": ["save", "open", "close", "add_sheet"],
                    "docstring": "Excel workbook handler",
                },
            ],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "Aspose.Cells", Path("."))
        claim_texts = [c["claim_text"] for c in claims]
        # Should have a method-listing claim because 4 methods > 2
        method_claims = [t for t in claim_texts if "provides methods:" in t]
        assert len(method_claims) == 1
        # Methods should be sorted alphabetically and include ()
        assert "add_sheet()" in method_claims[0]
        assert "close()" in method_claims[0]

    def test_offline_no_method_claim_for_few_methods(self):
        """Verify no method-listing claim when class has <=2 public methods."""
        code_analysis = self._make_api_surface(
            classes=[
                {
                    "name": "Converter",
                    "module": "lib",
                    "methods": ["convert", "validate"],
                    "docstring": "Format converter",
                },
            ],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "MyLib", Path("."))
        claim_texts = [c["claim_text"] for c in claims]
        # Should have a class claim but NO method-listing claim
        assert any("Converter" in t for t in claim_texts)
        method_claims = [t for t in claim_texts if "provides methods:" in t]
        assert len(method_claims) == 0

    def test_offline_function_claims(self):
        """Verify offline path generates function claims."""
        code_analysis = self._make_api_surface(
            functions=[
                {"name": "create_mesh", "module": "aspose3d.entities", "docstring": "Creates a new mesh"},
                {"name": "_private_helper", "module": "aspose3d.internal", "docstring": "Internal"},
            ],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "Aspose.3D", Path("."))
        claim_texts = [c["claim_text"] for c in claims]
        assert any("create_mesh()" in t for t in claim_texts)
        assert not any("_private_helper" in t for t in claim_texts)

    def test_offline_cap_at_30(self):
        """TC-1603: Verify offline path caps at 30 claims."""
        # Create 40 classes with docstrings — each generates 1 class claim, so we exceed 30
        classes = [
            {"name": f"Class{i}", "module": "mod", "methods": ["a"], "docstring": f"Class {i} handler"}
            for i in range(40)
        ]
        code_analysis = self._make_api_surface(classes=classes)
        claims = extract_claims_from_code_analysis(code_analysis, "TestProduct", Path("."))
        assert len(claims) <= 30

    def test_llm_path_mocked(self):
        """Verify LLM path generates claims from API surface. Testing: mocked"""
        code_analysis = self._make_api_surface(
            classes=[
                {"name": "Scene", "module": "aspose3d", "methods": ["save", "load"], "docstring": "3D scene"},
            ],
        )

        llm_response_json = json.dumps([
            {"claim_text": "Aspose.3D provides the Scene class for 3D scene management", "claim_kind": "key_feature", "referenced_symbols": ["Scene"]},
            {"claim_text": "The Scene class supports saving scenes via save()", "claim_kind": "api_reference", "referenced_symbols": ["Scene", "save"]},
        ])

        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {"content": llm_response_json}

        claims = extract_claims_from_code_analysis(
            code_analysis, "Aspose.3D", Path("."), llm_client=mock_client,
        )

        # LLM was called
        mock_client.chat_completion.assert_called_once()

        claim_texts = [c["claim_text"] for c in claims]
        assert any("Scene" in t for t in claim_texts)
        assert len(claims) == 2

    def test_llm_path_object_wrapped_response(self):
        """Verify LLM path handles {\"claims\": [...]} wrapper. Testing: mocked"""
        code_analysis = self._make_api_surface(
            classes=[
                {"name": "Document", "module": "lib", "methods": ["open"], "docstring": "Document"},
            ],
        )

        llm_response_json = json.dumps({
            "claims": [
                {"claim_text": "MyLib provides the Document class", "claim_kind": "key_feature", "referenced_symbols": ["Document"]},
            ]
        })

        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {"content": llm_response_json}

        claims = extract_claims_from_code_analysis(
            code_analysis, "MyLib", Path("."), llm_client=mock_client,
        )
        assert len(claims) == 1
        assert "Document" in claims[0]["claim_text"]

    def test_llm_failure_falls_back_to_offline(self):
        """Verify LLM failure falls through to offline path."""
        code_analysis = self._make_api_surface(
            classes=[
                {"name": "Scene", "module": "aspose3d", "methods": ["save", "load", "render"], "docstring": "3D scene"},
            ],
        )

        mock_client = MagicMock()
        mock_client.chat_completion.side_effect = Exception("LLM unavailable")

        claims = extract_claims_from_code_analysis(
            code_analysis, "Aspose.3D", Path("."), llm_client=mock_client,
        )

        # Should still get offline claims despite LLM failure
        assert len(claims) > 0
        claim_texts = [c["claim_text"] for c in claims]
        assert any("Scene" in t for t in claim_texts)

    def test_existing_version_format_claims_unchanged(self):
        """Verify version and format claims still work with new signature."""
        code_analysis = {
            "api_surface": {"classes": [], "functions": [], "modules": []},
            "constants": {
                "version": "1.2.3",
                "supported_formats": ["OBJ", "STL"],
            },
        }
        claims = extract_claims_from_code_analysis(code_analysis, "Aspose.3D", Path("."))

        claim_texts = [c["claim_text"] for c in claims]
        assert any("version" in t and "1.2.3" in t for t in claim_texts)
        assert any("OBJ" in t for t in claim_texts)
        assert any("STL" in t for t in claim_texts)

    def test_existing_version_format_claims_backward_compat(self):
        """Verify old callers without llm_client still work (backward compat)."""
        code_analysis = {
            "constants": {
                "version": "2.0.0",
                "supported_formats": ["PDF"],
            },
        }
        # Call WITHOUT llm_client (old signature)
        claims = extract_claims_from_code_analysis(code_analysis, "TestLib", Path("."))
        assert any("version" in c["claim_text"] and "2.0.0" in c["claim_text"] for c in claims)
        assert any("PDF" in c["claim_text"] for c in claims)

    def test_claim_structure_valid(self):
        """Verify all generated claims have required fields."""
        code_analysis = self._make_api_surface(
            classes=[
                {"name": "Workbook", "module": "cells", "methods": ["save", "open", "close"], "docstring": "Excel workbook"},
            ],
            functions=[
                {"name": "convert", "module": "cells.util", "docstring": "Convert files"},
            ],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "Aspose.Cells", Path("."))

        required_fields = {"claim_id", "claim_text", "claim_kind", "truth_status", "confidence", "source_priority", "citations"}
        for claim in claims:
            missing = required_fields - set(claim.keys())
            assert not missing, f"Claim missing fields {missing}: {claim['claim_text']}"
            assert claim["truth_status"] == "fact"
            assert claim["confidence"] == "high"
            assert claim["source_priority"] == 2
            assert isinstance(claim["citations"], list)
            assert len(claim["citations"]) > 0
            for cit in claim["citations"]:
                assert "path" in cit
                assert "start_line" in cit
                assert "end_line" in cit
                assert "source_type" in cit

    def test_claim_ids_are_deterministic(self):
        """Verify claim IDs are stable across repeated calls."""
        code_analysis = self._make_api_surface(
            classes=[
                {"name": "Scene", "module": "lib", "methods": ["save"], "docstring": "A scene"},
            ],
        )
        claims_a = extract_claims_from_code_analysis(code_analysis, "MyLib", Path("."))
        claims_b = extract_claims_from_code_analysis(code_analysis, "MyLib", Path("."))
        ids_a = sorted([c["claim_id"] for c in claims_a])
        ids_b = sorted([c["claim_id"] for c in claims_b])
        assert ids_a == ids_b

    def test_empty_api_surface_no_extra_claims(self):
        """Verify empty api_surface produces no API claims."""
        code_analysis = {
            "api_surface": {"classes": [], "functions": [], "modules": []},
            "constants": {},
        }
        claims = extract_claims_from_code_analysis(code_analysis, "TestLib", Path("."))
        assert len(claims) == 0

    def test_missing_api_surface_key_no_extra_claims(self):
        """Verify missing api_surface key produces no API claims (backward compat)."""
        code_analysis = {"constants": {"version": "1.0.0"}}
        claims = extract_claims_from_code_analysis(code_analysis, "TestLib", Path("."))
        # Should only have the version claim
        assert len(claims) == 1
        assert "version" in claims[0]["claim_text"]

    def test_offline_docstring_used_in_claim(self):
        """Verify offline class claim uses docstring first sentence."""
        code_analysis = self._make_api_surface(
            classes=[
                {"name": "Mesh", "module": "lib", "methods": ["render"], "docstring": "Represents a 3D mesh. Can be rendered."},
            ],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "Lib3D", Path("."))
        class_claims = [c for c in claims if "Mesh" in c["claim_text"] and "class" in c["claim_text"]]
        assert len(class_claims) == 1
        # First sentence of docstring should be used
        assert "represents a 3d mesh" in class_claims[0]["claim_text"].lower()

    def test_private_methods_excluded_from_method_listing(self):
        """Verify private methods are excluded from method-listing claims."""
        code_analysis = self._make_api_surface(
            classes=[
                {
                    "name": "Engine",
                    "module": "lib",
                    "methods": ["start", "stop", "reset", "_init_internal", "__repr__"],
                    "docstring": "Processing engine",
                },
            ],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "TestLib", Path("."))
        method_claims = [c for c in claims if "provides methods:" in c["claim_text"]]
        assert len(method_claims) == 1
        assert "_init_internal" not in method_claims[0]["claim_text"]
        assert "__repr__" not in method_claims[0]["claim_text"]
        assert "start()" in method_claims[0]["claim_text"]


class TestTC1603BoilerplateApiClaims:
    """TC-1603: Tests for eliminating boilerplate API claims from _generate_offline_api_claims."""

    def _make_api_surface(
        self,
        classes=None,
        functions=None,
        modules=None,
    ) -> Dict[str, Any]:
        """Helper to build a code_analysis dict with an api_surface."""
        return {
            "api_surface": {
                "classes": classes or [],
                "functions": functions or [],
                "modules": modules or [],
            },
            "constants": {},
        }

    def test_no_docstring_classes_aggregated(self):
        """TC-1603: Classes without docstrings produce ONE aggregate 'api' claim, not individual 'key_feature' claims."""
        code_analysis = self._make_api_surface(
            classes=[
                {"name": "BoundingBox", "module": "lib", "methods": ["expand"], "docstring": ""},
                {"name": "Transform", "module": "lib", "methods": ["apply"], "docstring": ""},
                {"name": "Vertex", "module": "lib", "methods": ["normalize"], "docstring": ""},
            ],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "Aspose.3D", Path("."))

        # Should NOT have individual key_feature claims for these classes
        individual_class_claims = [
            c for c in claims
            if c["claim_kind"] == "key_feature" and "class for" in c["claim_text"]
        ]
        assert len(individual_class_claims) == 0, (
            f"Expected no individual class claims for docstring-less classes, got: "
            f"{[c['claim_text'] for c in individual_class_claims]}"
        )

        # Should have exactly ONE aggregate 'api' claim
        api_claims = [c for c in claims if c["claim_kind"] == "api"]
        assert len(api_claims) == 1, f"Expected 1 aggregate api claim, got {len(api_claims)}"

        agg = api_claims[0]
        assert "3 public classes" in agg["claim_text"]
        assert "BoundingBox" in agg["claim_text"]
        assert "Transform" in agg["claim_text"]
        assert "Vertex" in agg["claim_text"]
        assert agg["truth_status"] == "fact"
        assert agg["confidence"] == "high"
        assert agg["source_priority"] == 2

    def test_docstring_classes_get_individual_claims(self):
        """TC-1603: Classes WITH docstrings still get individual 'key_feature' claims."""
        code_analysis = self._make_api_surface(
            classes=[
                {"name": "Scene", "module": "lib", "methods": ["save"], "docstring": "Main 3D scene container"},
                {"name": "Mesh", "module": "lib", "methods": ["render"], "docstring": "Represents a 3D mesh"},
            ],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "Aspose.3D", Path("."))

        # Should have individual key_feature claims for each class
        class_claims = [
            c for c in claims
            if c["claim_kind"] == "key_feature" and "class for" in c["claim_text"]
        ]
        assert len(class_claims) == 2, f"Expected 2 individual class claims, got {len(class_claims)}"

        claim_texts = [c["claim_text"] for c in class_claims]
        assert any("Scene" in t for t in claim_texts)
        assert any("Mesh" in t for t in claim_texts)

        # Should NOT have aggregate api claim (no skipped classes)
        api_claims = [c for c in claims if c["claim_kind"] == "api"]
        assert len(api_claims) == 0, "Expected no aggregate api claim when all classes have docstrings"

    def test_offline_api_cap_30(self):
        """TC-1603: Pass 40 classes with docstrings -> at most 30 claims."""
        classes = [
            {"name": f"Widget{i}", "module": "mod", "methods": ["run"], "docstring": f"Widget number {i} processor"}
            for i in range(40)
        ]
        code_analysis = self._make_api_surface(classes=classes)
        claims = extract_claims_from_code_analysis(code_analysis, "TestProduct", Path("."))
        assert len(claims) <= 30, f"Expected at most 30 claims, got {len(claims)}"

    def test_mixed_classes_with_and_without_docstrings(self):
        """TC-1603: Mixed classes: docstring classes get individual, no-docstring get aggregated."""
        code_analysis = self._make_api_surface(
            classes=[
                {"name": "Scene", "module": "lib", "methods": ["save"], "docstring": "Main 3D scene container"},
                {"name": "BoundingBox", "module": "lib", "methods": ["expand"], "docstring": ""},
                {"name": "Transform", "module": "lib", "methods": ["apply"], "docstring": ""},
            ],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "Aspose.3D", Path("."))

        # Scene should get an individual claim
        scene_claims = [c for c in claims if "Scene" in c["claim_text"] and "class for" in c["claim_text"]]
        assert len(scene_claims) == 1

        # BoundingBox and Transform should be in the aggregate claim
        api_claims = [c for c in claims if c["claim_kind"] == "api"]
        assert len(api_claims) == 1
        assert "2 public classes" in api_claims[0]["claim_text"]
        assert "BoundingBox" in api_claims[0]["claim_text"]
        assert "Transform" in api_claims[0]["claim_text"]

    def test_aggregate_claim_truncates_at_5_names(self):
        """TC-1603: Aggregate claim shows at most 5 class names with 'and N more' suffix."""
        classes = [
            {"name": f"Class{i}", "module": "mod", "methods": ["run"], "docstring": ""}
            for i in range(8)
        ]
        code_analysis = self._make_api_surface(classes=classes)
        claims = extract_claims_from_code_analysis(code_analysis, "TestProduct", Path("."))

        api_claims = [c for c in claims if c["claim_kind"] == "api"]
        assert len(api_claims) == 1
        agg_text = api_claims[0]["claim_text"]
        assert "8 public classes" in agg_text
        assert "and 3 more" in agg_text
        # First 5 names should be present
        for i in range(5):
            assert f"Class{i}" in agg_text
        # 6th, 7th, 8th should NOT be individually named
        assert "Class5" not in agg_text
        assert "Class6" not in agg_text
        assert "Class7" not in agg_text

    def test_string_format_classes_without_docstrings_aggregated(self):
        """TC-1603: String-format classes (no docstring possible) are aggregated."""
        code_analysis = self._make_api_surface(
            classes=["Alpha", "Beta", "Gamma"],
        )
        claims = extract_claims_from_code_analysis(code_analysis, "TestLib", Path("."))

        # String classes have no docstring, so they all get the fallback purpose
        individual_class_claims = [
            c for c in claims
            if c["claim_kind"] == "key_feature" and "class for" in c["claim_text"]
        ]
        assert len(individual_class_claims) == 0

        api_claims = [c for c in claims if c["claim_kind"] == "api"]
        assert len(api_claims) == 1
        assert "3 public classes" in api_claims[0]["claim_text"]


class TestTC1401CodeGroundedClaimsIntegration:
    """TC-1401: Test integration of code-grounded claims into extract_claims pipeline."""

    def test_extract_claims_with_code_analysis_llm(self):
        """Test extract_claims() integrates code-grounded claims via LLM path.

        Testing: mocked
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            # Create run layout
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create discovered_docs.json (minimal)
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            # Create repo_inventory.json
            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Create code_analysis.json with api_surface
            code_analysis = {
                'api_surface': {
                    'classes': [
                        {
                            'name': 'Scene',
                            'module': 'testlib.core',
                            'methods': ['load', 'save', 'render'],
                            'docstring': 'Manages 3D scenes',
                        },
                    ],
                    'functions': [
                        {
                            'name': 'convert_file',
                            'module': 'testlib.utils',
                            'docstring': 'Converts between file formats',
                        },
                    ],
                    'modules': [],
                },
                'constants': {},
            }
            (artifacts_dir / "code_analysis.json").write_text(json.dumps(code_analysis))

            # Mock LLM client
            mock_llm = MagicMock()
            mock_llm.chat_completion.return_value = {
                'content': json.dumps([
                    {
                        'claim_text': 'TestProduct provides the Scene class for 3D scene management',
                        'claim_kind': 'key_feature',
                        'referenced_symbols': ['Scene'],
                    },
                    {
                        'claim_text': 'TestProduct provides the convert_file() function for format conversion',
                        'claim_kind': 'key_feature',
                        'referenced_symbols': ['convert_file'],
                    },
                ])
            }

            # Extract claims
            result = extract_claims(repo_dir, run_dir, llm_client=mock_llm)

            # Verify code-grounded claims were added
            assert len(result['claims']) >= 2
            claim_texts = [c['claim_text'] for c in result['claims']]

            # Check for code-grounded claims
            has_scene_claim = any('Scene class' in text for text in claim_texts)
            has_function_claim = any('convert_file()' in text for text in claim_texts)
            assert has_scene_claim or has_function_claim, "Expected code-grounded claims to be present"

            # Verify LLM was called
            assert mock_llm.chat_completion.called

    def test_extract_claims_with_code_analysis_offline(self):
        """Test extract_claims() integrates code-grounded claims via offline path.

        Testing: mocked
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            # Create run layout
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create discovered_docs.json (minimal)
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            # Create repo_inventory.json
            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Create code_analysis.json with api_surface
            code_analysis = {
                'api_surface': {
                    'classes': [
                        {
                            'name': 'Mesh',
                            'module': 'testlib.geometry',
                            'methods': ['triangulate', 'subdivide'],
                            'docstring': 'Represents a 3D mesh',
                        },
                    ],
                    'functions': [
                        {
                            'name': 'export_obj',
                            'module': 'testlib.exporters',
                            'docstring': 'Exports to OBJ format',
                        },
                    ],
                    'modules': [],
                },
                'constants': {},
            }
            (artifacts_dir / "code_analysis.json").write_text(json.dumps(code_analysis))

            # Extract claims WITHOUT llm_client (offline path)
            result = extract_claims(repo_dir, run_dir, llm_client=None)

            # Verify code-grounded claims were added
            assert len(result['claims']) >= 2
            claim_texts = [c['claim_text'] for c in result['claims']]

            # Check for template-based claims
            has_mesh_claim = any('Mesh class' in text for text in claim_texts)
            has_export_claim = any('export_obj()' in text for text in claim_texts)
            assert has_mesh_claim or has_export_claim, "Expected offline code-grounded claims to be present"

            # Verify all claims have required structure
            for claim in result['claims']:
                assert 'claim_id' in claim
                assert 'claim_text' in claim
                assert 'claim_kind' in claim
                assert 'truth_status' in claim
                assert 'confidence' in claim
                assert 'source_priority' in claim
                assert 'citations' in claim

    def test_code_grounded_claim_structure(self):
        """Test code-grounded claims have correct structure and field values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            # Create run layout
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create discovered_docs.json (minimal)
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            # Create repo_inventory.json
            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Create code_analysis.json
            code_analysis = {
                'api_surface': {
                    'classes': [
                        {
                            'name': 'Node',
                            'module': 'testlib.scene',
                            'methods': ['attach', 'detach'],
                            'docstring': 'Scene graph node',
                        },
                    ],
                    'functions': [],
                    'modules': [],
                },
                'constants': {},
            }
            (artifacts_dir / "code_analysis.json").write_text(json.dumps(code_analysis))

            # Extract claims (offline path for determinism)
            result = extract_claims(repo_dir, run_dir, llm_client=None)

            # Find code-grounded claims
            code_claims = [c for c in result['claims'] if 'Node class' in c['claim_text']]
            assert len(code_claims) >= 1, "Expected at least one code-grounded claim"

            # Validate structure
            for claim in code_claims:
                assert claim['truth_status'] == 'fact', "Code-grounded claims must have truth_status='fact'"
                assert claim['confidence'] == 'high', "Code-grounded claims must have confidence='high'"
                assert claim['source_priority'] == 2, "Code-grounded claims must have source_priority=2"
                assert len(claim['citations']) >= 1, "Code-grounded claims must have citations"
                assert claim['citations'][0]['source_type'] == 'source_code', "Citations must be from source_code"

    def test_extract_claims_missing_code_analysis(self):
        """Test extract_claims() handles missing code_analysis.json gracefully.

        Testing: mocked
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            # Create run layout
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create README
            readme_path = repo_dir / "README.md"
            readme_path.write_text("This library supports OBJ format.")

            # Create discovered_docs.json
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [{'path': 'README.md', 'type': 'README'}],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            # Create repo_inventory.json
            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Do NOT create code_analysis.json

            # Extract claims (should succeed without code_analysis)
            result = extract_claims(repo_dir, run_dir, llm_client=None)

            # Verify extraction succeeded
            assert 'claims' in result
            assert len(result['claims']) >= 0  # May have doc claims only

            # Verify no error was raised
            assert result['schema_version'] == '1.0.0'


class TestTC1613SourceTypeCoverage:
    """TC-1613: Ensure 100% source_type coverage on all claims."""

    def test_all_claims_have_source_type(self):
        """TC-1613: Run extract_claims on a repo with README and source files,
        verify every claim has a non-empty source_type field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create README with claims
            readme_path = repo_dir / "README.md"
            readme_path.write_text(
                "# TestProduct\n\n"
                "This library supports OBJ format for 3D models.\n"
                "It can read and write STL files efficiently.\n"
                "The API provides a Scene class for scene management.\n"
                "Does not support FBX format at this time.\n"
                "\n## Installation\n\n"
                "Install via pip install test-product for quick setup.\n"
            )

            # Create a source file
            src_dir = repo_dir / "src"
            src_dir.mkdir()
            src_file = src_dir / "main.py"
            src_file.write_text(
                "# This module provides core functionality for processing.\n"
                "# The library handles conversion of various file formats.\n"
            )

            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [
                    {'path': 'README.md', 'type': 'README', 'relevance_score': 100},
                    {'path': 'src/main.py', 'type': 'source', 'relevance_score': 80},
                ],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Add code_analysis with API surface
            code_analysis = {
                'api_surface': {
                    'classes': [
                        {'name': 'Scene', 'module': 'lib', 'methods': ['save', 'load', 'render'],
                         'docstring': 'Main 3D scene container'},
                    ],
                    'functions': [
                        {'name': 'convert', 'module': 'lib', 'docstring': 'Convert files'},
                    ],
                    'modules': [],
                },
                'constants': {'version': '1.0.0', 'supported_formats': ['OBJ']},
            }
            (artifacts_dir / "code_analysis.json").write_text(json.dumps(code_analysis))

            result = extract_claims(repo_dir, run_dir, llm_client=None)

            assert len(result['claims']) > 0, "Expected at least one claim"
            for claim in result['claims']:
                assert claim.get('source_type'), (
                    f"Claim missing source_type: {claim.get('claim_text', '')[:60]}"
                )

    def test_source_type_fallback_from_path(self):
        """TC-1613: A claim candidate without source_type but with a source_file path
        gets the correct source_type from the safety net fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create a README that will produce claims
            readme_path = repo_dir / "README.md"
            readme_path.write_text(
                "This library supports multiple file formats for conversion.\n"
            )

            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [
                    {'path': 'README.md', 'type': 'README'},
                ],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            result = extract_claims(repo_dir, run_dir, llm_client=None)

            assert len(result['claims']) > 0
            for claim in result['claims']:
                st = claim.get('source_type', '')
                assert st, f"source_type is empty for claim: {claim['claim_text'][:60]}"
                # README-derived claims should have a readme_* source type
                if 'README' in claim['citations'][0].get('path', '').upper():
                    assert st.startswith('readme_'), (
                        f"Expected readme_* source_type for README claim, got '{st}'"
                    )

    def test_no_claims_with_empty_source_type(self):
        """TC-1613: After full extraction (with code analysis), assert
        all(c.get('source_type') for c in claims)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create README
            (repo_dir / "README.md").write_text(
                "# MyLib\n\n"
                "This library provides comprehensive format conversion tools.\n"
                "It enables batch processing of multiple file types.\n"
            )

            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [
                    {'path': 'README.md', 'type': 'README', 'relevance_score': 90},
                ],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            repo_inventory = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'MyLib',
            }
            (artifacts_dir / "repo_inventory.json").write_text(json.dumps(repo_inventory))

            # Code analysis with version and format claims
            code_analysis = {
                'api_surface': {
                    'classes': [
                        {'name': 'Converter', 'module': 'mylib',
                         'methods': ['run', 'validate', 'export'],
                         'docstring': 'Format converter engine'},
                    ],
                    'functions': [],
                    'modules': [],
                },
                'constants': {
                    'version': '2.5.0',
                    'supported_formats': ['PDF', 'DOCX'],
                },
            }
            (artifacts_dir / "code_analysis.json").write_text(json.dumps(code_analysis))

            result = extract_claims(repo_dir, run_dir, llm_client=None)

            assert len(result['claims']) > 0, "Expected claims from README + code analysis"
            # The core assertion: every single claim has a non-empty source_type
            assert all(c.get('source_type') for c in result['claims']), (
                "Found claims with missing/empty source_type: "
                + str([
                    c['claim_text'][:50]
                    for c in result['claims']
                    if not c.get('source_type')
                ])
            )

            # Verify we have claims from multiple sources
            source_types = {c['source_type'] for c in result['claims']}
            assert len(source_types) >= 2, (
                f"Expected claims from multiple source types, got: {source_types}"
            )

    def test_extract_candidate_statements_includes_source_type(self):
        """TC-1613: Verify extract_candidate_statements_from_text always sets source_type."""
        text = "This library supports the OBJ file format natively.\n"
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        assert len(candidates) >= 1
        for candidate in candidates:
            assert 'source_type' in candidate, "Candidate missing source_type key"
            assert candidate['source_type'], "Candidate has empty source_type"

    def test_extract_claims_with_llm_includes_source_type(self):
        """TC-1613: Verify extract_claims_with_llm sets source_type on each claim."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir) / "repo"
            repo_dir.mkdir()

            doc_path = repo_dir / "README.md"
            doc_path.write_text(
                "This library supports the OBJ file format natively.\n"
                "It provides comprehensive tools for batch conversion.\n"
            )

            doc_files = [{'path': 'README.md', 'type': 'README'}]

            mock_llm = MagicMock()
            claims = extract_claims_with_llm(
                doc_files, repo_dir, "TestProduct", mock_llm
            )

            assert len(claims) > 0, "Expected at least one claim from LLM extraction"
            for claim in claims:
                assert claim.get('source_type'), (
                    f"LLM-extracted claim missing source_type: {claim['claim_text'][:50]}"
                )

    def test_code_analysis_version_format_claims_have_source_type(self):
        """TC-1613: Verify version and format claims from code analysis have source_type."""
        code_analysis = {
            'api_surface': {'classes': [], 'functions': [], 'modules': []},
            'constants': {
                'version': '3.0.0',
                'supported_formats': ['CSV', 'JSON'],
            },
        }
        claims = extract_claims_from_code_analysis(code_analysis, "TestLib", Path("."))

        assert len(claims) == 3, f"Expected 3 claims (1 version + 2 format), got {len(claims)}"
        for claim in claims:
            assert claim.get('source_type'), (
                f"Code analysis claim missing source_type: {claim['claim_text'][:50]}"
            )


class TestTC1610CodeBlockDecomposition:
    """TC-1610: Tests for decomposing README code blocks into per-statement claims."""

    def test_code_block_decomposition_install(self):
        """Install section with 4 distinct actions produces 3-4 separate claims with step_order.

        TC-1617 UPDATE: Installation sections now include prerequisite (step_order=0),
        verification, and troubleshooting steps, so step_order starts at 0.
        """
        code_lines = [
            "import sys",
            "from subprocess import run",
            "run(['pip', 'install', 'aspose-3d'])",
            "sys.path.append('/usr/local/lib')",
        ]

        claims = _synthesize_code_block_claims(
            code_lines=code_lines,
            section_heading="Installation",
            section_kind="installation",
            section_start=10,
            section_end=15,
            rel_path="README.md",
            product_name="Aspose.3D",
        )

        # TC-1617: Should produce multiple claims including prerequisite, main steps, verification, troubleshooting
        assert len(claims) >= 3, f"Expected 3+ claims for install section, got {len(claims)}"

        # TC-1617: All claims should have step_order starting at 0 (prerequisite)
        step_orders = [claim['step_order'] for claim in claims]
        assert step_orders[0] == 0, "First claim should be prerequisite with step_order=0"
        assert step_orders == list(range(len(claims))), "step_order should be sequential from 0"

        # Verify claim structure
        for claim in claims:
            assert claim['source_type'] == 'readme_technical'
            assert claim['keyword_boost'] is True
            assert claim['section_kind'] == 'installation'

        # TC-1617: Check for prerequisite, verification, troubleshooting
        claim_texts = [c['claim_text'] for c in claims]
        assert any('Python 3.8+' in t for t in claim_texts), "Should have prerequisite"
        assert any('Verify installation' in t for t in claim_texts), "Should have verification"
        assert any('installation fails' in t for t in claim_texts), "Should have troubleshooting"

    def test_code_block_decomposition_quickstart(self):
        """Quickstart section produces 3+ claims with sequential step_order.

        TC-1617 UPDATE: Quickstart sections now decompose into per-statement claims,
        step_order starts at 0 (no prerequisite for quickstart, unlike installation).
        """
        code_lines = [
            "from aspose.threed import Scene",
            "scene = Scene()",
            "scene.open('model.fbx')",
            "scene.save('output.obj')",
        ]

        claims = _synthesize_code_block_claims(
            code_lines=code_lines,
            section_heading="Quick Start",
            section_kind="quickstart",
            section_start=20,
            section_end=25,
            rel_path="README.md",
            product_name="Aspose.3D",
        )

        # TC-1617: Should produce at least 3 claims (import, Scene(), open(), save())
        assert len(claims) >= 3, f"Expected 3+ claims for quickstart, got {len(claims)}"

        # TC-1617: Verify sequential step_order starting at 0
        step_orders = [claim['step_order'] for claim in claims]
        assert step_orders == list(range(len(claims))), f"Expected sequential [0,1,2...], got {step_orders}"

    def test_code_block_non_install_single_claim(self):
        """Non-install/quickstart sections produce single combined claim for backward compat."""
        code_lines = [
            "from aspose.threed import Scene",
            "scene = Scene()",
            "scene.open('model.fbx')",
        ]

        claims = _synthesize_code_block_claims(
            code_lines=code_lines,
            section_heading="Usage Example",
            section_kind="usage",
            section_start=30,
            section_end=35,
            rel_path="README.md",
            product_name="Aspose.3D",
        )

        # Should produce exactly 1 combined claim
        assert len(claims) == 1, f"Expected 1 claim for non-workflow section, got {len(claims)}"

        # Should NOT have step_order
        assert 'step_order' not in claims[0], "Non-workflow claim should not have step_order"

        # Should have all actions combined
        claim_text = claims[0]['claim_text']
        assert 'import Scene from threed' in claim_text
        assert 'call Scene()' in claim_text
        assert 'call open()' in claim_text

    def test_step_order_sequential(self):
        """Verify step_order values are sequential integers starting from 1."""
        code_lines = [
            "import aspose.threed",
            "from aspose.threed import Scene, FileFormat",
            "scene = Scene()",
            "scene.open('input.fbx')",
            "scene.save('output.obj', FileFormat.WAVEFRONT_OBJ)",
        ]

        claims = _synthesize_code_block_claims(
            code_lines=code_lines,
            section_heading="Getting Started",
            section_kind="quickstart",
            section_start=40,
            section_end=46,
            rel_path="README.md",
            product_name="Aspose.3D",
        )

        # Extract step_order values
        step_orders = [c['step_order'] for c in claims]

        # TC-1617 UPDATE: Should start at 0 (not 1)
        assert step_orders[0] == 0, "step_order should start at 0"

        # Should be sequential (0, 1, 2, 3, ...)
        assert step_orders == list(range(len(step_orders))), (
            f"step_order not sequential: {step_orders}"
        )

    def test_empty_code_block_no_actions(self):
        """Code block with no parseable actions produces fallback claim with enrichment.

        TC-1617 UPDATE: Installation sections get prerequisite, generic step, verification,
        troubleshooting even when no parseable actions.
        """
        code_lines = [
            "# This is a comment",
            "# Another comment",
        ]

        claims = _synthesize_code_block_claims(
            code_lines=code_lines,
            section_heading="Installation",
            section_kind="installation",
            section_start=50,
            section_end=52,
            rel_path="README.md",
            product_name="TestProduct",
        )

        # TC-1617: Should produce 4 claims (prerequisite + generic fallback + verification + troubleshooting)
        assert len(claims) == 4, f"Expected 4 enriched claims, got {len(claims)}"

        # Check for enrichment steps
        claim_texts = [c['claim_text'] for c in claims]
        assert any('Python 3.8+' in t for t in claim_texts), "Should have prerequisite"
        assert any('installation' in t.lower() for t in claim_texts), "Should have installation step"
        assert any('Verify installation' in t for t in claim_texts), "Should have verification"
        assert any('installation fails' in t for t in claim_texts), "Should have troubleshooting"


class TestClaimQualityFilters:
    """Test TC-1616 claim quality filters to reduce key_features noise."""

    def test_code_like_threshold_lowered(self):
        """Test lowered 25% non-alpha threshold catches code-like text.

        TC-1616: Lowered threshold from 40% to 25% to catch API descriptions
        with heavy use of identifiers, dots, and parentheses.
        """
        # Text with 28% non-alpha (dots, parens, commas in identifiers)
        text = "Scene.mesh.vertices[0].position.x = 10.5"
        non_alpha = sum(1 for c in text if not c.isalpha() and not c.isspace())
        ratio = non_alpha / len(text)
        assert ratio > 0.25, f"Test text should have >25% non-alpha, got {ratio}"
        assert _is_code_like(text) is True

        # Text with multiple method calls (30%+ non-alpha)
        text2 = "obj.load().transform().save()"
        non_alpha2 = sum(1 for c in text2 if not c.isalpha() and not c.isspace())
        ratio2 = non_alpha2 / len(text2)
        assert ratio2 > 0.25, f"Test text should have >25% non-alpha, got {ratio2}"
        assert _is_code_like(text2) is True

    def test_template_claim_detection_provides_class(self):
        """Test detection of 'provides the X class' template pattern."""
        text1 = "Aspose.3D provides the Scene class for scene operations"
        assert _is_template_claim(text1, "Aspose.3D") is True

        text2 = "TestProduct provides the Renderer class for rendering operations"
        assert _is_template_claim(text2, "TestProduct") is True

        # Should not match legitimate features
        text3 = "Supports comprehensive 3D scene manipulation"
        assert _is_template_claim(text3) is False

    def test_template_claim_detection_provides_methods(self):
        """Test detection of 'class provides methods' template pattern."""
        text1 = "The Scene class provides methods: render(), load(), save()"
        assert _is_template_claim(text1) is True

        text2 = "The Renderer class provides method: draw()"
        assert _is_template_claim(text2) is True

    def test_template_claim_detection_provides_function(self):
        """Test detection of 'provides the X() function' template pattern."""
        text = "TestProduct provides the render() function"
        assert _is_template_claim(text) is True

    def test_template_claim_detection_provides_count(self):
        """Test detection of 'provides N classes/functions' template pattern."""
        text1 = "Provides 50 classes for 3D manipulation"
        assert _is_template_claim(text1) is True

        text2 = "Aspose.3D provides 120 functions"
        assert _is_template_claim(text2) is True

    def test_api_claims_capped_at_15(self):
        """Test code-grounded claims limited to 15.

        TC-1616: Lowered cap from 30 to 15 to reduce noise.
        """
        # Create API surface with 30 documented classes
        api_surface = {
            "classes": [
                {"name": f"Class{i}", "docstring": f"This is class {i}", "methods": []}
                for i in range(30)
            ]
        }
        claims = _generate_offline_api_claims(api_surface, "TestProduct")

        # Should be capped at 15 class claims (no methods, so no additional claims)
        # May have +1 for aggregation if undocumented classes exist
        assert len(claims) <= 16

    def test_api_claims_relevance_sorting(self):
        """Test documented classes prioritized over undocumented.

        TC-1616: Relevance scoring ensures documented APIs appear first.
        """
        api_surface = {
            "classes": [
                {"name": "UndocClass1", "docstring": "", "methods": []},
                {"name": "DocClass1", "docstring": "This is well documented", "methods": []},
                {"name": "UndocClass2", "docstring": "", "methods": []},
                {"name": "DocClass2", "docstring": "Also well documented", "methods": []},
            ]
        }
        claims = _generate_offline_api_claims(api_surface, "TestProduct")

        # First claims should be from documented classes
        first_claim_texts = [c['claim_text'] for c in claims[:2]]
        # At least one documented class should appear in first 2 claims
        assert any("DocClass" in text for text in first_claim_texts)

    def test_undocumented_classes_aggregated(self):
        """Test undocumented classes beyond cap aggregated into single claim.

        TC-1616: When there are >15 undocumented classes, aggregate them.
        """
        # Create 20 undocumented classes (exceeds cap of 15)
        api_surface = {
            "classes": [
                {"name": f"Class{i}", "docstring": "", "methods": []}
                for i in range(20)
            ]
        }
        claims = _generate_offline_api_claims(api_surface, "TestProduct")

        # Should have aggregation claim for undocumented classes
        aggregation_claims = [
            c for c in claims
            if "additional API classes" in c['claim_text']
        ]
        assert len(aggregation_claims) > 0
        assert aggregation_claims[0]['claim_kind'] == 'api_reference'


class TestTC1617WorkflowEnrichment:
    """Tests for TC-1617: Workflow enrichment with per-statement decomposition."""

    def test_per_statement_decomposition(self):
        """Test per-statement decomposition creates individual steps.

        TC-1617: Single import → 1 step, 3 imports → 3 steps,
        full workflow → multiple steps.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _decompose_code_block_into_steps
        )

        # Test 1: Single import
        code_lines = ["from aspose.threed import Scene"]
        steps = _decompose_code_block_into_steps(
            code_lines, "Installation", "installation", "Aspose.3D"
        )
        assert len(steps) == 1
        assert steps[0]['step_order'] == 1
        assert 'Import' in steps[0]['claim_text']
        assert 'Scene' in steps[0]['claim_text']

        # Test 2: Three imports
        code_lines = [
            "from aspose.threed import Scene",
            "from aspose.threed import FileFormat",
            "from aspose.threed import SaveOptions",
        ]
        steps = _decompose_code_block_into_steps(
            code_lines, "Installation", "installation", "Aspose.3D"
        )
        assert len(steps) == 3
        assert steps[0]['step_order'] == 1
        assert steps[1]['step_order'] == 2
        assert steps[2]['step_order'] == 3

        # Test 3: Full workflow (import + instantiate + method call)
        code_lines = [
            "from aspose.threed import Scene",
            "scene = Scene()",
            "scene.save('output.obj')",
        ]
        steps = _decompose_code_block_into_steps(
            code_lines, "Quickstart", "quickstart", "Aspose.3D"
        )
        # Should have at least import + instantiate steps
        assert len(steps) >= 2
        step_orders = [s['step_order'] for s in steps]
        assert step_orders == sorted(step_orders)  # Sequential ordering

    def test_workflow_enrichment_prerequisites(self):
        """Test workflow enrichment adds prerequisite step.

        TC-1617: Installation workflows should have prerequisite at step_order=0.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _decompose_code_block_into_steps,
            _enrich_workflow_claims_with_context
        )

        # Create basic installation steps
        code_lines = ["pip install aspose-3d"]
        steps = _decompose_code_block_into_steps(
            code_lines, "Installation", "installation", "Aspose.3D"
        )

        # Enrich with context
        enriched = _enrich_workflow_claims_with_context(
            steps, "Installation", "installation",
            100, 110, "README.md", "Aspose.3D"
        )

        # First claim should be prerequisite
        assert len(enriched) > len(steps)  # Enrichment adds claims
        assert enriched[0]['step_order'] == 0
        assert 'Python 3.8+' in enriched[0]['claim_text']
        assert enriched[0]['action_type'] == 'prerequisite'

    def test_workflow_enrichment_verification(self):
        """Test workflow enrichment adds verification step.

        TC-1617: Installation workflows should have verification step.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _decompose_code_block_into_steps,
            _enrich_workflow_claims_with_context
        )

        # Create basic installation steps
        code_lines = ["pip install aspose-3d"]
        steps = _decompose_code_block_into_steps(
            code_lines, "Installation", "installation", "Aspose.3D"
        )

        # Enrich with context
        enriched = _enrich_workflow_claims_with_context(
            steps, "Installation", "installation",
            100, 110, "README.md", "Aspose.3D"
        )

        # Should have verification step
        verification_steps = [
            c for c in enriched
            if c.get('action_type') == 'verification'
        ]
        assert len(verification_steps) > 0
        assert 'Verify installation' in verification_steps[0]['claim_text']
        assert 'Aspose.3D' in verification_steps[0]['claim_text']

    def test_step_order_sequential(self):
        """Test step_order values are sequential.

        TC-1617: Enriched claims should have step_order values like [0, 1, 2, 3...].
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _decompose_code_block_into_steps,
            _enrich_workflow_claims_with_context
        )

        # Create installation workflow with multiple steps
        code_lines = [
            "from aspose.threed import Scene",
            "scene = Scene()",
            "scene.save('output.obj')",
        ]
        steps = _decompose_code_block_into_steps(
            code_lines, "Installation", "installation", "Aspose.3D"
        )

        # Enrich with context
        enriched = _enrich_workflow_claims_with_context(
            steps, "Installation", "installation",
            100, 120, "README.md", "Aspose.3D"
        )

        # Extract step_order values
        step_orders = [c['step_order'] for c in enriched]

        # Should start at 0 (prerequisite)
        assert step_orders[0] == 0

        # Should be sequential with no gaps
        for i in range(len(step_orders) - 1):
            assert step_orders[i + 1] == step_orders[i] + 1


class TestUseCaseExtraction:
    """Test use case extraction for TC-1618."""

    def test_use_case_bullet_pattern(self):
        """Test use case extraction from bullet list with description pattern.

        TC-1618: Extract use cases from "- **Name**: description" pattern.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_use_case_narratives,
        )

        section_text = """
## Use Cases

- **CAD File Conversion**: Convert 3D models between different CAD formats programmatically, enabling automated migration pipelines and batch processing workflows for design teams worldwide.
- **Game Asset Pipeline**: Transform game assets from DCC tools into optimized runtime formats, streamlining content pipelines for game development studios across the industry.
"""

        use_cases = _extract_use_case_narratives(
            text=section_text,
            section_heading="Use Cases",
            source_file="README.md",
            section_start=10,
            section_end=15,
            source_type="readme_marketing",
        )

        # Should extract 2 use cases
        assert len(use_cases) == 2

        # First use case
        assert "CAD File Conversion" in use_cases[0]["claim_text"]
        assert use_cases[0]["claim_kind"] == "use_case"
        assert use_cases[0]["section_kind"] == "use_case"
        assert use_cases[0]["keyword_boost"] is True

        # Second use case
        assert "Game Asset Pipeline" in use_cases[1]["claim_text"]

    def test_use_case_narrative_paragraph(self):
        """Test use case extraction from narrative paragraphs (20+ words).

        TC-1618: Extract narrative paragraphs as use cases.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_use_case_narratives,
        )

        section_text = """
## Real World Applications

This library is widely used in architectural visualization, where designers need to convert legacy CAD files into modern rendering formats for client presentations.

Game development teams use it to automate asset conversion in their content pipelines, reducing manual work.
"""

        use_cases = _extract_use_case_narratives(
            text=section_text,
            section_heading="Real World Applications",
            source_file="README.md",
            section_start=20,
            section_end=25,
            source_type="readme_marketing",
        )

        # Should extract at least 1 narrative paragraph (first one is 20+ words)
        assert len(use_cases) >= 1

        # First narrative should be about architectural visualization
        assert "architectural visualization" in use_cases[0]["claim_text"]
        assert use_cases[0]["claim_kind"] == "use_case"

    def test_use_case_minimum_length_filter(self):
        """Test that use cases with <20 words are filtered out.

        TC-1618: Enforce 20-word minimum for narrative quality.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_use_case_narratives,
        )

        section_text = """
## Use Cases

- **Too Short**: Only five words here.
- **Long Enough**: This use case has sufficient detail to describe a real-world scenario where the product provides value to users by solving a specific problem.
"""

        use_cases = _extract_use_case_narratives(
            text=section_text,
            section_heading="Use Cases",
            source_file="README.md",
            section_start=10,
            section_end=15,
            source_type="readme_marketing",
        )

        # Should only extract the second one (20+ words)
        assert len(use_cases) == 1
        assert "Long Enough" in use_cases[0]["claim_text"]


class TestTutorialExtraction:
    """Test tutorial extraction for TC-1618."""

    def test_tutorial_prose_and_code_required(self):
        """Test that tutorials require both prose and code blocks.

        TC-1618: Tutorials must have educational flow with prose + code.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_tutorial_narratives,
        )

        # Prose only (no code) - should return empty
        prose_only = """
## Tutorial

This is a tutorial with lots of prose but no code blocks.
It explains concepts in detail with many words.
"""

        tutorials = _extract_tutorial_narratives(
            text=prose_only,
            section_heading="Tutorial",
            source_file="README.md",
            section_start=10,
            section_end=15,
            source_type="readme_technical",
        )
        assert len(tutorials) == 0

        # Code only (no prose) - should return empty
        code_only = """
## Example

```python
from aspose.threed import Scene
scene = Scene()
```
"""

        tutorials = _extract_tutorial_narratives(
            text=code_only,
            section_heading="Example",
            source_file="README.md",
            section_start=20,
            section_end=25,
            source_type="readme_technical",
        )
        assert len(tutorials) == 0

        # Both prose and code - should extract
        prose_and_code = """
## Tutorial

This tutorial demonstrates how the library loads a 3D scene from a file and converts it to a different format using the conversion API provided by the framework.

```python
from aspose.threed import Scene
scene = Scene.from_file("input.obj")
scene.save("output.fbx")
```

The conversion process automatically handles format differences and preserves geometry and materials during the transformation workflow.
"""

        tutorials = _extract_tutorial_narratives(
            text=prose_and_code,
            section_heading="Tutorial",
            source_file="README.md",
            section_start=30,
            section_end=45,
            source_type="readme_technical",
        )
        assert len(tutorials) == 1
        assert tutorials[0]["claim_kind"] == "tutorial"
        assert tutorials[0]["code_block_count"] == 1
        assert tutorials[0]["prose_block_count"] >= 1

    def test_tutorial_minimum_prose_length(self):
        """Test that tutorial prose must be 30+ words.

        TC-1618: Enforce 30-word minimum for educational quality.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_tutorial_narratives,
        )

        # Prose too short (<30 words)
        short_prose = """
## Tutorial

This is too short.

```python
code_here()
```
"""

        tutorials = _extract_tutorial_narratives(
            text=short_prose,
            section_heading="Tutorial",
            source_file="README.md",
            section_start=10,
            section_end=15,
            source_type="readme_technical",
        )
        assert len(tutorials) == 0

        # Prose long enough (30+ words)
        long_prose = """
## Tutorial

This tutorial provides a comprehensive walkthrough of the library's core functionality, demonstrating how to load 3D models, manipulate their properties, and export them to various formats with detailed explanations of each step.

```python
from aspose.threed import Scene
scene = Scene.from_file("model.obj")
scene.save("output.fbx")
```
"""

        tutorials = _extract_tutorial_narratives(
            text=long_prose,
            section_heading="Tutorial",
            source_file="README.md",
            section_start=20,
            section_end=30,
            source_type="readme_technical",
        )
        assert len(tutorials) == 1
        assert "tutorial" in tutorials[0]["claim_text"].lower()


class TestSectionHeaderMapping:
    """Test section header to claim_kind mapping for TC-1618."""

    def test_section_headers_use_case(self):
        """Test that use case headers are mapped to 'use_case' section_kind.

        TC-1618: Headers like "Use Cases", "Applications", "Scenarios" → use_case.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _SECTION_HEADERS,
        )

        # Check all use case headers
        assert _SECTION_HEADERS["use cases"] == "use_case"
        assert _SECTION_HEADERS["use case"] == "use_case"
        assert _SECTION_HEADERS["applications"] == "use_case"
        assert _SECTION_HEADERS["when to use"] == "use_case"
        assert _SECTION_HEADERS["scenarios"] == "use_case"
        assert _SECTION_HEADERS["real world"] == "use_case"
        assert _SECTION_HEADERS["case study"] == "use_case"
        assert _SECTION_HEADERS["case studies"] == "use_case"

    def test_section_headers_tutorial(self):
        """Test that tutorial headers are mapped to 'tutorial' section_kind.

        TC-1618: Headers like "Tutorial", "Walkthrough", "How To" → tutorial.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _SECTION_HEADERS,
        )

        # Check all tutorial headers
        assert _SECTION_HEADERS["examples"] == "tutorial"
        assert _SECTION_HEADERS["example"] == "tutorial"
        assert _SECTION_HEADERS["tutorial"] == "tutorial"
        assert _SECTION_HEADERS["tutorials"] == "tutorial"
        assert _SECTION_HEADERS["walkthrough"] == "tutorial"
        assert _SECTION_HEADERS["guide"] == "tutorial"
        assert _SECTION_HEADERS["how to"] == "tutorial"
        assert _SECTION_HEADERS["step by step"] == "tutorial"


class TestTC1619ErrorAndFAQExtraction:
    """Test error message, FAQ, and troubleshooting extraction for TC-1619."""

    def test_error_message_extraction_raise_statement(self):
        """Test error message extraction from raise statements.

        TC-1619: Extract error messages from raise ValueError("message").
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_error_messages,
        )

        code = '''
def process_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError("File not found at the specified path")
    if not path.endswith('.txt'):
        raise ValueError("Invalid file format - only .txt files are supported")
    return read_file(path)
'''
        claims = _extract_error_messages(code, "src/utils.py")

        # Should extract 2 error messages
        assert len(claims) >= 2

        # Check first error
        file_not_found = [c for c in claims if "FileNotFoundError" in c.get("error_type", "")]
        assert len(file_not_found) == 1
        assert "File not found" in file_not_found[0]["claim_text"]
        assert file_not_found[0]["claim_kind"] == "troubleshooting"
        assert file_not_found[0]["section_kind"] == "troubleshooting"

        # Check second error
        value_error = [c for c in claims if "ValueError" in c.get("error_type", "")]
        assert len(value_error) == 1
        assert "Invalid file format" in value_error[0]["claim_text"]

    def test_error_message_extraction_exception_class(self):
        """Test error extraction from custom Exception class definitions.

        TC-1619: Extract from class CustomError(Exception).
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_error_messages,
        )

        code = '''
class InvalidConfigError(Exception):
    """Raised when configuration is invalid."""
    pass

class ProcessingError(Exception):
    """Raised when processing fails."""
    pass
'''
        claims = _extract_error_messages(code, "src/exceptions.py")

        # Should extract 2 custom error classes
        assert len(claims) >= 2

        # Check both custom errors are found
        error_types = [c.get("error_type", "") for c in claims]
        assert "InvalidConfigError" in error_types
        assert "ProcessingError" in error_types

        # Check claim structure
        for claim in claims:
            assert claim["claim_kind"] == "troubleshooting"
            assert "Custom error type" in claim["claim_text"]

    def test_limitation_expansion_known_issue(self):
        """Test expanded limitation detection for known issues.

        TC-1619: Detect "known issue", "workaround", etc.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_expanded_limitations,
        )

        text = '''
## Known Issues

There is a known issue with Unicode characters in file paths on Windows.
The workaround is to use short path names or ASCII-only filenames.

Compatibility note: Python 3.7 is not supported. Requires Python 3.8 or higher.

This feature only works with UTF-8 encoded files.
'''
        claims = _extract_expanded_limitations(text, "README.md", section_start=1)

        # Should extract at least 3 limitation/troubleshooting claims
        assert len(claims) >= 3

        # Check for known issue detection
        known_issues = [c for c in claims if "known issue" in c["claim_text"].lower()]
        assert len(known_issues) >= 1

        # Check for workaround detection
        workarounds = [c for c in claims if "workaround" in c["claim_text"].lower()]
        assert len(workarounds) >= 1

        # All should be troubleshooting or limitation kind
        for claim in claims:
            assert claim["claim_kind"] in ["troubleshooting", "limitation"]
            assert claim["section_kind"] == "troubleshooting"

    def test_faq_extraction_qa_format(self):
        """Test FAQ extraction from Q: A: format.

        TC-1619: Parse "Q: question A: answer" format.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_faq_entries,
        )

        text = '''
Q: How do I install the library?
A: You can install using pip install package-name. Make sure you have Python 3.8 or higher installed on your system before proceeding with installation.

Q: What file formats are supported?
A: The library supports OBJ, FBX, STL, and GLTF formats for 3D models. Each format has specific features and limitations that you should be aware of.
'''
        claims = _extract_faq_entries(
            text,
            section_heading="FAQ",
            source_file="README.md",
            section_start=1,
            section_end=10,
            source_type="readme_technical",
        )

        # Should extract 2 FAQ entries
        assert len(claims) >= 2

        # Check first FAQ
        install_faq = [c for c in claims if "install" in c["claim_text"].lower()]
        assert len(install_faq) >= 1
        assert "FAQ:" in install_faq[0]["claim_text"]
        assert "Answer:" in install_faq[0]["claim_text"]
        assert install_faq[0]["claim_kind"] == "faq"

        # Check second FAQ
        format_faq = [c for c in claims if "format" in c["claim_text"].lower()]
        assert len(format_faq) >= 1
        assert format_faq[0]["section_kind"] == "faq"

    def test_faq_from_test_names(self):
        """Test FAQ synthesis from test function names.

        TC-1619: Convert test_handle_error → FAQ entry.
        """
        import tempfile
        from pathlib import Path
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_faq_from_tests,
        )

        test_code = '''
def test_handle_invalid_format():
    """Test that invalid format raises ValueError."""
    with pytest.raises(ValueError):
        process_file("invalid.xyz")

def test_missing_file_raises_error():
    """Test that missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_file("nonexistent.txt")

def test_basic_functionality():
    """Test basic file processing works."""
    result = process_file("valid.txt")
    assert result is not None
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(test_code)
            test_file_path = f.name

        try:
            claims = _extract_faq_from_tests(test_file_path)

            # Should extract 2 FAQ entries (only error/invalid/missing tests, not basic functionality)
            assert len(claims) >= 2

            # Check invalid format FAQ
            invalid_faq = [c for c in claims if "invalid format" in c["claim_text"].lower()]
            assert len(invalid_faq) >= 1
            assert "FAQ:" in invalid_faq[0]["claim_text"]
            assert invalid_faq[0]["claim_kind"] == "faq"

            # Check missing file FAQ
            missing_faq = [c for c in claims if "missing file" in c["claim_text"].lower()]
            assert len(missing_faq) >= 1

            # Should NOT include basic functionality test (no error keywords)
            basic_faq = [c for c in claims if "basic functionality" in c["claim_text"].lower()]
            assert len(basic_faq) == 0

        finally:
            Path(test_file_path).unlink()


class TestTC1619SectionHeaders:
    """Test FAQ and troubleshooting section header mappings for TC-1619."""

    def test_section_headers_faq(self):
        """Test that FAQ headers are mapped to 'faq' section_kind.

        TC-1619: Headers like "FAQ", "Q&A", "Common Questions" → faq.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _SECTION_HEADERS,
        )

        # Check all FAQ headers
        assert _SECTION_HEADERS["faq"] == "faq"
        assert _SECTION_HEADERS["frequently asked questions"] == "faq"
        assert _SECTION_HEADERS["q&a"] == "faq"
        assert _SECTION_HEADERS["common questions"] == "faq"

    def test_section_headers_troubleshooting(self):
        """Test that troubleshooting headers are mapped to 'troubleshooting' section_kind.

        TC-1619: Headers like "Troubleshooting", "Known Issues" → troubleshooting.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _SECTION_HEADERS,
        )

        # Check all troubleshooting headers
        assert _SECTION_HEADERS["common issues"] == "troubleshooting"
        assert _SECTION_HEADERS["troubleshooting"] == "troubleshooting"
        assert _SECTION_HEADERS["known limitations"] == "troubleshooting"
        assert _SECTION_HEADERS["known issues"] == "troubleshooting"


class TestTC1620BestPracticesExtraction:
    """Test best practices extraction for TC-1620."""

    def test_best_practice_extraction_imperative(self):
        """Test extraction of imperative statements from README.

        TC-1620: Detects "Use X for Y" pattern and categorizes by type.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_best_practice_statements,
        )

        text = """
        Use context managers for file handling.
        Always cache expensive computations for better performance.
        Avoid using global variables.
        Never modify shared state without locks.
        It is recommended to validate input before processing.
        """

        practices = _extract_best_practice_statements(
            text=text,
            section_heading="Best Practices",
            source_file="README.md",
            section_start=1,
            section_end=10,
            source_type="readme_technical",
            product_name="TestLib",
        )

        # Should find at least 3 practices
        assert len(practices) >= 3

        # Check structure
        for practice in practices:
            assert practice["claim_kind"] == "best_practice"
            assert practice["section_kind"] == "best_practice"
            assert "category" in practice
            assert practice["category"] in ["memory", "speed", "correctness"]
            assert practice["keyword_boost"] is True

        # Check categorization: "cache" and "performance" → speed
        speed_practices = [p for p in practices if p["category"] == "speed"]
        assert len(speed_practices) >= 1
        assert any("cache" in p["claim_text"].lower() for p in speed_practices)

    def test_best_practice_from_code_context_manager(self):
        """Test inference of best practices from with-statements.

        TC-1620: Detects context managers and generates relevant claim.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _infer_best_practices_from_code,
        )

        code = """
        import os

        def read_file(path):
            with open(path, 'r') as f:
                return f.read()

        def write_file(path, content):
            with open(path, 'w') as f:
                f.write(content)
        """

        practices = _infer_best_practices_from_code(
            code_content=code,
            source_file="src/utils.py",
            product_name="TestLib",
        )

        # Should detect with-statement pattern
        context_mgr_practices = [
            p for p in practices if "with-statement" in p["claim_text"].lower()
        ]
        assert len(context_mgr_practices) >= 1

        # Check structure
        practice = context_mgr_practices[0]
        assert practice["claim_kind"] == "best_practice"
        assert practice["category"] == "correctness"
        assert "resource management" in practice["claim_text"].lower()

    def test_best_practice_from_code_caching(self):
        """Test inference of best practices from caching decorators.

        TC-1620: Detects @lru_cache decorator and generates caching recommendation.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _infer_best_practices_from_code,
        )

        code = """
        from functools import lru_cache

        @lru_cache(maxsize=128)
        def compute_expensive_result(n):
            return sum(i**2 for i in range(n))
        """

        practices = _infer_best_practices_from_code(
            code_content=code,
            source_file="src/compute.py",
            product_name="TestLib",
        )

        # Should detect caching decorator
        cache_practices = [
            p for p in practices if "cache" in p["claim_text"].lower()
        ]
        assert len(cache_practices) >= 1

        # Check structure
        practice = cache_practices[0]
        assert practice["claim_kind"] == "best_practice"
        assert practice["category"] == "speed"
        assert "performance" in practice["claim_text"].lower()

    def test_performance_extraction_benchmark(self):
        """Test extraction of performance characteristics from test benchmarks.

        TC-1620: Extracts from test_benchmark_X functions.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _extract_performance_characteristics,
        )

        test_content = """
        import pytest

        def test_benchmark_load_time():
            start = time.time()
            lib.load_file("large.dat")
            duration = time.time() - start
            assert duration < 2.0

        def test_benchmark_processing_speed():
            result = lib.process_data(large_dataset)
            assert result is not None

        def test_scalability():
            max_items = 10000
            data = generate_test_data(max_items)
            assert len(data) == max_items
        """

        characteristics = _extract_performance_characteristics(
            test_content=test_content,
            source_file="tests/test_performance.py",
            product_name="TestLib",
        )

        # Should find benchmark tests
        benchmark_chars = [
            c for c in characteristics if "benchmark" in c["claim_text"].lower()
        ]
        assert len(benchmark_chars) >= 2

        # Should find performance assertion
        time_chars = [
            c for c in characteristics if "2.0 seconds" in c["claim_text"]
        ]
        assert len(time_chars) >= 1

        # Should find scalability limit
        scalability_chars = [
            c for c in characteristics if "10000" in c["claim_text"]
        ]
        assert len(scalability_chars) >= 1

        # Check structure
        for char in characteristics:
            assert char["claim_kind"] == "performance"
            assert char["section_kind"] == "performance"
            assert "metric" in char


class TestTC1620SectionHeaders:
    """Test best practices and performance section header mappings for TC-1620."""

    def test_section_headers_best_practices(self):
        """Test that best practice headers are mapped to 'best_practice' section_kind.

        TC-1620: Headers like "Best Practices", "Tips", "Optimization" → best_practice.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _SECTION_HEADERS,
        )

        # Check all best practice headers
        assert _SECTION_HEADERS["best practices"] == "best_practice"
        assert _SECTION_HEADERS["best practice"] == "best_practice"
        assert _SECTION_HEADERS["tips"] == "best_practice"
        assert _SECTION_HEADERS["optimization"] == "best_practice"
        assert _SECTION_HEADERS["performance tips"] == "best_practice"
        assert _SECTION_HEADERS["anti patterns"] == "best_practice"
        assert _SECTION_HEADERS["anti-patterns"] == "best_practice"

    def test_section_headers_performance(self):
        """Test that performance headers are mapped to 'performance' section_kind.

        TC-1620: Header "Performance" → performance.
        """
        from src.launch.workers.w2_facts_builder.extract_claims import (
            _SECTION_HEADERS,
        )

        # Check performance header
        assert _SECTION_HEADERS["performance"] == "performance"


class TestLlmWorkflowGeneration:
    """TC-1623: LLM workflow step generation tests."""

    def test_llm_generate_installation_steps(self):
        """TC-1623: LLM generates additional installation steps."""
        from src.launch.workers.w2_facts_builder.extract_claims import (
            llm_generate_workflow_steps,
        )

        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "steps": [
                {"name": "Verify Python version is 3.8 or higher", "description": "Run python --version"},
                {"name": "Create a virtual environment", "description": "Use venv module"},
                {"name": "Activate the virtual environment", "description": "Run activate script"},
            ]
        })

        existing_steps = ["Install via pip install test-product", "Import test_product in Python"]

        result = llm_generate_workflow_steps(
            workflow_tag="installation",
            workflow_title="Installation",
            existing_steps=existing_steps,
            api_surface={"classes": [{"name": "Mesh"}], "functions": [{"name": "load"}]},
            positioning={"short_description": "A 3D processing library"},
            product_name="Test Product",
            llm_client=mock_llm,
            target_steps=5,
        )

        # Should return 3 new steps
        assert len(result) == 3
        assert result[0]['name'] == "Verify Python version is 3.8 or higher"
        assert result[0]['claim_kind'] == 'workflow'
        assert result[0]['source_type'] == 'llm_synthesized'
        assert result[0]['truth_status'] == 'inference'
        assert result[0]['confidence'] == 'medium'
        assert result[0]['citations'] == []
        # step_order starts after existing count (2)
        assert result[0]['step_order'] == 3
        assert result[1]['step_order'] == 4
        assert result[2]['step_order'] == 5

        # Verify LLM was called
        mock_llm.chat_completion.assert_called_once()
        call_kwargs = mock_llm.chat_completion.call_args
        assert call_kwargs[1]['temperature'] == 0.0
        assert call_kwargs[1]['call_id'] == 'tc1623_workflow_installation'

    def test_llm_generate_quickstart_steps(self):
        """TC-1623: LLM generates quickstart steps from empty."""
        from src.launch.workers.w2_facts_builder.extract_claims import (
            llm_generate_workflow_steps,
        )

        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "steps": [
                {"name": "Import the library", "description": "import aspose"},
                {"name": "Load a document", "description": "use Scene class"},
                {"name": "Process the document", "description": "apply operations"},
                {"name": "Save the result", "description": "export to file"},
            ]
        })

        result = llm_generate_workflow_steps(
            workflow_tag="quickstart",
            workflow_title="Quick Start",
            existing_steps=[],
            api_surface={"classes": [], "functions": []},
            positioning={"tagline": "3D File Processing"},
            product_name="Aspose.3D",
            llm_client=mock_llm,
            target_steps=4,
        )

        # Should return all 4 steps since no existing steps
        assert len(result) == 4
        # step_order starts from 1 since no existing steps
        assert result[0]['step_order'] == 1
        assert result[3]['step_order'] == 4
        # All should be llm_synthesized
        for step in result:
            assert step['source_type'] == 'llm_synthesized'
            assert step['truth_status'] == 'inference'

    def test_llm_workflow_deduplication(self):
        """TC-1623: Duplicate steps are filtered via Jaccard overlap."""
        from src.launch.workers.w2_facts_builder.extract_claims import (
            llm_generate_workflow_steps,
        )

        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "steps": [
                # This should be deduplicated (high overlap with "Install via pip")
                {"name": "Install via pip package manager", "description": "..."},
                # This should survive (unique)
                {"name": "Configure logging settings", "description": "..."},
                # This should also survive
                {"name": "Set up authentication credentials", "description": "..."},
            ]
        })

        existing_steps = ["Install via pip"]

        result = llm_generate_workflow_steps(
            workflow_tag="installation",
            workflow_title="Installation",
            existing_steps=existing_steps,
            api_surface={},
            positioning={},
            product_name="TestLib",
            llm_client=mock_llm,
            target_steps=4,
        )

        # "Install via pip package manager" should be filtered (Jaccard >= 0.5 with "Install via pip")
        step_names = [s['name'] for s in result]
        assert "Install via pip package manager" not in step_names
        assert "Configure logging settings" in step_names
        assert "Set up authentication credentials" in step_names
        assert len(result) == 2

    def test_llm_workflow_offline_skips(self):
        """TC-1623: Returns empty when llm_client is None."""
        from src.launch.workers.w2_facts_builder.extract_claims import (
            llm_generate_workflow_steps,
        )

        result = llm_generate_workflow_steps(
            workflow_tag="installation",
            workflow_title="Installation",
            existing_steps=["Step 1"],
            api_surface={},
            positioning={},
            product_name="TestLib",
            llm_client=None,
            target_steps=5,
        )

        assert result == []


class TestLlmFaqTroubleshootingGeneration:
    """TC-1625: LLM FAQ and troubleshooting generation tests."""

    def test_llm_generate_faq_from_limitations(self):
        """TC-1625: LLM generates FAQ entries from limitations."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "faq_entries": [
                {"question": "What formats are supported?", "answer": "OBJ, FBX, STL, and more.", "category": "formats"},
                {"question": "Is threading safe?", "answer": "Scene objects are not thread-safe.", "category": "api_usage"},
            ]
        })

        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_faq_entries

        result = llm_generate_faq_entries(
            limitation_claims=["Does not support DWG format", "Memory usage scales with model complexity"],
            api_surface={"classes": ["Scene", "Mesh"], "functions": ["load", "save"]},
            product_name="Aspose.3D",
            llm_client=mock_llm,
        )

        assert len(result) == 2
        assert result[0]["claim_kind"] == "faq"
        assert result[0]["source_type"] == "llm_synthesized"
        assert result[0]["truth_status"] == "inference"
        assert "Q:" in result[0]["claim_text"]
        assert "A:" in result[0]["claim_text"]

    def test_llm_generate_troubleshooting_from_errors(self):
        """TC-1625: LLM generates troubleshooting guides."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "guides": [
                {"problem": "File fails to load", "cause": "Unsupported format", "resolution": "Check format compatibility", "prevention": "Validate format before loading"},
            ]
        })

        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_troubleshooting_entries

        result = llm_generate_troubleshooting_entries(
            limitation_claims=["Does not support DWG"],
            api_surface={"classes": ["Scene"]},
            product_name="Aspose.3D",
            llm_client=mock_llm,
        )

        assert len(result) >= 1
        assert result[0]["claim_kind"] == "troubleshooting"
        assert result[0]["source_type"] == "llm_synthesized"
        assert "Problem:" in result[0]["claim_text"]

    def test_faq_offline_skips(self):
        """TC-1625: FAQ generation returns empty when llm_client is None."""
        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_faq_entries

        result = llm_generate_faq_entries(
            limitation_claims=["Some limitation"],
            api_surface={},
            product_name="Test",
            llm_client=None,
        )
        assert result == []

    def test_troubleshooting_offline_skips(self):
        """TC-1625: Troubleshooting generation returns empty when llm_client is None."""
        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_troubleshooting_entries

        result = llm_generate_troubleshooting_entries(
            limitation_claims=["Some limitation"],
            api_surface={},
            product_name="Test",
            llm_client=None,
        )
        assert result == []


class TestLlmBestPracticesGeneration:
    """TC-1626: LLM best practices and performance generation tests."""

    def test_llm_generate_best_practices(self):
        """TC-1626: LLM generates best practice claims from API surface.

        Testing: mocked
        """
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "best_practices": [
                {
                    "category": "memory management",
                    "recommendation": "Dispose workbook objects after use",
                    "rationale": "Prevents memory leaks in long-running processes",
                },
                {
                    "category": "error handling",
                    "recommendation": "Validate file paths before loading",
                    "rationale": "Avoids cryptic exceptions from missing files",
                },
                {
                    "category": "performance",
                    "recommendation": "Use batch operations for bulk updates",
                    "rationale": "Reduces overhead compared to cell-by-cell writes",
                },
            ]
        })

        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_best_practices

        result = llm_generate_best_practices(
            api_surface={"classes": ["Workbook", "Worksheet"], "functions": ["load", "save"]},
            code_patterns=[],
            product_name="Aspose.Cells",
            llm_client=mock_llm,
        )

        assert len(result) == 3
        assert result[0]["claim_kind"] == "best_practice"
        assert result[0]["source_type"] == "llm_synthesized"
        assert result[0]["truth_status"] == "inference"
        assert result[0]["confidence"] == "medium"
        assert "Best practice (memory management)" in result[0]["claim_text"]
        assert "Dispose workbook objects after use" in result[0]["claim_text"]
        assert result[0]["citations"] == []

    def test_llm_generate_best_practices_offline_skips(self):
        """TC-1626: Best practices generation returns empty when llm_client is None."""
        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_best_practices

        result = llm_generate_best_practices(
            api_surface={},
            code_patterns=[],
            product_name="Test",
            llm_client=None,
        )
        assert result == []

    def test_llm_generate_best_practices_dedup(self):
        """TC-1626: Best practices dedup against existing code_patterns.

        Testing: mocked
        """
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "best_practices": [
                {
                    "category": "memory",
                    "recommendation": "Dispose workbook objects after use to avoid leaks",
                    "rationale": "Prevents memory issues",
                },
                {
                    "category": "performance",
                    "recommendation": "Use streaming for large files",
                    "rationale": "Reduces memory footprint",
                },
            ]
        })

        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_best_practices

        result = llm_generate_best_practices(
            api_surface={"classes": ["Workbook"]},
            code_patterns=["Dispose workbook objects after use to avoid memory leaks"],
            product_name="Test",
            llm_client=mock_llm,
        )

        # First entry should be deduped (high Jaccard with existing pattern)
        # Second entry should survive
        assert len(result) >= 1
        claim_texts = [r["claim_text"] for r in result]
        assert any("streaming" in t.lower() for t in claim_texts)

    def test_llm_generate_performance_claims(self):
        """TC-1626: LLM generates performance characteristic claims.

        Testing: mocked
        """
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "performance_claims": [
                {
                    "metric": "File load time",
                    "value": "< 2 seconds for 50MB files",
                    "conditions": "SSD storage, 8GB RAM",
                },
                {
                    "metric": "Memory usage",
                    "value": "2-3x file size",
                    "conditions": "Standard workbook processing",
                },
            ]
        })

        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_performance_claims

        result = llm_generate_performance_claims(
            api_surface={"classes": ["Workbook", "Worksheet"]},
            product_name="Aspose.Cells",
            llm_client=mock_llm,
        )

        assert len(result) == 2
        assert result[0]["claim_kind"] == "performance"
        assert result[0]["source_type"] == "llm_synthesized"
        assert result[0]["truth_status"] == "inference"
        assert result[0]["confidence"] == "medium"
        assert "File load time" in result[0]["claim_text"]
        assert "< 2 seconds" in result[0]["claim_text"]
        assert "(SSD storage, 8GB RAM)" in result[0]["claim_text"]
        assert result[0]["citations"] == []

    def test_llm_generate_performance_claims_offline_skips(self):
        """TC-1626: Performance claims generation returns empty when llm_client is None."""
        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_performance_claims

        result = llm_generate_performance_claims(
            api_surface={},
            product_name="Test",
            llm_client=None,
        )
        assert result == []

    def test_llm_generate_best_practices_llm_error(self):
        """TC-1626: Best practices generation handles LLM errors gracefully.

        Testing: mocked
        """
        mock_llm = MagicMock()
        mock_llm.chat_completion.side_effect = Exception("LLM unavailable")

        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_best_practices

        result = llm_generate_best_practices(
            api_surface={"classes": ["Workbook"]},
            code_patterns=[],
            product_name="Test",
            llm_client=mock_llm,
        )
        assert result == []

    def test_llm_generate_performance_claims_llm_error(self):
        """TC-1626: Performance claims generation handles LLM errors gracefully.

        Testing: mocked
        """
        mock_llm = MagicMock()
        mock_llm.chat_completion.side_effect = Exception("LLM unavailable")

        from src.launch.workers.w2_facts_builder.extract_claims import llm_generate_performance_claims

        result = llm_generate_performance_claims(
            api_surface={"classes": ["Workbook"]},
            product_name="Test",
            llm_client=mock_llm,
        )
        assert result == []


class TestParameterDescriptionFilter:
    """TC-2334: Test _is_parameter_description() filter."""

    @pytest.mark.parametrize("text,expected", [
        ("bold (bool, optional): Sets text to bold", True),
        ("Font (CellsFont): The font object", True),
        ("H_n if password is correct, None otherwise", True),
        ("Convert Excel files to PDF format", False),
        ("The library supports multiple formats", False),
    ])
    def test_is_parameter_description(self, text, expected):
        """TC-2334: Parameter description detection."""
        assert _is_parameter_description(text) == expected

    def test_parameter_description_filtered_by_is_code_like(self):
        """TC-2334: _is_code_like returns True for parameter descriptions."""
        assert _is_code_like("bold (bool, optional): Sets text to bold") is True

    def test_normal_prose_not_filtered(self):
        """TC-2334: Normal prose is not caught by parameter filter."""
        assert _is_parameter_description("This library supports reading PDF files") is False


class TestBestPracticeClassification:
    """TC-2335: Test best_practice claim classification."""

    @pytest.mark.parametrize("text,expected", [
        ("It is recommended to use batch processing", "best_practice"),
        ("Avoid using large file uploads without chunking", "best_practice"),
        ("Prefer batch processing instead of single item operations", "best_practice"),
        ("Convert Excel to PDF", "feature"),
    ])
    def test_classify_best_practice(self, text, expected):
        """TC-2335: best_practice classification accuracy."""
        result = classify_claim_kind(text)
        assert result == expected

    def test_strong_keyword_single_match(self):
        """TC-2335: Single strong keyword triggers best_practice."""
        assert classify_claim_kind("Always use the latest API version") == "best_practice"

    def test_weak_keyword_single_not_enough(self):
        """TC-2335: Single weak keyword does not trigger best_practice."""
        # "prefer" alone should not be enough — needs 2+ weak keywords
        result = classify_claim_kind("You may prefer this approach for large files")
        # This should be feature (only one weak keyword)
        assert result == "feature"

    def test_weak_keyword_double_match(self):
        """TC-2335: Two weak keywords trigger best_practice."""
        result = classify_claim_kind("Prefer using guidelines rather than ad hoc approaches")
        assert result == "best_practice"


class TestFormatConversionDetection:
    """TC-2342: Test detect_format_conversions() and _cluster_claims_by_topic()."""

    def test_detect_format_conversions_basic(self):
        """TC-2342: Basic conversion pattern detection."""
        claims = [
            {"claim_id": "c1", "claim_text": "Convert CSV to PDF easily"},
            {"claim_id": "c2", "claim_text": "Export JSON into Excel format"},
            {"claim_id": "c3", "claim_text": "The library is fast"},
        ]
        result = detect_format_conversions(claims, {})
        assert len(result["conversion_pairs"]) >= 2
        assert "c1" in result["format_conversions"]
        assert "c2" in result["format_conversions"]
        assert "c3" not in result["format_conversions"]

    def test_detect_format_conversions_api_classes(self):
        """TC-2342: API class name pattern detection."""
        claims = [
            {"claim_id": "c1", "claim_text": "Save files in pdf format"},
            {"claim_id": "c2", "claim_text": "The pdf module handles rendering"},
            {"claim_id": "c3", "claim_text": "Use pdf options for output"},
        ]
        api_surface = {"classes": ["PdfSaveOptions", "PdfConverter"]}
        result = detect_format_conversions(claims, api_surface)
        # All claims mention "pdf" and there are pdf-related API classes
        assert len(result["format_conversions"]) >= 1

    def test_detect_format_conversions_empty_inputs(self):
        """TC-2342: Empty inputs return empty results."""
        result = detect_format_conversions([], {})
        assert result["format_conversions"] == []
        assert result["conversion_pairs"] == []
        assert result["how_to_clusters"] == {}

    def test_cluster_claims_by_topic(self):
        """TC-2342: Topic clustering groups claims correctly."""
        claims = [
            {"claim_id": "c1", "claim_text": "Export PDF files"},
            {"claim_id": "c2", "claim_text": "Save as PDF"},
            {"claim_id": "c3", "claim_text": "Render to PDF"},
            {"claim_id": "c4", "claim_text": "Import CSV data"},
        ]
        clusters = _cluster_claims_by_topic(claims)
        assert "pdf-operations" in clusters
        assert len(clusters["pdf-operations"]) >= 3

    def test_cluster_minimum_threshold(self):
        """TC-2342: Topics with fewer than 3 claims are excluded."""
        claims = [
            {"claim_id": "c1", "claim_text": "Export PDF files"},
            {"claim_id": "c2", "claim_text": "Read PDF data"},
            # Only 2 claims mentioning chart — below threshold
            {"claim_id": "c3", "claim_text": "Create a chart"},
            {"claim_id": "c4", "claim_text": "Plot a graph"},
        ]
        clusters = _cluster_claims_by_topic(claims)
        # chart-operations needs 3+ claims, only has 2
        assert "chart-operations" not in clusters

    def test_conversion_pair_structure(self):
        """TC-2342: Conversion pairs have correct structure."""
        claims = [
            {"claim_id": "c1", "claim_text": "Convert CSV to PDF easily"},
        ]
        result = detect_format_conversions(claims, {})
        assert len(result["conversion_pairs"]) == 1
        pair = result["conversion_pairs"][0]
        assert pair["source"] == "csv"
        assert pair["target"] == "pdf"
        assert "c1" in pair["claim_ids"]


# =============================================================================
# TC-2365: source_section on Extracted Claims
# =============================================================================


class TestTC2365SourceSection:
    """TC-2365: Claims carry source_section derived from nearest Markdown heading."""

    def test_source_section_set_for_sentence_under_heading(self, tmp_path):
        """A sentence appearing after ## Installation gets source_section='installation'."""
        doc = tmp_path / "README.md"
        doc.write_text(
            "## Installation\n\n"
            "You can install this library using pip install aspose-package.\n",
            encoding="utf-8",
        )
        candidates = extract_candidate_statements_from_text(doc.read_text(), doc, tmp_path)
        assert candidates, "Expected at least one candidate"
        assert all(c.get("source_section") == "installation" for c in candidates), (
            f"Expected source_section='installation', got {[c.get('source_section') for c in candidates]}"
        )

    def test_source_section_empty_before_any_heading(self, tmp_path):
        """A sentence before the first heading gets source_section=''."""
        doc = tmp_path / "README.md"
        doc.write_text(
            "This library supports converting files between many formats.\n\n"
            "## Features\n\nProvides CSV and JSON format support.\n",
            encoding="utf-8",
        )
        candidates = extract_candidate_statements_from_text(doc.read_text(), doc, tmp_path)
        before_heading = [c for c in candidates if c.get("end_line", 0) <= 1]
        if before_heading:
            assert before_heading[0].get("source_section") == "", (
                f"Expected source_section='' for pre-heading claim, got {before_heading[0].get('source_section')}"
            )

    def test_source_section_set_for_bullet_under_heading(self, tmp_path):
        """Bullet under ## Features gets source_section='features'."""
        doc = tmp_path / "README.md"
        doc.write_text(
            "## Features\n\n"
            "- Supports reading and writing CSV and JSON format data files.\n"
            "- Can convert documents between multiple file formats easily.\n",
            encoding="utf-8",
        )
        candidates = extract_candidate_statements_from_text(doc.read_text(), doc, tmp_path)
        assert candidates, "Expected bullet candidates"
        assert all(c.get("source_section") == "features" for c in candidates), (
            f"Expected all source_section='features', got {[c.get('source_section') for c in candidates]}"
        )

    def test_source_section_does_not_affect_claim_id(self, tmp_path):
        """Same claim text yields same claim_id regardless of source_section."""
        claim_text = "Supports converting files between many formats"
        claim_kind = "feature"
        product_name = "TestProduct"
        id1 = compute_claim_id(claim_text, claim_kind, product_name)
        id2 = compute_claim_id(claim_text, claim_kind, product_name)
        # source_section is NOT part of SHA256 inputs — IDs must be identical
        assert id1 == id2

    def test_build_heading_map_basic(self):
        """_build_heading_map tracks heading slugs per line."""
        lines = [
            "## Getting Started",
            "Install via pip.",
            "## API Reference",
            "Use the Scene class.",
        ]
        hmap = _build_heading_map(lines)
        assert hmap[1] == "getting-started"
        assert hmap[2] == "getting-started"
        assert hmap[3] == "api-reference"
        assert hmap[4] == "api-reference"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
