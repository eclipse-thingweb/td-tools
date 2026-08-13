"""LoRaWAN WoT binding vocabulary.

This module is the single source of truth for the LoRaWAN binding terms used in
Thing Descriptions and for the mapping between those terms and the MultiTech /
LoRa Alliance Payload Schema language. No other module may spell a ``lorav:``
term as a string literal; ``tests/test_vocab_source.py`` enforces that, because a
term defined in two places is a term that will eventually disagree with itself.

A LoRaWAN device *pushes* readings: it transmits an uplink when it has something
to report and cannot be polled. That is a WoT **event**, not a property, so every
decoded value is modelled as an event affordance whose ``data`` schema describes
the value and whose form carries the ``lorav:`` terms locating it in the payload.

Two namespaces are involved:

* ``lorav:`` -- the LoRaWAN binding vocabulary (this project). Terms appear on a
  Thing (``lorav:payloadLayout``, ``lorav:tagFields``) and on individual event
  *forms* (``lorav:fPort``, ``lorav:wireType``, ``lorav:endian`` ...). Binding
  terms stay on forms, matching the WoT Modbus binding, because they describe how
  a value is fetched off the wire rather than what the value means.
* ``xsd:``  -- XML Schema data types, reused by ``lorav:wireType`` to name the
  wire data type of a value, following the published LoRaWAN binding draft.

Anything TD core already expresses is *not* redefined here: value constraints use
``minimum``/``maximum``, categorical mappings use ``oneOf`` with ``const``, units
use ``unit``, and device metadata uses ``schema:``/``version``. :data:`REMOVED_TERMS`
records the terms that were withdrawn for that reason and what replaced them.
"""

from __future__ import annotations

from typing import Final

#: JSON-LD namespace IRI for the LoRaWAN binding vocabulary.
LORAWAN_NS: Final = "https://www.w3.org/2024/wot/lorawan#"
#: Prefix used for the binding vocabulary inside Thing Descriptions.
LORAWAN_PREFIX: Final = "lorav"

# --- Event affordance shape --------------------------------------------------
#
# Uplinks are modelled one event per decoded value. The alternative -- one event
# per uplink message carrying every value in a nested ``data`` object -- mirrors
# the radio more literally but makes each value harder to consume and would force
# the payload locators into the data schema, where they do not belong.

#: Key holding an event's payload schema, i.e. the description of the value.
DATA: Final = "data"
#: Key holding an affordance's protocol bindings.
FORMS: Final = "forms"
#: Top-level Thing key carrying the uplink affordances.
EVENTS: Final = "events"

#: Top-level Thing key uplinks used to be modelled under. Named here so the
#: converter can recognise a Thing Description written against the older model
#: and say so, instead of reporting that it contains nothing to convert.
PROPERTIES: Final = "properties"

#: Relative target of an uplink form. LoRaWAN has no per-value endpoint: values
#: arrive in whatever uplink the device chooses to send, so the href names the
#: direction and the ``lorav:`` terms do the actual locating.
UPLINK_HREF: Final = "uplink"

#: Operations an uplink form supports. A device cannot be polled, so ``readproperty``
#: has no meaning; subscribing to the device's transmissions is the only interaction.
UPLINK_OPS: Final = ("subscribeevent", "unsubscribeevent")

# --- Thing-level term --------------------------------------------------------

#: Term naming the overall payload layout of a device. It tells the converter
#: how to assemble the per-event field descriptors into one payload schema.
PAYLOAD_LAYOUT: Final = "lorav:payloadLayout"

#: Supported payload layout kinds.
LAYOUT_FIXED: Final = "fixed"  # fixed byte positions
LAYOUT_PORTS: Final = "ports"  # fPort selects a fixed layout
LAYOUT_TLV: Final = "tlv"  # tag/length/value
LAYOUT_CTV: Final = "ctv"  # channel/type/value (e.g. Cayenne LPP)
SUPPORTED_LAYOUTS: Final = frozenset({LAYOUT_FIXED, LAYOUT_PORTS, LAYOUT_TLV, LAYOUT_CTV})

#: Optional Thing-level term describing the tag field(s) for ``tlv``/``ctv``
#: layouts, e.g. ``[{"name": "channel", "type": "u8"}, {"name": "type",
#: "type": "u8"}]``. When omitted, ``ctv`` defaults to channel(u8)+type(u8).
TAG_FIELDS: Final = "lorav:tagFields"

# --- Form-level terms --------------------------------------------------------

#: Byte order of this multi-byte value. Form-level only: the schema-wide
#: default is derived from the per-form values, so a Thing-level declaration
#: would be lost and is rejected instead.
#:
#: This is *only* about byte order: the payload schema language has no
#: byte-swap or word-swap concept, so there is nothing else to express here.
ENDIAN: Final = "lorav:endian"

#: Supported byte orders. ``big`` is the default, matching both the LoRaWAN
#: convention and the reference payload schema language.
ENDIAN_BIG: Final = "big"
ENDIAN_LITTLE: Final = "little"
SUPPORTED_ENDIAN: Final = frozenset({ENDIAN_BIG, ENDIAN_LITTLE})

FPORT: Final = "lorav:fPort"  # LoRaWAN frame port (routing / branching)
WIRE_TYPE: Final = "lorav:wireType"  # wire data type (xsd:* alias or native)
MULTIPLIER: Final = "lorav:multiplier"  # raw * multiplier
DIVISOR: Final = "lorav:divisor"  # raw / divisor
ADDEND: Final = "lorav:addend"  # value + addend (after scaling)
BITMASK: Final = "lorav:bitmask"  # hex mask, e.g. "0x3FFF"
BYTE_OFFSET: Final = "lorav:byteOffset"  # fixed-layout position (bytes)
BYTE_LENGTH: Final = "lorav:byteLength"  # byte length for string/bytes/hex
TAG: Final = "lorav:tag"  # tlv/ctv case selector, e.g. [3, 103]

#: Scaling terms mapped to their MultiTech field key, in the order the reference
#: interpreter applies them. Declared once and inverted for the reverse direction
#: (see :data:`SCALE_TERMS_BY_FIELD_KEY`) so a rename cannot desync the two
#: converters, which previously each carried their own copy of this mapping.
SCALE_TERMS: Final[dict[str, str]] = {
    MULTIPLIER: "mult",
    DIVISOR: "div",
    ADDEND: "add",
}

#: Reverse of :data:`SCALE_TERMS`, for generating a Thing Description.
SCALE_TERMS_BY_FIELD_KEY: Final[dict[str, str]] = {v: k for k, v in SCALE_TERMS.items()}

# --- Grouping / conditional-presence terms -----------------------------------
#
# Some devices pack several values into one addressable unit, or include a value
# only conditionally. These terms let independent WoT events describe such a
# shared structure without abandoning the "one event = one value" model:
#
# * multi-field TLV -- several events share one ``lorav:tag`` and are ordered
#   by ``lorav:slot`` (e.g. a light channel reporting illumination + infrared).
# * ``flagged``     -- a value is present only when a bit of a named flags value
#   is set: ``lorav:presentWhen`` with ``field`` + ``bit``.
# * ``match``       -- a value belongs to the case selected when a named
#   discriminator equals a value: ``lorav:presentWhen`` with ``field`` + ``value``;
#   ordered within the case by ``lorav:slot``.
#
# Both conditional shapes answer one question -- "under what condition does this
# value appear?" -- so they share one term. Which shape is meant follows from
# which key is present: ``bit`` selects a flag bit, ``value`` selects a match case.
# They were previously four sibling terms (presenceField/presenceBit/switchField/
# switchValue) whose valid combinations could not be expressed, and so were not
# checked; as one object the JSON Schema states the rule directly.
#
# ``byte_group`` (bit fields packed into shared bytes) needs no new term: it is
# expressed with the existing ``lorav:bitmask`` on events sharing a
# ``lorav:byteOffset`` (or ``lorav:tag``/group), exactly like a status byte.

SLOT: Final = "lorav:slot"  # 0-based order of an event within its group
PAD_BEFORE: Final = "lorav:padBefore"  # reserved bytes consumed before this field in its group

#: Condition gating whether this value appears in the payload at all.
PRESENT_WHEN: Final = "lorav:presentWhen"

#: Name of the value that decides the condition: a flags field (with ``bit``) or
#: a discriminator (with ``value``).
PW_FIELD: Final = "field"
#: Bit index in the flags field that must be set for this value to appear.
PW_BIT: Final = "bit"
#: Discriminator value selecting the match case this value belongs to.
PW_VALUE: Final = "value"

#: Name under which other blocks reference *this* value as ``$alias``, needed
#: when a ``match`` block's name for its discriminator differs from the event
#: name. Deliberately not a ``lorav:presentWhen`` sub-key: that object says what
#: gates a value, whereas this names a value others point at -- the opposite
#: role, and never true of the same event at the same time.
ALIAS: Final = "lorav:alias"

# --- Computed / derived-value terms ------------------------------------------
#
# Some values are not read directly off the wire but *derived* from other
# already-decoded values (e.g. a calibrated temperature from a raw count, or an
# albedo ratio). They occupy zero payload bytes and carry ``lorav:wireType``
# ``"number"`` plus a ``lorav:derived`` object. The reference interpreter
# evaluates them natively, so the binding carries the descriptors verbatim:
#
# * ``ref``        -- input value, a ``$name`` reference to another event.
# * ``polynomial`` -- coefficient list evaluated against the referenced input.
# * ``transform``  -- ordered post-processing ops (add/div/mult/round).
# * ``compute``    -- a binary op ``{op, a, b}`` over two values/constants.
# * ``guard``      -- conditional gate ``{when:[...], else: value}``.
#
# Grouping them under one term keeps "this value is computed, not read" a single
# observable fact rather than five independent flags that all had to be tested.
#
# Scalar scaling terms (``lorav:multiplier``/``lorav:divisor``/``lorav:addend``)
# may also apply to a computed value, exactly as for a raw field.

COMPUTED_TYPE: Final = "number"  # lorav:wireType value marking a derived value

#: Descriptor object marking a value as derived rather than read from the wire.
DERIVED: Final = "lorav:derived"

#: Keys a :data:`DERIVED` object may carry, in the order they are emitted into a
#: MultiTech field. Each maps onto the identically named MultiTech field key, so
#: the mapping needs no lookup table in either direction; only the order needs
#: stating, because the interpreter applies descriptors in field-key order.
DERIVED_ORDER: Final = ("ref", "polynomial", "compute", "guard", "transform")

#: Set form of :data:`DERIVED_ORDER`, for membership checks.
DERIVED_KEYS: Final = frozenset(DERIVED_ORDER)

# --- Thing-level OTAA activation / identity terms ----------------------------
#
# These describe how a device joins the network over the air (OTAA). DevEUI and
# JoinEUI are *identifiers* (not secrets) and may appear in the TD. The root keys
# AppKey (LoRaWAN 1.0.x and 1.1.x) and NwkKey (LoRaWAN 1.1.x only) are *secrets*
# and must never be stored as values in the TD: they are declared as ``apikey``
# security schemes (see APP_KEY_NAME / NWK_KEY_NAME) and injected at runtime.

DEV_EUI: Final = "lorav:devEUI"  # 8-byte device identifier, 16 hex chars
JOIN_EUI: Final = "lorav:joinEUI"  # 8-byte join/app identifier (formerly AppEUI)
MAC_VERSION: Final = "lorav:macVersion"  # LoRaWAN MAC version, e.g. "1.0.3", "1.1.0"

#: Conventional ``apikey`` scheme ``name`` for the OTAA AppKey root key.
APP_KEY_NAME: Final = "appKey"
#: Conventional ``apikey`` scheme ``name`` for the LoRaWAN 1.1.x NwkKey root key.
NWK_KEY_NAME: Final = "nwkKey"

# --- Thing-level onboarding / device-repository metadata ---------------------
#
# Descriptive metadata used when registering a device with a LoRaWAN Network
# Server (LNS). None of these are secrets. Brand, model and the hardware/software
# versions are deliberately *not* minted here: TD core and schema.org already
# express them (see :data:`REMOVED_TERMS`).

REGION: Final = "lorav:region"  # regulatory profile, e.g. "EU868", "US915"
FREQUENCY_PLAN: Final = "lorav:frequencyPlan"  # LNS frequency plan id

#: Companion vocabulary used for device metadata that is not LoRaWAN-specific.
SCHEMA_ORG_NS: Final = "https://schema.org/"
SCHEMA_ORG_PREFIX: Final = "schema"
BRAND: Final = "schema:brand"  # end-device brand / vendor
MODEL: Final = "schema:model"  # end-device model

# --- Withdrawn terms ---------------------------------------------------------

#: Terms this binding no longer defines, mapped to what replaces them.
#:
#: Two kinds appear here. Some were renamed because they shadowed a TD core term
#: and read as if they meant it (``lorav:type`` next to a data schema's ``type``).
#: The rest were withdrawn because TD core or a companion vocabulary already says
#: the same thing, and a binding that restates them only creates two places to
#: look and two ways to disagree.
#:
#: Kept in the code -- not just in the changelog -- so the converter can fail with
#: an actionable message naming the replacement, and so
#: ``scripts/vocab_usage_report.py`` can flag Thing Descriptions still using them.
REMOVED_TERMS: Final[dict[str, str]] = {
    # Renamed: shadowed a TD core term or a sibling binding term.
    "lorav:type": WIRE_TYPE,
    "lorav:offset": f"{ADDEND} (renamed to free the name from {BYTE_OFFSET})",
    "lorav:length": BYTE_LENGTH,
    # Consolidated into one object apiece.
    "lorav:presenceField": f"{PRESENT_WHEN}/{PW_FIELD}",
    "lorav:presenceBit": f"{PRESENT_WHEN}/{PW_BIT}",
    "lorav:switchField": f"{PRESENT_WHEN}/{PW_FIELD}",
    "lorav:switchValue": f"{PRESENT_WHEN}/{PW_VALUE}",
    "lorav:var": ALIAS,
    "lorav:ref": f"{DERIVED}/ref",
    "lorav:polynomial": f"{DERIVED}/polynomial",
    "lorav:transform": f"{DERIVED}/transform",
    "lorav:compute": f"{DERIVED}/compute",
    "lorav:guard": f"{DERIVED}/guard",
    # Withdrawn: TD core or a companion vocabulary already expresses this.
    "lorav:validRange": "the data schema's 'minimum' and 'maximum'",
    "lorav:enum": "the data schema's 'oneOf' with 'const' and 'title'",
    "lorav:unece": "the data schema's 'unit' (which already carries UN/CEFACT codes)",
    "lorav:brand": BRAND,
    "lorav:model": MODEL,
    "lorav:hardwareVersion": "the Thing's 'version/model'",
    "lorav:softwareVersion": "the Thing's 'version/instance'",
    "lorav:endDeviceId": "the Thing's 'id' or 'title'",
}

# --- Term registries ---------------------------------------------------------

#: Terms that belong on the Thing itself.
THING_TERMS: Final = frozenset(
    {
        PAYLOAD_LAYOUT,
        TAG_FIELDS,
        DEV_EUI,
        JOIN_EUI,
        MAC_VERSION,
        REGION,
        FREQUENCY_PLAN,
    }
)

#: Terms that belong on an event's form, where they locate the value in the
#: payload and describe how to turn its bytes into the value the data schema
#: declares. They sit on the form rather than in ``data`` for the same reason the
#: WoT Modbus binding puts ``modv:address`` there: they describe the transfer,
#: not the meaning.
FORM_TERMS: Final = frozenset(
    {
        FPORT,
        WIRE_TYPE,
        ENDIAN,
        BYTE_OFFSET,
        BYTE_LENGTH,
        TAG,
        SLOT,
        PAD_BEFORE,
        BITMASK,
        MULTIPLIER,
        DIVISOR,
        ADDEND,
        PRESENT_WHEN,
        ALIAS,
        DERIVED,
    }
)

#: Every term this binding defines. Registered explicitly rather than discovered
#: by introspecting this module, so that adding a constant without deciding where
#: it belongs is caught by the vocabulary artifact tests instead of silently
#: becoming part of the published vocabulary.
ALL_TERMS: Final = THING_TERMS | FORM_TERMS

#: Mapping from XML Schema data type names to MultiTech wire types. Only sized
#: types can be mapped unambiguously; ``xsd:integer``/``xsd:decimal`` are
#: intentionally absent because they do not define a byte width on the wire.
XSD_TO_WIRE: Final[dict[str, str]] = {
    "xsd:byte": "s8",
    "xsd:short": "s16",
    "xsd:int": "s32",
    "xsd:long": "s64",
    "xsd:unsignedByte": "u8",
    "xsd:unsignedShort": "u16",
    "xsd:unsignedInt": "u32",
    "xsd:unsignedLong": "u64",
    "xsd:float": "f32",
    "xsd:double": "f64",
    "xsd:boolean": "bool",
    "xsd:hexBinary": "hex",
    "xsd:string": "ascii",
}

#: Native MultiTech wire types that ``lorav:type`` may use directly (in addition
#: to the ``xsd:`` aliases above), so authors are not forced through XSD names.
NATIVE_WIRE_TYPES: Final = frozenset(
    {
        "u8",
        "u16",
        "u24",
        "u32",
        "u64",
        "s8",
        "s16",
        "s24",
        "s32",
        "s64",
        "f16",
        "f32",
        "f64",
        "bool",
        "ascii",
        "hex",
        "bytes",
        "base64",
    }
)


def resolve_wire_type(lorav_type: str) -> str:
    """Resolve a ``lorav:wireType`` value to a MultiTech native wire type.

    Accepts either an ``xsd:`` alias (e.g. ``xsd:short``) or a native wire type
    (e.g. ``s16``). Raises :class:`KeyError`-free :class:`ValueError` with an
    actionable message for unsized or unknown types.
    """
    if lorav_type in NATIVE_WIRE_TYPES:
        return lorav_type
    if lorav_type in XSD_TO_WIRE:
        return XSD_TO_WIRE[lorav_type]
    # xsd:integer / xsd:decimal have no fixed wire width -> guide the author.
    raise ValueError(
        f"Unsupported {WIRE_TYPE} value {lorav_type!r}. Use a sized type such as "
        f"'xsd:short'/'s16' or 'xsd:unsignedByte'/'u8'. Unsized XSD types like "
        f"'xsd:integer' and 'xsd:decimal' cannot be mapped to a byte width."
    )
