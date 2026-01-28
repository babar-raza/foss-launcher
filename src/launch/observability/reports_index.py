"""
Reports Index Generation.

Scans all worker evidence directories and generates a structured index
with metadata for each report.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ReportMetadata:
    """Metadata for a single worker report."""

    taskcard_id: str
    agent_name: str
    status: str  # "complete", "in_progress", "failed"
    test_count: int
    test_pass_count: int
    quality_score: float  # 0.0-5.0
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    report_path: str
    self_review_path: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


@dataclass
class ReportsIndex:
    """Index of all worker reports."""

    generated_at: str  # ISO 8601
    total_reports: int
    reports: list[ReportMetadata]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "generated_at": self.generated_at,
            "total_reports": self.total_reports,
            "reports": [r.to_dict() for r in self.reports],
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def _extract_test_counts(report_path: Path) -> tuple[int, int]:
    """
    Extract test counts from report.md.

    Returns (test_count, test_pass_count).
    """
    if not report_path.exists():
        return 0, 0

    content = report_path.read_text(encoding="utf-8")

    # Look for patterns like "20/20 passing", "Tests: 20/20", etc.
    patterns = [
        r"(\d+)/(\d+)\s+passing",
        r"Tests:\s+(\d+)/(\d+)",
        r"Test\s+Results:\s+(\d+)/(\d+)",
        r"(\d+)\s+of\s+(\d+)\s+tests\s+pass",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            pass_count = int(match.group(1))
            total_count = int(match.group(2))
            return total_count, pass_count

    return 0, 0


def _extract_quality_score(self_review_path: Path) -> float:
    """
    Extract quality score from self_review.md.

    Returns score between 0.0 and 5.0.
    """
    if not self_review_path.exists():
        return 0.0

    content = self_review_path.read_text(encoding="utf-8")

    # Look for patterns like "Score: 4.8/5", "Quality: 5.0/5.0", etc.
    patterns = [
        r"Score:\s+([\d.]+)/5",
        r"Quality:\s+([\d.]+)/5",
        r"Overall:\s+([\d.]+)/5",
        r"Rating:\s+([\d.]+)/5",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            score = float(match.group(1))
            return min(max(score, 0.0), 5.0)  # Clamp to 0.0-5.0

    return 0.0


def _determine_status(report_path: Path, self_review_path: Path) -> str:
    """
    Determine report status based on file presence and content.

    Returns "complete", "in_progress", or "failed".
    """
    if not report_path.exists():
        return "in_progress"

    if not self_review_path.exists():
        return "in_progress"

    # Check for failure indicators in report
    content = report_path.read_text(encoding="utf-8")
    if "FAILED" in content.upper() or "ERROR" in content.upper():
        return "failed"

    return "complete"


def generate_reports_index(reports_dir: Path) -> ReportsIndex:
    """
    Generate reports index from worker evidence directories.

    Scans all directories matching reports/agents/<agent>/TC-<id>/ and
    extracts metadata from report.md and self_review.md files.

    Args:
        reports_dir: Path to reports root directory (e.g., reports/agents)

    Returns:
        ReportsIndex with metadata for all found reports
    """
    if not reports_dir.exists():
        # Return empty index if reports directory doesn't exist
        return ReportsIndex(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_reports=0,
            reports=[],
        )

    reports_metadata: list[ReportMetadata] = []

    # Scan all agent directories
    for agent_dir in sorted(reports_dir.iterdir()):
        if not agent_dir.is_dir():
            continue

        agent_name = agent_dir.name

        # Scan all taskcard directories
        for tc_dir in sorted(agent_dir.iterdir()):
            if not tc_dir.is_dir():
                continue

            # Extract taskcard ID (e.g., TC-580)
            taskcard_id = tc_dir.name
            if not taskcard_id.startswith("TC-"):
                continue

            report_path = tc_dir / "report.md"
            self_review_path = tc_dir / "self_review.md"

            # Skip if neither file exists
            if not report_path.exists() and not self_review_path.exists():
                continue

            # Extract metadata
            test_count, test_pass_count = _extract_test_counts(report_path)
            quality_score = _extract_quality_score(self_review_path)
            status = _determine_status(report_path, self_review_path)

            # Get file timestamps
            created_at = datetime.fromtimestamp(
                min(
                    report_path.stat().st_ctime if report_path.exists() else float("inf"),
                    self_review_path.stat().st_ctime if self_review_path.exists() else float("inf"),
                ),
                tz=timezone.utc,
            ).isoformat()

            updated_at = datetime.fromtimestamp(
                max(
                    report_path.stat().st_mtime if report_path.exists() else 0,
                    self_review_path.stat().st_mtime if self_review_path.exists() else 0,
                ),
                tz=timezone.utc,
            ).isoformat()

            reports_metadata.append(
                ReportMetadata(
                    taskcard_id=taskcard_id,
                    agent_name=agent_name,
                    status=status,
                    test_count=test_count,
                    test_pass_count=test_pass_count,
                    quality_score=quality_score,
                    created_at=created_at,
                    updated_at=updated_at,
                    report_path=str(report_path.relative_to(reports_dir.parent.parent)),
                    self_review_path=str(self_review_path.relative_to(reports_dir.parent.parent)),
                )
            )

    # Sort reports by agent name, then taskcard ID for deterministic ordering
    reports_metadata.sort(key=lambda r: (r.agent_name, r.taskcard_id))

    return ReportsIndex(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_reports=len(reports_metadata),
        reports=reports_metadata,
    )
