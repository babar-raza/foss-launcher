# TC-1020 Evidence Report — Update Specs for Exhaustive Ingestion

**Agent:** agent-c
**Date:** 2026-02-07
**Status:** Complete

## Files Changed

### 1. `specs/02_repo_ingestion.md`
**Changes:**
- **Added "Exhaustive file inventory" section** (after Step 1 Clone and fingerprint): Mandates W1 MUST record ALL files in `repo_inventory.paths[]` regardless of extension. Extension-based heuristics may be used as scoring boosts but not as filters. Binary files recorded with `binary: true` flag. Unknown extensions recorded with `extension: ""`.
- **Added "Configurable scan directories" section**: New `run_config.ingestion.scan_directories` config field with default of `["."]` (repo root) for backward compatibility.
- **Added ".gitignore support" section**: New `run_config.ingestion.gitignore_mode` config field with three modes (`respect`, `ignore`, `strict`), defaulting to `respect` for backward compatibility.
- **Updated phantom path detection algorithm**: Changed step 1 from scanning only `*.md, *.rst, *.txt` to scanning ALL text-based files (non-binary) for phantom path references. The original extensions are noted as highest priority but no longer exclusive.

### 2. `specs/03_product_facts_and_evidence.md`
**Changes:**
- **Added "Exhaustive document processing" section** (after "Rule" paragraph, before Edge Case): Mandates W2 MUST process ALL documents without count limits. No maximum document count, no minimum word-count filters, no keyword-presence filters. Scoring boosts allowed but not filtering gates.
- **Added evidence priority clarification**: Explicit statement that priority ranking is for PRIORITIZATION of conflicting evidence, NOT for FILTERING of evidence sources. All sources must be ingested and recorded regardless of priority level.
- **Added "Candidate extraction policy"** (after the detailed priority table): Reinforces that no word-count or keyword-presence filters may exclude documents from evidence extraction.

### 3. `specs/05_example_curation.md`
**Changes:**
- **Updated "Discover candidate examples" step**: Added reference to configurable example directories beyond the standard three.
- **Expanded example discovery order**: Added step 5 (source code inline examples) before generated snippets, and referenced configurable directories in step 1.
- **Added "Configurable example discovery directories" section**: New `run_config.ingestion.example_directories` config field that unions with standard directories (`examples/`, `samples/`, `demo/`). Alphabetically sorted for determinism. Default: standard dirs only.
- **Added "Language detection and unknown files" section**: Files with unrecognized extensions recorded with `language: "unknown"` instead of being dropped. Syntax validation may be skipped for unknown languages but snippets still appear in catalog.

### 4. `specs/21_worker_contracts.md`
**Changes:**
- **W1 RepoScout binding requirements**: Added 7 new bullet points mandating exhaustive file inventory, no extension-based filters, binary file recording, configurable scan directories, and .gitignore support. Cross-references spec 02.
- **W2 FactsBuilder binding requirements**: Added 6 new bullet points mandating no document count caps, no word-count filters, no keyword-presence filters, priority as scoring not filtering. Cross-references spec 03.
- **W3 SnippetCurator binding requirements**: Added 2 new bullet points for configurable example directories and unknown-language handling. Cross-references spec 05.

## New Config Fields Introduced (all with backward-compatible defaults)

| Config Field | Default | Spec |
|---|---|---|
| `run_config.ingestion.scan_directories` | `["."]` (repo root) | spec 02 |
| `run_config.ingestion.gitignore_mode` | `"respect"` | spec 02 |
| `run_config.ingestion.example_directories` | `[]` (standard dirs only) | spec 05 |

## Commands Run

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
# Result: 1949 passed, 12 skipped, 0 failed (76.67s)
```

## Deterministic Verification
- All spec changes are additive (no existing requirements deleted)
- All new config fields have sensible defaults ensuring backward compatibility
- No code changes were made, only spec/documentation changes
- Test suite passes identically before and after changes

## Cross-Reference Consistency Check
- spec 02 references `run_config.ingestion.scan_directories` and `run_config.ingestion.gitignore_mode` --> spec 21 W1 contract references both
- spec 03 references exhaustive processing mandate --> spec 21 W2 contract references the same mandate with cross-link
- spec 05 references `run_config.ingestion.example_directories` --> spec 21 W3 contract references the same with cross-link
- All four specs use consistent RFC-style language (MUST, SHOULD, MAY)
- All four specs tag changes with `(TC-1020)` for traceability
