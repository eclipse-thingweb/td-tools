"""Report how often each ``lorav:`` binding term is used across the TD examples.

Counts every term exported by :mod:`lorawan_wot.vocab` in the curated examples
(``examples/*.td.json``) and in the generated device catalog
(``examples/devices/<vendor>/<model>.td.json``), so documentation can state real
usage instead of guesses.

The term list is derived from ``vocab`` itself rather than hardcoded, so the
report can never drift from the vocabulary.

Note that ``examples/devices/`` is git-ignored, which makes ad-hoc ``grep``
counts unreliable; this script walks the working tree directly.

Usage::

    uv run --no-sync python -m scripts.vocab_usage_report
"""

from __future__ import annotations

import collections
import json
from pathlib import Path
from typing import Any

from lorawan_wot import vocab

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
DEVICES_DIR = EXAMPLES_DIR / "devices"


def _terms() -> dict[str, str]:
    """Return ``{term IRI: constant name}`` for every ``lorav:`` term in vocab."""
    return {
        value: name
        for name, value in vars(vocab).items()
        if name.isupper() and isinstance(value, str) and value.startswith("lorav:")
    }


def _count_keys(node: Any, counter: collections.Counter[str]) -> None:
    """Accumulate every ``lorav:`` key occurrence in a decoded JSON document."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key.startswith("lorav:"):
                counter[key] += 1
            _count_keys(value, counter)
    elif isinstance(node, list):
        for item in node:
            _count_keys(item, counter)


def _scan(paths: list[Path]) -> tuple[collections.Counter[str], dict[str, set[Path]]]:
    """Return total occurrences per term and the files each term appears in."""
    totals: collections.Counter[str] = collections.Counter()
    files: dict[str, set[Path]] = collections.defaultdict(set)

    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        counter: collections.Counter[str] = collections.Counter()
        _count_keys(document, counter)
        totals.update(counter)
        for term in counter:
            files[term].add(path)

    return totals, files


def _vendor(path: Path) -> str:
    """Return the catalog vendor folder for a device TD, or ``-`` for examples."""
    if DEVICES_DIR in path.parents:
        return path.relative_to(DEVICES_DIR).parts[0]
    return "-"


def report() -> None:
    """Print a markdown usage table plus a machine-diffable summary."""
    curated = sorted(EXAMPLES_DIR.glob("*.td.json"))
    catalog = sorted(DEVICES_DIR.rglob("*.td.json"))
    totals, files = _scan(curated + catalog)
    known = _terms()

    print(f"Curated examples scanned: {len(curated)}")
    print(f"Catalog device TDs scanned: {len(catalog)}")
    print()
    print("| Term | Occurrences | Files | Vendors |")
    print("|------|------------:|------:|---------|")

    for term in sorted(known, key=lambda t: (-totals[t], t)):
        paths = files.get(term, set())
        vendors = sorted({_vendor(p) for p in paths} - {"-"})
        print(f"| `{term}` | {totals[term]} | {len(paths)} | {', '.join(vendors) or '-'} |")

    unknown = sorted(set(totals) - set(known))
    if unknown:
        print()
        print("Terms found in TDs but not defined in vocab.py:")
        for term in unknown:
            print(f"  {term} ({totals[term]})")

    print()
    print("--- diffable summary ---")
    for term in sorted(known):
        print(f"{term}\t{totals[term]}\t{len(files.get(term, set()))}")


if __name__ == "__main__":
    report()
