# Spec 00: Virtual Environment Policy

**Status**: Binding
**Updated**: 2026-01-23

## Overview

This specification defines the **mandatory virtual environment policy** for all development, testing, CI, and agent execution in this repository.

## Core Policy

### Rule: Exactly One Virtual Environment

All Python work in this repository MUST use exactly one virtual environment:

```
.venv/
```

Located at the repository root.

### Forbidden Practices

The following are **explicitly prohibited**:

1. **Using global/system Python** for development, testing, or execution
2. **Creating alternate virtual environments** with any other name:
   - `venv/`
   - `env/`
   - `.tox/`
   - `.conda/`
   - `.mamba/`
   - `virtualenv/`
   - Any other custom name

3. **Guessing or defaulting** to system Python in any script, Makefile target, or CI job

### Rationale

**Problem**: Without a strict policy, agents and developers can:
- Accidentally use the wrong Python interpreter
- Create conflicting virtual environments
- Break reproducibility by mixing system and venv packages
- Cause hard-to-debug "works on my machine" issues

**Solution**: Enforce a single, unambiguous virtual environment location with automated gates.

## Implementation Requirements

### For Developers

1. **After cloning the repository**, create `.venv`:
   ```bash
   # Using uv (preferred)
   uv venv .venv
   uv sync

   # Using standard library venv (fallback)
   python -m venv .venv
   .venv/Scripts/activate  # Windows
   source .venv/bin/activate  # Linux/macOS
   pip install -e ".[dev]"
   ```

2. **Always activate `.venv`** before running commands:
   ```bash
   # Windows
   .venv\Scripts\activate

   # Linux/macOS
   source .venv/bin/activate
   ```

3. **Use explicit paths** when scripting:
   ```bash
   # Windows
   .venv/Scripts/python -m pytest

   # Linux/macOS
   .venv/bin/python -m pytest
   ```

### For Makefile Targets

All Makefile targets MUST:
1. Create `.venv` if it doesn't exist
2. Use `.venv/Scripts/python` (Windows) or `.venv/bin/python` (Linux/macOS) explicitly
3. Never rely on system `python` or activated virtualenv

Example:
```makefile
install-uv:
	python -m uv venv .venv
	.venv/Scripts/python -m uv pip sync uv.lock
```

### For CI/CD

All CI workflows (GitHub Actions, GitLab CI, etc.) MUST:
1. Create `.venv` explicitly before installing dependencies
2. Use `.venv` Python for all commands
3. Fail if `.venv` is not found when expected

Example (GitHub Actions):
```yaml
- name: Create virtual environment
  run: python -m venv .venv

- name: Install dependencies
  run: |
    .venv/Scripts/python -m pip install --upgrade pip
    .venv/Scripts/python -m pip install -e ".[dev]"

- name: Run tests
  run: .venv/Scripts/python -m pytest
```

### For Agents

All LLM agents executing in this repository MUST:
1. Verify they are running from `.venv` before starting work
2. Fail fast if not in `.venv`
3. Never create alternate virtual environments
4. Document `.venv` usage in all reports

## Enforcement

### Automated Gate

The policy is enforced by `tools/validate_dotvenv_policy.py`:

**Checks**:
1. Current Python interpreter is from `<repo>/.venv`
2. No forbidden venv directories exist at repo root (e.g., `venv/`, `env/`, `.tox/`)
3. No alternate virtual environments exist **anywhere** in the repo tree
   - Detects `pyvenv.cfg` files (Python venv marker)
   - Detects `conda-meta/` directories (Conda environment marker)
   - Ensures NO venvs can be hidden in subdirectories

**Exit Codes**:
- `0` - Policy compliant
- `1` - Policy violation detected

**Integration**:
- Wired into `tools/validate_swarm_ready.py` as **Gate 0** (runs first)
- Runs on every CI build
- Blocks agents from proceeding if policy violated

### Manual Verification

Check your current interpreter:

```bash
# Should output <repo>/.venv/...
python -c "import sys; print(sys.prefix)"

# Or check VIRTUAL_ENV
echo $VIRTUAL_ENV  # Linux/macOS
echo %VIRTUAL_ENV%  # Windows
```

## Cross-Platform Considerations

### Windows vs Linux/macOS

- **Windows**: `.venv/Scripts/python.exe`, `.venv/Scripts/activate`
- **Linux/macOS**: `.venv/bin/python`, `source .venv/bin/activate`

### Solution

Use platform detection in scripts:

```python
import sys
import platform
from pathlib import Path

repo_root = Path(__file__).parent.parent
if platform.system() == "Windows":
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
else:
    venv_python = repo_root / ".venv" / "bin" / "python"
```

Or use `sys.executable` when already running from the correct venv.

## Exceptions

**None**. This policy has zero exceptions for:
- Local development
- CI/CD
- Agent execution
- Testing
- Scripts
- Makefile targets

## Migration from Existing Setups

If you have an existing virtual environment (e.g., `venv/`):

1. Deactivate current environment
2. Delete old environment: `rm -rf venv/`
3. Create `.venv`: `python -m venv .venv`
4. Activate `.venv` and reinstall dependencies
5. Verify with `python -c "import sys; print(sys.prefix)"`

## Troubleshooting

### "I'm in .venv but gate fails"

**Cause**: You activated `.venv` but used system Python to create it.

**Fix**:
```bash
deactivate
rm -rf .venv
python3.12 -m venv .venv  # Use explicit Python 3.12+
source .venv/bin/activate
pip install -e ".[dev]"
```

### "Makefile target uses wrong Python"

**Cause**: Makefile target relies on PATH instead of explicit `.venv` path.

**Fix**: Update Makefile to use `.venv/Scripts/python` (Windows) or `.venv/bin/python` (Linux/macOS).

### "CI job can't find .venv"

**Cause**: CI job didn't create `.venv` or used wrong path.

**Fix**: Add explicit `.venv` creation step before installing dependencies.

## References

- [README.md](../README.md) - Installation instructions
- [Makefile](../Makefile) - Enforced targets
- [tools/validate_dotvenv_policy.py](../tools/validate_dotvenv_policy.py) - Enforcement gate
- [.github/workflows/ci.yml](../.github/workflows/ci.yml) - CI implementation

## Changelog

- **2026-01-23**: Initial policy specification (repo-hardening-agent)
- **2026-01-23**: Strengthened enforcement with Check 3 (no alternate venvs anywhere in repo tree)
