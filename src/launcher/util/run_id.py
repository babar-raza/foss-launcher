from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _sanitize_slug(value: str, max_len: int = 16) -> str:
    """Lowercase, strip 'aspose-' prefix, replace non-alnum with '-', truncate.

    The ``aspose-`` prefix is stripped because all products share it — it adds
    no discriminating information but costs 7 chars.
    """
    s = value.lower()
    if s.startswith("aspose-"):
        s = s[7:]
    s = re.sub(r"[^a-z0-9]", "-", s).strip("-")
    result = s[:max_len]  # 16 chars max keeps worst-case run_id under 50 chars
    if not result:
        raise ValueError(
            f"Slug sanitization produced empty string for input: {value!r}"
        )
    return result


def generate_run_id(family: str, platform: str) -> str:
    """Generate a date-sortable run ID that includes family and platform.

    Format: ``YYMMDD_HHMMSS_{family}_{platform}_{hex4}``

    Example: ``260307_082430_cells_python_a3f1``

    Design rationale:

    - **Date-first** so directories sort chronologically in file explorers.
    - **Family + platform** visible at a glance for identification.
    - **4-char hex suffix** (``os.urandom(2)``) provides ~65K unique IDs per
      second per family+platform, eliminating same-second collision risk for
      parallel batch runs.  Call sites still guard against the astronomically
      unlikely collision via a retry loop.
    - **Total length ~35 chars** — well within Windows MAX_PATH (260) when
      combined with deep ``content_bundle/`` paths (longest observed: ~200
      chars at the run-dir level).
    """
    now = datetime.now(timezone.utc)
    date = now.strftime("%y%m%d")
    time_part = now.strftime("%H%M%S")
    fam = _sanitize_slug(family)
    plat = _sanitize_slug(platform)
    if fam != family.lower():
        logger.debug("Sanitized family %r -> %r", family, fam)
    if plat != platform.lower():
        logger.debug("Sanitized platform %r -> %r", platform, plat)
    suffix = os.urandom(2).hex()
    return f"{date}_{time_part}_{fam}_{plat}_{suffix}"
