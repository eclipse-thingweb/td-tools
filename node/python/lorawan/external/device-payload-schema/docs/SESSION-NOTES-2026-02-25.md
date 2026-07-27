# Session Notes: 2026-02-25

## Requirement Numbering Alignment

### Problem
The prototype tests were using a custom `REQ-xxx-yyy` numbering scheme that was inconsistent with the official specification's requirement IDs in `la-payload-schema/spec/sections/A4-requirements.md`.

### Spec Requirement Scheme
The specification uses:
- **M001-M234**: Mandatory (MUST/SHALL) - 234 requirements
- **R001-R057**: Recommended (SHOULD) - 57 requirements  
- **O001-O044**: Optional (MAY) - 44 requirements
- **Total**: 335 requirements

Source format: `SNN:LLL` where NN = section number, LLL = line number in source markdown.

### Updates Made

1. **`test-requirements-map.yaml`**
   - Completely rewritten to map test functions to spec M/R/O requirement IDs
   - Organized by specification sections (Schema Format, Field Types, Modifiers, etc.)
   - Added summary section with coverage statistics
   - Notes prototype extensions not yet in spec

2. **`tests/test_schema_interpreter.py`**
   - Updated file header to reference A4-requirements.md
   - Converted all class docstrings from `REQ-xxx` to `M###`/`R###`/`O###`
   - Updated inline test method docstrings to spec IDs
   - 365 tests pass, 4 skipped (library tests)

### Prototype Extensions (Not Yet in Spec)

These features are implemented in the proto but not yet formally specified:

| Feature | Proto Implementation | Spec Approach |
|---------|---------------------|---------------|
| Encodings | `encoding: sign_magnitude\|bcd\|gray` | Not specified |
| Downlink commands | `downlink_commands:` structure | Uses `match` with `command_id` |
| Compact format parsing | `fields: ">B:version H:length"` | O021-O022 (MAY support) |

### Requirement Coverage

Tests now reference ~145 spec requirements:
- Schema format/structure: M003-M040
- Integer types: M041-M045
- Float types: M046-M047
- Bitfields: M048-M053
- Boolean/Enum: M054-M058
- Byte groups: M059-M060
- Strings: M061-M064
- Computed: M065-M067
- Repeat: M072-M076
- Modifiers: M085-M092
- Polynomial: M093-M097
- Transforms: M098-M101
- Compute: M102-M106
- Guard: M107-M111
- Valid range: M112-M115
- Nested objects: M119-M121
- Variables: M122-M127
- Match: M128-M132
- TLV: M133-M137
- Flagged: M138-M148
- Compact: M149-M156, M166-M169
- Validation: M179-M188
- Safety: M189-M201
- Downlink: M210-M213
- Composition: M226-M231
- Ports: M016-M023

### Files Modified
- `test-requirements-map.yaml` - Rewritten
- `tests/test_schema_interpreter.py` - Updated docstrings

### Next Steps
1. Consider adding spec requirements for prototype extensions (encodings, downlink_commands)
2. Increase test coverage for uncovered M/R/O requirements
3. Keep test-requirements-map.yaml in sync as new tests are added
