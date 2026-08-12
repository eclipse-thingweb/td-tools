# LoRaWAN binding for WoT Thing Descriptions

Describe a LoRaWAN sensor once as a **W3C Web of Things (WoT) Thing Description
(TD)** and get a working **payload codec** out of it. The generated codec is
validated against ChirpStack; it should also work in The Things Network (TTN).

The TD carries the payload binding *inside its property forms* (using
terms prefixed with `lorav:`). A converter translates that TD into the
[LoRa Alliance Payload Schema / MultiTech](https://github.com/MultiTechSystems/device-payload-schema)
language, and the reference interpreter (e.g. ChirpStack) does the actual byte decoding.

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

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

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

`--fport` is required for a `ports` layout, because the frame port selects which
layout to apply. Other layouts ignore it.

### Use it from Python

```python
import json

import yaml

from lorawan_wot import payload_schema_to_td, td_to_payload_schema
from lorawan_wot.decode import decode_uplink

with open("examples/milesight-am102.td.json", encoding="utf-8") as fp:
    td = json.load(fp)

schema = td_to_payload_schema(td)  # TD -> MultiTech schema (dict)
print(decode_uplink(td, "01755A03671B01046850"))
# {'battery': 90, 'temperature': 28.3, 'humidity': 40.0}

# The reverse direction: MultiTech schema -> Thing Description.
source_path = "external/device-payload-schema/schemas/devices/makerfabs/ath20.yaml"
with open(source_path, encoding="utf-8") as fp:
    generated_td = payload_schema_to_td(yaml.safe_load(fp), source="ath20.yaml")
```

### Generate a Thing Description from a payload schema

The reverse of `convert`: turn an existing LoRa Alliance / MultiTech payload
schema into a starter Thing Description.

```bash
uv run lorawan-wot generate external/device-payload-schema/schemas/devices/makerfabs/ath20.yaml -o examples/devices/makerfabs/ath20.td.json
```

This is how the bundled [device catalog](#device-catalog) is produced.

## Generate a ChirpStack / TTN JavaScript codec

`lorawan-wot decode` uses the Python reference interpreter. To run a codec inside
a network server instead, feed the converted schema to one of the two generator
scripts shipped by the submodule:

| Your schema | Generator | Output |
|-------------|-----------|--------|
| `fixed` only, **no** `ports`/`tlv`/`ctv` branching | `generate_js_decoder.py` | `*_decoder.js` |
| Everything else (`ports`, `tlv`/`ctv`, `flagged`, `match`, `enum`) | `generate_ts013_codec.py` | `*_codec.js` |

When in doubt, use `generate_ts013_codec.py`.

```bash
# 1. TD -> schema
uv run lorawan-wot convert examples/netvox-r718a.td.json -o examples/generated/netvox-r718a.schema.yaml

# 2. schema -> JS codec
uv run python external/device-payload-schema/tools/generate_ts013_codec.py
  examples/generated/netvox-r718a.schema.yaml -o examples/generated
# -> examples/generated/netvox_r718a.schema_codec.js
```

Paste the generated file into **ChirpStack → Device profile → Codec → JavaScript
functions** (or the equivalent TTN payload formatter). The generated JavaScript
can differ from `lorawan-wot decode` in unsupported edge cases; see
[Known limitations](#known-limitations).

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
          "lorav:endian": "big",            // big (default) | little
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

The **Tier** column shows how often each term appears across the bundled
[device catalog](#device-catalog): **core** is needed by almost every device,
**common** by a recognisable class of them, and **rare** by only a few.
The rare terms exist because the reference schemas model real vendor payloads,
so you can ignore them until a device needs one.

| Term | Meaning | MultiTech | Tier | Seen in |
|------|---------|-----------|------|---------|
| `lorav:type` | Wire data type (xsd alias or native, e.g. `xsd:short`, `s16`) | `type` | core | every device |
| `lorav:endian` | Byte order of this multi-byte value, `"big"` (default) or `"little"` | `endian` | core | every multi-byte value |
| `lorav:byteOffset` | Byte position in a fixed layout | field order / `skip` padding | core | `fixed` + `ports` devices |
| `lorav:tag` | Tag selecting a value, e.g. `[3, 103]` | `tlv` case key | core | Milesight, Elsys |
| `lorav:fPort` | LoRaWAN frame port | `ports` key | core | `ports` devices (e.g. Digital Matter) |
| `lorav:divisor` | `value = raw / divisor` | `div` | core | most vendors |
| `lorav:multiplier` | `value = raw * multiplier` | `mult` | common | Decentlab, Digital Matter, MClimate |
| `lorav:bitmask` | Extract a contiguous bit range (single- or multi-byte base) | bit range `u8[lo:hi]` | common | Dragino, Digital Matter, MClimate, RadioBridge, RAKwireless |
| `lorav:offset` | `value = value + offset` (after scaling) | `add` | common | Decentlab, MClimate, RadioBridge |
| `lorav:slot` | Order of a property within its group (multi-field TLV / flagged / match) | field order | common | any multi-value group |
| `lorav:enum` | Map raw integers to labels | `lookup` | common | Makerfabs, MClimate, RadioBridge |
| `lorav:presenceField` | Name of the bit-flags property that gates this property | `flagged.field` | common | Decentlab |
| `lorav:presenceBit` | Bit index in `presenceField` that must be set for this property to appear | `flagged.groups[*].bit` | common | Decentlab |
| `lorav:switchField` | Name of the discriminator property that selects this property's case | `match.field` | common | Dragino, Netvox, RadioBridge, Radionode |
| `lorav:switchValue` | Value of `switchField` under which this property appears | `match.cases` key | common | Dragino, Netvox, RadioBridge, Radionode |
| `lorav:validRange` | `[min, max]` plausibility range for the decoded value | `valid_range` | rare | MClimate |
| `lorav:ref` | Input value a computed property derives from, as `$name` | `ref` | rare | Decentlab, Digital Matter, MClimate |
| `lorav:compute` | Binary operation `{op, a, b}` combining two values | `compute` | rare | Decentlab, MClimate |
| `lorav:transform` | Ordered post-processing ops (`add`/`div`/`mult`) applied to a derived value | `transform` | rare | Decentlab, MClimate |
| `lorav:guard` | Conditional gate `{when, else}` selecting a derived value | `guard` | rare | Decentlab, MClimate |
| `lorav:var` | Discriminator alias, referenced as `$var` when the `match` field name differs from the property name | `var` | rare | RadioBridge, Radionode |
| `lorav:length` | Byte length for `bytes`/`string`/`hex` (`-1` = consume rest) | `length` | rare | RadioBridge |
| `lorav:padBefore` | Reserved bytes consumed before this property within its group | `skip` inside a case | rare | RadioBridge |
| `lorav:polynomial` | Coefficient list evaluated as `c0 + c1*x + c2*x² + …` | `polynomial` | rare | Decentlab DL-5TM |
| `lorav:unece` | UN/CEFACT unit code | `unece` | rare | none yet (see [Known limitations](#known-limitations)) |

Supported `lorav:type` values: the sized XSD types (`xsd:byte`, `xsd:short`,
`xsd:int`, `xsd:long`, the `xsd:unsigned*` variants, `xsd:float`, `xsd:double`,
`xsd:boolean`, `xsd:hexBinary`, `xsd:string`) and the native MultiTech types
(`u8`–`u64`, `s8`–`s64`, `f16`/`f32`/`f64`, `bool`, `ascii`, `hex`, `bytes`,
`base64`).

### Grouped and conditional values

One property always describes one value. Payloads that pack values together or
branch between them are expressed by giving several properties the same locator:

| Shape | How to express it |
|-------|-------------------|
| Several values share one byte or word | Same `lorav:byteOffset`, one `lorav:bitmask` each |
| Several values share one tag | Same `lorav:tag`, ordered by `lorav:slot` |
| A value appears only when a flag bit is set | `lorav:presenceField` + `lorav:presenceBit` |
| A value belongs to one branch of a discriminator | `lorav:switchField` + `lorav:switchValue` |
| A value is derived rather than read from the wire | `lorav:type: "number"` + `ref`/`polynomial`/`transform`/`compute`/`guard` |

`lorav:bitmask` must select a *contiguous* range of bits. The base value is read
once and decoded into every property masking it, and bases wider than one byte
(`u16`/`u24`/`u32`) work too, for ranges spanning several bytes.

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

  "lorav:devEUI": "A84041B98D5CB233",
  "lorav:joinEUI": "0000000000000000",
  "lorav:macVersion": "1.0.3"
  // plus the optional onboarding terms listed below
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
| `lorav:payloadLayout` | Payload structure: `fixed`, `ports`, `tlv` or `ctv` | no |
| `lorav:tagFields` | Tag field definitions for `tlv`/`ctv` layouts | no |
| `AppKey` | OTAA root key — `apikey` scheme `name: "appKey"` | **yes (runtime)** |
| `NwkKey` | OTAA network root key (1.1.x) — `apikey` scheme `name: "nwkKey"` | **yes (runtime)** |

## Examples

The repository ships **6 curated example pairs** (`*.td.json` + `*.vectors.json`)
in `examples/`:

| File | Layout | Highlights |
|------|--------|-----------|
| `examples/adeunis-comfort2.td.json` | `fixed` | Smallest complete example: signed temperature, humidity, battery |
| `examples/milesight-am102.td.json` | `ctv` | Little-endian channel/type/value; OTAA AppKey (1.0.3) |
| `examples/em300-zld.td.json` | `tlv` | Tagged uplinks with a `lorav:enum` leak state |
| `examples/dragino-lht65n.td.json` | `ports` | Two fPorts plus status bits via `lorav:bitmask`; OTAA AppKey (1.0.3). Extension-specific alternate paths are a documented gap |
| `examples/netvox-r718a.td.json` | `ports` | Validated against `TheThingsNetwork/lorawan-devices` vectors; two fPorts, each branching on a `match` discriminator |
| `examples/generic-lorawan11.td.json` | `fixed` | LoRaWAN 1.1 OTAA with AppKey **and** NwkKey; onboarding metadata |

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

Of the 158 reference schemas **157 convert**, covering every `fixed`, `ports`
and TLV layout plus the `flagged`, `match`, `byte_group` and computed shapes.
The single skip (`hbi/mla20`) is legitimate rather than a regression: it nests a
`byte_group` inside a length-prefixed TLV case, a shape the bundled reference
interpreter itself mis-decodes and which ships no test vectors, so no faithful
TD can be produced. The generator prints a per-reason report on each run.

## Development

```bash
uv run pytest          # run the test suite
uv run ruff check .    # lint
uv run ruff format .   # format
```

## Scope & roadmap

* **Now:** uplink decoding, JavaScript codec generation, and Thing Description
  generation from the reference device schemas — across all four layouts and the
  `flagged` / `match` / `byte_group` / computed shapes (the
  [device catalog](#device-catalog)).
* **Later:** downlink and actions (write/invoke); `formula`/`value`-style computed
  fields; per-`fPort` branched codec generation; further payload layouts.

### Known limitations

The binding covers most common fixed/ports/TLV layouts, but these gaps remain:

* **No unit codes in the generated catalog** — `lorav:unece` works in both
  directions, but no reference device schema carries one. UN/CEFACT codes live in
  the shared schema *library*, which a device would have to pull in via
  cross-file `$ref`, and none do. Codes you add to a TD by hand are preserved.
* **Arrays / nested object payloads** — dynamic `repeat` structures and
  object/array field values are not representable as flat TD properties.
* **Legacy computed-field forms** — the structured descriptors
  (`ref`/`polynomial`/`transform`/`compute`/`guard`) are supported, but raw
  `formula`/literal-`value` expressions in source schemas are not converted.
* **TLV variants outside `tag_fields` style** — `tag_size`/length-prefixed TLV
  forms and some non-standard tag-key encodings are not converted.
* **Match defaults** — explicit enumerated `match` cases are supported (including
  top-level frame-byte dispatch), but wildcard/default branches and raw `skip`
  entries inside a case are not.
* **Alternate source branches** — when one output field switches to a different
  byte source under an extension/status flag (Dragino `Ext`-style), only the
  common path is modeled.
* **TS013 JS generator shared-byte gap** — `generate_ts013_codec.py` can drop
  bare bit-range fields and fail to advance the cursor correctly. This affects
  generated JavaScript only; `lorawan-wot decode` remains correct.

