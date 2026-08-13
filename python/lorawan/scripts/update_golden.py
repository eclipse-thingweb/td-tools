"""Record the golden behavioural snapshot used to guard refactors.

Run this **before** starting a refactor of the Thing Description side of the
binding, then run the test suite after it: ``tests/test_golden.py`` replays the
same snapshot and fails on any difference, proving the payload schemas emitted
and the values decoded are unchanged.

Only re-run this when a change to the decoded output is *intended*; the diff on
``tests/golden/snapshot.json`` is then the reviewable record of that intent.

Usage::

    uv run --no-sync python -m scripts.update_golden
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.snapshot import build_snapshot

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = REPO_ROOT / "tests" / "golden" / "snapshot.json"


def main() -> None:
    """Rebuild the snapshot and write it to ``tests/golden/snapshot.json``."""
    snapshot = build_snapshot()
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False, default=repr) + "\n",
        encoding="utf-8",
    )

    catalog = snapshot["catalog"]
    print(f"Wrote {GOLDEN_PATH.relative_to(REPO_ROOT)}")
    print(f"  curated payload schemas: {len(snapshot['payload_schemas'])}")
    print(f"  decoded vectors:         {len(snapshot['decoded'])}")
    print(f"  catalog devices:         {catalog['generated']}/{catalog['scanned']}")


if __name__ == "__main__":
    main()
