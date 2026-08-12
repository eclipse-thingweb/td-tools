"""LoRaWAN WoT binding vocabulary.

This module is the single source of truth for the LoRaWAN binding terms used in
Thing Descriptions and for the mapping between those terms and the MultiTech /
LoRa Alliance Payload Schema language.

Two namespaces are involved:

* ``lorav:`` -- the LoRaWAN binding vocabulary (this project). Terms appear on a
  Thing (``lorav:payloadLayout``) and on individual property *forms*
  (``lorav:fPort``, ``lorav:type``, ``lorav:multiplier`` ...).
* ``xsd:``  -- XML Schema data types, reused by ``lorav:type`` to name the wire
  data type of a value, following the published LoRaWAN binding draft.
"""

from __future__ import annotations

from typing import Final

#: JSON-LD namespace IRI for the LoRaWAN binding vocabulary.
LORAWAN_NS: Final = "https://www.w3.org/2024/wot/lorawan#"
#: Prefix used for the binding vocabulary inside Thing Descriptions.
LORAWAN_PREFIX: Final = "lorav"

# --- Thing-level term --------------------------------------------------------

#: Term naming the overall payload layout of a device. It tells the converter
#: how to assemble the per-property field descriptors into one payload schema.
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

FPORT: Final = "lorav:fPort"  # LoRaWAN frame port (routing / branching)
TYPE: Final = "lorav:type"  # wire data type (xsd:* alias or native)
MSB: Final = "lorav:mostSignificantByte"  # True => big-endian
MULTIPLIER: Final = "lorav:multiplier"  # raw * multiplier
DIVISOR: Final = "lorav:divisor"  # raw / divisor
OFFSET: Final = "lorav:offset"  # value + offset (after scaling)
BITMASK: Final = "lorav:bitmask"  # hex mask, e.g. "0x3FFF"
BYTE_OFFSET: Final = "lorav:byteOffset"  # fixed-layout position (bytes)
LENGTH: Final = "lorav:length"  # byte length for string/bytes/hex
TAG: Final = "lorav:tag"  # tlv/ctv case selector, e.g. [3, 103]
UNECE: Final = "lorav:unece"  # UN/CEFACT unit code, e.g. "CEL"
ENUM: Final = "lorav:enum"  # categorical mapping {int: str}
VALID_RANGE: Final = "lorav:validRange"  # [min, max] plausibility range -> quality flag

# --- Grouping / conditional-presence terms -----------------------------------
#
# Some devices pack several values into one addressable unit, or include a value
# only conditionally. These terms let independent WoT properties describe such a
# shared structure without abandoning the "one property = one value" model:
#
# * multi-field TLV -- several properties share one ``lorav:tag`` and are ordered
#   by ``lorav:slot`` (e.g. a light channel reporting illumination + infrared).
# * ``flagged``     -- a property is present only when a bit of a named flags
#   property is set (``lorav:presenceField`` + ``lorav:presenceBit``).
# * ``match``       -- a property belongs to the case selected when a named
#   discriminator property equals a value (``lorav:switchField`` +
#   ``lorav:switchValue``); ordered within the case by ``lorav:slot``.
#
# ``byte_group`` (bit fields packed into shared bytes) needs no new term: it is
# expressed with the existing ``lorav:bitmask`` on properties sharing a
# ``lorav:byteOffset`` (or ``lorav:tag``/group), exactly like a status byte.

SLOT: Final = "lorav:slot"  # 0-based order of a property within its group
PRESENCE_FIELD: Final = "lorav:presenceField"  # name of the flags property
PRESENCE_BIT: Final = "lorav:presenceBit"  # flags bit gating this property
SWITCH_FIELD: Final = "lorav:switchField"  # name of the discriminator property
SWITCH_VALUE: Final = "lorav:switchValue"  # discriminator value selecting this case
CONST: Final = "lorav:const"  # fixed byte value used when encoding a downlink
VAR: Final = "lorav:var"  # discriminator alias, referenced as $var by a match block
PAD_BEFORE: Final = "lorav:padBefore"  # reserved bytes consumed before this field in its group

# --- Computed / derived-value terms ------------------------------------------
#
# Some properties are not read directly off the wire but *derived* from other
# already-decoded values (e.g. a calibrated temperature from a raw count, or an
# albedo ratio). They occupy zero payload bytes and carry ``lorav:type``
# ``"number"`` plus one or more of the descriptors below. The reference
# interpreter evaluates them natively, so the binding carries them verbatim:
#
# * ``lorav:ref``        -- input value, a ``$name`` reference to another property.
# * ``lorav:polynomial`` -- coefficient list evaluated against the referenced input.
# * ``lorav:transform``  -- ordered post-processing ops (add/div/mult/round).
# * ``lorav:compute``    -- a binary op ``{op, a, b}`` over two values/constants.
# * ``lorav:guard``      -- conditional gate ``{when:[...], else: value}``.
#
# Scalar scaling terms (``lorav:multiplier``/``lorav:divisor``/``lorav:offset``)
# may also apply to a computed value, exactly as for a raw field.

COMPUTED_TYPE: Final = "number"  # lorav:type value marking a derived value
REF: Final = "lorav:ref"  # $name of the input value
POLYNOMIAL: Final = "lorav:polynomial"  # coefficient list (c0 + c1*x + ...)
TRANSFORM: Final = "lorav:transform"  # ordered post-processing ops
COMPUTE: Final = "lorav:compute"  # binary op {op, a, b}
GUARD: Final = "lorav:guard"  # conditional gate {when, else}

#: Form terms that mark a property as a computed/derived value.
COMPUTED_TERMS: Final = frozenset({REF, POLYNOMIAL, TRANSFORM, COMPUTE, GUARD})

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
# Server (LNS). None of these are secrets.

BRAND: Final = "lorav:brand"  # end-device brand / vendor
MODEL: Final = "lorav:model"  # end-device model
HARDWARE_VERSION: Final = "lorav:hardwareVersion"  # hardware revision
SOFTWARE_VERSION: Final = "lorav:softwareVersion"  # firmware / software version
REGION: Final = "lorav:region"  # regulatory profile, e.g. "EU868", "US915"
FREQUENCY_PLAN: Final = "lorav:frequencyPlan"  # LNS frequency plan id
END_DEVICE_ID: Final = "lorav:endDeviceId"  # human/LNS end-device identifier

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
    """Resolve a ``lorav:type`` value to a MultiTech native wire type.

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
        f"Unsupported {TYPE} value {lorav_type!r}. Use a sized type such as "
        f"'xsd:short'/'s16' or 'xsd:unsignedByte'/'u8'. Unsized XSD types like "
        f"'xsd:integer' and 'xsd:decimal' cannot be mapped to a byte width."
    )
