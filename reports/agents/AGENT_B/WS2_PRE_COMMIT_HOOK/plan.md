# WS2: Pre-Commit Hook Implementation Plan
## Agent B (Implementation)

**Created:** 2026-02-03
**Mission:** Create pre-commit git hook to validate staged taskcard files before commits

---

## Objectives

1. Create `hooks/pre-commit` bash script that validates staged taskcards
2. Update `scripts/install_hooks.py` to install the new hook
3. Test hook blocking behavior with incomplete taskcards
4. Verify hook performance (<5 seconds)
5. Document all changes and evidence

---

## Implementation Steps

### PREVENT-2.1: Create hooks/pre-commit bash script
**File:** `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\hooks\pre-commit`

Script will:
- Check for staged taskcard files using `git diff --cached`
- Skip validation if no taskcards staged (exit 0)
- Run `python tools/validate_taskcards.py --staged-only` if taskcards found
- Block commit (exit 1) if validation fails
- Show clear error message with missing sections
- Provide bypass instructions (`git commit --no-verify`)

### PREVENT-2.2: Update scripts/install_hooks.py
**File:** `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\scripts\install_hooks.py`

Action:
- Add 'pre-commit' to the hooks list
- Update hook description mapping to include pre-commit entry

### PREVENT-2.3: Test hook installation
Commands:
```bash
.venv\Scripts\python.exe scripts\install_hooks.py
ls -la .git\hooks\pre-commit
```

### PREVENT-2.4: Test hook blocking behavior
**Test Case 1:** Block incomplete taskcard
- Create TC-999 with minimal sections
- Stage and attempt commit
- Verify hook blocks with validation errors

**Test Case 2:** Allow complete taskcard (if needed)
- Use existing complete taskcard
- Verify hook allows commit

### PREVENT-2.5: Measure hook performance
- Time hook execution with single taskcard
- Verify <5 seconds performance target

---

## Acceptance Criteria

- [x] hooks/pre-commit created and executable
- [x] Hook validates only staged taskcard files
- [x] Hook blocks commits on validation failure
- [x] Hook shows clear error message
- [x] Hook execution time <5 seconds
- [x] Bypass available via `git commit --no-verify`
- [x] scripts/install_hooks.py updated

---

## Success Metrics

- Hook blocks incomplete taskcards reliably
- Clear error messages guide users to fix issues
- Zero false positives
- Performance within budget (<5s)
- Integration with existing hook infrastructure

---

## Platform Notes

- **Environment:** Windows with Git Bash
- **Paths:** Use forward slashes in bash scripts (Git Bash handles conversion)
- **Python:** Use `python` in hook (git will use activated venv or system Python)
- **Executable:** On Windows, Git Bash handles executable bit automatically
