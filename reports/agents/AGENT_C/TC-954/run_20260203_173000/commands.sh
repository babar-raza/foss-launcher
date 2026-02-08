#!/bin/bash
# TC-954 Verification Commands
# Date: 2026-02-03
# Agent: AGENT_C

set -e

echo "=== TC-954: Absolute Cross-Subdomain Links Verification ==="
echo ""

# Change to project root
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"

echo "1. Verify function exists in public_urls.py"
grep -n "def build_absolute_public_url" src/launch/resolvers/public_urls.py && echo "✅ PASS: Function exists"
echo ""

echo "2. Verify subdomain mapping"
grep -A 6 "subdomain_map = {" src/launch/resolvers/public_urls.py && echo "✅ PASS: All 5 subdomains mapped"
echo ""

echo "3. Run TC-938 unit tests"
".venv\Scripts\python.exe" -m pytest tests/unit/workers/test_tc_938_absolute_links.py -v
echo ""

echo "4. Run specific test cases"
echo "  - Test docs section..."
".venv\Scripts\python.exe" -m pytest tests/unit/workers/test_tc_938_absolute_links.py::TestBuildAbsolutePublicUrl::test_docs_section_absolute_url -v
echo "  - Test reference section..."
".venv\Scripts\python.exe" -m pytest tests/unit/workers/test_tc_938_absolute_links.py::TestBuildAbsolutePublicUrl::test_reference_section_absolute_url -v
echo "  - Test products section..."
".venv\Scripts\python.exe" -m pytest tests/unit/workers/test_tc_938_absolute_links.py::TestBuildAbsolutePublicUrl::test_products_section_absolute_url -v
echo "  - Test kb section..."
".venv\Scripts\python.exe" -m pytest tests/unit/workers/test_tc_938_absolute_links.py::TestBuildAbsolutePublicUrl::test_kb_section_absolute_url -v
echo "  - Test blog section..."
".venv\Scripts\python.exe" -m pytest tests/unit/workers/test_tc_938_absolute_links.py::TestBuildAbsolutePublicUrl::test_blog_section_absolute_url -v
echo ""

echo "5. Verify cross-section link scenarios"
".venv\Scripts\python.exe" -m pytest tests/unit/workers/test_tc_938_absolute_links.py::TestCrossSectionLinkScenarios -v
echo ""

echo "6. Search for usage examples"
grep -rn "build_absolute_public_url" tests/unit/ --include="*.py" | head -20
echo ""

echo "=== TC-954 Verification Complete ==="
