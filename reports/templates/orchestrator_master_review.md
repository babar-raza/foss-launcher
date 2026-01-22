# Orchestrator Master Review

> Orchestrator: __ORCH_NAME__  
> Date: __DATE__  
> Repo state: __COMMIT__/__BRANCH__

## Preflight
- [ ] `python scripts/validate_spec_pack.py` passed
- [ ] `python scripts/validate_plans.py` passed

## Inputs reviewed
List all agent self-reviews and reports you read.
- `reports/agents/<agent>/<task>/self_review.md`
- `reports/agents/<agent>/<task>/report.md`

## Cross-agent consistency checks
- Spec adherence (which specs were validated, how):
- Interface contracts (CLI/MCP entrypoints, schemas, paths):
- Determinism (toolchain pins, hashing, stable ordering):
- Safety (allowed_paths enforcement, single-writer rules):
- Evidence coverage (are claims backed, are tests reproducible):

## Integration test summary
### Commands run
- `...`

### Results
- Pass/fail summary:
- Known failures + owners:

## GO/NO-GO decision
- Decision:
- Blocking issues (link to blocker issue artifacts when present):
- Required follow-ups:
