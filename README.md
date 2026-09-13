# Rookery

Local-first, human-reviewed 3D-printer configuration experiments. Status: Phase 0 design merged; the first Phase 1 contract-parsing foundation is under review. No printer connection, source importer, configuration writer, or hardware validation is implemented.

The [owner's engineering requirements](ROOKERY_ASTRA_BUILD_PROMPT.md) are preserved unchanged. The system prepares evidence and offline candidates; a person independently imports, activates, and starts each physical test through their existing interface.

## Design Review

Tracking: [design PR #14](https://github.com/travishriley/Rookery/pull/14), [issue #1](https://github.com/travishriley/Rookery/issues/1). The design was merged with explicit owner approval. Current work is [B01 #2](https://github.com/travishriley/Rookery/issues/2), branch `feat/2-contract-foundation`; see the [implementation scope and remaining gates](docs/implementation/b01-contract-foundation.md).

1. [Inventory and capability evidence](docs/design/inventory-and-capabilities.md)
2. [Requirements and traceability](docs/design/requirements.md)
3. [Architecture and access boundaries](docs/design/architecture.md)
4. [State machine](docs/design/state-machine.md)
5. [Threat and hazard model](docs/design/threat-hazard-model.md)
6. [Privacy, backup, recovery, and approval policy](docs/design/policies.md)
7. [Architecture decisions and owner review](docs/design/decisions.md)
8. [Data contracts](docs/design/data-contracts.md) and [JSON Schema drafts](schemas/0.1.0/rookery.schema.json)
9. [Acceptance specifications](docs/design/acceptance.md)
10. [Implementation backlog](docs/design/backlog.md) and [executed checks](docs/design/verification.md)

Only synthetic examples belong in this public repository. Private printer records, photographs, credentials, and full-fidelity backups must live outside it. No project license is selected yet; third-party dependencies are referenced with recorded provenance, not vendored. No model assets have been incorporated.

## Contract Foundation

The development package accepts one schema-versioned record as in-memory UTF-8 bytes. It returns an immutable envelope for any of the eleven record kinds, with exact original bytes and Decimal values. Parsing is not policy approval, proof of a backup, or authorization to perform an action. Canonical record hashes and fully typed nested domain models remain pending in B01.

Use CPython 3.13.7 x64 and a dedicated development environment. The commands below install the pinned dependencies into the active environment; wheel installation exercises bundled-schema lookup independently of the source layout.

```powershell
python -m pip install --only-binary=:all: -r requirements-dev.txt
python -m pip wheel . --no-deps --no-build-isolation --no-index --wheel-dir dist
python -m pip install --force-reinstall --no-deps --no-index dist/rookery_core-0.1.0.dev1-py3-none-any.whl
python -m pip check
python -m unittest discover -s tests -v
```

```python
from rookery import parse_record

# supplied_bytes is an explicitly provided synthetic JSON record, not a path.
record = parse_record(supplied_bytes)
print(record.kind, record.id)
```

The package exposes no CLI, file-path input, network client, printer adapter, writer or canonical digest API. [Fixture CI](.github/workflows/fixtures.yml) runs only synthetic design/package tests on GitHub-hosted machines; it does not prove worker isolation. Branch protection is not yet enabled.

## Design Checks

Requires Python 3.11 or newer; the checker exits with that message on older interpreters. Observed environment: Windows 11 AMD64, Python 3.13.7. Existing validator dependencies are recorded in [requirements-design.txt](requirements-design.txt). These are design tooling versions, not a product support promise.

The install below writes into whichever environment is currently active; create a virtual environment first if that matters to you.

```powershell
python -m pip install -r requirements-design.txt
python tools/check_design.py
python -m unittest discover -s tools -p test_check_design.py
git diff origin/main...HEAD --check
```

The diff command checks the committed PR changes even on a clean checkout. Before committing local edits, also run `git diff --check` and `git diff --cached --check` for unstaged and staged changes respectively.

These checks validate documents and schema shape. They do not validate a printer, slicer runtime, access sandbox, approval authenticity, or physical print quality. Future product acceptance criteria are specifications, not passing test claims.
