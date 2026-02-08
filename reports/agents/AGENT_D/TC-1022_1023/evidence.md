# Combined Evidence: TC-1022 + TC-1023

**Agent:** agent-d
**Date:** 2026-02-07
**Taskcards:** TC-1022 (Exhaustive Documentation Discovery), TC-1023 (Configurable Scan Directories)

## Summary

TC-1022 and TC-1023 implement Phase 2 of the Comprehensive Healing Plan: W1/W2 Exhaustive Ingestion. These taskcards extend the W1 RepoScout discovery pipeline to record ALL repository files (not just doc-extension files) and to support configurable scan directories, exclude patterns, and extra example directories from the run_config.

## Files Modified

### TC-1022: Exhaustive Documentation Discovery
| File | Change Description |
|------|-------------------|
| `src/launch/workers/w1_repo_scout/discover_docs.py` | Added DOC_EXTENSIONS, BINARY_EXTENSIONS constants; added is_binary_file(); rewrote discover_documentation_files() for exhaustive recording; removed 50-line content scan limit; added file_extension, file_size_bytes, is_binary fields |
| `tests/unit/workers/test_tc_403_discover_docs.py` | Renamed tests for TC-1022 behavior; added TestBinaryDetection (4 tests), TestExhaustiveDiscovery (4 tests); added is_binary_file import |
| `tests/unit/workers/test_tc_400_repo_scout.py` | Updated test_no_docs_no_examples to expect non-zero docs_found (exhaustive discovery) |

### TC-1023: Configurable Scan Directories
| File | Change Description |
|------|-------------------|
| `src/launch/workers/w1_repo_scout/discover_examples.py` | Added _matches_exclude_pattern(); updated identify_example_roots() for extra_example_dirs; updated discover_example_files() with scan_directories, exclude_patterns, file_size_bytes, and removed unknown-language skip |
| `src/launch/workers/w1_repo_scout/worker.py` | Updated execute_repo_scout() to pass run_config ingestion settings to discovery functions |
| `tests/unit/workers/test_tc_404_discover_examples.py` | Renamed test_skip_non_code_files to test_records_non_code_files_tc1023; added TestTC1023ConfigurableScanDirs (8 tests), TestMatchesExcludePattern (4 tests); added file_size_bytes assertions |

## Test Results

### TC-403 Discover Docs Tests
```
tests/unit/workers/test_tc_403_discover_docs.py: 64 passed
```

### TC-404 Discover Examples Tests
```
tests/unit/workers/test_tc_404_discover_examples.py: 68 passed
```

### Full Test Suite
```
2207 passed, 12 skipped, 1 warning in 75.27s
```

## Key Design Decisions

### TC-1022
1. **Extension-based filtering removed for recording, kept for scoring**: All files are now recorded, but DOC_EXTENSIONS files get full relevance scoring while non-doc files get reduced scores (max(score - 20, 10)).
2. **Binary detection dual approach**: Uses extension check (BINARY_EXTENSIONS set) combined with null byte heuristic (reads first 8KB) for robust detection.
3. **Full file content scan**: Removed the 50-line limit on check_content_based_detection() so keywords deep in files are properly detected.
4. **Binary files**: Recorded with is_binary=True, doc_type="binary", relevance_score=10.

### TC-1023
1. **Backward-compatible defaults**: scan_directories defaults to ["."], exclude_patterns defaults to [], extra_example_dirs defaults to []. These produce identical results to the old code for known-language files.
2. **fnmatch for exclude patterns**: Uses stdlib fnmatch for familiar glob-style pattern matching.
3. **Unknown language recording**: Files with unrecognized extensions in example roots are now recorded with language="unknown" instead of being skipped.
4. **file_size_bytes**: Added to every output entry via os.stat().

## Backward Compatibility

Both taskcards maintain full backward compatibility:
- TC-1022: Existing doc files retain original scoring. New fields are additive. Discovery summary gains binary_count but retains all existing fields.
- TC-1023: All new parameters have safe defaults matching original behavior. The only behavior change is that unknown-language files in example roots are now recorded instead of skipped.

## Dependencies Verified
- TC-1020 (specs): Complete. Updated specs/02_repo_ingestion.md, specs/05_example_curation.md.
- TC-1021 (schema+model): Complete. RunConfig model has get_scan_directories(), get_exclude_patterns(), get_example_directories() helpers.
