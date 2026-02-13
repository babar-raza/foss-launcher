---
id: TC-1504
title: "Ensure LLM is Used + Diagnostic Logging"
status: Done
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "llm", "logging", "diagnostics", "llm-provider"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1504_llm_diagnostic_logging.md
  - src/launch/clients/llm_provider.py
  - src/launch/workers/w2_facts_builder/worker.py
evidence_required:
  - "reports/agents/agent_b/TC-1504/evidence.md"
spec_ref: "7a2e753d308154582e85aea06a0cf85e2c91a5f2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1504 — Ensure LLM is Used + Diagnostic Logging

## Objective
Add diagnostic logging to the LLM client creation and W2 worker execution paths so operators can immediately see whether the LLM path is active or the offline fallback is being used, with clear remediation guidance when LLM is unavailable.

## Problem Statement
LLM calls failed silently — `api_key=None` was passed through to `create_llm_client_from_config()` without any warning. The W2 worker logged no indication of whether it was using LLM or offline mode. When `code_understanding` fell back to offline, the exception handler provided no guidance on what went wrong or how to fix it.

## Scope

### In scope
- WARNING in llm_provider.py when api_key is None (with remediation message)
- Structured LLM path summary log in worker.py (model, api_base_url, api_key_present, fallback_configured)
- Offline path WARNING in worker.py ("Documentation quality will be limited")
- Enhanced error context in code_understanding exception handler (error_type, is_auth_error, suggestion)

### Out of scope
- Changing LLM client behavior (still creates client even with None key for unauthenticated endpoints)
- Modifying run_config schema
- Adding new test infrastructure

## Acceptance criteria
1. WARNING logged when api_key is None in create_llm_client_from_config()
2. LLM path logs model, api_base_url, api_key_present, fallback_configured
3. Offline path logs WARNING with "Documentation quality will be limited"
4. Code understanding exception handler includes error_type and is_auth_error
5. All existing tests pass (no behavioral changes)
