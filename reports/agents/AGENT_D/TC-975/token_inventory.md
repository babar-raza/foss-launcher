# TC-975 Token Inventory

**Purpose**: Complete listing of all token placeholders used in the 3 new/modified templates for W5 SectionWriter integration.

---

## TOC Template Tokens

**Template**: `specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md`

| Token | Purpose | Section | Required |
|-------|---------|---------|----------|
| `__TITLE__` | Page title | Frontmatter | Yes |
| `__DESCRIPTION__` | SEO description | Frontmatter | Yes |
| `__SUMMARY__` | Summary text | Frontmatter | Yes |
| `__BODY_INTRO__` | Optional intro paragraph | Introduction | No |
| `__PRODUCT_NAME__` | Product name (e.g., "Aspose.3D for Python") | Introduction | Yes |
| `__PLATFORM__` | Platform name (e.g., "Python", "Java") | Introduction | Yes |
| `__URL_GETTING_STARTED__` | URL to getting started page | Documentation Index | Yes |
| `__URL_DEVELOPER_GUIDE__` | URL to developer guide | Documentation Index | Yes |
| `__CHILD_PAGES_LIST__` | Dynamically generated list of child pages | Documentation Index | Yes |
| `__URL_PRODUCTS__` | URL to products overview | Quick Links | Yes |
| `__URL_REFERENCE__` | URL to API reference | Quick Links | Yes |
| `__REPO_URL__` | GitHub repository URL | Quick Links | Yes |
| `__URL_KB__` | URL to knowledge base | Quick Links | Yes |

**Total Tokens**: 13
**Critical Tokens**: `__CHILD_PAGES_LIST__` (W4 must populate with all child page slugs)

---

## Comprehensive Developer Guide Template Tokens

**Template**: `specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/developer-guide/_index.md`

| Token | Purpose | Section | Required |
|-------|---------|---------|----------|
| `__TITLE__` | Page title | Frontmatter | Yes |
| `__DESCRIPTION__` | SEO description | Frontmatter | Yes |
| `__SUMMARY__` | Summary text | Frontmatter | Yes |
| `__BODY_INTRO__` | Optional intro paragraph | Introduction | No |
| `__PRODUCT_NAME__` | Product name | Introduction | Yes |
| `__URL_GETTING_STARTED__` | URL to getting started | Introduction | Yes |
| `__COMMON_SCENARIOS_SECTION__` | Common workflows with code (50-70% of workflows) | Common Scenarios | Yes |
| `__ADVANCED_SCENARIOS_SECTION__` | Advanced workflows with code (30-50% of workflows) | Advanced Scenarios | Yes |
| `__URL_REFERENCE__` | URL to API reference | Additional Resources | Yes |
| `__URL_KB__` | URL to knowledge base | Additional Resources | Yes |
| `__REPO_URL__` | GitHub repository URL | Additional Resources | Yes |

**Total Tokens**: 11
**Critical Tokens**:
- `__COMMON_SCENARIOS_SECTION__` (W5 must generate all common workflows)
- `__ADVANCED_SCENARIOS_SECTION__` (W5 must generate all advanced workflows)

**Note**: scenario_coverage must be "all" - W5 must populate ALL workflows from product_facts.workflows

---

## Feature Showcase Template Tokens

**Template**: `specs/templates/kb.aspose.org/3d/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-feature-showcase.md`

| Token | Purpose | Section | Required |
|-------|---------|---------|----------|
| `__TITLE__` | Page title (e.g., "How to: Convert 3D Models") | Frontmatter | Yes |
| `__DESCRIPTION__` | SEO description | Frontmatter | Yes |
| `__SUMMARY__` | Summary text | Frontmatter | Yes |
| `__WEIGHT__` | Page weight for ordering | Frontmatter | Yes |
| `__KEYWORD_1__` | SEO keyword 1 | Frontmatter | Yes |
| `__KEYWORD_2__` | SEO keyword 2 | Frontmatter | Yes |
| `__KEYWORD_3__` | SEO keyword 3 | Frontmatter | Yes |
| `__FEATURE_OVERVIEW__` | Feature description paragraph | Overview | Yes |
| `__FEATURE_CLAIM_ID__` | Claim ID for tracking | Overview | Yes |
| `__USE_CASE_1__` | Use case bullet 1 | When to Use | Yes |
| `__USE_CASE_2__` | Use case bullet 2 | When to Use | Yes |
| `__USE_CASE_3__` | Use case bullet 3 | When to Use | Yes |
| `__FEATURE_STEPS__` | Optional intro to steps | Step-by-Step Guide | No |
| `__STEP_1__` | Step 1 description | Step-by-Step Guide | Yes |
| `__STEP_2__` | Step 2 description | Step-by-Step Guide | Yes |
| `__STEP_3__` | Step 3 description | Step-by-Step Guide | Yes |
| `__STEP_4__` | Step 4 description | Step-by-Step Guide | Yes |
| `__LANGUAGE__` | Programming language (e.g., python, java) | Code Example | Yes |
| `__FEATURE_CODE__` | Code snippet | Code Example | Yes |
| `__URL_DEVELOPER_GUIDE__` | URL to developer guide | Related Links | Yes |
| `__URL_API_REFERENCE__` | URL to API reference | Related Links | Yes |
| `__URL_REPO_EXAMPLE__` | URL to GitHub example | Related Links | Yes |

**Total Tokens**: 22
**Critical Tokens**:
- `__FEATURE_CLAIM_ID__` (Must be valid claim ID from Truth Lock)
- `__FEATURE_CODE__` (Must be syntactically correct code for the feature)

---

## Token Format Validation

All tokens follow the standard format:
- **Pattern**: `__UPPERCASE__` (double underscore prefix and suffix)
- **Case**: All uppercase with underscores separating words
- **No Alternative Formats**: No `{TOKEN}`, `{{TOKEN}}`, or `$TOKEN` formats used

**Verification Command**:
```bash
grep -o "__[A-Z_]*__" template.md | sort | uniq
```

---

## Token Replacement Rules for W5

### Required Tokens
W5 MUST replace all tokens marked as "Required: Yes" in the tables above. Missing required tokens will result in incomplete content.

### Optional Tokens
W5 MAY leave optional tokens empty (replace with empty string) if content is not available:
- `__BODY_INTRO__` (TOC and Developer Guide)
- `__FEATURE_STEPS__` (Feature Showcase)

### Token Sources
W5 should populate tokens from these sources:
- Product facts: `__PRODUCT_NAME__`, `__PLATFORM__`
- URL generation: `__URL_*__` tokens (based on site structure)
- Repository metadata: `__REPO_URL__`
- Claims: `__FEATURE_CLAIM_ID__`, `__FEATURE_OVERVIEW__`, `__USE_CASE_*__`
- Snippets: `__FEATURE_CODE__`, `__LANGUAGE__`
- Page plan: `__TITLE__`, `__DESCRIPTION__`, `__SUMMARY__`, `__WEIGHT__`
- Child pages: `__CHILD_PAGES_LIST__` (from content_strategy.child_pages)
- Workflows: `__COMMON_SCENARIOS_SECTION__`, `__ADVANCED_SCENARIOS_SECTION__`

---

## Integration Notes

### W4 IAPlanner Responsibilities
W4 must populate these fields in page_plan for W5 to use:
- `content_strategy.child_pages` → becomes `__CHILD_PAGES_LIST__`
- `content_strategy.scenario_coverage` = "all" → W5 includes all workflows
- Assign `page_role` = "toc" | "comprehensive_guide" | "feature_showcase" → triggers template selection

### W5 SectionWriter Responsibilities
W5 must:
1. Select correct template based on page_role
2. Load template file
3. Replace all tokens with actual values from:
   - ProductFacts
   - Page plan
   - Snippet catalog
   - Claim catalog
   - URL generator
4. Validate no unreplaced tokens remain (should not have `__*__` in output)

### W7 Validator Gate 14 Checks
W7 must verify:
- TOC pages have NO code snippets (BLOCKER if violated)
- Feature showcase pages have claim marker present
- Comprehensive guide pages cover all workflows
- All forbidden topics rules respected

---

## Appendix: Token Naming Conventions

**Established Patterns**:
- `__URL_*__` - URLs to other pages/sections
- `__BODY_*__` - Large content blocks
- `__*_SECTION__` - Section-level content (multiple paragraphs/headings)
- `__FEATURE_*__` - Feature-specific content
- `__STEP_*__` - Individual steps in guides
- `__USE_CASE_*__` - Use case descriptions

**Future Token Additions**:
When adding new tokens, follow these conventions:
- Use `__UPPERCASE__` format
- Use descriptive names (not abbreviations)
- Group related tokens with common prefix
- Document in this inventory file
