"""Check 6: LLM artifact detection."""
from __future__ import annotations

import re
from collections import Counter

from launcher.models.evaluation import Finding
from launcher.shared.jaccard import strip_code_blocks

# Unambiguous LLM scaffold phrases. Intentionally excludes common technical
# writing idioms that generated false positives on legitimate docs:
#   "in this section", "when working with", "when it comes to",
#   "it's worth noting", "whether you're", "whether you need"
_ARTIFACT_PHRASES = [
    "let's explore",
    "let's dive",
    "as mentioned earlier",
    "as we discussed",
    "i hope this helps",
    "feel free to",
    "don't hesitate",
    "happy coding",
    "in conclusion",
    "to summarize",
    "as an ai",
    "i'm an ai",
    "certainly!",
    "absolutely!",
    "great question",
    "it is important to note",
    "plays a crucial role",
    "a powerful tool",
]

_ECHO_PATTERNS = [
    r"you (?:asked|mentioned|said)",
    r"based on (?:your|the) (?:request|question)",
]

# TC-GEN-602: Skeleton-directive sentence pattern: "ProductName -- description of what to write".
# Matches product display name (contains at least one dot, e.g. "Aspose.Cells") followed by " -- ".
# [^-\n]{0,200}: excludes dash and newline (no backtracking on " -- " delimiter), capped at 200 chars.
_SKELETON_DIRECTIVE_RE = re.compile(
    r'\b[A-Z][A-Za-z0-9]*\.[A-Za-z0-9]+[^-\n]{0,200} -- ',
)

# TC-3891: raw Python dict literal used as markdown link anchor text.
# Pattern: [{'type': ... or [{"type": ... as the link text portion.
_DICT_ANCHOR_RE = re.compile(r'\[\{[\'"]type[\'"]', re.DOTALL)

# TC-3891: empty or missing href in markdown links.
# Matches [text]() (empty parens) or [text]( at end-of-line (unclosed).
_EMPTY_HREF_RE = re.compile(
    r'\[[^\[\]]+\]\(\s*\)'           # [text]()
    r'|'
    r'\[[^\[\]]+\]\(\s*$',           # [text]( at end of line
    re.MULTILINE,
)


def check_artifacts(content: str, slug: str, *, product_name: str = "") -> list[Finding]:
    """Detect LLM scaffold text and boilerplate phrases."""
    findings: list[Finding] = []
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    # Strip code blocks so phrases in code comments don't fire false positives
    body_for_phrases = strip_code_blocks(body)
    lower_body = body_for_phrases.lower()

    for phrase in _ARTIFACT_PHRASES:
        if phrase in lower_body:
            findings.append(
                Finding(
                    check="artifacts",
                    message=f"LLM artifact phrase: '{phrase}'",
                    severity="medium",
                    location=slug,
                )
            )

    for pattern in _ECHO_PATTERNS:
        if re.search(pattern, lower_body):
            findings.append(
                Finding(
                    check="artifacts",
                    message=f"Echo pattern detected: '{pattern}'",
                    severity="medium",
                    location=slug,
                )
            )

    # Repeated section opener detector
    sections = re.split(r"(?m)^## ", body)
    openers: list[str] = []
    for section in sections[1:]:  # skip content before first ## heading
        lines = section.split("\n")
        first_sentence = ""
        for line in lines[1:]:  # skip the heading line itself
            stripped = line.strip()
            if stripped:
                # Take up to first sentence-ending period (period followed by whitespace).
                # Using `. ` avoids false positives from dotted product names like
                # "Aspose.Cells" — those periods are not sentence boundaries.
                m = re.search(r"\.\s", stripped)
                first_sentence = stripped[: m.start() + 1] if m else stripped
                break
        if first_sentence:
            openers.append(first_sentence.lower().strip())

    opener_counts = Counter(openers)
    for opener, count in opener_counts.items():
        if count >= 5:
            findings.append(
                Finding(
                    check="artifacts",
                    message=f"Repeated section opener ({count}x): '{opener[:80]}'",
                    severity="high",
                    location=slug,
                )
            )

    # Keyword stuffing detector
    # body_for_phrases = strip_code_blocks(body) computed above; reuse here
    prose = body_for_phrases
    if product_name:
        mentions = len(re.findall(re.escape(product_name), prose, re.IGNORECASE))
    else:
        mentions = len(re.findall(r"\b[A-Z][a-z]+\.[A-Z][A-Za-z]+\b", prose))
    word_count = len(prose.split())
    if word_count > 0:
        density = mentions / (word_count / 100)
        if density > 5:
            findings.append(
                Finding(
                    check="artifacts",
                    message=f"Keyword stuffing: product-name density {density:.1f} per 100 words (threshold 5)",
                    severity="medium",
                    location=slug,
                )
            )

    # TC-GEN-602: Skeleton-directive sentences leaked into published content.
    # Pattern: "Aspose.X -- description of what to write". The engineering strip in
    # section_validator.py removes these at generation time; this check catches any survivors.
    if product_name:
        skeleton_matches = _SKELETON_DIRECTIVE_RE.findall(body_for_phrases)
        if skeleton_matches:
            findings.append(
                Finding(
                    check="artifacts",
                    message=(
                        f"[ENG] {len(skeleton_matches)} skeleton-directive sentence(s) found "
                        f"(e.g. '{skeleton_matches[0].strip()}'). "
                        "Internal section-guidance text leaked into published content."
                    ),
                    severity="high",
                    location=slug,
                )
            )

    # TC-3891: dict-literal anchor text (unrendered linker artifact)
    # Scan the full body (including code blocks skipped for phrase checks) because
    # link syntax never legitimately appears inside fenced code blocks in rendered output.
    dict_matches = _DICT_ANCHOR_RE.findall(body)
    if dict_matches:
        findings.append(
            Finding(
                check="artifacts",
                message=(
                    f"[ENG] {len(dict_matches)} link(s) render raw Python dict as anchor text "
                    f"(e.g. '[{{\"type\": \"anchor\", ...}}](url)'). "
                    "This is an unrendered linker artifact visible to readers."
                ),
                severity="high",
                location=slug,
            )
        )

    # TC-3891: empty or missing href (broken links)
    # Strip code blocks first to avoid false positives from regex patterns in examples.
    # TC-3895: Severity raised from "medium" to "high" — broken links are user-visible failures.
    body_no_code = strip_code_blocks(body)
    empty_hrefs = _EMPTY_HREF_RE.findall(body_no_code)
    if empty_hrefs:
        findings.append(
            Finding(
                check="artifacts",
                message=(
                    f"[ENG] {len(empty_hrefs)} link(s) have an empty or missing href "
                    f"(e.g. '[text]()'). Broken links are visible to readers."
                ),
                severity="high",
                location=slug,
            )
        )

    return findings


# ---------------------------------------------------------------------------
# TC-QG-01: "When working with..." section-opener boilerplate detector
# ---------------------------------------------------------------------------

def check_opener_boilerplate(content: str, slug: str) -> list[Finding]:
    """Detect 'When working with...' used as a section opener (TC-QG-01).

    Fires when one or more paragraph-opening lines start with 'When working
    with ...'. Mid-paragraph uses ("This is useful when working with large
    files.") are not flagged — the phrase only becomes boilerplate when it
    leads a section.

    Severity:
      medium — 1 or 2 occurrences
      high   — 3 or more occurrences
    """
    # Strip frontmatter
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    # Strip code fences so phrases in code comments don't fire
    body = re.sub(r"```[^\n]*\n[\s\S]*?```", "", body, flags=re.DOTALL)

    count = 0
    for line in body.splitlines():
        stripped = line.strip()
        if re.match(r"when working with\b", stripped, re.IGNORECASE):
            count += 1

    if count == 0:
        return []

    severity = "high" if count >= 3 else "medium"
    return [Finding(
        check="opener_boilerplate",
        message=(
            f"{'Multiple sections use' if count >= 3 else 'Section uses'} "
            f"'When working with...' as an opener ({count} "
            f"occurrence{'s' if count != 1 else ''}). "
            "Replace with a specific statement about what the page covers."
        ),
        severity=severity,
        location=slug,
    )]
