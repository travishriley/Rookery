"""Evidence for S1: the Path pattern accepts Windows device names and aliasing paths.

Part 2 writes to a fresh temporary directory and removes it afterwards. It touches
nothing in the repository and no printer, device or network resource.
"""

import os
import re
import shutil
import tempfile
from pathlib import Path

from _common import SCHEMA, heading

PATTERN = SCHEMA["$defs"]["Path"]["pattern"]

COVERED_BY_CHECKER = [
    "../outside.json", "nested/../../outside.json", "/absolute.json",
    "C:/outside.json", "file.json:secret", "..\\outside.json",
]
NOT_COVERED = [
    "NUL", "CON", "PRN", "AUX", "COM1", "LPT1.json", "aux/config.cfg",
    "printer.cfg.", "printer.cfg ", "dir/", "a//b.json", "...", "a/.../b",
]


def probe_pattern():
    heading("S1 part 1: what the Path pattern accepts")
    print(f"  pattern: {PATTERN}\n")
    print("  already probed by check_design.py:118 (all correctly rejected):")
    for value in COVERED_BY_CHECKER:
        ok = re.fullmatch(PATTERN, value) is not None
        print(f"    {'ACCEPTED <-- unexpected' if ok else 'rejected'}  {value!r}")
    print("\n  NOT probed by check_design.py:")
    for value in NOT_COVERED:
        ok = re.fullmatch(PATTERN, value) is not None
        print(f"    {'ACCEPTED <-- finding' if ok else 'rejected'}  {value!r}")


def probe_filesystem():
    heading("S1 part 2: what Windows actually does with those paths")
    if os.name != "nt":
        print("  skipped: this behaviour is Windows-specific and this host is not Windows.")
        return
    workdir = Path(tempfile.mkdtemp(prefix="rookery-review-"))
    try:
        target = workdir / "secret.json"
        target.write_text("ORIGINAL")
        for variant in ["secret.json.", "secret.json "]:
            try:
                (workdir / variant).write_text(f"OVERWRITTEN-VIA-{variant!r}")
            except OSError as error:
                print(f"  {variant!r}: OSError {error}")
                continue
            print(f"  wrote {variant!r} -> secret.json now reads {target.read_text()!r}")
            print(f"    directory listing: {sorted(p.name for p in workdir.iterdir())}")
        nul = workdir / "NUL"
        nul.write_text("x" * 10)
        print(f"  wrote 'NUL' -> os.path.exists reports {nul.exists()}, "
              f"but listing is {sorted(p.name for p in workdir.iterdir())}")
        print("    (the bytes went to the null device and were discarded; "
              "an existence check after restore would still report success)")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    probe_pattern()
    probe_filesystem()
