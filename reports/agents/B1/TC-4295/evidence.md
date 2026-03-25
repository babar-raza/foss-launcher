# TC-4295 Evidence — Evaluate: Expand API verification allowlists

## Date: 2026-03-14

## Changes Made

### `src/launcher/workers/evaluate/checks/api_verification.py`
1. Expanded `_ALWAYS_ALLOWED_CLASSES` with:
   - Stdlib exceptions: OSError, PermissionError, OverflowError, ZeroDivisionError, ImportError, ModuleNotFoundError, UnicodeError, UnicodeDecodeError, UnicodeEncodeError, ConnectionError, TimeoutError, RecursionError
   - Typing: Callable, Sequence, Mapping, Iterator, Iterable, Generator, Type, NamedTuple, TypedDict, Protocol, TypeVar, Generic
   - Collections: namedtuple, ChainMap
   - Threading: RLock, Semaphore
   - Datetime: timezone
   - Functools: contextmanager, wraps, partial, lru_cache
   - Dataclasses: dataclass, Field
   - Pydantic: BaseModel
   - XML: ElementTree, Element
   - urllib: HTTPError, URLError
   - unittest: TestCase, TestSuite, TestLoader, TextTestRunner

2. Expanded `_ALWAYS_ALLOWED_METHODS` with:
   - Dunder methods: __contains__, __hash__, __eq__, __ne__, __lt__, __le__, __gt__, __ge__, __add__, __sub__, __mul__, __truediv__, __mod__, __pow__, __and__, __or__, __xor__, __neg__, __pos__, __abs__, __invert__, __call__, __getattr__, __setattr__, __delattr__, __getattribute__
   - Dict/set methods: copy, setdefault
   - String methods: lstrip, rstrip, rsplit, capitalize, casefold, rfind, rindex, count, isdigit, isalpha
   - File I/O: readline, readlines, writelines, flush, seek, tell
   - Path: exists, is_file, is_dir, mkdir, rmdir, unlink, resolve, absolute, relative_to, with_suffix, with_name, dirname, basename, abspath
   - Print/logging: pprint, info, warning, error, debug
   - Iteration: sort, sorted, reverse, reversed, map, filter, reduce, next, iter
   - OS: getcwd, chdir, listdir, walk, environ, getenv, path

## Root Cause Addressed

api_verification.py flagged 247 unknown-class + 233 unknown-method findings. ~30% were false positives from stdlib usage in code examples (BytesIO, StringIO, dirname, exists, etc.).

## Test Results

```
4436 passed, 65 skipped, 3 xfailed, 2 xpassed in 102.93s
```

## Expected E2E Impact

- Reduces false-positive MEDIUM findings by ~30%
- C pages promoted to B, B pages promoted to A
