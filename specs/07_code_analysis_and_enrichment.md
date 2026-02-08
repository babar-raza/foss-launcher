# Code Analysis and Enrichment Specification

**Document ID**: SPEC-007
**Status**: Active
**Version**: 1.0
**Created**: 2026-02-07
**Related Taskcards**: TC-1040, TC-1041, TC-1042
**Schema References**: `product_facts.schema.json`, `evidence_map.schema.json`

---

## 1. Goal

Extract structured information from source code to populate `api_surface_summary`, `code_structure`, and `positioning` fields in `product_facts.json`. This extraction supplements documentation-based claims with direct evidence from implementation artifacts.

Code analysis is a **sub-task of W2 FactsBuilder** and MUST complete within performance budgets (< 10% of W2 total runtime).

---

## 2. Python AST Parsing (binding)

### 2.1 Parser Selection

Use Python stdlib `ast` module (already proven in W3 SnippetCurator).

**Rationale**: No external dependencies, battle-tested, handles Python 3.7+ syntax.

### 2.2 Public Class Extraction

Extract public classes using pattern:
```python
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        if not node.name.startswith('_'):
            # node.name is public class
```

**Output**: Add to `api_surface_summary.classes[]`

### 2.3 Public Function Extraction

Extract public functions using pattern:
```python
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        if not node.name.startswith('_'):
            # node.name is public function
```

**Output**: Add to `api_surface_summary.functions[]`

### 2.4 Constant Extraction

Extract constants using pattern:
```python
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id.isupper():  # UPPERCASE_NAME
                    try:
                        value = ast.literal_eval(node.value)
                        # Store constant with provenance
                    except (ValueError, SyntaxError):
                        # Cannot safely evaluate, skip
```

**Output**: Store in evidence_map with citation to source file + line number

**Examples**:
- `__version__ = "1.2.3"`
- `SUPPORTED_FORMATS = ["OBJ", "FBX", "STL"]`
- `DEFAULT_TIMEOUT = 30`

### 2.5 Module Path Extraction

Extract module paths from imports and package structure:
```python
# From __init__.py imports
from .entities import Scene, FileFormat

# Infer module path: aspose.threed.entities
```

**Output**: Add to `api_surface_summary.modules[]`

### 2.6 Graceful Error Handling (binding)

```python
try:
    tree = ast.parse(source_code, filename=file_path)
    # ... extraction logic
except SyntaxError as e:
    logger.warning(f"AST parsing failed for {file_path}: {e}")
    return {}  # Empty result, continue W2
```

**Requirements**:
- Never crash W2 due to parsing errors
- Log all parsing failures with file path and error
- Return empty dict on failure
- Emit telemetry event `CODE_ANALYSIS_PARSE_FAILED`

---

## 3. JavaScript Parsing (MVP: Regex-Based)

### 3.1 Parser Selection

Use regex patterns for MVP (covers 80% of common cases).

**Future**: Consider `esprima` (JS parser) or Tree-sitter (multi-language) if regex proves insufficient.

### 3.2 Class Extraction Pattern

```python
import re
class_pattern = r'class\s+([A-Z][a-zA-Z0-9_]*)\s*\{'
matches = re.findall(class_pattern, source_code)
```

**Output**: Add matches to `api_surface_summary.classes[]`

### 3.3 Function Extraction Pattern

```python
function_pattern = r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
matches = re.findall(function_pattern, source_code)
```

**Output**: Add matches to `api_surface_summary.functions[]`

### 3.4 Export Extraction Pattern

```python
export_pattern = r'export\s+(?:class|function|const)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
matches = re.findall(export_pattern, source_code)
```

**Output**: Add matches to `api_surface_summary.functions[]` or `classes[]` based on context

### 3.5 Limitations

Regex-based parsing cannot handle:
- Multi-line class/function declarations
- Complex nested structures
- Dynamic exports (e.g., `module.exports = {...}`)

**Mitigation**: Document limitations in ProductFacts.limitations if insufficient data extracted.

---

## 4. C# Parsing (MVP: Regex-Based)

### 4.1 Parser Selection

Use regex patterns for MVP.

**Future**: Consider Roslyn (C# compiler API) or Tree-sitter if regex proves insufficient.

### 4.2 Class Extraction Pattern

```python
class_pattern = r'public\s+class\s+([A-Z][a-zA-Z0-9_]*)'
matches = re.findall(class_pattern, source_code)
```

**Output**: Add matches to `api_surface_summary.classes[]`

### 4.3 Method Extraction Pattern

```python
method_pattern = r'public\s+\w+\s+([A-Z][a-zA-Z0-9_]*)\s*\('
matches = re.findall(method_pattern, source_code)
```

**Output**: Add matches to `api_surface_summary.functions[]`

### 4.4 Namespace Extraction Pattern

```python
namespace_pattern = r'namespace\s+([\w\.]+)'
matches = re.findall(namespace_pattern, source_code)
```

**Output**: Add matches to `api_surface_summary.modules[]`

---

## 5. Manifest Parsing (binding)

### 5.1 pyproject.toml Parsing

**Parser**: Use `tomllib` (Python 3.11+) or `toml` package (fallback)

**Extract**:
```python
import tomllib  # or import toml

with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)

# Extract fields
name = data.get('project', {}).get('name')
version = data.get('project', {}).get('version')
description = data.get('project', {}).get('description')
dependencies = data.get('project', {}).get('dependencies', [])
scripts = data.get('project', {}).get('scripts', {})
```

**Output**:
- `product_name`: from `project.name`
- `version`: from `project.version`
- `positioning.short_description`: from `project.description`
- `dependencies.runtime`: from `project.dependencies`
- `code_structure.public_entrypoints`: from `project.scripts` keys

### 5.2 package.json Parsing

**Parser**: Use `json.loads()`

**Extract**:
```python
import json

with open('package.json', 'r') as f:
    data = json.load(f)

name = data.get('name')
version = data.get('version')
description = data.get('description')
dependencies = data.get('dependencies', {})
main = data.get('main')
bin = data.get('bin', {})
```

**Output**:
- `product_name`: from `name`
- `version`: from `version`
- `positioning.short_description`: from `description`
- `dependencies.runtime`: from `dependencies` keys
- `code_structure.public_entrypoints`: from `main` and `bin`

### 5.3 \*.csproj Parsing (future scope)

**Parser**: Use `xml.etree.ElementTree`

**Extract** (not in Phase 1):
```python
import xml.etree.ElementTree as ET

tree = ET.parse('Project.csproj')
root = tree.getroot()

name = root.find('.//PackageId').text
version = root.find('.//Version').text
description = root.find('.//Description').text
```

**Status**: Not implemented in TC-1041/TC-1042 (deferred to Phase 2+)

### 5.4 Manifest Priority

If multiple manifests exist, prefer in order:
1. Language-native manifest (`pyproject.toml` for Python, `package.json` for JS)
2. Legacy manifests (`setup.py`, `bower.json`)
3. README as fallback

---

## 6. Positioning Extraction (binding)

### 6.1 README Parsing Algorithm

```python
def extract_positioning(readme_path: str) -> dict:
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read(2000)  # First 2000 chars only

    lines = content.split('\n')
    tagline = None
    short_description = None

    for i, line in enumerate(lines):
        if line.startswith('# ') and not tagline:
            tagline = line[2:].strip()
        elif tagline and line.strip() and not line.startswith('#'):
            short_description = line.strip()
            break

    return {
        'tagline': tagline or 'No tagline found',
        'short_description': short_description or 'No description found'
    }
```

### 6.2 Fallback Strategy

If README not found or empty:
1. Use manifest `description` field as `short_description`
2. Generate tagline from `product_name`: `"{product_name} Library"`

### 6.3 Output Location

Store in `positioning.tagline` and `positioning.short_description` in `product_facts.json`.

---

## 7. Performance Budgets (binding)

### 7.1 Time Budget

**Requirement**: Total code analysis MUST complete in < 10% of W2 total runtime.

**Target**: < 3 seconds for medium-sized repositories (100-500 files)

**Measurement**: Emit telemetry event `CODE_ANALYSIS_DURATION` with milliseconds

### 7.2 File Limits

**Requirement**: Process maximum 100 source files per language.

**Prioritization** (highest to lowest):
1. `src/` directory
2. `lib/` directory
3. `{package_name}/` directory
4. `tests/` directory (lowest priority)

**Algorithm**: Sort files by priority directory, take first 100.

### 7.3 Timeout Per File

**Requirement**: Maximum 500ms per file for parsing.

**Implementation**:
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Parsing timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(1)  # 500ms timeout

try:
    tree = ast.parse(source_code)
    # ... processing
finally:
    signal.alarm(0)  # Cancel timeout
```

**Note**: Use `threading.Timer` on Windows (no SIGALRM support).

### 7.4 Parallel Processing

**Requirement**: Use ThreadPoolExecutor with maximum 4 workers.

**Implementation**:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(parse_file, f) for f in files[:100]]
    results = [f.result() for f in futures]
```

**Rationale**: Balances CPU utilization with memory overhead.

---

## 8. Graceful Fallback (binding)

### 8.1 Parsing Failure

**Behavior**:
1. Log warning with file path and error message
2. Emit telemetry event `CODE_ANALYSIS_PARSE_FAILED` with `{file_path, error_type}`
3. Return empty result for that file
4. Continue processing remaining files
5. Never crash W2

**Example**:
```python
try:
    result = parse_python_file(file_path)
except SyntaxError as e:
    logger.warning(f"Python parsing failed: {file_path}: {e}")
    telemetry.event('CODE_ANALYSIS_PARSE_FAILED', {
        'file_path': file_path,
        'error_type': 'SyntaxError',
        'error_message': str(e)
    })
    result = {}
```

### 8.2 Missing Manifests

**Behavior**:
1. Log info message: "No manifest found, using documentation-only extraction"
2. Emit telemetry event `CODE_ANALYSIS_NO_MANIFEST`
3. Continue with README-based positioning extraction
4. Mark `code_structure` fields as absent (omit from JSON)

### 8.3 All Files Unparseable

**Behavior**:
1. Emit telemetry warning `CODE_ANALYSIS_ALL_FAILED`
2. Return minimal `code_structure` with empty arrays
3. Continue W2 with documentation-based extraction only
4. Do NOT open blocker issue (code analysis is supplemental)

### 8.4 Optional Fields

All `code_structure` fields are OPTIONAL in schema:
- If extraction fails, omit field from JSON entirely
- Never emit null or placeholder values
- W5 MUST handle missing `code_structure` gracefully

---

## 9. Output Format (binding)

### 9.1 product_facts.json Structure

```json
{
  "code_structure": {
    "source_roots": ["src/", "lib/aspose/"],
    "public_entrypoints": ["__init__.py", "main.py"],
    "package_names": ["aspose-3d", "aspose.threed"]
  },
  "api_surface_summary": {
    "classes": ["Scene", "FileFormat", "Mesh"],
    "functions": ["load", "save", "convert"],
    "modules": ["aspose.threed", "aspose.threed.entities"]
  },
  "positioning": {
    "tagline": "3D File Processing for Python",
    "short_description": "Load, manipulate, and convert 3D files in Python applications."
  },
  "version": "24.2.0"
}
```

### 9.2 evidence_map.json Citations

Code analysis MUST create citations for extracted constants:

```json
{
  "claim_id": "const_supported_formats_obj",
  "claim_text": "Supports OBJ format",
  "claim_kind": "format",
  "truth_status": "fact",
  "source_priority": 2,
  "citations": [
    {
      "path": "src/aspose/threed/formats.py",
      "start_line": 15,
      "end_line": 15,
      "source_type": "source_code"
    }
  ]
}
```

---

## 10. Integration with W2 FactsBuilder

### 10.1 Execution Order

Code analysis runs AFTER documentation extraction but BEFORE claim grouping:

1. W2 discovers documents (TC-402)
2. W2 extracts claims from docs (TC-411)
3. **W2 runs code analysis** (TC-1041, TC-1042)
4. W2 maps evidence (TC-412)
5. W2 compiles TruthLock (TC-413)

### 10.2 Input Artifacts

Code analysis reads:
- `repo_inventory.json` (file paths)
- Repo worktree (source files)

Code analysis DOES NOT read:
- `product_facts.json` (not yet created)
- `evidence_map.json` (not yet created)

### 10.3 Output Artifacts

Code analysis produces intermediate dict that W2 merges into:
- `product_facts.code_structure`
- `product_facts.api_surface_summary`
- `product_facts.positioning` (supplement, not replace)
- `product_facts.version`

### 10.4 Conflict Resolution

If code analysis and documentation disagree:
1. Apply evidence priority ranking (source code = priority 2)
2. Use contradiction resolution algorithm (specs/03)
3. Record contradiction in `evidence_map.contradictions[]`

---

## 11. Testing Requirements

### 11.1 Unit Tests

MUST cover:
- Python AST parsing for classes, functions, constants
- Manifest parsing (pyproject.toml, package.json)
- README positioning extraction
- Graceful error handling (syntax errors, missing files)
- Performance timeout enforcement

### 11.2 Integration Tests

MUST verify:
- W2 integration: Code analysis results merged into product_facts.json
- Schema validation: All outputs validate against schemas
- Edge cases: Empty repos, binary-only repos, no manifests

### 11.3 Performance Tests

MUST measure:
- Code analysis duration for small/medium/large repos
- Verify < 10% of W2 total runtime
- Verify timeout enforcement (no file parses > 500ms)

---

## 12. Security Considerations

### 12.1 Code Execution

**Risk**: Arbitrary code execution via `eval()` or `exec()`

**Mitigation**: Use ONLY `ast.literal_eval()` for constant extraction. Never use `eval()` or `exec()`.

### 12.2 Path Traversal

**Risk**: Malicious file paths (e.g., `../../etc/passwd`)

**Mitigation**: Validate all file paths are within repo root using `os.path.commonpath()`.

### 12.3 Resource Exhaustion

**Risk**: Extremely large files or deeply nested AST structures

**Mitigation**:
- File size limit: Skip files > 1MB
- Timeout enforcement: 500ms per file
- Worker limit: Maximum 4 parallel workers

---

## 13. Future Enhancements

### 13.1 Phase 2+ Improvements

- Tree-sitter integration for robust multi-language parsing
- C# support via Roslyn API
- Go support via `go/ast` package
- Rust support via `syn` crate (via subprocess)

### 13.2 Advanced Features

- Type signature extraction (Python type hints, TypeScript types)
- Dependency graph analysis (import relationships)
- Code complexity metrics (cyclomatic complexity, LOC)
- API stability detection (deprecated methods, breaking changes)

---

## 14. References

- **Specs**: `specs/03_product_facts_and_evidence.md` (evidence priority ranking)
- **Schemas**: `specs/schemas/product_facts.schema.json`, `specs/schemas/evidence_map.schema.json`
- **W3 SnippetCurator**: Reference implementation for Python AST parsing
- **Taskcards**: TC-1041 (implementation), TC-1042 (testing)

---

## 15. Acceptance Criteria

- [ ] Python AST parsing extracts public classes, functions, constants
- [ ] Manifest parsing supports pyproject.toml and package.json
- [ ] README positioning extraction handles H1 + description pattern
- [ ] Performance budget: < 10% of W2 runtime (< 3s for medium repos)
- [ ] Graceful fallback: Parsing errors never crash W2
- [ ] Schema compliance: All outputs validate against product_facts.schema.json
- [ ] Test coverage: Unit tests + integration tests + performance tests
- [ ] Security: No use of `eval()`, path traversal protected, timeouts enforced
