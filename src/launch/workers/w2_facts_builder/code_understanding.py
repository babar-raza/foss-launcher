"""TC-1410: LLM-powered code understanding for W2 FactsBuilder.

Sends key source files to the LLM to build a structured understanding of the
codebase — class profiles, core concepts, usage workflows, and API
relationships.  The resulting ``code_understanding.json`` artifact is consumed
by W5 SectionWriter to produce richer, grounded content with real code
examples instead of pseudocode.

Offline fallback: When no LLM is available, generates minimal profiles from
AST data (docstrings, class/method names) already extracted by code_analyzer.

Spec references:
- specs/03_product_facts_and_evidence.md (Source quality tagging)
- specs/07_code_analysis_and_enrichment.md (Code analysis)
- specs/21_worker_contracts.md (W2 FactsBuilder contract)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...clients.llm_provider import LLMProviderClient, LLMError
from ...util.logging import get_logger

logger = get_logger()

# Maximum source chars to send per file to LLM
MAX_SOURCE_CHARS_PER_FILE = 4000
# Maximum number of source files to send to LLM
MAX_FILES_TO_LLM = 20
# Maximum completion tokens for code understanding LLM call
CODE_UNDERSTANDING_MAX_TOKENS = 16384
# Maximum classes to send with full details to LLM (rest sent as names only)
MAX_CLASSES_TO_LLM = 30


def _identify_public_api_files(
    code_analysis: Dict[str, Any],
    repo_dir: Path,
) -> List[Path]:
    """Identify the most important public API source files.

    Prioritizes files containing top-N classes (by public method count) and
    deprioritizes internal/parser paths. Returns up to MAX_FILES_TO_LLM files.
    """
    api_surface = code_analysis.get("api_surface", {})
    classes = api_surface.get("classes", [])

    # Build set of all public class names
    class_names = set()
    for cls in classes:
        name = cls.get("name", cls) if isinstance(cls, dict) else cls
        class_names.add(name)

    # Build set of top-N important classes (by public method count)
    top_class_names = set()
    if classes and isinstance(classes[0], dict):
        sorted_by_methods = sorted(
            classes,
            key=lambda c: len([m for m in c.get("methods", []) if not m.startswith("_")]),
            reverse=True,
        )
        top_class_names = {c.get("name", "") for c in sorted_by_methods[:MAX_CLASSES_TO_LLM]}

    # Internal/parser path segments to deprioritize
    internal_segments = {'formats/', 'parsers/', 'internal/', '_impl/', 'util/', 'compat/'}

    # Discover Python source files
    source_files: List[Path] = []
    for ext in (".py",):
        source_files.extend(repo_dir.rglob(f"*{ext}"))

    # Skip hidden dirs, test dirs, __pycache__
    skip_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules"}

    def _should_skip(p: Path) -> bool:
        for part in p.relative_to(repo_dir).parts:
            if part in skip_dirs or part.startswith("."):
                return True
            if part in ("tests", "test", "__tests__"):
                return True
        return False

    candidates = []
    for fp in source_files:
        if _should_skip(fp):
            continue
        if fp.name.startswith("_") and fp.name != "__init__.py":
            continue
        try:
            content = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # Count public classes in this file, distinguishing top-priority vs other
        top_cls_count = 0
        other_cls_count = 0
        for name in class_names:
            if re.search(rf"\bclass\s+{re.escape(name)}\b", content):
                if name in top_class_names:
                    top_cls_count += 1
                else:
                    other_cls_count += 1

        fn_count = content.count("def ")
        size = len(content)

        # Deprioritize internal/parser paths (0.5x weight)
        rel_str = str(fp.relative_to(repo_dir)).lower().replace('\\', '/')
        is_internal = any(seg in rel_str for seg in internal_segments)
        path_weight = 0.5 if is_internal else 1.0

        # Score: top classes weighted 10x, path penalty for internal files
        score = (top_cls_count * 10 + other_cls_count) * path_weight
        candidates.append((fp, score, fn_count, size))

    # Sort: highest score first, then most functions, then largest
    candidates.sort(key=lambda t: (-t[1], -t[2], -t[3]))
    return [c[0] for c in candidates[:MAX_FILES_TO_LLM]]


def _truncate_source(content: str, max_chars: int = MAX_SOURCE_CHARS_PER_FILE) -> str:
    """Truncate source content to max_chars, preferring complete lines."""
    if len(content) <= max_chars:
        return content
    truncated = content[:max_chars]
    # Cut at last newline to avoid mid-line truncation
    last_nl = truncated.rfind("\n")
    if last_nl > max_chars // 2:
        truncated = truncated[:last_nl]
    return truncated + "\n# ... (truncated)"


def _build_llm_messages(
    file_contents: List[Dict[str, str]],
    product_name: str,
    code_analysis: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Build LLM prompt for code understanding."""
    # Compact summary of what AST found
    api_surface = code_analysis.get("api_surface", {})
    classes_list = api_surface.get("classes", [])
    funcs_list = api_surface.get("functions", [])

    # Format all class names
    all_class_names = []
    for cls in classes_list:
        name = cls.get("name", cls) if isinstance(cls, dict) else cls
        all_class_names.append(name)

    # Sort classes by public method count (most methods = most important)
    # Send top N with full details, rest as names-only summary
    if classes_list and isinstance(classes_list[0], dict):
        sorted_classes = sorted(
            classes_list,
            key=lambda c: len([m for m in c.get("methods", []) if not m.startswith("_")]),
            reverse=True,
        )
        top_classes = sorted_classes[:MAX_CLASSES_TO_LLM]
        top_names = [c.get("name", "") for c in top_classes]
        remaining_names = [c.get("name", "") for c in sorted_classes[MAX_CLASSES_TO_LLM:] if c.get("name", "")]
    else:
        top_names = all_class_names[:MAX_CLASSES_TO_LLM]
        remaining_names = all_class_names[MAX_CLASSES_TO_LLM:]

    ast_summary = f"AST found {len(all_class_names)} public classes.\n"
    if len(all_class_names) > MAX_CLASSES_TO_LLM:
        ast_summary += f"Top {len(top_names)} classes (by method count): {', '.join(top_names)}\n"
        if remaining_names:
            ast_summary += f"Other classes (names only): {', '.join(remaining_names[:50])}\n"
    else:
        ast_summary += f"Classes: {', '.join(all_class_names)}\n"
    ast_summary += f"AST found {len(funcs_list)} public functions/methods"

    # Build source code section
    source_sections = []
    for fc in file_contents:
        source_sections.append(f"### File: {fc['path']}\n```python\n{fc['content']}\n```")

    source_code = "\n\n".join(source_sections)

    # Supplement prompt with AST details for top classes whose source wasn't included
    if classes_list and isinstance(classes_list[0], dict):
        included_class_names = set()
        for fc in file_contents:
            fc_content = fc["content"]
            for name in all_class_names:
                if re.search(rf"\bclass\s+{re.escape(name)}\b", fc_content):
                    included_class_names.add(name)

        top_classes_data = sorted_classes[:MAX_CLASSES_TO_LLM] if 'sorted_classes' in dir() else []
        if not top_classes_data:
            top_classes_data = sorted(
                classes_list,
                key=lambda c: len([m for m in c.get("methods", []) if not m.startswith("_")]),
                reverse=True,
            )[:MAX_CLASSES_TO_LLM]

        missing_top = [c for c in top_classes_data if c.get("name", "") not in included_class_names]
        if missing_top:
            ast_supplement = "\n\n## AST-Only Class Details (source not included — use these for minimal profiles)\n"
            for cls in missing_top[:20]:
                cname = cls.get("name", "")
                cdoc = cls.get("docstring", "")
                cbases = cls.get("bases", [])
                cmethods = [m for m in cls.get("methods", []) if not m.startswith("_")]
                cdetails = cls.get("method_details", [])

                ast_supplement += f"\n**{cname}**"
                if cbases:
                    ast_supplement += f" (extends {', '.join(cbases)})"
                if cdoc:
                    ast_supplement += f": {cdoc}"
                ast_supplement += f"\n  Public methods: {', '.join(cmethods[:10])}\n"
                for md in cdetails[:5]:
                    sig = md.get("signature", "")
                    mdoc = md.get("docstring", "")
                    if sig:
                        ast_supplement += f"  - {md.get('name', '')}({sig})"
                    else:
                        ast_supplement += f"  - {md.get('name', '')}"
                    if mdoc:
                        ast_supplement += f" — {mdoc}"
                    ast_supplement += "\n"

            source_code += ast_supplement

    # Add conciseness instruction when there are many classes
    conciseness_note = ""
    if len(all_class_names) > MAX_CLASSES_TO_LLM:
        conciseness_note = (
            f"\n\nIMPORTANT: Focus your class_profiles on the top {len(top_names)} classes "
            f"listed above. Mention other classes only in api_relationships if relevant. "
            f"Keep class_profiles concise to avoid output truncation."
            f"\n- For classes with AST-only details (no full source code), create minimal profiles "
            f"using the provided method names, signatures, and docstrings. Generate "
            f"a realistic code snippet showing class instantiation and 1-2 key method calls "
            f"as typical_usage, based on the provided method names and signatures. "
            f"Example format: 'obj = ClassName()\\nobj.method1()\\nobj.method2()'"
        )

    system_msg = (
        "You are a technical documentation expert. Analyze the source code of a "
        "software library and produce a structured JSON understanding of its API.\n\n"
        "Your output MUST be a single JSON object with these fields:\n"
        "- product_summary (string): 1-2 sentence description of what the library does\n"
        "- core_concepts (array): Key concepts a user should understand. Each has: "
        "concept (string), explanation (string), api (array of class/function names), level (beginner|intermediate|advanced)\n"
        "- class_profiles (array): For each major class: name, module, purpose (string), "
        "key_methods (array of {name, signature, purpose, example}), relationships (array of related class names), "
        "typical_usage (string with code example)\n"
        "- usage_workflows (array): Common workflows. Each has: name, description, "
        "steps (array of {step, description, code}), api_involved (array)\n"
        "- api_relationships (object): Map of class name -> array of related class names\n"
        "- use_cases (array): Real-world use cases for blog/marketing content. Each has: "
        "scenario (string, brief title), description (string, 20+ words explaining the use case), "
        "benefit (string, key value proposition), example_domain (string, industry/domain like 'CAD', 'Game development')\n"
        "- real_world_applications (array): Industry-specific applications. Each has: "
        "industry (string), use_case (string), value_proposition (string)\n\n"
        "IMPORTANT RULES:\n"
        "- ONLY describe classes/methods that exist in the source code or AST-Only details. Do NOT invent APIs.\n"
        "- Code examples MUST use real class names, method names, and signatures.\n"
        "- Keep explanations concise and user-facing (not developer-internal).\n"
        "- Focus on what users can accomplish, not implementation details.\n"
        "- You MUST produce class_profiles for ALL classes listed in the AST-Only section.\n"
        "- For use_cases and real_world_applications, infer from the product's capabilities and typical use patterns."
        + conciseness_note
    )

    user_msg = (
        f"Product: {product_name}\n\n"
        f"## AST Analysis Summary\n{ast_summary}\n\n"
        f"## Source Code\n{source_code}\n\n"
        "Generate the JSON understanding. Return ONLY the JSON object, no markdown fences."
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def _parse_llm_response(content: str) -> Dict[str, Any]:
    """Parse LLM response, handling markdown fences and common issues."""
    cleaned = content.strip()
    # Strip markdown fences
    if cleaned.startswith("```"):
        first_nl = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_nl + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object, got {type(parsed)}")
    return parsed


def _attempt_json_repair(content: str) -> Optional[Dict[str, Any]]:
    """Attempt to repair truncated JSON by closing open brackets/braces.

    Only handles simple trailing truncation cases. Returns None if repair fails.
    """
    cleaned = content.strip()
    # Strip markdown fences
    if cleaned.startswith("```"):
        first_nl = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_nl + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    if not cleaned.startswith("{"):
        return None

    # Find last complete key-value pair (ends with ", ] or })
    last_complete = max(
        cleaned.rfind('",'),
        cleaned.rfind("],"),
        cleaned.rfind("},"),
        cleaned.rfind('"]}'),
        cleaned.rfind('"}'),
    )
    if last_complete > len(cleaned) * 0.5:
        cleaned = cleaned[: last_complete + 1]

    # Remove trailing comma
    cleaned = cleaned.rstrip(",\n\r\t ")

    # Count and close open structures
    open_brackets = cleaned.count("[") - cleaned.count("]")
    open_braces = cleaned.count("{") - cleaned.count("}")

    cleaned += "]" * max(0, open_brackets)
    cleaned += "}" * max(0, open_braces)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    return None


def _build_offline_understanding(
    code_analysis: Dict[str, Any],
    product_name: str,
    repo_dir: Path,
) -> Dict[str, Any]:
    """Build code understanding from AST data only (no LLM).

    Generates minimal but useful profiles from class names, method names,
    docstrings, and module structure.
    """
    api_surface = code_analysis.get("api_surface", {})
    positioning = code_analysis.get("positioning", {})
    constants = code_analysis.get("constants", {})

    # Product summary from positioning
    tagline = positioning.get("tagline", "")
    desc = positioning.get("short_description", "")
    product_summary = desc or tagline or f"A library called {product_name}"

    # Build class profiles from AST data
    class_profiles = []
    classes_raw = api_surface.get("classes", [])
    functions_raw = api_surface.get("functions", [])

    # Group methods by class
    class_methods: Dict[str, List[str]] = {}
    standalone_functions: List[str] = []
    for func in functions_raw:
        fname = func.get("name", func) if isinstance(func, dict) else func
        if "." in fname:
            cls_name, method_name = fname.split(".", 1)
            class_methods.setdefault(cls_name, []).append(method_name)
        else:
            standalone_functions.append(fname)

    api_relationships: Dict[str, List[str]] = {}

    for cls in classes_raw:
        name = cls.get("name", cls) if isinstance(cls, dict) else cls
        docstring = cls.get("docstring", "") if isinstance(cls, dict) else ""
        module = cls.get("module", "") if isinstance(cls, dict) else ""
        bases = cls.get("bases", []) if isinstance(cls, dict) else []
        method_details = cls.get("method_details", []) if isinstance(cls, dict) else []

        methods = class_methods.get(name, [])
        key_methods = []
        for m in sorted(methods)[:10]:
            if m.startswith("_"):
                continue
            # Look up rich method details from AST
            detail = next((md for md in method_details if md["name"] == m), None)
            if detail:
                sig = detail.get("signature", f"{m}(...)")
                mdoc = detail.get("docstring", "")
                mpurpose = mdoc.split(".")[0].strip() if mdoc else f"Method {m} of {name}"
            else:
                sig = f"{m}(...)"
                mpurpose = f"Method {m} of {name}"
            key_methods.append({
                "name": m,
                "signature": sig,
                "purpose": mpurpose,
                "example": "",
            })

        # Build purpose from docstring, base classes, or method names
        if docstring:
            purpose = docstring.split(".")[0].strip()
        elif bases:
            purpose = f"{name} extending {', '.join(bases)}"
        elif methods:
            public_methods = [m for m in methods if not m.startswith("_")]
            if public_methods:
                purpose = f"{name} providing {', '.join(public_methods[:3])}"
            else:
                purpose = f"{name} class"
        else:
            purpose = f"{name} class"

        # Build relationships from base classes
        relationships = list(bases) if bases else []
        if relationships:
            api_relationships[name] = relationships

        # Generate basic usage example from class + method names
        typical_usage = ""
        public_methods = [m for m in methods if not m.startswith("_")]
        if public_methods:
            example_lines = [f"obj = {name}()"]
            for m in public_methods[:3]:
                example_lines.append(f"obj.{m}()")
            typical_usage = "\n".join(example_lines)

        class_profiles.append({
            "name": name,
            "module": module,
            "purpose": purpose,
            "key_methods": key_methods,
            "relationships": relationships,
            "typical_usage": typical_usage,
        })

    # Core concepts: one per major class
    core_concepts = []
    for cp in class_profiles[:5]:
        core_concepts.append({
            "concept": cp["name"],
            "explanation": cp["purpose"],
            "api": [cp["name"]],
            "level": "beginner",
        })

    # Build usage workflows
    usage_workflows = []
    version = constants.get("version", "")
    if version:
        usage_workflows.append({
            "name": "Installation",
            "description": f"Install {product_name}",
            "steps": [
                {"step": 1, "description": "Install via pip", "code": f"pip install {product_name.lower().replace(' ', '-')}"},
            ],
            "api_involved": [],
        })

    # Infer workflows from method patterns (load/save/open/close)
    io_classes = [
        cp for cp in class_profiles if any(
            m["name"] in ("load", "save", "open", "close", "read", "write", "export")
            for m in cp["key_methods"]
        )
    ]
    if io_classes:
        cls = io_classes[0]
        load_method = next(
            (m for m in cls["key_methods"] if m["name"] in ("load", "open", "read")), None
        )
        save_method = next(
            (m for m in cls["key_methods"] if m["name"] in ("save", "write", "export")), None
        )
        steps = []
        step_num = 1
        steps.append({
            "step": step_num,
            "description": f"Create a {cls['name']} instance",
            "code": f"obj = {cls['name']}()",
        })
        step_num += 1
        if load_method:
            steps.append({
                "step": step_num,
                "description": f"Load data using {load_method['name']}",
                "code": f"obj.{load_method['name']}('input_file')",
            })
            step_num += 1
        if save_method:
            steps.append({
                "step": step_num,
                "description": f"Save output using {save_method['name']}",
                "code": f"obj.{save_method['name']}('output_file')",
            })

        usage_workflows.append({
            "name": "Basic Usage",
            "description": f"Basic file processing with {cls['name']}",
            "steps": steps,
            "api_involved": [cls["name"]],
        })

    return {
        "schema_version": "1.0.0",
        "product_name": product_name,
        "product_summary": product_summary,
        "core_concepts": core_concepts,
        "class_profiles": class_profiles,
        "usage_workflows": usage_workflows,
        "api_relationships": api_relationships,
        "metadata": {
            "source": "offline_ast",
            "files_sent_to_llm": 0,
            "total_tokens_used": 0,
        },
    }


def _supplement_stub_usage(
    result: Dict[str, Any],
    code_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Replace stub typical_usage with AST-generated code examples.

    When the LLM returns ``# See source code for full usage`` (or empty) for a
    class profile, this function generates a minimal but real usage example from
    the class's method names — either from the LLM's own ``key_methods`` response
    or from the ``code_analysis.api_surface.classes`` AST data.
    """
    classes_list = code_analysis.get("api_surface", {}).get("classes", [])
    class_methods: Dict[str, List[str]] = {}
    for cls in classes_list:
        if isinstance(cls, dict):
            class_methods[cls.get("name", "")] = [
                m for m in cls.get("methods", []) if not m.startswith("_")
            ]

    for profile in result.get("class_profiles", []):
        usage = profile.get("typical_usage", "")
        if usage and not usage.startswith("# See source"):
            continue  # Already has real usage — don't overwrite

        name = profile.get("name", "")
        # Prefer key_methods from LLM response (richer: has signatures/purposes)
        methods = [
            km["name"] for km in profile.get("key_methods", [])
            if isinstance(km, dict) and not km.get("name", "").startswith("_")
        ]
        # Fall back to code_analysis AST methods
        if not methods:
            methods = class_methods.get(name, [])

        if methods:
            lines = [f"obj = {name}()"]
            for m in methods[:3]:
                lines.append(f"obj.{m}()")
            profile["typical_usage"] = "\n".join(lines)

    return result


def build_code_understanding(
    code_analysis: Dict[str, Any],
    repo_dir: Path,
    product_name: str,
    llm_client: Optional[LLMProviderClient] = None,
) -> Dict[str, Any]:
    """Build structured code understanding from source analysis.

    When an LLM client is available, sends key source files to the LLM
    for deep understanding. Falls back to AST-only profiles when offline.

    Args:
        code_analysis: Result from code_analyzer.analyze_repository_code
        repo_dir: Repository root directory
        product_name: Product name for context
        llm_client: Optional LLM client for rich understanding

    Returns:
        Code understanding dict (written as code_understanding.json)
    """
    api_surface = code_analysis.get("api_surface", {})
    has_api = (
        api_surface.get("classes")
        or api_surface.get("functions")
        or api_surface.get("modules")
    )

    if not has_api:
        logger.info("code_understanding_no_api", product_name=product_name)
        return {
            "schema_version": "1.0.0",
            "product_name": product_name,
            "product_summary": f"A library called {product_name}",
            "core_concepts": [],
            "class_profiles": [],
            "usage_workflows": [],
            "api_relationships": {},
            "metadata": {
                "source": "empty",
                "files_sent_to_llm": 0,
                "total_tokens_used": 0,
            },
        }

    # Identify key source files
    api_files = _identify_public_api_files(code_analysis, repo_dir)

    if not api_files:
        logger.info("code_understanding_no_files", product_name=product_name)
        return _build_offline_understanding(code_analysis, product_name, repo_dir)

    # Read and truncate file contents
    file_contents = []
    for fp in api_files:
        try:
            raw = fp.read_text(encoding="utf-8", errors="ignore")
            content = _truncate_source(raw)
            rel_path = str(fp.relative_to(repo_dir)).replace("\\", "/")
            file_contents.append({"path": rel_path, "content": content})
        except OSError:
            continue

    if not file_contents:
        return _build_offline_understanding(code_analysis, product_name, repo_dir)

    # Try LLM path
    if llm_client is not None:
        try:
            messages = _build_llm_messages(file_contents, product_name, code_analysis)
            response = llm_client.chat_completion(
                messages,
                call_id="code_understanding",
                temperature=0.0,
                max_tokens=CODE_UNDERSTANDING_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
            raw_content = response.get("content", "")
            finish_reason = response.get("finish_reason", "stop")

            if finish_reason == "length":
                logger.warning(
                    "code_understanding_llm_truncated",
                    product_name=product_name,
                    max_tokens=CODE_UNDERSTANDING_MAX_TOKENS,
                    finish_reason=finish_reason,
                    message=(
                        f"LLM response was truncated at max_tokens={CODE_UNDERSTANDING_MAX_TOKENS}. "
                        "Attempting JSON repair before falling back to offline."
                    ),
                )
                try:
                    understanding = _parse_llm_response(raw_content)
                except (json.JSONDecodeError, ValueError):
                    repaired = _attempt_json_repair(raw_content)
                    if repaired is not None:
                        understanding = repaired
                        logger.info(
                            "code_understanding_llm_truncated_repaired",
                            product_name=product_name,
                        )
                    else:
                        raise  # will be caught by outer except, falls to offline
            else:
                understanding = _parse_llm_response(raw_content)

            # Normalize and validate
            result = {
                "schema_version": "1.0.0",
                "product_name": product_name,
                "product_summary": understanding.get("product_summary", ""),
                "core_concepts": understanding.get("core_concepts", []),
                "class_profiles": understanding.get("class_profiles", []),
                "usage_workflows": understanding.get("usage_workflows", []),
                "api_relationships": understanding.get("api_relationships", {}),
                "metadata": {
                    "source": "llm",
                    "files_sent_to_llm": len(file_contents),
                    "total_tokens_used": response.get("usage", {}).get("total_tokens", 0),
                    "llm_model": llm_client.model,
                },
            }

            # TC-1513: Replace any remaining stub typical_usage with real code
            result = _supplement_stub_usage(result, code_analysis)

            logger.info(
                "code_understanding_llm_complete",
                product_name=product_name,
                classes_profiled=len(result["class_profiles"]),
                concepts=len(result["core_concepts"]),
                workflows=len(result["usage_workflows"]),
            )
            return result

        except Exception as e:
            logger.warning(
                "code_understanding_llm_failed",
                error=str(e),
                product_name=product_name,
            )
            # Fall through to offline

    # Offline fallback
    result = _build_offline_understanding(code_analysis, product_name, repo_dir)
    logger.info(
        "code_understanding_offline_complete",
        product_name=product_name,
        classes_profiled=len(result["class_profiles"]),
    )
    return result
