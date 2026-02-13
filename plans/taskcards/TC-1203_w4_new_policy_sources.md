---
id: TC-1203
title: "Page Expansion — W4 New Optional Page Policy Sources"
status: Draft
priority: Critical
owner: "Agent B (Backend/Workers)"
updated: "2026-02-11"
tags: ["w4", "ia-planner", "page-expansion", "phase-2"]
depends_on: ["TC-1200", "TC-1201", "TC-1202"]
allowed_paths:
  - plans/taskcards/TC-1203_w4_new_policy_sources.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_page_expansion.py
evidence_required:
  - reports/agents/AGENT_B/TC-1203/evidence.md
  - reports/agents/AGENT_B/TC-1203/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1203 — Page Expansion — W4 New Optional Page Policy Sources

## Objective
Implement 7 new candidate generation branches inside W4's `generate_optional_pages()` function, each corresponding to a new `optional_page_policy` source defined in TC-1200/TC-1201. This is the core page-count multiplier — it transforms evidence data into page plan entries.

## Required spec references
- specs/08_content_distribution_strategy.md (updated by TC-1200 — 7 new source contracts with scoring formulas)
- specs/rulesets/ruleset.v1.yaml (updated by TC-1201 — policies registered per section)
- specs/schemas/page_plan.schema.json (updated by TC-1200 — new page_role enum values)
- src/launch/workers/w4_ia_planner/worker.py (current W4 — `generate_optional_pages()` function)

## Scope

### In scope
1. **7 new source handlers** inside `generate_optional_pages()`:
   - `per_format_pair` — reads `product_facts["format_capabilities"]["confirmed_pairs"]`
   - `per_example` — reads `product_facts["examples"]` filtered by evidence
   - `per_workflow_tutorial` — reads `product_facts["workflows"]`
   - `per_namespace_reference` — reads `product_facts["api_surface_summary"]["classes"]` grouped by module
   - `per_feature_combination` — reads `claim_groups["key_features"]`, generates top-N pairwise
   - `per_theme_group` — reads `claim_groups` keys with 3+ claims
   - `per_faq_topic` — reads claims grouped by `claim_kind`
2. **Config-aware filtering** — Read `run_config.page_expansion.enabled_policies` to skip disabled sources
3. **Quality scoring** — Each source uses its spec-defined scoring formula
4. **Slug generation** — Deterministic, sanitized, alphabetical ordering for pairs
5. **Page role assignment** — Each source maps to its designated page_role
6. **Content strategy population** — Each candidate gets a content_strategy dict
7. **Unit tests** — At least 2 tests per source (happy path + edge case)

### Out of scope
- Sub-page generation (TC-1204)
- Template creation (TC-1205)
- W5 specialized generators (TC-1206)
- Existing policy source modification (per_feature, per_workflow, per_key_feature, per_api_symbol, per_deep_dive remain unchanged)

## Inputs
- product_facts.json (with `format_capabilities`, `examples`, `workflows`, `api_surface_summary`, `claim_groups`)
- snippet_catalog.json
- run_config (page_expansion settings)
- ruleset (optional_page_policies per section)

## Outputs
- src/launch/workers/w4_ia_planner/worker.py (UPDATED — +350 lines: 7 source handlers + config filtering)
- tests/unit/workers/test_w4_page_expansion.py (NEW — ~250 lines: 14+ test cases)

## Allowed paths
- plans/taskcards/TC-1203_w4_new_policy_sources.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_w4_page_expansion.py

### Allowed paths rationale
W4 worker is the only code file. Tests are co-located. No shared libraries modified.

## Implementation steps

### Step 1: Read current `generate_optional_pages()` function
Locate the function in worker.py. Understand the existing pattern for source handlers (per_feature, per_workflow, etc.). The implementation MUST follow the same pattern.

**Resilience note**: The function may have been modified since this taskcard was written. Locate it by searching for `def generate_optional_pages` rather than by line number. The existing source handlers follow a pattern: `if source == "per_X":` branches inside a loop over `optional_page_policies`.

### Step 2: Add config-aware policy filtering
At the top of `generate_optional_pages()`, read `page_expansion` from run_config:

```python
page_expansion = run_config.get("page_expansion", {}) if run_config else {}
enabled_policies = page_expansion.get("enabled_policies", [])
# Empty list means all enabled
```

In the policy loop, add a filter:
```python
for policy in optional_page_policies:
    source = policy["source"]
    if enabled_policies and source not in enabled_policies:
        logger.debug(f"[W4] Skipping disabled policy source: {source}")
        continue
    # ... existing + new handlers
```

### Step 3: Implement `per_format_pair` handler
```python
elif source == "per_format_pair":
    format_caps = product_facts.get("format_capabilities", {})
    confirmed_pairs = format_caps.get("confirmed_pairs", [])
    for pair in confirmed_pairs:
        src_fmt, tgt_fmt = sorted(pair)  # Deterministic ordering
        slug = f"convert-{src_fmt.lower()}-to-{tgt_fmt.lower()}"
        # ... build candidate dict with scoring
```

**Scoring**: `(len(matching_claims) * 2) + (len(matching_snippets) * 3)` where matching = claims/snippets mentioning either format name.

### Step 4: Implement `per_example` handler
```python
elif source == "per_example":
    examples = product_facts.get("examples", [])
    for ex in examples:
        claim_ids = ex.get("claim_ids", [])
        snippet_ids = ex.get("snippet_ids", [])
        if not claim_ids or not snippet_ids:
            continue  # Only with evidence
        slug = f"example-{sanitize_slug(ex.get('name', 'unnamed'))}"
        # ... build candidate
```

**Scoring**: `(len(claim_ids) * 2) + (len(snippet_ids) * 3) + (2 if audience == "beginner" else 0)`

### Step 5: Implement `per_workflow_tutorial` handler
```python
elif source == "per_workflow_tutorial":
    workflows = product_facts.get("workflows", [])
    for wf in workflows:
        slug = f"tutorial-{sanitize_slug(wf.get('name', 'unnamed'))}"
        step_count = len(wf.get("steps", []))
        # ... build candidate
```

**Scoring**: `(step_count * 2) + (len(matching_snippets) * 3) + (3 if complexity == "advanced" else 0)`

### Step 6: Implement `per_namespace_reference` handler
```python
elif source == "per_namespace_reference":
    classes = product_facts.get("api_surface_summary", {}).get("classes", [])
    # Group by module/namespace
    namespaces = {}
    for cls in classes:
        ns = cls.get("module", cls.get("namespace", "default"))
        namespaces.setdefault(ns, []).append(cls)
    for ns_name, ns_classes in sorted(namespaces.items()):
        slug = f"ref-{sanitize_slug(ns_name)}"
        # ... build candidate
```

**Scoring**: `(len(ns_classes) * 2) + (sum(len(c.get('methods', [])) for c in ns_classes))`

### Step 7: Implement `per_feature_combination` handler
```python
elif source == "per_feature_combination":
    combination_top_n = page_expansion.get("combination_top_n", 5)
    key_features = claim_groups.get("key_features", [])
    # Score and sort features
    scored = [(fid, compute_claim_quality(fid, claims)) for fid in key_features]
    scored.sort(key=lambda x: (-x[1], x[0]))
    top_features = scored[:combination_top_n]
    # Generate pairwise combinations
    for i, (fid_a, score_a) in enumerate(top_features):
        for fid_b, score_b in top_features[i+1:]:
            slug_a, slug_b = sorted([sanitize_slug(fid_a), sanitize_slug(fid_b)])
            slug = f"deep-dive-{slug_a}-and-{slug_b}"
            # ... build candidate
```

**Scoring**: `score_a + score_b + (5 if shared_snippets else 0)`

### Step 8: Implement `per_theme_group` handler
```python
elif source == "per_theme_group":
    for group_name, group_ids in sorted(claim_groups.items()):
        if len(group_ids) < 3:
            continue  # Only groups with 3+ claims
        slug = f"guide-{sanitize_slug(group_name)}"
        # ... build candidate
```

**Scoring**: `sum(claim_quality_scores) + (len(group_ids) * 1)`

### Step 9: Implement `per_faq_topic` handler
```python
elif source == "per_faq_topic":
    # Group claims by claim_kind
    topics = {}
    for claim in all_claims:
        kind = claim.get("claim_kind", "general")
        topics.setdefault(kind, []).append(claim)
    for topic_name, topic_claims in sorted(topics.items()):
        if len(topic_claims) < 3:
            continue  # Only topics with 3+ claims
        slug = f"faq-{sanitize_slug(topic_name)}"
        # ... build candidate
```

**Scoring**: `len(topic_claims) * 2`

### Step 10: Add `sanitize_slug()` helper
If not already present, add a deterministic slug sanitizer:
```python
def sanitize_slug(text: str) -> str:
    """Convert text to URL-safe slug. Deterministic."""
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug[:60]  # Cap length
```

### Step 11: Write unit tests
Create `tests/unit/workers/test_w4_page_expansion.py`:

For each of the 7 sources, write at minimum:
1. **Happy path** — Provide evidence, verify candidate generated with correct slug, role, and score
2. **Edge case** — Empty evidence → 0 candidates, no error

Additional tests:
3. **test_enabled_policies_filter** — Verify disabled sources are skipped
4. **test_slug_determinism** — Verify identical input → identical slugs across runs
5. **test_format_pair_ordering** — Verify alphabetical pair ordering
6. **test_combination_top_n** — Verify only top N features are paired

### Step 12: Run tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_page_expansion.py -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/ -k "w4" -v  # regression
```

## Failure modes

### Failure mode 1: Unknown source name in policy loop
**Detection:** `generate_optional_pages()` encounters a source name it doesn't handle. Currently silently skips via `else` branch.
**Resolution:** Add explicit `else` with `logger.warning(f"Unknown policy source: {source}")`. Do NOT error — forward compatibility requires graceful skip.
**Spec/Gate:** specs/08 forward compatibility rule

### Failure mode 2: Slug collision between new and existing pages
**Detection:** Two pages have identical slugs (e.g., `tutorial-model-loading` collides with existing `model-loading`).
**Resolution:** New source handlers use prefixed slugs (`convert-`, `example-`, `tutorial-`, `ref-`, `deep-dive-`, `guide-`, `faq-`). Collision detection already runs after generation in W4.
**Spec/Gate:** specs/06 collision detection rules

### Failure mode 3: Combinatorial explosion with per_feature_combination
**Detection:** combination_top_n=10 generates 45 pairs. With other policies, exceeds max_pages.
**Resolution:** The existing N = effective_max - mandatory_count cap applies. Candidates are scored and only top N selected. The combination_top_n config defaults to 5 (10 pairs max).
**Spec/Gate:** specs/08 quality score selection algorithm

## Task-specific review checklist
1. [ ] All 7 source handlers implemented following existing pattern
2. [ ] Config-aware filtering (enabled_policies) works
3. [ ] Each handler uses correct scoring formula from spec
4. [ ] Slug generation is deterministic (sorted, sanitized, capped)
5. [ ] Page role assignment matches spec (7 new roles)
6. [ ] Content strategy populated for each candidate
7. [ ] `per_format_pair` reads `format_capabilities.confirmed_pairs`
8. [ ] `per_example` filters to examples WITH evidence only
9. [ ] `per_feature_combination` respects `combination_top_n` config
10. [ ] `per_faq_topic` and `per_theme_group` require 3+ claims minimum
11. [ ] Unknown sources logged as warning, not error
12. [ ] 14+ unit tests (2 per source + 2 cross-cutting)

## Deliverables
- src/launch/workers/w4_ia_planner/worker.py (UPDATED — +350 lines)
- tests/unit/workers/test_w4_page_expansion.py (NEW — ~250 lines)
- reports/agents/AGENT_B/TC-1203/evidence.md
- reports/agents/AGENT_B/TC-1203/self_review.md

## Acceptance checks
1. [ ] 7 new source handlers in generate_optional_pages()
2. [ ] Config filtering works (enabled_policies)
3. [ ] All unit tests pass
4. [ ] Existing W4 tests pass (no regression)
5. [ ] Deterministic output (2 runs identical)
6. [ ] Slug prefixes prevent collisions with existing pages

## Preconditions / dependencies
- TC-1200 completed (specs define source contracts)
- TC-1201 completed (ruleset registers policies)
- TC-1202 completed (W2 provides format_capabilities in product_facts)

## Self-review
[To be completed by Agent B after implementation]
