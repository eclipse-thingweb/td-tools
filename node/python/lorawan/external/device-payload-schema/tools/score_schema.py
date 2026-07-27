#!/usr/bin/env python3
"""
score_schema.py - Quality scoring tool for payload schemas.

Validates schemas and calculates quality tier (Bronze/Silver/Gold/Platinum).

Usage:
    python tools/score_schema.py schema.yaml
    python tools/score_schema.py schema.yaml --verbose
    python tools/score_schema.py schemas/ --all --report score-report.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import yaml
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from schema_interpreter import SchemaInterpreter
from validate_schema import validate_schema, ValidationResult


@dataclass
class ScoringResult:
    """Result of schema quality scoring."""
    schema_path: str
    timestamp: str
    score: float
    tier: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_schema(path: str) -> Tuple[Dict[str, Any], List[str]]:
    """Load and parse YAML schema file."""
    errors = []
    try:
        with open(path, 'r') as f:
            schema = yaml.safe_load(f)
        if not isinstance(schema, dict):
            errors.append("Schema must be a YAML dictionary")
            return {}, errors
        return schema, errors
    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
        return {}, errors
    except FileNotFoundError:
        errors.append(f"File not found: {path}")
        return {}, errors


def check_schema_valid(schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate schema structure using validate_schema."""
    result = validate_schema(schema)
    return result.schema_valid, result.schema_errors


def check_test_vectors_exist(schema: Dict[str, Any]) -> Tuple[bool, int, List[str]]:
    """Check if schema has test vectors and count them."""
    vectors = schema.get('test_vectors', [])
    count = len(vectors)
    issues = []
    
    if count == 0:
        issues.append("No test vectors defined")
        return False, 0, issues
    
    if count < 3:
        issues.append(f"Only {count} test vectors (recommend at least 3)")
    
    for i, tv in enumerate(vectors):
        if 'payload' not in tv:
            issues.append(f"Test vector {i}: missing 'payload'")
        if 'expected' not in tv:
            issues.append(f"Test vector {i}: missing 'expected'")
    
    return count >= 1, count, issues


def run_python_tests(schema: Dict[str, Any]) -> Tuple[bool, int, int, List[str]]:
    """Run test vectors through Python interpreter."""
    vectors = schema.get('test_vectors', [])
    if not vectors:
        return False, 0, 0, ["No test vectors to run"]
    
    try:
        interpreter = SchemaInterpreter(schema)
    except Exception as e:
        return False, 0, 0, [f"Failed to create interpreter: {e}"]
    
    passed = 0
    failed = 0
    errors = []
    
    for i, tv in enumerate(vectors):
        tv_name = tv.get('name', f'test_{i}')
        payload_hex = tv.get('payload', '').replace(' ', '')
        expected = tv.get('expected', {})
        fport = tv.get('fPort') or tv.get('fport')
        
        try:
            payload_bytes = bytes.fromhex(payload_hex)
            result = interpreter.decode(payload_bytes, fPort=fport)
            
            if not result.success:
                failed += 1
                errors.append(f"{tv_name}: decode failed - {result.errors}")
                continue
            
            # Compare expected values
            all_match = True
            for key, exp_val in expected.items():
                actual_val = result.data.get(key)
                if actual_val is None:
                    all_match = False
                    errors.append(f"{tv_name}: missing field '{key}'")
                elif isinstance(exp_val, float):
                    if abs(actual_val - exp_val) > 0.01:
                        all_match = False
                        errors.append(f"{tv_name}: {key} = {actual_val}, expected {exp_val}")
                elif actual_val != exp_val:
                    all_match = False
                    errors.append(f"{tv_name}: {key} = {actual_val}, expected {exp_val}")
            
            if all_match:
                passed += 1
            else:
                failed += 1
                
        except Exception as e:
            failed += 1
            errors.append(f"{tv_name}: exception - {e}")
    
    return failed == 0, passed, failed, errors


def run_js_tests(schema: Dict[str, Any], schema_path: str) -> Tuple[bool, List[str]]:
    """Generate JS codec and run test vectors through Node.js."""
    vectors = schema.get('test_vectors', [])
    if not vectors:
        return False, ["No test vectors for JS validation"]
    
    try:
        from generate_ts013_codec import TS013Generator
        gen = TS013Generator(schema)
        js_code = gen.generate()
    except Exception as e:
        return False, [f"Failed to generate JS codec: {e}"]
    
    # Create test runner
    test_cases = []
    for i, tv in enumerate(vectors):
        tv_name = tv.get('name', f'test_{i}')
        payload_hex = tv.get('payload', '').replace(' ', '')
        expected = tv.get('expected', {})
        fport = tv.get('fPort') or tv.get('fport') or 1
        
        test_cases.append({
            'name': tv_name,
            'payload': payload_hex,
            'expected': expected,
            'fPort': fport
        })
    
    js_test = f'''
{js_code}

const tests = {json.dumps(test_cases)};
let passed = 0, failed = 0;
const errors = [];

for (const t of tests) {{
    try {{
        const bytes = [];
        for (let i = 0; i < t.payload.length; i += 2) {{
            bytes.push(parseInt(t.payload.substr(i, 2), 16));
        }}
        const result = decodeUplink({{ bytes, fPort: t.fPort }});
        
        if (result.errors && result.errors.length > 0) {{
            failed++;
            errors.push(t.name + ': ' + result.errors.join(', '));
            continue;
        }}
        
        let allMatch = true;
        for (const [key, expVal] of Object.entries(t.expected)) {{
            const actVal = result.data[key];
            if (actVal === undefined) {{
                allMatch = false;
                errors.push(t.name + ': missing ' + key);
            }} else if (typeof expVal === 'number') {{
                if (Math.abs(actVal - expVal) > 0.01) {{
                    allMatch = false;
                    errors.push(t.name + ': ' + key + '=' + actVal + ', expected ' + expVal);
                }}
            }} else if (actVal !== expVal) {{
                allMatch = false;
                errors.push(t.name + ': ' + key + '=' + actVal + ', expected ' + expVal);
            }}
        }}
        
        if (allMatch) passed++;
        else failed++;
    }} catch (e) {{
        failed++;
        errors.push(t.name + ': ' + e.message);
    }}
}}

console.log(JSON.stringify({{ passed, failed, errors }}));
'''
    
    # Run with Node.js
    try:
        result = subprocess.run(
            ['node', '-e', js_test],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False, [f"Node.js error: {result.stderr}"]
        
        output = json.loads(result.stdout.strip())
        js_errors = output.get('errors', [])
        
        if output['failed'] == 0:
            return True, []
        else:
            return False, js_errors
            
    except FileNotFoundError:
        return False, ["Node.js not found - skipping JS validation"]
    except subprocess.TimeoutExpired:
        return False, ["JS test timeout"]
    except json.JSONDecodeError:
        return False, ["Failed to parse JS test output"]
    except Exception as e:
        return False, [f"JS test error: {e}"]


def analyze_branch_coverage(schema: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Analyze test vector coverage of switch/flagged branches."""
    vectors = schema.get('test_vectors', [])
    if not vectors:
        return 0.0, ["No test vectors for branch analysis"]
    
    # Collect all branches in schema
    branches = set()
    uncovered = []
    
    def scan_fields(fields: List[Dict], prefix: str = ''):
        for field in fields:
            # Switch/match branches
            if 'match' in field or field.get('type') == 'match':
                match_def = field.get('match', field)
                on_field = match_def.get('on', match_def.get('field', ''))
                cases = match_def.get('cases', {})
                for case_val in cases.keys():
                    branches.add(f"switch:{on_field}={case_val}")
            
            # Flagged groups
            if 'flagged' in field:
                fg = field['flagged']
                flag_field = fg.get('field', '')
                for group in fg.get('groups', []):
                    bit = group.get('bit', 0)
                    branches.add(f"flagged:{flag_field}[{bit}]")
            
            # Recurse into nested structures
            if 'fields' in field:
                scan_fields(field['fields'], prefix)
            if 'byte_group' in field:
                bg = field['byte_group']
                bg_fields = bg if isinstance(bg, list) else bg.get('fields', [])
                scan_fields(bg_fields, prefix)
    
    # Scan top-level and port-specific fields
    if 'fields' in schema:
        scan_fields(schema['fields'])
    if 'ports' in schema:
        for port_def in schema['ports'].values():
            if isinstance(port_def, dict) and 'fields' in port_def:
                scan_fields(port_def['fields'])
    
    if not branches:
        return 1.0, []  # No branches = 100% coverage
    
    # Track which flag values are tested
    tested_flags = set()
    try:
        interpreter = SchemaInterpreter(schema)
        for tv in vectors:
            payload_hex = tv.get('payload', '').replace(' ', '')
            fport = tv.get('fPort') or tv.get('fport')
            try:
                payload_bytes = bytes.fromhex(payload_hex)
                result = interpreter.decode(payload_bytes, fPort=fport)
                # Track flag values from expected or decoded data
                expected = tv.get('expected', {})
                if 'flags' in expected:
                    tested_flags.add(expected['flags'])
                elif result.success and 'flags' in result.data:
                    tested_flags.add(result.data['flags'])
            except:
                pass
    except:
        pass
    
    # Calculate coverage based on branch testing
    if branches:
        # For flagged schemas: check if key flag combinations are tested
        # flags=0 (none), individual bits, all bits
        flagged_branches = [b for b in branches if b.startswith('flagged:')]
        if flagged_branches:
            # Check for: no flags (0), individual flags, combined flags
            has_no_flags = 0 in tested_flags
            has_all_flags = any(f >= 3 for f in tested_flags)  # At least 2 bits set
            has_individual = len(tested_flags) >= 2
            
            if has_no_flags and has_all_flags and has_individual and len(vectors) >= 5:
                coverage = 1.0
            elif has_all_flags and has_individual and len(vectors) >= 3:
                coverage = 0.9
            elif len(vectors) >= 3:
                coverage = 0.8
            else:
                coverage = 0.5
        else:
            coverage = 0.9 if len(vectors) >= 3 else 0.5
    else:
        coverage = 1.0
    
    # Note: detailed branch tracking would require interpreter instrumentation
    # For now, use flag-based heuristic above
    
    return coverage, uncovered


STANDARD_SENSOR_IPSO = {
    # Temperature & Environment
    'temperature': 3303,
    'humidity': 3304,
    'pressure': 3323,
    'barometer': 3315,
    'altitude': 3321,
    'depth': 3319,
    
    # Light
    'illuminance': 3301,
    'light': 3301,
    'lux': 3301,
    
    # Electrical
    'voltage': 3316,
    'battery': 3316,
    'current': 3317,
    'power': 3328,
    'energy': 3331,
    'frequency': 3318,
    'powerfactor': 3329,
    
    # Distance & Position
    'distance': 3330,
    'level': 3319,
    
    # Gas & Air Quality
    'co2': 3325,
    'concentration': 3325,
    'conductivity': 3327,
    'acidity': 3326,
    'ph': 3326,
    'loudness': 3324,
    'sound': 3324,
    'noise': 3324,
    
    # Location
    'gps': 3336,
    'location': 3336,
    'latitude': 3336,
    'longitude': 3336,
    
    # Motion sensors
    'accelerometer': 3313,
    'acceleration': 3313,
    'gyroscope': 3334,
    'gyro': 3334,
    'magnetometer': 3314,
    'compass': 3332,
    'direction': 3332,
    'heading': 3332,
    
    # Control & Actuators
    'setpoint': 3308,
    'target': 3308,
    'valve': 3337,
    'positioner': 3337,
    'valveposition': 3337,
    'openness': 3337,
    'dimmer': 3343,
    'actuator': 3306,
    
    # Presence & Input
    'presence': 3302,
    'motion': 3302,
    'occupancy': 3302,
    'pir': 3302,
    'button': 3347,
    'switch': 3342,
    
    # Other
    'load': 3322,
    'weight': 3322,
    'percentage': 3320,
    'digital': 3200,
    'analog': 3202,
    'generic': 3300,
}

SENML_UNITS = {
    # Temperature & Environment
    'temperature': 'Cel',
    'humidity': '%RH',
    'pressure': 'Pa',
    'barometer': 'Pa',
    'altitude': 'm',
    'depth': 'm',
    
    # Light
    'illuminance': 'lx',
    'light': 'lx',
    'lux': 'lx',
    
    # Electrical
    'voltage': 'V',
    'battery': 'V',
    'current': 'A',
    'power': 'W',
    'energy': 'J',
    'frequency': 'Hz',
    
    # Distance
    'distance': 'm',
    'level': 'm',
    
    # Gas & Sound
    'co2': 'ppm',
    'concentration': 'ppm',
    'loudness': 'dB',
    'sound': 'dB',
    'noise': 'dB',
    
    # Location
    'latitude': 'lat',
    'longitude': 'lon',
    
    # Control
    'setpoint': 'Cel',
    'target': 'Cel',
    'valve': '%',
    'openness': '%',
    'dimmer': '%',
    'percentage': '%',
    
    # Weight
    'load': 'kg',
    'weight': 'kg',
    
    # Direction
    'compass': 'deg',
    'direction': 'deg',
    'heading': 'deg',
}


def check_semantic_annotations(schema: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Check completeness of semantic annotations for standard output formats."""
    results = {
        'total_fields': 0,
        'ipso_mapped': 0,
        'ipso_missing': [],
        'senml_mapped': 0,
        'senml_missing': [],
        'semantic_mapped': 0,
        'detectable_sensors': 0,
    }
    recommendations = []
    
    def scan_fields(fields: List[Dict], prefix: str = ''):
        for field in fields:
            field_name = field.get('name', '')
            full_name = f"{prefix}{field_name}" if prefix else field_name
            field_type = str(field.get('type', '')).lower()
            
            # Handle flagged groups (can be standalone or with type)
            if 'flagged' in field:
                fg = field['flagged']
                for group in fg.get('groups', []):
                    if 'fields' in group:
                        scan_fields(group['fields'], prefix)
                continue
            
            # Handle nested structures
            if field_type in ('object', 'match'):
                if 'fields' in field:
                    scan_fields(field['fields'], f"{full_name}.")
                if 'cases' in field:
                    for case_def in field.get('cases', {}).values():
                        if isinstance(case_def, dict) and 'fields' in case_def:
                            scan_fields(case_def['fields'], f"{full_name}.")
                        elif isinstance(case_def, list):
                            scan_fields(case_def, f"{full_name}.")
                continue
            
            # Skip raw/internal/component fields
            if (field_name.startswith('_') or 
                field_name.endswith('_raw') or
                field_name.endswith('Raw') or
                field_name.endswith('Low') or
                field_name.endswith('High')):
                continue
            
            results['total_fields'] += 1
            
            name_lower = field_name.lower()
            detected_sensor = None
            for keyword, ipso_id in STANDARD_SENSOR_IPSO.items():
                if keyword in name_lower:
                    detected_sensor = (keyword, ipso_id)
                    results['detectable_sensors'] += 1
                    break
            
            has_ipso = 'ipso' in field
            has_senml = 'senml' in field
            has_semantic = 'semantic' in field
            
            if has_ipso:
                results['ipso_mapped'] += 1
            elif detected_sensor:
                results['ipso_missing'].append(
                    f"{full_name}: add ipso: {{object: {detected_sensor[1]}}}"
                )
            
            if has_senml:
                results['senml_mapped'] += 1
            elif detected_sensor and detected_sensor[0] in SENML_UNITS:
                results['senml_missing'].append(
                    f"{full_name}: add senml: {{unit: \"{SENML_UNITS[detected_sensor[0]]}\"}}"
                )
            
            if has_semantic:
                results['semantic_mapped'] += 1
    
    fields = schema.get('fields', [])
    scan_fields(fields)
    
    if 'ports' in schema:
        for port_name, port_def in schema['ports'].items():
            if isinstance(port_def, dict) and 'fields' in port_def:
                scan_fields(port_def['fields'], f"port{port_name}.")
    
    if results['ipso_missing']:
        recommendations.append(f"Add IPSO mappings for {len(results['ipso_missing'])} standard sensor fields")
    if results['senml_missing']:
        recommendations.append(f"Add SenML units for {len(results['senml_missing'])} fields")
    
    return results, recommendations


def check_edge_cases(schema: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Check which edge cases are covered by test vectors."""
    vectors = schema.get('test_vectors', [])
    
    covered = []
    missing = []
    
    # Analyze test vector payloads for edge case patterns
    has_zero = False
    has_max = False
    has_negative = False
    has_min_payload = False
    
    for tv in vectors:
        payload_hex = tv.get('payload', '').replace(' ', '')
        expected = tv.get('expected', {})
        desc = tv.get('description', '').lower()
        name = tv.get('name', '').lower()
        
        # Check payload patterns
        if payload_hex == '00' * (len(payload_hex) // 2):
            has_zero = True
        if 'ff' in payload_hex.lower():
            has_max = True
        if len(payload_hex) <= 12:  # 6 bytes or less is minimal
            has_min_payload = True
        
        # Check expected values
        for val in expected.values():
            if isinstance(val, (int, float)):
                if val == 0:
                    has_zero = True
                if val < 0:
                    has_negative = True
        
        # Check descriptions and names
        if 'zero' in desc or 'zero' in name:
            has_zero = True
        if 'max' in desc or 'maximum' in desc or 'max' in name:
            has_max = True
        if 'negative' in desc or 'negative' in name:
            has_negative = True
        if 'minimum' in desc or 'minimum' in name or 'min_payload' in name:
            has_min_payload = True
    
    if has_zero:
        covered.append('zero')
    else:
        missing.append('zero values')
    
    if has_max:
        covered.append('max')
    else:
        missing.append('maximum values')
    
    if has_negative:
        covered.append('negative')
    else:
        missing.append('negative values')
    
    if has_min_payload:
        covered.append('min_payload')
    else:
        missing.append('minimum payload length')
    
    return covered, missing


def calculate_score(results: Dict[str, Any]) -> Tuple[float, str]:
    """Calculate quality score and tier."""
    
    weights = {
        'schema_valid': 12,
        'has_test_vectors': 8,
        'python_tests_pass': 20,
        'js_tests_pass': 15,
        'branch_coverage': 12,
        'edge_cases': 8,
        'test_count': 5,
        'ipso_coverage': 7,
        'senml_coverage': 7,
        'semantic_coverage': 6,
    }
    
    score = 0
    max_score = sum(weights.values())
    
    # Schema valid (12 points)
    if results.get('schema_valid'):
        score += weights['schema_valid']
    
    # Has test vectors (8 points)
    if results.get('has_test_vectors'):
        score += weights['has_test_vectors']
    
    # Python tests pass (20 points)
    if results.get('python_tests_pass'):
        score += weights['python_tests_pass']
    
    # JS tests pass (15 points)
    if results.get('js_tests_pass'):
        score += weights['js_tests_pass']
    
    # Branch coverage (12 points, scaled)
    coverage = results.get('branch_coverage', 0)
    score += int(weights['branch_coverage'] * coverage)
    
    # Edge cases (8 points, scaled by coverage)
    edge_covered = results.get('edge_cases_covered', [])
    edge_missing = results.get('edge_cases_missing', [])
    if edge_covered:
        edge_ratio = len(edge_covered) / (len(edge_covered) + len(edge_missing))
        score += int(weights['edge_cases'] * edge_ratio)
    
    # Test count bonus (5 points for 5+ tests)
    test_count = results.get('test_count', 0)
    if test_count >= 5:
        score += weights['test_count']
    elif test_count >= 3:
        score += weights['test_count'] // 2
    
    # Semantic annotation scoring (20 points total)
    semantic = results.get('semantic_annotations', {})
    detectable = semantic.get('detectable_sensors', 0)
    total_fields = semantic.get('total_fields', 0)
    
    if detectable > 0:
        # IPSO coverage (7 points) - ratio of mapped to detectable, capped at 1.0
        ipso_mapped = semantic.get('ipso_mapped', 0)
        ipso_ratio = min(1.0, ipso_mapped / detectable)
        score += int(weights['ipso_coverage'] * ipso_ratio)
        
        # SenML coverage (7 points) - ratio of mapped to detectable, capped at 1.0
        senml_mapped = semantic.get('senml_mapped', 0)
        senml_ratio = min(1.0, senml_mapped / detectable)
        score += int(weights['senml_coverage'] * senml_ratio)
        
        # Semantic/normalized coverage (6 points)
        semantic_mapped = semantic.get('semantic_mapped', 0)
        semantic_ratio = min(1.0, semantic_mapped / detectable)
        score += int(weights['semantic_coverage'] * semantic_ratio)
    elif total_fields > 0:
        # Has fields but no standard sensors - partial credit based on any annotations
        ipso_mapped = semantic.get('ipso_mapped', 0)
        senml_mapped = semantic.get('senml_mapped', 0)
        semantic_mapped = semantic.get('semantic_mapped', 0)
        
        if ipso_mapped > 0:
            score += weights['ipso_coverage']
        if senml_mapped > 0:
            score += weights['senml_coverage']
        if semantic_mapped > 0:
            score += weights['semantic_coverage']
    else:
        # No fields at all - award full semantic points (edge case)
        score += weights['ipso_coverage'] + weights['senml_coverage'] + weights['semantic_coverage']
    
    pct = (score / max_score) * 100
    
    if pct >= 95:
        tier = 'PLATINUM'
    elif pct >= 85:
        tier = 'GOLD'
    elif pct >= 70:
        tier = 'SILVER'
    else:
        tier = 'BRONZE'
    
    return pct, tier


def generate_recommendations(results: Dict[str, Any]) -> List[str]:
    """Generate improvement recommendations."""
    recs = []
    
    if not results.get('schema_valid'):
        recs.append("Fix schema validation errors")
    
    if not results.get('has_test_vectors'):
        recs.append("Add at least 3 test vectors with payload and expected values")
    elif results.get('test_count', 0) < 3:
        recs.append("Add more test vectors (recommend at least 3)")
    
    if not results.get('python_tests_pass'):
        recs.append("Fix failing Python interpreter tests")
    
    if not results.get('js_tests_pass'):
        recs.append("Fix JS codec generation or test failures")
    
    edge_missing = results.get('edge_cases_missing', [])
    for missing in edge_missing[:3]:  # Top 3
        recs.append(f"Add test vector for {missing}")
    
    if results.get('branch_coverage', 1.0) < 0.8:
        recs.append("Add test vectors covering all switch/flagged branches")
    
    # Semantic annotation recommendations
    semantic = results.get('semantic_annotations', {})
    ipso_missing = semantic.get('ipso_missing', [])
    senml_missing = semantic.get('senml_missing', [])
    
    if ipso_missing:
        recs.append(f"Add IPSO object mappings for standard sensors ({len(ipso_missing)} fields)")
        for rec in ipso_missing[:2]:
            recs.append(f"  → {rec}")
    
    if senml_missing:
        recs.append(f"Add SenML units for standard sensors ({len(senml_missing)} fields)")
        for rec in senml_missing[:2]:
            recs.append(f"  → {rec}")
    
    return recs


def score_schema(schema_path: str, verbose: bool = False) -> ScoringResult:
    """Run all quality scoring checks on a schema."""
    
    timestamp = datetime.now().astimezone().isoformat()
    results = {}
    all_errors = []
    
    # Load schema
    schema, load_errors = load_schema(schema_path)
    if load_errors:
        return ScoringResult(
            schema_path=schema_path,
            timestamp=timestamp,
            score=0,
            tier='FAILED',
            details={'load_errors': load_errors},
            recommendations=['Fix YAML syntax errors']
        )
    
    # 1. Schema validation
    schema_valid, schema_errors = check_schema_valid(schema)
    results['schema_valid'] = schema_valid
    results['schema_errors'] = schema_errors
    all_errors.extend(schema_errors)
    
    if verbose and schema_errors:
        print(f"Schema errors: {schema_errors}")
    
    # 2. Test vectors
    has_vectors, test_count, vector_issues = check_test_vectors_exist(schema)
    results['has_test_vectors'] = has_vectors
    results['test_count'] = test_count
    results['vector_issues'] = vector_issues
    
    if verbose:
        print(f"Test vectors: {test_count}")
    
    # 3. Python tests
    py_pass, py_passed, py_failed, py_errors = run_python_tests(schema)
    results['python_tests_pass'] = py_pass
    results['python_passed'] = py_passed
    results['python_failed'] = py_failed
    results['python_errors'] = py_errors
    all_errors.extend(py_errors)
    
    if verbose:
        print(f"Python tests: {py_passed} passed, {py_failed} failed")
    
    # 4. JS cross-validation
    js_pass, js_errors = run_js_tests(schema, schema_path)
    results['js_tests_pass'] = js_pass
    results['js_errors'] = js_errors
    
    if verbose:
        print(f"JS tests: {'PASS' if js_pass else 'FAIL'}")
        if js_errors:
            for e in js_errors[:3]:
                print(f"  {e}")
    
    # 5. Branch coverage
    coverage, coverage_issues = analyze_branch_coverage(schema)
    results['branch_coverage'] = coverage
    results['coverage_issues'] = coverage_issues
    
    if verbose:
        print(f"Branch coverage: {coverage*100:.0f}%")
    
    # 6. Edge cases
    edge_covered, edge_missing = check_edge_cases(schema)
    results['edge_cases_covered'] = edge_covered
    results['edge_cases_missing'] = edge_missing
    
    if verbose:
        print(f"Edge cases: {edge_covered}, missing: {edge_missing}")
    
    # 7. Semantic annotations (IPSO, SenML, TTN normalization)
    semantic_results, semantic_recs = check_semantic_annotations(schema)
    results['semantic_annotations'] = semantic_results
    
    if verbose:
        detected = semantic_results.get('detectable_sensors', 0)
        ipso = semantic_results.get('ipso_mapped', 0)
        senml = semantic_results.get('senml_mapped', 0)
        print(f"Semantic: {detected} sensors detected, {ipso} IPSO mapped, {senml} SenML mapped")
    
    # Calculate score and tier
    score, tier = calculate_score(results)
    
    # Generate recommendations
    recommendations = generate_recommendations(results)
    
    return ScoringResult(
        schema_path=schema_path,
        timestamp=timestamp,
        score=round(score, 1),
        tier=tier,
        details=results,
        recommendations=recommendations
    )


def main():
    parser = argparse.ArgumentParser(
        description='Quality scoring tool for payload schemas'
    )
    parser.add_argument('path', help='Schema file or directory')
    parser.add_argument('--all', action='store_true', help='Process all schemas in directory')
    parser.add_argument('--report', '-r', help='Output JSON report file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--quiet', '-q', action='store_true', help='Only output tier')
    
    args = parser.parse_args()
    
    path = Path(args.path)
    results = []
    
    if path.is_file():
        result = score_schema(str(path), verbose=args.verbose)
        results.append(result)
    elif path.is_dir() and args.all:
        for yaml_file in sorted(path.rglob('*.yaml')):
            if verbose := args.verbose:
                print(f"\n=== {yaml_file} ===")
            result = score_schema(str(yaml_file), verbose=args.verbose)
            results.append(result)
    else:
        print(f"Error: {path} is not a file. Use --all for directories.")
        sys.exit(1)
    
    # Output results
    if args.report:
        report = {
            'timestamp': datetime.now().astimezone().isoformat(),
            'schemas': [r.to_dict() for r in results]
        }
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report written to {args.report}")
    
    # Console output
    for r in results:
        if args.quiet:
            print(f"{r.tier}")
        else:
            tier_color = {
                'PLATINUM': '\033[95m',  # Magenta
                'GOLD': '\033[93m',      # Yellow
                'SILVER': '\033[37m',    # White
                'BRONZE': '\033[33m',    # Orange
                'FAILED': '\033[91m',    # Red
            }.get(r.tier, '')
            reset = '\033[0m'
            
            print(f"\n{Path(r.schema_path).name}: {tier_color}{r.tier}{reset} ({r.score:.1f}%)")
            
            if r.recommendations and not args.quiet:
                print("Recommendations:")
                for rec in r.recommendations[:5]:
                    print(f"  - {rec}")
    
    # Exit code: 0 if all SILVER+, 1 otherwise
    all_pass = all(r.tier in ('PLATINUM', 'GOLD', 'SILVER') for r in results)
    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
