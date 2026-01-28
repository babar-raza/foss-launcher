# Real Pilot Runbook — Dry-Run and Live-Run Execution

## Overview

This runbook provides step-by-step instructions for executing FOSS Launcher pilots with real external services (LLM provider, commit service, git operations).

**Modes**:
- **Dry-Run**: Full execution with real LLM/git but deferred PR (no commit service call)
- **Live-Run**: Full execution with PR opened via commit service

## Prerequisites

### Required Environment Variables

```bash
# LLM Provider (Anthropic API)
export ANTHROPIC_API_KEY="sk-ant-..."

# GitHub Personal Access Token (for commit service)
export GITHUB_TOKEN="ghp_..."

# Optional: Commit service endpoint (defaults to production)
export COMMIT_SERVICE_URL="https://commit-service.example.com/v1"
```

### Required Tools

- Python 3.13+
- Git
- `.venv` with all dependencies installed (`make install-uv`)

### Recommended: Pre-flight Checks

Before running a real pilot:

```bash
# 1. Validate spec pack
make validate

# 2. Run tests
make test

# 3. Verify mock E2E works
export LLM_PROVIDER=mock OFFLINE_MODE=1 OFFLINE_FIXTURES=1
python -m launch run --config pilots/example_pilot.yml
# (Check runs/<run_id>/ for artifacts)
```

## Dry-Run Pilot Execution

**Purpose**: Test full orchestration with real LLM and git operations, but defer PR submission.

### Step 1: Prepare Pilot Configuration

Create or use an existing pilot config file:

**Example**: `pilots/dry_run_example.yml`

```yaml
schema_version: "1.0"
run_id: "dry-run-{{timestamp}}"

input:
  repo_url: "https://github.com/example/hugo-site"
  sha: "main"  # or specific commit SHA
  product_url: "https://example.com/product"

output:
  site_repo_url: "https://github.com/example/docs-site"
  base_ref: "main"
  allowed_paths:
    - "content/docs/example-product/**"

llm:
  provider: "anthropic"
  model: "claude-sonnet-4-5"
  temperature: 0.0
  max_tokens: 4096

commit_service:
  offline_mode: true  # Dry-run: defer PR

flags:
  allow_manual_edits: false
  dry_run: true
```

### Step 2: Execute Dry-Run

```bash
# Set environment
export ANTHROPIC_API_KEY="sk-ant-..."
export OFFLINE_MODE=1  # Defer PR submission

# Run pilot
python -m launch run --config pilots/dry_run_example.yml
```

### Step 3: Verify Dry-Run Results

After execution, check:

```bash
# Find latest run
ls -lt runs/ | head

# Check run directory
RUN_ID="<run_id_from_output>"
cd runs/$RUN_ID

# Verify artifacts exist
ls -la artifacts/
# Expected:
# - repo_inventory.json
# - frontmatter_index.json
# - site_context.json
# - hugo_facts.json
# - product_facts.json
# - evidence_map.json
# - snippet_catalog.json
# - page_plan.json
# - draft_content.md
# - patch_bundle.json
# - validation_report.json
# - create_commit_bundle.json (deferred)
# - open_pr_bundle.json (deferred)

# Check validation report
cat artifacts/validation_report.json | jq '.status'
# Should be "ok" or "w8_converged"

# Check PR bundle
cat artifacts/open_pr_bundle.json | jq '.payload.title'
```

### Step 4: Inspect Evidence

```bash
# LLM call evidence
ls evidence/llm_calls/
# Should contain .json files for each LLM call

# Validation run evidence
ls evidence/validation_runs/
# Should contain validation outputs

# Check snapshot
cat snapshot.json | jq '.run_state.status'
# Should be "w9_ok" or "w8_converged"
```

### Success Criteria (Dry-Run)

- ✅ All required artifacts exist
- ✅ Validation report status is "ok" or "w8_converged"
- ✅ PR bundle is written to `artifacts/open_pr_bundle.json`
- ✅ No network errors (commit service not called)
- ✅ Snapshot shows successful completion

## Live-Run Pilot Execution

**Purpose**: Full execution with PR opened via commit service.

**⚠️ Warning**: Live-run will create real commits and PRs on GitHub. Ensure:
- You have write access to target repository
- Commit service is configured and reachable
- PR allowed_paths are correctly scoped

### Step 1: Prepare Live Pilot Configuration

**Example**: `pilots/live_run_example.yml`

```yaml
schema_version: "1.0"
run_id: "live-run-{{timestamp}}"

input:
  repo_url: "https://github.com/example/hugo-site"
  sha: "main"
  product_url: "https://example.com/product"

output:
  site_repo_url: "https://github.com/example/docs-site"
  base_ref: "main"
  branch_name: "launch/example-product/{{run_id}}"
  allowed_paths:
    - "content/docs/example-product/**"

llm:
  provider: "anthropic"
  model: "claude-sonnet-4-5"
  temperature: 0.0
  max_tokens: 4096

commit_service:
  endpoint_url: "https://commit-service.example.com/v1"
  offline_mode: false  # Live-run: make real API calls
  timeout: 120
  max_retries: 3

flags:
  allow_manual_edits: false
  dry_run: false
```

### Step 2: Execute Live-Run

```bash
# Set environment
export ANTHROPIC_API_KEY="sk-ant-..."
export GITHUB_TOKEN="ghp_..."
export COMMIT_SERVICE_URL="https://commit-service.example.com/v1"

# Unset offline mode if previously set
unset OFFLINE_MODE

# Run pilot
python -m launch run --config pilots/live_run_example.yml
```

### Step 3: Monitor Execution

Watch for key events:

```bash
# Monitor logs (if enabled)
tail -f runs/<run_id>/logs/run.log

# Key milestones:
# - W1: Repository cloned and scanned
# - W2: Product facts extracted
# - W3: Snippets curated
# - W4: Page plan created
# - W5: Content drafted
# - W6: Patches applied
# - W7: Validation passed
# - W8: Fixes applied (if needed)
# - W9: PR created
```

### Step 4: Verify Live-Run Results

```bash
RUN_ID="<run_id_from_output>"
cd runs/$RUN_ID

# Check snapshot for PR details
cat snapshot.json | jq '.run_state.pr_result'
# Should contain:
# - pr_number
# - pr_url
# - pr_html_url

# Get PR URL
PR_URL=$(cat snapshot.json | jq -r '.run_state.pr_result.pr_html_url')
echo "PR created: $PR_URL"

# Open PR in browser (Linux/macOS)
# xdg-open "$PR_URL"  # Linux
# open "$PR_URL"      # macOS
```

### Step 5: Review PR on GitHub

1. Navigate to PR URL
2. Review changes:
   - Check files modified are within `allowed_paths`
   - Verify content quality and accuracy
   - Check claim markers are resolved
   - Ensure no secrets or sensitive data
3. Request reviews if needed
4. Merge or request changes

### Success Criteria (Live-Run)

- ✅ PR is created on GitHub
- ✅ PR title and description are meaningful
- ✅ Changed files are within allowed_paths
- ✅ Content is accurate and well-formatted
- ✅ All validation gates passed
- ✅ No secrets or sensitive data in PR

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes (real LLM) | - | Anthropic API key for Claude |
| `GITHUB_TOKEN` | Yes (live-run) | - | GitHub PAT for commit service |
| `COMMIT_SERVICE_URL` | No | - | Commit service endpoint URL |
| `OFFLINE_MODE` | No | `0` | Set to `1` for dry-run (defer PR) |
| `LLM_PROVIDER` | No | `anthropic` | Set to `mock` for mock E2E |
| `OFFLINE_FIXTURES` | No | `0` | Set to `1` to use fixture repos |
| `PYTHONHASHSEED` | Recommended | - | Set to `0` for deterministic tests |

## Artifact Locations

All artifacts are stored in `runs/<run_id>/`:

```
runs/<run_id>/
├── snapshot.json              # State graph snapshot
├── artifacts/
│   ├── repo_inventory.json    # W1.1 Clone output
│   ├── frontmatter_index.json # W1.3 Frontmatter scan
│   ├── site_context.json      # W1.4 Hugo context
│   ├── hugo_facts.json        # W1.4 Hugo config
│   ├── product_facts.json     # W2 Facts
│   ├── evidence_map.json      # W2 Evidence
│   ├── snippet_catalog.json   # W3 Snippets
│   ├── page_plan.json         # W4 IA plan
│   ├── draft_content.md       # W5 Draft
│   ├── patch_bundle.json      # W6 Patches
│   ├── validation_report.json # W7 Validation
│   ├── create_commit_bundle.json # W9 Commit request
│   └── open_pr_bundle.json    # W9 PR request
├── evidence/
│   ├── llm_calls/             # LLM request/response logs
│   └── validation_runs/       # Validation evidence
├── worktree/
│   ├── repo_clone/            # Cloned product repo
│   └── site_clone/            # Cloned docs site
└── logs/
    └── run.log                # Execution log (if enabled)
```

## Troubleshooting

### Issue: LLM API Error

**Symptom**: `LLMError: LLM API call failed`

**Fixes**:
1. Verify `ANTHROPIC_API_KEY` is set and valid
2. Check network connectivity
3. Verify API quota/limits
4. Check LLM provider status page

### Issue: Commit Service Unreachable

**Symptom**: `CommitServiceError: Health check failed`

**Fixes**:
1. Verify `COMMIT_SERVICE_URL` is correct
2. Check network connectivity
3. Verify commit service is running
4. Use `OFFLINE_MODE=1` to defer PR and debug offline

### Issue: Validation Errors

**Symptom**: `validation_report.json` shows errors

**Fixes**:
1. Check validation report details: `cat artifacts/validation_report.json | jq '.errors'`
2. W8 Fixer should have attempted fixes (check event log)
3. Review patch_bundle.json for issues
4. Re-run with manual review of draft_content.md

### Issue: PR Not Created

**Symptom**: No `pr_result` in snapshot.json

**Fixes**:
1. Check snapshot status: `cat snapshot.json | jq '.run_state.status'`
2. If status is `w8_converged`, validation may have failed (check `validation_report.json`)
3. If status is `w9_deferred`, check `artifacts/open_pr_bundle.json` for deferred PR data
4. Check commit service logs for errors

### Issue: Determinism Failures

**Symptom**: Same config produces different outputs

**Fixes**:
1. Set `PYTHONHASHSEED=0` for deterministic hashing
2. Verify LLM temperature is `0.0`
3. Check for timestamp fields in artifacts (should use stable timestamps)
4. Run determinism harness: `python scripts/verify_determinism.py --config <config>`

## Advanced Usage

### Running Multiple Pilots in Parallel

```bash
# Launch pilots concurrently
python -m launch run --config pilots/pilot1.yml &
python -m launch run --config pilots/pilot2.yml &
python -m launch run --config pilots/pilot3.yml &
wait
```

### Resuming Failed Runs

```bash
# Resume from checkpoint (if implemented)
python -m launch resume --run-id <run_id>
```

### Custom Evidence Packaging

```bash
# Create evidence bundle after run
cd runs/<run_id>
tar -czf ../../evidence_<run_id>.tar.gz evidence/ artifacts/ snapshot.json
```

## Next Steps

After successful pilot execution:

1. Review PR on GitHub
2. Collect feedback from stakeholders
3. Iterate on pilot configuration if needed
4. Scale to production workflows
5. Monitor telemetry and evidence for quality

---

**Document Version**: 1.0
**Last Updated**: 2026-01-28
**Related**: [03_mock_e2e_design.md](03_mock_e2e_design.md)
