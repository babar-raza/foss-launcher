"""Profile TC-412 evidence mapping performance to identify bottlenecks."""

import json
import time
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.launch.workers.w2_facts_builder.map_evidence import (
    enrich_claim_with_evidence,
    compute_text_similarity,
    find_supporting_evidence_in_docs,
)


def profile_evidence_mapping():
    """Profile TC-412 with a subset of claims to measure performance."""

    # Use the latest Note pilot run
    run_dir = Path("runs/r_20260207T150233Z_launch_pilot-aspose-note-foss-python_ec274a7_default_3489bec8")

    if not run_dir.exists():
        print(f"Run directory not found: {run_dir}")
        return

    # Load data
    print("Loading data...")
    with open(run_dir / "artifacts/extracted_claims.json", encoding='utf-8') as f:
        claims_data = json.load(f)

    with open(run_dir / "artifacts/discovered_docs.json", encoding='utf-8') as f:
        docs_data = json.load(f)

    with open(run_dir / "artifacts/discovered_examples.json", encoding='utf-8') as f:
        examples_data = json.load(f)

    claims = claims_data['claims']
    doc_files = docs_data['doc_entrypoint_details']
    example_files = examples_data['example_file_details']
    repo_dir = run_dir / "work/repo"

    print(f"Total claims: {len(claims)}")
    print(f"Total docs: {len(doc_files)}")
    print(f"Total examples: {len(example_files)}")
    print()

    # Profile first 10 claims
    sample_size = min(10, len(claims))
    print(f"Profiling first {sample_size} claims...")

    total_time = 0
    for i, claim in enumerate(claims[:sample_size], 1):
        start = time.time()
        enriched = enrich_claim_with_evidence(
            claim, doc_files, example_files, repo_dir
        )
        elapsed = time.time() - start
        total_time += elapsed

        print(f"Claim {i}/{sample_size}: {elapsed:.2f}s (evidence_count: {enriched.get('evidence_count', 0)})")

    print()
    print(f"Average time per claim: {total_time/sample_size:.2f}s")
    print(f"Estimated total time for {len(claims)} claims: {(total_time/sample_size * len(claims))/60:.1f} minutes")
    print()

    # Profile individual operations
    print("Profiling individual operations...")

    test_claim = claims[0]
    test_doc = doc_files[0]
    test_doc_path = repo_dir / test_doc['path']

    if test_doc_path.exists():
        # Time file read
        start = time.time()
        content = test_doc_path.read_text(encoding='utf-8', errors='ignore')
        read_time = time.time() - start
        print(f"File read time: {read_time*1000:.2f}ms (size: {len(content)} chars)")

        # Time similarity computation
        start = time.time()
        similarity = compute_text_similarity(test_claim['claim_text'], content)
        sim_time = time.time() - start
        print(f"Similarity computation: {sim_time*1000:.2f}ms")

        # Estimate total operations
        total_ops = len(claims) * (len(doc_files) + len(example_files))
        per_op_time = (read_time + sim_time)
        estimated_total = (per_op_time * total_ops) / 60
        print(f"Estimated time (read+sim per operation): {estimated_total:.1f} minutes")


if __name__ == "__main__":
    profile_evidence_mapping()
