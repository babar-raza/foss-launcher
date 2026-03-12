---
name: content-complete
description: Complete missing mandatory and optional pages for one or more FOSS product families using only repository evidence, golden corpus patterns, and available templates.
---

# SKL-204: content-complete

You are completing missing mandatory (and additional where evidence allows)
pages for one or more FOSS product families.

## Context

A family has uncovered mandatory pages, or thin subdomain coverage that the
repository evidence can support. Your job is to generate content that can pass
human review, grounded entirely in repository evidence, golden corpus patterns,
and available templates.

Do not invent features, APIs, workflows, or claims.

## Required inputs

- Cloned repositories (or the ability to clone)
- Golden corpus directory
- `specs/templates/` directory (all template variants)
- Org config (for org_scanner discovery)

## What to do

1. Run `org_scanner` to discover all relevant repositories for the target
   families. Do not assume repo URLs.

2. For each target family, determine:
   - Which repositories are in scope
   - Which mandatory pages already exist
   - Which mandatory pages are missing
   - What evidence exists to support each missing page
   - Which optional pages can be created with confidence

3. For each missing page:
   - Check whether evidence is sufficient before starting content
   - If evidence is insufficient, record the page as blocked with the reason
   - If evidence is sufficient, select the appropriate template variant and
     generate content using only the available claims and snippets

4. After generation, run SKL-104 (review-full) on each new page. Only pages
   graded B or higher are counted as complete.

## Output you must produce

- Completed mandatory pages for each target family
- Additional pages where evidence is sufficient
- List of blocked pages with exact reasons (not "insufficient evidence" —
  name specifically what is missing)
- Weak or missing evidence items that require human follow-up

## Constraints

- Use org_scanner for discovery — do not assume repo URLs
- Clone missing repos before content work begins
- Base all content on actual repository evidence + golden corpus patterns
- Do not invent features, APIs, workflows, or claims
- Mandatory pages before optional pages — always
- All new content must meet skills.md GENERATION STANDARDS

## Escalation rules

- If a mandatory page cannot be created because the repo lacks sufficient
  evidence, escalate to SKL-201 (understand-audit) before attempting to
  generate — do not generate thin content and then try to heal it
- If grade after two generate attempts is still D or F, stop generating that
  page and record it as blocked with the evidence gap as the reason

## Verification

- Run SKL-104 (review-full) on all new pages
- Grade B or higher for mandatory pages before declaring complete
- Any A/B-graded page is potentially publishable
