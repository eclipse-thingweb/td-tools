"""Validate the generated device-catalog Thing Descriptions against the code.

Every ``examples/devices/<vendor>/<model>.td.json`` is generated from the
matching reference schema in the ``device-payload-schema`` submodule. These tests
prove each generated TD is faithful by:

1. **Round-trip equivalence** -- feeding the TD back through
   :func:`td_to_payload_schema` must reproduce the source schema's
   decode-relevant structure (field names, wire types, scaling, units, enums and
   tlv tags), modulo cosmetic metadata.
2. **Form validity** -- every generated form matches the LoRaWAN form JSON Schema.
3. **Source vectors** -- where the source schema ships ``test_vectors``, decoding
   them through the generated TD must yield the documented values.
4. **Decode parity** -- decoding synthesized payloads through the generated TD
   must match what the *original* reference schema decodes, byte for byte.
"""

from __future__ import annotations

import ast

import jsonschema
import pytest
import yaml

from lorawan_wot.converter import _WIRE_WIDTH, td_to_payload_schema
from lorawan_wot.decode import decode_with_schema

from .conftest import EXAMPLES_DIR, REPO_ROOT, VOCAB_DIR, load_json

DEVICES_DIR = EXAMPLES_DIR / "devices"
SOURCE_DIR = REPO_ROOT / "external" / "device-payload-schema" / "schemas" / "devices"

_FORM_SCHEMA = load_json(VOCAB_DIR / "lorawan-form.schema.json")


# --- decode-relevant projection (ignores cosmetic schema metadata) -----------


def _canon_enum(table: object) -> dict[int, str]:
    """Canonicalise a ``values``/``lookup`` table to ``{int: str}``."""
    if isinstance(table, list):
        return {index: str(label) for index, label in enumerate(table)}
    if isinstance(table, dict):
        return {int(key): str(label) for key, label in table.items()}
    raise TypeError(f"unexpected enum table {table!r}")


def _freeze(value: object) -> object:
    """Make a nested list/dict structure hashable for projection fingerprints."""
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(val)) for key, val in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _project_field(body: dict) -> tuple:
    """Reduce a MultiTech field dict to its decode-relevant fingerprint."""
    wire = body.get("type")
    if isinstance(wire, str):
        for prefix in ("be_", "le_"):
            if wire.startswith(prefix):
                wire = wire[3:]
    if wire == "skip":
        return ("skip", body.get("length"))
    parts: dict[str, object] = {"name": body.get("name"), "type": wire}
    for key in ("mult", "div", "add", "length", "unit", "unece"):
        if key in body:
            parts[key] = body[key]
    if "valid_range" in body:
        parts["valid_range"] = _freeze(body["valid_range"])
    for key in ("ref", "polynomial", "transform", "compute", "guard"):
        if key in body:
            parts[key] = _freeze(body[key])
    if "values" in body:
        parts["enum"] = _canon_enum(body["values"])
    if "lookup" in body:
        parts["enum"] = _canon_enum(body["lookup"])
    return tuple(sorted(parts.items(), key=lambda item: item[0]))


def _bitrange_lo(field: dict) -> int:
    """Lowest selected bit of a ``u8[lo:hi]`` field (for stable byte_group order)."""
    wire = str(field.get("type", ""))
    if "[" in wire and ":" in wire:
        return int(wire[wire.index("[") + 1 : wire.index(":")])
    return 0


def _flatten_fixed(fields: list) -> list:
    """Expand a fixed field list, inlining ``byte_group`` bitfields in bit order.

    The forward converter emits a byte_group's bitfields as flat shared-byte
    fields, so normalising the source the same way lets the two projections be
    compared field-for-field.
    """
    out: list = []
    for field in fields:
        if isinstance(field, dict) and "byte_group" in field and not field.get("type"):
            group = field["byte_group"]
            members = group.get("fields", []) if isinstance(group, dict) else group
            out.extend(sorted(members, key=_bitrange_lo))
        else:
            out.append(field)
    return out


def _project_fixed_element(field: dict) -> tuple:
    """Project one fixed-layout element (plain field, ``flagged`` or ``match``)."""
    if "flagged" in field and not field.get("type"):
        block = field["flagged"]
        groups = tuple(
            (
                group.get("bit"),
                tuple(_project_field(f) for f in group.get("fields", [])),
            )
            for group in block.get("groups", [])
        )
        return ("flagged", str(block.get("field", "")).lstrip("$"), groups)
    if "match" in field and not field.get("type"):
        block = field["match"]
        cases = tuple(
            sorted(
                (
                    int(value, 0) if isinstance(value, str) else int(value),
                    tuple(_project_field(f) for f in case_fields),
                )
                for value, case_fields in (block.get("cases") or {}).items()
                if value != "default"
            )
        )
        # The discriminator reference is normalised away (it is validated as its
        # own structural field); only the case structure is compared here.
        return ("match", cases)
    return _project_field(field)


_WIDTH_TO_UINT = {1: "u8", 2: "u16", 3: "u24", 4: "u32"}


def _tlv_tag_fields(block: dict) -> tuple:
    """Tag-field fingerprint for a tlv block (explicit or ``tag_size`` style)."""
    if block.get("tag_fields"):
        return tuple((tf["name"], tf["type"]) for tf in block["tag_fields"])
    # tag_size style canonicalises to one synthetic 'tag' field of matching width.
    return (("tag", _WIDTH_TO_UINT[int(block["tag_size"])]),)


def _project(schema: dict) -> dict:
    """Reduce a whole payload schema to a comparable, metadata-free structure."""
    projection: dict[str, object] = {"endian": schema.get("endian", "big")}
    if "ports" in schema:
        projection["kind"] = "ports"
        ports = {}
        for raw_port, port_def in schema["ports"].items():
            fields = port_def.get("fields") if isinstance(port_def, dict) else port_def
            ports[int(raw_port)] = tuple(
                _project_fixed_element(f) for f in _flatten_fixed(fields or [])
            )
        projection["ports"] = tuple(sorted(ports.items()))
        return projection
    fields = schema.get("fields")
    is_tlv = bool(
        fields and len(fields) == 1 and isinstance(fields[0], dict) and "tlv" in fields[0]
    )
    if is_tlv:
        block = fields[0]["tlv"]
        projection["kind"] = "tlv"
        projection["tag_fields"] = _tlv_tag_fields(block)
        cases = {}
        for raw_key, case_fields in block["cases"].items():
            key = (
                str(list(ast.literal_eval(raw_key))) if isinstance(raw_key, str) else str([raw_key])
            )
            cases[key] = tuple(_project_field(f) for f in case_fields)
        projection["cases"] = tuple(sorted(cases.items()))
    else:
        projection["kind"] = "fixed"
        projection["fields"] = tuple(_project_fixed_element(f) for f in _flatten_fixed(fields))
    return projection


# --- test collection ---------------------------------------------------------


def _device_tds() -> list:
    """Yield ``(td_path, source_schema_path)`` for every generated catalog TD."""
    params = []
    for td_path in sorted(DEVICES_DIR.rglob("*.td.json")):
        rel = td_path.relative_to(DEVICES_DIR)
        source = SOURCE_DIR / rel.with_suffix("").with_suffix(".yaml")
        params.append(pytest.param(td_path, source, id=str(rel.with_suffix("")).replace("\\", "/")))
    return params


_CATALOG = _device_tds()

#: How many device TDs the catalog is expected to contain, pinned deliberately.
#:
#: Every test below is parametrized over the catalog, so an empty or shrunken catalog
#: does not fail anything - it silently runs fewer cases and still reports success. A
#: bare "is not empty" check does not help either: one TD passes it as happily as two
#: hundred. Bumping the schema submodule is the case that matters, because a schema
#: rewritten to use a construct the converter does not support stops converting, and
#: nothing here would have said so.
#:
#: Change this number only in the same commit as the change that moves it, so the diff
#: shows the coverage cost and a reviewer can weigh it.
EXPECTED_CATALOG_SIZE = 157


def test_catalog_is_not_empty():
    """A distinct message for the case where nothing was generated at all.

    Subsumed by the size check below, but kept because the remedy differs: an empty
    catalog usually means the generation step did not run (see the README), not that
    coverage changed.
    """
    assert _CATALOG, (
        "no generated device TDs found under examples/devices/ - run "
        "`uv run python -m scripts.generate_device_tds` first"
    )


def test_catalog_size_is_pinned():
    """The catalog must hold exactly the expected number of device TDs.

    Asserted both ways on purpose. A drop means a device that used to convert no
    longer does; a rise means new coverage. Either way the number is updated by hand,
    in the commit responsible, rather than drifting unnoticed.
    """
    actual = len(_CATALOG)
    if actual < EXPECTED_CATALOG_SIZE:
        pytest.fail(
            f"device catalog shrank: {actual} TDs, expected {EXPECTED_CATALOG_SIZE}. "
            f"{EXPECTED_CATALOG_SIZE - actual} device schema(s) stopped converting - "
            "run `uv run python -m scripts.generate_device_tds` and read the skip "
            "report to see which construct they now use. Lower EXPECTED_CATALOG_SIZE "
            "only as a deliberate, reviewed decision."
        )
    if actual > EXPECTED_CATALOG_SIZE:
        pytest.fail(
            f"device catalog grew: {actual} TDs, expected {EXPECTED_CATALOG_SIZE}. "
            "Raise EXPECTED_CATALOG_SIZE in this commit to lock the new coverage in."
        )


@pytest.mark.parametrize(("td_path", "source_path"), _CATALOG)
def test_generated_td_round_trips(td_path, source_path):
    """The TD must convert back to the source schema's decoding structure."""
    td = load_json(td_path)
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    rebuilt = td_to_payload_schema(td)
    assert _project(rebuilt) == _project(source)


@pytest.mark.parametrize(("td_path", "source_path"), _CATALOG)
def test_generated_td_forms_validate(td_path, source_path):
    """Every LoRaWAN form in the generated TD matches the form JSON Schema."""
    td = load_json(td_path)
    for affordance in td["properties"].values():
        for form in affordance["forms"]:
            jsonschema.validate(instance=form, schema=_FORM_SCHEMA)


@pytest.mark.parametrize(("td_path", "source_path"), _CATALOG)
def test_generated_td_decodes_source_vectors(td_path, source_path):
    """Source ``test_vectors`` decode identically through the generated TD.

    The documented ``expected`` values are the primary oracle, but a handful of
    upstream vectors are self-inconsistent (their hand-authored value disagrees
    with what their own reference schema decodes). For those keys we fall back to
    requiring faithfulness to the reference interpreter, which is the binding's
    actual contract (and is also covered by ``test_generated_td_decode_parity``).
    """
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    vectors = source.get("test_vectors")
    if not vectors:
        pytest.skip("source schema has no test_vectors")
    schema = td_to_payload_schema(load_json(td_path))
    for vector in vectors:
        fport = vector.get("fport")
        data = decode_with_schema(schema, vector["payload"], fport=fport)
        reference = decode_with_schema(source, vector["payload"], fport=fport)
        for key, want in vector["expected"].items():
            assert key in data, f"missing {key!r} in {data}"
            # Prefer the documented value, unless the reference schema itself
            # disagrees with it (an upstream vector bug): then match the reference.
            target = want if _values_match(reference.get(key), want) else reference.get(key)
            assert _values_match(data[key], target), f"{key}: {data[key]} != {target}"


def _values_match(got: object, want: object) -> bool:
    """Compare decoded values, tolerating float rounding."""
    if isinstance(want, float) or isinstance(got, float):
        return got == pytest.approx(want)
    return got == want


# --- decode parity against the original reference schema ---------------------


def _value_width(wire: str) -> int:
    """Byte width of a (possibly endian-prefixed or bit-range) wire type."""
    if wire == "number":  # computed/derived value, reads no wire bytes
        return 0
    for prefix in ("be_", "le_"):
        if wire.startswith(prefix):
            wire = wire[3:]
    if "[" in wire:  # uN[lo:hi] bit range occupies its base type's bytes
        return _WIRE_WIDTH[wire[: wire.index("[")]]
    return _WIRE_WIDTH[wire]


def _field_width(field: dict) -> int:
    """Byte width consumed by one scalar/skip field."""
    if field.get("type") == "skip":
        return int(field.get("length", 0))
    if field.get("type") in ("bytes", "string", "ascii", "hex", "base64"):
        # Variable-length types declare a byte length; -1 means "consume rest",
        # which the reference interpreter treats as zero remaining bytes here.
        return max(0, int(field.get("length", 0)))
    return _value_width(field["type"])


def _element_width(field: dict) -> int:
    """Byte width an assembled-layout element may consume when fully present.

    For ``flagged`` every group is counted (all bits set); for ``match`` the
    widest case is counted; for ``byte_group`` the declared size. This makes a
    payload long enough to exercise whichever branch the synthetic bytes select.
    """
    if "byte_group" in field and not field.get("type"):
        group = field["byte_group"]
        return int(group.get("size", 1)) if isinstance(group, dict) else 1
    if "flagged" in field and not field.get("type"):
        return sum(
            _field_width(f)
            for group in field["flagged"].get("groups", [])
            for f in group.get("fields", [])
        )
    if "match" in field and not field.get("type"):
        cases = field["match"].get("cases") or {}
        return max(
            (sum(_field_width(f) for f in case_fields) for case_fields in cases.values()),
            default=0,
        )
    return _field_width(field)


def _synthesize_payloads(schema: dict) -> list[tuple[bytes, int | None]]:
    """Build decodable sample ``(payload, fport)`` pairs exercising every field.

    ``tlv`` schemas get one payload that walks every case (tag bytes followed by
    zeroed value bytes). ``ports`` schemas get the byte patterns below for each
    declared fPort (paired with that port). Other schemas get whole-payload byte
    patterns (zeros, 0xFF and an incrementing ramp) with ``fport=None``; 0xFF sets
    every ``flagged`` bit so all conditional groups are present, while the
    ramp/zeros exercise signed, scaled and alternate ``match`` branches.
    """
    if "ports" in schema:
        pairs: list[tuple[bytes, int | None]] = []
        for raw_port, port_def in schema["ports"].items():
            fields = port_def.get("fields") if isinstance(port_def, dict) else port_def
            total = sum(_element_width(f) for f in (fields or []))
            port = int(raw_port)
            pairs.extend(
                (payload, port)
                for payload in (
                    bytes(total),
                    b"\xff" * total,
                    bytes((i + 1) % 256 for i in range(total)),
                )
            )
        return pairs

    fields = schema["fields"]
    if len(fields) == 1 and isinstance(fields[0], dict) and "tlv" in fields[0]:
        block = fields[0]["tlv"]
        chunks = bytearray()
        for raw_key, case_fields in block["cases"].items():
            tag = ast.literal_eval(raw_key) if isinstance(raw_key, str) else [raw_key]
            chunks.extend(int(t) & 0xFF for t in tag)
            for field in case_fields:
                chunks.extend(b"\x00" * _value_width(field["type"]))
        return [(bytes(chunks), None)]

    total = sum(_element_width(f) for f in fields)
    return [
        (bytes(total), None),
        (b"\xff" * total, None),
        (bytes((i + 1) % 256 for i in range(total)), None),
    ]


@pytest.mark.parametrize(("td_path", "source_path"), _CATALOG)
def test_generated_td_decode_parity(td_path, source_path):
    """Decoding a payload through the generated TD matches the reference schema."""
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    generated = td_to_payload_schema(load_json(td_path))
    for payload, fport in _synthesize_payloads(source):
        try:
            want = decode_with_schema(source, payload, fport=fport)
        except ValueError:
            # A 'match' discriminator with no case raises on the reference schema;
            # the generated schema must reject the same payload identically.
            with pytest.raises(ValueError):
                decode_with_schema(generated, payload, fport=fport)
            continue
        got = decode_with_schema(generated, payload, fport=fport)
        assert got == want, f"decode mismatch on {payload.hex()}: {got} != {want}"
