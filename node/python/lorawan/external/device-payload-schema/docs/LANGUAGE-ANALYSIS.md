# Schema Language Design Rationale

This document explains the design decisions behind the Payload Schema language.

## Design Goals

### 1. Declarative Over Imperative

**Decision**: Schema definitions describe *what* to decode, not *how*.

**Rationale**:
- **Security**: No code execution eliminates injection attacks (unlike `eval()`)
- **Portability**: Same schema works in Python, Go, C, JavaScript
- **Tooling**: Static analysis, validation, code generation all possible
- **Simplicity**: Device manufacturers don't need to write code

**Trade-off**: Cannot express arbitrary algorithms. Mitigated by:
- Comprehensive arithmetic modifiers (`add`, `mult`, `div`)
- Transform pipeline (`sqrt`, `log`, `clamp`)
- Polynomial evaluation for calibration curves
- Lookup tables for enumeration

### 2. Wire-Format Agnostic Output

**Decision**: Schema defines binary→structured data mapping; output format is interpreter choice.

**Rationale**:
- Same schema produces JSON, SenML, LwM2M, or native structs
- Semantic hints (`ipso`, `senml_unit`) enable format translation
- Decouples parsing from presentation

### 3. Explicit Over Magic

**Decision**: All transformations visible in schema, applied in YAML key order.

**Rationale**:
- Predictable: `div: 10` then `add: -40` always means `(raw / 10) - 40`
- Debuggable: Each step traceable
- No hidden conversions based on field names

**Example**:
```yaml
- name: temperature
  type: s16
  div: 10      # Step 1: divide
  add: -40     # Step 2: offset
```

### 4. Composition Over Inheritance

**Decision**: Use `definitions` for reuse, `use:` for inclusion.

**Rationale**:
- Flat structure easier to parse in constrained environments
- No diamond inheritance problems
- Clear data flow

```yaml
definitions:
  battery:
    - name: battery_mv
      type: u16

fields:
  - use: battery      # Include definition inline
  - name: temperature
    type: s16
```

### 5. Progressive Complexity

**Decision**: Simple cases are simple; complexity available when needed.

| Complexity | Feature |
|------------|---------|
| Basic | `type: u16`, `div: 10` |
| Intermediate | `switch`, `flagged`, `lookup` |
| Advanced | `polynomial`, `guard`, `tlv` |

Most sensors need only basic features. Complex industrial protocols can use full power.

## Type System Design

### Why Both Long and Short Type Names?

```yaml
type: u16         # Short form - common case
type: UInt        # Long form - explicit
  length: 2
```

**Rationale**:
- Short forms (`u8`, `s16`, `f32`) match C conventions, reduce verbosity
- Long forms allow explicit length for unusual sizes (`u24`)
- Both parse to same internal representation

### Why Bitfield Syntax Variants?

```yaml
type: u8[0:3]     # Range syntax - bits 0-3
type: u8:4        # Width syntax - 4 bits from current position
type: bits
  offset: 0
  width: 4
```

**Rationale**:
- Range syntax natural for hardware engineers (matches datasheets)
- Width syntax natural for sequential bit extraction
- Verbose form for complex cases or code generation

### Why Separate `udec`/`sdec` Types?

**Problem**: Some sensors encode decimals as BCD-like nibbles.

**Example**: Temperature 23.5°C encoded as `0x235` (not `0x00EB`).

**Solution**: Dedicated types that interpret nibbles:
```yaml
type: udec       # 0x235 → 23.5
type: sdec       # 0xF35 → -23.5 (high nibble=0xF means negative)
```

**Rationale**: Common enough in LoRaWAN to warrant first-class support.

## Conditional Parsing Design

### Why Three Conditional Constructs?

| Construct | Use Case |
|-----------|----------|
| `switch` | Dispatch on message type field |
| `flagged` | Bitmask presence indicators |
| `tlv` | Self-describing variable payloads |

**Rationale**: Each maps to common protocol patterns:

**`match`** - Fixed message types:
```yaml
- match:
    field: $msg_type
    cases:
      0x01: [temperature_fields]
      0x02: [gps_fields]
```

**`flagged`** - Optional sensor groups:
```yaml
- flagged:
    field: sensors_present
    groups:
      - bit: 0
        fields: [temperature]
      - bit: 1  
        fields: [humidity]
```

**`tlv`** - Extensible protocols:
```yaml
- tlv:
    tag_type: u8
    length_type: u8
    cases:
      0x67: [temperature]
      0x68: [humidity]
```

## Arithmetic Pipeline Design

### Why Order-Dependent Modifiers?

**Decision**: `add`, `mult`, `div` apply in YAML key order.

**Alternative considered**: Fixed order (mult→div→add).

**Rationale for YAML order**:
- Matches how engineers think about conversions
- Visible in schema - no hidden rules
- Handles both `(raw + offset) * scale` and `raw * scale + offset`

```yaml
# Pattern 1: Scale then offset
- name: temp_c
  type: u16
  div: 100
  add: -40

# Pattern 2: Offset then scale  
- name: pressure
  type: u16
  add: -32768
  mult: 0.1
```

### Why Separate `transform` Array?

**Problem**: Some operations don't fit mult/div/add model.

**Solution**: Transform pipeline for mathematical operations:
```yaml
transform:
  - sqrt: true
  - mult: 2
  - clamp: [0, 100]
```

**Rationale**:
- Clear ordering (array = sequential)
- Extensible (add new transforms without breaking existing)
- Composable with arithmetic modifiers

## Binary Format Design

### Why a Binary Schema Format?

**Use cases**:
- OTA schema transfer (save airtime)
- Embedded systems (no YAML parser)
- QR code encoding (limited space)

**Design**: 4-6 bytes per field:
```
Header: 'P' 'S' version flags field_count
Field:  type_byte mult_exp semantic_id[2] [options]
```

**Rationale**:
- 10-20x smaller than YAML
- O(1) field access
- No string parsing at runtime

### Why Not Use Protobuf/MessagePack?

**Considered**: Using existing binary formats.

**Rejected because**:
- Protobuf requires schema compilation
- MessagePack still needs schema definition
- Custom format optimized for this specific use case
- Simpler implementation in constrained C

## Feature Exclusions

### Why No Formula Field?

**Considered**: `formula: "sqrt(x * 0.01) + offset"`

**Rejected because**:
- Requires expression parser (complex, security risk)
- Platform-dependent floating point
- Debugging difficulty
- Covered by `polynomial` + `transform` + `compute`

### Why No Conditional Arithmetic?

**Considered**: `mult: { if: "$range == 1", then: 0.1, else: 0.01 }`

**Current approach**: Use `match_value` for range-dependent transforms:
```yaml
match_value:
  - when: "< 100"
    mult: 0.1
  - when: ">= 100"
    mult: 0.01
```

**Rationale**: Keeps arithmetic simple; complex cases use explicit matching.

### Why No Encryption/Compression?

**Decision**: Schema describes payload structure only.

**Rationale**:
- Encryption is transport concern (handled by LoRaWAN)
- Compression varies by implementation
- Schema remains focused and portable

## Compatibility Considerations

### TTN Codec Compatibility

**Goal**: Convert existing TTN JavaScript codecs to schemas.

**Mapping**:
| TTN Pattern | Schema Equivalent |
|-------------|-------------------|
| `bytes[i]` | Sequential field reads |
| `<< / >>` | Bitfields or multi-byte types |
| Lookup object | `lookup:` array |
| Math expressions | `add`/`mult`/`div` + `transform` |

**Limitation**: Complex algorithms require manual conversion or hybrid approach.

### Milesight TLV Compatibility

**Design decision**: First-class TLV support because Milesight (major vendor) uses it extensively.

```yaml
- tlv:
    tag_type: u8
    length_type: u8
    include_length_in_value: false
```

## Future Considerations

### Reserved Keywords

These are reserved for future use:
- `compress` - Payload compression hints
- `encrypt` - Field-level encryption markers
- `validate` - Runtime validation rules
- `encode` - Bidirectional encoding hints

### Extension Points

Schema can include vendor extensions:
```yaml
x-vendor:
  custom_property: value
```

Interpreters MUST ignore unknown `x-` prefixed keys.

## Summary

The Payload Schema language prioritizes:

1. **Security** - Declarative, no code execution
2. **Portability** - Works across languages and platforms  
3. **Simplicity** - Common cases are concise
4. **Predictability** - Explicit ordering, no magic
5. **Extensibility** - Future features won't break existing schemas
