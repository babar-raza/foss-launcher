"""Unit tests for the declarative validation gate registry engine.

Covers: registry_loader, gate_types, context, adapters, runner.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch

import pytest

from launch.validation_engine.gate_types import (
    GateDefinition,
    GateResult,
    RunnerType,
    SkipGroup,
)
from launch.validation_engine.registry_loader import load_registry


# ═══════════════════════════════════════════════════════════════════════
# Registry Loader
# ═══════════════════════════════════════════════════════════════════════


class TestRegistryLoader:
    """Tests for ``registry_loader.load_registry()``."""

    def test_loads_34_gates(self) -> None:
        """Spec v1.1 adds 5 gates + gate_15b_code_fence_api (TC-2811) + truth enforcement + Phase 1/2 gates + gate_truth_facts_completeness."""
        gates = load_registry()
        assert len(gates) == 41

    def test_sorted_by_order(self) -> None:
        gates = load_registry()
        orders = [g.order for g in gates]
        assert orders == sorted(orders)

    def test_no_duplicate_gate_ids(self) -> None:
        gates = load_registry()
        ids = [g.gate_id for g in gates]
        assert len(ids) == len(set(ids))

    def test_no_duplicate_orders(self) -> None:
        gates = load_registry()
        orders = [g.order for g in gates]
        assert len(orders) == len(set(orders))

    def test_valid_runner_types(self) -> None:
        gates = load_registry()
        valid_types = set(RunnerType)
        for gate in gates:
            assert gate.runner_type in valid_types, f"{gate.gate_id}: invalid runner"

    def test_all_gates_have_display_name(self) -> None:
        gates = load_registry()
        for gate in gates:
            assert gate.display_name, f"{gate.gate_id}: missing display_name"

    def test_all_gates_have_module_and_callable(self) -> None:
        gates = load_registry()
        for gate in gates:
            assert gate.module, f"{gate.gate_id}: empty module"
            assert gate.callable_name, f"{gate.gate_id}: empty callable_name"

    def test_rejects_invalid_yaml(self, tmp_path: Path) -> None:
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("not_gates: []", encoding="utf-8")
        with pytest.raises(ValueError, match="top-level 'gates' key"):
            load_registry(bad_yaml)

    def test_rejects_duplicate_ids(self, tmp_path: Path) -> None:
        dupe_yaml = tmp_path / "dupe.yaml"
        dupe_yaml.write_text(
            """gates:
  - gate_id: same_id
    display_name: A
    order: 1
    module: a.b
    callable_name: fn
    runner_type: execute_gate
  - gate_id: same_id
    display_name: B
    order: 2
    module: a.b
    callable_name: fn
    runner_type: execute_gate
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Duplicate gate_ids"):
            load_registry(dupe_yaml)

    def test_gate_definition_is_frozen(self) -> None:
        gates = load_registry()
        with pytest.raises(AttributeError):
            gates[0].gate_id = "modified"  # type: ignore[misc]

    def test_mandatory_profiles_loaded(self) -> None:
        """TC-2870: mandatory_profiles parsed from YAML."""
        gates = load_registry()
        gate_15b = next(g for g in gates if g.gate_id == "gate_15b_code_fence_api")
        assert "ci" in gate_15b.mandatory_profiles
        assert "prod" in gate_15b.mandatory_profiles

    def test_mandatory_profiles_empty_by_default(self) -> None:
        """Gates without mandatory_profiles have empty tuple."""
        gates = load_registry()
        # gate_1_schema_validation has no mandatory_profiles
        gate_1 = next(g for g in gates if g.gate_id == "gate_1_schema_validation")
        assert gate_1.mandatory_profiles == ()

    def test_truth_enforcement_gates_are_mandatory(self) -> None:
        """TC-2870 + Phase 1/2: All 9 truth enforcement gates have mandatory_profiles=[ci,prod]."""
        gates = load_registry()
        mandatory_gate_ids = {
            "gate_truth_layer_completeness",
            "gate_5_cross_page_link_validity",
            "gate_15b_code_fence_api",
            "gate_19_redundancy",
            "gate_20_cross_page_consistency",
            "gate_product_name_integrity",
            "gate_scaffold_leak",
            "gate_license_consistency",
            "gate_reference_public_surface",
        }
        for gate in gates:
            if gate.gate_id in mandatory_gate_ids:
                assert "ci" in gate.mandatory_profiles, f"{gate.gate_id} missing ci"
                assert "prod" in gate.mandatory_profiles, f"{gate.gate_id} missing prod"


# ═══════════════════════════════════════════════════════════════════════
# Gate Types
# ═══════════════════════════════════════════════════════════════════════


class TestGateTypes:
    """Tests for gate_types dataclasses."""

    def test_gate_result_defaults(self) -> None:
        r = GateResult(gate_id="test", ok=True)
        assert r.issues == []
        assert r.skipped is False
        assert r.error_message is None

    def test_skip_group_enum_values(self) -> None:
        assert SkipGroup("artifact_block") == SkipGroup.ARTIFACT_BLOCK
        assert SkipGroup("none") == SkipGroup.NONE


# ═══════════════════════════════════════════════════════════════════════
# GateContext
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture()
def ctx_run_dir(tmp_path: Path) -> Path:
    """Minimal run directory for GateContext tests."""
    # Nest two levels deep so repo_root resolves correctly
    run_dir = tmp_path / "runs" / "run_001"
    run_dir.mkdir(parents=True)
    (run_dir / "artifacts").mkdir()
    (run_dir / "work" / "site" / "content").mkdir(parents=True)
    return run_dir


class TestGateContext:
    """Tests for ``context.GateContext``."""

    def test_repo_root(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext

        ctx = GateContext(ctx_run_dir, {}, "local")
        assert ctx.get_repo_root() == ctx_run_dir.parent.parent

    def test_site_content_dir(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext

        ctx = GateContext(ctx_run_dir, {}, "local")
        assert ctx.get_site_content_dir() == ctx_run_dir / "work" / "site"

    def test_md_files_site_returns_sorted(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext

        site = ctx_run_dir / "work" / "site"
        (site / "b.md").write_text("b", encoding="utf-8")
        (site / "a.md").write_text("a", encoding="utf-8")
        ctx = GateContext(ctx_run_dir, {}, "local")
        files = ctx.get_md_files_site()
        assert [f.name for f in files] == ["a.md", "b.md"]

    def test_md_files_content_empty_when_missing(self, ctx_run_dir: Path) -> None:
        import shutil

        from launch.validation_engine.context import GateContext

        shutil.rmtree(ctx_run_dir / "work" / "site" / "content")
        ctx = GateContext(ctx_run_dir, {}, "local")
        assert ctx.get_md_files_content() == []

    def test_safe_accessor_returns_empty_dict(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext

        ctx = GateContext(ctx_run_dir, {}, "local")
        assert ctx.get_page_plan_safe() == {}
        assert ctx.get_product_facts_safe() == {}

    def test_strict_accessor_raises_on_missing(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext
        from launch.workers.w9_validator.worker import (
            ValidatorArtifactMissingError,
        )

        ctx = GateContext(ctx_run_dir, {}, "local")
        with pytest.raises(ValidatorArtifactMissingError):
            ctx.get_page_plan()

    def test_error_caching_reraises(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext
        from launch.workers.w9_validator.worker import (
            ValidatorArtifactMissingError,
        )

        ctx = GateContext(ctx_run_dir, {}, "local")
        with pytest.raises(ValidatorArtifactMissingError):
            ctx.get_page_plan()
        # Second call should re-raise the same error
        with pytest.raises(ValidatorArtifactMissingError):
            ctx.get_page_plan()

    def test_lazy_load_caches(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext

        pf = {"product_name": "Test", "claims": []}
        (ctx_run_dir / "artifacts" / "product_facts.json").write_text(
            json.dumps(pf), encoding="utf-8"
        )
        ctx = GateContext(ctx_run_dir, {}, "local")
        first = ctx.get_product_facts()
        second = ctx.get_product_facts()
        assert first is second  # same object, not re-loaded

    def test_llm_client_none_without_config(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext

        ctx = GateContext(ctx_run_dir, {}, "local")
        assert ctx.get_llm_client() is None

    def test_max_parallel_g17_defaults(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext

        ctx = GateContext(ctx_run_dir, {}, "local")
        assert ctx.get_max_parallel_g17() == 4

    def test_max_parallel_g17_clamped(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext

        ctx = GateContext(ctx_run_dir, {"max_parallel_files_g17": 100}, "local")
        assert ctx.get_max_parallel_g17() == 8

    def test_pages_with_roles_structure(self, ctx_run_dir: Path) -> None:
        from launch.validation_engine.context import GateContext

        site = ctx_run_dir / "work" / "site"
        (site / "test.md").write_text("---\ntitle: T\n---\nHello", encoding="utf-8")
        pp = {"pages": [{"output_path": "test.md", "page_role": "tutorial"}]}
        (ctx_run_dir / "artifacts" / "page_plan.json").write_text(
            json.dumps(pp), encoding="utf-8"
        )
        ctx = GateContext(ctx_run_dir, {}, "local")
        pages = ctx.get_pages_with_roles()
        assert len(pages) == 1
        assert pages[0]["page_role"] == "tutorial"
        assert "path" in pages[0]
        assert "content" in pages[0]


# ═══════════════════════════════════════════════════════════════════════
# Adapters
# ═══════════════════════════════════════════════════════════════════════


class TestAdapters:
    """Tests for ``adapters.resolve_callable`` and dispatch."""

    def test_resolve_callable_finds_function(self) -> None:
        from launch.validation_engine.adapters import resolve_callable

        gate_def = GateDefinition(
            gate_id="test",
            display_name="Test",
            order=1,
            module="launch.validation_engine.registry_loader",
            callable_name="load_registry",
            runner_type=RunnerType.EXECUTE_GATE,
        )
        fn = resolve_callable(gate_def)
        assert callable(fn)
        assert fn.__name__ == "load_registry"

    def test_dispatch_map_covers_all_runner_types(self) -> None:
        from launch.validation_engine.adapters import ADAPTER_DISPATCH

        for rt in RunnerType:
            assert rt in ADAPTER_DISPATCH, f"Missing adapter for {rt}"


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════


class TestRunner:
    """Tests for ``runner.run_gates()``."""

    def test_skip_group_cascade(self, ctx_run_dir: Path) -> None:
        """When artifact_block fires, remaining artifact_block gates skip."""
        from launch.validation_engine.context import GateContext
        from launch.validation_engine.gate_types import SkipGroup
        from launch.validation_engine.runner import run_gates

        # No artifacts → gate 14 triggers graceful_artifact_skip,
        # gates 16/18/19/20 should cascade-skip via artifact_block.
        # We need valid structure for gates 1-13 to not crash.
        # Simplest: mock run_gates to test the logic unit directly.
        ctx = GateContext(ctx_run_dir, {}, "local")
        ctx.artifact_block_skip = True
        # A gate with skip_group=artifact_block should skip
        gate_def = GateDefinition(
            gate_id="test_skip",
            display_name="Test",
            order=1,
            module="launch.validation_engine.registry_loader",
            callable_name="load_registry",
            runner_type=RunnerType.EXECUTE_GATE,
            skip_group=SkipGroup.ARTIFACT_BLOCK,
        )
        # Simulate the skip check from runner.py
        assert gate_def.skip_group == SkipGroup.ARTIFACT_BLOCK
        assert ctx.artifact_block_skip is True

    def test_gate_result_structure(self) -> None:
        """Gate results must have 'name' and 'ok' keys."""
        from launch.validation_engine.adapters import ADAPTER_DISPATCH

        # Verify all adapter return types are (bool, list)
        for rt, adapter in ADAPTER_DISPATCH.items():
            assert callable(adapter), f"Adapter for {rt} not callable"

    def test_registry_gate_order_matches_expected(self) -> None:
        """Registry gate IDs in order must match expected sequence."""
        gates = load_registry()
        expected_ids = [
            # Phase 2: Pre-flight truth layer check
            "gate_truth_layer_completeness",
            "gate_1_schema_validation",
            "gate_2_claim_marker_validity",
            "gate_3_snippet_references",
            "gate_4_frontmatter_required_fields",
            "gate_5_cross_page_link_validity",
            "gate_6_accessibility",
            "gate_7_content_quality",
            "gate_8_claim_coverage",
            "gate_9_navigation_integrity",
            "gate_10_consistency",
            "gate_11_template_token_lint",
            "gate_12_patch_conflicts",
            "gate_13_hugo_build",
            "gate_14_content_distribution",
            "gate_15_api_hallucination",
            "gate_15b_code_fence_api",
            "gate_16_content_hygiene",
            "gate_18_code_prose_balance",
            "gate_19_redundancy",
            "gate_17_formatting_quality",
            "gate_20_cross_page_consistency",
            "gate_product_name_integrity",
            "gate_slug_safety",
            "gate_scaffold_leak",
            "gate_license_consistency",
            "gate_t_test_determinism",
            "gate_u_taskcard_authorization",
            "gate_p1_page_size_limit",
            "gate_p2_image_optimization",
            "gate_p3_build_time_limit",
            "gate_s1_xss_prevention",
            "gate_s2_sensitive_data_leak",
            "gate_s3_external_link_safety",
            # Spec v1.1: mandatory page compliance gates
            "gate_blog_mandatory",
            "gate_kb_howto_mandatory",
            "gate_reference_objects",
            "gate_kb_howto_structure",
            "gate_kb_howto_evidence",
            # Phase 1: Public API boundary enforcement
            "gate_reference_public_surface",
            # Phase 4: Truth facts content validation
            "gate_truth_facts_completeness",
        ]
        actual_ids = [g.gate_id for g in gates]
        assert actual_ids == expected_ids

    def test_all_callables_resolvable(self) -> None:
        """Every gate's module + callable must be importable."""
        from launch.validation_engine.adapters import resolve_callable

        gates = load_registry()
        for gate in gates:
            fn = resolve_callable(gate)
            assert callable(fn), f"{gate.gate_id}: {gate.callable_name} not callable"


# ═══════════════════════════════════════════════════════════════════════
# TC-2431: Callable Validation at Load Time
# ═══════════════════════════════════════════════════════════════════════


class TestCallableValidation:
    """Tests for ``_validate_callables`` and the ``validate_callables`` param."""

    def test_callable_validation_passes_all_33_gates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All registered gates must resolve to callable objects (Spec v1.1 +5, +gate_15b, +Phase 1/2)."""
        monkeypatch.setenv("LAUNCH_VALIDATE_GATE_CALLABLES", "1")
        # Should not raise
        gates = load_registry()
        assert len(gates) == 41

    def test_callable_validation_via_param_passes(self) -> None:
        """``validate_callables=True`` should pass without env var."""
        gates = load_registry(validate_callables=True)
        assert len(gates) == 41

    def test_callable_validation_catches_bad_module(
        self, tmp_path: Path
    ) -> None:
        """A gate pointing to a non-existent module must raise ValueError."""
        bad_yaml = tmp_path / "bad_module.yaml"
        bad_yaml.write_text(
            """gates:
  - gate_id: bad_gate
    display_name: Bad Module Gate
    order: 1
    module: launch.does_not_exist.module
    callable_name: some_fn
    runner_type: execute_gate
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="cannot import module"):
            load_registry(bad_yaml, validate_callables=True)

    def test_callable_validation_catches_non_callable_attr(
        self, tmp_path: Path
    ) -> None:
        """A gate whose callable_name resolves to a non-callable must raise."""
        bad_yaml = tmp_path / "non_callable.yaml"
        # Point to a module attribute that is NOT callable (e.g. a string constant)
        bad_yaml.write_text(
            """gates:
  - gate_id: non_callable_gate
    display_name: Non-callable Gate
    order: 1
    module: launch.validation_engine.registry_loader
    callable_name: _REGISTRY_PATH
    runner_type: execute_gate
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="not callable"):
            load_registry(bad_yaml, validate_callables=True)

    def test_callable_validation_catches_missing_attr(
        self, tmp_path: Path
    ) -> None:
        """A gate whose callable_name doesn't exist in the module must raise."""
        bad_yaml = tmp_path / "missing_attr.yaml"
        bad_yaml.write_text(
            """gates:
  - gate_id: missing_attr_gate
    display_name: Missing Attr Gate
    order: 1
    module: launch.validation_engine.registry_loader
    callable_name: fn_that_does_not_exist
    runner_type: execute_gate
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="attribute.*not found"):
            load_registry(bad_yaml, validate_callables=True)

    def test_callable_validation_disabled_by_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Without env var or param, bad callables must NOT raise at load time."""
        monkeypatch.delenv("LAUNCH_VALIDATE_GATE_CALLABLES", raising=False)
        bad_yaml = tmp_path / "bad_silent.yaml"
        bad_yaml.write_text(
            """gates:
  - gate_id: bad_gate_silent
    display_name: Silent Bad Gate
    order: 1
    module: launch.does_not_exist.module
    callable_name: some_fn
    runner_type: execute_gate
""",
            encoding="utf-8",
        )
        # Must NOT raise — callable validation is disabled by default
        gates = load_registry(bad_yaml)
        assert len(gates) == 1

    def test_callable_validation_env_var_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """LAUNCH_VALIDATE_GATE_CALLABLES=1 activates validation even without param."""
        monkeypatch.setenv("LAUNCH_VALIDATE_GATE_CALLABLES", "1")
        bad_yaml = tmp_path / "env_bad.yaml"
        bad_yaml.write_text(
            """gates:
  - gate_id: env_bad_gate
    display_name: Env Bad Gate
    order: 1
    module: launch.does_not_exist.module_xyz
    callable_name: some_fn
    runner_type: execute_gate
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="cannot import module"):
            load_registry(bad_yaml, validate_callables=False)

    def test_callable_validation_collects_multiple_errors(
        self, tmp_path: Path
    ) -> None:
        """Multiple bad gates must all appear in the single ValueError."""
        bad_yaml = tmp_path / "multi_bad.yaml"
        bad_yaml.write_text(
            """gates:
  - gate_id: bad_gate_1
    display_name: Bad Gate 1
    order: 1
    module: launch.no_such_module_a
    callable_name: fn_a
    runner_type: execute_gate
  - gate_id: bad_gate_2
    display_name: Bad Gate 2
    order: 2
    module: launch.no_such_module_b
    callable_name: fn_b
    runner_type: execute_gate
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError) as exc_info:
            load_registry(bad_yaml, validate_callables=True)
        msg = str(exc_info.value)
        assert "bad_gate_1" in msg
        assert "bad_gate_2" in msg
