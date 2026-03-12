# SRI-09: Improve Config Dedup Performance

**Status:** Done
**Gap linkage:** Intake port self-review, Dimension 8 (Performance)
**Role:** Optimization
**Scope:** Replace O(n*m) YAML-parsing dedup with index-based lookup

---

## Problem

`check_dedup()` in `config_generator.py` globs all existing YAML files in the output directory and parses each one to extract `repo_url` for comparison. For large output directories (hundreds of pilot configs), this is O(n) YAML parses per call, and the onboard command calls it O(m) times = O(n*m) total.

## Acceptance Checks

- [ ] Dedup check uses an index file or filename-based lookup instead of parsing all YAMLs
- [ ] Performance is O(1) per check after initial index build
- [ ] Existing dedup behavior preserved (same true/false results)
- [ ] Unit test verifies dedup correctness with index approach
- [ ] Fallback to full scan if index is missing/corrupt

## Deliverables

1. Updated `src/launcher/intake/config_generator.py` with optimized dedup
2. Test proving correctness

## Hard Rules

- Must be backward compatible (existing output dirs work)
- Index corruption must not cause false negatives (allow duplicates rather than block valid configs)

## Review Dimensions

- Algorithmic improvement
- Correctness preservation
- Edge case handling

## Runbook

1. Profile current dedup with 100+ YAML files (measure baseline)
2. Implement slug-based index (e.g., `.dedup_index.json` mapping slug → repo_url)
3. Update `write_config()` to append to index on write
4. Update `check_dedup()` to read index first, fallback to glob
5. Test with empty dir, populated dir, corrupt index
