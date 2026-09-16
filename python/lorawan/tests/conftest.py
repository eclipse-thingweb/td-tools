"""Shared test helpers and fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

#: Repository root (two levels up from this file: tests/ -> repo).
REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
#: Hand-written fixtures, one binding construct each, that together cover every
#: feature of the binding the curated device examples happen not to reach. See
#: ``examples/conformance/README.md``.
CONFORMANCE_DIR = EXAMPLES_DIR / "conformance"
VOCAB_DIR = REPO_ROOT / "vocab"


def load_json(path: Path) -> dict[str, Any]:
    """Parse a JSON file into a dictionary."""
    return json.loads(path.read_text(encoding="utf-8"))


def example_tds() -> list[Path]:
    """Return every reviewed Thing Description: curated devices plus conformance.

    Deliberately not a recursive glob: ``examples/devices/`` and
    ``examples/generated/`` hold regenerated output that is gitignored and moves
    with the submodule pin, so it must not steer the checked-in test suite.
    """
    return sorted(EXAMPLES_DIR.glob("*.td.json")) + sorted(CONFORMANCE_DIR.glob("*.td.json"))


def vector_files() -> list[Path]:
    """Return every ``*.vectors.json`` file belonging to a reviewed example."""
    return sorted(EXAMPLES_DIR.glob("*.vectors.json")) + sorted(
        CONFORMANCE_DIR.glob("*.vectors.json")
    )


@pytest.fixture
def em300th_td() -> dict[str, Any]:
    return load_json(EXAMPLES_DIR / "milesight-em300-th.td.json")


@pytest.fixture
def lht65n_td() -> dict[str, Any]:
    return load_json(EXAMPLES_DIR / "dragino-lht65n.td.json")
