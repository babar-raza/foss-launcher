---
id: TC-954
title: "Absolute Cross-Subdomain Links Verification"
status: Draft
priority: Critical
owner: "LINK_VERIFIER"
updated: "2026-02-03"
tags: ["links", "verification", "cross-subdomain", "absolute-urls", "tc-938"]
depends_on: ["TC-938"]
allowed_paths:
  - plans/taskcards/TC-954_absolute_cross_subdomain_links.md
  - reports/agents/**/TC-954/**
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
evidence_required:
  - reports/agents/<agent>/TC-954/report.md
  - reports/agents/<agent>/TC-954/self_review.md
  - reports/agents/<agent>/TC-954/link_audit.txt
  - reports/agents/<agent>/TC-954/test_run.txt
spec_ref: "fe582540d14bb6648235fe9937d2197e4ed5cbac"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-954: Absolute Cross-Subdomain Links Verification

## Objective
Verify that TC-938 implementation correctly generates absolute URLs for cross-subdomain links in pilot-generated content, ensuring proper Hugo subdomain navigation.

## Problem Statement
**NOTE:** TC-938 already implemented absolute cross-subdomain links and is marked **Done**. TC-954 is a verification taskcard to ensure TC-938's implementation is working correctly for pilot runs.

Cross-subdomain links must be absolute to work across different Hugo subdomains:
- `https://docs.aspose.org/...` when linking from products to docs
- `https://reference.aspose.org/...` when linking from docs to reference
- `https://kb.aspose.org/...` when linking from docs to kb
- etc.

We need to verify that pilot-generated content uses absolute URLs for cross-subdomain navigation.

## Required spec references
- specs/18_site_repo_layout.md (Hugo subdomain structure)
- specs/38_link_resolution.md (Cross-subdomain link requirements)
- TC-938 (Absolute Cross-Subdomain Links implementation)

## Scope

### In scope
- Review TC-938 implementation (build_absolute_public_url, link_transformer)
- Run TC-938 unit tests and verify they pass
- Audit 5 cross-subdomain links from pilot content_preview
- Verify absolute URLs used for cross-subdomain links
- Document findings in link_audit.txt

### Out of scope
- Modifying TC-938 implementation (verification only)
- Changing link resolution logic
- Adding new link transformation features
- Fixing TC-938 issues (create new taskcard if needed)

## Inputs
- TC-938 implementation in src/launch/resolvers/public_urls.py
- TC-938 link transformation in src/launch/workers/w6_linker_and_patcher/link_transformer.py
- TC-938 unit tests in tests/unit/workers/test_tc_938_absolute_links.py
- Pilot content_preview directory with generated .md files

## Outputs
- reports/agents/<agent>/TC-954/link_audit.txt (5 cross-subdomain link examples)
- reports/agents/<agent>/TC-954/test_run.txt (pytest output for TC-938 tests)
- reports/agents/<agent>/TC-954/report.md (verification findings)
- reports/agents/<agent>/TC-954/self_review.md

## Allowed paths

- `plans/taskcards/TC-954_absolute_cross_subdomain_links.md`
- `reports/agents/**/TC-954/**`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`## Implementation steps

### Step 1: Review TC-938 implementation
Read src/launch/resolvers/public_urls.py to understand build_absolute_public_url() logic

### Step 2: Run TC-938 unit tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_938_absolute_links.py -v
```
Save output to reports/agents/<agent>/TC-954/test_run.txt

### Step 3: Audit pilot content for cross-subdomain links
After pilot run completes:
```bash
cd runs/<run_id>/content_preview/content/
grep -r "https://docs.aspose.org" . | head -2 > link_audit.txt
grep -r "https://reference.aspose.org" . | head -1 >> link_audit.txt
grep -r "https://products.aspose.org" . | head -1 >> link_audit.txt
grep -r "https://kb.aspose.org" . | head -1 >> link_audit.txt
```

### Step 4: Verify link format
Check that all 5 links use absolute URLs with correct subdomain prefixes

### Step 5: Document findings
Create report.md summarizing verification results

## Task-specific review checklist
1. [ ] TC-938 build_absolute_public_url() function reviewed and understood
2. [ ] TC-938 unit tests executed successfully
3. [ ] 5 cross-subdomain links extracted from pilot content
4. [ ] Products → Docs link uses https://docs.aspose.org/...
5. [ ] Docs → Reference link uses https://reference.aspose.org/...
6. [ ] KB → Docs link uses https://docs.aspose.org/...
7. [ ] Blog → Products link uses https://products.aspose.org/...
8. [ ] Reference → Docs link uses https://docs.aspose.org/...
9. [ ] Same-section links remain relative (not absolute)
10. [ ] All findings documented in link_audit.txt and report.md

## Failure modes

### Failure mode 1: Cross-subdomain links still relative
**Detection:** Audit shows links like `../../../reference.aspose.org/...` instead of `https://reference.aspose.org/...`
**Resolution:** Verify TC-938 link_transformer.py is being called by W6; check that build_absolute_public_url() detects cross-subdomain transitions; ensure link transformation happens after patch application; re-review TC-938 implementation for bugs
**Spec/Gate:** specs/38_link_resolution.md (Absolute URL requirements), TC-938

### Failure mode 2: TC-938 unit tests fail
**Detection:** pytest shows failures in test_tc_938_absolute_links.py
**Resolution:** Read test failure messages to identify issue; verify tests are up-to-date with current implementation; check if recent changes broke TC-938; create new taskcard to fix TC-938 if needed
**Spec/Gate:** TC-938 test contract

### Failure mode 3: Cannot find cross-subdomain links in pilot content
**Detection:** grep commands return empty results; no absolute URLs found in content_preview
**Resolution:** Verify TC-952 content export completed successfully; check that pilot generated pages across multiple subdomains; ensure W5 included cross-references in drafts; verify W6 link transformation actually ran
**Spec/Gate:** TC-952 (Content preview export), specs/18_site_repo_layout.md

## Deliverables
- reports/agents/<agent>/TC-954/link_audit.txt
- reports/agents/<agent>/TC-954/test_run.txt
- reports/agents/<agent>/TC-954/report.md
- reports/agents/<agent>/TC-954/self_review.md

## Acceptance checks
1. Review TC-938 implementation in [src/launch/resolvers/public_urls.py](src/launch/resolvers/public_urls.py) and [src/launch/workers/w6_linker_and_patcher/](src/launch/workers/w6_linker_and_patcher/)
2. Verify unit tests exist and pass: [tests/unit/workers/test_tc_938_absolute_links.py](tests/unit/workers/test_tc_938_absolute_links.py)
3. Run sample pilot and inspect 5 cross-subdomain links:
   - Products → Docs link: Must be `https://docs.aspose.org/...`
   - Docs → Reference link: Must be `https://reference.aspose.org/...`
   - KB → Docs link: Must be `https://docs.aspose.org/...`
   - Blog → Products link: Must be `https://products.aspose.org/...`
   - Reference → Docs link: Must be `https://docs.aspose.org/...`
4. Same-section links remain relative (e.g., docs to docs can be `../another-doc/`)
5. Document verification results in evidence
6. TC-938 unit tests pass
7. link_audit.txt contains 5 valid absolute URL examples
8. Report confirms TC-938 working correctly for pilots

## E2E verification
Run pilot and audit links:
```bash
.venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python
cd runs/<run_id>/content_preview/content/
grep -r "https://" . | grep -E "(docs|reference|products|kb|blog).aspose.org" | head -10
```

Expected artifacts:
- TC-938 unit tests pass (pytest output in test_run.txt)
- 5+ cross-subdomain links found in pilot content
- All cross-subdomain links use absolute URLs (https://subdomain.aspose.org/...)
- Same-section links remain relative (../another-page/)
- link_audit.txt documents 5 verified examples

## Integration boundary proven
**Upstream:** TC-938 implemented build_absolute_public_url() and link_transformer.py
**Downstream:** TC-954 verifies implementation works correctly in pilot runs
**Contract:** Cross-subdomain links must use absolute URLs; same-section links may remain relative; all 5 subdomains must be supported

## Self-review
- [ ] TC-938 implementation reviewed and understood
- [ ] TC-938 unit tests executed successfully
- [ ] 5 cross-subdomain links extracted and verified
- [ ] All absolute URLs use correct https://subdomain.aspose.org format
- [ ] Same-section links confirmed as relative (not absolute)
- [ ] Findings documented in link_audit.txt and report.md
- [ ] All required sections present per taskcard contract
- [ ] Verification-only scope maintained (no TC-938 modifications)
