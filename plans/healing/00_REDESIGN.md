# FOSS Launcher Content Pipeline: Comprehensive Redesign

**Date**: 2026-02-19  
**Status**: PROPOSED  
**Scope**: Complete pipeline redesign for origin-level prevention

## Executive Summary

The current FOSS launcher content pipeline fails to produce high-quality documentation that passes all validation gates 100% of the time. After 20+ rounds of incremental fixes, the root causes are clear: the system relies on reactive fixes (regex, post-hoc validation) rather than proactive prevention (AST parsing, pre-generation validation).

**Root Causes**:
1. Generators receive isolated claims without source context, leading to generic content
2. 40+ regex-based sanitizers are brittle and break when content patterns change
3. Validation happens after generation, wasting tokens on rejected content
4. Token allocation treats all sections equally, causing imbalanced content quality
5. Single-turn generation produces content without intermediate review
6. Claim extraction is context-unaware, missing important details
7. Cross-section consistency is never checked, allowing conflicting information

**Highest-Impact Fixes**:
1. Pass source excerpts to generators (fixes generic content)
2. Replace regex with AST parsing (fixes brittleness)
3. Add pre-generation validation (fixes wasted tokens)
4. Add priority weights to token allocation (fixes imbalanced quality)
5. Implement outline→expand→review cycle (fixes quality issues)
6. Add context-aware claim extraction (fixes missing details)
7. Add cross-section consistency checks (fixes conflicting information)

## Part 1: New Pipeline Contract

### 1.1 Information Collection and Segregation

**Current State**: Information is collected in a flat structure with claims, snippets, and metadata mixed together. This makes it hard to track provenance and context.

**New State**: Information is collected in a hierarchical structure with clear provenance:

```
product_facts/
├── repo_info/              # Repository metadata
│   ├── name
│   ├── url
│   ├── description
│   ├── primary_language
│   └── license
├── claims/                 # Claims with full provenance
│   ├── claim_id
│   ├── claim_text
│   ├── claim_kind
│   ├── citations/          # Source file references
│   │   ├── path
│   │   ├── line
│   │   ├── excerpt
│   │   └── context_before/after
│   └── metadata/           # Additional metadata
│       ├── confidence
│       └── extracted_at
├── snippets/               # Code snippets with context
│   ├── snippet_id
│   ├── snippet_code
│   ├── snippet_language
│   ├── snippet_context
│   └── related_claims/
└── sections/               # Section definitions
    ├── section_name
    ├── section_description
    ├── section_keywords
    ├── section_claims/
    └── section_tokens
```

**Key Changes**:
1. Claims include full citation context (file path, line, excerpt, surrounding context)
2. Snippets include surrounding code context for better grounding
3. Sections explicitly list their claims and token budget
4. All information has provenance tracking

### 1.2 Context Formation per Page Style

**Current State**: Context is formed ad-hoc for each generator, with no consistent approach.

**New State**: Context is formed using a template-driven approach with page-style-specific rules:

```python
# Page style context templates
PAGE_STYLE_CONTEXT_TEMPLATES = {
    "readme": {
        "structure": ["getting_started", "installation", "quick_start", "features", "usage"],
        "priority_weights": {"getting_started": 2.0, "installation": 2.0, "quick_start": 1.5},
        "required_claims": ["installation", "quick_start"],
        "max_sections": 10,
        "min_tokens_per_section": 100,
        "max_tokens_per_section": 2000,
    },
    "docs_readme": {
        "structure": ["overview", "getting_started", "tutorials", "how_to_guides", "reference"],
        "priority_weights": {"overview": 2.0, "getting_started": 2.0, "tutorials": 1.5},
        "required_claims": ["overview", "getting_started"],
        "max_sections": 15,
        "min_tokens_per_section": 100,
        "max_tokens_per_section": 2000,
    },
    "guide": {
        "structure": ["introduction", "prerequisites", "steps", "troubleshooting", "next_steps"],
        "priority_weights": {"prerequisites": 2.0, "steps": 2.0},
        "required_claims": ["prerequisites", "steps"],
        "max_sections": 8,
        "min_tokens_per_section": 150,
        "max_tokens_per_section": 3000,
    },
    "reference": {
        "structure": ["overview", "syntax", "parameters", "examples", "returns", "raises"],
        "priority_weights": {"syntax": 1.5, "parameters": 1.5, "examples": 1.5},
        "required_claims": ["syntax", "parameters", "examples"],
        "max_sections": 12,
        "min_tokens_per_section": 100,
        "max_tokens_per_section": 2500,
    },
    "tutorial": {
        "structure": ["introduction", "prerequisites", "step_1", "step_2", "step_3", "troubleshooting"],
        "priority_weights": {"prerequisites": 2.0, "step_1": 2.0, "step_2": 2.0, "step_3": 2.0},
        "required_claims": ["prerequisites", "step_1", "step_2", "step_3"],
        "max_sections": 10,
        "min_tokens_per_section": 200,
        "max_tokens_per_section": 4000,
    },
}
```

**Key Changes**:
1. Page styles have explicit structure definitions
2. Priority weights are configurable per page style
3. Required claims are enforced per page style
4. Token budgets are constrained per page style

### 1.3 Planner Avoidance of Family Imbalance

**Current State**: The planner allocates tokens based on fixed percentages, which can lead to one family getting too many tokens while another gets too few.

**New State**: The planner uses a balanced allocation algorithm:

```python
def balanced_token_allocation(
    total_tokens: int,
    sections: List[Dict[str, Any]],
    priority_weights: Dict[str, float],
) -> Dict[str, int]:
    """Allocate tokens based on priority weights with balancing.
    
    Ensures no section gets less than 50% of its base allocation
    and no section gets more than 200% of its base allocation.
    """
    # Calculate weighted scores
    weighted_scores = {}
    for section in sections:
        section_name = section["section_name"]
        base_tokens = section["section_tokens"]
        weight = priority_weights.get(section_name, 1.0)
        weighted_scores[section_name] = base_tokens * weight
    
    # Normalize to total tokens
    total_weighted = sum(weighted_scores.values())
    allocation = {}
    for section_name, weighted_score in weighted_scores.items():
        allocation[section_name] = int(total_tokens * weighted_score / total_weighted)
    
    # Apply min/max bounds
    for section_name in allocation:
        base_tokens = sections[section_name]["section_tokens"]
        allocation[section_name] = max(
            int(base_tokens * 0.5),  # At least 50%
            min(int(base_tokens * 2.0), allocation[section_name])  # At most 200%
        )
    
    return allocation
```

**Key Changes**:
1. Token allocation is based on priority weights
2. Min/max bounds prevent extreme imbalances
3. Allocation is recalculated for each page style

### 1.4 Generator Reliable Expansion

**Current State**: Generators produce content in a single turn, with no intermediate review.

**New State**: Generators use a multi-turn outline→expand→review cycle:

```python
def generate_content_multiturn(
    page_style: str,
    section_name: str,
    section_description: str,
    section_keywords: List[str],
    section_sections: List[Dict[str, Any]],
    section_claims: List[Dict[str, Any]],
    section_tokens: int,
    max_tokens: int,
    min_tokens: int,
    product_facts: Dict[str, Any],
    template: Dict[str, Any],
    llm_client: Any,
    llm_model: str,
    llm_temperature: float,
    llm_max_tokens: int,
    llm_timeout: float,
    llm_retry_count: int,
    llm_retry_delay: float,
) -> GenerationResult:
    """Generate content with multi-turn outline→expand→review cycle."""
    # Step 1: Generate outline
    outline = generate_outline(
        page_style=page_style,
        section_name=section_name,
        section_description=section_description,
        section_keywords=section_keywords,
        section_sections=section_sections,
        section_claims=section_claims,
        product_facts=product_facts,
        template=template,
        llm_client=llm_client,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
        llm_max_tokens=llm_max_tokens,
        llm_timeout=llm_timeout,
        llm_retry_count=llm_retry_count,
        llm_retry_delay=llm_retry_delay,
    )
    
    # Step 2: Expand outline
    content = expand_outline(
        page_style=page_style,
        section_name=section_name,
        section_description=section_description,
        section_keywords=section_keywords,
        section_sections=section_sections,
        section_claims=section_claims,
        outline=outline,
        product_facts=product_facts,
        template=template,
        llm_client=llm_client,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
        llm_max_tokens=llm_max_tokens,
        llm_timeout=llm_timeout,
        llm_retry_count=llm_retry_count,
        llm_retry_delay=llm_retry_delay,
    )
    
    # Step 3: Review content
    review_result = review_content(
        page_style=page_style,
        section_name=section_name,
        section_description=section_description,
        section_keywords=section_keywords,
        section_sections=section_sections,
        section_claims=section_claims,
        content=content,
        product_facts=product_facts,
        template=template,
        llm_client=llm_client,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
        llm_max_tokens=llm_max_tokens,
        llm_timeout=llm_timeout,
        llm_retry_count=llm_retry_count,
        llm_retry_delay=llm_retry_delay,
    )
    
    # Step 4: If review fails, regenerate with feedback
    if not review_result.get("is_valid", True):
        content = expand_outline_with_feedback(
            page_style=page_style,
            section_name=section_name,
            section_description=section_description,
            section_keywords=section_keywords,
            section_sections=section_sections,
            section_claims=section_claims,
            outline=outline,
            feedback=review_result.get("issues", []),
            product_facts=product_facts,
            template=template,
            llm_client=llm_client,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_tokens=llm_max_tokens,
            llm_timeout=llm_timeout,
            llm_retry_count=llm_retry_count,
            llm_retry_delay=llm_retry_delay,
        )
    
    return GenerationResult(
        outline=outline,
        content=content,
        review_issues=review_result.get("issues", []),
        is_valid=review_result.get("is_valid", True),
    )
```

**Key Changes**:
1. Multi-turn generation with outline, expand, and review steps
2. Review feedback is used to improve content
3. Content is validated before final output

### 1.5 Gate Upgrades for Origin-Level Prevention

**Current State**: Validation gates run post-generation, catching issues after content is produced.

**New State**: Validation gates run at multiple stages:

```python
# Pre-generation validation
def validate_pre_generation(ctx: PreGenValidationContext) -> PreGenValidationResult:
    """Validate content requirements before generation."""
    errors = []
    warnings = []
    
    # Check 1: Section has claims
    if not ctx.section_claims:
        errors.append("Section has no claims to generate content for")
    
    # Check 2: Section has description
    if not ctx.section_description:
        errors.append("Section has no description")
    
    # Check 3: Claims have citations
    uncited_claims = [c.get("claim_id", "unknown") for c in ctx.section_claims if not c.get("citations")]
    if uncited_claims:
        warnings.append(f"Claims without citations: {', '.join(uncited_claims)}")
    
    # Check 4: Claims have claim_text
    textless_claims = [c.get("claim_id", "unknown") for c in ctx.section_claims if not c.get("claim_text")]
    if textless_claims:
        errors.append(f"Claims without text: {', '.join(textless_claims)}")
    
    # Check 5: Claims have claim_kind
    kindless_claims = [c.get("claim_id", "unknown") for c in ctx.section_claims if not c.get("claim_kind")]
    if kindless_claims:
        errors.append(f"Claims without kind: {', '.join(kindless_claims)}")
    
    return PreGenValidationResult(
        is_valid=not errors,
        errors=errors,
        warnings=warnings,
    )

# Post-generation validation
def validate_post_generation(
    content: str,
    section_claims: List[Dict[str, Any]],
    page_style: str,
) -> PostGenValidationResult:
    """Validate content after generation."""
    issues = []
    
    # Check 1: Claims coverage
    for claim in section_claims:
        if claim.get("claim_text") not in content:
            issues.append({
                "type": "missing_claim",
                "claim_id": claim.get("claim_id"),
                "claim_text": claim.get("claim_text"),
            })
    
    # Check 2: Code snippet accuracy
    for claim in section_claims:
        if claim.get("claim_kind") == "code":
            snippet = claim.get("snippet_code", "")
            if snippet and snippet not in content:
                issues.append({
                    "type": "missing_code_snippet",
                    "claim_id": claim.get("claim_id"),
                    "snippet": snippet,
                })
    
    return PostGenValidationResult(
        is_valid=not issues,
        issues=issues,
    )
```

**Key Changes**:
1. Pre-generation validation catches issues before generation
2. Post-generation validation catches issues after generation
3. Validation is comprehensive and covers all aspects

## Part 2: Implementation Plan

### 2.1 Immediate (Fast, Low-Risk Changes)

1. **Pass source excerpts to generators** (TC-2370)
   - Add helper function to extract source context
   - Update context builders to include source excerpts
   - Update generator prompts to reference source excerpts
   - **Acceptance**: Generators receive source excerpts for 70%+ of claims

2. **Add pre-generation validation** (TC-2372)
   - Define pre-generation validation schema
   - Update generator to use pre-generation validation
   - Add validation metrics
   - **Acceptance**: Pre-generation validation catches 90%+ of issues before generation

3. **Add cross-section consistency checks** (TC-2376)
   - Define cross-section consistency checks
   - Update validator to use cross-section consistency checks
   - Add consistency metrics
   - **Acceptance**: Cross-section checks catch 80%+ of inconsistencies

### 2.2 Short-Term (Structural Changes)

1. **Replace regex with AST parser** (TC-2371)
   - Define zone types and parser
   - Rewrite sanitizers as zone processors
   - Create zone-aware pipeline runner
   - **Acceptance**: Zone parser correctly identifies all zone types (95%+ accuracy)

2. **Add priority weights to token allocation** (TC-2373)
   - Define priority weights per page style
   - Update token allocation to use priority weights
   - Add token allocation logging
   - **Acceptance**: Priority weights are applied correctly (95%+ accuracy)

3. **Implement outline→expand→review cycle** (TC-2374)
   - Define outline, expand, and review prompts
   - Implement multi-turn generation
   - Add multi-turn generation metrics
   - **Acceptance**: Multi-turn generation catches 80%+ of issues before final output

4. **Add context-aware claim extraction** (TC-2375)
   - Define context-aware claim extraction
   - Update claim extraction to use context-aware extraction
   - Add claim extraction metrics
   - **Acceptance**: Context extraction succeeds 95%+ of the time

### 2.3 Long-Term (Architecture Changes)

1. **Redesign information collection and segregation**
   - Implement hierarchical information structure
   - Add provenance tracking
   - Update all workers to use new structure
   - **Acceptance**: All information has provenance tracking

2. **Redesign context formation per page style**
   - Implement template-driven context formation
   - Add page-style-specific rules
   - Update all workers to use new context formation
   - **Acceptance**: Context formation is consistent across all pages

3. **Redesign planner to avoid family imbalance**
   - Implement balanced token allocation
   - Add min/max bounds
   - Update all workers to use balanced allocation
   - **Acceptance**: Token allocation is balanced across all families

4. **Redesign generator reliable expansion**
   - Implement multi-turn generation
   - Add review feedback loop
   - Update all workers to use multi-turn generation
   - **Acceptance**: Multi-turn generation catches 80%+ of issues before final output

5. **Redesign gates for origin-level prevention**
   - Implement pre-generation validation
   - Implement post-generation validation
   - Update all workers to use new gates
   - **Acceptance**: Gates catch 95%+ of issues before final output

## Part 3: Acceptance Criteria

### 3.1 Quality Gates

1. **Pass gates 100%**: All validation gates pass for all pages
2. **No manual fixes**: No manual content edits required
3. **No regex fixes**: No regex-based fixes required

### 3.2 Content Quality

1. **Repo-specific content**: All content is specific to the repository
2. **Accurate code snippets**: All code snippets match the repository
3. **Complete claims**: All claims are covered in the content
4. **Consistent terminology**: All sections use consistent terminology

### 3.3 Pipeline Performance

1. **Generation time**: Content generation completes in under 10 minutes
2. **Validation time**: Validation completes in under 5 minutes
3. **Token efficiency**: 90%+ of tokens are used for valid content

### 3.4 Maintainability

1. **No regex sanitizers**: All sanitizers use AST parsing
2. **Pre-generation validation**: All validation happens before generation
3. **Origin-level prevention**: All issues are caught at the origin

## Part 4: Verification Plan

### 4.1 Automated Verification

1. Run all pilots on `pilot-aspose-3d-foss-python`:
   ```bash
   PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/tc-2370-3d
   ```
2. Check validation report for gate pass rate
3. Check content quality metrics
4. Check pipeline performance metrics

### 4.2 Manual Verification

1. Review 5 generated pages for repo-specific content
2. Review 5 generated pages for accurate code snippets
3. Review 5 generated pages for complete claims
4. Review 5 generated pages for consistent terminology

## Part 5: Definition of Done

1. All validation gates pass 100% of the time
2. No manual content edits required
3. No regex-based fixes required
4. All content is repo-specific
5. All code snippets are accurate
6. All claims are covered in the content
7. All sections use consistent terminology
8. Content generation completes in under 10 minutes
9. Validation completes in under 5 minutes
10. 90%+ of tokens are used for valid content
11. All sanitizers use AST parsing
12. All validation happens before generation
13. All issues are caught at the origin

## Part 6: Next Steps

1. Implement immediate changes (TC-2370, TC-2372, TC-2376)
2. Implement short-term changes (TC-2371, TC-2373, TC-2374, TC-2375)
3. Implement long-term changes (TC-2377-TC-2380)
4. Run all pilots and verify acceptance criteria
5. Update documentation and training materials
