# Strict Compliance Guarantees (Master List)

This file is the **single source of truth** for the project’s strict compliance guarantees.  
Any ambiguity or missing detail MUST be treated as a **BLOCKER** (no improvisation).

---

## Enforcement contract (applies to every guarantee)

For each guarantee below, the system MUST provide:

- **Binding text** in specs (the requirement is written as MUST/SHALL).
- **Enforcement** via automated **gates** (preflight and/or runtime validators).
- **Tests** proving enforcement (unit + integration as applicable).
- **Evidence** for each run: `report.md` + `self_review.md`.

---

## A. Baseline guarantees (user-provided)

1. **No improvisation** — Ambiguities → blocker issues  
2. **Respect write-fence** — Only edit `allowed_paths`  
3. **Shared library boundaries** — Zero tolerance for violations  
4. **Test-driven** — Every feature has tests  
5. **Determinism** — Byte-for-byte reproducible (where applicable)  
6. **Preflight mandatory** — `validate_swarm_ready.py` before every task  
7. **Evidence always** — `report.md` + `self_review.md` required  
8. **No placeholders** — No `TODO` / `PIN_ME` / `NotImplemented` in production  
9. **.venv required** — Never use global Python  
10. **Spec authority** — Specs are binding, taskcards are law  

---

## B. Additional guarantees (expanded set)

These are additional guarantees that MUST be implemented as **docs + enforced gates + tests**.

### B1) Input immutability (pinned refs)
- **Guarantee:** All critical inputs MUST be pinned to immutable identifiers (e.g., commit SHAs). No floating branches/tags in production.

### B2) Hermetic execution boundaries
- **Guarantee:** No read/write outside the permitted sandbox (repo root, RUN_DIR, allowed paths). Realpath containment is mandatory; symlink/`..` escapes MUST be blocked.

### B3) Supply-chain pinning
- **Guarantee:** Toolchain and dependencies MUST be frozen/pinned and reproducible (lockfiles required; installs run in frozen mode).

### B4) Network egress allowlist
- **Guarantee:** Outbound network access MUST be restricted to an explicit allowlist. Any non-allowlisted host MUST be blocked.

### B5) Secret hygiene and redaction
- **Guarantee:** Secrets MUST NOT appear in logs, artifacts, reports, telemetry payloads, or PR text. Secret scanning and redaction are mandatory and enforced.

### B6) Budget limits and circuit breakers
- **Guarantee:** Hard caps MUST exist and be enforced for runtime, retries, LLM calls/tokens, and file churn. On breach: stop-the-line with a typed blocker.

### B7) Change-budget and minimal-diff discipline
- **Guarantee:** Only intended files change; changes must stay within defined change budgets. Formatting-only rewrites and uncontrolled diff explosions MUST be prevented.

### B8) CI parity and single canonical entrypoint
- **Guarantee:** Local and CI runs MUST use the same canonical entrypoint and commands. CI MUST NOT diverge into ad-hoc or “special” validation paths.

### B9) Non-flaky tests
- **Guarantee:** Tests MUST be stable and deterministic where possible (fixed seeds, deterministic ordering). Flake detection/mitigation is required for critical paths.

### B10) No execution of untrusted repo code
- **Guarantee:** Ingested or external repositories are treated as untrusted input: parse-only. Execution from untrusted paths MUST be prohibited.

### B11) Spec/taskcard version locking
- **Guarantee:** Taskcards and runs MUST declare the exact versions of specs/rules/templates they are bound to, and gates MUST fail if versions are missing/mismatched.

### B12) Rollback and recovery contract
- **Guarantee:** Every change MUST be reversible and every run MUST be resumable with replay metadata (base ref, run manifest, rollback steps).

---

## C. Canonical labels (optional, for traceability)

If you want a single lettered set for traceability, use:

- **A** Input immutability (pinned refs)  
- **B** Hermetic execution boundaries  
- **C** Supply-chain pinning  
- **D** Network egress allowlist  
- **E** Secret hygiene/redaction  
- **F** Budget limits/circuit breakers  
- **G** Change-budget/minimal-diff  
- **H** CI parity/single entrypoint  
- **I** Non-flaky tests  
- **J** No execution of untrusted code  
- **K** Spec/taskcard version locking  
- **L** Rollback/recovery contract  

(Keep the **baseline** items as overarching governance requirements that apply to every A–L item.)

---

## D. Definitions (short)

- **BLOCKER:** A documented stop-the-line issue caused by ambiguity, missing requirements, policy violation, or inability to comply within write-fence.
- **Production paths:** The repo-defined paths where runtime behavior is implemented and shipped (must be defined in specs).
- **Gates:** Automated checks that fail hard and prevent continuation when a guarantee is violated.
