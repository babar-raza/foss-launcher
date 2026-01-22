from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "reports" / "forensics"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Tree
    tree_path = OUT_DIR / "tree.txt"
    # Use os.walk for portability; hide extremely noisy dirs.
    skip = {".git", "__pycache__", ".pytest_cache", "runs"}
    lines = []
    for root, dirs, files in os.walk(REPO_ROOT):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if d not in skip]
        rel_root = root_path.relative_to(REPO_ROOT)
        indent = "  " * len(rel_root.parts)
        if rel_root == Path("."):
            lines.append(".")
        else:
            lines.append(f"{indent}{rel_root}/")
        for f in sorted(files):
            lines.append(f"{indent}  {f}")
    tree_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Catalog
    catalog_path = OUT_DIR / "file_catalog.tsv"
    with catalog_path.open("w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp, delimiter="\t")
        w.writerow(["path", "bytes", "mtime_epoch", "sha256"])
        for path in sorted(REPO_ROOT.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(REPO_ROOT)
            if rel.parts and rel.parts[0] in skip:
                continue
            st = path.stat()
            w.writerow([str(rel), st.st_size, int(st.st_mtime), sha256_file(path)])

    print(f"Wrote: {tree_path}")
    print(f"Wrote: {catalog_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
