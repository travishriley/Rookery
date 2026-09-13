"""Packaging and dataclass details that affect contributors and version bumps."""
import dataclasses
import json
import re
from pathlib import Path

from rookery import Record, contracts

ROOT = Path(__file__).resolve().parents[3]
examples = json.loads((ROOT / "schemas/0.1.0/examples.json").read_text(encoding="utf-8"))
raw = json.dumps(examples[0]).encode()

print("=== 1. Is Record.__hash__ = None load-bearing, or would the dataclass fail anyway? ===")
record = Record(raw)
print(f"  Record.__hash__ is None: {Record.__hash__ is None}")


@dataclasses.dataclass(frozen=True, slots=True)
class WithoutExplicitNone:
    raw_json: bytes
    data: dict = dataclasses.field(init=False, default_factory=dict)


try:
    hash(WithoutExplicitNone(b"x"))
    print("  a comparable dataclass WITHOUT the explicit None: hash() succeeded")
except TypeError as error:
    print(f"  a comparable dataclass WITHOUT the explicit None: TypeError({error})")
print("  -> the explicit None makes unhashability intentional and stable rather than")
print("     an accident of whichever field types happen to be unhashable.")

print()
print("=== 2. Hardcoded wheel filename vs declared version ===")
pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
version = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
workflow = (ROOT / ".github/workflows/fixtures.yml").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
expected = f"rookery_core-{version}-py3-none-any.whl"
print(f"  pyproject version              : {version}")
print(f"  workflow references that wheel : {expected in workflow}")
print(f"  README references that wheel   : {expected in readme}")
for label, text in [("workflow", workflow), ("README", readme)]:
    for hit in set(re.findall(r"rookery_core-[0-9a-zA-Z.]+-py3-none-any\.whl", text)):
        print(f"    {label}: hardcoded -> {hit}")
print("  -> bumping `version` in pyproject.toml silently breaks CI and the documented")
print("     install command until both literals are edited by hand.")

print()
print("=== 3. Do the tests run against an editable install? ===")
test = (ROOT / "tests/test_contracts.py").read_text(encoding="utf-8")
guard = [line.strip() for line in test.splitlines() if "is_relative_to" in line]
print(f"  guard in test_contracts.py: {guard[0] if guard else '(none)'}")
print(f"  contracts.__file__ now    : {contracts.__file__}")
print("  -> `pip install -e .` puts contracts.__file__ under src/, so this assertion")
print("     fails with 'False is not true' and no explanation of the cause.")

print()
print("=== 4. Wheel metadata completeness ===")
from importlib import metadata  # noqa: E402
meta = metadata.metadata("rookery-core")
for key in ["Name", "Version", "Requires-Python", "License", "License-Expression",
            "Description-Content-Type", "Classifier", "Author", "Project-URL"]:
    print(f"  {key:26}: {meta.get(key) or '(absent)'}")
