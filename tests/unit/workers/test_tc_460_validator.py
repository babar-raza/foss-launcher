"""TC-460: W7 Validator worker tests.

This module tests the W7 Validator worker implementation per
specs/09_validation_gates.md and specs/21_worker_contracts.md:253-282.

Test coverage:
1. Gate execution (individual gates)
2. Issue collection and categorization
3. Severity assignment (BLOCKER, WARNING, INFO)
4. Deterministic ordering (by gate_id, then by issue_id)
5. Event emission
6. Artifact validation
7. Error handling (missing files, malformed patches)
8. Schema validation gate
9. Template token lint gate
10. Consistency gate
11. Test determinism gate
12. Issue sorting (deterministic)
13. Frontmatter YAML validation
14. Overall validation report generation
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.launch.workers.w7_validator import (
    execute_validator,
    ValidatorError,
    ValidatorArtifactMissingError,
)
from src.launch.workers.w7_validator.worker import (
    emit_event,
    load_json_artifact,
    find_markdown_files,
    parse_frontmatter,
    check_unresolved_tokens,
    validate_frontmatter_yaml,
    gate_1_schema_validation,
    gate_10_consistency,
    gate_11_template_token_lint,
    gate_t_test_determinism,
    sort_issues,
)


@pytest.fixture
def temp_run_dir():
    """Create temporary run directory with required structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "run_001"
        run_dir.mkdir()

        # Create required subdirectories
        (run_dir / "artifacts").mkdir()
        (run_dir / "reports").mkdir()
        (run_dir / "work" / "site" / "content").mkdir(parents=True)

        # Create events.ndjson
        (run_dir / "events.ndjson").write_text("")

        yield run_dir


@pytest.fixture
def sample_run_config():
    """Sample run configuration."""
    return {
        "validation_profile": "local",
        "product_slug": "test-product",
        "launch_tier": "standard",
    }


@pytest.fixture
def sample_product_facts(temp_run_dir):
    """Create sample product_facts.json."""
    product_facts = {
        "schema_version": "1.0",
        "product_name": "Test Product",
        "repo_url": "https://github.com/test/test-product",
        "programming_languages": ["python"],
    }

    artifact_path = temp_run_dir / "artifacts" / "product_facts.json"
    with artifact_path.open("w") as f:
        json.dump(product_facts, f, indent=2)

    return product_facts


@pytest.fixture
def sample_page_plan(temp_run_dir):
    """Create sample page_plan.json."""
    page_plan = {
        "schema_version": "1.0",
        "product_slug": "test-product",
        "launch_tier": "standard",
        "pages": [
            {
                "section": "docs",
                "slug": "getting-started",
                "output_path": "content/docs/getting-started.md",
                "title": "Getting Started",
            }
        ],
    }

    artifact_path = temp_run_dir / "artifacts" / "page_plan.json"
    with artifact_path.open("w") as f:
        json.dump(page_plan, f, indent=2)

    return page_plan


# Test 1: Event emission
def test_emit_event(temp_run_dir):
    """Test event emission to events.ndjson."""
    emit_event(
        temp_run_dir,
        "VALIDATOR_STARTED",
        {"profile": "local"},
        trace_id="trace-123",
        span_id="span-456",
    )

    events_file = temp_run_dir / "events.ndjson"
    assert events_file.exists()

    content = events_file.read_text()
    assert "VALIDATOR_STARTED" in content
    assert "trace-123" in content
    assert "span-456" in content


# Test 2: Load JSON artifact success
def test_load_json_artifact_success(temp_run_dir, sample_product_facts):
    """Test loading existing JSON artifact."""
    result = load_json_artifact(temp_run_dir, "product_facts.json")
    assert result["product_name"] == "Test Product"
    assert result["repo_url"] == "https://github.com/test/test-product"


# Test 3: Load JSON artifact missing
def test_load_json_artifact_missing(temp_run_dir):
    """Test loading non-existent artifact raises error."""
    with pytest.raises(ValidatorArtifactMissingError):
        load_json_artifact(temp_run_dir, "missing_artifact.json")


# Test 4: Find markdown files
def test_find_markdown_files(temp_run_dir):
    """Test finding markdown files in site worktree."""
    site_dir = temp_run_dir / "work" / "site"

    # Create some markdown files
    (site_dir / "content" / "docs").mkdir(parents=True, exist_ok=True)
    (site_dir / "content" / "docs" / "guide.md").write_text("# Guide")
    (site_dir / "content" / "overview.md").write_text("# Overview")

    md_files = find_markdown_files(site_dir)

    assert len(md_files) == 2
    assert any("guide.md" in str(f) for f in md_files)
    assert any("overview.md" in str(f) for f in md_files)

    # Check deterministic ordering (sorted)
    assert md_files == sorted(md_files)


# Test 5: Parse frontmatter success
def test_parse_frontmatter_success():
    """Test parsing valid YAML frontmatter."""
    content = """---
title: Test Page
author: Test Author
---

# Content here
"""

    frontmatter, body = parse_frontmatter(content)

    assert frontmatter is not None
    assert frontmatter["title"] == "Test Page"
    assert frontmatter["author"] == "Test Author"
    assert "# Content here" in body


# Test 6: Parse frontmatter missing
def test_parse_frontmatter_missing():
    """Test parsing content without frontmatter."""
    content = "# Just a heading\n\nSome content."

    frontmatter, body = parse_frontmatter(content)

    assert frontmatter is None
    assert body == content


# Test 7: Check unresolved tokens
def test_check_unresolved_tokens(temp_run_dir):
    """Test detection of unresolved template tokens."""
    content = """# Test Page

This page has __PRODUCT_NAME__ and __VERSION__ tokens.

Some normal content here.
"""

    file_path = temp_run_dir / "test.md"
    issues = check_unresolved_tokens(content, file_path)

    assert len(issues) == 2
    assert any("__PRODUCT_NAME__" in issue["message"] for issue in issues)
    assert any("__VERSION__" in issue["message"] for issue in issues)
    assert all(issue["severity"] == "blocker" for issue in issues)
    assert all(issue["error_code"] == "GATE_TEMPLATE_TOKEN_UNRESOLVED" for issue in issues)


# Test 8: Check unresolved tokens in code blocks (should be ignored)
def test_check_unresolved_tokens_in_code_blocks(temp_run_dir):
    """Test that tokens in code blocks are ignored."""
    content = """# Test Page

Normal content with __TOKEN1__.

```python
# This __TOKEN2__ should be ignored
print("__TOKEN3__")
```

Another __TOKEN4__ outside code.
"""

    file_path = temp_run_dir / "test.md"
    issues = check_unresolved_tokens(content, file_path)

    # Should only find TOKEN1 and TOKEN4 (not TOKEN2 and TOKEN3 in code block)
    assert len(issues) == 2
    assert any("__TOKEN1__" in issue["message"] for issue in issues)
    assert any("__TOKEN4__" in issue["message"] for issue in issues)


# Test 9: Validate frontmatter YAML
def test_validate_frontmatter_yaml(temp_run_dir):
    """Test frontmatter YAML validation."""
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)

    # Valid frontmatter
    (site_dir / "content" / "valid.md").write_text("""---
title: Valid Page
---
Content
""")

    # Missing frontmatter
    (site_dir / "content" / "missing.md").write_text("# Just content")

    md_files = [
        site_dir / "content" / "valid.md",
        site_dir / "content" / "missing.md",
    ]

    issues = validate_frontmatter_yaml(md_files)

    # Should have one issue for missing frontmatter
    assert len(issues) == 1
    assert issues[0]["severity"] == "warn"
    assert "missing" in issues[0]["issue_id"]


# Test 10: Gate 1 - Schema validation
def test_gate_1_schema_validation(temp_run_dir, sample_product_facts, sample_page_plan, sample_run_config):
    """Test Gate 1: Schema validation."""
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)

    # Create valid markdown with frontmatter
    (site_dir / "content" / "test.md").write_text("""---
title: Test
---
Content
""")

    gate_passed, issues = gate_1_schema_validation(
        temp_run_dir, sample_run_config, "local"
    )

    # Should pass with no critical issues
    assert gate_passed or len([i for i in issues if i["severity"] in ["blocker", "error"]]) == 0


# Test 11: Gate 10 - Consistency check
def test_gate_10_consistency(temp_run_dir, sample_product_facts, sample_page_plan, sample_run_config):
    """Test Gate 10: Consistency validation."""
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)

    # Create markdown with matching repo_url
    (site_dir / "content" / "test.md").write_text("""---
title: Test
repo_url: https://github.com/test/test-product
---
Content
""")

    gate_passed, issues = gate_10_consistency(temp_run_dir, sample_run_config, "local")

    # Should pass - product slug matches
    assert gate_passed


# Test 12: Gate 10 - Consistency check with mismatch
def test_gate_10_consistency_mismatch(temp_run_dir, sample_product_facts, sample_run_config):
    """Test Gate 10: Consistency validation with mismatch."""
    # Create page_plan with mismatched product_slug
    page_plan = {
        "schema_version": "1.0",
        "product_slug": "different-product",  # Mismatch!
        "launch_tier": "standard",
        "pages": [],
    }

    artifact_path = temp_run_dir / "artifacts" / "page_plan.json"
    with artifact_path.open("w") as f:
        json.dump(page_plan, f, indent=2)

    gate_passed, issues = gate_10_consistency(temp_run_dir, sample_run_config, "local")

    # Should fail due to product name mismatch
    assert not gate_passed
    assert len(issues) > 0
    assert any("product name" in issue["message"].lower() for issue in issues)


# Test 13: Gate 11 - Template token lint
def test_gate_11_template_token_lint(temp_run_dir, sample_run_config):
    """Test Gate 11: Template token lint."""
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)

    # Create markdown with unresolved tokens
    (site_dir / "content" / "test.md").write_text("""---
title: Test
---

This has __UNRESOLVED_TOKEN__ in it.
""")

    gate_passed, issues = gate_11_template_token_lint(
        temp_run_dir, sample_run_config, "local"
    )

    # Should fail due to unresolved token
    assert not gate_passed
    assert len(issues) > 0
    assert any("UNRESOLVED_TOKEN" in issue["message"] for issue in issues)


# Test 14: Gate 11 - Template token lint passes
def test_gate_11_template_token_lint_passes(temp_run_dir, sample_run_config):
    """Test Gate 11: Template token lint with clean content."""
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)

    # Create markdown without unresolved tokens
    (site_dir / "content" / "test.md").write_text("""---
title: Test
---

This is clean content.
""")

    gate_passed, issues = gate_11_template_token_lint(
        temp_run_dir, sample_run_config, "local"
    )

    # Should pass
    assert gate_passed
    assert len(issues) == 0


# Test 15: Issue sorting determinism
def test_sort_issues_determinism():
    """Test deterministic issue sorting."""
    issues = [
        {
            "issue_id": "issue_3",
            "gate": "gate_11",
            "severity": "warn",
            "message": "Warning 1",
            "status": "OPEN",
        },
        {
            "issue_id": "issue_1",
            "gate": "gate_1",
            "severity": "blocker",
            "message": "Blocker 1",
            "error_code": "CODE1",
            "status": "OPEN",
        },
        {
            "issue_id": "issue_2",
            "gate": "gate_10",
            "severity": "error",
            "message": "Error 1",
            "error_code": "CODE2",
            "status": "OPEN",
        },
        {
            "issue_id": "issue_4",
            "gate": "gate_1",
            "severity": "blocker",
            "message": "Blocker 2",
            "error_code": "CODE3",
            "status": "OPEN",
        },
    ]

    sorted_issues = sort_issues(issues)

    # Check sorting: blocker < error < warn
    severities = [issue["severity"] for issue in sorted_issues]
    assert severities == ["blocker", "blocker", "error", "warn"]

    # Within same severity, sorted by gate then issue_id
    assert sorted_issues[0]["issue_id"] == "issue_1"  # gate_1, blocker
    assert sorted_issues[1]["issue_id"] == "issue_4"  # gate_1, blocker


# Test 16: Execute validator - full integration
def test_execute_validator_success(temp_run_dir, sample_product_facts, sample_page_plan, sample_run_config):
    """Test full validator execution with passing gates."""
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)

    # Create clean markdown
    (site_dir / "content" / "test.md").write_text("""---
title: Test Page
repo_url: https://github.com/test/test-product
---

# Test Page

Clean content without issues.
""")

    result = execute_validator(temp_run_dir, sample_run_config)

    # Check result structure
    assert "schema_version" in result
    assert "ok" in result
    assert "profile" in result
    assert "gates" in result
    assert "issues" in result

    assert result["profile"] == "local"
    assert isinstance(result["gates"], list)
    assert isinstance(result["issues"], list)

    # Check validation_report.json was written
    report_path = temp_run_dir / "artifacts" / "validation_report.json"
    assert report_path.exists()

    with report_path.open() as f:
        report = json.load(f)
        assert report["schema_version"] == "1.0"
        assert "ok" in report


# Test 17: Execute validator - with failures
def test_execute_validator_with_failures(temp_run_dir, sample_product_facts, sample_page_plan, sample_run_config):
    """Test validator execution with failing gates."""
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)

    # Create markdown with unresolved tokens
    (site_dir / "content" / "bad.md").write_text("""---
title: Bad Page
---

This has __UNRESOLVED__ tokens.
""")

    result = execute_validator(temp_run_dir, sample_run_config)

    # Should have failures
    assert len(result["issues"]) > 0
    assert any(not gate["ok"] for gate in result["gates"])

    # Check issues are sorted
    if len(result["issues"]) > 1:
        issues = result["issues"]
        severity_rank = {"blocker": 0, "error": 1, "warn": 2, "info": 3}
        for i in range(len(issues) - 1):
            rank1 = severity_rank.get(issues[i]["severity"], 3)
            rank2 = severity_rank.get(issues[i + 1]["severity"], 3)
            assert rank1 <= rank2


# Test 18: Validation profile handling
def test_validation_profile_handling(temp_run_dir, sample_product_facts, sample_page_plan):
    """Test different validation profiles."""
    run_config_ci = {
        "validation_profile": "ci",
        "product_slug": "test-product",
    }

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)
    (site_dir / "content" / "test.md").write_text("# Test")

    result = execute_validator(temp_run_dir, run_config_ci)

    assert result["profile"] == "ci"


# Test 19: Event emission during validation
def test_event_emission_during_validation(temp_run_dir, sample_product_facts, sample_page_plan, sample_run_config):
    """Test that events are emitted during validation."""
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)
    (site_dir / "content" / "test.md").write_text("# Test")

    execute_validator(temp_run_dir, sample_run_config)

    events_file = temp_run_dir / "events.ndjson"
    content = events_file.read_text()

    # Should have VALIDATOR_STARTED and VALIDATOR_COMPLETED events
    assert "VALIDATOR_STARTED" in content
    assert "VALIDATOR_COMPLETED" in content
    assert "ARTIFACT_WRITTEN" in content


# Test 20: Deterministic output (stable ordering)
def test_deterministic_output(temp_run_dir, sample_product_facts, sample_page_plan, sample_run_config):
    """Test that validator produces deterministic output."""
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "content").mkdir(parents=True, exist_ok=True)

    # Create multiple files with issues
    for i in range(3):
        (site_dir / "content" / f"test_{i}.md").write_text(
            f"# Test {i}\n\n__TOKEN_{i}__"
        )

    result1 = execute_validator(temp_run_dir, sample_run_config)

    # Remove validation report to run again
    (temp_run_dir / "artifacts" / "validation_report.json").unlink()

    result2 = execute_validator(temp_run_dir, sample_run_config)

    # Results should have same issue structure (sorted deterministically)
    assert len(result1["issues"]) == len(result2["issues"])

    # Check issue order is identical
    for i in range(len(result1["issues"])):
        assert result1["issues"][i]["issue_id"] == result2["issues"][i]["issue_id"]
        assert result1["issues"][i]["severity"] == result2["issues"][i]["severity"]
