"""Shared Phase 1 acquisition logic."""
from __future__ import annotations

import functools
import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CLONE_SHA_MARKER = ".clone_sha"
_CLONE_TIMESTAMP_MARKER = ".clone_timestamp"
_CLONE_URL_MARKER = ".clone_url"
_STALE_CACHE_DAYS = 7
_SLUG_STOP_WORDS = frozenset({"foss", "for", "the", "a", "ai", "org", "net"})
_MANIFEST_LANGUAGE_MAP: dict[str, str] = {
    "package.json": "node/typescript",
    "pyproject.toml": "python",
    "setup.py": "python",
    "setup.cfg": "python",
    "go.mod": "go",
    "cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "java",
    "gemfile": "ruby",
    "composer.json": "php",
}


@dataclass(frozen=True)
class AcquisitionResult:
    repo_dir: Path
    repo_sha: str
    is_fresh_clone: bool
    artifact: dict[str, Any]


def _normalize_slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _extract_brand_from_url(repo_url: str) -> str:
    try:
        org = repo_url.split("/")[3]
        segments = re.split(r"[-._\\s]+", org.lower())
        return next(
            (p for p in segments if p and p not in _SLUG_STOP_WORDS and len(p) > 1),
            "unknown",
        )
    except (IndexError, AttributeError):
        return "unknown"


def check_remote_sha(repo_url: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "ls-remote", str(repo_url), "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        line = result.stdout.strip()
        if line:
            return line.split()[0]
        return ""
    except Exception as exc:
        logger.warning("[Clone] git ls-remote network failure: %s", exc)
        return None


def _get_cache_dir(brand: str, family: str, platform: str, work_dir: Path) -> Path:
    slug = f"{_normalize_slug(brand)}_{_normalize_slug(family)}_{_normalize_slug(platform)}"
    cache_root = work_dir.parent.parent / ".clone_cache"
    return cache_root / slug


def _get_repo_sha(repo_dir: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _log_cache_age(cache_dir: Path, repo_url: str) -> None:
    ts_marker = cache_dir / _CLONE_TIMESTAMP_MARKER
    if not ts_marker.exists():
        return
    try:
        ts = datetime.fromisoformat(ts_marker.read_text(encoding="utf-8").strip())
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - ts).days
        if age_days > _STALE_CACHE_DAYS:
            logger.warning(
                "[Clone] Cache for %s is %d days old - consider force_refresh=True to update",
                repo_url,
                age_days,
            )
    except (ValueError, OSError):
        return


def _write_cache_timestamp(cache_dir: Path) -> None:
    try:
        (cache_dir / _CLONE_TIMESTAMP_MARKER).write_text(
            datetime.now(timezone.utc).isoformat(),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning(
            "[Clone] Could not write .clone_timestamp to %s: %s - stale cache age detection disabled.",
            cache_dir,
            exc,
        )


def _check_url_collision(cache_dir: Path, repo_url: str) -> None:
    url_marker = cache_dir / _CLONE_URL_MARKER
    if not url_marker.exists():
        return
    cached_url = url_marker.read_text(encoding="utf-8").strip()
    if cached_url != repo_url:
        raise RuntimeError(
            f"[Clone] Cache collision: slug {cache_dir.name!r} was previously cloned "
            f"from {cached_url!r} but is now requested for {repo_url!r}."
        )


def clone_repo_cached(
    repo_url: str,
    *,
    family: str,
    platform: str,
    brand: str | None = None,
    work_dir: Path | None = None,
    force_refresh: bool = False,
    allowed_org_prefixes: list[str] | None = None,
) -> tuple[Path, str, bool]:
    if allowed_org_prefixes is not None and not any(repo_url.startswith(p) for p in allowed_org_prefixes):
        raise ValueError(
            f"[Clone] repo_url {repo_url!r} is not in the allowed org list. "
            "Add the organization to configs/intake_config.yaml to allow cloning."
        )
    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="launcher-phase1-"))
    work_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = _get_cache_dir(brand or _extract_brand_from_url(repo_url), family, platform, work_dir)
    marker = cache_dir / _CLONE_SHA_MARKER

    if force_refresh and cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)

    remote_sha = check_remote_sha(repo_url)
    if remote_sha and marker.exists():
        cached_sha = marker.read_text(encoding="utf-8").strip()
        if cached_sha == remote_sha:
            cache_contents = list(cache_dir.iterdir()) if cache_dir.exists() else []
            if cache_contents:
                _check_url_collision(cache_dir, repo_url)
                _log_cache_age(cache_dir, repo_url)
                return cache_dir, remote_sha, False
            shutil.rmtree(cache_dir, ignore_errors=True)

    if not remote_sha and cache_dir.exists() and marker.exists():
        cached_sha = marker.read_text(encoding="utf-8").strip()
        cache_contents = list(cache_dir.iterdir()) if cache_dir.exists() else []
        if cache_contents:
            _check_url_collision(cache_dir, repo_url)
            _log_cache_age(cache_dir, repo_url)
            return cache_dir, cached_sha, False
        shutil.rmtree(cache_dir, ignore_errors=True)

    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", str(repo_url), str(cache_dir)],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    sha = remote_sha or _get_repo_sha(cache_dir)
    marker.write_text(sha, encoding="utf-8")
    (cache_dir / _CLONE_URL_MARKER).write_text(repo_url, encoding="utf-8")
    _write_cache_timestamp(cache_dir)
    return cache_dir, sha, True


def resolve_tier(launch_tier: str, default_auto_tier: str = "core") -> str:
    return default_auto_tier if launch_tier == "auto" else launch_tier


def compute_acquisition_confidence(provenance: dict[str, str]) -> str:
    values = set(provenance.values()) - {"config_override"}
    if not values or values == {"families_yaml"}:
        return "high"
    if "inferred_default" in values:
        return "low"
    return "medium"


def build_repo_signals(repo_dir: Path) -> dict[str, Any]:
    try:
        if not repo_dir.is_dir():
            return {
                "readme_present": False,
                "is_empty_clone": True,
                "files_estimated": 0,
                "detected_manifest_files": [],
                "inferred_language": "",
            }
        children = list(repo_dir.iterdir())
        if not children:
            return {
                "readme_present": False,
                "is_empty_clone": True,
                "files_estimated": 0,
                "detected_manifest_files": [],
                "inferred_language": "",
            }
        readme_present = any(
            child.name.lower() in {"readme.md", "readme.rst", "readme.txt", "readme"}
            for child in children
            if child.is_file()
        )
        manifests: list[str] = []
        inferred_language = ""
        for child in children:
            if not child.is_file():
                continue
            lower_name = child.name.lower()
            if lower_name in _MANIFEST_LANGUAGE_MAP:
                manifests.append(child.name)
                if not inferred_language:
                    inferred_language = _MANIFEST_LANGUAGE_MAP[lower_name]
            elif child.suffix.lower() == ".csproj":
                manifests.append(child.name)
                if not inferred_language:
                    inferred_language = "dotnet"
            elif child.suffix.lower() == ".gemspec":
                manifests.append(child.name)
                if not inferred_language:
                    inferred_language = "ruby"
        return {
            "readme_present": readme_present,
            "is_empty_clone": False,
            "files_estimated": min(len(children), 100),
            "detected_manifest_files": manifests,
            "inferred_language": inferred_language,
        }
    except OSError:
        return {
            "readme_present": False,
            "is_empty_clone": True,
            "files_estimated": 0,
            "detected_manifest_files": [],
            "inferred_language": "",
        }


def build_acquisition_artifact(
    *,
    family: str,
    platform: str,
    repo_url: str,
    display_name: str,
    canonical_import: str,
    runtime_import: str,
    launch_tier: str,
    repo_sha: str,
    repo_dir: Path,
    discovered_at: str,
    is_fresh_clone: bool,
    provenance: dict[str, str],
) -> dict[str, Any]:
    repo_signals = build_repo_signals(repo_dir)
    return {
        "phase": "phase1_acquisition",
        "family": family,
        "platform": platform,
        "repo_url": repo_url,
        "display_name": display_name,
        "canonical_import": canonical_import,
        "runtime_import": runtime_import,
        "launch_tier": launch_tier,
        "repo_sha": repo_sha,
        "repo_dir": str(repo_dir),
        "discovered_at": discovered_at,
        "is_fresh_clone": is_fresh_clone,
        "clone_cache_hit": not is_fresh_clone and bool(repo_sha),
        "field_provenance": provenance,
        "acquisition_confidence": compute_acquisition_confidence(provenance),
        "repo_signals": repo_signals,
        "failure_state": "" if repo_dir.is_dir() and not repo_signals["is_empty_clone"] else "unusable_clone",
    }


@functools.lru_cache(maxsize=8)
def load_allowed_org_prefixes(config_path: Path) -> tuple[str, ...]:
    try:
        from launcher.phase1.config_loader import load_intake_config

        cfg = load_intake_config(config_path)
        return tuple(f"https://github.com/{org.name}/" for org in cfg.organizations)
    except Exception:
        logger.warning(
            "[Phase1] Could not load intake config for org allowlist - clone restriction disabled. Check %s exists.",
            config_path,
        )
        return ()


def acquire_repository(
    *,
    family: str,
    platform: str,
    repo_url: str,
    display_name: str,
    canonical_import: str,
    runtime_import: str,
    launch_tier: str,
    provenance: dict[str, str],
    work_dir: Path,
    allowed_org_prefixes: list[str] | None = None,
) -> AcquisitionResult:
    repo_dir, repo_sha, is_fresh_clone = clone_repo_cached(
        repo_url,
        family=family,
        platform=platform,
        work_dir=work_dir,
        allowed_org_prefixes=allowed_org_prefixes,
    )
    discovered_at = datetime.now(timezone.utc).isoformat()
    artifact = build_acquisition_artifact(
        family=family,
        platform=platform,
        repo_url=repo_url,
        display_name=display_name,
        canonical_import=canonical_import,
        runtime_import=runtime_import,
        launch_tier=launch_tier,
        repo_sha=repo_sha,
        repo_dir=repo_dir,
        discovered_at=discovered_at,
        is_fresh_clone=is_fresh_clone,
        provenance=provenance,
    )
    if artifact["failure_state"]:
        raise RuntimeError(
            f"[Phase1] Acquisition produced unusable clone state for {repo_url!r}: {artifact['failure_state']}"
        )
    return AcquisitionResult(
        repo_dir=repo_dir,
        repo_sha=repo_sha,
        is_fresh_clone=is_fresh_clone,
        artifact=artifact,
    )


__all__ = [
    "AcquisitionResult",
    "_CLONE_SHA_MARKER",
    "_CLONE_TIMESTAMP_MARKER",
    "_CLONE_URL_MARKER",
    "acquire_repository",
    "build_acquisition_artifact",
    "build_repo_signals",
    "check_remote_sha",
    "clone_repo_cached",
    "compute_acquisition_confidence",
    "load_allowed_org_prefixes",
    "resolve_tier",
]
