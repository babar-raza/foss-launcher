"""Unit tests for repository URL validation (Guarantee M).

Tests enforce specs/36_repository_url_policy.md contract.
"""

import pytest

from launch.workers._git.repo_url_validator import (
    validate_repo_url,
    RepoUrlPolicyViolation,
    is_legacy_pattern_url,
    ALLOWED_FAMILIES,
    ALLOWED_PLATFORMS,
)


class TestValidProductRepos:
    """Test cases for valid product repository URLs."""

    @pytest.mark.parametrize("family", list(ALLOWED_FAMILIES))
    def test_all_families_valid(self, family):
        """All allowed families should pass validation."""
        url = f"https://github.com/test-org/aspose-{family}-foss-python"
        result = validate_repo_url(url, repo_type="product")

        assert result.family == family
        assert result.platform == "python"
        assert result.is_legacy_pattern is False

    @pytest.mark.parametrize("platform", list(ALLOWED_PLATFORMS))
    def test_all_platforms_valid(self, platform):
        """All allowed platforms should pass validation."""
        url = f"https://github.com/test-org/aspose-cells-foss-{platform}"
        result = validate_repo_url(url, repo_type="product")

        assert result.family == "cells"
        assert result.platform == platform
        assert result.is_legacy_pattern is False

    def test_standard_pattern_lowercase(self):
        """Standard pattern with lowercase names."""
        url = "https://github.com/aspose-cells/aspose-cells-foss-python"
        result = validate_repo_url(url, repo_type="product")

        assert result.family == "cells"
        assert result.platform == "python"
        assert result.organization == "aspose-cells"
        assert result.repository_name == "aspose-cells-foss-python"

    def test_standard_pattern_mixed_case(self):
        """Mixed case URLs are normalized to lowercase."""
        url = "https://github.com/Aspose-Cells/Aspose-Cells-FOSS-Python"
        result = validate_repo_url(url, repo_type="product")

        assert result.family == "cells"
        assert result.platform == "python"

    def test_url_with_git_suffix(self):
        """.git suffix should be stripped and validation passes."""
        url = "https://github.com/aspose-cells/aspose-cells-foss-python.git"
        result = validate_repo_url(url, repo_type="product")

        assert result.family == "cells"
        assert result.platform == "python"
        assert result.normalized_url == "https://github.com/aspose-cells/aspose-cells-foss-python"

    def test_different_organization(self):
        """Any valid GitHub organization should work."""
        url = "https://github.com/custom-org/aspose-words-foss-java"
        result = validate_repo_url(url, repo_type="product")

        assert result.family == "words"
        assert result.platform == "java"
        assert result.organization == "custom-org"


class TestValidSiteRepo:
    """Test cases for valid site repository URL."""

    def test_exact_site_url(self):
        """Exact site repository URL should pass."""
        url = "https://github.com/Aspose/aspose.org"
        result = validate_repo_url(url, repo_type="site")

        assert result.repo_type == "site"
        assert result.organization == "Aspose"
        assert result.repository_name == "aspose.org"

    def test_site_url_lowercase(self):
        """Site URL with lowercase should work (case-insensitive)."""
        url = "https://github.com/aspose/aspose.org"
        result = validate_repo_url(url, repo_type="site")

        assert result.repo_type == "site"

    def test_site_url_with_git_suffix(self):
        """Site URL with .git suffix should work."""
        url = "https://github.com/Aspose/aspose.org.git"
        result = validate_repo_url(url, repo_type="site")

        assert result.repo_type == "site"


class TestValidWorkflowsRepo:
    """Test cases for valid workflows repository URL."""

    def test_exact_workflows_url(self):
        """Exact workflows repository URL should pass."""
        url = "https://github.com/Aspose/aspose.org-workflows"
        result = validate_repo_url(url, repo_type="workflows")

        assert result.repo_type == "workflows"
        assert result.organization == "Aspose"
        assert result.repository_name == "aspose.org-workflows"

    def test_workflows_url_with_git_suffix(self):
        """Workflows URL with .git suffix should work."""
        url = "https://github.com/Aspose/aspose.org-workflows.git"
        result = validate_repo_url(url, repo_type="workflows")

        assert result.repo_type == "workflows"


class TestLegacyPatterns:
    """Test cases for legacy repository URL patterns."""

    def test_legacy_pattern_basic(self):
        """Legacy pattern should be accepted when allow_legacy=True."""
        url = "https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET"
        result = validate_repo_url(url, repo_type="product", allow_legacy=True)

        assert result.family == "3d"
        assert result.platform == "python"
        assert result.is_legacy_pattern is True

    def test_legacy_pattern_words_java(self):
        """Legacy Words for Java pattern."""
        url = "https://github.com/Aspose/Aspose.Words-for-Java"
        result = validate_repo_url(url, repo_type="product", allow_legacy=True)

        assert result.family == "words"
        assert result.platform == "java"
        assert result.is_legacy_pattern is True

    def test_legacy_pattern_rejected_when_not_allowed(self):
        """Legacy pattern should be rejected when allow_legacy=False."""
        url = "https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product", allow_legacy=False)

        assert exc.value.error_code == "REPO_URL_POLICY_VIOLATION"

    def test_is_legacy_pattern_helper(self):
        """is_legacy_pattern_url() helper should detect legacy URLs."""
        assert is_legacy_pattern_url("https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET") is True
        assert is_legacy_pattern_url("https://github.com/aspose-cells/aspose-cells-foss-python") is False


class TestInvalidProtocols:
    """Test cases for invalid protocols."""

    def test_git_protocol(self):
        """git:// protocol should be rejected."""
        url = "git://github.com/aspose-cells/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_PROTOCOL"
        assert "https://" in exc.value.reason

    def test_ssh_protocol(self):
        """ssh:// protocol should be rejected."""
        url = "ssh://git@github.com/aspose-cells/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_PROTOCOL"

    def test_http_protocol(self):
        """http:// (unencrypted) protocol should be rejected."""
        url = "http://github.com/aspose-cells/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_PROTOCOL"

    def test_no_protocol(self):
        """URL without protocol should be rejected."""
        url = "github.com/aspose-cells/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_PROTOCOL"


class TestInvalidHosts:
    """Test cases for invalid hosts."""

    def test_gitlab_host(self):
        """GitLab host should be rejected."""
        url = "https://gitlab.com/aspose-cells/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_HOST"
        assert "github.com" in exc.value.reason

    def test_bitbucket_host(self):
        """Bitbucket host should be rejected."""
        url = "https://bitbucket.org/aspose-cells/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_HOST"

    def test_self_hosted_git(self):
        """Self-hosted git server should be rejected."""
        url = "https://git.example.com/aspose-cells/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_HOST"


class TestInvalidFamilies:
    """Test cases for invalid product families."""

    def test_invalid_family_name(self):
        """Family not in allowed list should be rejected."""
        url = "https://github.com/test-org/aspose-invalidfamily-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_FAMILY"
        assert "invalidfamily" in exc.value.reason

    def test_typo_in_family(self):
        """Typo in family name should be rejected."""
        url = "https://github.com/test-org/aspose-celss-foss-python"  # celss instead of cells

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_FAMILY"


class TestInvalidPlatforms:
    """Test cases for invalid platforms."""

    def test_invalid_platform_name(self):
        """Platform not in allowed list should be rejected."""
        url = "https://github.com/test-org/aspose-cells-foss-invalidplatform"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_PLATFORM"
        assert "invalidplatform" in exc.value.reason

    def test_typo_in_platform(self):
        """Typo in platform name should be rejected."""
        url = "https://github.com/test-org/aspose-cells-foss-pyton"  # pyton instead of python

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_INVALID_PLATFORM"


class TestArbitraryGitHubRepos:
    """Test cases for arbitrary GitHub repositories."""

    def test_random_github_repo(self):
        """Random GitHub repository should be rejected."""
        url = "https://github.com/torvalds/linux"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_POLICY_VIOLATION"

    def test_personal_fork(self):
        """Personal fork not matching pattern should be rejected."""
        url = "https://github.com/johndoe/my-aspose-fork"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_POLICY_VIOLATION"

    def test_test_repository(self):
        """Test repository not matching pattern should be rejected."""
        url = "https://github.com/Aspose/test-repo"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_POLICY_VIOLATION"


class TestMalformedURLs:
    """Test cases for malformed URLs."""

    def test_empty_url(self):
        """Empty URL should be rejected."""
        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url("", repo_type="product")

        assert exc.value.error_code == "REPO_URL_MALFORMED"

    def test_path_traversal(self):
        """URL with path traversal should be rejected."""
        url = "https://github.com/test-org/aspose-cells-foss-python/../../../etc/passwd"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_MALFORMED"
        assert "traversal" in exc.value.reason.lower()

    def test_query_parameters(self):
        """URL with query parameters should be rejected."""
        url = "https://github.com/test-org/aspose-cells-foss-python?token=secret"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_MALFORMED"
        assert "query" in exc.value.reason.lower()

    def test_url_fragment(self):
        """URL with fragment should be rejected."""
        url = "https://github.com/test-org/aspose-cells-foss-python#readme"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert exc.value.error_code == "REPO_URL_MALFORMED"


class TestSiteRepoConstraints:
    """Test cases for site repository constraints."""

    def test_wrong_site_repo_url(self):
        """Wrong site repository URL should be rejected."""
        url = "https://github.com/Aspose/wrong-site-repo"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="site")

        assert exc.value.error_code == "REPO_URL_POLICY_VIOLATION"
        assert "aspose.org" in exc.value.reason

    def test_site_repo_wrong_org(self):
        """Site repo with wrong organization should be rejected."""
        url = "https://github.com/WrongOrg/aspose.org"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="site")

        assert exc.value.error_code == "REPO_URL_POLICY_VIOLATION"


class TestWorkflowsRepoConstraints:
    """Test cases for workflows repository constraints."""

    def test_wrong_workflows_repo_url(self):
        """Wrong workflows repository URL should be rejected."""
        url = "https://github.com/Aspose/wrong-workflows-repo"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="workflows")

        assert exc.value.error_code == "REPO_URL_POLICY_VIOLATION"
        assert "aspose.org-workflows" in exc.value.reason


class TestExceptionAttributes:
    """Test RepoUrlPolicyViolation exception attributes."""

    def test_exception_has_error_code(self):
        """Exception should include error_code attribute."""
        url = "git://github.com/test-org/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert hasattr(exc.value, "error_code")
        assert exc.value.error_code == "REPO_URL_INVALID_PROTOCOL"

    def test_exception_has_repo_url(self):
        """Exception should include repo_url attribute."""
        url = "git://github.com/test-org/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert hasattr(exc.value, "repo_url")
        assert exc.value.repo_url == url

    def test_exception_has_reason(self):
        """Exception should include reason attribute."""
        url = "git://github.com/test-org/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert hasattr(exc.value, "reason")
        assert len(exc.value.reason) > 0

    def test_exception_message_includes_policy_reference(self):
        """Exception message should reference the policy spec."""
        url = "git://github.com/test-org/aspose-cells-foss-python"

        with pytest.raises(RepoUrlPolicyViolation) as exc:
            validate_repo_url(url, repo_type="product")

        assert "specs/36_repository_url_policy.md" in str(exc.value)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_numeric_family(self):
        """Numeric family name (3d) should work."""
        url = "https://github.com/test-org/aspose-3d-foss-python"
        result = validate_repo_url(url, repo_type="product")

        assert result.family == "3d"

    def test_organization_with_hyphens(self):
        """Organization name with hyphens should work."""
        url = "https://github.com/aspose-cells-team/aspose-cells-foss-python"
        result = validate_repo_url(url, repo_type="product")

        assert result.organization == "aspose-cells-team"

    def test_whitespace_in_url(self):
        """URL with leading/trailing whitespace should be normalized."""
        url = "  https://github.com/test-org/aspose-cells-foss-python  "
        result = validate_repo_url(url, repo_type="product")

        assert result.family == "cells"
        assert result.platform == "python"
