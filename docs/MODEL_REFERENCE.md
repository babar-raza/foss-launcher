# LLM Model Reference

## Provider Configuration

### Primary: Custom OpenAI-Compatible Endpoint
- **Base URL**: `https://llm.professionalize.com/v1`
- **Auth**: Bearer token from env var `litellm_key`
- **Purpose**: Primary LLM provider for all workers (W2, W5, W5.5, W8)

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
| W5.5 ContentReviewer | LLM-based content regeneration | `run_config.llm` (when review_enabled=true) |
| W8 Fixer | Single-issue fix generation | `run_config.llm` (passed from orchestrator) |

## Fallback Behavior

1. **Primary Attempt**: Call remote endpoint with configured model
2. **Failure Classification**: Use `classify_failure()` from retry_policy.py
3. **Transient Failures** (trigger fallback): Connection errors, timeouts, HTTP 429/503/504
4. **Permanent Failures** (no fallback): HTTP 400/401/422, validation errors, logic errors
5. **Fallback Attempt**: Call Ollama local with fallback model
6. **Evidence**: Both primary failure reason and fallback result captured in evidence JSON

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
