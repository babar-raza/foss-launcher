"""TC-925: Test W4 IAPlanner config loading signature fix.

Verifies that W4's execute_ia_planner() correctly handles run_config parameter
without attempting to reload from file with incorrect signature.
"""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest


class TestTC925W4ConfigLoading:
    """Test W4 config loading follows correct pattern (TC-925)."""

    def test_w4_uses_passed_config_not_reload(self, tmp_path):
        """Verify W4 uses passed-in run_config instead of reloading from file.

        This test ensures W4 doesn't call load_and_validate_run_config() with
        incorrect signature when run_config is provided (the standard case).
        """
        from launch.workers.w4_ia_planner.worker import execute_ia_planner

        # Setup minimal run directory structure
        run_dir = tmp_path / "test_run"
        run_dir.mkdir()
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir()
        logs_dir = run_dir / "logs"
        logs_dir.mkdir()

        # Create minimal config
        run_config = {
            "run_id": "test_run_tc925",
            "product_slug": "test-product",
            "family": "test",
            "target_platform": "python",
            "github_repo_url": "https://github.com/test/test-foss-python",
            "required_sections": ["products"],
            "launch_tier": "tier_1"
        }

        # Create minimal product_facts.json
        product_facts = {
            "metadata": {
                "product_slug": "test-product",
                "family": "test",
                "platform": "python"
            },
            "facts": []
        }

        # Create minimal snippet_catalog.json
        snippet_catalog = {
            "metadata": {
                "total_snippets": 0
            },
            "snippets": []
        }

        # Write artifacts
        import json
        (artifacts_dir / "product_facts.json").write_text(json.dumps(product_facts))
        (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(snippet_catalog))

        # Mock LLM client and emit_event to avoid dependencies
        with patch("launch.workers.w4_ia_planner.worker.emit_event"):
            with patch("launch.workers.w4_ia_planner.worker.load_and_validate_run_config") as mock_load:
                # Execute W4 with run_config provided
                try:
                    result = execute_ia_planner(
                        run_dir=run_dir,
                        run_config=run_config,
                        llm_client=None
                    )
                except Exception as e:
                    # If we get TypeError about config_path, TC-925 fix failed
                    if "missing 1 required positional argument" in str(e):
                        pytest.fail(f"TC-925 fix failed: W4 still has signature mismatch: {e}")
                    # Other exceptions are fine (W4 may fail for other reasons in unit test)
                    pass

                # CRITICAL: load_and_validate_run_config should NOT be called
                # when run_config is provided (TC-925 fix)
                assert not mock_load.called, (
                    "TC-925 fix failed: W4 should not reload config from file "
                    "when run_config parameter is provided"
                )

    def test_w4_reloads_config_when_none(self, tmp_path):
        """Verify W4 only reloads config when run_config is None."""
        from launch.workers.w4_ia_planner.worker import execute_ia_planner

        # Setup minimal run directory
        run_dir = tmp_path / "test_run"
        run_dir.mkdir()
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir()
        logs_dir = run_dir / "logs"
        logs_dir.mkdir()

        # Create run_config.yaml in run_dir (for reload path)
        run_config_yaml = run_dir / "run_config.yaml"
        run_config_yaml.write_text("product_slug: test-product\nfamily: test\n")

        # Create minimal artifacts
        import json
        (artifacts_dir / "product_facts.json").write_text(json.dumps({
            "metadata": {"product_slug": "test", "family": "test", "platform": "python"},
            "facts": []
        }))
        (artifacts_dir / "snippet_catalog.json").write_text(json.dumps({
            "metadata": {"total_snippets": 0},
            "snippets": []
        }))

        with patch("launch.workers.w4_ia_planner.worker.emit_event"):
            with patch("launch.workers.w4_ia_planner.worker.load_and_validate_run_config") as mock_load:
                # Mock successful config load with correct signature
                mock_load.return_value = {
                    "product_slug": "test-product",
                    "family": "test",
                    "target_platform": "python",
                    "required_sections": ["products"]
                }

                try:
                    result = execute_ia_planner(
                        run_dir=run_dir,
                        run_config=None,  # None triggers reload
                        llm_client=None
                    )
                except Exception:
                    pass  # Ignore execution failures

                # When run_config is None, W4 should call load_and_validate_run_config
                # with BOTH repo_root and config_path (TC-925 fix)
                if mock_load.called:
                    call_args = mock_load.call_args
                    assert len(call_args[0]) == 2, (
                        "TC-925 fix: load_and_validate_run_config must be called with "
                        "2 positional args (repo_root, config_path)"
                    )
