# foss-launcher v2 — Agent Instructions

## Primary Goal: Publication-Ready Content

Every action in this repository must push toward **publication-ready content**.
Content that would embarrass the product in front of a paying customer is
never acceptable. This north star overrides convenience, speed, and scope.

## Architecture: v2

This is a clean rewrite. See `C:\Users\prora\.claude\plans\twinkly-puzzling-minsky.md` for the full plan.

- **5 Workers**: Intake, Understand, Generate, Evaluate, Publish
- **Config-driven pipeline**: `configs/pipeline.yaml` defines topology
- **Contract-bound**: Every boundary enforced by JSON schema or pydantic model
- **Sandwich model**: Engineering > LLM > Engineering at every LLM call
- **No patching**: Root-cause re-generation only (Rule 6)

## Package Structure

- Source: `src/launcher/` (note: `launcher`, not `launch`)
- Tests: `tests/`
- Specs: `specs/` (18 unnumbered spec files)
- Schemas: `specs/schemas/` (19 JSON schemas + event schemas)
- Templates: `specs/templates/` (Hugo templates by subdomain)
- Rulesets: `specs/rulesets/ruleset.yaml` (mandatory/optional page sets)
- Configs: `configs/` (families.yaml, pipeline.yaml, pilots/)

## Key Conventions

- **PYTHONHASHSEED=0**: Required for deterministic tests
- **Venv python**: `.venv/Scripts/python.exe -m pytest`
- **No numbered specs or gates**: Use descriptive names only
- **Schema validation at every boundary**: Worker I/O, LLM calls, events, gates
- **Orphan branch**: This is the `v2` branch; `main` has v1

## LLM Configuration

- Primary: `https://llm.professionalize.com/v1` model `qwen3-next/oss`
- Fallback: `http://127.0.0.1:11434/v1` model `gemma3:12b`
- API key env: `litellm_key`
- Temperature: 0.0 (deterministic)

## Governance

See `.claude_code_rules` for agent governance rules (AG-001 through AG-015).
Taskcard-first workflow applies to all code changes.
