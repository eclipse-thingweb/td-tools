"""Guard that refactors do not change the binding's observable output.

These tests replay the golden snapshot recorded by ``scripts/update_golden.py``
and compare it to what the code produces now. They exist to make behaviour-
preserving refactors *provable*: the Thing Description side of the binding can be
restructured freely as long as the payload schemas it emits and the values it
decodes stay identical.

A failure here means either a genuine regression, or an intended change that
still needs its snapshot re-recorded and reviewed in the diff.
"""

from __future__ import annotations

import json

import pytest

from .conftest import EXAMPLES_DIR, REPO_ROOT
from .snapshot import build_snapshot

GOLDEN_PATH = REPO_ROOT / "tests" / "golden" / "snapshot.json"

pytestmark = pytest.mark.skipif(
    not GOLDEN_PATH.exists(),
    reason="no golden snapshot recorded; run `python -m scripts.update_golden`",
)

#: The curated examples are mirrored from upstream, so the parts of the snapshot
#: built from them are only comparable once they are present on disk.
_EXAMPLES_MISSING = pytest.mark.skipif(
    not any(EXAMPLES_DIR.glob("*.td.json")),
    reason="curated examples not synced; run `uv run sync-examples`",
)


def _recorded_case_ids() -> list[str]:
    """Vector ids in the recorded snapshot, for parametrisation at collection time.

    Returns an empty list when no snapshot exists yet: parametrisation is
    evaluated during collection, before the module-level skip mark can apply.
    """
    if not GOLDEN_PATH.exists():
        return []
    return sorted(json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))["decoded"])


@pytest.fixture(scope="module")
def golden() -> dict:
    """The recorded snapshot."""
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def current() -> dict:
    """The snapshot as the code produces it now (built once for the module)."""
    return json.loads(json.dumps(build_snapshot(), default=repr))


@_EXAMPLES_MISSING
def test_curated_payload_schemas_unchanged(golden, current):
    """Every curated example must still convert to byte-identical schema."""
    assert current["payload_schemas"] == golden["payload_schemas"]


@_EXAMPLES_MISSING
@pytest.mark.parametrize("case_id", _recorded_case_ids())
def test_decoded_vector_unchanged(golden, current, case_id):
    """Each test vector decodes to exactly the values recorded before.

    Parametrised per vector so a failure names the offending device and case
    instead of collapsing every vector into one assertion.
    """
    assert case_id in current["decoded"], f"vector {case_id!r} is no longer decoded"
    assert current["decoded"][case_id] == golden["decoded"][case_id]


def test_catalog_coverage_unchanged(golden, current):
    """The reference-device catalog must convert exactly as many devices as before."""
    want, got = golden["catalog"], current["catalog"]
    assert (got["scanned"], got["generated"]) == (want["scanned"], want["generated"])
    assert got["skipped"] == want["skipped"]


def test_catalog_schemas_unchanged(golden, current):
    """Every reference device must still round-trip to the same payload schema."""
    want, got = golden["catalog"]["schema_digests"], current["catalog"]["schema_digests"]
    changed = sorted(key for key in want.keys() & got.keys() if want[key] != got[key])
    assert not changed, f"round-tripped schema changed for: {changed}"
    assert sorted(got) == sorted(want), "the set of convertible devices changed"
