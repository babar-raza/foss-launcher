"""
Stub Commit Service for Dry-Run Testing

This is a local stub implementation of the commit service API that:
- Validates requests against schemas
- Enforces allowed_paths
- Handles idempotency
- Returns deterministic fake responses
- DOES NOT push to GitHub
- Logs all requests for audit

Usage:
    python scripts/stub_commit_service.py [--host HOST] [--port PORT]
"""

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Stub Commit Service", version="1.0.0")

# In-memory idempotency store
_idempotency_store: dict[str, dict[str, Any]] = {}

# Audit log path
AUDIT_LOG_DIR = Path("reports/post_impl/20260128_205133_e2e_hardening")
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "stub_commit_service_audit.jsonl"


class PatchBundle(BaseModel):
    """Patch bundle schema (simplified)"""

    schema_version: str = Field(..., pattern="^1\\.0$")
    files: list[dict[str, Any]]


class AG001Approval(BaseModel):
    """AG-001 branch creation approval metadata"""

    approved: bool
    approval_source: str = Field(..., pattern="^(interactive-dialog|manual-marker|config-override)$")
    timestamp: str
    approver: Optional[str] = None


class AIGovernanceMetadata(BaseModel):
    """AI governance metadata for automated compliance checks"""

    ag001_approval: Optional[AG001Approval] = None


class CommitRequest(BaseModel):
    """Commit request matching commit_request.schema.json"""

    schema_version: str = Field(..., pattern="^1\\.0$")
    run_id: str
    idempotency_key: str
    repo_url: str
    base_ref: str
    branch_name: str
    allowed_paths: list[str]
    commit_message: str
    commit_body: str
    patch_bundle: PatchBundle
    require_clean_base: bool = True
    ai_governance_metadata: Optional[AIGovernanceMetadata] = None


class CommitResponse(BaseModel):
    """Commit response matching commit_response.schema.json"""

    schema_version: str = "1.0"
    run_id: str
    idempotency_key: str
    repo_url: str
    base_ref: str
    branch_name: str
    commit_sha: str
    created_at: str


class PRRequest(BaseModel):
    """PR open request (simplified)"""

    schema_version: str = Field(..., pattern="^1\\.0$")
    run_id: str
    idempotency_key: str
    repo_url: str
    base_branch: str
    head_branch: str
    pr_title: str
    pr_body: str


class PRResponse(BaseModel):
    """PR response"""

    schema_version: str = "1.0"
    run_id: str
    idempotency_key: str
    pr_number: int
    pr_url: str
    created_at: str


def _audit_log(event_type: str, data: dict[str, Any]) -> None:
    """Write audit log entry"""
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event_type, "data": data}
    with open(AUDIT_LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info(f"Audit log: {event_type} - {data.get('run_id', 'N/A')}")


def _generate_fake_sha(idempotency_key: str) -> str:
    """Generate deterministic fake commit SHA from idempotency key"""
    return hashlib.sha256(idempotency_key.encode()).hexdigest()[:40]


def _validate_paths(patch_bundle: PatchBundle, allowed_paths: list[str]) -> tuple[bool, str]:
    """Validate that all patch files are within allowed paths"""
    for file_change in patch_bundle.files:
        file_path = file_change.get("path", "")
        if not any(file_path.startswith(allowed) for allowed in allowed_paths):
            return False, f"Path violation: {file_path} not in allowed_paths"
    return True, ""


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "stub_commit_service", "version": "1.0.0"}


@app.post("/v1/commit")
async def commit(request: CommitRequest):
    """
    Stub commit endpoint

    - Validates request
    - Enforces allowed_paths
    - Enforces AG-001 approval requirement (Task A3)
    - Handles idempotency
    - Returns fake commit SHA
    - DOES NOT push to GitHub
    """
    logger.info(f"Commit request: run_id={request.run_id}, idempotency_key={request.idempotency_key}")

    # Check idempotency
    if request.idempotency_key in _idempotency_store:
        logger.info(f"Idempotent request detected: {request.idempotency_key}")
        cached_response = _idempotency_store[request.idempotency_key]
        return JSONResponse(content=cached_response, status_code=200)

    # AG-001 validation (Task A3): Check for branch creation approval
    # For new branches (not in idempotency store), require approval metadata
    if request.ai_governance_metadata is None or request.ai_governance_metadata.ag001_approval is None:
        logger.error(f"AG-001 approval missing: run_id={request.run_id}, branch={request.branch_name}")
        _audit_log(
            "commit_rejected_ag001",
            {
                "run_id": request.run_id,
                "branch_name": request.branch_name,
                "reason": "Missing AG-001 approval metadata",
                "error_code": "AG001_APPROVAL_REQUIRED",
            }
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AG001_APPROVAL_REQUIRED",
                "message": "Branch creation requires AI governance approval (AG-001)",
                "details": {
                    "branch_name": request.branch_name,
                    "gate": "AG-001",
                    "required_field": "ai_governance_metadata.ag001_approval",
                    "documentation": "specs/30_ai_agent_governance.md"
                }
            }
        )

    # Validate approval is actually approved
    if not request.ai_governance_metadata.ag001_approval.approved:
        logger.error(f"AG-001 approval denied: run_id={request.run_id}, branch={request.branch_name}")
        _audit_log(
            "commit_rejected_ag001_denied",
            {
                "run_id": request.run_id,
                "branch_name": request.branch_name,
                "reason": "AG-001 approval explicitly denied",
                "error_code": "AG001_APPROVAL_DENIED",
            }
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AG001_APPROVAL_DENIED",
                "message": "Branch creation was explicitly denied by user",
                "details": {
                    "branch_name": request.branch_name,
                    "gate": "AG-001",
                }
            }
        )

    # Log approval metadata
    logger.info(
        f"AG-001 approval verified: run_id={request.run_id}, "
        f"source={request.ai_governance_metadata.ag001_approval.approval_source}"
    )

    # Validate paths
    valid, error_msg = _validate_paths(request.patch_bundle, request.allowed_paths)
    if not valid:
        logger.error(f"Path validation failed: {error_msg}")
        _audit_log("commit_rejected", {"run_id": request.run_id, "reason": error_msg})
        raise HTTPException(status_code=400, detail=error_msg)

    # Generate fake response
    fake_sha = _generate_fake_sha(request.idempotency_key)
    now = datetime.now(timezone.utc).isoformat()

    response = CommitResponse(
        run_id=request.run_id,
        idempotency_key=request.idempotency_key,
        repo_url=request.repo_url,
        base_ref=request.base_ref,
        branch_name=request.branch_name,
        commit_sha=fake_sha,
        created_at=now,
    )

    # Store for idempotency
    _idempotency_store[request.idempotency_key] = response.model_dump()

    # Audit log
    _audit_log(
        "commit_created",
        {
            "run_id": request.run_id,
            "idempotency_key": request.idempotency_key,
            "commit_sha": fake_sha,
            "file_count": len(request.patch_bundle.files),
        },
    )

    logger.info(f"Stub commit created: {fake_sha}")
    return response


@app.post("/v1/open_pr")
async def open_pr(request: PRRequest):
    """
    Stub PR open endpoint

    - Returns fake PR number and URL
    - DOES NOT create GitHub PR
    """
    logger.info(f"PR request: run_id={request.run_id}, idempotency_key={request.idempotency_key}")

    # Check idempotency
    if request.idempotency_key in _idempotency_store:
        logger.info(f"Idempotent PR request detected: {request.idempotency_key}")
        cached_response = _idempotency_store[request.idempotency_key]
        return JSONResponse(content=cached_response, status_code=200)

    # Generate fake response
    fake_pr_number = abs(hash(request.idempotency_key)) % 10000
    fake_pr_url = f"https://github.com/stub/pr/{fake_pr_number}"
    now = datetime.now(timezone.utc).isoformat()

    response = PRResponse(
        run_id=request.run_id,
        idempotency_key=request.idempotency_key,
        pr_number=fake_pr_number,
        pr_url=fake_pr_url,
        created_at=now,
    )

    # Store for idempotency
    _idempotency_store[request.idempotency_key] = response.model_dump()

    # Audit log
    _audit_log(
        "pr_opened",
        {
            "run_id": request.run_id,
            "idempotency_key": request.idempotency_key,
            "pr_number": fake_pr_number,
            "pr_url": fake_pr_url,
        },
    )

    logger.info(f"Stub PR created: {fake_pr_url}")
    return response


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Run stub commit service")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=4320, help="Port to bind to")
    args = parser.parse_args()

    logger.info(f"Starting stub commit service on {args.host}:{args.port}")
    logger.info(f"Audit log: {AUDIT_LOG_FILE}")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
