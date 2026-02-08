#!/usr/bin/env bash
# TC-955 Storage Model Spec Verification - Commands Used

# Read taskcard
cat "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\plans\taskcards\TC-955_storage_model_spec.md"

# Read storage model spec
cat "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\40_storage_model.md"

# Find artifact files
find . -name "product_facts.json" -type f
find . -name "snippet_catalog.json" -type f
find . -name "evidence_map.json" -type f
find . -name "page_plan.json" -type f
find . -name "repo_inventory.json" -type f

# Read sample artifacts from recent run
RUN_DIR="c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\runs\r_20260203T095219Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5"

# Read artifacts (sample first 50 lines)
head -50 "$RUN_DIR/artifacts/product_facts.json"
head -50 "$RUN_DIR/artifacts/evidence_map.json"
head -50 "$RUN_DIR/artifacts/snippet_catalog.json"
head -100 "$RUN_DIR/artifacts/page_plan.json"
head -100 "$RUN_DIR/artifacts/repo_inventory.json"

# List run directory structure
ls -la "$RUN_DIR"

# Traceability test: Find getting-started page in page_plan
cat "$RUN_DIR/artifacts/page_plan.json" | jq '.pages[] | select(.output_path | contains("getting-started"))'

# Traceability test: Look up claim in evidence_map
cat "$RUN_DIR/artifacts/evidence_map.json" | jq '.claims[] | select(.claim_id == "05218d94b3cbd4922ba77f0e63dd77c3fb3c26125f091c6491d44f509c8bc755")'

# Traceability test: Verify source file exists
ls "$RUN_DIR/work/repo/README.md"

# Traceability test: Read source file lines 1-30
head -30 "$RUN_DIR/work/repo/README.md"

# Check telemetry database
ls "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\telemetry.db"

# Database schema (requires sqlite3)
# sqlite3 "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\telemetry.db" ".schema runs"
# sqlite3 "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\telemetry.db" ".schema events"

# Create report directory
mkdir -p "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\reports\agents\AGENT_D\TC-955\run_20260203_173000"

# Verify report directory
ls -la "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\reports\agents\AGENT_D\TC-955\run_20260203_173000"
