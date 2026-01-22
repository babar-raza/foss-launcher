# Toolchain and CI Contract (deterministic gates)

## Purpose
Specs/09_validation_gates.md defines what to validate, but not how to run gates deterministically.
Agents need a pinned toolchain and a single command surface so results match across machines and over time.

This document defines:
- a required toolchain lock file
- a standard gate runner interface
- deterministic defaults for each gate

## Required file: toolchain.lock.yaml
The repo MUST include a lock file checked into version control:

- config/toolchain.lock.yaml

The orchestrator and validators MUST refuse to run in production mode if this file is missing.

### toolchain.lock.yaml contract
- It pins exact tool versions (and preferably container images by digest).
- It pins the validation ruleset versions (markdownlint config, link checker allowlist).
- It pins the Hugo version used to build the target site.

**Binding rule:** `PIN_ME` is a sentinel that means "not pinned".
The validator MUST fail fast (prod + CI profiles) if any required version fields are still `PIN_ME`.

Example:
```yaml
schema_version: "1.0"

tools:
  hugo:
    flavor: "extended"
    version: "0.1.0"   # replace with your pinned version
  node:
    version: "20.0.0"  # replace with your pinned version
  python:
    version: "3.12.0"  # replace with your pinned version
  dotnet:
    version: "8.0.0"   # optional, only if snippet validation needs it

validation:
  markdownlint:
    cli: "markdownlint-cli2"
    version: "0.22.0"  # pinned (align to config/toolchain.lock.yaml)
    config_path: "config/markdownlint-cli2.yaml"
  link_checker:
    cli: "lychee"
    version: "0.22.0"  # pinned (align to config/toolchain.lock.yaml)
    allowlist_path: "config/lychee_allowlist.txt"

containers:
  python:
    image: "python:3.12-slim"  # prefer image@sha256:digest
  node:
    image: "node:20-slim"
  dotnet:
    image: "mcr.microsoft.com/dotnet/sdk:8.0"

## Standard gate runner interface
Implement exactly one command entrypoint for validation.
`--run_dir` is the absolute run folder path (`RUN_DIR`, see `specs/29_project_repo_structure.md`).

Implement exactly one command entrypoint for validation:

- `launch_validate --run_dir runs/<run_id> --profile prod`

This command MUST:
- read `config/toolchain.lock.yaml`
- run gates in the exact order defined below
- write all logs under `runs/<run_id>/logs/`
- write `RUN_DIR/artifacts/validation_report.json` that matches `schemas/validation_report.schema.json`

If you prefer Make or scripts, that is fine, but the orchestrator MUST have one stable invocation surface.

## Gate command definitions
These commands are canonical. The implementation can wrap them, but the underlying behavior must match.

### Gate 1: Schema validation
Inputs:
- `runs/<run_id>/artifacts/*.json`

Rules:
- validate all JSON artifacts against `specs/schemas/*.schema.json`
- fail on unknown keys (additionalProperties=false is already enforced by schemas)

Output:
- log: `runs/<run_id>/logs/gate_schema_validation.log`

### Gate 2: Frontmatter contract validation
Inputs:
- all created or modified `.md` files under the site worktree
- `RUN_DIR/artifacts/frontmatter_contract.json`

Rules:
- every new page must include all required keys for its section
- type mismatches are errors unless the contract type is `unknown`

Output:
- log: `runs/<run_id>/logs/gate_frontmatter.log`

### Gate 3: Markdown lint
Rules:
- use the pinned markdownlint config from `toolchain.lock.yaml`
- no new lint errors are allowed

Output:
- log: `runs/<run_id>/logs/gate_markdownlint.log`

### Gate 4: Hugo config compatibility
Rules:
- run the `hugo_config` gate defined in `specs/31_hugo_config_awareness.md`
- verify the plan targets a build-enabled `(subdomain, family)` pair for non-blog sections
- ensure config fingerprints exist in `RUN_DIR/artifacts/site_context.json`

Output:
- log: `runs/<run_id>/logs/gate_hugo_config.log`

### Gate 5: Hugo build
Rules:
- run Hugo in production mode using the pinned Hugo version
- build must succeed
- build output must be discarded after validation (do not commit generated files)

Output:
- log: `runs/<run_id>/logs/gate_hugo_build.log`

### Gate 6: Internal links
Rules:
- check links and anchors for files touched by the PatchBundle
- fail on broken internal links

Output:
- log: `runs/<run_id>/logs/gate_internal_links.log`

### Gate 7: External links (configurable)
Rules:
- optional by run_config
- if enabled, use pinned allowlist and retry settings

Output:
- log: `runs/<run_id>/logs/gate_external_links.log`

### Gate 8: Snippet checks
Rules:
- at minimum, syntax-check each snippet in SnippetCatalog
- if runnable checks are enabled, run them in pinned containers

Output:
- log: `runs/<run_id>/logs/gate_snippets.log`

### Gate 9: TruthLock
Rules:
- enforce `specs/04_claims_compiler_truth_lock.md`
- fail if any factual statement is missing a claim marker that resolves to a grounded EvidenceMap entry

Output:
- log: `runs/<run_id>/logs/gate_truthlock.log`

## Determinism rules for gate logs
- Logs MUST be stable and machine-parseable.
- Avoid timestamps inside logs unless required by the tool.
- If tool output includes timestamps, the validator MUST also write a normalized summary section.

## CI mapping
CI MUST run the same gate runner:
- `launch_validate --profile ci`

The `ci` profile may skip runnable snippet checks for speed, but must not skip schema, Hugo config compatibility, Hugo build, internal links, or TruthLock.

### Gate: TemplateTokenLint (required)
**Purpose**: fail fast if any template tokens leaked into generated content.

**Rule**: scan all newly generated or modified Markdown files in the launch diff for the pattern:
- `__([A-Z0-9]+(?:_[A-Z0-9]+)*)__`

If any matches remain, the gate MUST fail and report:
- file path
- line number
- the token found

This gate MUST run after Markdown linting and before Hugo-config and link checks, so agents do not waste cycles validating placeholder content.
