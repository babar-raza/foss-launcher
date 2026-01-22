# Universal Repo Handling Guidelines

## Purpose

This document consolidates the rules for handling **diverse product repositories** with varying levels of documentation, examples, structure, and quality. The goal is to ensure the launch agent produces appropriate content regardless of whether the source repo is a sparse weekend project or a comprehensive enterprise SDK.

---

## Repo Quality Spectrum

The system must handle repos across this spectrum:

| Quality Level | Characteristics | Expected Launch Tier |
|---------------|-----------------|---------------------|
| **Sparse** | No docs folder, no examples, legacy packaging, no CI | `minimal` |
| **Basic** | README with install/usage, tests but no examples | `minimal` to `standard` |
| **Standard** | Docs folder, some examples, tests, modern packaging | `standard` |
| **Rich** | Comprehensive docs, examples, CI, explicit API scope | `rich` |

---

## Universal Discovery Rules

### 1. Documentation Discovery (binding)

The system MUST discover documentation in this priority order:

1. **Manifest-embedded docs** (pyproject.toml readme, package.json homepage)
2. **Docs folders** (`docs/`, `documentation/`, `doc/`, `site/`)
3. **Root-level technical markdown** (`*_IMPLEMENTATION.md`, `ARCHITECTURE.md`, `DESIGN.md`)
4. **README.md** (always present, but may contain marketing)
5. **API docstrings** (extracted during code analysis)

### 2. Example Discovery (binding)

The system MUST discover examples in this fallback order:

1. **Dedicated folders** (`examples/`, `samples/`, `demo/`)
2. **README code fences** (extract Quick Start blocks)
3. **Docs code fences** (extract from tutorials/guides)
4. **Tests as examples** (select tests that demonstrate usage patterns)
5. **Generated minimal snippets** (last resort, must be validated)

### 3. Binary Asset Handling (binding)

When binary files are present (`testfiles/`, `assets/`, `.one`, `.pdf`, `.png`, etc.):
- Record paths in `binary_assets`
- Do NOT send binary content to LLMs
- Snippets MAY reference binary paths but MUST NOT embed content
- Documentation MAY link to sample files

---

## Launch Tier Auto-Selection

### Default tier by evidence quality

```
IF has_ci AND has_examples AND has_docs_folder:
    tier = "rich"
ELIF has_tests AND (has_examples OR has_docs_folder):
    tier = "standard"
ELSE:
    tier = "minimal"
```

### Tier adjustment rules

| Condition | Adjustment |
|-----------|------------|
| CI present with passing badge | +1 tier (max rich) |
| CI absent | -1 tier |
| Phantom paths detected | -1 tier |
| Unresolved contradictions | Force minimal |
| Generated snippets only | Force minimal |
| >10 test files with assertions | +1 tier (partial CI credit) |

---

## Contradiction Resolution

### Evidence priority ranking

1. **Manifests** (package name, version, deps)
2. **Source code** (constants, exports)
3. **Tests** (behavioral proof)
4. **Implementation docs** (developer truth)
5. **API docstrings**
6. **README technical sections**
7. **README marketing** (LOWEST)

### Resolution process

1. Identify conflicting claims
2. Assign priority to each source
3. Winner = higher priority claim
4. Record both claims with resolution reasoning
5. If unresolvable, flag for human review

---

## Product Type Handling

### Inference signals

| Type | Signals |
|------|---------|
| `cli` | console_scripts, bin/, command examples |
| `service` | Dockerfile, api/, endpoint docs |
| `plugin` | entry-points, host app integration |
| `sdk` | "sdk" in name, client patterns |
| `library` | Import patterns (default for Python) |
| `tool` | Standalone utility |

### Template implications

Each product type has specific template requirements:
- **cli**: Install, commands, flags, exit codes
- **library/sdk**: Imports, API patterns, formats
- **service**: Deploy, endpoints, auth

---

## Platform-Specific Adapters

### Required adapter outputs

Every platform adapter MUST produce:
- `distribution` (install method + commands)
- `runtime_requirements` (language versions, OS)
- `dependencies` (runtime + optional groups)
- `public_api_entrypoints` (main entry points)
- `recommended_test_commands` (best effort)

### Platform-specific rules

**Python:**
- Check `pyproject.toml` first, fall back to `setup.py`
- Detect `src/` layout vs flat package
- Extract `[project.optional-dependencies]` as extras
- Detect `_internal` convention for API scope

**Node:**
- Check `package.json` for scripts, main, exports
- Detect monorepo via workspaces

**Dotnet:**
- Check `*.csproj` and `*.sln`
- Detect multi-project via solution structure

---

## Failure Modes and Defaults

### When evidence is missing

| Missing | Default behavior |
|---------|------------------|
| No examples | Use tests as examples, then generate minimal |
| No docs folder | Use README + root markdown |
| No version | Use "0.0.0" or "unknown" |
| No license | Flag as issue, proceed with caution |
| No tests | Reduce tier, flag in report |
| Conflicting claims | Prefer implementation notes |

### Hard failures (block launch)

- Cannot determine package name
- No README or entry point found
- All claims are contradicted
- Security concerns detected

---

## Acceptance Criteria

A repo is successfully processed when:

1. ✅ RepoInventory produced with valid repo_profile
2. ✅ ProductFacts produced with grounded claims
3. ✅ EvidenceMap maps all claims to citations
4. ✅ SnippetCatalog has at least one quickstart snippet
5. ✅ PagePlan matches launch_tier requirements
6. ✅ All contradictions resolved or flagged
7. ✅ Binary assets recorded but not parsed
8. ✅ Phantom paths detected and recorded
