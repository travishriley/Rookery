# B01a Contract Foundation

Tracking: [B01 issue #2](https://github.com/travishriley/Rookery/issues/2), branch `feat/2-contract-foundation`. Phase 0 [PR #14](https://github.com/travishriley/Rookery/pull/14) was merged with explicit owner approval at `007919457864275fe4b537b5e9c19446f03a288c`. That approval grants no printer or experiment authority.

## Scope and API

This is the first bounded part of B01, not completion of B01 or Phase 1. `rookery.parse_record(raw_json: bytes) -> Record` accepts one record already in memory. It does not take a filename, URL, command, callback or schema supplied by the caller. There is no CLI, network client, source importer, writer, backup engine, approval validator, slicer or model adapter.

The frozen `Record` envelope exposes a `RecordKind` enum, typed record ID, schema version, original UTC timestamp text, immutable original bytes, and a recursively immutable `data` mapping. Objects become mapping proxies and arrays become tuples. Nested values remain schema-checked JSON values, not eleven complete per-field Python domain models. Those models remain B01b work. `Record(...)` validates too; ordinary construction or `dataclasses.replace` cannot skip validation. Python immutability is an accidental-mutation guard, not an adversarial process boundary.

The package bundles the authoritative schema directly from `schemas/0.1.0/`, using an explicit [setuptools package-directory mapping](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html). There is no generated schema copy and no dependency on the checkout at runtime. Tests compare the installed resource byte-for-byte with the source and rerun the design checker's record probes through the installed parser. The two `Id`/`Digest` patterns now require a strict end-of-string: new fixture tests exposed final-newline acceptance from regex `$` semantics. No persistent authoritative records or new schema fields exist yet.

## Parsing Contract

- Input is UTF-8 bytes only, without a BOM. Duplicate keys (including escaped equivalents), malformed/trailing JSON, non-finite constants, lone surrogates and unknown record versions/kinds/properties fail closed.
- Maximum input is 1 MiB; maximum decoded nesting depth is 64; maximum tree size is 50,000 nodes, counting object keys as nodes; maximum numeric token length is 256 characters. Byte limits apply before decoding; tree limits apply before schema validation. Interpreter recursion errors become a bounded parsing failure. These limits are provisional fixture-ingress limits, not an OS memory/CPU sandbox.
- Integer tokens retain exact Python integers. Fractional/exponent tokens retain exact `Decimal` values. Such tokens must also have a finite, nonzero binary64 approximation unless their exact value is zero; overflow and nonzero underflow are rejected. The approximation is a magnitude check only, never the stored value or a policy comparison.
- A mathematical integer token such as `1.0` satisfies a JSON Schema integer, while booleans and strings never coerce to integers. The [jsonschema type checker](https://python-jsonschema.readthedocs.io/en/stable/validate/) is extended narrowly for exact Decimal integers; the existing number/string/boolean constraints remain in force.
- Timestamp strings preserve all fractional digits. Calendar validation uses `datetime` but its microsecond-truncated result is not stored or used for ordering. Timestamp ordering and expiration enforcement remain pending.
- Expected failures raise `ContractError` with a stable code and field path, without embedding rejected values in its message. Records do not display raw content in `repr`.

There is intentionally no canonical serialization, record digest, equality-by-canonical-content, authentication verdict or persistence API. Original wire bytes remain available and equality includes them. Sorting a dictionary or converting these Decimal values to floats is **not** an approved canonicalization algorithm. B01b must reconcile exact decimal values and large integers with RFC 8785's numeric profile, select a vetted implementation, and supply independent vectors/domain-prefix rules before authoritative record hashes are introduced.

Inverted ranges, differing objects with duplicate semantic identities, forged approvals and fictional backup claims can still pass schema shape. Their fail-closed semantic requirements remain in [data-contracts.md](../design/data-contracts.md); this module does not authorize anything from them. Unknown hardware bounds and the operational change allowlist remain unset/empty.

## Runtime and Dependencies

Development target: standard CPython 3.13, initially tested with **3.13.7 x64**. Package metadata requires `>=3.13,<3.14`; no other Python minor is supported by this milestone. Local target is Windows 11 AMD64. Fixture CI targets GitHub-hosted `ubuntu-24.04` and `windows-2025` x64, not printer hosts. Passing these fixtures is not an arbitrary-file or deployment support claim. Hosted images are versioned labels, not immutable OS image digests.

Exact runtime/transitive pins are in [pyproject.toml](../../pyproject.toml); [requirements-dev.txt](../../requirements-dev.txt) reuses the existing design-tool pins. All runtime packages and the build backend were already available in the shared environment and were also installed as wheels into a clean workspace-local test environment. No third-party source was copied or vendored. Installed metadata and upstream URLs were inspected on 2026-09-12:

| Dependency | Version | Provenance / license | Compatibility scope |
| --- | --- | --- | --- |
| jsonschema | 4.25.1 | [python-jsonschema/jsonschema](https://github.com/python-jsonschema/jsonschema), MIT | Draft 2020-12, explicit format checker, denied remote reference retrieval |
| referencing | 0.36.2 | [python-jsonschema/referencing](https://github.com/python-jsonschema/referencing), MIT | Local schema resolution only |
| attrs | 25.3.0 | [python-attrs/attrs](https://github.com/python-attrs/attrs), MIT | Validator dependency |
| jsonschema-specifications | 2025.4.1 | [python-jsonschema/jsonschema-specifications](https://github.com/python-jsonschema/jsonschema-specifications), MIT | Validator metaschemas |
| rpds-py | 0.27.0 | [crate-py/rpds](https://github.com/crate-py/rpds), MIT | Persistent mapping dependency; platform wheel required |
| setuptools | 80.9.0 | [pypa/setuptools](https://github.com/pypa/setuptools), MIT | Build backend with bundled wheel builder; development only |
| pip | 25.2 | [pypa/pip](https://github.com/pypa/pip), MIT | Development installer, not a runtime import |

The design-only markdown-it-py/mdurl pins and their license review remain in [inventory-and-capabilities.md](../design/inventory-and-capabilities.md). MIT metadata permits dependency use subject to preserving applicable notices; it does not select a Rookery project license or constitute a full bundled-dependency/advisory audit. Project licensing remains an owner decision, and no package publishing/release workflow is added. Version pins are not artifact-hash locks; dependency hash locking and a release vulnerability review remain B01 follow-ups. Public dependency downloads occur only in CI bootstrap, not in record parsing.

## CI and Review Boundary

The workflow has real `design-contracts` and `unit-fixtures` jobs. It deliberately does not create placeholder green `boundary-fixtures` or `restore-fixtures` checks before those implementations exist. Tests run from an installed wheel, not an editable/source-path import. The wheel has only the explicit package modules and schema resource; no private records, build prompt or fixture images are packaged.

Official Action release metadata, inputs/runtime declarations and licenses were inspected before pinning:

| Action | Immutable revision | Review |
| --- | --- | --- |
| actions/checkout v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | [Pinned source](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1), MIT, Node 24; persisted credentials disabled |
| actions/setup-python v7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` | [Pinned source](https://github.com/actions/setup-python/tree/5fda3b95a4ea91299a34e894583c3862153e4b97), MIT, Node 24; Python/pip versions fixed, no shared package cache |

Consistent with [GitHub's secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use), only `contents: read` is granted. Triggers are `pull_request` and pushes to `main`; no `pull_request_target`, privileged follow-up workflow, deployment, publication, secret expression, custom token or self-hosted runner is configured. The read-only GitHub token exists during checkout/setup, but is not passed to tests or persisted in Git. No printer keys, live mounts, private records or home-network attachment is configured. GitHub-hosted runners still have general internet access: this is **not** a demonstrated OS-enforced worker sandbox or A01 pass.

Repository state re-read after the approved merge: `main.protected` was false, rulesets were empty, and the only listed collaborator was `travishriley` (admin). Actions are enabled with all Actions allowed and no repository-enforced SHA-pinning rule; this workflow pins its own references. No rule was changed. Recommended eventual required checks are `design-contracts`, `unit-fixtures (ubuntu-24.04)` and `unit-fixtures (windows-2025)`, plus a genuinely separate human reviewer, dismissal of stale approvals and no bypass by automation. Those controls are recommendations until the owner selects an arrangement and enforcement is verified. Agent and owner GitHub writes currently share the owner account; issue/PR comments from that account are not independent human reviews.

## Checks and Next Work

The first local package-test run caught the ID/digest newline regression; no passing result is claimed for that initial run. A first disposable virtual environment inherited the existing system dependencies: its package tests passed, but `pip check` found an unrelated pre-existing `snaptrade-python-sdk`/`typing_extensions` conflict. Those shared packages were not changed. A second workspace-local environment without system packages installed the exact development pins from public PyPI wheels, built/installed the project wheel offline, and passed `pip check` and package tests. No global package was installed or upgraded.

Executed locally in the clean environment: 19 installed-package tests; nine design-tool regression tests (including sixteen selected schema mutations); design validation of 230 references, 26 positive shapes, 119 negative probes, 33 local links and the unchanged prompt digest; successful wheel build/install and `pip check`. JavaScript RegExp probes independently reject final newlines/CRLF in IDs and digests. The wheel inventory contains only package modules, schema, typing marker and package metadata. The design checker and workflow explicitly exclude physical, isolation and authorization claims.

Final whitespace checks and hosted results are recorded with the implementation PR. Hosted runs establish the clean-install Linux/Windows matrix only once their actual results are available.

B01 remains open. Next smallest milestone is B01b: explicit per-field immutable domain models and a reviewed canonical-number/hash profile with independent vectors, retaining exact source bytes. Complete model/schema parity, hash-locked dependencies and the repository reviewer/protection decision before treating B01 as done. B02's single synthetic Orca import/snapshot/temporary restore follows that foundation; no live access is needed.
