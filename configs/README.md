# Run Configs

This folder is the recommended place to store validated `run_config.yaml` files for launches.

## Suggested layout (recommended)
- `configs/pilots/`  : pinned pilot configs used for determinism regression tests
- `configs/products/`: real product configs (one per product_slug)

The runner should accept a config path, for example:
- `launch_run --config configs/products/aspose-note-python-foss.yaml`

## Binding rules
- A run MUST copy the exact validated config into `RUN_DIR/run_config.yaml` before any work starts.
- Pilot configs MUST pin:
  - `github_ref` (commit SHA)
  - `site_ref` (commit SHA)
  - `ruleset_version` and `templates_version`
  - `allowed_paths`


## Templates
- `configs/products/_template.run_config.yaml`
- `configs/pilots/_template.pinned.run_config.yaml`
