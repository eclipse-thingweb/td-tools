# LoRaWAN binding for WoT Thing Descriptions

Describe a LoRaWAN sensor once as a **W3C Web of Things (WoT) Thing Description
(TD)** and get a working **payload codec** out of it. The generated codec is
validated against ChirpStack; it should also work in The Things Network (TTN).

The TD carries the payload binding *inside its event forms* (using
terms prefixed with `lorav:`). A converter translates that TD into the
[LoRa Alliance Payload Schema / MultiTech](https://github.com/MultiTechSystems/device-payload-schema)
language, and the reference interpreter (e.g. ChirpStack) does the actual byte decoding.

```
Thing Description (.td.json)
        │   lorav: terms on each event form
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
* **Uplinks are events, not properties** – a LoRaWAN device transmits on its own
  schedule and cannot be polled. Modelling a reading as a property would promise
  a read operation the radio link cannot perform; an event says what actually
  happens, which is that a value arrives when the device decides to send it.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

All commands must be run from the **`python/lorawan/`** subdirectory, where
`pyproject.toml` lives.

```bash
# 0. Enter the project directory
cd python/lorawan

# 1. Get the LoRa Alliance Payload / MultiTech interpreter (pinned submodule)
git submodule update --init --recursive

# 2. Create the environment and install dependencies
uv sync

# 3. Sync curated examples from upstream
uv run sync-examples
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
  lorawan-form.schema.json  # JSON Schema for LoRaWAN event forms
  lorawan-thing.schema.json  # JSON Schema for Thing-level OTAA / onboarding terms
examples/         # curated TDs, mirrored from eclipse-thingweb/examples (not checked in)
  devices/        # TD catalog generated from the reference device schemas (git-ignored)
  generated/      # output folder for generated schema/codec artifacts
scripts/
  sync_examples.py        # fetch curated *.td.json + *.vectors.json from upstream
  generate_device_tds.py  # batch-generate the examples/devices/ catalog
  migrate_td_to_events.py # rewrite a pre-0.3.0 TD into the events model
  vocab_usage_report.py   # count lorav: term usage across every bundled TD
  update_golden.py        # re-record the golden snapshot
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
field descriptor on each event's form.

```jsonc
{
  "@context": [
    "https://www.w3.org/2022/wot/td/v1.1",
    { "lorav": "https://www.w3.org/2024/wot/lorawan#" }
  ],
  "lorav:payloadLayout": "fixed",          // fixed | ports | tlv | ctv
  "events": {
    "temperature": {
      "data": {                             // what the notification carries
        "type": "number",
        "unit": "Cel"
      },
      "forms": [
        {
          "href": "uplink",
          "op": ["subscribeevent", "unsubscribeevent"],
          "lorav:byteOffset": 2,            // where in the payload
          "lorav:wireType": "xsd:short",    // wire data type
          "lorav:endian": "big",            // big (default) | little
          "lorav:multiplier": 0.01          // raw * 0.01
        }
      ]
    }
  }
}
```

Here, `data` says what the value *means*, the form says how
it is *transferred*. 

### Payload layouts

| `lorav:payloadLayout` | When to use | Required per-event terms |
|-----------------------|-------------|--------------------------|
| `fixed` | Every value sits at a fixed byte position | `lorav:byteOffset` |
| `ports` | The LoRaWAN `fPort` selects a fixed layout | `lorav:fPort`, `lorav:byteOffset` |
| `tlv` / `ctv` | Values are tagged (e.g. channel + type) | `lorav:tag` |

For `tlv`/`ctv` you may declare the tag fields at Thing level with
`lorav:tagFields` (defaults to `channel` + `type`, both `u8`).


### Form-level vocabulary (`lorav:` terms)

The **Tier** column shows how often each term appears across the bundled
[device catalog](#device-catalog): **core** is needed by almost every device,
**common** by a recognisable class of them, and **rare** by only a few.
The rare terms exist because the reference schemas model real vendor payloads,
so you can ignore them until a device needs one.

| Term | Meaning | MultiTech | Tier | Seen in |
|------|---------|-----------|------|---------|
| `lorav:wireType` | Wire data type (xsd alias or native, e.g. `xsd:short`, `s16`) | `type` | core | every device |
| `lorav:endian` | Byte order of this multi-byte value, `"big"` (default) or `"little"` | `endian` | core | every multi-byte value |
| `lorav:byteOffset` | Byte position in a fixed layout | field order / `skip` padding | core | `fixed` + `ports` devices |
| `lorav:tag` | Tag selecting a value, e.g. `[3, 103]` | `tlv` case key | core | Milesight, Elsys |
| `lorav:fPort` | LoRaWAN frame port | `ports` key | core | `ports` devices (e.g. Digital Matter) |
| `lorav:divisor` | `value = raw / divisor` | `div` | core | most vendors |
| `lorav:slot` | Order of an event within its group (multi-field TLV / flagged / match) | field order | common | any multi-value group |
| `lorav:presentWhen` | Condition gating this value: `{ field, bit }` or `{ field, value }` | `flagged` / `match` | common | Decentlab, Dragino, Netvox, RadioBridge, Radionode |
| `lorav:bitmask` | Extract a contiguous bit range (single- or multi-byte base) | bit range `u8[lo:hi]` | common | Dragino, Digital Matter, MClimate, RadioBridge, RAKwireless |
| `lorav:addend` | `value = value + addend` (after scaling) | `add` | common | Decentlab, MClimate, RadioBridge |
| `lorav:multiplier` | `value = raw * multiplier` | `mult` | common | Decentlab, Digital Matter, MClimate |
| `lorav:derived` | Computed value: `{ ref, polynomial, compute, guard, transform }` | `ref`/`polynomial`/… | rare | Decentlab, Digital Matter, MClimate |
| `lorav:alias` | Name this value is referenced by as `$alias`, when a condition's `field` differs from the event name | `var` | rare | RadioBridge, Radionode |
| `lorav:byteLength` | Byte length for `bytes`/`string`/`hex` (`-1` = consume rest) | `length` | rare | RadioBridge |
| `lorav:padBefore` | Reserved bytes consumed before this value within its group | `skip` inside a case | rare | RadioBridge |

`lorav:multiplier` and `lorav:divisor` are mutually exclusive. Prefer
`lorav:divisor`: `{"lorav:divisor": 100}` is exact, while the equivalent
`{"lorav:multiplier": 0.01}` is not representable in binary floating point and
accumulates error.

Supported `lorav:wireType` values: the sized XSD types (`xsd:byte`, `xsd:short`,
`xsd:int`, `xsd:long`, the `xsd:unsigned*` variants, `xsd:float`, `xsd:double`,
`xsd:boolean`, `xsd:hexBinary`, `xsd:string`) and the native MultiTech types
(`u8`–`u64`, `s8`–`s64`, `f16`/`f32`/`f64`, `bool`, `ascii`, `hex`, `bytes`,
`base64`), plus `number` for a `lorav:derived` value that occupies no bytes.

#### Terms this binding deliberately does *not* define

| Instead of a `lorav:` term | Use in `data` |
|----------------------------|---------------|
| a unit code | `"unit": "Cel"` (already carries UN/CEFACT codes) |
| a valid range | `"minimum": -40, "maximum": 85` |
| an enumeration | `"oneOf": [{ "const": 0, "title": "dry" }, …]` |
| brand / model | `"schema:brand"`, `"schema:model"` on the Thing |
| hardware / firmware version | the Thing's `"version": { "model": …, "instance": … }` |

### Grouped and conditional values

One event always describes one value. Payloads that pack values together or
branch between them are expressed by giving several events the same locator:

| Shape | How to express it |
|-------|-------------------|
| Several values share one byte or word | Same `lorav:byteOffset`, one `lorav:bitmask` each |
| Several values share one tag | Same `lorav:tag`, ordered by `lorav:slot` |
| A value appears only when a flag bit is set | `lorav:presentWhen: { "field": "flags", "bit": 0 }` |
| A value belongs to one branch of a discriminator | `lorav:presentWhen: { "field": "event", "value": 1 }` |
| A value is derived rather than read from the wire | `lorav:wireType: "number"` + `lorav:derived` |

`lorav:presentWhen` always names the value it depends on in `field`, then gates
on either a `bit` of it or an exact `value` — never both. Grouping the condition
under one term keeps the two halves impossible to separate: a bit index with no
field to index into is meaningless, and the old flat terms let you write exactly
that.

`lorav:bitmask` must select a *contiguous* range of bits. The base value is read
once and decoded into every event masking it, and bases wider than one byte
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
| `lorav:region` | Regulatory region / profile (e.g. `EU868`) | no |
| `lorav:frequencyPlan` | LNS frequency plan id (e.g. `EU_863_870_TTN`) | no |
| `lorav:payloadLayout` | Payload structure: `fixed`, `ports`, `tlv` or `ctv` | no |
| `lorav:tagFields` | Tag field definitions for `tlv`/`ctv` layouts | no |
| `AppKey` | OTAA root key — `apikey` scheme `name: "appKey"` | **yes (runtime)** |
| `NwkKey` | OTAA network root key (1.1.x) — `apikey` scheme `name: "nwkKey"` | **yes (runtime)** |

Device metadata that is not LoRaWAN-specific uses vocabularies that already
define it, such as `schema:brand` and `schema:model` from [schema.org](https://schema.org),
the Thing's `version` (`model` for hardware, `instance` for firmware), and the
Thing's `id`/`title` to identify the end device.



## Examples

The **6 curated example pairs** (`*.td.json` + `*.vectors.json`) in `examples/`
are sourced from
[`eclipse-thingweb/examples/TTC26/examples`](https://github.com/eclipse-thingweb/examples/tree/main/TTC26/examples)
and fetched by `uv run sync-examples` rather than checked in here.

| File | Layout | Highlights |
|------|--------|-----------|
| `examples/adeunis-comfort2.td.json` | `fixed` | Smallest complete example: signed temperature, humidity, battery |
| `examples/milesight-am102.td.json` | `ctv` | Little-endian channel/type/value; OTAA AppKey (1.0.3) |
| `examples/em300-zld.td.json` | `tlv` | Tagged uplinks with a `oneOf`-labelled leak state |
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


## Development

All commands assume you are in the `python/lorawan/` directory.

```bash
uv run python -m scripts.generate_device_tds   # generate examples/devices/ (see below)
uv run pytest                                  # run the test suite
uv run ruff check .                            # lint
uv run ruff format .                           # format

uv run python -m scripts.vocab_usage_report    # count lorav: term usage across all TDs
uv run python -m scripts.update_golden         # re-record tests/golden/snapshot.json
```

`examples/devices/` is generated, not checked in, so `tests/test_device_catalog.py`
fails on a fresh clone until you run the generator once.

The golden snapshot pins the decoded output of every bundled TD, so re-recording
it accepts whatever changed. Read the diff before committing it.


## Scope & roadmap

* **Now:** uplink decoding, JavaScript codec generation, and Thing Description
  generation from the reference device schemas — across all four layouts and the
  `flagged` / `match` / `byte_group` / computed shapes (the
  [device catalog](#device-catalog)).
* **Later:** downlink and actions (write/invoke); `formula`/`value`-style computed
  fields; per-`fPort` branched codec generation; further payload layouts.

### Known limitations

The binding covers most common fixed/ports/TLV layouts, but these gaps remain:

* **Arrays / nested object payloads** — dynamic `repeat` structures and
  object/array field values are not representable as flat TD events.
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

