"""Usability checks for W5.5 ContentReviewer.

This module implements 12 usability checks that ensure generated documentation
is user-friendly, navigable, and accessible.

TC-1100-P1: W5.5 ContentReviewer Phase 1 - Core Review Logic
Pattern: Check module pattern (similar to W7 gates)

Spec reference: abstract-hugging-kite.md:430-482 (Usability Dimension)
"""

import re
from pathlib import Path
from typing import Dict, List, Any


def check_all(
    drafts_dir: Path,
    page_plan: Dict[str, Any],
    product_facts: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Run all 12 usability checks and return issues.

    Args:
        drafts_dir: Path to drafts directory (RUN_DIR/drafts)
        page_plan: Page plan dict from page_plan.json
        product_facts: Product facts dict from product_facts.json

    Returns:
        List of issue dicts (same format as content_quality)

    Spec reference: abstract-hugging-kite.md:430-482
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
                "issue_id": f"usability_read_error_{md_file.stem}",
                "check": "usability.file_read",
                "severity": "error",
                "message": f"Failed to read file: {e}",
                "location": {"path": str(md_file.relative_to(drafts_dir.parent)), "line": 1},
                "auto_fixable": False,
            })
            continue

        rel_path = str(md_file.relative_to(drafts_dir.parent))
        page_slug = md_file.stem

        # Run all 12 checks
        issues.extend(_check_1_navigation_clarity(content, rel_path, page_slug, page_plan))
        issues.extend(_check_2_user_journey(content, rel_path, page_slug))
        issues.extend(_check_3_example_clarity(content, rel_path, page_slug))
        issues.extend(_check_4_heading_descriptiveness(content, rel_path, page_slug, product_facts))
        issues.extend(_check_5_call_to_action_presence(content, rel_path, page_slug))
        issues.extend(_check_6_prerequisites_clarity(content, rel_path, page_slug))
        issues.extend(_check_7_accessibility_compliance(content, rel_path, page_slug))
        issues.extend(_check_8_search_optimization(content, rel_path, page_slug, product_facts))
        issues.extend(_check_9_mobile_readability(content, rel_path, page_slug))
        issues.extend(_check_10_progressive_disclosure(content, rel_path, page_slug))
        issues.extend(_check_11_related_links(content, rel_path, page_slug))
        issues.extend(_check_12_error_message_clarity(content, rel_path, page_slug))

    return issues


# Check 1: Navigation Clarity
def _check_1_navigation_clarity(content: str, rel_path: str, page_slug: str, page_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """TOC pages list all children, landing pages link to sections.

    Spec: abstract-hugging-kite.md:398 (Check 1)
    Severity: ERROR
    """
    issues = []

    # Check if this is a TOC or landing page
    if '_index' in page_slug or 'index' in page_slug or 'toc' in page_slug.lower():
        # Get child pages from page_plan
        pages = page_plan.get('pages', [])
        current_page_url = None
        for page in pages:
            if page.get('slug') == page_slug or page.get('filename') == f"{page_slug}.md":
                current_page_url = page.get('url_path', '')
                break

        # Find child pages (pages with url_path starting with current page)
        child_pages = []
        for page in pages:
            page_url = page.get('url_path', '')
            if current_page_url and page_url.startswith(current_page_url) and page_url != current_page_url:
                child_pages.append(page)

        # Check if all children are linked in content
        for child in child_pages:
            child_slug = child.get('slug', '')
            child_url = child.get('url_path', '')
            if child_slug not in content and child_url not in content:
                issues.append({
                    "issue_id": f"usability_navigation_{page_slug}_{child_slug}",
                    "check": "usability.navigation_clarity",
                    "severity": "error",
                    "message": f"Child page not linked: {child_slug}",
                    "location": {"path": rel_path, "line": 1},
                    "auto_fixable": False,
                })

    return issues


# Check 2: User Journey
def _check_2_user_journey(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Getting Started → Developer Guide → Reference progression.

    Spec: abstract-hugging-kite.md:399 (Check 2)
    Severity: WARN
    """
    issues = []

    # Check for next steps or progressive links
    journey_keywords = ['getting started', 'next steps', 'learn more', 'developer guide', 'reference']

    # If this is getting-started, should link to guide
    if 'getting-started' in page_slug or 'quickstart' in page_slug:
        if not re.search(r'(developer guide|next steps|learn more)', content, re.IGNORECASE):
            issues.append({
                "issue_id": f"usability_user_journey_{page_slug}",
                "check": "usability.user_journey",
                "severity": "warn",
                "message": "Getting Started page should link to next steps (e.g., Developer Guide)",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": False,
            })

    return issues


# Check 3: Example Clarity
def _check_3_example_clarity(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Code blocks have ≥1 sentence intro + explanation.

    Spec: abstract-hugging-kite.md:400 (Check 3)
    Severity: WARN
    """
    issues = []

    # Find code blocks
    code_block_pattern = r'```\w*\n.*?```'
    matches = list(re.finditer(code_block_pattern, content, re.DOTALL))

    for match in matches:
        line_num = content[:match.start()].count('\n') + 1

        # Check for text before code block (intro)
        text_before = content[:match.start()].split('\n')[-2:]  # Last 2 lines before code
        has_intro = any(len(line.strip()) > 20 for line in text_before)

        # Check for text after code block (explanation)
        end_pos = match.end()
        text_after = content[end_pos:].split('\n')[:2]  # First 2 lines after code
        has_explanation = any(len(line.strip()) > 20 for line in text_after)

        if not has_intro:
            issues.append({
                "issue_id": f"usability_example_intro_{page_slug}_{line_num}",
                "check": "usability.example_clarity",
                "severity": "warn",
                "message": "Code block missing introduction",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": False,
            })

        if not has_explanation:
            issues.append({
                "issue_id": f"usability_example_explanation_{page_slug}_{line_num}",
                "check": "usability.example_clarity",
                "severity": "warn",
                "message": "Code block missing explanation",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": False,
            })

    return issues


# Check 4: Heading Descriptiveness
def _check_4_heading_descriptiveness(content: str, rel_path: str, page_slug: str, product_facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Headings >2 words or include product name.

    Spec: abstract-hugging-kite.md:401 (Check 4)
    Severity: WARN
    """
    issues = []

    product_name = product_facts.get('product_name', '')
    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        if line.strip().startswith('#'):
            # Extract heading text (remove # and trim)
            heading_text = re.sub(r'^#+\s*', '', line).strip()

            # Count words
            word_count = len(heading_text.split())

            # Check if heading is too short and doesn't include product name
            if word_count <= 2 and product_name.lower() not in heading_text.lower():
                # Allow some generic headings
                if heading_text.lower() not in ['overview', 'introduction', 'examples', 'usage', 'installation']:
                    issues.append({
                        "issue_id": f"usability_heading_descriptive_{page_slug}_{line_num}",
                        "check": "usability.heading_descriptiveness",
                        "severity": "warn",
                        "message": f"Generic heading: {heading_text}",
                        "location": {"path": rel_path, "line": line_num},
                        "auto_fixable": False,
                    })

    return issues


# Check 5: Call-to-Action Presence
def _check_5_call_to_action_presence(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Landing pages have CTA.

    Spec: abstract-hugging-kite.md:402 (Check 5)
    Severity: WARN
    """
    issues = []

    # Check if this is a landing page
    if '_index' in page_slug or 'index' in page_slug or page_slug in ['home', 'landing']:
        # Look for CTA patterns
        cta_patterns = [
            r'get started', r'download', r'install', r'try', r'explore',
            r'learn more', r'read the', r'check out',
        ]

        has_cta = any(re.search(pattern, content, re.IGNORECASE) for pattern in cta_patterns)

        if not has_cta:
            issues.append({
                "issue_id": f"usability_cta_{page_slug}",
                "check": "usability.call_to_action_presence",
                "severity": "warn",
                "message": "Landing page missing call-to-action",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": False,
            })

    return issues


# Check 6: Prerequisites Clarity
def _check_6_prerequisites_clarity(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """How-to guides have Prerequisites section.

    Spec: abstract-hugging-kite.md:403 (Check 6)
    Severity: WARN
    """
    issues = []

    # Check if this is a how-to guide
    if 'how-to' in page_slug or 'howto' in page_slug or 'guide' in page_slug:
        # Look for prerequisites section
        has_prerequisites = re.search(r'^#+\s*prerequisites', content, re.IGNORECASE | re.MULTILINE)

        if not has_prerequisites:
            issues.append({
                "issue_id": f"usability_prerequisites_{page_slug}",
                "check": "usability.prerequisites_clarity",
                "severity": "warn",
                "message": "How-to guide missing Prerequisites section",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": False,
            })

    return issues


# Check 7: Accessibility Compliance
def _check_7_accessibility_compliance(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Alt text for images, no "click here" links.

    Spec: abstract-hugging-kite.md:404 (Check 7)
    Severity: ERROR
    """
    issues = []

    # Check for images without alt text
    image_pattern = r'!\[\s*\]\('
    matches = re.finditer(image_pattern, content)
    for match in matches:
        line_num = content[:match.start()].count('\n') + 1
        issues.append({
            "issue_id": f"usability_accessibility_image_{page_slug}_{line_num}",
            "check": "usability.accessibility_compliance",
            "severity": "error",
            "message": "Image missing alt text",
            "location": {"path": rel_path, "line": line_num},
            "auto_fixable": False,
        })

    # Check for "click here" links
    click_here_pattern = r'\[click here\]'
    matches = re.finditer(click_here_pattern, content, re.IGNORECASE)
    for match in matches:
        line_num = content[:match.start()].count('\n') + 1
        issues.append({
            "issue_id": f"usability_accessibility_click_here_{page_slug}_{line_num}",
            "check": "usability.accessibility_compliance",
            "severity": "error",
            "message": "Avoid 'click here' links (use descriptive link text)",
            "location": {"path": rel_path, "line": line_num},
            "auto_fixable": False,
        })

    return issues


# Check 8: Search Optimization
def _check_8_search_optimization(content: str, rel_path: str, page_slug: str, product_facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Title includes product_name, description <160 chars.

    Spec: abstract-hugging-kite.md:405 (Check 8)
    Severity: WARN
    """
    issues = []

    product_name = product_facts.get('product_name', '')

    # Extract frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?\n)---', content, re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)

        # Check title includes product name
        title_match = re.search(r'^title:\s*(.+)$', frontmatter, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            if product_name and product_name.lower() not in title.lower():
                issues.append({
                    "issue_id": f"usability_seo_title_{page_slug}",
                    "check": "usability.search_optimization",
                    "severity": "warn",
                    "message": f"Title missing product name: {title}",
                    "location": {"path": rel_path, "line": 2},
                    "auto_fixable": False,
                })

        # Check description length
        desc_match = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE)
        if desc_match:
            description = desc_match.group(1).strip().strip('"').strip("'")
            if len(description) > 160:
                issues.append({
                    "issue_id": f"usability_seo_description_{page_slug}",
                    "check": "usability.search_optimization",
                    "severity": "warn",
                    "message": f"Description too long ({len(description)} chars, max 160)",
                    "location": {"path": rel_path, "line": 3},
                    "auto_fixable": False,
                })

    return issues


# Check 9: Mobile Readability
def _check_9_mobile_readability(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Tables <5 columns, code blocks <100 chars/line.

    Spec: abstract-hugging-kite.md:406 (Check 9)
    Severity: WARN
    """
    issues = []

    lines = content.split('\n')

    # Check table columns
    for line_num, line in enumerate(lines, start=1):
        if '|' in line and not line.strip().startswith('```'):
            # Count columns
            columns = line.count('|') - 1
            if columns > 5:
                issues.append({
                    "issue_id": f"usability_mobile_table_{page_slug}_{line_num}",
                    "check": "usability.mobile_readability",
                    "severity": "warn",
                    "message": f"Table too wide ({columns} columns, max 5 for mobile)",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

    # Check code block line length
    code_block_pattern = r'```\w*\n(.*?)```'
    matches = re.finditer(code_block_pattern, content, re.DOTALL)
    for match in matches:
        code = match.group(1)
        line_num_start = content[:match.start()].count('\n') + 1
        for i, line in enumerate(code.split('\n')):
            if len(line) > 100:
                issues.append({
                    "issue_id": f"usability_mobile_code_{page_slug}_{line_num_start + i}",
                    "check": "usability.mobile_readability",
                    "severity": "warn",
                    "message": f"Code line too long ({len(line)} chars, max 100 for mobile)",
                    "location": {"path": rel_path, "line": line_num_start + i},
                    "auto_fixable": False,
                })

    return issues


# Check 10: Progressive Disclosure
def _check_10_progressive_disclosure(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """H2 sections start with 1-2 sentence intro.

    Spec: abstract-hugging-kite.md:407 (Check 10)
    Severity: WARN
    """
    issues = []

    lines = content.split('\n')
    h2_line_nums = []

    # Find all H2 headings
    for line_num, line in enumerate(lines, start=1):
        if re.match(r'^##\s+', line):
            h2_line_nums.append(line_num)

    # Check each H2 for intro text
    for h2_line_num in h2_line_nums:
        # Get next 5 lines after H2
        next_lines = lines[h2_line_num:h2_line_num + 5]
        intro_text = ' '.join(line.strip() for line in next_lines if line.strip() and not line.strip().startswith('#'))

        # Count sentences (rough heuristic)
        sentence_count = intro_text.count('.') + intro_text.count('!') + intro_text.count('?')

        if sentence_count == 0:
            issues.append({
                "issue_id": f"usability_progressive_disclosure_{page_slug}_{h2_line_num}",
                "check": "usability.progressive_disclosure",
                "severity": "warn",
                "message": "H2 section missing introductory sentences",
                "location": {"path": rel_path, "line": h2_line_num},
                "auto_fixable": False,
            })

    return issues


# Check 11: Related Links
def _check_11_related_links(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Pages have ≥2 related links.

    Spec: abstract-hugging-kite.md:408 (Check 11)
    Severity: WARN
    """
    issues = []

    # Exempt index/TOC pages (use structured navigation, not prose links)
    if '_index' in page_slug or page_slug == 'index':
        return []

    # Count markdown links
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    link_count = len(re.findall(link_pattern, content))

    if link_count < 2:
        issues.append({
            "issue_id": f"usability_related_links_{page_slug}",
            "check": "usability.related_links",
            "severity": "warn",
            "message": f"Few related links ({link_count}, recommend ≥2)",
            "location": {"path": rel_path, "line": 1},
            "auto_fixable": False,
        })

    return issues


# Check 12: Error Message Clarity
def _check_12_error_message_clarity(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Troubleshooting pages format error messages in code blocks.

    Spec: abstract-hugging-kite.md:409 (Check 12)
    Severity: WARN
    """
    issues = []

    # Check if this is a troubleshooting page
    if 'troubleshoot' in page_slug or 'error' in page_slug or 'faq' in page_slug:
        # Look for error message patterns NOT in code blocks
        error_patterns = [
            r'Error:', r'Exception:', r'Warning:', r'Failed:', r'Cannot:',
        ]

        # Remove code blocks from content
        content_no_code = re.sub(r'```.*?```', '', content, flags=re.DOTALL)

        for pattern in error_patterns:
            matches = re.finditer(pattern, content_no_code)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "issue_id": f"usability_error_message_{page_slug}_{line_num}",
                    "check": "usability.error_message_clarity",
                    "severity": "warn",
                    "message": f"Error message not in code block: {match.group(0)}",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

    return issues
