"""Unit tests for scripts/project_knowledge.py renderers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Import the script directly (not a package)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import project_knowledge as pk


# ── Helpers ──────────────────────────────────────────────────────────────────

def _product(family="3d", platform="java", display_name="Aspose.3D", **kw):
    return {"family": family, "platform": platform, "display_name": display_name, **kw}


def _bundle(**kw):
    base = {
        "product": _product(),
        "api_surface": {"class_briefs": [], "public_classes": [], "api_identifiers": [], "format_matrix": []},
        "claims": [],
        "snippets": [],
        "product_evidence": {"limitations": [], "supported_formats": [], "input_formats": [], "output_formats": []},
        "repo": {"shared_facts": {}},
        "richness_tier": {"tier": "medium"},
    }
    base.update(kw)
    return base


# ── _sanitize_cell ────────────────────────────────────────────────────────────

def test_sanitize_cell_short():
    assert pk._sanitize_cell("short") == "short"


def test_sanitize_cell_multiline():
    result = pk._sanitize_cell("line1\nline2\nline3")
    assert result == "line1…"
    assert "\n" not in result


def test_sanitize_cell_truncate_long():
    long_str = "x" * 100
    result = pk._sanitize_cell(long_str, max_len=20)
    assert len(result) <= 21  # 20 chars + ellipsis


def test_sanitize_cell_non_string():
    result = pk._sanitize_cell(42)  # type: ignore[arg-type]
    assert result == "42"


# ── _render_limitations_md ───────────────────────────────────────────────────

def test_limitations_dict_constraint():
    bundle = _bundle()
    bundle["product_evidence"]["limitations"] = [
        {"constraint": "Feature X is not supported", "source_file": "README.md", "source_line": 10},
    ]
    out = pk._render_limitations_md(bundle, _product())
    assert "Feature X is not supported" in out
    assert "README.md" in out
    assert ":10" in out


def test_limitations_string_item():
    bundle = _bundle()
    bundle["product_evidence"]["limitations"] = ["No GPU acceleration"]
    out = pk._render_limitations_md(bundle, _product())
    assert "No GPU acceleration" in out


def test_limitations_empty():
    out = pk._render_limitations_md(_bundle(), _product())
    assert "_No limitations extracted._" in out


def test_limitations_skips_empty_constraint():
    bundle = _bundle()
    bundle["product_evidence"]["limitations"] = [{"constraint": "", "source_file": "x.md"}]
    out = pk._render_limitations_md(bundle, _product())
    assert "_No limitations extracted._" in out


# ── _render_formats_md ───────────────────────────────────────────────────────

def test_formats_format_matrix_primary():
    bundle = _bundle()
    bundle["api_surface"]["format_matrix"] = [
        {"name": "FBX", "extension": ".fbx", "can_import": True, "can_export": True},
        {"name": "STL", "extension": ".stl", "can_import": False, "can_export": True},
    ]
    out = pk._render_formats_md(bundle, _product())
    assert "| FBX | .fbx | yes | yes |" in out
    assert "| STL | .stl | no | yes |" in out


def test_formats_fallback_plain_strings():
    bundle = _bundle()
    bundle["product_evidence"]["supported_formats"] = ["OBJ", "FBX"]
    bundle["product_evidence"]["input_formats"] = ["OBJ"]
    bundle["product_evidence"]["output_formats"] = ["OBJ", "FBX"]
    out = pk._render_formats_md(bundle, _product())
    assert "| OBJ | — | yes | yes |" in out
    assert "| FBX | — | — | yes |" in out


def test_formats_empty():
    out = pk._render_formats_md(_bundle(), _product())
    assert "_No format data extracted._" in out


def test_formats_matrix_takes_precedence_over_fallback():
    bundle = _bundle()
    bundle["api_surface"]["format_matrix"] = [
        {"name": "PPTX", "extension": ".pptx", "can_import": False, "can_export": True},
    ]
    bundle["product_evidence"]["supported_formats"] = ["OBJ"]
    out = pk._render_formats_md(bundle, _product())
    assert "PPTX" in out
    assert "OBJ" not in out


# ── _render_claims_md ────────────────────────────────────────────────────────

def test_claims_evidence_source_file_keys():
    bundle = _bundle()
    bundle["claims"] = [{
        "claim_id": "CLM-001",
        "text": "Library supports FBX",
        "kind": "format",
        "confidence": 0.9,
        "claim_source": "llm",
        "evidence": [{"source_file": "README.md", "line_start": 10, "line_end": 12, "snippet": "FBX support added"}],
        "snippet_ids": [],
    }]
    out = pk._render_claims_md(bundle, _product())
    assert "README.md:10-12" in out
    assert "FBX support added" in out


def test_claims_no_evidence():
    bundle = _bundle()
    bundle["claims"] = [{
        "claim_id": "CLM-002",
        "text": "Supports OBJ",
        "kind": "format",
        "confidence": 0.5,
        "claim_source": "deterministic",
        "evidence": [],
        "snippet_ids": [],
    }]
    out = pk._render_claims_md(bundle, _product())
    assert "**Evidence**: _none_" in out


def test_claims_evidence_truncated():
    """Long snippets are truncated to 120 chars."""
    bundle = _bundle()
    long_snippet = "x" * 200
    bundle["claims"] = [{
        "claim_id": "CLM-003",
        "text": "t",
        "kind": "api",
        "confidence": 1.0,
        "claim_source": "docstring",
        "evidence": [{"source_file": "f.py", "line_start": 1, "snippet": long_snippet}],
        "snippet_ids": [],
    }]
    out = pk._render_claims_md(bundle, _product())
    # Should truncate to 120 + ellipsis
    assert "…" in out
    lines = [l for l in out.splitlines() if "x" * 10 in l]
    assert lines
    assert len(lines[0]) < 200


def test_claims_empty():
    out = pk._render_claims_md(_bundle(), _product())
    assert "claim_count: 0" in out


# ── _render_api_surface_md ───────────────────────────────────────────────────

def test_api_surface_class_briefs():
    bundle = _bundle()
    bundle["api_surface"]["class_briefs"] = [{
        "name": "Scene",
        "docstring_snippet": "Represents a 3D scene.",
        "typed_methods": [{"name": "load", "return_type": "Scene", "is_static": True}],
        "properties": ["name", "nodes"],
    }]
    out = pk._render_api_surface_md(bundle, _product())
    assert "## Scene" in out
    assert "Represents a 3D scene." in out
    assert "| `load` | `Scene` | yes |" in out
    assert "`name`" in out


def test_api_surface_public_classes_fallback():
    bundle = _bundle()
    bundle["api_surface"]["public_classes"] = ["Scene", "Node", "Mesh"]
    out = pk._render_api_surface_md(bundle, _product())
    assert "| `Scene` |" in out
    assert "| `Node` |" in out


def test_api_surface_api_identifiers_fallback():
    bundle = _bundle()
    bundle["api_surface"]["api_identifiers"] = ["Scene.load", "Scene.save", "Node"]
    out = pk._render_api_surface_md(bundle, _product())
    assert "Scene" in out  # dotted prefix extracted as class
    assert "Node" in out


def test_api_surface_empty():
    out = pk._render_api_surface_md(_bundle(), _product())
    assert "_No public classes extracted._" in out


def test_api_surface_sanitizes_multiline_return_type():
    """Constructor body in return_type must not corrupt the table."""
    bundle = _bundle()
    bundle["api_surface"]["class_briefs"] = [{
        "name": "Foo",
        "docstring_snippet": "",
        "typed_methods": [{"name": "Foo", "return_type": "{\n    int x;\n    return x;\n}", "is_static": False}],
        "properties": [],
    }]
    out = pk._render_api_surface_md(bundle, _product())
    # The return_type cell must be on a single line
    for line in out.splitlines():
        if "| `Foo` |" in line:
            assert "\n" not in line
            break


# ── project_bundle error isolation ──────────────────────────────────────────

def test_project_bundle_missing_family(tmp_path):
    """Bundle with no family/platform returns SKIP, not exception."""
    bad_bundle = {"product": {}, "api_surface": {}, "claims": [], "snippets": [],
                  "product_evidence": {}, "repo": {}}
    bundle_file = tmp_path / "understanding_bundle.json"
    bundle_file.write_text(json.dumps(bad_bundle), encoding="utf-8")
    result = pk.project_bundle(bundle_file, tmp_path / "knowledge")
    assert result.startswith("SKIP")


def test_project_bundle_corrupt_json(tmp_path):
    """Corrupt JSON returns ERROR string, not exception."""
    bundle_file = tmp_path / "understanding_bundle.json"
    bundle_file.write_text("not valid json {{{", encoding="utf-8")
    result = pk.project_bundle(bundle_file, tmp_path / "knowledge")
    assert result.startswith("ERROR")


def test_project_bundle_ok(tmp_path):
    """Valid minimal bundle projects successfully."""
    bundle = {
        "product": {"family": "test", "platform": "python", "display_name": "Test Lib",
                    "repo_sha": "abc123", "canonical_import": "test_lib", "repo_url": ""},
        "api_surface": {"class_briefs": [], "public_classes": ["Foo"], "api_identifiers": [],
                        "format_matrix": []},
        "claims": [],
        "snippets": [],
        "product_evidence": {"limitations": [], "supported_formats": [], "input_formats": [], "output_formats": []},
        "repo": {"shared_facts": {"install_command": "pip install test-lib", "package_name": "test-lib", "version": "1.0"}},
        "richness_tier": {"tier": "low"},
    }
    bundle_file = tmp_path / "understanding_bundle.json"
    bundle_file.write_text(json.dumps(bundle), encoding="utf-8")
    output_root = tmp_path / "knowledge"
    result = pk.project_bundle(bundle_file, output_root)
    assert result.startswith("OK test/python")
    assert (output_root / "test" / "python" / "api_surface.md").exists()
    assert (output_root / "test" / "python" / "claims.md").exists()
    assert (output_root / "test" / "python" / "model.yaml").exists()


def test_project_bundle_model_yaml_has_real_path(tmp_path):
    """model.yaml bundle_source points to the actual bundle file."""
    bundle = {
        "product": {"family": "test", "platform": "java", "display_name": "T",
                    "repo_sha": "", "canonical_import": "", "repo_url": ""},
        "api_surface": {"class_briefs": [], "public_classes": [], "api_identifiers": [], "format_matrix": []},
        "claims": [], "snippets": [],
        "product_evidence": {"limitations": [], "supported_formats": [], "input_formats": [], "output_formats": []},
        "repo": {"shared_facts": {}},
        "richness_tier": {},
    }
    bundle_file = tmp_path / "my_run" / "understanding_bundle.json"
    bundle_file.parent.mkdir()
    bundle_file.write_text(json.dumps(bundle), encoding="utf-8")
    output_root = tmp_path / "knowledge"
    pk.project_bundle(bundle_file, output_root)
    import yaml
    model = yaml.safe_load((output_root / "test" / "java" / "model.yaml").read_text())
    assert "understanding_bundle.json" in model["bundle_source"]
    assert "phase_store" not in model["bundle_source"]
