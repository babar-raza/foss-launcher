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
    classify_claim_kind,
    compute_claim_id,
    deduplicate_claims,
    determine_source_priority,
    determine_source_type,
    extract_candidate_statements_from_text,
    extract_claims,
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
        This library supports OBJ format.
        It can read and write STL files.
        The API provides a Scene class.
        """
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        assert len(candidates) >= 2
        assert any("supports" in c['claim_text'].lower() for c in candidates)
        assert any("provides" in c['claim_text'].lower() for c in candidates)

    def test_extract_candidate_statements_accepts_short_sentences(self):
        """TC-1026: Short sentences are no longer filtered out.

        All sentences with >= 1 word are accepted as candidates.
        Keyword presence is a scoring boost, not a gate.
        """
        text = "Hello. Short. This library supports many formats."
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        # All three sentences end with '.', so all should be candidates
        assert len(candidates) >= 1
        # The sentence with keywords should have keyword_boost=True
        keyword_candidates = [c for c in candidates if c.get('keyword_boost')]
        assert any("supports" in c['claim_text'].lower() for c in keyword_candidates)

    def test_extract_candidate_statements_includes_line_numbers(self):
        """Test that line numbers are recorded.

        TC-1026: All sentences are now candidates (no keyword gate),
        so we check line numbers on the sentence that has keywords.
        """
        text = "Line 1.\nLine 2 supports OBJ format.\nLine 3."
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        # TC-1026: All 3 sentences are now candidates
        assert len(candidates) == 3
        # Check line numbers on the keyword-boosted candidate
        keyword_candidate = [c for c in candidates if c.get('keyword_boost')][0]
        assert keyword_candidate['start_line'] >= 1
        assert keyword_candidate['end_line'] >= keyword_candidate['start_line']
        # All candidates should have valid line numbers
        for c in candidates:
            assert c['start_line'] >= 1
            assert c['end_line'] >= c['start_line']


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


class TestTC1026NoExtractionLimits:
    """TC-1026: Verify all extraction limits have been removed."""

    def test_single_word_sentences_are_candidates(self):
        """TC-1026: Single-word sentences ending in punctuation are accepted."""
        text = "Supported."
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        assert len(candidates) == 1
        assert candidates[0]['claim_text'] == "Supported."

    def test_keyword_boost_present_on_candidates(self):
        """TC-1026: Candidates have keyword_boost metadata field."""
        text = "This library supports OBJ format.\nJust a plain note."
        repo_dir = Path("/repo")
        file_path = Path("/repo/README.md")

        candidates = extract_candidate_statements_from_text(text, file_path, repo_dir)

        # Both sentences should be candidates
        assert len(candidates) >= 1
        # The first should have keyword_boost=True (has 'support')
        boost_candidates = [c for c in candidates if 'supports' in c['claim_text'].lower()]
        for c in boost_candidates:
            assert c['keyword_boost'] is True

    def test_no_keyword_sentences_still_extracted(self):
        """TC-1026: Sentences without keyword markers are still extracted."""
        text = "The sky is blue."
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
                doc_path.write_text(f"Document {i} supports feature {i}.")
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
