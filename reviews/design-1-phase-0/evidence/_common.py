"""Shared helpers for the review probe scripts. Read-only against the reviewed tree."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools"))

from check_design import FORMATS, no_remote_schema, parse  # noqa: E402

from jsonschema import Draft202012Validator  # noqa: E402
from referencing import Registry  # noqa: E402

SCHEMA = parse((REPO / "schemas/0.1.0/rookery.schema.json").read_text(encoding="utf-8"))
EXAMPLES = {item["kind"]: item for item in parse((REPO / "schemas/0.1.0/examples.json").read_text(encoding="utf-8"))}
DIGEST = "sha256:" + "a" * 64


def validator(schema=None):
    return Draft202012Validator(schema or SCHEMA, format_checker=FORMATS, registry=Registry(retrieve=no_remote_schema))


def branch_validator(name):
    """Validate against a single named $def, as check_supplemental does."""
    return validator({**SCHEMA, "oneOf": [{"$ref": f"#/$defs/{name}"}]})


def report(label, value, check):
    """Print whether `value` is accepted by `check`, aligned for scanning."""
    accepted = not list(check.iter_errors(value))
    print(f"  {'SCHEMA-VALID' if accepted else 'rejected    '}  {label}")
    return accepted


def heading(text):
    print(f"\n--- {text} ---")
