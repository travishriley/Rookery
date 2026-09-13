"""Does parse_record ever raise something other than ContractError?

That is the core robustness claim for an ingress parser: callers are told to
expect ContractError, so any other escaping exception is an unhandled path.
"""
import json
import random
import sys
import traceback
from pathlib import Path

from rookery import ContractError, parse_record

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = json.loads((ROOT / "schemas/0.1.0/examples.json").read_text(encoding="utf-8"))

CASES = []


def add(label, raw):
    CASES.append((label, raw))


# Structural / encoding edges
add("empty", b"")
add("null byte only", b"\x00")
add("bare BOM", b"\xef\xbb\xbf")
add("NUL inside a string", b'{"id":"a\x00b"}')
add("raw control char in string", b'{"id":"a\x01b"}')
add("very long key", b'{"' + b"k" * 500000 + b'":1}')
add("deeply nested objects", b'{"a":' * 300 + b"1" + b"}" * 300)
add("unicode escape overlong", b'{"id":"\\u0041\\u0301"}')
add("lone high surrogate pair split", b'{"id":"\\ud83d"}')
add("valid surrogate pair", b'{"id":"\\ud83d\\ude00"}')
add("huge exponent", b'{"n":1E+999999999999999999}')
add("huge negative exponent", b'{"n":1E-999999999999999999}')
add("negative zero", b'{"n":-0.0}')
add("integer with leading plus", b'{"n":+1}')
add("bare decimal point", b'{"n":.5}')
add("hex number", b'{"n":0x10}')
add("duplicate across nesting", b'{"a":{"b":1},"a":{"b":2}}')
add("array root", b"[]")
add("string root", b'"x"')
add("number root", b"1")
add("trailing whitespace only", b"   ")
add("utf-16 encoded", '{"id":"a"}'.encode("utf-16"))
add("utf-8 overlong encoding", b'{"id":"\xc0\xaf"}')
add("truncated multibyte", b'{"id":"\xe2\x82"}')
add("json with tab in string", b'{"id":"a\tb"}')

# Schema-shaped but hostile
base = EXAMPLES[0]
for mutation, value in [
    ("id is a huge string", "a" * 200000),
    ("id is a list", []),
    ("id is a dict", {}),
    ("id is a number", 1),
    ("label is null", None),
]:
    changed = dict(base)
    changed["id" if "id" in mutation else "label"] = value
    add(mutation, json.dumps(changed).encode())

# Random fuzz seeded from a valid record
valid = json.dumps(EXAMPLES[0]).encode()
rng = random.Random(20260913)
for i in range(4000):
    data = bytearray(valid)
    for _ in range(rng.randint(1, 6)):
        op = rng.random()
        if op < 0.4 and data:
            data[rng.randrange(len(data))] = rng.randrange(256)
        elif op < 0.7 and data:
            del data[rng.randrange(len(data))]
        else:
            data.insert(rng.randrange(len(data) + 1), rng.randrange(256))
    CASES.append((f"fuzz#{i}", bytes(data)))

unexpected = []
accepted = 0
rejected = 0
for label, raw in CASES:
    try:
        parse_record(raw)
        accepted += 1
    except ContractError:
        rejected += 1
    except RecursionError as error:
        unexpected.append((label, "RecursionError", str(error)[:80], raw[:60]))
    except Exception as error:  # noqa: BLE001 - the point is to catch everything
        unexpected.append((label, type(error).__name__, str(error)[:80], raw[:60]))

print(f"cases={len(CASES)}  accepted={accepted}  ContractError={rejected}  UNEXPECTED={len(unexpected)}")
if unexpected:
    print("\nExceptions that are NOT ContractError:")
    seen = set()
    for label, kind, message, sample in unexpected:
        key = (kind, message)
        if key in seen:
            continue
        seen.add(key)
        print(f"  {kind}: {message}")
        print(f"     first seen: {label}   input starts: {sample!r}")
    print(f"\n  ({len(unexpected)} total occurrences, {len(seen)} distinct)")
