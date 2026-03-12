"""Narrative extraction helpers: tutorial, use-case, and code step decomposition.

Ported from the v1 orphan (src/launcher/shared/extract_claims.py) for v2.
All functions return dicts with ``'path'`` and ``'content'`` keys compatible
with the doc_contexts format used by ``_build_doc_contexts()``.

Submodule of workers/understand/extract — no internal package deps (leaf node).
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_CLAIM_TEXT_LENGTH_EXTRACT = 500  # Characters

_MULTI_STMT_RE = re.compile(
    r'(?:^|\n)\s*(?:\w+\s*=\s*\w+|print\s*\(|assert\s+\w+|raise\s+\w+)',
    re.MULTILINE,
)

# ---------------------------------------------------------------------------
# Prose / code detection helpers
# ---------------------------------------------------------------------------


def _is_parameter_description(text: str) -> bool:
    """Detect function/method parameter descriptions."""
    stripped = text.strip()
    if re.match(r'^\w+\s*\((?:int|str|bool|float|list|dict|tuple|None|Any|Optional|object)\b[^)]*\)\s*:', stripped):
        return True
    if re.match(r'^\w+\s*\([A-Z]\w+\)\s*:', stripped):
        return True
    if re.match(r'^[A-Z]_\w+\s+if\s+', stripped):
        return True
    return False


def _is_code_like(text: str) -> bool:
    """Detect if text is source code rather than natural language."""
    if len(_MULTI_STMT_RE.findall(text)) >= 2:
        return True
    code_indicators = [
        r'\bdef\s+\w+\(',
        r'\bclass\s+\w+[:\(]',
        r'\bimport\s+\w+',
        r'\bself\.\w+',
        r'\breturn\b',
        r'\bassert\w*\(',
        r'\braise\s+\w+',
        r'^\s*#\s',
        r'\w+\.\w+\(\)',
        r'\bNotImplementedError\b',
        r'@\w+',
        r'->\s*[\'\"A-Z]',
        r'\bif\s+\w+\s+is\s+(not\s+)?None',
        r'\bfor\s+\w+\s+in\s+',
        r'\bwhile\s+\w+',
        r'\btry\s*:',
        r'\bexcept\s+\w+',
        r'\w+\s*=\s*\w+\.\w+\s+if\s+',
        r'\b\w+\s*=\s*\w+',
        r'^""".*"""$',
        r"^'''.*'''$",
        r'^\s*"""',
        r"^\s*'''",
        r'^(int|str|bool|float|list|dict|tuple|None):\s',
        r'->\s*(int|str|bool|float|list|dict|tuple|None)\b',
    ]
    matches = sum(1 for p in code_indicators if re.search(p, text))
    threshold = 2 if len(text.split()) <= 8 else 3
    if matches >= threshold:
        return True
    stripped = text.strip()
    if re.match(r'^(from\s+\S+\s+)?import\s+', stripped):
        return True
    if re.match(r'^class\s+\w+.*:', stripped):
        return True
    if re.match(r'^def\s+\w+\s*\(', stripped):
        return True
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return True
    if re.match(r'^(int|str|bool|float|list|dict|tuple|None):\s', stripped):
        return True
    if _is_parameter_description(stripped):
        return True
    if re.match(r'^raise\s+\w+\s*\(', stripped):
        return True
    if re.match(r'^\w+(Error|Exception)\s*\(', stripped):
        return True
    non_alpha = sum(1 for c in text if not c.isalpha() and not c.isspace())
    if len(text) > 20 and non_alpha / len(text) > 0.25:
        return True
    return False


def _is_prose_like(text: str) -> bool:
    """Check if text reads like natural language prose."""
    words = text.split()
    if len(words) < 3:
        return False
    common_verbs = {
        'is', 'are', 'was', 'were', 'has', 'have', 'can', 'will',
        'should', 'may', 'does', 'do', 'provides', 'supports',
        'allows', 'enables', 'requires', 'includes', 'uses',
        'creates', 'returns', 'takes', 'handles', 'processes',
        'implements', 'defines', 'contains', 'specifies', 'represents',
        'offers', 'generates', 'converts', 'exports', 'imports',
        'reads', 'writes', 'loads', 'saves', 'parses',
        'manages', 'transforms', 'validates', 'configures', 'initializes',
        'renders', 'extracts', 'builds', 'computes', 'runs',
    }
    text_lower = text.lower()
    cleaned = text_lower
    for idiom in [' is not none', ' is none', ' is not ', ' is true', ' is false']:
        cleaned = cleaned.replace(idiom, ' ')
    has_verb = any(f' {v} ' in f' {cleaned} ' for v in common_verbs)
    if not has_verb:
        return False
    if text.lstrip().startswith((
        'from ', 'import ', 'def ', 'class ', '{', '[', 'self.', 'raise ', '@',
        'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except ', 'return ',
        'yield ', 'with ', 'async ',
    )):
        return False
    if re.search(r'\braise\s+\w+\(', text):
        return False
    return True


# ---------------------------------------------------------------------------
# Ported narrative extractors
# ---------------------------------------------------------------------------


def _decompose_code_block_into_steps(
    code_lines: list[str],
    section_heading: str,
    section_kind: str,
    product_name: str,
) -> list[dict[str, Any]]:
    """Decompose code block into per-statement educational steps.

    Ported from src/launcher/shared/extract_claims.py for v2.
    Creates one step per logical statement (import, instantiation, method call, save)
    with educational context explaining purpose.
    """
    import ast as ast_mod

    code_text = "\n".join(code_lines)
    steps: list[dict[str, Any]] = []
    step_order = 1

    try:
        tree = ast_mod.parse(code_text)
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.ImportFrom):
                module = node.module or ""
                module_short = module.split('.')[-1] if module else ""
                names = [a.name for a in node.names[:3]]
                if names:
                    claim_text = f"Import {', '.join(names)} from {module_short} to access {product_name} functionality"
                    steps.append({
                        'claim_text': claim_text,
                        'step_order': step_order,
                        'action_type': 'import',
                    })
                    step_order += 1

            elif isinstance(node, ast_mod.Import):
                for alias in node.names:
                    module_short = alias.name.split('.')[-1]
                    claim_text = f"Import {module_short} module"
                    steps.append({
                        'claim_text': claim_text,
                        'step_order': step_order,
                        'action_type': 'import',
                    })
                    step_order += 1

            elif isinstance(node, ast_mod.Assign):
                if isinstance(node.value, ast_mod.Call):
                    if isinstance(node.value.func, ast_mod.Name):
                        class_name = node.value.func.id
                        claim_text = f"Create a {class_name} instance to work with {product_name}"
                        steps.append({
                            'claim_text': claim_text,
                            'step_order': step_order,
                            'action_type': 'instantiate',
                        })
                        step_order += 1

            elif isinstance(node, ast_mod.Expr) and isinstance(node.value, ast_mod.Call):
                if isinstance(node.value.func, ast_mod.Attribute):
                    method_name = node.value.func.attr
                    if 'save' in method_name.lower():
                        claim_text = f"Save the result using {method_name}() method"
                    elif 'load' in method_name.lower() or 'open' in method_name.lower():
                        claim_text = f"Load data using {method_name}() method"
                    elif 'process' in method_name.lower() or 'convert' in method_name.lower():
                        claim_text = f"Process content using {method_name}() method"
                    else:
                        claim_text = f"Call {method_name}() to perform operation"

                    steps.append({
                        'claim_text': claim_text,
                        'step_order': step_order,
                        'action_type': 'method_call',
                    })
                    step_order += 1

    except SyntaxError:
        pass

    return steps


def _extract_use_case_narratives(
    text: str,
    source_file: str,
) -> list[dict[str, Any]]:
    """Extract use case narratives from README sections.

    Ported from src/launcher/shared/extract_claims.py for v2.
    Adapted signature: removed v1-specific params (section_heading, section_start,
    section_end, source_type) not needed for v2 context enrichment.

    Returns list of dicts with 'path' and 'content' keys matching doc_contexts format.
    """
    use_cases: list[dict[str, Any]] = []

    # Strategy 1: Bullet list pattern with optional bold markers
    bullet_pattern = r'^[-*]\s+(?:\*\*)?([^:*]+?)(?:\*\*)?\s*:\s+(.+)$'
    lines = text.split('\n')

    for line in lines:
        stripped = line.strip()
        match = re.match(bullet_pattern, stripped)
        if match:
            use_case_name = match.group(1).strip()
            description = match.group(2).strip()
            if len(description.split()) >= 20:
                use_cases.append({
                    "path": source_file,
                    "content": f"{use_case_name}: {description}",
                })

    # Strategy 2: Narrative paragraphs (20+ words)
    paragraphs = text.split('\n\n')
    for para in paragraphs:
        para_clean = para.strip()
        word_count = len(para_clean.split())
        if word_count >= 20 and not para_clean.startswith(('#', '-', '*')):
            if not _is_code_like(para_clean) and _is_prose_like(para_clean):
                if len(para_clean) > _MAX_CLAIM_TEXT_LENGTH_EXTRACT:
                    para_clean = para_clean[:_MAX_CLAIM_TEXT_LENGTH_EXTRACT - 3] + "..."
                use_cases.append({
                    "path": source_file,
                    "content": para_clean,
                })

    return use_cases


_PYTHON_FENCE_RE: re.Pattern[str] = re.compile(r'```(?:python|py)\s*([\s\S]+?)```', re.IGNORECASE)


def _extract_tutorial_narratives(
    text: str,
    source_file: str,
) -> list[dict[str, Any]]:
    """Extract tutorial narratives preserving prose + code structure.

    Ported from src/launcher/shared/extract_claims.py for v2.
    Adapted signature: removed v1-specific params not needed for v2 context enrichment.

    Tutorials have educational flow with both prose and code.
    Minimum: 30+ words of prose AND code block present.

    Returns list of dicts with 'path' and 'content' keys matching doc_contexts format.
    Also decomposes python code blocks into per-step educational narratives.
    """
    tutorials: list[dict[str, Any]] = []

    code_fence_pattern = r'```[\s\S]+?```'
    parts = re.split(code_fence_pattern, text)
    code_blocks = re.findall(code_fence_pattern, text)

    if not code_blocks:
        return []

    prose_blocks = []
    total_prose_words = 0

    for part in parts:
        part_clean = part.strip()
        lines = part_clean.split('\n')
        prose_lines = [line for line in lines if not line.strip().startswith('#')]
        prose_only = '\n'.join(prose_lines).strip()

        if prose_only and _is_prose_like(prose_only):
            word_count = len(prose_only.split())
            prose_blocks.append(prose_only)
            total_prose_words += word_count

    if total_prose_words < 30 or not prose_blocks:
        return []

    tutorial_text = ""
    summary_blocks = prose_blocks[:2]
    for block in summary_blocks:
        if len(block) > 200:
            block = block[:197] + "..."
        tutorial_text += block + " "

    tutorial_text += f"(includes {len(code_blocks)} code example{'s' if len(code_blocks) > 1 else ''})"

    if len(tutorial_text) > _MAX_CLAIM_TEXT_LENGTH_EXTRACT:
        tutorial_text = tutorial_text[:_MAX_CLAIM_TEXT_LENGTH_EXTRACT - 3] + "..."

    tutorials.append({
        "path": source_file,
        "content": tutorial_text,
    })

    # Decompose each python code block into educational step narratives
    for py_match in _PYTHON_FENCE_RE.finditer(text):
        code_body = py_match.group(1)
        code_lines = code_body.splitlines()
        try:
            steps = _decompose_code_block_into_steps(
                code_lines, section_heading="tutorial", section_kind="example",
                product_name="the library",
            )
            for step in steps:
                claim_text = step.get("claim_text", "")
                if claim_text and len(claim_text) >= 20:
                    tutorials.append({"path": source_file, "content": claim_text})
            if steps:
                logger.debug("decomposed_steps=%d from %s", len(steps), source_file)
        except Exception:
            logger.warning("_decompose_code_block_into_steps failed for %s", source_file, exc_info=True)

    return tutorials
