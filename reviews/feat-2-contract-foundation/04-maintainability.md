# Maintainability and Best Practice

`src/rookery/contracts.py` is 227 lines and reads well. Helpers are small and single-purpose, the module docstring states the security boundary up front, and the ordering — decode, then bound, then validate, then freeze — is the right pipeline and is easy to follow. Type annotations are present and `py.typed` is shipped, so downstream type checking works.

Everything below is low severity.

---

## <a id="m1"></a>M1 — error codes are derived from JSON Schema keyword names

**Location:** `src/rookery/contracts.py:204`

```python
failure = best_match(_validator(kind).iter_errors(value))
if failure is not None:
    raise ContractError(f"schema_{failure.validator}", tuple(failure.absolute_path))
```

`ContractError`'s docstring promises a *"Stable error code"*, and `b01-contract-foundation.md` repeats it: *"Expected failures raise `ContractError` with a stable code and field path"*. For the pre-schema codes that is true — `duplicate_key`, `too_deep`, `number_out_of_range` and the rest are string literals in this file.

For schema failures the code is whatever keyword `best_match` happened to select. That makes it a function of three things outside this module:

- **The schema's structure.** Tightening `Id` from `pattern` to a `format`, or moving a constraint from `required` into an `if`/`then`, changes the public error code without touching `contracts.py`.
- **`best_match`'s heuristic.** It is a relevance ranking over a `oneOf`, not a specification. A jsonschema minor upgrade could reasonably change which error it considers best for a record failing several ways at once.
- **jsonschema's keyword naming**, which is stable in practice but is not this project's API surface.

Verified that nothing currently pins these:

```
error codes pinned by tests: ['bytes_required', 'duplicate_key', 'invalid_json',
                              'invalid_unicode', 'object_required', 'too_deep',
                              'too_many_nodes']
any schema_* code pinned by a test: False
```

Every schema-rejection test calls `assert_rejected(raw)` without a code, so the `schema_*` half of the documented-stable API has no test coverage at all. The pre-schema half is well covered — the asymmetry looks accidental rather than intended.

This matters because B02's importer will surface these codes to an operator, and `policies.md` requires that blocked operations *"store previous state, reason codes, related digests"*. A reason code that silently changes meaning across a dependency bump is a poor thing to persist in a journal.

**Suggested fix**, in increasing order of effort:

1. Pin a handful in tests — `schema_pattern` for a bad `id`, `schema_required` for a missing field, `schema_unevaluatedProperties` for an unknown one. Cheap, and it turns a silent change into a failing test.
2. Map keywords to a project-owned vocabulary (`invalid_format`, `missing_field`, `unknown_property`), with an explicit `_SCHEMA_CODES` dict and a fallback. This makes the code genuinely owned by this module and decouples it from the schema's internal shape.

Worth doing before B01b introduces persisted records, not after.

---

## <a id="m2"></a>M2 — `__hash__ = None` depends on a documented heuristic

**Location:** `src/rookery/contracts.py:190`

```python
@dataclass(frozen=True, slots=True)
class Record:
    raw_json: bytes = field(repr=False)
    data: Mapping[str, JsonValue] = field(init=False, repr=False)
    __hash__ = None
```

This works — verified `Record.__hash__ is None`, and `test_nested_data_and_original_bytes_are_immutable` asserts `hash(record)` raises `TypeError`. It is also doing real work:

```
  a comparable dataclass WITHOUT the explicit None: TypeError(unhashable type: 'dict')
```

So without the explicit `None`, a `Record` would still be unhashable, but only *accidentally* — because `MappingProxyType` happens to be unhashable. If `data` ever became a hashable frozen structure, `Record` would silently start being usable as a dict key, with `raw_json` bytes as part of the hash. Given the module deliberately has no canonical-content identity yet (`b01-contract-foundation.md`: *"There is intentionally no canonical serialization, record digest, equality-by-canonical-content"*), a `Record` silently becoming hashable-by-wire-bytes would be a subtle wrong turn — two records with identical content but different byte ordering would land in different buckets.

The concern is that `@dataclass(frozen=True, eq=True)` normally *generates* `__hash__`. It leaves the explicit `None` alone only because of the `has_explicit_hash` detection, which CPython's own source comments describe as *"a heuristic"*. It also has to survive the class rebuild that `slots=True` performs. Both hold on 3.13, and `requires-python` is pinned to 3.13 — but a reader has no way to know this line is load-bearing rather than redundant, and "the dataclass would make it unhashable anyway" is a tempting cleanup.

**Suggested fix:** a comment.

```python
    # Deliberately unhashable: there is no canonical content identity yet, so a
    # hash would key on wire bytes. Explicit rather than relying on data's type.
    __hash__ = None
```

---

## <a id="m3"></a>M3 — `tools` and `tests` are implicit namespace packages

**Location:** `tests/test_contracts.py:18`

```python
from tools import check_design as design
```

Neither `tools/` nor `tests/` has an `__init__.py`; both resolve as PEP 420 namespace packages from the current working directory:

```
tools: _NamespacePath(['C:\\...\\Rookery\\tools'])
tests: _NamespacePath(['C:\\...\\Rookery\\tests'])
```

This works in CI, which runs `python -m unittest discover -s tests -v` from the repository root, and it works for anyone following the README. It breaks with `ModuleNotFoundError: No module named 'tools'` if the suite is run from anywhere else — which a contributor will hit the first time they invoke tests from an IDE configured with a different working directory, or with `pytest tests/test_contracts.py` from a subdirectory.

The coupling is worth a note rather than a restructure: adding `__init__.py` files would make `tools` and `tests` importable packages that could shadow real distributions, which is arguably worse. A comment at the import, or a line in the README's command block noting that the commands must run from the repository root, is enough.

Related and deliberate: this import means the *installed-package* test suite depends on the source checkout, for `ROOT`-relative fixture reads and for `tools`. That is fine and is not a contradiction of the doc's *"no dependency on the checkout at runtime"* — that claim is about the package, which genuinely has none. Worth being explicit about the distinction somewhere, since the two statements sit close together.

---

## Style notes (no action needed)

- **`_check_tree` is iterative rather than recursive**, using an explicit stack. For a routine whose whole job is bounding nesting depth, not being able to blow the interpreter stack itself is the right call, and it is the kind of detail that usually gets missed.
- **The `_decode` exception ordering is correct and subtle.** `except ContractError: raise` comes before `except (ValueError, ArithmeticError)`, which matters because `ContractError` *is* a `ValueError` — the hooks raise it from inside `json.loads`, and without the early re-raise it would be rewritten to `invalid_json` and lose its specific code. Easy to break in a refactor; worth a comment.
- **`lru_cache` on `_schema` and `_validator`** with `maxsize=len(RecordKind)` is a nice touch — the cache is sized to the domain rather than to an arbitrary number.
- **`JsonValue` includes `Decimal` but not `float`**, which correctly reflects `parse_float=_decimal`. The type alias would have been an easy place to be sloppy.
- **`_decimal`'s magnitude check is well commented** — *"Bound magnitude without converting the stored value to a rounded float"* — and the `(value != 0 and approximate == 0)` clause catching nonzero underflow is a genuinely easy case to forget.
- **`created_at` returns `str`, not `datetime`**, with the reason in a comment: *"Do not silently truncate fractional seconds to datetime's microseconds."* Correct, and the kind of decision that gets reversed by someone being helpful unless the reason is written down. It is.
- **227 lines with no dead code, no TODO comments, and no commented-out blocks.** The absent things are absent deliberately and the docs say which ones and why.
