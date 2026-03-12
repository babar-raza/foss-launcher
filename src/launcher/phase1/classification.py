"""Phase 1 classification logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, FrozenSet, Optional, Sequence

DEFAULT_ALLOWED_LICENSES: FrozenSet[str] = frozenset({
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "LGPL-2.1",
    "LGPL-3.0",
    "GPL-2.0",
    "GPL-3.0",
    "MPL-2.0",
    "ISC",
    "Unlicense",
})


@dataclass(frozen=True)
class ClassificationResult:
    full_name: str
    decision: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "decision": self.decision,
            "reasons": list(self.reasons),
        }


@dataclass
class ClassifierConfig:
    min_stars: int = 0
    require_readme: bool = True
    require_python: bool = False
    require_license: bool = True
    allowed_licenses: FrozenSet[str] = DEFAULT_ALLOWED_LICENSES
    require_language: Optional[str] = None


def _required_language(config: ClassifierConfig) -> Optional[str]:
    if config.require_language:
        return config.require_language
    if config.require_python:
        return "python"
    return None


def classify_repo(repo: dict[str, Any], *, config: Optional[ClassifierConfig] = None) -> ClassificationResult:
    config = config or ClassifierConfig()
    full_name = repo.get("full_name", "unknown")
    ineligible: list[str] = []
    review: list[str] = []

    if repo.get("is_template", False):
        review.append("repository is a template")

    stars = repo.get("stargazers_count", 0)
    if stars < config.min_stars:
        ineligible.append(f"star count ({stars}) below minimum ({config.min_stars})")

    if config.require_readme:
        has_readme = repo.get("has_readme")
        if has_readme is False:
            ineligible.append("no README file detected")
        elif has_readme is None:
            if not repo.get("description") and repo.get("size", 0) < 5:
                review.append("unable to confirm README presence (small repo, no description)")

    required_language = _required_language(config)
    if required_language:
        language = str(repo.get("language", "") or "")
        if not language:
            review.append("no primary language detected")
        elif language.lower() != required_language.lower():
            review.append(f"primary language is '{language}', not {required_language}")

    if config.require_license:
        license_info = repo.get("license")
        if not license_info:
            ineligible.append("no license detected")
        else:
            spdx_id = license_info.get("spdx_id") if isinstance(license_info, dict) else None
            if spdx_id is None or spdx_id == "NOASSERTION":
                review.append(f"license SPDX unresolved: {spdx_id}")
            elif spdx_id not in config.allowed_licenses:
                ineligible.append(f"license '{spdx_id}' not in allowed set")

    if ineligible:
        return ClassificationResult(full_name=full_name, decision="ineligible", reasons=tuple(ineligible))
    if review:
        return ClassificationResult(full_name=full_name, decision="needs_review", reasons=tuple(review))
    return ClassificationResult(full_name=full_name, decision="eligible", reasons=("metadata checks passed",))


def classify_repos(
    repos: Sequence[dict[str, Any]],
    *,
    config: Optional[ClassifierConfig] = None,
) -> list[ClassificationResult]:
    return [classify_repo(repo, config=config) for repo in repos]


def classify_inspection(
    inspection: dict[str, Any],
    *,
    config: Optional[ClassifierConfig] = None,
) -> ClassificationResult:
    config = config or ClassifierConfig()
    repo = inspection.get("repo", {})
    full_name = repo.get("full_name", inspection.get("repo_url", "unknown"))
    ineligible: list[str] = []
    review: list[str] = []

    if repo.get("is_template", False):
        review.append("repository is a template")
    if repo.get("archived", False):
        ineligible.append("repository is archived")
    if repo.get("fork", False):
        ineligible.append("repository is a fork")

    stars = repo.get("stargazers_count", 0)
    if stars < config.min_stars:
        ineligible.append(f"star count ({stars}) below minimum ({config.min_stars})")

    acquisition = inspection.get("acquisition", {})
    repo_signals = acquisition.get("repo_signals", {})
    if acquisition.get("failure_state"):
        ineligible.append(f"acquisition failure: {acquisition['failure_state']}")
    if repo_signals.get("is_empty_clone"):
        ineligible.append("clone is empty")
    if config.require_readme and not repo_signals.get("readme_present", False):
        ineligible.append("no README detected in cloned repository")

    shared_facts = inspection.get("shared_facts", {})
    license_type = str(shared_facts.get("license_type", "") or "")
    metadata_license = repo.get("license") or {}
    metadata_spdx = metadata_license.get("spdx_id") if isinstance(metadata_license, dict) else ""
    effective_license = metadata_spdx or license_type
    if config.require_license:
        if not effective_license:
            ineligible.append("no license detected from metadata or manifests")
        elif effective_license == "NOASSERTION":
            review.append("license SPDX unresolved: NOASSERTION")
        elif effective_license not in config.allowed_licenses:
            ineligible.append(f"license '{effective_license}' not in allowed set")

    required_language = _required_language(config)
    detected_language = (
        shared_facts.get("primary_language")
        or repo_signals.get("inferred_language")
        or inspection.get("platform", "")
    )
    if required_language:
        if not detected_language:
            review.append("no platform/language detected from clone inspection")
        elif str(detected_language).lower() != required_language.lower():
            review.append(f"detected platform/language is '{detected_language}', not {required_language}")

    if not shared_facts.get("package_name"):
        review.append("package name not extracted from repository manifests")
    if not repo_signals.get("detected_manifest_files"):
        review.append("no known manifest file detected at repository root")

    if ineligible:
        return ClassificationResult(full_name=full_name, decision="ineligible", reasons=tuple(ineligible))
    if review:
        return ClassificationResult(full_name=full_name, decision="needs_review", reasons=tuple(review))
    return ClassificationResult(
        full_name=full_name,
        decision="eligible",
        reasons=("source-grounded phase1 inspection passed",),
    )


__all__ = [
    "ClassificationResult",
    "ClassifierConfig",
    "DEFAULT_ALLOWED_LICENSES",
    "classify_inspection",
    "classify_repo",
    "classify_repos",
]
