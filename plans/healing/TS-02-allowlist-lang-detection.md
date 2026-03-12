# TS-02 — Fix Allowlist Language Detection Gate

## Context

HC-01 changed `_build_import_allowlist()` in `extract.py` to use
TreeSitterAnalyzer for non-Python exports. But the gate condition uses
`getattr(product, "lang_tag", "")` which returns `""` for most products,
causing the TreeSitter path to run (or not run) incorrectly:

- If `lang_tag=""` → `"".lower() not in ("python","py")` → `True` →
  enters TreeSitter path even for Python repos (finds nothing, wastes time)
- If `lang_tag` not set → same as above
- The original code detected language from file existence (`__init__.py`
  → Python, `package.json` → JS, `go.mod` → Go). HC-01 broke that cascade.

Additionally, the code scans via `rglob("*")[:100]` which is a very broad
glob, and uses `if len(allowlist) > 5: break` as an undocumented heuristic.

## Status: Done

## Gap linkage

| Gap ID | Description |
|--------|-------------|
| G-02 | HC-01 `lang_tag` gate: enters TreeSitter path incorrectly for Python repos |

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

Restore the original file-detection cascade and add TreeSitter as a new
branch at the end for languages not already covered:

```python
def _build_import_allowlist(repo_dir, package_root, product):
    allowlist = []
    if product.canonical_import:
        allowlist.append(product.canonical_import)
    if not package_root:
        return allowlist

    # Python: parse __init__.py (ORIGINAL — unchanged)
    init_path = repo_dir / package_root / "__init__.py"
    if init_path.exists():
        allowlist.extend(_python_allowlist_from_init(init_path, package_root))
        return allowlist

    # Node/TS: package.json (ORIGINAL — unchanged)
    pkg_json = repo_dir / "package.json"
    if pkg_json.exists():
        # ... existing code ...
        return allowlist

    # Go: go.mod (ORIGINAL — unchanged)
    go_mod = repo_dir / "go.mod"
    if go_mod.exists():
        # ... existing code ...
        return allowlist

    # NEW: For other languages (Java, C#, Rust, etc.), use TreeSitter
    src_root = repo_dir / package_root
    if src_root.is_dir():
        try:
            from launcher.shared.ts_analyzer import analyzer as _ts
            from launcher.workers.understand.file_classifier import LANG_BY_EXT
            _non_py = set(LANG_BY_EXT.keys()) - {".py", ".pyi"}
            for f in sorted(src_root.rglob("*"))[:100]:
                if f.suffix not in _non_py or not f.is_file():
                    continue
                lang = LANG_BY_EXT.get(f.suffix, "")
                if not lang:
                    continue
                try:
                    exports = _ts.extract_exports_from_code(
                        f.read_text(encoding="utf-8", errors="replace"), lang)
                    allowlist.extend(exports)
                except Exception:
                    continue
                if len(allowlist) > 10:
                    break
        except ImportError:
            pass

        # Regex fallback for Java package / C# namespace
        if len(allowlist) <= 1:
            # ... existing Java/C# regex scanning ...

    return allowlist
```

Key changes from current code:
1. Remove the `lang_tag` gate entirely — detect from files
2. TreeSitter path is a fallback AFTER Python/JS/Go detection
3. Add `f.is_file()` guard to skip directories
4. Raise threshold from `> 5` to `> 10` and document it
5. Regex fallback condition: `len(allowlist) <= 1` (only canonical_import)

### Allowed paths

- `src/launcher/workers/understand/extract.py`

### Forbidden

Any other file or path.

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v` — 0 failures
- **Tests**: Full suite 0 failures
- **Config respected**: Python repos still use `__init__.py` path exclusively
- **Config respected**: JS repos still use `package.json` path exclusively
- **Config respected**: Java/C# repos reach TreeSitter export extraction
- No mock data in production paths

## Deliverables

- Updated `extract.py` with corrected `_build_import_allowlist()` logic
- No TODOs, no stubs

## Hard rules

- Keep `_build_import_allowlist` signature unchanged
- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Keep code/docs/tests in sync
- Python path MUST remain unchanged and use `__init__.py` / `__all__`

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | All detection cascades restored; TreeSitter is additive only |
| Consistency | Same file-detection pattern as pre-HC-01 code |
| Production grading | No silent wrong-path execution for any product |
| Correctness | Python repos never enter TreeSitter path; Java repos do |
| Robustness | `is_file()` guard; bounded rglob; ImportError fallback |
| Performance | rglob capped at 100; early break at threshold |
| Minimality | Only `_build_import_allowlist()` changed |
| Spec alignment | Original detection cascade preserved |

## Now (runbook)

```bash
# 1. Edit extract.py: restore file-detection cascade in _build_import_allowlist
#    Move TreeSitter to a fallback branch after Python/JS/Go

# 2. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x

# 3. Verify Python path unchanged
grep -n "__init__.py" src/launcher/workers/understand/extract.py
# Should still have the init_path.exists() check before any TreeSitter code
```
