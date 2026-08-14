"""Tests for the Thing Description -> MultiTech payload schema converter."""

from __future__ import annotations

import copy

import pytest

from lorawan_wot import vocab
from lorawan_wot.converter import ConversionError, td_to_payload_schema


def test_tlv_layout_builds_tag_cases(am102_td):
    """A ctv/tlv TD becomes a single tlv block keyed by each event's tag."""
    schema = td_to_payload_schema(am102_td)

    assert schema["endian"] == "little"
    assert schema["direction"] == "uplink"

    tlv = schema["fields"][0]["tlv"]
    assert tlv["tag_key"] == ["channel_id", "channel_type"]
    # Each event lands in a case keyed by the string form of its tag array.
    assert tlv["cases"]["[3, 103]"][0] == {
        "name": "temperature",
        "type": "s16",
        "div": 10,
        "unit": "Cel",
    }
    assert tlv["cases"]["[1, 117]"][0]["name"] == "battery"


def test_dragino_example_uses_ports_layout_for_basic_fport_coverage(lht65n_td):
    """The Dragino example models fPort-separated uplinks (`ports` layout)."""
    schema = td_to_payload_schema(lht65n_td)

    assert schema["endian"] == "big"
    ports = schema["ports"]
    assert sorted(ports.keys()) == [2]
    port2_names = [field["name"] for field in ports[2]["fields"]]
    assert port2_names == [
        "batteryVoltage",
        "temperature",
        "humidity",
        "extensionCode",
        "pollMessageStatus",
        "retransmissionStatus",
    ]


def _endian_td(*form_endians: str | None) -> dict:
    """Build a fixed TD with one ``u16`` event per given form byte order."""
    events = {}
    for index, endian in enumerate(form_endians):
        form: dict = {"lorav:byteOffset": index * 2, "lorav:wireType": "u16"}
        if endian is not None:
            form["lorav:endian"] = endian
        events[f"p{index}"] = {"forms": [form]}
    return {"lorav:payloadLayout": "fixed", "events": events}


def test_endian_defaults_to_big_when_undeclared():
    """With no byte order on any form, the LoRaWAN default (big-endian) applies."""
    schema = td_to_payload_schema(_endian_td(None))
    assert schema["endian"] == "big"
    assert schema["fields"][0]["type"] == "u16"  # no prefix needed


def test_majority_form_endian_becomes_the_schema_default():
    """The most common per-form byte order becomes the schema-wide default."""
    schema = td_to_payload_schema(_endian_td("little", "little", "big"))
    assert schema["endian"] == "little"
    # Only the field that disagrees with the default needs a prefix.
    assert [f["type"] for f in schema["fields"]] == ["u16", "u16", "be_u16"]


def test_thing_level_endian_is_rejected():
    """Byte order is a form-level term; on the Thing it would be silently lost."""
    td = _endian_td("little")
    td["lorav:endian"] = "little"
    with pytest.raises(ConversionError, match="form-level"):
        td_to_payload_schema(td)


def test_invalid_endian_is_rejected():
    """Any byte order other than 'big' or 'little' is a conversion error."""
    with pytest.raises(ConversionError, match="endian"):
        td_to_payload_schema(_endian_td("msb"))


def test_withdrawn_property_shape_is_rejected_with_a_migration_hint():
    """A pre-events Thing Description must fail loudly, not decode silently.

    Uplinks are pushed by the device and cannot be polled, so values moved from
    ``properties`` to ``events``. Accepting the old shape would mean guessing at
    a data schema that is no longer where the binding looks for it.
    """
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "a": {"forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u8"}]},
        },
    }
    with pytest.raises(ConversionError, match="events"):
        td_to_payload_schema(td)


@pytest.mark.parametrize("term", sorted(vocab.REMOVED_TERMS))
def test_withdrawn_term_is_rejected_with_its_replacement_named(term):
    """Every withdrawn term names what replaced it, wherever it appears."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "a": {"forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u8", term: "x"}]},
        },
    }
    with pytest.raises(ConversionError, match=vocab.REMOVED_TERMS[term].split()[0]):
        td_to_payload_schema(td)


def test_fixed_layout_inserts_padding_for_gaps():
    """A gap between byte offsets is filled with a skip field."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "a": {"forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u8"}]},
            "b": {"forms": [{"lorav:byteOffset": 3, "lorav:wireType": "u8"}]},
        },
    }
    fields = td_to_payload_schema(td)["fields"]
    assert [f.get("type") for f in fields] == ["u8", "skip", "u8"]
    assert fields[1]["length"] == 2  # bytes 1 and 2 are reserved


def test_fixed_layout_skips_leading_header_bytes():
    """A payload header before the first field becomes leading skip padding."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "value": {"forms": [{"lorav:byteOffset": 3, "lorav:wireType": "u8"}]},
        },
    }
    fields = td_to_payload_schema(td)["fields"]
    assert fields[0]["type"] == "skip"
    assert fields[0]["length"] == 3  # header bytes 0..2 are skipped
    assert fields[1]["name"] == "value"


def test_one_of_becomes_decodable_lookup_table():
    """A ``oneOf`` of ``const``/``title`` maps to a ``lookup`` table.

    The categorical mapping is stated with TD core's own data-schema terms rather
    than a binding term of our own. The reference interpreter only honours
    ``values`` on dedicated ``type: enum`` fields, so on a plain field it must be
    emitted as ``lookup``.
    """
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "hemisphere": {
                "data": {
                    "type": "integer",
                    "oneOf": [
                        {"const": 0, "title": "N"},
                        {"const": 1, "title": "S"},
                    ],
                },
                "forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u8"}],
            },
        },
    }
    field = td_to_payload_schema(td)["fields"][0]
    assert "values" not in field
    assert field["lookup"] == {0: "N", 1: "S"}


def test_minimum_and_maximum_become_a_valid_range():
    """TD core's ``minimum``/``maximum`` carry the plausibility range."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "temperature": {
                "data": {"type": "number", "minimum": -40, "maximum": 85},
                "forms": [{"lorav:byteOffset": 0, "lorav:wireType": "s16"}],
            },
        },
    }
    assert td_to_payload_schema(td)["fields"][0]["valid_range"] == [-40, 85]


def test_unit_is_read_from_the_event_data_schema():
    """The unit belongs to the decoded value, so it lives on ``data``."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "temperature": {
                "data": {"type": "number", "unit": "Cel"},
                "forms": [{"lorav:byteOffset": 0, "lorav:wireType": "s16"}],
            },
        },
    }
    assert td_to_payload_schema(td)["fields"][0]["unit"] == "Cel"


def test_ports_layout_groups_by_fport():
    """A ports TD groups events under their frame port."""
    td = {
        "lorav:payloadLayout": "ports",
        "events": {
            "a": {"forms": [{"lorav:fPort": 1, "lorav:byteOffset": 0, "lorav:wireType": "u8"}]},
            "b": {"forms": [{"lorav:fPort": 2, "lorav:byteOffset": 0, "lorav:wireType": "u16"}]},
        },
    }
    ports = td_to_payload_schema(td)["ports"]
    assert set(ports) == {1, 2}
    assert ports[1]["fields"][0]["name"] == "a"
    assert ports[2]["fields"][0]["type"] == "u16"


def test_scaling_terms_map_to_mult_div_add():
    """multiplier/divisor/addend map onto mult/div/add."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "v": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:wireType": "u16",
                        "lorav:multiplier": 2,
                        "lorav:divisor": 10,
                        "lorav:addend": -5,
                    }
                ]
            }
        },
    }
    field = td_to_payload_schema(td)["fields"][0]
    assert field["mult"] == 2
    assert field["div"] == 10
    assert field["add"] == -5


def test_missing_layout_raises():
    with pytest.raises(ConversionError, match="payloadLayout"):
        td_to_payload_schema({"events": {}})


def test_unknown_layout_raises():
    with pytest.raises(ConversionError, match="Unsupported"):
        td_to_payload_schema({"lorav:payloadLayout": "weird", "events": {}})


def test_missing_type_raises():
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {"a": {"forms": [{"lorav:byteOffset": 0, "lorav:fPort": 1}]}},
    }
    with pytest.raises(ConversionError, match="lorav:wireType"):
        td_to_payload_schema(td)


def test_unsized_xsd_type_raises():
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {"a": {"forms": [{"lorav:byteOffset": 0, "lorav:wireType": "xsd:integer"}]}},
    }
    with pytest.raises(ConversionError, match="sized type"):
        td_to_payload_schema(td)


def test_multibyte_bitmask_emits_bit_range():
    """A bitmask over a multi-byte unsigned base emits a ``uN[lo:hi]`` bit range."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "a": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:wireType": "xsd:unsignedShort",
                        "lorav:bitmask": "0x3FFF",
                    }
                ]
            }
        },
    }
    field = td_to_payload_schema(td)["fields"][0]
    assert field["type"] == "u16[0:13]"
    assert field["consume"] == 2


def test_bitmask_on_signed_type_raises():
    """A bitmask is only valid on unsigned base types."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "a": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:wireType": "s16",
                        "lorav:bitmask": "0x3FFF",
                    }
                ]
            }
        },
    }
    with pytest.raises(ConversionError, match="unsigned"):
        td_to_payload_schema(td)


def test_noncontiguous_bitmask_raises():
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "a": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:wireType": "u8",
                        "lorav:bitmask": "0x05",
                    }
                ]
            }
        },
    }
    with pytest.raises(ConversionError, match="non-contiguous"):
        td_to_payload_schema(td)


def test_fixed_layout_requires_byte_offset():
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {"a": {"forms": [{"lorav:wireType": "u8"}]}},
    }
    with pytest.raises(ConversionError, match="byteOffset"):
        td_to_payload_schema(td)


def test_overlapping_offsets_raise():
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "a": {"forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u16"}]},
            "b": {"forms": [{"lorav:byteOffset": 1, "lorav:wireType": "u8"}]},
        },
    }
    with pytest.raises(ConversionError, match="overlaps"):
        td_to_payload_schema(td)


def test_input_td_is_not_mutated(am102_td):
    """Conversion must not modify the caller's Thing Description."""
    original = copy.deepcopy(am102_td)
    td_to_payload_schema(am102_td)
    assert am102_td == original


def test_shared_byte_bitfields_consume_once():
    """Two masked events on one byte read it once; only the last consumes."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "voltage": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:wireType": "u8",
                        "lorav:bitmask": "0x7F",
                        "lorav:divisor": 10,
                    }
                ]
            },
            "lowBattery": {
                "forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u8", "lorav:bitmask": "0x80"}]
            },
            "next": {"forms": [{"lorav:byteOffset": 1, "lorav:wireType": "u8"}]},
        },
    }
    fields = td_to_payload_schema(td)["fields"]
    by_name = {f["name"]: f for f in fields}
    # Ordered by lowest selected bit: voltage (bits 0-6) then lowBattery (bit 7).
    assert by_name["voltage"]["type"] == "u8[0:6]"
    assert by_name["voltage"]["consume"] == 0
    assert by_name["lowBattery"]["type"] == "u8[7:7]"
    assert by_name["lowBattery"]["consume"] == 1
    # The shared byte advances the cursor by one, so 'next' is not padded over.
    assert "_pad_1" not in by_name
    assert by_name["next"]["type"] == "u8"


def test_shared_byte_requires_bitmask_on_all_members():
    """An event sharing a byte without a bitmask is an error, not an overlap."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "flag": {
                "forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u8", "lorav:bitmask": "0x80"}]
            },
            "whole": {"forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u8"}]},
        },
    }
    with pytest.raises(ConversionError, match="bitmask"):
        td_to_payload_schema(td)


def test_flagged_members_become_a_flagged_block():
    """Events gated by a flag bit assemble into a trailing flagged block."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "flags": {"forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u16"}]},
            "moisture": {
                "forms": [
                    {
                        "lorav:presentWhen": {"field": "flags", "bit": 0},
                        "lorav:wireType": "u16",
                        "lorav:divisor": 50,
                    }
                ]
            },
            "battery": {
                "forms": [
                    {
                        "lorav:presentWhen": {"field": "flags", "bit": 1},
                        "lorav:wireType": "u16",
                    }
                ]
            },
        },
    }
    fields = td_to_payload_schema(td)["fields"]
    # Structural flags field first, then the flagged block.
    assert fields[0]["name"] == "flags"
    block = fields[1]["flagged"]
    assert block["field"] == "flags"
    bits = {g["bit"]: [f["name"] for f in g["fields"]] for g in block["groups"]}
    assert bits == {0: ["moisture"], 1: ["battery"]}


def test_match_members_become_a_match_block():
    """Events gated by a discriminator value assemble into a trailing match block."""
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "event": {"forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u8"}]},
            "reset_reason": {
                "forms": [
                    {
                        "lorav:presentWhen": {"field": "event", "value": 0},
                        "lorav:wireType": "u8",
                    }
                ]
            },
            "alarm_code": {
                "forms": [
                    {
                        "lorav:presentWhen": {"field": "event", "value": 1},
                        "lorav:wireType": "u8",
                    }
                ]
            },
        },
    }
    fields = td_to_payload_schema(td)["fields"]
    assert fields[0]["name"] == "event"
    block = fields[1]["match"]
    assert block["field"] == "$event"
    assert {v: [f["name"] for f in cf] for v, cf in block["cases"].items()} == {
        0: ["reset_reason"],
        1: ["alarm_code"],
    }


def test_match_case_members_sharing_a_byte_offset_use_shared_byte():
    """Two bitmask members in the same match case share one byte's `consume`.

    Regression test for the bug where `_assemble_match` emitted `consume` for
    every masked member independently, double-advancing the cursor.
    """
    td = {
        "lorav:payloadLayout": "fixed",
        "events": {
            "event": {"forms": [{"lorav:byteOffset": 0, "lorav:wireType": "u8"}]},
            "volt": {
                "forms": [
                    {
                        "lorav:presentWhen": {"field": "event", "value": 1},
                        "lorav:slot": 0,
                        "lorav:byteOffset": 1,
                        "lorav:wireType": "u8",
                        "lorav:bitmask": "0x7F",
                    }
                ]
            },
            "lowBattery": {
                "forms": [
                    {
                        "lorav:presentWhen": {"field": "event", "value": 1},
                        "lorav:slot": 1,
                        "lorav:byteOffset": 1,
                        "lorav:wireType": "u8",
                        "lorav:bitmask": "0x80",
                    }
                ]
            },
            "next_byte": {
                "forms": [
                    {
                        "lorav:presentWhen": {"field": "event", "value": 1},
                        "lorav:slot": 2,
                        "lorav:wireType": "u8",
                    }
                ]
            },
        },
    }
    case = td_to_payload_schema(td)["fields"][1]["match"]["cases"][1]
    assert [f["name"] for f in case] == ["volt", "lowBattery", "next_byte"]
    # Only the last member of the shared byte may advance the cursor.
    assert case[0]["consume"] == 0
    assert case[1]["consume"] == 1


def test_ports_layout_supports_a_match_block_per_port():
    """`ports` fields route through the same structural/flagged/match assembly
    as the top-level `fixed` layout (regression test for `_assemble_ports`
    previously bypassing that partitioning entirely).
    """
    td = {
        "lorav:payloadLayout": "ports",
        "events": {
            "event": {"forms": [{"lorav:fPort": 6, "lorav:byteOffset": 0, "lorav:wireType": "u8"}]},
            "reset_reason": {
                "forms": [
                    {
                        "lorav:fPort": 6,
                        "lorav:presentWhen": {"field": "event", "value": 0},
                        "lorav:wireType": "u8",
                    }
                ]
            },
            "other_port_field": {
                "forms": [{"lorav:fPort": 7, "lorav:byteOffset": 0, "lorav:wireType": "u8"}]
            },
        },
    }
    ports = td_to_payload_schema(td)["ports"]
    port6_fields = ports[6]["fields"]
    assert port6_fields[0]["name"] == "event"
    assert port6_fields[1]["match"]["cases"][0][0]["name"] == "reset_reason"
    assert ports[7]["fields"][0]["name"] == "other_port_field"
