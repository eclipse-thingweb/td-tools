#!/usr/bin/env python3
"""
Schema Preprocessor - Resolves cross-file $ref references.

Inlines external references so existing interpreters work unchanged.

Usage:
    python schema_preprocessor.py input.yaml -o output.yaml
    python schema_preprocessor.py input.yaml --print
    
    # With custom library path
    python schema_preprocessor.py input.yaml -L /path/to/lib -o output.yaml

References supported:
    $ref: "#/definitions/local"                    # Local (passed through)
    $ref: "schemas/library/sensors/env.yaml#/definitions/temp" # Cross-file (resolved)
    $ref: "schemas/library/sensors/env.yaml"                   # Entire file's fields

Field renaming (for multiple same-type sensors):
    # Rename specific fields
    - $ref: "schemas/library/sensors/environmental.yaml#/definitions/temperature_c"
      rename:
        temperature: indoor_temp
    
    # Add prefix to all fields
    - $ref: "schemas/library/sensors/environmental.yaml#/definitions/temperature_c"
      prefix: "outdoor_"
    
    # Combined (prefix applied first, then renames)
    - $ref: "schemas/library/profiles/env-sensor.yaml#/definitions/temp_humidity"
      prefix: "room1_"
      rename:
        room1_temperature: room1_temp  # Override specific field after prefix
"""

import argparse
import copy
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import yaml


class SchemaPreprocessor:
    """Resolves cross-file $ref references in payload schemas."""
    
    def __init__(self, library_paths: Optional[List[Path]] = None):
        self.library_paths = library_paths or []
        self.cache: Dict[str, Dict] = {}
        self.resolution_stack: Set[str] = set()
    
    def process(self, schema_path: Path) -> Dict[str, Any]:
        """Process a schema file, resolving all cross-file references."""
        schema = self._load_yaml(schema_path)
        base_dir = schema_path.parent
        
        processed = self._process_node(schema, base_dir, str(schema_path))
        return processed
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load and cache a YAML file."""
        path_str = str(path.resolve())
        if path_str in self.cache:
            return copy.deepcopy(self.cache[path_str])
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        self.cache[path_str] = data
        return copy.deepcopy(data)
    
    def _resolve_file_path(self, ref_path: str, base_dir: Path) -> Optional[Path]:
        """Resolve a file path, checking library paths."""
        # Try relative to base directory first
        candidate = base_dir / ref_path
        if candidate.exists():
            return candidate.resolve()
        
        # Try library paths
        for lib_path in self.library_paths:
            candidate = lib_path / ref_path
            if candidate.exists():
                return candidate.resolve()
        
        return None
    
    def _resolve_ref(self, ref: str, base_dir: Path, source: str) -> Any:
        """Resolve a $ref, handling both local and cross-file references."""
        if ref.startswith('#/'):
            # Local reference - pass through unchanged
            return {'$ref': ref}
        
        # Parse cross-file reference
        if '#' in ref:
            file_part, fragment = ref.split('#', 1)
        else:
            file_part = ref
            fragment = None
        
        # Resolve file path
        file_path = self._resolve_file_path(file_part, base_dir)
        if not file_path:
            raise ValueError(f"Cannot resolve reference '{ref}' from {source}. "
                           f"File not found: {file_part}")
        
        # Circular reference detection
        ref_key = f"{file_path}#{fragment}" if fragment else str(file_path)
        if ref_key in self.resolution_stack:
            raise ValueError(f"Circular reference detected: {ref_key}")
        
        self.resolution_stack.add(ref_key)
        try:
            # Load referenced file
            ref_schema = self._load_yaml(file_path)
            ref_base_dir = file_path.parent
            
            # Navigate to fragment if specified
            if fragment:
                target = self._navigate_pointer(ref_schema, fragment)
            else:
                # No fragment - return fields array or entire schema
                target = ref_schema.get('fields', ref_schema)
            
            # Recursively process the referenced content
            processed = self._process_node(target, ref_base_dir, str(file_path))
            return processed
            
        finally:
            self.resolution_stack.discard(ref_key)
    
    def _navigate_pointer(self, data: Dict, pointer: str) -> Any:
        """Navigate a JSON pointer (e.g., /definitions/temperature)."""
        if pointer.startswith('/'):
            pointer = pointer[1:]
        
        parts = pointer.split('/')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    raise ValueError(f"Pointer '{pointer}' not found: missing '{part}'")
                current = current[part]
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx]
                except (ValueError, IndexError):
                    raise ValueError(f"Invalid array index in pointer: {part}")
            else:
                raise ValueError(f"Cannot navigate pointer '{pointer}' at '{part}'")
        
        return current
    
    def _apply_renames(self, node: Any, renames: Dict[str, str]) -> Any:
        """Apply field name renames to a resolved node."""
        if not renames:
            return node
        
        if isinstance(node, dict):
            # Check if this is a field with a name
            if 'name' in node and node['name'] in renames:
                node = copy.deepcopy(node)
                old_name = node['name']
                node['name'] = renames[old_name]
                
                # Also update any self-references (e.g., ref: $old_name)
                if 'ref' in node and node['ref'] == f'${old_name}':
                    node['ref'] = f'${renames[old_name]}'
            
            # Recurse into nested structures
            result = {}
            for key, value in node.items():
                result[key] = self._apply_renames(value, renames)
            return result
        
        elif isinstance(node, list):
            return [self._apply_renames(item, renames) for item in node]
        
        else:
            return node
    
    def _apply_prefix(self, node: Any, prefix: str) -> Any:
        """Apply a prefix to all field names in a resolved node."""
        if not prefix:
            return node
        
        if isinstance(node, dict):
            node = copy.deepcopy(node)
            if 'name' in node:
                old_name = node['name']
                node['name'] = f'{prefix}{old_name}'
                
                # Update self-references
                if 'ref' in node and node['ref'] == f'${old_name}':
                    node['ref'] = f'${prefix}{old_name}'
            
            # Recurse
            for key, value in node.items():
                if key != 'name':
                    node[key] = self._apply_prefix(value, prefix)
            return node
        
        elif isinstance(node, list):
            return [self._apply_prefix(item, prefix) for item in node]
        
        else:
            return node

    def _resolve_use(self, use_ref: str, base_dir: Path, source: str,
                      schema_defs: Dict[str, Any] = None) -> Any:
        """
        Resolve a 'use:' shorthand reference.
        
        Supports:
        - use: definition_name         -> local #/definitions/definition_name
        - use: std/sensors/temperature -> standard library path
        - use: ./local.yaml#def_name   -> cross-file reference
        """
        # Local definition (no path separators)
        if '/' not in use_ref and '#' not in use_ref and '.' not in use_ref:
            # Check if it's a local definition
            if schema_defs and use_ref in schema_defs:
                return copy.deepcopy(schema_defs[use_ref])
            # Convert to $ref format
            return self._resolve_ref(f"#/definitions/{use_ref}", base_dir, source)
        
        # Standard library reference (std/...)
        if use_ref.startswith('std/'):
            # Convert std/sensors/temperature -> schemas/library/std/sensors/temperature.yaml
            lib_path = f"schemas/library/{use_ref}.yaml"
            return self._resolve_ref(lib_path, base_dir, source)
        
        # Cross-file reference (file.yaml#fragment or ./file.yaml#fragment)
        if '#' in use_ref:
            file_part, fragment = use_ref.split('#', 1)
            ref = f"{file_part}#/definitions/{fragment}"
        else:
            ref = use_ref
        
        return self._resolve_ref(ref, base_dir, source)
    
    def _process_node(self, node: Any, base_dir: Path, source: str,
                      schema_defs: Dict[str, Any] = None) -> Any:
        """Recursively process a node, resolving references."""
        if isinstance(node, dict):
            # Track schema definitions for 'use:' resolution
            if 'definitions' in node and schema_defs is None:
                schema_defs = node.get('definitions', {})
            
            # Check for $ref (with optional rename/prefix modifiers)
            if '$ref' in node:
                ref = node['$ref']
                renames = node.get('rename', {})
                prefix = node.get('prefix', '')
                
                resolved = self._resolve_ref(ref, base_dir, source)
                
                # Apply prefix first, then specific renames
                if prefix:
                    resolved = self._apply_prefix(resolved, prefix)
                if renames:
                    resolved = self._apply_renames(resolved, renames)
                
                return resolved
            
            # Check for 'use:' shorthand (with optional rename/prefix)
            if 'use' in node:
                use_ref = node['use']
                renames = node.get('rename', {})
                prefix = node.get('prefix', '')
                
                resolved = self._resolve_use(use_ref, base_dir, source, schema_defs)
                
                # Apply prefix first, then specific renames
                if prefix:
                    resolved = self._apply_prefix(resolved, prefix)
                if renames:
                    resolved = self._apply_renames(resolved, renames)
                
                return resolved
            
            # Process all values
            result = {}
            for key, value in node.items():
                result[key] = self._process_node(value, base_dir, source, schema_defs)
            return result
        
        elif isinstance(node, list):
            result = []
            for item in node:
                processed = self._process_node(item, base_dir, source, schema_defs)
                # If a $ref or use: resolved to a list, flatten it
                if isinstance(processed, list):
                    result.extend(processed)
                else:
                    result.append(processed)
            return result
        
        else:
            return node


def main():
    parser = argparse.ArgumentParser(
        description='Preprocess schema files, resolving cross-file $ref references.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process and write to file
    python schema_preprocessor.py my_sensor.yaml -o my_sensor_resolved.yaml
    
    # Process and print to stdout
    python schema_preprocessor.py my_sensor.yaml --print
    
    # With library path
    python schema_preprocessor.py my_sensor.yaml -L ./lib -o output.yaml
        """
    )
    
    parser.add_argument('input', type=Path, help='Input schema file')
    parser.add_argument('-o', '--output', type=Path, help='Output file')
    parser.add_argument('--print', action='store_true', dest='print_output',
                       help='Print to stdout instead of file')
    parser.add_argument('-L', '--library', type=Path, action='append', default=[],
                       help='Library search path (can specify multiple)')
    parser.add_argument('--validate', action='store_true',
                       help='Validate output with schema_interpreter')
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Add default library paths
    lib_paths = list(args.library)
    
    # Add paths relative to input file
    lib_paths.append(args.input.parent)
    lib_paths.append(args.input.parent / 'lib')
    lib_paths.append(args.input.parent.parent)  # Parent of input (for examples/)
    lib_paths.append(args.input.parent.parent / 'lib')
    
    # Add paths relative to this script (for built-in library)
    script_dir = Path(__file__).parent
    lib_paths.append(script_dir / 'lib')
    lib_paths.append(script_dir.parent)  # payload-codec-proto root
    lib_paths.append(script_dir.parent / 'lib')
    
    try:
        preprocessor = SchemaPreprocessor(library_paths=lib_paths)
        result = preprocessor.process(args.input)
        
        output_yaml = yaml.dump(result, default_flow_style=False, 
                               allow_unicode=True, sort_keys=False)
        
        if args.print_output:
            print(output_yaml)
        elif args.output:
            with open(args.output, 'w') as f:
                f.write(output_yaml)
            print(f"Wrote: {args.output}")
        else:
            # Default: write to input_resolved.yaml
            output_path = args.input.with_stem(args.input.stem + '_resolved')
            with open(output_path, 'w') as f:
                f.write(output_yaml)
            print(f"Wrote: {output_path}")
        
        if args.validate:
            try:
                from schema_interpreter import SchemaInterpreter
                interpreter = SchemaInterpreter(result)
                print("Validation: Schema parsed successfully")
            except Exception as e:
                print(f"Validation error: {e}", file=sys.stderr)
                sys.exit(1)
                
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
