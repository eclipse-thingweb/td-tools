"""Tests for the Thing Description -> MultiTech payload schema converter."""

from __future__ import annotations

import copy

import pytest

from lorawan_wot.converter import ConversionError, td_to_payload_schema


def test_tlv_layout_builds_tag_cases(am102_td):
    """A ctv/tlv TD becomes a single tlv block keyed by each property's tag."""
    schema = td_to_payload_schema(am102_td)

    assert schema["endian"] == "little"
    assert schema["direction"] == "uplink"

    tlv = schema["fields"][0]["tlv"]
    assert tlv["tag_key"] == ["channel_id", "channel_type"]
    # Each property lands in a case keyed by the string form of its tag array.
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
    assert sorted(ports.keys()) == [2, 5]
    port2_names = [field["name"] for field in ports[2]["fields"]]
    assert port2_names == [
        "batteryVoltage",
        "temperature",
        "humidity",
        "extensionCode",
        "pollMessageStatus",
        "retransmissionStatus",
    ]
    assert [field["name"] for field in ports[5]["fields"]] == [
        "sensorModelCode",
        "_pad_1",
        "frequencyBandCode",
        "subBandCode",
        "deviceInfoBatteryVoltage",
    ]


def test_fixed_layout_inserts_padding_for_gaps():
    """A gap between byte offsets is filled with a skip field."""
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "a": {"forms": [{"lorav:byteOffset": 0, "lorav:type": "u8"}]},
            "b": {"forms": [{"lorav:byteOffset": 3, "lorav:type": "u8"}]},
        },
    }
    fields = td_to_payload_schema(td)["fields"]
    assert [f.get("type") for f in fields] == ["u8", "skip", "u8"]
    assert fields[1]["length"] == 2  # bytes 1 and 2 are reserved


def test_fixed_layout_skips_leading_header_bytes():
    """A payload header before the first field becomes leading skip padding."""
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "value": {"forms": [{"lorav:byteOffset": 3, "lorav:type": "u8"}]},
        },
    }
    fields = td_to_payload_schema(td)["fields"]
    assert fields[0]["type"] == "skip"
    assert fields[0]["length"] == 3  # header bytes 0..2 are skipped
    assert fields[1]["name"] == "value"


def test_enum_becomes_decodable_lookup_table():
    """``lorav:enum`` maps to a ``lookup`` table (which the interpreter applies).

    The reference interpreter only honours ``values`` on dedicated ``type: enum``
    fields; on a plain field a categorical mapping must use ``lookup``. JSON object
    keys arrive as strings and must be coerced back to ints for integer indexing.
    """
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "hemisphere": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:type": "u8",
                        "lorav:enum": {"0": "N", "1": "S"},
                    }
                ]
            },
        },
    }
    field = td_to_payload_schema(td)["fields"][0]
    assert "values" not in field
    assert field["lookup"] == {0: "N", 1: "S"}


def test_ports_layout_groups_by_fport():
    """A ports TD groups properties under their frame port."""
    td = {
        "lorav:payloadLayout": "ports",
        "properties": {
            "a": {"forms": [{"lorav:fPort": 1, "lorav:byteOffset": 0, "lorav:type": "u8"}]},
            "b": {"forms": [{"lorav:fPort": 2, "lorav:byteOffset": 0, "lorav:type": "u16"}]},
        },
    }
    ports = td_to_payload_schema(td)["ports"]
    assert set(ports) == {1, 2}
    assert ports[1]["fields"][0]["name"] == "a"
    assert ports[2]["fields"][0]["type"] == "u16"


def test_scaling_terms_map_to_mult_div_add():
    """multiplier/divisor/offset map onto mult/div/add."""
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "v": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:type": "u16",
                        "lorav:multiplier": 2,
                        "lorav:divisor": 10,
                        "lorav:offset": -5,
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
        td_to_payload_schema({"properties": {}})


def test_unknown_layout_raises():
    with pytest.raises(ConversionError, match="Unsupported"):
        td_to_payload_schema({"lorav:payloadLayout": "weird", "properties": {}})


def test_missing_type_raises():
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {"a": {"forms": [{"lorav:byteOffset": 0, "lorav:fPort": 1}]}},
    }
    with pytest.raises(ConversionError, match="lorav:type"):
        td_to_payload_schema(td)


def test_unsized_xsd_type_raises():
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {"a": {"forms": [{"lorav:byteOffset": 0, "lorav:type": "xsd:integer"}]}},
    }
    with pytest.raises(ConversionError, match="sized type"):
        td_to_payload_schema(td)


def test_multibyte_bitmask_emits_bit_range():
    """A bitmask over a multi-byte unsigned base emits a ``uN[lo:hi]`` bit range."""
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "a": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:type": "xsd:unsignedShort",
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
        "properties": {
            "a": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:type": "s16",
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
        "properties": {
            "a": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:type": "u8",
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
        "properties": {"a": {"forms": [{"lorav:type": "u8"}]}},
    }
    with pytest.raises(ConversionError, match="byteOffset"):
        td_to_payload_schema(td)


def test_overlapping_offsets_raise():
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "a": {"forms": [{"lorav:byteOffset": 0, "lorav:type": "u16"}]},
            "b": {"forms": [{"lorav:byteOffset": 1, "lorav:type": "u8"}]},
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
    """Two masked properties on one byte read it once; only the last consumes."""
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "voltage": {
                "forms": [
                    {
                        "lorav:byteOffset": 0,
                        "lorav:type": "u8",
                        "lorav:bitmask": "0x7F",
                        "lorav:divisor": 10,
                    }
                ]
            },
            "lowBattery": {
                "forms": [{"lorav:byteOffset": 0, "lorav:type": "u8", "lorav:bitmask": "0x80"}]
            },
            "next": {"forms": [{"lorav:byteOffset": 1, "lorav:type": "u8"}]},
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
    """A property sharing a byte without a bitmask is an error, not an overlap."""
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "flag": {
                "forms": [{"lorav:byteOffset": 0, "lorav:type": "u8", "lorav:bitmask": "0x80"}]
            },
            "whole": {"forms": [{"lorav:byteOffset": 0, "lorav:type": "u8"}]},
        },
    }
    with pytest.raises(ConversionError, match="bitmask"):
        td_to_payload_schema(td)


def test_flagged_members_become_a_flagged_block():
    """Properties carrying presence terms assemble into a trailing flagged block."""
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "flags": {"forms": [{"lorav:byteOffset": 0, "lorav:type": "u16"}]},
            "moisture": {
                "forms": [
                    {
                        "lorav:presenceField": "flags",
                        "lorav:presenceBit": 0,
                        "lorav:type": "u16",
                        "lorav:divisor": 50,
                    }
                ]
            },
            "battery": {
                "forms": [
                    {"lorav:presenceField": "flags", "lorav:presenceBit": 1, "lorav:type": "u16"}
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
    """Properties carrying switch terms assemble into a trailing match block."""
    td = {
        "lorav:payloadLayout": "fixed",
        "properties": {
            "event": {"forms": [{"lorav:byteOffset": 0, "lorav:type": "u8"}]},
            "reset_reason": {
                "forms": [
                    {"lorav:switchField": "event", "lorav:switchValue": 0, "lorav:type": "u8"}
                ]
            },
            "alarm_code": {
                "forms": [
                    {"lorav:switchField": "event", "lorav:switchValue": 1, "lorav:type": "u8"}
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
        "properties": {
            "event": {"forms": [{"lorav:byteOffset": 0, "lorav:type": "u8"}]},
            "volt": {
                "forms": [
                    {
                        "lorav:switchField": "event",
                        "lorav:switchValue": 1,
                        "lorav:slot": 0,
                        "lorav:byteOffset": 1,
                        "lorav:type": "u8",
                        "lorav:bitmask": "0x7F",
                    }
                ]
            },
            "lowBattery": {
                "forms": [
                    {
                        "lorav:switchField": "event",
                        "lorav:switchValue": 1,
                        "lorav:slot": 1,
                        "lorav:byteOffset": 1,
                        "lorav:type": "u8",
                        "lorav:bitmask": "0x80",
                    }
                ]
            },
            "next_byte": {
                "forms": [
                    {
                        "lorav:switchField": "event",
                        "lorav:switchValue": 1,
                        "lorav:slot": 2,
                        "lorav:type": "u8",
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
        "properties": {
            "event": {"forms": [{"lorav:fPort": 6, "lorav:byteOffset": 0, "lorav:type": "u8"}]},
            "reset_reason": {
                "forms": [
                    {
                        "lorav:fPort": 6,
                        "lorav:switchField": "event",
                        "lorav:switchValue": 0,
                        "lorav:type": "u8",
                    }
                ]
            },
            "other_port_field": {
                "forms": [{"lorav:fPort": 7, "lorav:byteOffset": 0, "lorav:type": "u8"}]
            },
        },
    }
    ports = td_to_payload_schema(td)["ports"]
    port6_fields = ports[6]["fields"]
    assert port6_fields[0]["name"] == "event"
    assert port6_fields[1]["match"]["cases"][0][0]["name"] == "reset_reason"
    assert ports[7]["fields"][0]["name"] == "other_port_field"
