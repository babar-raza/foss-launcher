# Development Environment Setup

---

## ⚠️ CRITICAL: FOR ALL AI AGENTS / LLMs / AUTOMATION

**BINDING REQUIREMENT: You MUST use `.venv` for ALL Python operations in this repository.**

### Mandatory Commands for Agents

```bash
# ALWAYS activate .venv first (Windows)
.venv\Scripts\activate

# ALWAYS activate .venv first (Unix-like: Linux, macOS, WSL)
source .venv/bin/activate

# Then run any Python commands, tests, or validations
python tools/validate_swarm_ready.py
pytest
python -m launch.workers.w1_repo_scout
```

### Why This Matters

- **Gate 0 will FAIL** if you don't use `.venv`
- **Tests may fail** with wrong dependencies
- **Validation will be inconsistent** across environments
- **CI expects .venv** - your work must match CI

### Quick Check: Am I in .venv?

```bash
# Your Python path should show .venv
python -c "import sys; print(sys.prefix)"
# Should output: /path/to/repo/.venv
```

**If you see system Python path instead of .venv, STOP and activate .venv first.**

---

## Python Virtual Environment Policy (Binding)

**ALWAYS use `.venv` for all development work in this repository.**

### Quick Start

```bash
# Create and activate .venv
python -m venv .venv

# Windows
.venv\Scripts\activate

# Unix-like (Linux, macOS, WSL)
source .venv/bin/activate

# Install dependencies (preferred: deterministic)
make install-uv

# OR fallback (non-deterministic, not recommended)
make install
```

### Why .venv Only?

This repository enforces a strict `.venv` policy per [specs/00_environment_policy.md](specs/00_environment_policy.md):

1. **Consistency**: All developers and CI use the same virtual environment name
2. **Isolation**: Prevents conflicts with system Python packages
3. **Validation**: Gate 0 (`tools/validate_dotvenv_policy.py`) fails if `.venv` is not used
4. **No global installs**: Never install packages globally or in user site-packages

### Forbidden Alternatives

Do NOT use:
- `venv/`, `env/`, `.env/` (reserved for other purposes)
- Global Python packages
- User site-packages (`pip install --user`)
- `virtualenv` with custom names
- `conda` environments (not supported)

### Verification

Before starting work, always run:

```bash
python tools/validate_swarm_ready.py
```

Gate 0 will verify you're running from the correct `.venv`.

### CI/Automation

CI workflows and automation scripts MUST also use `.venv`:

```yaml
# Example GitHub Actions
- name: Setup Python environment
  run: |
    python -m venv .venv
    .venv/Scripts/python.exe -m pip install --upgrade pip uv
    .venv/Scripts/uv.exe sync --frozen
```

## Deterministic Testing

To ensure test reproducibility and consistency:

```bash
# CI sets this automatically, recommended for local development
export PYTHONHASHSEED=0  # Unix-like
set PYTHONHASHSEED=0     # Windows CMD
$env:PYTHONHASHSEED="0"  # Windows PowerShell

# Run tests
pytest
```

**Note**: The CI workflow sets `PYTHONHASHSEED=0` globally to ensure deterministic hash ordering across all test runs.

## See Also

- [specs/00_environment_policy.md](specs/00_environment_policy.md) - Full environment policy spec
- [specs/19_toolchain_and_ci.md](specs/19_toolchain_and_ci.md) - Toolchain and CI contracts
- [Makefile](Makefile) - Automated install targets
