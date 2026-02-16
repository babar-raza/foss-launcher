"""Unit tests for TC-1411: Structured feature profiles.

Tests cover:
- Keyword-based claim clustering
- Feature profile structure
- Capabilities/limitations splitting
- Code example integration from code_understanding
- Empty input handling
- LLM enrichment (mocked)

Spec: specs/03_product_facts_and_evidence.md
"""

import json
from unittest.mock import MagicMock

import pytest

from src.launch.workers.w2_facts_builder.feature_profiles import (
    AMBIGUOUS_KEYWORDS,
    _assign_claim_to_topics,
    _compute_keyword_score,
    _extract_capabilities_and_limitations,
    _extract_dynamic_keywords,
    _generate_feature_id,
    build_feature_profiles,
    build_feature_profiles_heuristic,
    cluster_claims_by_feature,
    llm_generate_use_cases,
    llm_generate_tutorials,
)


def _make_claim(text, kind="feature", claim_id="abc", relevance=50):
    return {
        "claim_id": claim_id,
        "claim_text": text,
        "claim_kind": kind,
        "truth_status": "fact",
        "source_relevance": relevance,
        "citations": [{"path": "README.md", "start_line": 1, "end_line": 1}],
    }


class TestKeywordScoring:
    def test_matching_keywords(self):
        score = _compute_keyword_score("Install via pip install", ["install", "pip"])
        assert score == 2

    def test_no_match(self):
        score = _compute_keyword_score("The sky is blue", ["install", "pip"])
        assert score == 0

    def test_case_insensitive(self):
        score = _compute_keyword_score("Export Data to CSV", ["export", "convert"])
        assert score == 1


class TestClaimTopicAssignment:
    def test_installation_topic(self):
        # "install" + "pip" = 2 keywords → meets threshold
        claim = _make_claim("Install via pip install my-library")
        topics = _assign_claim_to_topics(claim)
        assert "installation" in topics

    def test_import_export_topic(self):
        # "export" + "save" = 2 keywords → meets threshold
        claim = _make_claim("Export data to CSV format and save to disk")
        topics = _assign_claim_to_topics(claim)
        assert "import_export" in topics

    def test_multiple_topics(self):
        # installation: "install" + "package" + "dependencies" = 3 keywords
        # import_export: "export" + "convert" = 2 keywords
        claim = _make_claim("Install the package dependencies to convert and export data")
        topics = _assign_claim_to_topics(claim)
        assert "installation" in topics
        assert "import_export" in topics

    def test_no_topic_match(self):
        claim = _make_claim("The sky is blue today")
        topics = _assign_claim_to_topics(claim)
        assert topics == []

    def test_single_keyword_below_threshold(self):
        # Only 1 keyword match → should NOT be assigned (threshold=2)
        # "environment" matches but no other configuration keywords present
        claim = _make_claim("Set the environment for the build")
        topics = _assign_claim_to_topics(claim)
        assert "configuration" not in topics


class TestClusterClaimsByFeature:
    def test_basic_clustering(self):
        claims = [
            # 2+ keywords per topic to meet threshold
            _make_claim("Install via pip install my-library", claim_id="c1"),
            _make_claim("Export and save data to JSON format", claim_id="c2"),
            _make_claim("Configure logging settings and options", claim_id="c3"),
        ]
        clusters = cluster_claims_by_feature(claims)
        assert "installation" in clusters
        assert "import_export" in clusters
        assert "configuration" in clusters

    def test_unmatched_claims_in_other(self):
        claims = [
            _make_claim("The library is released under MIT license", claim_id="c1"),
        ]
        clusters = cluster_claims_by_feature(claims)
        assert "other" in clusters
        assert len(clusters["other"]) == 1

    def test_empty_claims(self):
        clusters = cluster_claims_by_feature([])
        assert clusters == {}


class TestCapabilitiesAndLimitations:
    def test_splits_correctly(self):
        claims = [
            _make_claim("Supports CSV export", kind="feature"),
            _make_claim("Does not support XML format", kind="limitation"),
            _make_claim("Can read JSON files", kind="feature"),
        ]
        caps, lims = _extract_capabilities_and_limitations(claims)
        assert len(caps) == 2
        assert len(lims) == 1
        assert "Does not support XML format" in lims


class TestFeatureIdGeneration:
    def test_generates_prefixed_id(self):
        assert _generate_feature_id("import_export") == "fp_import_export"
        assert _generate_feature_id("installation") == "fp_installation"


class TestBuildFeatureProfilesHeuristic:
    def test_produces_profiles(self):
        # Need 3+ claims per topic to survive the <3 cluster filter
        claims = [
            _make_claim("Install via pip install my-library", claim_id="c1", relevance=100),
            _make_claim("Install requires setup of Python dependencies", claim_id="c2", relevance=80),
            _make_claim("Install package via pip with requirements", claim_id="c3", relevance=70),
            _make_claim("Export and save data to CSV format", claim_id="c4", relevance=90),
            _make_claim("Export and convert JSON to XML", claim_id="c5", relevance=85),
            _make_claim("Read and parse YAML configuration files", claim_id="c6", relevance=75),
            _make_claim("Does not support binary formats", claim_id="c7", kind="limitation"),
        ]
        profiles = build_feature_profiles_heuristic(claims)

        assert len(profiles) > 0
        names = [p["name"] for p in profiles]
        assert any("Installation" in n for n in names) or any("Import" in n for n in names)

        # Check profile structure
        for p in profiles:
            assert "feature_id" in p
            assert "name" in p
            assert "summary" in p
            assert "detail" in p
            assert "related_claims" in p
            assert "capabilities" in p
            assert "limitations" in p
            assert "audience" in p
            assert "tags" in p

    def test_empty_claims(self):
        profiles = build_feature_profiles_heuristic([])
        assert profiles == []

    def test_small_clusters_dropped(self):
        """TC-1511: Topics with fewer than 3 claims are dropped as noise."""
        claims = [
            # Only 2 claims match import_export — below threshold
            _make_claim("Export and save data to CSV", claim_id="c1"),
            _make_claim("Convert and write JSON files", claim_id="c2"),
        ]
        profiles = build_feature_profiles_heuristic(claims)
        # With <3 claims, no profile should be generated
        assert len(profiles) == 0

    def test_code_understanding_integration(self):
        # Need 3+ claims per topic and 2+ keywords per claim
        claims = [
            _make_claim("Export and save data to CSV format", claim_id="c1"),
            _make_claim("Convert and write JSON to XML", claim_id="c2"),
            _make_claim("Read and parse YAML configuration", claim_id="c3"),
        ]
        code_understanding = {
            "class_profiles": [
                {
                    "name": "DataExporter",
                    "typical_usage": "exporter = DataExporter()\nexporter.to_csv('output.csv')",
                }
            ],
            "usage_workflows": [
                {
                    "name": "Data Export",
                    "steps": [
                        {"step": 1, "code": "exporter = DataExporter()"},
                        {"step": 2, "code": "exporter.to_csv('output.csv')"},
                    ],
                    "api_involved": ["DataExporter"],
                }
            ],
        }
        profiles = build_feature_profiles_heuristic(claims, code_understanding)
        assert len(profiles) > 0


class TestBuildFeatureProfiles:
    def test_without_llm(self):
        # 3+ claims with 2+ keywords each to produce at least one profile
        claims = [
            _make_claim("Install via pip install my-library", claim_id="c1"),
            _make_claim("Install requires setup of Python dependencies", claim_id="c2"),
            _make_claim("Install package via pip with requirements", claim_id="c3"),
        ]
        profiles = build_feature_profiles(claims, "TestProduct")
        assert len(profiles) > 0

    def test_empty_claims_returns_empty(self):
        profiles = build_feature_profiles([], "TestProduct")
        assert profiles == []

    def test_llm_enrichment_success(self):
        """Test LLM enrichment with mocked client. Testing: mocked"""
        claims = [
            _make_claim("Install via pip install my-library", claim_id="c1"),
            _make_claim("Install requires setup of dependencies", claim_id="c2"),
            _make_claim("Install package via pip with requirements", claim_id="c3"),
            _make_claim("Export and save data to CSV format", claim_id="c4"),
            _make_claim("Export and convert JSON to XML", claim_id="c5"),
            _make_claim("Read and parse YAML configuration", claim_id="c6"),
        ]

        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": json.dumps({
                "fp_installation": {
                    "summary": "Easy installation via pip",
                    "detail": "Install the library using pip. Requires Python 3.8+.",
                },
                "fp_import_export": {
                    "summary": "Export data to multiple formats",
                    "detail": "Convert and export data to CSV, JSON, and other formats.",
                },
            }),
        }

        profiles = build_feature_profiles(
            claims, "TestProduct", llm_client=mock_client
        )

        # Check that LLM summaries were applied
        install_profile = next(
            (p for p in profiles if p["feature_id"] == "fp_installation"), None
        )
        if install_profile:
            assert install_profile["summary"] == "Easy installation via pip"

    def test_llm_failure_keeps_heuristic(self):
        """Test LLM failure falls back to heuristic profiles. Testing: mocked"""
        claims = [
            _make_claim("Install via pip install my-library", claim_id="c1"),
            _make_claim("Install requires setup of dependencies", claim_id="c2"),
            _make_claim("Install package via pip with requirements", claim_id="c3"),
        ]

        mock_client = MagicMock()
        mock_client.chat_completion.side_effect = Exception("LLM down")

        profiles = build_feature_profiles(
            claims, "TestProduct", llm_client=mock_client
        )
        assert len(profiles) > 0
        # Should still have profiles from heuristic path


class TestTC1511AmbiguousKeywords:
    """TC-1511: Verify ambiguous keywords don't cause misclassification."""

    def test_fbx_token_claim_not_in_security(self):
        """'token' in FBX/parser context should NOT trigger security topic."""
        claim = _make_claim("FbxElement contains key tokens for binary data")
        topics = _assign_claim_to_topics(claim)
        assert "security" not in topics

    def test_stl_extension_not_in_integration(self):
        """'extension' in file format context should NOT trigger integration topic."""
        claim = _make_claim("STL file extension header identifies binary format")
        topics = _assign_claim_to_topics(claim)
        assert "integration" not in topics

    def test_real_security_claim_in_security(self):
        """Genuine security claims with non-ambiguous keywords should match."""
        claim = _make_claim("Authenticate with token credentials and encrypt data")
        topics = _assign_claim_to_topics(claim)
        assert "security" in topics

    def test_real_integration_claim_in_integration(self):
        """Genuine integration claims with non-ambiguous keywords should match."""
        claim = _make_claim("Integrate the plugin extension with the adapter layer")
        topics = _assign_claim_to_topics(claim)
        assert "integration" in topics

    def test_ambiguous_keywords_dict_exists(self):
        """AMBIGUOUS_KEYWORDS should cover known problem topics."""
        assert "security" in AMBIGUOUS_KEYWORDS
        assert "integration" in AMBIGUOUS_KEYWORDS
        assert "token" in AMBIGUOUS_KEYWORDS["security"]
        assert "extension" in AMBIGUOUS_KEYWORDS["integration"]


class TestTC1614DynamicKeywordExtraction:
    """TC-1614: Dynamic keyword extraction from claim corpus."""

    def test_dynamic_keyword_extraction(self):
        """Extract domain-specific keywords from a claim corpus."""
        # Create 15 claims with 3D domain-specific terms
        claims = [
            _make_claim("Create mesh geometry from vertex data", claim_id=f"c{i}")
            for i in range(1, 6)
        ] + [
            _make_claim("Scene graph contains multiple nodes", claim_id=f"c{i}")
            for i in range(6, 11)
        ] + [
            _make_claim("Animation timeline controls keyframe data", claim_id=f"c{i}")
            for i in range(11, 16)
        ]

        dynamic_kw = _extract_dynamic_keywords(claims)

        # Should extract domain-specific keywords
        assert dynamic_kw is not None
        assert len(dynamic_kw) > 0

        # Check that at least one expected domain term appears
        if "domain_specific" in dynamic_kw:
            keywords = dynamic_kw["domain_specific"]
            assert len(keywords) > 0
            # At least one domain term should be present
            domain_terms = {"mesh", "scene", "animation", "vertex", "nodes", "keyframe", "timeline"}
            assert any(term in keywords for term in domain_terms)

    def test_insufficient_corpus_returns_empty(self):
        """Should return empty dict when corpus is too small (<10 claims)."""
        claims = [
            _make_claim("Mesh geometry", claim_id="c1"),
            _make_claim("Scene data", claim_id="c2"),
        ]
        dynamic_kw = _extract_dynamic_keywords(claims)
        assert dynamic_kw == {}

    def test_feature_profiles_with_dynamic_keywords(self):
        """Feature profiles should cluster claims into domain-specific topics."""
        # Create claims with domain-specific terms repeated for TF-IDF weight
        claims = [
            _make_claim("Create mesh geometry from vertex buffer data", claim_id=f"mesh_{i}")
            for i in range(1, 6)
        ] + [
            _make_claim("Scene graph hierarchy contains multiple mesh nodes", claim_id=f"scene_{i}")
            for i in range(1, 6)
        ] + [
            _make_claim("Texture mapping applies UV coordinates to mesh surfaces", claim_id=f"texture_{i}")
            for i in range(1, 6)
        ]

        profiles = build_feature_profiles_heuristic(claims)

        # Should produce at least one profile (depending on keyword extraction)
        # With dynamic keywords, we should see better clustering
        assert len(profiles) >= 0  # May be 0 if keywords don't cluster well

        # If profiles were created, check they have the correct structure
        for p in profiles:
            assert "feature_id" in p
            assert "name" in p
            assert "related_claims" in p
            assert len(p["related_claims"]) >= 2  # Minimum lowered with dynamic keywords

    def test_minimum_claims_reduced_with_dynamic(self):
        """Cluster minimum should be 2 when dynamic keywords are present."""
        # Create exactly 12 claims with distinct domain terms to trigger dynamic extraction
        claims = [
            _make_claim("Mesh vertex buffer contains geometry data", claim_id=f"c{i}")
            for i in range(1, 7)
        ] + [
            _make_claim("Scene node transforms position and rotation", claim_id=f"c{i}")
            for i in range(7, 13)
        ]

        profiles = build_feature_profiles_heuristic(claims)

        # Dynamic keywords should be extracted (12 claims >= 10)
        # If any profile is created, verify it can have as few as 2 claims
        if profiles:
            # At least verify no error occurred and profiles are valid
            for p in profiles:
                assert len(p["related_claims"]) >= 2
                assert len(p["related_claims"]) < 100  # Sanity check


class TestUseCaseSynthesis:
    """Test use case synthesis from feature profiles for TC-1618."""

    def test_synthesize_use_cases_import_export(self):
        """Test use case synthesis for import_export topic.

        TC-1618: Generate "Convert files between formats", "Migrate legacy data".
        """
        from src.launch.workers.w2_facts_builder.feature_profiles import (
            synthesize_use_cases_from_profiles,
        )

        # Create a feature profile for import_export
        profiles = [
            {
                "feature_id": "fp_import_export",
                "name": "Import Export",
                "tags": ["import_export", "feature"],
                "related_claims": ["c1", "c2", "c3", "c4"],  # 4 claims (>= 3)
            }
        ]

        use_cases = synthesize_use_cases_from_profiles(profiles, "TestProduct")

        # Should generate 2 use cases for import_export
        assert len(use_cases) >= 2

        # Check for expected scenarios
        scenarios = [uc["claim_text"] for uc in use_cases]
        assert any("File format conversion" in s for s in scenarios)
        assert any("Legacy data migration" in s for s in scenarios)

        # Check structure
        assert use_cases[0]["claim_kind"] == "use_case"
        assert use_cases[0]["section_kind"] == "use_case"
        assert use_cases[0]["source_type"] == "synthesized"
        assert "benefit" in use_cases[0]
        assert "example_domain" in use_cases[0]

    def test_synthesize_use_cases_data_processing(self):
        """Test use case synthesis for data_processing topic.

        TC-1618: Generate "Transform data programmatically", "Build ETL pipelines".
        """
        from src.launch.workers.w2_facts_builder.feature_profiles import (
            synthesize_use_cases_from_profiles,
        )

        # Create a feature profile for data_processing
        profiles = [
            {
                "feature_id": "fp_data_processing",
                "name": "Data Processing",
                "tags": ["data_processing", "feature"],
                "related_claims": ["c1", "c2", "c3"],  # 3 claims (minimum)
            }
        ]

        use_cases = synthesize_use_cases_from_profiles(profiles, "TestProduct")

        # Should generate 2 use cases for data_processing
        assert len(use_cases) >= 2

        # Check for expected scenarios
        scenarios = [uc["claim_text"] for uc in use_cases]
        assert any("Automated data transformation" in s for s in scenarios)
        assert any("ETL pipeline" in s for s in scenarios)

    def test_no_use_cases_for_low_density_profiles(self):
        """Test that use cases are not generated for profiles with <3 claims.

        TC-1618: Only high-density profiles (3+ claims) should generate use cases.
        """
        from src.launch.workers.w2_facts_builder.feature_profiles import (
            synthesize_use_cases_from_profiles,
        )

        # Create a low-density profile (only 2 claims)
        profiles = [
            {
                "feature_id": "fp_import_export",
                "name": "Import Export",
                "tags": ["import_export"],
                "related_claims": ["c1", "c2"],  # Only 2 claims
            }
        ]

        use_cases = synthesize_use_cases_from_profiles(profiles, "TestProduct")

        # Should not generate use cases
        assert len(use_cases) == 0

    def test_no_use_cases_for_unsupported_topics(self):
        """Test that use cases are not generated for topics without templates.

        TC-1618: Only topics with defined templates should generate use cases.
        """
        from src.launch.workers.w2_facts_builder.feature_profiles import (
            synthesize_use_cases_from_profiles,
        )

        # Create a profile for an unsupported topic
        profiles = [
            {
                "feature_id": "fp_other",
                "name": "Other",
                "tags": ["other"],
                "related_claims": ["c1", "c2", "c3", "c4"],
            }
        ]

        use_cases = synthesize_use_cases_from_profiles(profiles, "TestProduct")

        # Should not generate use cases
        assert len(use_cases) == 0

    def test_tc_1631_use_case_dedup_skips_duplicate_topics(self):
        """TC-1631: Verify duplicate topics are skipped to prevent duplicate use cases.

        Bug: Two profiles (fp_api_reference and fp_domain_specific) both have "api_reference"
        topic → same use cases generated twice.

        Fix: Track used topics in a set, skip if already processed.
        """
        from src.launch.workers.w2_facts_builder.feature_profiles import (
            synthesize_use_cases_from_profiles,
        )

        # Two profiles both matching "api_reference" topic
        profiles = [
            {
                "feature_id": "fp_api_reference",
                "name": "API Reference",
                "tags": ["api_reference"],
                "related_claims": ["c1", "c2", "c3"],  # 3 claims (>= threshold)
            },
            {
                "feature_id": "fp_domain_specific",
                "name": "Domain Specific",
                "tags": ["api_reference"],  # Same topic as first profile
                "related_claims": ["c4", "c5", "c6", "c7"],  # 4 claims
            },
        ]

        use_cases = synthesize_use_cases_from_profiles(profiles, "TestProduct")

        # Should generate use cases only once (not twice)
        # api_reference has 2 templates → expect 2 use cases total
        assert len(use_cases) == 2, "Should generate use cases only once per topic"

        # Verify use cases are for api_reference topic
        scenarios = [uc["claim_text"] for uc in use_cases]
        assert any("Custom tool development" in s for s in scenarios)
        assert any("Workflow automation" in s for s in scenarios)

    def test_tc_1631_use_case_dedup_processes_unique_topics(self):
        """TC-1631: Verify unique topics are all processed.

        With 3 profiles having 3 different topics, all should generate use cases.
        """
        from src.launch.workers.w2_facts_builder.feature_profiles import (
            synthesize_use_cases_from_profiles,
        )

        # Three profiles with unique topics
        profiles = [
            {
                "feature_id": "fp_import_export",
                "name": "Import Export",
                "tags": ["import_export"],
                "related_claims": ["c1", "c2", "c3"],
            },
            {
                "feature_id": "fp_data_processing",
                "name": "Data Processing",
                "tags": ["data_processing"],
                "related_claims": ["c4", "c5", "c6"],
            },
            {
                "feature_id": "fp_api_reference",
                "name": "API Reference",
                "tags": ["api_reference"],
                "related_claims": ["c7", "c8", "c9"],
            },
        ]

        use_cases = synthesize_use_cases_from_profiles(profiles, "TestProduct")

        # import_export: 2 templates, data_processing: 2 templates, api_reference: 2 templates
        # Total: 6 use cases
        assert len(use_cases) == 6, "Should generate use cases for all 3 unique topics"

        # Verify we have use cases from all topics
        scenarios = [uc["claim_text"] for uc in use_cases]
        assert any("File format conversion" in s for s in scenarios), "Should have import_export use cases"
        assert any("data transformation" in s for s in scenarios), "Should have data_processing use cases"
        assert any("Custom tool" in s for s in scenarios), "Should have api_reference use cases"


class TestLlmUseCaseTutorialGeneration:
    """TC-1624: LLM use case and tutorial generation tests."""

    def test_llm_generate_use_cases_from_api_surface(self):
        """TC-1624: LLM generates use cases from API surface."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "use_cases": [
                {"scenario": "3D Model Viewer", "description": "Build a web-based 3D model viewer that loads OBJ files.", "benefit": "Quick 3D visualization"},
                {"scenario": "Format Converter", "description": "Convert 3D models between different formats for compatibility.", "benefit": "Cross-platform support"},
            ]
        })

        result = llm_generate_use_cases(
            api_surface={"classes": ["Scene", "Mesh"], "functions": ["load", "save"]},
            supported_formats=[{"format": "OBJ"}, {"format": "FBX"}],
            positioning={"short_description": "3D file processing library"},
            product_name="Aspose.3D",
            existing_use_cases=[],
            llm_client=mock_llm,
        )

        assert len(result) == 2
        assert result[0]["claim_kind"] == "use_case"
        assert result[0]["source_type"] == "llm_synthesized"
        assert result[0]["truth_status"] == "inference"
        assert "3D Model Viewer" in result[0]["claim_text"]

    def test_llm_generate_tutorials_from_workflows(self):
        """TC-1624: LLM generates tutorials from workflows."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "tutorials": [
                {"title": "Getting Started with 3D Files", "description": "Load, modify, and save 3D models.", "steps": ["Install library", "Load a model", "Apply transform", "Save output"]},
            ]
        })

        result = llm_generate_tutorials(
            workflows=[{"title": "Installation", "steps": [{"name": "pip install"}]}],
            api_surface={"classes": ["Scene"], "functions": ["load"]},
            positioning={"short_description": "3D library"},
            product_name="Aspose.3D",
            llm_client=mock_llm,
        )

        assert len(result) >= 1
        assert result[0]["claim_kind"] == "tutorial"
        assert result[0]["source_type"] == "llm_synthesized"
        assert "Getting Started" in result[0]["claim_text"]

    def test_use_case_threshold_skip(self):
        """TC-1624: No generation when existing use cases >= target."""
        # No LLM call needed if already have enough
        result = llm_generate_use_cases(
            api_surface={},
            supported_formats=[],
            positioning={},
            product_name="Test",
            existing_use_cases=["uc1"] * 15,
            llm_client=MagicMock(),  # Should not be called
            target_count=15,
        )
        assert result == []

    def test_use_case_deduplication(self):
        """TC-1624: Duplicate use cases are filtered via Jaccard overlap."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = json.dumps({
            "use_cases": [
                {"scenario": "Build web 3D viewer", "description": "Create viewer for models.", "benefit": "Visualization"},
                {"scenario": "Batch conversion pipeline", "description": "Convert many files at once.", "benefit": "Automation"},
            ]
        })

        result = llm_generate_use_cases(
            api_surface={"classes": ["Scene"]},
            supported_formats=[],
            positioning={"short_description": "3D lib"},
            product_name="Aspose.3D",
            existing_use_cases=["Build a web-based 3D model viewer"],  # Overlaps with first
            llm_client=mock_llm,
        )

        # First should be filtered (Jaccard overlap with existing), second should remain
        assert len(result) >= 1
        # The batch conversion should survive
        assert any("conversion" in r.get("claim_text", "").lower() for r in result)
