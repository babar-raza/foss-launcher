"""Review-to-taskcard generator (TC-2537).

Parses ``review_report.json``, identifies dimensions scoring below 6 on
any page, and generates follow-up taskcard drafts targeting the specific
quality issues.  One taskcard is generated per failing dimension (not
per page) to keep remediation focused.

Usage:
    from launch.review.taskcard_generator import TaskcardGenerator

    gen = TaskcardGenerator(review_report)
    drafts = gen.generate()
    # drafts is a list of TaskcardDraft dataclasses
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .rubric import DIMENSION_MAP, TASKCARD_THRESHOLD

logger = logging.getLogger(__name__)


# Dimension-to-worker mapping: which pipeline component to fix
_DIMENSION_WORKER_MAP: Dict[str, Dict[str, str]] = {
    "RD-01": {"worker": "W5", "component": "multi_pass.py", "fix_type": "evidence grounding"},
    "RD-02": {"worker": "W10", "component": "worker.py", "fix_type": "contradiction resolver"},
    "RD-03": {"worker": "W4", "component": "worker.py", "fix_type": "slug generation"},
    "RD-04": {"worker": "W5/sanitizer", "component": "content_sanitizer.py", "fix_type": "code fence repair"},
    "RD-05": {"worker": "W5", "component": "multi_pass.py", "fix_type": "prompt leak prevention"},
    "RD-06": {"worker": "W5", "component": "section_templates.yaml", "fix_type": "structure enforcement"},
    "RD-07": {"worker": "W5/sanitizer", "component": "content_sanitizer.py", "fix_type": "heading normalization"},
    "RD-08": {"worker": "W5", "component": "multi_pass.py", "fix_type": "claim injection"},
    "RD-09": {"worker": "W5", "component": "prompts/", "fix_type": "readability prompt tuning"},
    "RD-10": {"worker": "W6", "component": "worker.py", "fix_type": "SEO metadata generation"},
    "RD-11": {"worker": "W5", "component": "generators/", "fix_type": "code example improvement"},
    "RD-12": {"worker": "W8", "component": "worker.py", "fix_type": "link validation"},
}


@dataclasses.dataclass
class TaskcardDraft:
    """A generated taskcard draft for a failing dimension."""

    dimension_id: str
    title: str
    objective: str
    affected_pages: List[Dict[str, Any]]
    worker: str
    component: str
    fix_type: str
    markdown: str


class TaskcardGenerator:
    """Generates follow-up taskcard drafts from review report results."""

    def __init__(self, review_report: Dict[str, Any]) -> None:
        self.report = review_report

    def _identify_failing_dimensions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Find dimensions with any page scoring below threshold.

        Returns:
            Dict mapping dimension_id -> list of affected page info dicts.
        """
        failing: Dict[str, List[Dict[str, Any]]] = {}

        for page in self.report.get("pages", []):
            path = page.get("path", "unknown")
            for ds in page.get("dimension_scores", []):
                dim_id = ds.get("dimension_id", "")
                score = ds.get("score", 10)
                if score < TASKCARD_THRESHOLD:
                    if dim_id not in failing:
                        failing[dim_id] = []
                    failing[dim_id].append({
                        "path": path,
                        "score": score,
                        "issues": ds.get("issues", []),
                    })

        return failing

    def _generate_draft(
        self,
        dimension_id: str,
        affected: List[Dict[str, Any]],
        draft_index: int,
    ) -> TaskcardDraft:
        """Generate a single taskcard draft for a failing dimension."""
        dim_meta = DIMENSION_MAP.get(dimension_id)
        dim_name = dim_meta.name if dim_meta else dimension_id
        worker_info = _DIMENSION_WORKER_MAP.get(dimension_id, {
            "worker": "Unknown",
            "component": "unknown",
            "fix_type": "quality improvement",
        })

        # Sort affected pages alphabetically for determinism
        affected_sorted = sorted(affected, key=lambda x: x["path"])

        # Build issue summary
        issue_summary_parts = []
        for ap in affected_sorted:
            page_name = ap["path"].rsplit("/", 1)[-1] if "/" in ap["path"] else ap["path"]
            issue_msgs = [i.get("message", "") for i in ap.get("issues", [])[:2]]
            issue_text = "; ".join(issue_msgs) if issue_msgs else "score below threshold"
            issue_summary_parts.append(
                f"- `{page_name}` (score: {ap['score']}/10) -- {issue_text}"
            )

        affected_list = "\n".join(issue_summary_parts)
        today = datetime.date.today().isoformat()
        tc_id = f"TC-REVIEW-{draft_index:03d}"
        title = f"Fix {dim_name}: quality below threshold on {len(affected_sorted)} page(s)"

        markdown = (
            f"---\n"
            f"id: {tc_id}\n"
            f'title: "{title}"\n'
            f'status: "Draft"\n'
            f'owner: "Unassigned"\n'
            f"priority: P2\n"
            f'updated: "{today}"\n'
            f"depends_on: []\n"
            f"blocks: []\n"
            f"---\n"
            f"\n"
            f"## Objective\n"
            f"\n"
            f"Address {dim_name} ({dimension_id}) quality issues across "
            f"{len(affected_sorted)} page(s) identified by the review agent.\n"
            f"\n"
            f"## Affected pages\n"
            f"\n"
            f"{affected_list}\n"
            f"\n"
            f"## Suggested fix\n"
            f"\n"
            f"**Fix type**: {worker_info['fix_type']}\n"
            f"**Worker**: {worker_info['worker']}\n"
            f"**Component**: {worker_info['component']}\n"
            f"\n"
            f"## Acceptance checks\n"
            f"\n"
            f"- [ ] All affected pages score >= 6 on {dimension_id} after fix\n"
            f"- [ ] No regressions on other dimensions\n"
            f"- [ ] All existing tests pass\n"
        )

        return TaskcardDraft(
            dimension_id=dimension_id,
            title=title,
            objective=f"Address {dim_name} quality issues across {len(affected_sorted)} page(s).",
            affected_pages=affected_sorted,
            worker=worker_info["worker"],
            component=worker_info["component"],
            fix_type=worker_info["fix_type"],
            markdown=markdown,
        )

    def generate(self) -> List[TaskcardDraft]:
        """Generate taskcard drafts for all failing dimensions.

        Returns:
            List of TaskcardDraft objects (one per failing dimension).
            Empty list if all dimensions score >= threshold.
        """
        failing = self._identify_failing_dimensions()
        if not failing:
            return []

        drafts: List[TaskcardDraft] = []
        # Sort by dimension ID for deterministic output
        for idx, dim_id in enumerate(sorted(failing.keys()), start=1):
            affected = failing[dim_id]
            if dim_id not in _DIMENSION_WORKER_MAP:
                logger.warning("Unknown dimension ID %s in review report; skipping.", dim_id)
                continue
            draft = self._generate_draft(dim_id, affected, idx)
            drafts.append(draft)

        return drafts


def write_taskcard_drafts(
    drafts: List[TaskcardDraft],
    output_dir: str | Path,
) -> List[Path]:
    """Write taskcard draft markdown files to the output directory.

    Args:
        drafts: List of TaskcardDraft objects.
        output_dir: Directory to write files to.

    Returns:
        List of written file paths.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    for draft in drafts:
        filename = f"{draft.dimension_id.replace('-', '_').lower()}_fix.md"
        path = out / filename
        path.write_text(draft.markdown, encoding="utf-8")
        written.append(path)
        logger.info("Taskcard draft written: %s", path)

    return written
