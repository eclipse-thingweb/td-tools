"""Keep the published vocabulary artifacts in step with ``vocab.py``.

``vocab.py`` is the single source of truth for the ``lorav:`` terms. The JSON-LD
context and the ontology are hand-maintained, so they can silently drift; these
tests make any drift a test failure instead of a documentation bug.
"""

from __future__ import annotations

import pytest

from lorawan_wot import vocab

from .conftest import VOCAB_DIR, load_json

_CONTEXT = load_json(VOCAB_DIR / "context.jsonld")["@context"]
_ONTOLOGY = (VOCAB_DIR / "ontology.ttl").read_text(encoding="utf-8")


def _declared_terms() -> list[str]:
    """Every ``lorav:`` term constant exported by ``vocab.py``."""
    return sorted(
        value
        for name, value in vars(vocab).items()
        if name.isupper() and isinstance(value, str) and value.startswith("lorav:")
    )


@pytest.mark.parametrize("term", _declared_terms())
def test_term_has_a_context_alias(term):
    """Every term is reachable through a short name in the JSON-LD context."""
    assert term in _CONTEXT.values(), f"{term} is missing from vocab/context.jsonld"


@pytest.mark.parametrize("term", _declared_terms())
def test_term_is_described_in_the_ontology(term):
    """Every term is defined (with a label and comment) in the ontology."""
    assert f"\n{term} a owl:DatatypeProperty" in _ONTOLOGY, (
        f"{term} is missing from vocab/ontology.ttl"
    )


def test_context_defines_no_unknown_terms():
    """The context must not alias terms that ``vocab.py`` does not define."""
    aliased = {
        value
        for value in _CONTEXT.values()
        if isinstance(value, str) and value.startswith("lorav:")
    }
    assert aliased <= set(_declared_terms())
