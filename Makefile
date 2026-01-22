.PHONY: install lint format test validate

install:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

lint:
	ruff check .

format:
	ruff format .

validate:
	python scripts/validate_spec_pack.py


test:
	pytest
