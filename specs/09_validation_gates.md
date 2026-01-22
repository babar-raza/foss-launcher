# Validation Gates (Stop the line)

## Purpose
Define quality gates that MUST pass before a run can be released, including timeout behavior, profile-based gating, and gate execution order.

## Dependencies
- [specs/01_system_contract.md](01_system_contract.md) - Error handling and exit codes
- [specs/04_claims_compiler_truth_lock.md](04_claims_compiler_truth_lock.md) - TruthLock rules
- [specs/18_site_repo_layout.md](18_site_repo_layout.md) - Content root contracts
- [specs/31_hugo_config_awareness.md](31_hugo_config_awareness.md) - Hugo config validation
- [specs/schemas/validation_report.schema.json](schemas/validation_report.schema.json) - Validation report schema
- [specs/schemas/issue.schema.json](schemas/issue.schema.json) - Issue schema

---

# Validation Gates (Stop the line)

## Gates
1) Schema validation
- Validate all JSON artifacts against schemas/.
- Validate page frontmatter against frontmatter rules or schema where available.

2) Markdown lint
- markdownlint or equivalent, with a pinned ruleset.
- No new lint errors allowed.

3) Hugo config compatibility (`hugo_config`)
- Ensure the planned `(subdomain, family)` pairs are enabled by Hugo configs (see `specs/31_hugo_config_awareness.md`).
- Ensure every planned `output_path` matches the content root contract (`specs/18_site_repo_layout.md`).
- Fail fast with blocker issue `HugoConfigMissing` when configs do not cover required sections.

4) Platform layout compliance (`content_layout_platform`) — **NEW**
- When `layout_mode` resolves to `v2` for a section:
  - Non-blog sections (products, docs, kb, reference) MUST contain `/{locale}/{platform}/` in output paths
  - Blog section MUST contain `/{platform}/` at correct depth
  - Products section MUST use `/{locale}/{platform}/` (NOT `/{platform}/` alone)
- All planned writes MUST be within taskcard `allowed_paths`
- `allowed_paths` MUST include platform-level roots for V2 sections
- Generated content MUST NOT contain unresolved `__PLATFORM__` tokens
- Resolved `layout_mode` per section MUST be consistent across planning artifacts
- **Gate failure**: BLOCKER (no acceptable warnings)
- See `specs/32_platform_aware_content_layout.md` for detailed requirements

5) Hugo build
- run hugo build in production mode.
- build must succeed.

6) Internal links
- check internal links and anchors.
- no broken internal links.

7) External links (optional by config)
- lychee or equivalent.
- allowlist domains if needed.

8) Snippet checks
Minimum:
- syntax check for each snippet
Optional:
- run snippets in container for supported languages

9) TruthLock
- enforce 04_claims_compiler_truth_lock.md rules.

10) Consistency
- product_name, repo_url, canonical URL consistent
- required headings present
- required sections present

## Gate outputs
- validation_report.json (schemas/validation_report.schema.json)
- truth_lock_report.json (schemas/truth_lock_report.schema.json)
- issues list (schemas/issue.schema.json)

## Fix loop
VALIDATING -> FAIL -> FIXING -> VALIDATING
- Fix attempts must be capped (config).
- Each fix must be targeted and recorded as patches.
- **Manual content edits are forbidden by default**.
  - If `run_config.allow_manual_edits=false` (default): any changed file must have a patch/evidence record produced by the pipeline stages; unexplained diffs fail with a policy issue.
  - If `run_config.allow_manual_edits=true` (emergency only): validator must set `validation_report.manual_edits=true` and enumerate the affected files; orchestrator master review must list and justify them.

## Timeout Configuration (binding)

Each gate MUST have explicit timeout values to prevent indefinite hangs:

### Gate Timeouts by Profile

**local profile** (development):
- Schema validation: 30s per artifact
- Markdown lint: 60s
- Hugo config check: 10s
- Hugo build: 300s (5 minutes)
- Internal links: 120s
- External links: 300s (when enabled)
- Snippet syntax checks: 60s per snippet file
- TruthLock: 60s
- Consistency checks: 30s

**ci profile** (continuous integration):
- Schema validation: 60s per artifact
- Markdown lint: 120s
- Hugo config check: 20s
- Hugo build: 600s (10 minutes)
- Internal links: 180s
- External links: 600s (when enabled)
- Snippet syntax checks: 120s per snippet file
- TruthLock: 120s
- Consistency checks: 60s

**prod profile** (not typically used for gating, reference only):
- Same as CI profile but may include additional checks

### Timeout Behavior
- On timeout: emit BLOCKER issue with `error_code: GATE_TIMEOUT`
- Record which gate timed out in validation_report.json
- Do NOT retry timed-out gates automatically (orchestrator decides)
- Log timeout events to telemetry with gate name and elapsed time

---

## Profile-Based Gating (binding)

Validation behavior varies by profile:

### Profile Selection
Profile is determined by:
1. `run_config.validation_profile` (if present)
2. `--profile` CLI argument to `launch_validate`
3. Environment variable `LAUNCH_VALIDATION_PROFILE`
4. Default: `local`

### Profile Characteristics

**local** (development, fast feedback):
- Skip external link checks by default (override with `--check-external-links`)
- Skip runnable snippet execution (syntax check only)
- Relaxed timeout values
- Warnings don't fail the run (only errors)

**ci** (continuous integration, comprehensive):
- Run all gates including external links (if configured)
- Stricter timeouts
- Warnings MAY fail the run (configurable per `run_config.ci_strictness`)
- Hugo build in production mode
- Full TruthLock enforcement

**prod** (hypothetical, maximum rigor):
- All gates enabled
- Zero tolerance for warnings
- Longest timeouts
- Additional compliance checks (if defined)

### Profile Transitions
- Profile MUST be set at run start and MUST NOT change mid-run
- Validation reports MUST record which profile was used
- Fix loops inherit the profile from the initial validation

---

## Acceptance
All gates pass and validation_report.ok == true.

Additional acceptance criteria:
- validation_report.json validates against schema
- validation_report.profile field matches the profile used
- All timeouts are respected (no gate exceeds its timeout)
- All issues are recorded in issues[] array
- Gate execution order is: schema → lint → hugo_config → content_layout_platform → hugo_build → links → snippets → truthlock → consistency

## Universality Gates

### Gate: Tier compliance (new)
- If `launch_tier=minimal`, pages MUST NOT include exhaustive API lists or ungrounded workflow claims.
- If `launch_tier=rich`, pages MUST demonstrate grounding (claim_groups -> snippets) before expanding page count.

### Gate: Limitations honesty (new)
If ProductFacts.limitations is non-empty, then:
- docs + reference MUST include a Limitations section (or equivalent) populated only from ProductFacts.
- products MAY include a short limitations note (optional).

### Gate: Distribution correctness (new)
If ProductFacts.distribution is present, then:
- Install commands shown in products/docs MUST match distribution.install_commands exactly.
- Do not invent package names.

### Gate: “No hidden inference” (clarified)
Even when `allow_inference=true`, the system MAY only infer:
- page structure decisions (what to write), not product capabilities.
Capabilities must always be grounded in EvidenceMap or omitted.
