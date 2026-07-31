"""Generate WoT Thing Descriptions for every supported reference device schema.

Walks the ``device-payload-schema`` submodule, converts each device schema that
falls within the binding's supported subset into a Thing Description under
``examples/devices/<vendor>/<model>.td.json``, and prints a coverage report
listing what was generated and what was skipped (and why).

Usage::

    uv run --no-sync python -m scripts.generate_device_tds
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

import yaml

from lorawan_wot.schema_to_td import UnsupportedSchemaError, payload_schema_to_td

REPO_ROOT = Path(__file__).resolve().parents[1]
DEVICES_DIR = REPO_ROOT / "external" / "device-payload-schema" / "schemas" / "devices"
OUTPUT_DIR = REPO_ROOT / "examples" / "devices"


def _skip_bucket(exc: UnsupportedSchemaError) -> str:
    """Return the coverage-report label for a skip.

    The label comes straight from the exception's structured
    :class:`~lorawan_wot.schema_to_td.SkipReason`, so the report stays correct
    even if the human-readable error message is reworded.
    """
    return exc.reason.value


def generate() -> int:
    """Generate all supported device TDs; return the number written."""
    schema_paths = sorted(DEVICES_DIR.rglob("*.yaml"))
    generated: list[Path] = []
    skipped: dict[str, list[str]] = collections.defaultdict(list)

    for schema_path in schema_paths:
        rel = schema_path.relative_to(DEVICES_DIR)
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
        try:
            td = payload_schema_to_td(schema, source=schema_path.name)
        except UnsupportedSchemaError as exc:
            skipped[_skip_bucket(exc)].append(str(rel).replace("\\", "/"))
            continue

        out_path = OUTPUT_DIR / rel.with_suffix(".td.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(td, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        generated.append(out_path)

    _report(len(schema_paths), generated, skipped)
    return len(generated)


def _report(total: int, generated: list[Path], skipped: dict[str, list[str]]) -> None:
    """Print a human-readable coverage summary."""
    print(f"Device schemas scanned: {total}")
    print(f"Thing Descriptions generated: {len(generated)}")
    print(f"  written under: {OUTPUT_DIR.relative_to(REPO_ROOT)}")
    skipped_total = sum(len(v) for v in skipped.values())
    print(f"Skipped (unsupported subset): {skipped_total}")
    for reason in sorted(skipped, key=lambda r: -len(skipped[r])):
        print(f"  {len(skipped[reason]):4d}  {reason}")


if __name__ == "__main__":
    generate()
