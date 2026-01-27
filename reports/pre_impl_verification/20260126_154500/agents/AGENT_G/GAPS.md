# Gates/Validators Enforcement Gaps

## Format
```
G-GAP-NNN | SEVERITY | description | evidence | proposed fix
```

---

## BLOCKER Gaps (Stop-the-Line)

### G-GAP-005 | BLOCKER | Hugo build gate (Gate 5) validator missing
**Description:** specs/09_validation_gates.md:45-48 requires Hugo build validation, but no validator exists

**Evidence:**
- **Spec:** specs/09_validation_gates.md:45-48
  ```
  5) Hugo build
  - run hugo build in production mode.
  - build must succeed.
  ```
- **Validator:** src/launch/validators/cli.py:221
  ```python
  # Gate marked NOT_IMPLEMENTED
  not_impl = ["frontmatter", "markdownlint", "template_token_lint", "hugo_config",
              "hugo_build", "internal_links", "external_links", "snippets", "truthlock"]
  ```
- **Gap:** No validator file found in tools/ or src/launch/validators/ that invokes Hugo

**Impact:**
- Hugo build failures will not be detected until PR review or production deployment
- Invalid Hugo syntax (e.g., malformed shortcodes) will not be caught
- Missing required sections in Hugo config will not be detected

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/hugo_build.py`
   - Entry point: `python -m launch.validators.hugo_build <run_dir>`
   - Invokes: `hugo build --environment production --source <RUN_DIR/work/site/>`
   - Exit codes: 0 if build succeeds, 2 if build fails
   - Output: Creates gate log at `<run_dir>/logs/gate_hugo_build.log`
   - Issue on failure: `issue_id=hugo_build_failed, error_code=GATE_HUGO_BUILD_FAILED`

2. **Integration:** Update src/launch/validators/cli.py:221
   ```python
   # Replace NOT_IMPLEMENTED stub with actual validator call
   from ..validators.hugo_build import validate_hugo_build
   hugo_ok = validate_hugo_build(run_dir, profile)
   gates.append({"name": "hugo_build", "ok": hugo_ok, "log_path": ...})
   ```

3. **Determinism:**
   - Pin Hugo version in config/toolchain.lock.yaml
   - Use --environment flag (not default, which may vary)
   - Hugo output is deterministic with same content + config

4. **Profile behavior:**
   - local/ci/prod: Always run (Hugo build is critical gate)
   - Timeout: local=300s, ci=600s (per specs/09_validation_gates.md:94,105)

**Acceptance Criteria:**
- [ ] Hugo build validator exists at src/launch/validators/hugo_build.py
- [ ] Validator integrated into launch_validate (cli.py line 221)
- [ ] Validator uses correct exit codes (0/2 per specs/01_system_contract.md:143)
- [ ] Validator outputs deterministic gate log (same build → same log)
- [ ] Validator enforces timeout per profile (specs/09_validation_gates.md:94,105)
- [ ] Tests exist at tests/unit/validators/test_hugo_build.py
- [ ] Documented in docs/cli_usage.md

---

### G-GAP-006 | BLOCKER | TruthLock gate (Gate 9) validator missing
**Description:** specs/09_validation_gates.md:63-65 requires TruthLock enforcement, but no validator exists

**Evidence:**
- **Spec:** specs/09_validation_gates.md:63-65
  ```
  9) TruthLock
  - enforce 04_claims_compiler_truth_lock.md rules.
  ```
- **TruthLock rules:** specs/04_claims_compiler_truth_lock.md:32-51
  - All factual claims MUST map to claim IDs and evidence anchors
  - Claim markers `[claim:claim_id]` must have corresponding evidence_id in EvidenceMap
  - No uncited claims allowed
- **Validator:** src/launch/validators/cli.py:225 - marked NOT_IMPLEMENTED
- **Gap:** No validator file found that checks TruthLock rules

**Impact:**
- Uncited claims in generated content will not be detected
- Broken claim → evidence linkage will not be caught
- False/ungrounded statements may reach production

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/truthlock.py`
   - Entry point: `python -m launch.validators.truthlock <run_dir>`
   - Inputs:
     - `<run_dir>/artifacts/evidence_map.json` - claim → evidence mapping
     - `<run_dir>/artifacts/truth_lock_report.json` - TruthLock report from W2
     - `<run_dir>/work/site/**/*.md` - generated pages
   - Validation steps:
     1. Parse all generated markdown files
     2. Extract all `[claim:claim_id]` markers
     3. Verify each claim_id exists in evidence_map.json
     4. Verify each claim has evidence_id linkage
     5. Check for factual statements without claim markers (heuristic: product capability assertions)
   - Exit codes: 0 if all claims cited, 2 if uncited claims found
   - Output: Creates gate log + issues in validation_report.json

2. **Integration:** Update src/launch/validators/cli.py:225
   ```python
   from ..validators.truthlock import validate_truthlock
   truthlock_ok = validate_truthlock(run_dir, profile)
   gates.append({"name": "truthlock", "ok": truthlock_ok, "log_path": ...})
   ```

3. **Issue format:**
   ```json
   {
     "issue_id": "truthlock_uncited_claim_<hash>",
     "gate": "truthlock",
     "severity": "blocker",
     "error_code": "VALIDATOR_TRUTHLOCK_VIOLATION",
     "message": "Uncited claim detected: <claim_text>",
     "location": {"path": "content/en/products/...", "line": 42},
     "suggested_fix": "Add [claim:claim_id] marker or remove ungrounded statement"
   }
   ```

4. **Determinism:**
   - Parse markdown in deterministic order (sorted by path)
   - Derive issue_id from sha256(gate + location + claim_text)
   - Sort issues per specs/10_determinism_and_caching.md:44

5. **Profile behavior:**
   - local: Run (fast, critical for quality)
   - ci: Run (required)
   - prod: Run (blocker if any violations)
   - Timeout: local=60s, ci=120s (per specs/09_validation_gates.md:98,109)

**Acceptance Criteria:**
- [ ] TruthLock validator exists at src/launch/validators/truthlock.py
- [ ] Validator checks claim markers against evidence_map.json
- [ ] Validator detects uncited claims (heuristic or strict)
- [ ] Validator integrated into launch_validate (cli.py line 225)
- [ ] Issues use error_code=VALIDATOR_TRUTHLOCK_VIOLATION
- [ ] Deterministic output (sorted issues, stable issue_ids)
- [ ] Tests exist at tests/unit/validators/test_truthlock.py
- [ ] Documented in docs/cli_usage.md

---

### G-GAP-007 | BLOCKER | Internal links gate (Gate 6) runtime validator missing
**Description:** specs/09_validation_gates.md:49-52 requires internal link validation, but runtime validator for generated content is missing

**Evidence:**
- **Spec:** specs/09_validation_gates.md:49-52
  ```
  6) Internal links
  - check internal links and anchors.
  - no broken internal links.
  ```
- **Preflight validator:** tools/check_markdown_links.py:1-163
  - Checks spec/ and plan/ markdown links ✅
  - Does NOT check generated content in RUN_DIR/work/site/ ❌
- **Runtime validator:** src/launch/validators/cli.py:222 - marked NOT_IMPLEMENTED
- **Gap:** No validator checks internal links in generated content

**Impact:**
- Broken internal links in generated pages (e.g., [](../docs/getting-started.md) pointing to non-existent file)
- Broken anchor links (e.g., [](#section-that-does-not-exist))
- Users will encounter 404 errors

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/internal_links.py`
   - Entry point: `python -m launch.validators.internal_links <run_dir>`
   - Inputs: `<run_dir>/work/site/**/*.md` (generated pages)
   - Validation steps:
     1. Parse all markdown files
     2. Extract all internal links: `[text] (path)`, `[text] (path#anchor)`, `[text] (#anchor)`
     3. Resolve relative paths against current file location
     4. Verify target file exists in work/site/
     5. If anchor specified, verify anchor exists in target file (check for `## Heading` or `{#anchor}`)
     6. Report broken links as BLOCKER issues
   - Exit codes: 0 if all links valid, 2 if broken links found
   - Output: Creates gate log + issues in validation_report.json

2. **Integration:** Update src/launch/validators/cli.py:222
   ```python
   from ..validators.internal_links import validate_internal_links
   links_ok = validate_internal_links(run_dir, profile)
   gates.append({"name": "internal_links", "ok": links_ok, "log_path": ...})
   ```

3. **Issue format:**
   ```json
   {
     "issue_id": "internal_link_broken_<hash>",
     "gate": "internal_links",
     "severity": "blocker",
     "error_code": "GATE_INTERNAL_LINK_BROKEN",
     "message": "Broken internal link: [text] (path) - target does not exist",
     "location": {"path": "content/en/products/...", "line": 42},
     "suggested_fix": "Fix link path or create missing target file"
   }
   ```

4. **Determinism:**
   - Process files in sorted order (lexicographic by path)
   - Derive issue_id from sha256(gate + source_path + line + target_path)
   - Sort issues per specs/10_determinism_and_caching.md:44

5. **Profile behavior:**
   - local/ci/prod: Always run (critical gate)
   - Timeout: local=120s, ci=180s (per specs/09_validation_gates.md:95,106)

**Acceptance Criteria:**
- [ ] Internal links validator exists at src/launch/validators/internal_links.py
- [ ] Validator checks all markdown links in RUN_DIR/work/site/
- [ ] Validator verifies anchor existence (heading or {#id})
- [ ] Validator integrated into launch_validate (cli.py line 222)
- [ ] Issues use error_code=GATE_INTERNAL_LINK_BROKEN
- [ ] Deterministic output (sorted issues, stable issue_ids)
- [ ] Tests exist at tests/unit/validators/test_internal_links.py
- [ ] Documented in docs/cli_usage.md

---

### G-GAP-008 | BLOCKER | Hugo config compatibility gate (Gate 3) validator missing
**Description:** specs/09_validation_gates.md:28-32 requires Hugo config validation, but no validator exists

**Evidence:**
- **Spec:** specs/09_validation_gates.md:28-32
  ```
  3) Hugo config compatibility (`hugo_config`)
  - Ensure the planned `(subdomain, family)` pairs are enabled by Hugo configs
  - Ensure every planned `output_path` matches the content root contract
  - Fail fast with blocker issue `HugoConfigMissing` when configs do not cover required sections.
  ```
- **Related spec:** specs/31_hugo_config_awareness.md (Hugo config awareness)
- **Validator:** src/launch/validators/cli.py:220 - marked NOT_IMPLEMENTED
- **Gap:** No validator checks run_config against Hugo configs

**Impact:**
- Mismatched Hugo config will cause Hugo build failures (detected late)
- Invalid (subdomain, family) pairs will not be caught
- Output paths incompatible with Hugo config will not be detected

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/hugo_config.py`
   - Entry point: `python -m launch.validators.hugo_config <run_dir>`
   - Inputs:
     - `<run_dir>/run_config.yaml` - planned sections and output_paths
     - `<run_dir>/work/site/config/_default/config.toml` (or .yaml) - Hugo config
     - `<run_dir>/artifacts/site_context.json` - Hugo build matrix
   - Validation steps:
     1. Parse Hugo config files
     2. Extract enabled sections (e.g., content/en/products/, content/en/docs/)
     3. Compare planned output_paths from run_config against Hugo sections
     4. Verify (subdomain, family) pairs are covered
     5. Check content root contract per specs/18_site_repo_layout.md
   - Exit codes: 0 if compatible, 2 if mismatched
   - Output: Creates gate log + blocker issue HugoConfigMissing if needed

2. **Integration:** Update src/launch/validators/cli.py:220
   ```python
   from ..validators.hugo_config import validate_hugo_config
   hugo_cfg_ok = validate_hugo_config(run_dir, profile)
   gates.append({"name": "hugo_config", "ok": hugo_cfg_ok, "log_path": ...})
   ```

3. **Issue format:**
   ```json
   {
     "issue_id": "hugo_config_missing",
     "gate": "hugo_config",
     "severity": "blocker",
     "error_code": "GATE_HUGO_CONFIG_MISSING",
     "message": "Hugo config does not cover required section: products/en/aspose-3d-python",
     "suggested_fix": "Update Hugo config to enable section or adjust run_config.allowed_paths"
   }
   ```

4. **Determinism:**
   - Hugo config parsing is deterministic (same config → same result)
   - Single issue per missing section (stable issue_id)

5. **Profile behavior:**
   - local/ci/prod: Always run (prevents Hugo build failures)
   - Timeout: local=10s, ci=20s (per specs/09_validation_gates.md:93,104)

**Acceptance Criteria:**
- [ ] Hugo config validator exists at src/launch/validators/hugo_config.py
- [ ] Validator parses Hugo config (TOML/YAML)
- [ ] Validator checks planned output_paths against enabled sections
- [ ] Validator emits HugoConfigMissing issue when sections not covered
- [ ] Validator integrated into launch_validate (cli.py line 220)
- [ ] Tests exist at tests/unit/validators/test_hugo_config.py
- [ ] Documented in docs/cli_usage.md

---

### G-GAP-009 | BLOCKER | Snippets syntax validation gate (Gate 8) missing
**Description:** specs/09_validation_gates.md:57-62 requires snippet syntax checks, but no validator exists

**Evidence:**
- **Spec:** specs/09_validation_gates.md:57-62
  ```
  8) Snippet checks
  Minimum:
  - syntax check for each snippet
  Optional:
  - run snippets in container for supported languages
  ```
- **Validator:** src/launch/validators/cli.py:224 - marked NOT_IMPLEMENTED
- **Gap:** No validator checks snippet syntax

**Impact:**
- Invalid code snippets in generated pages (e.g., Python syntax errors)
- Users will copy-paste broken code
- Documentation quality suffers

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/snippets.py`
   - Entry point: `python -m launch.validators.snippets <run_dir>`
   - Inputs:
     - `<run_dir>/artifacts/snippet_catalog.json` - snippet inventory
     - `<run_dir>/work/site/**/*.md` - generated pages with code blocks
   - Validation steps:
     1. Parse snippet_catalog.json
     2. For each snippet:
        - Extract language (e.g., python, java, typescript)
        - Write snippet to temp file
        - Run syntax checker for that language:
          - Python: `python -m py_compile <file>`
          - Java: `javac <file>` (or skip if no JDK)
          - TypeScript: `tsc --noEmit <file>` (or skip if no tsc)
          - JavaScript: `node --check <file>`
        - Report syntax errors as issues
     3. Profile behavior:
        - local: Syntax check only (fast)
        - ci/prod: Syntax check (container execution is optional per spec)
   - Exit codes: 0 if all valid, 2 if syntax errors
   - Output: Creates gate log + issues in validation_report.json

2. **Integration:** Update src/launch/validators/cli.py:224
   ```python
   from ..validators.snippets import validate_snippets
   snippets_ok = validate_snippets(run_dir, profile)
   gates.append({"name": "snippets", "ok": snippets_ok, "log_path": ...})
   ```

3. **Issue format:**
   ```json
   {
     "issue_id": "snippet_syntax_error_<hash>",
     "gate": "snippets",
     "severity": "error",
     "error_code": "GATE_SNIPPET_SYNTAX_ERROR",
     "message": "Snippet syntax error (python): SyntaxError: invalid syntax",
     "location": {"path": "content/en/docs/getting-started.md", "line": 42},
     "suggested_fix": "Fix snippet syntax or remove snippet"
   }
   ```

4. **Determinism:**
   - Process snippets in sorted order (by snippet_id from catalog)
   - Syntax checker output is deterministic (same code → same error)
   - Derive issue_id from sha256(gate + snippet_id + error_message)

5. **Profile behavior:**
   - local/ci/prod: Run syntax checks (fast, critical for quality)
   - Timeout: local=60s, ci=120s (per specs/09_validation_gates.md:97,108)
   - Container execution: Optional (defer to future enhancement)

**Acceptance Criteria:**
- [ ] Snippets validator exists at src/launch/validators/snippets.py
- [ ] Validator checks syntax for Python, Java, TypeScript, JavaScript
- [ ] Validator skips languages without available syntax checkers (emits warning)
- [ ] Validator integrated into launch_validate (cli.py line 224)
- [ ] Issues use error_code=GATE_SNIPPET_SYNTAX_ERROR
- [ ] Tests exist at tests/unit/validators/test_snippets.py
- [ ] Documented in docs/cli_usage.md

---

## MAJOR Gaps (Quality & Consistency)

### G-GAP-001 | MAJOR | Exit code semantics inconsistent across validators
**Description:** Validators use inconsistent exit codes; preflight uses 0/1, runtime uses 0/2, but spec defines 5 distinct codes

**Evidence:**
- **Spec:** specs/01_system_contract.md:141-146
  ```
  - 0: success
  - 2: validation/spec/schema failure
  - 3: policy violation (allowed_paths, governance)
  - 4: external dependency failure (commit service, telemetry API)
  - 5: unexpected internal error
  ```
- **Preflight validators:** All tools/*.py use exit 0/1
  - validate_pinned_refs.py:194,207: `return 0` or `return 1`
  - validate_supply_chain_pinning.py:133,141: `return 0` or `return 1`
  - All other tools/ follow same pattern
- **Runtime validator:** src/launch/validators/cli.py:265-268
  ```python
  if ok:
      raise typer.Exit(0)
  raise typer.Exit(2)
  ```
- **Gap:** Exit 1 is not defined in spec; exit 3/4/5 are not used

**Impact:**
- External systems cannot distinguish failure types (e.g., policy vs schema vs external dependency)
- Scripts that check exit codes must handle non-standard exit 1
- Inconsistent behavior between preflight and runtime

**Proposed Fix:**
1. **Standardize all validators to use spec-defined exit codes:**
   - Exit 0: success
   - Exit 2: validation/schema failure (malformed JSON, schema mismatch)
   - Exit 3: policy violation (pinned refs floating, placeholders in production, allowed_paths escape)
   - Exit 4: external dependency failure (Hugo not found, network unreachable)
   - Exit 5: unexpected internal error (Python exception, file not found when it should exist)

2. **Update preflight validators (tools/*.py):**
   - Policy gates (J, K, M, N, P, Q, R): Exit 3 for policy violations
   - Schema gates (A1, B): Exit 2 for validation failures
   - Tooling gates (0, C, D, E, F): Exit 2 for validation failures or exit 4 if tool missing
   - Example: tools/validate_pinned_refs.py:207
     ```python
     # OLD: return 1
     # NEW: return 3  # Policy violation (floating refs not allowed in prod)
     ```

3. **Update runtime validator (src/launch/validators/cli.py):**
   ```python
   # Classify failure type
   if any(iss["error_code"].startswith("POLICY_") for iss in issues):
       raise typer.Exit(3)  # Policy violation
   elif any(iss["error_code"].startswith("SCHEMA_") for iss in issues):
       raise typer.Exit(2)  # Validation failure
   elif any(iss["error_code"].startswith("GATE_TIMEOUT") for iss in issues):
       raise typer.Exit(4)  # External dependency (tool timeout)
   else:
       raise typer.Exit(2)  # Default: validation failure
   ```

4. **Update validate_swarm_ready.py:**
   - Aggregate exit codes from individual gates
   - Return highest severity exit code (3 > 2 > 0)

5. **Update documentation:**
   - docs/cli_usage.md:220-228 - Document exit codes for all validators
   - Add examples of how to interpret exit codes in CI scripts

**Acceptance Criteria:**
- [ ] All preflight validators use exit 2 for schema failures, exit 3 for policy violations
- [ ] Runtime validator classifies issues by error_code and uses appropriate exit code
- [ ] validate_swarm_ready.py aggregates exit codes (returns highest severity)
- [ ] docs/cli_usage.md documents exit codes for all validators
- [ ] Tests verify correct exit codes for each failure type
- [ ] CI workflows updated to interpret exit codes correctly

---

### G-GAP-002 | MAJOR | Issue ordering not implemented per determinism spec
**Description:** validation_report.json issues are not sorted, violating determinism requirement

**Evidence:**
- **Spec:** specs/10_determinism_and_caching.md:44-48
  ```
  issues by (severity_rank, gate, location.path, location.line, issue_id)
  Severity rank (binding): blocker > error > warn > info
  ```
- **Implementation:** src/launch/validators/cli.py:252-261
  ```python
  report = {
      "schema_version": "1.0",
      "ok": ok,
      "profile": profile,
      "gates": gates,
      "issues": issues,  # NOT SORTED
  }
  atomic_write_json(artifacts_dir / "validation_report.json", report)
  ```
- **Gap:** Issues are written in code order (not sorted by severity/gate/location)

**Impact:**
- validation_report.json is not byte-identical across runs (order varies)
- Determinism guarantee violated
- Cannot cache validation results reliably

**Proposed Fix:**
1. **Add issue sorting function:**
   ```python
   def _sort_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
       """Sort issues per specs/10_determinism_and_caching.md:44."""
       severity_order = {"blocker": 0, "error": 1, "warn": 2, "info": 3}

       def sort_key(issue):
           severity_rank = severity_order.get(issue["severity"], 99)
           gate = issue.get("gate", "")
           location = issue.get("location", {})
           path = location.get("path", "")
           line = location.get("line", 0)
           issue_id = issue.get("issue_id", "")
           return (severity_rank, gate, path, line, issue_id)

       return sorted(issues, key=sort_key)
   ```

2. **Update src/launch/validators/cli.py:252-261:**
   ```python
   # Sort issues before writing report
   sorted_issues = _sort_issues(issues)

   report = {
       "schema_version": "1.0",
       "ok": ok,
       "profile": profile,
       "gates": gates,
       "issues": sorted_issues,  # NOW SORTED
   }
   atomic_write_json(artifacts_dir / "validation_report.json", report)
   ```

3. **Add test:**
   ```python
   def test_validation_report_deterministic_issue_order():
       """Issues are sorted by severity > gate > location > issue_id."""
       issues = [
           {"issue_id": "iss_2", "gate": "g1", "severity": "warn", "location": {"path": "a", "line": 1}},
           {"issue_id": "iss_1", "gate": "g1", "severity": "blocker", "location": {"path": "a", "line": 1}},
           {"issue_id": "iss_3", "gate": "g2", "severity": "blocker", "location": {"path": "b", "line": 2}},
       ]
       sorted_issues = _sort_issues(issues)
       assert sorted_issues[0]["issue_id"] == "iss_1"  # blocker, g1, a:1
       assert sorted_issues[1]["issue_id"] == "iss_3"  # blocker, g2, b:2
       assert sorted_issues[2]["issue_id"] == "iss_2"  # warn, g1, a:1
   ```

**Acceptance Criteria:**
- [ ] Issue sorting function added to src/launch/validators/cli.py
- [ ] validation_report.json issues are sorted per specs/10_determinism_and_caching.md:44
- [ ] Tests verify deterministic issue order
- [ ] Same inputs → same validation_report.json (byte-identical)

---

### G-GAP-003 | MAJOR | No evidence of timestamp control per determinism spec
**Description:** Determinism spec requires controlled timestamps, but no evidence validators implement this

**Evidence:**
- **Spec:** specs/10_determinism_and_caching.md:51-52
  ```
  Repeat run with the same inputs produces byte-identical artifacts.
  The only allowed run-to-run variance is inside the local event stream (events.ndjson)
  where ts/event_id values differ.
  ```
- **Implication:** Logs and reports must NOT include wall-clock timestamps
- **Gap:** No inspection of gate logs performed; no evidence that validators use run_start_time

**Impact:**
- Unknown - logs may include timestamps, preventing byte-identical outputs
- Cannot verify determinism guarantee without inspecting log files

**Proposed Fix:**
1. **Audit gate log outputs:**
   - Inspect logs/ directory after running launch_validate
   - Check for timestamp patterns (ISO8601, epoch, etc.)
   - Identify which gates write timestamps

2. **If timestamps found:**
   - Update validators to use run_start_time from context (not datetime.now())
   - Pass run_start_time to all validators via CLI argument or environment variable
   - Format timestamps as relative to run start (e.g., "+5s" instead of "2026-01-27T15:45:33Z")

3. **Example fix for gate log:**
   ```python
   # OLD: atomic_write_text(log_path, f"{datetime.now()} - Gate OK\n")
   # NEW: atomic_write_text(log_path, f"Gate OK\n")  # No timestamp
   # OR:  atomic_write_text(log_path, f"[+{elapsed_s}s] Gate OK\n")  # Relative to run start
   ```

4. **Add determinism test:**
   ```python
   def test_validation_outputs_byte_identical():
       """Run validation twice with same inputs, outputs must be byte-identical."""
       run_validate(run_dir, profile="local")
       report1 = read_json(run_dir / "artifacts/validation_report.json")
       logs1 = read_all_logs(run_dir / "logs")

       run_validate(run_dir, profile="local")
       report2 = read_json(run_dir / "artifacts/validation_report.json")
       logs2 = read_all_logs(run_dir / "logs")

       assert report1 == report2  # Byte-identical JSON
       assert logs1 == logs2      # Byte-identical logs
   ```

**Acceptance Criteria:**
- [ ] Audit performed: all gate logs inspected for timestamps
- [ ] If timestamps found: updated to use run_start_time or removed
- [ ] Test added: validation outputs are byte-identical across runs
- [ ] Documentation updated: explain timestamp control in determinism guide

---

### G-GAP-004 | MAJOR | Issue IDs not derived from content hash
**Description:** Issue IDs are hardcoded strings, not algorithmically derived from (gate, location, issue_type)

**Evidence:**
- **Spec:** specs/10_determinism_and_caching.md:44 (implied requirement for stable IDs)
- **Implementation:** src/launch/validators/cli.py:122,145,165,200,233
  ```python
  issue_id="iss_missing_paths"      # Hardcoded
  issue_id="iss_toolchain_lock"     # Hardcoded
  issue_id="iss_run_config"         # Hardcoded
  issue_id="iss_artifact_schemas"   # Hardcoded
  issue_id=f"iss_not_implemented_{gate_name}"  # Template, but not hashed
  ```
- **Gap:** IDs are stable, but not algorithmically derived (harder to maintain across validators)

**Impact:**
- Minor - IDs are stable, but manual management required
- Risk of ID collisions if multiple validators use same hardcoded ID
- Harder to ensure uniqueness across all validators

**Proposed Fix:**
1. **Create issue ID derivation utility:**
   ```python
   # src/launch/util/issue_id.py
   import hashlib
   from typing import Optional

   def derive_issue_id(
       gate: str,
       issue_type: str,
       location_path: Optional[str] = None,
       location_line: Optional[int] = None
   ) -> str:
       """Derive stable issue ID from (gate, issue_type, location)."""
       components = [gate, issue_type]
       if location_path:
           components.append(location_path)
       if location_line:
           components.append(str(location_line))

       content = "|".join(components)
       hash_hex = hashlib.sha256(content.encode()).hexdigest()[:12]
       return f"iss_{gate}_{issue_type}_{hash_hex}"
   ```

2. **Update src/launch/validators/cli.py:**
   ```python
   from ..util.issue_id import derive_issue_id

   # OLD: issue_id="iss_missing_paths"
   # NEW:
   issue_id = derive_issue_id(
       gate="run_layout",
       issue_type="missing_paths"
   )
   ```

3. **Update all validators to use derive_issue_id:**
   - src/launch/validators/cli.py (4 instances)
   - All new validators (Hugo build, TruthLock, internal links, etc.)

4. **Add test:**
   ```python
   def test_issue_id_derivation_stable():
       """Same inputs produce same issue ID."""
       id1 = derive_issue_id("hugo_build", "build_failed", "content/en/products/page.md", 42)
       id2 = derive_issue_id("hugo_build", "build_failed", "content/en/products/page.md", 42)
       assert id1 == id2

   def test_issue_id_derivation_unique():
       """Different inputs produce different issue IDs."""
       id1 = derive_issue_id("hugo_build", "build_failed", "page1.md", 10)
       id2 = derive_issue_id("hugo_build", "build_failed", "page2.md", 10)
       assert id1 != id2
   ```

**Acceptance Criteria:**
- [ ] issue_id derivation utility created at src/launch/util/issue_id.py
- [ ] All validators use derive_issue_id instead of hardcoded IDs
- [ ] Tests verify stability and uniqueness
- [ ] No ID collisions (run full validation suite, check for duplicate issue_ids)

---

### G-GAP-010 | MAJOR | External links gate (Gate 7) validator missing
**Description:** specs/09_validation_gates.md:53-56 requires external link validation (lychee), but no validator exists

**Evidence:**
- **Spec:** specs/09_validation_gates.md:53-56
  ```
  7) External links (optional by config)
  - lychee or equivalent.
  - allowlist domains if needed.
  ```
- **Profile behavior:** specs/09_validation_gates.md:137-138
  ```
  local: Skip external link checks by default (override with --check-external-links)
  ci: Run all gates including external links (if configured)
  ```
- **Validator:** src/launch/validators/cli.py:223 - marked NOT_IMPLEMENTED
- **Gap:** No validator checks external links

**Impact:**
- Broken external links in generated pages (e.g., https://github.com/nonexistent/repo)
- Users will encounter 404 errors
- Acceptable in local profile (slow), required in ci/prod

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/external_links.py`
   - Entry point: `python -m launch.validators.external_links <run_dir> --profile <profile>`
   - Tool: Use lychee (https://github.com/lycheeverse/lychee) or Python equivalent
   - Inputs: `<run_dir>/work/site/**/*.md` (generated pages)
   - Profile behavior:
     - local: Skip by default (unless --check-external-links flag passed)
     - ci/prod: Run if configured in run_config (run_config.validation.check_external_links=true)
   - Validation steps:
     1. Extract all external links: `[text](https://...)`, `<https://...>`
     2. Check domain allowlist (if config/network_allowlist.yaml exists)
     3. Send HEAD request to each link (timeout: 5s)
     4. Report broken links (4xx, 5xx status) as issues
   - Exit codes: 0 if all links valid, 2 if broken links found
   - Output: Creates gate log + issues in validation_report.json

2. **Integration:** Update src/launch/validators/cli.py:223
   ```python
   # Check profile to determine if external links should be checked
   check_external = (
       profile in ("ci", "prod") or
       os.environ.get("CHECK_EXTERNAL_LINKS") == "true"
   )
   if check_external:
       from ..validators.external_links import validate_external_links
       ext_links_ok = validate_external_links(run_dir, profile)
       gates.append({"name": "external_links", "ok": ext_links_ok, "log_path": ...})
   else:
       # Skip in local profile
       gates.append({"name": "external_links", "ok": True, "log_path": "skipped (local profile)"})
   ```

3. **Issue format:**
   ```json
   {
     "issue_id": "external_link_broken_<hash>",
     "gate": "external_links",
     "severity": "warn",
     "error_code": "GATE_EXTERNAL_LINK_BROKEN",
     "message": "Broken external link: https://example.com/nonexistent (404 Not Found)",
     "location": {"path": "content/en/products/...", "line": 42},
     "suggested_fix": "Fix link URL or remove link"
   }
   ```

4. **Determinism:**
   - External link checks are NOT deterministic (sites may go down)
   - Use severity="warn" (not "blocker") to avoid flaky failures
   - Cache results per run (same run → same results)

5. **Profile behavior:**
   - local: Skip (slow, flaky)
   - ci: Run (if configured)
   - prod: Run (required)
   - Timeout: ci=300s, prod=600s (per specs/09_validation_gates.md:106,107)

**Acceptance Criteria:**
- [ ] External links validator exists at src/launch/validators/external_links.py
- [ ] Validator uses lychee or Python HTTP client
- [ ] Validator skipped in local profile (unless --check-external-links flag)
- [ ] Validator checks domain allowlist (if config/network_allowlist.yaml exists)
- [ ] Validator integrated into launch_validate (cli.py line 223)
- [ ] Issues use severity="warn" (not blocker, due to flakiness)
- [ ] Tests exist at tests/unit/validators/test_external_links.py
- [ ] Documented in docs/cli_usage.md

---

### G-GAP-011 | MAJOR | Frontmatter validation gate missing
**Description:** specs/09_validation_gates.md:22 requires frontmatter validation, but no validator exists

**Evidence:**
- **Spec:** specs/09_validation_gates.md:22
  ```
  Validate page frontmatter against frontmatter rules or schema where available.
  ```
- **Validator:** src/launch/validators/cli.py:217 - marked NOT_IMPLEMENTED
- **Gap:** No validator checks frontmatter in generated pages

**Impact:**
- Invalid frontmatter in generated pages (e.g., missing required fields like title, date)
- Hugo may fail to render pages (detected late in Hugo build gate)

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/frontmatter.py`
   - Entry point: `python -m launch.validators.frontmatter <run_dir>`
   - Inputs:
     - `<run_dir>/artifacts/frontmatter_contract.json` - frontmatter schema
     - `<run_dir>/work/site/**/*.md` - generated pages
   - Validation steps:
     1. Parse frontmatter_contract.json (section-specific requirements)
     2. Parse each generated markdown file
     3. Extract YAML frontmatter (between `---` delimiters)
     4. Validate frontmatter against contract:
        - Required fields present (e.g., title, date, section)
        - Field types correct (e.g., date is ISO8601, tags is array)
        - Enum values valid (e.g., section in [products, docs, kb, reference, blog])
     5. Report validation errors as issues
   - Exit codes: 0 if all valid, 2 if invalid frontmatter
   - Output: Creates gate log + issues in validation_report.json

2. **Integration:** Update src/launch/validators/cli.py:217
   ```python
   from ..validators.frontmatter import validate_frontmatter
   frontmatter_ok = validate_frontmatter(run_dir, profile)
   gates.append({"name": "frontmatter", "ok": frontmatter_ok, "log_path": ...})
   ```

3. **Issue format:**
   ```json
   {
     "issue_id": "frontmatter_invalid_<hash>",
     "gate": "frontmatter",
     "severity": "error",
     "error_code": "GATE_FRONTMATTER_INVALID",
     "message": "Frontmatter validation failed: missing required field 'title'",
     "location": {"path": "content/en/products/...", "line": 1},
     "suggested_fix": "Add required frontmatter field 'title'"
   }
   ```

4. **Determinism:**
   - Process files in sorted order
   - Derive issue_id from sha256(gate + path + field_name)

5. **Profile behavior:**
   - local/ci/prod: Always run (fast, critical for Hugo build)
   - Timeout: local=30s, ci=60s (per specs/09_validation_gates.md:91,102)

**Acceptance Criteria:**
- [ ] Frontmatter validator exists at src/launch/validators/frontmatter.py
- [ ] Validator checks frontmatter against frontmatter_contract.json
- [ ] Validator reports missing required fields, invalid types, invalid enum values
- [ ] Validator integrated into launch_validate (cli.py line 217)
- [ ] Tests exist at tests/unit/validators/test_frontmatter.py
- [ ] Documented in docs/cli_usage.md

---

## MINOR Gaps (Style & Documentation)

### G-GAP-012 | MINOR | Markdownlint gate missing
**Description:** specs/09_validation_gates.md:24-27 requires markdownlint, but no validator exists

**Evidence:**
- **Spec:** specs/09_validation_gates.md:24-27
  ```
  2) Markdown lint
  - markdownlint or equivalent, with a pinned ruleset.
  - No new lint errors allowed.
  ```
- **Validator:** src/launch/validators/cli.py:218 - marked NOT_IMPLEMENTED
- **Gap:** No validator runs markdownlint on generated content

**Impact:**
- Minor - Markdown style inconsistencies (e.g., inconsistent heading styles, trailing whitespace)
- Does not affect functionality, only style/readability

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/markdownlint.py`
   - Entry point: `python -m launch.validators.markdownlint <run_dir>`
   - Tool: Use markdownlint-cli2 (Node.js) or pymarkdownlnt (Python)
   - Pin version in config/toolchain.lock.yaml
   - Inputs: `<run_dir>/work/site/**/*.md` (generated pages)
   - Ruleset: .markdownlint.json at repo root (pinned rules)
   - Exit codes: 0 if no errors, 2 if lint errors
   - Output: Creates gate log + issues in validation_report.json

2. **Integration:** Update src/launch/validators/cli.py:218
   ```python
   from ..validators.markdownlint import validate_markdownlint
   mdlint_ok = validate_markdownlint(run_dir, profile)
   gates.append({"name": "markdownlint", "ok": mdlint_ok, "log_path": ...})
   ```

3. **Profile behavior:**
   - local: Run (fast, improves quality)
   - ci/prod: Run (enforces style consistency)
   - Timeout: local=60s, ci=120s (per specs/09_validation_gates.md:92,103)

**Acceptance Criteria:**
- [ ] Markdownlint validator exists at src/launch/validators/markdownlint.py
- [ ] .markdownlint.json ruleset created at repo root
- [ ] markdownlint-cli2 or pymarkdownlnt pinned in toolchain.lock.yaml
- [ ] Validator integrated into launch_validate (cli.py line 218)
- [ ] Tests exist at tests/unit/validators/test_markdownlint.py
- [ ] Documented in docs/cli_usage.md

---

### G-GAP-013 | MINOR | Template token lint gate missing
**Description:** specs/09_validation_gates.md:40 requires no unresolved template tokens, but no validator exists

**Evidence:**
- **Spec:** specs/09_validation_gates.md:40
  ```
  Generated content MUST NOT contain unresolved __PLATFORM__ tokens
  ```
- **Validator:** src/launch/validators/cli.py:219 - marked NOT_IMPLEMENTED
- **Gap:** No validator checks for unresolved tokens like `__PLATFORM__`, `__LOCALE__`, `__PRODUCT__`

**Impact:**
- Minor - Unresolved template tokens visible to users (e.g., "Download __PLATFORM__ SDK")
- Indicates incomplete template expansion (should be caught during generation)

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/template_token_lint.py`
   - Entry point: `python -m launch.validators.template_token_lint <run_dir>`
   - Inputs: `<run_dir>/work/site/**/*.md` (generated pages)
   - Validation steps:
     1. Parse all generated markdown files
     2. Search for unresolved token patterns: `__[A-Z_]+__`
     3. Report any matches as issues
   - Exit codes: 0 if no tokens, 2 if tokens found
   - Output: Creates gate log + issues in validation_report.json

2. **Integration:** Update src/launch/validators/cli.py:219
   ```python
   from ..validators.template_token_lint import validate_template_tokens
   token_lint_ok = validate_template_tokens(run_dir, profile)
   gates.append({"name": "template_token_lint", "ok": token_lint_ok, "log_path": ...})
   ```

3. **Issue format:**
   ```json
   {
     "issue_id": "template_token_unresolved_<hash>",
     "gate": "template_token_lint",
     "severity": "error",
     "error_code": "GATE_TEMPLATE_TOKEN_UNRESOLVED",
     "message": "Unresolved template token: __PLATFORM__",
     "location": {"path": "content/en/products/...", "line": 42},
     "suggested_fix": "Expand template token or remove placeholder"
   }
   ```

4. **Profile behavior:**
   - local/ci/prod: Always run (fast, critical for quality)
   - Timeout: local=30s, ci=60s (very fast regex scan)

**Acceptance Criteria:**
- [ ] Template token lint validator exists at src/launch/validators/template_token_lint.py
- [ ] Validator scans for `__[A-Z_]+__` patterns
- [ ] Validator integrated into launch_validate (cli.py line 219)
- [ ] Tests exist at tests/unit/validators/test_template_token_lint.py
- [ ] Documented in docs/cli_usage.md

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| BLOCKER | 5 | G-GAP-005 to G-GAP-009 - Missing runtime validators (Hugo build, TruthLock, internal links, Hugo config, snippets) |
| MAJOR | 6 | G-GAP-001 to G-GAP-004, G-GAP-010, G-GAP-011 - Exit codes, determinism, external links, frontmatter |
| MINOR | 2 | G-GAP-012, G-GAP-013 - Markdownlint, template token lint |
| **Total** | **13** | **13 gaps identified** |

## Priority Order (Implementation)

### Phase 1: Critical Validators (Blockers)
1. G-GAP-006: TruthLock validator (highest quality impact)
2. G-GAP-005: Hugo build validator (prevents late failures)
3. G-GAP-007: Internal links validator (prevents broken links)
4. G-GAP-008: Hugo config validator (prevents build failures)
5. G-GAP-009: Snippets validator (prevents broken code examples)

### Phase 2: Determinism & Exit Codes (Major)
6. G-GAP-002: Issue ordering (determinism requirement)
7. G-GAP-003: Timestamp control (determinism requirement)
8. G-GAP-001: Exit code standardization (consistency requirement)
9. G-GAP-004: Issue ID derivation (maintainability improvement)

### Phase 3: Additional Validators (Major)
10. G-GAP-011: Frontmatter validator (prevents Hugo errors)
11. G-GAP-010: External links validator (quality, but flaky)

### Phase 4: Style Validators (Minor)
12. G-GAP-012: Markdownlint (style consistency)
13. G-GAP-013: Template token lint (quality check)
