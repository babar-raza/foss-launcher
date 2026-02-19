"""Shared Content Sanitizer: Deterministic post-processing pipeline for markdown content.

Extracted from W5 SectionWriter (worker.py) to enable reuse by W5 AND W7.
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
import threading
from typing import Any, Dict, List, Optional

from ...util.logging import get_logger
from .markdown_zones import apply_to_prose_zones  # TC-2375 (RD-02): zone guard

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
        target_platform: str = "",
    ):
        self.page = page or {}
        self.product_facts = product_facts or {}
        self.snippet_catalog = snippet_catalog or {}
        self.llm_client = llm_client
        self._target_platform = target_platform

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

    @property
    def platform(self) -> str:
        return self._target_platform or self.product_facts.get("target_platform", "")


# ── Sanitizer Metrics (TC-2354) ──────────────────────────────────────────────

class SanitizerMetrics:
    """Thread-safe counters for sanitizer transform usage.

    Tracks how many times each transform actually changed the content (fired)
    vs how many times it was invoked (total calls). Used to identify transforms
    that no longer fire after upstream pipeline improvements.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._fire_counts: Dict[str, int] = {}
        self._call_counts: Dict[str, int] = {}
        self._total_pages: int = 0

    def record(self, name: str, fired: bool) -> None:
        """Record a transform invocation. Increment fire count only if content changed."""
        with self._lock:
            self._call_counts[name] = self._call_counts.get(name, 0) + 1
            if fired:
                self._fire_counts[name] = self._fire_counts.get(name, 0) + 1

    def increment_pages(self) -> None:
        """Increment total pages processed counter."""
        with self._lock:
            self._total_pages += 1

    def to_dict(self) -> Dict[str, Any]:
        """Return metrics as a JSON-serializable dict."""
        with self._lock:
            never_fired = sorted(
                name for name in self._call_counts
                if self._fire_counts.get(name, 0) == 0
            )
            return {
                "transform_fire_counts": dict(sorted(self._fire_counts.items())),
                "transform_call_counts": dict(sorted(self._call_counts.items())),
                "total_pages": self._total_pages,
                "transforms_that_never_fired": never_fired,
            }

    def reset(self) -> None:
        """Clear all counters."""
        with self._lock:
            self._fire_counts.clear()
            self._call_counts.clear()
            self._total_pages = 0


_global_metrics = SanitizerMetrics()


def get_metrics() -> Dict[str, Any]:
    """Return current sanitizer metrics as a dict."""
    return _global_metrics.to_dict()


def reset_metrics() -> None:
    """Clear all sanitizer metrics."""
    _global_metrics.reset()


def _track(name: str, result: str, original: str) -> str:
    """Record whether a transform changed content, return the result."""
    _global_metrics.record(name, result != original)
    return result


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

    For each code block, check if it contains markdown headings (# through ######),
    bold markers (**), or blockquotes (> ). If found, close the fence before
    the heading and re-open after if needed.

    IMPORTANT: When the fence has a known programming language tag where `#` is
    the comment character (python, bash, ruby, etc.), `# text` lines are code
    comments — NOT markdown headings. Skip heading detection for these languages
    to avoid shattering code examples.

    TC-1502: Deterministic post-processing fix (Issue 2).
    """
    # Languages where `#` is a comment character — never treat # lines as headings
    HASH_COMMENT_LANGS = {
        'python', 'py', 'python3', 'bash', 'shell', 'sh', 'zsh', 'fish',
        'ruby', 'rb', 'perl', 'pl', 'yaml', 'yml', 'toml', 'r',
        'julia', 'jl', 'elixir', 'ex', 'coffeescript', 'coffee',
        'make', 'makefile', 'dockerfile', 'docker', 'cmake', 'tcl',
        'powershell', 'ps1', 'pwsh', 'awk', 'sed', 'conf', 'ini',
    }

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
                fence_lang = stripped[3:].strip().lower()
                fence_buffer = [line]
            else:
                fence_buffer.append(line)
                result.extend(fence_buffer)
                in_fence = False
                fence_buffer = []
                fence_lang = ''
            continue

        if in_fence:
            is_heading = bool(re.match(r'^#{1,6}\s', stripped))
            is_blockquote = stripped.startswith('> ')
            has_bold = '**' in stripped and stripped.count('**') >= 2

            # For hash-comment languages (python, bash, ruby, etc.):
            # Single-hash lines (# comment) are code comments — never rescue.
            # Multi-hash headings (## Title) are clearly prose — still rescue.
            # Blockquotes and bold are not valid code — still rescue.
            if fence_lang in HASH_COMMENT_LANGS:
                if is_heading and not re.match(r'^#{2,6}\s', stripped):
                    is_heading = False

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


def fix_bare_language_line(content: str) -> str:
    """Fix bare language name on its own line acting as a broken fence opener.

    TC-2106: LLMs sometimes emit just 'python' (without ```) on a line,
    followed by actual code. This converts such sequences into proper fenced
    code blocks.

    Pattern detected:
        python
        from aspose.threed import Scene
        scene = Scene()

    Becomes:
        ```python
        from aspose.threed import Scene
        scene = Scene()
        ```
    """
    LANG_NAMES = {
        'python', 'bash', 'shell', 'javascript', 'typescript', 'csharp',
        'java', 'go', 'ruby', 'rust', 'cpp', 'json', 'yaml', 'xml',
    }
    # Patterns that indicate the next line is actual code
    CODE_INDICATORS = [
        r'^(from|import)\s+\w+',
        r'^(def|class|async|if|for|while|with|try|return)\s',
        r'^\w+\s*[=(]',
        r'^#\s*(Step|Install|Create|Load|Import|Save)',
    ]

    lines = content.split('\n')
    result: List[str] = []
    in_fence = False
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(lines[i])
            i += 1
            continue

        if in_fence:
            result.append(lines[i])
            i += 1
            continue

        # Check if this line is JUST a language name
        if stripped.lower() in LANG_NAMES and len(stripped) < 20:
            # Look ahead: is the next non-empty line code?
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                next_stripped = lines[j].strip()
                is_code = any(re.match(p, next_stripped) for p in CODE_INDICATORS)
                if is_code:
                    # Convert to proper fence opener and collect code lines
                    lang = stripped.lower()
                    result.append(f'```{lang}')
                    i = j  # skip blank lines between lang and code
                    # Collect code lines until blank line + non-code or heading
                    while i < len(lines):
                        cs = lines[i].strip()
                        if cs.startswith('```'):
                            break
                        if cs.startswith('#') and not cs.startswith('# '):
                            # Markdown heading — stop
                            if re.match(r'^#{1,6}\s', cs):
                                break
                        if not cs:
                            # Blank line — check if next non-empty line is still code-like
                            nxt = ''
                            for ni in range(i + 1, min(i + 3, len(lines))):
                                if lines[ni].strip():
                                    nxt = lines[ni].strip()
                                    break
                            if not nxt or nxt.startswith('```'):
                                break
                            # Stop at multi-hash headings (## or higher), not # comments
                            if re.match(r'^#{2,6}\s', nxt):
                                break
                            nxt_is_code = any(re.match(p, nxt) for p in CODE_INDICATORS)
                            nxt_is_assign = re.match(r'^\w+[\.\[\(]', nxt)
                            nxt_is_comment = nxt.startswith('#') and not re.match(r'^#{2,6}\s', nxt)
                            if not nxt_is_code and not nxt_is_assign and not nxt_is_comment:
                                break
                        result.append(lines[i])
                        i += 1
                    result.append('```')
                    continue

        result.append(lines[i])
        i += 1

    return '\n'.join(result)


def fix_claim_markers_in_urls(content: str) -> str:
    """Strip claim markers that leaked into markdown link URLs.

    TC-2107: Pattern: [text](url/<!-- claim: UUID -->/) → [text](url/)
    """
    # Remove claim markers inside parenthesized URLs
    content = re.sub(
        r'(\([^)]*?)<!--\s*claim:\s*[a-fA-F0-9_\-]+\s*-->([^)]*?\))',
        r'\1\2',
        content,
    )
    # Clean up double slashes that result from removal (but preserve protocol://)
    content = re.sub(r'(?<!:)//+', '/', content)
    return content


def fix_collapsed_markdown_tables(content: str) -> str:
    """Repair markdown tables where multiple rows collapsed onto one line.

    TC-2108: LLM sometimes emits table rows without newlines:
        | A | B | | a1 | b1 | | a2 | b2 |
    Should be:
        | A | B |
        | a1 | b1 |
        | a2 | b2 |
    """
    lines = content.split('\n')
    result: List[str] = []
    in_fence = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(line)
            continue

        if in_fence:
            result.append(line)
            continue

        # Detect collapsed table rows: line has multiple | ... | patterns
        # A properly formatted table row ends with | and starts with |
        if stripped.startswith('|') and stripped.count('|') > 6:
            # Try to split: find pattern | text | | text | (double pipe = row boundary)
            # But the actual pattern is | col1 | col2 | | col1 | col2 |
            # where "| |" marks a row boundary (end of one row, start of next)
            #
            # Strategy: split on "| |" pattern that indicates row boundaries
            # A row boundary is where one row's trailing | meets another row's leading |
            parts = re.split(r'\|\s*\|', stripped)
            if len(parts) > 2:
                # Reconstruct rows
                rows = []
                for idx, part in enumerate(parts):
                    p = part.strip()
                    if not p:
                        continue
                    # Add back the pipes
                    if not p.startswith('|'):
                        p = '| ' + p
                    if not p.endswith('|'):
                        p = p + ' |'
                    rows.append(p)

                if len(rows) >= 2:
                    # Check if we need to insert a separator row
                    # (header | sep | data pattern)
                    has_sep = any(re.match(r'^\|[\s\-:|]+\|$', r) for r in rows)
                    for row in rows:
                        result.append(row)
                    if not has_sep and len(rows) >= 2:
                        # Insert separator after first row
                        cols = rows[0].count('|') - 1
                        sep = '|' + '|'.join(['-------'] * max(cols, 1)) + '|'
                        result.insert(len(result) - len(rows) + 1, sep)
                    continue

        result.append(line)

    return '\n'.join(result)


def strip_inline_seo_keywords(content: str) -> str:
    """Strip SEO keyword lines that leaked into visible body text.

    TC-2109: Pattern: **SEO keywords:** word1, word2, word3
    Or: SEO keywords: ...
    """
    lines = content.split('\n')
    result: List[str] = []
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(line)
            continue
        if in_fence:
            result.append(line)
            continue
        # Match **SEO keywords:** or *SEO keywords:* or plain SEO keywords:
        if re.match(r'^(\*{1,2})?SEO\s+keywords?:?\*{0,2}\s*', stripped, re.IGNORECASE):
            continue
        # Match *Page focus (SEO keywords)*: ... (LLM prompt artifact)
        if re.search(r'\*?Page\s+focus\s*\(SEO\s+keywords?\)\*?\s*:', stripped, re.IGNORECASE):
            # Strip just the SEO portion from the line
            cleaned = re.sub(
                r'\*?Page\s+focus\s*\(SEO\s+keywords?\)\*?\s*:.*$',
                '', stripped, flags=re.IGNORECASE
            ).rstrip()
            if cleaned:
                result.append(cleaned)
            continue
        result.append(line)

    return '\n'.join(result)


def fence_bare_code_lines(content: str) -> str:
    """Wrap sequences of bare Python code outside fences into proper code blocks.

    TC-2110: Detects import statements, assignments, and common code patterns
    that appear outside code fences and wraps them.
    """
    CODE_PATTERNS = [
        r'^from\s+\w[\w.]*\s+import\s+',
        r'^import\s+\w[\w.]*',
        r'^(assert|raise)\s+\w',
        r'^(if|for|while|with|try)\s+.*:\s*$',
        r'^(elif|else|except|finally)\s*.*:\s*$',
        r'^[\w][\w.]*\s*=\s*\w',        # assignment: x = Foo(), foo.bar = value
        r'^[\w][\w.]*\s*=\s*["\'\[\({]',  # assignment to literal: x = "...", x = [...
        r'^[\w][\w.]*\.\w+\(',            # method call: obj.method(...)
        r'^print\s*\(',                    # print(...)
        r'^return\s+',                     # return ...
    ]

    lines = content.split('\n')
    result: List[str] = []
    in_fence = False
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(lines[i])
            i += 1
            continue

        if in_fence:
            result.append(lines[i])
            i += 1
            continue

        # Skip frontmatter, multi-hash headings, list items, links, HTML comments, table rows
        if (
            re.match(r'^#{2,6}\s', stripped)
            or stripped.startswith('-')
            or stripped.startswith('*')
            or stripped.startswith('[')
            or stripped.startswith('<!--')
            or stripped.startswith('|')
            or stripped.startswith('>')
            or stripped == '---'
        ):
            result.append(lines[i])
            i += 1
            continue

        # Single-hash lines (# comment): check if followed by code — if so, treat as
        # Python comment and collect together. If not, skip as markdown heading.
        if stripped.startswith('#') and not re.match(r'^#{2,6}\s', stripped):
            # Look ahead up to 2 lines for code patterns
            is_code_comment = False
            for look in range(1, 3):
                if i + look < len(lines):
                    nxt_s = lines[i + look].strip()
                    if nxt_s and not nxt_s.startswith('#') and not nxt_s.startswith('<!--'):
                        if any(re.match(p, nxt_s) for p in CODE_PATTERNS):
                            is_code_comment = True
                        break
            if not is_code_comment:
                result.append(lines[i])
                i += 1
                continue
            # Fall through to code collection below

        is_code = stripped.startswith('#') or any(re.match(p, stripped) for p in CODE_PATTERNS)
        if is_code:
            # Collect consecutive code-like lines (including # comments as code)
            code_block = []
            while i < len(lines):
                cs = lines[i].strip()
                if cs.startswith('```'):
                    break
                # Only break at ## or higher headings (2+ hashes) — not # comments.
                # Single-hash lines inside a code sequence are Python comments.
                if re.match(r'^#{2,6}\s', cs):
                    break
                if not cs:
                    # Blank line — check next
                    if i + 1 < len(lines):
                        nxt = lines[i + 1].strip()
                        # If next is prose (not code-like), stop
                        nxt_is_code = any(re.match(p, nxt) for p in CODE_PATTERNS)
                        nxt_is_indent = nxt.startswith('    ') or nxt.startswith('\t')
                        nxt_is_comment = nxt.startswith('#') and not re.match(r'^#{2,6}\s', nxt)
                        if not nxt_is_code and not nxt_is_indent and not nxt_is_comment and nxt:
                            break
                    else:
                        break
                code_block.append(lines[i])
                i += 1

            if code_block:
                result.append('```python')
                result.extend(code_block)
                result.append('```')
            continue

        result.append(lines[i])
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

    W7 ContentReviewer flags pages with <2 links as WARN.
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
    html_marker_re = re.compile(r'\s*<!--\s*claim_id:\s*[a-fA-F0-9_\-]+\s*-->\s*')
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
    """Fix content where most of the body is trapped inside code fences.

    TC-1810: When token values contain ``` markers, the template-rendered
    content can have nested/unclosed fences.

    Only triggers when BOTH conditions are met:
    1. >70% of body lines are inside fences
    2. >40% of fenced content looks like prose (not code)

    Code-heavy documentation (tutorials, API refs) legitimately has
    high fence ratios — this must NOT destroy valid code blocks.
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
    code_like_in_fence = 0
    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence and stripped:
            fenced_lines += 1
            # Check if this line looks like actual code
            is_code = (
                stripped.startswith(('import ', 'from ', 'def ', 'class ', 'pip ', 'python '))
                or stripped.startswith(('>>> ', '... ', '$ ', '#'))
                or (stripped.startswith('#') and not stripped.startswith('## '))
                or re.match(r'^[\w.]+\s*[=(]', stripped)
                or '=' in stripped
                or stripped.endswith((':', ')', ';', ','))
                or stripped.startswith(('return ', 'if ', 'for ', 'while ', 'try:', 'except'))
            )
            if is_code:
                code_like_in_fence += 1

    ratio = fenced_lines / total_lines if total_lines > 0 else 0
    if ratio <= 0.70:
        return content

    # If most fenced content is actual code, it's legitimate — don't destroy it
    code_ratio = code_like_in_fence / fenced_lines if fenced_lines > 0 else 0
    if code_ratio > 0.60:
        return content

    logger.warning(f"[Sanitizer TC-1810] {ratio:.0%} of body lines inside fences (code ratio {code_ratio:.0%}) — stripping spurious fences")

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


def fix_excess_backtick_fences(content: str) -> str:
    """Normalize 4+ backtick fences to standard 3-backtick fences.

    TC-1903: LLMs sometimes output 5+ backtick fences. These are valid
    markdown but non-standard. Normalize to 3 backticks.
    """
    return re.sub(r'^`{4,}', '```', content, flags=re.MULTILINE)


def fix_single_backtick_code_blocks(content: str) -> str:
    """Convert single-backtick code blocks to triple-backtick fenced code blocks.

    Uses a line-based state machine (TC-2104) instead of regex.
    The previous regex `[^`]{20,}` could not cross inline backtick spans.

    Pass 1: Line-based state machine
    - Tracks existing triple-backtick fences (skips their content)
    - Detects opener: stripped line is lone ` or `<known_lang>
    - Scans forward for closer: stripped line is ` or `.
    - Converts matched pairs to triple-backtick fences

    Pass 2: Legacy regex fallback for inline multi-line backtick spans.
    """
    _known_langs = {
        'python', 'javascript', 'bash', 'csharp', 'java', 'json',
        'yaml', 'xml', 'html', 'css', 'typescript', 'go', 'ruby',
        'php', 'cpp', 'c', 'rust', 'sql', 'shell', 'sh', 'py',
        'js', 'ts', 'yml', 'plaintext', 'text', 'powershell',
    }

    lines = content.split('\n')
    result: List[str] = []
    i = 0
    in_triple_fence = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Track existing triple-backtick fences — skip their content
        if stripped.startswith('```'):
            in_triple_fence = not in_triple_fence
            result.append(line)
            i += 1
            continue

        if in_triple_fence:
            result.append(line)
            i += 1
            continue

        # Detect single-backtick opener: line is just ` or `<lang>
        # Must NOT be `` or ``` (those are other syntax)
        if stripped.startswith('`') and not stripped.startswith('``'):
            after_backtick = stripped[1:].strip()
            # Check if it's a lone backtick or backtick+language
            is_lone_backtick = (after_backtick == '')
            is_backtick_lang = (after_backtick.lower() in _known_langs)

            if is_lone_backtick or is_backtick_lang:
                lang = after_backtick.lower() if is_backtick_lang else ''

                # Scan forward for closer
                j = i + 1
                found_closer = False
                while j < len(lines):
                    cstripped = lines[j].strip()
                    # Closer: lone ` or `.
                    if cstripped in ('`', '`.'):
                        found_closer = True
                        break
                    # If we hit a triple fence, stop scanning
                    if cstripped.startswith('```'):
                        break
                    j += 1

                if found_closer and j > i + 1:
                    # Extract content between opener and closer
                    content_lines = lines[i + 1:j]

                    # If no lang from opener, try first non-empty content line
                    if not lang:
                        for cl in content_lines:
                            cs = cl.strip().lower()
                            if cs and cs in _known_langs:
                                lang = cs
                                content_lines = [
                                    l for idx, l in enumerate(content_lines)
                                    if not (l.strip().lower() == lang and idx == content_lines.index(cl))
                                ]
                                # Remove just the first matching line
                                break

                    # Emit triple-backtick fence
                    result.append(f'```{lang}')
                    result.extend(content_lines)
                    result.append('```')
                    i = j + 1
                    continue

        # Default: emit line as-is
        result.append(line)
        i += 1

    return '\n'.join(result)


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
            # TC-RCA: Close fence if a markdown heading (any level) appears inside
            if re.match(r'^#{1,6}\s', stripped):
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


def collapse_duplicate_fence_openings(content: str) -> str:
    """Collapse consecutive duplicate fence openings (```python\\n```python → ```python).

    TC-RCA: LLMs sometimes emit multiple consecutive fence openings without
    closing the first. Also removes code fences that contain only a heading
    or comment-only placeholder (no actual code).
    """
    lines = content.split('\n')
    result: List[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.startswith('```'):
            is_bare_fence = (stripped == '```')
            # Check if next non-empty line is also a fence opener
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if not is_bare_fence:
                # Language-tagged fence opener
                if j < len(lines) and lines[j].strip().startswith('```') and lines[j].strip() != '```':
                    # Consecutive fence openers — skip duplicate, keep the first
                    result.append(lines[i])
                    i = j + 1  # Skip the duplicate opener
                    continue

            # Check for fences that wrap headings/prose instead of code
            if j < len(lines):
                next_stripped = lines[j].strip()
                # Scan to find the closing fence
                k = j + 1
                while k < len(lines) and not lines[k].strip():
                    k += 1

                # Single-line content in fence
                if k < len(lines) and lines[k].strip() == '```':
                    if re.match(r'^#{1,6}\s', next_stripped):
                        # Heading trapped in fence — emit heading, skip fences
                        result.append(lines[j])
                        i = k + 1
                        continue
                    if not is_bare_fence and next_stripped.startswith('#') and not next_stripped.startswith('#!'):
                        # Comment-only code fence — emit as regular text
                        result.append(next_stripped.lstrip('# ').strip())
                        i = k + 1
                        continue

                # Bare fence wrapping headings + non-code content (e.g., ```\n### Related Links\n...\n```)
                if is_bare_fence and re.match(r'^#{1,6}\s', next_stripped):
                    # Find the closing ``` and emit all content between as regular text
                    end_k = j
                    while end_k < len(lines):
                        if lines[end_k].strip() == '```':
                            break
                        end_k += 1
                    # Emit all lines between the fences as regular prose
                    for m in range(j, end_k):
                        result.append(lines[m])
                    i = end_k + 1 if end_k < len(lines) else end_k
                    continue

        result.append(lines[i])
        i += 1

    return '\n'.join(result)


def fix_trailing_periods_in_code(content: str) -> str:
    """Strip LLM-generated trailing periods from code lines inside code fences.

    TC-2105: LLMs sometimes treat code as prose, appending periods like
    `import Scene.`, `render(opts) #.`.

    Rules:
    1. `#.` at end of line → strip the `#.` suffix
    2. Comment lines (`# Comment.`) → preserve (prose in comments is OK)
    3. Strip trailing `.` from code, EXCEPT:
       - `pip install -e .` or similar (`.` is a path argument)
       - `...` (ellipsis)
       - Periods inside or adjacent to string literals
    """
    lines = content.split('\n')
    result: List[str] = []
    in_fence = False

    for line in lines:
        stripped = line.strip()

        # Track fence state
        if stripped.startswith('```'):
            in_fence = not in_fence
            result.append(line)
            continue

        if not in_fence:
            result.append(line)
            continue

        # Inside a code fence — apply trailing period rules
        rstripped = line.rstrip()

        # Rule 1: Strip `#.` suffix (LLM appends comment-period)
        if rstripped.endswith('#.'):
            line = rstripped[:-2].rstrip()
            result.append(line)
            continue

        # Skip empty lines
        if not stripped:
            result.append(line)
            continue

        # Rule 2: Comment lines — preserve (prose in comments is acceptable)
        # Detect lines that are primarily comments (start with #)
        code_part = stripped
        if code_part.startswith('#'):
            result.append(line)
            continue

        # Only process lines ending with a period
        if not rstripped.endswith('.'):
            result.append(line)
            continue

        # Rule 3 exceptions: preserve period in these cases
        # Exception: ellipsis (...)
        if rstripped.endswith('...'):
            result.append(line)
            continue

        # Exception: period is inside/adjacent to a string literal
        # Simple heuristic: if line ends with ." or .' or .`) with quote nearby
        if rstripped.endswith('."') or rstripped.endswith(".'") or rstripped.endswith(".')"):
            result.append(line)
            continue

        # Exception: pip/python commands where . is a path argument
        # e.g., `pip install .`, `pip install -e .`, `python .`
        if re.search(r'\b(pip|python|python3)\b.*\s\.$', rstripped):
            result.append(line)
            continue

        # Exception: line contains inline comment — period might be in comment text
        # Find # outside of strings
        in_str = None
        has_inline_comment = False
        for ci, ch in enumerate(stripped):
            if ch in ('"', "'") and (ci == 0 or stripped[ci - 1] != '\\'):
                if in_str == ch:
                    in_str = None
                elif in_str is None:
                    in_str = ch
            elif ch == '#' and in_str is None:
                has_inline_comment = True
                break

        if has_inline_comment:
            result.append(line)
            continue

        # Strip the trailing period
        result.append(rstripped[:-1])

    return '\n'.join(result)


def tokenize_zones(content: str) -> list:
    """Classify content lines into semantic zones.

    Returns list of (zone_type, start_line, end_line) tuples.
    Zone types: FRONTMATTER, PROSE, CODE_FENCE, HTML_COMMENT, BLANK

    This is a foundation for replacing fragile regex patterns with
    zone-aware processing. See RCA plan Phase 1.
    """
    lines = content.split('\n')
    zones = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Frontmatter detection (--- at start of file)
        if i == 0 and stripped == '---':
            start = i
            i += 1
            while i < len(lines) and lines[i].strip() != '---':
                i += 1
            zones.append(("FRONTMATTER", start, i))
            i += 1
            continue

        # Code fence
        if stripped.startswith('```'):
            start = i
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                i += 1
            zones.append(("CODE_FENCE", start, i))
            i += 1
            continue

        # HTML comment
        if stripped.startswith('<!--'):
            start = i
            if '-->' in stripped:
                zones.append(("HTML_COMMENT", start, i))
            else:
                while i < len(lines) and '-->' not in lines[i]:
                    i += 1
                zones.append(("HTML_COMMENT", start, i))
            i += 1
            continue

        # Blank line
        if not stripped:
            zones.append(("BLANK", i, i))
            i += 1
            continue

        # Prose (default)
        zones.append(("PROSE", i, i))
        i += 1

    return zones


def merge_adjacent_code_blocks(content: str) -> str:
    """Merge adjacent code blocks of the same language.

    Handles blocks separated by:
    - Blank lines only -> merge unconditionally
    - Comment-style text (# Step N:, # description) -> convert to code comment, merge
    - HTML claim markers (<!-- claim: ... -->) -> preserve markers after merged block

    Does NOT merge across:
    - Headings (##, ###)
    - Prose paragraphs (>10 words of non-comment text)
    - Different languages

    Safety limit: max 20 merges per invocation.
    """
    lines = content.split('\n')

    # Parse into blocks: each is either a code fence block or a text block
    blocks = []  # list of (type, lang, content_lines)
    # type = "code" | "text"

    i = 0
    while i < len(lines):
        line = lines[i]
        # Check for fence opening
        stripped = line.strip()
        if stripped.startswith('```'):
            lang = stripped[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines):
                if lines[i].strip() == '```':
                    break
                code_lines.append(lines[i])
                i += 1
            blocks.append(("code", lang, code_lines))
            i += 1  # skip closing ```
        else:
            # Text line
            if blocks and blocks[-1][0] == "text":
                blocks[-1][2].append(line)
            else:
                blocks.append(("text", "", [line]))
            i += 1

    # Now merge consecutive same-language code blocks
    merged_blocks = []
    merge_count = 0
    MAX_MERGES = 20

    j = 0
    while j < len(blocks):
        block = blocks[j]
        if block[0] != "code" or merge_count >= MAX_MERGES:
            merged_blocks.append(block)
            j += 1
            continue

        # Try to merge with next code blocks
        current_lang = block[1]
        current_code = list(block[2])
        collected_markers = []

        k = j + 1
        while k < len(blocks) and merge_count < MAX_MERGES:
            # Check if next block is a text separator
            if blocks[k][0] == "text":
                separator_lines = blocks[k][2]
                # Check what the separator contains
                non_empty = [l for l in separator_lines if l.strip()]

                if not non_empty:
                    # Only blank lines -- check if there's a code block after
                    if k + 1 < len(blocks) and blocks[k + 1][0] == "code":
                        next_code = blocks[k + 1]
                        # Only merge same language (or empty lang)
                        if next_code[1] == current_lang or not next_code[1] or not current_lang:
                            current_code.append("")  # blank separator
                            current_code.extend(next_code[2])
                            merge_count += 1
                            k += 2
                            continue
                    break

                # Check if ALL non-empty lines are mergeable (comments or claim markers)
                all_mergeable = True
                has_prose = False
                separator_comments = []
                separator_markers = []

                for sl in non_empty:
                    sl_stripped = sl.strip()
                    if sl_stripped.startswith('<!--') and 'claim:' in sl_stripped:
                        separator_markers.append(sl)
                    elif sl_stripped.startswith('#') and not sl_stripped.startswith('##'):
                        # Python-style comment (but NOT markdown heading)
                        separator_comments.append(sl_stripped)
                    elif len(sl_stripped.split()) > 10:
                        # Prose paragraph
                        has_prose = True
                        all_mergeable = False
                        break
                    elif sl_stripped.startswith('##') or sl_stripped.startswith('###'):
                        # Markdown heading -- never merge across
                        all_mergeable = False
                        break
                    else:
                        # Short text -- could be a comment-like description
                        # Allow step labels and known boilerplate filler phrases
                        if re.match(
                            r'^#?\s*(?:Step\s+\d|Then|Next|Now|First|Finally|Also)\b',
                            sl_stripped,
                            re.IGNORECASE,
                        ):
                            separator_comments.append(f"# {sl_stripped}")
                        elif re.match(
                            r'^The (code above|following example|snippet|example)',
                            sl_stripped,
                            re.IGNORECASE,
                        ):
                            # Known boilerplate between code blocks — skip it, allow merge
                            pass
                        else:
                            all_mergeable = False
                            break

                if all_mergeable and not has_prose:
                    # Check if there's a code block after
                    if k + 1 < len(blocks) and blocks[k + 1][0] == "code":
                        next_code = blocks[k + 1]
                        if next_code[1] == current_lang or not next_code[1] or not current_lang:
                            # Add comment lines as code comments
                            for sc in separator_comments:
                                current_code.append(sc if sc.startswith('#') else f"# {sc}")
                            current_code.append("")
                            current_code.extend(next_code[2])
                            collected_markers.extend(separator_markers)
                            merge_count += 1
                            k += 2
                            continue
                break  # Can't merge further
            elif blocks[k][0] == "code":
                # Directly adjacent code blocks (no separator)
                if blocks[k][1] == current_lang or not blocks[k][1] or not current_lang:
                    current_code.append("")
                    current_code.extend(blocks[k][2])
                    merge_count += 1
                    k += 1
                    continue
                break
            else:
                break

        # Emit the merged code block
        effective_lang = current_lang or block[1]
        merged_blocks.append(("code", effective_lang, current_code))
        # Emit any collected claim markers as text
        if collected_markers:
            merged_blocks.append(("text", "", collected_markers))
        j = k

    # Reconstruct content
    output_lines = []
    for block_type, lang, block_lines in merged_blocks:
        if block_type == "code":
            output_lines.append(f"```{lang}")
            output_lines.extend(block_lines)
            output_lines.append("```")
        else:
            output_lines.extend(block_lines)

    return '\n'.join(output_lines)


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

def fix_faq_doubled_prefix(content: str) -> str:
    """Fix doubled Q: prefix in FAQ headings (### Q: Q: -> ### Q:).

    TC-1902: When W2 claims already contain 'Q:' prefix and the FAQ
    generator adds another '### Q:', the result is '### Q: Q:'.
    """
    return re.sub(r'(###\s+)Q:\s*Q:', r'\1Q:', content)


def fix_faq_doubled_answer_prefix(content: str) -> str:
    """Fix doubled A: prefix in FAQ answers (**A:** A: -> **A:**).

    TC-2004.
    """
    return re.sub(r'(\*\*A:\*\*)\s*A:', r'\1', content)


def strip_llm_scaffolding(content: str) -> str:
    """Strip LLM prompt scaffolding sections leaked into generated content.

    When the LLM echoes back its prompt context, output can contain:
    - ``## Product Context`` with raw JSON (product_name, api_surface, etc.)
    - ``## Instructions`` with numbered pipeline directives
    These are internal scaffolding, never intended for publication.

    Removes the heading and all lines until the next ``##`` heading or EOF.
    Operates outside code fences only.
    """
    lines = content.split('\n')
    result: list[str] = []
    in_fence = False
    skip_until_heading = False

    for line in lines:
        stripped = line.strip()

        # Track code fences — never strip inside fences
        if stripped.startswith('```'):
            in_fence = not in_fence
            if not skip_until_heading:
                result.append(line)
            continue

        if in_fence:
            if not skip_until_heading:
                result.append(line)
            continue

        # Detect scaffolding headings (## Product Context, ## Instructions, etc.)
        # Catches exact and variant forms: "## Product Context", "## Aspose.3D ... Product Context"
        if re.match(r'^##\s+.*Product\s+Context\s*$', stripped):
            skip_until_heading = True
            continue
        if re.match(r'^##\s+Instructions\s*$', stripped):
            skip_until_heading = True
            continue
        if re.match(r'^##\s+Output\s+Rules\s*$', stripped):
            skip_until_heading = True
            continue
        if re.match(r'^##\s+.*SEO\s+Keywords?\s*$', stripped):
            skip_until_heading = True
            continue
        if re.match(r'^##\s+Audience\s*$', stripped):
            skip_until_heading = True
            continue
        # Italic/bold variant: *Product Context* or **Product Context**
        if re.match(r'^\*{1,2}Product\s+Context\*{1,2}\s*$', stripped):
            skip_until_heading = True
            continue

        # Stop skipping at the next heading
        if skip_until_heading:
            if re.match(r'^#{1,6}\s', stripped):
                skip_until_heading = False
                result.append(line)
            # else: skip this line (part of scaffolding section)
            continue

        result.append(line)

    return '\n'.join(result)


def strip_boilerplate_sentences(content: str) -> str:
    """Remove known filler sentences that add no value.

    TC-1502: Deterministic post-processing fix (Issue 9).
    """
    BOILERPLATE = [
        r'^The code above performs the described operation\.?\s*$',
        r'^The following example demonstrates this operation[.:]\s*$',
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
    """Strip ALL claim markers from body text (visible and HTML comment).

    Frontmatter already contains claim_ids for validation. Gate 14 uses
    required_claim_ids from page_plan.json, not HTML comments in content.
    Gate 2 validates marker→claim_id references; with markers stripped, it
    simply passes (no markers = no invalid references).

    Round 11.5 + Round 13 TC-1800/1801/1802 + Phase 5 TC-2354 fix.
    """
    # Fullwidth bracket markers: 【hex】, 【claim: hex】, truncated 【hex at EOL
    content = re.sub(r'\s*【[a-fA-F0-9_\-]{6,}】', '', content)
    content = re.sub(r'\s*【claim:?\s*[a-fA-F0-9_\-]*】?', '', content)
    content = re.sub(r'\s*【[a-fA-F0-9_\-]+[^】]*$', '', content, flags=re.MULTILINE)
    # Square bracket markers: [claim: hex]
    content = re.sub(r'\s*\[claim:\s*[a-fA-F0-9_\-]+\]', '', content)
    # HTML comment claim markers (valid format): <!-- claim: hex -->
    content = re.sub(r'\s*<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->\s*\n?', '', content)
    # Broken/incomplete HTML claim markers (missing closing -->)
    content = re.sub(r'<!--\s*claim:[^>]*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'<!--\s*claim:\s*-->', '', content)
    # Parenthesized and bare hex IDs (6+ chars — covers short 7-char, 12-char, and full 64-char SHA256)
    content = re.sub(r'\(\[?[a-fA-F0-9_\-]{6,}\]?\)', '', content)
    content = re.sub(r'\[[a-fA-F0-9_\-]{6,}\]', '', content)
    content = re.sub(r'<!--\s*claim_id:\s*[a-fA-F0-9_\-]+\s*-->\n?', '', content)
    content = re.sub(r'(?<!`)``(?!`)', '', content)
    content = re.sub(r'`\[claim:\s*[a-fA-F0-9_\-]+\]`', '', content)
    content = re.sub(r'`<!--\s*claim:?\s*[a-fA-F0-9_\-]*\s*-->`', '', content)
    content = re.sub(r'\([a-fA-F0-9_\-]{6,}[…\.]*\)', '', content)
    # Collapse double spaces within text (NOT at line starts — preserves YAML/code indentation)
    content = re.sub(r'(?<=\S)  +', ' ', content)
    content = re.sub(r' +\n', '\n', content)
    return content


def strip_pipeline_comments(content: str) -> str:
    """Strip pipeline-internal HTML comments from final output.

    Removes W7 review diagnostic comments (<!-- W7_REVIEW: ... -->)
    and any other pipeline-internal annotations that should not appear
    in published content.
    """
    # W7 review comments
    content = re.sub(r'\s*<!--\s*W7_REVIEW:.*?-->\s*\n?', '', content, flags=re.DOTALL)
    # Any other pipeline-internal comments (W5, W6, W7 prefixed)
    content = re.sub(r'\s*<!--\s*W[0-9]+(?:\.[0-9]+)?_[A-Z]+:.*?-->\s*\n?', '', content, flags=re.DOTALL)
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


# Subdomain mapping for all sections (TC-2103)
_SECTION_SUBDOMAINS = {
    "docs": "docs.aspose.org",
    "reference": "reference.aspose.org",
    "kb": "kb.aspose.org",
    "blog": "blog.aspose.org",
    "products": "products.aspose.org",
}


def absolutize_links(content: str, section: str, family: str, platform: str = "") -> str:
    """Convert relative markdown links to absolute URLs with correct subdomain.

    TC-2103: All injected links must be absolute. Handles all 5 subdomains:
    docs, reference, kb, blog, products.

    Rules:
    - Already-absolute URLs (http://, https://) → unchanged
    - Anchor links (#heading) → unchanged
    - Section-prefixed links (/docs/slug/) → https://docs.aspose.org/{family}/{platform}/slug/
    - Family-prefixed links (/{family}/slug/) → https://{section}.aspose.org/{family}/{platform}/slug/
    - Other relative links → https://{section}.aspose.org/{family}/{platform}/path/
    """
    current_subdomain = _SECTION_SUBDOMAINS.get(section, f"docs.aspose.org")

    def _build_absolute(subdomain: str, path_suffix: str) -> str:
        """Build absolute URL with family and platform segments."""
        # Clean up path suffix
        path_suffix = path_suffix.strip('/')
        if path_suffix:
            path_suffix = f"/{path_suffix}/"
        else:
            path_suffix = "/"
        return f"https://{subdomain}/{family}/{platform}/{path_suffix}".replace("///", "/").replace("/./", "/").replace("//", "/").replace(":/", "://")

    def _replace_link(match: re.Match) -> str:
        text = match.group(1)
        url = match.group(2)

        # Clean up already-absolute URLs (fix /./  and section-in-path issues)
        if url.startswith(('http://', 'https://')):
            cleaned = url.replace("/./", "/")
            # Strip section prefix from absolute URLs where subdomain already encodes it
            # e.g., https://docs.aspose.org/3d/python/docs/getting-started/ → strip inner /docs/
            for sec_name, sec_subdomain in _SECTION_SUBDOMAINS.items():
                prefix_in_path = f"https://{sec_subdomain}/{family}/{platform}/{sec_name}/" if platform else f"https://{sec_subdomain}/{family}/{sec_name}/"
                correct_base = f"https://{sec_subdomain}/{family}/{platform}/" if platform else f"https://{sec_subdomain}/{family}/"
                if cleaned.startswith(prefix_in_path):
                    cleaned = correct_base + cleaned[len(prefix_in_path):]
                    break
            if cleaned != url:
                return f"[{text}]({cleaned})"
            return match.group(0)

        # Skip anchors
        if url.startswith('#'):
            return match.group(0)

        # Skip empty URLs
        if not url.strip():
            return match.group(0)

        # Normalize leading ./ in relative paths
        while url.startswith('./'):
            url = url[2:]
        # If that left us with a bare path, ensure it starts with /
        if url and not url.startswith('/') and not url.startswith(('http://', 'https://')):
            url = '/' + url

        # Check if URL starts with a known section prefix
        for sec_name, sec_subdomain in _SECTION_SUBDOMAINS.items():
            prefix = f"/{sec_name}/"
            if url.startswith(prefix):
                remainder = url[len(prefix):]
                abs_url = _build_absolute(sec_subdomain, remainder)
                return f"[{text}]({abs_url})"
            # Also handle bare section (e.g., /docs/ or /reference/)
            if url.rstrip('/') == f"/{sec_name}":
                abs_url = _build_absolute(sec_subdomain, "")
                return f"[{text}]({abs_url})"

        # Check if URL starts with family (intra-section link)
        if family and url.startswith(f"/{family}/"):
            remainder = url[len(f"/{family}/"):]
            # Already has family, just needs subdomain
            suffix = remainder.strip('/')
            if platform and suffix.startswith(f"{platform}/"):
                # Already has platform too, just add subdomain
                return f"[{text}](https://{current_subdomain}/{family}/{suffix})"
            elif platform:
                return f"[{text}](https://{current_subdomain}/{family}/{platform}/{suffix}/)" if suffix else f"[{text}](https://{current_subdomain}/{family}/{platform}/)"
            else:
                return f"[{text}](https://{current_subdomain}/{family}/{suffix}/)" if suffix else f"[{text}](https://{current_subdomain}/{family}/)"

        # General relative link — use current section's subdomain
        path = url.strip('/')
        if path:
            abs_url = _build_absolute(current_subdomain, path)
            return f"[{text}]({abs_url})"

        return match.group(0)

    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _replace_link, content)
    # Clean /./ from URLs — path normalization
    content = content.replace("/./", "/")
    # Clean /index/ from URLs — Hugo serves _index.md at directory root
    content = re.sub(r'(https://[^)]+)/index/(\))', r'\1/\2', content)
    content = re.sub(r'(https://[^)]+)/index(\))', r'\1/\2', content)
    return content


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

    TC-1831 + TC-2111: Also handles truncated bullet points.
    Detects lines ending with dangling prepositions/conjunctions and
    trims the incomplete fragment, adding proper punctuation.
    """
    # Words that signal clear truncation when at end of line
    DANGLING_WORDS = {
        'and', 'or', 'the', 'a', 'an', 'for', 'with', 'to', 'in', 'of',
        'that', 'this', 'which', 'from', 'by', 'as', 'on', 'at', 'into',
        'via', 'using', 'through', 'during', 'after', 'before', 'between',
        'within', 'without', 'such', 'including', 'like', 'than',
        'streamlining', 'facilitating', 'enabling', 'providing',
    }

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

        # Skip lines we shouldn't touch
        if (
            not stripped
            or stripped.startswith('#')
            or stripped.startswith('[')
            or stripped.startswith('<!--')
            or stripped.startswith('|')
            or stripped.endswith('-->')
        ):
            result.append(line)
            continue

        # Extract the text portion (handle bullet prefixes)
        is_bullet = False
        text = stripped
        prefix = ''
        bullet_match = re.match(r'^(-|\*|\d+\.)\s+', stripped)
        if bullet_match:
            is_bullet = True
            prefix = stripped[:bullet_match.end()]
            text = stripped[bullet_match.end():]

        # Check for dangling word truncation (bullet or prose)
        if text and len(text) > 20:
            last_word = text.rstrip().split()[-1].lower().rstrip(',')
            if last_word in DANGLING_WORDS:
                # Trim the dangling word and add period
                trimmed = text.rstrip()
                # Remove the last word
                words = trimmed.rsplit(None, 1)
                if len(words) > 1:
                    trimmed = words[0].rstrip(',')
                    if not trimmed[-1] in '.!?:;)"\'>':
                        trimmed += '.'
                    if is_bullet:
                        line = line[:len(line) - len(line.lstrip())] + prefix + trimmed
                    else:
                        line = line[:len(line) - len(line.lstrip())] + trimmed
                result.append(line)
                continue

        # For non-bullet prose, add period if missing
        if not is_bullet:
            if text and len(text) > 20 and not text[-1] in '.!?:;)"\'>':
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
    _global_metrics.increment_pages()

    # Phase 1: Early / Structural
    if include_frontmatter_injection and frontmatter_injector:
        content = _track("frontmatter_injection", frontmatter_injector(content), content)

    content = _track("fix_license_page", fix_license_page(content, ctx.page, ctx.product_facts), content)
    content = _track("strip_source_annotations", strip_source_annotations(content), content)
    content = _track("strip_orphan_claim_markers", strip_orphan_claim_markers(content), content)
    content = _track("fix_prose_in_code_blocks", fix_prose_in_code_blocks(content), content)
    content = _track("fence_bare_commands", fence_bare_commands(content), content)
    content = _track("fix_bare_language_line", fix_bare_language_line(content), content)
    content = _track("fence_bare_code_lines", fence_bare_code_lines(content), content)

    content = _track("ensure_related_links", ensure_related_links(
        content,
        page_slug=ctx.page_slug,
        repo_url=ctx.repo_url,
        product_name=ctx.product_name,
        family=ctx.family,
        page_url=ctx.page_url,
    ), content)
    content = _track("fix_self_referential_links", fix_self_referential_links(content, ctx.page_url), content)
    content = _track("fix_trailing_whitespace_in_links", fix_trailing_whitespace_in_links(content), content)
    content = _track("ensure_h2_intros", ensure_h2_intros(content), content)
    content = _track("inject_machine_readable", inject_machine_readable(content, ctx.page, ctx.product_facts), content)

    # Phase 2: Fence Normalization Chain (strict ordering)
    content = _track("fix_collapsed_frontmatter", fix_collapsed_frontmatter(content), content)
    content = _track("fix_inline_html_claim_markers", fix_inline_html_claim_markers(content), content)
    content = _track("close_unclosed_fences", close_unclosed_fences(content), content)
    content = _track("fix_nested_fences", fix_nested_fences(content), content)
    content = _track("fix_single_backtick_code_blocks", fix_single_backtick_code_blocks(content), content)
    content = _track("fix_excess_backtick_fences", fix_excess_backtick_fences(content), content)
    content = _track("collapse_duplicate_fence_openings", collapse_duplicate_fence_openings(content), content)
    content = _track("fix_code_fences", fix_code_fences(content), content)
    content = _track("fix_trailing_periods_in_code", fix_trailing_periods_in_code(content), content)
    content = _track("merge_adjacent_code_blocks", merge_adjacent_code_blocks(content), content)
    content = _track("fix_unicode_in_code_blocks", fix_unicode_in_code_blocks(content), content)
    content = _track("validate_code_blocks", validate_code_blocks(content), content)

    # Phase 3: Content-Level Fixes
    content = _track("fix_collapsed_markdown_tables", fix_collapsed_markdown_tables(content), content)
    content = _track("strip_product_name_prefix", strip_product_name_prefix(content, ctx.product_name), content)
    content = _track("strip_forbidden_topic_headings", strip_forbidden_topic_headings(content, ctx.page), content)
    content = _track("remove_empty_sections", remove_empty_sections(content), content)

    # Phase 4: Strip Unwanted Patterns
    # TC-2375 (RD-02): Pure prose sanitizers are zone-guarded so they cannot
    # accidentally modify CODE_FENCE or FRONTMATTER content.
    content = _track("strip_llm_scaffolding", strip_llm_scaffolding(content), content)
    content = _track("strip_boilerplate_sentences", apply_to_prose_zones(strip_boilerplate_sentences, content), content)
    content = _track("strip_inline_seo_keywords", apply_to_prose_zones(strip_inline_seo_keywords, content), content)
    content = _track("fix_faq_doubled_prefix", fix_faq_doubled_prefix(content), content)
    content = _track("fix_faq_doubled_answer_prefix", fix_faq_doubled_answer_prefix(content), content)
    content = _track("fix_claim_markers_in_urls", fix_claim_markers_in_urls(content), content)
    content = _track("strip_visible_claim_markers", strip_visible_claim_markers(content), content)
    content = _track("strip_pipeline_comments", strip_pipeline_comments(content), content)
    content = _track("absolutize_links", absolutize_links(content, ctx.section, ctx.family, ctx.platform), content)
    content = _track("strip_double_periods", apply_to_prose_zones(strip_double_periods, content), content)
    content = _track("strip_emojis", apply_to_prose_zones(strip_emojis, content), content)
    content = _track("strip_ci_badges", strip_ci_badges(content), content)
    content = _track("strip_illustrative_comments", strip_illustrative_comments(content), content)
    content = _track("fix_truncated_sentences", fix_truncated_sentences(content), content)
    content = _track("normalize_module_names", apply_to_prose_zones(lambda c: normalize_module_names(c, ctx.product_facts), content), content)

    # Phase 5: Quality Enforcement
    content = _track("enforce_quality_floor", enforce_quality_floor(
        content, ctx.page, ctx.product_facts, ctx.snippet_catalog, ctx.llm_client
    ), content)

    return content
