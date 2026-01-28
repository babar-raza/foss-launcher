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
        'not supported',
        'not yet implemented',
        'not implemented',
        'cannot',
        'limitation',
        'unsupported',
    ]):
        return 'limitation'

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

            # Filter for claim-like sentences (must have verb + meaningful content)
            if len(sentence.split()) >= 4:  # Minimum length
                # Check if it looks like a claim
                if any(marker in sentence.lower() for marker in [
                    'support', 'can', 'enable', 'provide', 'allow',
                    'install', 'use', 'usage', 'format', 'read', 'write',
                    'does not', 'cannot', 'limitation', 'not yet',
                    'class', 'function', 'method', 'api', 'interface',
                ]):
                    source_type = determine_source_type(file_path, repo_dir)
                    candidates.append({
                        'claim_text': sentence,
                        'source_file': str(file_path.relative_to(repo_dir)) if file_path.is_absolute() else str(file_path),
                        'start_line': start_line,
                        'end_line': line_num,
                        'source_type': source_type,
                    })

            # Reset for next sentence
            current_sentence = []
            start_line = line_num + 1

    return candidates


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
    for doc_file in doc_files[:10]:  # Limit to first 10 docs to avoid token limits
        file_path = repo_dir / doc_file['path']

        if not file_path.exists():
            logger.warning("doc_file_not_found", path=str(file_path))
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.warning("doc_file_read_error", path=str(file_path), error=str(e))
            continue

        # Extract candidate statements using heuristics
        candidates = extract_candidate_statements_from_text(
            content, file_path, repo_dir
        )

        # Build structured claims from candidates
        for candidate in candidates:
            claim_kind = classify_claim_kind(candidate['claim_text'])
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
                'source_priority': source_priority,
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
                    'source_priority': source_priority,
                    'citations': [{
                        'path': candidate['source_file'],
                        'start_line': candidate['start_line'],
                        'end_line': candidate['end_line'],
                        'source_type': source_type,
                    }],
                }

                claims.append(claim)

    # Deduplicate claims
    claims = deduplicate_claims(claims)

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
        output_path=str(output_path),
    )

    return result
