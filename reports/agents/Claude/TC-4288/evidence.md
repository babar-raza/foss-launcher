# TC-4288 Evidence: API identifier allowlist expansion

## Root Cause

Post-TC-4287, 187 api_identifier_unknown_method MEDIUM findings and 147 api_identifier_unknown_class HIGH findings remained across pilots. Analysis revealed:

1. **Method allowlist gaps** (~120 false positives): Missing Python stdlib methods (json.loads, re.findall, os.makedirs), unittest assertions (assertEqual, assertTrue, etc.), Node.js fs methods (readFileSync, existsSync), TypeScript string builtins (toLowerCase, endsWith), and Jest matchers (toBeNull, toBe).

2. **User-defined test methods** (~56 false positives): Methods starting with `test_` (e.g., `test_cell_values()`) flagged as unknown API methods.

3. **Enum member names** (~34 false positives): Common English words used as enum member names (`Date`, `Time`, `Start`, `Web`, `Scatter`) flagged as unknown classes.

## Fix

Four additions to `api_verification.py`:

1. **Expanded `_ALWAYS_ALLOWED_METHODS`**: Added 50+ Python stdlib methods including os, json, re, sys, zipfile, collections, time, and all unittest assertions/lifecycle methods.

2. **Expanded `_TS_ALWAYS_ALLOWED_METHODS`**: Added 60+ TypeScript/Node.js methods including fs module, path module, String/Number/Date builtins, Jest matchers and lifecycle.

3. **`test_` prefix filter**: Skip method names starting with `test_` — user-defined test methods from extracted snippets.

4. **`_COMMON_ENUM_WORDS` filter**: 30+ common English words used as enum members/constants that are never standalone product class names.

## Tests

9 tests in `TestApiIdentifierAllowlistExpansionTC4288`:
1. Unittest assertions not flagged (Python)
2. Python stdlib methods not flagged (json, re, os)
3. `test_` prefix methods skipped
4. Node.js fs methods not flagged (TypeScript)
5. Jest matchers not flagged (TypeScript)
6. TypeScript string builtins not flagged
7. Enum member words not flagged as unknown classes
8. Genuine unknown methods still caught (regression)
9. Genuine unknown classes still caught (regression)

## Impact

Expected to eliminate ~210 false-positive findings:
- ~120 MEDIUM method findings (unittest, stdlib, Node.js)
- ~56 MEDIUM method findings (test_ prefix)
- ~34 HIGH class findings (enum member words)

This should push many C pages below the 3-MEDIUM or 2-HIGH thresholds, promoting them to B grade.

## Test Results

15/15 PASS (targeted), 4445/4445 PASS (full suite)
