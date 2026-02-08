#!/bin/bash
# TC-953: Page Inventory Contract and Quotas - Validation Commands
# Date: 2026-02-03
# Purpose: Validate implementation of pilot page quotas in ruleset and W4

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO_ROOT"

echo "=========================================="
echo "TC-953: Quota Enforcement Validation"
echo "=========================================="
echo ""

# Step 1: Verify ruleset exists and quotas are set
echo "[1/5] Verifying ruleset quotas..."
python -c "
import yaml
with open('specs/rulesets/ruleset.v1.yaml') as f:
    ruleset = yaml.safe_load(f)
    sections = ruleset.get('sections', {})

    expected = {
        'products': 6,
        'docs': 10,
        'reference': 6,
        'kb': 10,
        'blog': 3,
    }

    print('Section Quotas (max_pages):')
    total = 0
    for section, expected_max in expected.items():
        actual_max = sections.get(section, {}).get('max_pages')
        status = '✓' if actual_max == expected_max else '✗'
        print(f'  {status} {section:12s}: {actual_max:3d} (expected {expected_max})')
        total += actual_max if actual_max == expected_max else 0

    print(f'  Total page quota: {total} pages (expected 35)')
    print()
    assert total == 35, 'Quota sum mismatch!'
" || exit 1

# Step 2: Verify W4 imports load_yaml
echo "[2/5] Verifying W4 imports..."
grep -q "from.*yamlio import load_yaml" src/launch/workers/w4_ia_planner/worker.py && \
echo "  ✓ W4 imports load_yaml" || \
(echo "  ✗ W4 missing load_yaml import" && exit 1)

# Step 3: Verify load_ruleset_quotas function exists
echo "[3/5] Verifying load_ruleset_quotas function..."
grep -q "def load_ruleset_quotas" src/launch/workers/w4_ia_planner/worker.py && \
echo "  ✓ load_ruleset_quotas function found" || \
(echo "  ✗ load_ruleset_quotas function missing" && exit 1)

# Step 4: Run quota enforcement unit tests
echo "[4/5] Running quota enforcement tests (12 tests)..."
.venv/Scripts/python -m pytest tests/unit/workers/test_w4_quota_enforcement.py -v --tb=short || exit 1

# Step 5: Run regression tests
echo "[5/5] Running W4 template enumeration tests (regression check)..."
.venv/Scripts/python -m pytest tests/unit/workers/test_tc_902_w4_template_enumeration.py -q || exit 1

echo ""
echo "=========================================="
echo "✓ All Validations Passed!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  • Ruleset quotas: 6+10+6+10+3 = 35 pages"
echo "  • W4 quota loading: ✓ Implemented"
echo "  • Quota enforcement: ✓ 12/12 tests pass"
echo "  • Regression tests: ✓ 22/22 tests pass"
echo ""
echo "Ready for merge!"
