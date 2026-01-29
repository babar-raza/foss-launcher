# Wave 4 Follow-Up: 38 MAJOR Gaps - Commands Executed
# Agent: AGENT_D (Docs & Specs)
# Session: run_20260127_144304
# Date: 2026-01-27

# Read gaps file
# Read: reports/pre_impl_verification/20260126_154500/agents/AGENT_S/GAPS.md (offset 1441, multiple reads)

# Validation commands (run after each spec modification)
python scripts/validate_spec_pack.py  # After specs/02
python scripts/validate_spec_pack.py  # After specs/03
python scripts/validate_spec_pack.py  # After specs/06
python scripts/validate_spec_pack.py  # After specs/21
python scripts/validate_spec_pack.py  # After specs/08
python scripts/validate_spec_pack.py  # After specs/14
python scripts/validate_spec_pack.py  # After specs/17
python scripts/validate_spec_pack.py  # After specs/19
python scripts/validate_spec_pack.py  # After specs/26

# Final validation
python scripts/validate_spec_pack.py

# File operations
# - Modified: specs/02_repo_ingestion.md (2 edits: examples discovery, test discovery)
# - Modified: specs/03_product_facts_and_evidence.md (1 edit: edge case handling)
# - Modified: specs/04_claims_compiler_truth_lock.md (verified already complete)
# - Modified: specs/05_example_curation.md (verified already complete)
# - Modified: specs/06_page_planning.md (1 edit: vague language fix)
# - Modified: specs/21_worker_contracts.md (9 edits: W1-W9 edge cases and failure modes)
# - Modified: specs/08_patch_engine.md (1 edit: additional edge cases)
# - Modified: specs/14_mcp_endpoints.md (1 edit: MCP best practices)
# - Modified: specs/17_github_commit_service.md (1 edit: auth best practices)
# - Verified: specs/schemas/commit_request.schema.json (already exists)
# - Verified: specs/schemas/open_pr_request.schema.json (already exists)
# - Modified: specs/19_toolchain_and_ci.md (1 edit: toolchain verification best practices)
# - Modified: specs/26_repo_adapters_and_variability.md (1 edit: adapter implementation guide)

# Vague language analysis
grep -i -c "\\bshould\\b\\|\\bmay\\b\\|\\bcould\\b" specs/02_repo_ingestion.md  # 4 instances (descriptive contexts)
grep -i -c "\\bshould\\b\\|\\bmay\\b\\|\\bcould\\b" specs/03_product_facts_and_evidence.md  # 3 instances (descriptive contexts)
grep -i -c "\\bshould\\b\\|\\bmay\\b\\|\\bcould\\b" specs/06_page_planning.md  # 0 instances
grep -i -c "\\bshould\\b\\|\\bmay\\b\\|\\bcould\\b" specs/21_worker_contracts.md  # 1 instance (descriptive context)
grep -i -c "\\bshould\\b\\|\\bmay\\b\\|\\bcould\\b" specs/08_patch_engine.md  # 0 instances
grep -i -c "\\bshould\\b\\|\\bmay\\b\\|\\bcould\\b" specs/14_mcp_endpoints.md  # 9 instances (SHOULD for recommendations)
grep -i -c "\\bshould\\b\\|\\bmay\\b\\|\\bcould\\b" specs/17_github_commit_service.md  # 4 instances (SHOULD for recommendations)
grep -i -c "\\bshould\\b\\|\\bmay\\b\\|\\bcould\\b" specs/19_toolchain_and_ci.md  # 18 instances (SHOULD for recommendations)
grep -i -c "\\bshould\\b\\|\\bmay\\b\\|\\bcould\\b" specs/26_repo_adapters_and_variability.md  # 10 instances (SHOULD for recommendations)

# Total: 49 instances (mostly SHOULD for non-binding recommendations, appropriate usage)
# All binding requirements use MUST/SHALL as required

# Evidence bundle creation
# mkdir -p reports/agents/AGENT_D/WAVE4_FOLLOW_UP_38_MAJOR/run_20260127_144304
# Created: plan.md
# Created: commands.sh (this file)
# To create: changes.md, gaps_closed.md, evidence.md, self_review.md
