# Rookery

Local-first, human-reviewed 3D-printer configuration experiments. Status: Phase 0 design proposal only. No product, printer connection, or hardware validation is implemented.

The [owner's engineering requirements](ROOKERY_ASTRA_BUILD_PROMPT.md) are preserved unchanged. The system prepares evidence and offline candidates; a person independently imports, activates, and starts each physical test through their existing interface.

## Design Review

Tracking: [design PR #14](https://github.com/travishriley/Rookery/pull/14), [issue #1](https://github.com/travishriley/Rookery/issues/1), branch `design/1-phase-0`. The PR is open for human review and has not been merged.

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

Only synthetic examples belong in this public repository. Private printer records, photographs, credentials, and full-fidelity backups must live outside it. No project license is selected yet; third-party code and model assets have not been incorporated.

## Design Checks

Requires Python 3.11 or newer; the checker exits with that message on older interpreters. Observed environment: Windows 11 AMD64, Python 3.13.7. Existing validator dependencies are recorded in [requirements-design.txt](requirements-design.txt). These are design tooling versions, not a product support promise.

The install below writes into whichever environment is currently active; create a virtual environment first if that matters to you.

```powershell
python -m pip install -r requirements-design.txt
python tools/check_design.py
git diff --cached --check
```

These checks validate documents and schema shape. They do not validate a printer, slicer runtime, access sandbox, approval authenticity, or physical print quality. Future product acceptance criteria are specifications, not passing test claims.
