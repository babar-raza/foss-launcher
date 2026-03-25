"""Post-LLM engineering step: repair hallucinated API identifiers in generated sections.

TC-4213: The LLM frequently invents PascalCase class names that do not exist in the
real API surface (e.g., ``SpreadsheetManager``, ``RowIterator`` when only ``Workbook``
and ``Worksheet`` exist). This module provides a single deterministic pass that:

1. Builds a "known" set from the extracted ``ApiSurface``.
2. Builds an "exempt" set of Python builtins, primitives, and generic proper nouns.
3. Scans prose segments for PascalCase identifiers not in known/exempt sets.
4. In prose: strips the hallucinated token (TC-EVAL-501: no visible sentinel).
5. In code blocks: appends a comment noting the unknown identifier.
6. Returns the repaired text and an audit list of every replacement made.

Design principles
-----------------
- **Conservative**: Only replace true PascalCase identifiers (≥2 camel humps like
  ``FileFormat`` or PascalCase+digit like ``Vector3``) not found anywhere in the
  known set (including substring checks against known class names).
  Single-hump words ("Lambert", "Developers") are never matched (TC-4222/HG-22).
- **Non-destructive**: Never removes entire sentences. Prose gets a token replacement;
  code gets a comment appended on the offending line.
- **Audit trail**: Every replacement is recorded in ``repairs`` so callers can write
  an inspection artifact.
- **No LLM calls**: Pure deterministic string manipulation.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.product import ApiSurface

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# True PascalCase identifiers: ≥2 camel humps (FileFormat, ObjLoadOptions) or
# PascalCase+digit suffix (Vector3, Matrix4).  Single-hump words ("Lambert",
# "Phong", "Developers", "These") are intentionally NOT matched.
# TC-4222 (HG-22): narrowed from r"\b([A-Z][a-zA-Z0-9]{3,})\b" which matched any
# capitalised word ≥4 chars and produced massive false-positive replacement.
_PASCAL_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+|[A-Z][a-z]+\d+)\b')

# Markdown code fence opener: ```language or ``` (we track fenced regions)
_FENCE_START_RE = re.compile(r"^```")

# Markdown header line (level 1–6)
_HEADER_RE = re.compile(r"^#{1,6}\s")

# ---------------------------------------------------------------------------
# Exempt sets — never repair these
# ---------------------------------------------------------------------------

# Python built-in types, exceptions, and common stdlib names that happen to be PascalCase
_PYTHON_BUILTINS: frozenset[str] = frozenset({
    # Built-in types / singletons
    "True", "False", "None",
    # Built-in functions that are PascalCase (Python naming uses lowercase, but some
    # typing constructs and common imports appear PascalCase)
    # Exceptions — common ones
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "AttributeError", "RuntimeError", "StopIteration", "NotImplementedError",
    "FileNotFoundError", "PermissionError", "OSError", "IOError",
    "OverflowError", "ZeroDivisionError", "RecursionError", "MemoryError",
    "ImportError", "ModuleNotFoundError", "SyntaxError", "NameError",
    "AssertionError", "LookupError", "ArithmeticError", "UnicodeError",
    "UnicodeDecodeError", "UnicodeEncodeError", "TimeoutError", "ConnectionError",
    "IsADirectoryError", "NotADirectoryError", "ProcessLookupError",
    "ChildProcessError", "BrokenPipeError", "InterruptedError", "BlockingIOError",
    "BufferError", "FloatingPointError", "SystemError", "SystemExit",
    "KeyboardInterrupt", "GeneratorExit", "BaseException",
    # Common stdlib PascalCase names
    "Path", "PurePath", "PurePosixPath", "PureWindowsPath", "WindowsPath",
    "PosixPath", "BytesIO", "StringIO", "TextIOWrapper",
    "OrderedDict", "defaultdict", "Counter", "ChainMap",
    "Enum", "IntEnum", "Flag", "IntFlag",
    "NamedTuple", "TypedDict",
    "Callable", "Optional", "Union", "Any", "List", "Dict", "Tuple", "Set",
    "FrozenSet", "Type", "ClassVar", "Final", "Literal", "Annotated",
    "Generator", "Iterator", "Iterable", "Sequence", "Mapping", "MutableMapping",
    "MutableSequence", "MutableSet", "AbstractSet",
    "Awaitable", "Coroutine", "AsyncGenerator", "AsyncIterator", "AsyncIterable",
    "Protocol", "TypeVar", "Generic", "Self",
    "Thread", "Lock", "RLock", "Event", "Condition", "Semaphore",
    "Queue", "LifoQueue", "PriorityQueue",
    "Decimal", "Fraction", "Complex",
    "Pattern", "Match",
    "UTC", "timezone", "timedelta", "datetime", "date", "time",
    "Field", "BaseModel",  # pydantic
    "Logger",  # logging
    "Json",    # common alias
})

# Common proper nouns, frameworks, and language keywords that appear as PascalCase
# but are not product-specific API identifiers
_GENERIC_PROPER_NOUNS: frozenset[str] = frozenset({
    # Programming language names
    "Python", "Java", "JavaScript", "TypeScript", "Kotlin", "Swift",
    "Ruby", "Rust", "Golang", "Scala", "Groovy", "Perl", "Haskell",
    "CSharp", "Dotnet", "DotNet",
    # Common frameworks / libraries
    "Django", "Flask", "FastAPI", "NumPy", "Pandas", "TensorFlow", "PyTorch",
    "Matplotlib", "Scipy", "Sklearn", "Keras", "OpenCV", "Pillow",
    "React", "Angular", "Vue", "Svelte", "Express", "Nest",
    "Spring", "Hibernate", "Maven", "Gradle",
    # Common document / data format terms
    "Excel", "Word", "PowerPoint", "Outlook", "OneNote",
    "Markdown", "Html", "Xml", "Json", "Yaml", "Toml", "Csv",
    "Pdf", "Jpeg", "Png", "Gif", "Svg", "Tiff", "Bmp",
    # Common product-neutral terms that appear PascalCase in docs
    "GitHub", "GitLab", "Bitbucket", "Docker", "Kubernetes",
    "Windows", "Linux", "MacOS", "Android", "iOS",
    "Unicode", "Ascii", "Utf", "Base64",
    # Common generic class-like terms in technical writing
    "Example", "Overview", "Reference", "Guide", "Tutorial",
    "Manager",  # generic word — could be valid class name, but also often generic
    # Note: "Manager" is included because we check substring-in-known instead
})

# Words that look like PascalCase but are really just capitalized common English words.
# These appear at sentence starts or as normal prose words in technical docs.
_SHORT_EXEMPT: frozenset[str] = frozenset({
    # Common verbs that start sentences in technical docs
    "Create", "Creates", "Creating", "Created",
    "Build", "Builds", "Building", "Built",
    "Load", "Loads", "Loading", "Loaded",
    "Save", "Saves", "Saving", "Saved",
    "Open", "Opens", "Opening", "Opened",
    "Close", "Closes", "Closing", "Closed",
    "Read", "Reads", "Reading",
    "Write", "Writes", "Writing",
    "Parse", "Parses", "Parsing", "Parsed",
    "Convert", "Converts", "Converting", "Converted",
    "Export", "Exports", "Exporting", "Exported",
    "Import", "Imports", "Importing", "Imported",
    "Install", "Installs", "Installing", "Installed",
    "Call", "Calls", "Called", "Calling",
    "Return", "Returns", "Returning", "Returned",
    "Pass", "Passes", "Passing", "Passed",
    "Check", "Checks", "Checking",
    "Get", "Gets", "Getting",
    "Set", "Sets", "Setting",
    "Add", "Adds", "Adding", "Added",
    "Remove", "Removes", "Removing", "Removed",
    "Update", "Updates", "Updating", "Updated",
    "Delete", "Deletes", "Deleting", "Deleted",
    "Handle", "Handles", "Handling", "Handled",
    "Process", "Processes", "Processing", "Processed",
    "Define", "Defines", "Defining", "Defined",
    "Declare", "Declares", "Declaring", "Declared",
    "Extend", "Extends", "Extending", "Extended",
    "Implement", "Implements", "Implementing", "Implemented",
    "Override", "Overrides", "Overriding", "Overridden",
    "Inherit", "Inherits", "Inheriting", "Inherited",
    "Raise", "Raises", "Raising", "Raised",
    "Catch", "Catches", "Catching", "Caught",
    "Throw", "Throws", "Throwing", "Thrown",
    "Register", "Registers", "Registering", "Registered",
    "Initialize", "Initializes", "Initializing", "Initialized",
    "Configure", "Configures", "Configuring", "Configured",
    "Execute", "Executes", "Executing", "Executed",
    "Perform", "Performs", "Performing", "Performed",
    "Generate", "Generates", "Generating", "Generated",
    "Render", "Renders", "Rendering", "Rendered",
    "Validate", "Validates", "Validating", "Validated",
    "Serialize", "Serializes", "Serializing", "Serialized",
    "Deserialize", "Deserializes", "Deserializing",
    "Connect", "Connects", "Connecting", "Connected",
    "Disconnect", "Disconnects", "Disconnecting",
    "Download", "Downloads", "Downloading", "Downloaded",
    "Upload", "Uploads", "Uploading", "Uploaded",
    "Fetch", "Fetches", "Fetching", "Fetched",
    "Send", "Sends", "Sending", "Sent",
    "Receive", "Receives", "Receiving", "Received",
    "Access", "Accesses", "Accessing", "Accessed",
    "Modify", "Modifies", "Modifying", "Modified",
    "Append", "Appends", "Appending", "Appended",
    "Insert", "Inserts", "Inserting", "Inserted",
    "Replace", "Replaces", "Replacing", "Replaced",
    "Copy", "Copies", "Copying", "Copied",
    "Move", "Moves", "Moving", "Moved",
    "Merge", "Merges", "Merging", "Merged",
    "Split", "Splits", "Splitting",
    "Sort", "Sorts", "Sorting", "Sorted",
    "Filter", "Filters", "Filtering", "Filtered",
    "Search", "Searches", "Searching",
    "Find", "Finds", "Finding", "Found",
    "Extract", "Extracts", "Extracting", "Extracted",
    "Format", "Formats", "Formatting", "Formatted",
    "Print", "Prints", "Printing", "Printed",
    "Display", "Displays", "Displaying", "Displayed",
    "Show", "Shows", "Showing", "Shown",
    "Hide", "Hides", "Hiding", "Hidden",
    "Enable", "Enables", "Enabling", "Enabled",
    "Disable", "Disables", "Disabling", "Disabled",
    "Start", "Starts", "Starting", "Started",
    "Stop", "Stops", "Stopping", "Stopped",
    "Begin", "Begins", "Beginning", "Began",
    "End", "Ends", "Ending", "Ended",
    "Reset", "Resets", "Resetting",
    "Clear", "Clears", "Clearing", "Cleared",
    "Flush", "Flushes", "Flushing", "Flushed",
    "Sync", "Syncs", "Syncing", "Synced",
    "Lock", "Locks", "Locking", "Locked",
    "Unlock", "Unlocks", "Unlocking", "Unlocked",
    "Wrap", "Wraps", "Wrapping", "Wrapped",
    "Unwrap", "Unwraps", "Unwrapping",
    "Bind", "Binds", "Binding", "Bound",
    "Unbind", "Unbinds", "Unbinding",
    "Compress", "Compresses", "Compressing", "Compressed",
    "Decompress", "Decompresses", "Decompressing",
    "Encrypt", "Encrypts", "Encrypting", "Encrypted",
    "Decrypt", "Decrypts", "Decrypting", "Decrypted",
    "Hash", "Hashes", "Hashing", "Hashed",
    "Sign", "Signs", "Signing", "Signed",
    "Verify", "Verifies", "Verifying", "Verified",
    "Compile", "Compiles", "Compiling", "Compiled",
    "Link", "Links", "Linking", "Linked",
    "Unlink", "Unlinks", "Unlinking",
    "Patch", "Patches", "Patching", "Patched",
    "Apply", "Applies", "Applying", "Applied",
    "Attach", "Attaches", "Attaching", "Attached",
    "Detach", "Detaches", "Detaching", "Detached",
    "Mount", "Mounts", "Mounting", "Mounted",
    "Unmount", "Unmounts", "Unmounting",
    "Iterate", "Iterates", "Iterating", "Iterated",
    "Traverse", "Traverses", "Traversing", "Traversed",
    "Visit", "Visits", "Visiting", "Visited",
    "Walk", "Walks", "Walking", "Walked",
    "Scan", "Scans", "Scanning", "Scanned",
    "Parse", "Parses", "Parsing", "Parsed",
    "Resolve", "Resolves", "Resolving", "Resolved",
    "Lookup", "Lookups",
    "Query", "Queries", "Querying", "Queried",
    "Execute", "Executes",
    "Commit", "Commits", "Committing", "Committed",
    "Rollback", "Rollbacks",
    "Publish", "Publishes", "Publishing", "Published",
    "Subscribe", "Subscribes", "Subscribing", "Subscribed",
    "Emit", "Emits", "Emitting", "Emitted",
    "Trigger", "Triggers", "Triggering", "Triggered",
    "Notify", "Notifies", "Notifying", "Notified",
    "Watch", "Watches", "Watching", "Watched",
    "Listen", "Listens", "Listening",
    "Observe", "Observes", "Observing", "Observed",
    "Intercept", "Intercepts", "Intercepting",
    "Inject", "Injects", "Injecting", "Injected",
    "Provide", "Provides", "Providing", "Provided",
    "Consume", "Consumes", "Consuming", "Consumed",
    "Produce", "Produces", "Producing", "Produced",
    "Transform", "Transforms", "Transforming", "Transformed",
    "Reduce", "Reduces", "Reducing", "Reduced",
    "Expand", "Expands", "Expanding", "Expanded",
    "Collapse", "Collapses", "Collapsing", "Collapsed",
    "Flatten", "Flattens", "Flattening", "Flattened",
    "Normalize", "Normalizes", "Normalizing", "Normalized",
    "Encode", "Encodes", "Encoding", "Encoded",
    "Decode", "Decodes", "Decoding", "Decoded",
    # Common adjectives and adverbs in technical docs
    "When", "While", "Where", "Since", "After", "Before", "During",
    "Then", "Also", "Next", "Finally", "Note", "This", "That",
    "With", "From", "Into", "Upon", "Over", "Once", "Until",
    "Some", "Many", "Each", "Most", "Both", "True", "None",
    "Step", "More", "Last", "Full", "Back",
    # Common nouns in technical docs
    "Mode", "Line", "Word", "Menu", "Form",
    "Item", "User", "Name", "Help",
    "Root", "Task", "Date", "Time", "Size", "Done",
    "Page", "File", "Data", "Code", "Text", "List", "Type",
    "View", "Test", "Node", "Case", "Goto",
})


def _build_known_set(api_surface: "ApiSurface") -> frozenset[str]:
    """Build the set of all known API identifiers from ApiSurface.

    Includes:
    - public_classes (exact names)
    - method names from class_briefs (typed_methods)
    - property names from class_briefs (typed_properties)
    - top-level enum class names (api_surface.enums)
    """
    known: set[str] = set()

    # Public class names
    for cls in (api_surface.public_classes or []):
        if cls:
            known.add(cls)

    # Class brief method and property names
    for brief in (api_surface.class_briefs or []):
        if brief.name:
            known.add(brief.name)
        for method in (brief.typed_methods or []):
            if method.name:
                known.add(method.name)
        for prop in (brief.typed_properties or []):
            if prop.name:
                known.add(prop.name)
        # Legacy string lists
        for m in (brief.methods or []):
            if m:
                known.add(m)
        for p in (brief.properties or []):
            if p:
                known.add(p)

    # Top-level enum names
    for enum in (api_surface.enums or []):
        if enum.name:
            known.add(enum.name)
        for member in (enum.members or []):
            if member.name:
                known.add(member.name)

    return frozenset(known)


def _build_exempt_set(product_display_name: str = "") -> frozenset[str]:
    """Build the complete exempt set including product display name tokens."""
    exempt: set[str] = set()
    exempt.update(_PYTHON_BUILTINS)
    exempt.update(_GENERIC_PROPER_NOUNS)
    exempt.update(_SHORT_EXEMPT)

    # Tokenise product display name (e.g. "Aspose.Cells" → {"Aspose", "Cells"})
    if product_display_name:
        for token in re.split(r"[.\s\-_/]+", product_display_name):
            tok = token.strip()
            if tok and len(tok) >= 2:
                exempt.add(tok)

    return frozenset(exempt)


def _is_substring_of_known(identifier: str, known_set: frozenset[str]) -> bool:
    """Return True if ``identifier`` is a substring of any known class name.

    This prevents false-positive repairs like reporting "Cell" as unknown when
    the known set contains "CellRange" or "CellValue" — or vice versa, "CellData"
    being flagged when "Cell" is known and "Data" is a suffix.

    The check is intentionally asymmetric:
    - If ``identifier`` is entirely contained within a known name → skip (it's a stem).
    - If any known name is entirely contained within ``identifier`` → skip (it extends
      a known stem, so it might be a valid compound name).
    """
    for known in known_set:
        if identifier in known or known in identifier:
            return True
    return False


def _repair_prose_segment(
    segment: str,
    known_set: frozenset[str],
    exempt_set: frozenset[str],
) -> tuple[str, list[str]]:
    """Replace hallucinated PascalCase tokens in a prose segment.

    Skips markdown header lines.
    Returns (repaired_segment, repairs_list).
    """
    lines = segment.splitlines(keepends=True)
    repaired_lines: list[str] = []
    repairs: list[str] = []

    for line in lines:
        # Skip markdown headers — never modify them
        if _HEADER_RE.match(line):
            repaired_lines.append(line)
            continue

        def _replace_token(match: re.Match) -> str:  # type: ignore[type-arg]
            token = match.group(1)
            if token in known_set:
                return token
            if token in exempt_set:
                return token
            if _is_substring_of_known(token, known_set):
                return token
            repairs.append(token)
            return ""  # TC-EVAL-501: strip hallucinated token instead of inserting sentinel

        new_line = _PASCAL_RE.sub(_replace_token, line)
        # TC-EVAL-501: clean up artifacts from token removal (double spaces, orphan punctuation)
        new_line = re.sub(r"  +", " ", new_line)  # collapse multiple spaces
        new_line = re.sub(r" ([.,;:!?])", r"\1", new_line)  # remove space before punctuation
        new_line = re.sub(r"^\s+$", "\n", new_line) if new_line.strip() == "" else new_line
        repaired_lines.append(new_line)

    return "".join(repaired_lines), repairs


def _repair_code_segment(
    segment: str,
    known_set: frozenset[str],
    exempt_set: frozenset[str],
) -> tuple[str, list[str]]:
    """Annotate hallucinated PascalCase tokens in a code segment with comments.

    The fence delimiters (``` lines) are passed through unchanged.
    For each hallucinated token in a code line, append a comment to that line.
    Only the first hallucinated token per line is annotated to avoid cluttered output.
    Returns (repaired_segment, repairs_list).
    """
    lines = segment.splitlines(keepends=True)
    repaired_lines: list[str] = []
    repairs: list[str] = []

    for line in lines:
        stripped = line.rstrip("\n\r")

        # Fence delimiter lines pass through unchanged
        if _FENCE_START_RE.match(stripped):
            repaired_lines.append(line)
            continue

        # Find hallucinated tokens on this line
        hallucinated: list[str] = []
        for match in _PASCAL_RE.finditer(stripped):
            token = match.group(1)
            if token in known_set:
                continue
            if token in exempt_set:
                continue
            if _is_substring_of_known(token, known_set):
                continue
            hallucinated.append(token)

        if not hallucinated:
            repaired_lines.append(line)
            continue

        # Annotate the first hallucinated token only (keep output readable)
        token = hallucinated[0]
        repairs.extend(hallucinated)  # record all found, even if only first is annotated
        eol = line[len(stripped):]   # preserve original line ending (\n or \r\n)
        # Only add comment if line doesn't already have one (avoid double-commenting)
        if "#" not in stripped:
            annotated = f"{stripped}  # {token}: unknown — omitted{eol}"
        else:
            # Line already has a comment — insert the annotation before the comment
            comment_pos = stripped.index("#")
            code_part = stripped[:comment_pos].rstrip()
            existing_comment = stripped[comment_pos:]
            annotated = f"{code_part}  # {token}: unknown — {existing_comment.lstrip('# ').rstrip()}{eol}"
        repaired_lines.append(annotated)

    return "".join(repaired_lines), repairs


def repair_identifiers(
    section_text: str,
    api_surface: "ApiSurface",
    product_display_name: str = "",
) -> tuple[str, list[str]]:
    """Repair hallucinated API identifiers in a generated section's text.

    This is a pure deterministic post-LLM engineering step with no LLM calls.

    Parameters
    ----------
    section_text:
        The rendered markdown text of a section (prose + code fences).
    api_surface:
        The extracted ``ApiSurface`` from the ``UnderstandingBundle``.
        Provides the ground-truth set of known identifiers.
    product_display_name:
        The product's display name (e.g., "Aspose.Cells for Python").
        Its component tokens are added to the exempt set so the product
        name itself is never suppressed.

    Returns
    -------
    tuple[str, list[str]]
        ``(repaired_text, repairs)`` where ``repairs`` is a list of every
        identifier that was replaced or annotated. An empty list means no
        hallucinations were detected.

    Scope gates (identifiers that are NEVER repaired)
    --------------------------------------------------
    - Identifiers inside markdown headers (``# H1``, ``## H2``, …)
    - The product display name itself and its component tokens
    - Standard Python builtins, exceptions, typing constructs
    - Identifiers shorter than 4 characters
    - Identifiers that are substrings of any known class name (or vice versa)
    """
    if not section_text:
        return section_text, []

    known_set = _build_known_set(api_surface)
    exempt_set = _build_exempt_set(product_display_name)

    # Split text into alternating prose / code-fence segments.
    # We walk line-by-line to track fence state.
    segments: list[tuple[str, bool]] = []  # (text, is_code)
    current_lines: list[str] = []
    in_fence = False

    for raw_line in section_text.splitlines(keepends=True):
        stripped = raw_line.rstrip("\n\r")
        if _FENCE_START_RE.match(stripped):
            if not in_fence:
                # Flush any pending prose
                if current_lines:
                    segments.append(("".join(current_lines), False))
                    current_lines = []
                # Start new code segment with the fence opener
                current_lines = [raw_line]
                in_fence = True
            else:
                # Close the fence — include the closing ``` in the code segment
                current_lines.append(raw_line)
                segments.append(("".join(current_lines), True))
                current_lines = []
                in_fence = False
        else:
            current_lines.append(raw_line)

    # Flush remaining content
    if current_lines:
        segments.append(("".join(current_lines), in_fence))

    # Process each segment
    repaired_parts: list[str] = []
    all_repairs: list[str] = []

    for seg_text, is_code in segments:
        if is_code:
            repaired, repairs = _repair_code_segment(seg_text, known_set, exempt_set)
        else:
            repaired, repairs = _repair_prose_segment(seg_text, known_set, exempt_set)
        repaired_parts.append(repaired)
        all_repairs.extend(repairs)

    return "".join(repaired_parts), all_repairs
