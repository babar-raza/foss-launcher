# Pilot Content Quality Fixes
**Created**: 2026-02-05T09:00:00Z
**Source**: Chat investigation of pilot runs (3d + note) showing empty pages and 0 claims
**Investigation**: `C:\Users\prora\.claude\plans\deep-weaving-dongarra.md`

## Context

Both pilots (`pilot-aspose-3d-foss-python`, `pilot-aspose-note-foss-python`) complete with exit code 2. All 22 validation gates pass as `ok:true` but every page has zero meaningful content and zero claims injected. Five root causes form a chain of failures from W4 claim filtering through W5 content generation.

## Goals

1. Non-template pages (overview, api-overview, faq) have actual content paragraphs with claims
2. Template-driven pages (docs/index, blog/index) have product-specific token values
3. All GATE14_CLAIM_QUOTA_UNDERFLOW warnings eliminated
4. GATE_CONTENT_QUALITY_MIN_LENGTH warning eliminated
5. Note pilot tokens reference Note-specific classes, not 3D classes
6. No title leading space artifacts
7. All existing tests still pass

## Assumptions

- [VERIFIED] Individual claims in product_facts.json do NOT have a `claim_group` field
- [VERIFIED] `claim_groups` is a top-level dict mapping group names to claim_id arrays
- [VERIFIED] `api_surface_summary.classes` contains claim_id hashes, not class name strings
- [UNVERIFIED] Fixing RC-1 alone may be enough for non-zero claims on most pages
- [UNVERIFIED] Tests in tests/unit/workers/test_w4_* and test_w5_* cover the changed functions

## Steps

### Step 1: Fix W4 claim_group mismatch (RC-1) [CRITICAL]

**File**: `src/launch/workers/w4_ia_planner/worker.py`

1a. In `plan_pages_for_section()`, add a helper at the top to resolve claim IDs from groups:
```python
claim_groups = product_facts.get("claim_groups", {})
```

1b. Fix products section (lines 686-689):
```python
# Before:
overview_claim_ids = [c["claim_id"] for c in claims[:10]
    if c.get("claim_group", "").lower() in ["positioning", "features", "overview"]]
# After:
overview_claim_ids = (
    claim_groups.get("key_features", []) +
    claim_groups.get("install_steps", [])
)[:10]
```

1c. Fix reference section (line 819):
```python
# Before:
"required_claim_ids": [c["claim_id"] for c in claims if "api" in c.get("claim_group", "").lower()][:5],
# After:
"required_claim_ids": claim_groups.get("key_features", [])[:5],
```

1d. Fix KB section (lines 858-860):
```python
# Before:
key_feature_claims = [c for c in claims if c.get("claim_group", "").lower() in ["key_features", "features"]]
# After: Resolve claim IDs from groups, then look up full claim objects
key_feature_ids = set(claim_groups.get("key_features", []))
key_feature_claims = [c for c in claims if c["claim_id"] in key_feature_ids]
```

1e. Fix KB FAQ page — assign claims instead of empty list (line 915):
```python
# Before:
"required_claim_ids": [],
# After:
"required_claim_ids": (claim_groups.get("install_steps", []) + claim_groups.get("limitations", []))[:5],
```

### Step 2: Fix template pages skipping claims (RC-2)

**File**: `src/launch/workers/w4_ia_planner/worker.py`

2a. Add `product_facts` parameter to `fill_template_placeholders()` signature (line 1576)

2b. In `execute_ia_planner()`, pass product_facts to the call (line 1804)

2c. Inside `fill_template_placeholders()`, resolve claims:
```python
claim_groups = product_facts.get("claim_groups", {}) if product_facts else {}
required_claim_ids = (claim_groups.get("key_features", []) + claim_groups.get("install_steps", []))[:5]
```
Use in the returned page spec (line 1657).

### Step 3: Fix hardcoded generic tokens (RC-3)

**File**: `src/launch/workers/w4_ia_planner/worker.py`

3a. Add `product_facts` parameter to `generate_content_tokens()` (line 1352)

3b. Replace hardcoded values (lines 1505-1513) with product_facts-derived values:
- Extract class names from claims with `claim_kind == "api"` text
- If no API claims found, extract key nouns from key_features claims
- Fallback: use `f"{family.capitalize()}.{family.capitalize()}Document"` pattern

3c. Update call site (line 1632) to pass product_facts

### Step 4: Fix W5 fallback empty sections (RC-4)

**File**: `src/launch/workers/w5_section_writer/worker.py`

4a. In `_generate_fallback_content()`, distribute claims across headings instead of reusing first 2:
```python
# Distribute claims evenly across headings
claims_per_heading = max(1, len(claims) // max(len(required_headings), 1))
for i, heading in enumerate(required_headings):
    start = i * claims_per_heading
    heading_claims = claims[start:start + claims_per_heading]
```

4b. Broaden snippet matching (line 941) to include partial matches:
```python
heading_lower = heading.lower()
if snippets and any(kw in heading_lower for kw in ["example", "code", "quickstart", "started", "usage", "install"]):
```

### Step 5: Fix title leading space (RC-5)

**File**: `src/launch/workers/w4_ia_planner/worker.py`

5a. Fix line 678:
```python
product_name = product_facts.get("product_name", "").strip()
if not product_name:
    product_name = f"Aspose.{product_slug.capitalize()} for {platform.capitalize()}"
title = f"{product_name} Overview"
```

### Step 6: Run tests

```bash
python -m pytest tests/ -x --tb=short
```

### Step 7: Run pilots and verify

```bash
python scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/pilot_3d_verify.json
python scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output runs/pilot_note_verify.json
```

## Acceptance Criteria

1. `python -m pytest tests/ -x` passes (0 failures)
2. Both pilots complete with exit code 0 (no warnings) or exit code 2 with only non-claim warnings
3. `GATE14_CLAIM_QUOTA_UNDERFLOW` count = 0 (or significantly reduced)
4. `GATE_CONTENT_QUALITY_MIN_LENGTH` count = 0
5. Non-template drafts (overview.md, api-overview.md, faq.md) have >100 chars content
6. Note pilot `__BODY_KEY_SYMBOLS__` does NOT contain "Scene" or "Entity"
7. No title starts with a space character

## Risks + Rollback

- **Risk**: Changing claim distribution may break golden artifacts (expected_page_plan.json)
  - Rollback: Re-goldenize with `python scripts/run_pilot_vfv.py --pilot <id> --goldenize`
- **Risk**: Tests may assert specific empty claim_ids
  - Mitigation: Update test fixtures to match new behavior
- **Risk**: Token changes may break Gate 11 (template_token_lint)
  - Mitigation: Run Gate 11 specifically after token changes

## Evidence Commands

```bash
# Unit tests
python -m pytest tests/unit/workers/test_w4_content_distribution.py -v
python -m pytest tests/unit/workers/test_w4_docs_token_generation.py -v
python -m pytest tests/unit/workers/test_w5_specialized_generators.py -v
python -m pytest tests/ -x --tb=short

# Pilot verification
python scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/pilot_3d_verify.json
python scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output runs/pilot_note_verify.json

# Check specific outputs
python -c "import json; r=json.load(open('runs/pilot_3d_verify.json')); print([i for i in r.get('issues',[]) if 'QUOTA' in i.get('error_code','')])"
```

## Open Questions

(none — all answered by investigation)
