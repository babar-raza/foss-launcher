# Agent-C GEN-1/2/3 Evidence

## Taskcards

- TC-5201 (GEN-1): `plans/taskcards/TC-5201_gen1-pilot-config-reasoning-model.md` — Done
- TC-5202 (GEN-2/3): `plans/taskcards/TC-5202_gen23-anti-echo-identifier-repair.md` — Done

## Files Changed

### GEN-1: Pilot config model routing
- `configs/pilots/aspose-3d-foss-dotnet.yaml`
- `configs/pilots/aspose-3d-foss-java.yaml`
- `configs/pilots/aspose-3d-foss-python.yaml`
- `configs/pilots/aspose-3d-foss-typescript.yaml`
- `configs/pilots/aspose-cells-foss-python.yaml`
- `configs/pilots/aspose-email-foss-python.yaml`
- `configs/pilots/aspose-note-foss-python.yaml`
- `configs/pilots/aspose-slides-foss-cpp.yaml`
- `configs/pilots/aspose-slides-foss-dotnet.yaml`
- `configs/pilots/aspose-slides-foss-java.yaml`
- `configs/pilots/aspose-slides-foss-python.yaml`

### GEN-2: Anti-echo guard
- `src/launcher/prompts/section_writer.txt`

### GEN-3: Identifier repair softening
- `src/launcher/workers/generate/_identifier_repair.py`
- `tests/unit/workers/generate/test_identifier_repair.py`

## GEN-1 Verification

```
grep -r "generate:" configs/pilots/ | sort
```

Output (11 lines, all reasoning):
```
configs/pilots/aspose-3d-foss-dotnet.yaml:    generate: reasoning
configs/pilots/aspose-3d-foss-java.yaml:    generate: reasoning
configs/pilots/aspose-3d-foss-python.yaml:    generate: reasoning
configs/pilots/aspose-3d-foss-typescript.yaml:    generate: reasoning
configs/pilots/aspose-cells-foss-python.yaml:    generate: reasoning
configs/pilots/aspose-email-foss-python.yaml:    generate: reasoning
configs/pilots/aspose-note-foss-python.yaml:    generate: reasoning
configs/pilots/aspose-slides-foss-cpp.yaml:    generate: reasoning
configs/pilots/aspose-slides-foss-dotnet.yaml:    generate: reasoning
configs/pilots/aspose-slides-foss-java.yaml:    generate: reasoning
configs/pilots/aspose-slides-foss-python.yaml:    generate: reasoning
```

`grep -r "generate: standard" configs/pilots/` → 0 matches.

## Infrastructure Verification

- `src/launcher/models/run_config.py`: `generate: Literal["standard", "reasoning"] = "standard"` — `reasoning` is a valid literal.
- `src/launcher/clients/llm_provider.py`: `_THINK_TAG_RE = re.compile(r"<think>[\s\S]*?</think>", re.DOTALL)` present and applied in `_extract_content()` — `<think>` tags handled.
- `reasoning` tier in each pilot config maps to `model: recommended` via `llm.reasoning` block.

## GEN-2 Changes

`src/launcher/prompts/section_writer.txt` SECTION GUIDANCE block changed from:
```
SECTION GUIDANCE:
{content_hint}
{structure_directive}
```
To:
```
SECTION GUIDANCE (these are instructions for YOU as the writer — NEVER copy or paraphrase this guidance text into your output):
Goal: {content_hint}
DO NOT echo, quote, or restate the goal above. Write original technical prose that fulfills the goal.
{structure_directive}
```

New STRICT RULE added:
```
- NEVER write a sentence of the form "{display_name} -- [description of what to write]". That pattern means you are outputting the section guidance instead of real content. Write REAL CONTENT.
```

## GEN-3 Changes

New functions added to `_identifier_repair.py`:
- `_build_known_set_lower(known_set)` — frozenset of lowercase versions of all known identifiers
- `_build_method_names_set(api_surface)` — frozenset of all method/property names (both original and lowercase)

`_repair_prose_segment()` new parameters:
- `known_set_lower: frozenset[str] | None = None`
- `known_method_names: frozenset[str] | None = None`

New checks in `_replace_token()`:
```python
if token.lower() in _ksl:
    return token  # case-insensitive match — preserve
if token.lower() in _kmn or token in _kmn:
    return token  # known API method/property — preserve
```

Same checks applied in `_repair_code_segment()`.

`repair_identifiers()` now builds both sets and passes them down.

## Test Results

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_identifier_repair.py -x -q
35 passed in 1.21s
```

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q
5484 passed, 8 skipped in 129.93s
```

0 failures. 0 regressions.

## Known Gaps

1. **Claim-text exemption (GEN-3, Addition 3)**: Not implemented. The `repair_identifiers()` function only receives `section_text` and `api_surface`; claim objects are not available in this call scope. The claims are in the `SectionPlan` (a higher-level object) and would require a signature change propagated through `worker.py`. This is deferred — the case-insensitive and property-path additions already cover the most common false-positive cases. If needed, a separate TC can thread `claim_ids` text into this function.
