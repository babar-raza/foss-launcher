"""TC-3230: Token-safe truth pack builder for W5 hallucination prevention.

Builds ``truth_pack_min.json`` -- a deterministic ~2000-token payload
combining repo_truth, product_facts, and api_index into a single
injection-ready block for W5 system prompts.

All data comes from existing W2 artifacts -- no LLM involved.

Spec references:
- specs/03_product_facts_and_evidence.md (Evidence priority and structure)
- specs/21_worker_contracts.md (W2 FactsBuilder contract)
- specs/schemas/truth_pack_min.schema.json
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Hard caps to stay within ~2000 token budget
_MAX_FORMATS = 30
_MAX_CONVERSION_PAIRS = 10
_MAX_API_CLASSES = 5
_MAX_CAPABILITIES = 10
_MAX_LIMITATIONS = 5


def build_truth_pack_min(
    repo_truth: Dict[str, Any],
    *,
    product_facts: Optional[Dict[str, Any]] = None,
    api_index: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build ``truth_pack_min.json`` from available W2 artifacts.

    Deterministic -- no LLM. Aggregates canonical facts into a single
    payload that W5 can inject into system prompts within a ~2000 token
    budget.

    Args:
        repo_truth: ``repo_truth.json`` artifact (required, may be empty dict).
        product_facts: ``product_facts.json`` artifact (optional).
        api_index: ``api_index.json`` artifact (optional).

    Returns:
        Artifact dict ready for ``atomic_write_json``.
    """
    product_facts = product_facts or {}

    # ---------------------------------------------------------------
    # 1. Canonical package / install / runtime facts
    # ---------------------------------------------------------------
    pkg_name_obj = repo_truth.get("package_name", {})
    pkg_name = pkg_name_obj.get("value", "") if isinstance(pkg_name_obj, dict) else str(pkg_name_obj)

    py_req = repo_truth.get("python_requires", {})
    py_min = py_req.get("min", "") if isinstance(py_req, dict) else ""
    py_spec = py_req.get("spec", "") if isinstance(py_req, dict) else ""

    license_info = repo_truth.get("license", {})
    if not isinstance(license_info, dict):
        license_info = {}

    # Fallback: extract package_name from product_facts code_structure
    if not pkg_name:
        code_struct = product_facts.get("code_structure", {})
        pkg_names = code_struct.get("package_names", [])
        if pkg_names:
            pkg_name = pkg_names[0]

    # Fallback: extract installation_method from product_facts claims
    install_method = ""
    install_claims = product_facts.get("claim_groups", {}).get("install_steps", [])
    if install_claims:
        claim_by_id = {c.get("claim_id", ""): c for c in product_facts.get("claims", [])}
        for cid in install_claims[:3]:
            ct = claim_by_id.get(cid, {}).get("claim_text", "")
            m = re.search(r"pip\s+install\s+\S+", ct, re.IGNORECASE)
            if m:
                install_method = m.group(0)
                break

    # Fallback: construct pip install from package name
    if not install_method and pkg_name:
        install_method = f"pip install {pkg_name}"

    canonical_facts = {
        "installation_method": install_method,
        "license_name": license_info.get("name", ""),
        "license_spdx": license_info.get("spdx_id", ""),
        "package_name": pkg_name,
        "python_requires_min": py_min,
        "python_requires_spec": py_spec,
    }

    # ---------------------------------------------------------------
    # 2. Supported formats + directions
    # ---------------------------------------------------------------
    def _extract_values(obj: Any, max_items: int) -> List[str]:
        if isinstance(obj, dict):
            return obj.get("values", [])[:max_items]
        if isinstance(obj, list):
            return obj[:max_items]
        return []

    supported_formats = _extract_values(
        repo_truth.get("supported_formats", {}), _MAX_FORMATS
    )
    input_formats = _extract_values(
        repo_truth.get("input_formats", {}), _MAX_FORMATS
    )
    output_formats = _extract_values(
        repo_truth.get("output_formats", {}), _MAX_FORMATS
    )

    # Fallback: product_facts.supported_formats
    if not supported_formats:
        pf_formats = product_facts.get("supported_formats", [])
        if pf_formats:
            supported_formats = [
                f.get("format", f) if isinstance(f, dict) else str(f)
                for f in pf_formats[:_MAX_FORMATS]
            ]

    formats_block = {
        "input": sorted(input_formats),
        "output": sorted(output_formats),
        "supported": sorted(supported_formats),
    }

    # ---------------------------------------------------------------
    # 3. Conversion pairs (top 10)
    # ---------------------------------------------------------------
    raw_pairs = _extract_values(
        repo_truth.get("conversion_pairs", {}), _MAX_CONVERSION_PAIRS
    )
    conversion_pairs = []
    for p in raw_pairs:
        if isinstance(p, dict):
            conversion_pairs.append({
                "source": p.get("source", ""),
                "target": p.get("target", ""),
            })

    # ---------------------------------------------------------------
    # 4. API index summary
    # ---------------------------------------------------------------
    api_summary: Dict[str, Any] = {}
    if api_index:
        class_index = api_index.get("class_index", [])
        api_summary = {
            "top_classes": [
                {
                    "import_path": c.get("import_path", ""),
                    "method_count": c.get("method_count", 0),
                    "name": c.get("name", ""),
                }
                for c in class_index[:_MAX_API_CLASSES]
            ],
            "total_classes": len(class_index),
            "total_functions": len(api_index.get("function_index", [])),
            "total_symbols": api_index.get("symbol_count", 0),
        }

    # ---------------------------------------------------------------
    # 5. Capability boundaries (with evidence pointers)
    # ---------------------------------------------------------------
    capabilities_raw = _extract_values(
        repo_truth.get("capabilities", {}), _MAX_CAPABILITIES
    )
    capabilities = []
    for cap in capabilities_raw:
        if isinstance(cap, dict):
            capabilities.append({
                "evidence": cap.get("evidence", {}),
                "source": cap.get("source", ""),
                "text": cap.get("text", ""),
            })
        elif isinstance(cap, str):
            capabilities.append({"evidence": {}, "source": "", "text": cap})

    # ---------------------------------------------------------------
    # 6. Limitations
    # ---------------------------------------------------------------
    limitations_raw = _extract_values(
        repo_truth.get("limitations", {}), _MAX_LIMITATIONS
    )
    limitations = []
    for lim in limitations_raw:
        if isinstance(lim, dict):
            limitations.append({
                "source_file": lim.get("source_file", ""),
                "text": lim.get("text", ""),
            })
        elif isinstance(lim, str):
            limitations.append({"source_file": "", "text": lim})

    return {
        "schema_version": "1.0",
        "api_summary": api_summary,
        "canonical_facts": canonical_facts,
        "capabilities": capabilities,
        "conversion_pairs": conversion_pairs,
        "formats": formats_block,
        "limitations": limitations,
        "metadata": {
            "capability_count": len(capabilities),
            "conversion_pair_count": len(conversion_pairs),
            "format_count": len(supported_formats),
            "limitation_count": len(limitations),
        },
    }
