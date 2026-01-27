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

## Tool Version Verification (binding)

All validation gates MUST verify tool versions at runtime to prevent silent drift.

### Tool Lock File

Path: `config/toolchain.lock.yaml`

Format:
```yaml
schema_version: "1.0"
tools:
  - name: hugo
    version: "0.128.0"
    checksum: "sha256:abcdef123456..."
    download_url: "https://github.com/gohugoio/hugo/releases/download/v0.128.0/hugo_0.128.0_Linux-64bit.tar.gz"
  - name: markdownlint-cli
    version: "0.39.0"
    checksum: "sha256:fedcba654321..."
    install_cmd: "npm install -g markdownlint-cli@0.39.0"
  - name: lychee
    version: "0.14.3"
    checksum: "sha256:123abc456def..."
    download_url: "https://github.com/lycheeverse/lychee/releases/download/v0.14.3/lychee-v0.14.3-x86_64-unknown-linux-gnu.tar.gz"
```

### Verification Algorithm (binding)

Before running any validation gate that uses external tools:
1. Load `config/toolchain.lock.yaml`
2. For each tool used by the gate:
   a. Run `{tool} --version` and parse version string
   b. Compare to `tools[].version` in lock file
   c. If version mismatch:
      - Emit BLOCKER issue with error_code `GATE_TOOL_VERSION_MISMATCH`
      - Include in issue.message: "Expected {tool} version {expected}, found {actual}"
      - Halt gate execution
   d. If version matches, log INFO and proceed
3. Emit telemetry event `TOOL_VERSION_VERIFIED` with tool name and version

### Checksum Verification (optional but recommended)

For downloaded binaries (hugo, lychee):
1. After download, compute `sha256(binary)`
2. Compare to `tools[].checksum` in lock file
3. If mismatch: emit BLOCKER issue `TOOL_CHECKSUM_MISMATCH` and halt

### Tool Installation Script

Provide `scripts/install_tools.sh` (or .ps1 for Windows) that:
1. Reads `config/toolchain.lock.yaml`
2. Downloads/installs each tool at the specified version
3. Verifies checksums
4. Writes tools to `.tools/` directory at repo root
5. Emits telemetry event `TOOLS_INSTALLED` with versions

CI MUST run `scripts/install_tools.sh` before running validation gates.

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

## Toolchain Verification Best Practices (binding)

### Tool Version Pinning and Verification
- MUST pin exact tool versions in toolchain.lock.yaml (no version ranges like `>=0.1.0` or `^0.1.0`)
- MUST verify tool version matches lock file before executing any validation gate
- MUST fail with BLOCKER issue if tool version mismatch detected (emit error_code `TOOLCHAIN_VERSION_MISMATCH`)
- SHOULD use cryptographic checksums (sha256) for tool binaries to prevent supply chain attacks
- SHOULD prefer container images with digest pins (e.g., `python@sha256:abc123...`) over version tags

### Tool Installation and Caching
- MUST document tool installation instructions for all required validation tools
- SHOULD cache tool binaries in CI/CD pipeline to avoid re-downloading on every run
- SHOULD validate cached tool checksums before use (prevent cache poisoning)
- MUST provide fallback installation mechanism if cache miss or checksum mismatch
- SHOULD use version-specific cache keys (e.g., `hugo-0.128.0-linux-amd64`)

### Deterministic Execution Environment
- MUST set consistent locale/timezone (e.g., `LC_ALL=C.UTF-8`, `TZ=UTC`) for all tool executions
- MUST disable tool auto-updates and telemetry collection (e.g., `DOTNET_CLI_TELEMETRY_OPTOUT=1`)
- MUST use deterministic flags for tools (e.g., Hugo: `--gc --minify` for reproducible builds)
- SHOULD execute validation gates in isolated environments (containers or sandboxed processes)
- MUST document all environment variables required for deterministic tool behavior

### Error Handling and Diagnostics
- MUST capture full stdout/stderr from all tool executions
- MUST include tool version in error messages and telemetry events
- SHOULD log tool execution time for performance monitoring
- MUST emit telemetry event `TOOL_EXECUTION_FAILED` with error_code, tool name, version, exit code
- SHOULD provide actionable error messages (e.g., "Hugo build failed: missing shortcode 'product_link'")

### Continuous Integration Best Practices
- MUST use same toolchain.lock.yaml in CI as in local development (prevent CI-only failures)
- MUST fail CI builds fast if toolchain lock file is missing or invalid
- SHOULD run toolchain verification as first CI step (before expensive operations)
- SHOULD cache validation results per commit SHA (skip redundant validations on re-runs)
- MUST expose validation report as CI artifact for debugging failed builds

### Tool Update and Migration
- MUST document tool update process (how to safely update pinned versions)
- SHOULD test tool updates in isolated branch before updating main toolchain.lock.yaml
- MUST validate all gates pass with new tool versions before merging update
- SHOULD maintain changelog of tool version updates with rationale
- MUST coordinate tool updates across team (prevent version drift between developers)

### Security and Supply Chain
- MUST verify tool download URLs use HTTPS (prevent MITM attacks)
- SHOULD verify GPG signatures for tool releases (when available)
- MUST document approved tool sources (e.g., official GitHub releases, npm registry)
- SHOULD scan tools for known vulnerabilities using CVE databases
- MUST NOT execute tools from untrusted sources or user-provided URLs

### Performance Optimization
- SHOULD parallelize independent validation gates (e.g., markdownlint and Hugo build in parallel)
- SHOULD skip validation gates if no relevant files changed (e.g., skip Hugo build if no .md/.html files changed)
- MUST respect timeouts for long-running gates (default: 300s, configurable per gate)
- SHOULD implement incremental validation where possible (only validate changed files)

### Acceptance
- All tools pinned in toolchain.lock.yaml with exact versions
- Tool version verification implemented and tested
- Deterministic execution environment documented
- Error handling captures tool output for debugging
- CI pipeline uses same toolchain as local development
- Security best practices implemented (HTTPS, checksums, approved sources)
