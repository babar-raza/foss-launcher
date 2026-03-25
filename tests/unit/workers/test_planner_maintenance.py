"""Unit tests for maintenance mode planner filtering — TC-5168."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from launcher.models.plan import PlannedPage
from launcher.workers.planner.worker import _apply_maintenance_filter


def _make_page(page_id: str, content_path: str = "") -> PlannedPage:
    return PlannedPage(
        page_id=page_id,
        page_role="howto_article",
        title=f"Title {page_id}",
        content_path=content_path or page_id,
    )


def _make_context(run_dir: Path) -> MagicMock:
    ctx = MagicMock()
    ctx.run_dir = run_dir
    ctx.log = MagicMock()
    ctx.log.debug = lambda *a, **k: None
    ctx.log.info = lambda *a, **k: None
    ctx.log.warning = lambda *a, **k: None
    return ctx


# ---------------------------------------------------------------------------
# Decision tree: create/update/enhance/no-change
# ---------------------------------------------------------------------------


def test_no_change_pages_are_filtered(tmp_path: Path) -> None:
    """Pages with action=no-change are removed from the plan."""
    drift_report = {
        "page_drift_actions": {
            "kb.aspose.org/3d/python/howto.md": "no-change",
            "kb.aspose.org/3d/python/other.md": "update",
        }
    }
    (tmp_path / "drift_report.json").write_text(
        json.dumps(drift_report), encoding="utf-8"
    )
    pages = [
        _make_page("page-a", "kb.aspose.org/3d/python/howto.md"),
        _make_page("page-b", "kb.aspose.org/3d/python/other.md"),
    ]
    ctx = _make_context(tmp_path)
    result = _apply_maintenance_filter(pages, ctx)
    assert len(result) == 1
    assert result[0].page_id == "page-b"


def test_update_action_set_on_page(tmp_path: Path) -> None:
    """Pages with update action have maintenance_action='update' set."""
    drift_report = {
        "page_drift_actions": {
            "kb.aspose.org/3d/python/howto.md": "update",
        }
    }
    (tmp_path / "drift_report.json").write_text(
        json.dumps(drift_report), encoding="utf-8"
    )
    pages = [_make_page("page-a", "kb.aspose.org/3d/python/howto.md")]
    ctx = _make_context(tmp_path)
    result = _apply_maintenance_filter(pages, ctx)
    assert len(result) == 1
    assert result[0].maintenance_action == "update"


def test_enhance_action_set_on_page(tmp_path: Path) -> None:
    """Pages with enhance action have maintenance_action='enhance' set."""
    drift_report = {
        "page_drift_actions": {
            "kb.aspose.org/3d/python/howto.md": "enhance",
        }
    }
    (tmp_path / "drift_report.json").write_text(
        json.dumps(drift_report), encoding="utf-8"
    )
    pages = [_make_page("page-a", "kb.aspose.org/3d/python/howto.md")]
    ctx = _make_context(tmp_path)
    result = _apply_maintenance_filter(pages, ctx)
    assert len(result) == 1
    assert result[0].maintenance_action == "enhance"


def test_new_page_not_in_drift_report_gets_create(tmp_path: Path) -> None:
    """Pages not in drift_report page_drift_actions default to create."""
    drift_report = {"page_drift_actions": {}}
    (tmp_path / "drift_report.json").write_text(
        json.dumps(drift_report), encoding="utf-8"
    )
    pages = [_make_page("page-new", "kb.aspose.org/3d/python/brand-new.md")]
    ctx = _make_context(tmp_path)
    result = _apply_maintenance_filter(pages, ctx)
    assert len(result) == 1
    assert result[0].maintenance_action == "create"


def test_all_no_change_returns_empty(tmp_path: Path) -> None:
    """All no-change pages → empty plan returned."""
    drift_report = {
        "page_drift_actions": {
            "kb.aspose.org/3d/python/page-a.md": "no-change",
            "kb.aspose.org/3d/python/page-b.md": "no-change",
        }
    }
    (tmp_path / "drift_report.json").write_text(
        json.dumps(drift_report), encoding="utf-8"
    )
    pages = [
        _make_page("page-a", "kb.aspose.org/3d/python/page-a.md"),
        _make_page("page-b", "kb.aspose.org/3d/python/page-b.md"),
    ]
    ctx = _make_context(tmp_path)
    result = _apply_maintenance_filter(pages, ctx)
    assert result == []


# ---------------------------------------------------------------------------
# Missing/malformed drift_report fallback
# ---------------------------------------------------------------------------


def test_no_drift_report_returns_all_pages(tmp_path: Path) -> None:
    """When drift_report.json is absent, all pages are returned with no action set."""
    pages = [_make_page("page-a"), _make_page("page-b")]
    ctx = _make_context(tmp_path)
    result = _apply_maintenance_filter(pages, ctx)
    assert len(result) == 2


def test_malformed_drift_report_returns_all_pages(tmp_path: Path) -> None:
    """When drift_report.json is malformed JSON, all pages are returned."""
    (tmp_path / "drift_report.json").write_text("not valid json", encoding="utf-8")
    pages = [_make_page("page-a"), _make_page("page-b")]
    ctx = _make_context(tmp_path)
    result = _apply_maintenance_filter(pages, ctx)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# pipeline_mode field on RunConfig
# ---------------------------------------------------------------------------


def test_run_config_pipeline_mode_default() -> None:
    """RunConfig defaults to pipeline_mode='create'."""
    from launcher.models.run_config import RunConfig

    cfg = RunConfig(family="3d", platform="python", repo_url="https://example.com")
    assert cfg.pipeline_mode == "create"


def test_run_config_pipeline_mode_verify() -> None:
    """RunConfig accepts pipeline_mode='verify'."""
    from launcher.models.run_config import RunConfig

    cfg = RunConfig(
        family="3d", platform="python", repo_url="https://example.com",
        pipeline_mode="verify",
    )
    assert cfg.pipeline_mode == "verify"


def test_run_config_pipeline_mode_maintain() -> None:
    """RunConfig accepts pipeline_mode='maintain'."""
    from launcher.models.run_config import RunConfig

    cfg = RunConfig(
        family="3d", platform="python", repo_url="https://example.com",
        pipeline_mode="maintain",
    )
    assert cfg.pipeline_mode == "maintain"
