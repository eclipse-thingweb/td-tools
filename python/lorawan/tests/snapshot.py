"""Builder for the golden behavioural snapshot of the binding.

The snapshot pins the *observable output* of the binding -- the payload schemas
it emits and the values it decodes -- so a refactor of the Thing Description side
can be proven not to have changed anything downstream. It is deliberately built
from the public entry points only (:func:`~lorawan_wot.converter.td_to_payload_schema`
and :func:`~lorawan_wot.decode.decode_uplink`), never from internals, so it stays
valid across restructurings of the modules themselves.

Both the checked-in fixture writer (``scripts/update_golden.py``) and the test
that verifies it (``tests/test_golden.py``) call :func:`build_snapshot`, so the
recorded and the asserted snapshot can never drift apart.

What is recorded, and why in that form:

* ``payload_schemas`` -- the full schema for each curated example. Few and small,
  so they are stored verbatim and diff readably when something regresses.
* ``decoded`` -- every test vector's decoded field dictionary. This is the
  contract users actually depend on.
* ``catalog`` -- coverage counts plus one digest per reference device. 157
  schemas are too bulky to store verbatim, and a digest is enough to detect
  drift; regenerate locally and diff the schema itself when one trips.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from lorawan_wot.converter import ConversionError, td_to_payload_schema
from lorawan_wot.decode import decode_uplink

from .conftest import EXAMPLES_DIR, load_json, vector_files


def _digest(payload: Any) -> str:
    """Return a stable SHA-256 over ``payload``'s canonical JSON form.

    ``sort_keys`` canonicalises mapping order (which carries no meaning) while
    leaving list order intact (which does -- field order drives the wire layout).
    """
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=repr)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _curated_payload_schemas() -> dict[str, Any]:
    """Convert every curated example TD to its payload schema."""
    schemas: dict[str, Any] = {}
    for td_path in sorted(EXAMPLES_DIR.glob("*.td.json")):
        name = td_path.name.removesuffix(".td.json")
        schemas[name] = td_to_payload_schema(load_json(td_path))
    return schemas


def _decoded_vectors() -> dict[str, Any]:
    """Decode every payload in every ``*.vectors.json`` file."""
    decoded: dict[str, Any] = {}
    for vectors_path in vector_files():
        spec = load_json(vectors_path)
        td = load_json(EXAMPLES_DIR / spec["td"])
        stem = vectors_path.name.removesuffix(".vectors.json")
        for vector in spec["vectors"]:
            case_id = f"{stem}-{vector['name']}"
            decoded[case_id] = decode_uplink(td, vector["payload"], fport=vector.get("fport"))
    return decoded


def _catalog() -> dict[str, Any]:
    """Summarise the reference-device catalog and digest each round-tripped schema.

    Round-tripping the generated Thing Description back through the forward
    converter is what actually matters: it is the schema a user would deploy. A
    device whose round-trip *fails* records a marker instead of a digest, so a
    regression from working to failing shows up as a snapshot change rather than
    as a crash while building it.
    """
    # Imported lazily: ``scripts`` is a sibling package of ``tests`` and only
    # importable from the project root, which is where pytest and the updater run.
    from scripts.generate_device_tds import convert_catalog

    tds, skipped, scanned = convert_catalog()

    digests: dict[str, str] = {}
    for rel, td in sorted(tds.items()):
        try:
            digests[rel] = _digest(td_to_payload_schema(td))
        except ConversionError as exc:
            digests[rel] = f"round-trip failed: {exc}"

    return {
        "scanned": scanned,
        "generated": len(tds),
        "skipped": {reason: len(paths) for reason, paths in sorted(skipped.items())},
        "schema_digests": digests,
    }


def build_snapshot() -> dict[str, Any]:
    """Build the complete golden snapshot of the binding's observable output."""
    return {
        "payload_schemas": _curated_payload_schemas(),
        "decoded": _decoded_vectors(),
        "catalog": _catalog(),
    }
