# Healing Phase 2 — TreeSitter Integration Post-Review

## Origin

Honest self-review of the HC-01..HC-06 healing execution.
These taskcards fix every gap, bug, and architectural violation surfaced
during the dimension-by-dimension review (2026-03-07).

## Gap / Blocker Inventory

| ID | Gap | Severity | File(s) | Taskcard |
|----|-----|----------|---------|----------|
| G-01 | `_ensure_ts()` has TOCTOU race: global `_ts_available` modified without lock while `_get_parser()` claims thread safety | High | ts_analyzer.py | TS-01 |
| G-02 | HC-01 `lang_tag` gate: `getattr(product, "lang_tag", "")` returns `""` for most products, entering TreeSitter path for Python repos and skipping file-detection cascade | High | extract.py | TS-02 |
| G-03 | Go import regex unanchored: `"(github\.com/aspose/\w+)"` matches inside string literals; inconsistent with other anchored patterns | Medium | ts_analyzer.py | TS-01 |
| G-04 | `_language_cache` dict defined but never used — dead state | Low | ts_analyzer.py | TS-01 |
| G-05 | `todo_fixme_re` pattern `#\s*(?:TODO\|FIXME)` only matches `#` comments; Java/C#/JS/Go/Rust use `//`, making the multi-language extension of `extract_code_limitations` partially futile | Medium | code_analyzer.py | TS-03 |
| G-06 | Cross-layer import: `shared/code_analyzer.py` imports from `workers/understand/file_classifier.py` — architectural violation (shared must not depend on workers) | High | code_analyzer.py, file_classifier.py | TS-04 |
| G-07 | `discover_source_files` now iterates ALL `LANG_BY_EXT` keys including `.sh`, `.sql`, `.ps1`, `.zsh` — 26+ `rglob` calls on large repos, includes non-compilable files | Medium | code_analyzer.py | TS-04 |
| G-08 | `normalize_imports._replacer` has 7 identical `return original.replace(old_pkg, canonical_import)` branches — should be collapsed | Low | ts_analyzer.py | TS-01 |
| G-09 | No dedicated unit tests for HC-01 (allowlist with TreeSitter), HC-03 (section_validator multi-lang), HC-04 (discover_source_files/manifests/limitations) | High | tests/ | TS-05 |

## Execution Order

1. **TS-01** — ts_analyzer.py correctness + cleanup (G-01, G-03, G-04, G-08)
2. **TS-02** — extract.py allowlist logic fix (G-02)
3. **TS-03** — code_analyzer.py TODO/FIXME regex fix (G-05)
4. **TS-04** — cross-layer import elimination + discovery curating (G-06, G-07)
5. **TS-05** — comprehensive unit tests for HC-01, HC-03, HC-04 (G-09)

## Taskcard Files

- `plans/healing/TS-01-ts-analyzer-correctness.md`
- `plans/healing/TS-02-allowlist-lang-detection.md`
- `plans/healing/TS-03-todo-fixme-multi-lang.md`
- `plans/healing/TS-04-cross-layer-import-fix.md`
- `plans/healing/TS-05-missing-unit-tests.md`
