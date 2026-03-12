"""Check directive compliance in generated content (SR-06)."""
import json
import re
from pathlib import Path

run_dir = Path("runs/r_20260306T212616_82a6540e")
pages_dir = run_dir / "content_bundle" / "pages"

results = {"total_sections": 0, "compliant": 0, "issues": []}

for md_file in sorted(pages_dir.rglob("*.md")):
    content = md_file.read_text(encoding="utf-8", errors="replace")
    h2s = re.findall(r"^## (.+)$", content, re.MULTILINE)

    # Duplicate H2 check
    seen = {}
    for h in h2s:
        key = h.lower().strip()
        seen[key] = seen.get(key, 0) + 1
    for h, c in seen.items():
        if c > 1:
            results["issues"].append(f"DUPLICATE H2: '{h}' x{c} in {md_file.name}")

    results["total_sections"] += len(h2s)

    for h in h2s:
        hl = h.lower().strip()

        if hl in ("frequently asked questions", "faq"):
            h3s = re.findall(r"^### (.+)$", content, re.MULTILINE)
            if h3s:
                results["compliant"] += 1
            else:
                results["issues"].append(f"FAQ without H3 Q&A in {md_file.name}")

        elif hl in ("key features", "key highlights"):
            if re.search(r"^- .+", content, re.MULTILINE):
                results["compliant"] += 1
            else:
                results["issues"].append(f"{h} without bullet list in {md_file.name}")

        elif hl == "see also":
            idx = content.lower().find("## see also")
            if idx >= 0:
                section = content[idx:]
                if re.search(r"\[.+?\]\(.+?\)", section):
                    results["compliant"] += 1
                else:
                    results["issues"].append(f"See Also without links in {md_file.name}")
            else:
                results["compliant"] += 1

        elif hl in ("code example", "code examples", "code samples", "complete code example", "quick start"):
            if "```" in content:
                results["compliant"] += 1
            else:
                results["issues"].append(f"{h} without code block in {md_file.name}")

        elif hl in ("constructors", "properties", "methods"):
            if "|" in content:
                results["compliant"] += 1
            else:
                results["issues"].append(f"{h} without table in {md_file.name}")

        elif hl in ("steps", "solution steps", "step-by-step guide"):
            h3s_after = re.findall(r"^### (.+)$", content, re.MULTILINE)
            if h3s_after:
                results["compliant"] += 1
            else:
                results["issues"].append(f"{h} without H3 steps in {md_file.name}")

        else:
            results["compliant"] += 1

total = results["total_sections"]
comp = results["compliant"]
rate = comp / total * 100 if total else 0
print(f"Total sections: {total}")
print(f"Compliant: {comp}")
print(f"Compliance rate: {rate:.1f}%")
print(f"Issues: {len(results['issues'])}")
for issue in results["issues"]:
    print(f"  - {issue}")

# Also check for "No directive" warnings in the run
print("\n--- Checking for missing directive warnings ---")
import subprocess
result = subprocess.run(
    ["grep", "-r", "No directive for heading", str(run_dir / "evidence")],
    capture_output=True, text=True,
)
if result.stdout.strip():
    print(result.stdout)
else:
    print("No missing directive warnings found in evidence.")
