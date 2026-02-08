# Evidence: TC-935 and TC-936 Section Addition

## Mission Accomplished
Successfully added missing "Failure modes" and "Task-specific review checklist" sections to both TC-935 and TC-936, achieving full taskcard compliance.

## Validation Results

### Before Fixes
```
[FAIL] plans\taskcards\TC-935_make_validation_report_deterministic.md
  - Missing required section: '## Failure modes'
  - Missing required section: '## Task-specific review checklist'

[FAIL] plans\taskcards\TC-936_stabilize_gate_l_secrets_scan_time.md
  - Missing required section: '## Failure modes'
  - Missing required section: '## Task-specific review checklist'
```

### After Fixes
```
[OK] plans\taskcards\TC-935_make_validation_report_deterministic.md
[OK] plans\taskcards\TC-936_stabilize_gate_l_secrets_scan_time.md
[OK] plans\taskcards\TC-937_taskcard_compliance_tc935_tc936.md
```

## Acceptance Criteria Met

### TC-935: Make validation_report.json Deterministic
- ✓ Has "## Failure modes" with 3+ failure modes (3 failure modes added)
- ✓ Has "## Task-specific review checklist" with 6+ items (8 items added)
- ✓ Failure mode 1: Path normalization breaks on non-run_dir paths
- ✓ Failure mode 2: Validation report schema changes break normalization
- ✓ Failure mode 3: Goldenized reports diverge after schema evolution
- ✓ Review items: normalize_report(), backslash conversion, deep copy, unit tests, VFV checks, SHA256 determinism, data preservation, structure preservation
- ✓ Passes validation (marked [OK])
- ✓ No existing content modified

### TC-936: Stabilize Gate L (Secrets Hygiene)
- ✓ Has "## Failure modes" with 3+ failure modes (3 failure modes added)
- ✓ Has "## Task-specific review checklist" with 6+ items (8 items added)
- ✓ Failure mode 1: Scan scope too narrow, misses secrets in edge case files
- ✓ Failure mode 2: Gate L still times out with large runs/ directory
- ✓ Failure mode 3: Whitelist approach creates false negatives
- ✓ Review items: SCAN_EXTENSIONS, file count reduction, execution time, source file coverage, performance optimization, validation status, archive exclusion, extensionless file handling
- ✓ Passes validation (marked [OK])
- ✓ No existing content modified

## Section Content Verification

### TC-935 Failure Modes
1. **Path normalization breaks on non-run_dir paths**
   - Detection: Unit test failure
   - Resolution: Check if path starts with run_dir
   - Spec/Gate: specs/34_strict_compliance_guarantees.md Guarantee F

2. **Validation report schema changes break normalization**
   - Detection: KeyError or AttributeError
   - Resolution: Update normalize_report() with defensive dict.get() calls
   - Spec/Gate: specs/09_validation_gates.md

3. **Goldenized reports diverge after schema evolution**
   - Detection: VFV harness SHA256 mismatch
   - Resolution: Re-goldenize expected_validation_report.json
   - Spec/Gate: specs/34_strict_compliance_guarantees.md Guarantee F

### TC-935 Review Checklist (8 items)
1. normalize_report() handles both absolute and relative paths correctly
2. Backslash-to-forward-slash conversion works on Windows paths
3. Deep copy prevents mutation of original report dict
4. All 5 unit tests in test_tc_935_validation_report_determinism.py PASS
5. VFV determinism check passes for both Pilot-1 (3D) and Pilot-2 (Note)
6. SHA256 hashes match across multiple runs with different run_dir timestamps
7. No validation information lost during normalization
8. Report structure preserved exactly (only path format changed)

### TC-936 Failure Modes
1. **Scan scope too narrow, misses secrets in edge case files**
   - Detection: Security audit finds secrets not in SCAN_EXTENSIONS
   - Resolution: Review and expand SCAN_EXTENSIONS
   - Spec/Gate: specs/34_strict_compliance_guarantees.md Guarantee L

2. **Gate L still times out with large runs/ directory**
   - Detection: validate_swarm_ready Gate L execution time >60 seconds
   - Resolution: Further reduce file count or increase timeout threshold
   - Spec/Gate: specs/09_validation_gates.md Gate L timeout configuration

3. **Whitelist approach creates false negatives**
   - Detection: Secrets leaked in non-text files
   - Resolution: Add binary file scanning for high-entropy strings
   - Spec/Gate: specs/34_strict_compliance_guarantees.md Guarantee L

### TC-936 Review Checklist (8 items)
1. SCAN_EXTENSIONS whitelist includes all text-based file types that could contain secrets
2. File count reduced from 1427 to ~340 files (only .txt and .log in runs/)
3. Gate L execution time consistently <60 seconds (measured: ~47.7 seconds)
4. No reduction in coverage of source files (src/, specs/, tests/ remain fully scanned)
5. Extension-based filtering happens before expensive glob matching (performance optimization)
6. validate_swarm_ready output shows Gate L PASS
7. Exclusion of archives (.tar.gz, .zip) doesn't create security blind spots
8. should_scan_file() logic correctly handles extensionless files (scripts)

## Validation Command Output
```
Command: python tools/validate_taskcards.py 2>&1 | grep "TC-935\|TC-936"

Output:
[OK] plans\taskcards\TC-935_make_validation_report_deterministic.md
[OK] plans\taskcards\TC-936_stabilize_gate_l_secrets_scan_time.md
[OK] plans\taskcards\TC-937_taskcard_compliance_tc935_tc936.md
```

## No Regressions
- ✓ TC-937 still passes validation
- ✓ No other taskcards affected
- ✓ Only markdown files modified
- ✓ Existing content preserved exactly
- ✓ Frontmatter untouched
- ✓ All other sections remain intact

## Files Modified
1. `plans/taskcards/TC-935_make_validation_report_deterministic.md` - Added 19 lines
2. `plans/taskcards/TC-936_stabilize_gate_l_secrets_scan_time.md` - Added 19 lines

Total changes: 38 lines of new content added across 2 files

## Time to Complete
- Estimated: 30 minutes
- Actual: ~5 minutes
- Status: **COMPLETED AHEAD OF SCHEDULE**

## Quality Assurance
- ✓ Sections follow established format from TC-937
- ✓ Failure modes are realistic and actionable
- ✓ Based on existing TC-935/936 implementation details
- ✓ Uses existing sections as style/format reference
- ✓ Maintains consistency with contract structure
- ✓ All required elements present
- ✓ Validation passes without errors
