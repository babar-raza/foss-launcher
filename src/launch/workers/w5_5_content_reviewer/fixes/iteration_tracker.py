"""Iteration tracking for W5.5 ContentReviewer auto-fix loop.

This module tracks the number of fix iterations per page to enforce the
maximum of 3 iterations per page. This prevents infinite fix loops and
ensures graceful degradation when auto-fixes cannot fully resolve issues.

TC-1100-P2: W5.5 ContentReviewer Phase 2 - Auto-Fix Capabilities
Pattern: Simple state tracker with JSON persistence

Spec reference: abstract-hugging-kite.md:286-300 (Fix iteration limits)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any


class IterationTracker:
    """Tracks fix iterations per page to enforce max 3 iterations.

    Each page can be fixed up to 3 times before being marked as unfixable.
    This prevents infinite loops and provides clear diagnostics when auto-fixes
    cannot resolve issues.

    Usage:
        tracker = IterationTracker(run_dir)

        if tracker.can_iterate(page_id):
            tracker.record_iteration(page_id, fix_type="claim_markers", count=5)
            # ... apply fixes ...

        tracker.write_iterations_json()

    Attributes:
        run_dir: Path to run directory (RUN_DIR)
        iterations: Dict mapping page_id -> iteration data

    Spec reference: abstract-hugging-kite.md:292-296 (Iteration tracking)
    """

    MAX_ITERATIONS = 3

    def __init__(self, run_dir: Path):
        """Initialize iteration tracker.

        Args:
            run_dir: Path to run directory
        """
        self.run_dir = run_dir
        self.iterations: Dict[str, Dict[str, Any]] = {}

    def record_iteration(
        self,
        page_id: str,
        fix_type: str,
        count: int
    ) -> int:
        """Record an iteration for a page.

        Args:
            page_id: Page identifier (e.g., "docs/overview/index")
            fix_type: Type of fix applied (e.g., "claim_markers")
            count: Number of fixes applied in this iteration

        Returns:
            New iteration count for this page
        """
        if page_id not in self.iterations:
            self.iterations[page_id] = {
                "iteration_count": 0,
                "fixes_applied": []
            }

        # Increment iteration count
        self.iterations[page_id]["iteration_count"] += 1
        iteration_num = self.iterations[page_id]["iteration_count"]

        # Record fix details
        self.iterations[page_id]["fixes_applied"].append({
            "iteration": iteration_num,
            "fix_type": fix_type,
            "count": count
        })

        return iteration_num

    def can_iterate(self, page_id: str) -> bool:
        """Check if page can be iterated (< MAX_ITERATIONS).

        Args:
            page_id: Page identifier

        Returns:
            True if page can be iterated, False otherwise
        """
        if page_id not in self.iterations:
            return True

        return self.iterations[page_id]["iteration_count"] < self.MAX_ITERATIONS

    def get_iteration_count(self, page_id: str) -> int:
        """Get current iteration count for a page.

        Args:
            page_id: Page identifier

        Returns:
            Current iteration count (0 if page not tracked)
        """
        if page_id not in self.iterations:
            return 0

        return self.iterations[page_id]["iteration_count"]

    def write_iterations_json(self) -> None:
        """Write review_iterations.json to RUN_DIR/artifacts/.

        Output format:
        {
            "schema_version": "1.0",
            "timestamp": "2026-02-09T...",
            "max_iterations": 3,
            "iterations": {
                "page_id": {
                    "iteration_count": 2,
                    "fixes_applied": [
                        {"iteration": 1, "fix_type": "claim_markers", "count": 5},
                        {"iteration": 2, "fix_type": "frontmatter_comments", "count": 2}
                    ]
                }
            }
        }

        Spec reference: abstract-hugging-kite.md:298-300 (Output format)
        """
        artifacts_dir = self.run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        output = {
            "schema_version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "max_iterations": self.MAX_ITERATIONS,
            "iterations": self.iterations
        }

        # Write to review_iterations.json
        iterations_path = artifacts_dir / "review_iterations.json"
        with open(iterations_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
