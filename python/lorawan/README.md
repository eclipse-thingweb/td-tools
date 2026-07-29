# LoRaWAN binding for WoT Thing Descriptions

This project lets you describe a LoRaWAN sensor with a **W3C Web of Things (WoT)
Thing Description (TD)** and automatically turn it into a working **payload
codec**. We have validated the generated codec in ChirpStack to decode uplink payloads into JSON values. It should also work in The Things Network (TTN).

The TD carries the payload binding *inside its property forms* (using
`lorav:` terms). A converter translates that TD into the
[LoRa Alliance Payload Schema / MultiTech](https://github.com/MultiTechSystems/device-payload-schema)
language, and the reference interpreter does the actual byte decoding.

```
Thing Description (.td.json)
        │   lorav: terms on each property form
        ▼
  td_to_payload_schema()        ← this project
        │   MultiTech payload schema (YAML/dict)
        ▼
  Referenced SchemaInterpreter   ← pinned git submodule
        │
        ▼
  Decoded values  { "temperature": 28.3, ... }
```

## Why this design?

* **One source of truth** – the TD holds both the WoT abstraction *and* the
  payload binding.
* **No reinvented codec** – decoding is delegated to the referenced interpreter.
* **Real layouts** – supports fixed binary layouts, per-`fPort` layouts, and
  channel/type/value or type/length/value (TLV) payloads.

## Requirements

* [uv](https://docs.astral.sh/uv/) (Python project & environment manager)
* Python 3.11+

## Setup

```bash
# 1. Get the LoRa Alliance Payload / MultiTech interpreter (pinned submodule)
git submodule update --init --recursive

# 2. Create the environment and install dependencies
uv sync
```

## Project layout

```
src/lorawan_wot/
  vocab.py        # binding terms + xsd->wire type mapping (single source of truth)
  converter.py    # TD  ->  LoRa Alliance Payload / MultiTech payload schema
  schema_to_td.py # MultiTech payload schema  ->  TD (reverse of converter)
  decode.py       # drive the MultiTech interpreter from a TD + payload
  cli.py          # `lorawan-wot convert | decode | generate`
vocab/
  ontology.ttl            # RDF vocabulary
  context.jsonld          # JSON-LD context for the lorav: namespace
  lorawan-form.schema.json  # JSON Schema for LoRaWAN property forms
  lorawan-thing.schema.json  # JSON Schema for Thing-level OTAA / onboarding terms
examples/         # curated TD examples + vectors + generated artifacts
  devices/        # TD catalog generated from the reference device schemas
  generated/      # output folder for generated schema/codec artifacts
scripts/
  generate_device_tds.py  # batch-generate the examples/devices/ catalog
tests/            # converter, decode, schema-validation, and catalog tests
external/device-payload-schema/   # MultiTech interpreter (pinned git submodule)
```

## Usage

### Convert a Thing Description into a payload schema

```bash
uv run lorawan-wot convert examples/milesight-am102.td.json
# write to a file instead of stdout:
uv run lorawan-wot convert examples/milesight-am102.td.json -o am102.schema.yaml
```

### Decode an uplink payload

```bash
uv run lorawan-wot decode examples/dragino-lht65n.td.json 0B450A8C02DD010A1E --fport 2
# -> {
#      "batteryVoltage": 2.885,
#      "temperature": 27.0,
#      "humidity": 73.3,
#      "extensionCode": 1,
#      "pollMessageStatus": 0,
#      "retransmissionStatus": 0
#    }
```

For a `ports` layout, don't forget to pass the frame port:


### Use it from Python

```python
import json
import yaml
from lorawan_wot import payload_schema_to_td, td_to_payload_schema
from lorawan_wot.decode import decode_uplink

td = json.load(open("examples/milesight-am102.td.json"))

schema = td_to_payload_schema(td)            # TD  -> MultiTech schema (dict)
data = decode_uplink(td, "01755A03671B01046850")
print(data)  # {'battery': 90, 'temperature': 28.3, 'humidity': 40.0}

# The reverse direction: MultiTech schema -> Thing Description.
source = yaml.safe_load(open("external/device-payload-schema/schemas/devices/makerfabs/ath20.yaml"))
generated_td = payload_schema_to_td(source, source="ath20.yaml")
```

For production code, prefer context managers (`with open(...)`) and explicit
`encoding="utf-8"` when reading files.

### Generate a Thing Description from a payload schema

The reverse of `convert`: turn an existing MultiTech / LoRa Alliance payload
schema into a starter Thing Description.

```bash
uv run lorawan-wot generate external/device-payload-schema/schemas/devices/makerfabs/ath20.yaml -o examples/devices/makerfabs/ath20.td.json
```

This is how to generat a bundled [device catalog](#device-catalog).


## Generate a ChirpStack / TTN JavaScript codec

The reference MultiTech schema produced from a TD can be turned into a self-contained
`decodeUplink(input)` JavaScript codec (for ChirpStack / TTN).

**Quick rule**
1. Use `generate_ts013_codec.py` by default.
2. Use `generate_js_decoder.py` only for simple `fixed` schemas with top-level `fields` and no `fPort` dispatch.

| Layout | Generator | Output file |
|--------|-----------|-------------|
| `fixed` only, **no** `ports`/`tlv`/`ctv` branching | `generate_js_decoder.py` | `*_decoder.js` |
| `ports`, `tlv` / `ctv` (fPort dispatch, channel/tag cases, `flagged`, `match`, `enum`) | `generate_ts013_codec.py` | `*_codec.js` |

**Important notes**
- `generate_js_decoder.py` does not support top-level `ports`.
- `generate_ts013_codec.py` supports `ports`/`tlv`/`match`, but can still have edge-case gaps (see [Known limitations](#known-limitations)).
- `lorawan-wot decode` uses the Python reference interpreter (`SchemaInterpreter`); generated JS behavior can differ in unsupported edge cases.
- It does **not** call `generate_ts013_codec.py` or `generate_js_decoder.py`.
- Use those generator scripts only when you need a standalone JavaScript codec file.

### Ports + match layout (e.g. Netvox R718A)

```bash
# TD -> schema
uv run lorawan-wot convert examples/netvox-r718a.td.json -o examples/generated/netvox-r718a.schema.yaml

# schema -> JS codec
uv run python external/device-payload-schema/tools/generate_ts013_codec.py examples/generated/netvox-r718a.schema.yaml -o examples/generated
# -> examples/generated/netvox_r718a.schema_codec.js
```

This is the recommended path for `ports` and `match` devices.

### TLV / channel layout (e.g. Milesight EM300-ZLD)

```bash
# TD -> schema
uv run lorawan-wot convert examples/em300-zld.td.json -o examples/generated/em300-zld.schema.yaml

# schema -> JS codec
uv run python external/device-payload-schema/tools/generate_ts013_codec.py examples/generated/em300-zld.schema.yaml -o examples/generated
# -> examples/generated/em300_zld.schema_codec.js
```

Paste the generated `*_decoder.js` / `*_codec.js` into **ChirpStack → Device
profile → Codec → JavaScript functions** (or the equivalent TTN payload
formatter).



## How to describe a device in a TD

Add the binding namespace to `@context`, set a Thing-level layout, and put a
field descriptor on each property's form.

```jsonc
{
  "@context": [
    "https://www.w3.org/2022/wot/td/v1.1",
    { "lorav": "https://www.w3.org/2024/wot/lorawan#" }
  ],
  "lorav:payloadLayout": "fixed",          // fixed | ports | tlv | ctv
  "properties": {
    "temperature": {
      "type": "number",
      "unit": "Cel",
      "forms": [
        {
          "href": "uplink",
          "lorav:byteOffset": 2,            // where in the payload
          "lorav:type": "xsd:short",        // wire data type
          "lorav:mostSignificantByte": true,
          "lorav:multiplier": 0.01          // raw * 0.01
        }
      ]
    }
  }
}
```

### Payload layouts

| `lorav:payloadLayout` | When to use | Required per-property terms |
|-----------------------|-------------|-----------------------------|
| `fixed` | Every value sits at a fixed byte position | `lorav:byteOffset` |
| `ports` | The LoRaWAN `fPort` selects a fixed layout | `lorav:fPort`, `lorav:byteOffset` |
| `tlv` / `ctv` | Values are tagged (e.g. channel + type) | `lorav:tag` |

For `tlv`/`ctv` you may declare the tag fields at Thing level with
`lorav:tagFields` (defaults to `channel` + `type`, both `u8`).

### Form vocabulary (`lorav:` terms)
| Term | Meaning | Maps to (MultiTech) |
|------|---------|---------------------|
| `lorav:type` | Wire data type (xsd alias or native, e.g. `xsd:short`, `s16`) | `type` |
| `lorav:mostSignificantByte` | `true` = big-endian, `false` = little-endian | `endian` |
| `lorav:multiplier` | `value = raw * multiplier` | `mult` |
| `lorav:divisor` | `value = raw / divisor` | `div` |
| `lorav:offset` | `value = value + offset` (after scaling) | `add` |
| `lorav:bitmask` | Extract a contiguous bit range (single- or multi-byte base) | bit range `u8[lo:hi]` |
| `lorav:byteOffset` | Byte position in a fixed layout | field order / `skip` padding |
| `lorav:fPort` | LoRaWAN frame port | `ports` key |
| `lorav:tag` | Tag selecting a value, e.g. `[3, 103]` | `tlv` case key |
| `lorav:length` | Byte length for `bytes`/`string`/`hex` (`-1` = consume rest) | `length` |
| `lorav:unece` | UN/CEFACT unit code | `unece` |
| `lorav:enum` | Map raw integers to labels | `values` |
| `lorav:slot` | Order of a property within its group (multi-field TLV / flagged / match) | field order |
| `lorav:presenceField` | Name of the bit-flags property that gates this property | `flagged.field` |
| `lorav:presenceBit` | Bit index in `presenceField` that must be set for this property to appear | `flagged.groups[*].bit` |
| `lorav:switchField` | Name of the discriminator property that selects this property's case | `match.field` |
| `lorav:switchValue` | Value of `switchField` under which this property appears | `match.cases` key |
| `lorav:var` | Discriminator alias, referenced as `$var` when the `match` field name differs from the property name | `var` |
| `lorav:padBefore` | Reserved bytes consumed before this property within its group | `skip` inside a case |
| `lorav:ref` | Input value a computed property derives from, as `$name` | `ref` |
| `lorav:polynomial` | Coefficient list evaluated as `c0 + c1*x + c2*x² + …` | `polynomial` |
| `lorav:transform` | Ordered post-processing ops (`add`/`div`/`mult`) applied to a derived value | `transform` |
| `lorav:compute` | Binary operation `{op, a, b}` combining two values | `compute` |
| `lorav:guard` | Conditional gate `{when, else}` selecting a derived value | `guard` |

Supported `lorav:type` values: the sized XSD types (`xsd:byte`, `xsd:short`,
`xsd:int`, `xsd:long`, the `xsd:unsigned*` variants, `xsd:float`, `xsd:double`,
`xsd:boolean`, `xsd:hexBinary`, `xsd:string`) and the native MultiTech types
(`u8`–`u64`, `s8`–`s64`, `f16`/`f32`/`f64`, `bool`, `ascii`, `hex`, `bytes`,
`base64`).

> **Note on bitmasks:** `lorav:bitmask` extracts a contiguous bit range from an
> unsigned base value. Several properties may share one byte (or wider word) by
> each giving a `lorav:bitmask` at the same `lorav:byteOffset` (e.g. a status
> byte with a flag in bit 7 and a value in bits 0-6) — the base value is read
> once and decoded into each property. Multi-byte bases (`u16`/`u24`/`u32`) are
> supported for bit ranges that span more than one byte.

### Conditional and grouped payloads

Use these when one payload contains optional or alternative branches:

* **Flagged** (`presenceField` + `presenceBit`) — decode a group only when a flag bit is set.
* **Match/switch** (`switchField` + `switchValue`) — decode one case selected by a discriminator.
* **Byte group** — decode several bitfields from one shared byte/word.
* **Multi-field TLV case** — same `tag`, ordered by `slot`.
* **Computed field** (`lorav:type: number`) — derived from other fields via `ref`/`polynomial`/`transform`/`compute`/`guard`, consumes no bytes.

## Device onboarding & OTAA security

For OTAA, keep identifiers in the TD and keep root keys out of the TD.

* **Identifiers** (`lorav:devEUI`, `lorav:joinEUI`) are not secrets and live
  directly in the TD.
* **Root keys** (`AppKey`, and `NwkKey` for LoRaWAN 1.1.x) are secrets. Declare
  them as WoT `apikey` security schemes (`name: "appKey"` / `name: "nwkKey"`).
  Inject actual values at runtime; do not store them in the TD.

### LoRaWAN 1.0.x (AppKey only)

```jsonc
{
  "securityDefinitions": {
    "otaa_sc": { "scheme": "apikey", "in": "uri", "name": "appKey" }
  },
  "security": "otaa_sc",

  "lorav:endDeviceId": "dragino-lht65n-01",
  "lorav:devEUI": "A84041B98D5CB233",
  "lorav:joinEUI": "0000000000000000",
  "lorav:macVersion": "1.0.3",
  "lorav:brand": "Dragino",
  "lorav:model": "LHT65N",
  "lorav:hardwareVersion": "1.0",
  "lorav:softwareVersion": "1.4",
  "lorav:region": "EU868",
  "lorav:frequencyPlan": "EU_863_870_TTN"
}
```

### LoRaWAN 1.1.x (AppKey **and** NwkKey)

Version 1.1.x uses two root keys, so declare two `apikey` schemes and require both:

```jsonc
{
  "securityDefinitions": {
    "appkey_sc": { "scheme": "apikey", "in": "uri", "name": "appKey" },
    "nwkkey_sc": { "scheme": "apikey", "in": "uri", "name": "nwkKey" }
  },
  "security": ["appkey_sc", "nwkkey_sc"],

  "lorav:macVersion": "1.1.0",
  "lorav:devEUI": "70B3D57ED0050001",
  "lorav:joinEUI": "0000000000000001"
}
```

### Thing-level vocabulary

| Term | Meaning | Secret? |
|------|---------|---------|
| `lorav:devEUI` | 8-byte device identifier (16 hex chars) | no |
| `lorav:joinEUI` | 8-byte join/app identifier (formerly AppEUI) | no |
| `lorav:macVersion` | LoRaWAN MAC version, e.g. `1.0.3`, `1.1.0` | no |
| `lorav:endDeviceId` | Human/LNS end-device identifier | no |
| `lorav:brand` | End-device brand / vendor | no |
| `lorav:model` | End-device model | no |
| `lorav:hardwareVersion` | Hardware revision | no |
| `lorav:softwareVersion` | Firmware / software version | no |
| `lorav:region` | Regulatory region / profile (e.g. `EU868`) | no |
| `lorav:frequencyPlan` | LNS frequency plan id (e.g. `EU_863_870_TTN`) | no |
| `AppKey` | OTAA root key — `apikey` scheme `name: "appKey"` | **yes (runtime)** |
| `NwkKey` | OTAA network root key (1.1.x) — `apikey` scheme `name: "nwkKey"` | **yes (runtime)** |

## Examples

The repository ships **6 curated example pairs** (`*.td.json` + `*.vectors.json`)
in `examples/`:

| File | Layout | Highlights |
|------|--------|-----------|
| `examples/adeunis-comfort2.td.json` | `fixed` | Compact fixed layout with signed temperature + humidity scaling and battery percentage. |
| `examples/milesight-am102.td.json` | `ctv` | Channel/type/value, signed scaling, little-endian; OTAA AppKey (1.0.3) |
| `examples/dragino-lht65n.td.json` | `ports` | fPort-aware LHT65N example: fPort 2 status bits + basic battery/temperature/humidity, and fPort 5 device-info/battery; OTAA AppKey (1.0.3). Extension-specific alternate paths are documented gaps. |
| `examples/em300-zld.td.json` | `ctv` | Milesight channel/type payload with leak state + battery from tagged uplinks. |
| `examples/generic-lorawan11.td.json` | `fixed` | LoRaWAN 1.1 OTAA with AppKey **and** NwkKey; onboarding metadata |
| `examples/netvox-r718a.td.json` | `ports` | Real device validated against `TheThingsNetwork/lorawan-devices` reference vectors; fPort 6 (`match` on reportType: startup version report vs. status report with a shared status byte) and fPort 7 (`match` on commandId: config-report responses) |

Each example has a matching `*.vectors.json` file with known payloads and their
expected decoded values, used by the tests.

### Device catalog

`examples/devices/<vendor>/<model>.td.json` holds Thing Descriptions generated
straight from the reference schemas in the `device-payload-schema` submodule with
`lorawan-wot generate`. Regenerate the whole catalog with:

```bash
uv run python -m scripts.generate_device_tds
```

Validation is in `tests/test_device_catalog.py`: TD round-trip must preserve
decode structure, and TD-based decoding must match source schema decoding.

Coverage summary for the current reference set (158 schemas): **157 generated,
1 skipped**.

| Category | Status |
|----------|--------|
| `fixed`, `ports`, TLV (`single` + `multi-field`) | ✅ |
| `flagged`, `match`, `byte_group` | ✅ |
| computed (`ref`/`polynomial`/`transform`) | ✅ |
| mixed unsupported shape (`hbi/mla20`) | ⏭️ skipped |

The single remaining skip is legitimate, not a regression:

| Reason | Count | Why it can't round-trip |
|--------|------:|-------------------------|
| Mixed / unsupported field shape (`hbi/mla20`) | 1 | A fixed header followed by a length-prefixed TLV whose case nests a `byte_group` — a shape the bundled reference interpreter itself mis-decodes (it emits a bogus `unknown` field), and which ships no test vectors, so no faithful TD can be produced |

`scripts/generate_device_tds.py` prints this per-reason report each run.




## Development

```bash
uv run pytest          # run the test suite
uv run ruff check .    # lint
uv run ruff format .   # format
```

## Scope & roadmap

* **Now:** uplink decoding (sensor properties and events); generating
  ChirpStack/TTN JavaScript codecs for non-branching `fixed` uplinks
  (`generate_js_decoder.py`) and for `ports`/`tlv`/`ctv` layouts
  (`generate_ts013_codec.py`); and generating Thing Descriptions from the
  reference device schemas for `fixed`, `ports`, single- and multi-field `tlv`,
  and the conditional `flagged` / `match` / `byte_group` shapes (the
  [device catalog](#device-catalog)).
* **Later:** downlink / actions (write/invoke); `formula`/`value`-style computed
  fields; per-`fPort`/command-branched codec generation; and additional payload
  layouts.

### Known limitations

The binding covers most common fixed/ports/TLV layouts, but these gaps remain:

* **Arrays / nested object payloads** — dynamic `repeat` structures and object/array
  field values are not representable as flat TD properties.
* **Some computed-field shapes** — structured computed descriptors
  (`ref`/`polynomial`/`transform`/`compute`/`guard`) are supported, but legacy
  raw-form expressions (for example `formula`/literal-only `value` forms in
  source schemas) are not converted.
* **TLV variants outside `tag_fields` style** — `tag_size`/length-prefixed TLV
  forms and some non-standard tag-key encodings are not converted.
* **Match defaults and some mixed case internals** — explicit integer
  `match` cases are supported, but wildcard/default cases and certain embedded
  constructs (for example raw `skip` entries inside a case in source schemas)
  are not.
* **Frame-code dispatch nuance** — top-level frame-byte dispatch is supported
  when modeled as explicit enumerated `match` cases; open-ended default branches
  are still a gap.
* **Dragino-style alternate source branches** — when one logical output field
  switches to a different byte source under extension/status flags (`Ext`-style
  branching), only the stable/common path is modeled; branch-specific alternates
  are documented as gaps.
* **TS013 JS generator shared-byte gap** — `generate_ts013_codec.py` can drop
  bare bit-range fields and fail to advance the cursor correctly in those cases.
  This affects generated JavaScript only. The Python reference decode path
  (`lorawan-wot decode`) remains correct.

