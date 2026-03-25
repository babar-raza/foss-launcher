"""Shared frozenset of Python stdlib/builtin names for false-positive suppression.

Both ``worker._SCAN_BUILTINS`` and ``section_validator._PYTHON_BUILTINS`` need
the same set of Python standard-library PascalCase names (plus lowercase
builtins) to avoid flagging them as hallucinated product-API identifiers.

Maintaining two independent copies guarantees drift.  This module is the
single source of truth — both consumers import ``STDLIB_PYTHON_NAMES``.

SRP-01 (2026-03-24).
"""
from __future__ import annotations

STDLIB_PYTHON_NAMES: frozenset[str] = frozenset({
    # ── Builtin singletons / primitives ──────────────────────────────────
    "True", "False", "None", "Ellipsis",
    "int", "float", "complex", "str", "bytes", "bytearray",
    "list", "dict", "tuple", "set", "frozenset", "bool",
    "type", "object", "super",
    # ── Exception hierarchy ──────────────────────────────────────────────
    "Exception", "BaseException", "ValueError", "TypeError", "KeyError",
    "IndexError", "AttributeError", "RuntimeError", "NotImplementedError",
    "StopIteration", "GeneratorExit", "SystemExit", "KeyboardInterrupt",
    "OSError", "IOError", "FileNotFoundError", "PermissionError",
    "TimeoutError", "MemoryError", "RecursionError", "OverflowError",
    "ZeroDivisionError", "FloatingPointError", "ArithmeticError",
    "LookupError", "NameError", "UnboundLocalError", "ImportError",
    "ModuleNotFoundError", "AssertionError", "BufferError",
    "EOFError", "ConnectionError", "BrokenPipeError",
    "ConnectionResetError", "StopAsyncIteration",
    # ── ABC / meta ───────────────────────────────────────────────────────
    "ABC", "ABCMeta",
    # ── Enum ─────────────────────────────────────────────────────────────
    "Enum", "Flag", "IntEnum", "IntFlag",
    # ── Typing ───────────────────────────────────────────────────────────
    "Optional", "Union", "Any", "Callable", "Iterator", "Generator",
    "Sequence", "Mapping", "Iterable",
    "List", "Dict", "Tuple", "Set", "FrozenSet",
    "ClassVar", "Final", "Literal",
    "NamedTuple", "TypedDict", "Protocol", "TypeVar", "Generic",
    # ── Pathlib ──────────────────────────────────────────────────────────
    "Path", "PurePath", "PureWindowsPath", "PurePosixPath",
    # ── Datetime ─────────────────────────────────────────────────────────
    "datetime", "date", "time", "timedelta", "timezone",
    # ── IO / threading / collections ─────────────────────────────────────
    "StringIO", "BytesIO", "Thread", "Lock", "Event", "Queue",
    "Counter", "OrderedDict", "Decimal",
    # ── unittest ──────────────────────────────────────────────────────────
    "TestCase", "TestSuite", "TestLoader", "TextTestRunner", "TestResult",
})
