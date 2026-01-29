# Gates/Validators Gaps

**Audit Date**: 2026-01-27
**Auditor**: AGENT_G (Gates/Validators Auditor)
**Scope**: Validation gates and validators gap analysis

---

## Summary

**Total Gaps Identified**: 16
- **BLOCKER**: 13 (missing runtime gates)
- **WARN**: 3 (incomplete implementations)

**Impact**: Runtime validation is 87% incomplete. The launcher cannot validate generated content quality, Hugo compatibility, TruthLock compliance, or rollback metadata.

---

## G-GAP-001 | BLOCKER | Gate 2 (Markdown Lint) Not Implemented

**Gate**: Gate 2: Markdown Lint and Frontmatter Validation
**Spec Authority**: `specs/09_validation_gates.md:53-84`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:53-84):
```
### Gate 2: Markdown Lint and Frontmatter Validation

**Purpose**: Validate markdown quality and frontmatter compliance

**Validation Rules**:
1. All markdown files MUST pass markdownlint with pinned ruleset
2. No new lint errors allowed (compared to baseline if exists)
3. All required frontmatter fields MUST be present (per frontmatter_contract)
4. All frontmatter field types MUST match contract
```

Implementation status (src/launch/validators/cli.py:216-227):
```python
not_impl = [
    "frontmatter",
    "markdownlint",
    ...
]
for gate_name in not_impl:
    sev = "blocker" if profile == "prod" else "warn"
    issues.append(
        _issue(
            issue_id=f"iss_not_implemented_{gate_name}",
            gate=gate_name,
            severity=sev,
            error_code=f"GATE_NOT_IMPLEMENTED" if sev == "blocker" else None,
            message=f"Gate not implemented (no false pass: marked as FAILED per Guarantee E)",
            ...
        )
    )
```

**Impact**: Cannot enforce markdown quality or frontmatter contracts. Generated content may have:
- Broken markdown syntax
- Missing required frontmatter fields
- Type mismatches in frontmatter
- Lint errors that break Hugo rendering

**Proposed Fix**: Implement gate in `src/launch/validators/markdown_lint.py`:
1. Integrate markdownlint-cli2 or equivalent
2. Load frontmatter_contract.json from RUN_DIR/artifacts/
3. Validate all *.md files under RUN_DIR/work/site/
4. Emit GATE_MARKDOWN_LINT_ERROR and GATE_FRONTMATTER_* error codes
5. Respect profile-specific timeout (local: 60s, ci/prod: 120s)

**Related Specs**: specs/18_site_repo_layout.md (content roots), specs/02_repo_ingestion.md (frontmatter contracts)

---

## G-GAP-002 | BLOCKER | Gate 3 (Hugo Config) Not Implemented

**Gate**: Gate 3: Hugo Config Compatibility
**Spec Authority**: `specs/09_validation_gates.md:86-116`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:86-116):
```
### Gate 3: Hugo Config Compatibility

**Purpose**: Validate Hugo config coverage for planned content

**Validation Rules**:
1. All planned `(subdomain, family)` pairs MUST be enabled by Hugo configs
2. Every planned `output_path` MUST match content root contract
3. Hugo config MUST exist for all required sections
4. Content roots MUST match `site_layout.subdomain_roots` from run_config
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:220)

**Impact**: Cannot enforce Hugo config compatibility. Risks:
- Planned content without Hugo config → Hugo build fails
- Output paths mismatch content roots → broken links
- Subdomain/family pairs not enabled → 404s on deployed site

**Proposed Fix**: Implement gate in `src/launch/validators/hugo_config.py`:
1. Load page_plan.json and site_context.json from RUN_DIR/artifacts/
2. Parse Hugo config files from site repo
3. Validate all (subdomain, family) pairs have config coverage
4. Validate output_path matches content root contract
5. Emit GATE_HUGO_CONFIG_* error codes

**Related Specs**: specs/31_hugo_config_awareness.md, specs/18_site_repo_layout.md

---

## G-GAP-003 | BLOCKER | Gate 4 (Platform Layout) Runtime Validation Missing

**Gate**: Gate 4: Platform Layout Compliance
**Spec Authority**: `specs/09_validation_gates.md:118-154`
**Issue**: Runtime validation of generated content not implemented

**Evidence**:

Spec requirement (specs/09:118-154):
```
### Gate 4: Platform Layout Compliance

**Purpose**: Validate V2 platform-aware content layout compliance

**Validation Rules**:
1. When `layout_mode=v2` for a section:
   - Non-blog sections MUST contain `/{locale}/{platform}/` in output paths
   - Blog section MUST contain `/{platform}/` at correct depth
   - Products section MUST use `/{locale}/{platform}/` (NOT `/{platform}/` alone)
2. All planned writes MUST be within taskcard `allowed_paths`
3. `allowed_paths` MUST include platform-level roots for V2 sections
4. Generated content MUST NOT contain unresolved `__PLATFORM__` tokens
5. Resolved `layout_mode` per section MUST be consistent across artifacts
```

Implementation: NOT_IMPLEMENTED (cli.py does not list platform_layout in not_impl, but gate does not exist)

**Preflight Coverage**: tools/validate_platform_layout.py validates taskcards, but NOT generated content

**Impact**: Cannot enforce V2 platform layout in generated content. Risks:
- Unresolved `__PLATFORM__` tokens in content
- Output paths missing /{locale}/{platform}/ segments
- Writes outside allowed_paths
- layout_mode inconsistencies between artifacts

**Proposed Fix**: Implement runtime gate in `src/launch/validators/platform_layout.py`:
1. Load page_plan.json and patch_bundle.json
2. For each page with layout_mode=v2, validate path segments
3. Scan generated content for unresolved `__PLATFORM__` tokens
4. Validate all writes in allowed_paths
5. Emit GATE_PLATFORM_* error codes

**Related Specs**: specs/26_repo_adapters_and_variability.md, specs/18_site_repo_layout.md

---

## G-GAP-004 | BLOCKER | Gate 5 (Hugo Build) Not Implemented

**Gate**: Gate 5: Hugo Build
**Spec Authority**: `specs/09_validation_gates.md:156-186`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:156-186):
```
### Gate 5: Hugo Build

**Purpose**: Validate Hugo site builds successfully in production mode

**Validation Rules**:
1. Hugo build MUST succeed in production mode
2. Build MUST complete without errors
3. Build warnings MAY be allowed (profile-dependent)
4. Build MUST produce output in expected locations
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:221)

**Impact**: Cannot validate Hugo build succeeds. Risks:
- Content deployed that breaks Hugo build
- Template syntax errors not caught before PR
- Missing dependencies or broken shortcodes
- Build errors discovered only in CI/production

**Proposed Fix**: Implement gate in `src/launch/validators/hugo_build.py`:
1. Run `hugo --environment production` in RUN_DIR/work/site/
2. Capture stdout/stderr
3. Check exit code (must be 0)
4. Validate output directory created
5. Respect profile timeout (local: 300s, ci/prod: 600s)
6. Emit GATE_HUGO_BUILD_* error codes

**Related Specs**: specs/31_hugo_config_awareness.md, specs/19_toolchain_and_ci.md

---

## G-GAP-005 | BLOCKER | Gate 6 (Internal Links) Not Implemented

**Gate**: Gate 6: Internal Links
**Spec Authority**: `specs/09_validation_gates.md:188-218`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:188-218):
```
### Gate 6: Internal Links

**Purpose**: Validate no broken internal links or anchors

**Validation Rules**:
1. All internal markdown links MUST resolve to existing files
2. All anchor references (`#heading`) MUST resolve to existing headings
3. All cross-references between pages MUST be valid
4. No broken relative links allowed
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:222)

**Impact**: Cannot detect broken internal links before PR. Risks:
- Broken navigation between docs pages
- Invalid anchor links to non-existent headings
- 404s from cross-references
- Poor user experience on deployed site

**Proposed Fix**: Implement gate in `src/launch/validators/internal_links.py`:
1. Parse all *.md files in RUN_DIR/work/site/
2. Extract internal links (relative paths, anchors)
3. Validate link targets exist
4. Validate anchors match existing headings (after slug conversion)
5. Respect profile timeout (local: 120s, ci/prod: 180s)
6. Emit GATE_LINK_BROKEN_* error codes

**Related Specs**: specs/22_navigation_and_existing_content_update.md

---

## G-GAP-006 | BLOCKER | Gate 7 (External Links) Not Implemented

**Gate**: Gate 7: External Links
**Spec Authority**: `specs/09_validation_gates.md:220-249`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:220-249):
```
### Gate 7: External Links

**Purpose**: Validate external links are reachable (optional by config)

**Validation Rules**:
1. All external HTTP/HTTPS links SHOULD be reachable (HTTP 200-399)
2. Links to allowlisted domains always checked
3. Redirects (3xx) are acceptable
4. Rate limiting and timeouts handled gracefully
```

**Behavior by Profile** (specs/09:244-247):
- local: Skip by default (override with --check-external-links)
- ci: Run when enabled
- prod: Run all checks

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:223)

**Impact**: Cannot detect broken external links. Risks:
- Broken documentation references to upstream projects
- Dead links to GitHub issues/PRs
- 404s to external API docs
- Poor SEO from broken outbound links

**Proposed Fix**: Implement gate in `src/launch/validators/external_links.py`:
1. Parse all *.md files for external links
2. Check HTTP status codes (with timeout)
3. Handle rate limiting with exponential backoff
4. Support profile-based skipping
5. Respect profile timeout (local: 300s, ci/prod: 600s)
6. Emit GATE_LINK_EXTERNAL_* error codes

**Related Specs**: specs/34_strict_compliance_guarantees.md (Network Allowlist)

---

## G-GAP-007 | BLOCKER | Gate 8 (Snippet Checks) Not Implemented

**Gate**: Gate 8: Snippet Checks
**Spec Authority**: `specs/09_validation_gates.md:251-282`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:251-282):
```
### Gate 8: Snippet Checks

**Purpose**: Validate code snippet syntax and optionally execution

**Validation Rules**:
1. All code snippets MUST pass syntax validation for their language
2. Snippets MUST match language declared in code fence
3. Optional: Runnable snippets executed in container (ci/prod only)
4. Snippet sources MUST exist in snippet catalog
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:224)

**Impact**: Cannot validate snippet quality. Risks:
- Syntax errors in code examples
- Language mismatch (python code in bash fence)
- Broken snippets that don't execute
- Snippets not grounded in snippet_catalog.json

**Proposed Fix**: Implement gate in `src/launch/validators/snippet_checks.py`:
1. Load snippet_catalog.json from RUN_DIR/artifacts/
2. Parse code fences from all *.md files
3. Run syntax validators (python -m py_compile, shellcheck, etc.)
4. Validate language matches fence declaration
5. Check snippet sources exist in catalog
6. Optional: Execute snippets in container (ci/prod)
7. Emit GATE_SNIPPET_* error codes

**Related Specs**: specs/05_example_curation.md

---

## G-GAP-008 | BLOCKER | Gate 9 (TruthLock) Not Implemented

**Gate**: Gate 9: TruthLock
**Spec Authority**: `specs/09_validation_gates.md:284-317`
**Issue**: Spec defines gate but no validator exists — CRITICAL for evidence grounding

**Evidence**:

Spec requirement (specs/09:284-317):
```
### Gate 9: TruthLock

**Purpose**: Enforce claim stability and evidence grounding requirements

**Validation Rules**:
1. All claims in content MUST link to EvidenceMap entries
2. No uncited facts allowed (unless allow_inference=true with constraints)
3. Claim IDs MUST be stable (match truth_lock_report)
4. Evidence sources MUST be traceable to repo artifacts
5. Contradictions MUST be resolved (per priority rules)
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:225)

**Impact**: **CRITICAL** — Cannot enforce evidence grounding. Risks:
- Uncited claims in documentation (hallucinations)
- Unresolved contradictions between evidence sources
- Unstable claim IDs (breaks reproducibility)
- Evidence sources not traceable to repo
- Violations of allow_inference constraints

**Proposed Fix**: Implement gate in `src/launch/validators/truthlock.py`:
1. Load truth_lock_report.json and evidence_map.json from RUN_DIR/artifacts/
2. Parse generated content for claim markers
3. Validate all claims link to EvidenceMap entries
4. Validate claim IDs stable (match truth_lock_report)
5. Validate evidence sources exist in repo
6. Check contradictions resolved per priority rules
7. Emit GATE_TRUTHLOCK_* error codes

**Related Specs**: specs/04_claims_compiler_truth_lock.md (TruthLock rules), specs/03_product_facts_and_evidence.md

**Priority**: HIGHEST — TruthLock is core to foss-launcher's value proposition

---

## G-GAP-009 | BLOCKER | Gate 10 (Consistency) Not Implemented

**Gate**: Gate 10: Consistency
**Spec Authority**: `specs/09_validation_gates.md:319-353`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:319-353):
```
### Gate 10: Consistency

**Purpose**: Validate cross-artifact consistency and required content presence

**Validation Rules**:
1. `product_name` MUST be consistent across all artifacts and content
2. `repo_url` MUST match across ProductFacts and page frontmatter
3. Canonical URLs MUST match run_config canonical_urls
4. Required headings MUST be present (per page type)
5. Required sections MUST be present (per required_sections)
```

Implementation: NOT_IMPLEMENTED (not in cli.py not_impl list, but gate does not exist)

**Impact**: Cannot detect cross-artifact inconsistencies. Risks:
- product_name mismatches (e.g., "MyProject" vs "my-project")
- repo_url inconsistencies between artifacts
- canonical_url mismatches causing SEO issues
- Missing required headings/sections per page type

**Proposed Fix**: Implement gate in `src/launch/validators/consistency.py`:
1. Load all artifacts (product_facts.json, page_plan.json, site_context.json)
2. Validate product_name consistent across all
3. Validate repo_url matches everywhere
4. Validate canonical_urls match run_config
5. Check required headings per page type
6. Emit GATE_CONSISTENCY_* error codes

**Related Specs**: specs/03_product_facts_and_evidence.md, specs/06_page_planning.md

---

## G-GAP-010 | BLOCKER | Gate 11 (Template Token Lint) Not Implemented

**Gate**: Gate 11: Template Token Lint
**Spec Authority**: `specs/09_validation_gates.md:355-383`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:355-383):
```
### Gate 11: Template Token Lint

**Purpose**: Validate no unresolved template tokens remain in generated content

**Validation Rules**:
1. No unresolved `__UPPER_SNAKE__` tokens allowed in content
2. No unresolved `__PLATFORM__` tokens allowed
3. No unresolved `{{template_var}}` tokens allowed
4. Template tokens in code blocks are allowed (not evaluated)
```

Implementation: NOT_IMPLEMENTED (src/launch/validators/cli.py:219)

**Impact**: Cannot detect unresolved tokens. Risks:
- `__PRODUCT_NAME__` appearing in published docs
- `__PLATFORM__` tokens in V2 platform content
- `{{repo_url}}` not replaced in links
- Template syntax visible to end users

**Proposed Fix**: Implement gate in `src/launch/validators/template_token_lint.py`:
1. Parse all *.md files and *.json artifacts
2. Scan for patterns: `__[A-Z_]+__`, `{{[a-z_]+}}`
3. Exclude code blocks from scanning
4. Emit GATE_TEMPLATE_TOKEN_UNRESOLVED error for each match
5. Respect profile timeout (local: 30s, ci/prod: 60s)

**Related Specs**: specs/08_patch_engine.md (template expansion), specs/20_rulesets_and_templates_registry.md

---

## G-GAP-011 | BLOCKER | Gate 12 (Universality) Not Implemented

**Gate**: Gate 12: Universality Gates
**Spec Authority**: `specs/09_validation_gates.md:385-428`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:385-428):
```
### Gate 12: Universality Gates

**Purpose**: Validate content meets universality requirements

**Validation Rules**:

1. **Tier Compliance**:
   - If `launch_tier=minimal`: Pages MUST NOT include exhaustive API lists or ungrounded workflow claims
   - If `launch_tier=rich`: Pages MUST demonstrate grounding (claim_groups -> snippets) before expanding page count

2. **Limitations Honesty**:
   - If `ProductFacts.limitations` is non-empty: docs + reference MUST include Limitations section
   - Limitations content MUST come from ProductFacts only

3. **Distribution Correctness**:
   - If `ProductFacts.distribution` is present: Install commands MUST match `distribution.install_commands` exactly
   - No invented package names allowed

4. **No Hidden Inference**:
   - Even with `allow_inference=true`: Capabilities must be grounded in EvidenceMap
   - Only page structure decisions may be inferred, not product capabilities
```

Implementation: NOT_IMPLEMENTED (not in cli.py not_impl list, but gate does not exist)

**Impact**: Cannot enforce universality guarantees. Risks:
- Exhaustive API lists in minimal tier launches
- Missing Limitations section when required
- Invented install commands (hallucinations)
- Hidden inference of capabilities without evidence

**Proposed Fix**: Implement gate in `src/launch/validators/universality.py`:
1. Load product_facts.json, page_plan.json, run_config
2. Validate tier compliance (minimal vs rich)
3. Check Limitations section presence/content
4. Validate install commands match ProductFacts.distribution
5. Check inference constraints (capabilities grounded)
6. Emit GATE_UNIVERSALITY_* error codes

**Related Specs**: specs/03_product_facts_and_evidence.md, specs/06_page_planning.md

---

## G-GAP-012 | BLOCKER | Gate 13 (Rollback Metadata) Not Implemented

**Gate**: Gate 13: Rollback Metadata Validation (Guarantee L)
**Spec Authority**: `specs/09_validation_gates.md:430-468`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:430-468):
```
### Gate 13: Rollback Metadata Validation (Guarantee L)

**Purpose**: Validate PR artifacts include rollback metadata (prod profile only)

**Validation Rules** (only in prod profile):
1. `pr.json` MUST exist
2. `pr.json` MUST validate against `specs/schemas/pr.schema.json`
3. Required fields MUST be present: `base_ref`, `run_id`, `rollback_steps`, `affected_paths`
4. `base_ref` MUST match pattern `^[a-f0-9]{40}$` (40-char SHA)
5. `rollback_steps` array MUST have minItems: 1
6. `affected_paths` array MUST have minItems: 1
7. All paths in `affected_paths` MUST appear in PR diff
```

**Behavior by Profile**:
- prod: BLOCKER if validation fails
- ci: WARN if validation fails
- local: SKIP (not run)

Implementation: NOT_IMPLEMENTED (not in cli.py not_impl list, but gate does not exist)

**Impact**: Cannot enforce rollback contract in production. Risks:
- PRs without rollback metadata
- Invalid base_ref (not a commit SHA)
- Empty rollback_steps (cannot revert)
- Missing affected_paths (cannot assess impact)

**Proposed Fix**: Implement gate in `src/launch/validators/rollback.py`:
1. Check profile (skip if local, warn if ci, BLOCKER if prod)
2. Load pr.json from RUN_DIR/artifacts/
3. Validate against specs/schemas/pr.schema.json
4. Validate base_ref is 40-char SHA
5. Validate rollback_steps non-empty
6. Validate affected_paths non-empty
7. Emit PR_MISSING_ROLLBACK_METADATA and related error codes

**Related Specs**: specs/12_pr_and_release.md, specs/34_strict_compliance_guarantees.md (Guarantee L)

---

## G-GAP-013 | BLOCKER | Gate T (Test Determinism) Not Implemented

**Gate**: Gate T: Test Determinism Configuration (Guarantee I)
**Spec Authority**: `specs/09_validation_gates.md:471-495`
**Issue**: Spec defines gate but no validator exists

**Evidence**:

Spec requirement (specs/09:471-495):
```
### Gate T: Test Determinism Configuration (Guarantee I)

**Purpose**: Validate test configuration enforces determinism (PYTHONHASHSEED=0)

**Validation Rules**:
1. One of the following MUST be true:
   - `pyproject.toml` contains `[tool.pytest.ini_options]` with `env = ["PYTHONHASHSEED=0"]`
   - `pytest.ini` contains `[pytest]` section with `env = PYTHONHASHSEED=0`
   - All CI workflow test commands set `PYTHONHASHSEED=0` before running pytest
```

Implementation: NOT_IMPLEMENTED (not in cli.py not_impl list, but gate does not exist)

**Impact**: Cannot enforce test determinism. Risks:
- Flaky tests due to hash randomization
- Non-reproducible test failures
- Test results vary between runs
- Debugging intermittent failures difficult

**Proposed Fix**: Implement gate in `src/launch/validators/test_determinism.py`:
1. Check pyproject.toml for PYTHONHASHSEED in pytest env
2. Check pytest.ini for PYTHONHASHSEED
3. Check .github/workflows/*.yml for PYTHONHASHSEED in test commands
4. Pass if ANY of the above is true
5. Emit TEST_MISSING_PYTHONHASHSEED or TEST_DETERMINISM_NOT_ENFORCED

**Related Specs**: specs/34_strict_compliance_guarantees.md (Guarantee I)

---

## G-GAP-014 | WARN | Schema Validation Incomplete (Frontmatter Not Validated)

**Gate**: Gate 1: Schema Validation
**Spec Authority**: `specs/09_validation_gates.md:21-50`
**Issue**: Gate only validates JSON artifacts, not frontmatter

**Evidence**:

Spec requirement (specs/09:26-34):
```
**Inputs**:
- All `*.json` files under `RUN_DIR/artifacts/`
- All schemas under `specs/schemas/`
- All page frontmatter in `*.md` files under `RUN_DIR/work/site/`

**Validation Rules**:
1. All JSON artifacts MUST validate against their respective schemas
2. Schema validation MUST use JSON Schema Draft 2020-12
3. All page frontmatter MUST be valid YAML
4. If `frontmatter_contract.json` exists, all frontmatter MUST validate against it
```

Implementation (src/launch/validators/cli.py:177-211):
```python
# Gate 3: artifact schema validation for any present JSON artifacts
artifacts_dir = run_dir / "artifacts"
schema_log = run_dir / "logs" / "gate_schema_validation.log"

artifacts = sorted(p for p in artifacts_dir.glob("*.json") if p.is_file())
artifact_ok = True
errors: List[str] = []

for artifact in artifacts:
    schema_path = _infer_schema_path(repo_root, artifact)
    if not schema_path.exists():
        artifact_ok = False
        errors.append(f"No schema for {artifact.name} (expected {schema_path.name})")
        continue
    try:
        validate_json_file(artifact, schema_path)
    except Exception as e:
        artifact_ok = False
        errors.append(f"{artifact.name}: {e}")
```

**Coverage**:
- ✅ JSON artifact validation
- ❌ Frontmatter YAML validation
- ❌ Frontmatter contract validation

**Impact**: Cannot detect:
- Invalid YAML in frontmatter
- Missing required frontmatter fields
- Type mismatches in frontmatter

**Proposed Fix**: Extend cli.py Gate 1 to:
1. Glob all *.md files in RUN_DIR/work/site/
2. Parse frontmatter (YAML)
3. Validate YAML syntax
4. If frontmatter_contract.json exists, validate against it
5. Emit GATE_FRONTMATTER_* error codes

**Related Gaps**: G-GAP-001 (Gate 2 covers frontmatter validation, so overlap exists)

---

## G-GAP-015 | WARN | Profile-Specific Timeouts Not Implemented

**Gate**: All Gates
**Spec Authority**: `specs/09_validation_gates.md:511-547`
**Issue**: Timeout values hardcoded, not profile-dependent

**Evidence**:

Spec requirement (specs/09:515-542):
```
### Gate Timeouts by Profile

**local profile** (development):
- Schema validation: 30s per artifact
- Markdown lint: 60s
- Hugo config check: 10s
- Hugo build: 300s (5 minutes)
- Internal links: 120s
- ...

**ci profile** (continuous integration):
- Schema validation: 60s per artifact
- Markdown lint: 120s
- Hugo config check: 20s
- Hugo build: 600s (10 minutes)
- Internal links: 180s
- ...

**prod profile** (not typically used for gating, reference only):
- Same as CI profile but may include additional checks
```

**Timeout Behavior** (specs/09:542-547):
```
- On timeout: emit BLOCKER issue with `error_code: GATE_TIMEOUT`
- Record which gate timed out in validation_report.json
- Do NOT retry timed-out gates automatically (orchestrator decides)
- Log timeout events to telemetry with gate name and elapsed time
```

**Preflight Implementation** (tools/validate_swarm_ready.py:113):
```python
result = subprocess.run(
    [sys.executable, str(full_path)],
    cwd=str(self.repo_root),
    capture_output=True,
    text=True,
    timeout=60  # Hardcoded 60s
)
```

**Runtime Implementation** (src/launch/validators/cli.py):
- ❌ No timeout enforcement found
- ❌ No GATE_TIMEOUT error code emission
- ❌ No profile-specific timeout configuration

**Impact**:
- Gates can hang indefinitely (runtime)
- Timeout values not optimized per profile (preflight)
- No telemetry for timeout events
- Cannot distinguish timeout from other failures

**Proposed Fix**:
1. **Preflight**: Add profile parameter to validate_swarm_ready.py, use profile-specific timeouts
2. **Runtime**: Wrap gate execution in timeout handlers (signal.alarm or threading.Timer)
3. Emit GATE_TIMEOUT error code per spec
4. Log timeout events to telemetry (run_dir/telemetry_outbox.jsonl)

**Related Specs**: specs/16_local_telemetry_api.md (telemetry logging)

---

## G-GAP-016 | WARN | Gate Execution Order Not Enforced

**Gate**: All Runtime Gates
**Spec Authority**: `specs/09_validation_gates.md:598`
**Issue**: Spec defines execution order but implementation does not enforce it

**Evidence**:

Spec requirement (specs/09:598):
```
- Gate execution order is: schema → lint → hugo_config → content_layout_platform → hugo_build → links → snippets → truthlock → consistency
```

**Implementation Order** (src/launch/validators/cli.py:116-250):
1. Gate 0: run_layout
2. Gate 1: toolchain_lock
3. Gate 2: run_config_schema
4. Gate 3: artifact_schema
5. Gates (NOT_IMPLEMENTED): frontmatter, markdownlint, template_token_lint, hugo_config, hugo_build, internal_links, external_links, snippets, truthlock

**Gap**: Implementation order does not match spec order:
- Spec order: schema → lint → hugo_config → content_layout_platform → hugo_build → links → snippets → truthlock → consistency
- Implementation order: run_layout → toolchain_lock → run_config_schema → artifact_schema → (all NOT_IMPLEMENTED)

**Impact**:
- Dependency between gates not respected (e.g., hugo_config should run before hugo_build)
- Schema validation should run first (currently does, but by accident not design)
- TruthLock should run near end (after content generation validated)

**Proposed Fix**:
1. Refactor cli.py validate() to enforce spec-defined order
2. Run gates in sequence: schema → lint → hugo_config → platform_layout → hugo_build → links → snippets → truthlock → consistency
3. Short-circuit on BLOCKER issues (if profile=prod and blocker found, stop execution)
4. Document execution order in code comments

**Rationale**: Execution order matters for:
- Early failure (schema errors should fail before hugo build)
- Dependency (hugo_config must pass before hugo_build)
- Performance (cheap gates first)

---

## Gap Priority Summary

**BLOCKER Gaps** (must fix before production):
1. G-GAP-008 (TruthLock) — HIGHEST PRIORITY (core value proposition)
2. G-GAP-002 (Hugo Config) — HIGH (prevents broken builds)
3. G-GAP-004 (Hugo Build) — HIGH (validates site generation)
4. G-GAP-005 (Internal Links) — HIGH (prevents 404s)
5. G-GAP-009 (Consistency) — HIGH (prevents artifact mismatches)
6. G-GAP-010 (Template Tokens) — HIGH (prevents unresolved tokens in production)
7. G-GAP-001 (Markdown Lint) — MEDIUM (quality gates)
8. G-GAP-003 (Platform Layout Runtime) — MEDIUM (V2 compliance)
9. G-GAP-007 (Snippet Checks) — MEDIUM (code example quality)
10. G-GAP-011 (Universality) — MEDIUM (launch tier compliance)
11. G-GAP-012 (Rollback Metadata) — MEDIUM (prod profile only)
12. G-GAP-006 (External Links) — LOW (optional by profile)
13. G-GAP-013 (Test Determinism) — LOW (test infrastructure)

**WARN Gaps** (quality improvements):
1. G-GAP-015 (Timeouts) — MEDIUM (prevents hangs)
2. G-GAP-014 (Schema Frontmatter) — LOW (overlap with Gate 2)
3. G-GAP-016 (Execution Order) — LOW (optimization)

---

## Compliance Impact

**Guarantees Affected by Gaps**:
- **Guarantee A** (Pinned Refs): ✅ Preflight enforced, ⚠ Runtime check missing (should exist per specs/34:59-84)
- **Guarantee E** (No Placeholders): ⚠ Template tokens not validated at runtime (G-GAP-010)
- **Guarantee I** (Test Determinism): ❌ Gate T not implemented (G-GAP-013)
- **Guarantee L** (Rollback): ❌ Gate 13 not implemented (G-GAP-012)

**Spec Compliance**:
- specs/09_validation_gates.md: 13/15 runtime gates missing (87% gap)
- specs/34_strict_compliance_guarantees.md: 3/12 guarantees not fully enforced

**Risk Assessment**:
- **Critical Risk**: TruthLock (G-GAP-008) — Cannot validate evidence grounding
- **High Risk**: Hugo gates (G-GAP-002, G-GAP-004) — Cannot validate site builds
- **Medium Risk**: Content quality gates (G-GAP-001, G-GAP-005, G-GAP-010) — Content quality not enforced
- **Low Risk**: Optional gates (G-GAP-006, G-GAP-013) — Not blocking for basic launches

---

## Recommendations

1. **Immediate Actions** (before any production runs):
   - Implement G-GAP-008 (TruthLock) — blocking for evidence grounding
   - Implement G-GAP-002 (Hugo Config) — blocking for site generation
   - Implement G-GAP-004 (Hugo Build) — blocking for deployment readiness

2. **Short-term Actions** (before Phase 6):
   - Implement G-GAP-005 (Internal Links) — blocking for link integrity
   - Implement G-GAP-009 (Consistency) — blocking for artifact consistency
   - Implement G-GAP-010 (Template Tokens) — blocking for clean content
   - Fix G-GAP-015 (Timeouts) — blocking for robustness

3. **Medium-term Actions** (Phase 6-7):
   - Implement remaining content quality gates (G-GAP-001, G-GAP-003, G-GAP-007, G-GAP-011)
   - Implement G-GAP-012 (Rollback) — blocking for prod profile
   - Fix G-GAP-014, G-GAP-016 (quality improvements)

4. **Long-term Actions** (post-launch):
   - Implement G-GAP-006 (External Links) — optional by profile
   - Implement G-GAP-013 (Test Determinism) — test infrastructure improvement

---

## Evidence Summary

All gaps documented with:
- ✅ Spec authority (specs/09:line-range)
- ✅ Implementation evidence (path:line or "NOT_IMPLEMENTED")
- ✅ Impact assessment
- ✅ Proposed fix with specific implementation guidance
- ✅ Related specs cross-referenced
