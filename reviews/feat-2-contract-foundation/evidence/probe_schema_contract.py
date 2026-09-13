"""Mechanism of the uniqueItems cost, node-budget coherence, and error-path leakage."""
import json
from pathlib import Path
import time

from rookery import ContractError, contracts, parse_record

ROOT = Path(__file__).resolve().parents[3]
D = "sha256:" + "a" * 64

print("=== 1. Why objects are quadratic but strings are not ===")
from jsonschema._utils import uniq  # noqa: E402
for label, items in [
    ("3000 distinct strings", [f"sha256:{i:064x}" for i in range(3000)]),
    ("3000 distinct objects", [{"a": i, "b": "x"} for i in range(3000)]),
]:
    start = time.perf_counter()
    uniq(items)
    print(f"  {time.perf_counter() - start:7.3f}s  jsonschema._utils.uniq on {label}")
print("  -> sorted() succeeds for strings (O(n log n)); dicts are unorderable so uniq")
print("     falls back to a pairwise scan (O(n^2)).")

print()
print("=== 2. Is the schema's own maxItems reachable under MAX_NODES? ===")


def nodes(value):
    """Count the way _check_tree does: object keys count as nodes."""
    total = 1
    if isinstance(value, dict):
        for key, item in value.items():
            total += nodes(key) + nodes(item)
    elif isinstance(value, list):
        for item in value:
            total += nodes(item)
    return total


entry = {"root_id": "r", "path": "f.json", "digest": D, "size_bytes": 1,
         "metadata_digest": D, "role": "other_dependency"}
per_entry = nodes(entry)
print(f"  one FileEntry costs {per_entry} nodes")
print(f"  MAX_NODES={contracts.MAX_NODES:,} allows at most ~{contracts.MAX_NODES // per_entry:,} file entries")
schema = json.loads((ROOT / "schemas/0.1.0/rookery.schema.json").open(encoding="utf-8").read())
declared = schema["$defs"]["SourceSnapshot"]["properties"]["files"]["maxItems"]
print(f"  schema declares files.maxItems = {declared:,}")
print(f"  -> the schema bound is unreachable; MAX_NODES binds first by ~{declared // (contracts.MAX_NODES // per_entry)}x")

print()
print("=== 3. Does ContractError.path leak attacker-controlled property names? ===")
examples = json.loads((ROOT / "schemas/0.1.0/examples.json").open(encoding="utf-8").read())
value = dict(examples[0])
value["a_secret_looking_property_name"] = "x"
try:
    parse_record(json.dumps(value).encode())
except ContractError as error:
    print(f"  unknown property   -> code={error.code!r}  path={error.path}")
    print(f"                        str={str(error)!r}")

value = dict(examples[0])
value["label"] = "s3cr3t-value-should-not-appear"
value["id"] = "bad id"
try:
    parse_record(json.dumps(value).encode())
except ContractError as error:
    print(f"  bad id value       -> code={error.code!r}  path={error.path}")
    print(f"                        value echoed: {'s3cr3t' in str(error) or 'bad id' in str(error)}")

print()
print("=== 4. Time format: does the schema pattern alone hold without the format checker? ===")
from jsonschema import Draft202012Validator  # noqa: E402
from referencing import Registry  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
lax = Draft202012Validator({**schema, "oneOf": [{"$ref": "#/$defs/PrinterIdentity"}]},
                           registry=Registry(retrieve=contracts._no_remote_schema))
for bad in ["garbageZ", "2026-09-12T12:00:00Z\n", "2026-02-30T12:00:00Z", "ZZZZZ"]:
    value = dict(examples[0])
    value["created_at"] = bad
    verdict = "ACCEPTED" if lax.is_valid(value) else "rejected"
    print(f"  no format checker: {verdict}  created_at={bad!r}")
print("  (rookery itself always passes a format checker, so the product is unaffected;")
print("   this is about the schema shipped as a contract for other implementations.)")
