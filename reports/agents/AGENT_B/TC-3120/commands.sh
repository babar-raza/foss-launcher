#!/bin/bash
# Agent B — TC-3120 — Commands run

# Verification: confirm fix is in place
grep -n "_match_truth" src/launch/cli/triage.py
grep -n "truth.*issue.get" src/launch/cli/triage.py  # should return no output

# Run targeted tests (run by Agent C — see agent_c/TC-3120/evidence.md)
.venv/Scripts/python.exe -m pytest tests/unit/cli/test_triage.py -x -v
