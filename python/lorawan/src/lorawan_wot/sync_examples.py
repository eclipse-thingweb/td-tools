"""Sync curated example TDs and test vectors from the upstream repository.

The curated ``*.td.json`` and ``*.vectors.json`` files under ``examples/`` are
maintained in the ``eclipse-thingweb/examples`` repository and are **not**
checked in to this repo.  Run this script after cloning (or whenever you want
to pull the latest upstream examples):

Files are copied verbatim.  Upstream may still publish Thing Descriptions in the
pre-0.3.0 property model, which this binding rejects outright; when that happens
the sync names the affected files and exits non-zero instead of rewriting them
on the way in.  Migrating silently would hide the divergence from upstream,
which is the one thing worth knowing at that point.

Usage::

    uv run sync-examples
    # or:
    uv run python -m scripts.sync_examples
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from lorawan_wot import vocab

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


def _outdated(examples: Path) -> list[str]:
    """Names of synced Thing Descriptions that still speak the pre-0.3.0 dialect."""
    return sorted(
        path.name
        for path in examples.glob("*.td.json")
        if vocab.uses_withdrawn_vocabulary(json.loads(path.read_text(encoding="utf-8")))
    )


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

    outdated = _outdated(local_examples)
    if outdated:
        print(
            "\nWARNING: upstream still publishes the pre-0.3.0 property model.\n"
            f"  Affected: {', '.join(outdated)}\n"
            "  This binding rejects that shape, so the test suite fails until the\n"
            "  synced files are rewritten into the events model:\n\n"
            "      uv run python -m scripts.migrate_td_to_events examples\n",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
