# Patch: align telemetry docs with event schema

Update `specs/16_local_telemetry_api.md` to use `ts` instead of `timestamp` and to require trace/span IDs.

Recommended updated endpoint payload:

- POST /v1/events
  Body: { event_id, run_id, ts, type, payload, trace_id, span_id, parent_span_id? }
