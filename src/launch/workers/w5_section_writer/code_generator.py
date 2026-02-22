"""Dedicated code generation pass for W5 SectionWriter.

Reference: content-generator src/agents/code/code_generation.py
Generates code blocks separately from prose with API-only context.
"""
from __future__ import annotations
import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CodeBlock:
    label: str           # e.g. "Installation", "Basic Usage"
    language: str        # e.g. "python", "csharp"
    code: str
    explanation: str     # Filled by prose pass
    api_refs_used: List[str] = field(default_factory=list)
    is_valid: bool = True
    validation_issues: List[str] = field(default_factory=list)


def generate_code_block(
    section_title: str,
    api_context: List[str],   # API signatures from product_facts / snippets
    llm_client,
    language: str = "",
    temperature: float = 0.05,  # Lower than prose — code must be deterministic
) -> CodeBlock:
    """Generate a single code block with API-only context.

    Reference: content-generator code_generation.py:44
    """
    if not language:
        language = _infer_language(api_context)

    api_ctx_text = "\n".join(api_context[:20]) if api_context else "(no API context available)"

    prompt = (
        f"Write a self-contained {language} code example for: {section_title}\n\n"
        f"Available API (use ONLY these classes and methods):\n{api_ctx_text}\n\n"
        f"Requirements:\n"
        f"- ONLY use classes and methods listed above — do NOT invent APIs\n"
        f"- Complete, runnable example\n"
        f"- Include necessary imports and initialization\n"
        f"- Add inline comments for key lines\n"
        f"- Do NOT add explanatory prose — code only\n"
        f"Output: raw code block with language tag, nothing else."
    )

    try:
        response = llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            call_id=f"codegen_{section_title[:30]}",
            temperature=temperature,
            max_tokens=800,
        )
        raw = response.get("content", "")
    except Exception as e:
        logger.warning("code_generator_llm_fail section=%s error=%s", section_title, e)
        raw = f"```{language}\n# TODO: Add {language} example for {section_title}\n```"

    code, detected_lang = _extract_code_and_lang(raw, language)
    issues = _validate_code_static(code, api_context)

    return CodeBlock(
        label=section_title,
        language=detected_lang,
        code=code,
        explanation="",
        api_refs_used=_extract_api_refs_used(code, api_context),
        is_valid=not any(i["type"] == "critical" for i in issues),
        validation_issues=[i["message"] for i in issues],
    )


def normalize_assembled_content(content: str) -> str:
    """Post-assembly normalization: deduplicate headings + normalize fence language tags.

    Reference: content-generator content_assembly.py:512,523
    """
    # 1. Heading deduplication: remove consecutive duplicate ## or ### headings.
    # Allow optional blank lines between duplicates (e.g. ## Foo\n\n## Foo\n\n## Foo).
    content = re.sub(r'(#{2,3} [^\n]+)\n(\n*\1\n)+', r'\1\n', content)

    # 2. Infer language if missing from code fence (detect Python/C# markers)
    def _infer_fence_lang(m):
        lang = (m.group(1) or "").strip()
        code = m.group(2)
        if lang:
            return m.group(0)  # Already has a language tag
        if "using Aspose" in code or "namespace " in code or "Install-Package" in code:
            return f"```csharp\n{code}```"
        if "import " in code or "def " in code or "pip install" in code:
            return f"```python\n{code}```"
        return m.group(0)  # Leave as-is

    content = re.sub(r'```(\w*)?\n(.*?)```', _infer_fence_lang, content, flags=re.DOTALL)
    return content


def _validate_code_static(code: str, api_refs: List[str]) -> List[dict]:
    """Static validation: bracket balance, no placeholders, API compliance.

    Reference: content-generator code_validation.py:51
    """
    issues = []
    if code.count("(") != code.count(")"):
        issues.append({"type": "critical", "message": "Unbalanced parentheses in code"})
    if any(marker in code for marker in ["TODO", "YOUR_CODE", "...", "PLACEHOLDER"]):
        issues.append({"type": "critical", "message": "Placeholder text found in generated code"})
    if not api_refs:
        return issues  # No API refs to check against
    # Check that at least one API method from context appears in the code
    method_names = [r.split("(")[0].split(".")[-1] for r in api_refs if "." in r]
    if method_names and not any(m in code for m in method_names):
        issues.append({"type": "minor", "message": "No API methods from context found in code"})
    return issues


def _infer_language(api_context: List[str]) -> str:
    """Infer programming language from API context strings."""
    text = " ".join(api_context)
    if "using " in text or "namespace " in text or "Install-Package" in text:
        return "csharp"
    return "python"  # Default to Python


def _extract_code_and_lang(raw: str, default_lang: str = "python") -> tuple:
    """Extract code content and language from LLM response."""
    m = re.search(r"```(\w+)?\n(.*?)```", raw, re.DOTALL)
    if m:
        lang = m.group(1) or default_lang
        return m.group(2).strip(), lang
    # No fence — treat entire response as code
    return raw.strip(), default_lang


def _extract_api_refs_used(code: str, api_refs: List[str]) -> List[str]:
    """Return which API refs from context appear in the generated code."""
    return [r for r in api_refs if r.split("(")[0].split(".")[-1] in code]
