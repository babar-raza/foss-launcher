# Documentation — Reference Materials

This directory contains **reference documentation** (non-binding) that guides implementation but does not define system contracts. For binding specifications, see [specs/](../specs/).

## Overview

The `docs/` directory provides:
- **Architecture overviews** - System design and component relationships
- **CLI usage guides** - Command-line interface documentation
- **API references** - Detailed API documentation for MCP endpoints and telemetry
- **Implementation notes** - Non-normative guidance for developers

## Documentation vs Specifications

| Category | Location | Authority | Purpose |
|----------|----------|-----------|---------|
| **Binding Specs** | `specs/` | NORMATIVE | Define system contracts, must be implemented |
| **Reference Docs** | `docs/` | INFORMATIVE | Explain concepts, provide examples, guide implementation |

**Key Difference**: If there is a conflict between `specs/` and `docs/`, the spec is authoritative. Docs provide context and examples but do not override specs.

## Documentation Files

### System Architecture

| File | Description | Audience |
|------|-------------|----------|
| [architecture.md](architecture.md) | High-level system architecture and component relationships | All developers, architects |

**Contents**:
- System overview diagram
- Worker pipeline (W1-W9)
- Orchestrator responsibilities
- MCP server role
- State management approach

**When to Read**: Before starting implementation work or when designing new workers.

### CLI Usage

| File | Description | Audience |
|------|-------------|----------|
| [cli_usage.md](cli_usage.md) | Command-line interface documentation | End users, agent operators, CI authors |

**Contents**:
- `launch_run` - Create scaffold RUN_DIR from run_config
- `launch_validate` - Run validation gates on RUN_DIR
- CLI flags and options
- Environment variables
- Exit codes
- Common workflows
- Preflight validation (`validate_swarm_ready.py`)

**When to Read**: When running CLI commands or setting up CI pipelines.

### API References

| File | Description | Audience |
|------|-------------|----------|
| [reference/local-telemetry-api.md](reference/local-telemetry-api.md) | Local telemetry API endpoints | Worker implementers, debugging |
| [reference/local-telemetry.md](reference/local-telemetry.md) | Telemetry event schema and usage | Worker implementers, observability |

**Contents**:
- API endpoint specifications
- Request/response formats
- Event schema definitions
- Example usage
- Error handling

**When to Read**: When implementing workers that emit telemetry or when debugging event flows.

## Document Classification

All documents in `docs/` are **REFERENCE** (non-binding). They:
- Explain concepts from `specs/`
- Provide usage examples
- Offer implementation guidance
- Document existing behavior (not prescriptive)

If you need binding requirements, see [specs/README.md](../specs/README.md).

## When to Use Each Doc

### Starting Implementation
1. Read [architecture.md](architecture.md) for system overview
2. Read relevant binding specs in `specs/` for contracts
3. Read [cli_usage.md](cli_usage.md) for CLI workflows
4. Refer to API references as needed during development

### Writing a Worker
1. Read [specs/21_worker_contracts.md](../specs/21_worker_contracts.md) for I/O contracts (BINDING)
2. Read [architecture.md](architecture.md) for worker pipeline context
3. Read [reference/local-telemetry-api.md](reference/local-telemetry-api.md) for event emission

### Setting Up CI
1. Read [cli_usage.md](cli_usage.md) for CLI usage
2. Read [specs/19_toolchain_and_ci.md](../specs/19_toolchain_and_ci.md) for toolchain requirements (BINDING)
3. Read [specs/09_validation_gates.md](../specs/09_validation_gates.md) for gate definitions (BINDING)

### Debugging
1. Read [reference/local-telemetry-api.md](reference/local-telemetry-api.md) for event inspection
2. Read [architecture.md](architecture.md) for component relationships
3. Read relevant specs in `specs/` for expected behavior

## Adding New Documentation

When adding new documentation files:

1. **Determine if it should be a spec or doc**
   - **Spec** (binding): Defines contracts, workflows, runtime behavior that must be enforced
   - **Doc** (reference): Explains concepts, provides examples, guides implementation

2. **If it's a doc (non-binding)**:
   - Create file in `docs/` or `docs/reference/`
   - Use `.md` extension
   - Follow existing style (see below)

3. **Update this README**:
   - Add entry to relevant table above
   - Specify description and audience
   - Add to "When to Use Each Doc" section if applicable

4. **Cross-reference from specs**:
   - If doc explains a spec concept, link from spec to doc
   - Example: "See [docs/architecture.md](../docs/architecture.md) for diagram"

5. **Validate links**:
   ```bash
   python tools/check_markdown_links.py
   ```

## Documentation Style Guide

### Structure
- **Title** - Clear, descriptive (e.g., "Command-Line Interface Documentation")
- **Overview** - 1-2 paragraphs explaining purpose and scope
- **Sections** - Logical groupings with clear headings
- **Examples** - Concrete usage examples with expected output
- **References** - Links to related specs and docs

### Formatting
- Use markdown headings (`#`, `##`, `###`)
- Use code blocks for commands and outputs (```)
- Use tables for structured information
- Use bullet points for lists
- Use **bold** for emphasis, `code` for literals

### Tone
- **Clear and concise** - Avoid jargon, explain acronyms
- **Imperative for instructions** - "Run this command", "Set this variable"
- **Indicative for descriptions** - "This command creates...", "The system validates..."
- **Consistent terminology** - Use terms from [GLOSSARY.md](../GLOSSARY.md)

### Cross-References
- Link to specs using relative paths: `[specs/01_system_contract.md](../specs/01_system_contract.md)`
- Link to other docs using relative paths: `[architecture.md](architecture.md)`
- Link to external resources using full URLs

## Documentation Maintenance

### When Specs Change
If a spec is updated and affects documentation:
1. Update relevant docs to reflect spec changes
2. Ensure no conflicts between spec and doc
3. Add update note in doc (e.g., "Updated 2026-01-27: Reflects spec 01_system_contract.md v1.2")

### When Implementation Changes
If implementation changes (but spec stays same):
1. Update docs to reflect new behavior
2. Do NOT change specs unless contract changed
3. Document workarounds or known issues if applicable

### Regular Audits
Periodically audit docs for:
- **Accuracy** - Does doc match current specs/implementation?
- **Completeness** - Are all CLI commands/APIs documented?
- **Link health** - Do all internal links work? (run `python tools/check_markdown_links.py`)
- **Clarity** - Is explanation clear for target audience?

## Common Questions

### Should I update a spec or a doc?
- **Spec** if you're changing a contract, workflow, or validation rule
- **Doc** if you're clarifying usage, adding examples, or explaining concepts

### Where do I document CLI commands?
- **Binding interface** - `specs/` (e.g., `specs/01_system_contract.md` for contract)
- **Usage guide** - `docs/cli_usage.md` (examples, workflows, common issues)

### Where do I document API endpoints?
- **Binding contract** - `specs/` (e.g., `specs/14_mcp_endpoints.md` for MCP server)
- **API reference** - `docs/reference/` (detailed examples, error codes, edge cases)

### Can docs contradict specs?
**NO**. If there is a conflict:
1. Spec is authoritative (binding)
2. Doc must be updated to match spec
3. If spec is wrong, update spec first, then doc

## Reference Materials

- **Binding Specs**: [specs/README.md](../specs/README.md)
- **Glossary**: [GLOSSARY.md](../GLOSSARY.md)
- **Architecture**: [architecture.md](architecture.md)
- **CLI Usage**: [cli_usage.md](cli_usage.md)
- **Taskcard Contract**: [plans/taskcards/00_TASKCARD_CONTRACT.md](../plans/taskcards/00_TASKCARD_CONTRACT.md)

## Directory Structure

```
docs/
├── README.md (this file)
├── architecture.md - System architecture overview
├── cli_usage.md - CLI command documentation
└── reference/
    ├── local-telemetry-api.md - Telemetry API reference
    └── local-telemetry.md - Telemetry event schema
```

Future additions:
- `debugging.md` - Debugging guide for agents and workers
- `performance.md` - Performance tuning and optimization
- `troubleshooting.md` - Common issues and solutions
- `examples/` - Full end-to-end examples
