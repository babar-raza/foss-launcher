"""Regenerate .md files from snapshots/ PageIR store.

Zero-LLM regeneration: walks snapshots/ for *.ir.json files,
renders each via ir_renderer.render_page(), writes .md to output_dir.

Path invariant:
    snapshots_dir / (content_path + ".ir.json")
        → output_dir / (content_path + ".md")

The relative path (content_path) is preserved exactly — no flattening,
no restructuring.  output_dir is typically deploy/ for a full rebuild
or regen/ for a dry-run staging area.

TC-3906 / TC-3911 (double-suffix fix)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from launcher.io.atomic import atomic_write_text
from launcher.models.page_ir import PageIR
from launcher.shared.ir_renderer import render_page
from launcher.util.errors import FrontmatterError

logger = logging.getLogger(__name__)


def regenerate_from_snapshots(
    snapshots_dir: Path,
    output_dir: Path,
) -> list[Path]:
    """Render all IR files in snapshots/ to .md in output_dir.

    Walks snapshots_dir recursively for *.ir.json files.  For each file,
    deserialises the PageIR, calls render_page(), and writes the markdown
    to the corresponding path under output_dir (extension swapped to .md).

    The glob pattern rglob("*.ir.json") already excludes snapshot_manifest.json
    (which has a plain .json extension), so no additional name filter is needed.

    Path transform: slug.ir.json → slug.md (both suffixes stripped, .md added).

    One bad IR file does not abort the run — errors are logged per-page
    and that page is skipped.

    Args:
        snapshots_dir: Root of the snapshots/ store (e.g. Path("snapshots")).
        output_dir: Root to write .md files into (e.g. Path("deploy") or
            Path("regen")).  May be the same directory layout as deploy/.

    Returns:
        List of .md paths that were successfully written.
    """
    if not snapshots_dir.is_dir():
        logger.warning("snapshots_dir does not exist: %s", snapshots_dir)
        return []

    written: list[Path] = []

    for ir_file in sorted(snapshots_dir.rglob("*.ir.json")):
        rel = ir_file.relative_to(snapshots_dir)
        # Strip both suffixes (.ir.json → .ir → base) then add .md.
        # rel.with_suffix("") removes .json → slug.ir; again removes .ir → slug.
        dest = output_dir / rel.with_suffix("").with_suffix(".md")

        try:
            raw = json.loads(ir_file.read_text(encoding="utf-8"))
            page_ir = PageIR.model_validate(raw)
        except Exception:
            logger.error(
                "Failed to load/parse IR file %s — skipping", ir_file, exc_info=True
            )
            continue

        try:
            md_text = render_page(page_ir)
        except FrontmatterError:
            logger.error(
                "FrontmatterError rendering %s — skipping", ir_file, exc_info=True
            )
            continue
        except Exception:
            logger.error(
                "Unexpected error rendering %s — skipping", ir_file, exc_info=True
            )
            continue

        try:
            atomic_write_text(dest, md_text, validate_boundary=output_dir)
            written.append(dest)
            logger.debug("Regenerated %s", dest)
        except Exception:
            logger.error(
                "Failed to write %s — skipping", dest, exc_info=True
            )
            continue

    logger.info(
        "ir_regenerate: wrote %d .md file(s) from %s → %s",
        len(written), snapshots_dir, output_dir,
    )
    return written
