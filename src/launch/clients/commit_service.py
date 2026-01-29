"""Commit service client for centralized GitHub operations.

Binding contract:
- specs/17_github_commit_service.md (GitHub Commit Service)
- specs/34_strict_compliance_guarantees.md (Write fence enforcement)
- specs/10_determinism_and_caching.md (Deterministic request building)

All commits and PR operations MUST go through the commit service in production mode.
Idempotency is enforced via Idempotency-Key header.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..util.logging import get_logger
from .http import http_post

logger = get_logger()


class CommitServiceError(Exception):
    """Raised when commit service operation fails."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.response_body = response_body


class CommitServiceClient:
    """Client for GitHub commit service with idempotency.

    Features:
    - Deterministic request body formatting
    - Idempotency-Key header for all mutating requests
    - Bounded retry with exponential backoff
    - Clear error mapping for orchestrator
    - Auth token management
    - Path allowlist enforcement delegation to service

    Spec: specs/17_github_commit_service.md
    """

    def __init__(
        self,
        endpoint_url: str,
        auth_token: str,
        timeout: int = 60,
        max_retries: int = 3,
        offline_mode: bool = False,
        run_dir: Optional[Path] = None,
    ):
        """Initialize commit service client.

        Args:
            endpoint_url: Base URL for commit service (e.g., http://localhost:8080/v1)
            auth_token: Bearer token for authentication (GitHub PAT)
            timeout: Request timeout in seconds
            max_retries: Max retry attempts for network errors
            offline_mode: If True, write bundles to disk instead of API calls
            run_dir: Run directory for offline bundle storage (required if offline_mode=True)
        """
        self.endpoint_url = endpoint_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.offline_mode = offline_mode or os.getenv("OFFLINE_MODE") == "1"
        self.run_dir = Path(run_dir) if run_dir else None

        if self.offline_mode and not self.run_dir:
            raise ValueError("run_dir is required when offline_mode=True")

    def create_commit(
        self,
        run_id: str,
        repo_url: str,
        base_ref: str,
        branch_name: str,
        allowed_paths: List[str],
        commit_message: str,
        commit_body: str,
        patch_bundle: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        allow_existing_branch: bool = False,
        require_clean_base: bool = True,
    ) -> Dict[str, Any]:
        """Create a commit via commit service (POST /v1/commit).

        Args:
            run_id: Run identifier for traceability
            repo_url: Target repository URL (e.g., https://github.com/Aspose/aspose.org)
            base_ref: Base reference (e.g., main)
            branch_name: Branch name to create (e.g., launch/aspose-note/foss-python)
            allowed_paths: List of allowed path prefixes
            commit_message: Commit message (first line)
            commit_body: Commit body (additional lines)
            patch_bundle: Patch bundle object (must validate patch_bundle.schema.json)
            idempotency_key: Optional idempotency key (UUIDv4, generated if not provided)
            allow_existing_branch: Allow overwriting existing branch
            require_clean_base: Require base ref to be unchanged

        Returns:
            Response dict with:
                - commit_sha: Git commit SHA
                - branch_name: Branch name
                - repo_url: Repository URL

        Raises:
            CommitServiceError: On API error (auth, validation, conflict, server error)
        """
        if idempotency_key is None:
            idempotency_key = str(uuid.uuid4())

        # Build deterministic payload
        payload: Dict[str, Any] = {
            "schema_version": "1.0",
            "run_id": run_id,
            "repo_url": repo_url,
            "base_ref": base_ref,
            "branch_name": branch_name,
            "allowed_paths": sorted(allowed_paths),  # Stable ordering
            "commit_message": commit_message,
            "commit_body": commit_body,
            "patch_bundle": patch_bundle,
            "allow_existing_branch": allow_existing_branch,
            "require_clean_base": require_clean_base,
        }

        # Offline mode: write bundle instead of API call
        if self.offline_mode:
            return self._write_offline_bundle(
                operation="create_commit",
                payload=payload,
                idempotency_key=idempotency_key,
            )

        response_data = self._post_with_retry(
            endpoint="/commit",
            payload=payload,
            idempotency_key=idempotency_key,
            operation="create_commit",
        )

        return response_data

    def open_pr(
        self,
        run_id: str,
        repo_url: str,
        base_ref: str,
        head_ref: str,
        title: str,
        body: str,
        idempotency_key: Optional[str] = None,
        draft: bool = False,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Open a pull request via commit service (POST /v1/open_pr).

        Args:
            run_id: Run identifier for traceability
            repo_url: Target repository URL
            base_ref: Base reference (e.g., main)
            head_ref: Head reference (branch name)
            title: PR title
            body: PR body (markdown)
            idempotency_key: Optional idempotency key (UUIDv4, generated if not provided)
            draft: Open as draft PR
            labels: Optional list of labels to add

        Returns:
            Response dict with:
                - pr_number: Pull request number
                - pr_url: Pull request URL
                - pr_html_url: Pull request HTML URL

        Raises:
            CommitServiceError: On API error
        """
        if idempotency_key is None:
            idempotency_key = str(uuid.uuid4())

        # Build deterministic payload
        payload: Dict[str, Any] = {
            "schema_version": "1.0",
            "run_id": run_id,
            "repo_url": repo_url,
            "base_ref": base_ref,
            "head_ref": head_ref,
            "title": title,
            "body": body,
            "draft": draft,
        }

        if labels:
            payload["labels"] = sorted(labels)  # Stable ordering

        # Offline mode: write bundle instead of API call
        if self.offline_mode:
            return self._write_offline_bundle(
                operation="open_pr",
                payload=payload,
                idempotency_key=idempotency_key,
            )

        response_data = self._post_with_retry(
            endpoint="/open_pr",
            payload=payload,
            idempotency_key=idempotency_key,
            operation="open_pr",
        )

        return response_data

    def _post_with_retry(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        idempotency_key: str,
        operation: str,
    ) -> Dict[str, Any]:
        """POST with bounded retry.

        Args:
            endpoint: API endpoint path (e.g., /commit)
            payload: Request body
            idempotency_key: Idempotency key
            operation: Operation name for logging

        Returns:
            Response data dict

        Raises:
            CommitServiceError: On error after retries
        """
        backoff_seconds = [1, 2, 4]
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return self._post_direct(endpoint, payload, idempotency_key)
            except CommitServiceError as e:
                last_error = e

                # Don't retry on 4xx errors (client errors)
                if e.status_code and 400 <= e.status_code < 500:
                    logger.error(
                        "commit_service_client_error",
                        operation=operation,
                        error_code=e.error_code,
                        status_code=e.status_code,
                    )
                    raise

                # Retry on network errors and 5xx errors
                logger.warning(
                    "commit_service_retry",
                    operation=operation,
                    attempt=attempt + 1,
                    error=str(e),
                )

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    time.sleep(backoff_seconds[attempt])

        # All retries failed
        logger.error(
            "commit_service_max_retries_exceeded",
            operation=operation,
            max_retries=self.max_retries,
        )
        raise last_error

    def _post_direct(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Direct POST to commit service.

        Args:
            endpoint: API endpoint path
            payload: Request body
            idempotency_key: Idempotency key

        Returns:
            Response data dict

        Raises:
            CommitServiceError: On error
        """
        url = f"{self.endpoint_url}{endpoint}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "Idempotency-Key": idempotency_key,
        }

        # Stable JSON serialization (deterministic)
        json_data = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        try:
            response = http_post(
                url,
                data=json_data,
                headers=headers,
                timeout=self.timeout,
            )
        except Exception as e:
            raise CommitServiceError(
                f"Network error: {str(e)}",
                error_code="NETWORK_ERROR",
            )

        # Parse response
        if response.status_code >= 200 and response.status_code < 300:
            try:
                return response.json()
            except Exception as e:
                raise CommitServiceError(
                    f"Invalid JSON response: {str(e)}",
                    error_code="INVALID_RESPONSE",
                    status_code=response.status_code,
                    response_body=response.text,
                )
        else:
            # Parse error response
            try:
                error_data = response.json()
                error_code = error_data.get("code", "UNKNOWN_ERROR")
                error_message = error_data.get("message", response.text)
            except Exception:
                error_code = "UNKNOWN_ERROR"
                error_message = response.text

            raise CommitServiceError(
                f"Commit service error ({response.status_code}): {error_message}",
                error_code=error_code,
                status_code=response.status_code,
                response_body=response.text,
            )

    def _write_offline_bundle(
        self,
        operation: str,
        payload: Dict[str, Any],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Write offline bundle instead of making API call.

        Args:
            operation: Operation name (create_commit, open_pr)
            payload: Request payload
            idempotency_key: Idempotency key

        Returns:
            Mock response dict with deferred status
        """
        # Create artifacts directory
        artifacts_dir = self.run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Write bundle
        bundle_filename = f"{operation}_bundle.json"
        bundle_path = artifacts_dir / bundle_filename

        bundle = {
            "operation": operation,
            "idempotency_key": idempotency_key,
            "payload": payload,
            "timestamp": time.time(),
            "offline_mode": True,
        }

        # Write atomically
        tmp_file = bundle_path.with_suffix(".json.tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2, sort_keys=True)

        os.replace(tmp_file, bundle_path)

        logger.info(
            "commit_service_offline_bundle_written",
            operation=operation,
            bundle_path=str(bundle_path),
        )

        # Return mock response
        if operation == "create_commit":
            return {
                "status": "deferred",
                "bundle_path": str(bundle_path),
                "commit_sha": "0000000000000000000000000000000000000000",  # Mock SHA
                "branch_name": payload.get("branch_name", "unknown"),
                "repo_url": payload.get("repo_url", "unknown"),
            }
        elif operation == "open_pr":
            return {
                "status": "deferred",
                "bundle_path": str(bundle_path),
                "pr_number": 0,  # Mock PR number
                "pr_url": f"file://{bundle_path}",
                "pr_html_url": f"file://{bundle_path}",
            }
        else:
            return {
                "status": "deferred",
                "bundle_path": str(bundle_path),
            }

    def health_check(self) -> bool:
        """Check if commit service is reachable.

        Returns:
            True if service is healthy

        Raises:
            CommitServiceError: If service is unreachable
        """
        # Offline mode: always return True
        if self.offline_mode:
            logger.info("commit_service_health_check_offline_mode")
            return True

        url = f"{self.endpoint_url}/health"

        try:
            from .http import http_get
            response = http_get(url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            raise CommitServiceError(
                f"Health check failed: {str(e)}",
                error_code="HEALTH_CHECK_FAILED",
            )
