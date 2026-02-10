"""Technical Accuracy checks for W5.5 ContentReviewer.

This module implements 12 technical accuracy checks that ensure generated content
is technically correct and grounded in product_facts.

TC-1100-P1: W5.5 ContentReviewer Phase 1 - Core Review Logic
Pattern: Check module pattern (similar to W7 gates)

Spec reference: abstract-hugging-kite.md:376-428 (Technical Accuracy Dimension)
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any


def check_all(
    drafts_dir: Path,
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    evidence_map: Dict[str, Any],
    page_plan: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Run all 12 technical accuracy checks and return issues.

    Args:
        drafts_dir: Path to drafts directory (RUN_DIR/drafts)
        product_facts: Product facts dict from product_facts.json
        snippet_catalog: Snippet catalog dict from snippet_catalog.json
        evidence_map: Evidence map dict from evidence_map.json
        page_plan: Page plan dict from page_plan.json

    Returns:
        List of issue dicts (same format as content_quality)

    Spec reference: abstract-hugging-kite.md:370-428
    """
    issues = []

    if not drafts_dir.exists():
        return issues

    # Find all markdown files
    md_files = sorted(drafts_dir.rglob("*.md"))

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception as e:
            issues.append({
                "issue_id": f"technical_accuracy_read_error_{md_file.stem}",
                "check": "technical_accuracy.file_read",
                "severity": "error",
                "message": f"Failed to read file: {e}",
                "location": {"path": str(md_file.relative_to(drafts_dir.parent)), "line": 1},
                "auto_fixable": False,
            })
            continue

        rel_path = str(md_file.relative_to(drafts_dir.parent))
        page_slug = md_file.stem

        # Run all 12 checks
        issues.extend(_check_1_code_syntax_validation(content, rel_path, page_slug))
        issues.extend(_check_2_code_execution(content, rel_path, page_slug))
        issues.extend(_check_3_api_reference_validation(content, rel_path, page_slug, product_facts))
        issues.extend(_check_4_claim_validity(content, rel_path, page_slug, product_facts))
        issues.extend(_check_5_snippet_attribution(content, rel_path, page_slug, snippet_catalog))
        issues.extend(_check_6_workflow_coverage(content, rel_path, page_slug, product_facts, page_plan))
        issues.extend(_check_7_limitation_honesty(content, rel_path, page_slug, product_facts))
        issues.extend(_check_8_distribution_correctness(content, rel_path, page_slug, product_facts))
        issues.extend(_check_9_example_verifiability(content, rel_path, page_slug, snippet_catalog))
        issues.extend(_check_10_claim_evidence_linkage(content, rel_path, page_slug, evidence_map))
        issues.extend(_check_11_technical_terminology_consistency(content, rel_path, page_slug, product_facts))
        issues.extend(_check_12_forbidden_topics_compliance(content, rel_path, page_slug, page_plan))

    return issues


# Check 1: Code Syntax Validation
def _check_1_code_syntax_validation(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Validate Python/Java/C#/JS/TS/Go syntax in code blocks.

    Spec: abstract-hugging-kite.md:372 (Check 1)
    Severity: BLOCKER if syntax broken
    """
    issues = []

    # Extract code blocks with language
    code_block_pattern = r'```(\w+)\n(.*?)```'
    matches = re.finditer(code_block_pattern, content, re.DOTALL)

    for match in matches:
        language = match.group(1).lower()
        code = match.group(2)
        line_num = content[:match.start()].count('\n') + 1

        # Validate Python syntax
        if language in ['python', 'py']:
            try:
                ast.parse(code)
            except SyntaxError as e:
                issues.append({
                    "issue_id": f"technical_accuracy_code_syntax_{page_slug}_{line_num}",
                    "check": "technical_accuracy.code_syntax_validation",
                    "severity": "blocker",
                    "message": f"Python syntax error: {e.msg} at line {e.lineno}",
                    "location": {"path": rel_path, "line": line_num + (e.lineno or 0)},
                    "auto_fixable": False,
                })

        # For other languages, do basic checks (balanced braces, etc.)
        elif language in ['java', 'javascript', 'js', 'typescript', 'ts', 'csharp', 'cs', 'go']:
            # Check balanced braces
            open_braces = code.count('{')
            close_braces = code.count('}')
            if open_braces != close_braces:
                issues.append({
                    "issue_id": f"technical_accuracy_code_syntax_{page_slug}_{line_num}",
                    "check": "technical_accuracy.code_syntax_validation",
                    "severity": "error",
                    "message": f"Unbalanced braces in {language} code ({open_braces} open, {close_braces} close)",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

            # Check balanced parentheses
            open_parens = code.count('(')
            close_parens = code.count(')')
            if open_parens != close_parens:
                issues.append({
                    "issue_id": f"technical_accuracy_code_parens_{page_slug}_{line_num}",
                    "check": "technical_accuracy.code_syntax_validation",
                    "severity": "error",
                    "message": f"Unbalanced parentheses in {language} code ({open_parens} open, {close_parens} close)",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

    return issues


# Check 2: Code Execution
def _check_2_code_execution(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Run Python snippets in sandbox (offline mode skips).

    Spec: abstract-hugging-kite.md:373 (Check 2)
    Severity: ERROR if execution fails
    """
    issues = []

    # Skip code execution in Phase 1 (no sandbox implementation yet)
    # This check will be implemented in Phase 2 with auto-fixes
    return issues


# Check 3: API Reference Validation
def _check_3_api_reference_validation(content: str, rel_path: str, page_slug: str, product_facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Verify APIs exist in product_facts.api_surface_summary.

    Spec: abstract-hugging-kite.md:374 (Check 3)
    Severity: ERROR if hallucinated
    """
    issues = []

    # Get API surface from product_facts
    api_surface = product_facts.get('api_surface_summary', {})
    known_classes = set(api_surface.get('classes', []))
    known_functions = set(api_surface.get('functions', []))

    # Pattern: Class.method() or function() references in code blocks or text
    api_pattern = r'\b([A-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)*)\s*\('

    matches = re.finditer(api_pattern, content)
    for match in matches:
        api_ref = match.group(1)
        line_num = content[:match.start()].count('\n') + 1

        # Check if class name is known
        parts = api_ref.split('.')
        if len(parts) >= 1:
            class_name = parts[0]
            if class_name not in known_classes and api_ref not in known_functions:
                # Only flag if it looks like product API (not stdlib)
                if not _is_stdlib_api(api_ref):
                    issues.append({
                        "issue_id": f"technical_accuracy_api_ref_{page_slug}_{line_num}",
                        "check": "technical_accuracy.api_reference_validation",
                        "severity": "warn",  # WARN instead of ERROR (may be false positive)
                        "message": f"Unrecognized API reference: {api_ref}",
                        "location": {"path": rel_path, "line": line_num},
                        "auto_fixable": False,
                    })

    return issues


# Check 4: Claim Validity
def _check_4_claim_validity(content: str, rel_path: str, page_slug: str, product_facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """All claim IDs exist in product_facts.claims.

    Spec: abstract-hugging-kite.md:375 (Check 4)
    Severity: ERROR (auto-fixable)
    """
    issues = []

    # Get all claim IDs from product_facts
    claims = product_facts.get('claims', [])
    valid_claim_ids = set(c.get('claim_id') for c in claims if 'claim_id' in c)

    # Extract claim markers from content
    claim_pattern = r'<!--\s*claim_id:\s*([a-f0-9\-]{36})\s*-->'
    matches = re.finditer(claim_pattern, content, re.IGNORECASE)

    for match in matches:
        claim_id = match.group(1)
        line_num = content[:match.start()].count('\n') + 1

        if claim_id not in valid_claim_ids:
            issues.append({
                "issue_id": f"technical_accuracy_claim_validity_{page_slug}_{claim_id[:8]}",
                "check": "technical_accuracy.claim_validity",
                "severity": "error",
                "message": f"Invalid claim ID (not in product_facts): {claim_id}",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": True,
                "suggested_fix": "Remove claim marker or update claim_id",
            })

    return issues


# Check 5: Snippet Attribution
def _check_5_snippet_attribution(content: str, rel_path: str, page_slug: str, snippet_catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Snippets traceable to snippet_catalog.

    Spec: abstract-hugging-kite.md:376 (Check 5)
    Severity: WARN
    """
    issues = []

    # Extract code blocks
    code_block_pattern = r'```(\w+)\n(.*?)```'
    matches = re.finditer(code_block_pattern, content, re.DOTALL)

    snippets = snippet_catalog.get('snippets', [])
    snippet_texts = [s.get('snippet_text', '') for s in snippets]

    for match in matches:
        code = match.group(2)
        line_num = content[:match.start()].count('\n') + 1

        # Check if code appears in snippet catalog (exact or substring match)
        code_normalized = code.strip()
        if len(code_normalized) > 20:  # Only check substantial code blocks
            found = any(code_normalized in snippet_text for snippet_text in snippet_texts)
            if not found:
                issues.append({
                    "issue_id": f"technical_accuracy_snippet_attribution_{page_slug}_{line_num}",
                    "check": "technical_accuracy.snippet_attribution",
                    "severity": "warn",
                    "message": "Code block not found in snippet_catalog",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

    return issues


# Check 6: Workflow Coverage
def _check_6_workflow_coverage(content: str, rel_path: str, page_slug: str, product_facts: Dict[str, Any], page_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comprehensive guides cover all workflows.

    Spec: abstract-hugging-kite.md:377 (Check 6)
    Severity: ERROR (requires LLM regen)
    """
    issues = []

    # Check if this is a comprehensive guide by looking up page_role in page_plan
    is_comprehensive_guide = False
    pages = page_plan.get('pages', [])

    for page in pages:
        if page.get('slug') == page_slug or page.get('filename') == f"{page_slug}.md":
            page_role = page.get('page_role', '')
            purpose = page.get('purpose', '')

            # Check if this is explicitly a comprehensive guide
            if page_role == 'comprehensive_guide':
                is_comprehensive_guide = True
                break

            # Fallback: check purpose field for "comprehensive" keyword
            if 'comprehensive' in purpose.lower():
                is_comprehensive_guide = True
                break

    # Only check workflow coverage for comprehensive guides
    if is_comprehensive_guide:
        # Get workflows from product_facts
        workflows = product_facts.get('workflows', [])
        workflow_names = [w.get('name', '') for w in workflows]

        # Check if all workflows are mentioned in content
        for workflow_name in workflow_names:
            if workflow_name.lower() not in content.lower():
                issues.append({
                    "issue_id": f"technical_accuracy_workflow_coverage_{page_slug}_{workflow_name}",
                    "check": "technical_accuracy.workflow_coverage",
                    "severity": "error",
                    "message": f"Workflow not covered: {workflow_name}",
                    "location": {"path": rel_path, "line": 1},
                    "auto_fixable": False,
                })

    return issues


# Check 7: Limitation Honesty
def _check_7_limitation_honesty(content: str, rel_path: str, page_slug: str, product_facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Limitations section exists if product_facts.limitations non-empty.

    Spec: abstract-hugging-kite.md:378 (Check 7)
    Severity: ERROR
    """
    issues = []

    # Get limitations from product_facts
    claim_groups = product_facts.get('claim_groups', {})
    limitations = claim_groups.get('limitations', [])

    if limitations:
        # Check if content has limitations section
        if not re.search(r'^#+\s*limitations', content, re.IGNORECASE | re.MULTILINE):
            issues.append({
                "issue_id": f"technical_accuracy_limitation_honesty_{page_slug}",
                "check": "technical_accuracy.limitation_honesty",
                "severity": "error",
                "message": f"Missing Limitations section ({len(limitations)} limitations in product_facts)",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": False,
            })

    return issues


# Check 8: Distribution Correctness
def _check_8_distribution_correctness(content: str, rel_path: str, page_slug: str, product_facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Install commands match product_facts.distribution.

    Spec: abstract-hugging-kite.md:379 (Check 8)
    Severity: ERROR (auto-fixable)
    """
    issues = []

    # Get distribution info
    distribution = product_facts.get('distribution', {})
    install_commands = distribution.get('install_commands', [])

    # Check if install commands in content match product_facts
    for install_cmd in install_commands:
        if install_cmd and install_cmd not in content:
            issues.append({
                "issue_id": f"technical_accuracy_distribution_{page_slug}",
                "check": "technical_accuracy.distribution_correctness",
                "severity": "error",
                "message": f"Missing install command: {install_cmd}",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": True,
                "suggested_fix": f"Add install command: {install_cmd}",
            })

    return issues


# Check 9: Example Verifiability
def _check_9_example_verifiability(content: str, rel_path: str, page_slug: str, snippet_catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Code examples reference actual repo files.

    Spec: abstract-hugging-kite.md:380 (Check 9)
    Severity: WARN
    """
    issues = []

    # Get snippet sources
    snippets = snippet_catalog.get('snippets', [])
    snippet_sources = set(s.get('source_file', '') for s in snippets if s.get('source_file'))

    # Look for file references in content (e.g., "from examples/demo.py")
    file_ref_pattern = r'(?:from|see|in)\s+([\w/\._-]+\.(?:py|java|cs|js|ts|go))'
    matches = re.finditer(file_ref_pattern, content, re.IGNORECASE)

    for match in matches:
        file_ref = match.group(1)
        line_num = content[:match.start()].count('\n') + 1

        # Check if file exists in snippet sources
        if not any(file_ref in source for source in snippet_sources):
            issues.append({
                "issue_id": f"technical_accuracy_example_verifiability_{page_slug}_{line_num}",
                "check": "technical_accuracy.example_verifiability",
                "severity": "warn",
                "message": f"Referenced file not in snippet_catalog: {file_ref}",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": False,
            })

    return issues


# Check 10: Claim-Evidence Linkage
def _check_10_claim_evidence_linkage(content: str, rel_path: str, page_slug: str, evidence_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    """All claims have evidence in evidence_map.json.

    Spec: abstract-hugging-kite.md:381 (Check 10)
    Severity: ERROR
    """
    issues = []

    # Get claims from evidence_map
    claims_with_evidence = set()
    for claim in evidence_map.get('claims', []):
        claim_id = claim.get('claim_id')
        if claim_id:
            claims_with_evidence.add(claim_id)

    # Extract claim markers from content
    claim_pattern = r'<!--\s*claim_id:\s*([a-f0-9\-]{36})\s*-->'
    matches = re.finditer(claim_pattern, content, re.IGNORECASE)

    for match in matches:
        claim_id = match.group(1)
        line_num = content[:match.start()].count('\n') + 1

        if claim_id not in claims_with_evidence:
            issues.append({
                "issue_id": f"technical_accuracy_claim_evidence_{page_slug}_{claim_id[:8]}",
                "check": "technical_accuracy.claim_evidence_linkage",
                "severity": "error",
                "message": f"Claim has no evidence in evidence_map: {claim_id}",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": False,
            })

    return issues


# Check 11: Technical Terminology Consistency
def _check_11_technical_terminology_consistency(content: str, rel_path: str, page_slug: str, product_facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Product name, repo URL match product_facts.

    Spec: abstract-hugging-kite.md:382 (Check 11)
    Severity: ERROR (auto-fixable)
    """
    issues = []

    product_name = product_facts.get('product_name', '')
    repo_url = product_facts.get('repo_url', '')

    # Check product name variations (case-insensitive)
    if product_name:
        # Allow some variation but flag if completely missing
        if product_name.lower() not in content.lower():
            issues.append({
                "issue_id": f"technical_accuracy_product_name_{page_slug}",
                "check": "technical_accuracy.technical_terminology_consistency",
                "severity": "warn",
                "message": f"Product name not found: {product_name}",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": False,
            })

    # Check repo URL (if present in content, must be correct)
    if repo_url:
        # Look for any GitHub URLs
        github_pattern = r'https?://github\.com/[^\s\)"\']+'
        matches = re.finditer(github_pattern, content)
        for match in matches:
            found_url = match.group(0)
            if found_url != repo_url:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "issue_id": f"technical_accuracy_repo_url_{page_slug}_{line_num}",
                    "check": "technical_accuracy.technical_terminology_consistency",
                    "severity": "error",
                    "message": f"Incorrect repo URL: {found_url} (expected: {repo_url})",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": True,
                    "suggested_fix": f"Replace with: {repo_url}",
                })

    return issues


# Check 12: Forbidden Topics Compliance
def _check_12_forbidden_topics_compliance(content: str, rel_path: str, page_slug: str, page_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """No forbidden_topics from page_plan.

    Spec: abstract-hugging-kite.md:383 (Check 12)
    Severity: ERROR
    """
    issues = []

    # Get forbidden topics for this page from page_plan
    pages = page_plan.get('pages', [])
    forbidden_topics = []

    for page in pages:
        if page.get('slug') == page_slug or page.get('filename') == f"{page_slug}.md":
            forbidden_topics = page.get('forbidden_topics', [])
            break

    # Check if any forbidden topic appears in content
    for topic in forbidden_topics:
        if topic.lower() in content.lower():
            line_num = content.lower().index(topic.lower())
            line_num = content[:line_num].count('\n') + 1
            issues.append({
                "issue_id": f"technical_accuracy_forbidden_topic_{page_slug}_{topic}",
                "check": "technical_accuracy.forbidden_topics_compliance",
                "severity": "error",
                "message": f"Forbidden topic detected: {topic}",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": False,
            })

    return issues


# Helper function
def _is_stdlib_api(api_ref: str) -> bool:
    """Check if API reference is likely from standard library.

    Args:
        api_ref: API reference string (e.g., "print", "len", "str.split")

    Returns:
        True if likely stdlib, False otherwise
    """
    stdlib_functions = {
        'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set',
        'tuple', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'sum', 'min', 'max',
        'open', 'read', 'write', 'close', 'Exception', 'ValueError', 'TypeError',
    }

    stdlib_modules = {
        'os', 'sys', 'json', 'yaml', 're', 'pathlib', 'datetime', 'time',
        'math', 'random', 'collections', 'itertools', 'functools',
    }

    # Check if function name is in stdlib
    parts = api_ref.split('.')
    if parts[0].lower() in stdlib_functions or parts[0].lower() in stdlib_modules:
        return True

    return False
