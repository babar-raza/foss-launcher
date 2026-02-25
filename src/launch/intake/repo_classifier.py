"""Repository eligibility classifier.

Classifies GitHub repositories as ``eligible``, ``ineligible``, or
``needs_review`` based on deterministic heuristics applied to repo metadata.

Spec reference: specs/49_github_intake.md  Section 5
TC: TC-2541
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Sequence

logger = logging.getLogger(__name__)

# Default OSS license SPDX identifiers considered eligible.
DEFAULT_ALLOWED_LICENSES: FrozenSet[str] = frozenset({
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "LGPL-2.1", "LGPL-3.0", "GPL-2.0", "GPL-3.0",
    "MPL-2.0", "ISC", "Unlicense",
})


@dataclass(frozen=True)
class ClassificationResult:
    """Result of classifying a single repository."""

    full_name: str
    decision: str  # "eligible", "ineligible", "needs_review"
    reasons: tuple  # Immutable sequence of reason strings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "full_name": self.full_name,
            "decision": self.decision,
            "reasons": list(self.reasons),
        }


@dataclass
class ClassifierConfig:
    """Configuration for the repo classifier."""

    min_stars: int = 0
    require_readme: bool = True
    require_python: bool = True
    require_license: bool = True
    allowed_licenses: FrozenSet[str] = DEFAULT_ALLOWED_LICENSES
    require_language: Optional[str] = None


def classify_repo(
    repo: Dict[str, Any],
    *,
    config: Optional[ClassifierConfig] = None,
) -> ClassificationResult:
    """Classify a single repository as eligible, ineligible, or needs_review.

    The classification is purely deterministic on the input repo metadata.
    No network calls or LLM invocations.

    Args:
        repo: Slim repo dict (as returned by org_scanner._slim_repo).
        config: Classifier configuration. Uses defaults if None.

    Returns:
        ClassificationResult with decision and reasons.
    """
    if config is None:
        config = ClassifierConfig()

    full_name = repo.get("full_name", "unknown")
    ineligible_reasons: List[str] = []
    review_reasons: List[str] = []

    # 1. Template check
    if repo.get("is_template", False):
        review_reasons.append("repository is a template")

    # 2. Stars threshold
    stars = repo.get("stargazers_count", 0)
    if stars < config.min_stars:
        ineligible_reasons.append(
            f"star count ({stars}) below minimum ({config.min_stars})"
        )

    # 3. README check (heuristic: repos with description or size > 0 likely have README)
    # We check the 'description' field as a proxy -- for precise check, we would
    # need a separate API call to check file existence, which is done at scan time
    # if the scanner provides a 'has_readme' field.
    if config.require_readme:
        has_readme = repo.get("has_readme")
        if has_readme is not None and not has_readme:
            ineligible_reasons.append("no README file detected")
        elif has_readme is None:
            # Heuristic: empty description AND very small size suggests no readme
            if not repo.get("description") and repo.get("size", 0) < 5:
                review_reasons.append("unable to confirm README presence (small repo, no description)")

    # 4. Language check
    # require_language takes precedence over require_python when set.
    if config.require_language:
        language = repo.get("language", "")
        required = config.require_language
        if language and language.lower() != required.lower():
            review_reasons.append(f"primary language is '{language}', not {required}")
        elif not language:
            review_reasons.append("no primary language detected")
    elif config.require_python:
        language = repo.get("language", "")
        if language and language.lower() != "python":
            review_reasons.append(f"primary language is '{language}', not Python")
        elif not language:
            review_reasons.append("no primary language detected")

    # 5. License check
    if config.require_license:
        license_info = repo.get("license")
        if not license_info:
            ineligible_reasons.append("no license detected")
        else:
            spdx_id = license_info.get("spdx_id") if isinstance(license_info, dict) else None
            if spdx_id is None or spdx_id == "NOASSERTION":
                review_reasons.append(f"license SPDX unresolved: {spdx_id}")
            elif spdx_id not in config.allowed_licenses:
                ineligible_reasons.append(
                    f"license '{spdx_id}' not in allowed set"
                )

    # 6. Size check -- very small repos are suspicious
    size = repo.get("size", 0)
    if size < 10:
        review_reasons.append(f"very small repo ({size} KB)")

    # Decision logic
    if ineligible_reasons:
        decision = "ineligible"
        reasons = tuple(ineligible_reasons)
    elif review_reasons:
        decision = "needs_review"
        reasons = tuple(review_reasons)
    else:
        decision = "eligible"
        reasons = ("all checks passed",)

    result = ClassificationResult(
        full_name=full_name,
        decision=decision,
        reasons=reasons,
    )
    logger.info("Classified %s -> %s (%s)", full_name, decision, "; ".join(reasons))
    return result


def classify_repos(
    repos: Sequence[Dict[str, Any]],
    *,
    config: Optional[ClassifierConfig] = None,
) -> List[ClassificationResult]:
    """Classify multiple repositories.

    Args:
        repos: List of slim repo dicts.
        config: Classifier configuration.

    Returns:
        List of ClassificationResult, one per repo, in input order.
    """
    return [classify_repo(r, config=config) for r in repos]
