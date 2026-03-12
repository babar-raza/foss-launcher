import pathlib

BASE = pathlib.Path("c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2/publish")

FIXES = {
    "docs.aspose.org/3d/en/python/developer-guide/_index.md": [
        ("](../getting-started/_index.md)", "](/docs.aspose.org/3d/python/getting-started/)"),
        ("](../getting-started/installation.md)", "](/docs.aspose.org/3d/python/getting-started/installation/)"),
    ],
    "docs.aspose.org/3d/en/python/developer-guide/scene-graph.md": [
        ("](../getting-started/installation/)", "](/docs.aspose.org/3d/python/getting-started/installation/)"),
    ],
    "docs.aspose.org/3d/en/python/getting-started/_index.md": [
        ("](../developer-guide/_index.md)", "](/docs.aspose.org/3d/python/developer-guide/)"),
        ("](../developer-guide/features.md)", "](/docs.aspose.org/3d/python/developer-guide/features/)"),
    ],
    "docs.aspose.org/3d/en/python/getting-started/installation.md": [
        ("](../developer-guide/_index.md)", "](/docs.aspose.org/3d/python/developer-guide/)"),
        ("](../developer-guide/features.md)", "](/docs.aspose.org/3d/python/developer-guide/features/)"),
    ],
    "docs.aspose.org/3d/en/python/getting-started/license.md": [
        ("](../installation/)", "](/docs.aspose.org/3d/python/getting-started/installation/)"),
        ("](../../developer-guide/_index.md)", "](/docs.aspose.org/3d/python/developer-guide/)"),
    ],
    "docs.aspose.org/3d/en/typescript/developer-guide/_index.md": [
        ("](../getting-started/_index.md)", "](/docs.aspose.org/3d/typescript/getting-started/)"),
        ("](../getting-started/installation.md)", "](/docs.aspose.org/3d/typescript/getting-started/installation/)"),
    ],
    "docs.aspose.org/3d/en/typescript/developer-guide/format-support.md": [
        ("](./features.md)", "](/docs.aspose.org/3d/typescript/developer-guide/features/)"),
        ("](./scene-graph.md)", "](/docs.aspose.org/3d/typescript/developer-guide/scene-graph/)"),
        ("](../../developer-guide/scene-graph.md)", "](/kb.aspose.org/3d/typescript/how-to-build-mesh-programmatically-in-typescript/)"),
    ],
    "docs.aspose.org/3d/en/typescript/developer-guide/model-loading.md": [
        ("](../scene-graph/)", "](/docs.aspose.org/3d/typescript/developer-guide/rendering/)"),
    ],
    "docs.aspose.org/3d/en/typescript/developer-guide/scene-graph.md": [
        ("](./features.md)", "](/docs.aspose.org/3d/typescript/developer-guide/features/)"),
        ("](./format-support.md)", "](/docs.aspose.org/3d/typescript/developer-guide/format-support/)"),
        ("](../../developer-guide/scene-graph.md)", "](/kb.aspose.org/3d/typescript/how-to-build-mesh-programmatically-in-typescript/)"),
    ],
    "docs.aspose.org/3d/en/typescript/getting-started/installation.md": [
        ("](../developer-guide/_index.md)", "](/docs.aspose.org/3d/typescript/developer-guide/)"),
        ("](../developer-guide/features.md)", "](/docs.aspose.org/3d/typescript/developer-guide/features/)"),
    ],
    "docs.aspose.org/3d/en/typescript/getting-started/license.md": [
        ("](../installation/)", "](/docs.aspose.org/3d/typescript/getting-started/installation/)"),
        ("](../../developer-guide/_index.md)", "](/docs.aspose.org/3d/typescript/developer-guide/)"),
    ],
    "docs.aspose.org/cells/en/python/developer-guide/_index.md": [
        ("](../getting-started/)", "](/docs.aspose.org/cells/python/getting-started/)"),
    ],
    "docs.aspose.org/cells/en/python/getting-started/_index.md": [
        ("](../developer-guide/)", "](/docs.aspose.org/cells/python/developer-guide/)"),
    ],
    "docs.aspose.org/cells/en/python/getting-started/license.md": [
        ("](../installation/)", "](/docs.aspose.org/cells/python/getting-started/installation/)"),
        ("](../../developer-guide/_index.md)", "](/docs.aspose.org/cells/python/developer-guide/)"),
    ],
    "docs.aspose.org/note/en/python/developer-guide/_index.md": [
        ("](../getting-started/)", "](/docs.aspose.org/note/python/getting-started/)"),
        ("](../getting-started/installation/)", "](/docs.aspose.org/note/python/getting-started/installation/)"),
    ],
    "docs.aspose.org/note/en/python/getting-started/_index.md": [
        ("](../developer-guide/)", "](/docs.aspose.org/note/python/developer-guide/)"),
        ("](../developer-guide/features/)", "](/docs.aspose.org/note/python/developer-guide/features/)"),
    ],
    "docs.aspose.org/note/en/python/getting-started/installation.md": [
        ("](../developer-guide/)", "](/docs.aspose.org/note/python/developer-guide/)"),
    ],
    "docs.aspose.org/note/en/python/getting-started/license.md": [
        ("](../)", "](/docs.aspose.org/note/python/getting-started/)"),
    ],
    "docs.aspose.org/slides/en/python/developer-guide/_index.md": [
        ("](./features/)", "](/docs.aspose.org/slides/python/developer-guide/features/)"),
        ("](../getting-started/)", "](/docs.aspose.org/slides/python/getting-started/)"),
    ],
    "docs.aspose.org/slides/en/python/developer-guide/features.md": [
        ("](../getting-started/)", "](/docs.aspose.org/slides/python/getting-started/)"),
    ],
    "docs.aspose.org/slides/en/python/getting-started/_index.md": [
        ("](./installation/)", "](/docs.aspose.org/slides/python/getting-started/installation/)"),
        ("](./license/)", "](/docs.aspose.org/slides/python/getting-started/license/)"),
        ("](../developer-guide/)", "](/docs.aspose.org/slides/python/developer-guide/)"),
    ],
    "docs.aspose.org/slides/en/python/getting-started/license.md": [
        ("](../installation/)", "](/docs.aspose.org/slides/python/getting-started/installation/)"),
        ("](../../developer-guide/)", "](/docs.aspose.org/slides/python/developer-guide/)"),
    ],
    "kb.aspose.org/3d/en/typescript/how-to-build-mesh-programmatically-in-typescript.md": [
        ("](./how-to-traverse-scene-graph-in-typescript.md)", "](/kb.aspose.org/3d/typescript/how-to-traverse-scene-graph-in-typescript/)"),
        ("](./how-to-export-gltf-in-typescript.md)", "](/kb.aspose.org/3d/typescript/how-to-export-gltf-in-typescript/)"),
        ("](../../docs.aspose.net/3d/typescript/developer-guide/scene-graph/)", "](/docs.aspose.org/3d/typescript/developer-guide/scene-graph/)"),
    ],
    "kb.aspose.org/3d/en/typescript/how-to-export-gltf-in-typescript.md": [
        ("](../how-to-load-3d-models-in-typescript/)", "](/kb.aspose.org/3d/typescript/how-to-load-3d-models-in-typescript/)"),
    ],
    "kb.aspose.org/3d/en/typescript/how-to-load-3d-models-in-typescript.md": [
        ("](../how-to-export-gltf-in-typescript/)", "](/kb.aspose.org/3d/typescript/how-to-export-gltf-in-typescript/)"),
    ],
    "kb.aspose.org/3d/en/typescript/how-to-traverse-scene-graph-in-typescript.md": [
        ("](./how-to-load-3d-models-in-typescript.md)", "](/kb.aspose.org/3d/typescript/how-to-load-3d-models-in-typescript/)"),
        ("](./how-to-build-mesh-programmatically-in-typescript.md)", "](/kb.aspose.org/3d/typescript/how-to-build-mesh-programmatically-in-typescript/)"),
        ("](../../developer-guide/scene-graph/)", "](/docs.aspose.org/3d/typescript/developer-guide/scene-graph/)"),
    ],
    "kb.aspose.org/slides/en/python/_index.md": [
        ("](./how-to-create-presentations-python/)", "](/kb.aspose.org/slides/python/how-to-create-presentations-python/)"),
        ("](./how-to-load-presentations-python/)", "](/kb.aspose.org/slides/python/how-to-load-presentations-python/)"),
        ("](./how-to-save-presentations-python/)", "](/kb.aspose.org/slides/python/how-to-save-presentations-python/)"),
        ("](./how-to-add-shapes-python/)", "](/kb.aspose.org/slides/python/how-to-add-shapes-python/)"),
        ("](./how-to-format-text-python/)", "](/kb.aspose.org/slides/python/how-to-format-text-python/)"),
        ("](./how-to-work-with-tables-python/)", "](/kb.aspose.org/slides/python/how-to-work-with-tables-python/)"),
        ("](./faq/)", "](/kb.aspose.org/slides/python/faq/)"),
    ],
    "reference.aspose.org/note/en/python/document.md": [
        ("](../_index/#loadoptions)", "](/reference.aspose.org/note/python/#loadoptions)"),
        ("](../_index/#pdfsaveoptions)", "](/reference.aspose.org/note/python/#pdfsaveoptions)"),
        ("](../_index/#documentvisitor)", "](/reference.aspose.org/note/python/#documentvisitor)"),
    ],
    "reference.aspose.org/note/en/python/image.md": [
        ("](../_index/#attachedfile)", "](/reference.aspose.org/note/python/#attachedfile)"),
        ("](../_index/#notetag)", "](/reference.aspose.org/note/python/#notetag)"),
    ],
    "reference.aspose.org/note/en/python/page.md": [
        ("](../_index/#title)", "](/reference.aspose.org/note/python/#title)"),
        ("](../_index/#outline)", "](/reference.aspose.org/note/python/#outline)"),
    ],
    "reference.aspose.org/note/en/python/richtext.md": [
        ("](../_index/#textrun)", "](/reference.aspose.org/note/python/#textrun)"),
        ("](../_index/#textstyle)", "](/reference.aspose.org/note/python/#textstyle)"),
        ("](../_index/#notetag)", "](/reference.aspose.org/note/python/#notetag)"),
    ],
}

changed = 0
for rel_path, replacements in FIXES.items():
    fpath = BASE / rel_path
    if not fpath.exists():
        print(f"MISSING: {rel_path}")
        continue
    text = fpath.read_text(encoding="utf-8")
    original = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text != original:
        fpath.write_text(text, encoding="utf-8")
        print(f"FIXED:   {rel_path}")
        changed += 1
    else:
        print(f"NOOP:    {rel_path}")

print(f"\nTotal files changed: {changed}")
