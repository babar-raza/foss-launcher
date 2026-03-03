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

# Lazy-loaded prompt loader for centralized prompts (TC-1712)
_prompt_loader = None


def _get_prompt_loader():
    """Return a cached PromptLoader instance, or None if unavailable."""
    global _prompt_loader
    if _prompt_loader is None:
        try:
            from launch.prompts import PromptLoader
            _prompt_loader = PromptLoader()
        except Exception:
            pass
    return _prompt_loader


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


def _sanitize_claim_text(text: str) -> str:
    """TC-1901: Strip code fence markers from claim text.

    W2 install_steps and other claims sometimes contain literal ```bash or
    ```python markers from README code blocks. These nest inside templates
    when W4/W5 embed claim text in token values, causing broken fences.
    """
    # Strip opening fence markers (```bash, ```python, ```, etc.)
    text = re.sub(r'```\w*\n?', '', text)
    # Strip closing fence markers
    text = re.sub(r'\n```\s*', ' ', text)
    # Collapse whitespace
    text = re.sub(r'  +', ' ', text)
    return text.strip()


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

    # TC-2335: Best practice detection
    bp_strong = {"best practice", "recommended", "avoid", "never", "always use"}
    bp_weak = {"prefer", "instead of", "rather than", "should not", "guideline", "tip"}
    if any(kw in text_lower for kw in bp_strong):
        return "best_practice"
    if sum(1 for kw in bp_weak if kw in text_lower) >= 2:
        return "best_practice"

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


_MULTI_STMT_RE = re.compile(
    r'(?:^|\n)\s*(?:\w+\s*=\s*\w+|print\s*\(|assert\s+\w+|raise\s+\w+)',
    re.MULTILINE,
)


def _is_code_like(text: str) -> bool:
    """Detect if text is source code rather than natural language.

    Checks for common programming patterns that indicate the text
    was extracted from source code rather than documentation prose.

    Args:
        text: Candidate claim text

    Returns:
        True if text appears to be source code
    """
    # Multi-statement Python code (e.g., "has_normals = True\nprint(has_normals)")
    if len(_MULTI_STMT_RE.findall(text)) >= 2:
        return True
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
        r'^""".*"""$',           # TC-2302: Docstring wrapped in triple quotes
        r"^'''.*'''$",           # TC-2302: Single-quote docstring
        r'^\s*"""',              # TC-2302: Starts with triple-quote docstring marker
        r"^\s*'''",              # TC-2302: Starts with single-quote docstring marker
        r'^(int|str|bool|float|list|dict|tuple|None):\s',  # TC-2302: Type annotation at start
        r'->\s*(int|str|bool|float|list|dict|tuple|None)\b',  # TC-2302: Return type hint
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
    # TC-2302: Docstring marker at start is unambiguous code artifact
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return True
    # TC-2302: Type annotation prefix (e.g. "int: The number of...")
    if re.match(r'^(int|str|bool|float|list|dict|tuple|None):\s', stripped):
        return True
    # TC-2334: Parameter description is unambiguous code artifact
    if _is_parameter_description(stripped):
        return True
    # TC-RCA: raise ExceptionClass(...) with arguments is unambiguous code
    if re.match(r'^raise\s+\w+\s*\(', stripped):
        return True
    # TC-RCA: ExceptionClass instantiation (e.g., FormatError("bad"))
    if re.match(r'^\w+(Error|Exception)\s*\(', stripped):
        return True
    # If >25% non-alphabetic characters (brackets, dots, parens), likely code
    # TC-1616: Lowered from 0.40 to 0.25 to catch API descriptions like
    # "Scene.render(width, height, options)" which have ~38% non-alpha
    non_alpha = sum(1 for c in text if not c.isalpha() and not c.isspace())
    if len(text) > 20 and non_alpha / len(text) > 0.25:
        return True
    return False


def _is_implementation_detail(text: str) -> bool:
    """Detect if text describes internal implementation rather than user-facing behavior.

    TC-1731: Catches low-level code constructs that leaked through _is_code_like()
    but are still too implementation-specific for user documentation.

    Args:
        text: Candidate claim text

    Returns:
        True if text describes internal implementation details
    """
    impl_patterns = [
        r'\breturn\s+\w+\(',          # return SomeClass()
        r'\bisinstance\s*\(',          # isinstance() checks
        r'__\w+__',                     # __dunder__ methods
        r'\braise\s+(TypeError|ValueError|AttributeError|RuntimeError)',  # raise specific errors
        r'\bself\._\w+',              # self._private access
        r'\btry\s*:.*except',          # try/except blocks
        r'\bsuper\(\)\.\w+',          # super() calls
        r'\b_\w+\s*\(',              # _private_function() calls
        r'\btype\s*\(\s*\w+\s*\)',    # type() checks
        r'\bhasattr\s*\(',            # hasattr() checks
        r'\bgetattr\s*\(',            # getattr() calls
        r'\b@(staticmethod|classmethod|property)',  # decorators
        r'^""".*"""$',                 # TC-2302: Docstring (start to end)
        r'^(int|str|bool|float):\s',  # TC-2302: Type annotation prefix
        r'^(Gets?|Sets?)\s+(or\s+)?(gets?|sets?)\s+(the|a|an)\s',  # TC-2302: Property getter/setter prose
        r'^docProps/',                 # TC-2302: XML path (not user-facing)
        r'^xl/',                       # TC-2302: Excel XML path
    ]
    matches = sum(1 for p in impl_patterns if re.search(p, text))
    if matches >= 2:
        return True
    # TC-2302: Single strong indicators — unambiguous impl details
    stripped = text.strip()
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return True
    if re.match(r'^(int|str|bool|float|list|dict|tuple|None):\s', stripped):
        return True
    if re.match(r'^docProps/', stripped) or re.match(r'^xl/', stripped):
        return True
    # TC-2334: Parameter descriptions are implementation details
    if _is_parameter_description(stripped):
        return True
    return False


def _is_parameter_description(text: str) -> bool:
    """Detect function/method parameter descriptions.

    TC-2334: Catches parameter documentation lines that leak through
    other filters but are not user-facing claims.

    Catches: "bold (bool, optional): Sets text bold"
             "Font (CellsFont): The font object"
             "H_n if password is correct, None otherwise"

    Args:
        text: Candidate claim text

    Returns:
        True if text appears to be a parameter description
    """
    stripped = text.strip()
    # Pattern 1: name (type_annotation): description
    # e.g. "bold (bool, optional): Sets text to bold"
    if re.match(r'^\w+\s*\((?:int|str|bool|float|list|dict|tuple|None|Any|Optional|object)\b[^)]*\)\s*:', stripped):
        return True
    # Pattern 2: name (ClassName): description
    # e.g. "Font (CellsFont): The font object"
    if re.match(r'^\w+\s*\([A-Z]\w+\)\s*:', stripped):
        return True
    # Pattern 3: Variable_name if condition, else value
    # e.g. "H_n if password is correct, None otherwise"
    if re.match(r'^[A-Z]_\w+\s+if\s+', stripped):
        return True
    return False


def _is_target_language(text: str, target: str = "en") -> bool:
    """Check if text is in the target language (default: English).

    TC-1700: Block non-English text from entering the claims pipeline.
    Uses character-range detection (no external dependencies).

    Args:
        text: Candidate claim text
        target: Target language code (only "en" supported)

    Returns:
        True if text appears to be in the target language
    """
    if not text or len(text) < 3:
        return False

    # Count characters in non-Latin script ranges
    cyrillic_count = 0
    cjk_count = 0
    arabic_count = 0
    non_ascii_count = 0
    total_alpha = 0

    for ch in text:
        code = ord(ch)
        if ch.isalpha():
            total_alpha += 1
        if code > 127:
            non_ascii_count += 1
        # Cyrillic: U+0400-U+04FF
        if 0x0400 <= code <= 0x04FF:
            cyrillic_count += 1
        # CJK Unified Ideographs: U+4E00-U+9FFF
        elif 0x4E00 <= code <= 0x9FFF:
            cjk_count += 1
        # Arabic: U+0600-U+06FF
        elif 0x0600 <= code <= 0x06FF:
            arabic_count += 1

    # Hard reject if significant non-Latin script content
    if cyrillic_count > 5:
        return False
    if cjk_count > 3:
        return False
    if arabic_count > 5:
        return False

    # Soft reject if >15% of characters are non-ASCII
    if total_alpha > 0 and non_ascii_count / max(len(text), 1) > 0.15:
        return False

    return True


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

    # TC-1700: Reject non-English text before further analysis
    if not _is_target_language(text):
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
    # TC-RCA: Reject text containing raise Exception(...) anywhere
    if re.search(r'\braise\s+\w+\(', text):
        return False
    return True


def _is_spec_fragment(text: str) -> bool:
    """Detect RFC/specification fragment claims that should not appear in user-facing docs.

    TC-1820: Block claims containing RFC-2119 capitals (MUST, SHOULD, MAY etc.),
    specification language, or formal definitions that read as spec text rather
    than user-facing documentation.

    Args:
        text: Candidate claim text

    Returns:
        True if the text appears to be a specification fragment
    """
    # RFC-2119 uppercase keywords (only match standalone uppercase words)
    rfc_keywords = re.findall(
        r'\b(MUST NOT|MUST|SHALL NOT|SHALL|SHOULD NOT|SHOULD|MAY|REQUIRED|OPTIONAL|RECOMMENDED)\b',
        text,
    )
    if len(rfc_keywords) >= 1:
        return True

    text_lower = text.lower()
    # Specification language patterns
    spec_phrases = [
        'this specification',
        'as specified in',
        'this structure does not define',
        'unless otherwise specified',
        'as defined in',
        'the specification does not',
        'this document defines',
        'normative reference',
        'informative reference',
        'this field specifies',
        'this value indicates',
    ]
    if any(phrase in text_lower for phrase in spec_phrases):
        return True

    # Formal definition patterns (e.g., "globally unique identifier (GUID)")
    # that define terminology rather than describe user-facing behavior
    if re.match(r'^[a-z]', text) and '(' in text and ')' in text:
        # Starts lowercase with parenthetical definition — likely a glossary entry
        if re.search(r'\([A-Z]{2,}\)', text):
            return True

    # ── TC-3672: Extended patterns from pilot review evidence ────────────
    # Binary format terms observed in Note pilot (JCID, CompactID, etc.)
    if re.search(
        r'\b(?:JCID|FNDX?|CompactID|rgIndents|ObjectDeclaration)\b', text
    ):
        return True
    # Binary storage/structure terms
    if re.search(
        r'\b(?:transaction\s+log|free\s+chunk\s+list|hashed\s+chunk\s+list)\b',
        text, re.IGNORECASE,
    ):
        return True
    # Byte-order encoding terms
    if re.search(
        r'\b(?:little[.-]endian|big[.-]endian)\s+(?:encoding|byte\s+order)\b',
        text, re.IGNORECASE,
    ):
        return True
    # Hex constants (4+ hex digits)
    if re.search(r'0x[0-9A-Fa-f]{4,}', text):
        return True
    # Spec section references (e.g., "section 2.2.1.3")
    if re.search(r'\bsection\s+\d+\.\d+\.\d+', text, re.IGNORECASE):
        return True

    # ── TC-3683: Backport 7 gate G7 patterns missing from W2 classifier ──
    # Binary format structures
    if re.search(r'\bObject\s+Data\s+BLOB\b', text, re.IGNORECASE):
        return True
    if re.search(r'\bRgOutlineIndentDistance\b', text):
        return True
    # Encoding terms
    if re.search(r'\bcp1252\b', text, re.IGNORECASE):
        return True
    # RFC / protocol standards
    if re.search(r'\bRFC\s+4122\b', text):
        return True
    if re.search(r'\bC706\b', text):
        return True
    # Binary field descriptors
    if re.search(r'\bunsigned\s+\d+-bit\s+integer\b', text, re.IGNORECASE):
        return True
    if re.search(r'\bIsFileData\b', text):
        return True

    return False


# ── TC-3672: Patent/internal email pattern ───────────────────────────────
_PATENT_EMAIL_RE = re.compile(r'\biplg@microsoft\.com\b', re.IGNORECASE)


def classify_claim_visibility(claim_text: str, claim_kind: str) -> str:
    """Classify claim visibility as 'public' or 'internal'.

    TC-3672: Deterministic classification based on content patterns.
    Internal claims contain spec fragments, hex constants, binary format terms,
    spec section references, or patent emails.

    Args:
        claim_text: Claim text to classify.
        claim_kind: Claim kind (from classify_claim_kind).

    Returns:
        'public' or 'internal'.

    Spec: specs/03_product_facts_and_evidence.md §Claim Visibility (TC-3672)
    """
    if _is_spec_fragment(claim_text):
        return 'internal'
    if _PATENT_EMAIL_RE.search(claim_text):
        return 'internal'
    return 'public'


def _is_spec_header(claim_text: str) -> bool:
    """Detect claims that appear to be specification section headers, not real product claims.

    TC-1840: These produce malformed slugs in W4 and should be filtered out.

    Examples of spec headers to reject:
        "11 Section 3: In cases where this document..."
        "3.2.1 Format conversion capabilities"
        "Section 5 - Error handling procedures"
        "A.1 Appendix: Configuration options"

    Examples of valid claims to keep:
        "Supports converting 3D models between FBX and OBJ formats"
        "The library can load scenes from files or streams"

    Args:
        claim_text: Candidate claim text

    Returns:
        True if text appears to be a specification section header
    """
    text = claim_text.strip()

    # Pattern 1: Starts with section numbering (e.g., "11 Section 3:", "3.2.1 Format", "<11> Section 3:")
    if re.match(r'^<?(\d+)>?[\s.)\-]+(?:Section\s+)?\d*', text, re.IGNORECASE):
        return True

    # Pattern 2: Starts with appendix-style numbering (e.g., "A.1 Appendix:")
    if re.match(r'^[A-Z]\.\d+\s', text):
        return True

    # Pattern 3: Starts with "Section X" (header-style)
    # Matches "Section 5:", "Section 5 -", "Section 5 Error handling"
    if re.match(r'^Section\s+\d+', text, re.IGNORECASE):
        return True

    # Pattern 4: Starts with "In cases where" — often from spec conditional language
    if text.lower().startswith("in cases where"):
        return True

    return False


def _normalize_claim_text_for_slug(claim_text: str) -> str:
    """Normalize claim text by stripping section numbering and preamble phrases.

    TC-1841: This runs AFTER claim extraction but BEFORE claims are stored
    in product_facts. The original claim_text is preserved; this produces a
    'normalized_text' field used for slug/title generation.

    Args:
        claim_text: Raw claim text

    Returns:
        Normalized claim text suitable for slug/title generation
    """
    text = claim_text.strip()

    # Strip leading section numbers: "11 Section 3: " -> ""
    text = re.sub(
        r'^\d+[\s.)\-:]+(?:Section\s+\d+[\s:.\-]*)?',
        '', text, flags=re.IGNORECASE
    ).strip()

    # Strip leading preamble phrases
    preamble_patterns = [
        r'^In cases where\s+',
        r'^When you need to\s+',
        r'^It is possible to\s+',
        r'^You can use\s+',
        r'^This allows you to\s+',
        r'^The library provides\s+',
        r'^It should be noted that\s+',
    ]
    for pattern in preamble_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()

    # Strip leading articles after cleanup
    text = re.sub(r'^(?:the|a|an)\s+', '', text, flags=re.IGNORECASE).strip()

    return text or claim_text  # Fallback to original if everything was stripped


def _is_noun_phrase_claim(text: str) -> bool:
    """Accept short noun-phrase claims that describe features/formats.

    Examples: "CSV and JSON format support", "Python 3.8+ compatibility"

    TC-RCA: Tightened to reject text where the noun appears only inside
    a PascalCase identifier (e.g., FormatError) or code patterns.
    """
    # Reject if text contains error/exception class identifiers
    if re.search(r'\b\w+(Error|Exception)\b', text):
        return False
    # Reject if text contains function call patterns
    if re.search(r'\w+\(', text) and re.search(r'\)', text):
        return False
    text_lower = text.lower()
    feature_nouns = {
        'support', 'compatibility', 'integration', 'conversion', 'processing',
        'management', 'handling', 'rendering', 'format',
        'configuration', 'validation', 'optimization', 'feature',
        'version', 'platform', 'python',
    }
    # Require word boundary match — prevents matching "format" inside "formaterror"
    return any(re.search(rf'\b{noun}\b', text_lower) for noun in feature_nouns)


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


def _build_heading_map(lines: List[str]) -> Dict[int, str]:
    """Map each 1-based line number to the slug of the nearest Markdown heading above it.

    TC-2365: Provides source_section metadata for extracted claims so downstream
    workers can do section-matched claim assignment rather than keyword guessing.

    Args:
        lines: File lines (0-indexed list, mapped to 1-based line numbers internally)

    Returns:
        Dict mapping line_number (1-based) → heading slug (e.g., "getting-started").
        Returns "" for lines that appear before the first heading.
    """
    heading_map: Dict[int, str] = {}
    current_heading_slug = ""
    in_code_block = False
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
        if not in_code_block:
            m = re.match(r"^#{1,3}\s+(.+)$", stripped)
            if m:
                current_heading_slug = re.sub(
                    r"[^a-z0-9]+", "-", m.group(1).strip().lower()
                ).strip("-")
        heading_map[line_num] = current_heading_slug
    return heading_map


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
        - source_section: Slug of the nearest Markdown heading above the claim (TC-2365)

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

    # TC-2365: Build heading map before sentence extraction
    heading_map = _build_heading_map(lines)

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
                and not _is_parameter_description(sentence)  # TC-2334
                and (_is_prose_like(sentence) or _is_noun_phrase_claim(sentence))
                and not identifier_heavy
                and not _is_spec_fragment(sentence)  # TC-1820
                and not _is_spec_header(sentence)  # TC-1840
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
                    'source_section': heading_map.get(start_line, ""),  # TC-2365
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
            and not _is_parameter_description(bullet_text)  # TC-2334
            and (_is_prose_like(bullet_text) or _is_noun_phrase_claim(bullet_text))
            and not _is_spec_fragment(bullet_text)  # TC-1820
            and not _is_spec_header(bullet_text)  # TC-1840
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
                'source_section': heading_map.get(line_num, ""),  # TC-2365
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
    # Best practices and performance (TC-1620)
    'best practices': 'best_practice',
    'best practice': 'best_practice',
    'tips': 'best_practice',
    'optimization': 'best_practice',
    'performance': 'performance',
    'performance tips': 'best_practice',
    'anti patterns': 'best_practice',
    'anti-patterns': 'best_practice',
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


def _is_valid_troubleshooting_claim(text: str) -> bool:
    """Validate that a claim describes a real troubleshooting problem, not a spec fragment.

    TC-1701: Ensure troubleshooting/limitation claims are actionable problems,
    not spec field definitions, hex offsets, or type descriptions.

    Args:
        text: Candidate troubleshooting claim text

    Returns:
        True if text describes a real problem or limitation
    """
    if not text or len(text.split()) < 10:
        return False  # Too short to be actionable

    # Reject spec-field patterns: "FileNode.header: 0x8D..."
    if re.match(r'^[A-Z]\w+\.\w+:?\s', text):
        return False

    # Reject type/field definitions: "field_name = value_type"
    if re.match(r'^\w+\s*[=:]\s*\w+', text) and len(text.split()) < 12:
        return False

    # Reject hex offset patterns: "0x8D0044A4", "offset 0x100"
    if re.search(r'0x[0-9A-Fa-f]{4,}', text):
        return False

    # Reject byte/header spec patterns
    if re.search(r'\b(byte \d+|header:|offset:|specifies that the)', text, re.IGNORECASE):
        return False

    # Must contain at least one problem indicator
    problem_indicators = (
        r'\b(error|fail|issue|cannot|unable|crash|exception|timeout|incorrect|'
        r'missing|broken|slow|incompatib|deprecat|unsupport|not (yet )?supported|'
        r'not (yet )?implement|known (issue|bug|limitation)|workaround|'
        r"limitation|problem|warning|doesn't|don't|won't|can't|could not)\b"
    )
    if not re.search(problem_indicators, text, re.IGNORECASE):
        return False

    return True


# TC-1704: Performance Claim Extraction
_PERFORMANCE_INDICATORS = re.compile(
    r'\b(benchmark|speed|throughput|latency|memory|cpu|gpu|optimiz|cache|batch|'
    r'parallel|concurrent|scalab|performance|faster|slower|efficient|overhead|'
    r'profil|resource|footprint|millisecond|runtime)\b',
    re.IGNORECASE,
)


def _extract_performance_claims(text: str, source_file: str, product_name: str = "") -> List[Dict]:
    """Extract performance-related claims from documentation text.

    TC-1704: Pattern-match for performance indicators and extract surrounding
    sentences as performance claims.

    Args:
        text: Documentation text to extract from
        source_file: Source file path for citation
        product_name: Product name for context

    Returns:
        List of claim dicts with claim_kind='performance'
    """
    claims = []
    seen_texts = set()

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence.split()) < 8:
            continue  # Too short
        if not _PERFORMANCE_INDICATORS.search(sentence):
            continue
        if _is_code_like(sentence):
            continue
        if not _is_prose_like(sentence):
            continue

        # Normalize for dedup
        norm = sentence.lower().strip()
        if norm in seen_texts:
            continue
        seen_texts.add(norm)

        claims.append({
            'claim_text': sentence,
            'claim_kind': 'performance',
            'section_kind': 'performance',
            'source_type': 'documentation',
            'source_file': source_file,
            'start_line': 0,
            'end_line': 0,
            'keyword_boost': True,
        })

        if len(claims) >= 10:  # Cap per source file
            break

    return claims


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
                # TC-1701: Add troubleshooting quality gate
                if (len(context.split()) >= MIN_CLAIM_WORDS
                        and not _is_code_like(context)
                        and _is_valid_troubleshooting_claim(context)):
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


def _extract_best_practice_statements(
    text: str,
    section_heading: str,
    source_file: str,
    section_start: int,
    section_end: int,
    source_type: str,
    product_name: str,
) -> List[Dict]:
    """Extract best practice recommendations from text.

    TC-1620: Extracts optimization guides and best practices from README.

    Looks for:
    - Imperative statements ("Use X", "Avoid Y", "Always Z")
    - Recommendation patterns ("It is recommended to...", "Best practice is...")
    - Anti-pattern warnings ("Do not...", "Never...")

    Categorizes by type: memory, speed, correctness

    Args:
        text: Section text content
        section_heading: Section name (e.g., "Best Practices", "Tips")
        source_file: Relative source file path
        section_start: Starting line number
        section_end: Ending line number
        source_type: Source type (readme_technical, etc.)
        product_name: Product name for claim text

    Returns:
        List of best practice claim dicts
    """
    practices = []

    # Imperative patterns
    imperative_patterns = [
        r'\b(use|avoid|always|never|ensure|prefer|consider)\s+([^.!?\n]+[.!?])',
        r'\b(recommended|best practice|suggested)\s+to\s+([^.!?\n]+[.!?])',
        r'\b(do not|don\'t|should not|shouldn\'t)\s+([^.!?\n]+[.!?])',
        r'\b(make sure|be sure|remember)\s+to\s+([^.!?\n]+[.!?])',
    ]

    lines = text.split('\n')
    for line_num_offset, line in enumerate(lines):
        stripped = line.strip()

        # Skip empty lines and headings
        if not stripped or stripped.startswith('#'):
            continue

        # Try each pattern
        for pattern in imperative_patterns:
            matches = re.finditer(pattern, stripped, re.IGNORECASE)
            for match in matches:
                statement = match.group(0).strip()

                # Minimum length check
                if len(statement.split()) < MIN_CLAIM_WORDS:
                    continue

                # Skip if code-like
                if _is_code_like(statement):
                    continue

                # Categorize by keywords (order matters: check speed first)
                category = 'correctness'  # default
                statement_lower = statement.lower()
                if any(kw in statement_lower for kw in ['fast', 'slow', 'optim', 'perform', 'speed', 'latency', 'cache']):
                    category = 'speed'
                elif any(kw in statement_lower for kw in ['memory', 'allocate', 'buffer', 'leak']):
                    category = 'memory'

                practices.append({
                    'claim_text': statement,
                    'claim_kind': 'best_practice',
                    'section_kind': 'best_practice',
                    'category': category,
                    'source_file': source_file,
                    'start_line': section_start + line_num_offset,
                    'end_line': section_start + line_num_offset,
                    'source_type': source_type,
                    'keyword_boost': True,
                })

    return practices


def _infer_best_practices_from_code(
    code_content: str,
    source_file: str,
    product_name: str,
    source_type: str = 'source_code',
) -> List[Dict]:
    """Infer best practices from code patterns.

    TC-1620: Detects common patterns in source code that indicate best practices.

    Detects:
    - Context managers (with statements) → "Use with-statements for file handling"
    - Caching decorators (@lru_cache, @cache) → "Cache expensive computations"
    - Thread locks (threading.Lock) → "Thread safety considerations"
    - Try-except blocks (if frequent) → "Handle exceptions gracefully"

    Args:
        code_content: Python source code content
        source_file: Relative source file path
        product_name: Product name for claim text
        source_type: Source type (default: source_code)

    Returns:
        List of best practice claim dicts
    """
    practices = []

    # Pattern 1: Context managers (with statements)
    with_pattern = r'\bwith\s+(open\(|[\w.]+\()'
    with_matches = re.findall(with_pattern, code_content)
    if len(with_matches) >= 2:  # Minimum threshold
        practices.append({
            'claim_text': f"Use with-statements for resource management to ensure proper cleanup when working with {product_name}",
            'claim_kind': 'best_practice',
            'section_kind': 'best_practice',
            'category': 'correctness',
            'source_type': source_type,
            'source_file': source_file,
            'start_line': 0,
            'end_line': 0,
            'keyword_boost': True,
        })

    # Pattern 2: Caching decorators
    cache_pattern = r'@(lru_cache|cache|cached|memoize)'
    if re.search(cache_pattern, code_content):
        practices.append({
            'claim_text': f"Cache expensive computations using decorators for improved performance with {product_name}",
            'claim_kind': 'best_practice',
            'section_kind': 'best_practice',
            'category': 'speed',
            'source_type': source_type,
            'source_file': source_file,
            'start_line': 0,
            'end_line': 0,
            'keyword_boost': True,
        })

    # Pattern 3: Thread locks (thread safety)
    lock_pattern = r'threading\.(Lock|RLock|Semaphore)|from threading import'
    if re.search(lock_pattern, code_content):
        practices.append({
            'claim_text': f"Consider thread safety when using {product_name} in multi-threaded applications",
            'claim_kind': 'best_practice',
            'section_kind': 'best_practice',
            'category': 'correctness',
            'source_type': source_type,
            'source_file': source_file,
            'start_line': 0,
            'end_line': 0,
            'keyword_boost': True,
        })

    # Pattern 4: Exception handling (if frequent)
    try_pattern = r'\btry\s*:'
    exception_count = len(re.findall(try_pattern, code_content))
    if exception_count >= 3:
        practices.append({
            'claim_text': f"Handle exceptions gracefully when working with {product_name} APIs",
            'claim_kind': 'best_practice',
            'section_kind': 'best_practice',
            'category': 'correctness',
            'source_type': source_type,
            'source_file': source_file,
            'start_line': 0,
            'end_line': 0,
            'keyword_boost': True,
        })

    return practices


def _extract_performance_characteristics(
    test_content: str,
    source_file: str,
    product_name: str,
) -> List[Dict]:
    """Extract performance characteristics from test files.

    TC-1620: Extracts performance benchmarks and scalability limits from tests.

    Looks for:
    - Benchmark test results (test_benchmark_X)
    - Performance assertions (assert time < 1.0)
    - Scalability limits in fixtures (max_items=10000)

    Args:
        test_content: Test file content
        source_file: Relative source file path
        product_name: Product name for claim text

    Returns:
        List of performance characteristic claim dicts
    """
    characteristics = []

    # Pattern 1: Benchmark tests
    benchmark_pattern = r'def\s+test_benchmark_(\w+)'
    matches = re.finditer(benchmark_pattern, test_content)
    for match in matches:
        operation = match.group(1)
        # Convert snake_case to readable text
        operation_readable = operation.replace('_', ' ')
        characteristics.append({
            'claim_text': f"{product_name} performance for {operation_readable} has been benchmarked",
            'claim_kind': 'performance',
            'section_kind': 'performance',
            'metric': operation,
            'source_type': 'test',
            'source_file': source_file,
            'start_line': 0,
            'end_line': 0,
            'keyword_boost': True,
        })

    # Pattern 2: Performance assertions (time-based)
    time_pattern = r'assert\s+(\w*time\w*|\w*duration\w*)\s*<\s*([\d.]+)'
    matches = re.finditer(time_pattern, test_content, re.IGNORECASE)
    for match in matches:
        variable = match.group(1)
        threshold = match.group(2)
        characteristics.append({
            'claim_text': f"{product_name} operations complete in under {threshold} seconds",
            'claim_kind': 'performance',
            'section_kind': 'performance',
            'metric': variable,
            'value': threshold,
            'source_type': 'test',
            'source_file': source_file,
            'start_line': 0,
            'end_line': 0,
            'keyword_boost': True,
        })

    # Pattern 3: Scalability limits
    limit_pattern = r'\b(max_\w+|limit)\s*=\s*(\d+)'
    matches = re.finditer(limit_pattern, test_content)
    for match in matches:
        limit_name = match.group(1)
        limit_value = match.group(2)
        # Skip very small values (likely not scalability limits)
        if int(limit_value) < 100:
            continue
        limit_readable = limit_name.replace('_', ' ')
        characteristics.append({
            'claim_text': f"{product_name} supports {limit_readable} up to {limit_value}",
            'claim_kind': 'performance',
            'section_kind': 'performance',
            'metric': limit_name,
            'value': limit_value,
            'source_type': 'test',
            'source_file': source_file,
            'start_line': 0,
            'end_line': 0,
            'keyword_boost': True,
        })

    return characteristics


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

    # TC-1620: Handle best_practice sections with specialized extractor
    if section_kind == 'best_practice':
        # Reconstruct full section text from lines
        section_text = "\n".join(line for _, line in section_lines)
        best_practice_claims = _extract_best_practice_statements(
            section_text, section_heading, rel_path,
            section_start, section_end, source_type, product_name
        )
        candidates.extend(best_practice_claims)
        return

    # TC-1620: Handle performance sections (similar to best_practice)
    if section_kind == 'performance':
        # Reconstruct full section text from lines
        section_text = "\n".join(line for _, line in section_lines)
        best_practice_claims = _extract_best_practice_statements(
            section_text, section_heading, rel_path,
            section_start, section_end, source_type, product_name
        )
        candidates.extend(best_practice_claims)
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
        if _is_implementation_detail(claim_text):
            continue
        if _is_spec_header(claim_text):  # TC-1840
            continue

        # Accept if prose-like or noun-phrase
        if not (_is_prose_like(claim_text) or _is_noun_phrase_claim(claim_text)):
            continue

        prose_found = True
        section_slug = re.sub(r"[^a-z0-9]+", "-", section_heading.lower()).strip("-") if section_heading else ""
        candidates.append({
            'claim_text': claim_text,
            'source_file': rel_path,
            'start_line': line_num,
            'end_line': line_num,
            'source_type': 'readme_technical',
            'keyword_boost': True,
            'section_kind': section_kind,
            'source_section': section_slug,  # TC-2365
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
                'source_section': candidate.get('source_section', ""),  # TC-2365
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


def _extract_citation_excerpt(
    file_path: str, start_line: int, end_line: int,
    repo_root: Path, max_chars: int = 400,
) -> str:
    """Read up to 3 lines of context around the citation location.

    TC-2351: Gives the LLM actual source content instead of file paths.

    Args:
        file_path: Relative path to cited file.
        start_line: 1-based start line.
        end_line: 1-based end line.
        repo_root: Repository root directory.
        max_chars: Maximum excerpt length.

    Returns:
        Excerpt string, or empty string on error.
    """
    try:
        full_path = repo_root / file_path
        if not full_path.exists():
            return ""
        if full_path.stat().st_size > 5_000_000:
            return ""
        text = full_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        # Convert to 0-based, take ±3 lines for context
        ctx_start = max(0, start_line - 1 - 3)
        ctx_end = min(len(lines), end_line + 3)
        if ctx_start >= len(lines):
            return ""
        excerpt = " ".join(lines[ctx_start:ctx_end]).strip()
        if len(excerpt) > max_chars:
            excerpt = excerpt[:max_chars].rsplit(" ", 1)[0] + "..."
        return excerpt
    except Exception:
        return ""


def _enrich_citations_with_excerpts(
    claims: List[Dict[str, Any]], repo_dir: Path,
) -> None:
    """Add citation_excerpt field to every citation in-place.

    TC-2351: Post-processing step run once after deduplication.
    """
    for claim in claims:
        for citation in claim.get("citations", []):
            if "citation_excerpt" in citation:
                continue  # Already enriched (e.g. from merge)
            path = citation.get("path", "")
            start = citation.get("start_line", 0)
            end = citation.get("end_line", 0)
            if path and start > 0:
                citation["citation_excerpt"] = _extract_citation_excerpt(
                    path, start, end, repo_dir,
                )
                # Phase 2A: excerpt hash for stable references (TC-3060)
                excerpt = citation.get("citation_excerpt", "")
                if excerpt:
                    normalized = " ".join(excerpt.lower().split())
                    citation["excerpt_hash"] = hashlib.sha256(
                        normalized.encode("utf-8")
                    ).hexdigest()[:16]
                else:
                    citation["excerpt_hash"] = ""
                # Phase 2B: context line range (TC-3060)
                citation["context_start_line"] = max(1, start - 3)
                citation["context_end_line"] = end + 3
            else:
                citation["citation_excerpt"] = ""
                citation["excerpt_hash"] = ""
                citation["context_start_line"] = 0
                citation["context_end_line"] = 0


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

    # Try centralized prompt first (TC-1712)
    _loader = _get_prompt_loader()
    prompt_text = None
    if _loader:
        try:
            prompt_text = _loader.load(
                "synthesis/api_claims",
                product_name=product_name,
                source_code=api_listing,
                api_reference=api_listing,
            ).text
        except Exception:
            prompt_text = None

    if prompt_text:
        system_msg = prompt_text
        user_msg = (
            f"Product: {product_name}\n\n"
            f"API Surface:\n{api_listing}\n\n"
            "Generate claims as a JSON array. Example format:\n"
            '[{"claim_text": "ProductX provides the Scene class for managing 3D scenes", '
            '"claim_kind": "key_feature", "referenced_symbols": ["Scene"]}]'
        )
    else:
        # Fallback to inline prompt
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

    # TC-1620: Infer best practices from code patterns in main library files
    if code_analysis:
        try:
            best_practice_claims = []
            api_surface = code_analysis.get("api_surface", {})
            classes = api_surface.get("classes", [])

            # Extract unique module paths from classes
            module_paths = set()
            for cls in classes:
                mod_path = cls.get("module", "")
                if mod_path and mod_path not in module_paths:
                    module_paths.add(mod_path)

            # Process main library files (exclude tests, examples, docs)
            for module_path in list(module_paths)[:5]:  # Limit to top 5 modules to avoid noise
                if any(skip in module_path.lower() for skip in ['test', 'example', 'demo', 'doc', '__pycache__']):
                    continue

                full_path = repo_dir / module_path
                if not full_path.exists():
                    continue

                try:
                    code_content = full_path.read_text(encoding='utf-8', errors='ignore')
                    rel_path = str(full_path.relative_to(repo_dir)) if full_path.is_absolute() else module_path

                    bp_candidates = _infer_best_practices_from_code(
                        code_content, rel_path, product_name, source_type='source_code'
                    )

                    for candidate in bp_candidates:
                        claim_id = compute_claim_id(
                            candidate['claim_text'], 'best_practice', product_name
                        )
                        best_practice_claims.append({
                            'claim_id': claim_id,
                            'claim_text': candidate['claim_text'],
                            'claim_kind': 'best_practice',
                            'truth_status': 'inference',
                            'confidence': 'medium',
                            'source_type': 'source_code',
                            'source_priority': 2,
                            'source_relevance': 50,
                            'evidence_priority': 'medium',
                            'category': candidate.get('category', 'correctness'),
                            'citations': [{
                                'path': rel_path,
                                'start_line': 0,
                                'end_line': 0,
                                'source_type': 'source_code',
                            }],
                        })

                except Exception as e:
                    logger.debug(f"Could not read {module_path}: {e}")
                    continue

            if best_practice_claims:
                claims.extend(best_practice_claims)
                logger.info(
                    "best_practice_code_inference_added",
                    count=len(best_practice_claims),
                    product_name=product_name,
                )
        except Exception as e:
            logger.warning(
                "best_practice_code_inference_failed",
                error=str(e),
                product_name=product_name,
            )

    # TC-1620: Extract performance characteristics from test files
    try:
        performance_claims = []
        inventory_files = repo_inventory.get('files', [])

        # Process test files
        test_files = [f for f in inventory_files if 'test' in f.get('path', '').lower()]
        for test_file in test_files[:10]:  # Limit to 10 test files
            test_path = test_file.get('path', '')
            full_path = repo_dir / test_path

            if not full_path.exists():
                continue

            try:
                test_content = full_path.read_text(encoding='utf-8', errors='ignore')
                rel_path = str(full_path.relative_to(repo_dir)) if full_path.is_absolute() else test_path

                perf_candidates = _extract_performance_characteristics(
                    test_content, rel_path, product_name
                )

                for candidate in perf_candidates:
                    claim_id = compute_claim_id(
                        candidate['claim_text'], 'performance', product_name
                    )
                    performance_claims.append({
                        'claim_id': claim_id,
                        'claim_text': candidate['claim_text'],
                        'claim_kind': 'performance',
                        'truth_status': 'fact',
                        'confidence': 'high',
                        'source_type': 'test',
                        'source_priority': 2,
                        'source_relevance': 70,
                        'evidence_priority': 'high',
                        'metric': candidate.get('metric', ''),
                        'value': candidate.get('value', ''),
                        'citations': [{
                            'path': rel_path,
                            'start_line': 0,
                            'end_line': 0,
                            'source_type': 'test',
                        }],
                    })

            except Exception as e:
                logger.debug(f"Could not read test file {test_path}: {e}")
                continue

        if performance_claims:
            claims.extend(performance_claims)
            logger.info(
                "performance_characteristics_added",
                count=len(performance_claims),
                product_name=product_name,
            )
    except Exception as e:
        logger.warning(
            "performance_extraction_failed",
            error=str(e),
            product_name=product_name,
        )

    # TC-1704: Extract performance claims from README/doc text
    try:
        perf_from_docs = []
        for doc_file in doc_entrypoint_details:
            file_path = repo_dir / doc_file['path']
            if not file_path.exists():
                continue
            try:
                doc_content = file_path.read_text(encoding='utf-8', errors='ignore')
                rel_path = str(file_path.relative_to(repo_dir)) if file_path.is_absolute() else doc_file['path']
                doc_perf = _extract_performance_claims(doc_content, rel_path, product_name)
                for candidate in doc_perf:
                    claim_id = compute_claim_id(candidate['claim_text'], 'performance', product_name)
                    perf_from_docs.append({
                        'claim_id': claim_id,
                        'claim_text': candidate['claim_text'],
                        'claim_kind': 'performance',
                        'truth_status': 'fact',
                        'confidence': 'medium',
                        'source_type': 'documentation',
                        'source_priority': 2,
                        'source_relevance': 60,
                        'evidence_priority': 'medium',
                        'citations': [{'path': rel_path, 'start_line': 0, 'end_line': 0, 'source_type': 'documentation'}],
                    })
            except Exception:
                continue
        if perf_from_docs:
            claims.extend(perf_from_docs)
            logger.info("performance_claims_from_docs", count=len(perf_from_docs), product_name=product_name)
    except Exception as e:
        logger.warning("performance_doc_extraction_failed", error=str(e), product_name=product_name)

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

    # TC-2351: Enrich citations with source excerpts for LLM context
    _enrich_citations_with_excerpts(claims, repo_dir)

    # TC-1841: Add normalized_text for slug/title generation
    for claim in claims:
        claim['normalized_text'] = _normalize_claim_text_for_slug(
            claim.get('claim_text', '')
        )

    # Validate all claims
    for claim in claims:
        try:
            validate_claim_structure(claim)
        except ClaimsValidationError as e:
            logger.error("claim_validation_failed", claim_id=claim.get('claim_id'), error=str(e))
            raise

    # Sort deterministically
    claims = sort_claims_deterministically(claims)

    # TC-3672: Tag claim visibility (public/internal)
    for claim in claims:
        if 'visibility' not in claim:
            claim['visibility'] = classify_claim_visibility(
                claim.get('claim_text', ''),
                claim.get('claim_kind', ''),
            )

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


def llm_generate_workflow_steps(
    workflow_tag: str,
    workflow_title: str,
    existing_steps: list,
    api_surface: dict,
    positioning: dict,
    product_name: str,
    llm_client,
    target_steps: int = 10,
) -> list:
    """Generate additional workflow steps via LLM when deterministic extraction falls short.

    TC-1623: When existing step count < threshold, use LLM to generate
    additional steps based on API surface, positioning, and product context.

    Args:
        workflow_tag: Workflow type ('installation', 'quickstart', 'format_conversion')
        workflow_title: Human-readable title
        existing_steps: Steps already extracted (list of step name strings)
        api_surface: API surface dict with 'classes' and 'functions' lists
        positioning: Product positioning dict
        product_name: Product name
        llm_client: LLM provider client (must not be None)
        target_steps: Target number of total steps

    Returns:
        List of NEW step dicts (not including existing steps) with keys:
        name, claim_text, claim_kind, source_type, truth_status, confidence, step_order
    """
    if llm_client is None:
        return []

    n_existing = len(existing_steps)
    if n_existing >= target_steps:
        return []

    n_needed = target_steps - n_existing

    # Build existing steps list for context
    existing_steps_text = ""
    for i, step_name in enumerate(existing_steps, 1):
        existing_steps_text += f"{i}. {step_name}\n"
    if not existing_steps_text:
        existing_steps_text = "(none yet)\n"

    # Extract top API classes/functions for context
    classes = api_surface.get('classes', [])
    functions = api_surface.get('functions', [])

    # Classes/functions may be dicts or strings; extract names
    def _extract_names(items, limit=10):
        names = []
        for item in items[:limit]:
            if isinstance(item, dict):
                names.append(item.get('name', item.get('class_name', str(item))))
            else:
                names.append(str(item))
        return names

    top_classes = _extract_names(classes, 10)
    top_functions = _extract_names(functions, 10)

    # Build positioning context
    short_desc = positioning.get('short_description', '') or positioning.get('tagline', '')
    if not short_desc:
        short_desc = f"A software library called {product_name}"

    # Try centralized prompt first (TC-1712)
    _loader = _get_prompt_loader()
    _centralized_prompt = None
    if _loader:
        try:
            code_context = (
                f"Classes: {', '.join(top_classes) if top_classes else 'N/A'}\n"
                f"Functions: {', '.join(top_functions) if top_functions else 'N/A'}"
            )
            _centralized_prompt = _loader.load(
                "synthesis/workflow_steps",
                product_name=product_name,
                code_context=code_context,
                documentation_context=f"{workflow_title}: {existing_steps_text}",
            ).text
        except Exception:
            _centralized_prompt = None

    if _centralized_prompt:
        system_prompt = _centralized_prompt
    else:
        # Fallback to inline prompt
        system_prompt = (
            "You are a technical documentation writer. "
            "Generate detailed workflow steps for software library documentation."
        )

    user_prompt = (
        f'Generate additional steps for the "{workflow_title}" workflow of {product_name}.\n\n'
        f"Product description: {short_desc}\n\n"
        f"Existing steps:\n{existing_steps_text}\n"
        f"Available API classes: {', '.join(top_classes) if top_classes else 'N/A'}\n"
        f"Available API functions: {', '.join(top_functions) if top_functions else 'N/A'}\n\n"
        f"Generate {n_needed} MORE steps to create a comprehensive {workflow_tag} guide.\n"
        f"Each step should be a clear, actionable instruction.\n"
        f"Include prerequisite checks, verification steps, error handling guidance, "
        f"and next-steps suggestions.\n\n"
        f'Return JSON: {{"steps": [{{"name": "Step description", "description": "Detailed explanation"}}]}}'
    )

    try:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            call_id=f"tc1623_workflow_{workflow_tag}",
            temperature=0.0,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.get("content", "") if isinstance(response, dict) else response
        parsed = json.loads(content)
        raw_steps = parsed.get('steps', [])
    except (json.JSONDecodeError, LLMError, Exception) as e:
        logger.warning(
            "llm_workflow_step_generation_parse_failed",
            workflow_tag=workflow_tag,
            error=str(e),
        )
        return []

    if not raw_steps:
        return []

    # Deduplicate against existing steps using Jaccard word overlap
    existing_word_sets = [set(name.lower().split()) for name in existing_steps]

    def _is_duplicate(new_name: str) -> bool:
        new_words = set(new_name.lower().split())
        if not new_words:
            return False
        for existing_ws in existing_word_sets:
            if not existing_ws:
                continue
            intersection = new_words & existing_ws
            union = new_words | existing_ws
            if union and len(intersection) / len(union) >= 0.5:
                return True
        return False

    # Find max existing step_order
    max_step_order = n_existing

    new_steps = []
    for raw in raw_steps:
        step_name = raw.get('name', '').strip()
        if not step_name:
            continue
        if _is_duplicate(step_name):
            continue

        max_step_order += 1

        new_steps.append({
            'name': step_name,
            'claim_text': step_name,
            'claim_kind': 'workflow',
            'source_type': 'llm_synthesized',
            'truth_status': 'inference',
            'confidence': 'medium',
            'citations': [],
            'step_order': max_step_order,
        })

        # Also add to existing_word_sets to prevent self-duplicates
        existing_word_sets.append(set(step_name.lower().split()))

    logger.info(
        "llm_workflow_steps_raw",
        workflow_tag=workflow_tag,
        raw_count=len(raw_steps),
        after_dedup=len(new_steps),
        target_steps=target_steps,
    )

    return new_steps


def llm_generate_faq_entries(
    limitation_claims: list,
    api_surface: dict,
    product_name: str,
    llm_client,
    target_count: int = 12,
) -> list:
    """Generate FAQ claims via LLM from limitations and API surface.

    TC-1625: Creates FAQ Q&A pairs for knowledge base content.

    Args:
        limitation_claims: List of limitation claim texts
        api_surface: API surface dict with 'classes' and 'functions'
        product_name: Product name
        llm_client: LLM provider client
        target_count: Target FAQ count

    Returns:
        List of FAQ claim dicts with claim_text, claim_kind="faq",
        source_type="llm_synthesized", truth_status="inference"
    """
    if llm_client is None:
        return []

    # Build context from inputs
    limitations_text = "\n".join(
        f"- {lt}" for lt in limitation_claims[:10]
    ) or "None known"

    classes = api_surface.get("classes", [])[:10] if api_surface else []
    functions = api_surface.get("functions", [])[:10] if api_surface else []

    classes_text = ", ".join(str(c) for c in classes) if classes else "N/A"
    functions_text = ", ".join(str(f) for f in functions) if functions else "N/A"

    # Try centralized prompt first (TC-1712)
    _loader = _get_prompt_loader()
    _centralized_prompt = None
    if _loader:
        try:
            _centralized_prompt = _loader.load(
                "synthesis/faq_entries",
                product_name=product_name,
                features_context=f"Classes: {classes_text}\nFunctions: {functions_text}",
                documentation_context=f"Known limitations:\n{limitations_text}",
            ).text
        except Exception:
            _centralized_prompt = None

    if _centralized_prompt:
        system_prompt = _centralized_prompt
    else:
        # Fallback to inline prompt
        system_prompt = (
            "You are a technical support writer. "
            "Generate FAQ entries for a software library."
        )

    user_prompt = (
        f"Generate {target_count} FAQ entries for {product_name}.\n\n"
        f"Known limitations:\n{limitations_text}\n\n"
        f"API classes: {classes_text}\n"
        f"Functions: {functions_text}\n\n"
        f"Each FAQ: question, answer (2-4 sentences), category "
        f"(one of: installation, compatibility, api_usage, performance, formats, general).\n\n"
        f'Return JSON: {{"faq_entries": [{{"question": "...", "answer": "...", "category": "..."}}]}}'
    )

    try:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            call_id="tc1625_faq",
            temperature=0.0,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        content = response.get("content", "") if isinstance(response, dict) else response
        parsed = json.loads(content)
        raw_entries = parsed.get("faq_entries", [])
    except (json.JSONDecodeError, LLMError, Exception) as e:
        logger.warning(
            "llm_faq_generation_failed",
            error=str(e),
        )
        return []

    results = []
    for faq in raw_entries:
        question = faq.get("question", "").strip()
        answer = faq.get("answer", "").strip()
        if not question or not answer:
            continue

        results.append({
            "claim_text": f"Q: {question} A: {answer}",
            "claim_kind": "faq",
            "source_type": "llm_synthesized",
            "truth_status": "inference",
            "confidence": "medium",
            "citations": [],
        })

    logger.info(
        "llm_faq_entries_generated",
        raw_count=len(raw_entries),
        result_count=len(results),
        target_count=target_count,
    )

    return results


def llm_generate_troubleshooting_entries(
    limitation_claims: list,
    api_surface: dict,
    product_name: str,
    llm_client,
    target_count: int = 10,
) -> list:
    """Generate troubleshooting claims via LLM.

    TC-1625: Creates troubleshooting guides from limitations and API surface.

    Args:
        limitation_claims: List of limitation claim texts
        api_surface: API surface dict with 'classes' and 'functions'
        product_name: Product name
        llm_client: LLM provider client
        target_count: Target troubleshooting guide count

    Returns:
        List of troubleshooting claim dicts with claim_text,
        claim_kind="troubleshooting", source_type="llm_synthesized",
        truth_status="inference"
    """
    if llm_client is None:
        return []

    # Build context from inputs
    limitations_text = "\n".join(
        f"- {lt}" for lt in limitation_claims[:10]
    ) or "None known"

    classes = api_surface.get("classes", [])[:10] if api_surface else []
    classes_text = ", ".join(str(c) for c in classes) if classes else "N/A"

    # Try centralized prompt first (TC-1712)
    _loader = _get_prompt_loader()
    _centralized_prompt = None
    if _loader:
        try:
            _centralized_prompt = _loader.load(
                "synthesis/troubleshooting_entries",
                product_name=product_name,
                error_patterns=limitations_text,
                documentation_context=f"API classes: {classes_text}",
            ).text
        except Exception:
            _centralized_prompt = None

    if _centralized_prompt:
        system_prompt = _centralized_prompt
    else:
        # Fallback to inline prompt
        system_prompt = (
            "You are a technical support writer. "
            "Generate troubleshooting guides for a software library."
        )

    user_prompt = (
        f"Generate {target_count} troubleshooting guides for {product_name}.\n\n"
        f"Known limitations:\n{limitations_text}\n\n"
        f"API classes: {classes_text}\n\n"
        f"Each guide: problem, cause, resolution (step-by-step), prevention.\n\n"
        f'Return JSON: {{"guides": [{{"problem": "...", "cause": "...", '
        f'"resolution": "...", "prevention": "..."}}]}}'
    )

    try:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            call_id="tc1625_troubleshooting",
            temperature=0.0,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        content = response.get("content", "") if isinstance(response, dict) else response
        parsed = json.loads(content)
        raw_guides = parsed.get("guides", [])
    except (json.JSONDecodeError, LLMError, Exception) as e:
        logger.warning(
            "llm_troubleshooting_generation_failed",
            error=str(e),
        )
        return []

    results = []
    for g in raw_guides:
        problem = g.get("problem", "").strip()
        resolution = g.get("resolution", "").strip()
        if not problem or not resolution:
            continue

        results.append({
            "claim_text": f"Problem: {problem} Resolution: {resolution}",
            "claim_kind": "troubleshooting",
            "source_type": "llm_synthesized",
            "truth_status": "inference",
            "confidence": "medium",
            "citations": [],
        })

    logger.info(
        "llm_troubleshooting_entries_generated",
        raw_count=len(raw_guides),
        result_count=len(results),
        target_count=target_count,
    )

    return results


def _jaccard_overlap(a: str, b: str) -> float:
    """Compute Jaccard word overlap between two strings.

    Used for deduplication of LLM-generated content against existing items.
    """
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def llm_generate_best_practices(
    api_surface: dict,
    code_patterns: list,
    product_name: str,
    llm_client,
    target_count: int = 10,
) -> list:
    """Generate best practice claims via LLM from API surface and code patterns.

    TC-1626: Creates best practice recommendations for documentation content.

    Args:
        api_surface: API surface dict with 'classes' and 'functions'
        code_patterns: List of existing best practice recommendation texts
            from code_understanding
        product_name: Product name
        llm_client: LLM provider client
        target_count: Target best practice count

    Returns:
        List of best practice claim dicts with claim_text,
        claim_kind="best_practice", source_type="llm_synthesized",
        truth_status="inference"
    """
    if llm_client is None:
        return []

    classes = api_surface.get("classes", [])[:10] if api_surface else []
    functions = api_surface.get("functions", [])[:10] if api_surface else []

    classes_text = ", ".join(str(c) for c in classes) if classes else "N/A"
    functions_text = ", ".join(str(f) for f in functions) if functions else "N/A"

    existing_text = "\n".join(
        f"- {p}" for p in code_patterns[:10]
    ) or "None known"

    # Try centralized prompt first (TC-1712)
    _loader = _get_prompt_loader()
    _centralized_prompt = None
    if _loader:
        try:
            _centralized_prompt = _loader.load(
                "synthesis/best_practices",
                product_name=product_name,
                api_patterns=f"Classes: {classes_text}\nFunctions: {functions_text}",
                documentation_context=f"Already known best practices:\n{existing_text}",
            ).text
        except Exception:
            _centralized_prompt = None

    if _centralized_prompt:
        system_prompt = _centralized_prompt
    else:
        # Fallback to inline prompt
        system_prompt = (
            "You are a technical documentation expert. "
            "Generate best practice recommendations for a software library."
        )

    user_prompt = (
        f"Generate {target_count} best practice recommendations for {product_name}.\n\n"
        f"API classes: {classes_text}\n"
        f"Functions: {functions_text}\n\n"
        f"Already known best practices:\n{existing_text}\n\n"
        f"Categories: memory management, performance, error handling, "
        f"file handling, thread safety, code organization.\n\n"
        f"Each entry: category, recommendation (specific actionable advice), "
        f"rationale (why this is a best practice).\n\n"
        f'Return JSON: {{"best_practices": [{{"category": "...", '
        f'"recommendation": "...", "rationale": "..."}}]}}'
    )

    try:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            call_id="tc1626_best_practices",
            temperature=0.0,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        content = response.get("content", "") if isinstance(response, dict) else response
        parsed = json.loads(content)
        raw_entries = parsed.get("best_practices", [])
    except (json.JSONDecodeError, LLMError, Exception) as e:
        logger.warning(
            "llm_best_practices_generation_failed",
            error=str(e),
        )
        return []

    results = []
    for bp in raw_entries:
        category = bp.get("category", "").strip()
        recommendation = bp.get("recommendation", "").strip()
        rationale = bp.get("rationale", "").strip()
        if not recommendation:
            continue

        claim_text = (
            f"Best practice ({category}): {recommendation}. {rationale}"
            if rationale
            else f"Best practice ({category}): {recommendation}"
        )

        # Dedup against existing code_patterns using Jaccard overlap
        is_dup = any(
            _jaccard_overlap(recommendation, existing) > 0.5
            for existing in code_patterns
            if existing
        )
        if is_dup:
            continue

        results.append({
            "claim_text": claim_text,
            "claim_kind": "best_practice",
            "source_type": "llm_synthesized",
            "truth_status": "inference",
            "confidence": "medium",
            "citations": [],
        })

    logger.info(
        "llm_best_practices_entries_generated",
        raw_count=len(raw_entries),
        result_count=len(results),
        target_count=target_count,
    )

    return results


def llm_generate_performance_claims(
    api_surface: dict,
    product_name: str,
    llm_client,
    target_count: int = 5,
) -> list:
    """Generate performance characteristic claims via LLM.

    TC-1626: Creates performance and scalability claims for documentation.

    Args:
        api_surface: API surface dict with 'classes' and 'functions'
        product_name: Product name
        llm_client: LLM provider client
        target_count: Target performance claim count

    Returns:
        List of performance claim dicts with claim_text,
        claim_kind="performance", source_type="llm_synthesized",
        truth_status="inference"
    """
    if llm_client is None:
        return []

    classes = api_surface.get("classes", [])[:10] if api_surface else []
    classes_text = ", ".join(str(c) for c in classes) if classes else "N/A"

    # Try centralized prompt first (TC-1712)
    _loader = _get_prompt_loader()
    _centralized_prompt = None
    if _loader:
        try:
            _centralized_prompt = _loader.load(
                "synthesis/performance_claims",
                product_name=product_name,
                api_structure=f"API classes: {classes_text}",
                documentation_context="",
            ).text
        except Exception:
            _centralized_prompt = None

    if _centralized_prompt:
        system_prompt = _centralized_prompt
    else:
        # Fallback to inline prompt
        system_prompt = (
            "You are a technical documentation expert. "
            "Generate performance characteristics and scalability information "
            "for a software library."
        )

    user_prompt = (
        f"Generate {target_count} performance characteristics for {product_name}.\n\n"
        f"API classes: {classes_text}\n\n"
        f"Each entry: metric (operation name or characteristic), "
        f"value (measured value or range), "
        f"conditions (under what conditions).\n\n"
        f'Return JSON: {{"performance_claims": [{{"metric": "...", '
        f'"value": "...", "conditions": "..."}}]}}'
    )

    try:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            call_id="tc1626_performance",
            temperature=0.0,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        content = response.get("content", "") if isinstance(response, dict) else response
        parsed = json.loads(content)
        raw_entries = parsed.get("performance_claims", [])
    except (json.JSONDecodeError, LLMError, Exception) as e:
        logger.warning(
            "llm_performance_claims_generation_failed",
            error=str(e),
        )
        return []

    results = []
    for pc in raw_entries:
        metric = pc.get("metric", "").strip()
        value = pc.get("value", "").strip()
        conditions = pc.get("conditions", "").strip()
        if not metric or not value:
            continue

        claim_text = (
            f"{metric}: {value} ({conditions})"
            if conditions
            else f"{metric}: {value}"
        )

        results.append({
            "claim_text": claim_text,
            "claim_kind": "performance",
            "source_type": "llm_synthesized",
            "truth_status": "inference",
            "confidence": "medium",
            "citations": [],
        })

    logger.info(
        "llm_performance_claims_generated",
        raw_count=len(raw_entries),
        result_count=len(results),
        target_count=target_count,
    )

    return results


# ---------------------------------------------------------------------------
# TC-2342: Format conversion detection and topic clustering
# ---------------------------------------------------------------------------


def detect_format_conversions(
    claims: list,
    api_surface: dict,
    *,
    llm_client=None,
    product_name: str = "",
    product_description: str = "",
) -> dict:
    """Detect format conversion capabilities from claims and API surface.

    TC-2342: Scans claim text for "convert X to Y" patterns and API class
    names like XxxConverter/SaveOptions/LoadOptions to identify format
    conversion capabilities. Also clusters claims by topic for how-to
    generation.

    Args:
        claims: List of claim dicts with ``claim_id`` and ``claim_text``.
        api_surface: API surface dict with optional ``classes`` list.
        llm_client: Optional LLM client for capability discovery.
        product_name: Product name for LLM prompt context.
        product_description: Product description for LLM prompt context.

    Returns:
        Dict with keys:
            ``format_conversions`` - list of claim_ids involved in conversions
            ``conversion_pairs`` - list of {source, target, claim_ids} dicts
            ``how_to_clusters`` - dict of topic -> claim_id lists
    """
    conversion_re = re.compile(
        r'(?:convert|transform|export)\s+(\w+)\s+(?:to|into|as)\s+(\w+)',
        re.IGNORECASE,
    )
    class_re = re.compile(
        r'(\w+)(?:Converter|SaveOptions|LoadOptions|Exporter|Importer)',
    )

    pairs: Dict[Tuple[str, str], List[str]] = {}
    format_claim_ids: List[str] = []

    for claim in claims:
        text = claim.get("claim_text", "")
        cid = claim.get("claim_id", "")
        m = conversion_re.search(text)
        if m:
            src, tgt = m.group(1).lower(), m.group(2).lower()
            pairs.setdefault((src, tgt), []).append(cid)
            format_claim_ids.append(cid)

    # Also detect from API class names
    for cls in api_surface.get("classes", []):
        cls_name = cls if isinstance(cls, str) else cls.get("name", "")
        cm = class_re.search(cls_name)
        if cm:
            fmt = cm.group(1).lower()
            # Find claims mentioning this format
            for claim in claims:
                if fmt in claim.get("claim_text", "").lower():
                    format_claim_ids.append(claim.get("claim_id", ""))

    conversion_pairs = [
        {"source": src, "target": tgt, "claim_ids": sorted(set(cids))}
        for (src, tgt), cids in sorted(pairs.items())
    ]

    # LLM-driven capability discovery (product-agnostic, optional)
    llm_topics = []
    if llm_client is not None:
        try:
            llm_result = _discover_capabilities_via_llm(
                claims, api_surface, llm_client,
                product_name=product_name,
                product_description=product_description,
            )
            # Merge LLM-found conversion pairs with regex-found ones
            for llm_pair in llm_result.get("conversion_pairs", []):
                src = llm_pair.get("source_format", "").lower()
                tgt = llm_pair.get("target_format", "").lower()
                if src and tgt:
                    key = (src, tgt)
                    if key not in pairs:
                        pairs[key] = []  # LLM found pair that regex missed
            llm_topics = llm_result.get("how_to_topics", [])
            logger.info(
                "detect_format_conversions_llm pairs=%d topics=%d",
                len(llm_result.get("conversion_pairs", [])),
                len(llm_topics),
            )
        except Exception as e:
            logger.warning("detect_format_conversions_llm_fail error=%s", e)

    # Build how-to clusters by grouping claims with similar keywords
    clusters = _cluster_claims_by_topic(claims, llm_topics=llm_topics)

    return {
        "format_conversions": sorted(set(format_claim_ids)),
        "conversion_pairs": conversion_pairs,
        "how_to_clusters": clusters,
    }


_CAPABILITY_PROMPT = """\
Analyze this software library to discover its capabilities.

Product: {product_name}
Description: {product_description}

API classes (sample):
{api_sample}

Key claims (sample):
{claims_sample}

TASK 1 — Format Conversions:
Does this product convert files between formats?
YES -> list all supported conversion pairs.
NO  -> return empty list for conversion_pairs.

TASK 2 — KB How-To Topic Keywords:
Identify {max_topics} distinct how-to topic areas grounded in the claims above.
Each topic needs keywords that match actual claim text.

Output JSON only (no markdown, no prose):
{{
  "has_format_conversions": true,
  "conversion_pairs": [
    {{"source_format": "obj", "target_format": "stl",
      "title": "Convert OBJ to STL", "confidence": "high"}}
  ],
  "how_to_topics": [
    {{"slug": "mesh-operations",
      "title": "Manipulate 3D Meshes",
      "keywords": ["mesh", "vertex", "face", "normal", "geometry"]}}
  ]
}}
"""


def _discover_capabilities_via_llm(
    claims: list, api_surface: dict, llm_client,
    *, product_name: str = "", product_description: str = "",
) -> dict:
    """One LLM call discovers format conversion pairs + KB topic keywords.

    Returns dict with keys: has_format_conversions, conversion_pairs, how_to_topics.
    Raises on LLM error (caller must handle).
    """
    class_names = [
        c.get("name", "") if isinstance(c, dict) else str(c)
        for c in api_surface.get("classes", [])[:50]
    ]
    api_sample = "\n".join(class_names) or "(none)"
    claims_sample = "\n".join(
        f"- {c.get('claim_text', '')[:100]}" for c in claims[:40]
    ) or "(none)"
    prompt = _CAPABILITY_PROMPT.format(
        product_name=product_name or "Unknown",
        product_description=(product_description or "")[:400],
        api_sample=api_sample,
        claims_sample=claims_sample,
        max_topics=8,
    )
    response = llm_client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        call_id="detect_capabilities",
        temperature=0.1,
        max_tokens=1200,
    )
    raw = response.get("content", "").strip()
    # Strip fences if present
    import re as _re
    m = _re.search(r"```json\s*\n(.*?)\n```", raw, _re.DOTALL)
    if m:
        raw = m.group(1)
    elif raw.startswith("```"):
        m2 = _re.search(r"```\s*\n(.*?)\n```", raw, _re.DOTALL)
        if m2:
            raw = m2.group(1)
    import json as _json
    return _json.loads(raw)


def _cluster_claims_by_topic(claims: list, *, llm_topics: list = None) -> dict:
    """Group claims into topic clusters for how-to generation.

    TC-2342: Uses predefined keyword sets to cluster claims into topics.
    Only topics with 3+ matching claims are included (minimum viable cluster).

    Args:
        claims: List of claim dicts with ``claim_id`` and ``claim_text``.
        llm_topics: Optional list of LLM-discovered topic dicts with ``slug``
            and ``keywords`` keys. When provided, replaces the hardcoded
            Aspose.Cells-oriented fallback keywords.

    Returns:
        Dict mapping topic name to sorted list of matching claim_ids.
    """
    if llm_topics:
        # Use LLM-discovered product-specific keywords (product-agnostic)
        topic_keywords = {
            t["slug"]: set(kw.lower() for kw in t.get("keywords", []))
            for t in llm_topics
            if t.get("slug") and t.get("keywords")
        }
    else:
        # Legacy fallback — Aspose.Cells/Words oriented, kept for backward compat
        topic_keywords = {
            "pdf-operations": {"pdf", "export", "save", "render"},
            "data-import": {"import", "load", "read", "parse", "json", "csv", "xml"},
            "formatting": {"format", "style", "font", "color", "border", "alignment"},
            "chart-operations": {"chart", "graph", "plot", "series"},
            "image-operations": {"image", "picture", "photo", "png", "jpg", "svg"},
        }
    clusters: Dict[str, List[str]] = {}
    for topic, keywords in topic_keywords.items():
        matching: List[str] = []
        for claim in claims:
            text_lower = claim.get("claim_text", "").lower()
            if any(kw in text_lower for kw in keywords):
                matching.append(claim.get("claim_id", ""))
        if len(matching) >= 3:
            clusters[topic] = sorted(set(matching))
    return clusters
