from __future__ import annotations

import logging
from pathlib import Path

from launcher.models.product import PlatformProfile

logger = logging.getLogger(__name__)

PLATFORM_LANG_MAP: dict[str, str] = {
    "python": "python",
    "java": "java",
    "dotnet": "csharp",
    "node": "javascript",
}

_INSTALL_COMMANDS: dict[str, str] = {
    "python": "pip install {package}",
    "java": "mvn dependency:resolve -Dartifact={package}",
    "dotnet": "dotnet add package {package}",
    "node": "npm install {package}",
}

_IMPORT_PATTERNS: dict[str, str] = {
    "python": "import {family}",
    "java": "import com.aspose.{family}.*;",
    "dotnet": "using Aspose.{Family};",
    "node": "const {family} = require('{family}');",
}

# --- Default platform profiles (used when families.yaml is unavailable) ---

_DEFAULT_PROFILES: dict[str, dict] = {
    "python": {
        "lang_tag": "python",
        "import_tpl": "aspose_{family}_foss",
        "install_cmd": "pip install aspose-{family}-foss",
        "runtime_import_tpl": "aspose.{family}",
        "runtime_import_overrides": {"3d": "aspose.threed"},
        "file_ext": ".py",
        "doc_comment": "docstring",
        "ast_parser": "python_ast",
        "import_stmt_tpl": "from {import_path} import {class}",
    },
    "java": {
        "lang_tag": "java",
        "import_tpl": "com.aspose.{family}",
        "install_cmd": "maven",
        "file_ext": ".java",
        "doc_comment": "javadoc",
        "ast_parser": "tree_sitter",
        "import_stmt_tpl": "import {import_path}.{class};",
    },
    "dotnet": {
        "lang_tag": "csharp",
        "import_tpl": "Aspose.{Family}",
        "install_cmd": "dotnet add package Aspose.{Family}",
        "file_ext": ".cs",
        "doc_comment": "xmldoc",
        "ast_parser": "tree_sitter",
        "import_stmt_tpl": "using {import_path};",
    },
    "node": {
        "lang_tag": "javascript",
        "import_tpl": "@aspose/{family}",
        "install_cmd": "npm install @aspose/{family}",
        "file_ext": ".ts",
        "doc_comment": "jsdoc",
        "ast_parser": "tree_sitter",
        "import_stmt_tpl": "import {{ {class} }} from '{import_path}';",
    },
    "typescript": {
        "lang_tag": "typescript",
        "import_tpl": "@aspose/{family}",
        "install_cmd": "npm install @aspose/{family}",
        "file_ext": ".ts",
        "doc_comment": "jsdoc",
        "ast_parser": "tree_sitter",
        "import_stmt_tpl": "import {{ {class} }} from '{import_path}';",
    },
    "cpp": {
        "lang_tag": "cpp",
        "import_tpl": "aspose-{family}",
        "install_cmd": "vcpkg install aspose-{family}",
        "file_ext": ".cpp",
        "doc_comment": "doxygen",
        "ast_parser": "tree_sitter",
        "import_stmt_tpl": "#include <{import_path}/{class}.h>",
    },
}


def resolve_platform_profile(
    platform: str,
    family: str = "",
    families_config: dict | None = None,
) -> PlatformProfile:
    """Resolve a complete PlatformProfile from families.yaml config + family.

    Args:
        platform: Platform identifier (e.g. "python", "dotnet", "node").
        family: Family identifier (e.g. "cells", "3d"). Used to resolve
            templates into concrete values.
        families_config: Parsed families.yaml dict. When None, uses
            built-in defaults.

    Returns:
        Fully resolved PlatformProfile with templates expanded for the
        given family.
    """
    # Load platform config from families.yaml or defaults
    profile_data: dict = {}

    if families_config and "platforms" in families_config:
        yaml_platform = families_config["platforms"].get(platform, {})
        if yaml_platform:
            profile_data = {
                "lang_tag": yaml_platform.get("lang_tag", platform),
                "import_tpl": yaml_platform.get("import_tpl", ""),
                "install_cmd": yaml_platform.get("install_cmd", ""),
                "runtime_import_tpl": yaml_platform.get("runtime_import_tpl", ""),
                "runtime_import_overrides": yaml_platform.get("runtime_import_overrides", {}),
                "file_ext": yaml_platform.get("file_ext", ".py"),
                "doc_comment": yaml_platform.get("doc_comment", "docstring"),
                "ast_parser": yaml_platform.get("ast_parser", "python_ast"),
                "import_stmt_tpl": yaml_platform.get("import_stmt_tpl", ""),
            }

    if not profile_data:
        profile_data = dict(_DEFAULT_PROFILES.get(platform, _DEFAULT_PROFILES["python"]))

    # Resolve templates with family
    family_lower = family.lower() if family else ""
    family_cap = family.capitalize() if family else ""
    family_dash = family_lower.replace("_", "-")

    import_tpl = profile_data.get("import_tpl", "")
    install_cmd_tpl = profile_data.get("install_cmd", "")
    runtime_import_tpl = profile_data.get("runtime_import_tpl", "")
    runtime_overrides = profile_data.get("runtime_import_overrides", {})

    # Resolve package name from import template
    package_name = ""
    if import_tpl and family_lower:
        package_name = import_tpl.format(family=family_lower, Family=family_cap)

    # Resolve install command
    install_command = ""
    if install_cmd_tpl and family_lower:
        install_command = install_cmd_tpl.format(
            family=family_lower, Family=family_cap,
            package=package_name,
        )

    # Resolve import path (with override support)
    import_path = ""
    if family_lower in runtime_overrides:
        import_path = runtime_overrides[family_lower]
    elif runtime_import_tpl and family_lower:
        import_path = runtime_import_tpl.format(family=family_lower, Family=family_cap)
    elif package_name:
        import_path = package_name

    return PlatformProfile(
        platform=platform,
        lang_tag=profile_data.get("lang_tag", platform),
        import_tpl=import_tpl,
        install_cmd=install_cmd_tpl,
        runtime_import_tpl=runtime_import_tpl,
        runtime_import_overrides=runtime_overrides,
        file_ext=profile_data.get("file_ext", ".py"),
        doc_comment=profile_data.get("doc_comment", "docstring"),
        ast_parser=profile_data.get("ast_parser", "python_ast"),
        import_stmt_tpl=profile_data.get("import_stmt_tpl", ""),
        package_name=package_name,
        import_path=import_path,
        install_command=install_command,
    )


def get_lang_tag(platform: str) -> str:
    """Return the language tag for a platform.

    Falls back to the platform name itself if not in the map.
    """
    return PLATFORM_LANG_MAP.get(platform, platform)


def get_install_cmd(platform: str, package: str) -> str:
    """Return the canonical install command for *platform* and *package*.

    Falls back to ``pip install <package>`` for unknown platforms.
    """
    template = _INSTALL_COMMANDS.get(platform, "pip install {package}")
    return template.format(package=package)


def format_import(platform: str, family: str) -> str:
    """Produce a canonical import statement for *family* on *platform*.

    For .NET the family name is title-cased (e.g. ``Aspose.Cells``).
    For other platforms the family is kept lowercase.
    """
    template = _IMPORT_PATTERNS.get(platform, "import {family}")
    return template.format(
        family=family.lower(),
        Family=family.capitalize(),
    )
