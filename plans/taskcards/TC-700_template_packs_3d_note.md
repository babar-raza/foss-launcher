---
id: TC-700
title: "Template Packs + Mandatory/Optional Page Contract (3D + Note Families)"
status: Done
owner: "TEMPLATES_AGENT"
updated: "2026-01-30"
depends_on:
  - TC-430
allowed_paths:
  - specs/templates/products.aspose.org/3d/**
  - specs/templates/products.aspose.org/note/**
  - specs/templates/docs.aspose.org/3d/**
  - specs/templates/docs.aspose.org/note/**
  - specs/templates/kb.aspose.org/3d/**
  - specs/templates/kb.aspose.org/note/**
  - specs/templates/reference.aspose.org/3d/**
  - specs/templates/reference.aspose.org/note/**
  - specs/templates/blog.aspose.org/3d/**
  - specs/templates/blog.aspose.org/note/**
  - specs/06_page_planning.md
  - specs/templates/README.md
  - reports/agents/**/TC-700/**
evidence_required:
  - reports/agents/<agent>/TC-700/report.md
  - reports/agents/<agent>/TC-700/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-700 — Template Packs + Mandatory/Optional Page Contract (3D + Note Families)

## Objective
Create template packs for families "3d" and "note" by copying and adapting existing "cells" templates. Define mandatory vs optional page contract to enable W4 IA Planner to enumerate pages for Pilot-1 (3D) and Pilot-2 (Note).

## Required spec references
- specs/06_page_planning.md
- specs/20_rulesets_and_templates_registry.md
- specs/21_worker_contracts.md (W4)
- specs/templates/README.md

## Scope
### In scope
- Copy "cells" templates to create "3d" and "note" template directories across all 5 subdomains
- Update README files to reference correct family names
- Ensure all templates use `__FAMILY__` token placeholders (no hardcoded family text)
- Document mandatory vs optional page contract in specs/06_page_planning.md
- Update specs/templates/README.md with family documentation

### Out of scope
- Template-driven enumeration logic (handled by W4)
- Content generation (handled by W5+)
- Template variant selection implementation

## Inputs
- Existing specs/templates/*/cells/ directories
- specs/06_page_planning.md
- specs/templates/README.md

## Outputs
- 10 new template directories (5 subdomains × 2 families)
- Updated specs/06_page_planning.md with page contract
- Updated specs/templates/README.md with families documentation

## Allowed paths
- specs/templates/products.aspose.org/3d/**
- specs/templates/products.aspose.org/note/**
- specs/templates/docs.aspose.org/3d/**
- specs/templates/docs.aspose.org/note/**
- specs/templates/kb.aspose.org/3d/**
- specs/templates/kb.aspose.org/note/**
- specs/templates/reference.aspose.org/3d/**
- specs/templates/reference.aspose.org/note/**
- specs/templates/blog.aspose.org/3d/**
- specs/templates/blog.aspose.org/note/**
- specs/06_page_planning.md
- specs/templates/README.md
- reports/agents/**/TC-700/**

## Implementation steps
1) **Copy cells templates to 3d**:
   - Copy all 5 subdomain template directories (products, docs, kb, reference, blog)
   - Update README files to replace "cells" with "3d"
   - Verify no hardcoded family text in template content (only in READMEs)

2) **Copy cells templates to note**:
   - Copy all 5 subdomain template directories
   - Update README files to replace "cells" with "note"
   - Verify no hardcoded family text in template content

3) **Verify token placeholders**:
   - Ensure all templates use `__FAMILY__` token (not hardcoded)
   - Verify all other tokens preserved (`__LOCALE__`, `__PLATFORM__`, etc.)

4) **Document page contract**:
   - Add "Mandatory vs Optional Pages (Page Contract)" section to specs/06_page_planning.md
   - Define which pages MUST exist for minimal launch
   - Define which pages MAY exist based on evidence and quotas

5) **Update templates README**:
   - Add "Template Families" section (cells, 3d, note)
   - Add "Quotas and Page Selection" section
   - Add "Variant Selection Rules" section

## Failure modes

### Failure mode 1: Hardcoded family name "cells" remains in copied template content breaking 3d/note families
**Detection:** grep -r "cells" specs/templates/*/3d/ specs/templates/*/note/ finds hardcoded family text (excluding READMEs); W5 generates pages with wrong family name; validation fails
**Resolution:** Review template copy process; ensure all template .md files use __FAMILY__ token instead of hardcoded "cells"; verify READMEs updated to reference correct family; check that no hardcoded product names in template frontmatter or body; run find+sed to replace cells→__FAMILY__ in template content only (not README)
**Spec/Gate:** specs/20_rulesets_and_templates_registry.md (template token contract), Gate F (template lint)

### Failure mode 2: Token placeholders __FAMILY__ or __PLATFORM__ corrupted during copy losing template variables
**Detection:** grep cannot find __FAMILY__ tokens in new 3d/note templates; template rendering fails with undefined variables; W5 section writer errors
**Resolution:** Verify copy operation preserves all token placeholders; check that cp/rsync command doesn't modify file content; ensure __FAMILY__, __LOCALE__, __PLATFORM__, __SUBDOMAIN__ tokens intact in copied files; restore from cells templates if corrupted; validate token format (double underscores) matches template engine expectations
**Spec/Gate:** specs/06_page_planning.md (template contract), specs/20_rulesets_and_templates_registry.md (token placeholders)

### Failure mode 3: README files not updated still reference "cells" instead of family-specific names
**Detection:** READMEs in specs/templates/*/3d/ or */note/ directories still say "cells"; misleading documentation; operators confused about which templates for which family
**Resolution:** Update all README files with search-and-replace for family name; verify each README references correct family (3d or note); check that directory purpose described correctly; ensure no copy-paste errors from cells templates; review all 10 READMEs (5 subdomains × 2 families)
**Spec/Gate:** Documentation standards, specs/templates/README.md (template families documentation)

### Failure mode 4: Incomplete template directory structure missing subdomains for 3d or note families
**Detection:** ls specs/templates/*/3d/ or */note/ shows <10 total directories; expected 5 subdomains × 2 families = 10 directories; W4 enumeration fails for missing subdomain
**Resolution:** Verify copy operation completed for all 5 subdomains (products, docs, kb, reference, blog); check that both 3d and note have full coverage; review copy script or manual process for completeness; ensure directory permissions allow write; document template directory structure in specs/templates/README.md
**Spec/Gate:** specs/20_rulesets_and_templates_registry.md (registry structure), specs/templates/README.md (families documentation)

## Task-specific review checklist

Beyond the standard acceptance checks, verify:
- [ ] All 10 template directories exist (5 subdomains × 2 families)
- [ ] No hardcoded "cells" text in 3d template content (excluding READMEs)
- [ ] No hardcoded "cells" text in note template content (excluding READMEs)
- [ ] All templates use `__FAMILY__` token placeholders
- [ ] README files reference correct family names ("3d" or "note")
- [ ] specs/06_page_planning.md includes page contract section
- [ ] specs/templates/README.md documents all 3 families

## E2E verification
**Concrete command(s) to run:**
```bash
# Verify template directories exist
ls specs/templates/*/3d/ specs/templates/*/note/

# Verify no hardcoded family text (should return empty)
grep -r "cells" specs/templates/products.aspose.org/3d/ --exclude="README.md"

# Verify tokens are preserved (should find matches)
grep -r "__FAMILY__" specs/templates/products.aspose.org/3d/ | head -3
```

**Expected artifacts:**
- 10 new template directories
- Updated specs/06_page_planning.md
- Updated specs/templates/README.md

**Success criteria:**
- [ ] All template directories exist
- [ ] No hardcoded family text in content
- [ ] Token placeholders preserved
- [ ] Documentation updated

## Integration boundary proven
What upstream/downstream wiring was validated:
- Downstream: TC-701 (W4 uses templates for path enumeration)
- Downstream: TC-440 (W5 uses templates for content generation)
- Contracts: Template token format, page contract

## Deliverables
- Code:
  - 10 new template directories with complete structure
- Specs:
  - Updated specs/06_page_planning.md
  - Updated specs/templates/README.md
- Reports:
  - reports/agents/<agent>/TC-700/report.md
  - reports/agents/<agent>/TC-700/self_review.md

## Acceptance checks
- [ ] All 10 template directories exist with complete structure
- [ ] No hardcoded family text in template content (verified by grep)
- [ ] All templates use `__FAMILY__` token placeholders
- [ ] README files reference correct family names
- [ ] Page contract documented in specs/06_page_planning.md
- [ ] Template families documented in specs/templates/README.md

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
