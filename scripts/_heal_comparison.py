"""TC-HEAL pilot comparison script.

Shows:
1. TC-HEAL-005: Keywords in deployed 3D DotNet frontmatter that would be rejected by the new filter
2. TC-HEAL-006: Import rule before/after for aspose_email_foss
"""
from __future__ import annotations
import re
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# --------------------------------------------------------------------------
# TC-HEAL-005: SEO keyword filter on deployed 3D DotNet frontmatter
# --------------------------------------------------------------------------
kw_pattern = re.compile(r"^keywords:\s*\[(.+)\]", re.MULTILINE)
all_kws: list[tuple[str, str]] = []

# Walk deploy/ for 3D DotNet pages
deploy_base = os.path.join(os.path.dirname(__file__), "..", "deploy")
for root, dirs, files in os.walk(deploy_base):
    norm = root.replace("\\", "/")
    if "/3d/" in norm and "/dotnet" in norm:
        for fname in files:
            if fname.endswith(".md"):
                fpath = os.path.join(root, fname)
                try:
                    txt = open(fpath, encoding="utf-8").read()
                except Exception:
                    continue
                m = kw_pattern.search(txt)
                if m:
                    raw = m.group(1)
                    kws = [k.strip().strip('"').strip("'") for k in raw.split(",")]
                    for k in kws:
                        k = k.strip()
                        if k:
                            all_kws.append((k, fname))

from launcher.workers.generate.seo_metadata import _is_irrelevant_keyword  # noqa

print("=" * 70)
print("TC-HEAL-005: SEO keyword filter — deployed 3D DotNet frontmatter")
print("=" * 70)

rejected = [(k, f) for k, f in all_kws if _is_irrelevant_keyword(k)]
accepted = [(k, f) for k, f in all_kws if not _is_irrelevant_keyword(k)]

print(f"\nTotal keywords scanned : {len(all_kws)}")
print(f"REJECTED by new filter : {len(rejected)}")
print(f"ACCEPTED (kept)        : {len(accepted)}")

if rejected:
    print("\n--- REJECTED (would no longer appear in frontmatter) ---")
    for k, f in sorted(set(rejected)):
        reason = "question" if re.match(r"^\s*(is|are|can|how|what|why|when|where|which|does|do|did)\s", k, re.IGNORECASE) else \
                 "cost/comparison" if re.search(r"\b(cost|price|pricing|versus|alternative|symptoms?)\b", k, re.IGNORECASE) else \
                 "vs-shorthand" if re.search(r"\bvs\s", k, re.IGNORECASE) else \
                 "diff-between"
        print(f"  [{reason:14}] {k!r:<50} [{f}]")

if accepted:
    print("\n--- ACCEPTED SAMPLE (product-relevant, kept) ---")
    for k, f in sorted(set(accepted))[:20]:
        print(f"  {k!r}")

# --------------------------------------------------------------------------
# TC-HEAL-006: Import rule before/after
# --------------------------------------------------------------------------
print()
print("=" * 70)
print("TC-HEAL-006: Import rule block for aspose_email_foss")
print("=" * 70)

from launcher.workers.generate.section_prompt import _build_import_rule_block  # noqa

rule = _build_import_rule_block("python", "aspose_email_foss")
print("\nFULL RULE OUTPUT:")
print(rule)

print("\nKey assertions:")
print(f"  Contains 'aspose_email_foss' : {'aspose_email_foss' in rule}")
print(f"  Contains 'aspose.email'      : {'aspose.email' in rule}")
print(f"  Contains 'NEVER'             : {'NEVER' in rule}")
print(f"  Contains 'ImportError'       : {'ImportError' in rule}")
