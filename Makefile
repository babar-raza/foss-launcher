.PHONY: install install-uv install-hooks lint format test validate

# Detect OS and set Python path accordingly
# Windows uses .venv/Scripts/python.exe, Unix-like uses .venv/bin/python
ifeq ($(OS),Windows_NT)
    VENV_PY := .venv/Scripts/python.exe
    VENV_UV := .venv/Scripts/uv.exe
else
    VENV_PY := .venv/bin/python
    VENV_UV := .venv/bin/uv
endif

# Install AI governance hooks (AG-001 gate strengthening)
# Automatically copies hooks from hooks/ to .git/hooks/ with proper permissions
install-hooks:
	python scripts/install_hooks.py

# Preferred: deterministic install with uv into .venv
# Enforces .venv policy per specs/00_environment_policy.md
# Note: Requires uv to be pre-installed (e.g., via astral-sh/setup-uv action in CI)
install-uv: install-hooks
	python -m venv .venv
	uv sync --frozen --extra dev

# Fallback: non-deterministic install with pip into .venv
# WARNING: Not deterministic, not recommended for agents or CI
install: install-hooks
	python -m venv .venv
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -e ".[dev]"

lint:
	$(VENV_PY) -m ruff check .

format:
	$(VENV_PY) -m ruff format .

validate:
	$(VENV_PY) scripts/validate_spec_pack.py

test:
	$(VENV_PY) -m pytest
