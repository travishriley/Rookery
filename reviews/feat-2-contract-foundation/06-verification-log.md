# Verification Log

Every finding was checked by execution against commit `c0f329cd7ad8a787d9b3dbe405fe80e4bb9f4004`, in a clean virtual environment with the project wheel installed — the same shape as CI. This file records the commands and raw output so the findings can be audited rather than taken on trust.

**Environment:** Windows 11 Pro (build 26200), AMD64, CPython 3.13.7 x64, a fresh `venv` with only the pins from `requirements-dev.txt`.

**Nothing outside the repository and temporary directories was touched.** No printer, device, network service, slicer process, or model provider was contacted. Two throwaway virtual environments were created under `%TEMP%` and removed afterwards.

---

## 1. The PR's own claims reproduce exactly

```console
$ python -m venv <temp>/rkv
$ <temp>/rkv/Scripts/python -m pip install --only-binary=:all: -r requirements-dev.txt
$ <temp>/rkv/Scripts/python -m pip wheel . --no-deps --no-build-isolation --no-index --wheel-dir <temp>/rkdist
Successfully built rookery-core

$ <temp>/rkv/Scripts/python -m pip install --no-deps --no-index <temp>/rkdist/rookery_core-0.1.0.dev1-py3-none-any.whl
$ <temp>/rkv/Scripts/python -m pip check
No broken requirements found.

$ <temp>/rkv/Scripts/python -m unittest discover -s tests
......................
Ran 22 tests in 0.639s
OK

$ <temp>/rkv/Scripts/python tools/check_design.py
PASS: Draft 2020-12 schema, 230 local references, 26 positive shapes, 119 negative probes, 33 local links, original prompt SHA-256
Design checks only. No product policy, worker isolation, slicer runtime, live printer, restore destination, or physical-quality test was executed.

$ <temp>/rkv/Scripts/python -m unittest discover -s tools -p test_check_design.py
.........
Ran 9 tests in 4.687s
OK
```

The PR body claims "19 installed-package tests and three workflow configuration tests" (22 total ✓), "nine design-tool tests" ✓, and "230 schema references, 26 positive shapes, 119 negative probes, 33 local links" ✓. **Every number matches.** `pip check` is clean, and the wheel builds without network access.

## 2. The wheel contains only what it claims

```console
$ python -c "import zipfile; ..."
  rookery/__init__.py                              219
  rookery/contracts.py                           7,564
  rookery/py.typed                                   1
  rookery/schemas/0.1.0/rookery.schema.json     29,695
  rookery/schemas/__init__.py                       85
  rookery_core-0.1.0.dev1.dist-info/METADATA       359
  rookery_core-0.1.0.dev1.dist-info/RECORD         739
  rookery_core-0.1.0.dev1.dist-info/WHEEL           91
  rookery_core-0.1.0.dev1.dist-info/top_level.txt    8
```

No build prompt, examples, fixtures, tests or private data — matching the doc. **Confirmed.** The 359-byte METADATA is the basis of [U3](03-usability.md#u3).

## 3. No actuation path exists in the product code

```console
$ grep -nE "\bopen\(|subprocess|socket|urllib|requests|httpx|os\.system|eval\(|exec\(|pickle|__import__" src/rookery/*.py
  (none in src/rookery)
```

The only I/O in the package is `importlib.resources` reading the bundled schema. **Confirmed** — `parse_record`'s docstring promise holds literally.

A credential sweep over the full PR diff returned only prose about JSON number *tokens* and the workflow's own statement that it uses no secrets.

## 4. Parser robustness — the core claim

```console
$ <temp>/rkv/Scripts/python reviews/feat-2-contract-foundation/evidence/probe_parser_robustness.py
cases=4030  accepted=100  ContractError=3930  UNEXPECTED=0
```

4,030 inputs — hand-built structural and encoding edges plus 4,000 seeded byte mutations of a valid record. **Zero exceptions other than `ContractError`.** Basis of [05-what-is-good.md](05-what-is-good.md#robustness).

## 5. A2 — validation cost is not bounded by the documented limits

```console
$ <temp>/rkv/Scripts/python reviews/feat-2-contract-foundation/evidence/probe_validation_cost.py

Documented limits: MAX_RECORD_BYTES=1,048,576  MAX_NODES=50,000  MAX_DEPTH=64

SourceSnapshot.files -- uniqueItems over an array of objects:
    0.068s     26,732 bytes  accepted   100 unique file entries
    0.122s    131,932 bytes  accepted   500 unique file entries
    0.433s    263,432 bytes  accepted   1000 unique file entries
    1.633s    527,432 bytes  accepted   2000 unique file entries
    3.590s    791,432 bytes  accepted   3000 unique file entries
    4.816s    923,432 bytes  accepted   3500 unique file entries

Same shape, but the duplicate is at the very end (forces a full pairwise scan):
    4.721s    897,029 bytes  rejected(schema_uniqueItems)  3400 entries

Control -- an equally large record without uniqueItems on objects:
    0.120s    740,891 bytes  accepted   3400 edges (no uniqueItems)

Worst single-record validation time observed: 4.816s
```

Every one of those records satisfies all four documented limits. Quadratic growth is clear: 1000→2000 entries multiplies time by 3.8; 2000→3000 multiplies by 2.2 for a 1.5× size increase (1.5² = 2.25).

Mechanism confirmed rather than inferred:

```
    0.000s  jsonschema._utils.uniq on 3000 distinct strings
    4.875s  jsonschema._utils.uniq on 3000 distinct objects
```

`uniq` tries `sorted()` first — fine for strings, impossible for dicts, which fall back to a pairwise scan.

**Memory, for completeness:** a 360 KB input rejected with `too_many_nodes` peaked at 13 MB traced, because the node budget is enforced after `json.loads` materialises the tree. ~36× amplification, so roughly 38 MB at the 1 MiB ceiling — bounded and modest. Not a finding; recorded so it is not mistaken for unbounded.

## 6. A1 — `Time` without a format checker

```console
$ <temp>/rkv/Scripts/python reviews/feat-2-contract-foundation/evidence/probe_schema_contract.py

=== 4. Time format: does the schema pattern alone hold without the format checker? ===
  no format checker: ACCEPTED  created_at='garbageZ'
  no format checker: ACCEPTED  created_at='2026-09-12T12:00:00Z\n'
  no format checker: ACCEPTED  created_at='2026-02-30T12:00:00Z'
  no format checker: ACCEPTED  created_at='ZZZZZ'
```

I also enumerated every `pattern` keyword in the schema to confirm the asymmetry is limited to `Time`:

```
  guarded=True   /$defs/Digest   ^sha256:[0-9a-f]{64}$(?![\s\S])
  guarded=True   /$defs/Id       ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$(?![\s\S])
  guarded=True   /$defs/Path     ^(?!/)...$(?![\s\S])
  guarded=False  /$defs/Time     Z$
```

`Path` already carried the terminator guard before this PR. `Digest` and `Id` gained it here. `Time` is the only one left, and unlike the others its pattern constrains almost nothing even before the terminator question.

**Rookery itself is unaffected** — `contracts.py:168` always passes `format_checker=_FORMATS`, and I confirmed all four values are rejected through `parse_record`.

## 7. A3 — node budget versus declared `maxItems`

```
  one FileEntry costs 13 nodes
  MAX_NODES=50,000 allows at most ~3,846 file entries
  schema declares files.maxItems = 10,000
  -> the schema bound is unreachable; MAX_NODES binds first by ~2x
```

## 8. Error paths do not leak record content

```
  unknown property   -> code='schema_unevaluatedProperties'  path=()
                        str='schema_unevaluatedProperties: (record root)'
  bad id value       -> code='schema_pattern'  path=('id',)
                        value echoed: False
```

**Confirmed** — including that an attacker-chosen property name does not reach `path`.

## 9. U1 — editable install

```console
$ <temp>/rkedit/Scripts/python -m pip install -e . --no-build-isolation --no-deps
$ <temp>/rkedit/Scripts/python -c "from rookery import contracts; print(contracts.__file__)"
C:\Users\Travis\Documents\Coding\Rookery\src\rookery\contracts.py

$ <temp>/rkedit/Scripts/python -c "... parse_record ..."
parsed OK: PrinterIdentity

$ <temp>/rkedit/Scripts/python -m unittest discover -s tests
..........F...........
FAIL: test_packaged_schema_is_the_authoritative_schema
  File "...\tests\test_contracts.py", line 89
    self.assertFalse(Path(contracts.__file__).resolve().is_relative_to(ROOT / "src"))
AssertionError: True is not false

Ran 22 tests in 0.654s
FAILED (failures=1)
```

The package works correctly under an editable install; only the guard assertion fails, with a message that gives no indication of the cause. **Confirmed as described.**

## 10. U2 / M1 — coupling and test coverage

```
  pyproject version              : 0.1.0.dev1
  workflow references that wheel : True
  README references that wheel   : True

error codes pinned by tests: ['bytes_required', 'duplicate_key', 'invalid_json',
                              'invalid_unicode', 'object_required', 'too_deep',
                              'too_many_nodes']
any schema_* code pinned by a test: False
```

---

## What this review did not check

Stated plainly, in the spirit of the PR's own verification record:

- **I did not re-run the hosted CI.** I read `fixtures.yml` and reproduced its steps locally, and I took the linked [run 34728067314](https://github.com/travishriley/Rookery/actions/runs/34728067314) at face value for the Linux/Windows matrix results. I did not verify the runner images, the action SHAs against GitHub, or that the linked run corresponds to the reviewed commit beyond what the PR body states.
- **I did not audit the dependencies themselves.** The provenance table in `b01-contract-foundation.md` (licenses, upstream URLs) was not independently verified, and I did not review jsonschema, attrs, referencing or rpds-py source. [S1](02-security.md#s1) is about the *absence of hash locking*, not a claim that any current dependency is compromised.
- **No OS-level isolation, backup, restore, policy, slicer or printer behaviour was tested,** because none exists in this PR. The PR says so and it is accurate.
- **The fuzzing was seeded and bounded** — 4,000 mutations from one valid record with a fixed seed, not a coverage-guided campaign. It establishes that the obvious hostile shapes are handled, not that no input anywhere breaks the parser.
- **Timing measurements are from one machine under one load.** The absolute numbers will vary; the quadratic *shape* and the ~40× ratio against the control are the durable results.
- **I did not evaluate whether B01a is the right decomposition of B01.** That is a planning question, and the PR is explicit that B01 remains open.
