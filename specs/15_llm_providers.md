# LLM Providers (OpenAI-compatible)

## Requirement (binding)
The system MUST use **OpenAI-compatible** APIs.

Supported examples:
- Ollama (OpenAI-compatible server)
- OpenAI
- Any OpenAI-compatible gateway

The system MUST NOT rely on provider-specific features that break compatibility.

## HTTP contract
- Base URL: `{api_base_url}`
- Endpoint: `/v1/chat/completions` (or compatible)
- Must support:
  - system + user messages
  - tool/function calling (recommended)
  - JSON-mode or strongly structured output (preferred)

## Determinism defaults (binding)
- `temperature` MUST default to `0.0`.
- Use greedy decoding where available.
- All prompts MUST be hashable and logged.

## Error handling and resiliency (binding)
The system MUST implement a consistent, testable error strategy for LLM calls.

### Timeouts
- Connect timeout: 10s
- Read timeout: 120s
- Total request timeout: 180s

### Retry policy
Use a bounded retry policy (tenacity) with jitter.

Retry on:
- network timeouts
- transient transport failures
- HTTP: `429`, `500`, `502`, `503`, `504`

Do NOT retry on:
- HTTP: `400`, `401`, `403`, `404`, `422`
- schema/validation failures of the model output (treat as a deterministic prompt/constraint bug; go through the fix-loop)

Recommended defaults:
- max attempts: 5
- exponential backoff: 1s, 2s, 4s, 8s, 16s (+ random jitter)
- cap: 30s

### Idempotency + request correlation
Each LLM call MUST include a locally generated `request_id` and MUST be logged with:
- `run_id`
- `request_id`
- `model`, `base_url`
- decoding params
- prompt_hash / input_hash

If the provider supports it, pass an idempotency key header. Otherwise, implement idempotency at the caller via request_id.

### Output validation
Every structured output MUST be validated against the expected schema:
- If validation fails, emit a **BLOCKER** issue and route through the deterministic fix-loop.
- Do not silently coerce or drop fields.

### Circuit breaker (recommended)
If repeated failures occur (e.g., 5 consecutive 5xx/timeout), the orchestrator SHOULD:
- pause non-critical workers
- continue deterministic (non-LLM) steps
- fail fast with a clear summary if progress cannot continue

## Telemetry logging (binding)
Every LLM request/response MUST be logged to local-telemetry:
- prompt_hash, input_hash, tool_schema_hash
- model, base_url, decoding params
- latency, token usage (if provided)
- output_hash
- error category, status code, and retry attempt index

## Compatibility constraints (binding)
- Do not require vendor-specific tool schemas.
- Do not rely on streaming in a way that changes determinism.
- Any fallback model selection MUST be explicit in telemetry.
