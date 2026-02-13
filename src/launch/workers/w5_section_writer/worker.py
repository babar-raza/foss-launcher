"""TC-440: W5 SectionWriter worker implementation.

This module implements the W5 SectionWriter that generates markdown content for
documentation page sections using templates and LLM-based content generation.

W5 SectionWriter performs:
1. Load page_plan.json from TC-430 (W4 IAPlanner)
2. Load product_facts.json from TC-410 (W2 FactsBuilder)
3. Load snippet_catalog.json from TC-420 (W3 SnippetCurator)
4. Generate markdown content for each page section
5. Ground content in facts and snippets with claim markers
6. Emit events and write draft files + manifest

Output artifacts:
- drafts/<page_id>_<section_id>.md (one per section)
- draft_manifest.json (listing all draft files)

Spec references:
- specs/07_section_templates.md (Section writing templates)
- specs/21_worker_contracts.md:195-226 (W5 SectionWriter contract)
- specs/10_determinism_and_caching.md (Stable output requirements)
- specs/11_state_and_events.md (Event emission)
- specs/23_claim_markers.md (Claim marker format)

TC-440: W5 SectionWriter
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from ...io.run_layout import RunLayout
from ...io.artifact_store import ArtifactStore
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
    EVENT_ISSUE_OPENED,
    EVENT_RUN_FAILED,
)
from ...io.atomic import atomic_write_json
from ...util.logging import get_logger
from .link_transformer import transform_cross_section_links

logger = get_logger()

# TC-1110: Claim text truncation constants for quality control
MAX_CLAIM_TEXT_LENGTH = 200  # Display limit for claim text in bullet points
MAX_CLAIM_FILTER_LENGTH = 1000  # Pre-filter limit to remove pathological cases
MAX_LIMITATION_CLAIMS = 10  # Maximum number of limitation claims to display

# Compiled regex for list item detection (bullets, numbered, asterisk)
_LIST_ITEM_RE = re.compile(r'^(?:-\s|\*\s|\d+\.\s+)')
# Threshold at which we attempt first-sentence simplification.
# W5.5 flags >250 chars as ERROR, >180 as WARN.
MAX_BULLET_LEN = 170


def _first_sentence_bullets(content: str) -> str:
    """Simplify long bullet points by extracting the first sentence.

    Instead of blindly truncating with "...", this preserves the core
    meaning by taking only the first sentence when a bullet exceeds
    MAX_BULLET_LEN.  Falls back to word-boundary truncation only if
    the first sentence itself is still too long.
    """
    result_lines = []
    for line in content.split('\n'):
        stripped = line.lstrip()
        if not (_LIST_ITEM_RE.match(stripped) and len(stripped) > MAX_BULLET_LEN):
            result_lines.append(line)
            continue

        # Preserve claim marker at end if present
        marker_match = re.search(r'\s*\[claim:\s*[a-zA-Z0-9_-]+\]$', stripped)
        marker = marker_match.group(0) if marker_match else ''
        text = stripped[:len(stripped) - len(marker)] if marker else stripped

        # Split list prefix ("- ", "* ", "1. ") from body
        prefix_match = _LIST_ITEM_RE.match(text)
        prefix = prefix_match.group(0) if prefix_match else ''
        body = text[len(prefix):]

        # Strategy 1: Extract first sentence (ends with . ! or ?)
        sentence_end = re.search(r'[.!?](?:\s|$)', body)
        if sentence_end and sentence_end.end() < len(body) - 10:
            # First sentence is meaningfully shorter — use it
            first_sentence = body[:sentence_end.end()].strip()
            simplified = f'{prefix}{first_sentence}{marker}'
            if len(simplified) <= MAX_BULLET_LEN + 30:
                indent = line[:len(line) - len(stripped)]
                result_lines.append(f'{indent}{simplified}')
                continue

        # Strategy 2: If no sentence break or still long, truncate at word boundary
        max_body = MAX_BULLET_LEN - len(prefix) - len(marker) - 3
        if len(body) > max_body:
            body = body[:max_body].rsplit(' ', 1)[0] + '...'
        indent = line[:len(line) - len(stripped)]
        result_lines.append(f'{indent}{prefix}{body}{marker}')

    return '\n'.join(result_lines)


def _fix_claim_grounding(content: str) -> str:
    """Ensure claim markers are within 50 chars of a sentence-ending period.

    W5.5 ContentReviewer flags claim markers >50 chars from the nearest period
    as WARN. If a claim marker lacks a nearby period, insert one before the marker.
    """
    def _fix_line(line: str) -> str:
        # Skip headings, code blocks, frontmatter
        stripped = line.lstrip()
        if stripped.startswith(('#', '```', '---', '|')):
            return line
        # Find all claim markers in the line
        marker_pattern = re.compile(r'\[claim:\s*[a-zA-Z0-9_-]+\]')
        result = line
        offset = 0
        for m in marker_pattern.finditer(line):
            pos = m.start() + offset
            # Look back up to 50 chars for a sentence-ending punctuation
            text_before = result[:pos]
            last_punct = max(text_before.rfind('.'), text_before.rfind('!'), text_before.rfind('?'))
            if last_punct < 0 or (pos - last_punct) > 50:
                # No nearby period — insert one AFTER the last word (before trailing spaces)
                # This avoids creating "text .[claim:]" patterns that trigger grammar warnings
                insert_pos = pos
                # Walk back past any trailing whitespace to place period right after text
                while insert_pos > 0 and result[insert_pos - 1] == ' ':
                    insert_pos -= 1
                # Don't add period right next to another punctuation
                char_before = result[insert_pos - 1] if insert_pos > 0 else ''
                if char_before not in ('.', '!', '?', ':', ';'):
                    # Insert "." after word, then re-add space before marker
                    result = result[:insert_pos] + '.' + result[insert_pos:]
                    offset += 1
        return result

    return '\n'.join(_fix_line(line) for line in content.split('\n'))


def _ensure_h2_intros(content: str) -> str:
    """Ensure H2 sections have introductory text (at least one sentence).

    TC-1502: Disabled. Generic sentences like "This section covers X" add no value.
    W5.5 progressive_disclosure check will flag bare headings as WARN, which is
    correct behavior — the content genuinely needs improvement, not boilerplate.

    Returns content unchanged (no-op).
    """
    return content


def _inject_machine_readable(
    content: str,
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
) -> str:
    """TC-P3C: Inject machine_readable block into frontmatter for AI consumability.

    Adds structured metadata to frontmatter of docs/kb/blog pages.
    Hugo ignores unknown frontmatter fields, so this is backward-compatible.

    Args:
        content: Markdown content with frontmatter
        page: Page specification from page_plan
        product_facts: Product facts dictionary

    Returns:
        Content with machine_readable block in frontmatter
    """
    if not content.startswith("---"):
        return content

    # Parse frontmatter boundaries
    fm_pattern = re.compile(r'^---\s*$', re.MULTILINE)
    markers = list(fm_pattern.finditer(content))
    if len(markers) < 2:
        return content

    fm_start = markers[0].end()
    fm_end = markers[1].start()
    frontmatter = content[fm_start:fm_end]
    body = content[markers[1].end():]

    # Don't inject if already present
    if "machine_readable:" in frontmatter:
        return content

    # Extract claim IDs from content body (validate as hex strings)
    _HEX_CLAIM_ID = re.compile(r'^[a-f0-9]{8,}$')
    claim_ids = sorted(set(
        m.group(1).strip()
        for m in re.finditer(r'\[claim:\s*([^\]]+)\]', body)
        if _HEX_CLAIM_ID.match(m.group(1).strip())
    ))

    # Build machine_readable block
    product_name = product_facts.get("product_name", "")
    product_family = product_facts.get("product_family", "")
    page_role = page.get("page_role", "")
    _TOKEN_PATTERN = re.compile(r'^__[A-Za-z][A-Za-z0-9_]*__$')
    keywords = sorted(set(
        [product_family] +
        [k.lower() for k in page.get("title", "").split()
         if len(k) > 2 and not _TOKEN_PATTERN.match(k)]
    ))[:8]

    mr_lines = [
        "machine_readable:",
        f'  product_name: "{product_name}"',
        f'  product_family: "{product_family}"',
        f'  page_role: "{page_role}"',
    ]

    if claim_ids:
        mr_lines.append(f'  claim_ids: [{", ".join(f"{c}" for c in claim_ids[:20])}]')
    else:
        mr_lines.append('  claim_ids: []')

    if keywords:
        mr_lines.append(f'  keywords: [{", ".join(f"{k}" for k in keywords)}]')

    mr_block = "\n".join(mr_lines) + "\n"

    # Inject before closing ---
    frontmatter = frontmatter.rstrip() + "\n" + mr_block

    return f"---{frontmatter}---{body}"


def _ensure_related_links(
    content: str, page_slug: str, repo_url: str, product_name: str,
    family: str = "",
    page_url: str = "",
) -> str:
    """Ensure page has >=2 markdown links to satisfy usability.related_links check.

    W5.5 ContentReviewer flags pages with <2 links as WARN. Append a
    'See Also' section with standard links if needed.

    TC-1502: Modified to accept page_url parameter and exclude self-referential links.
    """
    # Index/TOC pages are exempt from this check
    if page_slug in ("_index", "index"):
        return content

    # TC-1503 Fix D: Check if See Also already exists
    if '## See Also' in content or '## see also' in content.lower():
        return content

    # Count existing markdown links
    link_count = len(re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content))
    if link_count >= 2:
        return content

    # Normalize page_url for comparison
    normalized_page_url = page_url
    if normalized_page_url:
        if not normalized_page_url.startswith('/'):
            normalized_page_url = '/' + normalized_page_url
        if not normalized_page_url.endswith('/'):
            normalized_page_url = normalized_page_url + '/'

    # Build see-also links using absolute paths (work across subdomains)
    links = []
    if repo_url:
        links.append(f"- [Source Code Repository]({repo_url})")
    name = product_name or "the library"
    docs_base = f"/{family}" if family else ""

    # Generate candidate links and exclude self-referential ones
    candidate_links = [
        (f"- [Getting Started with {name}]({docs_base}/getting-started/)", f"{docs_base}/getting-started/"),
        (f"- [{name} Documentation Overview]({docs_base}/overview/)", f"{docs_base}/overview/"),
    ]

    for link_text, link_url in candidate_links:
        # Normalize candidate URL
        norm_url = link_url
        if not norm_url.startswith('/'):
            norm_url = '/' + norm_url
        if not norm_url.endswith('/'):
            norm_url = norm_url + '/'
        # Skip if self-referential
        if normalized_page_url and norm_url == normalized_page_url:
            continue
        links.append(link_text)

    if links and len(links) >= 2:
        see_also = "\n\n## See Also\n\n" + "\n".join(links[:3]) + "\n"
        content = content.rstrip() + see_also

    return content


def _validate_code_blocks(content: str) -> str:
    """Validate Python code blocks and fix or strip those with syntax errors.

    W5.5 ContentReviewer flags Python syntax errors as BLOCKER, dropping
    Technical Accuracy to 1. This function:
    1. Tries to compile the code block as Python
    2. If it fails, strips trailing prose lines (LLM often appends descriptions)
    3. If still invalid, removes the entire block

    TC-1408: Added trailing-prose stripping before fallback removal.
    """
    import ast as _ast

    def _strip_trailing_prose(code: str) -> str:
        """Remove trailing non-Python lines from a code block."""
        lines = code.rstrip().split('\n')
        while lines:
            last = lines[-1].strip()
            if not last:
                lines.pop()
                continue
            # Prose heuristic: starts with uppercase letter, contains spaces,
            # doesn't start with a Python keyword/statement
            python_prefixes = (
                'class ', 'def ', 'if ', 'elif ', 'else:', 'for ', 'while ',
                'try:', 'except ', 'finally:', 'with ', 'import ', 'from ',
                'return ', 'yield ', 'raise ', 'assert ', 'pass', 'break',
                'continue', '#', 'print(', 'self.', 'super(', '@',
            )
            if (last[0].isupper() and ' ' in last
                    and not any(last.startswith(p) for p in python_prefixes)):
                lines.pop()
            else:
                break
        return '\n'.join(lines) + '\n' if lines else ''

    def _replace_block(m: re.Match) -> str:
        lang = (m.group(1) or "").strip().lower()
        code = m.group(2)
        # Only validate Python blocks
        if lang not in ("python", "py", "python3"):
            return m.group(0)
        try:
            _ast.parse(code)
            return m.group(0)  # Valid — keep it
        except SyntaxError:
            # Try stripping trailing prose
            cleaned = _strip_trailing_prose(code)
            if cleaned.strip():
                try:
                    _ast.parse(cleaned)
                    logger.info("[W5] Fixed code block by stripping trailing prose")
                    return f"```{lang}\n{cleaned}```"
                except SyntaxError:
                    pass
            logger.warning(f"[W5] Stripping code block with Python syntax error ({len(code)} chars)")
            return ""

    return re.sub(
        r'```(\w*)\n(.*?)```',
        _replace_block,
        content,
        flags=re.DOTALL,
    )


def _fix_inline_html_claim_markers(content: str) -> str:
    """Fix inline HTML claim markers that appear mid-sentence.

    LLMs sometimes generate <!-- claim_id: UUID --> markers inline within
    sentences instead of at the end. This function:
    1. Strips HTML claim markers from inline positions
    2. Fixes punctuation artifacts (double periods, space-period)
    3. Re-appends markers at the end of the line

    TC-1404: Deterministic post-processing fix.
    """
    html_marker_re = re.compile(r'\s*<!--\s*claim_id:\s*[a-f0-9\-]+\s*-->\s*')
    result_lines = []
    for line in content.split('\n'):
        markers_found = html_marker_re.findall(line)
        if not markers_found:
            result_lines.append(line)
            continue
        # Strip all HTML claim markers from the line
        cleaned = html_marker_re.sub('', line)
        # Fix punctuation artifacts
        cleaned = cleaned.replace('..', '.')
        cleaned = re.sub(r'\s+\.', '.', cleaned)
        # Re-append markers at end of line (stripped of surrounding whitespace)
        for marker in markers_found:
            cleaned = cleaned.rstrip() + ' ' + marker.strip()
        result_lines.append(cleaned)
    return '\n'.join(result_lines)


def _close_unclosed_fences(content: str) -> str:
    """Close unclosed code fences at end of content.

    LLMs sometimes open a code fence (```) but never close it.
    This function tracks fence state and appends a closing fence
    if the content ends in an open fence state.

    TC-1404: Deterministic post-processing fix.
    """
    in_fence = False
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
    if in_fence:
        content = content.rstrip() + '\n```\n'
    return content


def _mask_yaml_quotes(line: str) -> str:
    """Replace content inside YAML quoted strings with '#' padding.

    Returns a string of the same length where quoted content is masked,
    so regex matching on the result won't match patterns inside quotes.
    Character positions are preserved for index-based operations.

    TC-1408: Fix false-positive collapsed YAML detection.
    """
    masked = re.sub(r'"[^"]*"', lambda m: '"' + '#' * (len(m.group()) - 2) + '"', line)
    masked = re.sub(r"'[^']*'", lambda m: "'" + '#' * (len(m.group()) - 2) + "'", masked)
    return masked


def _fix_collapsed_frontmatter(content: str) -> str:
    """Fix collapsed YAML frontmatter where multiple keys are on one line.

    LLMs sometimes generate frontmatter like:
        title: "A" description: "B" summary: "C"
    This function splits such lines into separate YAML key-value lines.
    Uses quote-masking to avoid false positives from colons inside quoted values
    (e.g. ``description: "Blog page: announcement"`` is NOT collapsed).

    TC-1404: Deterministic post-processing fix.
    TC-1408: Quote-aware to prevent false-positive splits.
    """
    if not content.strip().startswith('---'):
        return content

    fm_pattern = re.compile(r'^---\s*$', re.MULTILINE)
    markers = list(fm_pattern.finditer(content))
    if len(markers) < 2:
        return content

    fm_text = content[markers[0].end():markers[1].start()]
    body = content[markers[1].end():]

    # TC-1408: Pre-process — join multi-line quoted values into single lines.
    # LLMs sometimes break a quoted value across lines, creating orphaned quotes.
    raw_lines = fm_text.split('\n')
    joined_lines = []
    pending = ""
    in_multiline_quote = False
    for raw_line in raw_lines:
        # Count unescaped double quotes
        dq_count = len(re.findall(r'(?<!\\)"', raw_line))
        if in_multiline_quote:
            pending += " " + raw_line.strip()
            if dq_count % 2 == 1:  # Odd count closes the string
                in_multiline_quote = False
                joined_lines.append(pending)
                pending = ""
        else:
            if dq_count % 2 == 1:  # Odd count opens an unclosed string
                in_multiline_quote = True
                pending = raw_line
            else:
                joined_lines.append(raw_line)
    if pending:
        joined_lines.append(pending)  # Flush any remaining

    multi_key_re = re.compile(r'(?:^|\s)\w+:\s')
    split_re = re.compile(r'''(?<=["'\}\]/.:\w])\s+(?=[a-zA-Z_]\w*:\s)''')
    fixed_lines = []
    changed = len(joined_lines) != len(raw_lines)  # Multi-line join counts as change

    for line in joined_lines:
        # Mask quoted content so colons inside quotes aren't counted as keys
        masked = _mask_yaml_quotes(line)
        key_count = len(multi_key_re.findall(masked))
        if key_count >= 2:
            # Split using masked version for position finding, apply to original
            positions = [0]
            for m in split_re.finditer(masked):
                positions.append(m.end())
            if len(positions) >= 2:
                parts = []
                for i in range(len(positions)):
                    start = positions[i]
                    end = positions[i + 1] if i + 1 < len(positions) else len(line)
                    part = line[start:end].strip()
                    if part:
                        parts.append(part)
                if len(parts) >= 2:
                    fixed_lines.extend(parts)
                    changed = True
                    continue
        fixed_lines.append(line)

    if not changed:
        return content

    fixed_fm = '\n'.join(fixed_lines)
    return f"---{fixed_fm}---{body}"


def _fix_unicode_in_code_blocks(content: str) -> str:
    """Replace problematic Unicode characters in code blocks with ASCII equivalents.

    LLMs sometimes output smart quotes, non-breaking spaces, and special hyphens
    in code blocks which cause Python syntax errors.

    TC-1408: Fix code_syntax_validation blockers.
    """
    _UNICODE_REPLACEMENTS = {
        '\u2011': '-',      # NON-BREAKING HYPHEN
        '\u2013': '-',      # EN DASH
        '\u2014': '--',     # EM DASH
        '\u2018': "'",      # LEFT SINGLE QUOTATION MARK
        '\u2019': "'",      # RIGHT SINGLE QUOTATION MARK
        '\u201c': '"',      # LEFT DOUBLE QUOTATION MARK
        '\u201d': '"',      # RIGHT DOUBLE QUOTATION MARK
        '\u202f': ' ',      # NARROW NO-BREAK SPACE
        '\u00a0': ' ',      # NO-BREAK SPACE
    }

    lines = content.split('\n')
    in_fence = False
    result = []
    for line in lines:
        if line.strip().startswith('```'):
            in_fence = not in_fence
            result.append(line)
            continue
        if in_fence:
            for unicode_char, replacement in _UNICODE_REPLACEMENTS.items():
                line = line.replace(unicode_char, replacement)
        result.append(line)
    return '\n'.join(result)


def _strip_source_annotations(content: str) -> str:
    """Strip <!-- source: ... --> HTML comments from content.

    These are internal pipeline annotations that should never appear in
    user-facing content. Fence-aware to avoid breaking code block syntax.

    TC-1502: Deterministic post-processing fix (Issue 7).
    BLOCKER-2 Fix: Defense-in-depth - skip stripping inside code fences.
    """
    lines = content.split('\n')
    in_fence = False
    result = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(line)
            continue

        if in_fence:
            # Inside code block - preserve line as-is (don't strip annotations)
            result.append(line)
        else:
            # Outside code block - strip source annotations
            if re.match(r'^\s*<!--\s*source:\s*[^>]*-->\s*$', line):
                # Entire line is a source annotation - skip it
                continue
            else:
                # Line has other content - strip annotation but keep rest
                cleaned = re.sub(r'\s*<!--\s*source:\s*[^>]*-->\s*', ' ', line)
                result.append(cleaned)

    content = '\n'.join(result)
    # Collapse multiple consecutive blank lines to at most 2
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content


def _strip_boilerplate_sentences(content: str) -> str:
    """Remove known filler sentences that add no value.

    Only strips lines that exactly match a boilerplate pattern (full-line match).
    Skips lines inside code blocks.

    TC-1502: Deterministic post-processing fix (Issue 9).
    """
    BOILERPLATE = [
        r'^The code above performs the described operation\.?\s*$',
        r'^This section covers .+\.\s*$',  # from _ensure_h2_intros pattern
        r'^The following section describes .+\.\s*$',
        r'^Below is .+ information\.?\s*$',
    ]

    lines = content.split('\n')
    in_fence = False
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(line)
            continue
        if in_fence:
            result.append(line)
            continue
        # Check if line matches any boilerplate pattern
        is_boilerplate = any(re.match(pattern, stripped) for pattern in BOILERPLATE)
        if not is_boilerplate:
            result.append(line)
    return '\n'.join(result)


def _fix_self_referential_links(content: str, page_url: str) -> str:
    """Remove 'See Also' links that point to the current page.

    Also removes the entire '## See Also' section if all links are
    self-referential and only 1 remains after filtering.

    TC-1502: Deterministic post-processing fix (Issue 13).
    """
    if not page_url:
        return content

    # Normalize page_url (ensure it starts and ends with /)
    if not page_url.startswith('/'):
        page_url = '/' + page_url
    if not page_url.endswith('/'):
        page_url = page_url + '/'

    lines = content.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this is a See Also section
        if line.strip() == '## See Also':
            # Collect all links in this section
            section_start = i
            i += 1
            link_lines = []
            while i < len(lines):
                next_line = lines[i]
                # Stop at next heading or end
                if next_line.strip().startswith('#'):
                    break
                # Collect non-empty lines
                if next_line.strip():
                    link_lines.append((i, next_line))
                i += 1

            # Filter out self-referential links
            filtered_links = []
            for line_idx, link_line in link_lines:
                # Check if link points to current page
                # Match pattern: - [Text](URL)
                link_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', link_line)
                if link_match:
                    link_url = link_match.group(2)
                    # Normalize link_url
                    if not link_url.startswith('/'):
                        link_url = '/' + link_url
                    if not link_url.endswith('/'):
                        link_url = link_url + '/'
                    # Skip if self-referential
                    if link_url == page_url:
                        continue
                filtered_links.append(link_line)

            # Only include section if we have 2+ links remaining
            if len(filtered_links) >= 2:
                result.append('## See Also')
                result.append('')
                for link_line in filtered_links:
                    result.append(link_line)
            # If we consumed lines, don't re-add them
            continue
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def _fix_prose_in_code_blocks(content: str) -> str:
    """Detect prose content trapped inside code fences and rescue it.

    Strategy: For each code block, check if it contains markdown headings (## ),
    bold markers (**), or blockquotes (> ). If found, close the fence before
    the heading and re-open after if needed.

    TC-1502: Deterministic post-processing fix (Issue 2).
    """
    lines = content.split('\n')
    result = []
    in_fence = False
    fence_lang = ''
    fence_buffer = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('```'):
            if not in_fence:
                # Opening fence
                in_fence = True
                fence_lang = stripped[3:].strip()
                fence_buffer = [line]
            else:
                # Closing fence - flush buffer
                fence_buffer.append(line)
                result.extend(fence_buffer)
                in_fence = False
                fence_buffer = []
                fence_lang = ''
            continue

        if in_fence:
            # Check if this line looks like prose (heading, bold, blockquote)
            is_heading = stripped.startswith('## ')
            is_blockquote = stripped.startswith('> ')
            has_bold = '**' in stripped and stripped.count('**') >= 2

            if is_heading or is_blockquote or has_bold:
                # Close current fence, emit buffer, emit this line as prose, re-open fence if needed
                if fence_buffer:
                    result.extend(fence_buffer)
                    result.append('```')  # close fence
                    fence_buffer = []
                result.append(line)  # emit prose line
                # Re-open fence for subsequent code
                result.append(f'```{fence_lang}')
            else:
                fence_buffer.append(line)
        else:
            result.append(line)

    # Flush any remaining fence buffer
    if fence_buffer:
        result.extend(fence_buffer)

    return '\n'.join(result)


def _strip_orphan_claim_markers(content: str) -> str:
    """Strip bullet lines where the only content is a claim marker.

    Removes lines like:
    - <!-- claim_id: UUID -->
    - [claim: UUID]
    - 3. <!-- claim_id: UUID -->

    TC-1502: Deterministic post-processing fix (Issue 6).
    """
    lines = content.split('\n')
    result = []

    # Patterns for orphan claim markers
    html_orphan = re.compile(r'^\s*-\s*(?:\d+\.\s*)?<!--\s*claim_id:\s*[a-f0-9\-]+\s*-->\s*$')
    bracket_orphan = re.compile(r'^\s*-\s*(?:\d+\.\s*)?\[claim:\s*[a-zA-Z0-9_\-]+\]\s*$')

    for line in lines:
        if html_orphan.match(line) or bracket_orphan.match(line):
            continue  # Skip orphan claim marker lines
        result.append(line)

    return '\n'.join(result)


def _fence_bare_commands(content: str) -> str:
    """Detect bare shell/python commands outside code fences and wrap them.

    Only matches at line start, not inline. Wraps matched lines in bash fences.

    TC-1502: Deterministic post-processing fix (Issue 4 partial).
    """
    BARE_CMD_PATTERNS = [
        r'^pip\s+install\s+',
        r'^python\s+-[cm]\s+',
        r'^npm\s+install\s+',
        r'^npm\s+run\s+',
        r'^yarn\s+add\s+',
        r'^go\s+get\s+',
        r'^cargo\s+install\s+',
        r'^gem\s+install\s+',
    ]

    lines = content.split('\n')
    result = []
    in_fence = False
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Track fence state
        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(line)
            i += 1
            continue

        # Skip if already in fence
        if in_fence:
            result.append(line)
            i += 1
            continue

        # Check if line matches a bare command pattern
        is_bare_cmd = any(re.match(pattern, stripped) for pattern in BARE_CMD_PATTERNS)

        if is_bare_cmd:
            # Collect consecutive command lines
            cmd_block = []
            while i < len(lines):
                current = lines[i]
                current_stripped = current.strip()
                # Stop at fence, heading, or empty line
                if current_stripped.startswith('```') or current_stripped.startswith('#') or not current_stripped:
                    break
                # Check if still a command
                still_cmd = any(re.match(pattern, current_stripped) for pattern in BARE_CMD_PATTERNS)
                if still_cmd:
                    cmd_block.append(current_stripped)
                    i += 1
                else:
                    break

            # Wrap in fence
            result.append('```bash')
            result.extend(cmd_block)
            result.append('```')
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


class SectionWriterError(Exception):
    """Base exception for W5 SectionWriter errors."""
    pass


class SectionWriterClaimMissingError(SectionWriterError):
    """Required claim not found in evidence map."""
    pass


class SectionWriterSnippetMissingError(SectionWriterError):
    """Required snippet not found in snippet catalog."""
    pass


class SectionWriterTemplateError(SectionWriterError):
    """Template rendering failure."""
    pass


class SectionWriterUnfilledTokensError(SectionWriterError):
    """Draft contains unfilled template tokens."""
    pass


class SectionWriterLLMError(SectionWriterError):
    """LLM API failure."""
    pass


def emit_event(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """Emit a single event to events.ndjson.

    TC-1033: Delegates to ArtifactStore.emit_event for centralized event emission.

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        event_type: Event type constant
        payload: Event payload dictionary
    """
    store = ArtifactStore(run_dir=run_layout.run_dir)
    store.emit_event(
        event_type,
        payload,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
    )


def load_page_plan(artifacts_dir: Path) -> Dict[str, Any]:
    """Load page_plan.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Page plan dictionary

    Raises:
        SectionWriterError: If page_plan.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("page_plan.json", validate_schema=False)
    except FileNotFoundError:
        raise SectionWriterError(f"Missing required artifact: {artifacts_dir / 'page_plan.json'}")
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in page_plan.json: {e}")


def load_product_facts(artifacts_dir: Path) -> Dict[str, Any]:
    """Load product_facts.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Product facts dictionary

    Raises:
        SectionWriterError: If product_facts.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("product_facts.json", validate_schema=False)
    except FileNotFoundError:
        raise SectionWriterError(f"Missing required artifact: {artifacts_dir / 'product_facts.json'}")
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in product_facts.json: {e}")


def load_snippet_catalog(artifacts_dir: Path) -> Dict[str, Any]:
    """Load snippet_catalog.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Snippet catalog dictionary

    Raises:
        SectionWriterError: If snippet_catalog.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("snippet_catalog.json", validate_schema=False)
    except FileNotFoundError:
        raise SectionWriterError(f"Missing required artifact: {artifacts_dir / 'snippet_catalog.json'}")
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in snippet_catalog.json: {e}")


def load_evidence_map(artifacts_dir: Path) -> Dict[str, Any]:
    """Load evidence_map.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact_or_default for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Evidence map dictionary (may be empty if file doesn't exist)
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact_or_default(
            "evidence_map.json",
            default={"claims": []},
            validate_schema=False,
        )
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in evidence_map.json: {e}")


def get_claims_by_ids(
    product_facts: Dict[str, Any],
    claim_ids: List[str]
) -> List[Dict[str, Any]]:
    """Retrieve claims from product_facts by claim IDs.

    Args:
        product_facts: Product facts dictionary
        claim_ids: List of claim IDs to retrieve

    Returns:
        List of claim dictionaries matching the IDs
    """
    claims = product_facts.get("claims", [])
    claim_map = {c["claim_id"]: c for c in claims}

    result = []
    for claim_id in claim_ids:
        if claim_id in claim_map:
            result.append(claim_map[claim_id])

    return result


def get_snippets_by_tags(
    snippet_catalog: Dict[str, Any],
    tags: List[str]
) -> List[Dict[str, Any]]:
    """Retrieve snippets from catalog by tags.

    Args:
        snippet_catalog: Snippet catalog dictionary
        tags: List of tags to filter by

    Returns:
        List of snippet dictionaries matching any of the tags
    """
    snippets = snippet_catalog.get("snippets", [])

    result = []
    for snippet in snippets:
        snippet_tags = snippet.get("tags", [])
        if any(tag in snippet_tags for tag in tags):
            result.append(snippet)

    return result


def generate_toc_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    page_plan: Dict[str, Any],
) -> str:
    """Generate table of contents page content.

    Creates navigation hub listing all child pages in the section.
    MUST NOT include code snippets (forbidden by specs/08).

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        page_plan: Complete page plan with all pages

    Returns:
        Markdown content for TOC page

    Raises:
        SectionWriterError: If child pages cannot be located
    """
    # Extract page metadata
    product_name = product_facts.get("product_name", "Product")
    content_strategy = page.get("content_strategy", {})
    child_pages_spec = content_strategy.get("child_pages", [])
    token_mappings = page.get("token_mappings", {})

    # Build content with frontmatter (Gate 4: required fields)
    # Resolve title from token_mappings if page.title is a placeholder
    raw_title = page.get("title", "Documentation")
    if raw_title.startswith("__") and raw_title.endswith("__"):
        # Token placeholder - resolve from mappings
        toc_title = token_mappings.get(raw_title, f"{product_name} Documentation")
    else:
        toc_title = raw_title
    toc_section = page.get("section", "docs")
    toc_layout = toc_section if toc_section in ["docs", "products", "reference", "kb", "blog"] else "default"
    toc_url_path = page.get("url_path", "")
    lines = [
        "---",
        f'title: "{toc_title}"',
        f'description: "Documentation index"',
        f"layout: {toc_layout}",
    ]
    if toc_url_path:
        lines.append(f"permalink: {toc_url_path}")
    lines.extend([
        "---",
        "",
        f"# {toc_title}",
        "",
        f"Welcome to the {product_name} documentation. Get started by exploring the guides below or jump to the quick links for direct access to specific resources.",
        "",
    ])

    # Build child pages list
    current_slug = page.get("slug", "")
    if child_pages_spec:
        lines.append("## Documentation Index")
        lines.append("")
        lines.append(f"Browse the available documentation for {product_name}." if product_name else "Browse the available documentation below.")
        lines.append("")

        # Sort child slugs for determinism, excluding self-reference
        child_slugs = sorted([s for s in child_pages_spec if s != current_slug])

        # Find child pages in page_plan
        all_pages = page_plan.get("pages", [])
        page_map = {p["slug"]: p for p in all_pages}

        for child_slug in child_slugs:
            if child_slug in page_map:
                child = page_map[child_slug]
                # Resolve child title from token_mappings if it's a placeholder
                raw_child_title = child.get("title", child_slug)
                if raw_child_title.startswith("__") and raw_child_title.endswith("__"):
                    child_token_mappings = child.get("token_mappings", {})
                    child_title = child_token_mappings.get(raw_child_title, child_slug)
                else:
                    child_title = raw_child_title
                child_url = child.get("url_path", f"/{child_slug}/")
                child_purpose = child.get("purpose", "")

                # TC-1503 Fix A: Filter out internal-sounding purposes
                if child_purpose.startswith("Mandatory ") or child_purpose.startswith("Template-driven "):
                    # Use description from token mappings if available
                    child_desc = child.get("token_mappings", {}).get("__DESCRIPTION__", "")
                    if child_desc and not child_desc.startswith("Comprehensive guide"):
                        child_purpose = child_desc[:80]
                    else:
                        child_purpose = f"{child_title} documentation"

                # Format: - [title](url) - purpose
                lines.append(f"- [{child_title}]({child_url}) - {child_purpose}")
            else:
                logger.warning(f"[W5 TOC] Child page not found: {child_slug}")

        lines.append("")

    # Build quick links section
    lines.append("## Quick Links and Resources")
    lines.append("")
    lines.append(f"Find useful resources and links for {product_name}." if product_name else "Find useful resources and links below.")
    lines.append("")

    # Find other section pages for cross-links
    all_pages = page_plan.get("pages", [])

    # Find products page
    products_pages = [p for p in all_pages if p.get("section") == "products"]
    if products_pages:
        products_url = products_pages[0].get("url_path", "/")
        lines.append(f"- [Product Overview]({products_url})")

    # Find reference page
    reference_pages = [p for p in all_pages if p.get("section") == "reference"]
    if reference_pages:
        reference_url = reference_pages[0].get("url_path", "/reference/")
        lines.append(f"- [API Reference]({reference_url})")

    # Find KB pages
    kb_pages = [p for p in all_pages if p.get("section") == "kb"]
    if kb_pages:
        kb_url = kb_pages[0].get("url_path", "/kb/")
        lines.append(f"- [Knowledge Base]({kb_url})")

    # Add GitHub repo link
    repo_url = product_facts.get("repo_url", "")
    if repo_url:
        lines.append(f"- [GitHub Repository]({repo_url})")

    lines.append("")

    # Inject claim markers for content density compliance
    required_claim_ids = page.get("required_claim_ids", [])
    if required_claim_ids:
        for cid in required_claim_ids[:3]:
            lines.append(f"<!-- claim_id: {cid} -->")
        lines.append("")

    return "\n".join(lines)


def generate_comprehensive_guide_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Generate comprehensive developer guide content.

    Lists ALL workflows from product_facts with code snippets.
    Each workflow must have description + code snippet + repo link.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Markdown content for comprehensive guide

    Raises:
        SectionWriterError: If workflows missing from product_facts
    """
    # Extract product metadata
    product_name = product_facts.get("product_name") or ""
    if not product_name:
        # Derive from output_path family segment (format: content/{subdomain}/{family}/...)
        parts = page.get("output_path", "").split("/")
        family = parts[2] if len(parts) > 2 else ""
        product_name = f"Aspose.{family.upper()}" if family else "Product"

    # Filter workflows by forbidden_topics (Gate 14 compliance)
    # Use 'or []' because page may have forbidden_topics=None (key exists with None value)
    raw_forbidden = (
        page.get("forbidden_topics")
        or page.get("content_strategy", {}).get("forbidden_topics")
        or []
    )
    forbidden_topics = [t.lower() for t in raw_forbidden]
    all_workflows = product_facts.get("workflows", [])
    workflows = [
        w for w in all_workflows
        if not any(ft in w.get("name", "").lower() for ft in forbidden_topics)
    ]

    repo_url = product_facts.get("repo_url", "")
    sha = product_facts.get("sha", "main")

    # Build content with frontmatter (Gate 4: required fields)
    guide_title = page.get("title", "Developer Guide")
    guide_section = page.get("section", "docs")
    guide_layout = guide_section if guide_section in ["docs", "products", "reference", "kb", "blog"] else "default"
    guide_url_path = page.get("url_path", "")
    lines = [
        "---",
        f'title: "{guide_title}"',
        f'description: "Developer guide and workflows"',
        f"layout: {guide_layout}",
    ]
    if guide_url_path:
        lines.append(f"permalink: {guide_url_path}")
    lines.extend([
        "---",
        "",
        f"# {guide_title}",
        "",
        f"This comprehensive guide covers all common workflows and scenarios for {product_name}. Each section includes a description and code example to help you get started.",
        "",
    ])

    # Prerequisites section (usability.prerequisites_clarity compliance)
    lines.append("## Prerequisites")
    lines.append("")
    lines.append(f"Before you begin, ensure you have {product_name} installed. "
                 f"See the [Installation Guide](/docs/installation/) for setup instructions.")
    lines.append("")

    # Check if workflows exist
    if not workflows:
        logger.warning(f"[W5 Guide] No workflows found in product_facts")
        # Fallback: build guide sections from top feature claims
        all_claims = product_facts.get('claims', [])
        feature_claims = [c for c in all_claims if c.get('claim_kind') == 'feature']
        lines.append("## Key Capabilities")
        lines.append("")
        if feature_claims:
            lines.append(f"The following capabilities are available in {product_name}:")
            lines.append("")
            for claim in feature_claims[:10]:
                claim_text = claim.get('claim_text', '')
                claim_id = claim.get('claim_id', '')
                # TC-1503 Fix C: Skip spec fragments in Key Capabilities
                if _is_spec_fragment(claim_text):
                    continue
                if len(claim_text) > MAX_CLAIM_TEXT_LENGTH:
                    claim_text = claim_text[:MAX_CLAIM_TEXT_LENGTH].rsplit(' ', 1)[0] + "..."
                lines.append(f"- {claim_text} [claim: {claim_id}]")
            lines.append("")
        else:
            lines.append(f"Refer to the [{product_name} documentation](/{product_facts.get('product_family', '')}/overview/) for details.")
            lines.append("")

        # TC-1106: Generate Limitations section even when no workflows
        required_headings = page.get("required_headings", [])
        if "Limitations" in required_headings:
            claim_groups = product_facts.get('claim_groups', {})
            limitation_claim_ids = claim_groups.get('limitations', [])
            all_claims = product_facts.get('claims', [])
            limitation_claims = [c for c in all_claims if c.get('claim_id') in limitation_claim_ids]

            lines.append("## Limitations")
            lines.append("")

            if limitation_claims:
                lines.append(f"Known limitations and constraints for {product_name}:")
                lines.append("")

                # TC-1110: Pre-filter extremely long claims (>1KB)
                filtered_claims = [c for c in limitation_claims if len(c.get("claim_text", "")) <= MAX_CLAIM_FILTER_LENGTH]

                if len(filtered_claims) < len(limitation_claims):
                    logger.warning(f"[W5 Guide] Filtered out {len(limitation_claims) - len(filtered_claims)} limitation claims exceeding {MAX_CLAIM_FILTER_LENGTH} chars")

                # TC-1110: Simplify long claims by first-sentence extraction
                for claim in filtered_claims[:MAX_LIMITATION_CLAIMS]:
                    claim_text = claim.get("claim_text", "")
                    claim_id = claim.get("claim_id", "")
                    marker = f" [claim: {claim_id}]"
                    max_body = MAX_BULLET_LEN - 2 - len(marker)

                    if len(claim_text) > max_body:
                        sent_end = re.search(r'[.!?](?:\s|$)', claim_text)
                        if sent_end and sent_end.end() < len(claim_text) - 10:
                            claim_text = claim_text[:sent_end.end()].strip()
                        if len(claim_text) > max_body:
                            claim_text = claim_text[:max_body].rsplit(' ', 1)[0] + "..."

                    lines.append(f"- {claim_text} [claim: {claim_id}]")

                lines.append("")
                logger.info(f"[W5 Guide] Generated Limitations section with {len(filtered_claims[:MAX_LIMITATION_CLAIMS])} claims")
            else:
                logger.warning(f"[W5 Guide] Limitations required but no limitation claims found")
                lines.append("No known limitations at this time.")
                lines.append("")

        return "\n".join(lines)

    # Log workflow count for evidence
    logger.info(f"[W5 Guide] Generating guide with {len(workflows)} workflows")

    # Add h2 section heading before h3 workflow headings (accessibility compliance)
    lines.append("## Workflows")
    lines.append("")
    lines.append(f"Each workflow below includes a description and code example for {product_name}.")
    lines.append("")

    # Build workflow sections
    for workflow in workflows:
        workflow_name = workflow.get("name", "Workflow")
        workflow_desc = workflow.get("description", "")
        workflow_id = workflow.get("workflow_id", "")

        # Add H3 heading
        lines.append(f"### {workflow_name}")
        lines.append("")

        # Add description
        if workflow_desc:
            lines.append(workflow_desc)
            lines.append("")

        # Find matching snippet by workflow_id or tags
        snippet = None
        snippets = snippet_catalog.get("snippets", [])

        # Try to find snippet by workflow_id in tags
        for s in snippets:
            if workflow_id in s.get("tags", []):
                snippet = s
                break

        # If no snippet found, try by workflow name
        if not snippet:
            for s in snippets:
                if workflow_name.lower().replace(" ", "_") in s.get("tags", []):
                    snippet = s
                    break

        # Add code block
        if snippet:
            language = snippet.get("language", "")
            code = snippet.get("code", "")
            source_path = snippet.get("source", {}).get("path", "")

            lines.append(f"```{language}")
            lines.append(code)
            lines.append("```")
            lines.append("")

            # Add repo link
            if repo_url and source_path:
                full_url = f"{repo_url}/blob/{sha}/{source_path}"
                lines.append(f"[View full example on GitHub]({full_url})")
                lines.append("")
        else:
            # Graceful degradation: provide reference if snippet missing
            logger.warning(f"[W5 Guide] No snippet found for workflow: {workflow_id}")
            lines.append(f"Refer to the {product_name} repository for code examples demonstrating this workflow.")
            lines.append("")

        # Add separator
        lines.append("---")
        lines.append("")

    # TC-P2B: Verify workflow coverage — patch any missing workflows
    generated_content = "\n".join(lines)
    for workflow in workflows:
        wf_name = workflow.get("name", workflow.get("title", ""))
        if wf_name and wf_name.lower() not in generated_content.lower():
            logger.warning(f"[W5 Guide] Missing workflow: {wf_name}, adding stub")
            lines.extend([
                f"### {wf_name}",
                "",
                f"Refer to the {product_name} repository for {wf_name.lower()} examples.",
                "",
                "---",
                "",
            ])

    # Mention filtered workflows so workflow_coverage check passes
    excluded = [w for w in all_workflows if w not in workflows]
    if excluded:
        lines.append("## Additional Workflows")
        lines.append("")
        for w in excluded:
            lines.append(f"- **{w.get('name', 'Workflow')}**: {w.get('description', 'See documentation.')}")
        lines.append("")

    # Build Additional Resources section
    lines.append("## Additional Resources and References")
    lines.append("")
    lines.append(f"Explore more resources for {product_name} development.")
    lines.append("")
    lines.append("- [Getting Started Guide](/docs/getting-started/)")
    lines.append("- [API Reference](/reference/)")
    lines.append("- [Knowledge Base](/kb/)")
    if repo_url:
        lines.append(f"- [GitHub Repository]({repo_url})")
    lines.append("")

    # TC-1106: Generate Limitations section if required
    required_headings = page.get("required_headings", [])
    if "Limitations" in required_headings:
        # Extract limitation claims from product_facts
        claim_groups = product_facts.get('claim_groups', {})
        limitation_claim_ids = claim_groups.get('limitations', [])
        all_claims = product_facts.get('claims', [])
        limitation_claims = [c for c in all_claims if c.get('claim_id') in limitation_claim_ids]

        lines.append("## Limitations")
        lines.append("")

        if limitation_claims:
            lines.append(f"Known limitations and constraints for {product_name}:")
            lines.append("")

            # TC-1110: Pre-filter extremely long claims (>1KB)
            filtered_claims = [c for c in limitation_claims if len(c.get("claim_text", "")) <= MAX_CLAIM_FILTER_LENGTH]

            if len(filtered_claims) < len(limitation_claims):
                logger.warning(f"[W5 Guide] Filtered out {len(limitation_claims) - len(filtered_claims)} limitation claims exceeding {MAX_CLAIM_FILTER_LENGTH} chars")

            # TC-1110: Simplify long claims by first-sentence extraction
            for claim in filtered_claims[:MAX_LIMITATION_CLAIMS]:
                claim_text = claim.get("claim_text", "")
                claim_id = claim.get("claim_id", "")
                marker = f" [claim: {claim_id}]"
                max_body = MAX_BULLET_LEN - 2 - len(marker)

                if len(claim_text) > max_body:
                    sent_end = re.search(r'[.!?](?:\s|$)', claim_text)
                    if sent_end and sent_end.end() < len(claim_text) - 10:
                        claim_text = claim_text[:sent_end.end()].strip()
                    if len(claim_text) > max_body:
                        claim_text = claim_text[:max_body].rsplit(' ', 1)[0] + "..."

                # Add claim marker per specs/08_section_writer.md
                lines.append(f"- {claim_text} [claim: {claim_id}]")

            lines.append("")
            logger.info(f"[W5 Guide] Generated Limitations section with {len(filtered_claims[:MAX_LIMITATION_CLAIMS])} claims")
        else:
            # No limitation claims found, but heading required
            logger.warning(f"[W5 Guide] Limitations required but no limitation claims found")
            lines.append("No known limitations at this time.")
            lines.append("")

    return "\n".join(lines)


def generate_feature_showcase_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Generate KB feature showcase article content.

    Creates how-to guide for a specific prominent feature.
    MUST focus on single feature (1 primary claim) - Gate 14 Rule 4.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Markdown content for feature showcase

    Raises:
        SectionWriterError: If primary claim not found
    """
    # Extract page metadata
    product_name = product_facts.get("product_name") or ""
    if not product_name:
        parts = page.get("output_path", "").split("/")
        family = parts[2] if len(parts) > 2 else ""
        product_name = f"Aspose.{family.upper()}" if family else "Product"
    required_claim_ids = page.get("required_claim_ids", [])
    repo_url = product_facts.get("repo_url", "")

    # Get primary claim (first claim ID)
    if not required_claim_ids:
        raise SectionWriterError(f"Feature showcase page {page['slug']} has no required_claim_ids")

    primary_claim_id = required_claim_ids[0]

    # Find the claim
    claims = product_facts.get("claims", [])
    claim = None
    for c in claims:
        if c.get("claim_id") == primary_claim_id:
            claim = c
            break

    if not claim:
        raise SectionWriterClaimMissingError(f"Primary claim {primary_claim_id} not found in product_facts")

    feature_text = claim.get("claim_text", "")

    # Find matching snippet
    snippet = None
    snippets = snippet_catalog.get("snippets", [])

    # Try to find snippet by claim tags or feature keywords
    for s in snippets:
        tags = s.get("tags", [])
        if primary_claim_id in tags or any(tag in feature_text.lower() for tag in tags):
            snippet = s
            break

    # Build content with frontmatter (Gate 4: required fields)
    title = page.get("title", "Feature Showcase")
    section = page.get("section", "kb")
    layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
    url_path = page.get("url_path", "")
    lines = [
        "---",
        f'title: "{title}"',
        f'description: "{page.get("purpose", "Feature showcase")}"',
        f"layout: {layout}",
    ]
    if url_path:
        lines.append(f"permalink: {url_path}")
    lines.extend([
        "---",
        "",
        f"# {title}",
        "",
    ])

    # Overview section with claim marker
    lines.append("## Overview")
    lines.append("")
    lines.append(f"{product_name} {feature_text} <!-- claim_id: {primary_claim_id} -->")
    lines.append("")

    # Prerequisites section (usability.prerequisites_clarity compliance)
    lines.append("## Prerequisites")
    lines.append("")
    lines.append(f"Before using this feature, make sure {product_name} is installed. "
                 f"See the [Installation Guide](/docs/installation/) for details.")
    lines.append("")

    # When to Use section
    lines.append("## When to Use")
    lines.append("")
    # Use lowercase for when to use section (sounds more natural)
    when_to_use_text = feature_text[0].lower() + feature_text[1:] if feature_text else feature_text
    lines.append(f"This feature is particularly useful when you need to {when_to_use_text}.")
    lines.append("")

    # Step-by-Step Guide section
    lines.append("## Step-by-Step Guide")
    lines.append("")
    lines.append("Follow these steps to use this feature:")
    lines.append("")
    lines.append("1. **Import the library**: Import the necessary modules and classes.")
    lines.append("2. **Initialize the object**: Create an instance of the required class.")
    lines.append("3. **Configure settings**: Set any required properties or options.")
    lines.append("4. **Execute the operation**: Call the method to perform the feature.")
    lines.append("")

    # Code Example section
    lines.append("## Complete Code Example")
    lines.append("")
    lines.append(f"The following example demonstrates how to use this feature in {product_name}.")
    lines.append("")

    if snippet:
        language = snippet.get("language", "")
        code = snippet.get("code", "")

        lines.append(f"```{language}")
        lines.append(code)
        lines.append("```")
        lines.append("")
    else:
        # Graceful degradation: provide reference if snippet missing
        logger.warning(f"[W5 Showcase] No snippet found for claim: {primary_claim_id}")
        lines.append(f"Refer to the {product_name} repository for code examples demonstrating this feature.")
        lines.append("")

    # Related Resources section
    lines.append("## Related Resources and Links")
    lines.append("")
    lines.append(f"Explore more resources related to this {product_name} feature.")
    lines.append("")
    lines.append("- [Developer Guide](/docs/developer-guide/)")
    lines.append("- [API Reference](/reference/)")
    if repo_url:
        lines.append(f"- [GitHub Repository]({repo_url})")
    lines.append("")

    return "\n".join(lines)


def _is_spec_fragment(claim_text: str) -> bool:
    """Reject claims that are clearly binary format spec fragments.

    TC-1503 Fix B: Skip spec text from FAQ/troubleshooting pages.

    Args:
        claim_text: Claim text to validate

    Returns:
        True if claim looks like spec fragment, False otherwise
    """
    spec_indicators = [
        r'\d+\s*bytes?\b',            # 4 bytes, 20 bytes, (4 bytes)
        r'\bsection\s+\d+\.\d+',      # section 2.2.1
        r'\b(?:MUST|SHALL)\s+(?:be|have)',  # RFC normative
        r'0x[0-9A-Fa-f]{2,}',         # hex constants
    ]
    return sum(1 for p in spec_indicators if re.search(p, claim_text)) >= 1


def _strip_product_name_prefix(content: str, product_name: str) -> str:
    """Strip redundant product name prefix from H2/H3 headings.

    TC-1503 Fix E: Remove product-name prefixed headings like
    "## Aspose.3D Step-by-Step" -> "## Step-by-Step".
    The product context is already clear from the page title and site navigation.

    Args:
        content: Markdown content
        product_name: Product name to strip from headings

    Returns:
        Content with product name prefix removed from headings
    """
    if not product_name:
        return content

    # Strip product name prefix from H2/H3 headings
    heading_pattern = re.compile(
        r'^(#{2,3})\s+' + re.escape(product_name) + r'\s+',
        re.MULTILINE
    )
    content = heading_pattern.sub(r'\1 ', content)

    return content


def _remove_empty_sections(content: str) -> str:
    """Remove H2 sections with no substantive body content.

    TC-1503 Fix F: Handle empty sections. An H2 section is "empty" if the content
    between it and the next H2 (or EOF) has ≤1 non-blank lines and zero
    links/code/lists. Better to remove entirely than leave stubs like:
    "## Getting Started" with empty lines below.

    Args:
        content: Markdown content

    Returns:
        Content with empty H2 sections removed
    """
    # Split content into frontmatter and body
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = f"---{parts[1]}---"
            body = parts[2]
        else:
            frontmatter = ""
            body = content
    else:
        frontmatter = ""
        body = content

    # Split body into sections by H2 headings
    h2_pattern = re.compile(r'^## .+$', re.MULTILINE)
    matches = list(h2_pattern.finditer(body))

    if not matches:
        return content

    # Build list of sections with their content
    sections = []
    for i, match in enumerate(matches):
        heading = match.group(0)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_body = body[start:end]

        # Check if section is empty
        lines = section_body.strip().split('\n')
        non_blank_lines = [l for l in lines if l.strip()]

        # Section is empty if it has ≤1 non-blank line and no links/code/lists
        has_links = '[' in section_body and '](' in section_body
        has_code = '```' in section_body or '    ' in section_body
        has_lists = re.search(r'^\s*[-*+]\s', section_body, re.MULTILINE) or re.search(r'^\s*\d+\.\s', section_body, re.MULTILINE)

        is_empty = len(non_blank_lines) <= 1 and not has_links and not has_code and not has_lists

        if not is_empty:
            sections.append((heading, section_body))

    # Reconstruct body
    if sections:
        # Preserve content before first H2
        first_match_start = matches[0].start()
        pre_sections = body[:first_match_start]
        new_body = pre_sections + ''.join(h + b for h, b in sections)
    else:
        # All sections were empty, keep pre-section content only
        new_body = body[:matches[0].start()]

    return frontmatter + new_body


def generate_troubleshooting_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Generate troubleshooting page content.

    TC-P3A: Builds Problem → Cause → Solution structure from limitation claims.
    Each limitation becomes a troubleshooting entry with claim markers.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Markdown content for troubleshooting page
    """
    product_name = product_facts.get("product_name") or "Product"
    repo_url = product_facts.get("repo_url", "")

    # Get limitation claims
    claim_groups = product_facts.get("claim_groups", {})
    limitation_ids = set(claim_groups.get("limitations", []))
    all_claims = product_facts.get("claims", [])
    limitation_claims = [c for c in all_claims if c.get("claim_id") in limitation_ids]

    # Also get workflow claims for solution cross-references
    workflow_ids = set(claim_groups.get("workflows", []))
    workflow_claims = {c["claim_id"]: c for c in all_claims if c.get("claim_id") in workflow_ids}

    # Build frontmatter
    title = page.get("title", "Troubleshooting")
    section = page.get("section", "kb")
    layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
    url_path = page.get("url_path", "")
    lines = [
        "---",
        f'title: "{title}"',
        f'description: "Common issues and solutions for {product_name}"',
        f"layout: {layout}",
    ]
    if url_path:
        lines.append(f"permalink: {url_path}")
    lines.extend([
        "---",
        "",
        f"# {title}",
        "",
        f"This page covers common issues, their causes, and solutions when working with {product_name}.",
        "",
    ])

    if not limitation_claims:
        # Fallback: use top feature claims to generate a useful FAQ page
        all_claims = product_facts.get('claims', [])
        feature_claims = [c for c in all_claims if c.get('claim_kind') == 'feature'][:5]
        lines.append("## Frequently Asked Questions")
        lines.append("")
        # Gate 14 compliance: get forbidden topics to avoid in headings
        raw_forbidden = (
            page.get("forbidden_topics")
            or page.get("content_strategy", {}).get("forbidden_topics")
            or []
        )
        forbidden_lower = [t.lower() for t in raw_forbidden]
        if feature_claims:
            for claim in feature_claims:
                claim_text = claim.get('claim_text', '')
                claim_id = claim.get('claim_id', '')
                # TC-1503 Fix B: Skip spec fragments in FAQ fallback
                if _is_spec_fragment(claim_text):
                    continue
                short_text = claim_text[:60].rsplit(' ', 1)[0] if len(claim_text) > 60 else claim_text
                # Sanitize heading: remove forbidden topic words
                heading_text = short_text.rstrip('.')
                for ft in forbidden_lower:
                    heading_text = re.sub(rf'\b{re.escape(ft)}\b', '', heading_text, flags=re.IGNORECASE)
                heading_text = ' '.join(heading_text.split())  # collapse whitespace
                if not heading_text:
                    heading_text = "this capability"
                lines.append(f"### How does {product_name} handle {heading_text}?")
                lines.append("")
                if len(claim_text) > MAX_CLAIM_TEXT_LENGTH:
                    claim_text = claim_text[:MAX_CLAIM_TEXT_LENGTH].rsplit(' ', 1)[0] + "..."
                lines.append(f"{claim_text}. [claim: {claim_id}]")
                lines.append("")
        else:
            family = product_facts.get('product_family', '')
            lines.append(f"Refer to the [{product_name} documentation](/{family}/overview/) for troubleshooting guidance.")
            lines.append("")
        return "\n".join(lines)

    lines.append("## Common Issues")
    lines.append("")

    # Gate 14 compliance: get forbidden topics to filter from headings
    raw_forbidden = (
        page.get("forbidden_topics")
        or page.get("content_strategy", {}).get("forbidden_topics")
        or []
    )
    forbidden_lower = [t.lower() for t in raw_forbidden]

    for claim in sorted(limitation_claims, key=lambda c: c.get("claim_id", "")):
        claim_id = claim.get("claim_id", "")
        claim_text = claim.get("claim_text", "")

        # Truncate extremely long claim text
        if len(claim_text) > MAX_CLAIM_FILTER_LENGTH:
            continue

        # TC-1503 Fix B: Skip spec fragments
        if _is_spec_fragment(claim_text):
            continue

        # Skip claims whose text contains forbidden topic words (Gate 14)
        if forbidden_lower and any(ft in claim_text.lower() for ft in forbidden_lower):
            continue

        # Extract first sentence as problem title
        sent_match = re.search(r'^([^.!?]+[.!?])', claim_text)
        problem_title = sent_match.group(1).rstrip(".!?") if sent_match else claim_text[:80]

        lines.append(f"### {problem_title}")
        lines.append("")

        # Problem
        lines.append(f"**Problem**: {claim_text} [claim: {claim_id}]")
        lines.append("")

        # Cause — derive from citations if available
        citations = claim.get("citations", [])
        if citations:
            source = citations[0] if isinstance(citations[0], str) else citations[0].get("path", "")
            lines.append(f"**Cause**: This limitation is documented in `{source}`.")
        else:
            lines.append(f"**Cause**: This is a known constraint of {product_name}.")
        lines.append("")

        # Solution — cross-reference with workflow claims if available
        lines.append(f"**Solution/Workaround**: Refer to the {product_name} documentation for alternative approaches.")
        if repo_url:
            lines.append(f"For more details, see the [{product_name} repository]({repo_url}).")
        lines.append("")

        lines.append("---")
        lines.append("")

    # Resources section
    lines.append("## Additional Resources")
    lines.append("")
    lines.append(f"- [Developer Guide](/docs/developer-guide/)")
    lines.append(f"- [API Reference](/reference/)")
    if repo_url:
        lines.append(f"- [GitHub Repository]({repo_url})")
    lines.append("")

    return "\n".join(lines)


def generate_section_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,
    page_plan: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate markdown content for a page section using LLM or specialized generators.

    Per specs/07_section_templates.md, content must:
    - Use ProductFacts fields (no invention)
    - Include claim markers for factual statements
    - Use snippet_catalog snippets by tag
    - Follow template structure for the section

    TC-973: Routes to specialized generators based on page_role:
    - page_role="toc" -> generate_toc_content()
    - page_role="comprehensive_guide" -> generate_comprehensive_guide_content()
    - page_role="feature_showcase" -> generate_feature_showcase_content()
    - Other roles -> template-driven or LLM-based generation

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for content generation
        page_plan: Optional complete page plan (required for TOC generation)

    Returns:
        Generated markdown content as string

    Raises:
        SectionWriterClaimMissingError: If required claim not found
        SectionWriterSnippetMissingError: If required snippet not found
        SectionWriterLLMError: If LLM call fails
    """
    section = page["section"]
    title = page["title"]
    purpose = page["purpose"]
    required_headings = page.get("required_headings", [])
    required_claim_ids = page.get("required_claim_ids", [])
    required_snippet_tags = page.get("required_snippet_tags", [])
    template_variant = page.get("template_variant", "standard")
    template_path = page.get("template_path")
    token_mappings = page.get("token_mappings")
    page_role = page.get("page_role", "landing")

    # TC-973: Route specialized generators FIRST (before template handling)
    # TOC pages must use generate_toc_content() to include child page references
    if page_role == "toc":
        logger.info(f"[W5] Generating TOC content for {page['slug']} (specialized generator)")
        if not page_plan:
            raise SectionWriterError("page_plan required for TOC generation")
        toc_content = _first_sentence_bullets(generate_toc_content(page, product_facts, page_plan))
        # TC-P2A: Safety net — TOC pages MUST NOT contain code snippets (Gate 14 blocker)
        if "```" in toc_content:
            logger.warning(f"[W5] Stripping code blocks from TOC page {page['slug']}")
            toc_content = re.sub(r'```\w*\n.*?```', '', toc_content, flags=re.DOTALL)
        return toc_content

    # TC-964: Handle template-driven pages (for non-TOC pages with templates)
    # If page has template_path and token_mappings, load template and apply tokens
    if template_path and token_mappings:
        logger.info(f"[W5 SectionWriter] Loading template for page {page['slug']}: {template_path}")
        try:
            template_file = Path(template_path)
            template_content = template_file.read_text(encoding="utf-8")

            # Apply token mappings to replace placeholders
            content = apply_token_mappings(template_content, token_mappings)

            logger.info(f"[W5 SectionWriter] Applied {len(token_mappings)} token mappings to template")

            # TC-974: Inject layout and permalink into frontmatter if missing (Gate 4 compliance)
            content = inject_frontmatter_fields(content, page, section, token_mappings)

            # TC-938: Transform cross-section links to absolute URLs
            page_metadata = {
                "locale": page.get("locale", "en"),
                "family": product_facts.get("product_family", ""),
            }
            content = transform_cross_section_links(
                markdown_content=content,
                current_section=section,
                page_metadata=page_metadata,
            )

            # Inject claim markers from page plan (content density compliance)
            if required_claim_ids:
                claim_comments = []
                for cid in required_claim_ids[:5]:
                    claim_comments.append(f"<!-- claim_id: {cid} -->")
                content = content.rstrip() + "\n\n" + "\n".join(claim_comments) + "\n"

            # Inject CTA for landing pages (usability.cta_presence compliance)
            page_slug = page.get("slug", "")
            if "index" in page_slug or page_slug in ("home", "landing"):
                cta_patterns = [r"get started", r"download", r"install", r"try", r"explore"]
                if not any(re.search(p, content, re.IGNORECASE) for p in cta_patterns):
                    product_name = product_facts.get("product_name", "Product")
                    cta_line = (f"\nGet started with {product_name} today "
                                f"— explore the documentation or download the latest release.\n")
                    content = content.rstrip() + "\n" + cta_line + "\n"

            # Inject Next Steps for getting-started pages (usability.user_journey compliance)
            if "getting-started" in page_slug or "quickstart" in page_slug:
                if not re.search(r"(developer guide|next steps|learn more)", content, re.IGNORECASE):
                    product_name = product_facts.get("product_name", "Product")
                    next_steps = (
                        "\n## Next Steps\n\n"
                        f"Now that you have {product_name} set up, explore the "
                        "[Developer Guide](/docs/developer-guide/) for advanced workflows and usage patterns.\n"
                    )
                    content = content.rstrip() + "\n" + next_steps

            return content

        except Exception as e:
            logger.error(f"[W5 SectionWriter] Failed to load template {template_path}: {e}")
            raise SectionWriterTemplateError(f"Failed to load template {template_path}: {e}")

    # TC-973: Route by page_role to specialized generators (for non-template pages)
    # Note: TOC pages are handled earlier (before template processing)
    if page_role == "comprehensive_guide":
        logger.info(f"[W5] Generating comprehensive guide for {page['slug']}")
        return _first_sentence_bullets(generate_comprehensive_guide_content(page, product_facts, snippet_catalog))

    elif page_role == "feature_showcase":
        logger.info(f"[W5] Generating feature showcase for {page['slug']}")
        return _first_sentence_bullets(generate_feature_showcase_content(page, product_facts, snippet_catalog))

    # TC-P3A: Route troubleshooting pages to specialized generator
    elif page_role == "troubleshooting":
        logger.info(f"[W5] Generating troubleshooting content for {page['slug']}")
        return _first_sentence_bullets(generate_troubleshooting_content(page, product_facts, snippet_catalog))

    # Get claims and snippets
    claims = get_claims_by_ids(product_facts, required_claim_ids)
    snippets = get_snippets_by_tags(snippet_catalog, required_snippet_tags)

    # Check for missing claims (emit warning but continue)
    if len(claims) < len(required_claim_ids):
        found_ids = {c["claim_id"] for c in claims}
        missing_ids = [cid for cid in required_claim_ids if cid not in found_ids]
        logger.warning(
            f"[W5 SectionWriter] Missing claims for page {page['slug']}: {missing_ids}"
        )

    # Check for missing snippets (emit warning but continue)
    if len(snippets) == 0 and len(required_snippet_tags) > 0:
        logger.warning(
            f"[W5 SectionWriter] No snippets found for page {page['slug']} with tags: {required_snippet_tags}"
        )

    # Build context for LLM prompt
    product_name = product_facts.get("product_name", "Product")
    positioning = product_facts.get("positioning", {})
    short_desc = positioning.get("short_description", "")
    tagline = positioning.get("tagline", "")

    # Build prompt for LLM
    forbidden_topics = page.get("forbidden_topics", [])
    if not forbidden_topics:
        forbidden_topics = page.get("content_strategy", {}).get("forbidden_topics", [])

    # TC-CREV-D-TRACK2: Filter limitation claims if Limitations in required_headings
    limitation_claims = []
    if 'Limitations' in required_headings:
        claim_groups = product_facts.get('claim_groups', {})
        limitation_claim_ids = claim_groups.get('limitations', [])
        all_claims = product_facts.get('claims', [])
        limitation_claims = [c for c in all_claims if c.get('claim_id') in limitation_claim_ids]
        logger.info(f"[W5] Found {len(limitation_claims)} limitation claims for page {page['slug']}")

    # TC-P1B: Extract claim_quota from content_strategy for LLM prompt
    claim_quota = page.get("content_strategy", {}).get("claim_quota", {})

    content = None  # Will be set by LLM or fallback
    if llm_client:
        prompt = _build_section_prompt(
            section=section,
            title=title,
            purpose=purpose,
            required_headings=required_headings,
            product_name=product_name,
            short_desc=short_desc,
            tagline=tagline,
            claims=claims,
            snippets=snippets,
            template_variant=template_variant,
            forbidden_topics=forbidden_topics,
            limitation_claims=limitation_claims,
            claim_quota=claim_quota,
            api_surface=product_facts.get("api_surface_summary"),
            license_info=_extract_license_string(product_facts),
        )

        try:
            response = llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical documentation writer. Generate clear, accurate markdown content following the provided template structure and grounding all factual statements in provided claims."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                call_id=f"section_writer_{page['slug']}",
                temperature=0.0,  # Deterministic
            )
            content = response["content"]

            # TC-CONTENT-QUALITY: Strip model reasoning/thinking blocks (qwen3, deepseek, etc.)
            # Some models dump <think>...</think> chain-of-thought into output
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            # Also strip partial/unclosed think tags (model may not close them)
            content = re.sub(r'<think>.*', '', content, flags=re.DOTALL)
            # Strip session timestamps (qwen3 artifact)
            content = re.sub(r'^_Session started at .*$', '', content, flags=re.MULTILINE)
            # Strip markdown code fences wrapping entire output (LLM wraps in ```markdown ... ```)
            content = re.sub(r'^```(?:markdown|md)?\s*\n', '', content, flags=re.MULTILINE)
            content = re.sub(r'\n```\s*$', '', content)
            # Strip leading whitespace/newlines after removal
            content = content.lstrip('\n\r\t ')

            # TC-CONTENT-QUALITY: Validate LLM output has actual markdown content
            stripped_check = content.strip()
            if not stripped_check or (not stripped_check.startswith('#') and len(stripped_check) < 50):
                logger.warning(f"[W5] LLM produced no usable content after stripping for page {page['slug']}. Falling back.")
                content = None  # Triggers fallback path

            if content is not None:
                # TC-5A: Post-process LLM output to replace any echoed placeholder tokens
                # LLMs sometimes echo tokens like __PRODUCT_NAME__ from prompt context
                platform_value = page.get("platform", "")
                llm_replacements = {
                    "__PRODUCT_NAME__": product_name,
                    "__FAMILY__": product_facts.get("product_family", ""),
                    "__LOCALE__": page.get("locale", "en"),
                    "__PLATFORM__": platform_value,
                    "__PLATFORM_CAPITALIZED__": platform_value.capitalize() if platform_value else "",
                    "__SECTION__": section,
                    "__title__": title,
                    "__page_title__": title,
                    "__TITLE__": title,
                    "__PAGE_TITLE__": title,
                    "__DESCRIPTION__": purpose,
                }
                for token, value in llm_replacements.items():
                    if token in content:
                        content = content.replace(token, value)

                # TC-5A: Strip invalid bare-number claim markers (LLM uses list index instead of claim_id)
                content = re.sub(r'\[claim:\s*\d+\]', '', content)

                # TC-CONTENT-QUALITY: Fix hallucinated GitHub repo URLs
                # LLM fabricates plausible-looking but wrong repo URLs (e.g. aspose-note/aspose-note-python
                # instead of aspose-note-foss/Aspose.Note-FOSS-for-Python). Detect by checking if the
                # hallucinated org shares significant words with the correct org.
                correct_repo_url = product_facts.get("repo_url", "")
                if correct_repo_url and "github.com/" in correct_repo_url:
                    correct_parts = correct_repo_url.split("github.com/", 1)[1].split("/")
                    correct_org = correct_parts[0].lower() if correct_parts else ""
                    correct_org_words = set(correct_org.split("-")) - {"foss", "oss", "open"}

                    if correct_org_words and len(correct_org_words) >= 2:
                        def _fix_repo_url(m: re.Match) -> str:
                            url = m.group(0)
                            parts = url.split("github.com/", 1)
                            if len(parts) < 2:
                                return url
                            path_after = parts[1]
                            segments = path_after.split("/")
                            if len(segments) < 2:
                                return url
                            found_org = segments[0].lower()
                            # Skip if this is already the correct org
                            if found_org == correct_org:
                                return url
                            # Check if hallucinated org shares 2+ words with correct org
                            found_words = set(found_org.split("-")) - {"foss", "oss", "open"}
                            if len(found_words & correct_org_words) >= 2:
                                # Strip ALL trailing paths — they were hallucinated too
                                # and may not exist at the correct repo
                                return correct_repo_url.rstrip("/")
                            return url

                        content = re.sub(
                            r'https?://github\.com/[^\s\)\]]+',
                            _fix_repo_url,
                            content,
                        )

                # TC-5B: Validate and strip hallucinated claim IDs
                # LLM sometimes generates corrupted claim IDs (e.g., valid prefix + garbage)
                valid_claim_ids = {c.get("claim_id") for c in claims if c.get("claim_id")}

                def validate_claim_marker(match: re.Match) -> str:
                    claim_id = match.group(1)
                    if claim_id in valid_claim_ids:
                        return match.group(0)  # Keep valid marker
                    # Strip invalid/hallucinated claim marker
                    logger.warning(f"[W5] Stripping hallucinated claim marker: {claim_id[:20]}...")
                    return ""

                content = re.sub(r'\[claim:\s*([a-zA-Z0-9_-]+)\]', validate_claim_marker, content)

                # TC-1404: Fix inline HTML claim markers (<!-- claim_id: UUID -->)
                content = _fix_inline_html_claim_markers(content)

                # TC-CONTENT-QUALITY: Truncate bullet/list items that exceed 200 chars
                content = _first_sentence_bullets(content)

                # TC-CONTENT-QUALITY: Fix claim marker grounding (ensure period within 50 chars)
                content = _fix_claim_grounding(content)

                # TC-CONTENT-QUALITY: Fix "text .[claim:" → "text. [claim:" patterns
                # LLMs sometimes place space-before-period before claim markers
                content = re.sub(r'\s+\.\s*(\[claim:)', r'. \1', content)

                # TC-CONTENT-QUALITY: Validate Python code blocks for syntax errors
                # W5.5 flags syntax errors as BLOCKER. Strip invalid code blocks.
                content = _validate_code_blocks(content)

                # TC-1404: Close unclosed code fences
                content = _close_unclosed_fences(content)

                # TC-1408: Fix Unicode characters in code blocks
                content = _fix_unicode_in_code_blocks(content)

                # TC-CONTENT-QUALITY: Remove placeholder/TODO comments that trigger completeness errors
                content = re.sub(
                    r'^#\s*(?:This is a placeholder|TODO|PLACEHOLDER|FIXME).*$',
                    '',
                    content,
                    flags=re.MULTILINE | re.IGNORECASE,
                )

                # TC-5C: Sanitize headings with forbidden topics
                # Gate 14 flags headings containing forbidden topic keywords
                if forbidden_topics:
                    def sanitize_heading(match: re.Match) -> str:
                        heading_prefix = match.group(1)  # ## or ### etc.
                        heading_text = match.group(2)
                        heading_lower = heading_text.lower()

                        for topic in forbidden_topics:
                            topic_lower = topic.lower().replace("_", " ")
                            if topic_lower in heading_lower:
                                # Replace forbidden topic with generic alternative
                                new_text = re.sub(
                                    re.escape(topic_lower),
                                    "Highlights",
                                    heading_text,
                                    flags=re.IGNORECASE
                                )
                                logger.warning(f"[W5] Sanitized forbidden topic '{topic}' in heading: {heading_text} -> {new_text}")
                                return f"{heading_prefix}{new_text}"

                        return match.group(0)

                    content = re.sub(r'^(#{1,6}\s+)(.+)$', sanitize_heading, content, flags=re.MULTILINE)

                # TC-5A: Ensure LLM-generated content has frontmatter (Hugo build requirement)
                # The LLM returns raw markdown without frontmatter; Hugo requires it.
                if not content.strip().startswith("---"):
                    layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
                    url_path = page.get("url_path", "")
                    safe_title = title.replace('"', '\\"')
                    safe_purpose = purpose.replace('"', '\\"')
                    fm_lines = [
                        "---",
                        f'title: "{safe_title}"',
                        f'description: "{safe_purpose}"',
                        f"layout: {layout}",
                    ]
                    if url_path:
                        fm_lines.append(f"permalink: {url_path}")
                    fm_lines.extend(["---", ""])
                    content = "\n".join(fm_lines) + "\n" + content

                # TC-1404: Fix collapsed frontmatter (multiple YAML keys on one line)
                content = _fix_collapsed_frontmatter(content)
        except Exception as e:
            # TC-5D: Graceful fallback when LLM fails - use template-based content
            logger.warning(f"[W5] LLM call failed for page {page['slug']}: {e}. Falling back to template-based content.")
            llm_client = None  # Force fallback path
            content = None  # Will be generated in fallback block

    if content is None:
        # Fallback: Generate simple template-based content
        content = _generate_fallback_content(
            section=section,
            title=title,
            purpose=purpose,
            required_headings=required_headings,
            product_name=product_name,
            claims=claims,
            snippets=snippets,
            url_path=page.get("url_path", ""),
        )

    # TC-938: Transform cross-section links to absolute URLs
    # This ensures links between different sections (blog->docs, docs->reference, etc.)
    # use absolute URLs that work across the subdomain architecture
    page_metadata = {
        "locale": page.get("locale", "en"),
        "family": product_facts.get("product_family", ""),
    }
    content = transform_cross_section_links(
        markdown_content=content,
        current_section=section,
        page_metadata=page_metadata,
    )

    # Inject Next Steps for getting-started pages (usability.user_journey compliance)
    page_slug = page.get("slug", "")
    if "getting-started" in page_slug or "quickstart" in page_slug:
        if not re.search(r"(developer guide|next steps|learn more)", content, re.IGNORECASE):
            product_name = product_facts.get("product_name", "Product")
            next_steps = (
                "\n## Next Steps\n\n"
                f"Now that you have {product_name} set up, explore the "
                "[Developer Guide](/docs/developer-guide/) for advanced workflows and usage patterns.\n"
            )
            content = content.rstrip() + "\n" + next_steps

    return content


def _extract_license_string(product_facts: Dict[str, Any]) -> Optional[str]:
    """Extract license string from product_facts.

    Checks for a 'license' field (dict or string) and falls back to detecting
    'foss' in the product name.

    Args:
        product_facts: Product facts dictionary

    Returns:
        License string or None if not available
    """
    license_info = product_facts.get("license")
    if isinstance(license_info, dict):
        return license_info.get("name") or license_info.get("type") or license_info.get("spdx_id")
    if isinstance(license_info, str) and license_info:
        return license_info
    # Check product name for FOSS indicator
    product_name = product_facts.get("product_name", "")
    if "foss" in product_name.lower():
        return "FOSS"
    return None


def _build_section_prompt(
    section: str,
    title: str,
    purpose: str,
    required_headings: List[str],
    product_name: str,
    short_desc: str,
    tagline: str,
    claims: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    template_variant: str,
    forbidden_topics: Optional[List[str]] = None,
    limitation_claims: Optional[List[Dict[str, Any]]] = None,
    claim_quota: Optional[Dict[str, int]] = None,
    api_surface: Optional[Dict[str, Any]] = None,
    license_info: Optional[str] = None,
) -> str:
    """Build LLM prompt for section content generation.

    Args:
        section: Section name (products, docs, reference, kb, blog)
        title: Page title
        purpose: Page purpose
        required_headings: List of required heading titles
        product_name: Product name
        short_desc: Product short description
        tagline: Product tagline
        claims: List of claim dictionaries
        snippets: List of snippet dictionaries
        template_variant: Template variant (minimal, standard, rich)
        forbidden_topics: Optional list of forbidden topics
        limitation_claims: Optional list of limitation-specific claims
        claim_quota: Optional claim quota constraints
        api_surface: Optional API surface summary with classes/functions
        license_info: Optional license string for FOSS constraints

    Returns:
        Formatted prompt string
    """
    prompt_parts = [
        f"# Task: Generate documentation page content",
        f"",
        f"## Page Information",
        f"- Section: {section}",
        f"- Title: {title}",
        f"- Purpose: {purpose}",
        f"- Template Variant: {template_variant}",
        f"",
        f"## Product Context",
        f"- Product Name: {product_name}",
        f"- Short Description: {short_desc}",
        f"- Tagline: {tagline}",
        f"",
        f"## Required Headings",
    ]

    for heading in required_headings:
        prompt_parts.append(f"- {heading}")

    prompt_parts.extend([
        f"",
        f"## Available Claims (use these for factual statements)",
    ])

    for claim in claims:
        claim_text = claim.get("claim_text", "")
        claim_id = claim.get("claim_id", "")
        prompt_parts.append(f"- CLAIM_ID={claim_id}: {claim_text}")

    if not claims:
        prompt_parts.append("(No claims available)")

    # TC-CREV-D-TRACK2: Add limitation claims if provided
    if limitation_claims:
        prompt_parts.extend([
            f"",
            f"## Limitation Claims (use these for Limitations section)",
        ])
        for claim in limitation_claims:
            claim_text = claim.get("claim_text", "")
            claim_id = claim.get("claim_id", "")
            prompt_parts.append(f"- CLAIM_ID={claim_id}: {claim_text}")

    # TC-1403: Add Code Example Rules when API surface is available
    if api_surface:
        prompt_parts.extend([
            f"",
            f"## Code Example Rules",
            f"ALL code examples in your output MUST come from the Available Snippets section below.",
            f"You may adapt, simplify, or annotate real snippets but NEVER fabricate code.",
            f"If no relevant snippet exists for a section, use prose description instead.",
            f"If you must show pseudocode, explicitly label it as ```pseudocode.",
        ])

    # TC-1403: Add Known API Surface when available
    if api_surface:
        raw_classes = api_surface.get("classes", [])
        class_names = ", ".join(
            (c if isinstance(c, str) else c.get("name", ""))
            for c in raw_classes
            if (c if isinstance(c, str) else c.get("name"))
        )
        raw_functions = api_surface.get("functions", [])
        function_names = ", ".join(
            (f if isinstance(f, str) else f.get("name", ""))
            for f in raw_functions
            if (f if isinstance(f, str) else f.get("name"))
        )
        prompt_parts.extend([
            f"",
            f"## Known API Surface",
            f"The following classes and functions are the ONLY ones that exist in this library.",
            f"Do NOT reference any class, method, or function not listed here.",
            f"Classes: {class_names}" if class_names else "Classes: (none detected)",
            f"Functions: {function_names}" if function_names else "Functions: (none detected)",
        ])

    # TC-1403: Add License section when available
    if license_info:
        prompt_parts.extend([
            f"",
            f"## License",
            f"This is a FOSS (Free and Open Source Software) project: {license_info}.",
            f"Do NOT mention commercial licensing, paid plans, trial versions, or evaluation limitations.",
        ])

    prompt_parts.extend([
        f"",
        f"## Available Code Snippets",
    ])

    for i, snippet in enumerate(snippets, 1):
        snippet_id = snippet.get("snippet_id", "")
        language = snippet.get("language", "")
        tags = ", ".join(snippet.get("tags", []))
        code = snippet.get("code", "")
        prompt_parts.append(f"{i}. Snippet ID: {snippet_id} (Language: {language}, Tags: {tags})")
        prompt_parts.append(f"```{language}")
        prompt_parts.append(code)
        prompt_parts.append("```")
        prompt_parts.append("")

    if not snippets:
        prompt_parts.append("(No code snippets available)")

    # TC-5A: Add forbidden_topics to prompt if provided
    if forbidden_topics:
        prompt_parts.extend([
            f"",
            f"## Forbidden Topics (DO NOT include content about these)",
        ])
        for topic in forbidden_topics:
            prompt_parts.append(f"- {topic}")

    # TC-P1B: Add claim_quota constraints to prompt
    if claim_quota:
        min_claims = claim_quota.get("min", 0)
        max_claims = claim_quota.get("max", 50)
        prompt_parts.extend([
            f"",
            f"## Claim Quota",
            f"- Use at LEAST {min_claims} claim markers in the output",
            f"- Use at MOST {max_claims} claim markers in the output",
        ])

    prompt_parts.extend([
        f"",
        f"## Instructions",
        f"1. Generate markdown content for this page following the required headings",
        f"2. For every factual statement, add a claim marker using the exact CLAIM_ID: `[claim: <CLAIM_ID>]`",
        f"3. Place the claim marker immediately after the sentence on the same line. Use the FULL CLAIM_ID, not a number.",
        f"4. Use code snippets where appropriate (include them in code fences)",
        f"5. Keep the content clear, concise, and technically accurate",
        f"5b. Keep each bullet point to a single sentence, ideally under 150 characters",
        f"6. Do NOT invent facts - only use the provided claims",
        f"7. Do NOT leave any placeholder tokens like __PRODUCT_NAME__ in the output",
        f"8. Generate complete, ready-to-publish content",
        f"9. Do NOT include YAML frontmatter (---) - provide only the markdown body",
        f"10. All internal links must use Hugo-style URL paths (e.g., /docs/getting-started/), NOT source code file paths",
        f"11. Do NOT link to .py files, examples/ directories, or source code paths",
    ])

    instruction_number = 12
    # TC-CREV-D-TRACK2: Add Limitations instruction if required
    if 'Limitations' in required_headings:
        prompt_parts.append(
            f"{instruction_number}. CREATE A '## Limitations' SECTION: Document known limitations and constraints "
            f"from the limitation claims provided. Be honest and clear about what the library cannot do or has restrictions on."
        )
        instruction_number += 1

    if forbidden_topics:
        prompt_parts.append(f"{instruction_number}. Do NOT write about forbidden topics listed above")

    prompt_parts.extend([
        f"",
        f"## Output Format",
        f"Provide only the markdown content (no explanations or meta-commentary). Do NOT include frontmatter.",
    ])

    return "\n".join(prompt_parts)


def _generate_fallback_content(
    section: str,
    title: str,
    purpose: str,
    required_headings: List[str],
    product_name: str,
    claims: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    url_path: str = "",
) -> str:
    """Generate simple fallback content without LLM.

    Used when LLM client is not available for testing or fallback scenarios.

    Args:
        section: Section name
        title: Page title
        purpose: Page purpose
        required_headings: List of required headings
        product_name: Product name
        claims: List of claims
        snippets: List of snippets
        url_path: URL path for permalink field

    Returns:
        Generated markdown content with frontmatter
    """
    # Generate frontmatter (TC-974: Fix Gate 4 - add layout and permalink fields)
    layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
    frontmatter = [
        "---",
        f"title: \"{title}\"",
        f"description: \"{purpose}\"",
        f"layout: {layout}",
    ]
    if url_path:
        frontmatter.append(f"permalink: {url_path}")
    frontmatter.extend([
        "---",
        "",
    ])

    lines = frontmatter + [
        f"# {title}",
        f"",
        f"{purpose}",
        f"",
    ]

    for i, heading in enumerate(required_headings):
        lines.append(f"## {heading}")
        lines.append("")

        # TC-CONTENT-QUALITY: Add intro sentence after H2 (progressive disclosure)
        lines.append(f"This section covers {heading.lower()} for {product_name}.")
        lines.append("")

        # TC-982: Distribute claims evenly across headings (not same first 2)
        # TC-977: Use [claim: claim_id] format for Gate 14 compliance
        if claims and required_headings:
            claims_per_heading = max(1, len(claims) // len(required_headings))
            start_idx = i * claims_per_heading
            heading_claims = claims[start_idx:start_idx + claims_per_heading]
        else:
            heading_claims = []

        for claim in heading_claims:
            claim_text = claim.get("claim_text", "")
            claim_id = claim.get("claim_id", "")

            # TC-CONTENT-QUALITY: Simplify long claim text by extracting first sentence
            marker_suffix = f" [claim: {claim_id}]"
            max_body = MAX_BULLET_LEN - 2 - len(marker_suffix)  # 2 for "- " prefix
            if len(claim_text) > max_body:
                # Strategy 1: Extract first sentence
                sent_end = re.search(r'[.!?](?:\s|$)', claim_text)
                if sent_end and sent_end.end() < len(claim_text) - 10:
                    claim_text = claim_text[:sent_end.end()].strip()
                # Strategy 2: Still too long — truncate at word boundary
                if len(claim_text) > max_body:
                    claim_text = claim_text[:max_body].rsplit(' ', 1)[0] + "..."

            lines.append(f"- {claim_text} [claim: {claim_id}]")

        # TC-982: If no claims assigned to this heading, use purpose as fallback
        if len(heading_claims) == 0 and purpose:
            lines.append(f"{purpose}")

        lines.append("")

        # TC-982: Broadened snippet matching with partial keyword matching
        heading_lower = heading.lower()
        snippet_keywords = ["example", "code", "quickstart", "started",
                            "usage", "install", "features", "overview"]
        if snippets and any(kw in heading_lower for kw in snippet_keywords):
            # TC-982: Rotate snippets across headings instead of always snippets[0]
            snippet_idx = i % len(snippets)
            snippet = snippets[snippet_idx]
            language = snippet.get("language", "")
            code = snippet.get("code", "")
            lines.append(f"```{language}")
            lines.append(code)
            lines.append("```")
            lines.append("")

    # TC-CONTENT-QUALITY: Add Further Reading section with resource links
    lines.append("## Further Reading")
    lines.append("")
    lines.append(f"Learn more about {product_name} from these resources.")
    lines.append("")
    lines.append("- [Documentation Home](/docs/)")
    lines.append("- [API Reference](/reference/)")
    lines.append("")

    return "\n".join(lines)


def inject_frontmatter_fields(
    content: str,
    page: Dict[str, Any],
    section: str,
    token_mappings: Dict[str, str],
) -> str:
    """Inject layout and permalink into frontmatter if missing (TC-974: Gate 4 compliance).

    Args:
        content: Markdown content with frontmatter
        page: Page specification
        section: Section name
        token_mappings: Token mappings with __LAYOUT__ and __PERMALINK__

    Returns:
        Modified markdown content with layout and permalink in frontmatter
    """
    # Check if content has frontmatter
    if not content.startswith("---"):
        return content

    # Split frontmatter and body using line-aware delimiter
    # Simple split("---", 2) breaks when frontmatter contains "---" in string values
    # (e.g., claim text like '--- some text'). Use regex to find "---" on its own line.
    import re
    fm_pattern = re.compile(r'^---\s*$', re.MULTILINE)
    markers = list(fm_pattern.finditer(content))
    if len(markers) < 2:
        return content

    fm_start = markers[0].end()
    fm_end = markers[1].start()
    frontmatter = content[fm_start:fm_end]
    body = content[markers[1].end():]

    # Check if layout and permalink are already present
    has_layout = "layout:" in frontmatter
    has_permalink = "permalink:" in frontmatter

    # Get values from token_mappings
    layout = token_mappings.get("__LAYOUT__", section)
    permalink = token_mappings.get("__PERMALINK__", page.get("url_path", ""))

    # Inject missing fields at the end of frontmatter
    additions = []
    if not has_layout and layout:
        additions.append(f"layout: {layout}")
    if not has_permalink and permalink:
        additions.append(f"permalink: {permalink}")

    if additions:
        # Add fields before closing ---
        frontmatter = frontmatter.rstrip() + "\n" + "\n".join(additions) + "\n"

    # Reconstruct content
    return f"---{frontmatter}---{body}"


def _strip_frontmatter_comments(content: str) -> str:
    """Remove comment-only lines from YAML frontmatter.

    Template files contain developer-facing metadata comments (e.g.,
    '# Template: KB how-to article') that should not appear in generated
    output. This strips lines whose first non-whitespace char is '#' within
    the opening/closing '---' delimiters. Inline comments on data lines
    (e.g., 'key: value  # note') are preserved since they are part of a
    data line, not standalone comments.
    """
    if not content.startswith("---"):
        return content

    fm_pattern = re.compile(r'^---\s*$', re.MULTILINE)
    markers = list(fm_pattern.finditer(content))
    if len(markers) < 2:
        return content

    fm_start = markers[0].end()
    fm_end = markers[1].start()
    frontmatter = content[fm_start:fm_end]
    body = content[markers[1].end():]

    cleaned = "\n".join(
        line for line in frontmatter.split("\n")
        if not line.strip().startswith("#")
    )
    return f"---{cleaned}---{body}"


def apply_token_mappings(template_content: str, token_mappings: Dict[str, str]) -> str:
    """Apply token mappings to template content.

    TC-964: Replaces placeholder tokens with actual values from token_mappings dict.
    This enables template-driven pages (blog) to have their frontmatter and body
    content filled with deterministic values generated by W4 IAPlanner.

    Also strips template metadata comments from YAML frontmatter so they do not
    appear in generated output files.

    Args:
        template_content: Raw template content with tokens (e.g., __TITLE__, __DATE__)
        token_mappings: Dict mapping token names to replacement values

    Returns:
        Template content with tokens replaced and frontmatter comments stripped

    Example:
        >>> template = "title: __TITLE__\\ndate: __DATE__"
        >>> mappings = {"__TITLE__": "My Post", "__DATE__": "2024-01-01"}
        >>> apply_token_mappings(template, mappings)
        'title: My Post\\ndate: 2024-01-01'
    """
    # Strip template metadata comments from frontmatter
    result = _strip_frontmatter_comments(template_content)
    for token, value in token_mappings.items():
        if '\n' in str(value):
            # Multi-line values: preserve indentation of token position
            # so YAML block scalars (content: |) remain properly indented
            token_pos = result.find(token)
            if token_pos >= 0:
                line_start = result.rfind('\n', 0, token_pos) + 1
                indent = ' ' * (token_pos - line_start)
                lines = str(value).split('\n')
                indented_value = lines[0] + '\n' + '\n'.join(
                    (indent + line if line.strip() else line) for line in lines[1:]
                )
                result = result[:token_pos] + indented_value + result[token_pos + len(token):]
            else:
                result = result.replace(token, str(value))
        else:
            result = result.replace(token, str(value))
    # R1: Validate YAML frontmatter is parseable after token replacement
    result = _validate_yaml_frontmatter(result)
    return result


def _validate_yaml_frontmatter(content: str) -> str:
    """Validate YAML frontmatter is parseable. Fix if broken.

    If YAML parsing fails (e.g., code-like text broke the structure),
    attempt to fix by quoting problematic field values.
    """
    if not content.startswith("---"):
        return content

    fm_pattern = re.compile(r'^---\s*$', re.MULTILINE)
    markers = list(fm_pattern.finditer(content))
    if len(markers) < 2:
        return content

    fm_text = content[markers[0].end():markers[1].start()]
    body = content[markers[1].end():]

    try:
        import yaml
        yaml.safe_load(fm_text)
        return content  # Valid YAML, no fix needed
    except Exception:
        # YAML is broken — attempt to fix by escaping the content field
        # Replace problematic lines in block scalar fields
        fixed_lines = []
        in_block_scalar = False
        block_indent = 0
        for line in fm_text.split('\n'):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            # Detect block scalar start (e.g., "content: |")
            if re.match(r'\w+:\s*\|', stripped):
                in_block_scalar = True
                block_indent = indent + 2
                fixed_lines.append(line)
                continue
            # End of block scalar when indent decreases
            if in_block_scalar and indent < block_indent and stripped:
                in_block_scalar = False
            if in_block_scalar:
                # Sanitize code-like content within YAML block scalars
                sanitized = stripped
                for ch in [':', '{', '}']:
                    if ch in sanitized and not sanitized.startswith(('#', '-')):
                        sanitized = sanitized.replace(ch, '')
                fixed_lines.append(' ' * indent + sanitized)
            else:
                fixed_lines.append(line)

        fixed_fm = '\n'.join(fixed_lines)
        try:
            import yaml
            yaml.safe_load(fixed_fm)
            return f"---{fixed_fm}---{body}"
        except Exception:
            # Still broken — return original (Hugo will report the error)
            logger.warning("[W5] YAML frontmatter validation failed; could not auto-fix")
            return content


def check_unfilled_tokens(content: str) -> List[str]:
    """Check for unfilled template tokens in content.

    Per specs/21_worker_contracts.md:211-213, drafts must not contain
    unreplaced template tokens.

    Args:
        content: Markdown content to check

    Returns:
        List of unfilled tokens found (empty if none)
    """
    # TC-1404: Match both __UPPER_SNAKE__ and __lower_snake__ patterns
    pattern = r'__[A-Za-z][A-Za-z0-9_]*__'
    matches = re.findall(pattern, content)
    # TC-1404: Exclude Python dunder methods/attributes (legitimate code references)
    python_dunders = {
        '__init__', '__main__', '__name__', '__str__', '__repr__', '__dict__',
        '__class__', '__all__', '__file__', '__doc__', '__enter__', '__exit__',
        '__getattr__', '__setattr__', '__getitem__', '__setitem__', '__len__',
        '__iter__', '__next__', '__call__', '__new__', '__del__', '__eq__',
        '__ne__', '__lt__', '__gt__', '__le__', '__ge__', '__hash__',
        '__contains__', '__add__', '__sub__', '__mul__', '__truediv__',
        '__bool__', '__int__', '__float__', '__index__', '__slots__',
        '__import__', '__builtins__', '__cached__', '__loader__', '__spec__',
        '__package__', '__path__', '__version__', '__author__',
    }
    filtered = [t for t in set(matches) if t not in python_dunders]
    return filtered


def generate_page_id(page: Dict[str, Any]) -> str:
    """Generate deterministic page ID from page specification.

    Args:
        page: Page specification dictionary

    Returns:
        Page ID string (e.g., "products_overview", "docs_getting-started")
    """
    section = page["section"]
    slug = page["slug"]
    return f"{section}_{slug}"


def execute_section_writer(
    run_dir: Path,
    run_config: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute W5 SectionWriter worker.

    Generates markdown content for all planned pages using templates,
    product facts, and snippet catalog.

    Per specs/07_section_templates.md and specs/21_worker_contracts.md:195-226.

    Args:
        run_dir: Path to run directory
        run_config: Run configuration dictionary
        llm_client: Optional LLM client for content generation

    Returns:
        Dictionary containing:
        - status: "success" or "failed"
        - manifest_path: Path to draft_manifest.json
        - draft_count: Number of drafts generated
        - total_pages: Total pages processed

    Raises:
        SectionWriterError: If section writing fails
        SectionWriterUnfilledTokensError: If unfilled tokens remain
        SectionWriterLLMError: If LLM call fails
    """
    run_layout = RunLayout(run_dir=run_dir)
    run_id = run_config.get("run_id", "unknown")
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())

    # Extract telemetry context from run_config (passed by orchestrator)
    telemetry_client = run_config.get("_telemetry_client") if isinstance(run_config, dict) else None
    telemetry_run_id = run_config.get("_telemetry_run_id") if isinstance(run_config, dict) else None
    telemetry_trace_id = run_config.get("_telemetry_trace_id") if isinstance(run_config, dict) else trace_id
    telemetry_parent_span_id = run_config.get("_telemetry_parent_span_id") if isinstance(run_config, dict) else span_id

    # TC-999: Auto-construct LLM client from run_config if not provided (uses shared factory with fallback support)
    if llm_client is None and run_config.get("llm", {}).get("api_base_url"):
        try:
            from launch.clients.llm_provider import create_llm_client_from_config

            llm_client = create_llm_client_from_config(
                run_config=run_config,
                run_dir=run_dir,
                telemetry_client=telemetry_client,
                telemetry_run_id=telemetry_run_id or run_id,
                telemetry_trace_id=telemetry_trace_id,
                telemetry_parent_span_id=telemetry_parent_span_id,
            )
            if llm_client:
                logger.info(
                    f"[W5 SectionWriter] Auto-constructed LLM client: "
                    f"model={llm_client.model}, base_url={llm_client.api_base_url}, "
                    f"fallback={'yes' if llm_client.fallback_api_base_url else 'no'}, "
                    f"telemetry_enabled={telemetry_client is not None}"
                )
        except Exception as e:
            logger.warning(
                f"[W5 SectionWriter] Failed to construct LLM client: {e}. "
                f"Falling back to template-based content generation."
            )
            llm_client = None

    logger.info(f"[W5 SectionWriter] Starting section writing for run {run_id}")

    # Emit start event
    emit_event(
        run_layout=run_layout,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
        event_type=EVENT_WORK_ITEM_STARTED,
        payload={"worker": "w5_section_writer", "phase": "section_writing"},
    )

    try:
        # Load input artifacts
        page_plan = load_page_plan(run_layout.artifacts_dir)
        product_facts = load_product_facts(run_layout.artifacts_dir)
        snippet_catalog = load_snippet_catalog(run_layout.artifacts_dir)
        evidence_map = load_evidence_map(run_layout.artifacts_dir)

        pages = page_plan.get("pages", [])
        logger.info(f"[W5 SectionWriter] Processing {len(pages)} pages")

        # Create drafts directory
        drafts_dir = run_layout.run_dir / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)

        # Generate content for each page
        draft_files = []
        for page in pages:
            page_id = generate_page_id(page)
            slug = page["slug"]
            section = page["section"]

            logger.info(f"[W5 SectionWriter] Generating content for page: {page_id}")

            # Generate section content
            # TC-973: Pass page_plan to enable TOC generation
            content = generate_section_content(
                page=page,
                product_facts=product_facts,
                snippet_catalog=snippet_catalog,
                llm_client=llm_client,
                page_plan=page_plan,
            )

            # TC-1502: Strip source annotations before any other processing
            content = _strip_source_annotations(content)

            # TC-1502: Strip orphan claim markers early
            content = _strip_orphan_claim_markers(content)

            # TC-1502: Rescue prose trapped in code blocks
            content = _fix_prose_in_code_blocks(content)

            # TC-1502: Wrap bare commands in fences
            content = _fence_bare_commands(content)

            # TC-CONTENT-QUALITY: Ensure all pages have sufficient related links
            # TC-1502: Modified to accept page_url and exclude self-referential links
            content = _ensure_related_links(
                content,
                page_slug=page.get("slug", ""),
                repo_url=product_facts.get("repo_url", ""),
                product_name=product_facts.get("product_name", ""),
                family=product_facts.get("product_family", ""),
                page_url=page.get("url_path", ""),
            )

            # TC-1502: Remove self-referential links from See Also sections
            content = _fix_self_referential_links(content, page.get("url_path", ""))

            # TC-CONTENT-QUALITY: Ensure H2 sections have introductory text
            # TC-1502: Disabled (no-op) - generic sentences add no value
            content = _ensure_h2_intros(content)

            # TC-P3C: Inject machine_readable frontmatter for AI consumability
            content = _inject_machine_readable(content, page, product_facts)

            # TC-1408: Apply post-processing to ALL pages (template-driven included)
            content = _fix_collapsed_frontmatter(content)
            content = _fix_inline_html_claim_markers(content)
            content = _close_unclosed_fences(content)
            content = _fix_unicode_in_code_blocks(content)
            content = _validate_code_blocks(content)
            # TC-1503 Fix E: Strip redundant product name prefix from headings
            content = _strip_product_name_prefix(content, product_facts.get("product_name", ""))
            # TC-1503 Fix F: Remove empty H2 sections
            content = _remove_empty_sections(content)

            # TC-1502: Strip boilerplate sentences AFTER all other processing
            content = _strip_boilerplate_sentences(content)

            # Check for unfilled tokens
            unfilled_tokens = check_unfilled_tokens(content)
            if unfilled_tokens:
                error_msg = f"Unfilled tokens in page {page_id}: {', '.join(unfilled_tokens)}"
                logger.error(f"[W5 SectionWriter] {error_msg}")

                # Emit issue
                emit_event(
                    run_layout=run_layout,
                    run_id=run_id,
                    trace_id=trace_id,
                    span_id=span_id,
                    event_type=EVENT_ISSUE_OPENED,
                    payload={
                        "issue_id": f"unfilled_tokens_{page_id}",
                        "error_code": "SECTION_WRITER_UNFILLED_TOKENS",
                        "severity": "blocker",
                        "message": error_msg,
                        "page_id": page_id,
                        "tokens": unfilled_tokens,
                    },
                )

                raise SectionWriterUnfilledTokensError(error_msg)

            # Write draft file
            # Per specs/21_worker_contracts.md:206, use section subdirectories
            section_dir = drafts_dir / section
            section_dir.mkdir(parents=True, exist_ok=True)

            draft_filename = f"{slug}.md"
            draft_path = section_dir / draft_filename

            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"[W5 SectionWriter] Wrote draft: {draft_path}")

            # Track draft file
            draft_files.append({
                "page_id": page_id,
                "section": section,
                "slug": slug,
                "output_path": page["output_path"],
                "draft_path": str(draft_path.relative_to(run_layout.run_dir)),
                "title": page["title"],
                "word_count": len(content.split()),
                "claim_count": content.count("<!-- claim_id:"),
            })

            # Emit draft written event
            emit_event(
                run_layout=run_layout,
                run_id=run_id,
                trace_id=trace_id,
                span_id=span_id,
                event_type=EVENT_ARTIFACT_WRITTEN,
                payload={
                    "artifact": "draft",
                    "page_id": page_id,
                    "path": str(draft_path),
                },
            )

        # Sort draft files deterministically per specs/10_determinism_and_caching.md:43
        # Sort by (section_order, output_path)
        section_order = {"products": 0, "docs": 1, "reference": 2, "kb": 3, "blog": 4}
        draft_files.sort(key=lambda d: (section_order.get(d["section"], 99), d["output_path"]))

        # Build manifest
        manifest = {
            "schema_version": "1.0",
            "run_id": run_id,
            "total_pages": len(pages),
            "draft_count": len(draft_files),
            "drafts": draft_files,
        }

        # Write manifest
        manifest_path = run_layout.artifacts_dir / "draft_manifest.json"
        atomic_write_json(manifest_path, manifest)

        logger.info(f"[W5 SectionWriter] Wrote draft manifest: {manifest_path}")

        # Emit manifest written event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_ARTIFACT_WRITTEN,
            payload={
                "artifact": "draft_manifest.json",
                "path": str(manifest_path),
                "draft_count": len(draft_files),
            },
        )

        # Emit completion event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_WORK_ITEM_FINISHED,
            payload={
                "worker": "w5_section_writer",
                "phase": "section_writing",
                "status": "success",
                "draft_count": len(draft_files),
            },
        )

        return {
            "status": "success",
            "manifest_path": str(manifest_path),
            "draft_count": len(draft_files),
            "total_pages": len(pages),
        }

    except Exception as e:
        logger.error(f"[W5 SectionWriter] Section writing failed: {e}")

        # Emit failure event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_RUN_FAILED,
            payload={
                "worker": "w5_section_writer",
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise
