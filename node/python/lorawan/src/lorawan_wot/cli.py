"""Command-line interface for the LoRaWAN WoT binding tools.

Three subcommands are provided:

* ``convert``  -- turn a Thing Description into a MultiTech payload schema (YAML).
* ``decode``   -- decode an uplink payload for a Thing Description.
* ``generate`` -- turn a MultiTech payload schema into a Thing Description (JSON).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from lorawan_wot.converter import td_to_payload_schema
from lorawan_wot.decode import decode_uplink
from lorawan_wot.schema_to_td import payload_schema_to_td


def _load_td(path: str) -> dict[str, Any]:
    """Read and parse a Thing Description JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cmd_convert(args: argparse.Namespace) -> int:
    td = _load_td(args.td)
    schema = td_to_payload_schema(td)
    # ``sort_keys=False`` keeps the field order we deliberately assembled.
    text = yaml.safe_dump(schema, sort_keys=False, allow_unicode=True)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote payload schema to {args.output}")
    else:
        sys.stdout.write(text)
    return 0


def _cmd_decode(args: argparse.Namespace) -> int:
    td = _load_td(args.td)
    data = decode_uplink(td, args.payload, fport=args.fport)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    schema = yaml.safe_load(Path(args.schema).read_text(encoding="utf-8"))
    td = payload_schema_to_td(schema, source=Path(args.schema).name)
    text = json.dumps(td, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote Thing Description to {args.output}")
    else:
        sys.stdout.write(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="lorawan-wot",
        description="LoRaWAN Web of Things binding: convert Thing Descriptions "
        "to MultiTech payload schemas and decode uplinks.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    convert = sub.add_parser("convert", help="Convert a TD to a payload schema (YAML).")
    convert.add_argument("td", help="Path to the Thing Description JSON file.")
    convert.add_argument("-o", "--output", help="Write YAML here instead of standard output.")
    convert.set_defaults(func=_cmd_convert)

    decode = sub.add_parser("decode", help="Decode an uplink payload for a TD.")
    decode.add_argument("td", help="Path to the Thing Description JSON file.")
    decode.add_argument("payload", help="Uplink payload as a hex string.")
    decode.add_argument(
        "--fport", type=int, default=None, help="LoRaWAN frame port (ports layout)."
    )
    decode.set_defaults(func=_cmd_decode)

    generate = sub.add_parser(
        "generate",
        help="Generate a Thing Description from a MultiTech payload schema (YAML).",
    )
    generate.add_argument("schema", help="Path to the MultiTech payload schema YAML file.")
    generate.add_argument("-o", "--output", help="Write JSON here instead of standard output.")
    generate.set_defaults(func=_cmd_generate)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point used by the ``lorawan-wot`` console script."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
