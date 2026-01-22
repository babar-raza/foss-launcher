# Hugo Config Snapshot (reference)

This folder contains a **snapshot** of the `aspose.org` Hugo `configs/` directory that was provided alongside the specs.

## Purpose
- Enables deterministic unit/integration tests for:
  - config discovery
  - build-matrix inference
  - `hugo_config` gate behavior

## Binding rule
At runtime, the system MUST read configs from the cloned site repo:
- `RUN_DIR/work/site/configs/`

This snapshot MUST NOT be used as the runtime source of truth.
See `specs/31_hugo_config_awareness.md`.
