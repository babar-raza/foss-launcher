"""W2 FactsBuilder worker - Extract product facts and evidence.

TC-410: W2 FactsBuilder integrator (main entry point).
TC-411: Extract claims from product documentation.
TC-412: Map evidence from claims to docs/examples.
TC-413: Detect contradictions and resolve conflicts.

Spec references:
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/03_product_facts_and_evidence.md (Facts extraction)
- specs/04_claims_compiler_truth_lock.md (Claims structure)
"""

# Main integrator entry point (TC-410)
from .worker import (
    execute_facts_builder,
    FactsBuilderError,
    FactsBuilderClaimsError,
    FactsBuilderEvidenceError,
    FactsBuilderContradictionError,
    FactsBuilderAssemblyError,
)

# Sub-worker functions (TC-411, TC-412, TC-413)
from .extract_claims import (
    extract_claims,
    ClaimsExtractionError,
    ClaimsValidationError,
    compute_claim_id,
    normalize_claim_text,
    classify_claim_kind,
)
from .map_evidence import (
    map_evidence,
    EvidenceMappingError,
)
from .detect_contradictions import (
    detect_contradictions,
    ContradictionDetectionError,
)

__all__ = [
    # Main integrator (TC-410)
    'execute_facts_builder',
    'FactsBuilderError',
    'FactsBuilderClaimsError',
    'FactsBuilderEvidenceError',
    'FactsBuilderContradictionError',
    'FactsBuilderAssemblyError',
    # Sub-worker functions
    'extract_claims',
    'map_evidence',
    'detect_contradictions',
    # Exceptions
    'ClaimsExtractionError',
    'ClaimsValidationError',
    'EvidenceMappingError',
    'ContradictionDetectionError',
    # Utilities
    'compute_claim_id',
    'normalize_claim_text',
    'classify_claim_kind',
]
