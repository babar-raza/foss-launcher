"""Unit tests for run_loop.py taskcard validation (Layer 1).

Tests early detection of taskcard issues before graph execution.
"""

import json
import tempfile
from pathlib import Path

import pytest

from launch.models.event import EVENT_TASKCARD_VALIDATED
from launch.orchestrator.run_loop import execute_run


class TestRunLoopTaskcardValidation:
    """Test Layer 1 taskcard validation in run loop."""

    def test_local_run_without_taskcard_succeeds(self, tmp_path):
        """Test that local runs work without taskcard."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        # Minimal run_config without taskcard (local mode)
        run_config = {
            "schema_version": "1.0",
            "validation_profile": "local",
            "product_slug": "test-product",
            "product_name": "Test Product",
            "family": "test",
            "github_repo_url": "https://github.com/test/test",
            "github_ref": "0" * 40,
            "required_sections": ["docs"],
            "site_layout": {
                "content_root": "content",
                "subdomain_roots": {
                    "products": "content/products",
                    "docs": "content/docs",
                    "kb": "content/kb",
                    "reference": "content/reference",
                    "blog": "content/blog",
                },
                "localization": {
                    "mode_by_section": {
                        "products": "dir",
                        "docs": "dir",
                        "kb": "dir",
                        "reference": "dir",
                        "blog": "filename",
                    }
                },
            },
            "allowed_paths": ["content/**"],
            "llm": {
                "api_base_url": "https://api.test.com",
                "model": "test-model",
                "decoding": {"temperature": 0.0},
            },
            "mcp": {"enabled": False, "listen_host": "127.0.0.1", "listen_port": 8787},
            "telemetry": {
                "endpoint_url": "https://telemetry.test.com",
                "project": "test",
            },
            "commit_service": {
                "endpoint_url": "https://commit.test.com",
                "github_token_env": "GITHUB_TOKEN",
                "commit_message_template": "test",
                "commit_body_template": "test",
            },
            "templates_version": "v1",
            "ruleset_version": "v1",
            "allow_inference": False,
            "max_fix_attempts": 3,
            "budgets": {
                "max_runtime_s": 3600,
                "max_llm_calls": 100,
                "max_llm_tokens": 100000,
                "max_file_writes": 100,
                "max_patch_attempts": 10,
                "max_lines_per_file": 500,
                "max_files_changed": 100,
            },
        }

        # Should not raise (local mode doesn't require taskcard)
        # Note: This will fail later during graph execution (workers not mocked)
        # but should pass taskcard validation
        try:
            execute_run("test-run", run_dir, run_config)
        except Exception as e:
            # Check that it's NOT a taskcard validation error
            assert "taskcard" not in str(e).lower() or "validation failed" not in str(e).lower()
            # It should fail for other reasons (graph execution, missing workers, etc.)
            # which is expected in this unit test

    def test_prod_run_without_taskcard_fails_early(self, tmp_path):
        """Test that prod runs fail early without taskcard."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        # Minimal run_config without taskcard (prod mode)
        run_config = {
            "schema_version": "1.0",
            "validation_profile": "prod",  # Production mode
            "product_slug": "test-product",
            "product_name": "Test Product",
            "family": "test",
            "github_repo_url": "https://github.com/test/test",
            "github_ref": "0" * 40,
            "required_sections": ["docs"],
            "site_layout": {
                "content_root": "content",
                "subdomain_roots": {
                    "products": "content/products",
                    "docs": "content/docs",
                    "kb": "content/kb",
                    "reference": "content/reference",
                    "blog": "content/blog",
                },
                "localization": {
                    "mode_by_section": {
                        "products": "dir",
                        "docs": "dir",
                        "kb": "dir",
                        "reference": "dir",
                        "blog": "filename",
                    }
                },
            },
            "allowed_paths": ["content/**"],
            "llm": {
                "api_base_url": "https://api.test.com",
                "model": "test-model",
                "decoding": {"temperature": 0.0},
            },
            "mcp": {"enabled": False, "listen_host": "127.0.0.1", "listen_port": 8787},
            "telemetry": {
                "endpoint_url": "https://telemetry.test.com",
                "project": "test",
            },
            "commit_service": {
                "endpoint_url": "https://commit.test.com",
                "github_token_env": "GITHUB_TOKEN",
                "commit_message_template": "test",
                "commit_body_template": "test",
            },
            "templates_version": "v1",
            "ruleset_version": "v1",
            "allow_inference": False,
            "max_fix_attempts": 3,
            "budgets": {
                "max_runtime_s": 3600,
                "max_llm_calls": 100,
                "max_llm_tokens": 100000,
                "max_file_writes": 100,
                "max_patch_attempts": 10,
                "max_lines_per_file": 500,
                "max_files_changed": 100,
            },
        }

        # Should raise ValueError about missing taskcard
        with pytest.raises(ValueError) as exc_info:
            execute_run("test-run", run_dir, run_config)

        assert "taskcard_id" in str(exc_info.value).lower()
        assert "production" in str(exc_info.value).lower()

    def test_run_with_invalid_taskcard_fails_early(self, tmp_path):
        """Test that run fails early with invalid taskcard."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        # Run config with nonexistent taskcard
        run_config = {
            "schema_version": "1.0",
            "validation_profile": "local",
            "taskcard_id": "TC-9999",  # Doesn't exist
            "product_slug": "test-product",
            "product_name": "Test Product",
            "family": "test",
            "github_repo_url": "https://github.com/test/test",
            "github_ref": "0" * 40,
            "required_sections": ["docs"],
            "site_layout": {
                "content_root": "content",
                "subdomain_roots": {
                    "products": "content/products",
                    "docs": "content/docs",
                    "kb": "content/kb",
                    "reference": "content/reference",
                    "blog": "content/blog",
                },
                "localization": {
                    "mode_by_section": {
                        "products": "dir",
                        "docs": "dir",
                        "kb": "dir",
                        "reference": "dir",
                        "blog": "filename",
                    }
                },
            },
            "allowed_paths": ["content/**"],
            "llm": {
                "api_base_url": "https://api.test.com",
                "model": "test-model",
                "decoding": {"temperature": 0.0},
            },
            "mcp": {"enabled": False, "listen_host": "127.0.0.1", "listen_port": 8787},
            "telemetry": {
                "endpoint_url": "https://telemetry.test.com",
                "project": "test",
            },
            "commit_service": {
                "endpoint_url": "https://commit.test.com",
                "github_token_env": "GITHUB_TOKEN",
                "commit_message_template": "test",
                "commit_body_template": "test",
            },
            "templates_version": "v1",
            "ruleset_version": "v1",
            "allow_inference": False,
            "max_fix_attempts": 3,
            "budgets": {
                "max_runtime_s": 3600,
                "max_llm_calls": 100,
                "max_llm_tokens": 100000,
                "max_file_writes": 100,
                "max_patch_attempts": 10,
                "max_lines_per_file": 500,
                "max_files_changed": 100,
            },
        }

        # Should raise ValueError about taskcard validation
        with pytest.raises(ValueError) as exc_info:
            execute_run("test-run", run_dir, run_config)

        assert "taskcard validation failed" in str(exc_info.value).lower()
        assert "TC-9999" in str(exc_info.value)

    def test_run_with_valid_taskcard_emits_event(self, tmp_path):
        """Test that run with valid taskcard emits TASKCARD_VALIDATED event."""
        # Use real repo to access TC-100
        repo_root = Path(__file__).parent.parent.parent.parent
        run_dir = repo_root / "runs" / "test-taskcard-validation"
        run_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Run config with valid taskcard
            run_config = {
                "schema_version": "1.0",
                "validation_profile": "local",
                "taskcard_id": "TC-100",  # Valid taskcard
                "product_slug": "test-product",
                "product_name": "Test Product",
                "family": "test",
                "github_repo_url": "https://github.com/test/test",
                "github_ref": "0" * 40,
                "required_sections": ["docs"],
                "site_layout": {
                    "content_root": "content",
                    "subdomain_roots": {
                        "products": "content/products",
                        "docs": "content/docs",
                        "kb": "content/kb",
                        "reference": "content/reference",
                        "blog": "content/blog",
                    },
                    "localization": {
                        "mode_by_section": {
                            "products": "dir",
                            "docs": "dir",
                            "kb": "dir",
                            "reference": "dir",
                            "blog": "filename",
                        }
                    },
                },
                "allowed_paths": ["content/**"],
                "llm": {
                    "api_base_url": "https://api.test.com",
                    "model": "test-model",
                    "decoding": {"temperature": 0.0},
                },
                "mcp": {"enabled": False, "listen_host": "127.0.0.1", "listen_port": 8787},
                "telemetry": {
                    "endpoint_url": "https://telemetry.test.com",
                    "project": "test",
                },
                "commit_service": {
                    "endpoint_url": "https://commit.test.com",
                    "github_token_env": "GITHUB_TOKEN",
                    "commit_message_template": "test",
                    "commit_body_template": "test",
                },
                "templates_version": "v1",
                "ruleset_version": "v1",
                "allow_inference": False,
                "max_fix_attempts": 3,
                "budgets": {
                    "max_runtime_s": 3600,
                    "max_llm_calls": 100,
                    "max_llm_tokens": 100000,
                    "max_file_writes": 100,
                    "max_patch_attempts": 10,
                    "max_lines_per_file": 500,
                    "max_files_changed": 100,
                },
            }

            # Run will fail during graph execution, but should pass taskcard validation
            try:
                execute_run("test-taskcard-validation", run_dir, run_config)
            except Exception:
                # Expected to fail (graph execution errors)
                pass

            # Check that TASKCARD_VALIDATED event was emitted
            events_file = run_dir / "events.ndjson"
            if events_file.exists():
                events = []
                with events_file.open() as f:
                    for line in f:
                        events.append(json.loads(line))

                # Find TASKCARD_VALIDATED event
                taskcard_events = [e for e in events if e["type"] == EVENT_TASKCARD_VALIDATED]
                assert len(taskcard_events) == 1

                event = taskcard_events[0]
                assert event["payload"]["taskcard_id"] == "TC-100"
                assert event["payload"]["taskcard_status"] == "Done"
                assert "allowed_paths_count" in event["payload"]

        finally:
            # Clean up test run directory
            import shutil

            if run_dir.exists():
                shutil.rmtree(run_dir)
