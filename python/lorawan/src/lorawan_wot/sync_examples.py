"""Sync curated example TDs and test vectors from the upstream repository.

The curated ``*.td.json`` and ``*.vectors.json`` files under ``examples/`` are
maintained in the ``eclipse-thingweb/examples`` repository and are **not**
checked in to this repo.  Run this script after cloning (or whenever you want
to pull the latest upstream examples):

Usage::

    uv run sync-examples
    # or:
    uv run python -m scripts.sync_examples
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REMOTE = "https://github.com/eclipse-thingweb/examples"
REMOTE_SUBDIR = "TTC26/examples"
_EXTENSIONS = (".td.json", ".vectors.json")


def _find_examples_dir() -> Path:
    """Locate the examples/ folder relative to the installed package or repo."""
    # Installed as a package: src/lorawan_wot/ -> repo root is four levels up.
    # Running from repo: same result via resolve().
    candidate = Path(__file__).resolve().parents[3] / "examples"
    if candidate.is_dir():
        return candidate
    # Fallback: cwd/examples (e.g. when invoked from python/lorawan/).
    return Path.cwd() / "examples"


def main() -> None:
    local_examples = _find_examples_dir()
    print(f"Cloning {REMOTE} (depth=1)…")
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            ["git", "clone", "--depth=1", REMOTE, tmp],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"ERROR: git clone failed:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)

        src = Path(tmp) / REMOTE_SUBDIR
        if not src.is_dir():
            print(
                f"ERROR: expected subdirectory '{REMOTE_SUBDIR}' not found in cloned repo.",
                file=sys.stderr,
            )
            sys.exit(1)

        copied = 0
        for f in sorted(src.iterdir()):
            if f.is_file() and any(f.name.endswith(ext) for ext in _EXTENSIONS):
                dest = local_examples / f.name
                shutil.copy2(f, dest)
                print(f"  copied  {f.name}")
                copied += 1

    print(f"\nDone — {copied} file(s) synced to {local_examples}")


if __name__ == "__main__":
    main()
