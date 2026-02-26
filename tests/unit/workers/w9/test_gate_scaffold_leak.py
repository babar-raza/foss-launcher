"""TC-2850: Tests for gate_scaffold_leak.

Covers:
- LLM scaffold patterns detected (completion artifacts)
- LLM meta-commentary detected
- Pipeline diagnostic patterns detected
- Clean content passes
- Code fence context reduces severity for pipeline diagnostics
- Profile-based severity (local=warn, ci=error, prod=blocker)
- MAX_ISSUES_PER_FILE cap respected
- Empty/missing site dir → graceful pass
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_scaffold_leak import (
    execute_gate,
    _get_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_md(run_dir: Path, rel_path: str, content: str) -> Path:
    md_file = run_dir / "work" / "site" / rel_path
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text(content, encoding="utf-8")
    return md_file


# ---------------------------------------------------------------------------
# _get_severity
# ---------------------------------------------------------------------------

class TestGetSeverity:

    def test_pipeline_diagnostic_in_fence_is_warn(self):
        assert _get_severity("PIPELINE_DIAGNOSTIC", True, "ci") == "warn"

    def test_pipeline_diagnostic_in_fence_prod_still_warn(self):
        assert _get_severity("PIPELINE_DIAGNOSTIC", True, "prod") == "warn"

    def test_llm_scaffold_local_is_warn(self):
        assert _get_severity("LLM_SCAFFOLD", False, "local") == "warn"

    def test_llm_scaffold_ci_is_error(self):
        assert _get_severity("LLM_SCAFFOLD", False, "ci") == "error"

    def test_llm_scaffold_prod_is_blocker(self):
        assert _get_severity("LLM_SCAFFOLD", False, "prod") == "blocker"

    def test_llm_meta_ci_is_error(self):
        assert _get_severity("LLM_META", False, "ci") == "error"

    def test_pipeline_diagnostic_prose_ci_is_error(self):
        assert _get_severity("PIPELINE_DIAGNOSTIC", False, "ci") == "error"


# ---------------------------------------------------------------------------
# execute_gate – clean content
# ---------------------------------------------------------------------------

class TestCleanContent:

    def test_clean_content_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "This is normal content about Aspose.Note.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0

    def test_no_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0

    def test_empty_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        site_dir = run_dir / "work" / "site"
        site_dir.mkdir(parents=True)
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True


# ---------------------------------------------------------------------------
# execute_gate – LLM scaffold detection
# ---------------------------------------------------------------------------

class TestLLMScaffold:

    def test_you_now_have_complete_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "You now have a complete guide to using the library.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "SCAFFOLD_LLM_SCAFFOLD" for i in issues)

    def test_you_now_have_working_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "You now have a working solution.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False

    def test_heres_a_complete_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Here's a complete example of the code.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "SCAFFOLD_LLM_SCAFFOLD" for i in issues)

    def test_here_is_a_complete_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Here is a complete implementation.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False


# ---------------------------------------------------------------------------
# execute_gate – LLM meta-commentary
# ---------------------------------------------------------------------------

class TestLLMMeta:

    def test_as_an_ai_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "As an AI, I cannot verify this.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "SCAFFOLD_LLM_META" for i in issues)

    def test_ill_help_you_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "I'll help you understand this concept.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False

    def test_let_me_explain_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Let me explain how this works.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "SCAFFOLD_LLM_META" for i in issues)

    def test_let_me_show_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Let me show you how to do this.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False

    def test_let_me_demonstrate_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Let me demonstrate the process.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False


# ---------------------------------------------------------------------------
# execute_gate – pipeline diagnostics
# ---------------------------------------------------------------------------

class TestPipelineDiagnostics:

    def test_claim_id_in_prose_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "claim_id: abc123-def456")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "SCAFFOLD_PIPELINE_DIAGNOSTIC" for i in issues)

    def test_evidence_score_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "evidence_score: 8")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False

    def test_claim_html_comment_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "<!-- claim.C001 evidence -->")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False

    def test_pipeline_diagnostic_in_code_fence_is_warn(self, tmp_path):
        """Pipeline diagnostics inside code fences demoted to warn (not error)."""
        run_dir = tmp_path / "run"
        content = "Normal text.\n\n```python\n# claim_id: abc123-def456\n```\n\nMore text."
        _write_md(run_dir, "page.md", content)
        passed, issues = execute_gate(run_dir, "ci")
        # Should pass because warn doesn't block
        assert passed is True
        assert len(issues) == 1
        assert issues[0]["severity"] == "warn"


# ---------------------------------------------------------------------------
# execute_gate – profile-based severity
# ---------------------------------------------------------------------------

class TestProfileSeverity:

    def test_local_profile_warns_only(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "You now have a complete solution.")
        passed, issues = execute_gate(run_dir, "local")
        assert passed is True  # warn doesn't block
        assert len(issues) >= 1
        assert issues[0]["severity"] == "warn"

    def test_ci_profile_errors(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "You now have a complete solution.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert issues[0]["severity"] == "error"

    def test_prod_profile_blockers(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "You now have a complete solution.")
        passed, issues = execute_gate(run_dir, "prod")
        assert passed is False
        assert issues[0]["severity"] == "blocker"


# ---------------------------------------------------------------------------
# execute_gate – edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_max_issues_per_file_cap(self, tmp_path):
        """At most MAX_ISSUES_PER_FILE (10) issues per file."""
        run_dir = tmp_path / "run"
        lines = ["As an AI, line {}.".format(i) for i in range(20)]
        _write_md(run_dir, "page.md", "\n".join(lines))
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert len(issues) == 10  # capped at MAX_ISSUES_PER_FILE

    def test_multiple_files_all_scanned(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page1.md", "You now have a complete guide.")
        _write_md(run_dir, "page2.md", "As an AI, I recommend this.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert len(issues) >= 2

    def test_fence_toggle_tracked_correctly(self, tmp_path):
        """Code fence state toggles correctly across multiple fences."""
        run_dir = tmp_path / "run"
        content = (
            "Normal text.\n"
            "```python\n"
            "# claim_id: abc123-def456\n"  # inside fence → warn
            "```\n"
            "claim_id: aabb00-ccddee\n"  # outside fence → error
        )
        _write_md(run_dir, "page.md", content)
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        severities = [i["severity"] for i in issues]
        assert "warn" in severities
        assert "error" in severities

    def test_issue_has_required_fields(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "You now have a full working app.")
        passed, issues = execute_gate(run_dir, "ci")
        assert len(issues) >= 1
        issue = issues[0]
        assert "issue_id" in issue
        assert "gate" in issue
        assert issue["gate"] == "gate_scaffold_leak"
        assert "severity" in issue
        assert "message" in issue
        assert "error_code" in issue
        assert "location" in issue
        assert "line" in issue["location"]
        assert "status" in issue

    def test_first_pattern_match_only_per_line(self, tmp_path):
        """Only the first matching pattern per line is reported."""
        run_dir = tmp_path / "run"
        # This line matches both LLM_META ("As an AI") and could match others
        _write_md(run_dir, "page.md", "As an AI, I'll help you understand.")
        passed, issues = execute_gate(run_dir, "ci")
        # Should only report one issue for this single line
        assert len(issues) == 1

    def test_case_insensitive_matching(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "you NOW have a COMPLETE solution.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert len(issues) >= 1
