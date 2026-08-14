"""Convert a WoT Thing Description into a MultiTech payload schema.

The conversion is intentionally mechanical: every LoRaWAN event *form* carries a
field descriptor (``lorav:`` terms) that maps almost one-to-one onto a MultiTech
field, while the event's ``data`` schema supplies what the value *means* (unit,
plausible range, categorical labels). The Thing-level ``lorav:payloadLayout``
term decides how those per-event fields are *assembled* into a device schema:

* ``fixed`` -- fields sit at fixed byte offsets; gaps become ``skip`` padding.
* ``ports`` -- ``lorav:fPort`` selects a fixed layout per frame port.
* ``tlv`` / ``ctv`` -- fields are located by a tag (e.g. channel+type), not by
  offset, and become ``cases`` of a single ``tlv`` block.

Uplinks are modelled as events because a LoRaWAN device transmits when it has
something to report and cannot be polled; see :mod:`lorawan_wot.vocab`.

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


def _emit_scaling(field: dict[str, Any], form: dict[str, Any]) -> None:
    """Copy scaling modifiers onto ``field`` in the order they appear on ``form``.

    The interpreter applies ``mult``/``div``/``add`` in field-key order, so
    emitting them in form order preserves the source schema's intended order of
    operations.
    """
    for term in form:
        key = vocab.SCALE_TERMS.get(term)
        if key is not None:
            field[key] = form[term]


#: Unsigned base types a ``lorav:bitmask`` may select bits from. Multi-byte bases
#: let a byte_group pack a bit range across more than one byte (e.g. ``u24``).
_BITRANGE_BASES: frozenset[str] = frozenset({"u8", "u16", "u24", "u32"})


class _Field:
    """Intermediate representation of one event's LoRaWAN field descriptor.

    A field is assembled from the two halves of an event affordance: the ``form``
    says where the value sits in the payload and how to turn bytes into it, and
    the ``data`` schema says what the value means (``unit``, ``minimum``/
    ``maximum``, ``oneOf`` labels). Keeping the halves distinct is what lets the
    binding stay out of TD core's way -- anything TD core can already express is
    read from ``data`` rather than restated as a ``lorav:`` term.
    """

    def __init__(
        self, name: str, form: dict[str, Any], *, data: dict[str, Any] | None = None
    ) -> None:
        self.name = name
        self.form = form
        self.data = data or {}
        # Resolved MultiTech field body (without endian prefix); filled lazily.
        self._body: dict[str, Any] | None = None

    # -- accessors over the raw form -----------------------------------------

    @property
    def unit(self) -> str | None:
        """Unit of the decoded value, from the data schema's ``unit``."""
        unit = self.data.get("unit")
        return unit if isinstance(unit, str) else None

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
        """Order of this event within a multi-member group (tlv/flagged/match)."""
        return self.form.get(vocab.SLOT)

    @property
    def _present_when(self) -> dict[str, Any]:
        """The ``lorav:presentWhen`` condition, or an empty mapping if unconditional."""
        condition = self.form.get(vocab.PRESENT_WHEN)
        if condition is None:
            return {}
        if not isinstance(condition, dict):
            raise ConversionError(
                f"Event {self.name!r}: {vocab.PRESENT_WHEN!r} must be an object with "
                f"{vocab.PW_FIELD!r} plus {vocab.PW_BIT!r} or {vocab.PW_VALUE!r}."
            )
        return condition

    @property
    def presence_field(self) -> str | None:
        """Flags field gating this value, set only for the ``bit`` form of the condition."""
        condition = self._present_when
        if vocab.PW_BIT not in condition:
            return None
        return condition.get(vocab.PW_FIELD)

    @property
    def presence_bit(self) -> int | None:
        return self._present_when.get(vocab.PW_BIT)

    @property
    def switch_field(self) -> str | None:
        """Discriminator selecting this case, set only for the ``value`` form."""
        condition = self._present_when
        if vocab.PW_VALUE not in condition:
            return None
        return condition.get(vocab.PW_FIELD)

    @property
    def switch_value(self) -> int | None:
        return self._present_when.get(vocab.PW_VALUE)

    @property
    def pad_before(self) -> int:
        """Reserved bytes to consume before this field within its group (0 if none)."""
        return int(self.form.get(vocab.PAD_BEFORE, 0))

    @property
    def var(self) -> str | None:
        """Discriminator alias, re-emitted so a ``match``'s ``$alias`` reference resolves."""
        return self.form.get(vocab.ALIAS)

    @property
    def endian(self) -> str | None:
        """Byte order override for this value, or ``None`` to inherit the default."""
        value = self.form.get(vocab.ENDIAN)
        if value is None:
            return None
        if value not in vocab.SUPPORTED_ENDIAN:
            raise ConversionError(
                f"Event {self.name!r}: invalid {vocab.ENDIAN!r} {value!r}; "
                f"expected one of {', '.join(sorted(vocab.SUPPORTED_ENDIAN))}."
            )
        return value

    @property
    def wire_type(self) -> str:
        raw = self.form.get(vocab.WIRE_TYPE)
        if raw is None:
            raise ConversionError(
                f"Event {self.name!r}: LoRaWAN form is missing required {vocab.WIRE_TYPE!r}."
            )
        try:
            return vocab.resolve_wire_type(raw)
        except ValueError as exc:
            raise ConversionError(f"Event {self.name!r}: {exc}") from exc

    @property
    def derived(self) -> dict[str, Any]:
        """The ``lorav:derived`` descriptors, or an empty mapping for a wire field."""
        descriptors = self.form.get(vocab.DERIVED)
        if descriptors is None:
            return {}
        if not isinstance(descriptors, dict):
            raise ConversionError(
                f"Event {self.name!r}: {vocab.DERIVED!r} must be an object with one or "
                f"more of {', '.join(sorted(vocab.DERIVED_KEYS))}."
            )
        if unknown := sorted(descriptors.keys() - vocab.DERIVED_KEYS):
            raise ConversionError(
                f"Event {self.name!r}: unknown {vocab.DERIVED!r} key(s) "
                f"{unknown}; expected {', '.join(sorted(vocab.DERIVED_KEYS))}."
            )
        return descriptors

    @property
    def is_computed(self) -> bool:
        """True when this value is derived (zero payload bytes).

        A computed value carries ``lorav:wireType`` ``"number"`` and/or a
        ``lorav:derived`` descriptor object; the reference interpreter evaluates
        it from other already-decoded values rather than reading wire bytes.
        """
        return self.form.get(vocab.WIRE_TYPE) == vocab.COMPUTED_TYPE or bool(self.derived)

    @property
    def byte_width(self) -> int:
        """Number of payload bytes this field occupies (for fixed layouts)."""
        if self.is_computed:
            return 0
        wire = self.wire_type
        if wire in _WIRE_WIDTH:
            return _WIRE_WIDTH[wire]
        # Variable-length types must declare an explicit length.
        length = self.form.get(vocab.BYTE_LENGTH)
        if length is None:
            raise ConversionError(
                f"Event {self.name!r}: type {wire!r} requires "
                f"{vocab.BYTE_LENGTH!r} to determine its byte width."
            )
        return int(length)

    # -- MultiTech field body -------------------------------------------------

    def body(self, default_endian: str) -> dict[str, Any]:
        """Build the MultiTech field ``dict`` for this event's value.

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
        if (length := self.form.get(vocab.BYTE_LENGTH)) is not None:
            field["length"] = int(length)

        # A masked field is emitted as a bit range over its base value; the
        # MultiTech interpreter does not advance the cursor for bit ranges on its
        # own, so we make the byte consumption explicit (one byte per base byte:
        # u8 -> 1, u24 -> 3). Within a shared group only the last field consumes.
        if self.form.get(vocab.BITMASK) is not None:
            field["consume"] = self.byte_width

        # Units live in the event's data schema and map directly to schema fields.
        if self.unit is not None:
            field["unit"] = self.unit
        self._emit_semantics(field)

        return field

    def _emit_semantics(self, field: dict[str, Any]) -> None:
        """Copy the data schema's value semantics onto a MultiTech ``field``.

        These are the parts TD core already expresses, so they are read from the
        event's ``data`` rather than from a ``lorav:`` term of our own:
        ``oneOf`` carries the categorical labels and ``minimum``/``maximum`` the
        plausibility range.
        """
        if (lookup := self._lookup()) is not None:
            # The reference interpreter applies a categorical mapping through the
            # ``lookup`` modifier on a normal field; ``values`` is only honoured
            # for dedicated ``type: enum`` fields.
            field["lookup"] = lookup
        if (valid_range := self._valid_range()) is not None:
            field["valid_range"] = valid_range

    def _lookup(self) -> dict[int, Any] | None:
        """Build the interpreter's ``lookup`` table from the data schema's ``oneOf``.

        A categorical value is a TD data schema listing its allowed values as
        ``oneOf`` entries, each a ``const`` with a human-readable ``title``. Only
        integer-keyed tables can drive a ``lookup``; anything else is a
        constraint the interpreter has no equivalent for and is left alone.
        """
        one_of = self.data.get("oneOf")
        if not isinstance(one_of, list) or not one_of:
            return None
        table: dict[int, Any] = {}
        for entry in one_of:
            if not isinstance(entry, dict) or "const" not in entry or "title" not in entry:
                return None
            const = entry["const"]
            if not isinstance(const, int) or isinstance(const, bool):
                return None
            table[const] = entry["title"]
        return table

    def _valid_range(self) -> list[Any] | None:
        """Build the interpreter's ``valid_range`` from the data schema's bounds.

        The interpreter's plausibility check is a closed interval, so it needs
        both ends; a one-sided bound stays a pure data-schema constraint.
        """
        low, high = self.data.get("minimum"), self.data.get("maximum")
        if low is None or high is None:
            return None
        return [low, high]

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
                    f"Event {self.name!r}: {vocab.BITMASK!r} is only supported "
                    f"on unsigned values ({', '.join(sorted(_BITRANGE_BASES))}), "
                    f"not {wire!r}."
                )
            lo, hi = _bitmask_to_range(bitmask, self.name)
            return f"{wire}[{lo}:{hi}]"

        # Apply an explicit byte-order prefix only when it differs from default.
        endian = self.endian
        if endian is not None and endian != default_endian:
            prefix = "be_" if endian == vocab.ENDIAN_BIG else "le_"
            return f"{prefix}{wire}"
        return wire

    def _computed_body(self) -> dict[str, Any]:
        """Build the MultiTech field for a computed/derived value.

        The derived-value descriptors are carried through verbatim so the
        reference interpreter evaluates the value exactly as the source schema
        intended; the field reads no wire bytes (``type: number``). Each
        ``lorav:derived`` key is named after the MultiTech field key it produces,
        so the mapping needs no table.
        """
        field: dict[str, Any] = {"name": self.name, "type": vocab.COMPUTED_TYPE}
        derived = self.derived
        for key in vocab.DERIVED_ORDER:
            if (descriptor := derived.get(key)) is not None:
                field[key] = copy.deepcopy(descriptor)
        # mult/div/add are applied in field-key order by the interpreter; emit
        # them in form order to preserve the source schema's operation order.
        _emit_scaling(field, self.form)
        if self.unit is not None:
            field["unit"] = self.unit
        self._emit_semantics(field)
        return field


def td_to_payload_schema(td: dict[str, Any]) -> dict[str, Any]:
    """Convert a Thing Description ``dict`` to a MultiTech payload schema ``dict``.

    Only the uplink direction is handled: every event is treated as a sensor
    reading packed into the device uplink.
    """
    _reject_withdrawn_terms(td)

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

    if vocab.ENDIAN in td:
        raise ConversionError(
            f"{vocab.ENDIAN!r} is a form-level term; move it onto the event "
            f"forms whose values use that byte order."
        )

    fields = _collect_fields(td)
    if not fields:
        raise ConversionError("Thing Description has no LoRaWAN event forms to convert.")

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
    layout, since both decode a single sequential byte cursor. Events are
    partitioned by how they are located in the payload:

    * *structural* fields sit at fixed ``lorav:byteOffset`` positions (this
      includes the flags field of a ``flagged`` block and the discriminator of a
      ``match`` block, which are read before the conditional data they govern);
    * *flagged* members (``lorav:presentWhen`` with a ``bit``) appear only when a
      flag bit is set and are emitted as a trailing ``flagged`` block;
    * *match* members (``lorav:presentWhen`` with a ``value``) belong to the case
      selected by a
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
    """Build a ``flagged`` block from events gated by a flags bit.

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
                f"Event {field.name!r}: {vocab.PRESENT_WHEN!r} requires "
                f"{vocab.PW_BIT!r} alongside {vocab.PW_FIELD!r}."
            )
        by_bit.setdefault(field.presence_bit, []).append(field)

    groups = []
    for bit in sorted(by_bit):
        ordered = sorted(by_bit[bit], key=lambda f: f.slot if f.slot is not None else 0)
        groups.append({"bit": bit, "fields": [m.body(default_endian) for m in ordered]})
    return {"flagged": {"field": flag_field, "groups": groups}}


def _assemble_match(members: list[_Field], default_endian: str) -> dict[str, Any]:
    """Build a ``match`` block from events selected by a discriminator value.

    All members must name the same discriminator in ``lorav:presentWhen``; they
    are grouped into one case per ``value`` and ordered within a case by
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
                f"Event {field.name!r}: {vocab.PRESENT_WHEN!r} requires "
                f"{vocab.PW_VALUE!r} alongside {vocab.PW_FIELD!r}."
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

    Several events may share one byte when each extracts a different bit range
    (e.g. a status byte carrying a flag in bit 7 and a value in bits 0-6). Such
    fields are emitted in sequence reading the same byte; only the last advances
    the cursor, so the shared byte is consumed exactly once.
    """
    for field in fields:
        if field.byte_offset is None:
            raise ConversionError(
                f"Event {field.name!r}: 'fixed' layout requires {vocab.BYTE_OFFSET!r}."
            )

    # Group events that start at the same byte offset.
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
                f"Event {members[0].name!r}: {vocab.BYTE_OFFSET!r} {offset} "
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
                f"Event {field.name!r}: multiple events share byte offset "
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
            raise ConversionError(f"Event {field.name!r}: 'ports' layout requires {vocab.FPORT!r}.")
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

    Several events may share one tag (a *multi-field* case, e.g. a light
    channel reporting illumination + infrared + visible together). Such
    events are grouped by their ``lorav:tag`` and emitted as the ordered
    field list of one case, sequenced by ``lorav:slot``.
    """
    tag_fields = td.get(vocab.TAG_FIELDS) or _default_tag_fields()
    tag_key = [tf["name"] for tf in tag_fields]

    # MultiTech keys cases by the string form of the tag array, e.g. "[3, 103]"
    # -- match Python's list repr exactly. Group all events per tag.
    grouped: dict[str, list[_Field]] = {}
    for field in fields:
        if field.tag is None:
            raise ConversionError(
                f"Event {field.name!r}: 'tlv'/'ctv' layout requires {vocab.TAG!r}."
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
    """Extract one :class:`_Field` per LoRaWAN form across all events.

    An event may carry *several* LoRaWAN forms when the same measurement is
    reported under more than one locator (e.g. a value that appears under two
    different tlv tags). Each such form becomes its own :class:`_Field`, so the
    assembly strategies can place it back into the right case/offset/group.
    """
    fields: list[_Field] = []
    for name, affordance in (td.get(vocab.EVENTS) or {}).items():
        if not isinstance(affordance, dict):
            continue
        data = affordance.get(vocab.DATA)
        data = data if isinstance(data, dict) else {}
        for form in _lorawan_forms(affordance.get(vocab.FORMS) or []):
            fields.append(_Field(name, form, data=data))
    return fields


def _lorawan_forms(forms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every form that carries LoRaWAN binding terms."""
    lorawan_terms = {vocab.WIRE_TYPE, vocab.FPORT, vocab.BYTE_OFFSET, vocab.TAG}
    return [form for form in forms if lorawan_terms & form.keys()]


def _reject_withdrawn_terms(td: dict[str, Any]) -> None:
    """Fail with a migration hint when a Thing Description uses a withdrawn term.

    Uplinks used to be modelled as properties, and several binding terms have
    since been renamed or replaced by TD core equivalents. Silently ignoring the
    old spellings would drop the information they carried and produce a schema
    that decodes the wrong bytes, so they are rejected by name instead.
    """
    if vocab.PROPERTIES in td:
        raise ConversionError(
            f"Thing Description declares {vocab.PROPERTIES!r}: LoRaWAN uplinks are "
            f"modelled as {vocab.EVENTS!r}, since a device transmits on its own "
            f"schedule and cannot be polled. Move each affordance under "
            f"{vocab.EVENTS!r}, put its data schema under {vocab.DATA!r}, and give "
            f"its forms op {list(vocab.UPLINK_OPS)}."
        )

    for term, replacement in vocab.REMOVED_TERMS.items():
        if _mentions_term(td, term):
            raise ConversionError(
                f"Thing Description uses withdrawn term {term!r}; use {replacement} instead."
            )


def _mentions_term(node: Any, term: str) -> bool:
    """True when ``term`` appears as a key anywhere in a decoded JSON document."""
    if isinstance(node, dict):
        return term in node or any(_mentions_term(value, term) for value in node.values())
    if isinstance(node, list):
        return any(_mentions_term(item, term) for item in node)
    return False


def _default_endian(fields: list[_Field]) -> str:
    """Pick the schema-wide endianness from the per-form byte orders.

    The schema language carries one document-wide ``endian`` plus a ``be_``/``le_``
    prefix on individual fields that disagree, so the most common per-form value
    becomes the schema default and only the minority needs a prefix. With nothing
    declared -- or on a tie -- the default is big-endian, matching both the LoRaWAN
    convention and the reference payload schema language.
    """
    votes = [endian for f in fields if (endian := f.endian) is not None]
    if not votes:
        return vocab.ENDIAN_BIG
    return max(set(votes), key=lambda e: (votes.count(e), e == vocab.ENDIAN_BIG))


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
            f"Event {field_name!r}: invalid {vocab.BITMASK!r} {bitmask!r}."
        ) from exc
    if mask <= 0:
        raise ConversionError(f"Event {field_name!r}: {vocab.BITMASK!r} must be a positive value.")
    lo = (mask & -mask).bit_length() - 1  # index of lowest set bit
    hi = mask.bit_length() - 1  # index of highest set bit
    if mask != (((1 << (hi + 1)) - 1) ^ ((1 << lo) - 1)):
        raise ConversionError(
            f"Event {field_name!r}: non-contiguous {vocab.BITMASK!r} {bitmask!r} "
            f"cannot be represented as a bit range."
        )
    return lo, hi


def _schema_name(td: dict[str, Any]) -> str:
    """Derive a MultiTech schema name from the TD id or title."""
    raw = td.get("id") or td.get("title") or "lorawan_device"
    # MultiTech names are identifiers; keep alphanumerics and underscores.
    name = re.sub(r"[^0-9A-Za-z]+", "_", raw).strip("_").lower()
    return name or "lorawan_device"
