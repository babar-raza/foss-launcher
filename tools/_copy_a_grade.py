"""Copy A-grade files from deploy/ to publish/ with /en/ inserted after family name."""
import shutil, os

BASE = r"c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher-v2"
SRC = os.path.join(BASE, "deploy")
DST = os.path.join(BASE, "publish")

FILES = [
    # blog/3d
    ("blog.aspose.org/3d/python/introducing-aspose-3d-foss-for-python/index.md",
     "blog.aspose.org/3d/en/python/introducing-aspose-3d-foss-for-python/index.md"),
    ("blog.aspose.org/3d/python/working-with-3d-formats-in-python/index.md",
     "blog.aspose.org/3d/en/python/working-with-3d-formats-in-python/index.md"),
    ("blog.aspose.org/3d/typescript/introducing-aspose-3d-foss-for-typescript/index.md",
     "blog.aspose.org/3d/en/typescript/introducing-aspose-3d-foss-for-typescript/index.md"),
    ("blog.aspose.org/3d/typescript/working-with-3d-formats-in-typescript/index.md",
     "blog.aspose.org/3d/en/typescript/working-with-3d-formats-in-typescript/index.md"),
    # blog/cells
    ("blog.aspose.org/cells/python/python-excel-chart-tutorial/index.md",
     "blog.aspose.org/cells/en/python/python-excel-chart-tutorial/index.md"),
    # blog/note
    ("blog.aspose.org/note/python/extract-text-onenote-python/index.md",
     "blog.aspose.org/note/en/python/extract-text-onenote-python/index.md"),
    ("blog.aspose.org/note/python/introducing-aspose-note-foss-for-python/index.md",
     "blog.aspose.org/note/en/python/introducing-aspose-note-foss-for-python/index.md"),
    ("blog.aspose.org/note/python/parse-onenote-tables-python/index.md",
     "blog.aspose.org/note/en/python/parse-onenote-tables-python/index.md"),
    # docs/3d/python
    ("docs.aspose.org/3d/python/developer-guide/_index.md",
     "docs.aspose.org/3d/en/python/developer-guide/_index.md"),
    ("docs.aspose.org/3d/python/developer-guide/features.md",
     "docs.aspose.org/3d/en/python/developer-guide/features.md"),
    ("docs.aspose.org/3d/python/developer-guide/format-support.md",
     "docs.aspose.org/3d/en/python/developer-guide/format-support.md"),
    ("docs.aspose.org/3d/python/developer-guide/scene-graph.md",
     "docs.aspose.org/3d/en/python/developer-guide/scene-graph.md"),
    ("docs.aspose.org/3d/python/getting-started/_index.md",
     "docs.aspose.org/3d/en/python/getting-started/_index.md"),
    ("docs.aspose.org/3d/python/getting-started/installation.md",
     "docs.aspose.org/3d/en/python/getting-started/installation.md"),
    ("docs.aspose.org/3d/python/getting-started/license.md",
     "docs.aspose.org/3d/en/python/getting-started/license.md"),
    # docs/3d/typescript
    ("docs.aspose.org/3d/typescript/developer-guide/_index.md",
     "docs.aspose.org/3d/en/typescript/developer-guide/_index.md"),
    ("docs.aspose.org/3d/typescript/developer-guide/features.md",
     "docs.aspose.org/3d/en/typescript/developer-guide/features.md"),
    ("docs.aspose.org/3d/typescript/developer-guide/format-support.md",
     "docs.aspose.org/3d/en/typescript/developer-guide/format-support.md"),
    ("docs.aspose.org/3d/typescript/developer-guide/scene-graph.md",
     "docs.aspose.org/3d/en/typescript/developer-guide/scene-graph.md"),
    ("docs.aspose.org/3d/typescript/getting-started/installation.md",
     "docs.aspose.org/3d/en/typescript/getting-started/installation.md"),
    ("docs.aspose.org/3d/typescript/getting-started/license.md",
     "docs.aspose.org/3d/en/typescript/getting-started/license.md"),
    # docs/cells/python
    ("docs.aspose.org/cells/python/developer-guide/_index.md",
     "docs.aspose.org/cells/en/python/developer-guide/_index.md"),
    ("docs.aspose.org/cells/python/developer-guide/features.md",
     "docs.aspose.org/cells/en/python/developer-guide/features.md"),
    ("docs.aspose.org/cells/python/developer-guide/working-with-cells.md",
     "docs.aspose.org/cells/en/python/developer-guide/working-with-cells.md"),
    ("docs.aspose.org/cells/python/developer-guide/working-with-charts.md",
     "docs.aspose.org/cells/en/python/developer-guide/working-with-charts.md"),
    ("docs.aspose.org/cells/python/developer-guide/working-with-formulas.md",
     "docs.aspose.org/cells/en/python/developer-guide/working-with-formulas.md"),
    ("docs.aspose.org/cells/python/getting-started/_index.md",
     "docs.aspose.org/cells/en/python/getting-started/_index.md"),
    ("docs.aspose.org/cells/python/getting-started/installation.md",
     "docs.aspose.org/cells/en/python/getting-started/installation.md"),
    # docs/note/python
    ("docs.aspose.org/note/python/developer-guide/_index.md",
     "docs.aspose.org/note/en/python/developer-guide/_index.md"),
    ("docs.aspose.org/note/python/developer-guide/features.md",
     "docs.aspose.org/note/en/python/developer-guide/features.md"),
    ("docs.aspose.org/note/python/developer-guide/images-and-attachments.md",
     "docs.aspose.org/note/en/python/developer-guide/images-and-attachments.md"),
    ("docs.aspose.org/note/python/developer-guide/pdf-export.md",
     "docs.aspose.org/note/en/python/developer-guide/pdf-export.md"),
    ("docs.aspose.org/note/python/developer-guide/tables.md",
     "docs.aspose.org/note/en/python/developer-guide/tables.md"),
    ("docs.aspose.org/note/python/developer-guide/text-extraction.md",
     "docs.aspose.org/note/en/python/developer-guide/text-extraction.md"),
    ("docs.aspose.org/note/python/getting-started/_index.md",
     "docs.aspose.org/note/en/python/getting-started/_index.md"),
    ("docs.aspose.org/note/python/getting-started/installation.md",
     "docs.aspose.org/note/en/python/getting-started/installation.md"),
    ("docs.aspose.org/note/python/getting-started/license.md",
     "docs.aspose.org/note/en/python/getting-started/license.md"),
    # kb/3d/python
    ("kb.aspose.org/3d/python/how-to-load-3d-models-in-python.md",
     "kb.aspose.org/3d/en/python/how-to-load-3d-models-in-python.md"),
    ("kb.aspose.org/3d/python/how-to-convert-3d-models-in-python.md",
     "kb.aspose.org/3d/en/python/how-to-convert-3d-models-in-python.md"),
    ("kb.aspose.org/3d/python/how-to-build-mesh-programmatically-in-python.md",
     "kb.aspose.org/3d/en/python/how-to-build-mesh-programmatically-in-python.md"),
    ("kb.aspose.org/3d/python/how-to-traverse-scene-graph-in-python.md",
     "kb.aspose.org/3d/en/python/how-to-traverse-scene-graph-in-python.md"),
    # kb/3d/typescript
    ("kb.aspose.org/3d/typescript/_index.md",
     "kb.aspose.org/3d/en/typescript/_index.md"),
    ("kb.aspose.org/3d/typescript/how-to-load-3d-models-in-typescript.md",
     "kb.aspose.org/3d/en/typescript/how-to-load-3d-models-in-typescript.md"),
    ("kb.aspose.org/3d/typescript/how-to-export-gltf-in-typescript.md",
     "kb.aspose.org/3d/en/typescript/how-to-export-gltf-in-typescript.md"),
    ("kb.aspose.org/3d/typescript/how-to-build-mesh-programmatically-in-typescript.md",
     "kb.aspose.org/3d/en/typescript/how-to-build-mesh-programmatically-in-typescript.md"),
    ("kb.aspose.org/3d/typescript/how-to-traverse-scene-graph-in-typescript.md",
     "kb.aspose.org/3d/en/typescript/how-to-traverse-scene-graph-in-typescript.md"),
    # kb/cells/python
    ("kb.aspose.org/cells/python/_index.md",
     "kb.aspose.org/cells/en/python/_index.md"),
    ("kb.aspose.org/cells/python/how-to-create-charts-python.md",
     "kb.aspose.org/cells/en/python/how-to-create-charts-python.md"),
    ("kb.aspose.org/cells/python/how-to-convert-excel-to-pdf-python.md",
     "kb.aspose.org/cells/en/python/how-to-convert-excel-to-pdf-python.md"),
    ("kb.aspose.org/cells/python/how-to-style-cells-python.md",
     "kb.aspose.org/cells/en/python/how-to-style-cells-python.md"),
    # kb/note/python
    ("kb.aspose.org/note/python/_index.md",
     "kb.aspose.org/note/en/python/_index.md"),
    ("kb.aspose.org/note/python/how-to-extract-text-from-onenote-python.md",
     "kb.aspose.org/note/en/python/how-to-extract-text-from-onenote-python.md"),
    ("kb.aspose.org/note/python/how-to-export-onenote-to-pdf-python.md",
     "kb.aspose.org/note/en/python/how-to-export-onenote-to-pdf-python.md"),
    ("kb.aspose.org/note/python/how-to-inspect-tags-onenote-python.md",
     "kb.aspose.org/note/en/python/how-to-inspect-tags-onenote-python.md"),
    ("kb.aspose.org/note/python/how-to-parse-tables-onenote-python.md",
     "kb.aspose.org/note/en/python/how-to-parse-tables-onenote-python.md"),
    ("kb.aspose.org/note/python/how-to-traverse-dom-onenote-python.md",
     "kb.aspose.org/note/en/python/how-to-traverse-dom-onenote-python.md"),
    # products
    ("products.aspose.org/3d/python/_index.md",
     "products.aspose.org/3d/en/python/_index.md"),
    ("products.aspose.org/cells/python/_index.md",
     "products.aspose.org/cells/en/python/_index.md"),
    # reference
    ("reference.aspose.org/3d/python/_index.md",
     "reference.aspose.org/3d/en/python/_index.md"),
    ("reference.aspose.org/3d/typescript/_index.md",
     "reference.aspose.org/3d/en/typescript/_index.md"),
    ("reference.aspose.org/note/python/_index.md",
     "reference.aspose.org/note/en/python/_index.md"),
    ("reference.aspose.org/note/python/document.md",
     "reference.aspose.org/note/en/python/document.md"),
]

count = 0
for rel_src, rel_dst in FILES:
    src = os.path.join(SRC, *rel_src.split("/"))
    dst = os.path.join(DST, *rel_dst.split("/"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    count += 1

print(f"Copied {count} A-grade files to publish/")
