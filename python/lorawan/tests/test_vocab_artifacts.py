"""Keep the published vocabulary artifacts in step with ``vocab.py``.

``vocab.py`` is the single source of truth for the ``lorav:`` terms. The JSON-LD
context, the ontology and the README tables are hand-maintained, so they can
silently drift; these tests make any drift a test failure instead of a
documentation bug.
"""

from __future__ import annotations

import re

import pytest

from lorawan_wot import vocab

from .conftest import REPO_ROOT, VOCAB_DIR, load_json

_CONTEXT = load_json(VOCAB_DIR / "context.jsonld")["@context"]
_ONTOLOGY = (VOCAB_DIR / "ontology.ttl").read_text(encoding="utf-8")
_README = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

#: Every ``lorav:`` term the README mentions in backticks.
_README_TERMS = set(re.findall(r"`(lorav:[A-Za-z]+)`", _README))


def _declared_terms() -> list[str]:
    """Every ``lorav:`` term the binding defines, from the explicit registry."""
    return sorted(vocab.ALL_TERMS)


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


def test_registries_do_not_overlap():
    """A term belongs either on the Thing or on a form, never on both."""
    assert not (vocab.THING_TERMS & vocab.FORM_TERMS)


def test_withdrawn_terms_are_not_redefined():
    """A withdrawn term must not reappear as a live term under the same name."""
    assert not (set(vocab.REMOVED_TERMS) & vocab.ALL_TERMS)


@pytest.mark.parametrize("term", sorted(vocab.REMOVED_TERMS))
def test_withdrawn_term_is_deprecated_in_the_ontology(term):
    """Withdrawn terms stay in the ontology, marked deprecated.

    A published vocabulary is a contract: deleting an IRI outright leaves already
    published Thing Descriptions referring to something undefined, so the term is
    retained with ``owl:deprecated`` and a pointer to its replacement.
    """
    assert f"\n{term} a owl:DatatypeProperty" in _ONTOLOGY, (
        f"withdrawn term {term} should remain in vocab/ontology.ttl as deprecated"
    )


@pytest.mark.parametrize("term", _declared_terms())
def test_term_is_documented_in_the_readme(term):
    """Every live term is explained where users actually look for it."""
    assert term in _README_TERMS, f"{term} is missing from the README vocabulary tables"


@pytest.mark.parametrize("term", sorted(vocab.REMOVED_TERMS))
def test_withdrawn_term_is_listed_in_the_readme_migration_table(term):
    """Anyone hitting a rejected term must find its replacement in the README.

    The converter names the replacement in its error, but only for the first term
    it trips over; the table is what lets a reader migrate a whole file at once.
    """
    assert term in _README_TERMS, f"withdrawn term {term} is missing from the README"


def test_readme_mentions_no_unknown_terms():
    """The README must not document terms the binding neither defines nor withdrew."""
    known = vocab.ALL_TERMS | set(vocab.REMOVED_TERMS)
    assert _README_TERMS <= known, f"README documents unknown terms: {_README_TERMS - known}"
