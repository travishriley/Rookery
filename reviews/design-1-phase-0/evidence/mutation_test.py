"""Evidence for S5: which safety rules would check_design.py notice the loss of?

Copies the repository to a temporary directory, deletes one safety rule from the schema
at a time, and re-runs check_design.py. A rule that can be deleted while the checker
still prints PASS is unprotected against future refactors.

The working tree is never modified. The temporary copy is removed afterwards.
"""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from _common import REPO

SCHEMA_REL = Path("schemas/0.1.0/rookery.schema.json")

MUTATIONS = {
    "DiagnosticResponse if/then  (model may escalate its own risk)":
        lambda s: (s["$defs"]["DiagnosticResponse"].pop("if"),
                   s["$defs"]["DiagnosticResponse"].pop("then")),
    "ProposalPayload if/then     (proposal may reach a klipper_audit_only domain)":
        lambda s: (s["$defs"]["ProposalPayload"].pop("if"),
                   s["$defs"]["ProposalPayload"].pop("then")),
    "Path pattern                (traversal and device paths become valid)":
        lambda s: s["$defs"]["Path"].__setitem__("pattern", "^.{1,1024}$"),
    "ActivationObservation rule  (matched Klipper activation needs no evidence)":
        lambda s: s["$defs"]["ActivationObservation"]["allOf"].pop(2),
    "BackupReceipt if/then       (a backup may claim verified with no read-back)":
        lambda s: (s["$defs"]["BackupReceipt"].pop("if"),
                   s["$defs"]["BackupReceipt"].pop("then")),
    "ProposalPayload maxItems    (a proposal may carry two independent changes)":
        lambda s: s["$defs"]["ProposalPayload"]["properties"]["changes"].pop("maxItems"),
}


def main():
    workdir = Path(tempfile.mkdtemp(prefix="rookery-mutation-"))
    sandbox = workdir / "repo"
    try:
        shutil.copytree(REPO, sandbox, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
        schema_path = sandbox / SCHEMA_REL
        original = schema_path.read_text(encoding="utf-8")
        schema = json.loads(original)

        print(f"{'checker':>10}   safety rule removed from the schema")
        print("-" * 92)
        unprotected = []
        for label, mutate in MUTATIONS.items():
            mutated = copy.deepcopy(schema)
            try:
                mutate(mutated)
            except (KeyError, IndexError) as error:
                print(f"{'SKIP':>10}   {label}  (schema changed: {error})")
                continue
            schema_path.write_text(json.dumps(mutated, indent=2), encoding="utf-8")
            result = subprocess.run([sys.executable, "tools/check_design.py"],
                                    cwd=sandbox, capture_output=True, text=True)
            passed = result.returncode == 0
            if passed:
                unprotected.append(label)
            print(f"{'PASS' if passed else 'FAIL':>10}   {label}"
                  f"{'  <-- UNPROTECTED' if passed else ''}")
            schema_path.write_text(original, encoding="utf-8")

        print("-" * 92)
        if unprotected:
            print(f"{len(unprotected)} of {len(MUTATIONS)} safety rules can be deleted "
                  f"without check_design.py noticing:")
            for label in unprotected:
                print(f"  - {label}")
        else:
            print("All mutated safety rules are covered by a negative probe.")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
