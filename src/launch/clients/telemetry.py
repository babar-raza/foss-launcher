"""Telemetry client with outbox buffering for local telemetry API.

Binding contract:
- specs/16_local_telemetry_api.md (Local Telemetry API)
- specs/11_state_and_events.md (State transitions and events)
- specs/10_determinism_and_caching.md (Stable JSON serialization)

All telemetry events MUST be recorded for audit and accountability.
Transport failures MUST NOT crash the run (outbox buffering).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from ..util.logging import get_logger
from .http import http_post

logger = get_logger()


class TelemetryError(Exception):
    """Raised when telemetry operation fails critically."""
    pass


class TelemetryClient:
    """Client for local telemetry API with outbox buffering.

    Features:
    - POST to telemetry API when online
    - Outbox buffering to RUN_DIR/telemetry_outbox.jsonl when offline
    - Stable payload formatting (deterministic JSON)
    - Bounded retry with exponential backoff
    - Idempotent writes using event_id

    Spec: specs/16_local_telemetry_api.md
    """

    def __init__(
        self,
        endpoint_url: str,
        run_dir: Path,
        auth_token: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 3,
        max_outbox_size_mb: int = 10,
    ):
        """Initialize telemetry client.

        Args:
            endpoint_url: Base URL for telemetry API (e.g., http://localhost:8765)
            run_dir: RUN_DIR for outbox storage
            auth_token: Optional bearer token for auth
            timeout: Request timeout in seconds
            max_retries: Max retry attempts per POST
            max_outbox_size_mb: Max outbox size in MB before truncation
        """
        self.endpoint_url = endpoint_url.rstrip("/")
        self.run_dir = Path(run_dir)
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_outbox_size_bytes = max_outbox_size_mb * 1024 * 1024
        self.outbox_path = self.run_dir / "telemetry_outbox.jsonl"

        # Ensure run_dir exists
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def create_run(
        self,
        run_id: str,
        agent_name: str,
        job_type: str,
        start_time: str,
        event_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        status: str = "running",
        product: Optional[str] = None,
        product_family: Optional[str] = None,
        platform: Optional[str] = None,
        git_repo: Optional[str] = None,
        git_branch: Optional[str] = None,
        metrics_json: Optional[Dict[str, Any]] = None,
        context_json: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a telemetry run (POST /api/v1/runs).

        Args:
            run_id: Stable run identifier (deterministic)
            agent_name: Agent name (e.g., launch.orchestrator, launch.workers.RepoScout)
            job_type: Job type (launch, orchestrator_node, worker, gate, llm_call, commit_service)
            start_time: ISO8601 timestamp with timezone
            event_id: Optional event ID (UUIDv4, generated if not provided)
            parent_run_id: Optional parent run_id for child runs
            status: Status (running, success, failure, partial, timeout, cancelled)
            product: Optional product slug
            product_family: Optional product family
            platform: Optional platform
            git_repo: Optional git repo URL
            git_branch: Optional git branch
            metrics_json: Optional metrics (counters, timings)
            context_json: Optional context (trace_id, span_id, hashes)

        Returns:
            True if POST succeeded, False if buffered to outbox
        """
        if event_id is None:
            event_id = str(uuid.uuid4())

        # Build payload with stable field ordering
        payload: Dict[str, Any] = {
            "event_id": event_id,
            "run_id": run_id,
            "agent_name": agent_name,
            "job_type": job_type,
            "start_time": start_time,
            "status": status,
        }

        # Add optional fields
        if parent_run_id:
            payload["parent_run_id"] = parent_run_id
        if product:
            payload["product"] = product
        if product_family:
            payload["product_family"] = product_family
        if platform:
            payload["platform"] = platform
        if git_repo:
            payload["git_repo"] = git_repo
        if git_branch:
            payload["git_branch"] = git_branch
        if metrics_json:
            payload["metrics_json"] = metrics_json
        if context_json:
            payload["context_json"] = context_json

        return self._post_with_retry(
            endpoint="/api/v1/runs",
            payload=payload,
            operation="create_run",
        )

    def update_run(
        self,
        event_id: str,
        status: Optional[str] = None,
        end_time: Optional[str] = None,
        duration_ms: Optional[int] = None,
        items_discovered: Optional[int] = None,
        items_succeeded: Optional[int] = None,
        items_failed: Optional[int] = None,
        items_skipped: Optional[int] = None,
        output_summary: Optional[str] = None,
        error_summary: Optional[str] = None,
        metrics_json: Optional[Dict[str, Any]] = None,
        context_json: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update a telemetry run (PATCH /api/v1/runs/{event_id}).

        Args:
            event_id: Event ID to update
            status: Optional status update
            end_time: Optional end time (ISO8601)
            duration_ms: Optional duration in milliseconds
            items_discovered: Optional count
            items_succeeded: Optional count
            items_failed: Optional count
            items_skipped: Optional count
            output_summary: Optional output summary
            error_summary: Optional error summary
            metrics_json: Optional metrics update
            context_json: Optional context update

        Returns:
            True if PATCH succeeded, False if buffered to outbox
        """
        payload: Dict[str, Any] = {}

        if status:
            payload["status"] = status
        if end_time:
            payload["end_time"] = end_time
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        if items_discovered is not None:
            payload["items_discovered"] = items_discovered
        if items_succeeded is not None:
            payload["items_succeeded"] = items_succeeded
        if items_failed is not None:
            payload["items_failed"] = items_failed
        if items_skipped is not None:
            payload["items_skipped"] = items_skipped
        if output_summary:
            payload["output_summary"] = output_summary
        if error_summary:
            payload["error_summary"] = error_summary
        if metrics_json:
            payload["metrics_json"] = metrics_json
        if context_json:
            payload["context_json"] = context_json

        return self._post_with_retry(
            endpoint=f"/api/v1/runs/{event_id}",
            payload=payload,
            operation="update_run",
            method="PATCH",
        )

    def associate_commit(
        self,
        event_id: str,
        commit_hash: str,
        commit_source: str,
        commit_author: Optional[str] = None,
        commit_timestamp: Optional[str] = None,
    ) -> bool:
        """Associate a commit with a run (POST /api/v1/runs/{event_id}/associate-commit).

        Args:
            event_id: Event ID to associate commit with
            commit_hash: Git commit SHA (7-40 chars)
            commit_source: Source (manual, llm, ci)
            commit_author: Optional commit author
            commit_timestamp: Optional commit timestamp (ISO8601)

        Returns:
            True if POST succeeded, False if buffered to outbox
        """
        payload: Dict[str, Any] = {
            "commit_hash": commit_hash,
            "commit_source": commit_source,
        }

        if commit_author:
            payload["commit_author"] = commit_author
        if commit_timestamp:
            payload["commit_timestamp"] = commit_timestamp

        return self._post_with_retry(
            endpoint=f"/api/v1/runs/{event_id}/associate-commit",
            payload=payload,
            operation="associate_commit",
        )

    def flush_outbox(self) -> tuple[int, int]:
        """Flush outbox to telemetry API.

        Attempts to send all buffered payloads. Successful sends are removed
        from the outbox. Failed sends remain for next flush attempt.

        Returns:
            Tuple of (successful_count, failed_count)
        """
        if not self.outbox_path.exists() or self.outbox_path.stat().st_size == 0:
            return (0, 0)

        logger.info("flushing_telemetry_outbox", outbox_path=str(self.outbox_path))

        # Read all outbox entries
        with open(self.outbox_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        successful = []
        failed = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
                endpoint = entry.get("endpoint", "/api/v1/runs")
                payload = entry.get("payload", {})
                method = entry.get("method", "POST")

                # Try to send
                if self._post_direct(endpoint, payload, method):
                    successful.append(line)
                else:
                    failed.append(line)
            except Exception as e:
                logger.warning("outbox_entry_invalid", error=str(e), line=line)
                # Skip invalid entries
                continue

        # Rewrite outbox with only failed entries
        if failed:
            with open(self.outbox_path, "w", encoding="utf-8") as f:
                f.write("\n".join(failed) + "\n")
        else:
            # All succeeded, delete outbox
            self.outbox_path.unlink()

        logger.info(
            "outbox_flush_complete",
            successful=len(successful),
            failed=len(failed),
        )

        return (len(successful), len(failed))

    def _post_with_retry(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        operation: str,
        method: str = "POST",
    ) -> bool:
        """POST with bounded retry and outbox fallback.

        Args:
            endpoint: API endpoint path (e.g., /api/v1/runs)
            payload: Request body
            operation: Operation name for logging
            method: HTTP method (POST or PATCH)

        Returns:
            True if successful, False if buffered to outbox
        """
        backoff_seconds = [1, 2, 4]

        for attempt in range(self.max_retries):
            try:
                if self._post_direct(endpoint, payload, method):
                    return True
            except Exception as e:
                logger.warning(
                    "telemetry_post_failed",
                    operation=operation,
                    attempt=attempt + 1,
                    error=str(e),
                )

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    time.sleep(backoff_seconds[attempt])

        # All retries failed, buffer to outbox
        logger.warning(
            "telemetry_buffered_to_outbox",
            operation=operation,
            endpoint=endpoint,
        )

        self._append_to_outbox(endpoint, payload, method)
        return False

    def _post_direct(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        method: str = "POST",
    ) -> bool:
        """Direct POST/PATCH to telemetry API.

        Args:
            endpoint: API endpoint path
            payload: Request body
            method: HTTP method (POST or PATCH)

        Returns:
            True if successful (2xx response)

        Raises:
            Exception on network error or non-2xx response
        """
        url = f"{self.endpoint_url}{endpoint}"

        headers = {
            "Content-Type": "application/json",
        }

        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        # Stable JSON serialization (deterministic)
        json_data = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        if method == "POST":
            response = http_post(
                url,
                data=json_data,
                headers=headers,
                timeout=self.timeout,
            )
        elif method == "PATCH":
            # Use requests directly for PATCH (http.py doesn't have PATCH wrapper)
            import requests
            response = requests.patch(
                url,
                data=json_data,
                headers=headers,
                timeout=self.timeout,
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        # Check response
        if response.status_code >= 200 and response.status_code < 300:
            return True
        elif response.status_code >= 400 and response.status_code < 500:
            # 4xx errors are client errors, don't retry
            logger.error(
                "telemetry_client_error",
                status_code=response.status_code,
                response=response.text,
            )
            raise TelemetryError(
                f"Telemetry API client error ({response.status_code}): {response.text}"
            )
        else:
            # 5xx errors are server errors, will retry
            raise TelemetryError(
                f"Telemetry API server error ({response.status_code}): {response.text}"
            )

    def _append_to_outbox(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        method: str,
    ) -> None:
        """Append failed request to outbox (atomic append).

        Args:
            endpoint: API endpoint path
            payload: Request body
            method: HTTP method
        """
        # Check outbox size limit
        if self.outbox_path.exists():
            outbox_size = self.outbox_path.stat().st_size
            if outbox_size > self.max_outbox_size_bytes:
                logger.error(
                    "telemetry_outbox_full",
                    size_mb=outbox_size / (1024 * 1024),
                    max_mb=self.max_outbox_size_bytes / (1024 * 1024),
                )
                # Truncate oldest entries (keep last 50%)
                self._truncate_outbox()

        # Create outbox entry
        entry = {
            "endpoint": endpoint,
            "payload": payload,
            "method": method,
            "timestamp": time.time(),
        }

        # Atomic append: write to temp file, then append
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"

        # Append atomically
        with open(self.outbox_path, "a", encoding="utf-8") as f:
            f.write(line)

    def _truncate_outbox(self) -> None:
        """Truncate outbox to last 50% of entries."""
        if not self.outbox_path.exists():
            return

        with open(self.outbox_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Keep last 50%
        keep_count = len(lines) // 2
        kept_lines = lines[-keep_count:]

        with open(self.outbox_path, "w", encoding="utf-8") as f:
            f.writelines(kept_lines)

        logger.warning(
            "telemetry_outbox_truncated",
            original_count=len(lines),
            kept_count=len(kept_lines),
        )
