# Security Policy

## Reporting

If you discover a security issue, do **not** open a public issue.
Instead, report it privately to the maintainers responsible for this repo.

Include:
- a minimal reproduction
- expected vs actual behavior
- any logs or artifacts that help triage

## Secrets

This repo is designed for agent execution. **Never** commit:
- API keys / tokens
- private SSH keys
- production endpoints or credentials

Use `*_TOKEN` env vars as described in `specs/16_local_telemetry_api.md` and `specs/17_github_commit_service.md`.
