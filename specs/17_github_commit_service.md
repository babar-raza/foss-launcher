# GitHub Commit Service (binding)

## Requirement (non-negotiable)
All commits and PR operations against the **site repo** (default: aspose.org) MUST be performed through a centralized **Commit Service**.

The orchestrator MUST NOT run `git commit`, `git push`, or open PRs directly in **production mode**.

## Purpose
- Centralize auth, audit, and policy enforcement.
- Standardize commit messages, PR titles/bodies.
- Enforce write-fence rules (`allowed_paths`) and patch integrity.
- Provide a single point for telemetry correlation and incident triage.

## Service versioning
- Base path: `/v1`
- All requests MUST include `schema_version` inside the JSON body.
- Backwards-incompatible changes require a new endpoint version (e.g. `/v2`).

## Authentication (binding)
- Requests MUST be authenticated.
- Minimum: `Authorization: Bearer <token>`.
- The service MUST reject unauthenticated requests with **401**.

## Idempotency (binding)
To prevent duplicate commits/PRs under retries:
- Client MUST send `Idempotency-Key: <opaque uuid>` on all mutating requests.
- Service MUST dedupe by `(endpoint, repo_url, idempotency_key)`.
- On replay, service MUST return the original response (same commit SHA / PR URL) with **200**.

## Minimum API contract

### 1) Create commit
- `POST /v1/commit`
- Request body MUST validate: `specs/schemas/commit_request.schema.json`
- Response body MUST validate: `specs/schemas/commit_response.schema.json`

### 2) Open PR
- `POST /v1/open_pr`
- Request body MUST validate: `specs/schemas/open_pr_request.schema.json`
- Response body MUST validate: `specs/schemas/open_pr_response.schema.json`

### Errors
- All error responses MUST validate: `specs/schemas/api_error.schema.json`

## Binding behavior

### allowed_paths enforcement (non-negotiable)
- The service MUST reject any file change outside `allowed_paths`.
- The service MUST reject path traversal and absolute paths.
- Recommended status: **403** (`code=PATH_NOT_ALLOWED`).

### Patch integrity (non-negotiable)
- Client MUST send either:
  - a `patch_bundle` object validating `specs/schemas/patch_bundle.schema.json`, OR
  - explicit file operations in the request (`file_changes`), depending on schema.
- Service MUST verify:
  - all paths are normalized
  - content is UTF-8
  - no binary payload unless explicitly allowed

### Concurrency + branch rules (recommended)
- If the branch already exists and `allow_existing_branch=false`, return **409**.
- If base ref moves and `require_clean_base=true`, return **409** with a conflict error.

### Telemetry (binding)
The service MUST emit local-telemetry events (directly or via an internal relay) that include:
- `run_id`
- `idempotency_key`
- `repo_url`
- `base_ref`, `branch_name`
- commit SHA / PR URL on success
- error `code`, `message`, `details` on failure

## Commit traceability (non-negotiable)
After the commit service returns `commit_sha`, the orchestrator MUST associate that SHA with telemetry runs using the Local Telemetry API `associate-commit` flow (see `specs/16_local_telemetry_api.md`).

Minimum behavior:
- Associate the commit SHA with the parent launch run.
- Propagate the same commit SHA to all child runs that happened before the commit.

## Suggested timeouts + retries (recommended)
- Client timeout: 60s (commit), 60s (open_pr)
- Retries: up to 3 (network timeouts, 502/503/504)
- Do NOT retry on 4xx except 409 if client policy allows rebase/resync.

## Example: commit request (illustrative)
```json
{
  "schema_version": "1.0",
  "run_id": "RUN-20260122-123000Z-abcdef",
  "repo_url": "https://github.com/Aspose/aspose.org",
  "base_ref": "main",
  "branch_name": "launch/aspose-note/foss-python",
  "allowed_paths": ["content/products.aspose.org/note/en/"],
  "commit_message": "Launch FOSS Launcher for Aspose.Note",
  "commit_body": "Automated launch run RUN-20260122-123000Z-abcdef\n\nValidation: all gates passed.",
  "patch_bundle": {
    "schema_version": "1.0",
    "operations": []
  }
}
```

## Authentication Best Practices (binding)

### Token Management
- MUST use GitHub Personal Access Tokens (PAT) or GitHub App tokens for authentication
- MUST NOT store tokens in source code, environment variables visible to logs, or commit messages
- MUST use secure secret management (e.g., Azure Key Vault, AWS Secrets Manager, HashiCorp Vault)
- Token MUST have minimum required scopes: `repo` (for private repos) or `public_repo` (for public repos) + `workflow` (if modifying GitHub Actions)
- MUST rotate tokens periodically (recommended: every 90 days)
- MUST revoke tokens immediately upon suspected compromise

### Token Validation
- Service MUST validate token on first use and cache validation result with 5-minute TTL
- Service MUST return **401 Unauthorized** with `error_code=AUTH_INVALID_TOKEN` if token is invalid or expired
- Service MUST return **403 Forbidden** with `error_code=AUTH_INSUFFICIENT_SCOPE` if token lacks required scopes
- Service MUST verify token has write access to target repository before accepting commit request

### Request Authentication
- MUST use `Authorization: Bearer <token>` header for all mutating requests
- MUST reject requests with missing or malformed Authorization header (return **401**)
- MUST implement rate limiting per token (default: 100 requests/hour per token)
- SHOULD log authentication failures to security audit log with client IP, timestamp, error reason

### Secure Transport
- If service is exposed over HTTP (not STDIO), MUST use TLS 1.2+ with valid certificate
- MUST NOT transmit tokens or sensitive data over unencrypted connections
- SHOULD implement HSTS (HTTP Strict Transport Security) header

### Idempotency Key Security
- Idempotency keys MUST be UUID v4 format (reject non-UUID keys with **400**)
- MUST store idempotency key mapping securely (encrypted at rest)
- MUST expire idempotency keys after 24 hours (prevent unbounded storage growth)
- MUST validate idempotency key matches request signature (prevent key reuse across different requests)

### Error Handling
- MUST NOT leak sensitive information in error messages (e.g., full token values, internal paths)
- MUST redact tokens from logs (show only last 4 characters: `ghp_***abc123`)
- MUST emit telemetry event `AUTH_FAILURE` with error_code but NOT token value
- SHOULD implement exponential backoff guidance in error responses for retryable auth failures

### Audit and Compliance
- MUST log all authenticated requests with: timestamp, token identifier (not full token), action, result
- MUST retain audit logs for minimum 90 days (configurable for compliance requirements)
- SHOULD implement webhook notifications for suspicious auth patterns (e.g., 10+ failures in 1 minute)

## Acceptance
- All requests authenticated with bearer tokens
- Schema validation enforced for all requests/responses
- Idempotency implemented and tested
- Allowed paths enforced
- Telemetry events emitted
- Auth best practices implemented and documented
