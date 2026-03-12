"""Check that install/getting-started pages use the correct install command.

TC-HO-02: Emits WRONG_INSTALL_COMMAND when a getting_started/installation/
quickstart page contains shell code blocks but none of them match the
deterministically-extracted ``product_evidence.install_recipe.install_command``.
"""
from __future__ import annotations

import logging
import re

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)

# Page roles where install command verification is meaningful.
_INSTALL_ROLES: frozenset[str] = frozenset({
    "getting_started",
    "installation",
    "quickstart",
})

# Regex to extract all fenced code block bodies (``` ... ```)
_CODE_BLOCK_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def _extract_code_blocks(content: str) -> list[str]:
    """Return a list of code block bodies from fenced markdown blocks."""
    return _CODE_BLOCK_RE.findall(content)


def check_install_recipe(
    content: str,
    slug: str,
    *,
    page_role: str = "",
    product_evidence: "dict | None" = None,
) -> "list[Finding]":
    """Check that install/getting-started pages use the expected install command.

    Only runs for pages with ``page_role`` in
    ``{"getting_started", "installation", "quickstart"}``.

    Logic:
    1. Skip if page_role is not an install role.
    2. Extract ``install_recipe`` from ``product_evidence``; skip if None or
       if ``install_command`` is empty.
    3. Extract all fenced code blocks from content.
    4. Skip if no code blocks found (don't penalise pages with no code).
    5. If code blocks exist but none contain the expected install_command
       (substring match) → emit WRONG_INSTALL_COMMAND finding.

    Args:
        content: Generated markdown content for the page.
        slug: Page slug for Finding location attribution.
        page_role: Hugo page role — check only runs for install roles.
        product_evidence: Dict loaded from understand_checkpoint.json. When
            None or empty, the check returns [] immediately.

    Returns:
        List of Findings. Each Finding has check="wrong_install_command",
        severity="high". Returns [] when no violation is detected.
    """
    # Only relevant for install-oriented page roles
    if page_role not in _INSTALL_ROLES:
        return []

    if not product_evidence:
        return []

    # Extract install_recipe — supports both dict and InstallRecipe model
    install_recipe_raw = product_evidence.get("install_recipe")
    if install_recipe_raw is None:
        return []

    # Get install_command from dict or model attribute
    if hasattr(install_recipe_raw, "install_command"):
        install_command = install_recipe_raw.install_command or ""
    else:
        install_command = install_recipe_raw.get("install_command", "") or ""

    if not install_command:
        return []

    # Extract all fenced code blocks
    code_blocks = _extract_code_blocks(content)
    if not code_blocks:
        return []

    # Check if any code block contains the expected install command (substring match)
    install_command_lower = install_command.lower()
    for block in code_blocks:
        if install_command_lower in block.lower():
            return []

    # Code blocks exist but none contain the expected install command
    logger.warning(
        "[install_recipe_check] slug=%s expected_command=%r not found in %d code block(s)",
        slug, install_command, len(code_blocks),
    )
    return [
        Finding(
            check="wrong_install_command",
            message=(
                f"Install page lacks expected install command "
                f"'{install_command}' — found {len(code_blocks)} code block(s) "
                f"but none contain the expected command"
            ),
            severity="high",
            location=slug,
        )
    ]
