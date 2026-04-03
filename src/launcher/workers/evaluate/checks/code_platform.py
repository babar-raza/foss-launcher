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

# TC-NET-003: Detect Python-style import syntax inside non-Python code blocks.
# Matches lines that start (possibly with whitespace) with "import X" or "from X import".
_PYTHON_IMPORT_LINE_RE = re.compile(r"^\s*(?:import|from)\s+\w", re.MULTILINE)
# Non-Python fence languages where Python imports are always wrong.
_NON_PYTHON_FENCE_LANGS = frozenset({"csharp", "cs", "c#", "java", "cpp", "c++"})
# Captures fence language tag and body content together.
_FENCE_BODY_RE = re.compile(r"```([\w#+.-]*)\n([\s\S]*?)```", re.DOTALL)

# TC-5329: Cross-ecosystem contamination patterns per platform.
# These detect .NET/C++CLI idioms appearing inside C++ code blocks, or C++ idioms
# appearing inside Java code blocks. Each entry is (compiled_regex, human_label).
# Patterns are checked only inside code fences whose language tag matches the platform.
_ECOSYSTEM_CONTAMINATION: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "cpp": [
        (re.compile(r"\bSystem\s*::\s*MakeObject\s*<"),   "System::MakeObject (.NET)"),
        (re.compile(r"\bSystem\s*::\s*DynamicCast\s*<"),  "System::DynamicCast (.NET)"),
        (re.compile(r"\bSystem\s*::\s*SafeCast\s*<"),     "System::SafeCast (.NET)"),
        (re.compile(r"\bSystem\s*::\s*Drawing\s*::"),     "System::Drawing (.NET)"),
        (re.compile(r"\bSystem\s*::\s*Exception\b"),      "System::Exception (.NET)"),
        (re.compile(r"\bgcnew\b"),                        "gcnew (C++/CLI)"),
        # ^ managed-pointer: letter/paren immediately before ^ (XOR has a space before ^)
        (re.compile(r"[A-Za-z_)]\^"),                     "managed-pointer ^ (C++/CLI)"),
        # IInterface instantiation: e.g. IPresentation p("file") — interfaces can't be instantiated
        (re.compile(r"\bI[A-Z][A-Za-z]{3,}\s+\w+\s*[=(;]"), "IInterface-instantiation (.NET/Java)"),
        # .get_X() .NET property accessor pattern: e.g. ->get_Message() ->get_Slides()
        (re.compile(r"->\s*get_[A-Z][A-Za-z]+\s*\(\)"),  ".get_X()-accessor (.NET)"),
    ],
    "java": [
        # C++ namespace syntax in Java code
        (re.compile(r"\bSystem\s*::\s*"),                 "System:: namespace (C++/.NET)"),
        # C++ using-namespace directive in Java code
        (re.compile(r"\busing\s+namespace\s+"),           "using namespace (C++)"),
    ],
}

# Which fence language tags correspond to each platform for ecosystem checking.
_ECOSYSTEM_FENCE_LANGS: dict[str, frozenset[str]] = {
    "cpp": frozenset({"cpp", "c++", "c"}),
    "java": frozenset({"java"}),
}


def _extract_platform(content: str) -> str:
    """Extract platform from frontmatter."""
    # Search full content — platform: field can be past char 500 in long frontmatter.
    m = _PLATFORM_FM_RE.search(content)
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

    # TC-NET-003: Detect Python-style import/from syntax inside non-Python fences.
    # Catches cases like `import Aspose.ThreeD` appearing inside a ```csharp block.
    for m in _FENCE_BODY_RE.finditer(content):
        lang_tag = m.group(1).strip().lower()
        body = m.group(2)
        if lang_tag in _NON_PYTHON_FENCE_LANGS and _PYTHON_IMPORT_LINE_RE.search(body):
            findings.append(Finding(
                check="code_platform",
                message=(
                    f"Python-style import/from statement found inside "
                    f"`{lang_tag}` code block — wrong language syntax for platform '{platform}'"
                ),
                severity="high",
                location=slug,
            ))

    return findings


def check_ecosystem_contamination(
    content: str,
    slug: str,
    *,
    page_role: str = "",
) -> list[Finding]:
    """Detect wrong-ecosystem code tokens inside code blocks (TC-5329).

    Checks for .NET/C++CLI idioms in C++ code fences and C++ idioms in Java
    code fences. Returns HIGH findings for each pattern match. This check runs
    in the Evaluate worker and provides grade-level visibility into residual
    contamination that survived the generate-loop scanner (TC-5330).
    """
    findings: list[Finding] = []
    platform = _extract_platform(content)
    patterns = _ECOSYSTEM_CONTAMINATION.get(platform)
    fence_langs = _ECOSYSTEM_FENCE_LANGS.get(platform)
    if not patterns or not fence_langs:
        return findings

    for m in _FENCE_BODY_RE.finditer(content):
        lang_tag = m.group(1).strip().lower()
        body = m.group(2)
        if lang_tag not in fence_langs:
            continue
        for regex, label in patterns:
            if regex.search(body):
                findings.append(Finding(
                    check="ecosystem_contamination",
                    message=(
                        f"Wrong-ecosystem pattern `{label}` found in `{lang_tag}` code block "
                        f"on `{platform}` page — this idiom belongs to a different "
                        f"language/runtime and will not compile or run correctly"
                    ),
                    severity="high",
                    location=slug,
                ))

    return findings
