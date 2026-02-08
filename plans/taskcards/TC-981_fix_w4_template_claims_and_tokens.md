---
id: TC-981
title: "Fix W4 template page claims and product-specific token generation"
status: Complete
priority: High
owner: "Agent-B (Implementation)"
updated: "2026-02-05"
tags: ["w4", "tokens", "claims", "templates", "content-quality", "pilot-fix"]
depends_on: ["TC-980"]
allowed_paths:
  - plans/taskcards/TC-981_fix_w4_template_claims_and_tokens.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_docs_token_generation.py
  - tests/unit/workers/test_w4_content_distribution.py
evidence_required:
  - reports/agents/agent_b/TC-981/evidence.md
  - reports/agents/agent_b/TC-981/self_review.md
spec_ref: "fad128dc63faba72bad582ddbc15c19a4c29d684"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-981 — Fix W4 Template Claims and Product-Specific Tokens

## Objective
Fix two interconnected issues: (1) template-driven pages always get empty `required_claim_ids`, and (2) `generate_content_tokens()` produces hardcoded 3D-specific values for all products. After this fix, template pages will have claims and Note pilot will show Note-specific class names.

## Problem Statement
**RC-2**: `fill_template_placeholders()` hardcodes `required_claim_ids: []` (line 1657). Template-driven pages (docs/index, blog/index) always have 0 claims.

**RC-3**: `generate_content_tokens()` uses hardcoded "Scene, Entity, Node" (lines 1508-1509) for ALL products. The Note pilot incorrectly shows 3D class names. The function takes no `product_facts` parameter.

**RC-5**: Title has leading space when `product_name` is empty (line 678).

Full investigation: `C:\Users\prora\.claude\plans\deep-weaving-dongarra.md` (RC-2, RC-3, RC-5 sections)

## Required spec references
- specs/06_page_planning.md (page specification requirements)
- specs/07_section_templates.md (template token contract)
- specs/08_content_distribution_strategy.md (claim distribution rules)

## Scope

### In scope
- Add `product_facts` parameter to `generate_content_tokens()` and `fill_template_placeholders()`
- Replace hardcoded API tokens with product_facts-derived values
- Assign claims to template-driven pages via claim_groups
- Fix title leading space (RC-5)
- Update call sites in `execute_ia_planner()`
- Update tests

### Out of scope
- W5 fallback content improvements (TC-982)
- Non-template page claim assignment (TC-980)

## Inputs
- `product_facts.json` with `api_surface_summary`, `claims`, `claim_groups`
- Template files in `specs/templates/`
- Existing W4 worker

## Outputs
- Modified `generate_content_tokens()` accepting product_facts
- Modified `fill_template_placeholders()` assigning claims
- Product-specific token values based on actual claim/API data
- Updated tests

## Allowed paths
- plans/taskcards/TC-981_fix_w4_template_claims_and_tokens.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_w4_docs_token_generation.py
- tests/unit/workers/test_w4_content_distribution.py

### Allowed paths rationale
TC-981 modifies W4 token generation and template placeholder filling, plus their tests.

## Implementation steps

### Step 1: Add product_facts parameter to generate_content_tokens() (line 1352)
```python
def generate_content_tokens(
    page_spec: Dict[str, Any],
    section: str,
    family: str,
    platform: str,
    locale: str = "en",
    product_facts: Optional[Dict[str, Any]] = None,  # NEW
) -> Dict[str, str]:
```

### Step 2: Replace hardcoded API tokens (lines 1505-1513)
Extract class names from product_facts claims:
```python
if product_facts:
    api_claims = [c for c in product_facts.get("claims", [])
                  if c.get("claim_kind") == "api"]
    # Extract key class/symbol names from claim text
    key_symbols = _extract_symbols_from_claims(product_facts)
    popular_classes = _extract_classes_from_claims(product_facts)
else:
    key_symbols = f"{family.capitalize()}Document, {family.capitalize()}Page"
    popular_classes = key_symbols

tokens["__BODY_KEY_SYMBOLS__"] = key_symbols
tokens["__BODY_POPULAR_CLASSES__"] = popular_classes
tokens["__BODY_SIGNATURE__"] = f"class {family.capitalize()}Document"
tokens["__BODY_REMARKS__"] = f"Use {family.capitalize()}Document as the entry point for {family} operations."
tokens["__BODY_RETURNS__"] = f"Returns a {family.capitalize()}Document object"
```

### Step 3: Add helper to extract symbols from product_facts
Create `_extract_symbols_from_claims()` that:
- Looks at claims with claim_kind == "api"
- Extracts capitalized class-like words from claim_text
- Falls back to family-based naming if no API claims

### Step 4: Add product_facts to fill_template_placeholders() signature (line 1576)
```python
def fill_template_placeholders(
    template, section, product_slug, locale, platform, subdomain,
    product_facts=None,  # NEW
):
```

### Step 5: Assign claims in fill_template_placeholders() (line 1657)
```python
claim_groups = product_facts.get("claim_groups", {}) if product_facts else {}
required_claim_ids = (
    claim_groups.get("key_features", []) +
    claim_groups.get("install_steps", [])
)[:5]
...
"required_claim_ids": required_claim_ids,
```

### Step 6: Update call sites in execute_ia_planner()
- Line 1632: Pass product_facts to generate_content_tokens()
- Line 1804: Pass product_facts to fill_template_placeholders()

### Step 7: Fix title leading space (line 678)
```python
product_name = product_facts.get("product_name", "").strip()
if not product_name:
    product_name = f"Aspose.{product_slug.capitalize()} for {platform.capitalize()}"
title = f"{product_name} Overview"
```

### Step 8: Run tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_docs_token_generation.py -v
.venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```

## Failure modes

### Failure mode 1: Symbol extraction returns empty or garbage
**Detection:** Token values contain empty strings or non-class words
**Resolution:** Improve regex/heuristic for extracting class names; add fallback to family-based naming
**Spec/Gate:** Gate 11 template_token_lint

### Failure mode 2: Tests assert specific hardcoded token values
**Detection:** Test failures comparing old "Scene, Entity, Node" values
**Resolution:** Update test fixtures with new product_facts-derived values
**Spec/Gate:** Gate T test determinism

### Failure mode 3: fill_template_placeholders() callers don't pass product_facts
**Detection:** TypeError on missing argument
**Resolution:** product_facts has default=None; backward compatible
**Spec/Gate:** specs/06_page_planning.md

## Task-specific review checklist
1. [ ] generate_content_tokens() accepts product_facts parameter
2. [ ] No hardcoded "Scene", "Entity", "Node", "Mesh" remains in token values
3. [ ] Note pilot tokens would produce Note-specific class names
4. [ ] fill_template_placeholders() assigns non-empty required_claim_ids
5. [ ] Title has no leading space
6. [ ] execute_ia_planner() passes product_facts to both functions
7. [ ] All tests pass
8. [ ] Backward compatible (product_facts=None works)

## Deliverables
- Modified `src/launch/workers/w4_ia_planner/worker.py`
- Updated tests
- Evidence at `reports/agents/agent_b/TC-981/evidence.md`
- Self-review at `reports/agents/agent_b/TC-981/self_review.md`

## Acceptance checks
1. [ ] `__BODY_KEY_SYMBOLS__` does NOT contain "Scene" for Note pilot
2. [ ] `__BODY_POPULAR_CLASSES__` is product-specific
3. [ ] Template pages have >0 required_claim_ids
4. [ ] Title "Overview" has no leading space
5. [ ] All tests pass

## Preconditions / dependencies
- TC-980 completed (claim_groups lookup established)
- Python venv activated

## Test plan
1. Run W4 token generation tests
2. Verify Note pilot produces Note-specific tokens
3. Verify template pages have claim_ids

## Self-review
### 12D Checklist
1. **Determinism:** Token derivation from claims is deterministic (sorted, no random)
2. **Dependencies:** No new dependencies
3. **Documentation:** TC-981 taskcard
4. **Data preservation:** Token values derived from actual product data
5. **Deliberate design:** Fallback chain: product_facts -> family-based naming -> generic
6. **Detection:** Gate 11 catches malformed tokens; Gate 14 catches missing claims
7. **Diagnostics:** Logger messages for token generation
8. **Defensive coding:** product_facts=None fallback at every level
9. **Direct testing:** Unit tests + pilot verification
10. **Deployment safety:** Backward compatible (Optional parameter)
11. **Delta tracking:** Modified generate_content_tokens, fill_template_placeholders, execute_ia_planner
12. **Downstream impact:** W5 receives better tokens and non-empty claim_ids

### Verification results
- [ ] Tests: PASS
- [ ] Note pilot tokens: Note-specific

## E2E verification
```bash
.venv/Scripts/python.exe -m pytest tests/ -x --tb=short
.venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output runs/pilot_note_tc981.json
```

## Integration boundary proven
**Upstream:** W2 produces product_facts with api_surface_summary and claims
**Downstream:** W5 applies tokens to templates and uses required_claim_ids
**Contract:** Token values must be non-empty strings; claim_ids must exist in product_facts.claims

## Evidence Location
`reports/agents/agent_b/TC-981/`
