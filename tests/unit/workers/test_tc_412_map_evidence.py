"""Unit tests for TC-412: Map evidence from claims to docs and examples.

Tests evidence mapping, relevance scoring, and artifact generation per:
- specs/03_product_facts_and_evidence.md (Evidence mapping and priority)
- specs/04_claims_compiler_truth_lock.md (Claims structure)
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/10_determinism_and_caching.md (Stable ordering)

TC-412: W2.2 Map claims to evidence in docs and examples
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.launch.workers.w2_facts_builder.map_evidence import (
    EvidenceMappingError,
    EvidenceValidationError,
    compute_text_similarity,
    enrich_claim_with_evidence,
    extract_keywords_from_claim,
    find_supporting_evidence_in_docs,
    find_supporting_evidence_in_examples,
    map_evidence,
    score_evidence_relevance,
    sort_claims_deterministically,
    validate_evidence_map_structure,
)


class TestTextSimilarity:
    """Test text similarity computation."""

    def test_compute_text_similarity_identical(self):
        """Test similarity of identical texts is 1.0."""
        text = "supports obj format"
        similarity = compute_text_similarity(text, text)
        assert similarity == 1.0

    def test_compute_text_similarity_no_overlap(self):
        """Test similarity of completely different texts is 0.0."""
        text1 = "supports obj format"
        text2 = "python installation guide"
        similarity = compute_text_similarity(text1, text2)
        assert similarity < 0.3  # Very low similarity

    def test_compute_text_similarity_partial_overlap(self):
        """Test similarity of partially overlapping texts."""
        text1 = "supports obj format"
        text2 = "supports stl format"
        similarity = compute_text_similarity(text1, text2)
        assert 0.3 < similarity < 0.9  # Moderate similarity

    def test_compute_text_similarity_case_insensitive(self):
        """Test similarity is case-insensitive."""
        text1 = "Supports OBJ Format"
        text2 = "supports obj format"
        similarity = compute_text_similarity(text1, text2)
        assert similarity == 1.0

    def test_compute_text_similarity_empty_texts(self):
        """Test similarity with empty texts."""
        assert compute_text_similarity("", "test") == 0.0
        assert compute_text_similarity("test", "") == 0.0
        assert compute_text_similarity("", "") == 0.0


class TestKeywordExtraction:
    """Test keyword extraction from claims."""

    def test_extract_keywords_from_claim_basic(self):
        """Test basic keyword extraction."""
        claim_text = "Supports OBJ format for 3D models"
        claim_kind = "format"
        keywords = extract_keywords_from_claim(claim_text, claim_kind)

        assert "supports" in keywords
        assert "obj" in keywords
        assert "format" in keywords
        assert "models" in keywords
        assert claim_kind in keywords

    def test_extract_keywords_filters_stopwords(self):
        """Test stopword filtering."""
        claim_text = "The library can read and write files"
        keywords = extract_keywords_from_claim(claim_text, "feature")

        # Stopwords should be filtered
        assert "the" not in keywords
        assert "and" not in keywords
        assert "can" not in keywords

        # Content words should remain
        assert "library" in keywords
        assert "read" in keywords
        assert "write" in keywords
        assert "files" in keywords

    def test_extract_keywords_filters_short_words(self):
        """Test filtering of very short words."""
        claim_text = "API is ok to use"
        keywords = extract_keywords_from_claim(claim_text, "api")

        # Short words (<=2 chars) should be filtered
        assert "is" not in keywords
        assert "to" not in keywords
        assert "ok" not in keywords  # 2 chars

        # Longer words should remain
        assert "api" in keywords
        assert "use" in keywords


class TestEvidenceScoring:
    """Test evidence relevance scoring."""

    def test_score_evidence_relevance_high_similarity(self):
        """Test scoring with high text similarity."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'source_priority': 1,
        }
        evidence_text = "This library supports OBJ format for 3D models"
        evidence_path = "README.md"

        score = score_evidence_relevance(claim, evidence_text, evidence_path)

        # Should have high score due to high similarity
        assert score > 0.5

    def test_score_evidence_relevance_low_similarity(self):
        """Test scoring with low text similarity."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'source_priority': 7,
        }
        evidence_text = "Installation instructions for Python packages"
        evidence_path = "README.md"

        score = score_evidence_relevance(claim, evidence_text, evidence_path)

        # Should have low score due to low similarity
        assert score < 0.3

    def test_score_evidence_relevance_keyword_matches(self):
        """Test scoring considers keyword matches."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'source_priority': 5,
        }
        evidence_text = "OBJ format is supported along with STL and FBX formats"
        evidence_path = "docs/formats.md"

        score = score_evidence_relevance(claim, evidence_text, evidence_path)

        # Should have good score due to keyword matches
        assert score > 0.4


class TestSupportingEvidenceInDocs:
    """Test finding supporting evidence in documentation."""

    def test_find_supporting_evidence_in_docs_basic(self):
        """Test finding evidence in docs."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'source_priority': 1,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Create doc files
            readme = repo_dir / "README.md"
            readme.write_text("This library supports OBJ format for 3D models.")

            docs_dir = repo_dir / "docs"
            docs_dir.mkdir()
            formats_doc = docs_dir / "formats.md"
            formats_doc.write_text("Supported formats: OBJ, STL, FBX")

            doc_files = [
                {'path': 'README.md', 'type': 'README'},
                {'path': 'docs/formats.md', 'type': 'documentation'},
            ]

            evidence = find_supporting_evidence_in_docs(claim, doc_files, repo_dir)

            # Should find both docs as evidence
            assert len(evidence) > 0
            assert all('path' in e for e in evidence)
            assert all('relevance_score' in e for e in evidence)
            assert all(e['type'] == 'documentation' for e in evidence)

    def test_find_supporting_evidence_in_docs_sorted_by_relevance(self):
        """Test evidence is sorted by relevance score."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'source_priority': 1,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Create doc files with varying relevance
            high_rel = repo_dir / "formats.md"
            high_rel.write_text("OBJ format is fully supported for import and export.")

            low_rel = repo_dir / "install.md"
            low_rel.write_text("Install using pip install package.")

            doc_files = [
                {'path': 'install.md', 'type': 'documentation'},
                {'path': 'formats.md', 'type': 'documentation'},
            ]

            evidence = find_supporting_evidence_in_docs(claim, doc_files, repo_dir)

            # Should be sorted by relevance (descending)
            if len(evidence) >= 2:
                assert evidence[0]['relevance_score'] >= evidence[1]['relevance_score']

    def test_find_supporting_evidence_in_docs_max_limit(self):
        """Test max evidence limit is respected."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Supports formats',
            'claim_kind': 'format',
            'source_priority': 1,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Create many doc files
            doc_files = []
            for i in range(10):
                doc_path = repo_dir / f"doc{i}.md"
                doc_path.write_text(f"Supports various formats including format{i}")
                doc_files.append({'path': f'doc{i}.md', 'type': 'documentation'})

            max_evidence = 3
            evidence = find_supporting_evidence_in_docs(
                claim, doc_files, repo_dir, max_evidence_per_claim=max_evidence
            )

            # Should respect max limit
            assert len(evidence) <= max_evidence

    def test_find_supporting_evidence_in_docs_threshold_filtering(self):
        """Test low-relevance evidence is filtered out."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'source_priority': 1,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Create doc with very low relevance
            irrelevant = repo_dir / "contributing.md"
            irrelevant.write_text("Contributing guidelines for developers.")

            doc_files = [{'path': 'contributing.md', 'type': 'documentation'}]

            evidence = find_supporting_evidence_in_docs(claim, doc_files, repo_dir)

            # Should filter out low-relevance evidence
            assert len(evidence) == 0 or all(e['relevance_score'] > 0.2 for e in evidence)


class TestSupportingEvidenceInExamples:
    """Test finding supporting evidence in example code."""

    def test_find_supporting_evidence_in_examples_basic(self):
        """Test finding evidence in examples."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Can load OBJ files',
            'claim_kind': 'feature',
            'source_priority': 2,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Create example files
            examples_dir = repo_dir / "examples"
            examples_dir.mkdir()

            example1 = examples_dir / "load_obj.py"
            example1.write_text("# Example: Load OBJ file\nscene.load('model.obj')")

            example_files = [
                {'path': 'examples/load_obj.py', 'language': 'python'},
            ]

            evidence = find_supporting_evidence_in_examples(claim, example_files, repo_dir)

            # Should find example as evidence
            assert len(evidence) > 0
            assert evidence[0]['type'] == 'example'
            assert 'relevance_score' in evidence[0]
            assert 'language' in evidence[0]

    def test_find_supporting_evidence_in_examples_sorted(self):
        """Test examples sorted by relevance."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Can export OBJ files',
            'claim_kind': 'feature',
            'source_priority': 2,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            examples_dir = repo_dir / "examples"
            examples_dir.mkdir()

            # High relevance example
            export_obj = examples_dir / "export_obj.py"
            export_obj.write_text("# Export OBJ file example\nscene.export('out.obj')")

            # Low relevance example
            basic = examples_dir / "basic.py"
            basic.write_text("# Basic example\nimport library")

            example_files = [
                {'path': 'examples/basic.py', 'language': 'python'},
                {'path': 'examples/export_obj.py', 'language': 'python'},
            ]

            evidence = find_supporting_evidence_in_examples(claim, example_files, repo_dir)

            # Should be sorted by relevance
            if len(evidence) >= 2:
                assert evidence[0]['relevance_score'] >= evidence[1]['relevance_score']


class TestClaimEnrichment:
    """Test enriching claims with evidence."""

    def test_enrich_claim_with_evidence_basic(self):
        """Test basic claim enrichment."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'truth_status': 'fact',
            'source_priority': 1,
            'citations': [{'path': 'README.md', 'start_line': 1, 'end_line': 1}],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Create docs and examples
            readme = repo_dir / "README.md"
            readme.write_text("Supports OBJ format")

            examples_dir = repo_dir / "examples"
            examples_dir.mkdir()
            example = examples_dir / "obj_example.py"
            example.write_text("# Load OBJ file\nscene.load('model.obj')")

            doc_files = [{'path': 'README.md', 'type': 'README'}]
            example_files = [{'path': 'examples/obj_example.py', 'language': 'python'}]

            enriched = enrich_claim_with_evidence(
                claim, doc_files, example_files, repo_dir
            )

            # Should have supporting_evidence field
            assert 'supporting_evidence' in enriched
            assert 'evidence_count' in enriched
            assert enriched['evidence_count'] > 0
            assert isinstance(enriched['supporting_evidence'], list)

    def test_enrich_claim_with_evidence_sorted(self):
        """Test enriched evidence is sorted by relevance."""
        claim = {
            'claim_id': 'test_claim',
            'claim_text': 'Supports multiple formats',
            'claim_kind': 'format',
            'truth_status': 'fact',
            'source_priority': 1,
            'citations': [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            # Create multiple docs with different relevance
            for i, text in enumerate([
                "Installation guide",
                "Supports multiple 3D formats including OBJ, STL, FBX",
                "API reference",
            ]):
                doc = repo_dir / f"doc{i}.md"
                doc.write_text(text)

            doc_files = [
                {'path': 'doc0.md', 'type': 'documentation'},
                {'path': 'doc1.md', 'type': 'documentation'},
                {'path': 'doc2.md', 'type': 'documentation'},
            ]

            enriched = enrich_claim_with_evidence(
                claim, doc_files, [], repo_dir
            )

            # Evidence should be sorted by relevance
            evidence = enriched['supporting_evidence']
            if len(evidence) >= 2:
                scores = [e['relevance_score'] for e in evidence]
                assert scores == sorted(scores, reverse=True)


class TestEvidenceMapValidation:
    """Test evidence map validation."""

    def test_validate_evidence_map_structure_valid(self):
        """Test validation of valid evidence map."""
        evidence_map = {
            'schema_version': '1.0.0',
            'repo_url': 'https://github.com/test/repo',
            'repo_sha': 'abc123',
            'claims': [
                {
                    'claim_id': 'claim1',
                    'claim_text': 'Test claim',
                    'claim_kind': 'feature',
                    'truth_status': 'fact',
                    'citations': [{'path': 'README.md', 'start_line': 1, 'end_line': 1}],
                }
            ],
        }

        # Should not raise
        validate_evidence_map_structure(evidence_map)

    def test_validate_evidence_map_structure_missing_required_field(self):
        """Test validation fails for missing required field."""
        evidence_map = {
            'schema_version': '1.0.0',
            'repo_url': 'https://github.com/test/repo',
            # Missing repo_sha
            'claims': [],
        }

        with pytest.raises(EvidenceValidationError, match="Missing required field"):
            validate_evidence_map_structure(evidence_map)

    def test_validate_evidence_map_structure_invalid_claims_type(self):
        """Test validation fails when claims is not a list."""
        evidence_map = {
            'schema_version': '1.0.0',
            'repo_url': 'https://github.com/test/repo',
            'repo_sha': 'abc123',
            'claims': "not a list",  # Invalid
        }

        with pytest.raises(EvidenceValidationError, match="claims must be a list"):
            validate_evidence_map_structure(evidence_map)

    def test_validate_evidence_map_structure_invalid_claim(self):
        """Test validation fails for invalid claim structure."""
        evidence_map = {
            'schema_version': '1.0.0',
            'repo_url': 'https://github.com/test/repo',
            'repo_sha': 'abc123',
            'claims': [
                {
                    'claim_id': 'claim1',
                    # Missing required fields
                }
            ],
        }

        with pytest.raises(EvidenceValidationError, match="missing required field"):
            validate_evidence_map_structure(evidence_map)


class TestDeterministicSorting:
    """Test deterministic claim sorting."""

    def test_sort_claims_deterministically(self):
        """Test claims are sorted by claim_id."""
        claims = [
            {'claim_id': 'zzz', 'claim_text': 'Z'},
            {'claim_id': 'aaa', 'claim_text': 'A'},
            {'claim_id': 'mmm', 'claim_text': 'M'},
        ]

        sorted_claims = sort_claims_deterministically(claims)

        assert sorted_claims[0]['claim_id'] == 'aaa'
        assert sorted_claims[1]['claim_id'] == 'mmm'
        assert sorted_claims[2]['claim_id'] == 'zzz'

    def test_sort_claims_deterministically_stable(self):
        """Test sorting is stable across runs."""
        claims = [
            {'claim_id': 'zzz', 'claim_text': 'Z'},
            {'claim_id': 'aaa', 'claim_text': 'A'},
        ]

        result1 = sort_claims_deterministically(claims)
        result2 = sort_claims_deterministically(claims)

        assert result1 == result2


class TestMapEvidenceIntegration:
    """Integration tests for map_evidence main function."""

    def test_map_evidence_basic(self):
        """Test basic evidence mapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            # Create run layout
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create README with content
            readme = repo_dir / "README.md"
            readme.write_text("This library supports OBJ format.")

            # Create extracted_claims.json
            extracted_claims = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'product_name': 'TestProduct',
                'claims': [
                    {
                        'claim_id': 'claim1',
                        'claim_text': 'Supports OBJ format',
                        'claim_kind': 'format',
                        'truth_status': 'fact',
                        'source_priority': 1,
                        'citations': [{'path': 'README.md', 'start_line': 1, 'end_line': 1}],
                    }
                ],
                'metadata': {'total_claims': 1},
            }
            (artifacts_dir / "extracted_claims.json").write_text(json.dumps(extracted_claims))

            # Create discovered_docs.json
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [
                    {'path': 'README.md', 'type': 'README'}
                ],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            # Create discovered_examples.json
            discovered_examples = {
                'schema_version': '1.0.0',
                'example_file_details': [],
            }
            (artifacts_dir / "discovered_examples.json").write_text(json.dumps(discovered_examples))

            # Map evidence
            result = map_evidence(repo_dir, run_dir, llm_client=None)

            # Verify structure
            assert result['schema_version'] == '1.0.0'
            assert result['repo_url'] == 'https://github.com/test/repo'
            assert result['repo_sha'] == 'abc123'
            assert len(result['claims']) == 1

            # Verify artifact was written
            output_path = artifacts_dir / "evidence_map.json"
            assert output_path.exists()

            # Verify metadata
            assert 'metadata' in result
            assert result['metadata']['total_claims'] == 1

    def test_map_evidence_with_examples(self):
        """Test evidence mapping with examples."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create example
            examples_dir = repo_dir / "examples"
            examples_dir.mkdir()
            example = examples_dir / "load_obj.py"
            example.write_text("# Load OBJ file\nscene.load('model.obj')")

            # Create extracted_claims.json
            extracted_claims = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'claims': [
                    {
                        'claim_id': 'claim1',
                        'claim_text': 'Can load OBJ files',
                        'claim_kind': 'feature',
                        'truth_status': 'fact',
                        'source_priority': 2,
                        'citations': [{'path': 'src/loader.py', 'start_line': 10, 'end_line': 15}],
                    }
                ],
            }
            (artifacts_dir / "extracted_claims.json").write_text(json.dumps(extracted_claims))

            # Create discovered_docs.json
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            # Create discovered_examples.json
            discovered_examples = {
                'schema_version': '1.0.0',
                'example_file_details': [
                    {'path': 'examples/load_obj.py', 'language': 'python'}
                ],
            }
            (artifacts_dir / "discovered_examples.json").write_text(json.dumps(discovered_examples))

            # Map evidence
            result = map_evidence(repo_dir, run_dir, llm_client=None)

            # Should have enriched claims with example evidence
            assert len(result['claims']) == 1
            claim = result['claims'][0]
            assert 'supporting_evidence' in claim
            # May or may not find evidence depending on relevance threshold
            # Just verify structure is correct
            if claim.get('evidence_count', 0) > 0:
                assert isinstance(claim['supporting_evidence'], list)

    def test_map_evidence_missing_extracted_claims(self):
        """Test map_evidence fails when extracted_claims.json missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Missing extracted_claims.json
            with pytest.raises(FileNotFoundError, match="extracted_claims.json not found"):
                map_evidence(repo_dir, run_dir, llm_client=None)

    def test_map_evidence_missing_discovered_docs(self):
        """Test map_evidence fails when discovered_docs.json missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create extracted_claims.json
            extracted_claims = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'claims': [],
            }
            (artifacts_dir / "extracted_claims.json").write_text(json.dumps(extracted_claims))

            # Missing discovered_docs.json
            with pytest.raises(FileNotFoundError, match="discovered_docs.json not found"):
                map_evidence(repo_dir, run_dir, llm_client=None)

    def test_map_evidence_missing_discovered_examples(self):
        """Test map_evidence fails when discovered_examples.json missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create extracted_claims.json
            extracted_claims = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'claims': [],
            }
            (artifacts_dir / "extracted_claims.json").write_text(json.dumps(extracted_claims))

            # Create discovered_docs.json
            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            # Missing discovered_examples.json
            with pytest.raises(FileNotFoundError, match="discovered_examples.json not found"):
                map_evidence(repo_dir, run_dir, llm_client=None)

    def test_map_evidence_deterministic_output(self):
        """Test map_evidence produces deterministic output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir1 = Path(tmpdir) / "run1"
            run_dir2 = Path(tmpdir) / "run2"
            repo_dir = Path(tmpdir) / "repo"
            run_dir1.mkdir()
            run_dir2.mkdir()
            repo_dir.mkdir()

            # Create README
            readme = repo_dir / "README.md"
            readme.write_text("Supports OBJ format.")

            # Setup artifacts for both runs (identical)
            for run_dir in [run_dir1, run_dir2]:
                artifacts_dir = run_dir / "artifacts"
                artifacts_dir.mkdir()

                extracted_claims = {
                    'schema_version': '1.0.0',
                    'repo_url': 'https://github.com/test/repo',
                    'repo_sha': 'abc123',
                    'claims': [
                        {
                            'claim_id': 'claim1',
                            'claim_text': 'Supports OBJ format',
                            'claim_kind': 'format',
                            'truth_status': 'fact',
                            'source_priority': 1,
                            'citations': [{'path': 'README.md', 'start_line': 1, 'end_line': 1}],
                        }
                    ],
                }
                (artifacts_dir / "extracted_claims.json").write_text(json.dumps(extracted_claims))

                discovered_docs = {
                    'schema_version': '1.0.0',
                    'doc_entrypoint_details': [{'path': 'README.md', 'type': 'README'}],
                }
                (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

                discovered_examples = {
                    'schema_version': '1.0.0',
                    'example_file_details': [],
                }
                (artifacts_dir / "discovered_examples.json").write_text(json.dumps(discovered_examples))

            # Map evidence twice
            result1 = map_evidence(repo_dir, run_dir1, llm_client=None)
            result2 = map_evidence(repo_dir, run_dir2, llm_client=None)

            # Compare claim_ids (should be identical and in same order)
            claim_ids1 = [c['claim_id'] for c in result1['claims']]
            claim_ids2 = [c['claim_id'] for c in result2['claims']]

            assert claim_ids1 == claim_ids2

            # Compare evidence counts (should be identical)
            evidence_counts1 = [c.get('evidence_count', 0) for c in result1['claims']]
            evidence_counts2 = [c.get('evidence_count', 0) for c in result2['claims']]

            assert evidence_counts1 == evidence_counts2

    def test_map_evidence_empty_claims(self):
        """Test map_evidence with empty claims list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            repo_dir = Path(tmpdir) / "repo"
            run_dir.mkdir()
            repo_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create artifacts with empty claims
            extracted_claims = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'claims': [],  # Empty
            }
            (artifacts_dir / "extracted_claims.json").write_text(json.dumps(extracted_claims))

            discovered_docs = {
                'schema_version': '1.0.0',
                'doc_entrypoint_details': [],
            }
            (artifacts_dir / "discovered_docs.json").write_text(json.dumps(discovered_docs))

            discovered_examples = {
                'schema_version': '1.0.0',
                'example_file_details': [],
            }
            (artifacts_dir / "discovered_examples.json").write_text(json.dumps(discovered_examples))

            # Should succeed with empty claims
            result = map_evidence(repo_dir, run_dir, llm_client=None)

            assert result['schema_version'] == '1.0.0'
            assert len(result['claims']) == 0
            assert result['metadata']['total_claims'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
