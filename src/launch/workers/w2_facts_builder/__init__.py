"""W2 FactsBuilder worker - Extract product facts and evidence.

TC-411: Extract claims from product documentation.

Spec references:
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/03_product_facts_and_evidence.md (Facts extraction)
- specs/04_claims_compiler_truth_lock.md (Claims structure)
"""

from .extract_claims import (
    extract_claims,
    ClaimsExtractionError,
    ClaimsValidationError,
    compute_claim_id,
    normalize_claim_text,
    classify_claim_kind,
)

__all__ = [
    'extract_claims',
    'ClaimsExtractionError',
    'ClaimsValidationError',
    'compute_claim_id',
    'normalize_claim_text',
    'classify_claim_kind',
]
