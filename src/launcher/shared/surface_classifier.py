"""Repository richness classification and profiling.

Classifies repositories into Tier A/B/C based on documentation depth,
example coverage, API surface, and build/CI signals.

Also builds a detailed RepoProfile with 13+ signals for use by
evidence mapping, slug generation, and planning.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from launcher.models.product import RepoProfile, RichnessResult, RichnessTier
from launcher.models.understanding import RepoInfo


def classify_richness(repo_info: RepoInfo) -> RichnessResult:
    """Classify a repository into richness Tier A, B, or C.

    Scoring rubric
    ---------------
    - ``doc_files``:  1 pt each, capped at 10
    - ``readme_length``:  5 pts if > 500 chars
    - ``example_files``:  1 pt each, capped at 10
    - ``has_tests``:  3 pts
    - ``has_ci``:  2 pts

    Uses SharedFacts if populated, otherwise infers from file_tree.

    Thresholds
    ----------
    - Tier A: score >= 25
    - Tier B: score >= 12
    - Tier C: score < 12
    """
    score = 0
    reasons: list[str] = []

    # doc_files
    doc_count = min(len(repo_info.doc_paths), 10)
    score += doc_count
    reasons.append(f"doc_files={doc_count}")

    # readme_length
    readme_len = len(repo_info.readme_summary)
    if readme_len > 500:
        score += 5
        reasons.append("readme>500")

    # example_files
    example_count = min(len(repo_info.example_paths), 10)
    score += example_count
    reasons.append(f"example_files={example_count}")

    # has_tests / has_ci — prefer shared_facts, fall back to file_tree scan
    facts = repo_info.shared_facts
    has_tests = facts.has_tests if facts.has_tests else any(_is_test_path(p) for p in repo_info.file_tree)
    if has_tests:
        score += 3
        reasons.append("has_tests")

    has_ci = facts.has_ci if facts.has_ci else any(_is_ci_path(p) for p in repo_info.file_tree)
    if has_ci:
        score += 2
        reasons.append("has_ci")

    # Determine tier
    if score >= 25:
        tier = RichnessTier.A
    elif score >= 12:
        tier = RichnessTier.B
    else:
        tier = RichnessTier.C

    return RichnessResult(
        tier=tier,
        score=score,
        reason="; ".join(reasons),
    )


# TC-3903: Minimum combined (example_files + extracted_snippets) to be considered
# code-evidence-rich.  Repos below this threshold have code_evidence_sparse=True
# regardless of richness tier.
_CODE_EVIDENCE_SPARSE_THRESHOLD: int = 3


def classify_richness_with_surface(
    repo_info: RepoInfo,
    *,
    api_confidence: str = "low",
    public_class_count: int = 0,
    extracted_snippet_count: int = 0,
) -> RichnessResult:
    """Like :func:`classify_richness` but also scores API surface fields.

    TC-3871: composite scoring adds:
    - API surface confidence: +0 (low), +5 (medium), +10 (high)
    - Public class count: +5 if >20 classes
    - Extracted snippet count: +3 if >=10 extracted snippets (code evidence
      from the actual repo, not LLM-generated)

    TC-3903: Also sets ``code_evidence_sparse`` — True when combined
    example_files + extracted_snippets < :data:`_CODE_EVIDENCE_SPARSE_THRESHOLD`.
    Orthogonal to tier: a Tier B repo (docs + tests + CI) with zero executable
    examples gets ``code_evidence_sparse=True`` (e.g. 3D TypeScript pilot).

    Thresholds remain: Tier A >=25, Tier B >=12, Tier C <12.
    """
    base = classify_richness(repo_info)
    extra = 0
    reasons = [base.reason]

    # API surface confidence signal
    confidence_pts = {"high": 10, "medium": 5, "low": 0}
    pts = confidence_pts.get(api_confidence, 0)
    extra += pts
    reasons.append(f"api_confidence={api_confidence}({pts})")

    # Public class count signal (existing)
    if public_class_count > 20:
        extra += 5
        reasons.append(f"public_classes={public_class_count}>20")

    # TC-3871: Extracted snippet count signal — code evidence from the repo
    # 10+ extracted snippets means concrete code examples exist in the repo
    if extracted_snippet_count >= 10:
        extra += 3
        reasons.append(f"extracted_snippets={extracted_snippet_count}>=10")

    new_score = base.score + extra

    if new_score >= 25:
        tier = RichnessTier.A
    elif new_score >= 12:
        tier = RichnessTier.B
    else:
        tier = RichnessTier.C

    # TC-3903: Code evidence sparsity — orthogonal to richness tier.
    # Counts executable proof available in the repo (capped to avoid saturation).
    _code_evidence_score = (
        min(len(repo_info.example_paths), 10)
        + min(extracted_snippet_count, 10)
    )
    code_evidence_sparse = _code_evidence_score < _CODE_EVIDENCE_SPARSE_THRESHOLD
    reasons.append(
        f"code_evidence={_code_evidence_score}"
        f"(sparse={code_evidence_sparse})"
    )

    return RichnessResult(
        tier=tier,
        score=new_score,
        reason="; ".join(reasons),
        code_evidence_sparse=code_evidence_sparse,
    )


def build_repo_profile(
    repo_info: RepoInfo,
    *,
    api_surface_count: int = 0,
) -> RepoProfile:
    """Build a detailed RepoProfile with 13+ signals from repo metadata.

    All signals are deterministic (no LLM, no network).
    """
    file_tree = repo_info.file_tree
    facts = repo_info.shared_facts

    # README detection
    has_readme = any(
        Path(p).name.lower().startswith("readme") for p in file_tree
    )
    readme_size_bytes = len(repo_info.readme_summary.encode("utf-8"))

    # Markdown file count
    markdown_file_count = sum(
        1 for p in file_tree
        if p.lower().endswith(".md") or p.lower().endswith(".markdown")
    )

    # Type stubs
    has_type_stubs = any(p.endswith(".pyi") for p in file_tree)

    # Language breakdown (top 15)
    ext_counter: Counter[str] = Counter()
    for p in file_tree:
        ext = Path(p).suffix.lower().lstrip(".")
        if ext:
            ext_counter[ext] += 1
    language_breakdown = dict(
        sorted(ext_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    )

    # Confidence and warnings
    confidence = 0.8
    warnings: list[str] = []
    if not file_tree:
        confidence = 0.1
        warnings.append("no_paths")
    else:
        if not has_readme:
            confidence -= 0.15
            warnings.append("no_readme")
        if not repo_info.doc_paths:
            confidence -= 0.15
            warnings.append("no_docs")
        if not repo_info.example_paths:
            warnings.append("no_examples")
    confidence = round(max(0.0, min(1.0, confidence)), 4)

    return RepoProfile(
        docs_depth=len(repo_info.doc_paths) + len(repo_info.example_paths),
        examples_count=len(repo_info.example_paths),
        api_surface_count=api_surface_count,
        has_readme=has_readme,
        readme_size_bytes=readme_size_bytes,
        has_docs_folder=facts.has_docs_folder,
        has_examples_folder=facts.has_examples_folder,
        has_ci=facts.has_ci or any(_is_ci_path(p) for p in file_tree),
        has_tests=facts.has_tests or any(_is_test_path(p) for p in file_tree),
        has_type_stubs=has_type_stubs,
        markdown_file_count=markdown_file_count,
        primary_language=facts.primary_language,
        build_systems=facts.build_systems,
        language_breakdown=language_breakdown,
        confidence=confidence,
        warnings=sorted(warnings),
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_TEST_MARKERS = ("test_", "tests/", "test/", "_test.py", "_test.java", "Test.java")
_CI_MARKERS = (".github/workflows/", ".gitlab-ci", "Jenkinsfile", ".circleci/", "azure-pipelines")


def _is_test_path(path: str) -> bool:
    return any(marker in path for marker in _TEST_MARKERS)


def _is_ci_path(path: str) -> bool:
    return any(marker in path for marker in _CI_MARKERS)
