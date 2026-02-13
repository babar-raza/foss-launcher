"""Model discovery script for available LLM endpoints.

Queries configured LLM endpoints (remote and local Ollama) to discover
available models and report their capabilities.

Usage:
    .venv/Scripts/python.exe scripts/discover_models.py
    .venv/Scripts/python.exe scripts/discover_models.py --remote-only
    .venv/Scripts/python.exe scripts/discover_models.py --local-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)


ENDPOINTS = {
    "remote": {
        "url": "https://llm.professionalize.com/v1/models",
        "key_env": "litellm_key",
        "label": "Remote (llm.professionalize.com)",
    },
    "local": {
        "url": "http://127.0.0.1:11434/v1/models",
        "key_env": None,
        "label": "Local Ollama (127.0.0.1:11434)",
    },
}


def discover_models(endpoint_name: str, url: str, api_key: str | None = None) -> list[dict]:
    """Query an OpenAI-compatible endpoint for available models.

    Args:
        endpoint_name: Display name for the endpoint
        url: Models endpoint URL
        api_key: Optional Bearer token

    Returns:
        List of model dicts with at least "id" key
    """
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", [])
        else:
            print(f"  [{endpoint_name}] HTTP {resp.status_code}: {resp.text[:200]}")
            return []
    except requests.exceptions.ConnectionError:
        print(f"  [{endpoint_name}] Connection refused - endpoint not reachable")
        return []
    except requests.exceptions.Timeout:
        print(f"  [{endpoint_name}] Request timed out (10s)")
        return []
    except Exception as e:
        print(f"  [{endpoint_name}] Error: {e}")
        return []


def format_model_table(models: list[dict], endpoint_label: str) -> str:
    """Format models as a markdown table.

    Args:
        models: List of model dicts
        endpoint_label: Label for the endpoint

    Returns:
        Markdown table string
    """
    if not models:
        return f"### {endpoint_label}\n\nNo models found.\n"

    lines = [
        f"### {endpoint_label}",
        "",
        "| Model ID | Created | Owned By |",
        "|----------|---------|----------|",
    ]

    for m in sorted(models, key=lambda x: x.get("id", "")):
        model_id = m.get("id", "unknown")
        created = m.get("created", "")
        owned_by = m.get("owned_by", "")
        lines.append(f"| {model_id} | {created} | {owned_by} |")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover available LLM models")
    parser.add_argument("--remote-only", action="store_true", help="Query only remote endpoint")
    parser.add_argument("--local-only", action="store_true", help="Query only local Ollama")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    targets = list(ENDPOINTS.keys())
    if args.remote_only:
        targets = ["remote"]
    elif args.local_only:
        targets = ["local"]

    all_results = {}

    for name in targets:
        cfg = ENDPOINTS[name]
        api_key = None
        if cfg["key_env"]:
            api_key = os.environ.get(cfg["key_env"])
            if not api_key:
                print(f"  [{cfg['label']}] WARNING: {cfg['key_env']} env var not set")

        print(f"Querying {cfg['label']}...")
        models = discover_models(name, cfg["url"], api_key)
        all_results[name] = models
        print(f"  Found {len(models)} model(s)")

    if args.json:
        print(json.dumps(all_results, indent=2, default=str))
        return 0

    # Print markdown summary
    print("\n" + "=" * 60)
    print("# Model Discovery Results")
    print("=" * 60 + "\n")

    for name in targets:
        cfg = ENDPOINTS[name]
        models = all_results.get(name, [])
        print(format_model_table(models, cfg["label"]))

    # Cross-reference
    if len(targets) == 2 and all_results.get("remote") and all_results.get("local"):
        remote_ids = {m.get("id") for m in all_results["remote"]}
        local_ids = {m.get("id") for m in all_results["local"]}
        overlap = remote_ids & local_ids

        print("### Cross-Reference\n")
        if overlap:
            print(f"Models available on BOTH endpoints: {', '.join(sorted(overlap))}")
        else:
            print("No overlapping models between endpoints.")

        remote_only = remote_ids - local_ids
        if remote_only:
            print(f"Remote-only models: {', '.join(sorted(remote_only))}")

        local_only = local_ids - remote_ids
        if local_only:
            print(f"Local-only models: {', '.join(sorted(local_only))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
