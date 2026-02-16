"""Shared Content Sanitizer: Deterministic post-processing pipeline for markdown content.

Extracted from W5 SectionWriter (worker.py) to enable reuse by W5 AND W5.5.
Each function is a standalone sanitizer that can be composed into pipelines.

The canonical pipeline order is defined by `run_pipeline()`, which applies all
sanitizers in dependency-safe order. Sanitizers in the same phase are independent
and could theoretically run in parallel.

Phase 1 (Early): Structural fixes that other sanitizers depend on
Phase 2 (Fence): Code fence normalization chain (strict ordering)
Phase 3 (Content): Content-level fixes (mostly independent)
Phase 4 (Strip): Remove unwanted patterns (independent)
Phase 5 (Late): Quality enforcement (may add content)

Usage:
    from launch.workers._shared.content_sanitizer import run_pipeline, SanitizerContext

    ctx = SanitizerContext(page=page, product_facts=product_facts, ...)
    content = run_pipeline(content, ctx)

Or individual functions:
    from launch.workers._shared.content_sanitizer import strip_emojis, fix_code_fences
    content = strip_emojis(content)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ...util.logging import get_logger

logger = get_logger()


# ── Constants ─────────────────────────────────────────────────────────────────

# Section-specific minimum body word counts (TC-1733)
MIN_BODY_WORDS = {
    "blog": 300,
    "docs": 200,
    "products": 150,
    "reference": 100,
    "kb": 200,
    "default": 150,
}


# ── Context Object ────────────────────────────────────────────────────────────

class SanitizerContext:
    """Bundled context for sanitizers that need more than just content.

    Pure sanitizers (content -> content) ignore this. Context-dependent sanitizers
    (e.g., ensure_related_links, enforce_quality_floor) use it for page metadata,
    product info, and LLM client access.
    """

    def __init__(
        self,
        page: Optional[Dict[str, Any]] = None,
        product_facts: Optional[Dict[str, Any]] = None,
        snippet_catalog: Optional[Dict[str, Any]] = None,
        llm_client: Optional[Any] = None,
    ):
        self.page = page or {}
        self.product_facts = product_facts or {}
        self.snippet_catalog = snippet_catalog or {}
        self.llm_client = llm_client

    @property
    def product_name(self) -> str:
        return self.product_facts.get("product_name", "")

    @property
    def page_slug(self) -> str:
        return self.page.get("slug", "")

    @property
    def page_url(self) -> str:
        return self.page.get("url_path", "")

    @property
    def section(self) -> str:
        return self.page.get("section", "default")

    @property
    def repo_url(self) -> str:
        return self.product_facts.get("repo_url", "")

    @property
    def family(self) -> str:
        return self.product_facts.get("product_family", "")


# ── Phase 1: Early / Structural ──────────────────────────────────────────────

def strip_source_annotations(content: str) -> str:
    """Strip <!-- source: ... --> HTML comments from content.

    Fence-aware to avoid breaking code block syntax.
    TC-1502: Deterministic post-processing fix (Issue 7).
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
            result.append(line)
        else:
            if re.match(r'^\s*<!--\s*source:\s*[^>]*-->\s*$', line):
                continue
            else:
                cleaned = re.sub(r'\s*<!--\s*source:\s*[^>]*-->\s*', ' ', line)
                result.append(cleaned)

    content = '\n'.join(result)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content


def strip_orphan_claim_markers(content: str) -> str:
    """Strip bullet lines where the only content is a claim marker.

    Removes lines like:
    - <!-- claim_id: UUID -->
    - [claim: UUID]
    TC-1502: Deterministic post-processing fix (Issue 6).
    """
    lines = content.split('\n')
    result = []
    html_orphan = re.compile(r'^\s*-\s*(?:\d+\.\s*)?<!--\s*claim(?:_id)?:\s*[a-zA-Z0-9_\-]+\s*-->\s*$')
    bracket_orphan = re.compile(r'^\s*-\s*(?:\d+\.\s*)?\[claim:\s*[a-zA-Z0-9_\-]+\]\s*$')

    for line in lines:
        if html_orphan.match(line) or bracket_orphan.match(line):
            continue
        result.append(line)

    return '\n'.join(result)


def fix_prose_in_code_blocks(content: str) -> str:
    """Detect prose content trapped inside code fences and rescue it.

    For each code block, check if it contains markdown headings (## ),
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
                in_fence = True
                fence_lang = stripped[3:].strip()
                fence_buffer = [line]
            else:
                fence_buffer.append(line)
                result.extend(fence_buffer)
                in_fence = False
                fence_buffer = []
                fence_lang = ''
            continue

        if in_fence:
            is_heading = stripped.startswith('## ')
            is_blockquote = stripped.startswith('> ')
            has_bold = '**' in stripped and stripped.count('**') >= 2

            if is_heading or is_blockquote or has_bold:
                if fence_buffer:
                    result.extend(fence_buffer)
                    result.append('```')
                    fence_buffer = []
                result.append(line)
                result.append(f'```{fence_lang}')
            else:
                fence_buffer.append(line)
        else:
            result.append(line)

    if fence_buffer:
        result.extend(fence_buffer)

    return '\n'.join(result)


def fence_bare_commands(content: str) -> str:
    """Detect bare shell/python commands outside code fences and wrap them.

    Only matches at line start, not inline.
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

        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(line)
            i += 1
            continue

        if in_fence:
            result.append(line)
            i += 1
            continue

        is_bare_cmd = any(re.match(pattern, stripped) for pattern in BARE_CMD_PATTERNS)

        if is_bare_cmd:
            cmd_block = []
            while i < len(lines):
                current = lines[i]
                current_stripped = current.strip()
                if current_stripped.startswith('```') or current_stripped.startswith('#') or not current_stripped:
                    break
                still_cmd = any(re.match(pattern, current_stripped) for pattern in BARE_CMD_PATTERNS)
                if still_cmd:
                    cmd_block.append(current_stripped)
                    i += 1
                else:
                    break

            result.append('```bash')
            result.extend(cmd_block)
            result.append('```')
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def fix_license_page(content: str, page: Dict[str, Any], product_facts: Dict[str, Any]) -> str:
    """Ensure license page contains actual licensing information.

    TC-1830: License pages should contain license type, terms, and usage info.
    """
    slug = page.get("slug", "")
    if slug != "license":
        return content

    product_name = product_facts.get("product_name", "")
    license_info = product_facts.get("license")
    license_str = ""
    if isinstance(license_info, dict):
        license_str = license_info.get("name") or license_info.get("type") or license_info.get("spdx_id", "")
    elif isinstance(license_info, str):
        license_str = license_info

    repo_url = product_facts.get("repo_url", "")

    parts = content.split('---', 2)
    if len(parts) >= 3:
        frontmatter = parts[0] + '---' + parts[1] + '---\n'
    else:
        frontmatter = ''

    license_display = license_str if license_str else "Open Source"
    body_lines = [
        f"## License Information",
        f"",
        f"{product_name} is released as Free and Open Source Software (FOSS) under the **{license_display}** license.",
        f"",
        f"### What This Means",
        f"",
        f"- You are free to use {product_name} in personal and commercial projects.",
        f"- You may modify the source code to suit your needs.",
        f"- You may distribute copies and derivative works.",
        f"- Attribution requirements depend on the specific license terms.",
        f"",
        f"### License Terms",
        f"",
        f"The complete license text is available in the [LICENSE file in the source repository]({repo_url}/blob/main/LICENSE)." if repo_url else f"The complete license text is available in the LICENSE file included with the source distribution.",
        f"",
        f"### No Commercial Restrictions",
        f"",
        f"As FOSS software, {product_name} has no commercial licensing requirements, no paid plans, and no evaluation limitations. The full feature set is available to all users.",
        f"",
        f"## See Also",
        f"",
    ]
    if repo_url:
        body_lines.append(f"- [Source Code Repository]({repo_url})")
    family = product_facts.get("product_family", "")
    body_lines.append(f"- [{product_name} Documentation Overview](/{family}/python/overview/)")

    return frontmatter + '\n'.join(body_lines) + '\n'


def ensure_related_links(
    content: str,
    page_slug: str,
    repo_url: str,
    product_name: str,
    family: str = "",
    page_url: str = "",
) -> str:
    """Ensure page has >=2 markdown links to satisfy usability.related_links check.

    W5.5 ContentReviewer flags pages with <2 links as WARN.
    TC-1502: Modified to accept page_url and exclude self-referential links.
    """
    if page_slug in ("_index", "index"):
        return content

    if '## See Also' in content or '## see also' in content.lower():
        return content

    link_count = len(re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content))
    if link_count >= 2:
        return content

    normalized_page_url = page_url
    if normalized_page_url:
        if not normalized_page_url.startswith('/'):
            normalized_page_url = '/' + normalized_page_url
        if not normalized_page_url.endswith('/'):
            normalized_page_url = normalized_page_url + '/'

    links = []
    if repo_url:
        links.append(f"- [Source Code Repository]({repo_url})")
    name = product_name or "the library"
    docs_base = f"/{family}" if family else ""

    candidate_links = [
        (f"- [Getting Started with {name}]({docs_base}/getting-started/)", f"{docs_base}/getting-started/"),
        (f"- [{name} Documentation Overview]({docs_base}/overview/)", f"{docs_base}/overview/"),
    ]

    for link_text, link_url in candidate_links:
        norm_url = link_url
        if not norm_url.startswith('/'):
            norm_url = '/' + norm_url
        if not norm_url.endswith('/'):
            norm_url = norm_url + '/'
        if normalized_page_url and norm_url == normalized_page_url:
            continue
        links.append(link_text)

    if links and len(links) >= 2:
        see_also = "\n\n## See Also\n\n" + "\n".join(links[:3]) + "\n"
        content = content.rstrip() + see_also

    return content


def fix_self_referential_links(content: str, page_url: str) -> str:
    """Remove 'See Also' links that point to the current page.

    Also removes the entire '## See Also' section if all links are
    self-referential and only 1 remains after filtering.
    TC-1502: Deterministic post-processing fix (Issue 13).
    """
    if not page_url:
        return content

    if not page_url.startswith('/'):
        page_url = '/' + page_url
    if not page_url.endswith('/'):
        page_url = page_url + '/'

    lines = content.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == '## See Also':
            section_start = i
            i += 1
            link_lines = []
            while i < len(lines):
                next_line = lines[i]
                if next_line.strip().startswith('#'):
                    break
                if next_line.strip():
                    link_lines.append((i, next_line))
                i += 1

            filtered_links = []
            for line_idx, link_line in link_lines:
                link_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', link_line)
                if link_match:
                    link_url = link_match.group(2)
                    if not link_url.startswith('/'):
                        link_url = '/' + link_url
                    if not link_url.endswith('/'):
                        link_url = link_url + '/'
                    if link_url == page_url:
                        continue
                filtered_links.append(link_line)

            if len(filtered_links) >= 2:
                result.append('## See Also')
                result.append('')
                for link_line in filtered_links:
                    result.append(link_line)
            continue
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def fix_trailing_whitespace_in_links(content: str) -> str:
    """Strip trailing whitespace from markdown link URLs.

    Fixes: [text](url/ ) -> [text](url/)
    TC-1820.
    """
    def _strip_trailing(match):
        text = match.group(1)
        url = match.group(2).rstrip()
        return f"[{text}]({url})"

    return re.sub(r'\[([^\]]*)\]\(([^)]*\S)\s+\)', _strip_trailing, content)


def ensure_h2_intros(content: str) -> str:
    """Ensure H2 sections have introductory text.

    TC-1502: Disabled (no-op). Generic sentences add no value.
    Returns content unchanged.
    """
    return content


def inject_machine_readable(
    content: str,
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
) -> str:
    """TC-P3C: Inject machine_readable block into frontmatter for AI consumability."""
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

    if "machine_readable:" in frontmatter:
        return content

    _HEX_CLAIM_ID = re.compile(r'^[a-f0-9]{8,}$')
    claim_ids = sorted(set(
        m.group(1).strip()
        for m in re.finditer(r'\[claim:\s*([^\]]+)\]', body)
        if _HEX_CLAIM_ID.match(m.group(1).strip())
    ))

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
    frontmatter = frontmatter.rstrip() + "\n" + mr_block

    return f"---{frontmatter}---{body}"


# ── Phase 2: Fence Normalization Chain ────────────────────────────────────────
# These MUST run in order: collapsed_frontmatter → inline_html → close_unclosed →
# nested_fences → code_fences → merge_adjacent → unicode → validate

def _mask_yaml_quotes(line: str) -> str:
    """Replace content inside YAML quoted strings with '#' padding.

    Returns a string of the same length where quoted content is masked.
    TC-1408: Fix false-positive collapsed YAML detection.
    """
    masked = re.sub(r'"[^"]*"', lambda m: '"' + '#' * (len(m.group()) - 2) + '"', line)
    masked = re.sub(r"'[^']*'", lambda m: "'" + '#' * (len(m.group()) - 2) + "'", masked)
    return masked


def fix_collapsed_frontmatter(content: str) -> str:
    """Fix collapsed YAML frontmatter where multiple keys are on one line.

    Uses quote-masking to avoid false positives from colons inside quoted values.
    TC-1404 + TC-1408.
    """
    if not content.strip().startswith('---'):
        return content

    fm_pattern = re.compile(r'^---\s*$', re.MULTILINE)
    markers = list(fm_pattern.finditer(content))
    if len(markers) < 2:
        return content

    fm_text = content[markers[0].end():markers[1].start()]
    body = content[markers[1].end():]

    raw_lines = fm_text.split('\n')
    joined_lines = []
    pending = ""
    in_multiline_quote = False
    for raw_line in raw_lines:
        dq_count = len(re.findall(r'(?<!\\)"', raw_line))
        if in_multiline_quote:
            pending += " " + raw_line.strip()
            if dq_count % 2 == 1:
                in_multiline_quote = False
                joined_lines.append(pending)
                pending = ""
        else:
            if dq_count % 2 == 1:
                in_multiline_quote = True
                pending = raw_line
            else:
                joined_lines.append(raw_line)
    if pending:
        joined_lines.append(pending)

    multi_key_re = re.compile(r'(?:^|\s)\w+:\s')
    split_re = re.compile(r'''(?<=["'\}\]/.:\w])\s+(?=[a-zA-Z_]\w*:\s)''')
    fixed_lines = []
    changed = len(joined_lines) != len(raw_lines)

    for line in joined_lines:
        masked = _mask_yaml_quotes(line)
        key_count = len(multi_key_re.findall(masked))
        if key_count >= 2:
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


def fix_inline_html_claim_markers(content: str) -> str:
    """Fix inline HTML claim markers that appear mid-sentence.

    Strips them from inline positions and re-appends at end of line.
    TC-1404: Deterministic post-processing fix.
    """
    html_marker_re = re.compile(r'\s*<!--\s*claim_id:\s*[a-f0-9\-]+\s*-->\s*')
    result_lines = []
    for line in content.split('\n'):
        markers_found = html_marker_re.findall(line)
        if not markers_found:
            result_lines.append(line)
            continue
        cleaned = html_marker_re.sub('', line)
        cleaned = cleaned.replace('..', '.')
        cleaned = re.sub(r'\s+\.', '.', cleaned)
        for marker in markers_found:
            cleaned = cleaned.rstrip() + ' ' + marker.strip()
        result_lines.append(cleaned)
    return '\n'.join(result_lines)


def close_unclosed_fences(content: str) -> str:
    """Close unclosed code fences at end of content.

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


def fix_nested_fences(content: str) -> str:
    """Fix content where >50% of body is trapped inside code fences.

    TC-1810: When token values contain ``` markers, the template-rendered
    content can have nested/unclosed fences.
    """
    parts = content.split('---', 2)
    if len(parts) >= 3:
        frontmatter = parts[0] + '---' + parts[1] + '---'
        body = parts[2]
    else:
        frontmatter = ''
        body = content

    body_lines = body.split('\n')
    total_lines = len([l for l in body_lines if l.strip()])
    if total_lines == 0:
        return content

    in_fence = False
    fenced_lines = 0
    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence and stripped:
            fenced_lines += 1

    ratio = fenced_lines / total_lines if total_lines > 0 else 0
    if ratio <= 0.35:
        return content

    logger.warning(f"[Sanitizer TC-1810] {ratio:.0%} of body lines inside fences — stripping spurious fences")

    result_lines: List[str] = []
    code_buffer: List[str] = []
    in_actual_code = False

    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            if code_buffer:
                result_lines.append('```python')
                result_lines.extend(code_buffer)
                result_lines.append('```')
                code_buffer = []
                in_actual_code = False
            continue

        is_code = (
            stripped.startswith(('import ', 'from ', 'def ', 'class ', 'pip ', 'python '))
            or stripped.startswith(('>>> ', '... ', '$ ', '# '))
            or (stripped.startswith('#') and not stripped.startswith('## '))
            or re.match(r'^[\w.]+\s*[=(]', stripped)
        )

        if is_code:
            code_buffer.append(line)
            in_actual_code = True
        else:
            if code_buffer:
                result_lines.append('```python')
                result_lines.extend(code_buffer)
                result_lines.append('```')
                code_buffer = []
                in_actual_code = False
            result_lines.append(line)

    if code_buffer:
        result_lines.append('```python')
        result_lines.extend(code_buffer)
        result_lines.append('```')

    return frontmatter + '\n'.join(result_lines)


def fix_single_backtick_code_blocks(content: str) -> str:
    """Convert single-backtick multi-line code to triple-backtick fenced code blocks.

    Detects patterns like:
    `code line 1
    code line 2
    code line 3`

    And converts to:
    ```
    code line 1
    code line 2
    code line 3
    ```

    TC-1821.
    """
    def _fix_block(match):
        code = match.group(1)
        # Only convert if it spans multiple lines
        if '\n' in code:
            return f"```\n{code}\n```"
        return match.group(0)  # Leave single-line inline code alone

    return re.sub(r'`([^`]{20,}?)`', _fix_block, content, flags=re.DOTALL)


def fix_code_fences(content: str) -> str:
    """Fix broken code fences: orphaned fences, pseudocode blocks, unclosed fences.

    TC-1662 + TC-1731: Comprehensive code fence fixes.
    """
    lang_normalize = {
        'Python': 'python', 'PYTHON': 'python', 'Py': 'python', 'py': 'python',
        'Javascript': 'javascript', 'JS': 'javascript', 'js': 'javascript',
        'Bash': 'bash', 'BASH': 'bash', 'Shell': 'bash', 'shell': 'bash', 'sh': 'bash',
        'Csharp': 'csharp', 'C#': 'csharp',
        'Cpp': 'cpp', 'C++': 'cpp',
        'Json': 'json', 'JSON': 'json',
        'Yaml': 'yaml', 'YAML': 'yaml', 'Yml': 'yaml',
        'Xml': 'xml', 'XML': 'xml',
    }

    lines = content.split('\n')
    result_lines: List[str] = []
    in_fence = False
    fence_line_idx = -1
    fence_has_lang = False
    fence_content_lines = 0

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('```') and not in_fence:
            rest = stripped[3:].strip()
            if rest == '.':
                continue

        if in_fence and stripped == '```.':
            stripped = '```'
            line = '```'

        if stripped.startswith('```'):
            if not in_fence:
                lang = stripped[3:].strip()
                if lang in lang_normalize:
                    lang = lang_normalize[lang]

                if lang.lower() == 'pseudocode':
                    result_lines.append('```python')
                    in_fence = True
                    fence_line_idx = len(result_lines) - 1
                    fence_has_lang = True
                    fence_content_lines = 0
                    continue
                in_fence = True
                fence_line_idx = len(result_lines)
                fence_has_lang = bool(lang)
                fence_content_lines = 0
                if lang and lang != stripped[3:].strip():
                    result_lines.append(f'```{lang}')
                    continue
            else:
                if fence_content_lines == 0 and 0 <= fence_line_idx < len(result_lines):
                    del result_lines[fence_line_idx]
                    in_fence = False
                    fence_line_idx = -1
                    continue
                in_fence = False
                fence_line_idx = -1
        elif in_fence:
            fence_content_lines += 1
            if stripped.startswith('## '):
                result_lines.append('```')
                in_fence = False
                fence_line_idx = -1

        result_lines.append(line)

    if in_fence:
        if fence_has_lang:
            result_lines.append('```')
        else:
            if 0 <= fence_line_idx < len(result_lines):
                del result_lines[fence_line_idx]

    return '\n'.join(result_lines)


def merge_adjacent_code_blocks(content: str) -> str:
    """TC-1907: Merge consecutive code blocks of the same language."""
    content = re.sub(
        r'```\s*\n\s*```(\w+)\n',
        r'\n',
        content,
    )
    return content


def fix_unicode_in_code_blocks(content: str) -> str:
    """Replace problematic Unicode characters in code blocks with ASCII equivalents.

    TC-1408: Fix code_syntax_validation blockers.
    """
    _UNICODE_REPLACEMENTS = {
        '\u2011': '-',
        '\u2013': '-',
        '\u2014': '--',
        '\u2018': "'",
        '\u2019': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u202f': ' ',
        '\u00a0': ' ',
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


def validate_code_blocks(content: str) -> str:
    """Validate Python code blocks and fix or strip those with syntax errors.

    TC-1408: Added trailing-prose stripping before fallback removal.
    """
    import ast as _ast

    def _strip_trailing_prose(code: str) -> str:
        lines = code.rstrip().split('\n')
        while lines:
            last = lines[-1].strip()
            if not last:
                lines.pop()
                continue
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
        if lang not in ("python", "py", "python3"):
            return m.group(0)
        try:
            _ast.parse(code)
            return m.group(0)
        except SyntaxError:
            cleaned = _strip_trailing_prose(code)
            if cleaned.strip():
                try:
                    _ast.parse(cleaned)
                    logger.info("[Sanitizer] Fixed code block by stripping trailing prose")
                    return f"```{lang}\n{cleaned}```"
                except SyntaxError:
                    pass
            logger.warning(f"[Sanitizer] Stripping code block with Python syntax error ({len(code)} chars)")
            return ""

    return re.sub(
        r'```(\w*)\n(.*?)```',
        _replace_block,
        content,
        flags=re.DOTALL,
    )


# ── Phase 3: Content-Level Fixes ─────────────────────────────────────────────

def strip_product_name_prefix(content: str, product_name: str) -> str:
    """Strip redundant product name prefix from H2/H3 headings.

    TC-1503 Fix E.
    """
    if not product_name:
        return content

    heading_pattern = re.compile(
        r'^(#{2,3})\s+' + re.escape(product_name) + r'\s+',
        re.MULTILINE
    )
    content = heading_pattern.sub(r'\1 ', content)
    return content


def remove_empty_sections(content: str) -> str:
    """Remove H2 sections with no substantive body content.

    TC-1503 Fix F.
    """
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

    h2_pattern = re.compile(r'^## .+$', re.MULTILINE)
    matches = list(h2_pattern.finditer(body))

    if not matches:
        return content

    sections = []
    for i, match in enumerate(matches):
        heading = match.group(0)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_body = body[start:end]

        lines = section_body.strip().split('\n')
        non_blank_lines = [l for l in lines if l.strip()]

        has_links = '[' in section_body and '](' in section_body
        has_code = '```' in section_body or '    ' in section_body
        has_lists = re.search(r'^\s*[-*+]\s', section_body, re.MULTILINE) or re.search(r'^\s*\d+\.\s', section_body, re.MULTILINE)

        is_empty = len(non_blank_lines) <= 1 and not has_links and not has_code and not has_lists

        if not is_empty:
            sections.append((heading, section_body))

    if sections:
        first_match_start = matches[0].start()
        pre_sections = body[:first_match_start]
        new_body = pre_sections + ''.join(h + b for h, b in sections)
    else:
        new_body = body[:matches[0].start()]

    return frontmatter + new_body


# ── Phase 4: Strip Unwanted Patterns ─────────────────────────────────────────

def strip_boilerplate_sentences(content: str) -> str:
    """Remove known filler sentences that add no value.

    TC-1502: Deterministic post-processing fix (Issue 9).
    """
    BOILERPLATE = [
        r'^The code above performs the described operation\.?\s*$',
        r'^This section covers .+\.\s*$',
        r'^The following section describes .+\.\s*$',
        r'^Below is .+ information\.?\s*$',
        r'^Refer to the .+ documentation .+\.\s*$',
        r'^Refer to the .+ repository .+\.\s*$',
        r'^Please refer to .+\.\s*$',
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
        is_boilerplate = any(re.match(pattern, stripped) for pattern in BOILERPLATE)
        if not is_boilerplate:
            result.append(line)
    return '\n'.join(result)


def strip_visible_claim_markers(content: str) -> str:
    """Strip visible claim markers from body text.

    Frontmatter already contains claim_ids. HTML comment markers preserved for W7 Gate 14.
    Round 11.5 + Round 13 TC-1800/1801/1802.
    """
    # Fullwidth bracket markers: 【hex】, 【claim: hex】, truncated 【hex at EOL
    content = re.sub(r'\s*【[a-f0-9]{6,}】', '', content)
    content = re.sub(r'\s*【claim:?\s*[a-f0-9]*】?', '', content)
    content = re.sub(r'\s*【[a-f0-9]+[^】]*$', '', content, flags=re.MULTILINE)
    # Square bracket markers: [claim: hex]
    content = re.sub(r'\s*\[claim:\s*[a-f0-9\-]+\]', '', content)
    # Broken/incomplete HTML claim markers (missing closing -->)
    content = re.sub(r'<!--\s*claim:[^>]*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'<!--\s*claim:\s*-->', '', content)
    # Parenthesized and bare hex IDs (6+ chars — covers short 7-char, 12-char, and full 64-char SHA256)
    content = re.sub(r'\(\[?[a-f0-9]{6,}\]?\)', '', content)
    content = re.sub(r'\[[a-f0-9]{6,}\]', '', content)
    content = re.sub(r'<!--\s*claim_id:\s*[a-f0-9]+\s*-->\n?', '', content)
    content = re.sub(r'``(?!`)', '', content)
    content = re.sub(r'`\[claim:\s*[a-f0-9]+\]`', '', content)
    content = re.sub(r'\([a-f0-9]{6,}[…\.]*\)', '', content)
    # Collapse double spaces within text (NOT at line starts — preserves YAML/code indentation)
    content = re.sub(r'(?<=\S)  +', ' ', content)
    content = re.sub(r' +\n', '\n', content)
    return content


def strip_forbidden_topic_headings(content: str, page: Dict[str, Any]) -> str:
    """Remove or rename headings that mention forbidden topics (Gate 14 compliance).

    When a page's content_strategy defines forbidden_topics, generated headings
    must not contain those topic keywords. This function removes such headings
    and their content (up to the next heading at the same or higher level).
    """
    forbidden = page.get("content_strategy", {}).get("forbidden_topics", [])
    if not forbidden:
        return content

    # Normalize forbidden topics for matching
    forbidden_lower = [t.lower().replace("_", " ") for t in forbidden]

    lines = content.split("\n")
    result = []
    skip_until_level = None  # If set, skip lines until a heading at this level or higher

    for line in lines:
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).lower()

            # If we're skipping and hit a heading at same/higher level, stop skipping
            if skip_until_level is not None and level <= skip_until_level:
                skip_until_level = None

            # Check if this heading mentions a forbidden topic
            if skip_until_level is None:
                is_forbidden = any(ft in heading_text for ft in forbidden_lower)
                if is_forbidden:
                    skip_until_level = level
                    continue

        if skip_until_level is not None:
            continue

        result.append(line)

    return "\n".join(result)


def strip_double_periods(content: str) -> str:
    """Strip double periods (..) from body text, preserving ellipsis (...).

    TC-1803.
    """
    content = re.sub(r'(?<!\.)\.\.(?!\.)', '.', content)
    return content


def strip_emojis(content: str) -> str:
    """Strip emoji characters from body text (not from frontmatter).

    TC-1805.
    """
    parts = content.split('---', 2)
    if len(parts) >= 3:
        frontmatter = parts[0] + '---' + parts[1] + '---'
        body = parts[2]
    else:
        frontmatter = ''
        body = content

    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U0000FE00-\U0000FE0F"
        "\U0000200D"
        "]+",
        flags=re.UNICODE,
    )
    body = emoji_pattern.sub('', body)
    body = re.sub(r'  +', ' ', body)

    return frontmatter + body


def strip_ci_badges(content: str) -> str:
    """Strip CI badge markdown from body text.

    TC-1806.
    """
    content = re.sub(r'\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)', '', content)
    content = re.sub(r'!\[(?:CI|Build|Tests?|Coverage|Status|Badge)[^\]]*\]\([^)]*\)', '', content)
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    return content


def strip_illustrative_comments(content: str) -> str:
    """Remove '# Illustrative example' comments from code blocks.

    TC-1807.
    """
    content = re.sub(r'^(\s*)# Illustrative example\s*\n', '', content, flags=re.MULTILINE)
    return content


def fix_truncated_sentences(content: str) -> str:
    """Fix lines that end mid-sentence (no terminal punctuation).

    TC-1831.
    """
    parts = content.split('---', 2)
    if len(parts) >= 3:
        frontmatter = parts[0] + '---' + parts[1] + '---'
        body = parts[2]
    else:
        frontmatter = ''
        body = content

    lines = body.split('\n')
    in_fence = False
    result = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(line)
            continue

        if in_fence:
            result.append(line)
            continue

        if (
            not stripped
            or stripped.startswith('#')
            or stripped.startswith(('-', '*', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.'))
            or stripped.startswith('[')
            or stripped.startswith('<!--')
            or stripped.startswith('|')
            or stripped.endswith('-->')
            or ':' in stripped[:20]
        ):
            result.append(line)
            continue

        if stripped and len(stripped) > 20 and not stripped[-1] in '.!?:;)"\'>':
            line = line.rstrip() + '.'

        result.append(line)

    return frontmatter + '\n'.join(result)


def normalize_module_names(content: str, product_facts: Dict[str, Any]) -> str:
    """Normalize import/module names to canonical form.

    TC-1821.
    """
    family = product_facts.get("product_family", "").lower()
    product_name = product_facts.get("product_name", "")

    replacements: List[tuple] = []

    if family == "3d" or "3d" in product_name.lower():
        replacements = [
            (r'\baspose_3d_foss\b', 'aspose.threed'),
            (r'\baspose_3d\b', 'aspose.threed'),
            (r'\bAspose3D\b', 'aspose.threed'),
            (r'\baspose3d\b', 'aspose.threed'),
        ]
    elif family == "note" or "note" in product_name.lower():
        replacements = [
            (r'\bAsposeNote\b', 'aspose.note'),
            (r'\baspose_note\b', 'aspose.note'),
            (r'\bfrom onenote import\b', 'from aspose.note import'),
        ]

    if not replacements:
        return content

    lines = content.split('\n')
    in_fence = False
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(line)
            continue

        if in_fence or stripped.startswith(('import ', 'from ', '>>> import', '>>> from')):
            for pattern, replacement in replacements:
                line = re.sub(pattern, replacement, line)

        result.append(line)
    return '\n'.join(result)


# ── Phase 5: Quality Enforcement ──────────────────────────────────────────────

def enforce_quality_floor(
    content: str,
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> str:
    """Enforce minimum content thresholds per section type.

    TC-1733: Pages below the minimum word count get expanded.
    """
    # Import here to avoid circular dependency
    from ..w5_section_writer.worker import (
        _get_display_text,
        _smart_truncate,
        _call_llm_for_content,
        _build_enriched_claim_context,
        _inject_claim_markers_as_comments,
    )

    body = content
    frontmatter = ""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = "---" + parts[1] + "---"
            body = parts[2]

    body_words = len(body.split())
    section = page.get("section", "default")
    min_words = MIN_BODY_WORDS.get(section, MIN_BODY_WORDS["default"])

    if body_words >= min_words:
        return content

    product_name = product_facts.get("product_name", "Product")
    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    all_claims = product_facts.get("claims", [])
    claim_map = {c.get("claim_id"): c for c in all_claims}
    page_claims = [claim_map[cid] for cid in claim_ids if cid in claim_map]

    if not page_claims:
        kf_ids = product_facts.get("claim_groups", {}).get("key_features", [])[:15]
        page_claims = [claim_map[cid] for cid in kf_ids if cid in claim_map]

    if not page_claims:
        logger.warning(f"[Sanitizer QualityFloor] Page {page.get('slug', '?')} has {body_words} words "
                       f"(need {min_words}) but no claims available to expand")
        return content

    if llm_client:
        claim_context = _build_enriched_claim_context(page_claims[:10], product_facts)
        title = page.get("title", page.get("slug", "Page"))
        prompt = (
            f"The following documentation page about {product_name} titled '{title}' "
            f"has insufficient content ({body_words} words, need {min_words}).\n\n"
            f"CURRENT CONTENT:\n{body}\n\n"
            f"FACTS TO USE:\n{claim_context}\n\n"
            f"Expand the existing content to at least {min_words} words. Keep existing "
            f"headings and add substantive information under thin sections. Use specific "
            f"details from the facts. Write in professional English. Do NOT add frontmatter."
        )
        result = _call_llm_for_content(prompt, page_claims, [], llm_client, min_words=min(80, min_words))
        if result["success"]:
            expanded_body = result["content"]
            expanded_body = _inject_claim_markers_as_comments(expanded_body, claim_ids[:5], page_claims)
            return (frontmatter + "\n" + expanded_body).strip() + "\n"

    extra_lines = ["\n## Additional Information\n"]
    for claim in page_claims[:10]:
        text = _get_display_text(claim)
        if text and len(text.split()) >= 5:
            extra_lines.append(f"- {_smart_truncate(text, 250)}")
    for cid in claim_ids[:5]:
        extra_lines.append(f"<!-- claim: {cid} -->")

    body = body.rstrip() + "\n" + "\n".join(extra_lines) + "\n"
    expanded_words = len(body.split())

    if expanded_words < min_words:
        logger.warning(f"[Sanitizer QualityFloor] Page {page.get('slug', '?')} still below minimum "
                       f"({expanded_words}/{min_words} words) after expansion")

    return (frontmatter + "\n" + body).strip() + "\n"


# ── Pipeline Runner ───────────────────────────────────────────────────────────

def run_pipeline(
    content: str,
    ctx: SanitizerContext,
    *,
    include_frontmatter_injection: bool = False,
    frontmatter_injector=None,
) -> str:
    """Run the full sanitizer pipeline in dependency-safe order.

    This replaces the 27-line sequential call chain in execute_section_writer().

    Args:
        content: Raw markdown content to sanitize
        ctx: Sanitizer context with page, product_facts, etc.
        include_frontmatter_injection: If True, calls frontmatter_injector first
        frontmatter_injector: Callable(content) -> content for frontmatter injection

    Returns:
        Sanitized markdown content
    """
    # Phase 1: Early / Structural
    if include_frontmatter_injection and frontmatter_injector:
        content = frontmatter_injector(content)

    content = fix_license_page(content, ctx.page, ctx.product_facts)
    content = strip_source_annotations(content)
    content = strip_orphan_claim_markers(content)
    content = fix_prose_in_code_blocks(content)
    content = fence_bare_commands(content)

    content = ensure_related_links(
        content,
        page_slug=ctx.page_slug,
        repo_url=ctx.repo_url,
        product_name=ctx.product_name,
        family=ctx.family,
        page_url=ctx.page_url,
    )
    content = fix_self_referential_links(content, ctx.page_url)
    content = fix_trailing_whitespace_in_links(content)
    content = ensure_h2_intros(content)
    content = inject_machine_readable(content, ctx.page, ctx.product_facts)

    # Phase 2: Fence Normalization Chain (strict ordering)
    content = fix_collapsed_frontmatter(content)
    content = fix_inline_html_claim_markers(content)
    content = close_unclosed_fences(content)
    content = fix_nested_fences(content)
    content = fix_single_backtick_code_blocks(content)
    content = fix_code_fences(content)
    content = merge_adjacent_code_blocks(content)
    content = fix_unicode_in_code_blocks(content)
    content = validate_code_blocks(content)

    # Phase 3: Content-Level Fixes
    content = strip_product_name_prefix(content, ctx.product_name)
    content = strip_forbidden_topic_headings(content, ctx.page)
    content = remove_empty_sections(content)

    # Phase 4: Strip Unwanted Patterns
    content = strip_boilerplate_sentences(content)
    content = strip_visible_claim_markers(content)
    content = strip_double_periods(content)
    content = strip_emojis(content)
    content = strip_ci_badges(content)
    content = strip_illustrative_comments(content)
    content = fix_truncated_sentences(content)
    content = normalize_module_names(content, ctx.product_facts)

    # Phase 5: Quality Enforcement
    content = enforce_quality_floor(
        content, ctx.page, ctx.product_facts, ctx.snippet_catalog, ctx.llm_client
    )

    return content
