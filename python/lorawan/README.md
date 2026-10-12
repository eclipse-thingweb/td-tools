# LoRaWAN binding for WoT Thing Descriptions

Describe a LoRaWAN sensor once as a **W3C Web of Things (WoT) Thing Description
(TD)** and get a working **payload codec** out of it. The generated codec is
validated against ChirpStack; it should also work in The Things Network (TTN).

The TD carries the payload binding *inside its event forms* (using
terms prefixed with `lorav:`). A converter translates that TD into the
[LoRa Alliance Payload Schema / MultiTech](https://github.com/MultiTechSystems/device-payload-schema)
language, where the reference interpreter converts it into decoding functions. These functions can then be used in the LoRaWAN server (e.g. ChirpStack / TTN) for actual byte decoding.

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
  Decoder functions   ← LoRaWAN network server (ChirpStack / TTN)
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

All commands must be run from the **`python/lorawan/`** subdirectory, where
`pyproject.toml` lives.

```bash
# 0. Enter the project directory
cd python/lorawan

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
  lorawan-form.schema.json  # JSON Schema for LoRaWAN event forms
  lorawan-thing.schema.json  # JSON Schema for Thing-level OTAA / onboarding terms
examples/         # curated TDs and their test vectors (checked in)
  devices/        # TD catalog generated from the reference device schemas (git-ignored)
  generated/      # output folder for generated schema/codec artifacts
scripts/
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
uv run lorawan-wot convert examples/milesight-em300-th.td.json
# write to a file instead of stdout:
uv run lorawan-wot convert examples/milesight-em300-th.td.json -o examples/generated/em300-th.schema.yaml
```

### Decode an uplink payload

```bash
uv run lorawan-wot decode examples/milesight-em300-th.td.json 0175640367F900046862 --fport 85
# -> {
#      "battery": 100,
#      "temperature": 24.9,
#      "humidity": 49.0
#    }
```

`--fport` is required for a `ports` layout, because the frame port selects which
layout to apply; Without it the interpreter cannot select the right field set. Other layouts ignore it.

### Use it from Python

```python
import json

import yaml

from lorawan_wot import payload_schema_to_td, td_to_payload_schema
from lorawan_wot.decode import decode_uplink

with open("examples/milesight-em300-th.td.json", encoding="utf-8") as fp:
    td = json.load(fp)

schema = td_to_payload_schema(td)  # TD -> MultiTech schema (dict)
print(decode_uplink(td, "0175640367F900046862"))
# {'battery': 100, 'temperature': 24.9, 'humidity': 49.0}

# The reverse direction: MultiTech schema -> Thing Description.
source_path = "external/device-payload-schema/schemas/devices/makerfabs/ath20.yaml"
with open(source_path, encoding="utf-8") as fp:
    generated_td = payload_schema_to_td(yaml.safe_load(fp), source="ath20.yaml")
```

### Generate a ChirpStack / TTN JavaScript codec

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

### Generate a Thing Description from a payload schema

The reverse of `convert`: turn an existing LoRa Alliance / MultiTech payload
schema into a starter Thing Description.

```bash
uv run lorawan-wot generate external/device-payload-schema/schemas/devices/makerfabs/ath20.yaml -o examples/devices/makerfabs/ath20.td.json
```

This is how the bundled [device catalog](#device-catalog) is produced.

## How to describe a device in a TD

Add the binding namespace to `@context`, set a Thing-level layout, and put a
field descriptor on each event's form.

```jsonc
{
  "@context": [
    "https://www.w3.org/2022/wot/td/v1.1",
    { "lorav": "https://www.w3.org/2024/wot/lorawan#" }
  ],
  "@type": "Thing",
  "id": "urn:dev:example:env-sensor",
  "title": "Environmental Sensor",
  "description": "Environmental Sensor with temperature, humidity, and battery packed at fixed byte positions.",
  "securityDefinitions": {
    "otaa_sc": {
      "scheme": "apikey",
      "in": "uri",
      "name": "appKey",
      "description": "LoRaWAN OTAA AppKey. Injected at runtime."
    }
  },
  "security": "otaa_sc",
  "lorav:devEUI": "0000000000000001",
  "lorav:joinEUI": "0000000000000000",
  "lorav:macVersion": "1.0.3",
  "lorav:region": "EU868",
  "lorav:frequencyPlan": "EU_863_870",
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

Here, `data` says what the value *means*, the `form` says how
it is *transferred*. 


### Thing-level vocabulary

| Term | Meaning | Secret? |
|------|---------|---------|
| `lorav:devEUI` | 8-byte device identifier (16 hex chars) | no |
| `lorav:joinEUI` | 8-byte join/app identifier (formerly AppEUI) | no |
| `lorav:macVersion` | LoRaWAN MAC version, e.g. `1.0.3`, `1.1.0` | no |
| `lorav:region` | Regulatory region / profile (e.g. `EU868`) | no |
| `lorav:frequencyPlan` | LNS frequency plan id (e.g. `EU_863_870_TTN`) | no |
| `lorav:defaultEventingFrequencyMinutes` | Expected minutes between unprompted uplinks | no |
| `lorav:payloadLayout` | Payload structure: `fixed`, `ports`, `tlv` or `ctv` | no |
| `lorav:tagFields` | Tag field definitions for `tlv`/`ctv` layouts | no |
| `AppKey` | OTAA root key — `apikey` scheme `name: "appKey"` | **yes (runtime)** |
| `NwkKey` | OTAA network root key (1.1.x) — `apikey` scheme `name: "nwkKey"` | **yes (runtime)** |

Device metadata that is not LoRaWAN-specific uses established schemas, such as [schema.org](https://schema.org):
`schema:manufacturer` and `schema:mpn` (the manufacturer's part number) identify
the model, `schema:version` and `schema:softwareVersion` carry the hardware and
firmware revisions, and the Thing's `id`/`title` identify the end device.


### Payload layouts

| `lorav:payloadLayout` | When to use | Required per-event terms |
|-----------------------|-------------|--------------------------|
| `fixed` | Every value sits at a fixed byte position | `lorav:byteOffset` |
| `ports` | The LoRaWAN `fPort` selects a fixed layout | `lorav:fPort`, `lorav:byteOffset` |
| `tlv` / `ctv` | Values are tagged (e.g. channel + type) | `lorav:tag` |

For `tlv`/`ctv` you may declare the tag fields at Thing level with
`lorav:tagFields` (defaults to `channel` + `type`, both `u8`).

`ctv` is currently accepted as an alias and converts identically — the two names describe the same tagged structure.

### Form-level vocabulary (`lorav:` terms)

The **Tier** column shows how often each term appears across the bundled
[device catalog](#device-catalog): **core** is needed by almost every device,
**common** by a recognisable class of them, and **rare** by only a few.
The rare terms exist because the reference schemas model real vendor payloads,
so you can ignore them until a device needs one.

| Term | Meaning | LoRa Alliance Payload Schema / MultiTech | Tier | Seen in |
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
| `lorav:valueMap` | Map each wire integer to the value it denotes: `[{ wireValue, value }, …]` | `lookup` | rare | Milesight, MClimate, RadioBridge, Makerfabs |
| `lorav:addend` | `value = value + addend` (after scaling) | `add` | common | Decentlab, MClimate, RadioBridge |
| `lorav:multiplier` | `value = raw * multiplier` | `mult` | common | Decentlab, Digital Matter, MClimate |
| `lorav:derived` | Computed value: `{ ref, polynomial, compute, guard, transform }` | `ref`/`polynomial`/… | rare | Decentlab, Digital Matter, MClimate |
| `lorav:alias` | Name this value is referenced by as `$alias`, when a condition's `field` differs from the event name | `var` | rare | RadioBridge, Radionode |
| `lorav:byteLength` | Byte length for `bytes`/`string`/`hex` (`-1` = consume rest) | `length` | rare | RadioBridge |
| `lorav:padBefore` | Reserved bytes consumed before this value within its group | `skip` inside a case | rare | RadioBridge |

`lorav:multiplier` and `lorav:divisor` are mutually exclusive. Prefer
`lorav:divisor`: `{"lorav:divisor": 100}`, while the equivalent
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
| the values a reading may take | `"enum": ["dry", "wet"]` |
| a byte fixed at one value (e.g. a downlink command byte) | `"const": 3` |
| manufacturer / part number | `"schema:manufacturer"`, `"schema:mpn"` on the Thing |
| hardware / firmware version | `"schema:version"`, `"schema:softwareVersion"` on the Thing |

#### Categorical values (`lorav:valueMap`)

A reading such as a leak state is split across the two halves of the affordance.
The `data` schema says which values the reading may take, using TD core's `enum`;
the form says which byte on the wire produces which of them:

```json
"leakage_status": {
  "data": { "type": "string", "enum": ["normal", "leak"] },
  "forms": [{
    "href": "uplink",
    "op": ["subscribeevent", "unsubscribeevent"],
    "lorav:tag": [5, 0],
    "lorav:wireType": "u8",
    "lorav:valueMap": [
      { "wireValue": 0, "value": "normal" },
      { "wireValue": 1, "value": "leak" }
    ]
  }]
}
```

#### Grouped and conditional values

One event always describes one value. Payloads that pack values together or
branch between them are expressed by giving several events the same locator:

| Shape | How to express it |
|-------|-------------------|
| Several values share one byte or word | Same `lorav:byteOffset`, one `lorav:bitmask` each |
| Several values share one tag | Same `lorav:tag`, ordered by `lorav:slot` |
| A value appears only when a flag bit is set | `lorav:presentWhen: { "field": "flags", "bit": 0 }` |
| A value belongs to one branch of a discriminator | `lorav:presentWhen: { "field": "event", "value": 1 }` |
| A value is derived rather than read from the wire | `lorav:wireType: "number"` + `lorav:derived` |

`lorav:presentWhen` names the value it depends on in `field`, then gates
on either a `bit` of it or an exact `value`.

`lorav:bitmask` selects a *contiguous* range of bits. The base value is read
once and decoded into every event masking it, and bases wider than one byte
(`u16`/`u24`/`u32`) work too, for ranges spanning several bytes.

#### Derived values (`lorav:derived`)

Some values a device reports are never transmitted. The payload carries a raw
count and the vendor's documentation gives the arithmetic that turns it into the
quantity the user needs, such as, a value is computed from two other sensor readings.
Such a value occupies **zero payload bytes**, which is what `lorav:wireType:
"number"` records — there is no wire type, because there is nothing to read.

`transform` is the exception. It post-processes a value that *was* read from the
wire, so it sits next to a real `lorav:wireType` and `lorav:byteOffset` rather
than replacing them. A `lorav:derived` carrying only `transform` keeps its wire
type; one carrying `ref`, `polynomial`, `compute` or `guard` declares
`"number"`.

`lorav:derived` is one object with up to five keys, each naming *where the value
comes from*. They apply in this order:

| Key | Meaning |
|-----|---------|
| `ref` | The input: `$name` of the event this value is computed from |
| `polynomial` | Coefficients `[c0, c1, c2, …]`, applied to the input as `c0 + c1·x + c2·x² + …` |
| `compute` | A binary operation `{ "op": "div", "a": …, "b": … }` over two values or constants |
| `guard` | A precondition `{ "when": [ … ], "else": v }`; the value falls back to `v` when a `when` clause fails |
| `transform` | Ordered post-processing steps, each one of `add` / `div` / `mult` / `round` |

Examples: 

Decentlab's 5TM soil sensor transmits a raw dielectric permittivity and
documents a fourth-order fit for the water content derived from it:

```jsonc
"volumetric_water_content": {
  "data": { "type": "number" },
  "forms": [{
    "href": "uplink",
    "lorav:wireType": "number",
    "lorav:derived": {
      "ref": "$dielectric_permittivity",
      "polynomial": [4.3e-06, -0.00055, 0.0292, -0.053]
    }
  }]
}
```

Its albedo sensor divides two other readings, and guards the division so a night
time reading does not divide by zero:

```jsonc
"lorav:derived": {
  "compute": { "op": "div", "a": "$reflected_radiation", "b": "$incoming_radiation" },
  "guard": {
    "when": [
      { "field": "$incoming_radiation", "gt": 0 },
      { "field": "$reflected_radiation", "gte": 0 }
    ],
    "else": 0
  }
}
```

These were five sibling terms before 0.3.0 (`lorav:ref`, `lorav:polynomial`,
`lorav:compute`, `lorav:guard`, `lorav:transform`). Grouping them under one term
makes "this value is computed rather than read."

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



## Examples

**Some curated example pairs** (`*.td.json` + `*.vectors.json`) in `examples/`
are checked in and maintained here.

| File | Layout | Highlights |
|------|--------|-----------|
| `examples/adeunis-comfort2.td.json` | `fixed` | Smallest complete example: signed temperature, humidity, battery |
| `examples/milesight-em300-th.td.json` | `tlv` | Little-endian channel/type/value; OTAA AppKey (1.0.3) |
| `examples/milesight-em300-zld.td.json` | `tlv` | Tagged uplinks with a `lorav:valueMap`-labelled leak state |
| `examples/dragino-lht65n.td.json` | `ports` | Two fPorts plus status bits via `lorav:bitmask`; OTAA AppKey (1.0.3). Extension-specific alternate paths are a documented gap |
| `examples/mclimate-mc-button.td.json` | `fixed` | Affine raw-byte scaling (`lorav:multiplier` + `lorav:addend`); an inverted status bit named through `lorav:valueMap` |
| `examples/netvox-r718a.td.json` | `ports` | Validated against `TheThingsNetwork/lorawan-devices` vectors; two fPorts, each branching on a `match` discriminator |
| `examples/generic-lorawan11.td.json` | `fixed` | LoRaWAN 1.1 OTAA with AppKey **and** NwkKey; onboarding metadata |

Each example has a matching `*.vectors.json` file with known payloads and their
expected decoded values, used by the tests.

### Conformance fixtures

The curated examples above are real devices, so they only reach the constructs
those devices happen to use. `examples/conformance/` fills the rest in: one
hand-written Thing Description per binding construct, covering every wire type,
both byte orders, all four payload layouts, both `lorav:presentWhen` shapes and
all five `lorav:derived` descriptors. They are checked in and reviewed like any
other example, and are decoded, schema-validated and round-tripped by the same
tests.

`tests/test_conformance_corpus.py` keeps that coverage from decaying: it walks
the vocabulary, the layout set, the wire-type enum and the derived-value
descriptors, and fails if any published member has no example. Adding a
`lorav:` term without an example that exercises it breaks the suite.

See `examples/conformance/README.md`, which also records the two published
constructs that deliberately have no fixture, and why.

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
```

`examples/devices/` is generated, not checked in, so `tests/test_device_catalog.py`
fails on a fresh clone until you run the generator once.


## Scope & roadmap

* **Now:** uplink decoding, JavaScript codec generation, and Thing Description
  generation from the reference device schemas — across all four layouts and the
  `flagged` / `match` / `byte_group` / computed shapes (the
  [device catalog](#device-catalog)).
* **Later:** downlink and actions (write/invoke); `formula`-style computed
  fields; per-`fPort` branched codec generation; further payload layouts.

### Known limitations

The binding covers most common fixed/ports/TLV layouts, but these gaps remain:

* **Arrays / nested object payloads** — dynamic `repeat` structures and
  object/array field values are not representable as flat TD events.
* **`formula` expressions** — the structured descriptors
  (`ref`/`polynomial`/`transform`/`compute`/`guard`) are supported, but raw
  `formula` expressions in source schemas are not converted.
* **`bitfield_string` fields** — a field rendering packed bits as text has no
  form term and takes its device out of the catalog. Affects 36 Milesight
  schemas, which adopted the type in the current submodule pin.
* **TLV variants outside the supported tag-key subset** — plain `tag_size`
  TLV without a length prefix is converted, but length-prefixed TLV forms and
  non-standard tag-key patterns (for example wildcard or negated tag parts) are
  not.
* **Match defaults** — explicit enumerated `match` cases are supported (including
  top-level frame-byte dispatch, and `skip` padding between fields of a case,
  which becomes `lorav:padBefore`), but wildcard/default branches and a case
  ending in trailing `skip` padding are not.
* **Alternate source branches** — when one output field switches to a different
  byte source under an extension/status flag (Dragino `Ext`-style), only the
  common path is modeled.
* **TS013 JS generator shared-byte gap** — `generate_ts013_codec.py` can drop
  bare bit-range fields and fail to advance the cursor correctly. This affects
  generated JavaScript only; `lorawan-wot decode` remains correct.

