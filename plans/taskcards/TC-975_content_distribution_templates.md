---
id: TC-975
title: "Content Distribution Templates"
status: Ready
priority: Critical
owner: "Agent D (Docs & Specs)"
updated: "2026-02-04"
tags: ["templates", "content-distribution", "phase-2"]
depends_on: ["TC-971"]
allowed_paths:
  - plans/taskcards/TC-975_content_distribution_templates.md
  - specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md
  - specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/developer-guide/_index.md
  - specs/templates/kb.aspose.org/3d/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-feature-showcase.md
evidence_required:
  - reports/agents/AGENT_D/TC-975/evidence.md
  - reports/agents/AGENT_D/TC-975/self_review.md
spec_ref: "3e91498d6b9dbda85744df6bf8d5f3774ca39c60"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-975 — Content Distribution Templates

## Objective
Create 3 new template files for specialized content types (TOC, comprehensive developer guide, feature showcase) used by W5 SectionWriter specialized generators to produce consistent, spec-compliant content.

## Problem Statement
The FOSS Launcher system lacks template files for the new page roles introduced by the content distribution strategy:
1. No TOC template (docs/_index.md) - navigation hub structure undefined
2. No comprehensive developer guide template (docs/developer-guide/_index.md) - workflow listing format undefined
3. No feature showcase template (kb/how-to-*.md) - how-to article structure undefined

Without these templates, W5 specialized generators have no reference structure for consistent content generation, leading to inconsistent formatting and missing required sections.

## Required spec references
- C:\Users\prora\.claude\plans\magical-prancing-fountain.md (Primary implementation plan, Phase 2 Tasks 2.5-2.7)
- specs/07_section_templates.md (Updated by TC-971 - defines template types)
- specs/08_content_distribution_strategy.md (From TC-971 - defines content rules per role)
- specs/templates/ (Existing templates directory structure)
- CONTRIBUTING.md (No manual edits policy)

## Scope

### In scope
- Create TOC template: specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md (~50 lines)
- Create comprehensive developer guide template: specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/developer-guide/_index.md (~40 lines)
- Create feature showcase template: specs/templates/kb.aspose.org/3d/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-feature-showcase.md (~60 lines)
- All templates use Hugo frontmatter format
- All templates use token placeholders (__TOKEN_NAME__)
- Templates follow specs/07 template type definitions exactly

### Out of scope
- W4 IAPlanner modifications (covered by TC-972)
- W5 SectionWriter generator implementation (covered by TC-973)
- W7 Validator Gate 14 implementation (covered by TC-974)
- Spec/schema creation (covered by TC-971)
- Template rendering logic (W5 already has token replacement)
- Modification of existing templates (products, blog, reference unchanged)

## Inputs
- specs/07_section_templates.md (updated by TC-971 with template type definitions)
- specs/08_content_distribution_strategy.md (from TC-971 with content rules)
- Existing template structure in specs/templates/ for reference
- Hugo frontmatter format requirements
- Token placeholder conventions (__TOKEN__)

## Outputs
- specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md (NEW, ~50 lines)
- specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/developer-guide/_index.md (NEW, ~40 lines)
- specs/templates/kb.aspose.org/3d/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-feature-showcase.md (NEW, ~60 lines)
- Git diff showing 3 new template files
- Evidence showing templates have correct structure (frontmatter + body)
- Evidence showing all required tokens present

## Allowed paths
- plans/taskcards/TC-975_content_distribution_templates.md
- specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md
- specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/developer-guide/_index.md
- specs/templates/kb.aspose.org/3d/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-feature-showcase.md

### Allowed paths rationale
TC-975 creates template files in specs/templates/ directory. All templates are under 3d family pattern (used as reference for other families). No code modifications, only template file creation.

## Implementation steps

### Step 1: Create TOC template
Create new file at specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md for table of contents pages.

**Structure:**
```markdown
---
title: "__TITLE__"
description: "__DESCRIPTION__"
summary: "__SUMMARY__"
weight: 1
type: docs
---

__BODY_INTRO__

Welcome to the __PRODUCT_NAME__ documentation. This comprehensive guide covers all aspects of using __PRODUCT_NAME__ in your __PLATFORM__ applications.

## Documentation Index

### Getting Started
- [Getting Started](__URL_GETTING_STARTED__) - Installation instructions and first task

### Developer Guide
- [Developer Guide](__URL_DEVELOPER_GUIDE__) - Comprehensive listing of all usage scenarios with source code

### Additional Topics

__CHILD_PAGES_LIST__

## Quick Links

- [Product Overview](__URL_PRODUCTS__)
- [API Reference](__URL_REFERENCE__)
- [Code Examples on GitHub](__REPO_URL__)
- [Knowledge Base](__URL_KB__)
```

**Tokens:**
- __TITLE__ - Page title
- __DESCRIPTION__ - SEO description
- __SUMMARY__ - Summary text
- __PRODUCT_NAME__ - Product name (e.g., "Aspose.3D for Python")
- __PLATFORM__ - Platform name (e.g., "Python", "Java")
- __BODY_INTRO__ - Optional intro paragraph
- __URL_GETTING_STARTED__ - URL to getting started page
- __URL_DEVELOPER_GUIDE__ - URL to developer guide
- __CHILD_PAGES_LIST__ - Dynamically generated list of child pages
- __URL_PRODUCTS__ - URL to products overview
- __URL_REFERENCE__ - URL to API reference
- __REPO_URL__ - GitHub repository URL
- __URL_KB__ - URL to knowledge base

**Critical:** NO code snippets (``` blocks) - violates Gate 14

**Acceptance:** File created with correct structure, all tokens present, no code snippets

### Step 2: Create comprehensive developer guide template
Create new file at specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/developer-guide/_index.md for comprehensive scenario listing.

**Structure:**
```markdown
---
title: "__TITLE__"
description: "__DESCRIPTION__"
summary: "__SUMMARY__"
weight: 20
type: docs
---

__BODY_INTRO__

This guide provides a comprehensive listing of all major usage scenarios for __PRODUCT_NAME__. Each scenario includes a brief description, source code example, and links to related resources.

## Common Scenarios

__SCENARIOS_SECTION__

## Additional Resources

- [Getting Started](__URL_GETTING_STARTED__)
- [API Reference](__URL_REFERENCE__)
- [Knowledge Base](__URL_KB__)
- [GitHub Repository](__REPO_URL__)
```

**Tokens:**
- __TITLE__ - Page title
- __DESCRIPTION__ - SEO description
- __SUMMARY__ - Summary text
- __PRODUCT_NAME__ - Product name
- __BODY_INTRO__ - Optional intro paragraph
- __SCENARIOS_SECTION__ - Dynamically generated scenarios (H3 + description + code + link per workflow)
- __URL_GETTING_STARTED__ - URL to getting started
- __URL_REFERENCE__ - URL to API reference
- __URL_KB__ - URL to knowledge base
- __REPO_URL__ - GitHub repository URL

**Critical:** MUST cover ALL workflows (scenario_coverage="all")

**Acceptance:** File created with correct structure, scenarios section placeholder present

### Step 3: Create feature showcase template
Create new file at specs/templates/kb.aspose.org/3d/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-feature-showcase.md for KB how-to articles.

**Structure:**
```markdown
---
title: "__TITLE__"
description: "__DESCRIPTION__"
summary: "__SUMMARY__"
weight: __WEIGHT__
type: kb
keywords: [__KEYWORD_1__, __KEYWORD_2__, __KEYWORD_3__]
---

## Overview

__FEATURE_OVERVIEW__

<!-- claim_id:__FEATURE_CLAIM_ID__ -->

## When to Use

This feature is particularly useful when:
- __USE_CASE_1__
- __USE_CASE_2__
- __USE_CASE_3__

## Step-by-Step Guide

__FEATURE_STEPS__

1. __STEP_1__
2. __STEP_2__
3. __STEP_3__
4. __STEP_4__

## Code Example

```__LANGUAGE__
__FEATURE_CODE__
```

## Related Links

- [Developer Guide](__URL_DEVELOPER_GUIDE__)
- [API Reference](__URL_API_REFERENCE__)
- [Full Example on GitHub](__URL_REPO_EXAMPLE__)
```

**Tokens:**
- __TITLE__ - Page title (e.g., "How to: Convert 3D Models")
- __DESCRIPTION__ - SEO description
- __SUMMARY__ - Summary text
- __WEIGHT__ - Page weight for ordering
- __KEYWORD_1__, __KEYWORD_2__, __KEYWORD_3__ - SEO keywords
- __FEATURE_OVERVIEW__ - Feature description paragraph
- __FEATURE_CLAIM_ID__ - Claim ID for tracking
- __USE_CASE_1__, __USE_CASE_2__, __USE_CASE_3__ - Use case bullets
- __FEATURE_STEPS__ - Optional intro to steps
- __STEP_1__, __STEP_2__, __STEP_3__, __STEP_4__ - Step descriptions
- __LANGUAGE__ - Programming language (e.g., python, java)
- __FEATURE_CODE__ - Code snippet
- __URL_DEVELOPER_GUIDE__ - URL to developer guide
- __URL_API_REFERENCE__ - URL to API reference
- __URL_REPO_EXAMPLE__ - URL to GitHub example

**Critical:** Single feature focus only (1 primary claim)

**Acceptance:** File created with correct structure, claim marker present, code example section present

### Step 4: Validate template structure
Verify all templates have correct Hugo frontmatter and required sections.

**Validation checks:**
1. Frontmatter starts with `---` and ends with `---`
2. Required frontmatter fields present: title, description, summary, weight, type
3. Body content uses markdown H2 headings (##)
4. Token placeholders use __UPPERCASE__ format
5. No hardcoded values (all dynamic content uses tokens)
6. Templates follow specs/07 template type definitions

**Commands:**
```bash
# Check frontmatter syntax
head -n 10 specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md | grep -c "^---$"  # Should be 2

# Check for hardcoded URLs (should be none)
grep -E "https?://" specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md  # Should find none

# Check for token placeholders
grep -o "__[A-Z_]*__" specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md | sort | uniq

# Lint markdown
make lint
```

**Acceptance:** All validation checks pass, templates follow conventions

### Step 5: Create git diff summary
Generate evidence of changes for audit trail.

```bash
# Git status
git status --short | grep "specs/templates/"

# Git diff (should show 3 new files)
git diff --cached specs/templates/ > reports/agents/AGENT_D/TC-975/changes.diff

# Count lines per template
wc -l specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md
wc -l specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/developer-guide/_index.md
wc -l specs/templates/kb.aspose.org/3d/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-feature-showcase.md
```

**Acceptance:** Git shows 3 new files, line counts match expectations (~50, ~40, ~60)

### Step 6: Cross-reference with specs
Verify templates match specs/07_section_templates.md template type definitions.

**Cross-reference checks:**
1. TOC template has required headings: Introduction, Documentation Index, Quick Links
2. Comprehensive guide template has required headings: Introduction, Common Scenarios, Additional Resources
3. Feature showcase template has required headings: Overview, When to Use, Step-by-Step Guide, Code Example, Related Links
4. All templates use correct Hugo type (docs for TOC/guide, kb for showcase)
5. All templates follow content distribution strategy rules (specs/08)

**Acceptance:** All templates match spec definitions exactly

## Failure modes

### Failure mode 1: Template missing required frontmatter fields
**Detection:** Hugo build fails with "missing required field" error; validation check fails with grep showing <2 "---" lines; W5 generator fails to parse template
**Resolution:** Review Hugo frontmatter requirements (title, description, summary, weight, type all required); check for typos in field names; ensure frontmatter is at top of file; verify closing "---" present; compare with existing templates for reference
**Spec/Gate:** Hugo documentation (frontmatter requirements), specs/07_section_templates.md

### Failure mode 2: TOC template includes code snippets (Gate 14 blocker)
**Detection:** Template validation finds ``` in TOC template; W7 Gate 14 fails with GATE14_TOC_HAS_SNIPPETS when using this template; manual review shows code blocks
**Resolution:** Remove all triple backticks from template; scan for ``` in file; verify no code example sections present; TOC should only have links and text; use grep to confirm: `grep -c '```' _index.md` should return 0
**Spec/Gate:** specs/08_content_distribution_strategy.md TOC section (forbidden: code_snippets), specs/09_validation_gates.md Gate 14 Rule 2

### Failure mode 3: Template has hardcoded values instead of tokens
**Detection:** Grep finds hardcoded URLs, product names, or version numbers; template not reusable across products; W5 generator produces wrong content
**Resolution:** Replace all hardcoded content with token placeholders; scan for URLs: `grep -E "https?://" template.md`; scan for product names: `grep -i "aspose" template.md` (should only be in path, not content); verify all dynamic content uses __TOKEN__ format
**Spec/Gate:** specs/07_section_templates.md (templates must be reusable)

### Failure mode 4: Token placeholder format inconsistent
**Detection:** Template has {TOKEN}, {{TOKEN}}, or $TOKEN instead of __TOKEN__; W5 generator doesn't replace tokens; generated content has placeholder text
**Resolution:** Standardize all tokens to __UPPERCASE__ format; search for other formats: `grep -E "\{[A-Z_]+\}" template.md`; verify all tokens use double underscore prefix/suffix; compare with existing templates for convention
**Spec/Gate:** Internal convention (W5 expects __TOKEN__ format)

### Failure mode 5: Feature showcase template missing claim marker
**Detection:** Template validation doesn't find `<!-- claim_id:` marker; W7 Gate 14 fails to validate claim tracking; generated showcase articles missing claim markers
**Resolution:** Add claim marker in Overview section: `<!-- claim_id:__FEATURE_CLAIM_ID__ -->`; verify HTML comment format correct; ensure marker is on its own line; check existing templates for claim marker examples
**Spec/Gate:** specs/08_content_distribution_strategy.md (claim tracking required), Truth Lock system (claim markers mandatory)

## Task-specific review checklist
1. [ ] TOC template created at correct path with ~50 lines
2. [ ] TOC template has NO code snippets (``` blocks) - critical for Gate 14
3. [ ] TOC template has required headings: Introduction, Documentation Index, Quick Links
4. [ ] Comprehensive guide template created at correct path with ~40 lines
5. [ ] Comprehensive guide template has scenarios section placeholder (__SCENARIOS_SECTION__)
6. [ ] Feature showcase template created at correct path with ~60 lines
7. [ ] Feature showcase template has claim marker: `<!-- claim_id:__FEATURE_CLAIM_ID__ -->`
8. [ ] All templates have valid Hugo frontmatter (starts/ends with ---, has required fields)
9. [ ] All tokens use __UPPERCASE__ format (no {}, {{}}, $ formats)
10. [ ] No hardcoded values (all dynamic content uses tokens)
11. [ ] Templates match specs/07 template type definitions exactly
12. [ ] Git diff shows 3 new files with expected line counts

## Deliverables
- specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md (NEW, ~50 lines)
- specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/developer-guide/_index.md (NEW, ~40 lines)
- specs/templates/kb.aspose.org/3d/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-feature-showcase.md (NEW, ~60 lines)
- Git diff summary at reports/agents/AGENT_D/TC-975/changes.diff
- Token inventory for each template (list of all __TOKENS__ used)
- Validation output showing frontmatter syntax correct
- Evidence bundle at reports/agents/AGENT_D/TC-975/evidence.md
- Self-review at reports/agents/AGENT_D/TC-975/self_review.md (12 dimensions, scores 1-5)

## Acceptance checks
1. [ ] All 3 template files created at correct paths
2. [ ] TOC template has NO code snippets (grep '```' returns 0)
3. [ ] All templates have valid Hugo frontmatter (title, description, summary, weight, type)
4. [ ] All templates use token placeholders (__TOKEN__ format)
5. [ ] No hardcoded values in templates (grep for URLs returns none in content)
6. [ ] TOC template has 3 required sections: Introduction, Documentation Index, Quick Links
7. [ ] Comprehensive guide template has 2 required sections: Common Scenarios, Additional Resources
8. [ ] Feature showcase template has 5 required sections: Overview, When to Use, Steps, Code, Links
9. [ ] Feature showcase template has claim marker in Overview
10. [ ] Templates match specs/07 definitions exactly
11. [ ] Lint passes (make lint exits 0)
12. [ ] Git status shows 3 new files in specs/templates/

## Preconditions / dependencies
- TC-971 completed (specs/07 has template type definitions)
- Access to specs/templates/ directory structure
- Knowledge of Hugo frontmatter format
- Token placeholder conventions understood
- Git repository is clean (no conflicting changes)

## Self-review
[To be completed by Agent D after implementation]

Dimensions to score (1-5, need 4+ on all):
1. Coverage: All 3 templates created with required sections ✓
2. Correctness: Templates match specs/07 definitions exactly ✓
3. Evidence: Git diff + token inventory + validation output ✓
4. Test Quality: N/A (templates are data files, not code)
5. Maintainability: Clear structure, well-commented, reusable ✓
6. Safety: No breaking changes, templates are new files ✓
7. Security: N/A (no code execution, just markdown templates)
8. Reliability: Templates render correctly in Hugo ✓
9. Observability: N/A
10. Performance: N/A
11. Compatibility: Works with existing W5 token replacement logic ✓
12. Docs/Specs Fidelity: Matches specs/07 and specs/08 exactly ✓

## E2E verification
After TC-971, TC-972, TC-973, TC-974, TC-975 complete:
1. Run pilot with updated system
2. Verify W5 can load and parse all 3 templates
3. Verify W5 generates docs/_index.md using TOC template
4. Verify W5 generates docs/developer-guide/_index.md using comprehensive guide template
5. Verify W5 generates kb/how-to-*.md using feature showcase template
6. Verify generated content has tokens replaced (no __TOKEN__ placeholders remain)
7. Verify Hugo builds successfully with generated content
8. Visual inspection: generated pages look correct in browser

## Integration boundary proven
**Boundary:** specs/templates/ (template files) → W5 SectionWriter (content generation)

**Contract:** W5 reads template files, replaces tokens with actual values, and generates content. Templates provide structure and required sections per specs/07 and specs/08.

**Verification:** After all 5 taskcards complete:
1. W5 loads TOC template → generates docs/_index.md with child list
2. W5 loads comprehensive guide template → generates developer-guide/_index.md with all workflows
3. W5 loads feature showcase template → generates kb/how-to-*.md with single feature
4. End-to-end test shows all generated content matches template structure
5. No __TOKEN__ placeholders remain in generated content (all replaced)
