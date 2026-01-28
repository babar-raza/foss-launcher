"""
Observability and Evidence Packaging module.

Provides functionality for:
- Reports index generation with metadata extraction
- Evidence packaging with ZIP creation and manifest generation
- Run summary report generation
- Evidence completeness validation

See specs/11_state_and_events.md and specs/21_worker_contracts.md for contracts.
"""

from __future__ import annotations

from .evidence_packager import (
    PackageFile,
    PackageManifest,
    create_evidence_package,
)
from .reports_index import (
    ReportMetadata,
    ReportsIndex,
    generate_reports_index,
)
from .run_summary import (
    RunSummary,
    TimelineEvent,
    generate_run_summary,
    validate_evidence_completeness,
)

__all__ = [
    # Reports index
    "ReportMetadata",
    "ReportsIndex",
    "generate_reports_index",
    # Evidence packaging
    "PackageFile",
    "PackageManifest",
    "create_evidence_package",
    # Run summary
    "RunSummary",
    "TimelineEvent",
    "generate_run_summary",
    "validate_evidence_completeness",
]
