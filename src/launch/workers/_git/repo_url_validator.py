"""Repository URL validation and policy enforcement (Guarantee L).

All git clone operations must validate repository URLs against the allowed
patterns defined in specs/36_repository_url_policy.md.

Binding contract: specs/36_repository_url_policy.md
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from typing import Literal, Optional


# Exhaustive list of allowed product families (specs/36:37-59)
ALLOWED_FAMILIES = frozenset([
    "3d",
    "barcode",
    "cad",
    "cells",
    "diagram",
    "email",
    "finance",
    "font",
    "gis",
    "html",
    "imaging",
    "note",
    "ocr",
    "page",
    "pdf",
    "psd",
    "slides",
    "svg",
    "tasks",
    "tex",
    "words",
    "zip",
])

# Exhaustive list of allowed platforms (specs/36:61-79)
ALLOWED_PLATFORMS = frozenset([
    "android",
    "cpp",
    "dotnet",
    "go",
    "java",
    "javascript",
    "net",
    "nodejs",
    "php",
    "python",
    "ruby",
    "rust",
    "swift",
    "typescript",
])

# Fixed site repository URL
SITE_REPO_URL = "https://github.com/Aspose/aspose.org"

# Fixed workflows repository URL
WORKFLOWS_REPO_URL = "https://github.com/Aspose/aspose.org-workflows"

# Standard product repository pattern
# https://github.com/{org}/aspose-{family}-foss-{platform}
PRODUCT_REPO_PATTERN = re.compile(
    r"^https://github\.com/"
    r"(?P<org>[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)"
    r"/aspose-(?P<family>[a-z0-9]+)-foss-(?P<platform>[a-z0-9]+)"
    r"(?:\.git)?$",
    re.IGNORECASE
)

# Legacy repository pattern (temporary compatibility)
# https://github.com/{org}/Aspose.{Family}-for-{Platform}-via-.NET
LEGACY_REPO_PATTERN = re.compile(
    r"^https://github\.com/"
    r"(?P<org>[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)"
    r"/Aspose\.(?P<family>[a-zA-Z0-9]+)-for-(?P<platform>[a-zA-Z0-9]+)(?:-via-\.NET)?"
    r"(?:\.git)?$",
    re.IGNORECASE
)

# Legacy FOSS repository pattern (for existing pilot repos)
# https://github.com/{org}/Aspose.{Family}-FOSS-for-{Platform}
LEGACY_FOSS_REPO_PATTERN = re.compile(
    r"^https://github\.com/"
    r"(?P<org>[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)"
    r"/Aspose\.(?P<family>[a-zA-Z0-9]+)-FOSS-for-(?P<platform>[a-zA-Z0-9]+)"
    r"(?:\.git)?$",
    re.IGNORECASE
)


class RepoUrlPolicyViolation(Exception):
    """Raised when repository URL violates policy (Guarantee L).

    Per specs/36_repository_url_policy.md, this exception is raised when:
    - URL protocol is not HTTPS
    - URL host is not github.com
    - Repository name doesn't match allowed patterns
    - Family or platform is not in allowlist
    - URL structure is malformed

    Attributes:
        error_code: Error code from specs/36 (e.g., REPO_URL_POLICY_VIOLATION)
        repo_url: The repository URL that was rejected
        reason: Human-readable explanation of why validation failed
    """

    def __init__(self, error_code: str, repo_url: str, reason: str):
        self.error_code = error_code
        self.repo_url = repo_url
        self.reason = reason
        super().__init__(
            f"Repository URL policy violation ({error_code}): {reason}\n"
            f"URL: {repo_url}\n"
            f"Policy: specs/36_repository_url_policy.md"
        )


@dataclass(frozen=True)
class ValidatedRepoUrl:
    """Result of repository URL validation.

    Attributes:
        original_url: The original URL provided for validation
        normalized_url: Normalized URL (lowercase, no .git suffix)
        repo_type: Type of repository (product/site/workflows)
        family: Product family (e.g., 'cells', '3d') - None for site/workflows
        platform: Target platform (e.g., 'python', 'java') - None for site/workflows
        organization: GitHub organization name
        repository_name: GitHub repository name
        is_legacy_pattern: True if URL uses legacy naming pattern
    """

    original_url: str
    normalized_url: str
    repo_type: Literal["product", "site", "workflows"]
    family: Optional[str]
    platform: Optional[str]
    organization: str
    repository_name: str
    is_legacy_pattern: bool


def _normalize_url(url: str) -> str:
    """Normalize repository URL for validation.

    Normalization steps:
    1. Strip leading/trailing whitespace
    2. Remove trailing .git suffix if present
    3. Convert to lowercase for case-insensitive matching

    Args:
        url: Raw repository URL

    Returns:
        Normalized URL
    """
    normalized = url.strip()

    # Remove .git suffix (case-insensitive)
    if normalized.lower().endswith(".git"):
        normalized = normalized[:-4]

    return normalized


def _validate_url_structure(url: str) -> None:
    """Validate basic URL structure.

    Checks:
    - URL is not empty
    - URL can be parsed
    - No path traversal sequences
    - No query parameters or fragments

    Args:
        url: URL to validate

    Raises:
        RepoUrlPolicyViolation: If URL structure is invalid
    """
    if not url:
        raise RepoUrlPolicyViolation(
            error_code="REPO_URL_MALFORMED",
            repo_url=url,
            reason="Repository URL is empty or None"
        )

    # Parse URL
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        raise RepoUrlPolicyViolation(
            error_code="REPO_URL_MALFORMED",
            repo_url=url,
            reason=f"URL parsing failed: {e}"
        )

    # Check for path traversal
    if ".." in parsed.path or "/./" in parsed.path:
        raise RepoUrlPolicyViolation(
            error_code="REPO_URL_MALFORMED",
            repo_url=url,
            reason="Path traversal sequences (.., /./) are forbidden"
        )

    # Check for query parameters or fragments
    if parsed.query or parsed.fragment:
        raise RepoUrlPolicyViolation(
            error_code="REPO_URL_MALFORMED",
            repo_url=url,
            reason="Query parameters and fragments are forbidden in repository URLs"
        )


def _validate_protocol(url: str) -> None:
    """Validate URL protocol is HTTPS.

    Args:
        url: URL to validate

    Raises:
        RepoUrlPolicyViolation: If protocol is not HTTPS
    """
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme.lower() != "https":
        raise RepoUrlPolicyViolation(
            error_code="REPO_URL_INVALID_PROTOCOL",
            repo_url=url,
            reason=f"Protocol must be 'https://', got '{parsed.scheme}://'. "
                   f"git://, ssh://, and http:// are forbidden."
        )


def _validate_host(url: str) -> None:
    """Validate URL host is github.com.

    Args:
        url: URL to validate

    Raises:
        RepoUrlPolicyViolation: If host is not github.com
    """
    parsed = urllib.parse.urlparse(url)

    if parsed.netloc.lower() != "github.com":
        raise RepoUrlPolicyViolation(
            error_code="REPO_URL_INVALID_HOST",
            repo_url=url,
            reason=f"Host must be 'github.com', got '{parsed.netloc}'. "
                   f"Only GitHub repositories are allowed."
        )


def _normalize_legacy_family(family: str) -> str:
    """Normalize legacy family name to standard format.

    Examples:
        '3D' -> '3d'
        'Words' -> 'words'
        'PDF' -> 'pdf'

    Args:
        family: Legacy family name

    Returns:
        Normalized family name (lowercase)
    """
    return family.lower()


def _normalize_legacy_platform(platform: str) -> str:
    """Normalize legacy platform name to standard format.

    Examples:
        'Python-via-.NET' -> 'python'
        'Java' -> 'java'
        'NET' -> 'dotnet'

    Args:
        platform: Legacy platform name

    Returns:
        Normalized platform name (lowercase, stripped of '-via-.NET')
    """
    normalized = platform.lower()

    # Handle .NET special cases
    if normalized == "net":
        return "dotnet"

    # Strip '-via-' suffix if present
    if "-via-" in normalized:
        normalized = normalized.split("-via-")[0]

    return normalized


def _validate_product_repo(
    url: str,
    normalized_url: str,
    allow_legacy: bool
) -> ValidatedRepoUrl:
    """Validate product repository URL.

    Checks URL against standard and legacy patterns.

    Args:
        url: Original URL
        normalized_url: Normalized URL for matching
        allow_legacy: Whether to allow legacy URL patterns

    Returns:
        ValidatedRepoUrl with extracted metadata

    Raises:
        RepoUrlPolicyViolation: If URL doesn't match allowed patterns
    """
    # Try standard pattern first
    match = PRODUCT_REPO_PATTERN.match(normalized_url)
    if match:
        org = match.group("org")
        family = match.group("family").lower()
        platform = match.group("platform").lower()

        # Validate family
        if family not in ALLOWED_FAMILIES:
            raise RepoUrlPolicyViolation(
                error_code="REPO_URL_INVALID_FAMILY",
                repo_url=url,
                reason=f"Product family '{family}' is not in allowed list. "
                       f"Allowed families: {', '.join(sorted(ALLOWED_FAMILIES))}"
            )

        # Validate platform
        if platform not in ALLOWED_PLATFORMS:
            raise RepoUrlPolicyViolation(
                error_code="REPO_URL_INVALID_PLATFORM",
                repo_url=url,
                reason=f"Platform '{platform}' is not in allowed list. "
                       f"Allowed platforms: {', '.join(sorted(ALLOWED_PLATFORMS))}"
            )

        return ValidatedRepoUrl(
            original_url=url,
            normalized_url=normalized_url,
            repo_type="product",
            family=family,
            platform=platform,
            organization=org,
            repository_name=f"aspose-{family}-foss-{platform}",
            is_legacy_pattern=False
        )

    # Try legacy pattern if allowed
    if allow_legacy:
        match = LEGACY_REPO_PATTERN.match(normalized_url)
        if match:
            org = match.group("org")
            family = _normalize_legacy_family(match.group("family"))
            platform = _normalize_legacy_platform(match.group("platform"))

            # Validate normalized family
            if family not in ALLOWED_FAMILIES:
                raise RepoUrlPolicyViolation(
                    error_code="REPO_URL_INVALID_FAMILY",
                    repo_url=url,
                    reason=f"Product family '{family}' (normalized from legacy) is not in allowed list. "
                           f"Allowed families: {', '.join(sorted(ALLOWED_FAMILIES))}"
                )

            # Validate normalized platform
            if platform not in ALLOWED_PLATFORMS:
                raise RepoUrlPolicyViolation(
                    error_code="REPO_URL_INVALID_PLATFORM",
                    repo_url=url,
                    reason=f"Platform '{platform}' (normalized from legacy) is not in allowed list. "
                           f"Allowed platforms: {', '.join(sorted(ALLOWED_PLATFORMS))}"
                )

            # Extract original repository name from URL
            repo_name = normalized_url.split('/')[-1]

            return ValidatedRepoUrl(
                original_url=url,
                normalized_url=normalized_url,
                repo_type="product",
                family=family,
                platform=platform,
                organization=org,
                repository_name=repo_name,
                is_legacy_pattern=True
            )

        # Try legacy FOSS pattern
        match = LEGACY_FOSS_REPO_PATTERN.match(normalized_url)
        if match:
            org = match.group("org")
            family = _normalize_legacy_family(match.group("family"))
            platform = _normalize_legacy_platform(match.group("platform"))

            if family not in ALLOWED_FAMILIES:
                raise RepoUrlPolicyViolation(
                    error_code="REPO_URL_INVALID_FAMILY",
                    repo_url=url,
                    reason=f"Product family '{family}' (normalized from legacy FOSS) is not in allowed list. "
                           f"Allowed families: {', '.join(sorted(ALLOWED_FAMILIES))}"
                )

            if platform not in ALLOWED_PLATFORMS:
                raise RepoUrlPolicyViolation(
                    error_code="REPO_URL_INVALID_PLATFORM",
                    repo_url=url,
                    reason=f"Platform '{platform}' (normalized from legacy FOSS) is not in allowed list. "
                           f"Allowed platforms: {', '.join(sorted(ALLOWED_PLATFORMS))}"
                )

            repo_name = normalized_url.split('/')[-1]

            return ValidatedRepoUrl(
                original_url=url,
                normalized_url=normalized_url,
                repo_type="product",
                family=family,
                platform=platform,
                organization=org,
                repository_name=repo_name,
                is_legacy_pattern=True
            )

    # No pattern matched
    raise RepoUrlPolicyViolation(
        error_code="REPO_URL_POLICY_VIOLATION",
        repo_url=url,
        reason="Repository name does not match allowed patterns. "
               "Expected: https://github.com/{org}/aspose-{family}-foss-{platform}"
               + (" or legacy patterns (Aspose.{Family}-for-{Platform}, Aspose.{Family}-FOSS-for-{Platform})" if allow_legacy else "")
    )


def _validate_site_repo(url: str, normalized_url: str) -> ValidatedRepoUrl:
    """Validate site repository URL.

    Args:
        url: Original URL
        normalized_url: Normalized URL for matching

    Returns:
        ValidatedRepoUrl for site repository

    Raises:
        RepoUrlPolicyViolation: If URL doesn't match expected site repo
    """
    expected_normalized = _normalize_url(SITE_REPO_URL)

    if normalized_url.lower() != expected_normalized.lower():
        raise RepoUrlPolicyViolation(
            error_code="REPO_URL_POLICY_VIOLATION",
            repo_url=url,
            reason=f"Site repository must be '{SITE_REPO_URL}', got '{url}'"
        )

    return ValidatedRepoUrl(
        original_url=url,
        normalized_url=normalized_url,
        repo_type="site",
        family=None,
        platform=None,
        organization="Aspose",
        repository_name="aspose.org",
        is_legacy_pattern=False
    )


def _validate_workflows_repo(url: str, normalized_url: str) -> ValidatedRepoUrl:
    """Validate workflows repository URL.

    Args:
        url: Original URL
        normalized_url: Normalized URL for matching

    Returns:
        ValidatedRepoUrl for workflows repository

    Raises:
        RepoUrlPolicyViolation: If URL doesn't match expected workflows repo
    """
    expected_normalized = _normalize_url(WORKFLOWS_REPO_URL)

    if normalized_url.lower() != expected_normalized.lower():
        raise RepoUrlPolicyViolation(
            error_code="REPO_URL_POLICY_VIOLATION",
            repo_url=url,
            reason=f"Workflows repository must be '{WORKFLOWS_REPO_URL}', got '{url}'"
        )

    return ValidatedRepoUrl(
        original_url=url,
        normalized_url=normalized_url,
        repo_type="workflows",
        family=None,
        platform=None,
        organization="Aspose",
        repository_name="aspose.org-workflows",
        is_legacy_pattern=False
    )


def validate_repo_url(
    repo_url: str,
    *,
    repo_type: Literal["product", "site", "workflows"],
    allow_legacy: bool = True
) -> ValidatedRepoUrl:
    """Validate repository URL against policy (Guarantee L).

    This function enforces the repository URL policy defined in
    specs/36_repository_url_policy.md. All git clone operations MUST
    call this function before attempting to clone.

    Validation steps:
    1. Normalize URL (strip .git, lowercase)
    2. Validate URL structure (no malformed URLs, path traversal, etc.)
    3. Validate protocol is HTTPS
    4. Validate host is github.com
    5. Validate repository name matches allowed pattern for repo_type
    6. Validate family and platform (for product repos)

    Args:
        repo_url: Repository URL to validate
        repo_type: Type of repository being validated
                   - "product": aspose-{family}-foss-{platform} pattern
                   - "site": Fixed site repository URL
                   - "workflows": Fixed workflows repository URL
        allow_legacy: Whether to allow legacy URL patterns (default: True)
                      Set to False to enforce strict modern patterns only

    Returns:
        ValidatedRepoUrl containing normalized URL and extracted metadata

    Raises:
        RepoUrlPolicyViolation: If URL violates policy

    Examples:
        >>> # Valid product repository
        >>> result = validate_repo_url(
        ...     "https://github.com/aspose-cells/aspose-cells-foss-python",
        ...     repo_type="product"
        ... )
        >>> result.family
        'cells'
        >>> result.platform
        'python'

        >>> # Invalid family
        >>> validate_repo_url(
        ...     "https://github.com/foo/aspose-invalid-foss-python",
        ...     repo_type="product"
        ... )
        RepoUrlPolicyViolation: REPO_URL_INVALID_FAMILY

        >>> # Invalid protocol
        >>> validate_repo_url(
        ...     "git://github.com/aspose-cells/aspose-cells-foss-python",
        ...     repo_type="product"
        ... )
        RepoUrlPolicyViolation: REPO_URL_INVALID_PROTOCOL

    Spec reference:
        specs/36_repository_url_policy.md (Binding contract)
    """
    # Step 1: Normalize URL
    normalized_url = _normalize_url(repo_url)

    # Step 2: Validate URL structure
    _validate_url_structure(normalized_url)

    # Step 3: Validate protocol
    _validate_protocol(normalized_url)

    # Step 4: Validate host
    _validate_host(normalized_url)

    # Step 5-6: Validate repository name pattern (type-specific)
    if repo_type == "product":
        return _validate_product_repo(repo_url, normalized_url, allow_legacy)
    elif repo_type == "site":
        return _validate_site_repo(repo_url, normalized_url)
    elif repo_type == "workflows":
        return _validate_workflows_repo(repo_url, normalized_url)
    else:
        raise ValueError(f"Invalid repo_type: {repo_type}. Must be 'product', 'site', or 'workflows'.")


def is_legacy_pattern_url(repo_url: str) -> bool:
    """Check if URL uses legacy naming pattern (without full validation).

    This is a lightweight check for generating deprecation warnings.
    For full validation, use validate_repo_url().

    Args:
        repo_url: Repository URL to check

    Returns:
        True if URL matches legacy pattern, False otherwise
    """
    normalized = _normalize_url(repo_url)
    return LEGACY_REPO_PATTERN.match(normalized) is not None
