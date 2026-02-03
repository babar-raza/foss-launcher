# TC-953: Page Inventory Contract and Quotas

## Metadata
- **Status**: Ready
- **Owner**: PAGE_QUOTA_ENFORCER
- **Depends On**: TC-430, TC-700, TC-940
- **Created**: 2026-02-03
- **Updated**: 2026-02-03

## Problem Statement
Current pilot runs generate only **5 pages total** across all subdomains, suggesting:
1. W4 IAPlanner is only generating mandatory pages
2. Optional pages are not being added up to max_pages quotas
3. Some subdomains may be missing entirely (e.g., kb section)

**Evidence:** Page inventory from finalization bundle shows minimal coverage, preventing realistic validation.

## Acceptance Criteria
1. W4 IAPlanner MUST include ALL mandatory pages for each section (per TC-940):
   - products: Overview/Landing (1 page)
   - docs: Getting Started + at least one how-to (min 2 pages)
   - reference: API Overview/Landing (1 page)
   - kb: FAQ + Known Limitations + Basic troubleshooting (3 pages)
   - blog: Announcement post (1 page)
   **Minimum total: 8 pages (not 5)**

2. W4 MUST add optional pages deterministically up to max_pages per section:
   - products: up to 10 pages (add Features, Quickstart, Supported Environments, etc.)
   - docs: up to 50 pages (add workflow how-tos)
   - reference: up to 100 pages (add module/class pages)
   - kb: up to 30 pages (add FAQs, troubleshooting guides)
   - blog: up to 20 pages (add deep-dive posts)

3. Optional page selection is deterministic and evidence-driven:
   - Prioritize pages with strong claim coverage
   - Prioritize frequently used features (snippet usage)
   - Sort deterministically (alphabetically by slug within priority tier)

4. For pilots, quotas should be meaningful but not excessive. Suggested pilot quotas:
   - products: 6 pages (landing, features, quickstart, environments, installation, FAQ)
   - docs: 10 pages (getting started, 9 how-tos)
   - reference: 6 pages (landing, 5 key modules/classes)
   - kb: 10 pages (FAQ, limitations, 8 troubleshooting guides)
   - blog: 3 pages (announcement, deep-dive, release notes)
   **Pilot total: ~35 pages (vs current 5)**

5. Unit test verifies:
   - Given ruleset with quotas, W4 generates at least min_pages per section
   - Given abundant evidence, W4 stops at max_pages per section
   - Mandatory pages are always included
   - Page count per section matches expected range

6. Gate H (if applicable) passes after fix

## Allowed Paths
- plans/taskcards/TC-953_page_inventory_contract_and_quotas.md
- specs/schemas/ruleset.schema.json (if schema changes needed)
- specs/rulesets/ruleset.v1.yaml (to adjust pilot quotas)
- specs/06_page_planning.md (documentation clarifications)
- specs/07_section_templates.md (mandatory page list clarifications)
- src/launch/workers/w4_ia_planner/worker.py (ONLY if quota enforcement is missing)
- tests/unit/workers/test_w4_quota_enforcement.py
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- reports/agents/**/TC-953/**

## Evidence Requirements
- reports/agents/<agent>/TC-953/report.md
- reports/agents/<agent>/TC-953/self_review.md
- reports/agents/<agent>/TC-953/test_output.txt (pytest showing quota tests)
- reports/agents/<agent>/TC-953/page_count_comparison.txt (before/after page counts per section)
- reports/agents/<agent>/TC-953/w4_quota_diff.txt (git diff if W4 code changed)

## Implementation Notes

### Current Quotas (specs/rulesets/ruleset.v1.yaml:40-70)
Already defined:
```yaml
sections:
  products: {min_pages: 1, max_pages: 10}
  docs: {min_pages: 2, max_pages: 50}
  reference: {min_pages: 1, max_pages: 100}
  kb: {min_pages: 3, max_pages: 30}
  blog: {min_pages: 1, max_pages: 20}
```

### Mandatory Pages (specs/06_page_planning.md:61-84, specs/07_section_templates.md:39-100)
Already documented in TC-940:
- products: Overview/Landing
- docs: Getting Started + one how-to
- reference: API Overview/Landing
- kb: FAQ + Known Limitations + Basic troubleshooting
- blog: Announcement post

### Proposed Changes

**1. Adjust pilot quotas in ruleset (or use override in pilot configs):**
```yaml
# For pilots, use smaller but meaningful quotas
sections:
  products: {min_pages: 1, max_pages: 6}
  docs: {min_pages: 2, max_pages: 10}
  reference: {min_pages: 1, max_pages: 6}
  kb: {min_pages: 3, max_pages: 10}
  blog: {min_pages: 1, max_pages: 3}
```

**2. Ensure W4 enforces quotas:**
Check [src/launch/workers/w4_ia_planner/worker.py](src/launch/workers/w4_ia_planner/worker.py) to verify:
- Mandatory pages are always added first
- Optional pages are added until max_pages is reached
- Page selection is deterministic (sorted by priority, then slug)

If W4 is missing quota enforcement, add:
```python
def enforce_quota(section_pages, section_config):
    """Enforce min/max quotas per section."""
    min_pages = section_config.get("min_pages", 1)
    max_pages = section_config.get("max_pages", 10)

    # Separate mandatory and optional
    mandatory = [p for p in section_pages if p.get("mandatory", False)]
    optional = [p for p in section_pages if not p.get("mandatory", False)]

    # Always include mandatory
    selected = mandatory[:]

    # Add optional up to max_pages
    remaining_slots = max_pages - len(selected)
    if remaining_slots > 0:
        # Sort optional by priority, then slug
        optional_sorted = sorted(optional, key=lambda p: (p.get("priority", 99), p["slug"]))
        selected.extend(optional_sorted[:remaining_slots])

    # Verify minimum
    if len(selected) < min_pages:
        raise PlannerQuotaViolationError(f"Section {section} has {len(selected)} pages, min is {min_pages}")

    return selected
```

### Test Requirements
Add test in `tests/unit/workers/test_w4_quota_enforcement.py`:
1. **Test A**: Given ruleset with min_pages=3, W4 generates at least 3 pages
2. **Test B**: Given ruleset with max_pages=5 and 20 candidate pages, W4 generates exactly 5
3. **Test C**: Mandatory pages are always included even when max_pages is tight
4. **Test D**: Optional page selection is deterministic (same order each run)

### Integration with TC-940
TC-940 already documented the mandatory/optional policy. TC-953 ensures W4 actually implements it.

## Dependencies
- TC-430 (W4 IAPlanner)
- TC-700 (Template Packs)
- TC-940 (Page Inventory Policy documentation)

## Related Issues
- VFV status truthfulness (TC-950)
- Approval gate blocking (TC-951)
- No visible .md files (TC-952)

## Definition of Done
- [ ] Pilot quotas adjusted to meaningful levels (products=6, docs=10, reference=6, kb=10, blog=3)
- [ ] W4 enforces min_pages and max_pages per section
- [ ] Mandatory pages always included
- [ ] Optional pages added deterministically up to max_pages
- [ ] Unit tests verify quota enforcement
- [ ] Page count comparison shows increase from 5 to ~35 pages
- [ ] validate_swarm_ready and pytest fully green
- [ ] Report and self-review written
