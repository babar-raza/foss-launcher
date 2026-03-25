"""Pre-LLM prompt builder for per-section content generation."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from launcher.models.claims import Claim, Snippet
from launcher.models.product import (
    ClassBrief,
    EnumMember,
    EnumRecord,
    MethodSignature,
    ProductIdentity,
    PropertyRecord,
)
from launcher.models.understanding import PlannedPage
from launcher.shared.page_skeletons import SkeletonSection
from launcher.shared.platform_utils import get_install_cmd, get_lang_tag


_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "section_writer.txt"

# TC-CPP-411: Platform-aware language tag for verification code fences.
_VERIFICATION_LANG: dict[str, str] = {
    "python": "python",
    "dotnet": "csharp",
    "java": "java",
    "cpp": "cpp",
    "node": "javascript",
    "typescript": "typescript",
}

# ---------------------------------------------------------------------------
# TC-FIX-214: Prose contract loading
# ---------------------------------------------------------------------------

_PROSE_CONTRACTS_DIR: Path = Path(__file__).resolve().parents[2] / "prompts" / "prose_contracts"
_prose_contract_cache: dict[str, str] = {}


def _load_prose_contract(page_role: str) -> str:
    """Load the prose contract for *page_role*, falling back to ``_default.txt``."""
    if page_role in _prose_contract_cache:
        return _prose_contract_cache[page_role]

    path = _PROSE_CONTRACTS_DIR / f"{page_role}.txt"
    if not path.is_file():
        path = _PROSE_CONTRACTS_DIR / "_default.txt"
    if not path.is_file():
        _prose_contract_cache[page_role] = ""
        return ""

    text = path.read_text(encoding="utf-8").strip()
    _prose_contract_cache[page_role] = text
    return text


# ---------------------------------------------------------------------------
# TC-GEN-212: Platform-aware import conventions for section_writer.txt
# ---------------------------------------------------------------------------

_IMPORT_KEYWORD: dict[str, str] = {
    "python": "import",
    "java": "import",
    "dotnet": "using",
    "cpp": "#include",
    "node": "require/import",
    "typescript": "import",
}


def _build_import_statement(platform: str, code_import: str) -> str:
    """Build the canonical import statement for the platform."""
    kw = _IMPORT_KEYWORD.get(platform, "import")
    if platform == "dotnet":
        return f"using {code_import};"
    if platform == "cpp":
        return f'#include <{code_import}>'
    if platform in ("node", "typescript"):
        return f'import {{ ... }} from "{code_import}";'
    if platform == "java":
        return f"import {code_import}.*;"
    # python and fallback
    return f"{kw} {code_import}"


def _build_wrong_import_warning(platform: str, code_import: str) -> str:
    """Build a platform-appropriate wrong-import warning, or empty string."""
    if platform == "python" and "aspose" in code_import.lower():
        return ' If you write "import aspose.cells" or any dotted Aspose path that differs from the one above, your output is wrong.'
    if platform == "cpp":
        return (
            f' Do NOT append, modify, or extend the namespace. '
            f'For example, NEVER write `{code_import}::Foss` or any sub-namespace not listed in the API SURFACE.'
        )
    return ""


def _build_import_rule_block(platform: str, code_import: str) -> str:
    """Build the CRITICAL IMPORT RULE block for section_writer.txt."""
    if platform == "python":
        return (
            f"CRITICAL IMPORT RULE: The ONLY valid Python import for this product is "
            f"`{code_import}`. NEVER write `import aspose.cells`, `import aspose.pydrawing`, "
            f"`import Aspose.Cells`, or any dotted Aspose path that differs from `{code_import}`. "
            f"ALWAYS write: `import {code_import}`. Any other import path is WRONG and will be rejected"
        )
    if platform == "dotnet":
        return (
            f"CRITICAL IMPORT RULE: The ONLY valid .NET using directive for this product is "
            f"`using {code_import};`. NEVER write `using Aspose.Cells`, `using aspose_cells_foss`, "
            f"or any namespace not matching `{code_import}`. ALWAYS write: `using {code_import};`"
        )
    if platform == "java":
        return (
            f"CRITICAL IMPORT RULE: The ONLY valid Java import for this product is "
            f"`import {code_import}.*;` (or specific classes). NEVER write `import aspose.cells`, "
            f"`import Aspose.Cells`, or any package path not starting with `{code_import}`. "
            f"ALWAYS write: `import {code_import}.*;<your specific class imports>`"
        )
    if platform == "cpp":
        return (
            f"CRITICAL IMPORT RULE: The ONLY valid C++ namespace for this product is "
            f"`{code_import}`. All `#include` directives and `using namespace` declarations "
            f"MUST use exactly `{code_import}`. Do NOT append, modify, or extend the namespace "
            f"(e.g., do NOT use `{code_import}::Foss` or any other variant). "
            f"NEVER write Python-style imports or .NET-style using directives"
        )
    # Fallback for node/typescript/unknown
    return (
        f"CRITICAL IMPORT RULE: The ONLY valid import for this product is `{code_import}`. "
        f"Do NOT use any other import path"
    )

# ---------------------------------------------------------------------------
# Reference-page role awareness (TC-3801)
# ---------------------------------------------------------------------------

_REFERENCE_ROLES: set[str] = {"api_reference", "reference_object_page"}

# TC-3902: Roles that require at least one code block per section.
# When a section belongs to one of these roles AND no executable snippets are
# available, an "EVIDENCE ABSENT" instruction is injected to prevent the LLM
# from fabricating code.  Keep in sync with _CODE_REQUIRED_ROLES in worker.py.
_CODE_EVIDENCE_ROLES: frozenset[str] = frozenset({
    "api_reference", "reference_object_page", "howto_article",
    "getting_started", "installation",
})

# TC-4041 (QSR-04): module-level constant — evaluated once, not per call.
_FORMAT_ELIGIBLE_ROLES: frozenset[str] = frozenset({
    "feature_overview",
    "how_to_convert",
    "feature_blog",
    "landing_page",
    "developer_guide",
    "how_to",
})

_INSTALL_REFERENCE_PAGE_ROLES: frozenset[str] = frozenset({
    "install",
    "installation",
    "getting_started",
})

_REFERENCE_PREAMBLE: str = (
    "IMPORTANT — This is a REFERENCE page, not a content page.\n"
    "- Lead with structured data (tables, signatures). "
    "Limit prose to 1-2 sentences before each table.\n"
    "- For Constructors, Properties, Methods sections: the table IS the "
    "primary content. Do NOT write multi-paragraph descriptions before the table.\n"
    "- Table content MUST be pipe-delimited markdown "
    "(| Col1 | Col2 |), NOT JSON arrays or Python dicts.\n"
    "- Do NOT write marketing language, feature lists, or general product "
    "descriptions.\n"
    "- Do NOT use HTML anchor tags. Use markdown [text](url) syntax only.\n\n"
)

_REFERENCE_DIRECTIVE_OVERRIDES: dict[str, str] = {
    "overview": (
        "Write exactly 1-3 sentences stating what this class or module does. "
        "No feature lists, no marketing language, no general product descriptions."
    ),
    "remarks": (
        "Write 1-2 sentences about usage caveats or important notes. "
        "No general library descriptions."
    ),
    "see also": (
        "Produce a list block with 2-5 markdown links. "
        "Do NOT use HTML anchor tags (<a href>). Use markdown [text](url) syntax only."
    ),
}

# Section-type-specific structural directives that tell the LLM what
# output shape to produce.  Keys are matched case-insensitively against
# the section heading.
_STRUCTURE_DIRECTIVES: dict[str, str] = {
    "overview": (
        "Write 1-3 concise paragraphs introducing the topic. "
        "Lead with the main purpose, then summarize key capabilities."
    ),
    "introduction": (
        "Write 1-3 concise paragraphs introducing the topic. "
        "Lead with the main purpose, then summarize key capabilities."
    ),
    "frequently asked questions": (
        "Produce Q&A pairs. Each question is a SHORT H3 heading (max 15 words, "
        "question only — no answer in the heading). The answer MUST be a separate "
        "paragraph block immediately after the heading. Never put answer text in "
        "the heading block. Cover 3-6 distinct questions drawn from the claims."
    ),
    "key features": (
        "Produce a list block with 4-8 feature bullet points. "
        "Each item should name the feature and give a one-sentence benefit."
    ),
    "key highlights": (
        "Produce a list block with 4-8 highlight bullet points. "
        "Each item should name the highlight and give a one-sentence description."
    ),
    "prerequisites": (
        "List the required setup: language version, pip install command, "
        "and any system dependencies. Use a list block or short paragraphs."
    ),
    "step-by-step guide": (
        "Produce numbered step-by-step instructions. Use H3 heading blocks "
        "for each step title (e.g. 'Step 1: Create a Workbook'), followed by "
        "a paragraph explaining the step and a code block showing the code."
    ),
    "steps": (
        "Produce numbered step-by-step instructions. Use H3 heading blocks "
        "for each step title (e.g. 'Step 1: Create a Workbook'), followed by "
        "a paragraph explaining the step and a code block showing the code."
    ),
    "solution": (
        "Present the working solution. Start with a brief explanation of the "
        "approach, then provide a complete code block demonstrating the fix. "
        "Use only the canonical import."
    ),
    "solution steps": (
        "Produce numbered step-by-step instructions. Use H3 heading blocks "
        "for each step title (e.g. 'Step 1: Create a Workbook'), followed by "
        "a paragraph explaining the step and a code block showing the code."
    ),
    "code examples": (
        "Produce one or more complete, runnable code examples. Each example "
        "should have a brief paragraph explaining what it does, followed by "
        "a code block. Use only the canonical import."
    ),
    "code samples": (
        "Produce one or more complete, runnable code examples. Each example "
        "should have a brief paragraph explaining what it does, followed by "
        "a code block. Use only the canonical import."
    ),
    "complete code example": (
        "Produce one complete, runnable code example combining all prior steps. "
        "Start with a brief paragraph explaining the end-to-end workflow, then "
        "a single code block. Use only the canonical import."
    ),
    "code example": (
        "Produce one complete, runnable code example. Start with a brief "
        "paragraph explaining what it demonstrates, then a code block. "
        "Use only the canonical import."
    ),
    "constructors": (
        "Produce a markdown table listing constructor signatures. "
        "Use this exact format:\n"
        "| Signature | Parameters | Description |\n"
        "|-----------|------------|-------------|\n"
        "| ... | ... | ... |\n\n"
        "Do NOT output JSON arrays or dicts — use markdown table syntax only. "
        "If no constructors are known from the claims, write a brief paragraph."
    ),
    "properties": (
        "Produce a markdown table listing properties. "
        "Use this exact format:\n"
        "| Name | Type | Description |\n"
        "|------|------|-------------|\n"
        "| ... | ... | ... |\n\n"
        "Do NOT output JSON arrays or dicts — use markdown table syntax only. "
        "If no properties are known from the claims, write a brief paragraph."
    ),
    "methods": (
        "Produce a markdown table listing methods. "
        "Use this exact format:\n"
        "| Method | Return Type | Description |\n"
        "|--------|-------------|-------------|\n"
        "| ... | ... | ... |\n\n"
        "Do NOT output JSON arrays or dicts — use markdown table syntax only. "
        "If no methods are known from the claims, write a brief paragraph."
    ),
    "see also": (
        "Produce a list block with 2-5 related links. Each item should be "
        "a markdown link with descriptive anchor text."
    ),
    "troubleshooting": (
        "Produce problem-solution pairs. Use H3 heading blocks for each problem "
        "title, followed by a paragraph with the cause and solution."
    ),
    "common issues": (
        "Produce problem-solution pairs. Use H3 heading blocks for each issue "
        "title, followed by a paragraph with symptoms, cause, and fix."
    ),
    "getting started": (
        "Write a brief introduction, then provide a minimal code example "
        "that demonstrates the simplest usage of the library."
    ),
    "remarks": (
        "Write 1-2 paragraphs covering important notes, caveats, or best "
        "practices that developers should be aware of."
    ),
    "notes and best practices": (
        "Write 1-2 paragraphs covering important notes, caveats, or best "
        "practices that developers should be aware of."
    ),
    "problem": (
        "Write 1-2 sentences clearly stating the problem the reader wants to solve."
    ),
    "goal": (
        "Write 1-2 sentences clearly stating what the reader will accomplish."
    ),
    "result": (
        "Describe the expected output or how to verify the operation succeeded. "
        "Include a brief code block or expected console output if applicable."
    ),
    "pages in this section": (
        "Produce a list block where each item is a markdown link to a child page "
        "with a one-sentence description of what that page covers."
    ),
    "recommendations": (
        "Produce a list of best-practice recommendations. Each item should "
        "state the recommendation and give a one-sentence rationale."
    ),
    "common mistakes": (
        "Produce a list of common anti-patterns. Each item should describe "
        "the mistake and explain the correct approach."
    ),
    "common pitfalls": (
        "Produce a list of common performance pitfalls. Each item should "
        "describe the issue and the recommended alternative."
    ),
    "optimization strategies": (
        "Produce specific optimization techniques. Use H3 heading blocks "
        "for each strategy, followed by a paragraph explaining the technique "
        "and a code block demonstrating it."
    ),
    "key takeaways": (
        "Produce a list block with 3-5 concise takeaway bullet points. "
        "Each item should state one actionable lesson or important fact the "
        "reader should remember."
    ),
    "how it works": (
        "Explain the technical mechanism in 2-3 paragraphs. Include a code "
        "block if it helps illustrate the concept."
    ),
    "quick start": (
        "Provide the shortest possible path to a working example: install, "
        "import, and a 5-10 line code block."
    ),
    "api summary": (
        "Produce a table block listing the main classes or functions. "
        "Columns: Name, Description. Keep descriptions to one sentence each."
    ),
    "key members": (
        "Produce a table block listing key class members. "
        "Columns: Member, Type, Description."
    ),
    "installation": (
        "Show the pip install command in a code block, then describe any "
        "post-install verification steps."
    ),
    "install via package manager": (
        "Show the pip install command in a code block."
    ),
    "manual installation": (
        "Describe step-by-step manual installation from source."
    ),
    "verify installation": (
        "Show a short code block that verifies the installation succeeded."
    ),
    "verification": (
        "Describe how to verify the operation succeeded. Provide a short code "
        "block that checks the output or result, and state the expected outcome."
    ),
    "system requirements": (
        "List minimum Python version, OS compatibility, and any system "
        "dependencies in a list block."
    ),
    "next steps": (
        "Produce a list of 2-4 links to related pages the reader should "
        "explore next, each with a one-sentence description."
    ),
    "first steps": (
        "Walk the reader through the simplest useful workflow step by step. "
        "Use H3 heading blocks for each step, followed by a paragraph and "
        "a code block. The reader should have a working result by the end."
    ),
    "error messages": (
        "Produce a table block of common error messages. "
        "Columns: Error, Cause, Fix."
    ),
    "getting help": (
        "List support channels: GitHub issues, documentation links, "
        "and community resources."
    ),
    "when to use": (
        "Describe 2-3 scenarios where this approach is the right choice."
    ),
    "core concepts": (
        "Explain the 3-5 foundational concepts a developer must understand "
        "to use this library effectively. Use H3 heading blocks for each "
        "concept, followed by a 1-2 sentence explanation."
    ),
    "implementation": (
        "Provide detailed implementation guidance with code examples. "
        "Use H3 heading blocks for each implementation aspect, followed "
        "by a paragraph and a code block demonstrating the technique."
    ),
    "advanced usage": (
        "Cover advanced patterns and techniques. Use H3 heading blocks "
        "for each advanced topic, followed by a paragraph explaining the "
        "use case and a code block demonstrating it."
    ),
    "constructor": (
        "Describe the constructor signature and its parameters. "
        "Include a code block showing how to instantiate the object."
    ),
    "example": (
        "Produce one complete, runnable code example. Start with a brief "
        "paragraph explaining what it demonstrates, then a code block. "
        "Use only the canonical import."
    ),
    # --- SR-01: Missing directive entries (alphabetical) ---
    "additional resources": (
        "Produce a list block with 3-5 links to supplementary resources such as "
        "documentation, tutorials, and community pages, each with a one-sentence description."
    ),
    "advanced scenarios": (
        "Describe 2-4 advanced use cases. Use H3 heading blocks for each scenario "
        "title, followed by a paragraph explaining the scenario and a code block "
        "demonstrating it."
    ),
    "applying a license": (
        "Show how to apply a license file or key in code. Provide a code block "
        "with the license-loading snippet, then explain file placement and alternatives."
    ),
    "common scenarios": (
        "Describe 3-5 common use cases. Use a list block where each item names "
        "the scenario and links to the relevant guide page."
    ),
    "evaluation limitations": (
        "List the limitations that apply when running without a license. "
        "Use a list block with 3-6 items describing each restriction."
    ),
    "faq": (
        "Produce Q&A pairs. Each question is a SHORT H3 heading (max 15 words, "
        "question only — no answer in the heading). The answer MUST be a separate "
        "paragraph block immediately after the heading. Never put answer text in "
        "the heading block. Cover 3-6 distinct questions drawn from the claims."
    ),
    "license types": (
        "Describe the available license types in a table block. "
        "Columns: License Type, Description, Use Case."
    ),
    "metered licensing": (
        "Explain metered licensing in 1-2 paragraphs, then provide a code block "
        "showing how to set metered credentials."
    ),
    "popular guides": (
        "Produce a list block with 4-8 links to the most important guides, "
        "each with a one-sentence description of what the guide covers."
    ),
    "reference and api": (
        "Produce a list block with 3-5 links to API reference pages and "
        "related reference documentation, each with a one-sentence description."
    ),
    "support": (
        "List support channels and resources: GitHub issues, documentation links, "
        "forums, and paid support options. Use a list block."
    ),
    # --- TC-3799: Skeleton variant headings ---
    "working with data": (
        "Explain core data manipulation operations with code examples. Cover "
        "reading, writing, and modifying data elements. Use H3 heading blocks "
        "for each operation, followed by a code block demonstrating it."
    ),
    "loading the file": (
        "Show how to load the file with code. Cover loading from file paths "
        "and streams, and mention available load options. Provide a code block "
        "for the most common loading scenario."
    ),
    "saving the file": (
        "Show how to save or export the file with code. Cover format selection, "
        "save options, and output paths. Provide a code block for the most "
        "common saving scenario."
    ),
    "conversion steps": (
        "Produce step-by-step format conversion instructions. Use H3 heading "
        "blocks for each step (e.g. 'Step 1: Load Source File'), followed by "
        "a paragraph and code block. Show input format, configuration, and "
        "output format."
    ),
    "symptoms": (
        "Describe the observable symptoms the reader will recognize: error "
        "messages, stack traces, unexpected output, or performance degradation. "
        "Use a list block or short paragraphs."
    ),
    "root cause": (
        "Explain why the problem occurs. Reference specific API behavior, "
        "configuration defaults, or environment issues. Keep it factual and "
        "trace to claims."
    ),
    "optimization steps": (
        "Produce concrete optimization techniques. Use H3 heading blocks for "
        "each technique, followed by a paragraph explaining the approach and "
        "a code block showing before/after or the optimized version."
    ),
    "benchmarks": (
        "Show measurable performance improvements. Include timing code, memory "
        "comparisons, or throughput measurements. Use a code block with "
        "measurement code and a table or paragraph stating the results."
    ),
    "supported formats": (
        "List supported file formats in a table block. "
        "Use this exact format:\n"
        "| Format | Extension | Notes |\n"
        "|--------|-----------|-------|\n"
        "| ... | ... | ... |\n\n"
        "Only list formats mentioned in the claims."
    ),
    "output options": (
        "Describe available output formats and configuration parameters. "
        "Use a table block or list block. Cover format selection, quality "
        "settings, and any format-specific options."
    ),
}

# ---------------------------------------------------------------------------
# SR-05: Heading alias normalization
# ---------------------------------------------------------------------------
# Maps variant heading text (lowered) to the canonical directive key.
# This avoids duplicating directive entries for near-identical headings.
_HEADING_ALIASES: dict[str, str] = {
    "quickstart": "quick start",
    "what's next": "next steps",
}

# TC-3879 Wave 1 (F3): Prefix/substring map for common heading patterns that don't
# exactly match a directive key. Maps heading substrings (lowered) to directive keys.
# Applied as Tier 3 lookup when exact match (Tier 1) and alias (Tier 2) both miss.
_HEADING_PREFIX_MAP: dict[str, str] = {
    "how to": "getting started",
    "get started": "getting started",
    "quick start": "quick start",
    "working with": "usage examples",
    "work with": "usage examples",
    "use case": "common scenarios",
    "use cases": "common scenarios",
    "scenario": "common scenarios",
    "step-by-step": "step-by-step guide",
    "converting": "conversion steps",
    "conversion": "conversion steps",
    "loading": "loading data",
    "saving": "saving data",
    "exporting": "exporting data",
    "importing": "importing data",
    "formatting": "formatting",
    "styling": "formatting",
    "install": "installation",
    "setup": "installation",
    "config": "configuration",
    "setting": "configuration",
    "trouble": "troubleshooting",
    "debug": "troubleshooting",
    "error": "troubleshooting",
    "best practice": "best practices",
    "tip": "best practices",
    "reference": "api reference",
    "advance": "advanced topics",
    "concept": "key concepts",
    "introduction": "introduction",
    "overview": "overview",
}

# TC-HAL-08: Claims below this confidence are excluded from generation prompts
_CLAIM_CONFIDENCE_THRESHOLD: float = 0.5

# TC-4230: Maximum claims injected into a single section prompt.
# api-overview pages can have 160+ claims assigned; injecting all of them
# into one prompt causes finish_reason: length (truncated responses).
# Cap at 20 — a 400-word section rarely needs more than 20 distinct claims.
_MAX_CLAIMS_PER_SECTION: int = 20

# TC-3876 (W2-S5): Tier-aware word count targets.
# Tier C repos have limited evidence — target concise, factual sections.
_TIER_WORD_COUNTS: dict[str, tuple[int, int]] = {
    "A": (150, 500),
    "B": (100, 350),
    "C": (60, 200),
}

# TC-3879 Wave 1 (F3): Generic structural fallback directive returned when no tier matches.
# Replaces the previous empty-string return which gave the LLM zero structural guidance.
_GENERIC_STRUCTURAL_DIRECTIVE: str = (
    "Write 2-4 focused paragraphs covering the topic indicated by the section heading. "
    "Be specific and practical: include concrete examples, a code block if relevant, "
    "or a short list. Avoid generic introductory sentences. Lead with the most useful "
    "information for a developer who needs to accomplish a task."
)


def _get_structure_directive(heading: str, page_role: str = "") -> str:
    """Return the structural directive for a section heading.

    4-tier lookup (TC-3879 Wave 1 F3):
      Tier 1: Exact match in _STRUCTURE_DIRECTIVES (case-insensitive via lowering)
      Tier 2: Alias match in _HEADING_ALIASES → then Tier 1 on canonical
      Tier 3: Prefix/keyword match in _HEADING_PREFIX_MAP (substring check)
      Tier 4: _GENERIC_STRUCTURAL_DIRECTIVE (always matches — never returns empty)

    For reference page roles, checks _REFERENCE_DIRECTIVE_OVERRIDES before Tier 1.
    """
    key = heading.strip().lower()
    if not key:
        return ""  # Empty / whitespace heading — no directive applies

    # Reference pages use tighter directives for certain sections
    if page_role in _REFERENCE_ROLES:
        override = _REFERENCE_DIRECTIVE_OVERRIDES.get(key)
        if override:
            return override

    # Tier 1: exact match
    directive = _STRUCTURE_DIRECTIVES.get(key, "")
    if directive:
        return directive

    # Tier 2: alias → canonical → exact match
    canonical = _HEADING_ALIASES.get(key)
    if canonical:
        directive = _STRUCTURE_DIRECTIVES.get(canonical, "")
        if directive:
            return directive

    # Tier 3: prefix/keyword substring match in _HEADING_PREFIX_MAP
    for keyword, directive_key in _HEADING_PREFIX_MAP.items():
        if keyword in key:
            directive = _STRUCTURE_DIRECTIVES.get(directive_key, "")
            if directive:
                logger.debug(
                    "Directive Tier 3 (prefix): heading='%s' matched keyword='%s' -> key='%s'",
                    heading, keyword, directive_key,
                )
                return directive

    # Tier 4: generic structural fallback — always returns useful guidance
    logger.debug(
        "Directive Tier 4 (generic): no match for heading='%s' (page_role='%s')",
        heading, page_role,
    )
    return _GENERIC_STRUCTURAL_DIRECTIVE


def _rank_snippets(
    snippets: list,
    section_claim_ids: set,
    max_count: int = 5,
) -> list:
    """Rank snippets by quality: extracted > generated > synthetic, then by claim overlap.

    Deterministic (uses tuple sort, PYTHONHASHSEED=0 safe).
    Only returns snippets that have at least one claim overlapping section_claim_ids.
    """
    _SOURCE_PRIORITY = {"extracted": 0, "generated": 1, "synthetic": 2}
    relevant = [s for s in snippets if set(getattr(s, "claim_ids", [])) & section_claim_ids]
    return sorted(
        relevant,
        key=lambda s: (
            _SOURCE_PRIORITY.get(getattr(s, "source_type", "generated"), 1),
            -len(set(getattr(s, "claim_ids", [])) & section_claim_ids),
            # tertiary: stable string key for full determinism
            getattr(s, "snippet_id", "") or (
                getattr(s, "claim_ids", [""])[0]
                if getattr(s, "claim_ids", []) else ""
            ),
        ),
    )[:max_count]


def _format_limitations(limitations: "list | None") -> str:
    """Format up to 10 LimitationEntry objects into a bullet list for prompt injection.

    HG-11: Surfaces source-verified limitations so the LLM does not fabricate capabilities
    that are explicitly known to be missing or experimental.
    """
    if not limitations:
        return ""
    lines = []
    for lim in limitations[:10]:
        feature = getattr(lim, "feature", "") or str(lim)
        constraint = getattr(lim, "constraint", "")
        status = getattr(lim, "status", "warning")
        line = f"- {feature}: {constraint}" if constraint else f"- {feature}"
        if status in ("experimental", "unsupported", "deprecated"):
            line += f" [{status}]"
        lines.append(line)
    return "\n".join(lines)


def _format_api_ids_guard(api_identifiers: "list[str] | None", display_name: str) -> str:
    """Format top API identifiers into a MUST-NOT-INVENT guard block.

    HG-11: The pilot revealed the LLM fabricates class names not in the extracted API.
    Presenting the known class names explicitly reduces hallucination.
    Capped at 30 to stay within token budget.
    """
    if not api_identifiers:
        return ""
    # Only show class-level identifiers (capitalized tokens) to keep the list short
    class_names = [t for t in api_identifiers if t and t[0].isupper()][:30]
    if not class_names:
        class_names = list(api_identifiers)[:30]
    names_str = ", ".join(class_names)
    return (
        f"KNOWN API CLASSES FOR {display_name.upper()} "
        f"(DO NOT invent any class or module name outside this list — "
        f"any class not listed here does NOT exist):\n{names_str}"
    )


def _format_capabilities(caps: "list[dict] | None") -> str:
    """Format up to 5 capability dicts as a bullet list for prompt injection.

    TC-HO-04: Surfaces product_evidence.capabilities so the LLM has explicit capability
    statements from README/docstrings rather than inferring from claims alone.
    Each dict is expected to have a 'text' key; missing keys are handled gracefully.
    """
    if not caps:
        return ""
    lines = []
    for cap in caps[:5]:
        text = (
            cap.get("text", "") if isinstance(cap, dict)
            else getattr(cap, "text", "") or str(cap)
        )
        if text:
            lines.append(f"- {text}")
    if not lines:
        return ""
    return "PRODUCT CAPABILITIES (source-verified from README/docstrings):\n" + "\n".join(lines)


def _format_conversion_pairs(pairs: "list[dict] | None", heading: str) -> str:
    """Format up to 8 conversion pairs as arrow-separated bullet lines.

    TC-HO-05: Only injected when the section heading matches conversion keywords
    (convert, export, transform, save as, output). Helps the LLM produce
    accurate "convert X to Y" content rather than guessing from flat format lists.
    """
    if not pairs:
        return ""
    _CONVERSION_KEYWORDS = ("convert", "export", "transform", "save as", "output")
    lower_heading = heading.lower()
    if not any(kw in lower_heading for kw in _CONVERSION_KEYWORDS):
        return ""
    lines = []
    for pair in pairs[:8]:
        if isinstance(pair, dict):
            source = pair.get("source", "")
            target = pair.get("target", "")
        else:
            source = getattr(pair, "source", "")
            target = getattr(pair, "target", "")
        if source and target:
            lines.append(f"- {source} \u2192 {target}")
    if not lines:
        return ""
    return "SUPPORTED CONVERSION PAIRS (source-verified):\n" + "\n".join(lines)


def _format_missing_info(missing: "list | None") -> str:
    """Format MissingInfoEntry list as DO NOT CLAIM instructions.

    TC-HO-06: Prevents the LLM from fabricating install commands, workflows,
    or capabilities that Understand explicitly recorded as unknowable.
    """
    if not missing:
        return ""
    lines = []
    for entry in missing:
        if isinstance(entry, dict):
            field = entry.get("field", "") or entry.get("field_name", "")
            reason = entry.get("reason", "")
        else:
            field = getattr(entry, "field", "") or getattr(entry, "field_name", "")
            reason = getattr(entry, "reason", "")
        if field:
            line = f"DO NOT CLAIM OR INVENT: {field}"
            if reason:
                line += f" (could not be extracted: {reason})"
            lines.append(line)
    if not lines:
        return ""
    return (
        "EXTRACTION GAPS — MANDATORY (fields below could not be verified from source):\n"
        + "\n".join(lines)
    )


def _format_richness_profile(richness_tier: "Any | None") -> str:
    """Format RichnessResult into a REPOSITORY PROFILE block for prompt injection.

    TC-HO-08A: Parses the semicolon-separated reason string from RichnessResult
    into a structured block so the LLM understands evidence quality constraints.
    For Tier C with code_evidence_sparse=True, adds a fabrication warning.
    """
    if richness_tier is None:
        return ""
    tier_str = getattr(richness_tier, "tier", None)
    if tier_str is None:
        return ""
    # RichnessTier enum — get string value
    if hasattr(tier_str, "value"):
        tier_str = tier_str.value
    reason = getattr(richness_tier, "reason", "") or ""
    sparse = getattr(richness_tier, "code_evidence_sparse", False)

    lines = [f"REPOSITORY PROFILE:", f"- Richness Tier: {tier_str}"]
    if reason:
        for part in reason.split(";"):
            part = part.strip()
            if part:
                lines.append(f"- {part}")
    if tier_str == "C" and sparse:
        lines.append(
            "- Do not fabricate code examples. One real example or prose only."
        )
    return "\n".join(lines)


def _should_include_install_reference(page: PlannedPage) -> bool:
    """Return True when install guidance belongs in this page context."""
    return (getattr(page, "page_role", "") or "") in _INSTALL_REFERENCE_PAGE_ROLES


def build_section_prompt(
    section: SkeletonSection,
    section_index: int,
    section_count: int,
    page: PlannedPage,
    product: ProductIdentity,
    claims: list[Claim],
    snippets: list[Snippet],
    public_classes: list[str] | None = None,
    class_briefs: list[ClassBrief] | None = None,
    heal_metadata: dict | None = None,
    skills_block: str = "",
    golden_dir: "Path | None" = None,
    variant: str = "standard",  # TC-3881 Wave 3 (G2): tier-aware golden variant
    install_recipe: "Any | None" = None,  # InstallRecipe | None (TC-HYBRID-04)
    limitations: "list | None" = None,  # HG-11: list[LimitationEntry] from product_evidence
    api_identifiers: "list[str] | None" = None,  # HG-11: known API class/method tokens
    workflow_examples: "list | None" = None,  # TC-4041: WorkflowExample list from product_evidence
    supported_formats: "dict[str, list[str]] | None" = None,  # TC-4041: {input:[...], output:[...]}
    capabilities: "list[dict] | None" = None,  # TC-HO-04: product_evidence.capabilities
    conversion_pairs: "list[dict] | None" = None,  # TC-HO-05: product_evidence.conversion_pairs
    missing_info: "list | None" = None,  # TC-HO-06: product_evidence.missing_info
    richness_tier_obj: "Any | None" = None,  # TC-HO-08A: RichnessResult from understanding bundle
    claim_context: str = "",  # TC-4219: verified claim texts for LLM grounding (claim_id → text)
    api_facts_by_class: "dict[str, list] | None" = None,  # TC-5162: ApiFact lists keyed by class_name
    evidence_score: "Any | None" = None,  # TC-5161: PageEvidenceScore or dict
    prior_sections_summary: "list[dict] | None" = None,  # GEN-5 (TC-5205): summaries of already-generated sections
) -> str:
    """Build a focused prompt for generating one section.

    Parameters
    ----------
    section:
        The skeleton section being generated.
    section_index:
        Zero-based index of *section* within the page skeleton.
    section_count:
        Total number of sections in the page skeleton.
    page:
        The planned page (carries ``assigned_claims``).
    product:
        Canonical product identity.
    claims:
        Full list of claims from the understanding bundle.
    snippets:
        Full list of snippets from the understanding bundle.
    claim_context:
        TC-4219: Pre-formatted string of verified claim facts assigned to this page
        (one line per claim: "- [CLM-001] claim text"). Injected into the LLM prompt
        so the section writer grounds content in source-verified facts rather than
        world knowledge. Defaults to "" (no injection) for backward compatibility.

    Notes
    -----
    TC-4221: When ``page.page_role == "faq"``, an additional "FAQ writing rules"
    block is appended to the prompt (after ``claim_context``) requiring:
    - minimum 3 complete sentences per answer
    - at least one fenced code block per page
    - no one-sentence answers

    Returns
    -------
    str
        A fully-formatted prompt string ready to send to the LLM.
    """
    # Filter claims assigned to this page
    page_claims = [c for c in claims if c.claim_id in page.assigned_claims]

    # TC-HAL-08: Filter low-confidence claims before distributing to sections
    _orig_page_claims_count = len(page_claims)
    page_claims = [
        c for c in page_claims
        if getattr(c, 'confidence', 1.0) >= _CLAIM_CONFIDENCE_THRESHOLD
    ]
    if len(page_claims) < _orig_page_claims_count:
        logger.debug(
            "section_prompt [TC-HAL-08]: filtered %d low-confidence claims for page %s section %s",
            _orig_page_claims_count - len(page_claims),
            getattr(page, 'slug', 'unknown'),
            getattr(section, 'heading', 'unknown'),
        )

    # Distribute claims across sections (round-robin)
    section_claims = _distribute_claims(page_claims, section_index, section_count)

    # TC-4230: Cap claims per section to prevent finish_reason: length.
    # Pages with many assigned claims (e.g. api-overview with 160+) generate prompts
    # large enough to hit the LLM's max_tokens limit, causing truncated responses.
    if len(section_claims) > _MAX_CLAIMS_PER_SECTION:
        logger.warning(
            "section_prompt [TC-4230]: capping %d claims to %d for section %r (page %r)",
            len(section_claims),
            _MAX_CLAIMS_PER_SECTION,
            getattr(section, "heading", "unknown"),
            getattr(page, "slug", getattr(page, "page_id", "unknown")),
        )
        section_claims = section_claims[:_MAX_CLAIMS_PER_SECTION]

    # Filter snippets linked to section claims, rank by quality, cap at 5
    section_claim_ids = {c.claim_id for c in section_claims}
    section_snippets = _rank_snippets(snippets, section_claim_ids)

    # Prioritize class_briefs based on page claims (AQ-03)
    if class_briefs and page_claims:
        class_briefs = _prioritize_class_briefs(class_briefs, page_claims)

    # Build claims block
    claims_block = _format_claims(section_claims)
    snippets_block = _format_snippets(section_snippets)
    # TC-3882 Wave 4 (Gap2): Pass has_snippets so snippet-permissive message used when available.
    # TC-3882 Wave 4 (Gap6): Extract claim-mentioned classes for deeper API depth.
    _claim_text = " ".join(c.claim_text for c in section_claims if hasattr(c, "claim_text"))
    _claim_mentioned: set[str] = set()
    if _claim_text and public_classes:
        for _cls in public_classes:
            if _cls and _cls in _claim_text:
                _claim_mentioned.add(_cls)
    api_surface_block = _format_api_surface(
        public_classes or [],
        class_briefs=class_briefs,
        has_snippets=bool(section_snippets),
        claim_mentioned_classes=_claim_mentioned,
        enums=_get_top_level_enums(class_briefs),
        api_facts_by_class=api_facts_by_class,  # TC-5162
    )

    # Build SEO keywords block from page-level keywords
    seo_keywords = getattr(page, "seo_keywords", None) or []
    if seo_keywords:
        seo_keywords_block = ", ".join(seo_keywords[:8])
    else:
        seo_keywords_block = "(No specific SEO keywords for this section)"

    # SR-03: guard against duck-typed callers that lack page_role attribute
    _page_role_str = getattr(page, "page_role", "unknown") or "unknown"

    # Build section-type-specific directive
    structure_directive = _get_structure_directive(section.heading, page_role=_page_role_str)

    # Build golden reference block
    # golden_dir may be passed directly (from generate worker) or derived from page.golden
    if golden_dir is None:
        try:
            golden_cfg = getattr(page, "golden", None)
            if golden_cfg is not None and golden_cfg.get("enabled"):
                golden_dir = Path(golden_cfg.get("dir", "golden/"))
        except Exception:
            pass

    # OPT-4: Prune api_surface_block when golden spec has no code requirement (G002)
    if _page_role_str not in _REFERENCE_ROLES and golden_dir is not None:
        try:
            from launcher.shared.golden_loader import GoldenIndex as _GI
            _gi = _GI.load(golden_dir)
            _spec = _gi.get_spec(
                getattr(page, "page_role", "") or "",
                "standard",
                getattr(section, "heading", "") or "",
            )
            if _spec is not None and "code" not in _spec.required_block_types:
                api_surface_block = (
                    "(No code output expected for this section — omit all code blocks)"
                )
        except Exception:
            pass

    # G6: In heal mode with cached section content, use diff-aware golden block.
    _current_section_content: str | None = (heal_metadata or {}).get("_current_section_content")
    if _current_section_content:
        golden_reference_block = _build_heal_golden_block(
            page_role=getattr(page, "page_role", "") or "",
            section_heading=getattr(section, "heading", "") or "",
            golden_dir=golden_dir,
            current_content=_current_section_content,
            variant=variant,
        )
    else:
        golden_reference_block = _build_golden_reference_block(
            page_role=getattr(page, "page_role", "") or "",
            section_heading=getattr(section, "heading", "") or "",
            golden_dir=golden_dir,
            variant=variant,  # TC-3881 Wave 3 (G2): pass tier-aware variant
        )

    heal_directives_block = _build_heal_directives_block(
        heal_metadata=heal_metadata or {},
        section_heading=getattr(section, "heading", "") or "",
    )

    # TC-3876 (W2-S3): Saturation warning — injected when claim density is thin.
    claim_saturation = getattr(page, "claim_saturation", 1.0)
    saturation_warning = ""
    if claim_saturation < 0.5:
        n_claims = len(page_claims)
        n_sections = section_count
        saturation_warning = (
            f"\nSATURATION WARNING: This page has limited claims ({n_claims} claims for "
            f"{n_sections} sections). Write concise factual sections. "
            "Do NOT invent capabilities, features, or API methods not supported by the "
            "claims above.\n"
        )

    # TC-5161: Evidence quality note — injected when page_evidence_index signals insufficient evidence.
    evidence_note = ""
    if evidence_score is not None:
        _ev_sufficient = (
            evidence_score.get("evidence_sufficient", True)
            if isinstance(evidence_score, dict)
            else getattr(evidence_score, "evidence_sufficient", True)
        )
        if not _ev_sufficient:
            _ev_missing = (
                evidence_score.get("missing", [])
                if isinstance(evidence_score, dict)
                else getattr(evidence_score, "missing", [])
            ) or []
            _missing_str = ", ".join(list(_ev_missing)[:3]) or "unspecified"
            evidence_note = (
                f"\nEVIDENCE QUALITY NOTE: This page role ({_page_role_str}) was "
                f"planned with insufficient evidence signals (missing: {_missing_str}). "
                "Write only what is directly verifiable from the claims and API surface "
                "above. Prefer short, factual statements. Do NOT speculate or invent "
                "capabilities not listed in the claims.\n"
            )

    # TC-3902 + TR-01: Evidence-absent instruction — injected only when:
    # 1. No executable snippets are available for this section, AND
    # 2. Either: this role requires code (_CODE_EVIDENCE_ROLES), OR
    #            repo has code_evidence_sparse=True (zero executable examples/snippets)
    # Condition is FALSE for rich repos → zero behavioral change for A-grade repos.
    _no_snippets = not section_snippets
    _code_role = getattr(page, "page_role", "") in _CODE_EVIDENCE_ROLES
    _sparse = getattr(page, "code_evidence_sparse", False)  # TR-01
    if _no_snippets and (_code_role or _sparse):
        skip_instruction = (
            "EVIDENCE ABSENT: The CODE EXAMPLES section below is empty — "
            "no working snippets were extracted from this repository. "
            "Write prose only for this section. "
            "Do NOT generate any fenced code block. "
            "Omit any code block entirely rather than fabricating one.\n\n"
        )
    else:
        skip_instruction = ""

    # TC-3876 (W2-S5): Tier-aware word count targets.
    richness_tier = getattr(page, "richness_tier", "A")
    tier_min, tier_max = _TIER_WORD_COUNTS.get(richness_tier, (150, 500))
    # Section-level overrides take precedence when they are more restrictive than tier defaults.
    effective_min = section.min_words if (section.min_words and section.min_words > 0) else tier_min
    effective_max = section.max_words if (section.max_words and section.max_words > 0) else tier_max
    # Tier C: cap at tier maximum to prevent hollow filler
    if richness_tier == "C":
        effective_max = min(effective_max, tier_max)

    # GEN-5 (TC-5205): Build prior-sections context block to prevent cross-section repetition.
    # Injected into the prompt so the LLM knows what claim_ids and topics were already covered.
    if prior_sections_summary:
        _prior_lines = [
            "PRIOR SECTIONS ALREADY COVERED"
            " (do NOT repeat these topics, claim_ids, or API calls in your output):",
        ]
        for _ps in prior_sections_summary:
            _ps_heading = _ps.get("heading", "")
            _ps_claim_ids = _ps.get("claim_ids", [])
            _ps_topics = _ps.get("topics", [])
            _ps_code = _ps.get("code_patterns", [])
            _parts: list[str] = []
            if _ps_claim_ids:
                _parts.append(f"Claims: {', '.join(_ps_claim_ids[:4])}")
            if _ps_topics:
                _parts.append(f"Topics: {'; '.join(_ps_topics[:2])}")
            if _ps_code:
                _parts.append(f"APIs: {', '.join(_ps_code[:3])}")
            _prior_lines.append(f'- Section "{_ps_heading}": {" | ".join(_parts)}')
        prior_context_block = "\n".join(_prior_lines) + "\n\n"
    else:
        prior_context_block = ""

    # Load and format prompt template
    # TC-GEN-212: code_import = what to write in code; canonical_import = pip package name
    code_import = product.runtime_import or product.canonical_import
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    # TC-5160: Context-aware empty-claims fallback.
    # If claims existed before TC-HAL-08 filtering but were all below the confidence
    # threshold, tell the LLM WHY it received no claims so it stays grounded.
    if not claims_block:
        if _orig_page_claims_count > 0:
            _claims_fallback = (
                "(All claims for this page were below the confidence threshold of 0.50 — "
                "write ONLY from API SURFACE above. Do NOT invent features, methods, or "
                "capabilities not listed. Brevity over fabrication.)"
            )
        else:
            _claims_fallback = (
                "(No specific claims available. Write ONLY a 1-2 sentence overview referencing "
                "the product name and classes from the API SURFACE above. Do NOT invent features, "
                "methods, or capabilities not listed in the API SURFACE. Brevity over fabrication.)"
            )
    else:
        _claims_fallback = claims_block

    # TC-GEN-212: Build platform-aware import convention strings
    _import_statement = _build_import_statement(product.platform, code_import)
    _wrong_import_warning = _build_wrong_import_warning(product.platform, code_import)
    _import_rule_block = _build_import_rule_block(product.platform, code_import)

    result = template.format(
        display_name=product.display_name,
        canonical_import=product.canonical_import,
        code_import=code_import,
        import_statement=_import_statement,
        wrong_import_warning=_wrong_import_warning,
        import_rule_block=_import_rule_block,
        platform=product.platform,
        page_title=page.title,
        page_role=_page_role_str,
        section_heading=section.heading,
        section_index=section_index + 1,
        section_count=section_count,
        content_hint=section.content_hint,
        structure_directive=structure_directive,
        claims_block=_claims_fallback,
        api_surface_block=api_surface_block
        or "(No API surface information available — only reference facts from claims)",
        snippets_block=snippets_block or "(No code examples for this section)",
        seo_keywords_block=seo_keywords_block,
        min_words=effective_min,
        max_words=effective_max,
        lang_tag=get_lang_tag(product.platform),
        golden_reference_block=golden_reference_block,
        heal_directives_block=heal_directives_block,
        skills_block=skills_block,
        skip_instruction=skip_instruction,
        evidence_note=evidence_note,  # TC-5161: injected via template placeholder
        prose_contract_block=_load_prose_contract(_page_role_str),
        prior_context_block=prior_context_block,  # GEN-5 (TC-5205): cross-section context
    )

    # TC-4227 + TC-GEN-212: Platform-aware canonical import reminder at the top.
    # Overrides LLM world-knowledge bias toward commercial import paths.
    _kw = _IMPORT_KEYWORD.get(product.platform, "import")
    if product.platform == "python":
        _wrong_import_example = "aspose.cells" if "aspose" in code_import.lower() else f"import_{code_import.replace('_', '.')}"
        _canonical_reminder = (
            f"CANONICAL IMPORT REMINDER — THIS OVERRIDES YOUR WORLD KNOWLEDGE:\n"
            f"CORRECT:  import {code_import}\n"
            f"WRONG:    import {_wrong_import_example}  \u2190 NEVER write this\n\n"
        )
    elif product.platform == "dotnet":
        _canonical_reminder = (
            f"CANONICAL IMPORT REMINDER — THIS OVERRIDES YOUR WORLD KNOWLEDGE:\n"
            f"CORRECT:  using {code_import};\n"
            f"WRONG:    import {code_import}  \u2190 NEVER write Python-style imports\n\n"
        )
    elif product.platform == "java":
        _canonical_reminder = (
            f"CANONICAL IMPORT REMINDER — THIS OVERRIDES YOUR WORLD KNOWLEDGE:\n"
            f"CORRECT:  import {code_import}.*;\n"
            f"WRONG:    using {code_import}  \u2190 NEVER write .NET-style directives\n\n"
        )
    elif product.platform == "cpp":
        _canonical_reminder = (
            f"CANONICAL IMPORT REMINDER \u2014 THIS OVERRIDES YOUR WORLD KNOWLEDGE:\n"
            f"CORRECT:  using namespace {code_import};\n"
            f"WRONG:    using namespace {code_import}::Foss;  \u2190 NEVER extend the namespace\n"
            f"WRONG:    import {code_import}  \u2190 NEVER write Python-style imports\n\n"
        )
    else:
        _canonical_reminder = (
            f"CANONICAL IMPORT REMINDER:\n"
            f"CORRECT:  {_import_statement}\n\n"
        )
    result = _canonical_reminder + result

    # TC-HYBRID-04: Inject install recipe block for install/getting-started pages.
    # TC-4084: Use install_command (renamed from pip_command) to support multi-platform.
    _install_cmd = getattr(install_recipe, "install_command", "") or getattr(install_recipe, "pip_command", "")
    if install_recipe and _install_cmd and _should_include_install_reference(page):
        _install_block = (
            "\n\n## INSTALL REFERENCE (authoritative — do not deviate)\n"
            "```bash\n" + _install_cmd + "\n```\n"
        )
        if getattr(install_recipe, "verification_code", ""):
            _install_block += (
                f"```{_VERIFICATION_LANG.get(product.platform, 'python')}\n" + install_recipe.verification_code + "\n```\n"
            )
        result = result + _install_block

    # HG-11: Inject known limitations block so LLM does not fabricate absent capabilities.
    _lim_text = _format_limitations(limitations)
    if _lim_text:
        result = result + (
            "\n\nKNOWN LIMITATIONS (source-verified — do NOT contradict these):\n"
            + _lim_text + "\n"
        )

    # TC-4041: Inject real usage patterns so LLM writes specific rather than hedging prose.
    if workflow_examples:
        _wf_lines = ["REAL USAGE PATTERNS (source-verified from repository tests):"]
        for ex in workflow_examples[:3]:  # cap at 3 examples
            _title = getattr(ex, "title", "") or ""
            _lang = getattr(ex, "language", "python") or "python"
            _code = (getattr(ex, "code", "") or "")[:500]  # cap at 500 chars
            _steps = getattr(ex, "steps", []) or []
            if _title:
                _wf_lines.append(f"### {_title}")
            _wf_lines.append(f"```{_lang}")
            _wf_lines.append(_code)
            _wf_lines.append("```")
            if _steps:
                _wf_lines.append("Steps: " + ", ".join(str(s) for s in _steps[:5]))
        result = result + "\n\n" + "\n".join(_wf_lines) + "\n"

    # TC-4041: Inject format matrix for pages where format info is central to the content.
    _page_role = getattr(page, "page_role", "") or ""
    if supported_formats and _page_role in _FORMAT_ELIGIBLE_ROLES:
        _in_fmts = supported_formats.get("input", [])
        _out_fmts = supported_formats.get("output", [])
        if _in_fmts or _out_fmts:
            _fmt_lines = ["SUPPORTED FORMATS (source-verified):"]
            if _in_fmts:
                _fmt_lines.append(f"Input: {', '.join(_in_fmts[:20])}")
            if _out_fmts:
                _fmt_lines.append(f"Output: {', '.join(_out_fmts[:20])}")
            result = result + "\n\n" + "\n".join(_fmt_lines) + "\n"

    # TC-4219: Inject verified claim text so LLM grounds writing in source facts.
    # Injected after format matrix but before API identifier guard, so the LLM
    # sees claim facts as high-priority context before the structural constraints.
    if claim_context:
        result = result + (
            "\n\n## Claims to address\n"
            "The following claims are verified facts about this product that MUST be addressed "
            "in this page. Ground your writing in these facts:\n"
            + claim_context + "\n"
        )

    # TC-4221: Inject FAQ depth constraints so LLM writes substantive answers with code.
    # Only injected when page_role == "faq" — no effect on any other page role.
    if getattr(page, "page_role", "") == "faq":
        result = result + (
            "\n\n## FAQ writing rules\n"
            "- Each answer must contain at least 3 complete sentences of explanation.\n"
            "- The FAQ page must include at least one code example (fenced code block) "
            "showing how to use the product for the most common question.\n"
            "- Do not use one-sentence answers. Every answer must be substantive."
            "\n"
        )

    # HG-11: Inject API class name guard to prevent hallucinated class names.
    _api_ids_guard = _format_api_ids_guard(api_identifiers, product.display_name)
    if _api_ids_guard:
        result = result + "\n\n" + _api_ids_guard + "\n"

    # TC-HO-04: Inject product_evidence.capabilities as explicit capability statements.
    _caps_block = _format_capabilities(capabilities)
    if _caps_block:
        result = result + "\n\n" + _caps_block + "\n"

    # TC-HO-05: Inject conversion pairs for conversion-headed sections.
    _conv_block = _format_conversion_pairs(conversion_pairs, section.heading)
    if _conv_block:
        result = result + "\n\n" + _conv_block + "\n"

    # TC-HO-06: Inject DO NOT CLAIM guard for fields that could not be extracted.
    _missing_block = _format_missing_info(missing_info)
    if _missing_block:
        result = _missing_block + "\n\n" + result

    # TC-HO-08A: Inject REPOSITORY PROFILE block with richness tier context.
    _repo_profile = _format_richness_profile(richness_tier_obj)
    if _repo_profile:
        result = _repo_profile + "\n\n" + result

    # TC-3876 (W2-S3/S5): Inject saturation warning and Tier C evidence constraint.
    # NOTE: evidence_note is injected via {evidence_note} template placeholder (TC-5161/SR-01),
    # not prepended here. saturation_warning is still prepended (no template slot available).
    if saturation_warning:
        result = saturation_warning + result
    if richness_tier == "C":
        result = (
            "EVIDENCE CONSTRAINT: This is a lean repository with limited documentation. "
            "Write concise factual sections. Quality over length. "
            "Do NOT pad to meet word counts.\n\n"
        ) + result

    # Prepend reference preamble for API reference pages (TC-3801)
    if _page_role_str in _REFERENCE_ROLES:
        result = _REFERENCE_PREAMBLE + result

    # FPRSR05SR-01: Intro-quality directive for getting-started pages, introduction
    # section only (section_index == 0). Instructs the LLM to mention the product name
    # in the first paragraph so the intro reads as a proper getting-started guide.
    # NOTE: route_consistency evaluator already skips getting_started pages (_SKIP_ROLES);
    # this directive is for prose quality, not evaluator compliance.
    if section_index == 0 and getattr(page, "page_role", "") == "getting_started":  # TC-5196: canonical form only
        _intro_product_name = product.display_name
        result = result + (
            f"\n\nINTRO QUALITY REQUIREMENT: Your introduction paragraph MUST mention"
            f" '{_intro_product_name}' and use the phrase"
            f" 'getting started with {_intro_product_name}'.\n"
        )
        logger.debug(
            "[SectionPrompt] FPRSR05SR-01: intro-quality directive injected for slug=%s product=%s",
            getattr(page, "slug", "?"),
            _intro_product_name,
        )

    return result


# ---------------------------------------------------------------------------
# TC-FIX-214: Affinity-based claim routing
# ---------------------------------------------------------------------------

_TAG_CLAIM_AFFINITY: dict[str, set[str]] = {
    "faq": {"troubleshoot", "feature", "config"},
    "install": {"config"},
    "methods": {"api"},
    "formats": {"format"},
    "overview": {"feature", "api", "format", "computation"},
    "troubleshooting": {"troubleshoot", "config"},
    "examples": {"api", "feature", "computation"},
    "see_also": set(),
}


def _distribute_claims(
    claims: list[Claim],
    section_idx: int,
    total_sections: int,
    *,
    semantic_tag: str = "",
) -> list[Claim]:
    """Distribute claims across sections with optional affinity routing.

    TC-3879 Wave 1 (Gap1): When fewer claims than sections, return ALL claims to every
    under-provisioned section so each section has full context to write from.

    TC-FIX-214: When *semantic_tag* matches a key in ``_TAG_CLAIM_AFFINITY``,
    filter claims to matching kinds first. Falls back to round-robin if affinity
    yields nothing (starvation guard).

    When claims >= sections and no affinity: round-robin assignment.
    """
    if not claims or total_sections <= 0:
        return []
    if len(claims) < total_sections:
        # All claims to every under-provisioned section — let heading+directive differentiate
        return list(claims)

    # Affinity routing: filter by kind when tag is known
    if semantic_tag and semantic_tag in _TAG_CLAIM_AFFINITY:
        wanted_kinds = _TAG_CLAIM_AFFINITY[semantic_tag]
        if wanted_kinds:
            matched = [c for c in claims if c.kind in wanted_kinds]
            if matched:
                return matched

    # Default: round-robin
    return [c for i, c in enumerate(claims) if i % total_sections == section_idx]


def _confidence_tag(claim: Claim) -> str:
    """Return a short confidence tier tag for a claim.

    TC-5160: Surfaces the TC-HAL-06 confidence tier to the LLM so it can
    distinguish ground-truth docstring claims from heuristic/LLM-inferred ones.

    Tags:
      [AST] — extracted directly from docstring (confidence=1.0, source=docstring)
      [VER] — LLM-verified or multi-source evidence (confidence≥0.75)
      [DET] — deterministic/heuristic extraction (confidence≥0.5)
    """
    src = getattr(claim, "claim_source", "") or ""
    conf = getattr(claim, "confidence", 1.0)
    if src == "docstring" and conf >= 1.0:
        return "[AST]"
    if conf >= 0.75:
        return "[VER]"
    return "[DET]"


def _format_claims(claims: list[Claim]) -> str:
    """Format claims as a bulleted list for the prompt.

    TC-3876 (W2-S2): When a claim has evidence with a non-empty snippet that
    differs from the claim text, emit a Source line anchoring the LLM to real
    source code.  Snippet capped at 150 chars to stay within token budgets.

    TC-5160: Each claim line is prefixed with a confidence tier tag ([AST]/[VER]/[DET])
    so the LLM can prioritise ground-truth docstring claims over heuristic ones.
    """
    lines = []
    for c in claims:
        tag = _confidence_tag(c)
        line = f"- [{c.claim_id}]{tag} ({c.kind}): {c.text}"
        # Emit evidence snippet when non-empty and distinct from claim text
        if c.evidence:
            anchor = c.evidence[0]
            raw_snippet = (anchor.snippet or "").strip()
            if raw_snippet and raw_snippet != c.text.strip():
                snippet = raw_snippet[:150]
                src = anchor.source_file
                if anchor.line_start is not None:
                    src = f"{src}:{anchor.line_start}"
                line += f"\n  Source: {src} → `{snippet}`"
        lines.append(line)
    return "\n".join(lines)


def _build_typed_method_sig(sig: MethodSignature) -> str:
    """Format a MethodSignature as a compact readable string.

    Example: 'load(path: str, options: LoadOptions) -> Scene'
    Falls back to bare name() when parameter/return info is absent.

    TC-HYBRID-07: Provides typed context for LLM to avoid hallucinating
    parameter types and return types.
    """
    params = ", ".join(
        f"{p.name}: {p.type_annotation}" if p.type_annotation else p.name
        for p in sig.parameters
    )
    result = f"{sig.name}({params})"
    if sig.return_type:
        result += f" -> {sig.return_type}"
    if sig.is_static:
        result = f"[static] {result}"
    return result


_API_BLOCK_MAX_CHARS: int = 4000  # ~1000 tokens; hard cap to avoid context overload


def _get_top_level_enums(class_briefs: list[ClassBrief] | None) -> list[EnumRecord]:
    """Collect all unique enums from class_briefs for the top-level enum block.

    Deduplicates by enum name across all class_briefs.
    Returns empty list when class_briefs is None or empty.

    TC-HYBRID-07: Used to inject top-level enum context into section prompts.
    """
    if not class_briefs:
        return []
    seen: set[str] = set()
    result: list[EnumRecord] = []
    for brief in class_briefs:
        for enum in brief.enums:
            if enum.name not in seen:
                seen.add(enum.name)
                result.append(enum)
    return result


def _prioritize_class_briefs(
    class_briefs: list[ClassBrief],
    page_claims: list[Claim],
    cap: int = 15,
) -> list:
    """Reorder class_briefs: claim-mentioned classes first, then rest (AQ-03)."""
    import re
    claim_text = " ".join(c.text for c in page_claims)
    mentioned = [
        b for b in class_briefs
        if re.search(r'\b' + re.escape(b.name) + r'\b', claim_text)
    ]
    mentioned_set = set(id(b) for b in mentioned)
    rest = [b for b in class_briefs if id(b) not in mentioned_set]
    return (mentioned + rest)[:cap]


def _format_api_surface(
    public_classes: list[str],
    class_briefs: list[ClassBrief] | None = None,
    *,
    has_snippets: bool = False,
    claim_mentioned_classes: set[str] | None = None,
    enums: list[EnumRecord] | None = None,
    api_facts_by_class: "dict[str, list] | None" = None,
) -> str:
    """Format API surface as structured lines for the prompt.

    TC-3882 Wave 4 (Gap2): Added has_snippets param. When API surface is empty
    but snippets are available, permit code generation from snippets rather than
    blocking all code entirely (which causes code gate failures for code-required roles).

    TC-3882 Wave 4 (Gap6): claim_mentioned_classes receive deeper API depth
    (methods[:10], properties[:8]) vs default (methods[:5], properties[:5]).

    TC-HYBRID-07: Extended to emit typed method signatures (MethodSignature),
    typed property annotations (PropertyRecord), and enum members (EnumRecord)
    when available. Falls back to plain method/property name lists when typed
    fields are absent (backwards-compatible). Hard cap of _API_BLOCK_MAX_CHARS
    (~1000 tokens) prevents context overload.

    When class_briefs are available (from TC-3816), emit rich context
    with methods, properties, and docstrings. Falls back to bare class
    names when briefs are not available.

    TC-5162: When api_facts_by_class is provided (dict of class_name →
    list[ApiFact]), docstrings from AST-verified api_facts are appended
    inline to matched methods (capped at 80 chars, first 3 methods per
    class only). api_facts_by_class=None preserves pre-TC-5162 behaviour
    exactly.
    """
    if not public_classes and not class_briefs:
        if has_snippets:
            # TC-3882 (Gap2): Snippets available — permit code generation from them.
            return (
                "(No API surface detected. Use ONLY code from the CODE EXAMPLES section "
                "verbatim — do NOT invent class names or method names. You MAY generate "
                "code blocks by adapting the provided examples.)"
            )
        return (
            "(No API surface detected for this product. Do NOT invent any class names, "
            "method names, or property names. Use ONLY code from the CODE EXAMPLES section "
            "verbatim. If no code examples are available for this section, write prose only "
            "— do NOT generate any code blocks.)"
        )

    # Rich mode: use class_briefs for detailed context
    if class_briefs:
        lines = []
        # Build brief lookup
        brief_map = {b.name: b for b in class_briefs}
        _mentioned = claim_mentioned_classes or set()
        # Prioritize classes that have briefs, cap at 15
        shown = 0
        for cls in public_classes:
            if shown >= 15:
                break
            brief = brief_map.get(cls)
            if brief:
                parts = [f"- `{brief.name}`"]
                if brief.docstring_snippet:
                    parts.append(f": {brief.docstring_snippet}")
                # TC-3882 (Gap6): Claim-mentioned classes get deeper depth
                _is_mentioned = cls in _mentioned
                _method_cap = 10 if _is_mentioned else 5
                _prop_cap = 8 if _is_mentioned else 5

                # TC-5162: Build per-class api_facts lookup for docstring enrichment.
                # Only the first 3 methods per class are enriched to limit token overhead.
                _cls_api_facts: dict[str, str] = {}
                if api_facts_by_class:
                    _enrichment_count = 0
                    for _af in api_facts_by_class.get(cls, []):
                        if _enrichment_count >= 3:
                            break
                        _mname = getattr(_af, "member_name", "") or ""
                        _doc = (getattr(_af, "docstring", "") or "").strip()
                        if _mname and _doc:
                            _cls_api_facts[_mname] = _doc[:80]
                            _enrichment_count += 1

                # TC-HYBRID-07: Use typed signatures when available, fall back to plain names
                if brief.typed_methods:
                    sigs = []
                    for m in brief.typed_methods[:_method_cap]:
                        sig_str = _build_typed_method_sig(m)
                        # TC-5162: append docstring if available for this method
                        _doc_note = _cls_api_facts.get(m.name, "")
                        if _doc_note:
                            sig_str += f" [{_doc_note}]"
                        sigs.append(sig_str)
                    parts.append(f"\n  Methods: {', '.join(sigs)}.")
                elif brief.methods:
                    enriched_methods = []
                    for m_name in brief.methods[:_method_cap]:
                        _doc_note = _cls_api_facts.get(m_name, "")
                        enriched_methods.append(f"{m_name} [{_doc_note}]" if _doc_note else m_name)
                    parts.append(f" Methods: {', '.join(enriched_methods)}.")

                # TC-HYBRID-07: Use typed properties when available, fall back to plain names
                if brief.typed_properties:
                    prop_strs = []
                    for p in brief.typed_properties[:_prop_cap]:
                        ps = p.name
                        if p.type_annotation:
                            ps += f": {p.type_annotation}"
                        if p.is_readonly:
                            ps += " (read-only)"
                        prop_strs.append(ps)
                    parts.append(f"\n  Properties: {', '.join(prop_strs)}.")
                elif brief.properties:
                    parts.append(f" Properties: {', '.join(brief.properties[:_prop_cap])}.")

                # TC-HYBRID-07: Include per-class enum members (cap at 3 enums, 8 members each)
                if brief.enums:
                    for enum in brief.enums[:3]:
                        member_names = [m.name for m in enum.members[:8]]
                        if member_names:
                            parts.append(f"\n  Enum {enum.name}: {', '.join(member_names)}.")

                lines.append("".join(parts))
            else:
                lines.append(f"- `{cls}`")
            shown += 1

        # TC-HYBRID-07: Add top-level enums block after class list
        if enums:
            lines.append("")
            lines.append("Top-level enums:")
            for enum in enums[:5]:  # cap at 5 top-level enums
                member_names = [m.name for m in enum.members[:10]]
                if member_names:
                    lines.append(f"  {enum.name}: {', '.join(member_names)}")

        result = "\n".join(lines)
        # TC-HYBRID-07: Hard cap to ~1000 tokens to avoid context overload
        if len(result) > _API_BLOCK_MAX_CHARS:
            result = result[:_API_BLOCK_MAX_CHARS] + "\n  ... (API surface truncated)"
        return result

    # Fallback: bare class names
    classes = public_classes[:30]
    return "Known classes: " + ", ".join(f"`{c}`" for c in classes)


def _build_heal_directives_block(
    heal_metadata: dict,
    section_heading: str,
) -> str:
    """Return a formatted heal directives block for the section prompt.

    Returns empty string when heal_metadata is empty (normal generation mode).
    """
    if not heal_metadata:
        return ""
    directives: list[str] = []
    # Page-level directives (apply to every section)
    page_directives = heal_metadata.get("page_directives") or []
    directives.extend(str(d) for d in page_directives)
    # Section-specific directives (keyed by heading)
    section_directives_map = heal_metadata.get("section_directives") or {}
    section_specific = section_directives_map.get(section_heading) or []
    directives.extend(str(d) for d in section_specific)
    if not directives:
        return ""
    lines = "\n".join(f"- {d}" for d in directives)
    return (
        "\n## HEAL DIRECTIVES\n"
        "The previous generation had quality issues. Apply these specific corrections:\n\n"
        f"{lines}\n"
        "## END HEAL DIRECTIVES\n"
    )


def _build_golden_reference_block(
    page_role: str,
    section_heading: str,
    golden_dir: "Path | None",
    *,
    variant: str = "standard",
) -> str:
    """Return a formatted golden reference block for the section prompt.

    TC-3881 Wave 3 (G1/G2): Now injects a structural fingerprint (block sequence,
    counts) before the excerpt so the LLM receives binding structural guidance,
    not just a raw excerpt with a vague "match structure" instruction.

    Returns empty string when golden reference is unavailable.
    """
    if golden_dir is None:
        return ""
    try:
        gdir = Path(golden_dir) if not isinstance(golden_dir, Path) else golden_dir
        if not gdir.exists():
            return ""
        from launcher.shared.golden_loader import (
            _load_golden_for_role,
            _load_golden_section_for_role,
            _summarize_section_structure,
        )
        # TC-3881 Wave 3 (G1): Load section for structural fingerprint.
        section = _load_golden_section_for_role(page_role, gdir, section_heading, variant=variant)
        excerpt = _load_golden_for_role(page_role, gdir, section_heading, variant=variant)
        if not excerpt:
            return ""
        # Build structural fingerprint block
        fingerprint = ""
        if section is not None:
            fingerprint = _summarize_section_structure(section) + "\n\n"
        return (
            "\n## GOLDEN REFERENCE EXAMPLE\n"
            "The following is an A-grade example of this section type.\n"
            "Use its structural elements as a MINIMUM guide — include all listed "
            "block types and expand with additional content to fully cover the topic:\n\n"
            f"{fingerprint}"
            f"--- EXAMPLE ---\n{excerpt}\n--- END EXAMPLE ---\n"
            "## END GOLDEN REFERENCE\n"
        )
    except Exception:
        return ""


def _build_heal_golden_block(
    page_role: str,
    section_heading: str,
    golden_dir: "Path | None",
    current_content: str,
    *,
    variant: str = "standard",
) -> str:
    """Return a diff-aware golden block for heal re-generation.

    TC-3882 Wave 4 (G6): In heal mode, the LLM receives:
    Part 1 — "YOUR PREVIOUS OUTPUT" (what the section currently contains)
    Part 2 — Golden structural fingerprint (what it should contain)
    Part 3 — Gap list (block types in golden but missing in previous output)

    This gives the LLM clear visibility into what to improve, unlike standard
    golden injection which only shows the target without showing what's wrong.
    """
    try:
        # Part 1: Previous output excerpt
        prev_excerpt = current_content[:500].strip()

        # Part 2+3: Try to get golden reference for fingerprint + gap list
        if golden_dir is not None:
            gdir = Path(golden_dir) if not isinstance(golden_dir, Path) else golden_dir
            if gdir.exists():
                from launcher.shared.golden_loader import (
                    _load_golden_for_role,
                    _load_golden_section_for_role,
                    _summarize_section_structure,
                )
                section = _load_golden_section_for_role(
                    page_role, gdir, section_heading, variant=variant
                )
                excerpt = _load_golden_for_role(
                    page_role, gdir, section_heading, variant=variant
                )

                # Build gap list: block types in golden but absent in current output
                gap_list = ""
                if section is not None:
                    golden_has_code = getattr(section, "code_block_count", 0) > 0
                    golden_has_list = getattr(section, "list_block_count", 0) > 0
                    golden_has_table = getattr(section, "table_count", 0) > 0
                    has_code_fence = "```" in current_content
                    has_list = "\n- " in current_content or "\n* " in current_content or "\n1." in current_content
                    has_table = "|" in current_content and "---" in current_content
                    gaps = []
                    if golden_has_code and not has_code_fence:
                        gaps.append("code block(s)")
                    if golden_has_list and not has_list:
                        gaps.append("bulleted/numbered list")
                    if golden_has_table and not has_table:
                        gaps.append("markdown table")
                    if gaps:
                        gap_list = f"\nGAPS (present in golden but absent in your previous output): {', '.join(gaps)}\n"

                    fingerprint = _summarize_section_structure(section)
                    if excerpt:
                        return (
                            "\n## HEAL CONTEXT\n"
                            "YOUR PREVIOUS OUTPUT (what you wrote last time — identify and fix gaps):\n"
                            f"```\n{prev_excerpt}\n```\n\n"
                            f"TARGET STRUCTURE:\n{fingerprint}\n"
                            f"{gap_list}"
                            f"--- GOLDEN EXAMPLE ---\n{excerpt[:500]}\n--- END GOLDEN EXAMPLE ---\n"
                            "## END HEAL CONTEXT\n"
                        )

        # Fallback: just show previous output without golden
        return (
            "\n## HEAL CONTEXT\n"
            "YOUR PREVIOUS OUTPUT (what you wrote last time — improve this):\n"
            f"```\n{prev_excerpt}\n```\n"
            "## END HEAL CONTEXT\n"
        )
    except Exception:
        return ""


_ARTIFACT_LINE_PREFIXES: tuple[str, ...] = (
    "*/",             # C/C++ block-comment close
    "using namespace",  # C++ namespace directive
    "System.",        # C# framework artifact
)


def _sanitize_snippet_code(code: str) -> str:
    """Strip HTML entities and cross-language artifacts from snippet code.

    TC-4035: snippets extracted from multi-language repos may carry HTML
    entities (&reg;, &trade;) or C/C#/C++ artifacts that do not belong in
    Python or TypeScript output.
    """
    import html as _html_mod
    code = _html_mod.unescape(code)
    lines = [ln for ln in code.splitlines() if not ln.lstrip().startswith(_ARTIFACT_LINE_PREFIXES)]
    return "\n".join(lines)


def _snippet_provenance_line(snippet: "Any") -> str:
    """Return a one-line provenance label for a snippet.

    TC-5165: Disclosed to LLM so it knows whether code is from the actual
    repository or was synthetically generated.
    """
    source_type = (getattr(snippet, "source_type", "") or "").lower()
    source_file = getattr(snippet, "source_file", "") or ""

    if source_type == "extracted" and source_file:
        # Show last 2 path components to keep it concise
        parts = source_file.replace("\\", "/").split("/")
        short_path = "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]
        return f"[Extracted from: {short_path}]"
    elif source_type in ("generated", "synthetic") or not source_type:
        return "[Generated — treat as illustrative only, validate before use]"
    else:
        return f"[Source: {source_type}]"


def _format_snippets(snippets: list[Snippet]) -> str:
    """Format snippets as fenced code blocks for the prompt.

    TC-5165: Each snippet is preceded by a one-line provenance label so the LLM
    knows whether the code came from the actual repository or was synthetically
    generated.
    """
    parts = []
    for s in snippets:
        claims_str = ", ".join(s.claim_ids) if s.claim_ids else "general"
        clean_code = _sanitize_snippet_code(s.code)
        provenance = _snippet_provenance_line(s)
        parts.append(f"{provenance}\n```{s.language}\n# Claims: {claims_str}\n{clean_code}\n```")
    return "\n\n".join(parts)
