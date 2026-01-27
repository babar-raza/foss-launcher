# AGENT_G: Gaps and Issues Catalog

**Mission**: Identify all gaps, blockers, and improvement opportunities in validation gates.

**Audit Date**: 2026-01-27
**Run ID**: 20260127-1518

---

## Gap Format

Each gap follows the pattern:
```
G-GAP-NNN | SEVERITY | Description | Evidence | Proposed Fix
```

**Severity Levels**:
- **BLOCKER**: Must be fixed before production deployment
- **MAJOR**: Significant gap affecting enforcement strength
- **MINOR**: Enhancement opportunity, not critical

---

## BLOCKER Gaps

### G-GAP-001 | BLOCKER | Runtime Validation Gates (Gates 4-12) Not Implemented

**Description**: Content validation gates (frontmatter, markdown lint, Hugo, links, snippets, TruthLock) are not implemented in runtime validation. Only scaffold stubs exist.

**Impact**:
- No enforcement of markdown quality at runtime
- No Hugo build validation during runs
- No link integrity checks during runs
- No TruthLock enforcement during runs
- False passes possible if scaffold is bypassed

**Evidence**:
- src/launch/validators/cli.py:216-250 (stub implementation)
- TRACEABILITY_MATRIX.md:321-324: "Runtime Validation Gates (Gates 1-10 + special gates): ⚠️ NOT YET IMPLEMENTED"
- TC-460 (Validator W7): Taskcard tracks implementation
- TC-570 (validation gates extensions): Taskcard tracks extensions

**Current Mitigation**:
- Scaffold correctly marks unimplemented gates as FAILED in prod profile (cli.py:228-239)
- No false passes occur (correct per Guarantee E)
- Gates visible as "NOT_IMPLEMENTED" in validation_report.json

**Proposed Fix**:
1. Implement Gates 4-12 in src/launch/validators/cli.py:
   - Gate 4 (frontmatter): Validate frontmatter against schemas
   - Gate 5 (markdownlint): Run markdownlint with pinned ruleset
   - Gate 6 (template_token_lint): Detect unresolved template tokens
   - Gate 7 (hugo_config): Validate Hugo config compatibility
   - Gate 8 (hugo_build): Run Hugo build and check for errors
   - Gate 9 (internal_links): Validate internal links and anchors
   - Gate 10 (external_links): Validate external links (optional by profile)
   - Gate 11 (snippets): Validate snippet syntax
   - Gate 12 (truthlock): Enforce TruthLock rules

2. Follow deterministic patterns from preflight gates:
   - Use sorted() for file iteration
   - Use fixed patterns/rules (no random state)
   - Use typed error codes
   - Add comprehensive tests

3. Integration:
   - Add gate results to validation_report.json
   - Emit issues[] with typed error codes
   - Respect profile-based timeouts (specs/09_validation_gates.md:86-119)

**Tracking**: TC-460 (Validator W7), TC-570 (validation gates extensions)

**Priority**: P0 (BLOCKER for production readiness)

---

### G-GAP-002 | BLOCKER | Rollback Metadata Validation Not Implemented

**Description**: Guarantee L (Rollback + Recovery Contract) requires validation of rollback metadata in production runs, but no validator exists.

**Impact**:
- No enforcement of rollback metadata presence in PR artifacts
- Rollback procedures may fail due to missing metadata
- Production runs may proceed without recovery plan

**Evidence**:
- TRACEABILITY_MATRIX.md:619-627: "⚠️ Runtime validation PENDING"
- specs/34_strict_compliance_guarantees.md (Guarantee L section): "Runtime: `launch_validate` checks rollback metadata exists in prod profile"
- TC-480 (PRManager W9): Taskcard not started (rollback metadata validation)

**Required Behavior**:
- Validate PR artifacts include rollback metadata in prod profile
- Required fields: base_ref, run_id, rollback_steps, affected_paths (per specs/12_pr_and_release.md)
- Schema: specs/schemas/pr.schema.json (may need rollback fields added)
- Error code: PR_MISSING_ROLLBACK_METADATA

**Proposed Fix**:
1. Add Gate 13 (rollback_metadata) to src/launch/validators/cli.py:
   ```python
   # Gate 13: Rollback metadata validation (prod profile only)
   if profile == "prod":
       pr_artifacts = artifacts_dir.glob("pr_*.json")
       for pr_artifact in pr_artifacts:
           # Validate rollback metadata exists
           pr_data = json.loads(pr_artifact.read_text())
           if "rollback_metadata" not in pr_data:
               issues.append(_issue(
                   issue_id="iss_rollback_metadata",
                   gate="rollback_metadata",
                   severity="blocker",
                   error_code="PR_MISSING_ROLLBACK_METADATA",
                   message="PR artifact missing rollback metadata (required in prod profile)",
                   files=[str(pr_artifact)],
                   suggested_fix="Add rollback_metadata to PR artifact per specs/12_pr_and_release.md"
               ))
   ```

2. Extend specs/schemas/pr.schema.json with rollback_metadata fields
3. Add tests for rollback metadata validation

**Tracking**: TC-480 (PRManager W9 - taskcard not started)

**Priority**: P0 (BLOCKER for production PR workflows)

---

## MAJOR Gaps

### G-GAP-003 | MAJOR | Secret Redaction Runtime Utilities Not Implemented

**Description**: Guarantee E requires runtime redaction of secrets in logs/artifacts, but only preflight scan exists. Runtime logging utilities do not redact secrets.

**Impact**:
- Secrets may leak in logs during runs
- Secrets may leak in artifacts/reports
- Preflight scan is insufficient (only checks committed files, not runtime outputs)

**Evidence**:
- TRACEABILITY_MATRIX.md:445-450: "⚠️ Runtime redaction PENDING"
- specs/34_strict_compliance_guarantees.md:139-143: "Runtime: Logging utilities MUST redact secret patterns"
- TC-590 (security and secrets): Taskcard tracks implementation

**Required Behavior**:
- All secret-like patterns redacted from logs/artifacts/reports
- Display format: Show ***REDACTED*** instead of actual values
- Location: Logging utilities (likely src/launch/util/logging.py or src/launch/util/redaction.py - TBD)

**Proposed Fix**:
1. Create src/launch/util/redaction.py:
   ```python
   """Secret redaction utilities (Guarantee E)."""

   import re
   from typing import List, Tuple

   # Reuse patterns from validate_secrets_hygiene.py
   SECRET_PATTERNS = [
       (r"ghp_[A-Za-z0-9]{36}", "GitHub PAT"),
       (r"github_pat_[A-Za-z0-9_]{82}", "GitHub Fine-Grained PAT"),
       (r"Bearer\s+[A-Za-z0-9._\-]{20,}", "Bearer Token"),
       (r"(?i)api[_\-]?key[\"\']?\s*[:=]\s*[\"\']?([A-Za-z0-9_\-]{32,})[\"\']?", "API Key"),
       (r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "Private Key"),
       (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
   ]

   def redact_secrets(text: str) -> str:
       """Redact all secret patterns from text."""
       for pattern, name in SECRET_PATTERNS:
           text = re.sub(pattern, "***REDACTED***", text)
       return text
   ```

2. Integrate into logging utilities:
   - Wrap all log output with redact_secrets()
   - Wrap all artifact writes with redact_secrets()
   - Wrap all report generation with redact_secrets()

3. Add tests:
   - Test all secret patterns are redacted
   - Test redaction does not break structured data (JSON)
   - Test performance (redaction should be fast)

**Tracking**: TC-590 (security and secrets)

**Priority**: P1 (MAJOR security risk)

---

### G-GAP-004 | MAJOR | Floating Ref Rejection Not Integrated at Runtime

**Description**: Gate J validates pinned refs at preflight, but runtime rejection is not integrated into orchestrator. Floating refs may be accepted at runtime.

**Impact**:
- Preflight check can be bypassed if run_config is modified after validation
- No runtime enforcement of Guarantee A (Input Immutability)

**Evidence**:
- TRACEABILITY_MATRIX.md:346-350: "⚠️ Runtime rejection PENDING"
- specs/34_strict_compliance_guarantees.md:47-48: "Runtime: `launch_validate` MUST reject floating refs in prod profile"
- TC-300 (orchestrator startup): Taskcard tracks orchestrator integration
- TC-460 (launch_validate integration): Taskcard tracks runtime validation

**Required Behavior**:
- Reject run_config with floating branches/tags in prod profile at runtime
- Error code: POLICY_PINNED_REFS_VIOLATION

**Proposed Fix**:
1. Add floating ref check to src/launch/validators/cli.py (after Gate 2):
   ```python
   # Gate 2.5: Pinned refs validation (prod profile only)
   if profile == "prod":
       run_config = load_and_validate_run_config(repo_root, run_dir / "run_config.yaml")
       ref_fields = ["github_ref", "site_ref", "workflows_ref", "base_ref"]

       for field in ref_fields:
           if field in run_config:
               ref_value = run_config[field]
               if not re.match(r"^[0-9a-f]{7,40}$", ref_value.lower()):
                   issues.append(_issue(
                       issue_id="iss_floating_ref",
                       gate="pinned_refs_runtime",
                       severity="blocker",
                       error_code="POLICY_PINNED_REFS_VIOLATION",
                       message=f"{field}='{ref_value}' is not a commit SHA (floating refs forbidden in prod profile)",
                       suggested_fix="Use commit SHA instead of branch/tag name"
                   ))
   ```

2. Add tests for runtime floating ref rejection

**Tracking**: TC-300 (orchestrator), TC-460 (validator)

**Priority**: P1 (MAJOR supply-chain risk)

---

### G-GAP-005 | MAJOR | Preflight Gates Lack Structured Error Output

**Description**: Preflight gates (tools/validate_*.py) emit human-readable text output but do not emit structured JSON error reports. This makes programmatic parsing difficult.

**Impact**:
- CI tools must parse text output (brittle)
- No standardized issue schema for preflight failures
- Harder to aggregate/analyze failures

**Evidence**:
- All preflight gates emit text-only output (e.g., validate_pinned_refs.py:183-207)
- Runtime gates use specs/schemas/issue.schema.json (cli.py:44-71)
- No shared error reporting pattern

**Proposed Fix**:
1. Create shared error reporting utility in tools/gate_utils.py:
   ```python
   """Shared utilities for preflight gates."""

   import json
   from pathlib import Path
   from typing import Dict, Any, List

   def emit_gate_report(
       gate_id: str,
       ok: bool,
       issues: List[Dict[str, Any]],
       output_path: Path
   ) -> None:
       """Emit structured gate report."""
       report = {
           "gate_id": gate_id,
           "ok": ok,
           "issues": issues
       }
       output_path.parent.mkdir(parents=True, exist_ok=True)
       output_path.write_text(json.dumps(report, indent=2))
   ```

2. Update all preflight gates to emit JSON report in addition to text output:
   ```python
   # At end of main()
   from tools.gate_utils import emit_gate_report

   emit_gate_report(
       gate_id="J",
       ok=len(all_violations) == 0,
       issues=[{
           "issue_id": f"iss_floating_ref_{i}",
           "severity": "blocker",
           "message": f"{config_path}: {', '.join(errors)}"
       } for i, (config_path, errors) in enumerate(all_violations)],
       output_path=Path("reports/gates/gate_J.json")
   )
   ```

3. Benefits:
   - CI can consume JSON reports directly
   - Consistent issue schema across preflight and runtime
   - Easier aggregation/analysis

**Tracking**: No taskcard (new recommendation)

**Priority**: P2 (MAJOR usability issue)

---

## MINOR Gaps

### G-GAP-006 | MINOR | Test Flakiness Not Automatically Enforced

**Description**: Guarantee I (Non-Flaky Tests) requires PYTHONHASHSEED=0 and deterministic RNG seeding, but no automated gate validates this configuration.

**Impact**:
- Developers may run tests without PYTHONHASHSEED=0
- Flaky tests may be introduced without detection
- Manual review required to ensure determinism

**Evidence**:
- TRACEABILITY_MATRIX.md:551-556: "✅ POLICY DEFINED (automated validation not implemented)"
- specs/34_strict_compliance_guarantees.md:242-250: "Enforcement: Verify test configuration enforces determinism"

**Proposed Fix**:
1. Create Gate T (test_determinism) in tools/validate_test_determinism.py:
   ```python
   #!/usr/bin/env python3
   """Test Determinism Validator (Gate T)

   Validates that test configuration enforces determinism per Guarantee I.

   Checks:
   - PYTHONHASHSEED=0 in pytest.ini or pyproject.toml
   - No unseeded RNG usage in tests (random.random without seed)
   """

   def check_pytest_config(repo_root: Path) -> List[str]:
       errors = []
       pytest_ini = repo_root / "pytest.ini"
       pyproject_toml = repo_root / "pyproject.toml"

       # Check pytest.ini
       if pytest_ini.exists():
           content = pytest_ini.read_text()
           if "PYTHONHASHSEED" not in content or "PYTHONHASHSEED=0" not in content:
               errors.append("pytest.ini missing PYTHONHASHSEED=0 setting")

       # Check pyproject.toml
       elif pyproject_toml.exists():
           content = pyproject_toml.read_text()
           if "PYTHONHASHSEED" not in content or "PYTHONHASHSEED=0" not in content:
               errors.append("pyproject.toml missing PYTHONHASHSEED=0 setting")

       else:
           errors.append("No pytest configuration found (pytest.ini or pyproject.toml)")

       return errors
   ```

2. Add to validate_swarm_ready.py gate list (Gate T)

**Tracking**: No taskcard (new recommendation)

**Priority**: P3 (MINOR enhancement)

---

### G-GAP-007 | MINOR | run_config.schema.json Lacks SHA Format Validation

**Description**: run_config.schema.json does not enforce commit SHA format for *_ref fields. Only runtime/preflight gates enforce this.

**Impact**:
- Schema validation alone does not catch floating refs
- Developers may use invalid ref formats without immediate feedback

**Evidence**:
- specs/schemas/run_config.schema.json: No pattern constraint on *_ref fields
- validate_pinned_refs.py:49-51: SHA validation in preflight gate only

**Proposed Fix**:
1. Update specs/schemas/run_config.schema.json to add pattern constraints:
   ```json
   {
     "properties": {
       "github_ref": {
         "type": "string",
         "pattern": "^[0-9a-f]{7,40}$",
         "description": "Commit SHA (7-40 hex chars)"
       },
       "site_ref": {
         "type": "string",
         "pattern": "^[0-9a-f]{7,40}$",
         "description": "Commit SHA (7-40 hex chars)"
       }
     }
   }
   ```

2. Benefits:
   - Earlier feedback for developers (schema validation fails immediately)
   - Redundant enforcement (defense in depth)

**Tracking**: No taskcard (new recommendation)

**Priority**: P3 (MINOR enhancement)

---

### G-GAP-008 | MINOR | Runtime Gate Stub Messages Generic

**Description**: Unimplemented runtime gates (Gates 4-12) emit generic "NOT_IMPLEMENTED" message. No gate-specific guidance provided.

**Impact**:
- Developers/users don't know what each unimplemented gate will do
- Harder to prioritize gate implementation

**Evidence**:
- src/launch/validators/cli.py:237: "Gate not implemented (no false pass: marked as FAILED per Guarantee E)"

**Proposed Fix**:
1. Add gate-specific descriptions to stub messages:
   ```python
   not_impl = {
       "frontmatter": "Validate page frontmatter against schemas",
       "markdownlint": "Run markdownlint with pinned ruleset",
       "template_token_lint": "Detect unresolved template tokens (e.g., __PLATFORM__)",
       "hugo_config": "Validate Hugo config compatibility with planned sections",
       "hugo_build": "Run Hugo build and check for errors",
       "internal_links": "Validate internal links and anchors",
       "external_links": "Validate external links (optional by profile)",
       "snippets": "Validate snippet syntax and optionally run in container",
       "truthlock": "Enforce TruthLock rules (specs/04_claims_compiler_truth_lock.md)",
   }

   for gate_name, description in not_impl.items():
       issues.append(_issue(
           issue_id=f"iss_not_implemented_{gate_name}",
           gate=gate_name,
           severity=sev,
           error_code=f"GATE_NOT_IMPLEMENTED" if sev == "blocker" else None,
           message=f"Gate not implemented: {description}",
           suggested_fix=f"Implement {gate_name} gate per specs/09_validation_gates.md"
       ))
   ```

**Tracking**: No taskcard (new recommendation)

**Priority**: P3 (MINOR usability enhancement)

---

### G-GAP-009 | MINOR | Preflight Gate Performance Not Profiled

**Description**: No timing instrumentation for preflight gates. Unknown if any gates are slow.

**Impact**:
- Slow gates may delay CI feedback
- No data to prioritize performance optimizations

**Proposed Fix**:
1. Add timing to validate_swarm_ready.py GateRunner:
   ```python
   import time

   def run_gate(self, gate_id: str, description: str, script_path: str, check_warnings: bool = False) -> bool:
       start_time = time.time()
       # ... existing logic ...
       elapsed = time.time() - start_time

       self.results.append((gate_id, description, passed, status_msg, elapsed))
       print(f"  Elapsed: {elapsed:.2f}s")
       return passed
   ```

2. Emit timing report at end:
   ```python
   print("\n=== Gate Performance ===")
   for gate_id, description, passed, status_msg, elapsed in self.results:
       print(f"  Gate {gate_id}: {elapsed:.2f}s")
   print(f"  Total: {sum(r[4] for r in self.results):.2f}s")
   ```

**Tracking**: No taskcard (new recommendation)

**Priority**: P3 (MINOR optimization opportunity)

---

### G-GAP-010 | MINOR | Gate Dependency Ordering Not Documented

**Description**: Preflight gates have implicit dependencies (e.g., Gate 0 should run before other gates), but execution order is not explicitly documented.

**Impact**:
- Unclear which gates depend on others
- May waste time running dependent gates if prerequisite fails

**Proposed Fix**:
1. Add docstring to validate_swarm_ready.py listing gate dependencies:
   ```python
   """Gate Execution Order (Topological):

   Level 0 (No dependencies):
   - Gate 0: .venv policy

   Level 1 (Depends on Level 0):
   - Gate A1: Spec pack validation
   - Gate K: Supply chain pinning

   Level 2 (Depends on Level 1):
   - All other gates

   Rationale:
   - Gate 0 must pass before any Python code runs (ensures .venv)
   - Gate A1 and K must pass before schema-based validators
   """
   ```

2. Implement fail-fast logic:
   ```python
   # If Gate 0 fails, skip all other gates
   if not gate_0_passed:
       print("Gate 0 failed. Skipping remaining gates.")
       return 1
   ```

**Tracking**: No taskcard (new recommendation)

**Priority**: P3 (MINOR documentation issue)

---

## Summary

**Total Gaps**: 10
- **BLOCKER**: 2 (G-GAP-001, G-GAP-002)
- **MAJOR**: 3 (G-GAP-003, G-GAP-004, G-GAP-005)
- **MINOR**: 5 (G-GAP-006, G-GAP-007, G-GAP-008, G-GAP-009, G-GAP-010)

**Priority Distribution**:
- **P0 (Blocker)**: 2 gaps
- **P1 (Major)**: 2 gaps
- **P2 (Major)**: 1 gap
- **P3 (Minor)**: 5 gaps

**Key Themes**:
1. **Runtime validation incomplete**: Majority of gaps are pending runtime implementations
2. **Enforcement gaps**: Some preflight checks not integrated into runtime
3. **Usability improvements**: Structured output, profiling, documentation

---

## Gap Resolution Tracking

| Gap ID | Taskcard | Status | Target Phase |
|--------|----------|--------|--------------|
| G-GAP-001 | TC-460, TC-570 | 🔄 Pending | Phase 6 (W7) |
| G-GAP-002 | TC-480 | 🔄 Pending | Phase 6 (W9) |
| G-GAP-003 | TC-590 | 🔄 Pending | Phase 7 |
| G-GAP-004 | TC-300, TC-460 | 🔄 Pending | Phase 6 (Orchestrator + W7) |
| G-GAP-005 | (new) | 📋 Proposed | TBD |
| G-GAP-006 | (new) | 📋 Proposed | TBD |
| G-GAP-007 | (new) | 📋 Proposed | TBD |
| G-GAP-008 | (new) | 📋 Proposed | TBD |
| G-GAP-009 | (new) | 📋 Proposed | TBD |
| G-GAP-010 | (new) | 📋 Proposed | TBD |

---

**Report Generated**: 2026-01-27 (AGENT_G)
**Gap Analysis Method**: Code review + spec cross-reference + TRACEABILITY_MATRIX.md analysis
