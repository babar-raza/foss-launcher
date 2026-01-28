"""Unit tests for TC-413: Detect contradictions and compute similarity scores.

Tests contradiction detection, semantic similarity, and resolution algorithms per:
- specs/03_product_facts_and_evidence.md:130-184 (Contradiction resolution)
- specs/04_claims_compiler_truth_lock.md:43-68 (Claims compilation)
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/10_determinism_and_caching.md (Stable ordering)

TC-413: W2.3 Detect contradictions and compute similarity scores
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from src.launch.workers.w2_facts_builder.detect_contradictions import (
    ContradictionDetectionError,
    compute_semantic_similarity,
    detect_all_contradictions,
    detect_claim_contradiction,
    detect_contradictions,
    extract_claim_core_meaning,
    resolve_contradiction,
    update_claims_with_contradiction_resolution,
    validate_evidence_map_with_contradictions,
)


class TestSemanticSimilarity:
    """Test semantic similarity computation."""

    def test_compute_semantic_similarity_identical(self):
        """Test similarity of identical claims is 1.0."""
        claim = "Supports OBJ format"
        similarity = compute_semantic_similarity(claim, claim)
        assert similarity == 1.0

    def test_compute_semantic_similarity_no_overlap(self):
        """Test similarity of unrelated claims is low."""
        claim_a = "Supports OBJ format"
        claim_b = "Installation via pip"
        similarity = compute_semantic_similarity(claim_a, claim_b)
        assert similarity < 0.3

    def test_compute_semantic_similarity_partial_overlap(self):
        """Test similarity of related claims."""
        claim_a = "Supports OBJ format"
        claim_b = "Supports STL format"
        similarity = compute_semantic_similarity(claim_a, claim_b)
        assert 0.3 < similarity < 1.0

    def test_compute_semantic_similarity_case_insensitive(self):
        """Test similarity is case-insensitive."""
        claim_a = "Supports OBJ Format"
        claim_b = "supports obj format"
        similarity = compute_semantic_similarity(claim_a, claim_b)
        assert similarity == 1.0

    def test_compute_semantic_similarity_empty_claims(self):
        """Test similarity with empty claims."""
        assert compute_semantic_similarity("", "test") == 0.0
        assert compute_semantic_similarity("test", "") == 0.0
        assert compute_semantic_similarity("", "") == 0.0


class TestClaimCoreMeaning:
    """Test claim core meaning extraction."""

    def test_extract_claim_core_meaning_positive_format(self):
        """Test extraction from positive format claim."""
        claim_text = "Supports OBJ format"
        subject, affirmative, format_name = extract_claim_core_meaning(claim_text)

        assert subject == "format"
        assert affirmative is True
        assert format_name == "OBJ"

    def test_extract_claim_core_meaning_negative_format(self):
        """Test extraction from negative format claim."""
        claim_text = "Does not support FBX format"
        subject, affirmative, format_name = extract_claim_core_meaning(claim_text)

        assert subject == "format"
        assert affirmative is False
        assert format_name == "FBX"

    def test_extract_claim_core_meaning_limitation(self):
        """Test extraction from limitation claim."""
        claim_text = "STL export is not yet implemented"
        subject, affirmative, format_name = extract_claim_core_meaning(claim_text)

        assert subject == "format"
        assert affirmative is False
        assert format_name == "STL"

    def test_extract_claim_core_meaning_workflow(self):
        """Test extraction from workflow claim."""
        claim_text = "Install via pip install package"
        subject, affirmative, format_name = extract_claim_core_meaning(claim_text)

        assert subject == "workflow"
        assert affirmative is True
        assert format_name is None

    def test_extract_claim_core_meaning_api(self):
        """Test extraction from API claim."""
        claim_text = "Provides Scene class for 3D manipulation"
        subject, affirmative, format_name = extract_claim_core_meaning(claim_text)

        assert subject == "api"
        assert affirmative is True
        assert format_name is None

    def test_extract_claim_core_meaning_feature(self):
        """Test extraction from feature claim."""
        claim_text = "Enables advanced rendering capabilities"
        subject, affirmative, format_name = extract_claim_core_meaning(claim_text)

        assert subject == "feature"
        assert affirmative is True
        assert format_name is None


class TestContradictionDetection:
    """Test contradiction detection between claim pairs."""

    def test_detect_claim_contradiction_basic_format(self):
        """Test detecting basic format contradiction."""
        claim_a = {
            'claim_id': 'claim_a',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'source_priority': 2,
            'citations': [{'source_type': 'source_code'}],
        }
        claim_b = {
            'claim_id': 'claim_b',
            'claim_text': 'Does not support OBJ format',
            'claim_kind': 'limitation',
            'source_priority': 6,
            'citations': [{'source_type': 'readme_technical'}],
        }

        contradiction = detect_claim_contradiction(claim_a, claim_b)

        assert contradiction is not None
        assert contradiction['claim_a_id'] == 'claim_a'
        assert contradiction['claim_b_id'] == 'claim_b'
        assert contradiction['resolution'] == 'prefer_higher_priority'
        assert contradiction['winning_claim_id'] == 'claim_a'

    def test_detect_claim_contradiction_no_conflict(self):
        """Test no contradiction when claims are compatible."""
        claim_a = {
            'claim_id': 'claim_a',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'source_priority': 2,
            'citations': [{'source_type': 'source_code'}],
        }
        claim_b = {
            'claim_id': 'claim_b',
            'claim_text': 'Supports STL format',
            'claim_kind': 'format',
            'source_priority': 2,
            'citations': [{'source_type': 'source_code'}],
        }

        contradiction = detect_claim_contradiction(claim_a, claim_b)

        # Should not detect contradiction (different formats, both positive)
        assert contradiction is None

    def test_detect_claim_contradiction_low_similarity(self):
        """Test no contradiction when claims are unrelated."""
        claim_a = {
            'claim_id': 'claim_a',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'source_priority': 2,
            'citations': [{'source_type': 'source_code'}],
        }
        claim_b = {
            'claim_id': 'claim_b',
            'claim_text': 'Cannot install on Windows',
            'claim_kind': 'limitation',
            'source_priority': 4,
            'citations': [{'source_type': 'implementation_doc'}],
        }

        contradiction = detect_claim_contradiction(claim_a, claim_b)

        # Should not detect contradiction (unrelated topics)
        assert contradiction is None

    def test_detect_claim_contradiction_same_claim(self):
        """Test no contradiction when comparing claim to itself."""
        claim_a = {
            'claim_id': 'claim_a',
            'claim_text': 'Supports OBJ format',
            'claim_kind': 'format',
            'source_priority': 2,
            'citations': [{'source_type': 'source_code'}],
        }

        contradiction = detect_claim_contradiction(claim_a, claim_a)

        # Should not detect contradiction (same claim)
        assert contradiction is None


class TestContradictionResolution:
    """Test contradiction resolution algorithm."""

    def test_resolve_contradiction_auto_resolution(self):
        """Test automatic resolution with priority_diff >= 2."""
        claim_a = {
            'claim_id': 'claim_a',
            'claim_text': 'Supports FBX format',
            'source_priority': 2,
            'citations': [{'source_type': 'source_code'}],
        }
        claim_b = {
            'claim_id': 'claim_b',
            'claim_text': 'Does not support FBX format',
            'source_priority': 7,
            'citations': [{'source_type': 'readme_marketing'}],
        }

        result = resolve_contradiction(claim_a, claim_b, "FBX")

        assert result['claim_a_id'] == 'claim_a'
        assert result['claim_b_id'] == 'claim_b'
        assert result['resolution'] == 'prefer_higher_priority'
        assert result['winning_claim_id'] == 'claim_a'
        assert 'priority 2' in result['reasoning']

    def test_resolve_contradiction_manual_review(self):
        """Test manual review required when priority_diff == 1."""
        claim_a = {
            'claim_id': 'claim_a',
            'claim_text': 'Supports STL format',
            'source_priority': 3,
            'citations': [{'source_type': 'test'}],
        }
        claim_b = {
            'claim_id': 'claim_b',
            'claim_text': 'Does not support STL format',
            'source_priority': 4,
            'citations': [{'source_type': 'implementation_doc'}],
        }

        result = resolve_contradiction(claim_a, claim_b, "STL")

        assert result['resolution'] == 'manual_review_required'
        assert result['winning_claim_id'] == 'claim_a'  # Tentatively higher priority
        assert 'manual review' in result['reasoning'].lower()

    def test_resolve_contradiction_unresolved(self):
        """Test unresolved conflict when priority_diff == 0."""
        claim_a = {
            'claim_id': 'claim_a',
            'claim_text': 'Supports ONE format',
            'source_priority': 5,
            'citations': [{'source_type': 'api_doc'}],
        }
        claim_b = {
            'claim_id': 'claim_b',
            'claim_text': 'Does not support ONE format',
            'source_priority': 5,
            'citations': [{'source_type': 'api_doc'}],
        }

        result = resolve_contradiction(claim_a, claim_b, "ONE")

        assert result['resolution'] == 'unresolved'
        assert 'cannot be resolved automatically' in result['reasoning'].lower()
        assert 'same priority' in result['reasoning'].lower()


class TestDetectAllContradictions:
    """Test pairwise contradiction detection."""

    def test_detect_all_contradictions_basic(self):
        """Test detecting contradictions in claim list."""
        claims = [
            {
                'claim_id': 'claim_a',
                'claim_text': 'Supports OBJ format',
                'claim_kind': 'format',
                'source_priority': 2,
                'citations': [{'source_type': 'source_code'}],
            },
            {
                'claim_id': 'claim_b',
                'claim_text': 'Does not support OBJ format',
                'claim_kind': 'limitation',
                'source_priority': 6,
                'citations': [{'source_type': 'readme_technical'}],
            },
            {
                'claim_id': 'claim_c',
                'claim_text': 'Supports STL format',
                'claim_kind': 'format',
                'source_priority': 2,
                'citations': [{'source_type': 'source_code'}],
            },
        ]

        contradictions = detect_all_contradictions(claims)

        # Should detect exactly one contradiction (claim_a vs claim_b)
        assert len(contradictions) == 1
        assert contradictions[0]['claim_a_id'] == 'claim_a'
        assert contradictions[0]['claim_b_id'] == 'claim_b'

    def test_detect_all_contradictions_multiple(self):
        """Test detecting multiple contradictions."""
        claims = [
            {
                'claim_id': 'claim_a',
                'claim_text': 'Supports OBJ format',
                'source_priority': 2,
                'citations': [{'source_type': 'source_code'}],
            },
            {
                'claim_id': 'claim_b',
                'claim_text': 'Does not support OBJ format',
                'source_priority': 6,
                'citations': [{'source_type': 'readme_technical'}],
            },
            {
                'claim_id': 'claim_c',
                'claim_text': 'Supports FBX format',
                'source_priority': 3,
                'citations': [{'source_type': 'test'}],
            },
            {
                'claim_id': 'claim_d',
                'claim_text': 'Does not support FBX format',
                'source_priority': 7,
                'citations': [{'source_type': 'readme_marketing'}],
            },
        ]

        contradictions = detect_all_contradictions(claims)

        # Should detect two contradictions
        assert len(contradictions) >= 2

    def test_detect_all_contradictions_no_conflicts(self):
        """Test no contradictions when all claims compatible."""
        claims = [
            {
                'claim_id': 'claim_a',
                'claim_text': 'Supports OBJ format',
                'source_priority': 2,
                'citations': [{'source_type': 'source_code'}],
            },
            {
                'claim_id': 'claim_b',
                'claim_text': 'Supports STL format',
                'source_priority': 2,
                'citations': [{'source_type': 'source_code'}],
            },
            {
                'claim_id': 'claim_c',
                'claim_text': 'Supports FBX format',
                'source_priority': 3,
                'citations': [{'source_type': 'test'}],
            },
        ]

        contradictions = detect_all_contradictions(claims)

        # Should detect no contradictions
        assert len(contradictions) == 0

    def test_detect_all_contradictions_deterministic_order(self):
        """Test contradictions are sorted deterministically."""
        claims = [
            {
                'claim_id': 'zzz',
                'claim_text': 'Supports OBJ format',
                'source_priority': 2,
                'citations': [{'source_type': 'source_code'}],
            },
            {
                'claim_id': 'aaa',
                'claim_text': 'Does not support OBJ format',
                'source_priority': 6,
                'citations': [{'source_type': 'readme_technical'}],
            },
        ]

        contradictions = detect_all_contradictions(claims)

        # Should be sorted by claim_a_id, then claim_b_id
        # After sorting, 'aaa' should come before 'zzz'
        if contradictions:
            # The sorting puts claim_ids in lexicographic order
            assert contradictions[0]['claim_a_id'] == 'aaa'
            assert contradictions[0]['claim_b_id'] == 'zzz'


class TestClaimUpdate:
    """Test updating claims based on contradiction resolution."""

    def test_update_claims_with_contradiction_resolution(self):
        """Test claims are updated based on resolution."""
        claims = [
            {
                'claim_id': 'claim_a',
                'claim_text': 'Supports OBJ format',
                'truth_status': 'fact',
                'confidence': 'high',
                'source_priority': 2,
            },
            {
                'claim_id': 'claim_b',
                'claim_text': 'Does not support OBJ format',
                'truth_status': 'fact',
                'confidence': 'medium',
                'source_priority': 6,
            },
        ]

        contradictions = [
            {
                'claim_a_id': 'claim_a',
                'claim_b_id': 'claim_b',
                'resolution': 'prefer_higher_priority',
                'winning_claim_id': 'claim_a',
            }
        ]

        updated_claims = update_claims_with_contradiction_resolution(claims, contradictions)

        # Winning claim should remain unchanged
        winning = next(c for c in updated_claims if c['claim_id'] == 'claim_a')
        assert winning['truth_status'] == 'fact'
        assert winning['confidence'] == 'high'

        # Losing claim should be downgraded
        losing = next(c for c in updated_claims if c['claim_id'] == 'claim_b')
        assert losing['truth_status'] == 'inference'
        assert losing['confidence'] == 'low'

    def test_update_claims_no_downgrade_for_manual_review(self):
        """Test claims are NOT downgraded when manual review required."""
        claims = [
            {
                'claim_id': 'claim_a',
                'claim_text': 'Supports STL format',
                'truth_status': 'fact',
                'confidence': 'high',
                'source_priority': 3,
            },
            {
                'claim_id': 'claim_b',
                'claim_text': 'Does not support STL format',
                'truth_status': 'fact',
                'confidence': 'medium',
                'source_priority': 4,
            },
        ]

        contradictions = [
            {
                'claim_a_id': 'claim_a',
                'claim_b_id': 'claim_b',
                'resolution': 'manual_review_required',
                'winning_claim_id': 'claim_a',
            }
        ]

        updated_claims = update_claims_with_contradiction_resolution(claims, contradictions)

        # Both claims should remain unchanged (manual review)
        for claim in updated_claims:
            assert claim['truth_status'] == 'fact'


class TestEvidenceMapValidation:
    """Test evidence map validation with contradictions."""

    def test_validate_evidence_map_with_contradictions_valid(self):
        """Test validation passes for valid structure."""
        evidence_map = {
            'schema_version': '1.0.0',
            'repo_url': 'https://github.com/test/repo',
            'repo_sha': 'abc123',
            'claims': [],
            'contradictions': [
                {
                    'claim_a_id': 'claim_a',
                    'claim_b_id': 'claim_b',
                    'resolution': 'prefer_higher_priority',
                    'winning_claim_id': 'claim_a',
                    'reasoning': 'Test reasoning',
                }
            ],
        }

        # Should not raise
        validate_evidence_map_with_contradictions(evidence_map)

    def test_validate_evidence_map_with_contradictions_missing_field(self):
        """Test validation fails when required field missing."""
        evidence_map = {
            'schema_version': '1.0.0',
            'repo_url': 'https://github.com/test/repo',
            'repo_sha': 'abc123',
            'claims': [],
            # Missing contradictions
        }

        with pytest.raises(ContradictionDetectionError, match="Missing required field"):
            validate_evidence_map_with_contradictions(evidence_map)

    def test_validate_evidence_map_with_contradictions_invalid_type(self):
        """Test validation fails when contradictions is not a list."""
        evidence_map = {
            'schema_version': '1.0.0',
            'repo_url': 'https://github.com/test/repo',
            'repo_sha': 'abc123',
            'claims': [],
            'contradictions': "not a list",
        }

        with pytest.raises(ContradictionDetectionError, match="contradictions must be a list"):
            validate_evidence_map_with_contradictions(evidence_map)

    def test_validate_evidence_map_with_contradictions_invalid_entry(self):
        """Test validation fails when contradiction entry is malformed."""
        evidence_map = {
            'schema_version': '1.0.0',
            'repo_url': 'https://github.com/test/repo',
            'repo_sha': 'abc123',
            'claims': [],
            'contradictions': [
                {
                    'claim_a_id': 'claim_a',
                    # Missing required fields
                }
            ],
        }

        with pytest.raises(ContradictionDetectionError, match="missing required field"):
            validate_evidence_map_with_contradictions(evidence_map)


class TestDetectContradictionsIntegration:
    """Integration tests for detect_contradictions main function."""

    def test_detect_contradictions_basic(self):
        """Test basic contradiction detection integration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            run_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create evidence_map.json with contradictory claims
            evidence_map = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'claims': [
                    {
                        'claim_id': 'claim_a',
                        'claim_text': 'Supports OBJ format',
                        'claim_kind': 'format',
                        'truth_status': 'fact',
                        'confidence': 'high',
                        'source_priority': 2,
                        'citations': [{'path': 'src/loader.py', 'start_line': 10, 'end_line': 15, 'source_type': 'source_code'}],
                    },
                    {
                        'claim_id': 'claim_b',
                        'claim_text': 'Does not support OBJ format',
                        'claim_kind': 'limitation',
                        'truth_status': 'fact',
                        'confidence': 'medium',
                        'source_priority': 6,
                        'citations': [{'path': 'README.md', 'start_line': 20, 'end_line': 20, 'source_type': 'readme_technical'}],
                    },
                ],
                'contradictions': [],
                'metadata': {},
            }
            (artifacts_dir / "evidence_map.json").write_text(json.dumps(evidence_map))

            # Detect contradictions
            result = detect_contradictions(run_dir, llm_client=None)

            # Verify contradictions were detected
            assert len(result['contradictions']) >= 1

            # Verify metadata
            assert 'metadata' in result
            assert result['metadata']['total_contradictions'] >= 1
            assert 'auto_resolved_contradictions' in result['metadata']

            # Verify artifact was updated
            updated_path = artifacts_dir / "evidence_map.json"
            assert updated_path.exists()

            with open(updated_path, 'r') as f:
                updated_map = json.load(f)

            assert len(updated_map['contradictions']) >= 1

    def test_detect_contradictions_no_conflicts(self):
        """Test contradiction detection with no conflicts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            run_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create evidence_map.json with compatible claims
            evidence_map = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'claims': [
                    {
                        'claim_id': 'claim_a',
                        'claim_text': 'Supports OBJ format',
                        'claim_kind': 'format',
                        'truth_status': 'fact',
                        'source_priority': 2,
                        'citations': [{'path': 'src/loader.py', 'start_line': 10, 'end_line': 15}],
                    },
                    {
                        'claim_id': 'claim_b',
                        'claim_text': 'Supports STL format',
                        'claim_kind': 'format',
                        'truth_status': 'fact',
                        'source_priority': 2,
                        'citations': [{'path': 'src/loader.py', 'start_line': 20, 'end_line': 25}],
                    },
                ],
                'contradictions': [],
            }
            (artifacts_dir / "evidence_map.json").write_text(json.dumps(evidence_map))

            # Detect contradictions
            result = detect_contradictions(run_dir, llm_client=None)

            # Should find no contradictions
            assert len(result['contradictions']) == 0
            assert result['metadata']['total_contradictions'] == 0

    def test_detect_contradictions_missing_evidence_map(self):
        """Test detect_contradictions fails when evidence_map.json missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            run_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Missing evidence_map.json
            with pytest.raises(FileNotFoundError, match="evidence_map.json not found"):
                detect_contradictions(run_dir, llm_client=None)

    def test_detect_contradictions_empty_claims(self):
        """Test contradiction detection with empty claims list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            run_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create evidence_map.json with empty claims
            evidence_map = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'claims': [],
                'contradictions': [],
            }
            (artifacts_dir / "evidence_map.json").write_text(json.dumps(evidence_map))

            # Should succeed with no contradictions
            result = detect_contradictions(run_dir, llm_client=None)

            assert len(result['contradictions']) == 0
            assert result['metadata']['total_contradictions'] == 0

    def test_detect_contradictions_deterministic(self):
        """Test detect_contradictions produces deterministic output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir1 = Path(tmpdir) / "run1"
            run_dir2 = Path(tmpdir) / "run2"
            run_dir1.mkdir()
            run_dir2.mkdir()

            # Setup identical evidence maps
            for run_dir in [run_dir1, run_dir2]:
                artifacts_dir = run_dir / "artifacts"
                artifacts_dir.mkdir()

                evidence_map = {
                    'schema_version': '1.0.0',
                    'repo_url': 'https://github.com/test/repo',
                    'repo_sha': 'abc123',
                    'claims': [
                        {
                            'claim_id': 'claim_a',
                            'claim_text': 'Supports OBJ format',
                            'claim_kind': 'format',
                            'truth_status': 'fact',
                            'source_priority': 2,
                            'citations': [{'path': 'src/loader.py', 'start_line': 10, 'end_line': 15}],
                        },
                        {
                            'claim_id': 'claim_b',
                            'claim_text': 'Does not support OBJ format',
                            'claim_kind': 'limitation',
                            'truth_status': 'fact',
                            'source_priority': 6,
                            'citations': [{'path': 'README.md', 'start_line': 20, 'end_line': 20}],
                        },
                    ],
                    'contradictions': [],
                }
                (artifacts_dir / "evidence_map.json").write_text(json.dumps(evidence_map))

            # Run detection twice
            result1 = detect_contradictions(run_dir1, llm_client=None)
            result2 = detect_contradictions(run_dir2, llm_client=None)

            # Compare contradiction counts (should be identical)
            assert len(result1['contradictions']) == len(result2['contradictions'])

            # Compare metadata (should be identical)
            assert result1['metadata']['total_contradictions'] == result2['metadata']['total_contradictions']

    def test_detect_contradictions_claim_downgrade(self):
        """Test losing claims are downgraded to inference with low confidence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            run_dir.mkdir()

            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create evidence_map.json with contradictory claims
            evidence_map = {
                'schema_version': '1.0.0',
                'repo_url': 'https://github.com/test/repo',
                'repo_sha': 'abc123',
                'claims': [
                    {
                        'claim_id': 'claim_a',
                        'claim_text': 'Supports FBX format',
                        'claim_kind': 'format',
                        'truth_status': 'fact',
                        'confidence': 'high',
                        'source_priority': 2,
                        'citations': [{'path': 'src/loader.py', 'start_line': 10, 'end_line': 15}],
                    },
                    {
                        'claim_id': 'claim_b',
                        'claim_text': 'Does not support FBX format',
                        'claim_kind': 'limitation',
                        'truth_status': 'fact',
                        'confidence': 'medium',
                        'source_priority': 7,
                        'citations': [{'path': 'README.md', 'start_line': 5, 'end_line': 5}],
                    },
                ],
                'contradictions': [],
            }
            (artifacts_dir / "evidence_map.json").write_text(json.dumps(evidence_map))

            # Detect contradictions
            result = detect_contradictions(run_dir, llm_client=None)

            # Find the losing claim
            losing_claim = next(c for c in result['claims'] if c['claim_id'] == 'claim_b')

            # Should be downgraded
            assert losing_claim['truth_status'] == 'inference'
            assert losing_claim['confidence'] == 'low'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
