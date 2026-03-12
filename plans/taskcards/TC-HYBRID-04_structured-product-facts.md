---
id: TC-HYBRID-04
title: "StructuredProductFacts — InstallRecipe extraction and generation context injection"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-10"
tags: [evidence-model, spk, install-recipe, generation]
depends_on: [TC-HYBRID-01, TC-HYBRID-02, TC-HYBRID-03]
allowed_paths:
  - plans/taskcards/TC-HYBRID-04_structured-product-facts.md
  - src/launcher/models/understanding.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/test_understand.py
  - tests/unit/workers/test_section_prompt.py
  - reports/TC-HYBRID-04/evidence.md
  - reports/agents/B/TC-HYBRID-04/self_review.md
  - reports/agents/B/TC-HYBRID-04/plan.md
evidence_required:
  - reports/TC-HYBRID-04/evidence.md
---

# Taskcard TC-HYBRID-04 — StructuredProductFacts (InstallRecipe)

## Objective

Extend `ProductEvidence` with an `InstallRecipe` model populated deterministically from
`pyproject.toml`/`setup.cfg`/`setup.py`/`requirements.txt`. Inject the install recipe into
generation prompts for installation and getting-started pages so the LLM uses the real
install command rather than guessing. This eliminates a class of hallucination where
the generated `pip install` command is wrong.

## Required spec references

- `specs/product_model.md` (ProductEvidence, ProductIdentity)
- `specs/worker_understand.md` (Phase B extraction)
- `specs/worker_generate.md` (section prompt context)

## Scope

### In scope
- Add `InstallRecipe` model to `src/launcher/models/understanding.py`
- Add `install_recipe: InstallRecipe | None = None` to `ProductEvidence`
- Add `extract_install_recipe(repo_dir, product)` to `_deterministic.py`
- Wire extraction into `understand/worker.py` `_extract_product_evidence()` function
- Add `install_recipe` optional param to `section_prompt.py` `build_section_prompt()`
- Update `generate/worker.py` to pass `product_evidence.install_recipe` to prompt

### Out of scope
- `LimitationEntry` and `WorkflowExample` — deferred to TC-HYBRID-10
- Java/TypeScript/Node install recipe (Python-first; other langs have simpler patterns)
- Injecting install recipe into evaluation/go criteria (TC-HYBRID-05/06 scope)

## Inputs

- `src/launcher/models/understanding.py` — `ProductEvidence` (extend)
- `src/launcher/workers/understand/worker.py` — `_extract_product_evidence()` at line ~231
- `src/launcher/workers/generate/section_prompt.py` — `build_section_prompt()` at line ~547
- `src/launcher/workers/generate/worker.py` — where `build_section_prompt()` is called
- Product repos: `pyproject.toml`, `setup.cfg`, `setup.py`, `requirements.txt`

## Outputs

- `InstallRecipe` model in `understanding.py`
- `ProductEvidence.install_recipe` field populated from deterministic extraction
- `build_section_prompt()` accepts and injects `install_recipe` context
- Tests: install recipe extracted from fixture; injected into prompt for install page roles

## Allowed paths

- plans/taskcards/TC-HYBRID-04_structured-product-facts.md
- src/launcher/models/understanding.py
- src/launcher/workers/understand/extract/_deterministic.py
- src/launcher/workers/understand/worker.py
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/worker.py
- tests/unit/workers/test_understand.py
- tests/unit/workers/test_section_prompt.py
- reports/TC-HYBRID-04/evidence.md
- reports/agents/B/TC-HYBRID-04/self_review.md
- reports/agents/B/TC-HYBRID-04/plan.md

### Allowed paths rationale
- `understanding.py`: InstallRecipe model and ProductEvidence extension
- `_deterministic.py`: extract_install_recipe() function
- `understand/worker.py`: _extract_product_evidence() wiring
- `section_prompt.py`: build_section_prompt() install recipe injection
- `generate/worker.py`: pass product_evidence.install_recipe to build_section_prompt
- Tests and reports

## Implementation steps

### Step 1: Read key files first

Read these before writing any code:
- `src/launcher/models/understanding.py` (full file)
- `src/launcher/workers/understand/worker.py` lines 231-305 (_extract_product_evidence function)
- `src/launcher/workers/generate/section_prompt.py` lines 547-650 (build_section_prompt signature and early body)
- `src/launcher/workers/generate/worker.py` — grep for "build_section_prompt" to find all call sites
- `src/launcher/workers/understand/extract/_deterministic.py` — last 50 lines (to find end of file for appending)

### Step 2: Add InstallRecipe to understanding.py

In `src/launcher/models/understanding.py`, add before `ProductEvidence`:

```python
class InstallRecipe(LauncherBaseModel):
    """Deterministically extracted install instructions for a product.

    Populated from pyproject.toml, setup.cfg, setup.py, or requirements.txt.
    Injected into generation context so install/getting-started pages use the
    real command rather than LLM guesses.
    """
    pip_command: str = ""         # e.g. "pip install aspose-3d-foss"
    package_name: str = ""        # e.g. "aspose-3d-foss"
    version_constraint: str = ""  # e.g. ">=1.0.0" or ""
    verification_code: str = ""   # e.g. "import aspose.threed"
    source_file: str = ""         # which config file provided this
```

Then extend `ProductEvidence`:
```python
class ProductEvidence(LauncherBaseModel):
    ...existing fields...
    install_recipe: "InstallRecipe | None" = None  # TC-HYBRID-04
```

Add `from __future__ import annotations` at the top if not already present (for the `InstallRecipe | None` forward ref).

### Step 3: Implement extract_install_recipe() in _deterministic.py

Append to `src/launcher/workers/understand/extract/_deterministic.py`:

```python
# ---------------------------------------------------------------------------
# Install recipe extraction (TC-HYBRID-04)
# ---------------------------------------------------------------------------


def extract_install_recipe(
    repo_dir: "Path",
    product: "ProductIdentity",
) -> "Any | None":
    """Extract pip install command from project config files.

    Strategy (in priority order):
    1. pyproject.toml [project].name + version
    2. setup.cfg [metadata].name + version
    3. setup.py name=... argument
    4. requirements.txt — line matching canonical_import pattern
    5. Fallback — derive from canonical_import (aspose_3d_foss → aspose-3d-foss)

    Returns an InstallRecipe or None on complete failure.
    Never raises.
    """
    try:
        from launcher.models.understanding import InstallRecipe
    except ImportError:
        return None

    package_name = ""
    version_constraint = ""
    source_file = ""

    # Strategy 1: pyproject.toml
    pyproject_path = repo_dir / "pyproject.toml"
    if pyproject_path.exists():
        try:
            content = pyproject_path.read_text(encoding="utf-8", errors="replace")
            # Match [project] section, then name = "..." on following lines
            name_m = re.search(
                r'\[project\][^\[]*?\bname\s*=\s*["\']([^"\']+)["\']',
                content, re.DOTALL,
            )
            if name_m:
                package_name = name_m.group(1).strip()
                source_file = "pyproject.toml"
                ver_m = re.search(
                    r'\[project\][^\[]*?\bversion\s*=\s*["\']([^"\']+)["\']',
                    content, re.DOTALL,
                )
                if ver_m:
                    version_constraint = f">={ver_m.group(1).strip()}"
        except Exception:
            logger.debug("extract_install_recipe: pyproject.toml failed", exc_info=True)

    # Strategy 2: setup.cfg
    if not package_name:
        setupcfg = repo_dir / "setup.cfg"
        if setupcfg.exists():
            try:
                content = setupcfg.read_text(encoding="utf-8", errors="replace")
                m = re.search(r'^name\s*=\s*(.+)$', content, re.MULTILINE)
                if m:
                    package_name = m.group(1).strip()
                    source_file = "setup.cfg"
                vm = re.search(r'^version\s*=\s*(.+)$', content, re.MULTILINE)
                if vm:
                    version_constraint = f">={vm.group(1).strip()}"
            except Exception:
                logger.debug("extract_install_recipe: setup.cfg failed", exc_info=True)

    # Strategy 3: setup.py
    if not package_name:
        setup_py = repo_dir / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text(encoding="utf-8", errors="replace")
                m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    package_name = m.group(1).strip()
                    source_file = "setup.py"
            except Exception:
                logger.debug("extract_install_recipe: setup.py failed", exc_info=True)

    # Strategy 4: requirements.txt
    if not package_name and product.canonical_import:
        req = repo_dir / "requirements.txt"
        if req.exists():
            try:
                content = req.read_text(encoding="utf-8", errors="replace")
                slug = product.canonical_import.replace("_", "-").lower()
                for line in content.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if slug in line.lower().replace("_", "-"):
                        package_name = re.split(r"[>=<!]", line)[0].strip()
                        source_file = "requirements.txt"
                        break
            except Exception:
                logger.debug("extract_install_recipe: requirements.txt failed", exc_info=True)

    # Strategy 5: derive from canonical_import
    if not package_name and product.canonical_import:
        package_name = product.canonical_import.replace("_", "-")
        source_file = "derived"

    if not package_name:
        return None

    pip_cmd = f"pip install {package_name}"
    if version_constraint:
        pip_cmd = f"pip install {package_name}{version_constraint}"

    # Verification code
    runtime = getattr(product, "runtime_import", "") or product.canonical_import
    verification = f"import {runtime}\nprint('Installation successful')" if runtime else ""

    logger.info("extract_install_recipe: package=%s source=%s", package_name, source_file)
    return InstallRecipe(
        pip_command=pip_cmd,
        package_name=package_name,
        version_constraint=version_constraint,
        verification_code=verification,
        source_file=source_file,
    )
```

Note: Uses `from __future__ import annotations` already present in `_deterministic.py`. Uses `re` and `Path` which are already imported. Uses `logger` already defined at module level.

### Step 4: Wire into understand/worker.py

In `src/launcher/workers/understand/worker.py`, find `_extract_product_evidence()` (around line 231).

After `evidence = ProductEvidence(...)` (around line 278), add:

```python
        # TC-HYBRID-04: extract install recipe deterministically
        try:
            from launcher.workers.understand.extract._deterministic import extract_install_recipe as _extract_recipe
            _recipe = _extract_recipe(repo_dir, product)
            if _recipe:
                evidence = evidence.model_copy(update={"install_recipe": _recipe})
                context.log.info("[Understand] InstallRecipe: pip_command=%s", _recipe.pip_command)
        except Exception:
            context.log.debug("[Understand] extract_install_recipe skipped", exc_info=True)
```

Place this BEFORE the `return evidence` line.

### Step 5: Update section_prompt.py

In `src/launcher/workers/generate/section_prompt.py`, find `build_section_prompt()` signature (line ~547).

Add optional parameter:
```python
def build_section_prompt(
    ...existing params...,
    install_recipe: "Any | None" = None,  # InstallRecipe | None (TC-HYBRID-04)
) -> str:
```

Inside `build_section_prompt()`, find where the prompt string is assembled (look for "PRODUCT IDENTITY" or the main prompt template block). Add install recipe block near the install/getting-started context:

```python
    # Inject install recipe for installation/getting-started pages (TC-HYBRID-04)
    _install_block = ""
    if install_recipe and getattr(install_recipe, "pip_command", ""):
        _install_block = (
            f"\n\n## INSTALL REFERENCE (authoritative — do not deviate)\n"
            f"```bash\n{install_recipe.pip_command}\n```\n"
        )
        if getattr(install_recipe, "verification_code", ""):
            _install_block += (
                f"```python\n{install_recipe.verification_code}\n```\n"
            )
```

Then include `_install_block` in the final prompt string at an appropriate place.

Note: Only inject when page role contains "install" or "getting_started". Check `page.role` or `section.title` to decide. If you can't easily check, inject unconditionally — a short install block in a non-install page is low-risk.

### Step 6: Update generate/worker.py

Find all call sites for `build_section_prompt(...)` in `generate/worker.py`. Add `install_recipe=...` arg. The generate worker has access to the `UnderstandingBundle` — check how it's accessed.

Look for the pattern:
```python
prompt = build_section_prompt(
    section, section_index, ..., product=product, ...
)
```

Pass:
```python
install_recipe=getattr(getattr(context, "understanding", None), "product_evidence", None) and
    getattr(getattr(context, "understanding", None).product_evidence, "install_recipe", None),
```

OR the more readable:
```python
_evidence = getattr(getattr(context, "understanding", None), "product_evidence", None)
_recipe = getattr(_evidence, "install_recipe", None) if _evidence else None
...
prompt = build_section_prompt(..., install_recipe=_recipe)
```

If the understanding bundle is passed differently (e.g., as a constructor arg to the worker), adapt accordingly.

### Step 7: Write unit tests

In `tests/unit/workers/test_understand.py`, add to `TestFormatMatrix` or a new class:

```python
class TestInstallRecipe:
    def test_extract_from_pyproject_toml(self, tmp_path):
        """extract_install_recipe returns correct pip_command from pyproject.toml."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.product import ProductIdentity

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "aspose-3d-foss"\nversion = "1.2.0"\n'
        )
        product = ProductIdentity(
            family="3d", platform="python",
            display_name="Aspose.3D", canonical_import="aspose_3d_foss",
            runtime_import="aspose.threed",
            repo_url="file://" + str(tmp_path),
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert recipe.package_name == "aspose-3d-foss"
        assert "aspose-3d-foss" in recipe.pip_command
        assert recipe.source_file == "pyproject.toml"

    def test_fallback_to_canonical_import(self, tmp_path):
        """extract_install_recipe falls back to canonical_import when no config files."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.product import ProductIdentity

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="file://" + str(tmp_path),
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert "aspose-cells-foss" in recipe.pip_command
        assert recipe.source_file == "derived"

    def test_none_on_no_canonical_import(self, tmp_path):
        """Returns None when no config files and no canonical_import."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.product import ProductIdentity

        product = ProductIdentity(
            family="unknown", platform="python",
            display_name="Unknown", canonical_import="",
            repo_url="file://" + str(tmp_path),
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is None
```

In `tests/unit/workers/test_section_prompt.py` — check if this file exists first. If yes, add:

```python
def test_build_section_prompt_with_install_recipe():
    """build_section_prompt includes install recipe when provided."""
    from launcher.workers.generate.section_prompt import build_section_prompt
    from launcher.models.understanding import InstallRecipe
    # ... create minimal mocks and verify install block appears in prompt output
```

### Step 8: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v -k "install" --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

### Step 9: Write evidence and self-review

Create `reports/TC-HYBRID-04/evidence.md` and `reports/agents/B/TC-HYBRID-04/self_review.md`.

## Failure modes

### Failure mode 1: Circular import (understanding.py ↔ _deterministic.py)

**Detection**: `ImportError: cannot import name 'InstallRecipe'`
**Resolution**: Use late import `from launcher.models.understanding import InstallRecipe` inside `extract_install_recipe()` body (not at module level). Same pattern as `FormatRecord` in `extract_format_matrix()`.
**Gate**: Unit test `test_extract_from_pyproject_toml` imports and calls function; if circular, test fails immediately

### Failure mode 2: generate/worker.py uses understanding bundle differently than expected

**Detection**: `AttributeError: 'WorkerContext' has no attribute 'understanding'`
**Resolution**: Read how the generate worker receives the understanding bundle before writing. Check constructor args or `context.config` or `input_data` — the understanding bundle may be passed differently.
**Gate**: Read generate/worker.py fully before writing any changes to it

### Failure mode 3: model_copy update of frozen model

**Detection**: `TypeError: 'ProductEvidence' object doesn't support item assignment` or `ValidationError` on model_copy
**Resolution**: Check if `ProductEvidence` inherits from `LauncherBaseModel` which should support `model_copy`. Pydantic v2: `evidence.model_copy(update={"install_recipe": recipe})`. Pydantic v1: `evidence.copy(update={"install_recipe": recipe})`.
**Gate**: Unit test that creates ProductEvidence and calls model_copy with install_recipe

### Failure mode 4: pyproject.toml regex too greedy (DOTALL + [^\[]) captures wrong section

**Detection**: `package_name` extracted from a different `[tool.poetry]` or `[tool.setuptools]` section, not `[project]`
**Resolution**: Use a tighter regex — stop at the next `[` section marker: `r'\[project\][^\[]*?\bname\s*=\s*["\']([^"\']+)["\']'` with `re.DOTALL`. Test with a pyproject.toml fixture that has multiple sections.
**Gate**: Fixture test with real pyproject.toml content

## Task-specific review checklist

1. [ ] `InstallRecipe` model defined with all required fields, all with defaults
2. [ ] `ProductEvidence.install_recipe` field added, defaults to `None`
3. [ ] `extract_install_recipe()` correctly parses pyproject.toml with realistic fixture
4. [ ] Fallback to canonical_import works when no config files exist
5. [ ] `_extract_product_evidence()` in understand/worker.py calls extractor and populates `install_recipe`
6. [ ] `build_section_prompt()` accepts `install_recipe` and includes it in prompt when present
7. [ ] All new fields have defaults — no breaking changes
8. [ ] Spec `specs/product_model.md` updated with InstallRecipe and ProductEvidence.install_recipe
9. [ ] Schema `"description"` fields present on new model properties
10. [ ] Late import pattern used for `InstallRecipe` in `_deterministic.py` (circular import safety)
11. [ ] Checked `docs/README.md` ownership map for trigger events

## Deliverables

1. `src/launcher/models/understanding.py` — InstallRecipe + ProductEvidence.install_recipe
2. `src/launcher/workers/understand/extract/_deterministic.py` — extract_install_recipe()
3. `src/launcher/workers/understand/worker.py` — wiring in _extract_product_evidence()
4. `src/launcher/workers/generate/section_prompt.py` — install_recipe param + injection
5. `src/launcher/workers/generate/worker.py` — pass install_recipe to build_section_prompt
6. `tests/unit/workers/test_understand.py` — 3 TestInstallRecipe tests
7. `reports/TC-HYBRID-04/evidence.md`
8. `reports/agents/B/TC-HYBRID-04/self_review.md`

## Acceptance checks

1. [ ] `InstallRecipe` importable from `launcher.models.understanding`
2. [ ] `ProductEvidence().install_recipe` is `None` (backwards compat)
3. [ ] `extract_install_recipe(tmp_path_with_pyproject, product)` returns `InstallRecipe` with correct pip_command
4. [ ] `extract_install_recipe(empty_tmp_path, product_with_canonical)` returns fallback recipe
5. [ ] All 3 TestInstallRecipe tests pass
6. [ ] Full suite passes: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no`

## Self-review

### Verification results
- [x] Tests: 10/10 TC-specific PASS; 3364 suite PASS
- [x] Evidence captured: reports/TC-HYBRID-04/evidence.md
- [x] Doc freshness acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -v -k "install" --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

## Integration boundary proven

**Upstream**: `pyproject.toml`/`setup.cfg`/`setup.py` → `extract_install_recipe()` → `ProductEvidence.install_recipe`
**Downstream**: `build_section_prompt()` injects install recipe into LLM generation prompt
**Contract**: `ProductEvidence.install_recipe: InstallRecipe | None` — None means not extracted; never raises; all recipe fields default to `""`
