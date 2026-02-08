#!/usr/bin/env python3
"""TC-966 Validation Script - Demonstrates Fix Works

This script validates that TC-966 fix successfully enables template discovery
for all 5 sections (docs, products, reference, kb, blog) by discovering
templates in placeholder directories instead of literal locale/platform paths.

Usage:
    python reports/agents/AGENT_B/TC-966/VALIDATION_SCRIPT.py

Expected Output:
    All 5 sections should show >0 templates discovered
    All sections should use placeholder directories
"""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from launch.workers.w4_ia_planner.worker import enumerate_templates, classify_templates


def validate_template_discovery():
    """Validate that all 5 sections discover templates from placeholder directories."""

    print("=" * 70)
    print("TC-966 VALIDATION: W4 Template Enumeration Fix")
    print("=" * 70)
    print()
    print("Testing template discovery for all 5 sections...")
    print()

    template_dir = Path("specs/templates")

    sections = [
        ("docs.aspose.org", "3d", "Documentation"),
        ("products.aspose.org", "cells", "Products"),
        ("reference.aspose.org", "cells", "API Reference"),
        ("kb.aspose.org", "cells", "Knowledge Base"),
        ("blog.aspose.org", "3d", "Blog"),
    ]

    all_passed = True
    results = []

    for subdomain, family, label in sections:
        templates = enumerate_templates(
            template_dir=template_dir,
            subdomain=subdomain,
            family=family,
            locale="en",
            platform="python"
        )

        count = len(templates)
        passed = count > 0

        # Check if uses placeholder directories
        uses_placeholders = False
        if templates:
            first_template = templates[0]["template_path"]
            uses_placeholders = any(
                placeholder in first_template
                for placeholder in ["__LOCALE__", "__PLATFORM__", "__POST_SLUG__", "__CONVERTER_SLUG__", "__REFERENCE_SLUG__"]
            )

        # Classify templates
        mandatory, optional = classify_templates(templates, launch_tier="full")

        status = "✓ PASS" if passed else "✗ FAIL"

        print(f"{label:20} ({subdomain})")
        print(f"  Status: {status}")
        print(f"  Templates discovered: {count}")
        print(f"  Mandatory: {len(mandatory)}")
        print(f"  Optional: {len(optional)}")
        print(f"  Uses placeholder dirs: {uses_placeholders}")

        if templates and count <= 3:
            # Show all templates for small counts
            for t in templates:
                path_rel = t["template_path"].replace(str(template_dir) + "\\", "").replace(str(template_dir) + "/", "")
                print(f"    - {path_rel}")
        elif templates:
            # Show first template as example
            path_rel = templates[0]["template_path"].replace(str(template_dir) + "\\", "").replace(str(template_dir) + "/", "")
            print(f"    Example: {path_rel[:80]}...")

        print()

        results.append({
            "label": label,
            "subdomain": subdomain,
            "count": count,
            "passed": passed,
            "uses_placeholders": uses_placeholders
        })

        if not passed:
            all_passed = False

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    total_templates = sum(r["count"] for r in results)

    print(f"Sections tested: {total_count}")
    print(f"Sections passing: {passed_count}/{total_count}")
    print(f"Total templates discovered: {total_templates}")
    print()

    if all_passed:
        print("✓ VALIDATION PASSED - All sections discover templates!")
        print()
        print("Before TC-966 fix:")
        print("  docs=0, products=0, reference=0, kb=0, blog=8 (4/5 broken)")
        print()
        print(f"After TC-966 fix:")
        for r in results:
            print(f"  {r['label'].lower()[:4]}={r['count']}", end="")
            if r != results[-1]:
                print(", ", end="")
        print(" (5/5 working)")
        print()
        return 0
    else:
        print("✗ VALIDATION FAILED - Some sections returned 0 templates")
        print()
        print("Failed sections:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['label']} ({r['subdomain']}): {r['count']} templates")
        print()
        return 1


if __name__ == "__main__":
    try:
        exit_code = validate_template_discovery()
        sys.exit(exit_code)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
