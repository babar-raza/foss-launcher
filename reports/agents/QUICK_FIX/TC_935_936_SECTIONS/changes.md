# Changes Summary: TC-935 and TC-936 Missing Sections

## Overview
Added two missing required sections to both TC-935 and TC-936 to achieve full taskcard compliance:
1. **## Failure modes** - 3+ failure modes with detection, resolution, and spec/gate references
2. **## Task-specific review checklist** - 6-8 actionable verification items

## Files Modified

### 1. TC-935: Make validation_report.json Deterministic
**File:** `plans/taskcards/TC-935_make_validation_report_deterministic.md`

**Sections Added:**

#### ## Failure modes
Three critical failure modes identified:
1. **Path normalization breaks on non-run_dir paths**
   - Detection: Unit test failure in `test_normalize_report_preserves_non_run_paths()`
   - Resolution: Check if path starts with run_dir before attempting relative_to()
   - Spec/Gate: specs/34_strict_compliance_guarantees.md Guarantee F (Determinism)

2. **Validation report schema changes break normalization**
   - Detection: KeyError or AttributeError in normalize_report()
   - Resolution: Update normalize_report() to handle new schema fields with defensive dict.get() calls
   - Spec/Gate: specs/09_validation_gates.md (Validation report schema)

3. **Goldenized reports diverge after schema evolution**
   - Detection: VFV harness SHA256 mismatch for validation_report.json
   - Resolution: Re-goldenize expected_validation_report.json for both pilots after schema changes
   - Spec/Gate: specs/34_strict_compliance_guarantees.md Guarantee F (Determinism)

#### ## Task-specific review checklist
8-item verification checklist:
1. normalize_report() handles both absolute and relative paths correctly
2. Backslash-to-forward-slash conversion works on Windows paths
3. Deep copy prevents mutation of original report dict
4. All 5 unit tests in test_tc_935_validation_report_determinism.py PASS
5. VFV determinism check passes for both Pilot-1 (3D) and Pilot-2 (Note)
6. SHA256 hashes match across multiple runs with different run_dir timestamps
7. No validation information lost during normalization
8. Report structure preserved exactly (only path format changed)

---

### 2. TC-936: Stabilize Gate L (Secrets Hygiene) to Avoid Timeout
**File:** `plans/taskcards/TC-936_stabilize_gate_l_secrets_scan_time.md`

**Sections Added:**

#### ## Failure modes
Three critical failure modes identified:
1. **Scan scope too narrow, misses secrets in edge case files**
   - Detection: Security audit finds secrets in file extensions not in SCAN_EXTENSIONS
   - Resolution: Review and expand SCAN_EXTENSIONS based on audit findings; re-run validation
   - Spec/Gate: specs/34_strict_compliance_guarantees.md Guarantee L (Secret hygiene)

2. **Gate L still times out with large runs/ directory**
   - Detection: validate_swarm_ready shows Gate L execution time >60 seconds
   - Resolution: Further reduce file count or increase timeout threshold
   - Spec/Gate: specs/09_validation_gates.md Gate L timeout configuration

3. **Whitelist approach creates false negatives**
   - Detection: Secrets leaked in non-text files (serialized data, encoded strings)
   - Resolution: Add binary file scanning for high-entropy strings; expand SCAN_EXTENSIONS
   - Spec/Gate: specs/34_strict_compliance_guarantees.md Guarantee L (Secret detection completeness)

#### ## Task-specific review checklist
8-item verification checklist:
1. SCAN_EXTENSIONS whitelist includes all text-based file types that could contain secrets
2. File count reduced from 1427 to ~340 files (only .txt and .log in runs/)
3. Gate L execution time consistently <60 seconds (measured: ~47.7 seconds)
4. No reduction in coverage of source files (src/, specs/, tests/ remain fully scanned)
5. Extension-based filtering happens before expensive glob matching (performance optimization)
6. validate_swarm_ready output shows Gate L PASS
7. Exclusion of archives (.tar.gz, .zip) doesn't create security blind spots
8. should_scan_file() logic correctly handles extensionless files (scripts)

---

## Insertion Point
Both sections were added in the same location:
- **Before:** `## Evidence Location` section
- **After:** `## Self-review` section (which includes Verification results subsection)

This placement maintains logical flow and matches the contract structure defined in TC-937.

## Format Validation
All sections follow the established format from TC-937:
- Failure modes: Use **bold** headers with consistent structure (Detection/Resolution/Spec/Gate)
- Review checklist: Numbered items with clear, measurable criteria
- No structural changes to frontmatter or other existing sections
- Maintains consistent markdown formatting and style

## Validation Status
- **Before:** TC-935 and TC-936 marked as [FAIL]
  - Missing required section: '## Failure modes'
  - Missing required section: '## Task-specific review checklist'

- **After:** Both taskcards marked as [OK]
  - All required sections present
  - Section structure validates correctly
  - No other validation errors introduced
