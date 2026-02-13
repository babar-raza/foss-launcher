"""TC-411: Extract claims from product documentation.

This module implements claims extraction from product repositories per
specs/03_product_facts_and_evidence.md and specs/04_claims_compiler_truth_lock.md.

Claims are atomic statements about capabilities, limitations, workflows, etc.,
each backed by citations from the repository.

Spec references:
- specs/03_product_facts_and_evidence.md (Claims extraction algorithm)
- specs/04_claims_compiler_truth_lock.md (Claim structure and ID generation)
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/10_determinism_and_caching.md (Stable ordering and determinism)

TC-411: W2.1 Extract claims from product repo
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...clients.llm_provider import LLMProviderClient, LLMError
from ...io.atomic import atomic_write_json
from ...io.run_layout import RunLayout
from ...util.logging import get_logger

logger = get_logger()


class ClaimsExtractionError(Exception):
    """Raised when claims extraction fails."""
    pass


class ClaimsValidationError(Exception):
    """Raised when claim validation fails."""
    pass


def normalize_claim_text(claim_text: str, product_name: str) -> str:
    """Normalize claim text for stable claim_id generation.

    Normalization rules per specs/04_claims_compiler_truth_lock.md:15-19:
    - Trim whitespace
    - Collapse whitespace to single spaces
    - Lowercase
    - Replace product_name with {product_name} token

    Args:
        claim_text: Raw claim text
        product_name: Product name to tokenize

    Returns:
        Normalized claim text

    Spec: specs/04_claims_compiler_truth_lock.md:15-19
    """
    # Trim
    text = claim_text.strip()

    # Collapse whitespace to single spaces
    text = re.sub(r'\s+', ' ', text)

    # Lowercase
    text = text.lower()

    # Replace product_name with token (case-insensitive)
    text = re.sub(
        re.escape(product_name.lower()),
        '{product_name}',
        text,
        flags=re.IGNORECASE
    )

    return text


def compute_claim_id(claim_text: str, claim_kind: str, product_name: str) -> str:
    """Compute stable claim_id from normalized claim text and kind.

    Per specs/04_claims_compiler_truth_lock.md:12-19:
    claim_id = sha256(normalize(claim_text) + "|" + claim_kind)

    Args:
        claim_text: Raw claim text
        claim_kind: Claim kind (feature, workflow, format, etc.)
        product_name: Product name for normalization

    Returns:
        SHA256 hash (hex string)

    Spec: specs/04_claims_compiler_truth_lock.md:12-19
    """
    normalized = normalize_claim_text(claim_text, product_name)
    claim_input = f"{normalized}|{claim_kind}"
    return hashlib.sha256(claim_input.encode('utf-8')).hexdigest()


def classify_claim_kind(claim_text: str) -> str:
    """Classify claim kind based on text patterns.

    Per specs/04_claims_compiler_truth_lock.md:35-46:
    - Feature claims: "supports X", "can Y", "enables Z"
    - Workflow claims: "install via X", "usage: Y"
    - Format claims: "reads/writes X format"
    - API claims: "provides X class/function"
    - Limitation claims: "does not support X", "not yet implemented"

    Args:
        claim_text: Claim text

    Returns:
        Claim kind string

    Spec: specs/04_claims_compiler_truth_lock.md:35-46
    """
    text_lower = claim_text.lower()

    # Limitation patterns (check first - most specific)
    if any(pattern in text_lower for pattern in [
        'does not support',
        "doesn't support",
        'does not',
        'not supported',
        'not yet implemented',
        'not implemented',
        'cannot',
        'limitation',
        'unsupported',
        'no support',
        'deprecated',
        'experimental',
        'beta ',
        'limited to',
        'only supports',
        'partial support',
        'not recommended',
        'restricted',
        'not available',
    ]):
        return 'limitation'

    # Compatibility / version patterns (check before workflow — more specific)
    if any(pattern in text_lower for pattern in [
        'python 3', 'python 2', 'python version',
        'requires python', 'compatible with',
        'works with', 'tested on', 'supported on',
        'operating system', 'os support',
        '.net framework', 'java version', 'node version',
    ]):
        return 'compatibility'

    # Install/workflow patterns (check before format - more specific)
    if any(pattern in text_lower for pattern in [
        'install',
        'setup',
        'usage:',
        'how to',
        'getting started',
        'pip install',
        'npm install',
        'maven',
        'nuget',
        'run ',
        'execute',
        'activate',
        'build from source',
        'clone ',
        'download ',
        'requirements',
        'dependency',
        'configure ',
        'step 1',
        'step 2',
        'then ',
        'first,',
        'to begin',
        'quickstart',
        'tutorial',
    ]):
        return 'workflow'

    # API patterns (high priority - very specific)
    # Check for "API includes/provides X" or "X class/function/method"
    api_strong_patterns = [
        'api includes',
        'api provides',
        'class for',
        'class that',
        'function exports',
        'function imports',
        'function for',
        'method for',
    ]
    if any(pattern in text_lower for pattern in api_strong_patterns):
        return 'api'

    # Check for general API markers without format context
    if any(pattern in text_lower for pattern in ['class', 'function', 'method', 'interface']):
        # Only API if NOT talking about file formats
        if not any(fmt_marker in text_lower for fmt_marker in ['format', 'file type', 'reads', 'writes']):
            return 'api'

    # Format patterns (specific file operations)
    if any(pattern in text_lower for pattern in [
        'reads',
        'writes',
        'file type',
    ]):
        return 'format'

    # "provides" can be API or feature depending on context
    if 'provides' in text_lower:
        if any(marker in text_lower for marker in ['class', 'function', 'method', 'api']):
            # Check if it's about API or formats
            if 'format' not in text_lower:
                return 'api'
        elif 'format' in text_lower:
            return 'format'
        else:
            return 'feature'

    # Import/export are usually format-related, but check context
    if any(pattern in text_lower for pattern in ['import', 'export']):
        # If talking about models/files/formats, it's format-related
        if any(marker in text_lower for marker in ['model', 'file', 'format', 'fbx', 'obj', 'stl']):
            return 'format'
        # If talking about code modules, it's feature
        if 'module' in text_lower or 'package' in text_lower:
            return 'feature'
        # Default for import/export is format
        return 'format'

    # Generic "format" or "supports X formats"
    if 'format' in text_lower:
        # "supports X format" or "X format supported" with specific format -> format
        if any(marker in text_lower for marker in ['obj', 'stl', 'fbx', 'pdf', 'file']):
            return 'format'
        # "supports multiple/various formats" or "3d formats" (generic) -> feature
        if any(marker in text_lower for marker in ['multiple', 'various', 'many', '3d']):
            return 'feature'
        # Default when "format" appears but unclear -> format
        return 'format'

    # Default: feature
    return 'feature'


def determine_source_type(file_path: Path, repo_dir: Path) -> str:
    """Determine source type based on file path.

    Per specs/03_product_facts_and_evidence.md:117-128:
    Priority ranking: manifest > source_code > test > implementation_doc >
                      api_doc > readme_technical > readme_marketing

    Args:
        file_path: File path
        repo_dir: Repository root directory

    Returns:
        Source type string

    Spec: specs/03_product_facts_and_evidence.md:117-128
    """
    path_lower = str(file_path).lower()

    # Compute relative path for pattern matching
    try:
        if file_path.is_absolute() and repo_dir.resolve() in file_path.resolve().parents:
            rel_path = file_path.relative_to(repo_dir)
        else:
            rel_path = file_path
    except (ValueError, OSError):
        rel_path = file_path

    rel_path_str = str(rel_path).lower().replace('\\', '/')

    # Meta/build instruction files (not product docs)
    if any(marker in rel_path_str for marker in [
        'agents.md', '.claude/', 'claude.md', '.github/',
        'contributing.md', 'code_of_conduct',
    ]):
        return 'meta'

    # Manifest files
    if any(name in rel_path_str for name in [
        'pyproject.toml', 'setup.py', 'package.json',
        'pom.xml', '*.csproj', 'cargo.toml', 'go.mod'
    ]):
        return 'manifest'

    # Source code (non-test .py, .js, .java, etc. in src/)
    if 'src/' in rel_path_str or 'lib/' in rel_path_str:
        if not any(test_marker in rel_path_str for test_marker in ['test', 'spec', '__pycache__']):
            return 'source_code'

    # Tests
    if any(marker in rel_path_str for marker in ['test', 'tests', 'spec', 'specs', '__tests__']):
        return 'test'

    # Implementation docs
    if any(marker in rel_path_str for marker in [
        'implementation', 'architecture', 'design', 'adr', 'tech'
    ]):
        return 'implementation_doc'

    # API docs (docstrings, API reference)
    if any(marker in rel_path_str for marker in ['api', 'reference', 'docs/api']):
        return 'api_doc'

    # README (distinguish technical from marketing)
    if 'readme' in path_lower:
        # Technical sections usually have code/install/usage
        try:
            if file_path.exists():
                content_preview = file_path.read_text(encoding='utf-8', errors='ignore')[:1000]
                if any(marker in content_preview.lower() for marker in [
                    'install', 'usage', 'api', 'import', 'pip install', 'npm install'
                ]):
                    return 'readme_technical'
                else:
                    return 'readme_marketing'
        except (OSError, FileNotFoundError):
            pass
        return 'readme_technical'

    # Default: readme_technical (general documentation)
    return 'readme_technical'


def determine_source_priority(source_type: str) -> int:
    """Determine evidence priority ranking for source type.

    Per specs/03_product_facts_and_evidence.md:117-128:
    1=manifest, 2=source_code, 3=test, 4=implementation_doc,
    5=api_doc, 6=readme_technical, 7=readme_marketing

    Args:
        source_type: Source type string

    Returns:
        Priority integer (1-7)

    Spec: specs/03_product_facts_and_evidence.md:117-128
    """
    priority_map = {
        'manifest': 1,
        'source_code': 2,
        'test': 3,
        'implementation_doc': 4,
        'api_doc': 5,
        'readme_technical': 6,
        'readme_marketing': 7,
    }
    return priority_map.get(source_type, 7)


# TC-CONTENT-QUALITY: Claim quality filter constants
MAX_CLAIM_TEXT_LENGTH_EXTRACT = 500  # Characters — allow longer explanations (was 300)
MIN_CLAIM_WORDS = 3  # Minimum words for a valid claim (was 4)
MIN_CLAIM_CHARS = 40  # Minimum characters for a valid claim (TC-1602)


def _is_code_like(text: str) -> bool:
    """Detect if text is source code rather than natural language.

    Checks for common programming patterns that indicate the text
    was extracted from source code rather than documentation prose.

    Args:
        text: Candidate claim text

    Returns:
        True if text appears to be source code
    """
    code_indicators = [
        r'\bdef\s+\w+\(',       # Python function def
        r'\bclass\s+\w+[:\(]',  # Class definition
        r'\bimport\s+\w+',      # Import statement
        r'\bself\.\w+',         # self.method
        r'\breturn\b',          # return statement
        r'\bassert\w*\(',       # assert calls
        r'\braise\s+\w+',       # raise exception
        r'^\s*#\s',             # Comment lines
        r'\w+\.\w+\(\)',        # method() calls
        r'\bNotImplementedError\b',  # Common exception class
        r'@\w+',                # Decorators (@staticmethod, etc.)
        r'->\s*[\'\"A-Z]',      # Return type annotations
        r'\bif\s+\w+\s+is\s+(not\s+)?None',  # if X is None / if X is not None
        r'\bfor\s+\w+\s+in\s+',              # for X in Y (loop)
        r'\bwhile\s+\w+',                     # while loop
        r'\btry\s*:',                          # try block
        r'\bexcept\s+\w+',                     # except clause
        r'\w+\s*=\s*\w+\.\w+\s+if\s+',        # ternary: X = Y.Z if ...
        r'\b\w+\s*=\s*\w+',                    # variable assignment: x = y
    ]
    matches = sum(1 for p in code_indicators if re.search(p, text))
    # Short text (<=8 words) needs fewer indicators — short code snippets are obvious
    threshold = 2 if len(text.split()) <= 8 else 3
    if matches >= threshold:
        return True
    # Single strong indicator: line starts with unambiguous code patterns
    stripped = text.strip()
    if re.match(r'^(from\s+\S+\s+)?import\s+', stripped):
        return True
    if re.match(r'^class\s+\w+.*:', stripped):
        return True
    if re.match(r'^def\s+\w+\s*\(', stripped):
        return True
    # If >25% non-alphabetic characters (brackets, dots, parens), likely code
    # TC-1616: Lowered from 0.40 to 0.25 to catch API descriptions like
    # "Scene.render(width, height, options)" which have ~38% non-alpha
    non_alpha = sum(1 for c in text if not c.isalpha() and not c.isspace())
    if len(text) > 20 and non_alpha / len(text) > 0.25:
        return True
    return False


def _is_prose_like(text: str) -> bool:
    """Check if text reads like natural language prose.

    Validates that text contains verb-like words and follows
    natural sentence structure rather than code or data fragments.

    Args:
        text: Candidate claim text

    Returns:
        True if text appears to be natural language prose
    """
    words = text.split()
    if len(words) < MIN_CLAIM_WORDS:
        return False
    # Must contain at least one common English verb
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
    # Remove Python idioms before verb matching to prevent false positives
    # e.g., "is" in "is not None" should not count as an English verb
    cleaned = text_lower
    for idiom in [' is not none', ' is none', ' is not ', ' is true', ' is false']:
        cleaned = cleaned.replace(idiom, ' ')
    has_verb = any(f' {v} ' in f' {cleaned} ' for v in common_verbs)
    if not has_verb:
        return False
    # Must not start with code-like patterns (Python statements/keywords)
    if text.lstrip().startswith((
        'from ', 'import ', 'def ', 'class ', '{', '[', 'self.', 'raise ', '@',
        'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except ', 'return ',
        'yield ', 'with ', 'async ',
    )):
        return False
    return True


def _is_noun_phrase_claim(text: str) -> bool:
    """Accept short noun-phrase claims that describe features/formats.

    Examples: "CSV and JSON format support", "Python 3.8+ compatibility"
    """
    text_lower = text.lower()
    feature_nouns = {
        'support', 'compatibility', 'integration', 'conversion', 'processing',
        'management', 'handling', 'rendering', 'format',
        'configuration', 'validation', 'optimization', 'feature',
        'version', 'platform', 'python',
    }
    return any(noun in text_lower for noun in feature_nouns)


def _is_template_claim(text: str, product_name: str = "") -> bool:
    """Detect template-generated claims that are too generic for key_features.

    TC-1616: Filter out template claims like:
    - "{product} provides the {ClassName} class for {classname} operations"
    - "The {ClassName} class provides methods: {method1}(), {method2}()"
    - "{product} provides the {x}() function"

    Args:
        text: Claim text to check
        product_name: Product name (currently unused but reserved for future patterns)

    Returns:
        True if the text matches template patterns

    Examples:
        >>> _is_template_claim("Aspose.3D provides the Scene class for scene operations")
        True
        >>> _is_template_claim("The Scene class provides methods: render(), load()")
        True
        >>> _is_template_claim("Supports comprehensive 3D scene manipulation")
        False
    """
    text_lower = text.lower()

    # Template patterns to detect
    template_patterns = [
        r'provides? the \w+ class for \w+ operations',
        r'the \w+ class provides? methods?:',
        r'provides? the \w+\(\) function',
        r'provides? \d+ (classes?|functions?|methods?)',
        r'aspose[-.]\w+ provides? the',
    ]

    for pattern in template_patterns:
        if re.search(pattern, text_lower):
            return True

    return False


def extract_candidate_statements_from_text(
    text: str,
    file_path: Path,
    repo_dir: Path,
) -> List[Dict[str, Any]]:
    """Extract candidate claim statements from text.

    Per specs/04_claims_compiler_truth_lock.md:34-46:
    Extract declarative sentences matching claim patterns.

    Args:
        text: Document text
        file_path: Source file path
        repo_dir: Repository root directory

    Returns:
        List of candidate claim dictionaries with:
        - claim_text: Raw claim text
        - source_file: Relative path to source file
        - start_line: Starting line number
        - end_line: Ending line number
        - source_type: Source type classification

    Spec: specs/04_claims_compiler_truth_lock.md:34-46
    """
    # Skip license files — they produce spurious limitation/legal claims
    file_name_lower = file_path.name.lower()
    if file_name_lower in (
        'license', 'license.md', 'license.txt',
        'copying', 'copying.md', 'copying.txt',
    ):
        return []

    candidates = []

    # Simple sentence extraction (split by periods, newlines)
    # This is a basic implementation; production would use NLP
    lines = text.split('\n')

    current_sentence = []
    start_line = 1

    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue

        # Skip code blocks, comments that don't look like sentences
        if line.startswith('#') and not any(marker in line.lower() for marker in [
            'supports', 'can', 'enables', 'install', 'usage', 'format', 'provides'
        ]):
            continue

        # Accumulate multi-line sentences
        current_sentence.append(line)

        # Sentence end markers
        if line.endswith(('.', '!', '?')) or line.endswith(':'):
            sentence = ' '.join(current_sentence)

            # TC-CONTENT-QUALITY: Apply claim quality filters
            # Reject code-like text, non-prose, overly long/short claims
            words = sentence.split()
            # Identifier ratio check: reject if >40% of tokens look like code identifiers
            # Strip trailing punctuation so "Hello." doesn't count as code (only "self.method" does)
            code_tokens = sum(1 for w in words if '.' in w.rstrip('.,;:!?') or '_' in w or '(' in w)
            identifier_heavy = len(words) > 0 and code_tokens / len(words) > 0.4
            if (
                len(words) >= MIN_CLAIM_WORDS
                and len(sentence.strip()) >= MIN_CLAIM_CHARS
                and len(sentence) <= MAX_CLAIM_TEXT_LENGTH_EXTRACT
                and not _is_code_like(sentence)
                and (_is_prose_like(sentence) or _is_noun_phrase_claim(sentence))
                and not identifier_heavy
            ):
                keyword_boost = any(marker in sentence.lower() for marker in [
                    'support', 'can', 'enable', 'provide', 'allow',
                    'install', 'use', 'usage', 'format', 'read', 'write',
                    'does not', 'cannot', 'limitation', 'not yet',
                    'class', 'function', 'method', 'api', 'interface',
                ])
                source_type = determine_source_type(file_path, repo_dir)
                candidates.append({
                    'claim_text': sentence,
                    'source_file': str(file_path.relative_to(repo_dir)) if file_path.is_absolute() else str(file_path),
                    'start_line': start_line,
                    'end_line': line_num,
                    'source_type': source_type,
                    'keyword_boost': keyword_boost,
                })

            # Reset for next sentence
            current_sentence = []
            start_line = line_num + 1

    # Second pass: extract bullet point items
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Match bullet points: "- item", "* item", "1. item"
        bullet_match = re.match(r'^(?:[-*]|\d+\.)\s+(.+)$', stripped)
        if not bullet_match:
            continue
        bullet_text = bullet_match.group(1).strip()
        bullet_words = bullet_text.split()
        if (
            len(bullet_words) >= MIN_CLAIM_WORDS
            and len(bullet_text.strip()) >= MIN_CLAIM_CHARS
            and len(bullet_text) <= MAX_CLAIM_TEXT_LENGTH_EXTRACT
            and not _is_code_like(bullet_text)
            and (_is_prose_like(bullet_text) or _is_noun_phrase_claim(bullet_text))
        ):
            source_type = determine_source_type(file_path, repo_dir)
            keyword_boost = any(marker in bullet_text.lower() for marker in [
                'support', 'can', 'enable', 'provide', 'allow',
                'install', 'use', 'usage', 'format', 'read', 'write',
                'does not', 'cannot', 'limitation', 'not yet',
            ])
            candidates.append({
                'claim_text': bullet_text,
                'source_file': str(file_path.relative_to(repo_dir)) if file_path.is_absolute() else str(file_path),
                'start_line': line_num,
                'end_line': line_num,
                'source_type': source_type,
                'keyword_boost': keyword_boost,
            })

    return candidates


# Section heading patterns that indicate structured documentation content
_SECTION_HEADERS = {
    'installation': 'workflow',
    'install': 'workflow',
    'setup': 'workflow',
    'getting started': 'workflow',
    'quick start': 'workflow',
    'quickstart': 'workflow',
    'usage': 'workflow',
    'features': 'feature',
    'requirements': 'workflow',
    'prerequisites': 'workflow',
    'python version': 'compatibility',
    'supported versions': 'compatibility',
    'compatibility': 'compatibility',
    'system requirements': 'compatibility',
    'platform support': 'compatibility',
    'supported platforms': 'compatibility',
    'supported python': 'compatibility',
    'version support': 'compatibility',
    # Use cases (TC-1618)
    'use cases': 'use_case',
    'use case': 'use_case',
    'applications': 'use_case',
    'when to use': 'use_case',
    'scenarios': 'use_case',
    'real world': 'use_case',
    'case study': 'use_case',
    'case studies': 'use_case',
    # Tutorials (TC-1618)
    'examples': 'tutorial',
    'example': 'tutorial',
    'tutorial': 'tutorial',
    'tutorials': 'tutorial',
    'walkthrough': 'tutorial',
    'guide': 'tutorial',
    'how to': 'tutorial',
    'step by step': 'tutorial',
    # FAQ and troubleshooting (TC-1619)
    'faq': 'faq',
    'frequently asked questions': 'faq',
    'q&a': 'faq',
    'common questions': 'faq',
    'common issues': 'troubleshooting',
    'troubleshooting': 'troubleshooting',
    'known limitations': 'troubleshooting',
    'known issues': 'troubleshooting',
}


def extract_structured_sections_from_readme(
    text: str,
    file_path: Path,
    repo_dir: Path,
    product_name: str,
) -> List[Dict[str, Any]]:
    """Extract claims from README sections by heading.

    Identifies documentation sections (## Installation, ## Getting Started, etc.)
    and extracts their content as classified claims with proper citations.
    For code-only sections (e.g., Quick Start with only a code block), synthesizes
    a narrative claim describing what the code does.

    Args:
        text: Full file text
        file_path: Source file path
        repo_dir: Repository root directory
        product_name: Product name for normalization

    Returns:
        List of claim dicts with claim_kind based on section heading
    """
    lines = text.split('\n')
    candidates = []

    current_section_kind = None
    current_section_heading = ""
    section_start = 0
    section_lines = []
    in_code_block = False

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Track code fences to avoid treating # comments inside code as headings
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            if current_section_kind:
                section_lines.append((line_num, line))
            continue

        # Only match headings outside code blocks
        heading_match = re.match(r'^#{1,3}\s+(.+)$', line) if not in_code_block else None
        if heading_match:
            # Process previous section
            if current_section_kind and section_lines:
                _extract_section_claims(
                    current_section_kind, section_lines, section_start, line_num - 1,
                    file_path, repo_dir, product_name, candidates,
                    section_heading=current_section_heading,
                )
            # Start new section
            heading_text_raw = heading_match.group(1).strip()
            heading_text_lower = heading_text_raw.lower()
            current_section_heading = heading_text_raw
            current_section_kind = None
            for pattern, kind in _SECTION_HEADERS.items():
                if pattern in heading_text_lower:
                    current_section_kind = kind
                    break
            section_start = line_num
            section_lines = []
        elif current_section_kind:
            section_lines.append((line_num, line))

    # Process last section
    if current_section_kind and section_lines:
        last_line_num = section_lines[-1][0] if section_lines else section_start
        _extract_section_claims(
            current_section_kind, section_lines, section_start, last_line_num,
            file_path, repo_dir, product_name, candidates,
            section_heading=current_section_heading,
        )

    return candidates


def _decompose_code_block_into_steps(
    code_lines: List[str],
    section_heading: str,
    section_kind: str,
    product_name: str,
) -> List[Dict[str, Any]]:
    """Decompose code block into per-statement educational steps.

    TC-1617: Creates one step per logical statement (import, instantiation, method call, save)
    with educational context explaining purpose.

    Args:
        code_lines: Python code lines to analyze
        section_heading: Section heading text
        section_kind: Kind of section (e.g., "installation", "quickstart")
        product_name: Product name for templates

    Returns:
        List of step dictionaries with step_order and educational claim_text
    """
    import ast as ast_mod

    code_text = "\n".join(code_lines)
    steps: List[Dict[str, Any]] = []
    step_order = 1

    # Parse AST to extract individual statements
    try:
        tree = ast_mod.parse(code_text)
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.ImportFrom):
                module = node.module or ""
                module_short = module.split('.')[-1] if module else ""
                names = [a.name for a in node.names[:3]]
                if names:
                    # Educational context for imports
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
                # Detect instantiation (e.g., obj = ClassName())
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
                # Top-level method calls (not nested in assignments)
                if isinstance(node.value.func, ast_mod.Attribute):
                    method_name = node.value.func.attr
                    # Infer purpose from common method patterns
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
        # Fallback for non-parseable code
        pass

    return steps


def _enrich_workflow_claims_with_context(
    claims: List[Dict[str, Any]],
    section_heading: str,
    section_kind: str,
    section_start: int,
    section_end: int,
    rel_path: str,
    product_name: str,
) -> List[Dict[str, Any]]:
    """Add prerequisites, verification, and troubleshooting steps to workflows.

    TC-1617: Enriches workflow claims with educational context steps.

    Args:
        claims: Decomposed step claims from _decompose_code_block_into_steps
        section_heading: Section name (e.g., "Installation", "Quickstart")
        section_kind: Section kind
        section_start: Starting line number
        section_end: Ending line number
        rel_path: Relative path to source file
        product_name: Product name

    Returns:
        Enriched claims with prerequisites, verification, troubleshooting added
    """
    enriched = []
    heading_lower = section_heading.lower()

    # For installation workflows, add prerequisite
    if 'install' in heading_lower:
        enriched.append({
            'claim_text': "Ensure Python 3.8+ is installed on your system",
            'claim_kind': 'workflow',
            'source_file': rel_path,
            'start_line': section_start,
            'end_line': section_end,
            'source_type': 'readme_technical',
            'keyword_boost': True,
            'section_kind': section_kind,
            'step_order': 0,  # Prerequisite comes first
            'action_type': 'prerequisite',
        })

    # Add original steps with sequential numbering
    next_step_num = 1 if 'install' in heading_lower else 0
    for claim in claims:
        # Add required fields
        claim.setdefault('source_file', rel_path)
        claim.setdefault('start_line', section_start)
        claim.setdefault('end_line', section_end)
        claim.setdefault('source_type', 'readme_technical')
        claim.setdefault('keyword_boost', True)
        claim.setdefault('section_kind', section_kind)
        claim.setdefault('claim_kind', 'workflow')

        # Renumber to ensure sequential ordering
        claim['step_order'] = next_step_num
        next_step_num += 1

        enriched.append(claim)

    # Track next step_order for additional steps
    next_step_order = next_step_num

    # Add verification step after installation
    if 'install' in heading_lower and enriched:
        enriched.append({
            'claim_text': f"Verify installation by importing {product_name} in Python",
            'claim_kind': 'workflow',
            'source_file': rel_path,
            'start_line': section_start,
            'end_line': section_end,
            'source_type': 'readme_technical',
            'keyword_boost': True,
            'section_kind': section_kind,
            'step_order': next_step_order,
            'action_type': 'verification',
        })
        next_step_order += 1

    # Add troubleshooting context for installation
    if 'install' in heading_lower and enriched:
        enriched.append({
            'claim_text': "If installation fails, try upgrading pip with: python -m pip install --upgrade pip",
            'claim_kind': 'workflow',
            'source_file': rel_path,
            'start_line': section_start,
            'end_line': section_end,
            'source_type': 'readme_technical',
            'keyword_boost': True,
            'section_kind': section_kind,
            'step_order': next_step_order,
            'action_type': 'troubleshooting',
        })

    return enriched


def _extract_use_case_narratives(
    text: str,
    section_heading: str,
    source_file: str,
    section_start: int,
    section_end: int,
    source_type: str,
) -> List[Dict]:
    """Extract use case narratives from README sections.

    TC-1618: Extracts use cases for blog/marketing content.

    Strategies:
    1. Bullet list pattern: "- **Use case name**: description"
    2. Narrative paragraphs: 20+ word blocks describing real-world applications

    Args:
        text: Section text content
        section_heading: Section name (e.g., "Use Cases", "Applications")
        source_file: Relative source file path
        section_start: Starting line number
        section_end: Ending line number
        source_type: Source type (readme_technical, readme_marketing, etc.)

    Returns:
        List of use case claim dicts
    """
    use_cases = []

    # Strategy 1: Bullet list pattern with optional bold markers
    # Matches: "- **Use case**: description" or "- Use case: description"
    bullet_pattern = r'^[-*]\s+(?:\*\*)?([^:*]+?)(?:\*\*)?\s*:\s+(.+)$'
    lines = text.split('\n')

    for line_num_offset, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(bullet_pattern, stripped)
        if match:
            use_case_name = match.group(1).strip()
            description = match.group(2).strip()

            # Minimum narrative length (20 words)
            if len(description.split()) >= 20:
                use_cases.append({
                    'claim_text': f"{use_case_name}: {description}",
                    'claim_kind': 'use_case',
                    'section_kind': 'use_case',
                    'source_type': source_type,
                    'source_file': source_file,
                    'start_line': section_start + line_num_offset,
                    'end_line': section_start + line_num_offset,
                    'keyword_boost': True,
                })

    # Strategy 2: Narrative paragraphs (20+ words)
    # Split on double newlines to get paragraphs
    paragraphs = text.split('\n\n')
    for para_idx, para in enumerate(paragraphs):
        para_clean = para.strip()
        word_count = len(para_clean.split())

        # Must be 20+ words, not a heading, not code-like, and prose-like
        if word_count >= 20 and not para_clean.startswith(('#', '-', '*')):
            # Check if it's a narrative (not code, not metadata)
            if not _is_code_like(para_clean) and _is_prose_like(para_clean):
                # Truncate if too long
                if len(para_clean) > MAX_CLAIM_TEXT_LENGTH_EXTRACT:
                    para_clean = para_clean[:MAX_CLAIM_TEXT_LENGTH_EXTRACT - 3] + "..."

                use_cases.append({
                    'claim_text': para_clean,
                    'claim_kind': 'use_case',
                    'section_kind': 'use_case',
                    'source_type': source_type,
                    'source_file': source_file,
                    'start_line': section_start,
                    'end_line': section_end,
                    'keyword_boost': True,
                })

    return use_cases


def _extract_tutorial_narratives(
    text: str,
    section_heading: str,
    source_file: str,
    section_start: int,
    section_end: int,
    source_type: str,
) -> List[Dict]:
    """Extract tutorial narratives preserving prose + code structure.

    TC-1618: Extracts tutorials for educational content.

    Tutorials have educational flow with both prose and code.
    Minimum: 30+ words of prose AND code block present.

    Args:
        text: Section text content
        section_heading: Section name (e.g., "Tutorial", "Walkthrough")
        source_file: Relative source file path
        section_start: Starting line number
        section_end: Ending line number
        source_type: Source type

    Returns:
        List of tutorial claim dicts
    """
    tutorials = []

    # Split on code block boundaries (```...```)
    code_fence_pattern = r'```[\s\S]+?```'
    parts = re.split(code_fence_pattern, text)
    code_blocks = re.findall(code_fence_pattern, text)

    # Tutorial must have BOTH prose and code
    if not code_blocks:
        return []

    # Extract prose blocks and check total word count
    prose_blocks = []
    total_prose_words = 0

    for part in parts:
        part_clean = part.strip()

        # Remove markdown headings (##, ###, etc.) from the prose
        lines = part_clean.split('\n')
        prose_lines = [line for line in lines if not line.strip().startswith('#')]
        prose_only = '\n'.join(prose_lines).strip()

        # Count words and check if prose-like
        if prose_only and _is_prose_like(prose_only):
            word_count = len(prose_only.split())
            prose_blocks.append(prose_only)
            total_prose_words += word_count

    # Tutorial must have 30+ total words of prose across all blocks
    if total_prose_words < 30 or not prose_blocks:
        return []

    # Create tutorial claim preserving structure
    tutorial_text = f"{section_heading}: "

    # Use first 2 prose blocks for summary (or just first if only one)
    summary_blocks = prose_blocks[:2]
    for block in summary_blocks:
        # Truncate long blocks to keep claim manageable
        if len(block) > 200:
            block = block[:197] + "..."
        tutorial_text += block + " "

    # Add code example count as metadata
    tutorial_text += f"(includes {len(code_blocks)} code example{'s' if len(code_blocks) > 1 else ''})"

    # Final length check
    if len(tutorial_text) > MAX_CLAIM_TEXT_LENGTH_EXTRACT:
        tutorial_text = tutorial_text[:MAX_CLAIM_TEXT_LENGTH_EXTRACT - 3] + "..."

    tutorials.append({
        'claim_text': tutorial_text,
        'claim_kind': 'tutorial',
        'section_kind': 'tutorial',
        'source_type': source_type,
        'source_file': source_file,
        'start_line': section_start,
        'end_line': section_end,
        'keyword_boost': True,
        'code_block_count': len(code_blocks),
        'prose_block_count': len(prose_blocks),
    })

    return tutorials


def _extract_faq_entries(
    text: str,
    section_heading: str,
    source_file: str,
    section_start: int,
    section_end: int,
    source_type: str,
) -> List[Dict]:
    """Extract FAQ entries from README FAQ sections.

    TC-1619: Extracts Q&A patterns for knowledge base articles.

    Patterns:
    1. Q: question text\nA: answer text
    2. **How do I...?** Answer text
    3. Numbered list of questions with answers

    Args:
        text: Section text content
        section_heading: Section name (e.g., "FAQ", "Q&A")
        source_file: Relative source file path
        section_start: Starting line number
        section_end: Ending line number
        source_type: Source type

    Returns:
        List of FAQ claim dicts
    """
    faq_entries = []

    # Pattern 1: Q: ... A: ... format
    qa_pattern = r'Q:?\s*(.+?)\s*A:?\s*(.+?)(?=\n\n|Q:|$)'
    matches = re.finditer(qa_pattern, text, re.DOTALL | re.IGNORECASE)

    for match in matches:
        question = match.group(1).strip()
        answer = match.group(2).strip()

        # Ensure answer has minimum content (20 words)
        if len(answer.split()) >= 20:
            claim_text = f"FAQ: {question} Answer: {answer}"

            # Truncate if too long
            if len(claim_text) > MAX_CLAIM_TEXT_LENGTH_EXTRACT:
                claim_text = claim_text[:MAX_CLAIM_TEXT_LENGTH_EXTRACT - 3] + "..."

            faq_entries.append({
                'claim_text': claim_text,
                'claim_kind': 'faq',
                'section_kind': 'faq',
                'source_type': source_type,
                'source_file': source_file,
                'start_line': section_start,
                'end_line': section_end,
                'keyword_boost': True,
            })

    # Pattern 2: **How do I...?** or **What is...?** format
    how_pattern = r'\*\*([^*]+\?)\*\*\s*(.+?)(?=\n\n|\*\*|$)'
    matches = re.finditer(how_pattern, text, re.DOTALL)

    for match in matches:
        question = match.group(1).strip()
        answer = match.group(2).strip()

        # Ensure answer has minimum content (20 words)
        if len(answer.split()) >= 20:
            claim_text = f"{question} {answer}"

            # Truncate if too long
            if len(claim_text) > MAX_CLAIM_TEXT_LENGTH_EXTRACT:
                claim_text = claim_text[:MAX_CLAIM_TEXT_LENGTH_EXTRACT - 3] + "..."

            faq_entries.append({
                'claim_text': claim_text,
                'claim_kind': 'faq',
                'section_kind': 'faq',
                'source_type': source_type,
                'source_file': source_file,
                'start_line': section_start,
                'end_line': section_end,
                'keyword_boost': True,
            })

    # Pattern 3: Numbered lists with question-like items
    # Matches: "1. How do I install?" followed by answer text
    numbered_pattern = r'\d+\.\s+([^?]+\?)\s*(.+?)(?=\n\d+\.|$)'
    matches = re.finditer(numbered_pattern, text, re.DOTALL)

    for match in matches:
        question = match.group(1).strip()
        answer = match.group(2).strip()

        # Ensure answer has minimum content (20 words)
        if len(answer.split()) >= 20:
            claim_text = f"{question} {answer}"

            # Truncate if too long
            if len(claim_text) > MAX_CLAIM_TEXT_LENGTH_EXTRACT:
                claim_text = claim_text[:MAX_CLAIM_TEXT_LENGTH_EXTRACT - 3] + "..."

            faq_entries.append({
                'claim_text': claim_text,
                'claim_kind': 'faq',
                'section_kind': 'faq',
                'source_type': source_type,
                'source_file': source_file,
                'start_line': section_start,
                'end_line': section_end,
                'keyword_boost': True,
            })

    return faq_entries


def _extract_error_messages(code_content: str, source_file: str) -> List[Dict]:
    """Extract error messages from raise statements and Error classes.

    TC-1619: Extracts troubleshooting content from source code.

    Patterns:
    - raise ValueError("error message")
    - raise CustomError(f"error {variable}")
    - class CustomError(Exception): ...

    Args:
        code_content: Python source code
        source_file: Source file path

    Returns:
        List of troubleshooting claim dicts with error context
    """
    troubleshooting_claims = []

    # Pattern 1: raise statements with string literals
    raise_pattern = r'raise\s+(\w+)\s*\(\s*[\'"]([^\'"]+)[\'"]'
    matches = re.finditer(raise_pattern, code_content)

    for match in matches:
        error_class = match.group(1)
        error_message = match.group(2)

        # Filter out code-like error messages and ensure minimum length
        if len(error_message) >= 10 and not _is_code_like(error_message):
            troubleshooting_claims.append({
                'claim_text': f"Error: {error_message} (raised as {error_class})",
                'claim_kind': 'troubleshooting',
                'section_kind': 'troubleshooting',
                'error_type': error_class,
                'source_type': 'source_code',
                'source_file': source_file,
                'start_line': 0,  # Line number extraction requires tokenization
                'end_line': 0,
                'keyword_boost': True,
            })

    # Pattern 2: Exception class definitions
    exception_pattern = r'class\s+(\w+Error|Exception)\s*\([^)]*Exception[^)]*\):'
    matches = re.finditer(exception_pattern, code_content)

    for match in matches:
        error_class = match.group(1)
        troubleshooting_claims.append({
            'claim_text': f"Custom error type: {error_class} indicates specific failure conditions",
            'claim_kind': 'troubleshooting',
            'section_kind': 'troubleshooting',
            'error_type': error_class,
            'source_type': 'source_code',
            'source_file': source_file,
            'start_line': 0,
            'end_line': 0,
            'keyword_boost': True,
        })

    return troubleshooting_claims


def _extract_expanded_limitations(text: str, source_file: str, section_start: int = 0) -> List[Dict]:
    """Extract limitations including known issues, workarounds, compatibility notes.

    TC-1619: Expands limitation extraction beyond "not yet supported".

    Patterns:
    - "not yet supported"
    - "not implemented"
    - "known issue"
    - "workaround"
    - "compatibility note"
    - "requires X version"
    - "only works with Y"

    Args:
        text: Documentation text
        source_file: Source file path
        section_start: Starting line number for context

    Returns:
        List of limitation/troubleshooting claim dicts
    """
    limitations = []

    limitation_patterns = [
        (r'not yet (supported|implemented)', 'limitation'),
        (r'not (supported|implemented)', 'limitation'),
        (r'known (issue|bug|limitation)', 'troubleshooting'),
        (r'workaround:?\s+(.+)', 'troubleshooting'),
        (r'compatibility:?\s+(.+)', 'troubleshooting'),
        (r'requires?\s+(python|[\w.]+)\s+(\d+\.\d+)', 'troubleshooting'),
        (r'only (works|supported) (with|on|for)\s+(\w+)', 'limitation'),
    ]

    lines = text.split('\n')
    for line_num, line in enumerate(lines, start=section_start):
        line_lower = line.lower()

        for pattern, claim_kind in limitation_patterns:
            matches = re.finditer(pattern, line_lower, re.IGNORECASE)
            for match in matches:
                # Extract surrounding context (up to 200 chars)
                start_idx = max(0, match.start() - 50)
                end_idx = min(len(line), match.end() + 150)
                context = line[start_idx:end_idx].strip()

                # Ensure minimum length and quality
                if len(context.split()) >= MIN_CLAIM_WORDS and not _is_code_like(context):
                    # Truncate if too long
                    if len(context) > MAX_CLAIM_TEXT_LENGTH_EXTRACT:
                        context = context[:MAX_CLAIM_TEXT_LENGTH_EXTRACT - 3] + "..."

                    limitations.append({
                        'claim_text': context,
                        'claim_kind': claim_kind,
                        'section_kind': 'troubleshooting',
                        'source_type': 'readme_technical',
                        'source_file': source_file,
                        'start_line': line_num,
                        'end_line': line_num,
                        'keyword_boost': True,
                    })

    return limitations


def _extract_faq_from_tests(test_file_path: str) -> List[Dict]:
    """Extract FAQ entries from test names and docstrings.

    TC-1619: Synthesizes FAQ from test file patterns.

    Test names often describe issues:
    - test_handle_invalid_format → "What happens when format is invalid?"
    - test_missing_file_raises_error → "What happens when file is missing?"

    Args:
        test_file_path: Path to test file

    Returns:
        List of FAQ claim dicts
    """
    faq_entries = []

    # Parse test file
    try:
        with open(test_file_path, encoding='utf-8', errors='ignore') as f:
            code = f.read()
    except Exception:
        return []

    # Extract test function names and docstrings
    test_pattern = r'def\s+(test_\w+)\s*\([^)]*\):\s*(?:\"\"\"([^\"]+)\"\"\")?'
    matches = re.finditer(test_pattern, code)

    for match in matches:
        test_name = match.group(1)
        docstring = match.group(2) if match.group(2) else ""

        # Convert test name to FAQ question
        # test_handle_invalid_format → "handle invalid format"
        question_slug = test_name.replace('test_', '').replace('_', ' ')

        # Only create FAQ if test name indicates error/failure/invalid scenario
        if any(keyword in test_name for keyword in ['error', 'fail', 'invalid', 'missing', 'raises', 'exception']):
            # Generate question based on pattern
            if 'raises' in test_name or 'error' in test_name:
                faq_text = f"FAQ: What happens when {question_slug}?"
            elif 'fail' in test_name:
                faq_text = f"FAQ: Why does {question_slug}?"
            elif 'invalid' in test_name or 'missing' in test_name:
                faq_text = f"FAQ: How to handle {question_slug}?"
            else:
                faq_text = f"FAQ: What about {question_slug}?"

            # Add docstring if available
            if docstring:
                faq_text += f" {docstring.strip()}"

            # Ensure minimum length
            if len(faq_text.split()) >= MIN_CLAIM_WORDS:
                faq_entries.append({
                    'claim_text': faq_text,
                    'claim_kind': 'faq',
                    'section_kind': 'faq',
                    'source_type': 'test',
                    'source_file': test_file_path,
                    'start_line': 0,
                    'end_line': 0,
                    'keyword_boost': True,
                })

    return faq_entries


def _synthesize_code_block_claims(
    code_lines: List[str],
    section_heading: str,
    section_kind: str,
    section_start: int,
    section_end: int,
    rel_path: str,
    product_name: str,
) -> List[Dict[str, Any]]:
    """Synthesize narrative claims from a code-only section.

    Uses AST-based extraction for Python code blocks to produce deterministic
    claims describing what the code does. For install/quickstart sections,
    decomposes into per-statement claims with educational enrichment (TC-1617).
    For other sections, produces a single combined claim for backward compatibility.

    Args:
        code_lines: Python code lines to analyze
        section_heading: Section heading text
        section_kind: Kind of section (e.g., "installation", "quickstart")
        section_start: Starting line number in source file
        section_end: Ending line number in source file
        rel_path: Relative path to source file
        product_name: Product name for templates

    Returns:
        List of claim dictionaries (one or more depending on section type)
    """
    heading_lower = section_heading.lower()
    is_workflow_section = any(
        m in heading_lower
        for m in ['install', 'quickstart', 'quick start', 'getting started']
    )

    # TC-1617: For workflow sections, decompose into per-statement claims with enrichment
    if is_workflow_section:
        # Step 1: Decompose code into individual steps
        steps = _decompose_code_block_into_steps(
            code_lines, section_heading, section_kind, product_name
        )

        # Step 2: Enrich with prerequisites, verification, troubleshooting
        if steps:
            enriched_claims = _enrich_workflow_claims_with_context(
                steps, section_heading, section_kind,
                section_start, section_end, rel_path, product_name
            )
            return enriched_claims
        else:
            # Fallback if no steps extracted: create generic enriched workflow
            generic_steps = [{
                'claim_text': f"Follow {section_heading.lower()} instructions",
                'step_order': 1,
                'action_type': 'generic',
            }]
            enriched_claims = _enrich_workflow_claims_with_context(
                generic_steps, section_heading, section_kind,
                section_start, section_end, rel_path, product_name
            )
            return enriched_claims

    # For non-workflow sections, use existing single-claim behavior
    import ast as ast_mod

    code_text = "\n".join(code_lines)
    actions: List[str] = []

    try:
        tree = ast_mod.parse(code_text)
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.ImportFrom):
                module = node.module or ""
                names = [a.name for a in node.names[:3]]
                actions.append(f"import {', '.join(names)} from {module.split('.')[-1]}")
            elif isinstance(node, ast_mod.Import):
                for alias in node.names:
                    actions.append(f"import {alias.name.split('.')[-1]}")
            elif isinstance(node, ast_mod.Call):
                if isinstance(node.func, ast_mod.Attribute):
                    actions.append(f"call {node.func.attr}()")
                elif isinstance(node.func, ast_mod.Name):
                    actions.append(f"call {node.func.id}()")
    except SyntaxError:
        pass

    # Deduplicate while preserving order
    seen: set = set()
    unique_actions: List[str] = []
    for a in actions:
        if a not in seen:
            seen.add(a)
            unique_actions.append(a)

    is_quickstart = any(m in heading_lower for m in ['quickstart', 'quick start', 'getting started'])

    if unique_actions:
        actions_str = ", ".join(unique_actions[:5])
        if is_quickstart:
            claim_text = f"Quick start: {actions_str}"
        else:
            claim_text = f"{section_heading}: {actions_str}"
    else:
        if is_quickstart:
            claim_text = f"Quick start: demonstrates basic usage with a code example for {product_name}"
        else:
            claim_text = f"{section_heading}: demonstrates usage with a code example for {product_name}"

    if len(claim_text) > MAX_CLAIM_TEXT_LENGTH_EXTRACT:
        claim_text = claim_text[: MAX_CLAIM_TEXT_LENGTH_EXTRACT - 3] + "..."

    return [{
        'claim_text': claim_text,
        'source_file': rel_path,
        'start_line': section_start,
        'end_line': section_end,
        'source_type': 'readme_technical',
        'keyword_boost': True,
        'section_kind': section_kind,
    }]


def _extract_section_claims(
    section_kind: str,
    section_lines: List[tuple],
    section_start: int,
    section_end: int,
    file_path: Path,
    repo_dir: Path,
    product_name: str,
    candidates: List[Dict[str, Any]],
    section_heading: str = "",
) -> None:
    """Extract claims from a single README section."""
    rel_path = str(file_path.relative_to(repo_dir)) if file_path.is_absolute() else str(file_path)
    source_type = determine_source_type(file_path, repo_dir)

    # TC-1618: Handle use_case and tutorial sections with specialized extractors
    if section_kind == 'use_case':
        # Reconstruct full section text from lines
        section_text = "\n".join(line for _, line in section_lines)
        use_case_claims = _extract_use_case_narratives(
            section_text, section_heading, rel_path,
            section_start, section_end, source_type
        )
        candidates.extend(use_case_claims)
        return

    if section_kind == 'tutorial':
        # Reconstruct full section text from lines
        section_text = "\n".join(line for _, line in section_lines)
        tutorial_claims = _extract_tutorial_narratives(
            section_text, section_heading, rel_path,
            section_start, section_end, source_type
        )
        candidates.extend(tutorial_claims)
        return

    # TC-1619: Handle FAQ sections with specialized extractor
    if section_kind == 'faq':
        # Reconstruct full section text from lines
        section_text = "\n".join(line for _, line in section_lines)
        faq_claims = _extract_faq_entries(
            section_text, section_heading, rel_path,
            section_start, section_end, source_type
        )
        candidates.extend(faq_claims)
        return

    # TC-1619: Handle troubleshooting sections with expanded limitation extraction
    if section_kind == 'troubleshooting':
        # Reconstruct full section text from lines
        section_text = "\n".join(line for _, line in section_lines)
        limitation_claims = _extract_expanded_limitations(
            section_text, rel_path, section_start
        )
        candidates.extend(limitation_claims)
        return

    # For other section kinds, use existing extraction logic
    prose_found = False
    in_code_block = False
    code_block_lines: List[str] = []
    all_code_lines: List[str] = []

    for line_num, line in section_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip headings within section (but not inside code blocks)
        if stripped.startswith('#') and not in_code_block:
            continue

        # Track code fences
        if stripped.startswith('```'):
            if in_code_block:
                in_code_block = False
                all_code_lines.extend(code_block_lines)
                code_block_lines = []
            else:
                in_code_block = True
                code_block_lines = []
            continue

        if in_code_block:
            code_block_lines.append(stripped)
            continue

        # Extract bullet point content
        bullet_match = re.match(r'^(?:[-*]|\d+\.)\s+(.+)$', stripped)
        claim_text = bullet_match.group(1).strip() if bullet_match else stripped

        words = claim_text.split()
        if len(words) < MIN_CLAIM_WORDS:
            continue
        if len(claim_text.strip()) < MIN_CLAIM_CHARS:
            continue
        if len(claim_text) > MAX_CLAIM_TEXT_LENGTH_EXTRACT:
            continue
        if _is_code_like(claim_text):
            continue

        # Accept if prose-like or noun-phrase
        if not (_is_prose_like(claim_text) or _is_noun_phrase_claim(claim_text)):
            continue

        prose_found = True
        candidates.append({
            'claim_text': claim_text,
            'source_file': rel_path,
            'start_line': line_num,
            'end_line': line_num,
            'source_type': 'readme_technical',
            'keyword_boost': True,
            'section_kind': section_kind,
        })

    # Flush any unclosed code block (e.g., outer function split on a heading inside code)
    if in_code_block and code_block_lines:
        all_code_lines.extend(code_block_lines)

    # Synthesize claims from code blocks if no prose was found
    if not prose_found and all_code_lines:
        synthetic_claims = _synthesize_code_block_claims(
            code_lines=all_code_lines,
            section_heading=section_heading or section_kind.replace("_", " ").title(),
            section_kind=section_kind,
            section_start=section_start,
            section_end=section_end,
            rel_path=rel_path,
            product_name=product_name,
        )
        candidates.extend(synthetic_claims)


def extract_claims_with_llm(
    doc_files: List[Dict[str, Any]],
    repo_dir: Path,
    product_name: str,
    llm_client: LLMProviderClient,
) -> List[Dict[str, Any]]:
    """Extract structured claims using LLM.

    Uses LLM to parse documentation and extract atomic claims with citations.

    Args:
        doc_files: List of discovered documentation files
        repo_dir: Repository root directory
        product_name: Product name for normalization
        llm_client: LLM client with deterministic settings

    Returns:
        List of extracted claim dictionaries

    Raises:
        ClaimsExtractionError: If LLM extraction fails
    """
    all_claims = []

    # Build prompt with documentation context
    # TC-1026: Process ALL discovered docs (no count limit).
    for doc_file in doc_files:
        file_path = repo_dir / doc_file['path']

        if not file_path.exists():
            logger.warning("doc_file_not_found", path=str(file_path))
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.warning("doc_file_read_error", path=str(file_path), error=str(e))
            continue

        # Source quality metadata from W1 discovery
        doc_relevance = doc_file.get('relevance_score', 50)
        doc_evidence_priority = doc_file.get('evidence_priority', 'medium')

        # Extract candidate statements using heuristics
        candidates = extract_candidate_statements_from_text(
            content, file_path, repo_dir
        )

        # Build structured claims from candidates
        for candidate in candidates:
            claim_kind = classify_claim_kind(candidate['claim_text'])

            # TC-1616: Reclassify template claims from key_feature to api_reference
            if claim_kind == 'key_feature':
                if _is_template_claim(candidate['claim_text'], product_name):
                    claim_kind = 'api_reference'

            claim_id = compute_claim_id(
                candidate['claim_text'], claim_kind, product_name
            )
            source_type = candidate['source_type']
            source_priority = determine_source_priority(source_type)

            # Determine truth_status based on source priority
            # Per specs/04_claims_compiler_truth_lock.md:50-54
            truth_status = 'fact' if source_priority <= 3 else 'inference'

            claim = {
                'claim_id': claim_id,
                'claim_text': candidate['claim_text'],
                'claim_kind': claim_kind,
                'truth_status': truth_status,
                'confidence': 'high' if source_priority <= 2 else 'medium' if source_priority <= 5 else 'low',
                'source_type': source_type,
                'source_priority': source_priority,
                'source_relevance': doc_relevance,
                'evidence_priority': doc_evidence_priority,
                'citations': [{
                    'path': candidate['source_file'],
                    'start_line': candidate['start_line'],
                    'end_line': candidate['end_line'],
                    'source_type': source_type,
                }],
            }

            all_claims.append(claim)

    return all_claims


def validate_claim_structure(claim: Dict[str, Any]) -> None:
    """Validate claim structure against schema.

    Per specs/schemas/evidence_map.schema.json:14-50.

    Args:
        claim: Claim dictionary

    Raises:
        ClaimsValidationError: If claim structure is invalid

    Spec: specs/schemas/evidence_map.schema.json:14-50
    """
    required_fields = ['claim_id', 'claim_text', 'claim_kind', 'truth_status', 'citations']

    for field in required_fields:
        if field not in claim:
            raise ClaimsValidationError(f"Missing required field: {field}")

    # Validate truth_status
    if claim['truth_status'] not in ['fact', 'inference']:
        raise ClaimsValidationError(
            f"Invalid truth_status: {claim['truth_status']} (must be 'fact' or 'inference')"
        )

    # Validate citations structure
    if not isinstance(claim['citations'], list) or len(claim['citations']) == 0:
        raise ClaimsValidationError("Citations must be non-empty list")

    for citation in claim['citations']:
        required_citation_fields = ['path', 'start_line', 'end_line']
        for field in required_citation_fields:
            if field not in citation:
                raise ClaimsValidationError(
                    f"Missing required citation field: {field}"
                )


def deduplicate_claims(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate claims by claim_id, merging citations.

    Args:
        claims: List of claims (may have duplicate claim_ids)

    Returns:
        Deduplicated list with merged citations

    Spec: specs/04_claims_compiler_truth_lock.md (stable claim IDs)
    """
    claims_map: Dict[str, Dict[str, Any]] = {}

    for claim in claims:
        claim_id = claim['claim_id']

        if claim_id in claims_map:
            # Merge citations
            existing = claims_map[claim_id]
            existing['citations'].extend(claim['citations'])

            # Upgrade truth_status if any citation is 'fact'
            if claim['truth_status'] == 'fact':
                existing['truth_status'] = 'fact'

            # Use highest confidence
            confidence_order = {'high': 3, 'medium': 2, 'low': 1}
            if confidence_order.get(claim.get('confidence', 'low'), 0) > confidence_order.get(existing.get('confidence', 'low'), 0):
                existing['confidence'] = claim['confidence']

            # Use highest source_priority (lowest number)
            if claim.get('source_priority', 7) < existing.get('source_priority', 7):
                existing['source_priority'] = claim['source_priority']

            # Use highest source_relevance (higher = better source)
            if claim.get('source_relevance', 0) > existing.get('source_relevance', 0):
                existing['source_relevance'] = claim['source_relevance']
                existing['evidence_priority'] = claim.get('evidence_priority', 'medium')
        else:
            claims_map[claim_id] = claim

    return list(claims_map.values())


def sort_claims_deterministically(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort claims deterministically by claim_id.

    Per specs/10_determinism_and_caching.md:39-46:
    Claims must be sorted by claim_id lexicographically.

    Args:
        claims: List of claims

    Returns:
        Sorted list of claims

    Spec: specs/10_determinism_and_caching.md:45
    """
    return sorted(claims, key=lambda c: c['claim_id'])


def _build_code_grounded_prompt(
    api_surface: Dict[str, Any],
    product_name: str,
) -> List[Dict[str, str]]:
    """Build LLM prompt for code-grounded claim generation.

    Constructs a prompt listing the real API surface (classes, methods,
    modules) and instructs the LLM to generate user-facing claims that
    ONLY reference symbols present in the provided list.

    Args:
        api_surface: Dict with "classes", "functions", "modules" lists
        product_name: Product name for context

    Returns:
        List of message dicts for chat_completion
    """
    # Build a compact representation of the API surface
    surface_lines = []
    for cls in api_surface.get("classes", []):
        name = cls.get("name", "")
        if name.startswith("_"):
            continue
        module = cls.get("module", "")
        methods = [m for m in cls.get("methods", []) if not m.startswith("_")]
        docstring = cls.get("docstring", "")
        surface_lines.append(
            f"Class: {name} (module: {module})"
            f"  Methods: {', '.join(methods) if methods else 'none'}"
            f"  Docstring: {docstring[:200] if docstring else 'N/A'}"
        )

    for func in api_surface.get("functions", []):
        name = func.get("name", "")
        if name.startswith("_"):
            continue
        module = func.get("module", "")
        docstring = func.get("docstring", "")
        surface_lines.append(
            f"Function: {name}() (module: {module})"
            f"  Docstring: {docstring[:200] if docstring else 'N/A'}"
        )

    for mod in api_surface.get("modules", []):
        name = mod.get("name", "")
        if name.startswith("_"):
            continue
        docstring = mod.get("docstring", "")
        surface_lines.append(
            f"Module: {name}"
            f"  Docstring: {docstring[:200] if docstring else 'N/A'}"
        )

    api_listing = "\n".join(surface_lines) if surface_lines else "(empty)"

    system_msg = (
        "You are a technical documentation assistant. Generate user-facing claims "
        "about a software library based on its API surface. "
        "ONLY describe classes/methods listed below. Do NOT invent any methods or "
        "classes not in the provided list. "
        "Return a JSON array of claim objects. Each object must have: "
        '"claim_text" (string, a concise user-facing statement), '
        '"claim_kind" (string, one of "key_feature" or "api_reference"), '
        '"referenced_symbols" (list of strings, the class/function names referenced). '
        "Generate between 10 and 30 claims. Focus on what users can accomplish."
    )

    user_msg = (
        f"Product: {product_name}\n\n"
        f"API Surface:\n{api_listing}\n\n"
        "Generate claims as a JSON array. Example format:\n"
        '[{"claim_text": "ProductX provides the Scene class for managing 3D scenes", '
        '"claim_kind": "key_feature", "referenced_symbols": ["Scene"]}]'
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def _parse_code_grounded_llm_response(content: str) -> List[Dict[str, Any]]:
    """Parse LLM response for code-grounded claims.

    Handles both plain JSON array and object-wrapped formats.

    Args:
        content: Raw LLM response string

    Returns:
        List of claim dicts with claim_text, claim_kind, referenced_symbols

    Raises:
        ValueError: If response cannot be parsed as valid JSON
    """
    # Strip markdown fences if present
    cleaned = content.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    parsed = json.loads(cleaned)

    # Handle both [...] and {"claims": [...]} formats
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("claims", "results", "data"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        # Try any list value
        for v in parsed.values():
            if isinstance(v, list):
                return v
    raise ValueError(f"Could not extract claims list from LLM response: {type(parsed)}")


def _generate_offline_api_claims(
    api_surface: Dict[str, Any],
    product_name: str,
) -> List[Dict[str, Any]]:
    """Generate template-based claims from API surface (offline fallback).

    Produces class-level, method-listing, and function claims using
    deterministic templates. Skips private symbols (underscore-prefixed).
    TC-1616: Caps output at 15 claims (lowered from 30) and prioritizes
    documented classes over undocumented ones.

    Args:
        api_surface: Dict with "classes", "functions", "modules" lists
        product_name: Product name for claim text

    Returns:
        List of claim dicts (max 15)
    """
    claims: List[Dict[str, Any]] = []
    cap = 15  # TC-1616: Lowered from 30 to reduce noise
    skipped_class_names: List[str] = []

    def _score_api_element_relevance(element: Dict) -> int:
        """Score API element relevance for claim generation.

        TC-1616: Elements with docstrings are much more relevant than undocumented ones.
        """
        if element.get('docstring') and len(element['docstring']) > 10:
            return 100  # Documented = high relevance
        return 10  # Undocumented = low relevance

    source_code_citation = [{
        "path": "source_code",
        "start_line": 1,
        "end_line": 1,
        "source_type": "source_code",
    }]

    # Source quality for code-grounded claims
    code_source_relevance = 80
    code_evidence_priority = "high"

    # TC-1616: Sort classes by relevance (documented first)
    classes_list = api_surface.get("classes", [])
    # Convert string format to dict format for uniform processing
    classes_normalized = []
    for cls in classes_list:
        if isinstance(cls, str):
            classes_normalized.append({"name": cls, "docstring": "", "methods": []})
        else:
            classes_normalized.append(cls)

    classes_sorted = sorted(
        classes_normalized,
        key=_score_api_element_relevance,
        reverse=True
    )

    # Class-level claims
    for cls in classes_sorted:
        if len(claims) >= cap:
            break

        # All classes are now in dict format after normalization
        name = cls.get("name", "")
        docstring = cls.get("docstring", "")

        if not name or name.startswith("_"):
            continue

        # Build purpose from docstring first sentence or generic
        if docstring:
            # First sentence: up to first period
            first_sentence = docstring.split(".")[0].strip().lower()
            if first_sentence:
                purpose = first_sentence
            else:
                purpose = f"{name.lower()} operations"
        else:
            purpose = f"{name.lower()} operations"

        # TC-1603: Skip tautological claims from classes without docstrings
        if purpose == f"{name.lower()} operations":
            skipped_class_names.append(name)
            continue

        claim_text = f"{product_name} provides the {name} class for {purpose}"
        claim_kind = "key_feature"
        claims.append({
            "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
            "claim_text": claim_text,
            "claim_kind": claim_kind,
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "source_code",
            "source_priority": 2,
            "source_relevance": code_source_relevance,
            "evidence_priority": code_evidence_priority,
            "citations": list(source_code_citation),
        })

        # Method-listing claim for classes with >2 public methods
        if len(claims) >= cap:
            break
        # All classes are now dicts after normalization
        public_methods = [m for m in cls.get("methods", []) if not m.startswith("_")]
        if len(public_methods) > 2:
            method_list = ", ".join(f"{m}()" for m in sorted(public_methods)[:5])
            method_claim_text = f"The {name} class provides methods: {method_list}"
            method_kind = "api_reference"
            claims.append({
                "claim_id": compute_claim_id(method_claim_text, method_kind, product_name),
                "claim_text": method_claim_text,
                "claim_kind": method_kind,
                "truth_status": "fact",
                "confidence": "high",
                "source_type": "source_code",
                "source_priority": 2,
                "source_relevance": code_source_relevance,
                "evidence_priority": code_evidence_priority,
                "citations": list(source_code_citation),
            })

    # TC-1603: Single aggregate claim for classes without docstrings
    # TC-1616: Also aggregate undocumented classes beyond cap
    undocumented_classes = [
        cls['name'] for cls in classes_normalized
        if not cls.get('docstring') or len(cls.get('docstring', '')) <= 10
    ]

    # If there are undocumented classes beyond what we processed, aggregate them
    if len(undocumented_classes) > cap and len(claims) < cap:
        agg_text = (
            f"{product_name} provides {len(undocumented_classes)} "
            f"additional API classes for advanced use cases"
        )
        agg_kind = "api_reference"
        claims.append({
            "claim_id": compute_claim_id(agg_text, agg_kind, product_name),
            "claim_text": agg_text,
            "claim_kind": agg_kind,
            "truth_status": "fact",
            "confidence": "medium",
            "source_type": "source_code",
            "source_priority": 2,
            "source_relevance": code_source_relevance,
            "evidence_priority": code_evidence_priority,
            "citations": list(source_code_citation),
        })
    elif skipped_class_names and len(claims) < cap:
        # Original aggregation for skipped tautological classes
        top_names = ", ".join(skipped_class_names[:5])
        suffix = f" and {len(skipped_class_names) - 5} more" if len(skipped_class_names) > 5 else ""
        agg_text = f"{product_name} provides {len(skipped_class_names)} public classes including {top_names}{suffix}"
        agg_kind = "api"
        claims.append({
            "claim_id": compute_claim_id(agg_text, agg_kind, product_name),
            "claim_text": agg_text,
            "claim_kind": agg_kind,
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "source_code",
            "source_priority": 2,
            "source_relevance": code_source_relevance,
            "evidence_priority": code_evidence_priority,
            "citations": list(source_code_citation),
        })

    # Function claims
    for func in api_surface.get("functions", []):
        if len(claims) >= cap:
            break

        # Handle both string and dict formats
        if isinstance(func, str):
            name = func
        else:
            name = func.get("name", "")

        if not name or name.startswith("_"):
            continue

        claim_text = f"{product_name} provides the {name}() function"
        claim_kind = "key_feature"
        claims.append({
            "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
            "claim_text": claim_text,
            "claim_kind": claim_kind,
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "source_code",
            "source_priority": 2,
            "source_relevance": code_source_relevance,
            "evidence_priority": code_evidence_priority,
            "citations": list(source_code_citation),
        })

    return claims


def extract_claims_from_code_analysis(
    code_analysis: Dict[str, Any],
    product_name: str,
    repo_dir: Path,
    llm_client: Optional[LLMProviderClient] = None,
) -> List[Dict[str, Any]]:
    """Generate claims from code analysis including API surface. TC-1042 / TC-1401.

    Produces version and format claims from constants (original TC-1042 behavior),
    plus code-grounded claims from the full API surface (classes, functions, modules).
    Uses LLM when available; falls back to deterministic templates offline.

    Args:
        code_analysis: Result from code_analyzer.analyze_repository_code
        product_name: Product name for normalization
        repo_dir: Repository directory path
        llm_client: Optional LLM client for richer claim generation

    Returns:
        List of claim dictionaries
    """
    claims = []

    # --- Original TC-1042: version + format claims ---

    # Source quality for code-grounded claims: source code is high-quality evidence
    # (source_priority=2 in the ranking), so assign high relevance/priority.
    code_source_relevance = 80
    code_evidence_priority = "high"

    # Version claim
    version = code_analysis.get("constants", {}).get("version")
    if version:
        claim_text = f"{product_name} version is {version}"
        claims.append({
            "claim_id": compute_claim_id(claim_text, "metadata", product_name),
            "claim_text": claim_text,
            "claim_kind": "metadata",
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "manifest",
            "source_priority": 2,
            "source_relevance": code_source_relevance,
            "evidence_priority": code_evidence_priority,
            "citations": [{
                "path": "pyproject.toml",
                "start_line": 1,
                "end_line": 1,
                "source_type": "manifest",
            }],
        })

    # Format claims from SUPPORTED_FORMATS constant
    for fmt in code_analysis.get("constants", {}).get("supported_formats", []):
        claim_text = f"{product_name} supports {fmt} format"
        claims.append({
            "claim_id": compute_claim_id(claim_text, "format", product_name),
            "claim_text": claim_text,
            "claim_kind": "format",
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "source_code",
            "source_priority": 2,
            "source_relevance": code_source_relevance,
            "evidence_priority": code_evidence_priority,
            "citations": [{
                "path": "src/__init__.py",
                "start_line": 1,
                "end_line": 1,
                "source_type": "source_code",
            }],
        })

    # --- TC-1401: Code-grounded claims from API surface ---

    api_surface = code_analysis.get("api_surface", {})
    has_api_surface = (
        api_surface.get("classes")
        or api_surface.get("functions")
        or api_surface.get("modules")
    )

    if not has_api_surface:
        return claims

    api_claims: List[Dict[str, Any]] = []

    # Try LLM path first
    if llm_client is not None:
        try:
            messages = _build_code_grounded_prompt(api_surface, product_name)
            response = llm_client.chat_completion(
                messages,
                call_id="code_grounded_claims",
                temperature=0.0,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            content = response.get("content", "")
            raw_claims = _parse_code_grounded_llm_response(content)

            source_code_citation = [{
                "path": "source_code",
                "start_line": 1,
                "end_line": 1,
                "source_type": "source_code",
            }]

            for rc in raw_claims:
                claim_text = rc.get("claim_text", "").strip()
                if not claim_text:
                    continue
                claim_kind = rc.get("claim_kind", "key_feature")
                # Normalize claim_kind to allowed values
                if claim_kind not in ("key_feature", "api_reference"):
                    claim_kind = "key_feature"
                api_claims.append({
                    "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
                    "claim_text": claim_text,
                    "claim_kind": claim_kind,
                    "truth_status": "fact",
                    "confidence": "high",
                    "source_type": "source_code",
                    "source_priority": 2,
                    "source_relevance": code_source_relevance,
                    "evidence_priority": code_evidence_priority,
                    "citations": list(source_code_citation),
                })

            logger.info(
                "code_grounded_claims_llm",
                count=len(api_claims),
                product_name=product_name,
            )
        except Exception as e:
            # LLM failed — fall through to offline path
            logger.warning(
                "code_grounded_claims_llm_failed",
                error=str(e),
                product_name=product_name,
            )
            api_claims = []

    # Offline fallback (no LLM or LLM failed)
    if not api_claims:
        api_claims = _generate_offline_api_claims(api_surface, product_name)
        logger.info(
            "code_grounded_claims_offline",
            count=len(api_claims),
            product_name=product_name,
        )

    claims.extend(api_claims)
    return claims


def extract_claims(
    repo_dir: Path,
    run_dir: Path,
    llm_client: Optional[LLMProviderClient] = None,
) -> Dict[str, Any]:
    """Extract claims from product repository.

    This is the main entry point for TC-411 claims extraction.

    Per specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract):
    - Reads discovered_docs.json and repo_inventory.json
    - Extracts claims from documentation and source code
    - Validates claim structure
    - Writes extracted_claims.json artifact

    Args:
        repo_dir: Repository directory path
        run_dir: Run directory path
        llm_client: Optional LLM client (for LLM-based extraction)

    Returns:
        Dictionary with extracted claims and metadata:
        {
            "schema_version": "1.0.0",
            "repo_url": str,
            "repo_sha": str,
            "product_name": str,
            "claims": List[Dict],
            "metadata": {
                "total_claims": int,
                "fact_claims": int,
                "inference_claims": int,
                "claim_kinds": Dict[str, int]
            }
        }

    Raises:
        ClaimsExtractionError: If extraction fails
        FileNotFoundError: If required artifacts are missing

    Spec references:
    - specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
    - specs/03_product_facts_and_evidence.md (Claims extraction algorithm)
    - specs/04_claims_compiler_truth_lock.md (Claim structure)
    """
    run_layout = RunLayout(run_dir=run_dir)

    # Load discovered_docs.json
    discovered_docs_path = run_layout.artifacts_dir / "discovered_docs.json"
    if not discovered_docs_path.exists():
        raise FileNotFoundError(
            f"discovered_docs.json not found: {discovered_docs_path}"
        )

    with open(discovered_docs_path, 'r', encoding='utf-8') as f:
        discovered_docs = json.load(f)

    # Load repo_inventory.json
    repo_inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
    if not repo_inventory_path.exists():
        raise FileNotFoundError(
            f"repo_inventory.json not found: {repo_inventory_path}"
        )

    with open(repo_inventory_path, 'r', encoding='utf-8') as f:
        repo_inventory = json.load(f)

    # Load code_analysis.json (TC-1042, TC-1401)
    code_analysis_path = run_layout.artifacts_dir / "code_analysis.json"
    code_analysis = {}
    if code_analysis_path.exists():
        with open(code_analysis_path, 'r', encoding='utf-8') as f:
            code_analysis = json.load(f)
    else:
        logger.info(
            "code_analysis_not_found",
            message="code_analysis.json not found, skipping code-grounded claims",
        )

    # Extract metadata
    repo_url = repo_inventory.get('repo_url', '')
    repo_sha = repo_inventory.get('repo_sha', '')
    product_name = repo_inventory.get('product_name', repo_url.split('/')[-1].replace('.git', ''))

    # Get doc files
    doc_entrypoint_details = discovered_docs.get('doc_entrypoint_details', [])

    if len(doc_entrypoint_details) == 0:
        logger.warning(
            "zero_docs_found",
            repo_url=repo_url,
            message="No documentation files found. Proceeding with empty claims."
        )

    # Extract claims
    if llm_client:
        # Use LLM-based extraction
        try:
            claims = extract_claims_with_llm(
                doc_entrypoint_details,
                repo_dir,
                product_name,
                llm_client,
            )
        except LLMError as e:
            raise ClaimsExtractionError(f"LLM extraction failed: {e}") from e
    else:
        # Use heuristic extraction (no LLM)
        claims = []
        for doc_file in doc_entrypoint_details:
            file_path = repo_dir / doc_file['path']
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            except Exception as e:
                logger.warning("doc_read_error", path=str(file_path), error=str(e))
                continue

            # Source quality metadata from W1 discovery
            doc_relevance = doc_file.get('relevance_score', 50)
            doc_evidence_priority = doc_file.get('evidence_priority', 'medium')

            candidates = extract_candidate_statements_from_text(
                content, file_path, repo_dir
            )

            for candidate in candidates:
                claim_kind = classify_claim_kind(candidate['claim_text'])
                claim_id = compute_claim_id(
                    candidate['claim_text'], claim_kind, product_name
                )
                source_type = candidate['source_type']
                source_priority = determine_source_priority(source_type)

                truth_status = 'fact' if source_priority <= 3 else 'inference'

                claim = {
                    'claim_id': claim_id,
                    'claim_text': candidate['claim_text'],
                    'claim_kind': claim_kind,
                    'truth_status': truth_status,
                    'confidence': 'high' if source_priority <= 2 else 'medium' if source_priority <= 5 else 'low',
                    'source_type': source_type,
                    'source_priority': source_priority,
                    'source_relevance': doc_relevance,
                    'evidence_priority': doc_evidence_priority,
                    'citations': [{
                        'path': candidate['source_file'],
                        'start_line': candidate['start_line'],
                        'end_line': candidate['end_line'],
                        'source_type': source_type,
                    }],
                }

                claims.append(claim)

    # TC-1502: Extract structured section claims from README files
    total_section_claims = 0
    for doc_file in doc_entrypoint_details:
        file_path = repo_dir / doc_file['path']
        path_lower = str(file_path).lower()
        # Only process README and documentation files
        if not any(marker in path_lower for marker in ['readme', 'getting_started', 'install', 'quickstart']):
            continue
        if not file_path.exists():
            continue
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        doc_relevance = doc_file.get('relevance_score', 50)
        doc_evidence_priority = doc_file.get('evidence_priority', 'medium')

        section_candidates = extract_structured_sections_from_readme(
            content, file_path, repo_dir, product_name
        )
        for candidate in section_candidates:
            # Use section_kind to override claim classification if available
            section_kind = candidate.get('section_kind')
            claim_kind = section_kind if section_kind == 'workflow' else classify_claim_kind(candidate['claim_text'])
            claim_id = compute_claim_id(candidate['claim_text'], claim_kind, product_name)
            source_priority = determine_source_priority(candidate['source_type'])

            claim_dict = {
                'claim_id': claim_id,
                'claim_text': candidate['claim_text'],
                'claim_kind': claim_kind,
                'truth_status': 'fact' if source_priority <= 3 else 'inference',
                'confidence': 'high' if source_priority <= 2 else 'medium',
                'source_type': candidate['source_type'],
                'source_priority': source_priority,
                'source_relevance': doc_relevance,
                'evidence_priority': doc_evidence_priority,
                'citations': [{
                    'path': candidate['source_file'],
                    'start_line': candidate['start_line'],
                    'end_line': candidate['end_line'],
                    'source_type': candidate['source_type'],
                }],
            }

            # Preserve step_order for workflow claims (TC-1610)
            if 'step_order' in candidate:
                claim_dict['step_order'] = candidate['step_order']

            claims.append(claim_dict)
            total_section_claims += 1

    if total_section_claims > 0:
        logger.info(
            "structured_section_claims_added",
            count=total_section_claims,
            product_name=product_name,
        )

    # Add code-grounded claims from API surface (TC-1401)
    if code_analysis:
        try:
            code_claims = extract_claims_from_code_analysis(
                code_analysis=code_analysis,
                product_name=product_name,
                repo_dir=repo_dir,
                llm_client=llm_client,
            )
            claims.extend(code_claims)
            logger.info(
                "code_grounded_claims_added",
                count=len(code_claims),
                product_name=product_name,
            )
        except Exception as e:
            logger.warning(
                "code_grounded_claims_failed",
                error=str(e),
                product_name=product_name,
            )
            # Continue without code claims (not critical)

    # Deduplicate claims
    claims = deduplicate_claims(claims)

    # TC-1613: Ensure 100% source_type coverage as a safety net.
    # All claim creation paths above should set source_type, but this
    # catches any edge cases (e.g. future paths that forget to set it).
    for claim in claims:
        if not claim.get('source_type'):
            # Try to derive from the first citation's source_type
            citations = claim.get('citations', [])
            if citations and citations[0].get('source_type'):
                claim['source_type'] = citations[0]['source_type']
            else:
                # Fallback: derive from source file path
                src_path = citations[0].get('path', '') if citations else ''
                if src_path:
                    claim['source_type'] = determine_source_type(
                        Path(src_path), repo_dir
                    )
                else:
                    claim['source_type'] = 'unknown'

    # Validate all claims
    for claim in claims:
        try:
            validate_claim_structure(claim)
        except ClaimsValidationError as e:
            logger.error("claim_validation_failed", claim_id=claim.get('claim_id'), error=str(e))
            raise

    # Sort deterministically
    claims = sort_claims_deterministically(claims)

    # Compute metadata
    fact_claims = [c for c in claims if c['truth_status'] == 'fact']
    inference_claims = [c for c in claims if c['truth_status'] == 'inference']

    claim_kinds = {}
    for claim in claims:
        kind = claim['claim_kind']
        claim_kinds[kind] = claim_kinds.get(kind, 0) + 1

    # Build result
    result = {
        'schema_version': '1.0.0',
        'repo_url': repo_url,
        'repo_sha': repo_sha,
        'product_name': product_name,
        'claims': claims,
        'metadata': {
            'total_claims': len(claims),
            'fact_claims': len(fact_claims),
            'inference_claims': len(inference_claims),
            'claim_kinds': claim_kinds,
        },
    }

    # Write artifact
    output_path = run_layout.artifacts_dir / "extracted_claims.json"
    atomic_write_json(output_path, result)

    logger.info(
        "claims_extracted",
        total_claims=len(claims),
        fact_claims=len(fact_claims),
        inference_claims=len(inference_claims),
        claims_extracted_count=len(claims),
        docs_processed_count=len(doc_entrypoint_details),
        output_path=str(output_path),
    )

    return result
