# foss-launcher v2

Publication-ready content generation for FOSS products across families, platforms, and API richness tiers.

## Architecture

5-worker pipeline with config-driven topology:

```
Intake → Understand → Generate → Evaluate → Publish
                         ↑            │
                         └── RE-RUN ──┘
```

## Quick Start

```bash
# Install
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -e ".[dev]"

# Run tests
PYTHONHASHSEED=0 pytest

# Run a pilot
launch run --config configs/pilots/aspose-cells-foss-python.yaml
```

## Ground Rules

0. Only one goal: best quality content
1. Every worker reviews its own work
2. Every phase is reviewable
3. Checkpoint + manual edit + resume
4. Multi-family, multi-platform
5. Sandwich model at every LLM call
6. No patching — root cause fixes only
7. Fewer merged workers
8. Built-in content reviewer
9. Config-driven pipeline
10. Contract-bound, schema-driven at every boundary
