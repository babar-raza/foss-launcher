import json, os, sys

base = "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/runs/r_20260213T133232Z_launch_pilot-aspose-3d-foss-python_3711472_default_5e3e97b1/artifacts"

with open(os.path.join(base, "product_facts.json"), "r", encoding="utf-8") as f:
    pf = json.load(f)

with open(os.path.join(base, "code_understanding.json"), "r", encoding="utf-8") as f:
    cu = json.load(f)

with open(os.path.join(base, "repo_inventory.json"), "r", encoding="utf-8") as f:
    ri = json.load(f)

with open(os.path.join(base, "evidence_map.json"), "r", encoding="utf-8") as f:
    em = json.load(f)

print("=" * 70)
print("PRODUCT_FACTS.JSON — FIELD-BY-FIELD AUDIT")
print("=" * 70)

# Top-level fields
print("\n--- TOP-LEVEL FIELDS ---")
for key in sorted(pf.keys()):
    val = pf[key]
    if isinstance(val, str):
        print(f"  {key}: {repr(val[:100])}" + ("..." if len(val) > 100 else ""))
    elif isinstance(val, list):
        print(f"  {key}: list[{len(val)}]")
    elif isinstance(val, dict):
        print(f"  {key}: dict with keys {sorted(val.keys())[:10]}")
    else:
        print(f"  {key}: {type(val).__name__} = {val}")

# Claims by kind
print("\n--- CLAIMS BY KIND ---")
from collections import Counter
kinds = Counter(c.get("claim_kind", "unknown") for c in pf.get("claims", []))
for kind, count in sorted(kinds.items(), key=lambda x: -x[1]):
    print(f"  {kind}: {count}")

# Claim groups
print("\n--- CLAIM GROUPS ---")
cg = pf.get("claim_groups", {})
for group, ids in sorted(cg.items()):
    print(f"  {group}: {len(ids)} claims")
    # Show first 2 claim texts
    for cid in ids[:2]:
        claim = next((c for c in pf["claims"] if c["claim_id"] == cid), None)
        if claim:
            print(f"    -> {claim['claim_text'][:80]}")

# Positioning
print("\n--- POSITIONING ---")
pos = pf.get("positioning", {})
for k, v in sorted(pos.items()):
    print(f"  {k}: {repr(str(v)[:100])}")

# Workflows detail
print("\n--- WORKFLOWS ---")
for w in pf.get("workflows", []):
    print(f"  {w['name']}:")
    print(f"    steps: {len(w.get('steps', []))}")
    print(f"    source: {w.get('source', 'claim-based')}")
    for s in w.get("steps", [])[:3]:
        code = s.get("code", "")
        print(f"    step {s.get('step_num', '?')}: {s.get('name', '?')[:50]} {'[has code]' if code else '[no code]'}")

# Supported formats
print("\n--- SUPPORTED FORMATS ---")
for fmt in pf.get("supported_formats", []):
    print(f"  {fmt['format']}: direction={fmt['direction']}, claims={len(fmt.get('claim_ids', []))}")

# Feature profiles detail
print("\n--- FEATURE PROFILES ---")
for fp in pf.get("feature_profiles", []):
    print(f"  {fp.get('feature_id', '?')} ({fp.get('name', '?')}):")
    print(f"    topic: {fp.get('topic', '?')}")
    print(f"    claims: {len(fp.get('claim_ids', []))}")
    print(f"    summary: {fp.get('summary', '')[:80]}")
    print(f"    capabilities: {len(fp.get('capabilities', []))}")
    print(f"    limitations: {len(fp.get('limitations', []))}")
    print(f"    code_example: {bool(fp.get('code_example', ''))}")

# Example inventory
print("\n--- EXAMPLE INVENTORY ---")
examples = pf.get("example_inventory", [])
print(f"  Total: {len(examples)}")
for e in examples[:5]:
    code_len = len(e.get("code", ""))
    print(f"  {e['example_id']}: {e.get('title', '?')[:50]} ({code_len} chars)")
print(f"  ... and {max(0, len(examples)-5)} more")

# Compatibility
print("\n--- COMPATIBILITY ---")
print(f"  compatibility_notes: {pf.get('compatibility_notes', [])}")
print(f"  supported_platforms: {pf.get('supported_platforms', [])}")

# API surface
print("\n--- API SURFACE SUMMARY ---")
api = pf.get("api_surface_summary", {})
classes = api.get("classes", [])
functions = api.get("functions", [])
print(f"  Classes: {len(classes)}")
if classes:
    for c in classes[:5]:
        if isinstance(c, dict):
            print(f"    {c.get('name', '?')}: {len(c.get('methods', []))} methods")
        else:
            print(f"    {c}")
    if len(classes) > 5:
        print(f"    ... and {len(classes)-5} more")
print(f"  Functions: {len(functions)}")

# Code understanding
print("\n\n" + "=" * 70)
print("CODE_UNDERSTANDING.JSON — SUMMARY")
print("=" * 70)
print(f"  product_summary: {cu.get('product_summary', '')[:100]}")
print(f"  core_concepts: {len(cu.get('core_concepts', []))}")
for cc in cu.get("core_concepts", [])[:3]:
    print(f"    {cc.get('concept', '?')}: {cc.get('explanation', '')[:60]}")
print(f"  class_profiles: {len(cu.get('class_profiles', []))}")
print(f"  usage_workflows: {len(cu.get('usage_workflows', []))}")
print(f"  api_relationships: {len(cu.get('api_relationships', {}))}")

# Repo inventory
print("\n\n" + "=" * 70)
print("REPO_INVENTORY.JSON — KEY FIELDS")
print("=" * 70)
for k in ["product_name", "repo_url", "supported_platforms", "primary_language"]:
    print(f"  {k}: {ri.get(k, 'MISSING')}")
docs = ri.get("discovered_docs", [])
print(f"  discovered_docs: {len(docs)}")
for d in docs[:5]:
    if isinstance(d, dict):
        print(f"    {d.get('path', '?')}")
    else:
        print(f"    {d}")

# Evidence map
print("\n\n" + "=" * 70)
print("EVIDENCE_MAP.JSON — SUMMARY")
print("=" * 70)
em_claims = em.get("claims", [])
print(f"  claims: {len(em_claims)}")
citations_total = sum(len(c.get("citations", [])) for c in em_claims)
print(f"  total citations: {citations_total}")
source_files = set()
for c in em_claims:
    for cit in c.get("citations", []):
        source_files.add(cit.get("path", ""))
print(f"  unique source files: {len(source_files)}")
for sf in sorted(source_files)[:10]:
    print(f"    {sf}")

# What's MISSING?
print("\n\n" + "=" * 70)
print("GAPS ANALYSIS — WHAT'S MISSING OR THIN")
print("=" * 70)

# Check for empty/missing fields that templates might need
missing = []
if not pf.get("positioning", {}).get("tagline"):
    missing.append("positioning.tagline")
if not pf.get("positioning", {}).get("short_description"):
    missing.append("positioning.short_description")
if not pf.get("version"):
    missing.append("version")
if not pf.get("compatibility_notes"):
    missing.append("compatibility_notes (empty)")
if len(pf.get("workflows", [])) < 3:
    missing.append(f"workflows (only {len(pf.get('workflows', []))})")
    
# Check claim diversity
kind_counts = Counter(c.get("claim_kind") for c in pf.get("claims", []))
for expected_kind in ["feature", "install", "format", "api", "limitation", "compatibility", "performance", "example"]:
    count = kind_counts.get(expected_kind, 0)
    if count == 0:
        missing.append(f"claims.{expected_kind} (0 claims)")
    elif count < 5:
        missing.append(f"claims.{expected_kind} (only {count})")

# Check code understanding depth
for profile in cu.get("class_profiles", [])[:5]:
    methods = profile.get("key_methods", [])
    if not methods:
        missing.append(f"code_understanding.{profile.get('name','?')}.key_methods (empty)")

for item in missing:
    print(f"  MISSING/THIN: {item}")
