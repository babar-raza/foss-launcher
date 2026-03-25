#!/usr/bin/env bash
# TC-3263 Commands Log
# Run: 20260228_123000

# --- STEP 0: Preconditions ---
grep -n "status:" plans/taskcards/TC-3211_w10_fq4_heading_fusion_fix.md | head -1
grep -n "status:" plans/taskcards/TC-3212_placeholder_page_frontmatter.md | head -1
grep -n "FQ-3\|TRUNCATION\|truncat" src/launch/workers/w10_fixer/worker.py | head -20
grep -n "FQ-3\|FQ3\|truncat" src/launch/workers/w9_validator/gates/gate_17_prelints.py | head -20

# --- STEP 1-3: Reading files (done via file read tools) ---
# sed -n '50,80p' src/launch/workers/w10_fixer/worker.py
# sed -n '856,890p' src/launch/workers/w10_fixer/worker.py
# tail -60 tests/unit/workers/test_w10_scaffold_fix.py

# --- STEP 4: Implement improved FQ-3 strategy ---
# (Applied via Python script: add module-level constants + replace FQ-3 block)
.venv/Scripts/python.exe -c "import ast; ast.parse(open('src/launch/workers/w10_fixer/worker.py').read()); print('Syntax OK')"

# --- STEP 5: Add 4 unit tests ---
# (Appended via cat >> to test_w10_scaffold_fix.py)

# --- STEP 6: Run targeted tests ---
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w10_scaffold_fix.py -v -k "fq3 or FQ3"
# Result: 4 passed

# --- STEP 7: Run full W10 suite ---
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_w10_scaffold_fix.py \
  tests/unit/workers/test_w10_path_normalization.py \
  tests/unit/workers/test_w10_kb_howto_fix.py -v
# Result: 101 passed, 0 failed
