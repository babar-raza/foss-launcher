# Master Gap Index — Post-Self-Review Healing Plan

**Date**: 2026-03-08
**Source review covers**: TC-3829..TC-3855 (Tiers 0–5 across Heal H1–H5, Golden G1–G5, SEO-16–SEO-20)
**Total gaps**: 19 across 4 plan files
**All gaps have taskcards**: yes

---

## All Gaps at a Glance

| Gap ID  | Severity  | Plan File                     | Taskcard | One-line description |
|---------|-----------|-------------------------------|----------|----------------------|
| G-HL-01 | High      | HL-heal-loop-hardening.md     | HL-01    | ~~3-step multi-step heal integration test absent~~ **Done** |
| G-HL-02 | High      | HL-heal-loop-hardening.md     | HL-02    | ~~Regression rollback integration test absent~~ **Done** |
| G-HL-03 | High      | HL-heal-loop-hardening.md     | HL-03    | ~~Budget exhaustion integration test absent~~ **Done** |
| G-HO-01 | High      | HO-heal-h5-optimization.md   | HO-01    | H5.1: Skipped pages dropped from page_results (empty manifest risk) |
| G-HO-02 | Critical  | HO-heal-h5-optimization.md   | HO-02    | H5.2: Worker skip in graph_builder.py not implemented |
| G-HO-03 | Medium    | HO-heal-h5-optimization.md   | HO-03    | ~~H5.4: FOSS_LAUNCHER_LLM_CACHE=1 not set in heal session~~ **Done** |
| G-HO-04 | Medium    | HO-heal-h5-optimization.md   | HO-04    | H5.5: Adaptive F→D→C page prioritization absent |
| G-HO-05 | High      | HO-heal-h5-optimization.md   | HO-05    | H5.6: asyncio.gather page/evaluate parallelism not implemented |
| G-HO-06 | High      | HO-heal-h5-optimization.md   | HO-06    | H5.8: Section-level finding→section_id granularity absent |
| G-GE-01 | Critical  | GE-golden-enforcement.md     | GE-01    | G3: Pass 2 LLM retry in enforce_block_spec deferred |
| G-GE-02 | High      | GE-golden-enforcement.md     | GE-02    | G3: OPT-5 section-level asyncio.gather not implemented |
| G-GE-03 | Medium    | GE-golden-enforcement.md     | GE-03    | G2: OPT-2 max_tokens wiring unverified |
| G-GE-04 | Medium    | GE-golden-enforcement.md     | GE-04    | G2: OPT-4 api_surface_block pruning unverified |
| G-GE-05 | Low       | GE-golden-enforcement.md     | GE-05    | G1: has_code acceptance check not tested |
| G-ST-01 | Medium    | ST-seo-test-gaps.md          | ST-01    | SEO-16: 5 of 12 contextual link tests missing |
| G-ST-02 | Low       | ST-seo-test-gaps.md          | ST-02    | SEO-18: 3 of 7 freshness date tests missing |
| G-ST-03 | Medium    | ST-seo-test-gaps.md          | ST-03    | SEO-19: _check_anchor_diversity signature mismatch + 5 tests missing |
| G-ST-04 | Medium    | ST-seo-test-gaps.md          | ST-04    | SEO-20: FK threshold + table + long-sentence + abbreviation tests missing |
| G-GV-01 | Low       | ST-seo-test-gaps.md          | GV-01    | AG-002: evaluate/worker.py modified under wrong TC's allowed_paths |

---

## Recommended Execution Order

### Batch 1 — Critical correctness (do first)
- **GE-01** — Pass 2 LLM retry (3-pass promise broken without it)
- **HO-02** — H5.2 graph_builder worker skip (100% upstream savings undelivered)
- **HO-01** — H5.1 safe skip with cached PageIR (empty manifest risk)

### Batch 2 — Integration test coverage
- **HL-01** — 3-step heal test
- **HL-02** — Regression rollback test
- **HL-03** — Budget exhaustion test

### Batch 3 — Parallelism and performance
- **GE-02** — OPT-5 section-level gather (depends: GE-01 stable)
- **HO-05** — H5.6 page-level gather (depends: GE-02 stable, HO-01 stable)
- **HO-06** — H5.8 section-id granularity (depends: HO-05 stable)

### Batch 4 — Configuration and adaptive logic
- **HO-03** — H5.4 cache env var
- **HO-04** — H5.5 adaptive prioritization
- **GE-03** — OPT-2 max_tokens wiring
- **GE-04** — OPT-4 pruning wiring

### Batch 5 — Test gaps (can run any time, no ordering deps)
- **ST-01** — SEO-16 contextual link tests
- **ST-02** — SEO-18 freshness tests
- **ST-03** — SEO-19 anchor diversity + signature fix
- **ST-04** — SEO-20 FK threshold tests
- **GE-05** — G1 has_code test
- **GV-01** — AG-002 governance remediation

---

## Sequencing Constraints

```
GE-01 (Pass 2 stable) → GE-02 (section gather)
GE-02 (section gather stable) → HO-05 (page gather, same file)
HO-01 (safe skip stable) → HO-05 (page gather, same file)
HO-05 (page gather stable) → HO-06 (section-id granularity, same file)
```

All other taskcards are file-independent and can run in parallel.

---

## Gate: All Gaps Closed

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
# Expected: N passed, 0 failed
```

Additional integration verification after HO-02:
```bash
launch heal --run-dir <latest-run-dir> --dry-run
# Expected: HealDecision JSON printed; no Understand/Planner workers logged when responsible_worker=generate
```
