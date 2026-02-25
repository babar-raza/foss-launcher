"""GitHub organization intake system for FOSS Launcher.

Discovers, classifies, and onboards repositories from GitHub organizations
into the FOSS Launcher pipeline.

Modules:
    config_loader    - Persistent YAML config loading with platform support
    org_scanner      - Paginated GitHub API repo discovery with rate limiting
    repo_classifier  - Deterministic eligibility classification
    config_generator - Pilot config YAML generation (platform-aware)
    scheduler        - Priority queue with batch and dry-run modes

Spec reference: specs/49_github_intake.md
Schema: specs/schemas/intake_config.schema.json
TC: TC-2539, TC-2540, TC-2541, TC-2542, TC-2543, TC-2544, TC-2545
"""
