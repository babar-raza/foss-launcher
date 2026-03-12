"""Contradiction resolver (TC-4002 / humming-greeting-kay Phase 1).

Compares LLM-generated claims against source-verified evidence (format
matrix, limitations, API surface) and downgrades or amends claims that
conflict with deterministic facts.

Runs AFTER LLM claim extraction and BEFORE claim normalization.
"""
from __future__ import annotations

import logging
import re
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.claims import Claim
    from launcher.models.product import ApiSurface
    from launcher.models.understanding import LimitationEntry

logger = logging.getLogger(__name__)


def resolve_contradictions(
    claims: "list[Claim]",
    api_surface: "ApiSurface | None",
    limitations: "list[LimitationEntry] | None" = None,
) -> "tuple[list[Claim], list[dict[str, Any]]]":
    """Resolve contradictions between LLM claims and source-verified facts.

    Returns:
        (resolved_claims, contradiction_log) where contradiction_log is a list
        of dicts recording each resolution for observability.
    """
    if not claims:
        return claims, []

    contradiction_log: list[dict[str, Any]] = []

    # Build format lookup from api_surface.format_matrix
    fmt_lookup: dict[str, Any] = {}
    if api_surface:
        for fr in getattr(api_surface, "format_matrix", []) or []:
            fmt_lookup[fr.name.upper()] = fr
            if fr.extension:
                ext = fr.extension.lstrip(".").upper()
                if ext:
                    fmt_lookup[ext] = fr

    # Build API identifier set
    api_ids: set[str] = set()
    if api_surface:
        for ident in getattr(api_surface, "api_identifiers", []) or []:
            api_ids.add(ident.lower())
        for cls in getattr(api_surface, "class_briefs", []) or []:
            api_ids.add(cls.name.lower())
            for m in cls.methods or []:
                api_ids.add(m.lower())

    # TC-HAL-01: Split method/property sets for type checking
    method_ids: set[str] = set()
    property_ids: set[str] = set()
    if api_surface:
        for cls in getattr(api_surface, "class_briefs", []) or []:
            for m in cls.methods or []:
                if m:
                    method_ids.add(m.lower())
            for p in cls.properties or []:
                if p:
                    property_ids.add(p.lower())

    # TC-HAL-03: Build enum member lookup
    enum_member_map: dict[str, set[str]] = {}
    if api_surface:
        for enum_rec in getattr(api_surface, "enums", []) or []:
            member_names = {m.name.lower() for m in (enum_rec.members or [])}
            enum_member_map[enum_rec.name.lower()] = member_names
        for cls in getattr(api_surface, "class_briefs", []) or []:
            for enum_rec in (cls.enums or []):
                member_names = {m.name.lower() for m in (enum_rec.members or [])}
                enum_member_map[enum_rec.name.lower()] = member_names

    # Build limitation features set
    limitation_features: dict[str, str] = {}
    for lim in (limitations or []):
        limitation_features[lim.feature.lower()] = lim.constraint

    resolved: list[Claim] = []
    for claim in claims:
        text_upper = claim.text.upper()
        text_lower = claim.text.lower()
        was_modified = False

        # Check 1: Format capability contradiction
        for fmt_name, fmt_rec in fmt_lookup.items():
            if fmt_name not in text_upper:
                continue
            # Check export claims against can_export=False
            if not fmt_rec.can_export and _mentions_export(claim.text):
                claim = claim.model_copy(update={"visibility": "internal"})
                contradiction_log.append({
                    "claim_id": claim.claim_id,
                    "type": "format_capability",
                    "original_text": claim.text[:200],
                    "resolution": f"downgraded to internal — {fmt_name} can_export=False",
                    "evidence": f"FormatRecord({fmt_name}).can_export=False",
                })
                was_modified = True
                break
            # Check import claims against can_import=False
            if not fmt_rec.can_import and _mentions_import(claim.text):
                claim = claim.model_copy(update={"visibility": "internal"})
                contradiction_log.append({
                    "claim_id": claim.claim_id,
                    "type": "format_capability",
                    "original_text": claim.text[:200],
                    "resolution": f"downgraded to internal — {fmt_name} can_import=False",
                    "evidence": f"FormatRecord({fmt_name}).can_import=False",
                })
                was_modified = True
                break

        # Check 2: API existence — claim references class/method not in API surface
        # TC-4090 P2-E: Expanded from backtick-only to also catch unquoted PascalCase
        # identifiers (≥5 chars) such as "Document", "Workbook", "Presentation".
        if not was_modified and api_ids:
            # Backtick-wrapped identifiers (original)
            backtick_refs = re.findall(r'`([A-Za-z_]\w+)`', claim.text)
            # Unquoted compound PascalCase identifiers (two or more PascalCase segments),
            # e.g. "LoadDocument", "ExcelWorkbook", "PdfSaveOptions".
            # Requires internal uppercase to avoid false positives on common capitalized
            # English words like "Export", "Import", "Create", "Delete".
            pascal_refs = re.findall(r'\b([A-Z][a-z]+[A-Z][A-Za-z0-9]+)\b', claim.text)
            all_refs = dict.fromkeys(backtick_refs + pascal_refs)  # dedup, preserve order
            for ref in all_refs:
                if ref.lower() not in api_ids and len(ref) > 3:
                    claim = claim.model_copy(update={"visibility": "internal"})
                    contradiction_log.append({
                        "claim_id": claim.claim_id,
                        "type": "api_existence",
                        "original_text": claim.text[:200],
                        "resolution": f"downgraded to internal — '{ref}' not in API surface",
                        "evidence": f"api_identifiers does not contain '{ref}'",
                    })
                    was_modified = True
                    break

        # Check 2b: method-call pattern on property-only identifier (TC-HAL-01)
        if not was_modified and property_ids:
            call_refs = re.findall(r'\b([a-zA-Z_]\w+)\s*\(', claim.text)
            for ref in call_refs:
                ref_lower = ref.lower()
                # Only fire if: in property_ids AND NOT in method_ids AND not a builtin-like name
                if (ref_lower in property_ids
                        and ref_lower not in method_ids
                        and len(ref) > 2):
                    claim = claim.model_copy(update={"visibility": "internal"})
                    contradiction_log.append({
                        "claim_id": claim.claim_id,
                        "type": "method_property_mismatch",
                        "original_text": claim.text[:200],
                        "resolution": f"downgraded to internal — '{ref}' is a property, not callable",
                        "evidence": f"property_ids contains '{ref_lower}'; method_ids does not",
                    })
                    was_modified = True
                    break

        # Check 2c: lowercase dot-notation API identifiers for api-kind claims (TC-HAL-02)
        if not was_modified and api_ids and claim.kind == "api":
            dot_refs = re.findall(r'\b\w+\.([a-z_]\w*)\b', claim.text)
            for ref in dot_refs:
                if len(ref) < 3:
                    continue  # skip very short names to avoid false positives
                if ref.lower() not in api_ids:
                    claim = claim.model_copy(update={"visibility": "internal"})
                    contradiction_log.append({
                        "claim_id": claim.claim_id,
                        "type": "unknown_lowercase_api",
                        "original_text": claim.text[:200],
                        "resolution": f"downgraded to internal — '.{ref}' not in API surface",
                        "evidence": f"api_ids does not contain '{ref.lower()}'",
                    })
                    was_modified = True
                    break

        # Check 2d: Enum member verification — ClassName.MEMBER (TC-HAL-03)
        if not was_modified and enum_member_map:
            enum_refs = re.findall(r'\b([A-Z][a-zA-Z0-9]+)\.([A-Z][A-Z0-9_]+)\b', claim.text)
            for cls_name, member_name in enum_refs:
                cls_lower = cls_name.lower()
                if cls_lower not in enum_member_map:
                    continue  # not a known enum class
                if member_name.lower() not in enum_member_map[cls_lower]:
                    claim = claim.model_copy(update={"visibility": "internal"})
                    contradiction_log.append({
                        "claim_id": claim.claim_id,
                        "type": "enum_member_unknown",
                        "original_text": claim.text[:200],
                        "resolution": f"downgraded to internal — '{cls_name}.{member_name}' member not in enum",
                        "evidence": f"enum_member_map['{cls_lower}'] known members: {sorted(list(enum_member_map[cls_lower]))[:5]}",
                    })
                    was_modified = True
                    break

        # Check 3: Limitation override — claim says feature works but limitation says otherwise
        if not was_modified and limitation_features:
            for feat_key, constraint_text in limitation_features.items():
                if feat_key in text_lower and "support" in text_lower:
                    # Claim positively asserts support for a limited feature
                    if not any(neg in text_lower for neg in ("not", "cannot", "doesn't", "limited", "partial")):
                        # Append caveat
                        caveat = f" (Note: {constraint_text})"
                        claim = claim.model_copy(update={"text": claim.text + caveat})
                        contradiction_log.append({
                            "claim_id": claim.claim_id,
                            "type": "limitation_override",
                            "original_text": claim.text[:200],
                            "resolution": f"appended caveat: {caveat}",
                            "evidence": f"LimitationEntry: {feat_key} → {constraint_text}",
                        })
                        was_modified = True
                        break

        resolved.append(claim)

    if contradiction_log:
        logger.info(
            "resolve_contradictions: %d contradictions resolved out of %d claims",
            len(contradiction_log), len(claims),
        )

    return resolved, contradiction_log


def _mentions_export(text: str) -> bool:
    return bool(re.search(
        r'\b(?:export|save|write|output)\b', text, re.IGNORECASE
    ))


def _mentions_import(text: str) -> bool:
    return bool(re.search(
        r'\b(?:import|load|read|open)\b', text, re.IGNORECASE
    ))
