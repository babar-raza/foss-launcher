"""
Unit tests for scripts/check_doc_freshness.py (AG-019 doc-drift detector).

The script lives in scripts/, which is not in the project's pythonpath
(pyproject.toml has pythonpath = ["src"]). We load it via importlib and
register it in sys.modules so @patch decorators work correctly.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ── Module loading ────────────────────────────────────────────────────────────

_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location(
    "check_doc_freshness",
    _SCRIPTS_DIR / "check_doc_freshness.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
# Register so @patch("check_doc_freshness.subprocess.run") resolves correctly
sys.modules["check_doc_freshness"] = _mod

# Expose module symbols for direct use in tests
CODE_TO_SPEC = _mod.CODE_TO_SPEC
matches_pattern = _mod.matches_pattern
find_governing_spec = _mod.find_governing_spec
get_changed_files = _mod.get_changed_files
_has_uncommitted_changes = _mod._has_uncommitted_changes


# ── Group 1: matches_pattern ──────────────────────────────────────────────────

class TestMatchesPattern:
    """Verify both matching strategies: fnmatch and directory-prefix."""

    def test_exact_file_match(self):
        assert matches_pattern("configs/pipeline.yaml", "configs/pipeline.yaml")

    def test_exact_file_no_match(self):
        assert not matches_pattern("configs/families.yaml", "configs/pipeline.yaml")

    def test_double_star_deep_path(self):
        # Three directory levels deep inside the ** subtree
        assert matches_pattern(
            "src/launcher/workers/evaluate/checks/slug_safety.py",
            "src/launcher/workers/evaluate/**",
        )

    def test_double_star_direct_child(self):
        # One level deep inside the ** subtree
        assert matches_pattern(
            "src/launcher/workers/evaluate/worker.py",
            "src/launcher/workers/evaluate/**",
        )

    def test_double_star_sibling_no_match(self):
        assert not matches_pattern(
            "src/launcher/workers/generate/worker.py",
            "src/launcher/workers/evaluate/**",
        )

    def test_double_star_parent_no_match(self):
        # The directory itself (no trailing slash, no child) must not match
        assert not matches_pattern(
            "src/launcher/workers",
            "src/launcher/workers/evaluate/**",
        )

    def test_windows_path_separators_normalized(self):
        # Backslashes (Windows git output) must be treated as forward slashes
        assert matches_pattern(
            r"src\launcher\workers\evaluate\worker.py",
            "src/launcher/workers/evaluate/**",
        )


# ── Group 2: find_governing_spec ─────────────────────────────────────────────

class TestFindGoverningSpec:
    """Verify CODE_TO_SPEC mapping covers expected paths and returns None for exclusions."""

    def test_evaluate_worker(self):
        assert (
            find_governing_spec("src/launcher/workers/evaluate/worker.py")
            == "specs/worker_evaluate.md"
        )

    def test_evaluate_deep_check_file(self):
        assert (
            find_governing_spec("src/launcher/workers/evaluate/checks/seo.py")
            == "specs/worker_evaluate.md"
        )

    def test_generate_worker(self):
        assert (
            find_governing_spec("src/launcher/workers/generate/worker.py")
            == "specs/worker_generate.md"
        )

    def test_understand_worker(self):
        assert (
            find_governing_spec("src/launcher/workers/understand/scout.py")
            == "specs/worker_understand.md"
        )

    def test_llm_client(self):
        assert (
            find_governing_spec("src/launcher/clients/llm_provider.py")
            == "specs/llm_provider.md"
        )

    def test_state_event_log(self):
        assert (
            find_governing_spec("src/launcher/state/event_log.py")
            == "specs/state_events_checkpoints.md"
        )

    def test_resilience_module(self):
        assert (
            find_governing_spec("src/launcher/resilience/retry_policy.py")
            == "specs/state_events_checkpoints.md"
        )

    def test_specific_override_wins_before_wildcard(self):
        # ts_analyzer.py has a specific override to worker_understand.md,
        # NOT the generic shared/** → system_overview.md fallback.
        assert (
            find_governing_spec("src/launcher/shared/ts_analyzer.py")
            == "specs/worker_understand.md"
        )

    def test_slug_engine_specific_override(self):
        assert (
            find_governing_spec("src/launcher/shared/slug_engine.py")
            == "specs/worker_understand.md"
        )

    def test_generic_shared_file(self):
        # A shared file that is NOT a specific override falls through to
        # the shared/** catch-all mapping.
        assert (
            find_governing_spec("src/launcher/shared/platform_utils.py")
            == "specs/system_overview.md"
        )

    def test_config_pipeline(self):
        assert (
            find_governing_spec("configs/pipeline.yaml") == "specs/system_overview.md"
        )

    def test_config_families(self):
        assert (
            find_governing_spec("configs/families.yaml") == "specs/product_model.md"
        )

    def test_util_intentionally_excluded(self):
        # src/launcher/util/** is excluded — no single governing spec
        assert find_governing_spec("src/launcher/util/logging.py") is None

    def test_unknown_path_returns_none(self):
        assert find_governing_spec("some/unknown/path.py") is None

    def test_test_file_returns_none(self):
        assert find_governing_spec("tests/unit/workers/test_evaluate.py") is None


# ── Group 3: get_changed_files with mocked subprocess ─────────────────────────

class TestGetChangedFiles:
    """Verify git-diff parsing and error handling without real git calls."""

    @patch("check_doc_freshness.subprocess.run")
    def test_success_parses_lines(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="src/launcher/workers/evaluate/worker.py\nconfigs/pipeline.yaml\n",
            stderr="",
        )
        result = get_changed_files("HEAD~1")
        assert "src/launcher/workers/evaluate/worker.py" in result
        assert "configs/pipeline.yaml" in result
        assert len(result) == 2

    @patch("check_doc_freshness.subprocess.run")
    def test_empty_stdout_returns_empty_list(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = get_changed_files("HEAD~1")
        assert result == []

    @patch("check_doc_freshness.subprocess.run")
    def test_git_failure_both_forms_exits_2(self, mock_run):
        # Both the "since HEAD" and fallback form fail
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="fatal: bad object INVALID"
        )
        with pytest.raises(SystemExit) as exc:
            get_changed_files("INVALID_REF")
        assert exc.value.code == 2

    @patch("check_doc_freshness.subprocess.run")
    def test_backslash_paths_normalized_to_forward(self, mock_run):
        # Windows git may return backslash-separated paths
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=r"src\launcher\workers\evaluate\worker.py" + "\n",
            stderr="",
        )
        result = get_changed_files("HEAD~1")
        assert result[0] == "src/launcher/workers/evaluate/worker.py"

    @patch("check_doc_freshness.subprocess.run")
    def test_first_form_failure_triggers_fallback(self, mock_run):
        # First call (with HEAD) fails; fallback (without HEAD) succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="fatal: bad revision 'HEAD'"),
            MagicMock(returncode=0, stdout="src/launcher/models/base.py\n", stderr=""),
        ]
        result = get_changed_files("HEAD~1")
        assert result == ["src/launcher/models/base.py"]
        assert mock_run.call_count == 2


# ── Group 4: _has_uncommitted_changes ────────────────────────────────────────

class TestHasUncommittedChanges:

    @patch("check_doc_freshness.subprocess.run")
    def test_returns_true_when_porcelain_has_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=" M src/launcher/foo.py\n"
        )
        assert _has_uncommitted_changes() is True

    @patch("check_doc_freshness.subprocess.run")
    def test_returns_false_when_porcelain_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        assert _has_uncommitted_changes() is False

    @patch("check_doc_freshness.subprocess.run")
    def test_returns_false_on_git_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert _has_uncommitted_changes() is False


# ── Group 5: Drift detection logic ───────────────────────────────────────────

class TestDriftDetection:
    """
    Tests for the core drift-detection loop.

    We replicate the loop from _run() here to avoid os.chdir side-effects
    and real filesystem/git calls. The loop is simple enough that testing
    it directly is more valuable than mocking the entire _run() stack.
    """

    def _detect(
        self,
        changed: list[str],
        existing_specs: set[str],
    ) -> list[tuple[str, str]]:
        """Replicate the drift-detection loop from _run()."""
        changed_set = set(changed)
        drift_pairs: list[tuple[str, str]] = []
        checked_specs: set[str] = set()
        for filepath in changed:
            spec = find_governing_spec(filepath)
            if spec is None:
                continue
            if spec in checked_specs:
                continue
            checked_specs.add(spec)
            if spec not in changed_set and spec in existing_specs:
                drift_pairs.append((filepath, spec))
        return drift_pairs

    def test_no_drift_when_spec_also_changed(self):
        changed = [
            "src/launcher/workers/evaluate/worker.py",
            "specs/worker_evaluate.md",
        ]
        assert self._detect(changed, {"specs/worker_evaluate.md"}) == []

    def test_drift_detected_when_spec_not_touched(self):
        changed = ["src/launcher/workers/evaluate/worker.py"]
        drift = self._detect(changed, {"specs/worker_evaluate.md"})
        assert len(drift) == 1
        assert drift[0] == (
            "src/launcher/workers/evaluate/worker.py",
            "specs/worker_evaluate.md",
        )

    def test_no_mapping_never_triggers_drift(self):
        # util/** is intentionally excluded
        changed = ["src/launcher/util/logging.py"]
        assert self._detect(changed, set()) == []

    def test_spec_not_on_disk_no_drift(self):
        # If the spec file doesn't exist (not in existing_specs), no drift reported
        changed = ["src/launcher/workers/evaluate/worker.py"]
        assert self._detect(changed, existing_specs=set()) == []

    def test_multiple_files_same_spec_reported_once(self):
        # Two evaluate files map to the same spec — report only once
        changed = [
            "src/launcher/workers/evaluate/worker.py",
            "src/launcher/workers/evaluate/checks/seo.py",
        ]
        drift = self._detect(changed, {"specs/worker_evaluate.md"})
        assert len(drift) == 1

    def test_multiple_distinct_specs_all_reported(self):
        changed = [
            "src/launcher/workers/evaluate/worker.py",
            "src/launcher/workers/generate/worker.py",
        ]
        drift = self._detect(
            changed,
            {"specs/worker_evaluate.md", "specs/worker_generate.md"},
        )
        spec_files = {pair[1] for pair in drift}
        assert "specs/worker_evaluate.md" in spec_files
        assert "specs/worker_generate.md" in spec_files

    def test_mixed_mapped_and_unmapped_files(self):
        # util file (unmapped) mixed with evaluate file (mapped, spec not touched)
        changed = [
            "src/launcher/util/logging.py",
            "src/launcher/workers/evaluate/worker.py",
        ]
        drift = self._detect(changed, {"specs/worker_evaluate.md"})
        assert len(drift) == 1
        assert drift[0][0] == "src/launcher/workers/evaluate/worker.py"
