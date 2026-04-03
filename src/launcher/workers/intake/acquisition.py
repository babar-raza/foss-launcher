"""Runtime acquisition logic for the Intake worker.

All clone/cache/signal logic used by the runtime pipeline lives here.
Pre-pipeline CLI tooling (discover, inspect, batch-onboard) lives in
``launcher.phase1.acquisition`` which re-imports from this module.

Separation rationale: the runtime worker must not depend on pre-pipeline
internals. This module is the single source of truth for clone operations
at runtime.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _force_rmtree(path: Path) -> None:
    """Remove a directory tree, handling read-only files on Windows.

    git sets some files (packed-refs, ORIG_HEAD, etc.) as read-only.
    On Windows, shutil.rmtree with ignore_errors=True silently leaves
    these behind, causing a subsequent git clone to fail on a non-empty
    destination dir (exit status 128).  This helper marks files as
    writable before deletion so the tree is always fully removed.
    """

    def _on_error(func: Any, path_str: str, exc_info: Any) -> None:
        try:
            os.chmod(path_str, stat.S_IWRITE)
            func(path_str)
        except Exception:
            pass

    try:
        # Python 3.12+ uses onexc; earlier versions use onerror.
        try:
            shutil.rmtree(str(path), onexc=_on_error)  # type: ignore[call-arg]
        except TypeError:
            shutil.rmtree(str(path), onerror=_on_error)  # type: ignore[call-arg]
    except Exception:
        pass


from launcher.shared.families_loader import get_manifest_language_map as _get_manifest_language_map

_CLONE_SHA_MARKER = ".clone_sha"
_CLONE_TIMESTAMP_MARKER = ".clone_timestamp"
_CLONE_URL_MARKER = ".clone_url"
_STALE_CACHE_DAYS = 7
_SLUG_STOP_WORDS = frozenset({"foss", "for", "the", "a", "ai", "org", "net", "python", "java"})

# SR-02: License detection constants
_LICENSE_FILE_NAMES: frozenset[str] = frozenset({
    "license", "license.md", "license.txt", "license.rst", "copying",
})

_LICENSE_KEYWORDS: list[tuple[str, str]] = [
    ("MIT LICENSE", "MIT"),
    ("MIT", "MIT"),
    ("APACHE LICENSE", "Apache-2.0"),
    ("APACHE-2.0", "Apache-2.0"),
    ("GNU GENERAL PUBLIC LICENSE", "GPL"),
    ("GNU LESSER GENERAL PUBLIC", "LGPL"),
    ("BSD 2-CLAUSE", "BSD-2-Clause"),
    ("BSD 3-CLAUSE", "BSD-3-Clause"),
    ("MOZILLA PUBLIC LICENSE", "MPL-2.0"),
    ("ISC LICENSE", "ISC"),
]


def _detect_license(repo_dir: Path) -> tuple[bool, str]:
    """Detect presence and type of open-source license at repo root.

    Scans for LICENSE, LICENSE.md, LICENSE.txt, COPYING at repo root.
    Returns (license_detected: bool, license_type: str).
    Reads only the first 500 bytes to bound I/O cost.
    """
    for child in sorted(repo_dir.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_file():
            continue
        if child.name.lower() not in _LICENSE_FILE_NAMES:
            continue
        try:
            content = child.read_bytes()[:500].decode("utf-8", errors="replace").upper()
        except OSError:
            continue
        for keyword, license_type in _LICENSE_KEYWORDS:
            if keyword in content:
                logger.debug("[Intake] license detected: %s from %s", license_type, child.name)
                return True, license_type
        # File exists but keyword not in first 500 bytes — still present
        return True, "unknown"
    return False, ""


def _normalize_slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _extract_brand_from_org(org: str) -> str:
    """Canonical brand extractor — single source of truth for brand normalization.

    Splits a raw GitHub org/login string on hyphens, dots, underscores, and whitespace,
    then returns the first segment that is not a stop word and is longer than one character.
    Returns ``"unknown"`` when no qualifying segment is found.
    """
    segments = re.split(r"[-._\s]+", org.lower())
    return next(
        (p for p in segments if p and p not in _SLUG_STOP_WORDS and len(p) > 1),
        "unknown",
    )


def _extract_brand_from_url(repo_url: str) -> str:
    """Extract brand name from the GitHub org segment of a repository URL."""
    try:
        org = repo_url.split("/")[3]
        return _extract_brand_from_org(org)
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
        work_dir = Path(tempfile.mkdtemp(prefix="launcher-intake-"))
    work_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = _get_cache_dir(brand or _extract_brand_from_url(repo_url), family, platform, work_dir)
    marker = cache_dir / _CLONE_SHA_MARKER

    if force_refresh and cache_dir.exists():
        _force_rmtree(cache_dir)

    remote_sha = check_remote_sha(repo_url)
    if remote_sha and marker.exists():
        cached_sha = marker.read_text(encoding="utf-8").strip()
        if cached_sha == remote_sha:
            cache_contents = list(cache_dir.iterdir()) if cache_dir.exists() else []
            if cache_contents:
                _check_url_collision(cache_dir, repo_url)
                _log_cache_age(cache_dir, repo_url)
                return cache_dir, remote_sha, False
            _force_rmtree(cache_dir)

    if not remote_sha and cache_dir.exists() and marker.exists():
        cached_sha = marker.read_text(encoding="utf-8").strip()
        cache_contents = list(cache_dir.iterdir()) if cache_dir.exists() else []
        if cache_contents:
            _check_url_collision(cache_dir, repo_url)
            _log_cache_age(cache_dir, repo_url)
            return cache_dir, cached_sha, False
        _force_rmtree(cache_dir)

    # TC-5300: preserve stale cache before attempting fresh clone so we can
    # fall back to it if the network clone fails (e.g. CI without internet).
    stale_backup = cache_dir.parent / (cache_dir.name + "_stale")
    had_stale = cache_dir.exists()
    if had_stale:
        if stale_backup.exists():
            _force_rmtree(stale_backup)
        shutil.copytree(str(cache_dir), str(stale_backup))
        _force_rmtree(cache_dir)

    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", str(repo_url), str(cache_dir)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as clone_exc:
        _force_rmtree(cache_dir)
        if had_stale and stale_backup.exists():
            stale_backup.rename(cache_dir)
            stale_sha = marker.read_text(encoding="utf-8").strip() if marker.exists() else "unknown"
            logger.warning(
                "[Clone] Fresh clone of %r failed (%s). "
                "Falling back to stale cache (sha=%s).",
                repo_url,
                clone_exc,
                stale_sha,
            )
            return cache_dir, stale_sha, False
        raise

    if had_stale and stale_backup.exists():
        _force_rmtree(stale_backup)

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
                "license_detected": False,
                "license_type": "",
            }
        children = list(repo_dir.iterdir())
        if not children:
            return {
                "readme_present": False,
                "is_empty_clone": True,
                "files_estimated": 0,
                "detected_manifest_files": [],
                "inferred_language": "",
                "license_detected": False,
                "license_type": "",
            }
        readme_present = any(
            child.name.lower() in {"readme.md", "readme.rst", "readme.txt", "readme"}
            for child in children
            if child.is_file()
        )
        manifests: list[str] = []
        inferred_language = ""
        _manifest_map = _get_manifest_language_map()
        for child in children:
            if not child.is_file():
                continue
            lower_name = child.name.lower()
            if lower_name in _manifest_map:
                manifests.append(child.name)
                if not inferred_language:
                    inferred_language = _manifest_map[lower_name]
            elif child.suffix.lower() in {".csproj", ".sln"}:
                manifests.append(child.name)
                if not inferred_language:
                    inferred_language = "dotnet"
            elif child.suffix.lower() == ".gemspec":
                manifests.append(child.name)
                if not inferred_language:
                    inferred_language = "ruby"
        # SR-01: Shallow subdir scan — catch .csproj/.sln one level below root
        # (common .NET repo layout: MyLib/MyLib.csproj).
        # Only fires when root-level scan yielded no language signal.
        if not inferred_language:
            for sub_csproj in sorted(repo_dir.glob("*/*.csproj"))[:5]:
                manifests.append(sub_csproj.name)
                inferred_language = "dotnet"
                logger.debug("[Intake] inferred language dotnet from sub-manifest %s", sub_csproj.name)
                break
        if not inferred_language:
            for sub_sln in sorted(repo_dir.glob("*/*.sln"))[:3]:
                manifests.append(sub_sln.name)
                inferred_language = "dotnet"
                logger.debug("[Intake] inferred language dotnet from sub-manifest %s", sub_sln.name)
                break

        # SR-02: License file detection
        license_detected, license_type = _detect_license(repo_dir)

        return {
            "readme_present": readme_present,
            "is_empty_clone": False,
            "files_estimated": min(len(children), 100),
            "detected_manifest_files": manifests,
            "inferred_language": inferred_language,
            "license_detected": license_detected,
            "license_type": license_type,
        }
    except OSError:
        return {
            "readme_present": False,
            "is_empty_clone": True,
            "files_estimated": 0,
            "detected_manifest_files": [],
            "inferred_language": "",
            "license_detected": False,
            "license_type": "",
        }


def _extract_canonical_import_candidates(
    repo_dir: Path,
    platform: str,
    *,
    scan_limit: int = 30,
) -> tuple[list[str], str]:
    """Extract repo-grounded canonical_import candidates by scanning source files.

    Returns (candidates, confidence) where:
    - candidates: top-ranked namespace/package strings derived from the repo
    - confidence: "high" (one clear winner >=70%), "medium" (found but ambiguous),
      "low" (scan ran but nothing useful found), "none" (platform unsupported)

    Platforms:
    - cpp: scans .h/.hpp for ``namespace A::B::C {`` patterns
    - dotnet: scans .cs for ``namespace A.B.C`` patterns
    - java: scans .java for ``package A.B.C;`` patterns
    - typescript: reads package.json ``name`` field
    - python: detects ``aspose/X/__init__.py`` namespace package paths

    TC-5321 (INT-H2): First structural verification of canonical_import at Intake.
    """
    plat = (platform or "").lower().strip()

    if plat == "cpp":
        return _scan_cpp_namespaces(repo_dir, scan_limit=scan_limit)
    if plat in ("dotnet", "csharp"):
        return _scan_dotnet_namespaces(repo_dir, scan_limit=scan_limit)
    if plat == "java":
        return _scan_java_packages(repo_dir, scan_limit=scan_limit)
    if plat == "typescript":
        return _scan_typescript_package(repo_dir)
    if plat == "python":
        return _scan_python_module(repo_dir)
    return [], "none"


# Internal namespace markers — segments containing these are NOT public API.
_CPP_INTERNAL_SEGMENTS: frozenset[str] = frozenset({"internal", "detail", "impl", "private"})
_DOTNET_INTERNAL_SEGMENTS: frozenset[str] = frozenset({"internal", "impl", "detail", "private"})
_JAVA_INTERNAL_SEGMENTS: frozenset[str] = frozenset({"internal", "impl", "detail"})

# Maximum depth of namespace/package to retain — trims very deep chains.
_NS_MAX_DEPTH = 4

# Minimum frequency fraction to declare "high" confidence (70% of sampled files agree).
_HIGH_CONF_THRESHOLD = 0.70


def _score_candidates(counter: dict[str, int], total: int) -> tuple[list[str], str]:
    """Convert a frequency counter to (candidates, confidence).

    Root-namespace promotion: if any candidate is a strict prefix of the top
    candidate and has meaningful presence (>= 5% of total), promote it to first
    place. This handles .NET/Java libraries where sub-namespaces like
    ``Aspose.ThreeD.Entities`` are more frequent than the root ``Aspose.ThreeD``.
    """
    if not counter or total == 0:
        return [], "low"
    ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    top_ns, top_count = ranked[0]

    # Root-namespace promotion: prefer shortest prefix that appears meaningfully.
    min_presence = max(1, int(total * 0.05))
    for ns, count in ranked:
        if ns == top_ns:
            continue
        if count < min_presence:
            continue
        sep = "::" if "::" in top_ns else "."
        if top_ns.startswith(ns + sep) and len(ns) < len(top_ns):
            # ns is a shorter prefix of top_ns — promote it as root namespace.
            top_ns = ns
            top_count = count
            break

    combined = top_count + sum(
        c for n, c in ranked
        if n != top_ns and (
            n.startswith(top_ns + "::") or n.startswith(top_ns + ".")
        )
    )
    confidence = "high" if (combined / total) >= _HIGH_CONF_THRESHOLD else "medium"
    other = [ns for ns, _ in ranked if ns != top_ns][:2]
    return [top_ns] + other, confidence


def _scan_cpp_namespaces(repo_dir: Path, *, scan_limit: int) -> tuple[list[str], str]:
    """Scan C++ header files for namespace declarations."""
    import re as _re

    # Prefer public headers (not in _internal/); sort them first.
    all_headers = list(repo_dir.rglob("*.h")) + list(repo_dir.rglob("*.hpp"))
    public_first = sorted(
        all_headers,
        key=lambda p: (1 if "_internal" in str(p).lower() else 0, str(p)),
    )[:scan_limit]

    # Match: namespace Aspose::Slides::Foss {  (C++17 style)
    ns_re = _re.compile(r"^namespace\s+([\w:]+)\s*\{?\s*$", _re.MULTILINE)

    counter: dict[str, int] = {}
    total = 0
    for header in public_first:
        try:
            text = header.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in ns_re.finditer(text):
            raw_ns = match.group(1).strip(":").strip()
            segments = [s for s in raw_ns.split("::") if s]
            if any(seg.lower() in _CPP_INTERNAL_SEGMENTS for seg in segments):
                continue
            ns = "::".join(segments[:_NS_MAX_DEPTH])
            if ns:
                counter[ns] = counter.get(ns, 0) + 1
                total += 1

    return _score_candidates(counter, total)


def _scan_dotnet_namespaces(repo_dir: Path, *, scan_limit: int) -> tuple[list[str], str]:
    """Scan .cs files for namespace declarations."""
    import re as _re

    cs_files = sorted(repo_dir.rglob("*.cs"))
    public_first = sorted(
        cs_files,
        key=lambda p: (
            1 if any(
                seg.lower() in {"tests", "test", "internal", "impl"}
                for seg in p.parts
            ) else 0,
            str(p),
        ),
    )[:scan_limit]

    # Match: namespace Aspose.Slides.Foss;  OR  namespace Aspose.Slides.Foss {
    ns_re = _re.compile(r"^namespace\s+([\w\.]+)\s*[{;]?\s*$", _re.MULTILINE)

    counter: dict[str, int] = {}
    total = 0
    for cs_file in public_first:
        try:
            text = cs_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in ns_re.finditer(text):
            raw_ns = match.group(1).strip()
            segments = raw_ns.split(".")
            if any(seg.lower() in _DOTNET_INTERNAL_SEGMENTS for seg in segments):
                continue
            ns = ".".join(segments[:_NS_MAX_DEPTH])
            if ns:
                counter[ns] = counter.get(ns, 0) + 1
                total += 1

    return _score_candidates(counter, total)


def _scan_java_packages(repo_dir: Path, *, scan_limit: int) -> tuple[list[str], str]:
    """Scan .java files for package declarations."""
    import re as _re

    java_files = sorted(repo_dir.rglob("*.java"))
    public_first = sorted(
        java_files,
        key=lambda p: (
            1 if any(
                seg.lower() in {"test", "tests", "internal", "impl"}
                for seg in p.parts
            ) else 0,
            str(p),
        ),
    )[:scan_limit]

    pkg_re = _re.compile(r"^package\s+([\w\.]+)\s*;", _re.MULTILINE)

    counter: dict[str, int] = {}
    total = 0
    for jf in public_first:
        try:
            text = jf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in pkg_re.finditer(text):
            raw_pkg = match.group(1).strip()
            segments = raw_pkg.split(".")
            if any(seg.lower() in _JAVA_INTERNAL_SEGMENTS for seg in segments):
                continue
            pkg = ".".join(segments[:_NS_MAX_DEPTH])
            if pkg:
                counter[pkg] = counter.get(pkg, 0) + 1
                total += 1

    return _score_candidates(counter, total)


def _scan_typescript_package(repo_dir: Path) -> tuple[list[str], str]:
    """Read package.json to extract the npm package name."""
    import json as _json

    pkg_json = repo_dir / "package.json"
    if not pkg_json.is_file():
        return [], "low"
    try:
        data = _json.loads(pkg_json.read_text(encoding="utf-8"))
        name = data.get("name", "").strip()
        if name:
            return [name], "high"
    except (OSError, ValueError):
        pass
    return [], "low"


def _scan_python_module(repo_dir: Path) -> tuple[list[str], str]:
    """Detect the Python module import path from namespace package layout.

    Handles two layouts:
    - Flat: ``repo_root/aspose/X/__init__.py`` → ``aspose.X``
    - Src:  ``repo_root/src/aspose/X/__init__.py`` → ``aspose.X``
    """
    candidates: list[str] = []
    for base in [repo_dir, repo_dir / "src"]:
        aspose_dir = base / "aspose"
        if not aspose_dir.is_dir():
            continue
        for subdir in sorted(aspose_dir.iterdir()):
            if not subdir.is_dir():
                continue
            if (subdir / "__init__.py").exists():
                module_path = f"aspose.{subdir.name}"
                if module_path not in candidates:
                    candidates.append(module_path)
    if not candidates:
        return [], "low"
    confidence = "high" if len(candidates) == 1 else "medium"
    return candidates, confidence


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
    candidates, import_confidence = _extract_canonical_import_candidates(repo_dir, platform)
    if candidates and import_confidence == "high" and candidates[0] != canonical_import:
        logger.warning(
            "[Intake] canonical_import mismatch: config=%r repo_extracted=%r "
            "(platform=%r). Config value used; repo value in candidates list.",
            canonical_import,
            candidates[0],
            platform,
        )
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
        "canonical_import_candidates": candidates,
        "import_confidence": import_confidence,
        "failure_state": "" if repo_dir.is_dir() and not repo_signals["is_empty_clone"] else "unusable_clone",
    }


__all__ = [
    "_CLONE_SHA_MARKER",
    "_CLONE_TIMESTAMP_MARKER",
    "_CLONE_URL_MARKER",
    "_STALE_CACHE_DAYS",
    "_check_url_collision",
    "_extract_brand_from_org",
    "_extract_brand_from_url",
    "_extract_canonical_import_candidates",
    "_get_cache_dir",
    "_get_repo_sha",
    "_log_cache_age",
    "_normalize_slug",
    "_write_cache_timestamp",
    "build_acquisition_artifact",
    "build_repo_signals",
    "check_remote_sha",
    "clone_repo_cached",
    "compute_acquisition_confidence",
    "resolve_tier",
]
