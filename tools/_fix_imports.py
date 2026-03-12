"""Fix wrong aspose.cells imports across publish/ directory."""
import os

publish = r"c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher-v2\publish"
fixed = 0

for root, dirs, files in os.walk(publish):
    for fname in files:
        if not fname.endswith(".md"):
            continue
        path = os.path.join(root, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        new = content.replace("from aspose.cells import", "from aspose_cells import")
        new = new.replace("import aspose.cells", "import aspose_cells")
        if new != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            fixed += 1
            print(f"Fixed: {os.path.relpath(path, publish)}")

print(f"\nTotal fixed this pass: {fixed}")
