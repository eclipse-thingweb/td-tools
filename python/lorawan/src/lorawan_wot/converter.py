"""Convert a WoT Thing Description into a MultiTech payload schema.

The conversion is intentionally mechanical: every LoRaWAN property *form* carries
a field descriptor (``lorav:`` terms) that maps almost one-to-one onto a
MultiTech field. The Thing-level ``lorav:payloadLayout`` term decides how those
per-property fields are *assembled* into a single device schema:

* ``fixed`` -- fields sit at fixed byte offsets; gaps become ``skip`` padding.
* ``ports`` -- ``lorav:fPort`` selects a fixed layout per frame port.
* ``tlv`` / ``ctv`` -- fields are located by a tag (e.g. channel+type), not by
  offset, and become ``cases`` of a single ``tlv`` block.

The output is a plain ``dict`` matching the MultiTech / LoRa Alliance Payload
Schema language, ready to be serialised to YAML or fed to the interpreter.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from lorawan_wot import vocab

#: Byte width of each fixed-width MultiTech wire type, used to lay out ``fixed``
#: and ``ports`` payloads and to size ``skip`` padding between fields.
_WIRE_WIDTH: dict[str, int] = {
    "u8": 1,
    "s8": 1,
    "bool": 1,
    "u16": 2,
    "s16": 2,
    "f16": 2,
    "u24": 3,
    "s24": 3,
    "u32": 4,
    "s32": 4,
    "f32": 4,
    "u64": 8,
    "s64": 8,
    "f64": 8,
}


class ConversionError(ValueError):
    """Raised when a Thing Description cannot be converted to a payload schema."""


#: Form scaling terms mapped to their MultiTech field key. The interpreter applies
#: ``mult``/``div``/``add`` in field-key order, so emitting them in form order
#: preserves the source schema's intended order of operations.
_SCALE_MAP: dict[str, str] = {
    vocab.MULTIPLIER: "mult",
    vocab.DIVISOR: "div",
    vocab.OFFSET: "add",
}


def _emit_scaling(field: dict[str, Any], form: dict[str, Any]) -> None:
    """Copy scaling modifiers onto ``field`` in the order they appear on ``form``."""
    for term in form:
        key = _SCALE_MAP.get(term)
        if key is not None:
            field[key] = form[term]


#: Unsigned base types a ``lorav:bitmask`` may select bits from. Multi-byte bases
#: let a byte_group pack a bit range across more than one byte (e.g. ``u24``).
_BITRANGE_BASES: frozenset[str] = frozenset({"u8", "u16", "u24", "u32"})


class _Field:
    """Intermediate representation of one property's LoRaWAN field descriptor."""

    def __init__(self, name: str, form: dict[str, Any], *, unit: str | None = None) -> None:
        self.name = name
        self.form = form
        self.unit = unit
        # Resolved MultiTech field body (without endian prefix); filled lazily.
        self._body: dict[str, Any] | None = None

    # -- accessors over the raw form -----------------------------------------

    @property
    def byte_offset(self) -> int | None:
        return self.form.get(vocab.BYTE_OFFSET)

    @property
    def fport(self) -> int | None:
        return self.form.get(vocab.FPORT)

    @property
    def tag(self) -> list[int] | None:
        return self.form.get(vocab.TAG)

    @property
    def slot(self) -> int | None:
        """Order of this property within a multi-member group (tlv/flagged/match)."""
        return self.form.get(vocab.SLOT)

    @property
    def presence_field(self) -> str | None:
        return self.form.get(vocab.PRESENCE_FIELD)

    @property
    def presence_bit(self) -> int | None:
        return self.form.get(vocab.PRESENCE_BIT)

    @property
    def switch_field(self) -> str | None:
        return self.form.get(vocab.SWITCH_FIELD)

    @property
    def switch_value(self) -> int | None:
        return self.form.get(vocab.SWITCH_VALUE)

    @property
    def pad_before(self) -> int:
        """Reserved bytes to consume before this field within its group (0 if none)."""
        return int(self.form.get(vocab.PAD_BEFORE, 0))

    @property
    def var(self) -> str | None:
        """Discriminator alias, re-emitted so a ``match``'s ``$var`` reference resolves."""
        return self.form.get(vocab.VAR)

    @property
    def msb(self) -> bool | None:
        return self.form.get(vocab.MSB)

    @property
    def wire_type(self) -> str:
        raw = self.form.get(vocab.TYPE)
        if raw is None:
            raise ConversionError(
                f"Property {self.name!r}: LoRaWAN form is missing required {vocab.TYPE!r}."
            )
        try:
            return vocab.resolve_wire_type(raw)
        except ValueError as exc:
            raise ConversionError(f"Property {self.name!r}: {exc}") from exc

    @property
    def is_computed(self) -> bool:
        """True when this property is a derived value (zero payload bytes).

        A computed property carries ``lorav:type`` ``"number"`` and/or one of the
        derived-value descriptors (``lorav:ref``/``polynomial``/``transform``/
        ``compute``/``guard``); the reference interpreter evaluates it from other
        already-decoded values rather than reading wire bytes for it.
        """
        wire = self.form.get(vocab.TYPE)
        if wire is None:
            # No wire type at all: derived if it says where its value comes from.
            return bool(vocab.COMPUTED_TERMS & self.form.keys())
        # A real wire type means bytes are read, whatever post-processing rides along.
        # Inferring "computed" from any lorav: descriptor gave a transform-carrying
        # scalar a byte width of zero, so every field after it read from the wrong
        # offset and the field itself vanished from the decode.
        return wire == vocab.COMPUTED_TYPE

    @property
    def byte_width(self) -> int:
        """Number of payload bytes this field occupies (for fixed layouts)."""
        if self.is_computed:
            return 0
        wire = self.wire_type
        if wire in _WIRE_WIDTH:
            return _WIRE_WIDTH[wire]
        # Variable-length types must declare an explicit length.
        length = self.form.get(vocab.LENGTH)
        if length is None:
            raise ConversionError(
                f"Property {self.name!r}: type {wire!r} requires "
                f"{vocab.LENGTH!r} to determine its byte width."
            )
        return int(length)

    # -- MultiTech field body -------------------------------------------------

    def body(self, default_endian: str) -> dict[str, Any]:
        """Build the MultiTech field ``dict`` for this property.

        ``default_endian`` is the schema-wide endianness; a per-field byte order
        that differs is expressed with a ``be_``/``le_`` type prefix.
        """
        if self.is_computed:
            return self._computed_body()

        field: dict[str, Any] = {"name": self.name, "type": self._typed(default_endian)}

        # A discriminator alias (``var``) must survive the round-trip so a
        # ``match`` block referencing ``$var`` resolves to this field's value.
        if self.var is not None:
            field["var"] = self.var

        # Scaling: multiplier -> mult, divisor -> div, offset -> add. The
        # interpreter applies these in field-key order, so emit them in the order
        # they appear on the form (which preserves the source schema's order).
        _emit_scaling(field, self.form)

        # Length for variable-length types (string/bytes/hex/base64).
        if (length := self.form.get(vocab.LENGTH)) is not None:
            field["length"] = int(length)

        # A masked field is emitted as a bit range over its base value; the
        # MultiTech interpreter does not advance the cursor for bit ranges on its
        # own, so we make the byte consumption explicit (one byte per base byte:
        # u8 -> 1, u24 -> 3). Within a shared group only the last field consumes.
        if self.form.get(vocab.BITMASK) is not None:
            field["consume"] = self.byte_width

        # Units live at property level in TDs and map directly to schema fields.
        if self.unit is not None:
            field["unit"] = self.unit
        # Semantics carried straight through to the schema.
        if (unece := self.form.get(vocab.UNECE)) is not None:
            field["unece"] = unece
        if (enum := self.form.get(vocab.ENUM)) is not None:
            # The reference interpreter applies a categorical mapping through the
            # ``lookup`` modifier on a normal field; ``values`` is only honoured
            # for dedicated ``type: enum`` fields. JSON object keys arrive as
            # strings, so coerce them back to ints for integer-indexed lookup.
            field["lookup"] = {int(key): label for key, label in enum.items()}
        if (valid_range := self.form.get(vocab.VALID_RANGE)) is not None:
            field["valid_range"] = copy.deepcopy(valid_range)
        if (transform := self.form.get(vocab.TRANSFORM)) is not None:
            # Post-processing on a wire field. Restored here as well as on the derived
            # path: without it the field decoded to its raw value (65535 rather than
            # 327.67 for decentlab's air_temperature), because the stages were dropped
            # while the bytes were read correctly.
            field["transform"] = copy.deepcopy(transform)
        if (const := self.form.get(vocab.CONST)) is not None:
            # The byte an encoder must emit. Decoding ignores it, so this only has to
            # survive the round trip.
            field["value"] = const

        return field

    def _typed(self, default_endian: str) -> str:
        """Return the wire type, applying a bitmask and endianness prefix."""
        wire = self.wire_type
        bitmask = self.form.get(vocab.BITMASK)
        if bitmask is not None:
            # The reference interpreter extracts a contiguous bit range from an
            # unsigned base value; single-byte (u8) and multi-byte (u16/u24/u32)
            # bases are both supported, the latter for byte_groups wider than one
            # byte (e.g. a 20-bit field packed across three bytes).
            if wire not in _BITRANGE_BASES:
                raise ConversionError(
                    f"Property {self.name!r}: {vocab.BITMASK!r} is only supported "
                    f"on unsigned values ({', '.join(sorted(_BITRANGE_BASES))}), "
                    f"not {wire!r}."
                )
            lo, hi = _bitmask_to_range(bitmask, self.name)
            return f"{wire}[{lo}:{hi}]"

        # Apply an explicit byte-order prefix only when it differs from default.
        if self.msb is not None and _endian(self.msb) != default_endian:
            prefix = "be_" if self.msb else "le_"
            return f"{prefix}{wire}"
        return wire

    def _computed_body(self) -> dict[str, Any]:
        """Build the MultiTech field for a computed/derived value.

        The derived-value descriptors are carried through verbatim so the
        reference interpreter evaluates the property exactly as the source schema
        intended; the field reads no wire bytes (``type: number``).
        """
        field: dict[str, Any] = {"name": self.name, "type": vocab.COMPUTED_TYPE}
        if (ref := self.form.get(vocab.REF)) is not None:
            field["ref"] = ref
        if (polynomial := self.form.get(vocab.POLYNOMIAL)) is not None:
            field["polynomial"] = copy.deepcopy(polynomial)
        if (compute := self.form.get(vocab.COMPUTE)) is not None:
            field["compute"] = copy.deepcopy(compute)
        if (guard := self.form.get(vocab.GUARD)) is not None:
            field["guard"] = copy.deepcopy(guard)
        if (transform := self.form.get(vocab.TRANSFORM)) is not None:
            field["transform"] = copy.deepcopy(transform)
        # mult/div/add are applied in field-key order by the interpreter; emit
        # them in form order to preserve the source schema's operation order.
        _emit_scaling(field, self.form)
        if self.unit is not None:
            field["unit"] = self.unit
        if (unece := self.form.get(vocab.UNECE)) is not None:
            field["unece"] = unece
        if (valid_range := self.form.get(vocab.VALID_RANGE)) is not None:
            field["valid_range"] = copy.deepcopy(valid_range)
        return field


def td_to_payload_schema(td: dict[str, Any]) -> dict[str, Any]:
    """Convert a Thing Description ``dict`` to a MultiTech payload schema ``dict``.

    Only the uplink direction is handled: every property is treated as a sensor
    reading packed into the device uplink.
    """
    layout = td.get(vocab.PAYLOAD_LAYOUT)
    if layout is None:
        raise ConversionError(
            f"Thing Description is missing the Thing-level {vocab.PAYLOAD_LAYOUT!r} "
            f"term (one of: {', '.join(sorted(vocab.SUPPORTED_LAYOUTS))})."
        )
    if layout not in vocab.SUPPORTED_LAYOUTS:
        raise ConversionError(
            f"Unsupported {vocab.PAYLOAD_LAYOUT!r} {layout!r}; expected one of "
            f"{', '.join(sorted(vocab.SUPPORTED_LAYOUTS))}."
        )

    fields = _collect_fields(td)
    if not fields:
        raise ConversionError("Thing Description has no LoRaWAN property forms to convert.")

    default_endian = _default_endian(fields)
    schema: dict[str, Any] = {
        "name": _schema_name(td),
        "version": 1,
        "endian": default_endian,
        "direction": "uplink",
    }
    if (description := td.get("title") or td.get("description")) is not None:
        schema["description"] = description

    if layout == vocab.LAYOUT_FIXED:
        schema["fields"] = _assemble_fixed_layout(fields, default_endian)
    elif layout == vocab.LAYOUT_PORTS:
        schema["ports"] = _assemble_ports(fields, default_endian)
    else:  # tlv / ctv
        schema["fields"] = [_assemble_tlv(td, fields, default_endian)]

    return schema


# --- assembly strategies -----------------------------------------------------


def _assemble_grouped_fixed(fields: list[_Field], default_endian: str) -> list[dict[str, Any]]:
    """Partition fields by location and assemble them into a fixed-cursor body.

    Shared by the Thing-level ``fixed`` layout and each port of a ``ports``
    layout, since both decode a single sequential byte cursor. Properties are
    partitioned by how they are located in the payload:

    * *structural* fields sit at fixed ``lorav:byteOffset`` positions (this
      includes the flags field of a ``flagged`` block and the discriminator of a
      ``match`` block, which are read before the conditional data they govern);
    * *flagged* members (``lorav:presenceField``) appear only when a flag bit is
      set and are emitted as a trailing ``flagged`` block;
    * *match* members (``lorav:switchField``) belong to the case selected by a
      discriminator value and are emitted as a trailing ``match`` block.

    Structural data is laid out first (the conditional blocks decode from the
    cursor left after it), matching how the reference interpreter walks payloads.
    """
    structural = [f for f in fields if f.presence_field is None and f.switch_field is None]
    flagged_members = [f for f in fields if f.presence_field is not None]
    match_members = [f for f in fields if f.switch_field is not None]

    out = _assemble_fixed(structural, default_endian) if structural else []
    if flagged_members:
        out.append(_assemble_flagged(flagged_members, default_endian))
    if match_members:
        out.append(_assemble_match(match_members, default_endian))
    return out


def _assemble_fixed_layout(fields: list[_Field], default_endian: str) -> list[dict[str, Any]]:
    """Assemble the Thing-level ``fixed`` layout (see `_assemble_grouped_fixed`)."""
    out = _assemble_grouped_fixed(fields, default_endian)
    if not out:
        raise ConversionError("'fixed' layout produced no fields.")
    return out


def _assemble_flagged(members: list[_Field], default_endian: str) -> dict[str, Any]:
    """Build a ``flagged`` block from properties gated by a flags bit.

    All members must reference the same ``lorav:presenceField``; they are grouped
    by ``lorav:presenceBit`` (one group per bit, in bit order) and ordered within
    a group by ``lorav:slot``.
    """
    flag_names = {f.presence_field for f in members}
    if len(flag_names) != 1:
        raise ConversionError(
            f"'flagged' members reference differing presence fields: {sorted(flag_names)}."
        )
    flag_field = next(iter(flag_names))

    by_bit: dict[int, list[_Field]] = {}
    for field in members:
        if field.presence_bit is None:
            raise ConversionError(
                f"Property {field.name!r}: {vocab.PRESENCE_FIELD!r} requires "
                f"{vocab.PRESENCE_BIT!r}."
            )
        by_bit.setdefault(field.presence_bit, []).append(field)

    groups = []
    for bit in sorted(by_bit):
        ordered = sorted(by_bit[bit], key=lambda f: f.slot if f.slot is not None else 0)
        groups.append({"bit": bit, "fields": [m.body(default_endian) for m in ordered]})
    return {"flagged": {"field": flag_field, "groups": groups}}


def _assemble_match(members: list[_Field], default_endian: str) -> dict[str, Any]:
    """Build a ``match`` block from properties selected by a discriminator value.

    All members must reference the same ``lorav:switchField``; they are grouped
    into one case per ``lorav:switchValue`` and ordered within a case by
    ``lorav:slot``. The discriminator is referenced by name (``$field``); the
    interpreter stores every decoded scalar by name, so no explicit ``var`` is
    needed.
    """
    switch_names = {f.switch_field for f in members}
    if len(switch_names) != 1:
        raise ConversionError(
            f"'match' members reference differing switch fields: {sorted(switch_names)}."
        )
    switch_field = next(iter(switch_names))

    by_value: dict[int, list[_Field]] = {}
    for field in members:
        if field.switch_value is None:
            raise ConversionError(
                f"Property {field.name!r}: {vocab.SWITCH_FIELD!r} requires {vocab.SWITCH_VALUE!r}."
            )
        by_value.setdefault(field.switch_value, []).append(field)

    cases: dict[int, list[dict[str, Any]]] = {}
    for value in sorted(by_value):
        ordered = sorted(by_value[value], key=lambda f: f.slot if f.slot is not None else 0)
        cases[value] = _assemble_case_body(ordered, default_endian, value)
    return {"match": {"field": f"${switch_field}", "cases": cases}}


def _assemble_case_body(
    ordered: list[_Field], default_endian: str, value: int
) -> list[dict[str, Any]]:
    """Emit one ``match`` case's fields, in ``lorav:slot`` order.

    Reserved bytes recorded on a member (``lorav:padBefore``) are replayed as
    ``skip`` padding immediately before it, restoring the sequential layout.
    Consecutive members that declare the *same* ``lorav:byteOffset`` read bit
    ranges out of one shared byte -- exactly like a ``fixed`` layout's shared
    byte (e.g. a status byte carrying a low-battery flag in bit 7 and a voltage
    value in bits 0-6) -- and are combined via `_assemble_shared_byte` so only
    the last one advances the cursor.
    """
    body: list[dict[str, Any]] = []
    i = 0
    while i < len(ordered):
        member = ordered[i]
        if member.pad_before:
            body.append(
                {"name": f"_pad_{value}_{len(body)}", "type": "skip", "length": member.pad_before}
            )
        group = [member]
        j = i + 1
        while (
            j < len(ordered)
            and member.byte_offset is not None
            and ordered[j].byte_offset == member.byte_offset
            and not ordered[j].pad_before
        ):
            group.append(ordered[j])
            j += 1
        if len(group) > 1:
            body.extend(_assemble_shared_byte(group, default_endian, member.byte_offset))
        else:
            body.append(member.body(default_endian))
        i = j
    return body


def _assemble_fixed(fields: list[_Field], default_endian: str) -> list[dict[str, Any]]:
    """Lay fields out by ``lorav:byteOffset``, inserting ``skip`` padding.

    Several properties may share one byte when each extracts a different bit range
    (e.g. a status byte carrying a flag in bit 7 and a value in bits 0-6). Such
    fields are emitted in sequence reading the same byte; only the last advances
    the cursor, so the shared byte is consumed exactly once.
    """
    for field in fields:
        if field.byte_offset is None:
            raise ConversionError(
                f"Property {field.name!r}: 'fixed' layout requires {vocab.BYTE_OFFSET!r}."
            )

    # Group properties that start at the same byte offset.
    groups: dict[int, list[_Field]] = {}
    for field in fields:
        groups.setdefault(field.byte_offset, []).append(field)

    out: list[dict[str, Any]] = []
    # The interpreter reads sequentially from payload position 0, so any header
    # bytes before the first field must be skipped explicitly.
    cursor = 0
    for offset in sorted(groups):
        members = groups[offset]
        gap = offset - cursor
        if gap < 0:
            raise ConversionError(
                f"Property {members[0].name!r}: {vocab.BYTE_OFFSET!r} {offset} "
                f"overlaps the previous field (cursor at {cursor})."
            )
        if gap > 0:
            # Reserved/undecoded bytes between two fields become padding.
            out.append({"name": f"_pad_{cursor}", "type": "skip", "length": gap})

        # Derived values read no wire bytes; they reference earlier-decoded
        # fields, so they are emitted first (in slot order) and do not move the
        # cursor. A group may be computed-only (trailing derived values).
        computed = [m for m in members if m.is_computed]
        raw = [m for m in members if not m.is_computed]
        for field in sorted(computed, key=lambda f: f.slot if f.slot is not None else 0):
            out.append(field.body(default_endian))

        if not raw:
            continue
        if len(raw) == 1:
            field = raw[0]
            out.append(field.body(default_endian))
            cursor = offset + field.byte_width
        else:
            out.extend(_assemble_shared_byte(raw, default_endian, offset))
            # A shared group consumes its base width once (u8 group -> 1 byte,
            # u24 group -> 3 bytes), regardless of how many bit ranges read it.
            cursor = offset + max(field.byte_width for field in raw)
    return out


def _assemble_shared_byte(
    members: list[_Field], default_endian: str, offset: int
) -> list[dict[str, Any]]:
    """Emit several bit-range fields that share one (possibly multi-byte) group.

    Each member must carry a ``lorav:bitmask`` (the only way to read part of a
    value). The fields all read the same bytes; only the last one consumes them,
    so the cursor advances by the group's base width exactly once.
    """
    for field in members:
        if field.form.get(vocab.BITMASK) is None:
            raise ConversionError(
                f"Property {field.name!r}: multiple properties share byte offset "
                f"{offset}, so each must use {vocab.BITMASK!r} to select its bits; "
                f"{field.name!r} does not."
            )

    # Order by lowest selected bit for stable, readable output.
    ordered = sorted(members, key=lambda f: _bitmask_to_range(f.form[vocab.BITMASK], f.name)[0])
    bodies = [field.body(default_endian) for field in ordered]
    # body() sets consume=base width for masked fields; only the last field may
    # advance the shared group, so the earlier ones must not consume it.
    for body in bodies[:-1]:
        body["consume"] = 0
    bodies[-1]["consume"] = max(field.byte_width for field in ordered)
    return bodies


def _assemble_ports(fields: list[_Field], default_endian: str) -> dict[int, dict[str, Any]]:
    """Group fields by ``lorav:fPort``; each port assembles like a ``fixed``
    layout (structural fields plus an optional trailing ``flagged``/``match``
    block), via `_assemble_grouped_fixed`.
    """
    by_port: dict[int, list[_Field]] = {}
    for field in fields:
        if field.fport is None:
            raise ConversionError(
                f"Property {field.name!r}: 'ports' layout requires {vocab.FPORT!r}."
            )
        by_port.setdefault(field.fport, []).append(field)

    result: dict[int, dict[str, Any]] = {}
    for port, port_fields in sorted(by_port.items()):
        body = _assemble_grouped_fixed(port_fields, default_endian)
        if not body:
            raise ConversionError(f"Port {port}: produced no fields.")
        result[port] = {"fields": body}
    return result


def _assemble_tlv(td: dict[str, Any], fields: list[_Field], default_endian: str) -> dict[str, Any]:
    """Build a single ``tlv`` block whose cases are keyed by ``lorav:tag``.

    Several properties may share one tag (a *multi-field* case, e.g. a light
    channel reporting illumination + infrared + visible together). Such
    properties are grouped by their ``lorav:tag`` and emitted as the ordered
    field list of one case, sequenced by ``lorav:slot``.
    """
    tag_fields = td.get(vocab.TAG_FIELDS) or _default_tag_fields()
    tag_key = [tf["name"] for tf in tag_fields]

    # MultiTech keys cases by the string form of the tag array, e.g. "[3, 103]"
    # -- match Python's list repr exactly. Group all properties per tag.
    grouped: dict[str, list[_Field]] = {}
    for field in fields:
        if field.tag is None:
            raise ConversionError(
                f"Property {field.name!r}: 'tlv'/'ctv' layout requires {vocab.TAG!r}."
            )
        grouped.setdefault(str(list(field.tag)), []).append(field)

    cases: dict[str, list[dict[str, Any]]] = {}
    for key, members in grouped.items():
        ordered = sorted(members, key=lambda f: f.slot if f.slot is not None else 0)
        cases[key] = [member.body(default_endian) for member in ordered]

    return {
        "tlv": {
            "tag_fields": tag_fields,
            "tag_key": tag_key,
            "cases": cases,
        }
    }


# --- helpers -----------------------------------------------------------------


def _collect_fields(td: dict[str, Any]) -> list[_Field]:
    """Extract one :class:`_Field` per LoRaWAN form across all properties.

    A property may carry *several* LoRaWAN forms when the same measurement is
    reported under more than one locator (e.g. a value that appears under two
    different tlv tags). Each such form becomes its own :class:`_Field`, so the
    assembly strategies can place it back into the right case/offset/group.
    """
    fields: list[_Field] = []
    for name, affordance in (td.get("properties") or {}).items():
        unit = affordance.get("unit") if isinstance(affordance, dict) else None
        unit = unit if isinstance(unit, str) else None
        for form in _lorawan_forms(affordance.get("forms") or []):
            fields.append(_Field(name, form, unit=unit))
    return fields


def _lorawan_forms(forms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every form that carries LoRaWAN binding terms."""
    lorawan_terms = {vocab.TYPE, vocab.FPORT, vocab.BYTE_OFFSET, vocab.TAG}
    return [form for form in forms if lorawan_terms & form.keys()]


def _default_endian(fields: list[_Field]) -> str:
    """Pick the schema-wide endianness from the property forms.

    Defaults to big-endian (the LoRaWAN convention). The most common explicit
    ``lorav:mostSignificantByte`` value wins so that the majority of fields need
    no per-field prefix.
    """
    votes = [_endian(f.msb) for f in fields if f.msb is not None]
    if not votes:
        return "big"
    return max(set(votes), key=votes.count)


def _endian(msb: bool) -> str:
    return "big" if msb else "little"


def _default_tag_fields() -> list[dict[str, str]]:
    """Channel + type tag fields, the common channel/type/value convention."""
    return [{"name": "channel", "type": "u8"}, {"name": "type", "type": "u8"}]


def _bitmask_to_range(bitmask: str, field_name: str) -> tuple[int, int]:
    """Convert a contiguous hex bitmask (e.g. ``"0x3FFF"``) to ``(lo, hi)`` bits.

    Raises :class:`ConversionError` for non-contiguous masks, which the MultiTech
    bit-range syntax cannot express.
    """
    try:
        mask = int(bitmask, 16) if isinstance(bitmask, str) else int(bitmask)
    except ValueError as exc:
        raise ConversionError(
            f"Property {field_name!r}: invalid {vocab.BITMASK!r} {bitmask!r}."
        ) from exc
    if mask <= 0:
        raise ConversionError(
            f"Property {field_name!r}: {vocab.BITMASK!r} must be a positive value."
        )
    lo = (mask & -mask).bit_length() - 1  # index of lowest set bit
    hi = mask.bit_length() - 1  # index of highest set bit
    if mask != (((1 << (hi + 1)) - 1) ^ ((1 << lo) - 1)):
        raise ConversionError(
            f"Property {field_name!r}: non-contiguous {vocab.BITMASK!r} {bitmask!r} "
            f"cannot be represented as a bit range."
        )
    return lo, hi


def _schema_name(td: dict[str, Any]) -> str:
    """Derive a MultiTech schema name from the TD id or title."""
    raw = td.get("id") or td.get("title") or "lorawan_device"
    # MultiTech names are identifiers; keep alphanumerics and underscores.
    name = re.sub(r"[^0-9A-Za-z]+", "_", raw).strip("_").lower()
    return name or "lorawan_device"
