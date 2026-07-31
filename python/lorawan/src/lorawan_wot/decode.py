"""Decode LoRaWAN uplinks by driving the MultiTech reference interpreter.

The MultiTech ``schema_interpreter.py`` lives in a pinned git submodule under
``external/device-payload-schema``. Rather than re-implement decoding, this
module converts a Thing Description to a MultiTech schema and hands that schema
to the upstream interpreter.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from lorawan_wot.converter import td_to_payload_schema

#: Location of the MultiTech interpreter inside the pinned submodule.
_INTERPRETER_PATH = (
    Path(__file__).resolve().parents[2]
    / "external"
    / "device-payload-schema"
    / "tools"
    / "schema_interpreter.py"
)

_interpreter_module: ModuleType | None = None


def _load_interpreter() -> ModuleType:
    """Import (and cache) the MultiTech interpreter module from the submodule."""
    global _interpreter_module
    if _interpreter_module is not None:
        return _interpreter_module

    if not _INTERPRETER_PATH.exists():
        raise FileNotFoundError(
            f"MultiTech interpreter not found at {_INTERPRETER_PATH}. "
            f"Initialise the submodule with: git submodule update --init --recursive"
        )

    spec = importlib.util.spec_from_file_location("multitech_schema_interpreter", _INTERPRETER_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Could not load interpreter spec from {_INTERPRETER_PATH}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _interpreter_module = module
    return module


def parse_hex(payload: str | bytes) -> bytes:
    """Normalise a hex string (with optional spaces / ``0x``) or bytes to bytes."""
    if isinstance(payload, bytes):
        return payload
    cleaned = payload.strip().replace("0x", "").replace(" ", "")
    return bytes.fromhex(cleaned)


def decode_uplink(
    td: dict[str, Any],
    payload: str | bytes,
    *,
    fport: int | None = None,
) -> dict[str, Any]:
    """Decode a single uplink ``payload`` for the device described by ``td``.

    Returns the decoded field dictionary. ``fport`` is required for ``ports``
    layouts so the interpreter can select the correct field set.
    """
    schema = td_to_payload_schema(td)
    return decode_with_schema(schema, payload, fport=fport)


def decode_with_schema(
    schema: dict[str, Any],
    payload: str | bytes,
    *,
    fport: int | None = None,
) -> dict[str, Any]:
    """Decode a ``payload`` using an already-built MultiTech ``schema`` dict."""
    interpreter_module = _load_interpreter()
    interpreter = interpreter_module.SchemaInterpreter(schema)
    result = interpreter.decode(parse_hex(payload), fPort=fport)
    if not result.success:
        raise ValueError(f"Decode failed: {result.errors}")
    return result.data
