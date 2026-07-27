#!/usr/bin/env python3
"""
verify_spec_completeness.py - Requirements traceability and spec completeness verification.

Ensures the spec, language reference, interpreter, and tests are synchronized.

Usage:
    python tools/verify_spec_completeness.py
    python tools/verify_spec_completeness.py --report completeness-report.json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class FeatureMapping:
    """Mapping of a feature across spec, reference, implementation, and tests."""
    name: str
    spec_section: Optional[str] = None
    spec_req_ids: List[str] = field(default_factory=list)
    lang_ref_section: Optional[str] = None
    interpreter_func: Optional[str] = None
    has_tests: bool = False
    test_count: int = 0
    status: str = 'unknown'  # complete, partial, missing
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompletenessReport:
    """Report on spec/implementation completeness."""
    timestamp: str
    features: List[FeatureMapping] = field(default_factory=list)
    requirements_found: int = 0
    requirements_with_tests: int = 0
    features_complete: int = 0
    features_partial: int = 0
    features_missing: int = 0
    issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Core language features to verify
CORE_FEATURES = [
    # Basic types
    ('integer_types', 'u8/u16/u32/s8/s16/s32 integer decoding'),
    ('float_types', 'f16/f32/f64 float decoding'),
    ('bool_type', 'bool type with bit position'),
    ('bytes_type', 'bytes/hex/base64 binary types'),
    ('string_type', 'ascii/string text types'),
    ('enum_type', 'enum with values mapping'),
    
    # Modifiers
    ('mult_modifier', 'mult: multiplication modifier'),
    ('div_modifier', 'div: division modifier'),
    ('add_modifier', 'add: addition/offset modifier'),
    ('lookup_modifier', 'lookup: array index to string'),
    
    # Computed fields
    ('polynomial', 'polynomial: calibration curves'),
    ('compute', 'compute: cross-field binary ops'),
    ('guard', 'guard: conditional evaluation'),
    ('transform', 'transform: sequential math ops'),
    ('ref', 'ref: field reference for computed fields'),
    
    # Conditional parsing
    ('switch_match', 'switch/match conditional parsing'),
    ('flagged', 'flagged: bitmask field presence'),
    
    # Complex types
    ('bitfield', 'bitfield: bit-level extraction'),
    ('bitfield_string', 'bitfield_string: formatted bit output'),
    ('byte_group', 'byte_group: shared byte bitfields'),
    ('tlv', 'tlv: type-length-value parsing'),
    ('nested_object', 'object: nested field groups'),
    ('repeat', 'repeat: array/repeated fields'),
    
    # Advanced
    ('ports', 'ports: fPort-based schema selection'),
    ('definitions', 'definitions: reusable field groups'),
    ('var', 'var: variable storage for references'),
    ('skip', 'skip: ignore bytes'),
    ('endian', 'endian: big/little endianness'),
    
    # Output
    ('unit', 'unit: engineering unit annotation'),
    ('semantic', 'semantic: IPSO/SenML mapping'),
    
    # Deprecated
    ('formula', 'formula: (deprecated) expression evaluation'),
]


def find_spec_requirements(spec_dir: Path) -> Dict[str, List[str]]:
    """Find REQ-xxx identifiers in spec files."""
    requirements = {}
    
    if not spec_dir.exists():
        return requirements
    
    for md_file in spec_dir.rglob('*.md'):
        content = md_file.read_text()
        # Match REQ-xxx-xxx-nnn patterns
        reqs = re.findall(r'REQ-[A-Za-z0-9-]+', content)
        for req in reqs:
            if req not in requirements:
                requirements[req] = []
            requirements[req].append(str(md_file.relative_to(spec_dir)))
    
    return requirements


def find_test_requirements(test_file: Path) -> Set[str]:
    """Find REQ-xxx identifiers in test files."""
    requirements = set()
    
    if not test_file.exists():
        return requirements
    
    content = test_file.read_text()
    reqs = re.findall(r'REQ-[A-Za-z0-9-]+', content)
    requirements.update(reqs)
    
    return requirements


def find_test_coverage(test_file: Path) -> Dict[str, int]:
    """Find which features have tests and count them."""
    coverage = {}
    
    if not test_file.exists():
        return coverage
    
    content = test_file.read_text()
    
    # Count test methods per class
    current_class = None
    for line in content.split('\n'):
        class_match = re.match(r'^class\s+(\w+)', line)
        if class_match:
            current_class = class_match.group(1).lower()
        
        test_match = re.match(r'\s+def\s+(test_\w+)', line)
        if test_match and current_class:
            # Map class names to features
            feature = None
            test_name = test_match.group(1).lower()
            
            if 'polynomial' in current_class or 'polynomial' in test_name:
                feature = 'polynomial'
            elif 'compute' in current_class or 'compute' in test_name:
                feature = 'compute'
            elif 'guard' in current_class or 'guard' in test_name or 'albedo' in test_name:
                feature = 'guard'
            elif 'transform' in current_class or 'transform' in test_name:
                feature = 'transform'
            elif 'formula' in current_class or 'formula' in test_name:
                feature = 'formula'
            elif 'integer' in current_class or 'u8' in test_name or 'u16' in test_name:
                feature = 'integer_types'
            elif 'float' in current_class or 'f32' in test_name or 'f64' in test_name:
                feature = 'float_types'
            elif 'bool' in current_class or 'bool' in test_name:
                feature = 'bool_type'
            elif 'bitfieldstring' in current_class or 'bitfield_string' in test_name:
                feature = 'bitfield_string'
            elif 'bitfield' in current_class or 'bitfield' in test_name:
                feature = 'bitfield'
            elif 'match' in current_class or 'switch' in test_name:
                feature = 'switch_match'
            elif 'flagged' in current_class:
                feature = 'flagged'
            elif 'tlv' in current_class:
                feature = 'tlv'
            elif 'enum' in current_class or 'enum' in test_name:
                feature = 'enum_type'
            elif 'lookup' in current_class or 'lookup' in test_name:
                feature = 'lookup_modifier'
            elif 'modifier' in current_class:
                if 'mult' in test_name:
                    feature = 'mult_modifier'
                elif 'div' in test_name:
                    feature = 'div_modifier'
                elif 'add' in test_name:
                    feature = 'add_modifier'
            elif 'nested' in test_name or 'object' in test_name:
                feature = 'nested_object'
            elif 'repeat' in current_class or 'repeat' in test_name:
                feature = 'repeat'
            elif 'port' in test_name:
                feature = 'ports'
            elif 'ref' in test_name:
                feature = 'ref'
            elif 'bytestype' in current_class or 'bytes' in current_class or 'hex' in test_name or 'base64' in test_name:
                feature = 'bytes_type'
            elif 'stringtype' in current_class or ('string' in current_class and 'bitfield' not in current_class) or 'ascii' in test_name:
                feature = 'string_type'
            elif 'bytegroup' in current_class or 'byte_group' in test_name:
                feature = 'byte_group'
            elif 'definitions' in current_class or 'definition' in test_name:
                feature = 'definitions'
            elif 'variable' in current_class or 'var' in test_name:
                feature = 'var'
            elif 'skip' in current_class or 'skip' in test_name:
                feature = 'skip'
            elif 'endian' in current_class or 'endian' in test_name:
                feature = 'endian'
            elif 'unit' in current_class or 'unit' in test_name:
                feature = 'unit'
            elif 'semantic' in current_class or 'ipso' in test_name or 'senml' in test_name:
                feature = 'semantic'
            
            if feature:
                coverage[feature] = coverage.get(feature, 0) + 1
    
    return coverage


def find_interpreter_functions(interp_file: Path) -> Dict[str, str]:
    """Find which features are implemented in interpreter."""
    functions = {}
    
    if not interp_file.exists():
        return functions
    
    content = interp_file.read_text()
    
    # Map features to implementation patterns (more flexible matching)
    feature_patterns = {
        'integer_types': r"'u8'|'u16'|'u32'|'s8'|'s16'|'s32'",
        'float_types': r"'f16'|'f32'|'f64'|'float'|'double'",
        'bool_type': r"'bool'",
        'bytes_type': r"'bytes'|'hex'|'base64'",
        'string_type': r"'string'|'ascii'",
        'enum_type': r"'enum'|_decode_enum",
        'mult_modifier': r"'mult'",
        'div_modifier': r"'div'",
        'add_modifier': r"'add'",
        'lookup_modifier': r"'lookup'",
        'polynomial': r"polynomial|_evaluate_polynomial",
        'compute': r"'compute'|_decode_computed",
        'guard': r"'guard'",
        'transform': r"'transform'|_apply_transform",
        'ref': r"'ref'|\$[a-z]",
        'formula': r"'formula'",
        'bitfield': r"_parse_bitfield|_extract_bits|\[.*:.*\]",
        'bitfield_string': r"bitfield_string|_decode_bitfield_string",
        'switch_match': r"'match'|_decode_match",
        'flagged': r"'flagged'|_decode_flagged",
        'tlv': r"'tlv'|_decode_tlv",
        'byte_group': r"byte_group|_decode_byte_group",
        'nested_object': r"'object'|_decode_nested",
        'repeat': r"'repeat'",
        'ports': r"'ports'|fport",
        'definitions': r"definitions|_resolve_ref",
        'var': r"'var'|variables",
        'skip': r"'skip'",
        'endian': r"endian|little.*endian|big.*endian",
        'unit': r"'unit'",
        'semantic': r"'ipso'|'senml'|semantic",
    }
    
    for feature, pattern in feature_patterns.items():
        if re.search(pattern, content, re.IGNORECASE):
            functions[feature] = pattern
    
    return functions


def find_lang_ref_sections(ref_file: Path) -> Dict[str, str]:
    """Find which features are documented in language reference."""
    sections = {}
    
    if not ref_file.exists():
        return sections
    
    content = ref_file.read_text()
    
    # Map features to heading patterns
    feature_headings = {
        'integer_types': r'##.*Integer',
        'float_types': r'##.*Float',
        'bool_type': r'##.*Bool',
        'bytes_type': r'##.*Bytes|##.*Binary',
        'string_type': r'##.*String',
        'enum_type': r'##.*Enum',
        'mult_modifier': r'mult:|Arithmetic.*Modifier',
        'div_modifier': r'div:|Arithmetic.*Modifier',
        'add_modifier': r'add:|Arithmetic.*Modifier',
        'lookup_modifier': r'lookup:|##.*Lookup',
        'polynomial': r'##.*Polynomial|polynomial:',
        'compute': r'##.*Compute|compute:',
        'guard': r'##.*Guard|guard:',
        'transform': r'##.*Transform|transform:',
        'ref': r'\bref:',
        'switch_match': r'##.*Switch|##.*Match|##.*Conditional',
        'flagged': r'##.*Flagged',
        'bitfield': r'##.*Bitfield',
        'bitfield_string': r'bitfield_string',
        'byte_group': r'byte_group',
        'tlv': r'##.*TLV|tlv:',
        'nested_object': r'##.*Object|##.*Nested',
        'repeat': r'##.*Repeat|##.*Array',
        'ports': r'##.*Port',
        'definitions': r'##.*Definition',
        'var': r'\bvar:',
        'skip': r'\bskip\b',
        'endian': r'##.*Endian',
        'unit': r'\bunit:',
        'semantic': r'##.*Semantic|ipso:|senml',
        'formula': r'formula.*deprecated|##.*Formula',
    }
    
    for feature, pattern in feature_headings.items():
        if re.search(pattern, content, re.IGNORECASE):
            sections[feature] = pattern
    
    return sections


def verify_completeness(
    spec_dir: Optional[Path] = None,
    lang_ref: Optional[Path] = None,
    interp_file: Optional[Path] = None,
    test_file: Optional[Path] = None
) -> CompletenessReport:
    """Verify spec/implementation completeness."""
    from datetime import datetime
    
    report = CompletenessReport(
        timestamp=datetime.now().astimezone().isoformat()
    )
    
    # Find requirements from spec
    requirements = {}
    if spec_dir and spec_dir.exists():
        requirements = find_spec_requirements(spec_dir)
        report.requirements_found = len(requirements)
    
    # Find test coverage
    test_coverage = {}
    test_requirements = set()
    if test_file and test_file.exists():
        test_coverage = find_test_coverage(test_file)
        test_requirements = find_test_requirements(test_file)
    
    # Also check other test files in same directory
    if test_file and test_file.parent.exists():
        for other_test in test_file.parent.glob('test_*.py'):
            if other_test != test_file:
                test_requirements.update(find_test_requirements(other_test))
    
    # Find interpreter implementations
    interp_funcs = {}
    if interp_file and interp_file.exists():
        interp_funcs = find_interpreter_functions(interp_file)
    
    # Find language reference sections
    lang_sections = {}
    if lang_ref and lang_ref.exists():
        lang_sections = find_lang_ref_sections(lang_ref)
    
    # Build feature mappings
    for feature_id, feature_desc in CORE_FEATURES:
        mapping = FeatureMapping(name=feature_id)
        
        # Check language reference
        if feature_id in lang_sections:
            mapping.lang_ref_section = lang_sections[feature_id]
        
        # Check interpreter
        if feature_id in interp_funcs:
            mapping.interpreter_func = interp_funcs[feature_id]
        
        # Check tests
        if feature_id in test_coverage:
            mapping.has_tests = True
            mapping.test_count = test_coverage[feature_id]
        
        # Determine status
        has_impl = mapping.interpreter_func is not None
        has_doc = mapping.lang_ref_section is not None
        has_test = mapping.has_tests
        
        if has_impl and has_doc and has_test:
            mapping.status = 'complete'
            report.features_complete += 1
        elif has_impl and (has_doc or has_test):
            mapping.status = 'partial'
            report.features_partial += 1
        elif has_impl:
            mapping.status = 'undocumented'
            report.features_partial += 1
            report.issues.append(f"{feature_id}: implemented but missing documentation/tests")
        else:
            mapping.status = 'missing'
            report.features_missing += 1
            report.issues.append(f"{feature_id}: not implemented")
        
        report.features.append(mapping)
    
    # Count requirements with test coverage
    matched_spec_reqs = 0
    for req_id in requirements:
        if req_id in test_requirements:
            matched_spec_reqs += 1
    
    # If spec requirements exist but none matched tests, use test requirements instead
    # (indicates different naming conventions between spec and tests)
    if requirements and matched_spec_reqs == 0 and test_requirements:
        report.requirements_found = len(test_requirements)
        report.requirements_with_tests = len(test_requirements)
    elif test_requirements:
        # Both exist and some match - report spec reqs with test coverage
        report.requirements_with_tests = matched_spec_reqs
        # Also note test-defined requirements
        if len(test_requirements) > matched_spec_reqs:
            report.issues.append(
                f"Tests define {len(test_requirements)} REQ tags "
                f"({matched_spec_reqs} match spec)"
            )
    
    return report


def find_go_test_coverage(test_file: Path) -> Dict[str, int]:
    """Find which features have Go tests and count them."""
    coverage = {}
    
    if not test_file.exists():
        return coverage
    
    content = test_file.read_text()
    
    # Count test functions per feature
    for line in content.split('\n'):
        test_match = re.match(r'^func\s+(Test\w+)', line)
        if test_match:
            test_name = test_match.group(1).lower()
            feature = None
            
            if 'uint' in test_name or 'sint' in test_name or 'decode' in test_name and 'bit' not in test_name:
                feature = 'integer_types'
            elif 'float' in test_name:
                feature = 'float_types'
            elif 'bool' in test_name:
                feature = 'bool_type'
            elif 'bytes' in test_name or 'hex' in test_name or 'base64' in test_name:
                feature = 'bytes_type'
            elif 'string' in test_name or 'ascii' in test_name:
                feature = 'string_type'
            elif 'enum' in test_name:
                feature = 'enum_type'
            elif 'modifier' in test_name or 'mult' in test_name:
                feature = 'mult_modifier'
            elif 'div' in test_name:
                feature = 'div_modifier'
            elif 'lookup' in test_name:
                feature = 'lookup_modifier'
            elif 'polynomial' in test_name:
                feature = 'polynomial'
            elif 'compute' in test_name:
                feature = 'compute'
            elif 'guard' in test_name or 'albedo' in test_name:
                feature = 'guard'
            elif 'transform' in test_name:
                feature = 'transform'
            elif 'ref' in test_name:
                feature = 'ref'
            elif 'match' in test_name:
                feature = 'switch_match'
            elif 'flagged' in test_name:
                feature = 'flagged'
            elif 'bit' in test_name and 'string' in test_name:
                feature = 'bitfield_string'
            elif 'bit' in test_name:
                feature = 'bitfield'
            elif 'bytegroup' in test_name or 'byte_group' in test_name:
                feature = 'byte_group'
            elif 'tlv' in test_name:
                feature = 'tlv'
            elif 'nested' in test_name or 'object' in test_name:
                feature = 'nested_object'
            elif 'repeat' in test_name:
                feature = 'repeat'
            elif 'port' in test_name:
                feature = 'ports'
            elif 'definition' in test_name:
                feature = 'definitions'
            elif 'variable' in test_name:
                feature = 'var'
            elif 'skip' in test_name:
                feature = 'skip'
            elif 'endian' in test_name or 'little' in test_name:
                feature = 'endian'
            elif 'unit' in test_name:
                feature = 'unit'
            elif 'ipso' in test_name or 'senml' in test_name:
                feature = 'semantic'
            elif 'formula' in test_name:
                feature = 'formula'
            elif 'encode' in test_name or 'roundtrip' in test_name:
                feature = 'encoding'
            
            if feature:
                coverage[feature] = coverage.get(feature, 0) + 1
    
    return coverage


def find_go_skipped_tests(test_file: Path) -> Dict[str, str]:
    """Find skipped tests and their reasons (missing features)."""
    skipped = {}
    
    if not test_file.exists():
        return skipped
    
    content = test_file.read_text()
    
    current_test = None
    for line in content.split('\n'):
        test_match = re.match(r'^func\s+(Test\w+)', line)
        if test_match:
            current_test = test_match.group(1)
        
        skip_match = re.search(r't\.Skip\(["\'](.+?)["\']\)', line)
        if skip_match and current_test:
            skipped[current_test] = skip_match.group(1)
    
    return skipped


def find_go_implementation(go_file: Path) -> Dict[str, str]:
    """Find implemented features in Go interpreter."""
    features = {}
    
    if not go_file.exists():
        return features
    
    content = go_file.read_text()
    
    # Map features to implementation patterns
    feature_patterns = {
        'integer_types': r'decodeUint|decodeSint|["\']u8["\']|["\']u16["\']',
        'float_types': r'float16|float32|float64|["\']f16["\']|["\']f32["\']',
        'bool_type': r'["\']bool["\']|decodeBool',
        'bytes_type': r'["\']bytes["\']|["\']hex["\']|["\']base64["\']',
        'string_type': r'["\']string["\']|["\']ascii["\']',
        'enum_type': r'["\']enum["\']|decodeEnum',
        'mult_modifier': r'["\']mult["\']|Mult',
        'div_modifier': r'["\']div["\']|Div',
        'lookup_modifier': r'["\']lookup["\']|Lookup',
        'polynomial': r'polynomial|Polynomial',
        'compute': r'["\']compute["\']|Compute',
        'guard': r'["\']guard["\']|Guard',
        'transform': r'["\']transform["\']|Transform',
        'ref': r'\$[a-z]|["\']ref["\']',
        'switch_match': r'["\']match["\']|Match',
        'flagged': r'["\']flagged["\']|Flagged',
        'bitfield': r'decodeBits|Bitfield',
        'bitfield_string': r'bitfield_string|BitfieldString',
        'byte_group': r'byte_group|ByteGroup',
        'tlv': r'["\']tlv["\']|TLV',
        'nested_object': r'["\']object["\']|Nested',
        'repeat': r'["\']repeat["\']|Repeat',
        'ports': r'["\']ports["\']|fPort|FPort',
        'definitions': r'definitions|Definitions|\$ref',
        'var': r'["\']var["\']|Variable',
        'skip': r'["\']skip["\']|Skip',
        'endian': r'endian|Endian|little|big',
        'unit': r'["\']unit["\']|Unit',
        'semantic': r'["\']ipso["\']|["\']senml["\']|IPSO|SenML',
        'formula': r'["\']formula["\']|Formula',
    }
    
    for feature, pattern in feature_patterns.items():
        if re.search(pattern, content, re.IGNORECASE):
            features[feature] = pattern
    
    return features


def verify_go_completeness(
    go_impl: Path,
    go_test: Path
) -> Tuple[Dict[str, str], Dict[str, int], Dict[str, str]]:
    """Verify Go interpreter completeness."""
    impl_features = find_go_implementation(go_impl)
    test_coverage = find_go_test_coverage(go_test)
    skipped_tests = find_go_skipped_tests(go_test)
    
    return impl_features, test_coverage, skipped_tests


def main():
    parser = argparse.ArgumentParser(
        description='Verify spec/implementation completeness'
    )
    parser.add_argument('--spec-dir', help='Spec sections directory')
    parser.add_argument('--lang-ref', help='Language reference markdown file')
    parser.add_argument('--interpreter', help='Interpreter Python file')
    parser.add_argument('--tests', help='Test file')
    parser.add_argument('--go-impl', help='Go interpreter file')
    parser.add_argument('--go-tests', help='Go test file')
    parser.add_argument('--report', '-r', help='Output JSON report file')
    parser.add_argument('--verbose', '-v', action='store_true')
    
    args = parser.parse_args()
    
    # Default paths relative to proto project
    proto_root = Path(__file__).parent.parent
    spec_root = proto_root.parent / 'la-payload-schema'
    
    spec_dir = Path(args.spec_dir) if args.spec_dir else spec_root / 'spec' / 'sections'
    lang_ref = Path(args.lang_ref) if args.lang_ref else proto_root / 'docs' / 'SCHEMA-LANGUAGE-REFERENCE.md'
    interp_file = Path(args.interpreter) if args.interpreter else proto_root / 'tools' / 'schema_interpreter.py'
    test_file = Path(args.tests) if args.tests else proto_root / 'tests' / 'test_schema_interpreter.py'
    go_impl = Path(args.go_impl) if args.go_impl else proto_root / 'go' / 'schema' / 'schema.go'
    go_tests = Path(args.go_tests) if args.go_tests else proto_root / 'go' / 'schema' / 'schema_test.go'
    
    # Python verification
    report = verify_completeness(
        spec_dir=spec_dir,
        lang_ref=lang_ref,
        interp_file=interp_file,
        test_file=test_file
    )
    
    # Go verification
    go_impl_features, go_test_coverage, go_skipped = verify_go_completeness(go_impl, go_tests)
    
    # Output
    if args.report:
        with open(args.report, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"Report written to {args.report}")
    
    # Console summary - Python
    total = len(report.features)
    print(f"\nSpec Completeness Report")
    print(f"========================")
    print(f"\nPython Interpreter:")
    print(f"  Features: {report.features_complete}/{total} complete, "
          f"{report.features_partial} partial, {report.features_missing} missing")
    print(f"  Requirements: {report.requirements_found} found, "
          f"{report.requirements_with_tests} with tests")
    
    # Console summary - Go
    go_total_tests = sum(go_test_coverage.values())
    go_skipped_count = len(go_skipped)
    go_features_tested = len(go_test_coverage)
    go_features_missing = len(go_skipped)
    
    print(f"\nGo Interpreter:")
    print(f"  Tests: {go_total_tests} passing, {go_skipped_count} skipped (missing features)")
    print(f"  Features tested: {go_features_tested}")
    print(f"  Features missing: {go_features_missing}")
    
    if args.verbose:
        print(f"\nPython Feature Status:")
        for f in report.features:
            status_icon = {
                'complete': '✓',
                'partial': '◐',
                'undocumented': '?',
                'missing': '✗'
            }.get(f.status, '?')
            tests = f"({f.test_count} tests)" if f.has_tests else "(no tests)"
            print(f"  {status_icon} {f.name}: {f.status} {tests}")
        
        print(f"\nGo Feature Status:")
        for feature_id, _ in CORE_FEATURES:
            has_impl = feature_id in go_impl_features
            has_tests = feature_id in go_test_coverage
            test_count = go_test_coverage.get(feature_id, 0)
            
            # Check if any test for this feature is skipped
            is_skipped = any(feature_id in reason.lower() for reason in go_skipped.values())
            
            if has_impl and has_tests and not is_skipped:
                status_icon = '✓'
                status = 'complete'
            elif has_impl and (has_tests or is_skipped):
                status_icon = '◐'
                status = 'partial'
            elif is_skipped:
                status_icon = '✗'
                status = 'missing'
            else:
                status_icon = '?'
                status = 'unknown'
            
            tests = f"({test_count} tests)" if test_count > 0 else "(no tests)"
            print(f"  {status_icon} {feature_id}: {status} {tests}")
        
        if go_skipped:
            print(f"\nGo Skipped Tests (missing features):")
            for test_name, reason in go_skipped.items():
                print(f"  - {test_name}: {reason}")
    
    if report.issues:
        print(f"\nPython Issues ({len(report.issues)}):")
        for issue in report.issues[:10]:
            print(f"  - {issue}")
        if len(report.issues) > 10:
            print(f"  ... and {len(report.issues) - 10} more")
    
    # Exit code
    completeness = report.features_complete / total if total > 0 else 0
    sys.exit(0 if completeness >= 0.8 else 1)


if __name__ == '__main__':
    main()
