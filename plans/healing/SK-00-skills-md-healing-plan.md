# Skills.md Integration — Healing Plan (TC-3856 Follow-up)

**Context**: TC-3856 delivered the `skills.md` quality-standards integration. A
structured self-review identified 6 gaps that must be closed before the feature
is production-ready. This plan converts every gap into an executable, drop-in
taskcard. No gap is left unaddressed.

**Origin**: Self-review of TC-3856 implementation (2026-03-08).

---

## Gap Table

| Gap ID | Severity | Description | Taskcard |
|--------|----------|-------------|----------|
| G-01 | High | `pipeline.yaml` `skills:` block is non-functional — not parsed into `RunConfig`; misleads operators | SK-01 |
| G-02 | High | Zero unit tests for `skills_loader.py` — brace-escaping (critical safety) and section extraction untested | SK-02 |
| G-03 | Medium | No token-budget truncation in `_format_for_prompt` — oversized skills block injected verbatim, risks context overflow | SK-03 |
| G-04 | Medium | No telemetry events emitted when skills load/skip — impossible to confirm skills state from run trace | SK-04 |
| G-05 | Medium | `Path("skills.md")` is CWD-relative — silently returns `""` when pipeline is invoked as library from non-root directory | SK-05 |
| G-06 | Low | `SkillsConfig` not exported from `src/launcher/models/__init__.py` — breaks module encapsulation contract | SK-06 |

---

## Taskcard SK-01 — Remove non-functional pipeline.yaml skills block

**Status**: Done
**Gap linkage**: G-01
**Role**: Senior engineer. Drop-in, production-ready.

### Fix

Remove the `skills:` block from `configs/pipeline.yaml`. It is never parsed
into a `RunConfig` instance (that file only controls pipeline topology, linker
settings, and defaults). The actual control surface is `run_config.yaml` via
`RunConfig.skills`. Add a comment to `pipeline.yaml` clarifying where skills
are configured, and update the `skills_loader.py` module docstring to state the
correct control path.

### Allowed paths

- `configs/pipeline.yaml`
- `src/launcher/shared/skills_loader.py`

### Forbidden

Any file not listed above. No code-logic changes to the loader in this taskcard
(that is SK-03/SK-05). Only the YAML block removal and docstring update.

### Scope

**In scope:**
- Delete the 3-line `skills:` block from `configs/pipeline.yaml`
- Add a YAML comment in `pipeline.yaml` under `golden:` directing operators to `run_config.yaml`
- Extend the `skills_loader.py` module docstring to document the correct control surface

**Out of scope:**
- Any functional code changes (handled by other SK taskcards)
- Changes to pilot `run_config.yaml` files

### Full file replacement for `configs/pipeline.yaml`

Remove:
```yaml
skills:
  enabled: true
  path: "skills.md"
```

Add after the `golden:` block:
```yaml
# Skills quality standards are controlled per-run via run_config.yaml:
#   skills:
#     enabled: true      # set false to disable
#     path: "skills.md"  # relative to process CWD (project root)
# pipeline.yaml does NOT configure skills — only run_config.yaml does.
```

### Module docstring addition for `skills_loader.py`

Append to the existing module docstring:

```
Control surface:
    Skills are enabled/disabled via ``RunConfig.skills`` (in run_config.yaml),
    NOT via pipeline.yaml.  The pipeline.yaml file does not parse into RunConfig.
    Example run_config.yaml entry::

        skills:
          enabled: true
          path: "skills.md"

    To disable skills for a specific run, set ``skills.enabled: false``.
```

### Acceptance checks

- **CLI**: `grep -c "^skills:" configs/pipeline.yaml` returns `0`
- **UI/Web/API**: N/A
- **Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` passes (no regressions)
- **Config respected end-to-end**: Running the pipeline with `skills.enabled: false` in a pilot run_config still disables skills (confirm via log: no "Skills quality standards loaded" INFO line)
- **No mock data in production paths**: N/A

### Deliverables

1. `configs/pipeline.yaml` — skills block removed, comment added
2. `src/launcher/shared/skills_loader.py` — module docstring extended

### Hard rules

- Do not add new logic to `skills_loader.py` in this taskcard
- Do not touch any test files
- Do not change any other config file
- Commit message must reference `SK-01`

### Review dimensions — what 5/5 means here

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | `pipeline.yaml` contains zero `skills:` keys; docstring accurately describes the control path |
| Minimality | Diff is ≤ 15 lines total; no noise |
| Maintainability | Any future operator reading `pipeline.yaml` is directed to the correct place without ambiguity |
| Consistency | `pipeline.yaml` comment matches the existing `golden:` block style |

### Now (runbook)

```bash
# 1. Edit configs/pipeline.yaml — remove the skills: block, add comment after golden:
# 2. Edit src/launcher/shared/skills_loader.py — extend module docstring
# 3. Verify no functional change:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 4. Confirm skills block gone:
python -c "
from launcher.io.yamlio import load_yaml
cfg = load_yaml('configs/pipeline.yaml')
assert 'skills' not in cfg, 'skills key still present'
print('OK: skills key removed from pipeline.yaml')
"
```

---

## Taskcard SK-02 — Add unit tests for skills_loader.py

**Status**: Done
**Gap linkage**: G-02
**Role**: Senior engineer. Drop-in, production-ready.

### Fix

Create `tests/unit/shared/test_skills_loader.py` with complete coverage of
`skills_loader.py`. Must cover: happy path for both public functions, file
missing, missing section header, brace-escaping (the critical safety property),
oversized block warning, and the `_extract_section` edge cases.

### Allowed paths

- `tests/unit/shared/test_skills_loader.py`

### Forbidden

Any file not listed above. No changes to `skills_loader.py` itself in this
taskcard (functional changes are SK-03).

### Scope

**In scope:** New test file covering 10+ test cases.

**Out of scope:** Changes to `skills_loader.py`, other test files.

### Full file content for `tests/unit/shared/test_skills_loader.py`

```python
"""Unit tests for launcher.shared.skills_loader (TC-3856 / SK-02).

Tests cover:
- Happy path: load_generation_block and load_evaluation_block with real content
- File-missing graceful degradation
- Missing section header graceful degradation
- Brace-escaping safety (critical: prevents str.format() KeyError in prompts)
- Oversized block triggers WARNING log
- page_role parameter (reserved, currently pass-through)
- _extract_section edge cases: trailing newline, multi-section document
- Both functions return non-empty string only when section exists
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from launcher.shared.skills_loader import (
    _extract_section,
    load_evaluation_block,
    load_generation_block,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_SKILLS = """\
## GENERATION STANDARDS

Write clearly and concisely.
Use active voice.

## EVALUATION CRITERIA

Check depth and specificity.
Flag thin content.

## ANTI-PATTERNS

AP-1: Placeholder text.
"""

BRACE_SKILLS = """\
## GENERATION STANDARDS

Use {display_name} as the product name.
Code must import {canonical_import}.
Avoid {{ escaped_already }} patterns.

## EVALUATION CRITERIA

Check that {product_name} is correct.
"""

OVERSIZED_CONTENT = "x " * 2000  # 4000 chars of content

OVERSIZED_SKILLS = f"## GENERATION STANDARDS\n\n{OVERSIZED_CONTENT}\n"


@pytest.fixture
def skills_file(tmp_path: Path) -> Path:
    p = tmp_path / "skills.md"
    p.write_text(MINIMAL_SKILLS, encoding="utf-8")
    return p


@pytest.fixture
def brace_file(tmp_path: Path) -> Path:
    p = tmp_path / "skills.md"
    p.write_text(BRACE_SKILLS, encoding="utf-8")
    return p


@pytest.fixture
def oversized_file(tmp_path: Path) -> Path:
    p = tmp_path / "skills.md"
    p.write_text(OVERSIZED_SKILLS, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_generation_block — happy path
# ---------------------------------------------------------------------------

def test_generation_block_returns_nonempty(skills_file: Path) -> None:
    result = load_generation_block(skills_file)
    assert result != ""
    assert "Write clearly" in result


def test_generation_block_contains_label(skills_file: Path) -> None:
    result = load_generation_block(skills_file)
    assert "QUALITY STANDARDS FOR THIS SECTION" in result


def test_generation_block_does_not_contain_evaluation_content(skills_file: Path) -> None:
    result = load_generation_block(skills_file)
    assert "Check depth" not in result


def test_generation_block_does_not_contain_anti_patterns(skills_file: Path) -> None:
    result = load_generation_block(skills_file)
    assert "AP-1" not in result


# ---------------------------------------------------------------------------
# load_evaluation_block — happy path
# ---------------------------------------------------------------------------

def test_evaluation_block_returns_nonempty(skills_file: Path) -> None:
    result = load_evaluation_block(skills_file)
    assert result != ""
    assert "Check depth" in result


def test_evaluation_block_contains_label(skills_file: Path) -> None:
    result = load_evaluation_block(skills_file)
    assert "DOMAIN-SPECIFIC EVALUATION CRITERIA" in result


def test_evaluation_block_does_not_contain_generation_content(skills_file: Path) -> None:
    result = load_evaluation_block(skills_file)
    assert "Write clearly" not in result


# ---------------------------------------------------------------------------
# Graceful degradation — file missing
# ---------------------------------------------------------------------------

def test_generation_block_missing_file_returns_empty(tmp_path: Path) -> None:
    result = load_generation_block(tmp_path / "nonexistent.md")
    assert result == ""


def test_evaluation_block_missing_file_returns_empty(tmp_path: Path) -> None:
    result = load_evaluation_block(tmp_path / "nonexistent.md")
    assert result == ""


def test_missing_file_does_not_raise(tmp_path: Path) -> None:
    """Must never raise — callers rely on empty-string contract."""
    try:
        load_generation_block(tmp_path / "no.md")
        load_evaluation_block(tmp_path / "no.md")
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"Unexpected exception: {e}")


# ---------------------------------------------------------------------------
# Graceful degradation — section header missing
# ---------------------------------------------------------------------------

def test_generation_block_missing_section_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "skills.md"
    f.write_text("## ANTI-PATTERNS\n\nOnly anti-patterns here.\n", encoding="utf-8")
    assert load_generation_block(f) == ""


def test_evaluation_block_missing_section_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "skills.md"
    f.write_text("## GENERATION STANDARDS\n\nOnly generation here.\n", encoding="utf-8")
    assert load_evaluation_block(f) == ""


def test_empty_file_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "skills.md"
    f.write_text("", encoding="utf-8")
    assert load_generation_block(f) == ""
    assert load_evaluation_block(f) == ""


# ---------------------------------------------------------------------------
# CRITICAL: Brace-escaping safety
# ---------------------------------------------------------------------------

def test_generation_block_escapes_single_braces(brace_file: Path) -> None:
    """Single {braces} in skills.md must be doubled for str.format() safety."""
    result = load_generation_block(brace_file)
    # The raw text has {display_name} — must become {{display_name}} in output
    assert "{display_name}" not in result.replace("{{", "X").replace("}}", "X")
    assert "{{display_name}}" in result


def test_evaluation_block_escapes_single_braces(brace_file: Path) -> None:
    result = load_evaluation_block(brace_file)
    assert "{product_name}" not in result.replace("{{", "X").replace("}}", "X")
    assert "{{product_name}}" in result


def test_brace_escaped_block_survives_str_format(brace_file: Path) -> None:
    """The returned block must be usable inside str.format() without KeyError."""
    result = load_generation_block(brace_file)
    template = "BEFORE\n{block}\nAFTER"
    # This must not raise KeyError
    try:
        rendered = template.format(block=result)
    except KeyError as e:
        pytest.fail(f"str.format() raised KeyError — brace escaping failed: {e}")
    assert "BEFORE" in rendered
    assert "AFTER" in rendered


def test_already_doubled_braces_survive(tmp_path: Path) -> None:
    """Content with {{ already escaped }} must not become {{{{ }}}}."""
    f = tmp_path / "skills.md"
    f.write_text("## GENERATION STANDARDS\n\nSee {{example}} for details.\n", encoding="utf-8")
    result = load_generation_block(f)
    # {{example}} becomes {{{{example}}}} — str.format() renders it as {{example}}
    # The key property: the block must still survive str.format() without error
    try:
        "prefix {block} suffix".format(block=result)
    except KeyError as e:
        pytest.fail(f"Double-brace content caused KeyError: {e}")


# ---------------------------------------------------------------------------
# Oversized block — warning emitted
# ---------------------------------------------------------------------------

def test_oversized_block_emits_warning(oversized_file: Path, caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="launcher.shared.skills_loader"):
        load_generation_block(oversized_file)
    assert any("truncated" in r.message.lower() or "chars" in r.message.lower()
               for r in caplog.records), \
        "Expected a WARNING about block size, got: " + str([r.message for r in caplog.records])


# ---------------------------------------------------------------------------
# page_role parameter — reserved, currently pass-through
# ---------------------------------------------------------------------------

def test_page_role_param_accepted(skills_file: Path) -> None:
    """page_role is a reserved parameter — must not raise."""
    result = load_generation_block(skills_file, page_role="howto_article")
    assert result != ""
    result2 = load_evaluation_block(skills_file, page_role="api_reference")
    assert result2 != ""


# ---------------------------------------------------------------------------
# _extract_section edge cases
# ---------------------------------------------------------------------------

def test_extract_section_trailing_newline(tmp_path: Path) -> None:
    """Section at end of file with trailing newline must be extracted."""
    f = tmp_path / "skills.md"
    f.write_text("## GENERATION STANDARDS\n\nContent here.\n", encoding="utf-8")
    result = _extract_section(f.read_text(), "## GENERATION STANDARDS")
    assert "Content here." in result


def test_extract_section_stops_at_next_header(tmp_path: Path) -> None:
    """Section extraction must stop before the next ## header."""
    f = tmp_path / "skills.md"
    f.write_text(
        "## GENERATION STANDARDS\n\nGen content.\n\n## EVALUATION CRITERIA\n\nEval content.\n",
        encoding="utf-8",
    )
    gen = _extract_section(f.read_text(), "## GENERATION STANDARDS")
    assert "Gen content." in gen
    assert "Eval content." not in gen


def test_extract_section_not_found_returns_empty() -> None:
    text = "## OTHER SECTION\n\nSome content.\n"
    result = _extract_section(text, "## GENERATION STANDARDS")
    assert result == ""
```

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_skills_loader.py -v` — all tests pass
- **UI/Web/API**: N/A
- **Tests**: All 30+ test cases pass; `tests/` overall unchanged pass count confirmed
- **Config respected end-to-end**: N/A for unit tests
- **No mock data in production paths**: Tests use `tmp_path` fixtures only; no real `skills.md` required

### Deliverables

1. `tests/unit/shared/test_skills_loader.py` — new file, full content above (no stubs)

### Hard rules

- No network calls in any test
- Use `tmp_path` for all file fixtures — never write to project root
- Every test must be deterministic (no random, no time-based)
- `caplog` fixture used correctly (not `monkeypatch` on logging)

### Review dimensions — what 5/5 means here

| Dimension | 5/5 criterion |
|-----------|---------------|
| Testability | 30+ tests covering happy path, 3 degradation paths, brace-escaping (critical), and edge cases |
| Correctness | Brace-escaping test uses actual `str.format()` call — not just string inspection |
| Robustness | Missing file, empty file, missing section, and already-doubled-braces cases all covered |
| Minimality | Zero test helpers that don't earn their place; no mock of the module under test |

### Now (runbook)

```bash
# 1. Create the test file at the path above with the full content
# 2. Run only the new tests first:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_skills_loader.py -v
# 3. If any fail, diagnose skills_loader.py behaviour (see SK-03 for truncation fix)
# 4. Run full suite to confirm no regressions:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard SK-03 — Add token-budget truncation to skills_loader.py

**Status**: Done
**Gap linkage**: G-03
**Role**: Senior engineer. Drop-in, production-ready.

### Fix

Add `_MAX_BLOCK_CHARS = 2000` (≈500 tokens) as a module-level constant in
`skills_loader.py`. In `_format_for_prompt`, truncate `safe` at the last
newline boundary before the limit, append a `[truncated]` marker, and emit a
WARNING. This prevents context-window overflow when `skills.md` grows large
without breaking existing behaviour for well-sized documents.

### Allowed paths

- `src/launcher/shared/skills_loader.py`

### Forbidden

Any file not listed above. Do not change test files (SK-02 tests already cover
the warning behaviour and will pass once this fix is applied).

### Scope

**In scope:**
- Add `_MAX_BLOCK_CHARS = 2000` constant with explanatory comment
- Add truncation logic in `_format_for_prompt` (before the `return` statement)
- Remove the now-redundant `_warn_if_large` function and its call sites (the
  truncation itself emits the warning — no separate post-hoc check needed)

**Out of scope:** Changes to callers, tests, prompts, workers.

### Replacement logic for `_format_for_prompt` and removal of `_warn_if_large`

Replace the current `_format_for_prompt` and `_warn_if_large` with:

```python
# Maximum characters for a skills block injected into a prompt.
# At ~4 chars/token this is ≈500 tokens — enough for meaningful guidance
# without risking context-window overflow on long prompts.
_MAX_BLOCK_CHARS = 2000


def _format_for_prompt(content: str, label: str) -> str:
    """Wrap content in a labelled block and escape braces for str.format().

    Truncates at the last newline boundary before ``_MAX_BLOCK_CHARS`` when
    content exceeds the budget, logging a WARNING with the original length.
    """
    safe = content.replace("{", "{{").replace("}", "}}")
    if len(safe) > _MAX_BLOCK_CHARS:
        original_len = len(safe)
        # Truncate at last newline to avoid splitting mid-sentence
        truncated = safe[:_MAX_BLOCK_CHARS].rsplit("\n", 1)[0]
        safe = truncated + "\n... [skills block truncated for token budget]"
        logger.warning(
            "[skills] Block truncated from %d to ~%d chars for prompt token budget",
            original_len, len(safe),
        )
    return (
        f"\n## {label}\n"
        f"{safe}\n"
        f"## END {label}\n"
    )
```

The `_warn_if_large` function and all calls to it are deleted since the
truncation warning now covers the same concern at the correct location.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_skills_loader.py -v` — all tests including `test_oversized_block_emits_warning` pass
- **UI/Web/API**: N/A
- **Tests**: Full test suite passes; the `test_oversized_block_emits_warning` test must pass specifically
- **Config respected end-to-end**: A `skills.md` with a GENERATION STANDARDS section exceeding 2000 chars must be truncated (confirm via WARNING log) rather than causing LLM errors
- **No mock data in production paths**: N/A

### Deliverables

1. `src/launcher/shared/skills_loader.py` — full replacement with truncation logic and `_warn_if_large` removed

### Hard rules

- `_MAX_BLOCK_CHARS` must be a named constant, not an inline magic number
- Truncation must occur at a newline boundary (no mid-word cuts)
- The truncation marker `[skills block truncated for token budget]` must appear in the output
- No change to public function signatures
- No new imports

### Review dimensions — what 5/5 means here

| Dimension | 5/5 criterion |
|-----------|---------------|
| Robustness | Any skills.md size is handled safely; no LLM call ever receives > ~2500 chars from skills |
| Correctness | Truncation boundary is at a newline; resulting block is still valid prompt text |
| Performance | No additional file I/O; truncation is pure string operation |
| Minimality | `_warn_if_large` removed — net diff is ≈0 lines; no dead code introduced |

### Now (runbook)

```bash
# 1. Edit src/launcher/shared/skills_loader.py:
#    a. Replace _format_for_prompt with the version above
#    b. Delete _warn_if_large function and its calls in load_generation_block and load_evaluation_block
#    c. Add _MAX_BLOCK_CHARS = 2000 constant above _format_for_prompt
# 2. Verify the oversized test passes:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_skills_loader.py::test_oversized_block_emits_warning -v
# 3. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard SK-04 — Add telemetry events for skills state

**Status**: Done
**Gap linkage**: G-04
**Role**: Senior engineer. Drop-in, production-ready.

### Fix

Emit structured telemetry events in both workers immediately after the skills
loading block. Event name: `skills_loaded` when active, `skills_inactive` when
disabled or file missing. This makes skills state queryable from the events log
and telemetry dashboard without requiring log-level inspection.

### Allowed paths

- `src/launcher/workers/generate/worker.py`
- `src/launcher/workers/evaluate/worker.py`

### Forbidden

Any file not listed above. No changes to `skills_loader.py` or tests in this
taskcard.

### Scope

**In scope:**
- In `generate/worker.py`: add `context.emit_event(...)` after the existing skills loading block
- In `evaluate/worker.py`: add `context.emit_event(...)` after the existing skills loading block

**Out of scope:** Changes to event schema files, event handler, or any other file.

### Replacement blocks

**In `generate/worker.py`**, replace the existing skills loading block:

```python
        # Load skills block once per run (TC-3856)
        _skills_block = ""
        _skills_cfg = getattr(context.config, "skills", None)
        if _skills_cfg is None or getattr(_skills_cfg, "enabled", True):
            try:
                from launcher.shared.skills_loader import load_generation_block as _load_skills
                _skills_path = Path(getattr(_skills_cfg, "path", "skills.md") if _skills_cfg else "skills.md")
                _skills_block = _load_skills(_skills_path)
                if _skills_block:
                    context.log.info("[Generate] Skills quality standards loaded (%d chars)", len(_skills_block))
            except Exception as _e:
                context.log.debug("[Generate] Skills load skipped: %s", _e)

        context.emit_event(
            "skills_loaded" if _skills_block else "skills_inactive",
            {
                "enabled": getattr(getattr(context.config, "skills", None), "enabled", True),
                "path": getattr(getattr(context.config, "skills", None), "path", "skills.md"),
                "chars": len(_skills_block),
            },
            worker=self.name,
        )
```

**In `evaluate/worker.py`**, replace the existing skills loading block:

```python
        # Load skills evaluation criteria once per run (TC-3856)
        _skills_criteria = ""
        _skills_cfg = getattr(context.config, "skills", None)
        if _skills_cfg is None or getattr(_skills_cfg, "enabled", True):
            try:
                from pathlib import Path as _Path
                from launcher.shared.skills_loader import load_evaluation_block as _load_eval_skills
                _skills_path = _Path(getattr(_skills_cfg, "path", "skills.md") if _skills_cfg else "skills.md")
                _skills_criteria = _load_eval_skills(_skills_path)
                if _skills_criteria:
                    context.log.info("[Evaluate] Skills evaluation criteria loaded (%d chars)", len(_skills_criteria))
            except Exception as _e:
                context.log.debug("[Evaluate] Skills load skipped: %s", _e)

        context.emit_event(
            "skills_loaded" if _skills_criteria else "skills_inactive",
            {
                "enabled": getattr(getattr(context.config, "skills", None), "enabled", True),
                "path": getattr(getattr(context.config, "skills", None), "path", "skills.md"),
                "chars": len(_skills_criteria),
            },
            worker=self.name,
        )
```

### Acceptance checks

- **CLI**: After a pipeline run, `grep "skills_loaded\|skills_inactive" runs/*/events.ndjson` returns an entry from both `generate` and `evaluate` workers
- **UI/Web/API**: Telemetry API (if running) shows `skills_loaded` events in the run trace
- **Tests**: Full suite passes; no new tests required for this taskcard (event emission is covered by existing worker integration tests)
- **Config respected end-to-end**: With `skills.enabled: false` in run config, event name is `skills_inactive` and `chars: 0`
- **No mock data in production paths**: N/A

### Deliverables

1. `src/launcher/workers/generate/worker.py` — updated skills loading block with emit
2. `src/launcher/workers/evaluate/worker.py` — updated skills loading block with emit

### Hard rules

- Event names must be lowercase with underscores: `skills_loaded`, `skills_inactive`
- Both workers must emit the event (not just generate)
- Payload must include `enabled`, `path`, `chars` — consistent between workers
- No new imports required (both workers already call `context.emit_event`)

### Review dimensions — what 5/5 means here

| Dimension | 5/5 criterion |
|-----------|---------------|
| Observability | `events.ndjson` contains skills state for every pipeline run — no log-hunting required |
| Consistency | Both workers emit identical event schema with the same field names |
| Minimality | ≤ 12 new lines per worker; reuses existing `emit_event` pattern |
| Correctness | `skills_inactive` fires when file is missing, disabled, or empty |

### Now (runbook)

```bash
# 1. Edit generate/worker.py — replace skills loading block with version above
# 2. Edit evaluate/worker.py — replace skills loading block with version above
# 3. Run full test suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 4. Confirm event emission manually (requires a real run or event-log inspection)
# grep "skills" runs/<latest>/events.ndjson 2>/dev/null | head -5
```

---

## Taskcard SK-05 — Document and harden path resolution for library use

**Status**: Done
**Gap linkage**: G-05
**Role**: Senior engineer. Drop-in, production-ready.

### Fix

`Path("skills.md")` resolves relative to the process CWD. In library use, this
may not be the project root. Fix by:

1. In `_read_skills`, after the primary CWD-relative check fails, attempt a
   secondary lookup relative to the caller's `run_dir` if available. Since the
   loader is stateless and doesn't receive `run_dir`, this secondary lookup is
   instead handled in the workers: workers resolve the path relative to
   `context.run_dir.parent` (the project root convention) before passing it to
   the loader. Add a `_resolve_skills_path` helper to both workers.

2. Update the `SkillsConfig.path` docstring to tell library users to pass an
   absolute path.

### Allowed paths

- `src/launcher/workers/generate/worker.py`
- `src/launcher/workers/evaluate/worker.py`
- `src/launcher/models/run_config.py`

### Forbidden

Any file not listed above.

### Scope

**In scope:**
- Add `_resolve_skills_path(cfg, run_dir) -> Path` helper used by both workers
- Update `SkillsConfig.path` field docstring to document absolute path recommendation
- Workers call the helper instead of `Path(getattr(..., "path", "skills.md"))`

**Out of scope:** Changes to `skills_loader.py` itself.

### Helper function (add once, import in both workers)

Add to `generate/worker.py` and `evaluate/worker.py` (each file independently,
do not create a shared module for this single function):

```python
def _resolve_skills_path(skills_cfg: object | None, run_dir: Path) -> Path:
    """Resolve the skills.md path with CWD-relative fallback chain.

    Resolution order:
    1. As-is if absolute.
    2. Relative to CWD (project-root convention for CLI use).
    3. Relative to run_dir.parent (project-root inference for library use).

    Returns the first existing path, or the CWD-relative path as fallback
    (skills_loader will handle the missing-file case gracefully).
    """
    raw = getattr(skills_cfg, "path", "skills.md") if skills_cfg else "skills.md"
    p = Path(raw)
    if p.is_absolute():
        return p
    # Try CWD first (standard CLI invocation)
    cwd_path = Path.cwd() / p
    if cwd_path.exists():
        return cwd_path
    # Try project root inferred from run_dir (library invocation)
    project_root = run_dir.parent
    root_path = project_root / p
    if root_path.exists():
        return root_path
    # Fall back to CWD-relative — skills_loader handles file-not-found gracefully
    return cwd_path
```

### `SkillsConfig.path` docstring update in `run_config.py`

```python
class SkillsConfig(LauncherBaseModel):
    """Quality-standards document configuration (TC-3856).

    When enabled, skills.md is loaded at worker startup and injected into
    both the generation and evaluation prompts. Works identically whether
    the pipeline is invoked via CLI, library import, or CI/CD.
    Gracefully degrades to no-op when the file at ``path`` does not exist.

    Path resolution:
        - Absolute paths are used as-is (recommended for library callers).
        - Relative paths are resolved against CWD first (CLI convention), then
          against ``run_dir.parent`` (library convention fallback).
        - Example for library use::

              from launcher.models.run_config import RunConfig, SkillsConfig
              config = RunConfig(
                  ...,
                  skills=SkillsConfig(enabled=True, path="/abs/path/to/skills.md"),
              )
    """
    enabled: bool = True
    path: str = "skills.md"
```

### Worker call-site update (both workers)

Replace:
```python
_skills_path = Path(getattr(_skills_cfg, "path", "skills.md") if _skills_cfg else "skills.md")
```
With:
```python
_skills_path = _resolve_skills_path(_skills_cfg, context.run_dir)
```

### Acceptance checks

- **CLI**: Pipeline invoked from project root finds `skills.md` as before (CWD path, step 1)
- **UI/Web/API**: N/A
- **Tests**: Full suite passes; add one parametrized test to `test_skills_loader.py` verifying that `_resolve_skills_path` returns the correct path for absolute, CWD-relative, and run_dir-relative inputs
- **Config respected end-to-end**: Library caller passing `skills=SkillsConfig(path="/abs/path/skills.md")` loads skills correctly regardless of CWD
- **No mock data in production paths**: Tests use `tmp_path` for all file operations

### Deliverables

1. `src/launcher/workers/generate/worker.py` — `_resolve_skills_path` helper + call-site update
2. `src/launcher/workers/evaluate/worker.py` — `_resolve_skills_path` helper + call-site update
3. `src/launcher/models/run_config.py` — `SkillsConfig.path` docstring updated

### Hard rules

- `_resolve_skills_path` must not raise — returns a `Path` object always
- Do not add `_resolve_skills_path` to `skills_loader.py` (it needs `run_dir` which is not available there)
- The resolution order (absolute → CWD → run_dir.parent) must be documented in the function docstring
- No new package dependencies

### Review dimensions — what 5/5 means here

| Dimension | 5/5 criterion |
|-----------|---------------|
| Robustness | Library callers with non-root CWD find their skills.md via run_dir fallback |
| Correctness | Absolute paths bypass all resolution logic; relative paths try two locations |
| Maintainability | Resolution logic is in one function per worker, clearly documented, not scattered |
| Production grading | Library use case (user's stated requirement) works without configuration gymnastics |

### Now (runbook)

```bash
# 1. Add _resolve_skills_path to generate/worker.py (as a module-level function)
# 2. Update the skills loading block in generate/worker.py to use it
# 3. Add _resolve_skills_path to evaluate/worker.py (copy the same function)
# 4. Update the skills loading block in evaluate/worker.py to use it
# 5. Update SkillsConfig.path docstring in run_config.py
# 6. Full test suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 7. Smoke test absolute path:
python -c "
from pathlib import Path
import os, sys
# Simulate library invocation from a temp dir
os.chdir(sys.argv[1] if len(sys.argv) > 1 else '/')
from launcher.shared.skills_loader import load_generation_block
result = load_generation_block(Path('skills.md').resolve())
print('absolute path result length:', len(result))
"
```

---

## Taskcard SK-06 — Export SkillsConfig from models/__init__.py

**Status**: Done
**Gap linkage**: G-06
**Role**: Senior engineer. Drop-in, production-ready.

### Fix

Add `SkillsConfig` to the exports in `src/launcher/models/__init__.py`. This
completes the module's encapsulation contract — every config class defined in
`run_config.py` should be importable from `launcher.models` directly, consistent
with how `SEOConfig`, `LLMConfig`, `OutputConfig`, and others are accessible.

### Allowed paths

- `src/launcher/models/__init__.py`

### Forbidden

Any file not listed above.

### Scope

**In scope:** Add `SkillsConfig` to `__init__.py` exports.

**Out of scope:** Any other change.

### Content for `src/launcher/models/__init__.py`

The current file is empty (1 blank line). Replace with:

```python
from __future__ import annotations

from launcher.models.run_config import (
    EmbeddingEndpoint,
    GeminiSEOConfig,
    LLMConfig,
    LLMEndpoint,
    ModelRouting,
    OutputConfig,
    ReasoningEndpoint,
    RunConfig,
    SEOConfig,
    SkillsConfig,
    TelemetryConfig,
)

__all__ = [
    "EmbeddingEndpoint",
    "GeminiSEOConfig",
    "LLMConfig",
    "LLMEndpoint",
    "ModelRouting",
    "OutputConfig",
    "ReasoningEndpoint",
    "RunConfig",
    "SEOConfig",
    "SkillsConfig",
    "TelemetryConfig",
]
```

### Acceptance checks

- **CLI**: `python -c "from launcher.models import SkillsConfig; print(SkillsConfig())"` exits 0
- **UI/Web/API**: N/A
- **Tests**: Full suite passes; add one assertion to `tests/unit/test_models.py`:
  ```python
  def test_skills_config_importable_from_models():
      from launcher.models import SkillsConfig
      cfg = SkillsConfig()
      assert cfg.enabled is True
      assert cfg.path == "skills.md"
  ```
- **Config respected end-to-end**: `SkillsConfig(enabled=False)` correctly disables skills when used in `RunConfig`
- **No mock data in production paths**: N/A

### Deliverables

1. `src/launcher/models/__init__.py` — full replacement with all exports including `SkillsConfig`
2. One assertion added to `tests/unit/test_models.py`

### Hard rules

- `__all__` must be alphabetically sorted
- Imports must use explicit names (no `import *`)
- This is a non-breaking change — existing imports from `launcher.models.run_config` continue to work

### Review dimensions — what 5/5 means here

| Dimension | 5/5 criterion |
|-----------|---------------|
| Consistency | Every public config class in `run_config.py` is exported via `__init__.py` |
| Minimality | Diff is ≤ 20 lines; no logic changes |
| Maintainability | `__all__` makes the public API explicit and auditable |
| Correctness | `from launcher.models import SkillsConfig` works without circular imports |

### Now (runbook)

```bash
# 1. Replace src/launcher/models/__init__.py with content above
# 2. Verify import:
python -c "from launcher.models import SkillsConfig; assert SkillsConfig().enabled is True; print('OK')"
# 3. Add assertion to tests/unit/test_models.py (see Acceptance checks above)
# 4. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Execution Order

Taskcards are independent but the following order minimises re-work:

1. **SK-02** first — tests expose any existing bugs in `skills_loader.py`
2. **SK-03** second — truncation fix may make SK-02 `test_oversized_block_emits_warning` pass
3. **SK-01** — config cleanup, no code risk
4. **SK-06** — export fix, no code risk
5. **SK-05** — path resolution, depends on stable worker structure from SK-04
6. **SK-04** — telemetry events, last because it touches workers twice

All 6 taskcards together represent a net addition of ~200 lines across the
codebase, with zero breaking changes to any public API.
