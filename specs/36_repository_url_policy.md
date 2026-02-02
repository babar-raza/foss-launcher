# Spec 36: Repository URL Policy and Validation

**Status**: Binding
**Updated**: 2026-02-01

## Overview

This specification defines the **mandatory repository URL allowlist policy** for all git clone operations performed by the system. This policy ensures that only authorized repositories can be ingested, preventing potential security risks from arbitrary repository cloning.

## Core Policy

### Rule: Allowed Repository Patterns

All repository URLs cloned by the system MUST match one of the following patterns:

#### 1. Product Repositories (Primary Pattern)

```
https://github.com/{org}/aspose-{family}-foss-{platform}
```

**Constraints**:
- **Protocol**: MUST be `https://` (no git://, ssh://, or http://)
- **Host**: MUST be `github.com` exactly
- **Organization**: ANY valid GitHub organization name (alphanumeric, hyphens, no leading/trailing hyphens)
- **Repository name**: MUST follow the exact pattern `aspose-{family}-foss-{platform}`

**Valid `{family}` values** (exhaustive list):
- `3d`
- `barcode`
- `cad`
- `cells`
- `diagram`
- `email`
- `finance`
- `font`
- `gis`
- `html`
- `imaging`
- `note`
- `ocr`
- `page`
- `pdf`
- `psd`
- `slides`
- `svg`
- `tasks`
- `tex`
- `words`
- `zip`

**Valid `{platform}` values** (exhaustive list):
- `android`
- `cpp`
- `dotnet`
- `go`
- `java`
- `javascript`
- `net`
- `nodejs`
- `php`
- `python`
- `ruby`
- `rust`
- `swift`
- `typescript`

**Matching rules**:
- Case-insensitive for family and platform (normalized to lowercase)
- No additional path components after repository name
- No query parameters or fragments
- No `.git` suffix required (but allowed and stripped for validation)

**Examples of valid product repository URLs**:
```
https://github.com/aspose-cells/aspose-cells-foss-python
https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET  # Legacy, maps to aspose-3d-foss-python
https://github.com/Aspose/aspose-words-foss-java
https://github.com/custom-org/aspose-pdf-foss-dotnet
```

#### 2. Site Repository (Fixed Default)

```
https://github.com/Aspose/aspose.org
```

**Constraints**:
- MUST be exact match (case-insensitive)
- Used for `site_repo_url` in run configuration

#### 3. Workflows Repository (Fixed Default)

```
https://github.com/Aspose/aspose.org-workflows
```

**Constraints**:
- MUST be exact match (case-insensitive)
- Used for `workflows_repo_url` in run configuration

#### 4. Legacy Repository Patterns (Temporary Compatibility)

For backward compatibility with existing pilots, the following patterns are allowed **temporarily**:

```
https://github.com/{org}/Aspose.{Family}-for-{Platform}-via-.NET
```

**Example**: `https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET`

**Deprecation timeline**:
- **Phase 1 (Current)**: Both legacy and standard patterns accepted
- **Phase 2 (Target: Q2 2026)**: Legacy patterns trigger warnings
- **Phase 3 (Target: Q3 2026)**: Legacy patterns rejected

**Normalization**: Legacy URLs are normalized to standard pattern internally:
- `Aspose.3D-for-Python-via-.NET` → `aspose-3d-foss-python`
- `Aspose.Words-for-Java` → `aspose-words-foss-java`

## Forbidden Patterns

The following repository patterns are **explicitly forbidden**:

1. **Non-GitHub hosts**:
   - GitLab, Bitbucket, or any other git hosting service
   - Self-hosted git servers
   - Raw IP addresses

2. **Non-HTTPS protocols**:
   - `git://` (git protocol)
   - `ssh://` or `git@` (SSH)
   - `http://` (unencrypted HTTP)
   - `file://` (local filesystem)

3. **Arbitrary GitHub repositories**:
   - Any repository not matching allowed patterns
   - Personal forks outside approved organizations
   - Test/demo repositories not following naming convention

4. **Path traversal or injection attempts**:
   - URLs with `..` or `/./` sequences
   - URLs with encoded characters in critical positions
   - URLs with query parameters or fragments

## Validation Requirements

### Pre-Clone Validation (Binding)

Before any `git clone` operation, the system MUST:

1. **Parse and normalize the URL**:
   - Strip trailing `.git` suffix if present
   - Normalize to lowercase for pattern matching
   - Validate URL structure (no malformed URLs)

2. **Validate against allowed patterns**:
   - Check protocol is `https://`
   - Check host is `github.com`
   - Check repository name matches allowed pattern
   - Check family is in allowed list (if product repo)
   - Check platform is in allowed list (if product repo)

3. **On validation failure**:
   - **DO NOT** attempt to clone
   - Emit telemetry event: `REPO_URL_BLOCKED`
   - Open BLOCKER issue with error code: `REPO_URL_POLICY_VIOLATION`
   - Exit with status code `1` (user error - invalid input)
   - Include in error message: exact reason for rejection and policy reference

4. **On validation success**:
   - Emit telemetry event: `REPO_URL_VALIDATED`
   - Proceed with clone operation
   - Record validated URL in `resolved_refs.json` artifact

### Error Codes

| Error Code | Severity | Meaning |
|------------|----------|---------|
| `REPO_URL_POLICY_VIOLATION` | BLOCKER | Repository URL does not match allowed patterns |
| `REPO_URL_INVALID_PROTOCOL` | BLOCKER | Protocol is not HTTPS |
| `REPO_URL_INVALID_HOST` | BLOCKER | Host is not github.com |
| `REPO_URL_INVALID_FAMILY` | BLOCKER | Family not in allowed list |
| `REPO_URL_INVALID_PLATFORM` | BLOCKER | Platform not in allowed list |
| `REPO_URL_MALFORMED` | BLOCKER | URL structure is invalid |

## Implementation Contract

### Validator Module: `src/launch/workers/_git/repo_url_validator.py`

The validator module MUST expose:

```python
def validate_repo_url(
    repo_url: str,
    *,
    repo_type: Literal["product", "site", "workflows"],
    allow_legacy: bool = True
) -> ValidatedRepoUrl:
    """Validate repository URL against policy.

    Args:
        repo_url: Repository URL to validate
        repo_type: Type of repository (product/site/workflows)
        allow_legacy: Whether to allow legacy URL patterns

    Returns:
        ValidatedRepoUrl with normalized URL and extracted metadata

    Raises:
        RepoUrlPolicyViolation: If URL violates policy
    """
```

**Return type**:
```python
@dataclass(frozen=True)
class ValidatedRepoUrl:
    original_url: str
    normalized_url: str
    repo_type: str
    family: Optional[str]  # For product repos
    platform: Optional[str]  # For product repos
    organization: str
    repository_name: str
    is_legacy_pattern: bool
```

**Exception type**:
```python
class RepoUrlPolicyViolation(Exception):
    """Raised when repository URL violates policy."""
    error_code: str
    repo_url: str
    reason: str
```

### Integration Points

1. **W1 RepoScout Clone Worker** ([clone.py](../src/launch/workers/w1_repo_scout/clone.py)):
   - MUST call `validate_repo_url()` before calling `clone_and_resolve()`
   - MUST validate all three repository types:
     - Product repo: `github_repo_url` → `repo_type="product"`
     - Site repo: `site_repo_url` → `repo_type="site"`
     - Workflows repo: `workflows_repo_url` → `repo_type="workflows"`

2. **Run Config Validation** ([io/run_config.py](../src/launch/io/run_config.py)):
   - SHOULD validate repository URLs during config load (early fail-fast)
   - Validation is advisory at config load, binding at clone time

3. **MCP Tool Schemas** ([specs/24_mcp_tool_schemas.md](24_mcp_tool_schemas.md)):
   - Tool schema documentation MUST reference this policy
   - Example URLs in schemas MUST follow allowed patterns

## Testing Requirements

### Unit Tests: `tests/unit/workers/_git/test_repo_url_validator.py`

MUST include test cases for:

**Valid URLs**:
- Standard product repo pattern (all valid families × platforms)
- Site repository URL
- Workflows repository URL
- Legacy pattern URLs (with deprecation warnings)
- URLs with trailing `.git` suffix
- Mixed-case URLs (normalized to lowercase)

**Invalid URLs**:
- Wrong protocol (git://, ssh://, http://)
- Wrong host (gitlab.com, bitbucket.org, etc.)
- Invalid family name
- Invalid platform name
- Arbitrary GitHub repositories
- Malformed URLs
- URLs with path traversal attempts
- URLs with query parameters

**Edge cases**:
- Empty string
- None value
- Very long URLs
- URLs with unicode characters
- URLs with encoded characters

### Integration Tests: `tests/integration/test_clone_validation.py`

MUST verify:
- Clone operation blocked for invalid URLs
- BLOCKER issue opened with correct error code
- Telemetry events emitted correctly
- Exit code is `1` for policy violations

## Allowlist Updates

### Adding New Families

To add a new product family (e.g., `note`, `finance`):

1. Update `ALLOWED_FAMILIES` constant in `repo_url_validator.py`
2. Update this spec (line 37-59) with new family name
3. Add test cases for the new family
4. Document in commit message and changelog

### Adding New Platforms

To add a new platform (e.g., `kotlin`, `dart`):

1. Update `ALLOWED_PLATFORMS` constant in `repo_url_validator.py`
2. Update this spec (line 61-79) with new platform name
3. Add test cases for the new platform
4. Document in commit message and changelog

### Emergency Override (NOT RECOMMENDED)

If an emergency requires cloning a non-conformant repository:

1. **Preferred approach**: Rename the repository to match the pattern
2. **Temporary workaround**: Add repository as explicit exception in validator
3. **File a tracking issue** to migrate to conformant naming
4. **Document rationale** in code comments and issue tracker

**DO NOT** disable the validator entirely - add specific exceptions only.

## Compliance Guarantee

This policy implements **Guarantee L: Repository URL Allowlist** per [specs/34_strict_compliance_guarantees.md](34_strict_compliance_guarantees.md).

**Guarantee statement**:
> The system MUST only clone repositories matching the approved URL patterns. Any attempt to clone an arbitrary repository MUST be blocked with a BLOCKER issue and appropriate error code.

**Verification**:
- Automated: Unit tests verify all pattern matches
- Automated: Integration tests verify clone blocking
- Manual: Code review of validator implementation
- Runtime: Telemetry events track all validation attempts

## Migration Path for Existing Pilots

Pilots using non-conformant repository URLs MUST:

1. **Identify non-conformant URLs** in pilot run configs
2. **Choose migration strategy**:
   - **Option A**: Rename repository to match pattern (preferred)
   - **Option B**: Use legacy pattern support (temporary)
   - **Option C**: Add explicit exception (not recommended)
3. **Update run_config.yaml** with new URL
4. **Re-run validation**: `python tools/validate_swarm_ready.py`
5. **Update pilot documentation** with migration notes

## References

- [specs/01_system_contract.md](01_system_contract.md) - System inputs and repository configuration
- [specs/02_repo_ingestion.md](02_repo_ingestion.md) - Clone and fingerprint operations
- [specs/34_strict_compliance_guarantees.md](34_strict_compliance_guarantees.md) - Guarantee L
- [config/network_allowlist.yaml](../config/network_allowlist.yaml) - Network egress controls (complementary)
- [src/launch/workers/_git/clone_helpers.py](../src/launch/workers/_git/clone_helpers.py) - Clone implementation

## Changelog

- **2026-02-01**: Initial specification for repository URL policy (Guarantee L)
