---
name: thin-family-expand
description: Systematically increase page coverage for thin FOSS product families — distinguishes justified thinness from pipeline gaps, then expands coverage using only repository evidence.
---

# SKL-210: thin-family-expand

You are systematically increasing page coverage for families that are thin
across one or more subdomains, using only evidence supported by the FOSS repo.

## Context

A family has fewer pages than expected in one or more subdomains (products,
docs, KB, blog, or reference). Your job is to assess whether thinness is
justified by limited evidence or caused by a pipeline gap, and to expand
coverage where evidence supports it.

Do not create pages by guessing or stretching weak signals.

## Required inputs

- Cloned repositories for all target families
- Current publish directory or content manifest (to see what already exists)
- `specs/rulesets/ruleset.yaml` (mandatory + optional page sets)
- `specs/templates/` directory

## What to do

1. For each thin family, determine current coverage per subdomain:
   - Count existing pages by subdomain
   - Compare to the expected range for the repo's richness tier

2. For each subdomain, assess what evidence exists:
   - Examples and sample projects
   - Source modules and public classes
   - Docstrings and README content
   - Tests and CI configurations
   - Format support definitions

3. Classify thinness:
   - Justified thin: the repo genuinely lacks evidence for this subdomain
   - Pipeline gap: evidence exists but was not used to create the page

4. For each unjustified gap, determine:
   - What page can be created
   - What evidence supports it
   - Whether it is mandatory or optional
   - Which template variant to use

5. Create pages in this order: mandatory first, then optional where evidence
   is strong. Run SKL-104 (review-full) on each new page. Only B or higher
   counts as complete.

## Output you must produce

- Thin-family assessment per subdomain (justified vs. pipeline gap)
- Coverage expansion plan (pages to add, subdomain, evidence, mandatory/optional)
- Gap classification per missed opportunity

## Constraints

- Mandatory pages first, always
- Do not create pages from weak or absent evidence
- Equal page count is not the goal; evidence depth determines coverage
- Every new page must grade B or higher before being counted as complete
- Reference pages must include object-level entries, not just a home page
- KB pages must be derived from actual example workflows in the repo

## Escalation rules

- If a subdomain is thin because the repo genuinely lacks evidence for those
  page types, stop expanding and document the evidence gap — do not pad with
  thin content
- If a new page grades D or F after two generation attempts, block it and
  escalate to SKL-201 (understand-audit) to check whether Understand captured
  sufficient evidence for that page type

## Verification

- After expansion, run SKL-104 on all new pages
- Compare subdomain page counts before and after
- No new page grades below B
