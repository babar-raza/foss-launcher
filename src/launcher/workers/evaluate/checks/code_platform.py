"""Check: code_platform — validate code block languages and install commands match page platform.

Catches cross-platform contamination such as Python ``pip install`` appearing on
a C++ page, or Java code blocks on a .NET page.  Severity: HIGH.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

# Platform → expected code fence languages (lowered)
_PLATFORM_LANGUAGES: dict[str, set[str]] = {
    "python": {"python", "py", "bash", "shell", "sh", "console", "text", "json", "yaml", "toml", "csv", "xml", ""},
    "dotnet": {"csharp", "cs", "c#", "xml", "json", "bash", "shell", "powershell", "text", ""},
    "java": {"java", "xml", "json", "bash", "shell", "gradle", "groovy", "text", "properties", ""},
    "cpp": {"cpp", "c++", "c", "cmake", "bash", "shell", "text", "json", "xml", ""},
    "typescript": {"typescript", "ts", "javascript", "js", "json", "bash", "shell", "text", "yaml", ""},
}

# Platform → wrong install commands (regex patterns)
_WRONG_INSTALL: dict[str, list[re.Pattern[str]]] = {
    "python": [
        re.compile(r"\bnuget\s+install\b", re.IGNORECASE),
        re.compile(r"\bmvn\s+", re.IGNORECASE),
        re.compile(r"\bgradle\s+", re.IGNORECASE),
        re.compile(r"\bdotnet\s+add\b", re.IGNORECASE),
    ],
    "dotnet": [
        re.compile(r"\bpip\s+install\b", re.IGNORECASE),
        re.compile(r"\bnpm\s+install\b", re.IGNORECASE),
        re.compile(r"\bmvn\s+", re.IGNORECASE),
    ],
    "java": [
        re.compile(r"\bpip\s+install\b", re.IGNORECASE),
        re.compile(r"\bnpm\s+install\b", re.IGNORECASE),
        re.compile(r"\bnuget\s+install\b", re.IGNORECASE),
    ],
    "cpp": [
        re.compile(r"\bpip\s+install\b", re.IGNORECASE),
        re.compile(r"\bnpm\s+install\b", re.IGNORECASE),
        re.compile(r"\bnuget\s+install\b", re.IGNORECASE),
        re.compile(r"\bmvn\s+", re.IGNORECASE),
    ],
    "typescript": [
        re.compile(r"\bpip\s+install\b", re.IGNORECASE),
        re.compile(r"\bnuget\s+install\b", re.IGNORECASE),
        re.compile(r"\bmvn\s+", re.IGNORECASE),
    ],
}

_FENCE_RE = re.compile(r"^```(\w*)", re.MULTILINE)
_PLATFORM_FM_RE = re.compile(r"^platform:\s*[\"']?(\w+)", re.MULTILINE)


def _extract_platform(content: str) -> str:
    """Extract platform from frontmatter."""
    m = _PLATFORM_FM_RE.search(content[:500])
    return m.group(1).lower() if m else ""


def check_code_platform(content: str, slug: str, *, page_role: str = "") -> list[Finding]:
    """Validate code block languages and install commands match the page platform."""
    findings: list[Finding] = []
    platform = _extract_platform(content)
    if not platform:
        return findings

    allowed_langs = _PLATFORM_LANGUAGES.get(platform)
    if allowed_langs:
        for m in _FENCE_RE.finditer(content):
            lang = m.group(1).lower()
            if lang and lang not in allowed_langs:
                findings.append(Finding(
                    check="code_platform",
                    message=f"Code block language '{lang}' unexpected for platform '{platform}'",
                    severity="high",
                    location=slug,
                ))

    wrong_patterns = _WRONG_INSTALL.get(platform, [])
    for pat in wrong_patterns:
        if pat.search(content):
            findings.append(Finding(
                check="code_platform",
                message=f"Wrong install command for platform '{platform}': {pat.pattern}",
                severity="critical",
                location=slug,
            ))

    return findings
