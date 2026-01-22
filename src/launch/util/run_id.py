from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from ..io.hashing import sha256_bytes


def stable_config_hash8(run_config: Dict[str, Any]) -> str:
    # Stable serialization: JSON with sorted keys, no whitespace variability.
    import json

    raw = json.dumps(run_config, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(raw)[:8]


def make_run_id(product_slug: str, github_ref: str, site_ref: str, run_config: Dict[str, Any]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    gh = github_ref[:7]
    site = site_ref[:7]
    h8 = stable_config_hash8(run_config)
    return f"r_{ts}_launch_{product_slug}_{gh}_{site}_{h8}"
