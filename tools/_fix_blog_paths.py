"""Move blog files from /family/en/lang/ back to /family/lang/ (no /en/ on blog)."""
import os, shutil

blog = r"c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher-v2\publish\blog.aspose.org"

moved = 0
for root, dirs, files in os.walk(blog, topdown=False):
    for fname in files:
        src = os.path.join(root, fname)
        rel = os.path.relpath(src, blog)          # e.g. 3d\en\python\foo.md
        parts = rel.split(os.sep)
        if len(parts) >= 2 and parts[1] == "en":  # family/en/...
            new_parts = [parts[0]] + parts[2:]    # drop "en"
            dst = os.path.join(blog, *new_parts)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            print(f"  {rel}  ->  {os.path.relpath(dst, blog)}")
            moved += 1

# Remove now-empty /en/ dirs
for family in os.listdir(blog):
    en_dir = os.path.join(blog, family, "en")
    if os.path.isdir(en_dir):
        shutil.rmtree(en_dir)
        print(f"Removed empty dir: {os.path.relpath(en_dir, blog)}")

print(f"\nMoved {moved} files.")
