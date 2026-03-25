#!/usr/bin/env bash
# GEN-001 Verification Commands
# Run from the repo root: bash reports/agents/B1_generate_fix/GEN-001/commands.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "=== GEN-001 Verification ==="

# 1. Syntax checks
echo ""
echo "--- Syntax checks ---"
python -c "import ast; ast.parse(open('src/launcher/workers/generate/worker.py').read()); print('worker.py: OK')"
python -c "import ast; ast.parse(open('src/launcher/workers/generate/section_prompt.py', encoding='utf-8').read()); print('section_prompt.py: OK')"
python -c "import ast; ast.parse(open('src/launcher/workers/generate/section_validator.py', encoding='utf-8').read()); print('section_validator.py: OK')"
python -c "import ast; ast.parse(open('src/launcher/workers/generate/_identifier_repair.py', encoding='utf-8').read()); print('_identifier_repair.py: OK')"

# 2. GEN-001 marker presence
echo ""
echo "--- GEN-001 markers ---"
grep -n "GEN-001" src/launcher/workers/generate/worker.py
grep -n "GEN-001\|prose_only" src/launcher/workers/generate/section_prompt.py
grep -n "GEN-001" src/launcher/workers/generate/section_validator.py
grep -n "GEN-001" src/launcher/workers/generate/_identifier_repair.py

# 3. prose_only parameter in build_section_prompt
echo ""
echo "--- prose_only parameter ---"
grep "prose_only" src/launcher/workers/generate/section_prompt.py
grep "prose_only" src/launcher/workers/generate/worker.py

# 4. _select_snippets_for_section function defined and called
echo ""
echo "--- _select_snippets_for_section ---"
grep -n "_select_snippets_for_section" src/launcher/workers/generate/worker.py

# 5. Code block rejection in validator
echo ""
echo "--- Code block rejection in validator ---"
grep -n "Rejecting LLM-generated code block\|_rejected_code_count" src/launcher/workers/generate/section_validator.py

# 6. Comment-line skip in identifier repair
echo ""
echo "--- Comment-line skip in _repair_code_segment ---"
grep -n "_code_part_for_scan\|code_for_scanning\|Skip pure comment" src/launcher/workers/generate/_identifier_repair.py

# 7. Phase C injection guard
echo ""
echo "--- Phase C guard condition ---"
grep -n "_selected_snippets and _prose_only_mode and not _fb" src/launcher/workers/generate/worker.py

# 8. _needs_code_retry suppression
echo ""
echo "--- _needs_code_retry suppression ---"
grep -n "_prose_only_mode" src/launcher/workers/generate/worker.py

# 9. Run relevant unit tests (requires pytest and project dependencies)
echo ""
echo "--- Unit tests (requires pytest + deps) ---"
if python -c "import pytest" 2>/dev/null; then
    python -m pytest tests/unit/workers/generate/test_section_validator.py \
                     tests/unit/workers/generate/test_identifier_repair.py \
                     tests/unit/workers/generate/test_section_prompt.py \
                     tests/unit/workers/generate/test_code_block_retry.py \
                     -v --tb=short
else
    echo "  pytest not available — skipping unit tests (syntax checks passed)"
fi

echo ""
echo "=== All checks complete ==="
