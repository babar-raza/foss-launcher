"""TC-2528: Tests for G20-005/006/007 cross-page consistency checks and
W10 contradiction resolver.

Covers:
- G20-005: Package name consistency across pages
- G20-006: Install command consistency across pages
- G20-007: Format claim consistency against shared_facts canonical list
- W10 _resolve_contradictions(): version and package name correction
- W10 fix_contradiction(): graceful skip when shared_facts absent
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_20_cross_page_consistency import (
    run_gate_20,
    _find_package_name_inconsistency,
    _find_install_command_inconsistency,
    _find_format_claim_inconsistency,
)
from src.launch.workers.w10_fixer.worker import (
    _resolve_contradictions,
    fix_contradiction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_page(tmp_path: Path, name: str, content: str) -> Path:
    """Write a markdown file under tmp_path and return its Path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _page_dict(path: str, content: str, body: str = "") -> dict:
    """Create a page dict matching the internal gate_20 structure."""
    return {"path": path, "content": content, "body": body or content}


def _write_shared_facts(run_dir: Path, facts: dict) -> None:
    """Write shared_facts.json into run_dir/artifacts/."""
    arts = run_dir / "artifacts"
    arts.mkdir(parents=True, exist_ok=True)
    (arts / "shared_facts.json").write_text(
        json.dumps(facts), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# G20-005: Package name consistency
# ---------------------------------------------------------------------------


class TestG20005PackageName:
    """G20-005: All pages must reference the same pip package name."""

    def test_same_package_name_passes(self):
        """No issue when all pages use the same package name."""
        pages = [
            _page_dict("/a.md", "Install with `pip install aspose-3d`"),
            _page_dict("/b.md", "Run `pip install aspose-3d` first"),
        ]
        issues = _find_package_name_inconsistency(pages)
        assert len(issues) == 0

    def test_different_package_names_fails(self):
        """Error when pages use different package names."""
        pages = [
            _page_dict("/a.md", "Install with `pip install aspose-3d`"),
            _page_dict("/b.md", "Run `pip install aspose.3d` first"),
        ]
        issues = _find_package_name_inconsistency(pages)
        assert len(issues) == 1
        assert issues[0]["error_code"] == "G20-005"
        assert issues[0]["severity"] == "error"
        assert "aspose-3d" in issues[0]["message"]
        assert "aspose.3d" in issues[0]["message"]

    def test_same_package_with_version_spec_passes(self):
        """Package name extraction strips version specifiers for comparison."""
        pages = [
            _page_dict("/a.md", "pip install aspose-3d>=24.1"),
            _page_dict("/b.md", "pip install aspose-3d"),
        ]
        issues = _find_package_name_inconsistency(pages)
        assert len(issues) == 0

    def test_no_pip_install_passes(self):
        """No issue when no pip install commands are present."""
        pages = [
            _page_dict("/a.md", "This page has no install commands."),
            _page_dict("/b.md", "Neither does this one."),
        ]
        issues = _find_package_name_inconsistency(pages)
        assert len(issues) == 0

    def test_single_page_always_passes(self):
        """Single page cannot have inconsistency."""
        pages = [
            _page_dict("/a.md", "pip install aspose-3d"),
        ]
        issues = _find_package_name_inconsistency(pages)
        assert len(issues) == 0

    def test_g20_005_fails_full_gate(self, tmp_path):
        """G20-005 error causes the full gate to fail."""
        p1 = _make_page(tmp_path, "a.md", "pip install aspose-3d\n\nSome content here to pad.")
        p2 = _make_page(tmp_path, "b.md", "pip install aspose.3d\n\nMore content here for padding.")
        passed, issues = run_gate_20([p1, p2])
        assert passed is False
        error_codes = [i["error_code"] for i in issues if i["severity"] == "error"]
        assert "G20-005" in error_codes


# ---------------------------------------------------------------------------
# G20-006: Install command consistency
# ---------------------------------------------------------------------------


class TestG20006InstallCommand:
    """G20-006: All pip install commands should have the same form."""

    def test_same_install_command_passes(self):
        """No issue when all pages use identical install commands."""
        pages = [
            _page_dict("/a.md", "Run `pip install aspose-3d`"),
            _page_dict("/b.md", "Use `pip install aspose-3d`"),
        ]
        issues = _find_install_command_inconsistency(pages)
        assert len(issues) == 0

    def test_different_install_extras_warns(self):
        """Warning when install commands have different extras/versions."""
        pages = [
            _page_dict("/a.md", "Run `pip install aspose-3d`"),
            _page_dict("/b.md", "Use `pip install aspose-3d>=24.1`"),
        ]
        issues = _find_install_command_inconsistency(pages)
        assert len(issues) == 1
        assert issues[0]["error_code"] == "G20-006"
        assert issues[0]["severity"] == "warn"

    def test_no_install_commands_passes(self):
        """No issue when no pip install commands are present."""
        pages = [
            _page_dict("/a.md", "No commands here."),
            _page_dict("/b.md", "Nor here."),
        ]
        issues = _find_install_command_inconsistency(pages)
        assert len(issues) == 0

    def test_g20_006_warn_does_not_fail_gate(self, tmp_path):
        """G20-006 warnings do not cause the gate to fail."""
        p1 = _make_page(tmp_path, "a.md", "pip install aspose-3d\n\nContent padding for test.")
        p2 = _make_page(tmp_path, "b.md", "pip install aspose-3d>=24.1\n\nMore content padding.")
        passed, issues = run_gate_20([p1, p2])
        assert passed is True
        warn_codes = [i["error_code"] for i in issues if i["severity"] == "warn"]
        assert "G20-006" in warn_codes


# ---------------------------------------------------------------------------
# G20-007: Format claim consistency
# ---------------------------------------------------------------------------


class TestG20007FormatClaim:
    """G20-007: Format mentions should be in the canonical format list."""

    def test_format_in_canonical_list_passes(self):
        """No issue when mentioned formats are all in canonical list."""
        pages = [
            _page_dict(
                "/a.md",
                "This library supports FBX file format conversion.",
                body="This library supports FBX file format conversion.",
            ),
        ]
        shared_facts = {
            "supported_formats": [
                {"format": "FBX", "direction": "both"},
                {"format": "OBJ", "direction": "both"},
            ]
        }
        issues = _find_format_claim_inconsistency(pages, shared_facts)
        assert len(issues) == 0

    def test_format_not_in_canonical_warns(self):
        """Warning when a format mention is not in the canonical list."""
        pages = [
            _page_dict(
                "/a.md",
                "Export to GLTF file format is supported.",
                body="Export to GLTF file format is supported.",
            ),
        ]
        shared_facts = {
            "supported_formats": [
                {"format": "FBX", "direction": "both"},
                {"format": "OBJ", "direction": "both"},
            ]
        }
        issues = _find_format_claim_inconsistency(pages, shared_facts)
        assert len(issues) == 1
        assert issues[0]["error_code"] == "G20-007"
        assert issues[0]["severity"] == "warn"
        assert "GLTF" in issues[0]["message"]

    def test_no_shared_facts_skips(self):
        """No issues when shared_facts is None."""
        pages = [
            _page_dict("/a.md", "Convert to GLTF format.", body="Convert to GLTF format."),
        ]
        issues = _find_format_claim_inconsistency(pages, None)
        assert len(issues) == 0

    def test_empty_supported_formats_skips(self):
        """No issues when canonical format list is empty."""
        pages = [
            _page_dict("/a.md", "Convert to FBX format.", body="Convert to FBX format."),
        ]
        issues = _find_format_claim_inconsistency(pages, {"supported_formats": []})
        assert len(issues) == 0

    def test_string_format_list(self):
        """Handles both string and dict format entries in shared_facts."""
        pages = [
            _page_dict(
                "/a.md",
                "Export to GLTF file format from FBX.",
                body="Export to GLTF file format from FBX.",
            ),
        ]
        shared_facts = {"supported_formats": ["FBX", "OBJ"]}
        issues = _find_format_claim_inconsistency(pages, shared_facts)
        assert len(issues) == 1
        assert "GLTF" in issues[0]["message"]

    def test_exclusion_list_filters_non_formats(self):
        """Common acronyms like API, SDK are not flagged as unknown formats."""
        pages = [
            _page_dict(
                "/a.md",
                "Use the API to convert FBX file format.",
                body="Use the API to convert FBX file format.",
            ),
        ]
        shared_facts = {"supported_formats": [{"format": "FBX"}]}
        issues = _find_format_claim_inconsistency(pages, shared_facts)
        assert len(issues) == 0

    def test_g20_007_with_full_gate(self, tmp_path):
        """G20-007 fires through the full gate flow when shared_facts present."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        _write_shared_facts(run_dir, {
            "supported_formats": [{"format": "FBX"}],
        })
        p1 = _make_page(
            tmp_path, "a.md",
            "Convert to GLTF file format from FBX.\n\nMore content."
        )
        p2 = _make_page(
            tmp_path, "b.md",
            "Export to FBX file format.\n\nAdditional content."
        )
        passed, issues = run_gate_20([p1, p2], run_dir=run_dir)
        # G20-007 is only a warn, so gate still passes
        assert passed is True
        warn_codes = [i.get("error_code") for i in issues if i.get("severity") == "warn"]
        assert "G20-007" in warn_codes


# ---------------------------------------------------------------------------
# W10: _resolve_contradictions
# ---------------------------------------------------------------------------


class TestW10ResolveContradictions:
    """Test the _resolve_contradictions() helper in W10 fixer."""

    def test_resolves_version_contradiction(self):
        """Replaces non-canonical Python version with canonical."""
        content = "Requires Python 3.6 or higher."
        shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.10"}},
        }
        fixed, corrections = _resolve_contradictions(content, shared_facts)
        assert "Python 3.10" in fixed
        assert "3.6" not in fixed
        assert len(corrections) == 1
        assert "version" in corrections[0]

    def test_resolves_package_name(self):
        """Replaces incorrect package name with canonical."""
        content = "Install via `pip install aspose.3d`"
        shared_facts = {
            "package_name": "aspose-3d",
        }
        fixed, corrections = _resolve_contradictions(content, shared_facts)
        assert "pip install aspose-3d" in fixed
        assert "aspose.3d" not in fixed
        assert len(corrections) == 1
        assert "package" in corrections[0]

    def test_no_change_when_already_canonical(self):
        """No corrections when content already uses canonical values."""
        content = "Requires Python 3.10. Install via `pip install aspose-3d`."
        shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.10"}},
            "package_name": "aspose-3d",
        }
        fixed, corrections = _resolve_contradictions(content, shared_facts)
        assert fixed == content
        assert len(corrections) == 0

    def test_preserves_version_specifier_on_package(self):
        """Version specifier on pip install is preserved after name fix."""
        content = "pip install aspose.3d>=24.1"
        shared_facts = {"package_name": "aspose-3d"}
        fixed, corrections = _resolve_contradictions(content, shared_facts)
        assert "pip install aspose-3d>=24.1" in fixed
        assert len(corrections) == 1

    def test_empty_shared_facts_no_crash(self):
        """Empty shared_facts dict produces no corrections."""
        content = "Some content with Python 3.6."
        fixed, corrections = _resolve_contradictions(content, {})
        assert fixed == content
        assert len(corrections) == 0

    def test_multiple_version_fixes(self):
        """Multiple version mentions all get fixed."""
        content = "Python 3.6 in setup. Also Python >= 3.7 required."
        shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.10"}},
        }
        fixed, corrections = _resolve_contradictions(content, shared_facts)
        assert "3.6" not in fixed
        assert "3.7" not in fixed
        assert fixed.count("3.10") == 2
        assert len(corrections) == 2


# ---------------------------------------------------------------------------
# W10: fix_contradiction (integration)
# ---------------------------------------------------------------------------


class TestW10FixContradiction:
    """Test the fix_contradiction() function end-to-end."""

    def test_skips_when_no_shared_facts(self, tmp_path):
        """Gracefully skips when shared_facts.json is absent."""
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        page = tmp_path / "page.md"
        page.write_text("Python 3.6 content", encoding="utf-8")

        issue = {
            "issue_id": "test_issue",
            "error_code": "G20-004",
            "location": {"path": str(page), "line": 1},
        }
        result = fix_contradiction(issue, run_dir, None)
        assert result["fixed"] is False
        assert "shared_facts" in result["error"]

    def test_fixes_version_with_shared_facts(self, tmp_path):
        """Applies version fix when shared_facts.json is available."""
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, {
            "runtime_versions": {"python": {"minimum": "3.10"}},
        })
        page = tmp_path / "page.md"
        page.write_text("Requires Python 3.6 or higher.", encoding="utf-8")

        issue = {
            "issue_id": "test_version",
            "error_code": "G20-004",
            "location": {"path": str(page), "line": 1},
        }
        result = fix_contradiction(issue, run_dir, None)
        assert result["fixed"] is True
        assert str(page) in result["files_changed"]
        fixed_content = page.read_text(encoding="utf-8")
        assert "Python 3.10" in fixed_content

    def test_fixes_package_name_with_shared_facts(self, tmp_path):
        """G20-005: scans all .md files under work/site/ and normalises package names."""
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, {
            "package_name": "aspose-3d",
        })
        # Page must live under run_dir/work/site/ — the G20-005 fixer scans that tree
        site_dir = run_dir / "work" / "site"
        site_dir.mkdir(parents=True)
        page = site_dir / "page.md"
        page.write_text("Install via pip install aspose.3d", encoding="utf-8")

        issue = {
            "issue_id": "test_pkg",
            "error_code": "G20-005",
            "location": {"path": str(page), "line": 1},
        }
        result = fix_contradiction(issue, run_dir, None)
        assert result["fixed"] is True
        fixed_content = page.read_text(encoding="utf-8")
        assert "aspose-3d" in fixed_content

    def test_no_file_path_returns_not_fixed(self, tmp_path):
        """G20-005: returns not-fixed when work/site/ has no .md files."""
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, {"package_name": "aspose-3d"})
        # No .md files in work/site/ — should report not-fixed
        issue = {
            "issue_id": "test_no_path",
            "error_code": "G20-005",
            "location": {},
        }
        result = fix_contradiction(issue, run_dir, None)
        assert result["fixed"] is False
