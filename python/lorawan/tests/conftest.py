"""Shared test helpers and fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

#: Repository root (two levels up from this file: tests/ -> repo).
REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
VOCAB_DIR = REPO_ROOT / "vocab"


def load_json(path: Path) -> dict[str, Any]:
    """Parse a JSON file into a dictionary."""
    return json.loads(path.read_text(encoding="utf-8"))


def vector_files() -> list[Path]:
    """Return all ``*.vectors.json`` test-vector files under ``examples/``."""
    return sorted(EXAMPLES_DIR.glob("*.vectors.json"))


@pytest.fixture
def am102_td() -> dict[str, Any]:
    return load_json(EXAMPLES_DIR / "milesight-am102.td.json")


@pytest.fixture
def lht65n_td() -> dict[str, Any]:
    return load_json(EXAMPLES_DIR / "dragino-lht65n.td.json")
