---
id: TC-3812
title: "SEO config + allowlist + dependencies wiring"
status: Done
priority: Medium
owner: agent
updated: "2026-03-07"
tags: [seo, config, dependencies]
depends_on: [TC-3811]
allowed_paths:
  - plans/taskcards/TC-3812_seo_config_wiring.md
  - configs/network_allowlist.yaml
  - pyproject.toml
evidence_required:
  - test output
---

# Taskcard TC-3812 — SEO Config + Allowlist + Dependencies

## Objective
Add SEO-related network hosts to allowlist and pytrends dependency to pyproject.toml.

## Scope
### In scope
- Add Google Trends/Suggest/Gemini hosts to network_allowlist.yaml
- Add pytrends to pyproject.toml dependencies

### Out of scope
- All SEO module code (already done in TC-3806 through TC-3811)

## Allowed paths
- plans/taskcards/TC-3812_seo_config_wiring.md
- configs/network_allowlist.yaml
- pyproject.toml

## Failure modes
### FM1: pytrends version conflict
**Detection**: pip install fails
**Resolution**: Use flexible version spec (>=4.9)

### FM2: Allowlist too restrictive
**Detection**: API calls blocked at runtime
**Resolution**: Add all required subdomains

### FM3: Missing host blocks legitimate requests
**Detection**: HTTP client raises allowlist error
**Resolution**: Hosts are additive — existing ones untouched

## Task-specific review checklist
1. [ ] Google Trends host added
2. [ ] Google Suggest host added
3. [ ] Gemini API host added
4. [ ] pytrends added to dependencies
5. [ ] All existing tests pass

## Acceptance checks
1. [ ] All existing tests pass (PYTHONHASHSEED=0)
