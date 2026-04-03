#!/usr/bin/env python3
"""Standalone quality-metrics scanner for foss-launcher v2.

Scans a directory of .md files for G1--G7 defects and emits a JSON report
plus an optional Markdown summary.

Defect categories
-----------------
G1  LLM artifact phrases
G2  Near-duplicate sentences (Jaccard >= 0.7)
G3  Unknown identifiers (backticked names not in allowlist)
G4  Structural issues (duplicate H2s, content after See Also, missing H2s)
G5  Product-name misspellings
G6  Duplicate slugs across files
G7  Forbidden patterns (pipeline artifacts, placeholders, leaks)

Usage::

    python scripts/quality_metrics.py --dir deploy/docs.aspose.org/cells/python \\
        --output metrics.json --summary metrics.md \\
        --allowlist knowledge/cells/python/api_surface.md \\
        --product-name "Aspose.Cells"

Compare mode::

    python scripts/quality_metrics.py --compare before.json after.json
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Import from launcher package when available; fall back to inline
# ---------------------------------------------------------------------------

# G1: artifact phrases
try:
    from launcher.workers.evaluate.checks.artifacts import _ARTIFACT_PHRASES
except ImportError:
    _ARTIFACT_PHRASES = [
        "let's explore",
        "let's dive",
        "as mentioned earlier",
        "as we discussed",
        "i hope this helps",
        "feel free to",
        "don't hesitate",
        "happy coding",
        "in conclusion",
        "to summarize",
        "as an ai",
        "i'm an ai",
        "certainly!",
        "absolutely!",
        "great question",
        "it is important to note",
        "plays a crucial role",
        "a powerful tool",
        "what the reader will build",
        "class or function purpose",
        "section title here",
        "in 1-3 sentences",
        "[fill in",
        "[content to be",
    ]

# G5: product-name patterns
try:
    from launcher.workers.evaluate.checks.product_names import _build_patterns
except ImportError:

    def _build_patterns(product_name: str) -> list[tuple[re.Pattern[str], str]]:
        """Inline fallback for product-name misspelling patterns."""
        patterns: list[tuple[re.Pattern[str], str]] = []
        parts = product_name.split(".", 1)
        prefix, suffix = parts[0], parts[1] if len(parts) > 1 else ""
        if prefix.lower() == "aspose":
            for typo in ["Aspire", "Aspuse", "Apose", "Aspsoe", "Asopse"]:
                if suffix:
                    patterns.append((
                        re.compile(rf"\b{typo}[.\s]{suffix}\b", re.IGNORECASE),
                        f"Misspelled product prefix: '{typo}' should be '{prefix}'",
                    ))
                else:
                    patterns.append((
                        re.compile(rf"\b{typo}\b", re.IGNORECASE),
                        f"Misspelled product prefix: '{typo}' should be '{prefix}'",
                    ))
        if suffix:
            patterns.append((
                re.compile(rf"\b{re.escape(prefix)}\s+{re.escape(suffix)}\b"),
                f"Missing dot: '{prefix} {suffix}' should be '{product_name}'",
            ))
            patterns.append((
                re.compile(r"\bfor\s+(\w+)\s+for\s+\1\b", re.IGNORECASE),
                "Doubled qualifier",
            ))
            if prefix[0].isupper() or suffix[0].isupper():
                patterns.append((
                    re.compile(
                        rf"\b{re.escape(prefix.lower())}\.{re.escape(suffix.lower())}\b"
                    ),
                    f"Wrong case: should be '{product_name}'",
                ))
        return patterns


# G7: forbidden patterns
try:
    from launcher.shared.forbidden_patterns import scan_forbidden
except ImportError:

    def scan_forbidden(content: str) -> list[tuple[str, str, str, int]]:
        """Inline fallback forbidden-pattern scanner."""
        _pats = [
            (re.compile(r"\[identifier omitted\]", re.IGNORECASE), "hallucinated_identifier", "critical", "Hallucinated identifier"),
            (re.compile(r"#\s*source:\s*snippet_\d+"), "internal_metadata", "high", "Internal traceability comment"),
            (re.compile(r"CLM-[a-z]+-[a-f0-9]+:"), "claim_id_leak", "critical", "Internal claim ID"),
            (re.compile(r"\[CLM-[^\]]*\]"), "claim_id_leak", "critical", "Internal claim citation"),
            (re.compile(r"\[Content to be generated\]", re.IGNORECASE), "template_placeholder", "critical", "Template placeholder"),
            (re.compile(r"\b\d+-\d+\s+sentences\b"), "template_placeholder", "high", "Template length hint"),
            (re.compile(r"docs\.example\.com"), "placeholder_url", "high", "Placeholder URL"),
            (re.compile(r"\(link-to-[a-z-]+\)"), "placeholder_link", "high", "Placeholder link"),
            (re.compile(r"\b\d+%\s*confidence\b", re.IGNORECASE), "llm_reasoning_leak", "high", "LLM reasoning leak"),
        ]
        results = []
        for regex, cat, sev, desc in _pats:
            matches = regex.findall(content)
            if matches:
                results.append((cat, sev, desc, len(matches)))
        return results


# ---------------------------------------------------------------------------
# Helper: code-block and frontmatter stripping
# ---------------------------------------------------------------------------

def _strip_code_blocks(content: str) -> str:
    """Remove fenced code blocks, replacing their lines with blanks."""
    lines = content.split("\n")
    in_block = False
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_block = not in_block
            result.append("")
        elif in_block:
            result.append("")
        else:
            result.append(line)
    return "\n".join(result)


def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter delimited by --- fences."""
    if not content.startswith("---"):
        return content
    end = content.find("\n---", 3)
    return content[end + 4:] if end != -1 else content


def _parse_frontmatter(content: str) -> dict[str, str]:
    """Extract key: value pairs from YAML frontmatter (flat, string-only)."""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    fm_block = content[4:end]
    result: dict[str, str] = {}
    for line in fm_block.split("\n"):
        m = re.match(r"^(\w[\w_]*)\s*:\s*(.+)$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip("\"'")
            result[key] = val
    return result


# ---------------------------------------------------------------------------
# Allowlist loader
# ---------------------------------------------------------------------------

def load_allowlist(path: str | None) -> set[str]:
    """Load API identifiers from an api_surface.md file.

    Format::

        ## ClassName
        **Methods**:
        - `method_name(args) -> ret`
        **Properties**:
        - `prop_name: type  [readonly]`

    Returns a set of all class names, method names, and property names.
    """
    if not path or not os.path.isfile(path):
        return set()
    text = Path(path).read_text(encoding="utf-8")
    ids: set[str] = set()

    for m in re.finditer(r"^## (\w+)", text, re.MULTILINE):
        ids.add(m.group(1))

    for m in re.finditer(r"`(\w+)\s*\(", text):
        ids.add(m.group(1))

    for m in re.finditer(r"`(\w+)\s*:", text):
        ids.add(m.group(1))

    # Remove common noise words
    ids.discard("none")
    ids.discard("None")
    return ids


# ---------------------------------------------------------------------------
# Defect dataclass
# ---------------------------------------------------------------------------

@dataclass
class Defect:
    """A single defect instance."""

    gate: str         # G1..G7
    message: str
    count: int = 1


# ---------------------------------------------------------------------------
# FileMetrics / DirectoryMetrics
# ---------------------------------------------------------------------------

@dataclass
class FileMetrics:
    """Per-file defect metrics."""

    path: str
    slug: str = ""
    page_role: str = ""
    defects: list[Defect] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(d.count for d in self.defects)

    def counts_by_gate(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for d in self.defects:
            result[d.gate] = result.get(d.gate, 0) + d.count
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "slug": self.slug,
            "page_role": self.page_role,
            "total": self.total,
            "by_gate": self.counts_by_gate(),
            "defects": [dataclasses.asdict(d) for d in self.defects],
        }


@dataclass
class DirectoryMetrics:
    """Aggregate metrics across a directory of files."""

    files: list[FileMetrics] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_defects(self) -> int:
        return sum(f.total for f in self.files)

    @property
    def files_with_defects(self) -> int:
        return sum(1 for f in self.files if f.total > 0)

    def counts_by_gate(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for f in self.files:
            for gate, count in f.counts_by_gate().items():
                result[gate] = result.get(gate, 0) + count
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files": self.total_files,
            "total_defects": self.total_defects,
            "files_with_defects": self.files_with_defects,
            "by_gate": self.counts_by_gate(),
            "files": [f.to_dict() for f in self.files],
        }


# ---------------------------------------------------------------------------
# Gate checks
# ---------------------------------------------------------------------------

_WHEN_WORKING_RE = re.compile(
    r"(?m)^(?:#+\s+.+\n+)?When working with\b", re.IGNORECASE
)


def _check_g1(prose: str) -> list[Defect]:
    """G1: LLM artifact phrases."""
    defects: list[Defect] = []
    lower = prose.lower()
    for phrase in _ARTIFACT_PHRASES:
        n = lower.count(phrase)
        if n:
            defects.append(Defect(gate="G1", message=f"Artifact phrase: '{phrase}'", count=n))
    # "When working with" opener
    matches = _WHEN_WORKING_RE.findall(prose)
    if matches:
        defects.append(Defect(gate="G1", message="'When working with' section opener", count=len(matches)))
    return defects


def _tokenize_sentence(s: str) -> set[str]:
    """Tokenize a sentence into a word set for Jaccard comparison."""
    return set(re.findall(r"\b[a-z]{3,}\b", s.lower()))


def _check_g2(prose: str) -> list[Defect]:
    """G2: Near-duplicate sentences (Jaccard >= 0.7)."""
    sentences = re.split(r"(?<=[.!?])\s+", prose)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    tokenized = [(s, _tokenize_sentence(s)) for s in sentences]
    dup_count = 0
    seen_pairs: set[tuple[int, int]] = set()
    for i in range(len(tokenized)):
        for j in range(i + 1, len(tokenized)):
            if (i, j) in seen_pairs:
                continue
            sa, sb = tokenized[i][1], tokenized[j][1]
            if not sa or not sb:
                continue
            sim = len(sa & sb) / len(sa | sb)
            if sim >= 0.7:
                dup_count += 1
                seen_pairs.add((i, j))
    if dup_count:
        return [Defect(gate="G2", message=f"{dup_count} near-duplicate sentence pair(s)", count=dup_count)]
    return []


def _check_g3(body: str, allowlist: set[str]) -> list[Defect]:
    """G3: Unknown backticked identifiers not in allowlist."""
    if not allowlist:
        return []
    # Extract backticked identifiers from the full body (including code blocks)
    ids = set(re.findall(r"`(\w+)`", body))
    # Filter: only flag identifiers that look like API names (PascalCase or snake_case
    # with length >= 3), not common words or short tokens.
    unknown: list[str] = []
    for ident in sorted(ids):
        if len(ident) < 3:
            continue
        if ident in allowlist:
            continue
        # Only flag identifiers that look like code: PascalCase, snake_case, or UPPER
        if re.match(r"^[A-Z][a-zA-Z0-9]+$", ident) or "_" in ident:
            unknown.append(ident)
    if unknown:
        return [Defect(
            gate="G3",
            message=f"{len(unknown)} unknown identifier(s): {', '.join(unknown[:10])}",
            count=len(unknown),
        )]
    return []


def _check_g4(body: str) -> list[Defect]:
    """G4: Structural issues — duplicate H2s, content after See Also, missing H2."""
    defects: list[Defect] = []

    # Extract H2 headings
    h2s = re.findall(r"^## (.+)$", body, re.MULTILINE)
    h2_lower = [h.strip().lower() for h in h2s]

    # Duplicate H2s
    seen: dict[str, int] = {}
    for h in h2_lower:
        seen[h] = seen.get(h, 0) + 1
    dups = {h: c for h, c in seen.items() if c > 1}
    for h, c in dups.items():
        defects.append(Defect(gate="G4", message=f"Duplicate H2: '{h}' ({c}x)", count=c - 1))

    # Content after "See Also" section
    see_also_m = re.search(r"^## See Also\b", body, re.MULTILINE | re.IGNORECASE)
    if see_also_m:
        after = body[see_also_m.end():]
        # Check for another H2 after See Also
        if re.search(r"^## ", after, re.MULTILINE):
            defects.append(Defect(gate="G4", message="Content section(s) after 'See Also'"))

    # No H2 headings at all (only if body has real content)
    stripped_body = body.strip()
    if stripped_body and len(stripped_body) > 100 and not h2s:
        defects.append(Defect(gate="G4", message="No H2 headings found"))

    return defects


def _check_g5(prose: str, product_name: str) -> list[Defect]:
    """G5: Product-name misspellings."""
    if not product_name:
        return []
    patterns = _build_patterns(product_name)
    defects: list[Defect] = []
    for pat, msg in patterns:
        matches = pat.findall(prose)
        if matches:
            defects.append(Defect(gate="G5", message=msg, count=len(matches)))
    return defects


def _check_g7(content: str) -> list[Defect]:
    """G7: Forbidden patterns (pipeline artifacts, placeholders, leaks)."""
    results = scan_forbidden(content)
    defects: list[Defect] = []
    for _cat, _sev, desc, count in results:
        defects.append(Defect(gate="G7", message=desc, count=count))
    return defects


# ---------------------------------------------------------------------------
# File scanner
# ---------------------------------------------------------------------------

def scan_file(
    path: str,
    *,
    allowlist: set[str] | None = None,
    product_name: str = "",
) -> FileMetrics:
    """Scan a single .md file for G1--G5 and G7 defects."""
    content = Path(path).read_text(encoding="utf-8")
    fm = _parse_frontmatter(content)
    body = _strip_frontmatter(content)
    prose = _strip_code_blocks(body)

    metrics = FileMetrics(
        path=path,
        slug=fm.get("slug", fm.get("url", "")),
        page_role=fm.get("page_role", ""),
    )

    # G1: artifact phrases (scan prose only)
    metrics.defects.extend(_check_g1(prose))

    # G2: near-duplicate sentences (scan prose only)
    metrics.defects.extend(_check_g2(prose))

    # G3: unknown identifiers (scan full body including code)
    metrics.defects.extend(_check_g3(body, allowlist or set()))

    # G4: structural issues (scan body, not code-stripped)
    metrics.defects.extend(_check_g4(body))

    # G5: product-name misspellings (scan prose only)
    metrics.defects.extend(_check_g5(prose, product_name))

    # G7: forbidden patterns (scan full content including frontmatter)
    metrics.defects.extend(_check_g7(content))

    return metrics


def scan_directory(
    directory: str,
    *,
    allowlist: set[str] | None = None,
    product_name: str = "",
) -> DirectoryMetrics:
    """Scan all .md files in a directory tree for defects.

    G6 (duplicate slugs) is checked at the directory level after all files
    are scanned.
    """
    dm = DirectoryMetrics()
    md_files = sorted(Path(directory).rglob("*.md"))

    for md_path in md_files:
        fm = scan_file(str(md_path), allowlist=allowlist, product_name=product_name)
        dm.files.append(fm)

    # G6: duplicate slugs across files
    slug_map: dict[str, list[str]] = {}
    for fm in dm.files:
        if fm.slug:
            slug_map.setdefault(fm.slug, []).append(fm.path)
    for slug, paths in slug_map.items():
        if len(paths) > 1:
            for p in paths:
                for fm in dm.files:
                    if fm.path == p:
                        fm.defects.append(Defect(
                            gate="G6",
                            message=f"Duplicate slug '{slug}' shared with {len(paths)-1} other file(s)",
                        ))
                        break

    return dm


# ---------------------------------------------------------------------------
# Compare mode
# ---------------------------------------------------------------------------

def compare_baselines(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare two JSON report dicts and compute deltas."""
    delta: dict[str, Any] = {
        "total_defects_before": before.get("total_defects", 0),
        "total_defects_after": after.get("total_defects", 0),
        "total_defects_delta": after.get("total_defects", 0) - before.get("total_defects", 0),
        "by_gate": {},
    }
    all_gates = sorted(set(list(before.get("by_gate", {}).keys()) + list(after.get("by_gate", {}).keys())))
    for gate in all_gates:
        b = before.get("by_gate", {}).get(gate, 0)
        a = after.get("by_gate", {}).get(gate, 0)
        delta["by_gate"][gate] = {"before": b, "after": a, "delta": a - b}
    return delta


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def render_summary(dm: DirectoryMetrics) -> str:
    """Render a Markdown summary table."""
    lines: list[str] = []
    lines.append("# Quality Metrics Summary\n")
    lines.append(f"- **Files scanned**: {dm.total_files}")
    lines.append(f"- **Files with defects**: {dm.files_with_defects}")
    lines.append(f"- **Total defects**: {dm.total_defects}\n")

    lines.append("## Defects by Gate\n")
    lines.append("| Gate | Count |")
    lines.append("|------|------:|")
    for gate in ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]:
        count = dm.counts_by_gate().get(gate, 0)
        lines.append(f"| {gate} | {count} |")

    lines.append("\n## Per-File Details\n")
    lines.append("| File | Total | G1 | G2 | G3 | G4 | G5 | G6 | G7 |")
    lines.append("|------|------:|---:|---:|---:|---:|---:|---:|---:|")
    for fm in sorted(dm.files, key=lambda f: f.total, reverse=True):
        gates = fm.counts_by_gate()
        cols = [str(gates.get(f"G{i}", 0)) for i in range(1, 8)]
        basename = Path(fm.path).name
        lines.append(f"| {basename} | {fm.total} | {' | '.join(cols)} |")

    return "\n".join(lines) + "\n"


def render_compare_summary(delta: dict[str, Any]) -> str:
    """Render a Markdown comparison summary."""
    lines: list[str] = []
    lines.append("# Quality Metrics Comparison\n")
    lines.append(f"- **Before**: {delta['total_defects_before']} defects")
    lines.append(f"- **After**: {delta['total_defects_after']} defects")
    d = delta["total_defects_delta"]
    sign = "+" if d > 0 else ""
    lines.append(f"- **Delta**: {sign}{d}\n")

    lines.append("## By Gate\n")
    lines.append("| Gate | Before | After | Delta |")
    lines.append("|------|-------:|------:|------:|")
    for gate, vals in sorted(delta["by_gate"].items()):
        gd = vals["delta"]
        gs = "+" if gd > 0 else ""
        lines.append(f"| {gate} | {vals['before']} | {vals['after']} | {gs}{gd} |")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan .md files for G1-G7 quality defects")
    parser.add_argument("--dir", help="Directory to scan")
    parser.add_argument("--output", help="Path for JSON output")
    parser.add_argument("--summary", help="Path for Markdown summary")
    parser.add_argument("--allowlist", help="Path to api_surface.md for G3 allowlist")
    parser.add_argument("--product-name", default="", help="Product name for G5 check (e.g. 'Aspose.Cells')")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"), help="Compare two JSON reports")
    args = parser.parse_args(argv)

    if args.compare:
        before = json.loads(Path(args.compare[0]).read_text(encoding="utf-8"))
        after = json.loads(Path(args.compare[1]).read_text(encoding="utf-8"))
        delta = compare_baselines(before, after)
        print(render_compare_summary(delta))
        if args.output:
            Path(args.output).write_text(json.dumps(delta, indent=2), encoding="utf-8")
        return 0

    if not args.dir:
        parser.error("--dir is required unless using --compare")

    allowlist = load_allowlist(args.allowlist)
    dm = scan_directory(args.dir, allowlist=allowlist, product_name=args.product_name)

    report = dm.to_dict()
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        print(json.dumps(report, indent=2))

    if args.summary:
        Path(args.summary).write_text(render_summary(dm), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
