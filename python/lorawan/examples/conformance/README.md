# WoT binding conformance fixtures

These are not devices. Each Thing Description here exercises one construct of the
LoRaWAN WoT binding that no curated device example reaches, so that every term the
binding publishes has at least one checked-in example that is decoded, schema-
validated and round-tripped on every run.

They exist because neither existing corpus can play this role:

* the seven curated `examples/*.td.json` are real devices, and between them they
  reached 15 of the 24 `lorav:` terms, 3 of the 4 payload layouts, 5 of the 32
  `lorav:wireType` values, one of the two `lorav:presentWhen` shapes and none of
  the five `lorav:derived` descriptors;
* `examples/devices/` covers far more, but it is generated, gitignored and pinned
  to a submodule, so nothing in it is reviewed and nothing in it is stable. It
  also only ever covers what vendors happen to ship.

`tests/test_conformance_corpus.py` is what keeps the coverage from decaying: it
walks the vocabulary, the layout set, the wire-type enum and the derived-value
descriptors, and fails if any published member has no example. Minting a term
without an example now breaks the suite.

This mirrors, one layer up, the `_language-conformance/` fixtures in the payload
schema repository, which hold the four reference interpreters to the same
behaviour for constructs no device schema uses.

## What each fixture pins

| Fixture | Construct |
| --- | --- |
| `wiretype-integer-widths` | every unsigned and signed integer width, `u8`..`u64` / `s8`..`s64` |
| `wiretype-float-precision` | `f16`, `f32`, `f64` |
| `wiretype-xsd-aliases` | every `xsd:` alias with a defined wire width, decoding identically to its native spelling |
| `wiretype-variable-length` | `hex`, `bytes`, `base64`, `ascii`, sized with `lorav:byteLength`, plus the `-1` "consume the rest" sentinel |
| `endian-big-explicit` / `endian-little-explicit` | both `lorav:endian` values, stated rather than defaulted |
| `layout-ctv-default-tags` | the `ctv` layout, and the default `channel`(u8) + `type`(u8) tag fields supplied when `lorav:tagFields` is omitted |
| `layout-tlv-multifield-slot` | several values sharing one `lorav:tag`, sequenced by `lorav:slot` |
| `presentwhen-bit-flagged` | the flag-bit shape of `lorav:presentWhen` |
| `derived-ref-polynomial` | `lorav:derived` with `ref`, `polynomial` (descending powers) and `transform` |
| `derived-compute-guard` | `lorav:derived` with `compute`, and a `guard` both passing and falling back |
| `alias-and-padbefore` | `lorav:alias` on a match discriminator, and `lorav:padBefore` inside a case |

Every expected value in a `*.vectors.json` here was computed from the wire bytes
by hand and is then held against the reference interpreter, rather than recorded
from whatever the interpreter happened to return.

## Constructs deliberately absent

Two things the binding publishes have no fixture, because an example would have
to encode wrong behaviour in order to pass. They are recorded in
`UNCOVERED_WIRE_TYPES` and in the notes below so the gap stays visible.

### `bool` / `xsd:boolean`

The reference interpreter reads `bool` as a *bit* of the byte under the cursor
and does not advance the cursor unless the field carries `consume`:

```
fields: [ {a: bool}, {b: bool}, {c: bool} ]   payload 01 00 00  ->  a=b=c=True
fields: [ {a: u8}, {flag: bool}, {b: u8} ]    payload 0A 01 FF  ->  b=1, not 255
```

The binding has no term for either `bit` or `consume`, and
`converter._WIRE_WIDTH` assigns `bool` a width of 1, so a Thing Description
using it decodes its second boolean from the first one's byte and reads every
subsequent field one byte early. A boolean is spelled today as an unsigned byte
with `lorav:bitmask` and `lorav:valueMap` — see `mclimate-mc-button.td.json`.

### Mixed `lorav:endian` within one Thing Description

`lorav:endian` is documented as a form-level term, and `converter._typed()`
emits a `be_`/`le_` type prefix for a field whose byte order disagrees with the
schema-wide default. The reference interpreter has no such prefix — byte order
is one document-wide `endian` value — and rejects the field outright:

```
Decode failed: ['Error decoding le_override: Unknown type: le_u16']
```

Nothing in either corpus emits that prefix (167 generated Thing Descriptions and
7 curated ones: zero), so the path had never been executed. The two endian
fixtures are therefore each uniform, and a mixed-endian device cannot currently
be expressed.
