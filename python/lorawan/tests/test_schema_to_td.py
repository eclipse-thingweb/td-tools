"""Tests for the MultiTech payload schema -> Thing Description generator."""

from __future__ import annotations

import pytest

from lorawan_wot import vocab
from lorawan_wot.converter import td_to_payload_schema
from lorawan_wot.schema_to_td import (
    SkipReason,
    UnsupportedSchemaError,
    payload_schema_to_td,
)


def test_fixed_schema_assigns_sequential_byte_offsets():
    """Plain sequential fields get cumulative byte offsets and the right types."""
    schema = {
        "name": "demo_fixed",
        "endian": "big",
        "fields": [
            {"name": "count", "type": "u16"},
            {"name": "battery", "type": "u8", "div": 10, "unit": "V"},
            {"name": "temperature", "type": "s16", "div": 100, "unit": "Cel"},
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")

    assert td[vocab.PAYLOAD_LAYOUT] == vocab.LAYOUT_FIXED
    events = td[vocab.EVENTS]
    offsets = {name: ev[vocab.FORMS][0][vocab.BYTE_OFFSET] for name, ev in events.items()}
    assert offsets == {"count": 0, "battery": 2, "temperature": 3}
    assert events["battery"][vocab.DATA]["type"] == "number"  # div -> number
    assert events["count"][vocab.DATA]["type"] == "integer"


def test_every_event_form_subscribes_to_the_uplink():
    """Uplinks are pushed, so each form offers only the subscribe operations."""
    schema = {"endian": "big", "fields": [{"name": "count", "type": "u16"}]}
    form = payload_schema_to_td(schema, source="demo.yaml")[vocab.EVENTS]["count"][vocab.FORMS][0]
    assert form["href"] == vocab.UPLINK_HREF
    assert form["op"] == list(vocab.UPLINK_OPS)


def test_fixed_skip_advances_offset_without_an_event():
    """A ``skip`` field advances the cursor but creates no event."""
    schema = {
        "endian": "big",
        "fields": [
            {"name": "_hdr", "type": "skip", "length": 2},
            {"name": "value", "type": "u8"},
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    assert "_hdr" not in td[vocab.EVENTS]
    assert td[vocab.EVENTS]["value"][vocab.FORMS][0][vocab.BYTE_OFFSET] == 2


def test_schema_endian_is_recorded_on_each_form():
    """Byte order is a form-level term, so every value states its own."""
    schema = {
        "endian": "little",
        "fields": [
            {"name": "a", "type": "u16"},
            {"name": "b", "type": "u16"},
            {"name": "c", "type": "be_u16"},
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")

    assert vocab.ENDIAN not in td  # never a Thing-level term
    events = td[vocab.EVENTS]
    assert events["a"][vocab.FORMS][0][vocab.ENDIAN] == vocab.ENDIAN_LITTLE
    assert events["c"][vocab.FORMS][0][vocab.ENDIAN] == vocab.ENDIAN_BIG
    # Converting back rebuilds the schema-wide default and the odd-one-out prefix.
    round_tripped = td_to_payload_schema(td)
    assert round_tripped["endian"] == "little"
    assert [f["type"] for f in round_tripped["fields"]] == ["u16", "u16", "be_u16"]


def test_unit_round_trips_through_the_event_data_schema():
    """``unit`` describes the decoded value, so it belongs on ``data``."""
    schema = {
        "endian": "big",
        "fields": [{"name": "temperature", "type": "s16", "div": 10, "unit": "Cel"}],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")

    assert td[vocab.EVENTS]["temperature"][vocab.DATA]["unit"] == "Cel"
    assert td_to_payload_schema(td)["fields"][0]["unit"] == "Cel"


def test_valid_range_round_trips_as_minimum_and_maximum():
    """A plausibility range is stated with TD core's own data-schema keywords."""
    schema = {
        "endian": "big",
        "fields": [{"name": "temperature", "type": "s16", "valid_range": [-40, 85]}],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")

    data = td[vocab.EVENTS]["temperature"][vocab.DATA]
    assert (data["minimum"], data["maximum"]) == (-40, 85)
    assert td_to_payload_schema(td)["fields"][0]["valid_range"] == [-40, 85]


def test_tlv_schema_carries_tag_fields_and_tags():
    """A single-field tlv block becomes per-event tags plus tag fields."""
    schema = {
        "endian": "little",
        "fields": [
            {
                "tlv": {
                    "tag_fields": [
                        {"name": "channel_id", "type": "u8"},
                        {"name": "channel_type", "type": "u8"},
                    ],
                    "tag_key": ["channel_id", "channel_type"],
                    "cases": {
                        "[3, 103]": [{"name": "temperature", "type": "s16", "div": 10}],
                    },
                }
            }
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    assert td[vocab.PAYLOAD_LAYOUT] == vocab.LAYOUT_TLV
    assert td[vocab.TAG_FIELDS][0]["name"] == "channel_id"
    assert td[vocab.EVENTS]["temperature"][vocab.FORMS][0][vocab.TAG] == [3, 103]
    # And it round-trips through the forward converter.
    assert td_to_payload_schema(td)["fields"][0]["tlv"]["cases"]["[3, 103]"][0]["name"] == (
        "temperature"
    )


def test_lookup_enum_round_trips_to_strings():
    """A ``lookup`` table becomes a TD core ``oneOf`` and a string-typed event."""
    schema = {
        "endian": "big",
        "fields": [{"name": "hemi", "type": "u8", "lookup": {0: "N", 1: "S"}}],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    data = td[vocab.EVENTS]["hemi"][vocab.DATA]
    assert data["oneOf"] == [{"const": 0, "title": "N"}, {"const": 1, "title": "S"}]
    assert data["type"] == "string"
    assert td_to_payload_schema(td)["fields"][0]["lookup"] == {0: "N", 1: "S"}


def test_multi_field_tlv_case_becomes_slotted_events():
    """Several fields under one tag become slot-ordered events sharing the tag."""
    schema = {
        "endian": "little",
        "fields": [
            {
                "tlv": {
                    "tag_fields": [{"name": "ch", "type": "u8"}, {"name": "ty", "type": "u8"}],
                    "tag_key": ["ch", "ty"],
                    "cases": {
                        "[6, 101]": [
                            {"name": "illumination", "type": "u16"},
                            {"name": "infrared", "type": "u16"},
                        ],
                    },
                }
            }
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    illum = td[vocab.EVENTS]["illumination"][vocab.FORMS][0]
    infra = td[vocab.EVENTS]["infrared"][vocab.FORMS][0]
    assert illum[vocab.TAG] == [6, 101] and infra[vocab.TAG] == [6, 101]
    assert illum[vocab.SLOT] == 0 and infra[vocab.SLOT] == 1
    # The forward converter rebuilds the multi-field case in slot order.
    case = td_to_payload_schema(td)["fields"][0]["tlv"]["cases"]["[6, 101]"]
    assert [f["name"] for f in case] == ["illumination", "infrared"]


def test_flagged_groups_become_presence_gated_events():
    """Each flagged group field becomes an event gated by a flags bit."""
    schema = {
        "endian": "big",
        "fields": [
            {"name": "flags", "type": "u16"},
            {
                "flagged": {
                    "field": "flags",
                    "groups": [
                        {"bit": 0, "fields": [{"name": "moisture", "type": "u16", "div": 50}]},
                        {"bit": 1, "fields": [{"name": "battery", "type": "u16", "div": 1000}]},
                    ],
                }
            },
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    moisture = td[vocab.EVENTS]["moisture"][vocab.FORMS][0][vocab.PRESENT_WHEN]
    battery = td[vocab.EVENTS]["battery"][vocab.FORMS][0][vocab.PRESENT_WHEN]
    assert moisture == {vocab.PW_FIELD: "flags", vocab.PW_BIT: 0}
    assert battery[vocab.PW_BIT] == 1
    # And it rebuilds into a flagged block referencing the flags field.
    block = td_to_payload_schema(td)["fields"][1]["flagged"]
    assert block["field"] == "flags"
    assert {g["bit"] for g in block["groups"]} == {0, 1}


def test_match_cases_become_value_gated_events():
    """Each match case field becomes an event gated by a discriminator value."""
    schema = {
        "endian": "big",
        "fields": [
            {"name": "event", "type": "u8"},
            {
                "match": {
                    "field": "$event",
                    "cases": {
                        "0": [{"name": "reset_reason", "type": "u8"}],
                        "1": [{"name": "alarm_code", "type": "u8"}],
                    },
                }
            },
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    reset = td[vocab.EVENTS]["reset_reason"][vocab.FORMS][0][vocab.PRESENT_WHEN]
    assert reset == {vocab.PW_FIELD: "event", vocab.PW_VALUE: 0}
    block = td_to_payload_schema(td)["fields"][1]["match"]
    assert block["field"] == "$event"
    assert set(block["cases"]) == {0, 1}


def test_match_case_skip_padding_round_trips_via_pad_before():
    """Reserved bytes inside a match case survive as ``lorav:padBefore`` padding."""
    schema = {
        "endian": "big",
        "fields": [
            {"name": "event_type", "type": "u8", "var": "evt"},
            {
                "match": {
                    "field": "$evt",
                    "cases": {
                        "1": [
                            {"name": "flags", "type": "u8"},
                            {"name": "_reserved", "type": "skip", "length": 4},
                            {"name": "count", "type": "u16"},
                        ]
                    },
                }
            },
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    # The discriminator alias is preserved so the '$evt' reference still resolves.
    assert td[vocab.EVENTS]["event_type"][vocab.FORMS][0][vocab.ALIAS] == "evt"
    # The reserved bytes are recorded on the field that follows them.
    assert td[vocab.EVENTS]["count"][vocab.FORMS][0][vocab.PAD_BEFORE] == 4
    # Rebuilding restores the exact sequential case layout, padding included.
    rebuilt = td_to_payload_schema(td)
    case = rebuilt["fields"][1]["match"]["cases"][1]
    assert [(f.get("type")) for f in case] == ["u8", "skip", "u16"]
    assert case[1]["length"] == 4
    assert rebuilt["fields"][0]["var"] == "evt"


def test_byte_group_bitfields_become_masked_events():
    """``u8[lo:hi]`` byte_group fields become bitmasked events sharing a byte."""
    schema = {
        "endian": "big",
        "fields": [
            {
                "byte_group": {
                    "size": 1,
                    "fields": [
                        {"name": "lo", "type": "u8[0:3]"},
                        {"name": "hi", "type": "u8[4:7]"},
                    ],
                }
            },
            {"name": "tail", "type": "u8"},
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    lo = td[vocab.EVENTS]["lo"][vocab.FORMS][0]
    hi = td[vocab.EVENTS]["hi"][vocab.FORMS][0]
    assert lo[vocab.BYTE_OFFSET] == 0 and hi[vocab.BYTE_OFFSET] == 0
    assert lo[vocab.BITMASK] == "0x0F" and hi[vocab.BITMASK] == "0xF0"
    # The byte_group consumes one byte, so the trailing field sits at offset 1.
    assert td[vocab.EVENTS]["tail"][vocab.FORMS][0][vocab.BYTE_OFFSET] == 1


def test_tag_size_tlv_becomes_single_tag_tlv():
    """A ``tag_size`` tlv (no tag_fields, no length prefix) maps to a single-tag tlv."""
    schema = {
        "endian": "big",
        "fields": [
            {
                "tlv": {
                    "tag_size": 1,
                    "length_size": 0,
                    "cases": {
                        0x01: [{"name": "temperature", "type": "s16", "div": 10}],
                        0x03: [
                            {"name": "x", "type": "s8"},
                            {"name": "y", "type": "s8"},
                            {"name": "z", "type": "s8"},
                        ],
                    },
                }
            }
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    assert td[vocab.TAG_FIELDS] == [{"name": "tag", "type": "u8"}]
    assert td[vocab.EVENTS]["temperature"][vocab.FORMS][0][vocab.TAG] == [1]
    # The multi-field case keeps slot order when rebuilt.
    cases = td_to_payload_schema(td)["fields"][0]["tlv"]["cases"]
    assert [f["name"] for f in cases["[3]"]] == ["x", "y", "z"]


def test_computed_field_round_trips_with_ordered_scaling():
    """A derived ``ref`` field round-trips, preserving its mult/div/add order."""
    schema = {
        "endian": "big",
        "fields": [
            {"name": "raw", "type": "u8"},
            {
                "name": "temperature",
                "type": "number",
                "ref": "$raw",
                "add": -28.0,
                "div": 5.0,
                "unit": "Cel",
            },
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    form = td[vocab.EVENTS]["temperature"][vocab.FORMS][0]
    assert form[vocab.WIRE_TYPE] == vocab.COMPUTED_TYPE
    assert form[vocab.DERIVED] == {"ref": "$raw"}
    # The derived value occupies no payload bytes (shares the raw field's offset).
    assert form[vocab.BYTE_OFFSET] == 1
    rebuilt = td_to_payload_schema(td)["fields"][1]
    assert rebuilt["type"] == "number" and rebuilt["ref"] == "$raw"
    # add must precede div so the interpreter computes (raw + add) / div.
    keys = [k for k in rebuilt if k in ("add", "div")]
    assert keys == ["add", "div"]


def test_computed_field_in_tlv_case_round_trips():
    """A derived field sharing a tlv tag round-trips as a computed event."""
    schema = {
        "endian": "big",
        "fields": [
            {
                "tlv": {
                    "tag_fields": [{"name": "ch", "type": "u8"}, {"name": "ty", "type": "u8"}],
                    "tag_key": ["ch", "ty"],
                    "cases": {
                        "[3, 103]": [
                            {"name": "temp_raw", "type": "u16"},
                            {
                                "name": "temperature",
                                "type": "number",
                                "ref": "$temp_raw",
                                "div": 10.0,
                            },
                        ],
                    },
                }
            }
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    computed = td[vocab.EVENTS]["temperature"][vocab.FORMS][0]
    assert computed[vocab.WIRE_TYPE] == vocab.COMPUTED_TYPE
    assert computed[vocab.DERIVED] == {"ref": "$temp_raw"}
    assert computed[vocab.TAG] == [3, 103] and computed[vocab.SLOT] == 1
    # The forward converter rebuilds the raw + derived pair under the shared tag.
    case = td_to_payload_schema(td)["fields"][0]["tlv"]["cases"]["[3, 103]"]
    assert [f["name"] for f in case] == ["temp_raw", "temperature"]
    assert case[1]["type"] == "number" and case[1]["ref"] == "$temp_raw"


def test_multibyte_byte_group_bitfields_round_trip():
    """A 3-byte ``byte_group`` with ``u24[lo:hi]`` ranges round-trips faithfully."""
    schema = {
        "endian": "big",
        "fields": [
            {
                "byte_group": {
                    "size": 3,
                    "fields": [
                        {"name": "temp_raw", "type": "u24[4:23]"},
                        {"name": "humi_raw", "type": "u24[0:11]"},
                    ],
                }
            },
            {"name": "tail", "type": "u8"},
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    temp = td[vocab.EVENTS]["temp_raw"][vocab.FORMS][0]
    humi = td[vocab.EVENTS]["humi_raw"][vocab.FORMS][0]
    assert temp[vocab.WIRE_TYPE] == "u24" and temp[vocab.BITMASK] == "0xFFFFF0"
    assert humi[vocab.BITMASK] == "0x000FFF"
    # The 3-byte group consumes three bytes, so the trailing field sits at offset 3.
    assert td[vocab.EVENTS]["tail"][vocab.FORMS][0][vocab.BYTE_OFFSET] == 3
    # Rebuilding emits multi-byte bit ranges; only the last member consumes the group.
    rebuilt = td_to_payload_schema(td)["fields"]
    bitrange = [f for f in rebuilt if "[" in str(f.get("type", ""))]
    assert {f["type"] for f in bitrange} == {"u24[4:23]", "u24[0:11]"}
    assert sum(f.get("consume", 0) for f in bitrange) == 3


def test_recurring_tlv_name_becomes_multiform_event():
    """A field name reused across tlv cases becomes one event with two forms."""
    schema = {
        "endian": "little",
        "fields": [
            {
                "tlv": {
                    "tag_fields": [
                        {"name": "channel_id", "type": "u8"},
                        {"name": "channel_type", "type": "u8"},
                    ],
                    "cases": {
                        "[3, 103]": [{"name": "temperature", "type": "s16", "div": 10}],
                        "[131, 103]": [
                            {"name": "temperature", "type": "s16", "div": 10},
                            {"name": "temperature_alarm", "type": "u8"},
                        ],
                    },
                }
            }
        ],
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    forms = td[vocab.EVENTS]["temperature"][vocab.FORMS]
    assert len(forms) == 2
    assert {tuple(f[vocab.TAG]) for f in forms} == {(3, 103), (131, 103)}
    # It must rebuild into both original cases, including the paired alarm field.
    cases = td_to_payload_schema(td)["fields"][0]["tlv"]["cases"]
    assert set(cases) == {"[3, 103]", "[131, 103]"}
    assert [f["name"] for f in cases["[131, 103]"]] == ["temperature", "temperature_alarm"]


@pytest.mark.parametrize(
    ("schema", "needle", "reason"),
    [
        (
            {"ports": {1: {"fields": []}}},
            "no 'fields'",
            SkipReason.MALFORMED,
        ),
        (
            {"fields": [{"type": "u8"}]},
            "named scalar fields",
            SkipReason.MIXED_FIELD_SHAPE,
        ),
        (
            {
                "fields": [
                    {
                        "tlv": {
                            "tag_fields": [{"name": "t", "type": "u8"}],
                            "cases": {
                                "1": [
                                    {"name": "dup", "type": "u8"},
                                    {"name": "dup", "type": "u8"},
                                ],
                            },
                        }
                    }
                ]
            },
            "duplicate",
            SkipReason.DUPLICATE_NAME,
        ),
        (
            {"fields": [{"name": "x", "type": "number", "formula": "y * 2"}]},
            "computed",
            SkipReason.COMPUTED,
        ),
        (
            {"fields": [{"name": "x", "type": "number", "value": 42}]},
            "computed",
            SkipReason.COMPUTED,
        ),
        (
            {
                "fields": [
                    {"name": "evt", "type": "u8"},
                    {
                        "match": {
                            "field": "$evt",
                            "cases": {
                                "0": [
                                    {"name": "a", "type": "u8"},
                                    {"name": "_pad", "type": "skip", "length": 2},
                                ]
                            },
                        }
                    },
                ]
            },
            "trailing skip padding",
            SkipReason.SKIP_IN_MATCH,
        ),
    ],
)
def test_unsupported_shapes_raise(schema, needle, reason):
    """Out-of-subset schema shapes raise a descriptive error, not bad output."""
    with pytest.raises(UnsupportedSchemaError) as exc:
        payload_schema_to_td(schema, source="demo.yaml")
    assert needle in str(exc.value)
    assert exc.value.reason is reason


def test_ports_layout_tags_each_form_with_its_fport():
    """A ``ports`` schema yields per-fPort forms, sharing names across ports."""
    schema = {
        "endian": "little",
        "ports": {
            1: {"fields": [{"name": "battery", "type": "u8"}]},
            4: {
                "fields": [
                    {"name": "battery", "type": "u8"},
                    {"name": "speed", "type": "u16"},
                ]
            },
        },
    }
    td = payload_schema_to_td(schema, source="demo.yaml")
    assert td[vocab.PAYLOAD_LAYOUT] == vocab.LAYOUT_PORTS
    # 'battery' is reported on both ports -> one event, two fPort-tagged forms.
    battery_forms = td[vocab.EVENTS]["battery"][vocab.FORMS]
    assert {f[vocab.FPORT] for f in battery_forms} == {1, 4}
    assert td[vocab.EVENTS]["speed"][vocab.FORMS][0][vocab.FPORT] == 4
    # It must rebuild into the original per-port field map.
    rebuilt = td_to_payload_schema(td)
    assert set(rebuilt["ports"]) == {1, 4}
    assert [f["name"] for f in rebuilt["ports"][4]["fields"]] == ["battery", "speed"]
