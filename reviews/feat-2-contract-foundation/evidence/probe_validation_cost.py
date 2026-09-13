"""Do MAX_RECORD_BYTES / MAX_NODES / MAX_DEPTH actually bound validation CPU time?

The limits bound the *size* of the input. Schema keywords such as uniqueItems on
an array of objects are O(n^2) in jsonschema (sorted() fails on dicts, so it
falls back to pairwise comparison). This measures the worst case that still fits
inside every documented limit.
"""
import json
from pathlib import Path
import time

from rookery import ContractError, contracts, parse_record

ROOT = Path(__file__).resolve().parents[3]

D = "sha256:" + "a" * 64


def timed(label, raw):
    start = time.perf_counter()
    try:
        parse_record(raw)
        outcome = "accepted"
    except ContractError as error:
        outcome = f"rejected({error.code})"
    elapsed = time.perf_counter() - start
    print(f"  {elapsed:7.3f}s  {len(raw):>9,} bytes  {outcome:<28} {label}")
    return elapsed


def file_entry(index):
    # Distinct digests so uniqueItems must compare every pair before succeeding.
    return {"root_id": "r", "path": f"f{index}.json", "digest": "sha256:" + f"{index:064x}",
            "size_bytes": 1, "metadata_digest": D, "role": "other_dependency"}


def snapshot(count):
    return {"schema_version": "0.1.0", "kind": "SourceSnapshot", "id": "s",
            "created_at": "2026-09-12T12:00:00Z", "printer_digest": D,
            "content_manifest_digest": D, "capture_started_at": "2026-09-12T12:00:00Z",
            "capture_finished_at": "2026-09-12T12:00:00Z", "complete": True,
            "files": [file_entry(i) for i in range(count)],
            "edges": [], "provenance_digest": D, "issues": []}


print("Documented limits: "
      f"MAX_RECORD_BYTES={contracts.MAX_RECORD_BYTES:,}  MAX_NODES={contracts.MAX_NODES:,}  "
      f"MAX_DEPTH={contracts.MAX_DEPTH}\n")

print("SourceSnapshot.files -- uniqueItems over an array of objects:")
worst = 0
for count in [100, 500, 1000, 2000, 3000, 3500]:
    raw = json.dumps(snapshot(count)).encode()
    if len(raw) > contracts.MAX_RECORD_BYTES:
        print(f"  (skipped {count} files: {len(raw):,} bytes exceeds MAX_RECORD_BYTES)")
        continue
    worst = max(worst, timed(f"{count} unique file entries", raw))

print()
print("Same shape, but the duplicate is at the very end (forces a full pairwise scan):")
value = snapshot(3400)
value["files"][-1] = dict(value["files"][0])
raw = json.dumps(value).encode()
if len(raw) <= contracts.MAX_RECORD_BYTES:
    worst = max(worst, timed("3400 entries, last duplicates first", raw))

print()
print("Control -- an equally large record without uniqueItems on objects:")
edges = {"schema_version": "0.1.0", "kind": "SourceSnapshot", "id": "s",
         "created_at": "2026-09-12T12:00:00Z", "printer_digest": D,
         "content_manifest_digest": D, "capture_started_at": "2026-09-12T12:00:00Z",
         "capture_finished_at": "2026-09-12T12:00:00Z", "complete": True,
         "files": [file_entry(0)],
         "edges": [{"from_digest": "sha256:" + f"{i:064x}", "to_digest": D,
                    "relation": "include", "order": i} for i in range(3400)],
         "provenance_digest": D, "issues": []}
raw = json.dumps(edges).encode()
if len(raw) <= contracts.MAX_RECORD_BYTES:
    timed("3400 edges (no uniqueItems)", raw)

print(f"\nWorst single-record validation time observed: {worst:.3f}s")
