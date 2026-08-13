"""Check that converted schemas conform to the payload schema language.

The converter's output is only useful if the reference toolchain accepts it, so
these tests validate every emitted schema against the two definitions of the
language that ship inside the pinned ``device-payload-schema`` submodule:

1. ``schemas/payload-schema.json`` -- the JSON Schema for the language.
2. ``tools/validate_schema.py`` -- the structural validator, which is stricter
   than the JSON Schema (it knows the wire-type vocabulary and the required keys
   of ``flagged``/``match``/``parts`` constructs).

Together they catch converter output that decodes today only by accident of the
interpreter being lenient. ``test_structural_validator_rejects_unknown_type``
guards the guard: if upstream ever stops reporting errors, these tests would
otherwise pass vacuously.
"""

from __future__ import annotations

import functools
import importlib.util
import sys
from types import ModuleType

import jsonschema
import pytest

from lorawan_wot.converter import td_to_payload_schema

from .conftest import EXAMPLES_DIR, REPO_ROOT, load_json

_SUBMODULE = REPO_ROOT / "external" / "device-payload-schema"
_LANGUAGE_SCHEMA_PATH = _SUBMODULE / "schemas" / "payload-schema.json"
_VALIDATOR_PATH = _SUBMODULE / "tools" / "validate_schema.py"
_DEVICES_DIR = EXAMPLES_DIR / "devices"

_SUBMODULE_MISSING = pytest.mark.skipif(
    not _VALIDATOR_PATH.exists() or not _LANGUAGE_SCHEMA_PATH.exists(),
    reason="device-payload-schema submodule not initialised",
)


@functools.lru_cache(maxsize=1)
def _load_validator() -> ModuleType:
    """Import (and cache) the reference structural validator from the submodule."""
    spec = importlib.util.spec_from_file_location("reference_validate_schema", _VALIDATOR_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Could not load validator spec from {_VALIDATOR_PATH}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=1)
def _language_schema() -> dict:
    """Load (and cache) the JSON Schema for the payload schema language."""
    return load_json(_LANGUAGE_SCHEMA_PATH)


def _conversion_sources():
    """Yield every TD whose conversion should conform: examples plus the catalog.

    The generated device catalog is the broad case -- it covers every layout and
    conditional shape present in the reference device schemas -- but it is not
    checked in, so it only contributes cases once it has been generated.
    """
    for td_path in sorted(EXAMPLES_DIR.glob("*.td.json")):
        yield pytest.param(td_path, id=td_path.stem)
    for td_path in sorted(_DEVICES_DIR.rglob("*.td.json")):
        rel = td_path.relative_to(_DEVICES_DIR).with_suffix("").with_suffix("")
        yield pytest.param(td_path, id="catalog-" + rel.as_posix())


_CONVERSIONS = list(_conversion_sources())


@_SUBMODULE_MISSING
@pytest.mark.parametrize("td_path", _CONVERSIONS)
def test_emitted_schema_matches_language_json_schema(td_path):
    """The converted schema validates against the language's JSON Schema."""
    schema = td_to_payload_schema(load_json(td_path))
    jsonschema.validate(instance=schema, schema=_language_schema())


@_SUBMODULE_MISSING
@pytest.mark.parametrize("td_path", _CONVERSIONS)
def test_emitted_schema_passes_structural_validator(td_path):
    """The reference structural validator reports no errors for the conversion."""
    schema = td_to_payload_schema(load_json(td_path))
    errors = _load_validator().validate_schema_structure(schema)
    assert errors == [], f"{td_path.name} converts to a schema the reference toolchain rejects"


@_SUBMODULE_MISSING
def test_structural_validator_rejects_unknown_type():
    """Sanity check: the validator really does report errors we would care about."""
    broken = {"name": "sanity", "fields": [{"name": "temperature", "type": "s17"}]}
    assert _load_validator().validate_schema_structure(broken), (
        "the reference validator accepted an unknown wire type, so the "
        "conformance tests above would pass vacuously"
    )
