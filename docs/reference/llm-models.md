# LLM Model Reference

## Provider Configuration

### Primary: Custom OpenAI-Compatible Endpoint
- **Base URL**: `https://llm.professionalize.com/v1`
- **Auth**: Bearer token from env var `litellm_key`
- **Purpose**: Primary LLM provider for all workers (W2, W5, W7, W10)

### Fallback: Ollama Local
- **Base URL**: `http://127.0.0.1:11434/v1`
- **Auth**: None required (local endpoint)
- **Purpose**: Fallback when remote endpoint is unavailable (transient failures only)

## Current Model Assignments

| Pilot | Primary Model | Fallback Model | Notes |
|-------|--------------|----------------|-------|
| pilot-aspose-3d-foss-python | gemma3:12b | gemma3:12b | |
| pilot-aspose-note-foss-python | gemma3:12b | gemma3:12b | |
| pilot-aspose-cells-foss-python | gemma3:27b | gemma3:27b | Larger model for complex product |

## Workers Using LLM

| Worker | Task | Config Source |
|--------|------|--------------|
| W2 FactsBuilder | Claims extraction & enrichment | `run_config.llm` via factory |
| W5 SectionWriter | Page content generation | `run_config.llm` via factory |
| W7 ContentReviewer | LLM-based content regeneration | `run_config.llm` (when review_enabled=true) |
| W10 Fixer | Single-issue fix generation | `run_config.llm` (passed from orchestrator) |

## Fallback Behavior

1. **Primary Attempt**: Call remote endpoint with configured model
2. **Failure Classification**: Use `classify_failure()` from retry_policy.py
3. **Transient Failures** (trigger fallback): Connection errors, timeouts, HTTP 429/503/504
4. **Permanent Failures** (no fallback): HTTP 400/401/422, validation errors, logic errors
5. **Fallback Attempt**: Call Ollama local with fallback model
6. **Evidence**: Both primary failure reason and fallback result captured in evidence JSON

## Circuit Breaker (TC-3590)

A passive state machine that monitors primary endpoint health across calls and proactively routes to the Ollama fallback when the primary is detected as flaky — eliminating the per-call timeout penalty.

### States

| State | Meaning | Next |
|-------|---------|------|
| CLOSED | Normal — calls go to primary | → OPEN when trigger fires |
| OPEN | Flaky — calls skip primary, go to fallback | → HALF_OPEN after recovery_timeout_s |
| HALF_OPEN | Recovery probe — one call goes to primary | → CLOSED (success) or OPEN (failure) |

### Triggers (any one opens the circuit)

| Trigger | Default | Notes |
|---------|---------|-------|
| Consecutive transient failures | ≥ 3 | Resets to 0 on any success |
| Error rate in rolling window | > 50% | Window size: 10 calls |
| Average latency in window | > 30 s | Measured per primary attempt |

Only **transient** failures are recorded (connection errors, timeouts, HTTP 429/500/502/503/504).
Permanent failures (4xx auth/validation) are not counted — they do not trip the circuit.

### Recovery

After `recovery_timeout_s` (default 60 s) in OPEN state, one probe call is sent to the primary:
- **Probe succeeds** → CLOSED (normal operations resume)
- **Probe fails** → OPEN (recovery_timeout_s resets)

### Behavior When No Fallback

When the circuit is OPEN but `llm.fallback` is not configured, the system logs a warning and
tries the primary anyway (graceful degradation — no hard failure).

### Configuration

Auto-enabled when `llm.fallback.api_base_url` is set. Optional override in `run_config.yaml`:

```yaml
llm:
  # circuit_breaker:           # optional; auto-enabled when fallback is configured
  #   enabled: true
  #   failure_threshold: 3     # consecutive failures → OPEN
  #   error_rate_threshold: 0.5  # >50% in rolling window → OPEN
  #   window_size: 10          # rolling window size
  #   latency_threshold_s: 30.0  # avg latency > 30s → OPEN
  #   recovery_timeout_s: 60.0   # seconds before HALF_OPEN probe
```

Set `enabled: false` to disable explicitly. See `specs/schemas/run_config.schema.json` for full schema.

### Implementation

- `src/launch/resilience/circuit_breaker.py` — `CircuitBreaker`, `CircuitBreakerConfig`, `CircuitState`, `build_circuit_breaker_from_config()`
- Wired into `LLMProviderClient._chat_completion_impl()` L1 retry loop
- Thread-safe via `threading.RLock`
- Spec: `specs/15_llm_providers.md` § Circuit breaker

## API Key Configuration

### Environment Variables (priority order)
1. Config-specified: Value of env var named in `llm.api_key_env` (e.g., `litellm_key`)
2. `litellm_key` - Remote LLM endpoint key
3. `ANTHROPIC_API_KEY` - Anthropic API key
4. `OPENAI_API_KEY` - OpenAI API key

### Setup (Windows)
```powershell
[System.Environment]::SetEnvironmentVariable('litellm_key', 'your-key-here', 'User')
```

## Model Discovery

Run the discovery script to see available models:
```bash
.venv/Scripts/python.exe scripts/discover_models.py
```

## Budget Limits

All pilots enforce per-run limits:
- **Max LLM calls**: 500
- **Max LLM tokens**: 1,000,000 (input + output)
- **Max runtime**: 3,600 seconds (1 hour)

Self-hosted models (gemma3:12b, gemma3:27b) have zero API cost.

## Discovery Results

_To be filled after running `scripts/discover_models.py`._
