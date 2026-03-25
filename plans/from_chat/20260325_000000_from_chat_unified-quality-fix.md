# From-Chat Plan: Unified Quality Fix (2026-03-25)

## Context
Cross-plan re-evaluation of 3 prior plans against current codebase.
Root cause: generate phase quality failures, evaluate false positives, governance debt.

## Goals
1. Eliminate evaluate false-positives (string-unaware class scan, missing enum members, kept syntax errors)
2. Improve generate quality (model routing, anti-echo, identifier repair, strip-and-replace, cross-section context, deterministic See Also)
3. Governance: commit working tree, add evidence tooling

## Steps (from elegant-spinning-blanket.md)
1. GOV-1: Commit working tree modifications
2. GEN-1: Switch pilot configs generate:standard → generate:reasoning
3. EVL-1+2+3+4: Evaluate false-positive reduction (api_verification.py + worker.py syntax gate)
4. GEN-4: Strip-and-replace for code blocks
5. GEN-2: Anti-echo guard in section_writer.txt
6. GEN-3: Identifier repair softening
7. GEN-5: Cross-section context injection
8. GEN-6: Deterministic See Also
9. UND-1: Snippet extraction from test files
10. ARC-1: Code synthesis stub → real
11. ARC-2: Heal loop improvement
12. GOV-2+3: Tooling (agents.md + evidence script)

## Acceptance criteria
- PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ passes, 0 failures
- D+F rate ≤ 30% on cells/python pilot (from 55% baseline)
- 0 [identifier omitted] placeholders in reference pages
- All See Also links resolve to known deployed slugs
- git status shows clean working tree for tracked files

## Evidence commands
- PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q
- python scripts/check_tc_evidence.py
- git log --oneline -20
- git status --short | grep "^ M" | wc -l

## Risks
- reasoning model may produce preamble before BlockIR JSON (add extraction guard)
- strip-and-replace depends on snippet pool coverage
- cross-section sequential generation increases latency

## Open questions
(none — all resolved by codebase analysis)
