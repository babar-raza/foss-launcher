# LLM Provider

Canonical schemas:
- `specs/schemas/llm_request.schema.json`
- `specs/schemas/llm_response.schema.json`

## Overview

The LLM provider is the infrastructure layer that manages all LLM API calls.
Every LLM call in the pipeline passes through this layer, which handles endpoint
routing, fallback, batching, resilience, and telemetry.

---

## Endpoint Configuration

Endpoints are configured per-run in the pilot config YAML.

### Primary Endpoint

- **base_url**: `https://llm.professionalize.com/v1`
- **model**: `qwen3-next/oss`
- **api_key_env**: `litellm_key` (environment variable name)
- **temperature**: `0.0` (deterministic output)
- **max_tokens**: `6000`

### Fallback Endpoint

- **base_url**: `http://127.0.0.1:11434/v1`
- **model**: `gemma3:12b`
- **api_key_env**: none (local Ollama)
- **temperature**: `0.0`
- **max_tokens**: `6000`

### Configuration Schema

```yaml
llm:
  primary:
    base_url: "https://llm.professionalize.com/v1"
    model: "qwen3-next/oss"
  fallback:
    base_url: "http://127.0.0.1:11434/v1"
    model: "gemma3:12b"
  temperature: 0.0
  max_tokens: 6000
  max_concurrency: 4
```

---

## Fallback Chain

The provider attempts endpoints in order. Fallback triggers on failure, not on
low quality (quality is handled by the sandwich model post-LLM).

### Chain Order

1. **Primary**: Remote endpoint via LiteLLM proxy.
2. **Fallback**: Local Ollama instance.
3. **Hard fail**: If both endpoints fail, the call raises `LLMUnavailableError`.

### Fallback Triggers

| Condition | Action |
|-----------|--------|
| HTTP 5xx from primary | Retry once, then fall back |
| Connection timeout (>120s) | Fall back immediately |
| HTTP 429 rate limit | Wait + retry on primary (see rate limiting) |
| Response validation failure | Do NOT fall back (post-LLM engineering handles this) |
| Primary circuit open | Route directly to fallback |

The `fallback_count` in generation stats tracks how many calls used the fallback.

---

## Batched Concurrent Calls

The pipeline makes approximately 150 LLM calls per run (~700 tokens context
each). These are batched for throughput.

### Concurrency Model

- **max_concurrency**: Configurable (default 4). Defines the maximum number of
  simultaneous in-flight LLM calls.
- **Batch strategy**: Workers submit call batches via `asyncio.Semaphore`.
- **Ordering**: Results are collected in submission order to maintain
  deterministic output.

### Per-Section Micro-Prompts

Each LLM call generates content for a single section of a single page. This
keeps context windows small (~700 tokens) and failures isolated.

---

## Resilience

### Circuit Breaker

- **Threshold**: 3 consecutive failures, >50% error rate in a 10-call window,
  or average latency >30s on an endpoint.
- **Open duration**: Starts at 60 seconds (`recovery_timeout_s`).
- **Half-open**: After the recovery timeout elapses, allow one probe call using
  a shorter timeout (`probe_timeout_s`, default 15s). If the probe succeeds,
  close the circuit and reset all backoff state. If it fails, re-open with
  exponential backoff on the recovery interval.
- **Exponential backoff**: Each failed probe multiplies the recovery interval
  by `recovery_backoff_factor` (default 2.0), capped at
  `recovery_max_timeout_s` (default 600s). Progression: 60→120→240→480→600s.
- **Reset**: A single successful probe resets the recovery interval to the
  base value and clears the probe failure counter.
- **Scope**: Per-endpoint (primary and fallback have independent circuits).

#### Circuit Breaker Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `failure_threshold` | int | 3 | Consecutive failures to trip OPEN |
| `error_rate_threshold` | float | 0.5 | Error rate in window to trip OPEN |
| `window_size` | int | 10 | Rolling window for error rate |
| `latency_threshold_s` | float | 30.0 | Avg latency above this trips OPEN |
| `recovery_timeout_s` | float | 60.0 | Base seconds in OPEN before probe |
| `probe_timeout_s` | float | 15.0 | Shorter timeout for HALF_OPEN probes |
| `recovery_backoff_factor` | float | 2.0 | Multiplier after failed probe |
| `recovery_max_timeout_s` | float | 600.0 | Cap on backoff interval |

### Retry Policy

| Condition | Max retries | Backoff |
|-----------|:-----------:|---------|
| HTTP 5xx | 1 | 2 seconds |
| HTTP 429 | 3 | Exponential: 1s, 2s, 4s |
| Timeout | 0 | Immediate fallback |
| Connection error | 0 | Immediate fallback |

### Rate Limiting

- The provider tracks calls-per-minute per endpoint.
- If the endpoint returns HTTP 429, the provider applies the `Retry-After`
  header value or exponential backoff.
- The `max_concurrency` setting provides client-side throttling.

---

## Request/Response Contract

Every LLM call is wrapped in schema-validated envelopes.

### LLMRequest

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `call_id` | string | yes | Unique ID for tracing |
| `model` | string | yes | Model identifier |
| `messages` | Message[] | yes | Chat messages (system, user, assistant) |
| `temperature` | number | yes | Sampling temperature |
| `max_tokens` | integer | yes | Max response tokens |
| `response_format` | object | no | Structured output spec (JSON mode) |

### LLMResponse

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `call_id` | string | yes | Matching request call_id |
| `model` | string | yes | Model that produced the response |
| `content` | string | yes | Response text |
| `usage` | object | yes | Token counts (prompt + completion) |
| `finish_reason` | string | yes | Stop reason (stop, length) |
| `duration_ms` | number | yes | Round-trip latency |

---

## Evidence and Telemetry

Every LLM call emits an `llm_call_completed` event to the event stream.

### Event Payload

- `call_id`: Links to the request.
- `model`: Actual model used (may differ from requested if fallback fired).
- `endpoint`: Which endpoint was used (`primary` or `fallback`).
- `prompt_tokens`, `completion_tokens`: For cost tracking.
- `duration_ms`: Latency measurement.
- `retries`: Number of retries before success.
- `cache_hit`: Whether the response was served from disk cache.

### Reasoning Content

Some models return `reasoning_content` in addition to `content`. The provider
extracts reasoning content when present and stores it in the event payload for
debugging, but it is not used in pipeline logic.
