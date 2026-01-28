"""Security and secrets handling module.

Binding contracts:
- specs/09_validation_gates.md (security validation)
- specs/34_strict_compliance_guarantees.md (security requirements)
- specs/11_state_and_events.md (event redaction)

This module provides:
1. Secret detection (API keys, tokens, passwords, private keys)
2. Secret redaction with placeholder generation
3. File scanning with allowlist support
4. Event log redaction
5. Security validation gate
"""

from __future__ import annotations

from .event_redactor import redact_events_log
from .file_scanner import ScanResult, scan_file, scan_directory
from .redactor import RedactionMapping, redact_text
from .secret_detector import SecretMatch, detect_secrets

__all__ = [
    "SecretMatch",
    "detect_secrets",
    "redact_text",
    "RedactionMapping",
    "scan_file",
    "scan_directory",
    "ScanResult",
    "redact_events_log",
]
