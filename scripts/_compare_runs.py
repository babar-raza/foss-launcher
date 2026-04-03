import json, pathlib, sys

BASELINE_PATH = None  # from stash, captured separately
PREV_PATH = "runs/260323_132132_cells_python_378e/understanding_bundle.json"
NEW_PATH = "runs/260324_104213_cells_python_1fdc/understanding_bundle.json"

def load(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))

prev = load(PREV_PATH)
curr = load(NEW_PATH)

prev_db = prev.get("extraction_db", {})
curr_db = curr.get("extraction_db", {})

print("=== STRUCTURAL DELTA (prev=260323 vs new=260324) ===")
for label, pv, cv in [
    ("claims",        len(prev.get("claims",[])),                          len(curr.get("claims",[]))),
    ("snippets",      len(prev.get("snippets",[])),                        len(curr.get("snippets",[]))),
    ("format_facts",  len(prev_db.get("format_facts",[])),                 len(curr_db.get("format_facts",[]))),
    ("format_matrix", len(prev.get("api_surface",{}).get("format_matrix",[])), len(curr.get("api_surface",{}).get("format_matrix",[]))),
    ("richness_tier", prev.get("richness_tier"),                           curr.get("richness_tier")),
    ("api_facts",     len(prev_db.get("api_facts",[])),                    len(curr_db.get("api_facts",[]))),
]:
    mark = "==" if pv == cv else "!="
    print("  %-20s %s  prev=%-6s  curr=%s" % (label+":", mark, str(pv), str(cv)))

print()
print("=== FORMAT FACTS DELTA ===")
prev_ff = {f["format_name"]: f for f in prev_db.get("format_facts", [])}
curr_ff = {f["format_name"]: f for f in curr_db.get("format_facts", [])}
all_names = sorted(set(prev_ff) | set(curr_ff))
for name in all_names:
    pf = prev_ff.get(name)
    cf = curr_ff.get(name)
    if pf and cf:
        fields = ("can_export","can_import","confidence","evidence_source")
        diffs = [k for k in fields if pf.get(k) != cf.get(k)]
        status = ("CHANGED fields=%s" % diffs) if diffs else "identical"
    elif pf:
        status = "REMOVED"
    else:
        status = "ADDED"
    print("  %-12s %s" % (name+":", status))

print()
print("=== FORMAT MATRIX DELTA ===")
prev_fm = {r["name"]: r for r in prev.get("api_surface",{}).get("format_matrix",[])}
curr_fm = {r["name"]: r for r in curr.get("api_surface",{}).get("format_matrix",[])}
all_names = sorted(set(prev_fm) | set(curr_fm))
for name in all_names:
    pr = prev_fm.get(name)
    cr = curr_fm.get(name)
    if pr and cr:
        fields = ("can_export","can_import","source_evidence")
        diffs = [k for k in fields if pr.get(k) != cr.get(k)]
        status = ("CHANGED fields=%s" % diffs) if diffs else "identical"
    elif pr:
        status = "REMOVED"
    else:
        status = "ADDED"
    print("  %-12s %s" % (name+":", status))

print()
print("=== CLAIM COUNT BY PAGE_ROLE ===")
prev_roles = {}
curr_roles = {}
for c in prev.get("claims",[]):
    prev_roles[c.get("page_role","?")] = prev_roles.get(c.get("page_role","?"), 0) + 1
for c in curr.get("claims",[]):
    curr_roles[c.get("page_role","?")] = curr_roles.get(c.get("page_role","?"), 0) + 1
all_roles = sorted(set(list(prev_roles)+list(curr_roles)))
for role in all_roles:
    pv = prev_roles.get(role, 0)
    cv = curr_roles.get(role, 0)
    mark = "==" if pv == cv else "!="
    print("  %-30s %s  prev=%-3d  curr=%d" % (role+":", mark, pv, cv))
