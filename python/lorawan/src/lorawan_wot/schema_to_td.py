"""Generate a WoT Thing Description from a MultiTech payload schema.

This is the inverse of :func:`lorawan_wot.converter.td_to_payload_schema`, used to
bootstrap Thing Descriptions from the reference device schemas shipped in the
``device-payload-schema`` submodule. It deliberately covers only the schema
shapes the forward converter can faithfully round-trip:

* ``plain``/fixed -- a flat ordered list of named fields (sequential offsets,
  ``skip`` padding allowed).
* single-field ``tlv`` -- a ``tag_fields`` block whose every case maps to exactly
  one field (one WoT property per tag).

Anything outside that subset (``flagged`` groups, ``byte_group``, ``match``,
multi-field ``tlv`` cases, computed ``ref``/``formula`` fields, ``tag_size`` style
``tlv``, duplicate field names, ...) raises :class:`UnsupportedSchemaError` so a batch
caller can skip it and report it, rather than emitting a lossy Thing Description.
"""

from __future__ import annotations

import ast
import copy
import enum
import re
from typing import Any

from lorawan_wot import vocab
from lorawan_wot.converter import _WIRE_WIDTH

#: Field keys whose meaning the binding can express on a ``lorav:`` form.
_KNOWN_FIELD_KEYS: frozenset[str] = frozenset(
    {
        "name",
        "type",
        "mult",
        "div",
        "add",
        "unit",
        "unece",
        "length",
        "values",
        "lookup",
        "value",
        "valid_range",
        "transform",  # post-processing of a value read from the wire
    }
)

#: Purely descriptive field keys that do not affect decoding and are ignored.
_IGNORABLE_FIELD_KEYS: frozenset[str] = frozenset(
    {
        "description",
        "title",
        "ipso",
        "senml",
        "semantic",
        "resolution",
        "raw",
        "comment",
        "var",  # names a field for later $reference; decoding-neutral here
        "sensor",  # names the sensor a channel belongs to; an annotation like `semantic`
    }
)

#: Field keys / types that mark a *computed* (derived) value the binding cannot
#: express, since it is post-processing math rather than a raw wire field.
_COMPUTED_FIELD_KEYS: frozenset[str] = frozenset(
    {"ref", "polynomial", "transform", "formula", "compute", "guard"}
)
#: `number` is the derived-value marker and is routed, not rejected. `bitfield_string`
#: renders packed bits as text and has no form term yet, so it stays out of the subset.
_UNSUPPORTED_FIELD_TYPES: frozenset[str] = frozenset({"bitfield_string"})

#: Derived-value descriptors the binding *does* support (carried verbatim onto a
#: ``lorav:`` form). ``formula`` remains unsupported and keeps its fields out of the
#: convertible subset.
#:
#: ``value`` used to sit here, which cost 45 device schemas - every downlink command
#: in the library declares its category and command bytes that way. It is not a
#: derived value at all: the reference interpreter ignores it when decoding, reading
#: the byte and reporting what the payload actually held. It fixes the byte only when
#: *encoding*, so it rides on the form as ``lorav:const`` and the field is otherwise
#: an ordinary scalar.
_COMPUTED_DESCRIPTORS: frozenset[str] = frozenset(
    {"ref", "polynomial", "transform", "compute", "guard"}
)

#: Keys a computed/derived field may carry and still be representable.
_COMPUTED_KNOWN_KEYS: frozenset[str] = (
    frozenset({"name", "type", "mult", "div", "add", "unit", "unece", "length", "valid_range"})
    | _COMPUTED_DESCRIPTORS
)


class SkipReason(enum.Enum):
    """Why a device schema falls outside the convertible subset.

    Each member's *value* is the short, human-readable label used in the
    catalog coverage report (``scripts/generate_device_tds.py``). Categorising a
    skip by a stable enum member -- rather than by matching on the exception's
    free-text message -- keeps the report robust when error wording changes.
    """

    COMPUTED = "computed/derived field (ref/polynomial/transform)"
    DUPLICATE_NAME = "duplicate field name (reused across cases/groups)"
    MULTI_BYTE_BYTE_GROUP = "multi-byte byte_group"
    SKIP_IN_MATCH = "skip inside match case"
    TLV_NO_TAG_FIELDS = "tag_size TLV (no tag_fields)"
    MIXED_FIELD_SHAPE = "mixed/unsupported field shape"
    BIT_RANGE = "bit-range field type"
    WIRE_TYPE = "unsupported wire type"
    UNSUPPORTED_KEYS = "unsupported field keys (repeat/object/array)"
    MATCH_DEFAULT = "match default case"
    MATCH_CASE_KEY = "non-integer match case key"
    TLV_TAG = "unsupported tlv tag key"
    ENUM_TABLE = "unsupported enum table"
    INTERNAL_REF = "derived field reads a value the TD does not carry"
    LENGTH_NOT_FIXED = "length is not a fixed byte count (remaining/$var)"
    MALFORMED = "malformed / non-conforming schema"
    OTHER = "other"


class UnsupportedSchemaError(ValueError):
    """Raised when a device schema is outside the convertible subset.

    Carries a structured :class:`SkipReason` (``reason``) so a batch caller can
    bucket skips reliably without parsing the human-readable message.
    """

    def __init__(self, message: str, *, reason: SkipReason = SkipReason.OTHER) -> None:
        super().__init__(message)
        self.reason = reason


def payload_schema_to_td(schema: dict[str, Any], *, source: str) -> dict[str, Any]:
    """Convert a MultiTech payload-schema ``dict`` to a Thing Description ``dict``.

    ``source`` is a human-readable origin (e.g. the schema file name) used to
    derive a fallback Thing id when the schema has no ``name``.
    """
    if not isinstance(schema, dict):
        raise UnsupportedSchemaError("schema is not a mapping", reason=SkipReason.MALFORMED)
    if "ports" in schema:
        return _ports_td(schema, source)

    fields = schema.get("fields")
    if not isinstance(fields, list) or not fields:
        raise UnsupportedSchemaError(
            "schema has no top-level 'fields' list", reason=SkipReason.MALFORMED
        )

    if len(fields) == 1 and isinstance(fields[0], dict) and "tlv" in fields[0]:
        td = _tlv_td(schema, source)
    else:
        td = _fixed_td(schema, source)
    _reject_unresolvable_inputs(td.get("properties") or {})
    return td


# --- layout builders ---------------------------------------------------------


def _fixed_td(schema: dict[str, Any], source: str) -> dict[str, Any]:
    """Build a ``fixed``-layout Thing Description from a flat field list.

    Besides plain scalar fields the list may contain grouped/conditional
    sub-structures: ``byte_group`` (bitfields packed into shared bytes),
    ``flagged`` (groups gated by a flags bit) and ``match`` (cases selected by a
    discriminator). Each contributes one WoT property per decoded value, located
    by the relevant ``lorav:`` grouping term rather than a byte offset.
    """
    endian_big = _endian_is_big(schema)
    properties: dict[str, Any] = {}
    _emit_fixed_fields(schema["fields"], properties, endian_big)
    if not properties:
        raise UnsupportedSchemaError(
            "fixed layout has no decodable fields", reason=SkipReason.MALFORMED
        )
    return _assemble_td(schema, source, vocab.LAYOUT_FIXED, properties)


def _ports_td(schema: dict[str, Any], source: str) -> dict[str, Any]:
    """Build a ``ports``-layout Thing Description from a per-fPort field map.

    Each entry of ``ports`` is a fixed layout decoded when the uplink arrives on
    that frame port; every property in a port carries ``lorav:fPort``. A value
    reported on more than one port (e.g. ``latitude`` in two formats) becomes a
    single WoT property with one form per port.
    """
    endian_big = _endian_is_big(schema)
    properties: dict[str, Any] = {}
    for raw_port, port_def in schema["ports"].items():
        port = _port_number(raw_port)
        fields = port_def.get("fields") if isinstance(port_def, dict) else port_def
        if not isinstance(fields, list) or not fields:
            raise UnsupportedSchemaError(
                f"port {raw_port!r} has no 'fields' list", reason=SkipReason.MALFORMED
            )
        _emit_fixed_fields(fields, properties, endian_big, fport=port)
    if not properties:
        raise UnsupportedSchemaError(
            "ports layout has no decodable fields", reason=SkipReason.MALFORMED
        )
    return _assemble_td(schema, source, vocab.LAYOUT_PORTS, properties)


def _port_number(raw: Any) -> int:
    """Coerce an fPort key (``1`` or ``"1"``) to an integer in the valid range."""
    try:
        port = int(raw)
    except (TypeError, ValueError) as exc:
        raise UnsupportedSchemaError(
            f"unsupported fPort key {raw!r}", reason=SkipReason.MALFORMED
        ) from exc
    if not 1 <= port <= 255:
        raise UnsupportedSchemaError(
            f"fPort {port} is outside the valid range 1-255", reason=SkipReason.MALFORMED
        )
    return port


def _emit_fixed_fields(
    fields: list[Any], properties: dict[str, Any], endian_big: bool, *, fport: int | None = None
) -> None:
    """Walk a flat field list, storing one property per decoded value.

    ``fport`` (when set) tags every form for a ``ports`` layout. The cursor and
    computed-slot counters are local to this list, so each port starts at byte 0.
    """
    offset = 0
    computed_slot = 0
    for field in fields:
        if not isinstance(field, dict):
            raise UnsupportedSchemaError(
                "fixed layout expects mapping field entries", reason=SkipReason.MALFORMED
            )
        if "byte_group" in field:
            offset = _emit_byte_group(
                field["byte_group"], properties, endian_big, offset, fport=fport
            )
            continue
        if "flagged" in field and not field.get("type"):
            _emit_flagged(field["flagged"], properties, endian_big, fport=fport)
            continue
        if "match" in field and not field.get("type"):
            _emit_match(field["match"], properties, endian_big, fport=fport)
            continue
        if "name" not in field:
            raise UnsupportedSchemaError(
                "fixed layout expects only named scalar fields",
                reason=SkipReason.MIXED_FIELD_SHAPE,
            )
        if field.get("type") == "skip":
            offset += int(field.get("length", 0))
            continue
        if _is_computed_field(field):
            # A derived value occupies no payload bytes; it sits at the current
            # cursor (so it sorts before the next raw field there) and a slot
            # keeps consecutive derived values in source order.
            prop = _computed_property(field, byte_offset=offset, slot=computed_slot, fport=fport)
            _store_property(properties, field.get("name"), prop)
            computed_slot += 1
            continue
        base, prop = _scalar_property(field, endian_big, byte_offset=offset, fport=fport)
        _store_property(properties, field["name"], prop)
        offset += _byte_width(base, field)


def _emit_flagged(
    flagged_def: dict[str, Any],
    properties: dict[str, Any],
    endian_big: bool,
    *,
    fport: int | None = None,
) -> None:
    """Emit one WoT property per field of every ``flagged`` group.

    Each property records the flags field name (``lorav:presenceField``) and the
    bit that gates it (``lorav:presenceBit``); members of a multi-field group are
    ordered by ``lorav:slot``.
    """
    flag_field = str(flagged_def.get("field", "")).lstrip("$")
    if not flag_field:
        raise UnsupportedSchemaError("flagged block has no 'field'", reason=SkipReason.MALFORMED)
    for group in flagged_def.get("groups", []):
        bit = group.get("bit")
        if not isinstance(bit, int):
            raise UnsupportedSchemaError(
                f"flagged group has non-integer bit {bit!r}", reason=SkipReason.MALFORMED
            )
        group_fields = group.get("fields", [])
        multi = len(group_fields) > 1
        for index, field in enumerate(group_fields):
            slot = index if multi else None
            if _is_computed_field(field):
                prop = _computed_property(
                    field, presence_field=flag_field, presence_bit=bit, slot=slot, fport=fport
                )
            else:
                _, prop = _scalar_property(
                    field,
                    endian_big,
                    presence_field=flag_field,
                    presence_bit=bit,
                    slot=slot,
                    fport=fport,
                )
            _store_property(properties, field.get("name"), prop)


def _emit_match(
    match_def: dict[str, Any],
    properties: dict[str, Any],
    endian_big: bool,
    *,
    fport: int | None = None,
) -> None:
    """Emit one WoT property per field of every ``match`` case.

    Each property records the discriminator field name (``lorav:switchField``)
    and the value selecting its case (``lorav:switchValue``); members of a
    multi-field case are ordered by ``lorav:slot``.
    """
    switch_field = str(match_def.get("field", "")).lstrip("$")
    if not switch_field:
        raise UnsupportedSchemaError(
            "match block references no discriminator field", reason=SkipReason.MALFORMED
        )
    cases = match_def.get("cases")
    if not isinstance(cases, dict) or not cases:
        raise UnsupportedSchemaError(
            "match block has no cases mapping", reason=SkipReason.MALFORMED
        )
    for raw_value, case_fields in cases.items():
        if raw_value == "default":
            raise UnsupportedSchemaError(
                "match 'default' cases are not supported", reason=SkipReason.MATCH_DEFAULT
            )
        value = _match_case_value(raw_value)
        if not isinstance(case_fields, list) or not case_fields:
            raise UnsupportedSchemaError(
                f"match case {raw_value!r} has no fields", reason=SkipReason.MALFORMED
            )
        multi = len(case_fields) > 1
        pending_pad = 0  # reserved bytes to consume before the next real field
        for index, field in enumerate(case_fields):
            if field.get("type") == "skip":
                # Padding inside a case has no decoded value; fold it into the
                # next field's ``lorav:padBefore`` so the sequential layout (and
                # thus every following field's position) round-trips faithfully.
                pending_pad += int(field.get("length", 0))
                continue
            slot = index if multi else None
            pad_before = pending_pad or None
            pending_pad = 0
            if _is_computed_field(field):
                prop = _computed_property(
                    field,
                    switch_field=switch_field,
                    switch_value=value,
                    slot=slot,
                    fport=fport,
                    pad_before=pad_before,
                )
            else:
                _, prop = _scalar_property(
                    field,
                    endian_big,
                    switch_field=switch_field,
                    switch_value=value,
                    slot=slot,
                    fport=fport,
                    pad_before=pad_before,
                )
            _store_property(properties, field.get("name"), prop)
        if pending_pad:
            # A case ending in reserved bytes has no field to attach them to;
            # this shape is not represented (no device in the corpus needs it).
            raise UnsupportedSchemaError(
                f"match case {raw_value!r} ends with trailing skip padding",
                reason=SkipReason.SKIP_IN_MATCH,
            )


def _emit_byte_group(
    byte_group: Any,
    properties: dict[str, Any],
    endian_big: bool,
    offset: int,
    *,
    fport: int | None = None,
) -> int:
    """Emit a WoT property per bitfield of a ``byte_group`` and advance the cursor.

    A ``byte_group`` packs several bit-range fields (``uN[lo:hi]``) into ``size``
    shared bytes. Each becomes a masked property sharing the group's byte offset
    (the existing ``lorav:bitmask`` + shared-offset mechanism). A multi-byte group
    (``size`` > 1) uses a wider base type whose width matches ``size`` (e.g. a
    3-byte group with ``u24[lo:hi]`` ranges). Returns the new cursor position.
    """
    if isinstance(byte_group, dict):
        group_fields = byte_group.get("fields", [])
        size = int(byte_group.get("size", 1))
    else:
        group_fields = byte_group
        size = 1
    if not group_fields:
        return offset + size
    for field in group_fields:
        _reject_computed(field)
        _check_field_keys(field)
        base, bitmask = _parse_bitrange(field["type"])
        form = _build_form(field, base, None, byte_offset=offset, bitmask=bitmask, fport=fport)
        _store_property(properties, field.get("name"), _build_property(field, base, form))
    return offset + size


#: Map a tag/field byte width to the unsigned wire type of that width.
_WIDTH_TO_UINT: dict[int, str] = {1: "u8", 2: "u16", 3: "u24", 4: "u32"}


def _resolve_tag_fields(block: dict[str, Any]) -> list[dict[str, str]]:
    """Return the ``tag_fields`` for a tlv block, real or synthesized.

    Two tlv styles are accepted: an explicit ``tag_fields`` list (channel/type),
    and the ``tag_size`` style (a single tag of ``tag_size`` bytes with no length
    prefix), which is canonicalised to one synthetic ``tag`` field of matching
    width. A ``length_size`` greater than zero (length-prefixed values) is not
    yet supported.
    """
    tag_fields = block.get("tag_fields")
    if tag_fields:
        for tag_field in tag_fields:
            if set(tag_field) - {"name", "type"}:
                raise UnsupportedSchemaError(
                    "complex tag_fields are not supported", reason=SkipReason.TLV_NO_TAG_FIELDS
                )
        return tag_fields
    if "tag_size" in block:
        if int(block.get("length_size", 0)) != 0:
            raise UnsupportedSchemaError(
                "length-prefixed tlv is not yet supported", reason=SkipReason.TLV_NO_TAG_FIELDS
            )
        tag_type = _WIDTH_TO_UINT.get(int(block["tag_size"]))
        if tag_type is None:
            raise UnsupportedSchemaError(
                f"unsupported tag_size {block['tag_size']!r}", reason=SkipReason.TLV_NO_TAG_FIELDS
            )
        return [{"name": "tag", "type": tag_type}]
    raise UnsupportedSchemaError(
        "only 'tag_fields' style tlv is supported", reason=SkipReason.TLV_NO_TAG_FIELDS
    )


def _tlv_td(schema: dict[str, Any], source: str) -> dict[str, Any]:
    """Build a ``tlv``-layout Thing Description from a single-field tlv block."""
    block = schema["fields"][0]["tlv"]
    tag_fields = _resolve_tag_fields(block)

    endian_big = _endian_is_big(schema)
    properties: dict[str, Any] = {}
    for key, case_fields in (block.get("cases") or {}).items():
        if not isinstance(case_fields, list) or not case_fields:
            raise UnsupportedSchemaError(f"empty tlv case {key!r}", reason=SkipReason.MALFORMED)
        tag = _parse_tag(key)
        # A case may carry several fields (a multi-field TLV channel): each
        # becomes its own WoT property sharing the tag, ordered by lorav:slot.
        multi = len(case_fields) > 1
        for index, field in enumerate(case_fields):
            slot = index if multi else None
            if _is_computed_field(field):
                # A derived value inside a case maps to a computed property,
                # mirroring the forward converter which emits computed fields
                # in tlv cases as well.
                prop = _computed_property(field, tag=tag, slot=slot)
            else:
                _, prop = _scalar_property(field, endian_big, tag=tag, slot=slot)
            _store_property(properties, field.get("name"), prop)

    if not properties:
        raise UnsupportedSchemaError("tlv block has no cases", reason=SkipReason.MALFORMED)
    td = _assemble_td(schema, source, vocab.LAYOUT_TLV, properties)
    td[vocab.TAG_FIELDS] = [dict(tag_field) for tag_field in tag_fields]
    return td


# --- field/property helpers --------------------------------------------------


def _scalar_property(
    field: dict[str, Any], endian_big: bool, **locator: Any
) -> tuple[str, dict[str, Any]]:
    """Build a WoT property for one named scalar field, validating its keys.

    ``locator`` carries the positioning terms for this field's form
    (``byte_offset`` / ``tag`` / ``slot`` / ``presence_field`` / ``presence_bit``
    / ``switch_field`` / ``switch_value``). Returns ``(base_wire_type, property)``.
    """
    _reject_computed(field)
    _check_field_keys(field)
    base, msb = _parse_type(field["type"])
    form = _build_form(field, base, _coalesce_msb(msb, endian_big), **locator)
    return base, _build_property(field, base, form)


def _store_property(properties: dict[str, Any], name: Any, prop: dict[str, Any]) -> None:
    """Register a property, merging a recurring name into extra forms.

    WoT property keys must be unique. When a field name recurs under a *distinct*
    locator -- e.g. the same measurement reported under two different tlv tags
    (``temperature`` in ``[3, 103]`` and ``[131, 103]``) -- the new descriptor is
    appended as an additional form on the existing property rather than rejected.
    A recurrence with an *identical* locator is a genuine collision and still
    raises, since the interpreter would silently overwrite one value with another.
    """
    if not isinstance(name, str) or not name:
        raise UnsupportedSchemaError(
            f"field has no usable name: {name!r}", reason=SkipReason.MALFORMED
        )
    if name in properties:
        existing = properties[name]
        new_form = prop["forms"][0]
        if any(_form_locator(form) == _form_locator(new_form) for form in existing["forms"]):
            raise UnsupportedSchemaError(
                f"duplicate field name {name!r}", reason=SkipReason.DUPLICATE_NAME
            )
        existing["forms"].append(new_form)
        return
    properties[name] = prop


def _form_locator(form: dict[str, Any]) -> tuple[Any, ...]:
    """Return a hashable key for where/how a form's value sits in the payload.

    ``lorav:slot`` is deliberately excluded: it only orders members within a
    group, so two same-named fields in one case (which the interpreter would
    overwrite) share a locator and are correctly flagged as a real collision.
    """
    tag = form.get(vocab.TAG)
    return (
        tuple(tag) if tag is not None else None,
        form.get(vocab.FPORT),
        form.get(vocab.BYTE_OFFSET),
        form.get(vocab.PRESENCE_FIELD),
        form.get(vocab.PRESENCE_BIT),
        form.get(vocab.SWITCH_FIELD),
        form.get(vocab.SWITCH_VALUE),
        form.get(vocab.BITMASK),
    )


def _check_field_keys(field: dict[str, Any]) -> None:
    """Reject fields carrying decode-affecting keys the binding cannot express."""
    unknown = set(field) - _KNOWN_FIELD_KEYS - _IGNORABLE_FIELD_KEYS
    if unknown:
        raise UnsupportedSchemaError(
            f"field {field.get('name')!r} uses unsupported keys: {sorted(unknown)}",
            reason=SkipReason.UNSUPPORTED_KEYS,
        )


def _reject_computed(field: dict[str, Any]) -> None:
    """Reject computed/derived fields (post-processing math, not raw wire data)."""
    if not isinstance(field, dict):
        raise UnsupportedSchemaError(
            f"field is not a mapping: {field!r}", reason=SkipReason.MALFORMED
        )
    if field.get("type") in _UNSUPPORTED_FIELD_TYPES:
        raise UnsupportedSchemaError(
            f"unsupported field type {field.get('type')!r}", reason=SkipReason.COMPUTED
        )
    if _is_computed_field(field):
        # A derived field reaching the scalar path is a routing mistake, not a schema
        # the binding cannot express: every caller checks _is_computed_field first.
        raise UnsupportedSchemaError(
            f"derived field {field.get('name')!r} reached the scalar path",
            reason=SkipReason.COMPUTED,
        )
    if "formula" in field:
        # A free-text expression the binding has no term for.
        raise UnsupportedSchemaError("field uses 'formula'", reason=SkipReason.COMPUTED)


def _is_computed_field(field: dict[str, Any]) -> bool:
    """True when a source field is a derived value rather than a raw wire field.

    A derived value is one with nothing to read: either `type: number` or no type at
    all, plus a descriptor saying where its value comes from.

    Carrying a descriptor does not make a field derived. `transform` post-processes a
    value that *was* read from the wire, and this used to treat any field carrying one
    as derived - so `air_temperature` (a `u16` with `transform: [{div: 100},
    {add: -327.68}]`) had its wire type replaced by the derived marker and became a
    zero-byte field. The generated TD then decoded without it entirely: not a skipped
    schema but a silently wrong one, which the catalog count cannot detect.
    """
    if not isinstance(field, dict):
        return False
    ftype = field.get("type")
    if ftype is None:
        return bool(_COMPUTED_DESCRIPTORS & field.keys())
    return ftype == vocab.COMPUTED_TYPE


def _referenced_names(descriptor: Any) -> set[str]:
    """Every ``$name`` a derived-value descriptor reads, at any nesting depth."""
    found: set[str] = set()
    if isinstance(descriptor, str):
        if descriptor.startswith("$"):
            found.add(descriptor[1:])
    elif isinstance(descriptor, dict):
        for value in descriptor.values():
            found |= _referenced_names(value)
    elif isinstance(descriptor, list):
        for item in descriptor:
            found |= _referenced_names(item)
    return found


def _reject_unresolvable_inputs(properties: dict[str, Any]) -> None:
    """Reject a Thing Description whose derived fields read a value it does not carry.

    A derived field names its inputs with ``$name``. The reverse conversion rebuilds a
    schema from the properties alone, so an input that is not a property comes back as
    nothing and the reference interpreter evaluates the field against zero - qingping
    decoded a temperature of -50 where its schema says 359.5, because ``$_temp_raw``
    was internal scratch state with no property of its own.

    Checked against the assembled properties rather than by rejecting every internal
    reference: most internal inputs *are* emitted as properties and resolve correctly.
    Rejecting the name alone cost 22 schemas to prevent one wrong Thing Description.

    Skipped rather than approximated: a TD that decodes to the wrong number is worse
    than one that does not exist, and the catalog size cannot detect it.
    """
    available = set(properties)
    # An internal input that is a bit range cannot survive the round trip. The forms are
    # emitted correctly, but rebuilding flattens the byte_group into top-level bit-range
    # fields, and the reference interpreter decodes a top-level `_`-prefixed field
    # without storing it as a variable - so `$_temp_raw` resolves to nothing and
    # qingping reported -50 degrees where its schema says 359.5. Plain internal scalars
    # are unaffected and stay convertible.
    masked_internal = {
        name
        for name, prop in properties.items()
        if name.startswith("_") and any(vocab.BITMASK in form for form in prop.get("forms", []))
    }
    missing: dict[str, list[str]] = {}
    for name, prop in properties.items():
        for form in prop.get("forms", []):
            for key in vocab.COMPUTED_TERMS:
                if key not in form:
                    continue
                referenced = _referenced_names(form[key])
                unresolved = sorted((referenced - available) | (referenced & masked_internal))
                if unresolved:
                    missing.setdefault(name, []).extend(unresolved)
    if missing:
        detail = "; ".join(f"{n} reads {sorted(set(refs))}" for n, refs in missing.items())
        raise UnsupportedSchemaError(
            f"derived field input is not a property: {detail}",
            reason=SkipReason.INTERNAL_REF,
        )


def _computed_property(field: dict[str, Any], **locator: Any) -> dict[str, Any]:
    """Build a WoT property for a computed/derived field (zero payload bytes).

    The derived-value descriptors (``ref``/``polynomial``/``transform``/
    ``compute``/``guard``) are carried verbatim onto the form so the forward
    converter can reproduce the exact field the reference interpreter evaluates.
    """
    unknown = set(field) - _COMPUTED_KNOWN_KEYS - _IGNORABLE_FIELD_KEYS
    if unknown:
        raise UnsupportedSchemaError(
            f"computed field {field.get('name')!r} uses unsupported keys: {sorted(unknown)}",
            reason=SkipReason.COMPUTED,
        )
    form = _build_computed_form(field, **locator)
    prop: dict[str, Any] = {
        "type": "number",
        "readOnly": True,
        "observable": True,
        "forms": [form],
    }
    if "unit" in field:
        prop["unit"] = field["unit"]
    _apply_valid_range(prop, field)
    if isinstance(field.get("description"), str):
        prop["description"] = field["description"]
    return prop


def _build_computed_form(
    field: dict[str, Any],
    *,
    byte_offset: int | None = None,
    tag: list[int] | None = None,
    slot: int | None = None,
    presence_field: str | None = None,
    presence_bit: int | None = None,
    switch_field: str | None = None,
    switch_value: int | None = None,
    fport: int | None = None,
    pad_before: int | None = None,
) -> dict[str, Any]:
    """Assemble a LoRaWAN binding form for a computed/derived field."""
    form: dict[str, Any] = {"href": "uplink", "op": ["readproperty", "observeproperty"]}
    if fport is not None:
        form[vocab.FPORT] = fport
    if byte_offset is not None:
        form[vocab.BYTE_OFFSET] = byte_offset
    if tag is not None:
        form[vocab.TAG] = tag
    if slot is not None:
        form[vocab.SLOT] = slot
    if pad_before is not None:
        form[vocab.PAD_BEFORE] = pad_before
    if presence_field is not None:
        form[vocab.PRESENCE_FIELD] = presence_field
    if presence_bit is not None:
        form[vocab.PRESENCE_BIT] = presence_bit
    if switch_field is not None:
        form[vocab.SWITCH_FIELD] = switch_field
    if switch_value is not None:
        form[vocab.SWITCH_VALUE] = switch_value
    form[vocab.TYPE] = vocab.COMPUTED_TYPE
    if "ref" in field:
        form[vocab.REF] = field["ref"]
    if "polynomial" in field:
        form[vocab.POLYNOMIAL] = field["polynomial"]
    if "compute" in field:
        form[vocab.COMPUTE] = field["compute"]
    if "guard" in field:
        form[vocab.GUARD] = field["guard"]
    if "transform" in field:
        form[vocab.TRANSFORM] = field["transform"]
    _store_scaling(form, field)
    if "unece" in field:
        form[vocab.UNECE] = field["unece"]
    if "valid_range" in field:
        form[vocab.VALID_RANGE] = field["valid_range"]
    return form


def _match_case_value(raw: Any) -> int:
    """Coerce a ``match`` case key (e.g. ``0x0D`` or ``"5"``) to an integer."""
    if isinstance(raw, bool):
        raise UnsupportedSchemaError(
            f"unsupported match case key {raw!r}", reason=SkipReason.MATCH_CASE_KEY
        )
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw, 0)
        except ValueError as exc:
            raise UnsupportedSchemaError(
                f"unsupported match case key {raw!r} (only integer cases are supported)",
                reason=SkipReason.MATCH_CASE_KEY,
            ) from exc
    raise UnsupportedSchemaError(
        f"unsupported match case key {raw!r}", reason=SkipReason.MATCH_CASE_KEY
    )


def _parse_bitrange(raw: Any) -> tuple[str, str]:
    """Parse a ``uN[lo:hi]`` bit-range type into ``(base_type, hex_bitmask)``.

    Supports single- and multi-byte unsigned bases (``u8``/``u16``/``u24``/``u32``)
    so a ``byte_group`` may pack bit ranges spanning more than one byte (e.g.
    ``u24[4:23]`` for a 20-bit value). The bitmask is rendered with two hex digits
    per base byte so the selected bits map onto the whole group.
    """
    if not isinstance(raw, str):
        raise UnsupportedSchemaError(
            f"non-string bit-range type {raw!r}", reason=SkipReason.BIT_RANGE
        )
    match = re.fullmatch(r"(u8|u16|u24|u32)\[(\d+):(\d+)\]", raw)
    if not match:
        raise UnsupportedSchemaError(
            f"unsupported bit-range type {raw!r}", reason=SkipReason.BIT_RANGE
        )
    base, lo_s, hi_s = match.groups()
    lo, hi = int(lo_s), int(hi_s)
    width_bytes = _WIRE_WIDTH[base]
    if lo > hi or hi > width_bytes * 8 - 1:
        raise UnsupportedSchemaError(f"invalid bit range in {raw!r}", reason=SkipReason.BIT_RANGE)
    mask = ((1 << (hi + 1)) - 1) ^ ((1 << lo) - 1)
    return base, f"0x{mask:0{width_bytes * 2}X}"


def _parse_type(raw: Any) -> tuple[str, bool | None]:
    """Split a wire type into its base type and explicit endianness (if any)."""
    if not isinstance(raw, str):
        raise UnsupportedSchemaError(f"non-string field type {raw!r}", reason=SkipReason.WIRE_TYPE)
    msb: bool | None = None
    base = raw
    if base.startswith("be_"):
        msb, base = True, base[3:]
    elif base.startswith("le_"):
        msb, base = False, base[3:]
    if "[" in base:
        raise UnsupportedSchemaError(
            f"bit-range type {raw!r} is not supported", reason=SkipReason.BIT_RANGE
        )
    if base not in vocab.NATIVE_WIRE_TYPES:
        raise UnsupportedSchemaError(f"unsupported wire type {raw!r}", reason=SkipReason.WIRE_TYPE)
    return base, msb


def _byte_width(base: str, field: dict[str, Any]) -> int:
    """Number of payload bytes a fixed-layout field occupies."""
    if base in _WIRE_WIDTH:
        return _WIRE_WIDTH[base]
    length = field.get("length")
    if length is None:
        raise UnsupportedSchemaError(
            f"variable-length type {base!r} on field {field.get('name')!r} needs a length",
            reason=SkipReason.MALFORMED,
        )
    return int(length)


def _build_form(
    field: dict[str, Any],
    base: str,
    msb: bool | None,
    *,
    byte_offset: int | None = None,
    tag: list[int] | None = None,
    slot: int | None = None,
    presence_field: str | None = None,
    presence_bit: int | None = None,
    switch_field: str | None = None,
    switch_value: int | None = None,
    bitmask: str | None = None,
    fport: int | None = None,
    pad_before: int | None = None,
) -> dict[str, Any]:
    """Assemble one LoRaWAN binding form for a field.

    The keyword arguments are the field's *locator* terms -- how the value is
    positioned/selected in the payload (byte offset, tlv tag, group slot, flagged
    presence, match switch) -- plus an optional bit-range ``bitmask``.
    """
    form: dict[str, Any] = {"href": "uplink", "op": ["readproperty", "observeproperty"]}
    if fport is not None:
        form[vocab.FPORT] = fport
    if byte_offset is not None:
        form[vocab.BYTE_OFFSET] = byte_offset
    if tag is not None:
        form[vocab.TAG] = tag
    if slot is not None:
        form[vocab.SLOT] = slot
    if pad_before is not None:
        form[vocab.PAD_BEFORE] = pad_before
    if presence_field is not None:
        form[vocab.PRESENCE_FIELD] = presence_field
    if presence_bit is not None:
        form[vocab.PRESENCE_BIT] = presence_bit
    if switch_field is not None:
        form[vocab.SWITCH_FIELD] = switch_field
    if switch_value is not None:
        form[vocab.SWITCH_VALUE] = switch_value
    form[vocab.TYPE] = base
    if bitmask is not None:
        form[vocab.BITMASK] = bitmask
    if msb is not None:
        form[vocab.MSB] = msb
    _store_scaling(form, field)
    if "var" in field:
        form[vocab.VAR] = field["var"]
    if "length" in field:
        length = field["length"]
        if not _is_int_key(length):
            # `length: remaining` consumes to the end of the payload (PS-014). The
            # form carries a fixed byte count, so there is nothing to put here.
            raise UnsupportedSchemaError(
                f"unsupported length {length!r}",
                reason=SkipReason.LENGTH_NOT_FIXED,
            )
        form[vocab.LENGTH] = int(length)
    enum = _enum(field)
    if enum is not None:
        form[vocab.ENUM] = enum
    if "unece" in field:
        form[vocab.UNECE] = field["unece"]
    if "valid_range" in field:
        form[vocab.VALID_RANGE] = field["valid_range"]
    if "transform" in field:
        # Post-processing of a value read from the wire. The stages run in order after
        # mult/div/add, so the list is carried as written.
        form[vocab.TRANSFORM] = copy.deepcopy(field["transform"])
    if "value" in field:
        # Decode-neutral - the interpreter reads the byte and reports what the payload
        # held - so this rides along only to keep a downlink encoder able to fix it.
        form[vocab.CONST] = field["value"]
    return form


#: Source scaling keys mapped to their ``lorav:`` form term. Preserving the
#: source key order matters: the interpreter applies ``mult``/``div``/``add`` in
#: field-key order, so the order must survive the round-trip through the form.
_SCALING_TERMS: dict[str, str] = {
    "mult": vocab.MULTIPLIER,
    "div": vocab.DIVISOR,
    "add": vocab.OFFSET,
}


def _store_scaling(form: dict[str, Any], field: dict[str, Any]) -> None:
    """Copy scaling modifiers onto ``form`` in the field's source key order."""
    for key in field:
        term = _SCALING_TERMS.get(key)
        if term is not None:
            form[term] = field[key]


def _build_property(field: dict[str, Any], base: str, form: dict[str, Any]) -> dict[str, Any]:
    """Wrap a form in a read-only, observable WoT property affordance."""
    prop: dict[str, Any] = {
        "type": _wot_type(base, field),
        "readOnly": True,
        "observable": True,
        "forms": [form],
    }
    if "unit" in field:
        prop["unit"] = field["unit"]
    _apply_valid_range(prop, field)
    if isinstance(field.get("description"), str):
        prop["description"] = field["description"]
    return prop


def _apply_valid_range(prop: dict[str, Any], field: dict[str, Any]) -> None:
    """Reflect a ``valid_range`` ``[min, max]`` as WoT ``minimum``/``maximum``."""
    rng = field.get("valid_range")
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        prop["minimum"], prop["maximum"] = rng[0], rng[1]


def _wot_type(base: str, field: dict[str, Any]) -> str:
    """Pick the WoT DataSchema type that matches a wire type + modifiers."""
    if _enum(field) is not None:
        return "string"
    if base in ("ascii", "hex", "bytes", "base64"):
        return "string"
    if base == "bool":
        return "boolean"
    if base in ("f16", "f32", "f64") or "div" in field or "mult" in field:
        return "number"
    return "integer"


def _is_int_key(key: Any) -> bool:
    """Whether a lookup table key names an integer value."""
    try:
        int(key)
    except (TypeError, ValueError):
        return False
    return True


def _enum(field: dict[str, Any]) -> dict[int, Any] | None:
    """Canonicalise a ``values``/``lookup`` table to a ``{int: label}`` mapping."""
    raw = field.get("values", field.get("lookup"))
    if raw is None:
        return None
    if isinstance(raw, list):
        return dict(enumerate(raw))
    if isinstance(raw, dict):
        # A mapping may carry a `default` label, which applies to every value the
        # table does not list (PS-269). The form vocabulary has no term for it, so
        # the field cannot round-trip: dropping the key would silently decode an
        # unmapped value as absent where the schema names it.
        if any(not _is_int_key(key) for key in raw):
            raise UnsupportedSchemaError(
                f"enum table has a non-integer key: {sorted(map(str, raw))}",
                reason=SkipReason.ENUM_TABLE,
            )
        return {int(key): label for key, label in raw.items()}
    raise UnsupportedSchemaError(f"unsupported enum table {raw!r}", reason=SkipReason.ENUM_TABLE)


def _parse_tag(key: Any) -> list[int]:
    """Turn a tlv case key (e.g. ``"[3, 103]"`` or ``5``) into an integer list."""
    if isinstance(key, int):
        return [key]
    if isinstance(key, str):
        try:
            parsed = ast.literal_eval(key)
        except (ValueError, SyntaxError) as exc:
            raise UnsupportedSchemaError(
                f"unparseable tlv tag {key!r}", reason=SkipReason.TLV_TAG
            ) from exc
        if isinstance(parsed, int):
            return [parsed]
        if isinstance(parsed, (list, tuple)) and all(isinstance(x, int) for x in parsed):
            return list(parsed)
    raise UnsupportedSchemaError(f"unsupported tlv tag key {key!r}", reason=SkipReason.TLV_TAG)


# --- thing assembly ----------------------------------------------------------


def _assemble_td(
    schema: dict[str, Any], source: str, layout: str, properties: dict[str, Any]
) -> dict[str, Any]:
    """Build the Thing Description skeleton around the decoded properties."""
    name = schema.get("name") or _slug(source)
    title = name.replace("_", " ").strip() or name
    td: dict[str, Any] = {
        "@context": [
            "https://www.w3.org/2022/wot/td/v1.1",
            {"lorav": vocab.LORAWAN_NS},
        ],
        "@type": "Thing",
        "id": f"urn:dev:{_slug(name)}",
        "title": title,
        "securityDefinitions": {"nosec_sc": {"scheme": "nosec"}},
        "security": "nosec_sc",
        vocab.PAYLOAD_LAYOUT: layout,
        "properties": properties,
    }
    if isinstance(schema.get("description"), str):
        td["description"] = schema["description"]
    return td


def _endian_is_big(schema: dict[str, Any]) -> bool:
    """Resolve the schema-wide endianness (LoRaWAN defaults to big-endian)."""
    endian = schema.get("endian", "big")
    if endian not in ("big", "little"):
        raise UnsupportedSchemaError(f"unknown endian {endian!r}", reason=SkipReason.MALFORMED)
    return endian == "big"


def _coalesce_msb(field_msb: bool | None, endian_big: bool) -> bool:
    """A field inherits the schema endianness unless it overrides it explicitly."""
    return endian_big if field_msb is None else field_msb


def _slug(raw: str) -> str:
    """Lowercase identifier slug, matching ``converter._schema_name`` rules."""
    slug = re.sub(r"[^0-9A-Za-z]+", "_", raw).strip("_").lower()
    return slug or "lorawan_device"
