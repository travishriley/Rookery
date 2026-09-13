# Design Safety

There is no printer path in this PR. I checked directly rather than taking it on trust: `src/rookery/` contains no `open()`, no `subprocess`, no `socket`, no `urllib`/`requests`/`httpx`, no `os.system`, no `eval`/`exec`, no `pickle`, and no `__import__`. The only I/O is `importlib.resources` reading the packaged schema. `parse_record` takes `bytes` and returns a frozen object. The claim that this module cannot actuate anything holds.

So safety at this layer means two things: does the ingress boundary hold when fed hostile input, and are the bounds it advertises the bounds it actually has?

The first is answered well — see [05-what-is-good.md](05-what-is-good.md#robustness). The findings below are about the second, plus one about the schema's new status as a shipped artifact.

---

## <a id="a1"></a>A1 — Medium — `Time` accepts `"garbageZ"` for any consumer without format assertion

**Location:** `schemas/0.1.0/rookery.schema.json:26`

```json
"Time": {"type": "string", "format": "date-time", "pattern": "Z$"}
```

This PR's headline schema change fixes exactly this class of bug for two other types. `Digest` and `Id` both gained `$(?![\s\S])` because jsonschema applies `pattern` with `re.search`, where a bare `$` also matches just before a trailing newline. The implementation doc records the discovery honestly: *"new fixture tests exposed final-newline acceptance from regex `$` semantics."*

`Time` was not given the same treatment, and its pattern is far weaker than a terminator fix would address — `Z$` constrains almost nothing. All of the following are accepted as `created_at` when validated **without** a format checker (verified, `evidence/probe_schema_contract.py`):

```
no format checker: ACCEPTED  created_at='garbageZ'
no format checker: ACCEPTED  created_at='ZZZZZ'
no format checker: ACCEPTED  created_at='2026-09-12T12:00:00Z\n'
no format checker: ACCEPTED  created_at='2026-02-30T12:00:00Z'
```

**Rookery itself is not affected.** `contracts.py:168` always passes `format_checker=_FORMATS`, and `_utc_datetime` uses `re.fullmatch` plus `datetime.fromisoformat`, so the product rejects all four. I confirmed this. The finding is about the schema as an exported contract.

Why that matters more in this PR than it did in Phase 0: the schema was previously a design document read by one checker that always enabled format assertion. This PR packages it into a wheel as `rookery.schemas`, and the implementation doc states the intent plainly — *"The package bundles the authoritative schema directly from `schemas/0.1.0/`"*, with tests comparing the installed resource byte-for-byte against source. Anyone consuming that resource gets a document where:

- JSON Schema `format` is **annotation-only by default**; assertion is opt-in per validator, and most implementations do not enable it unless asked.
- `Digest` and `Id` are self-enforcing regardless of configuration, because of the change in this very PR.
- `Time` is not, and there is nothing in the schema to signal the asymmetry.

`approved_at` and `expires_at` are both `Time`. Approval expiry is one of the safety gates that `policies.md` relies on ("Validate immediately before export"), and `data-contracts.md` already records `approved_at < expires_at` as a runtime invariant. A consumer that cannot even establish those two fields are timestamps cannot evaluate that invariant.

**Suggested fix** — give `Time` the same self-contained pattern the format checker already applies, and keep `format` for calendar validation:

```json
"Time": {
  "type": "string",
  "format": "date-time",
  "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]+)?Z$(?![\\s\\S])"
}
```

That is byte-identical to the regex in `_utc_datetime` (`contracts.py:140`) with the terminator guard added, so the two cannot drift. Leap seconds and impossible dates such as `2026-02-30` still require `format`, which is correct and unavoidable — a regex cannot do calendar arithmetic. But after this change a format-less consumer rejects garbage rather than accepting it.

Worth adding a negative probe in `tools/check_design.py` that validates a bad timestamp **without** a format checker, since that is the consumer configuration the current tests never exercise.

---

## <a id="a2"></a>A2 — Medium — the documented limits bound input size, not validation cost

**Location:** `src/rookery/contracts.py:26-29`

```python
MAX_RECORD_BYTES = 1024 * 1024
MAX_DEPTH = 64
MAX_NODES = 50000
MAX_NUMBER_CHARS = 256
```

These four constants are the ingress bound, and the implementation doc presents them as the resource contract. They bound *size* linearly and do so correctly. They do not bound *time*, and one schema keyword makes the gap large.

Measured on a record that satisfies every one of the four limits (`evidence/probe_validation_cost.py`):

```
    0.068s     26,732 bytes  accepted   100 unique file entries
    0.122s    131,932 bytes  accepted   500 unique file entries
    0.433s    263,432 bytes  accepted   1000 unique file entries
    1.633s    527,432 bytes  accepted   2000 unique file entries
    3.590s    791,432 bytes  accepted   3000 unique file entries
    4.816s    923,432 bytes  accepted   3500 unique file entries

Control -- an equally large record without uniqueItems on objects:
    0.120s    740,891 bytes  accepted   3400 edges (no uniqueItems)
```

**4.8 seconds for a single sub-1 MiB record, against 0.12 s for a comparable record without the keyword — roughly 40×, growing quadratically.** Doubling the entry count from 1000 to 2000 multiplies time by 3.8; 2000 to 3000 multiplies by 2.2 for a 1.5× size increase, which is 1.5² almost exactly.

The mechanism is confirmed rather than inferred:

```
    0.000s  jsonschema._utils.uniq on 3000 distinct strings
    4.875s  jsonschema._utils.uniq on 3000 distinct objects
```

`jsonschema._utils.uniq` tries `sorted()` first, which succeeds for strings and gives O(n log n). Dictionaries are unorderable, so it falls back to a pairwise scan, which is O(n²). `SourceSnapshot.files` and `EvidenceBundle.captures` are both arrays of objects with `uniqueItems: true` — and both constraints were added in response to the Phase 0 review, so this is a cost that arrived with a correctness fix rather than a pre-existing one.

Placing the worst case last (so uniqueness fails only after every pair has been compared) costs the same 4.7 s and still returns a rejection, so an attacker does not need the record to be *valid* to spend the time.

**The implementation doc does say** *"These limits are provisional fixture-ingress limits, not an OS memory/CPU sandbox"*, which is honest and correct as far as it goes. But that sentence reads as a disclaimer about the absence of an *external* sandbox, not as a statement that an in-library quadratic makes the effective per-record cost ~40× what the size bounds suggest. A reader choosing `MAX_RECORD_BYTES = 1 MiB` would reasonably expect sub-second validation.

This matters now rather than later because B02 — the next milestone — is *"bounded read-only fixture import and lossless snapshot"*, the point at which this parser starts receiving files the operator did not hand-write. H07 in the threat model already names bounded resource use as a required property, and A03 requires "bounded resource use" as an observable outcome.

**Suggested fixes**, cheapest first:

1. **Add a cost probe to the test suite.** A regression test asserting that a worst-case record validates in under, say, 1 s would have caught this and would catch the next schema keyword with the same shape. This is the one I would land regardless of which mitigation is chosen.
2. **Lower the effective bound.** `MAX_NODES = 50000` permits ~3,846 file entries (see [A3](#a3)). If the real fixture ceiling is a few hundred files, `MAX_NODES = 8000` costs nothing in practice and caps validation near 0.2 s.
3. **Pre-check uniqueness cheaply before schema validation.** For `files`, uniqueness that matters is `(root_id, path)` and full-object identity — both projectable to a hashable tuple and checkable in O(n). The schema keyword can stay as the declarative contract for external consumers while the parser short-circuits the expensive path.

Worth recording whichever is chosen in `b01-contract-foundation.md` next to the existing limits paragraph, since the numbers there are the thing a reader will trust.

**Memory, for completeness:** the node budget is enforced after `json.loads` has already materialised the tree, so peak memory tracks input size rather than `MAX_NODES`. Measured at 13 MB peak for a 360 KB input rejected with `too_many_nodes`. That is a ~36× amplification but bounded and modest — roughly 38 MB at the 1 MiB ceiling. Not worth changing; noted so it is not mistaken for unbounded.

---

## <a id="a3"></a>A3 — Low — the schema declares a bound that can never apply

**Location:** `schemas/0.1.0/rookery.schema.json` (`SourceSnapshot.files`), `src/rookery/contracts.py:28`

```
  one FileEntry costs 13 nodes
  MAX_NODES=50,000 allows at most ~3,846 file entries
  schema declares files.maxItems = 10,000
```

Two bounds on the same array disagree by about 2.6×, and the tighter one lives in a different file. A reader of the schema alone — which, after this PR, includes anyone who installs the wheel for its `rookery.schemas` resource — takes away 10,000 as the limit. The real answer depends on `MAX_NODES`, on the parser's key-counting rule, and on how many fields a `FileEntry` happens to have.

This is not a vulnerability; both bounds fail closed and the tighter one wins. It is a coherence problem: neither number documents the actual limit, and the effective limit shifts silently if a field is ever added to `FileEntry` (14 nodes per entry would drop the ceiling to ~3,571 without any file that mentions `files` being edited).

**Suggested fix:** either bring `maxItems` down to something the parser can actually reach and state the relationship, or add a sentence to the limits paragraph in `b01-contract-foundation.md` saying that `MAX_NODES` binds before any array `maxItems` and that the schema's array bounds are upper bounds for external consumers rather than the parser's effective limit. The second is cheaper and is probably the honest description of the intent.

The same arithmetic applies to `Digests` (`maxItems: 10000`) and `edges` (`maxItems: 100000`), where the gap is larger still.

---

## What I checked and found correct

- **No actuation path of any kind.** No file, network, process, or device access in `src/rookery/`. `parse_record`'s docstring promise — *"never opens a user-supplied path"* — is literally true.
- **Remote schema retrieval is blocked**, by the same `NoSuchResource` mechanism as the design checker, and there is a test asserting it (`test_unknown_properties_and_script_strings_are_inert_data` calls `contracts._no_remote_schema` directly).
- **Untrusted strings stay inert.** The test that parses a record containing a URL while patching `socket.socket` and `subprocess.Popen` to raise is a good idea, and it passes.
- **Exact numeric preservation is real.** `0.10000000000000000000001` round-trips as a `Decimal`, and `9007199254740993` (2⁵³+1) is not rounded to binary64. Both matter later: `data-contracts.md` requires `Decimal` comparison at safety bounds, and a float round-trip would silently move a temperature bound.
- **Overflow and underflow are rejected, not silently clamped.** `1e309` and `1e-9999` both raise `number_out_of_range`, and the magnitude check deliberately does not store the float approximation.
- **`1.0` satisfies `"type": "integer"` while `true` and `"1"` do not.** The narrow type-checker extension is correct — `type(value) is int` excludes `bool` (which subclasses `int`), and the `Decimal` branch requires `is_finite()` before comparing to `to_integral_value()`, so a NaN could not slip through even if one could be constructed.
- **Schema shape is explicitly not policy, and the tests say so.** `test_shape_acceptance_explicitly_does_not_enforce_semantic_policy` asserts that an inverted range (`minimum=300, maximum=10`) and duplicate-identity files still parse, with a comment that these are limitations rather than verdicts. That is exactly the right way to encode the Phase 0 review's conclusion that those invariants belong to the policy engine.
