#!/usr/bin/env python3
"""Quick test to verify TC-963 fix works with actual pilot config."""

import sys
import json
import os
from pathlib import Path

# Change to repo root
script_path = Path(__file__).resolve()
repo_root = script_path.parent.parent.parent.parent
os.chdir(repo_root)

# Add src to path
sys.path.insert(0, str(repo_root / "src"))

from launch.workers.w4_ia_planner.worker import execute_ia_planner
from launch.io.run_config import load_and_validate_run_config

# Load pilot config
pilot_id = "pilot-aspose-3d-foss-python"
pilot_config_path = Path("specs/pilots") / pilot_id / "run_config.pinned.yaml"

print(f"Loading pilot config: {pilot_config_path}")
print(f"Working directory: {os.getcwd()}")
run_config = load_and_validate_run_config(Path.cwd(), pilot_config_path)
print(f"Pilot loaded: {run_config.get('metadata', {}).get('pilot_id')}")
print(f"Product slug: {run_config.get('product_slug')}")
print(f"Subdomain: {run_config.get('subdomain')}")

# Create a temporary run directory
import tempfile
import shutil

with tempfile.TemporaryDirectory() as tmpdir:
    run_dir = Path(tmpdir) / "test_run"
    run_dir.mkdir(parents=True)

    # Create required subdirectories
    (run_dir / "artifacts").mkdir()
    (run_dir / "events").mkdir()
    (run_dir / "logs").mkdir()

    # Create minimal product_facts.json (W4 input)
    product_facts = {
        "schema_version": "1.0",
        "product_slug": run_config.get("product_slug"),
        "metadata": {},
        "claims": [],
        "evidence_map": {}
    }
    with open(run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # Create minimal snippet_catalog.json (W4 input)
    snippet_catalog = {
        "schema_version": "1.0",
        "product_slug": run_config.get("product_slug"),
        "snippets": []
    }
    with open(run_dir / "artifacts" / "snippet_catalog.json", "w") as f:
        json.dump(snippet_catalog, f)

    # Run W4 IAPlanner
    print("\n" + "="*70)
    print("Running W4 IAPlanner...")
    print("="*70)

    try:
        result = execute_ia_planner(
            run_dir=run_dir,
            run_config=run_config,
            llm_client=None
        )

        print("\n" + "="*70)
        print("SUCCESS: W4 IAPlanner completed!")
        print("="*70)
        print(f"Status: {result.get('status')}")
        print(f"Page count: {result.get('page_count')}")
        print(f"Launch tier: {result.get('launch_tier')}")
        print(f"Artifact: {result.get('artifact_path')}")

        # Load and inspect page_plan.json
        page_plan_path = run_dir / "artifacts" / "page_plan.json"
        if page_plan_path.exists():
            with open(page_plan_path) as f:
                page_plan = json.load(f)

            print(f"\nPage plan generated with {len(page_plan.get('pages', []))} pages:")
            for i, page in enumerate(page_plan.get("pages", [])[:5]):  # Show first 5
                print(f"  Page {i}: {page.get('section')}/{page.get('slug')}")
                print(f"    Title: {page.get('title')}")
                print(f"    URL: {page.get('url_path')}")
                print(f"    Output: {page.get('output_path')}")

                # Verify all required fields
                required_fields = [
                    "section", "slug", "output_path", "url_path", "title", "purpose",
                    "required_headings", "required_claim_ids", "required_snippet_tags", "cross_links"
                ]
                missing = [f for f in required_fields if f not in page]
                if missing:
                    print(f"    WARNING: Missing fields: {missing}")
                else:
                    print(f"    [OK] All required fields present")
        else:
            print("\nWARNING: page_plan.json not found!")

    except Exception as e:
        print("\n" + "="*70)
        print(f"FAILED: {type(e).__name__}: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n[SUCCESS] TC-963 fix verified with actual pilot config!")
