"""Hold the reviewed examples to full coverage of the binding they demonstrate.

The curated device examples show the binding doing useful work, but they only
reach the constructs those seven devices happen to use, and the generated device
catalog under ``examples/devices/`` cannot stand in for them: it is gitignored
and its contents move with the submodule pin, so nothing in it is reviewed and
nothing in it is stable. Between them they left `ctv`, most of the wire types,
`lorav:derived`, `lorav:alias`, `lorav:padBefore`, `lorav:byteLength` and the
flag-bit form of `lorav:presentWhen` with no checked-in example at all.

``examples/conformance/`` closes that, one construct per fixture. The tests here
are what keeps it closed: each asserts that some enumeration the binding
publishes -- its vocabulary terms, its layouts, its wire types -- is exhausted by
the examples. Minting a term without an example that exercises it fails the
suite, which is the point; a published term nobody has decoded once is a term
nobody knows works.

Each fixture is also decoded, schema-validated and round-tripped by the existing
suite, which discovers it through ``conftest.example_tds`` / ``vector_files``.
"""

from __future__ import annotations

from typing import Any

import pytest

from lorawan_wot import vocab
from lorawan_wot.converter import td_to_payload_schema
from lorawan_wot.schema_to_td import payload_schema_to_td

from .conftest import CONFORMANCE_DIR, VOCAB_DIR, example_tds, load_json, vector_files

#: ``lorav:wireType`` values with no conformance fixture, and why.
#:
#: Both are published in ``lorawan-form.schema.json`` and resolve through
#: ``vocab.resolve_wire_type``, but neither can be decoded correctly today, so
#: an example would have to encode wrong behaviour to pass. Recorded here rather
#: than as a fixture so the gap is visible and this list can only shrink.
UNCOVERED_WIRE_TYPES: dict[str, str] = {
    # The reference interpreter reads 'bool' as a *bit* of the byte at the
    # cursor and does not advance the cursor unless the field carries
    # 'consume'. The binding has no term for either 'bit' or 'consume' and
    # converter._WIRE_WIDTH assigns bool a width of 1, so a second boolean
    # re-reads the first one's byte and every field after a boolean is read one
    # byte early. A boolean is spelled today as an unsigned byte with
    # lorav:bitmask and lorav:valueMap -- see mclimate-mc-button.td.json.
    "bool": "interpreter does not advance the cursor; no lorav: term for bit/consume",
    "xsd:boolean": "alias of 'bool'",
}


def _forms(td: dict[str, Any]):
    """Yield every uplink form across a Thing Description's events."""
    for affordance in td.get(vocab.EVENTS, {}).values():
        yield from affordance.get(vocab.FORMS, [])


def _terms_used(td: dict[str, Any]) -> set[str]:
    """Return every ``lorav:`` term appearing anywhere in ``td``."""
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            found.update(key for key in node if key.startswith(f"{vocab.LORAWAN_PREFIX}:"))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(td)
    return found


_TDS = [load_json(path) for path in example_tds()]
_ALL_TERMS = set().union(*(_terms_used(td) for td in _TDS))
_ALL_FORMS = [form for td in _TDS for form in _forms(td)]


@pytest.mark.parametrize("term", sorted(vocab.THING_TERMS | vocab.FORM_TERMS))
def test_every_published_term_has_an_example(term):
    """No ``lorav:`` term may be published without an example that uses it."""
    assert term in _ALL_TERMS, (
        f"{term} is published in vocab.py but no reviewed example uses it. "
        f"Add a fixture under {CONFORMANCE_DIR.name}/ that exercises it."
    )


@pytest.mark.parametrize("layout", sorted(vocab.SUPPORTED_LAYOUTS))
def test_every_supported_layout_has_an_example(layout):
    """Each accepted ``lorav:payloadLayout`` value must be demonstrated."""
    used = {td.get(vocab.PAYLOAD_LAYOUT) for td in _TDS}
    assert layout in used, f"no reviewed example declares payload layout {layout!r}"


@pytest.mark.parametrize("endian", sorted(vocab.SUPPORTED_ENDIAN))
def test_every_supported_endianness_has_an_example(endian):
    """Both byte orders must be stated explicitly somewhere, not just defaulted."""
    used = {form[vocab.ENDIAN] for form in _ALL_FORMS if vocab.ENDIAN in form}
    assert endian in used, f"no reviewed example declares {vocab.ENDIAN} {endian!r}"


def _published_wire_types() -> list[str]:
    schema = load_json(VOCAB_DIR / "lorawan-form.schema.json")
    return schema["properties"][vocab.WIRE_TYPE]["enum"]


@pytest.mark.parametrize(
    "wire_type", sorted(set(_published_wire_types()) - set(UNCOVERED_WIRE_TYPES))
)
def test_every_published_wire_type_has_an_example(wire_type):
    """Each ``lorav:wireType`` the form schema accepts must be decoded somewhere."""
    used = {form[vocab.WIRE_TYPE] for form in _ALL_FORMS if vocab.WIRE_TYPE in form}
    assert wire_type in used, (
        f"{wire_type!r} is accepted by lorawan-form.schema.json but no reviewed example decodes it"
    )


@pytest.mark.parametrize("wire_type", sorted(UNCOVERED_WIRE_TYPES))
def test_uncovered_wire_types_are_still_published(wire_type):
    """Keep the gap list honest: a type listed as uncovered must still exist.

    If the type is withdrawn from the form schema its entry here is stale, and
    if it gains a fixture the entry should be deleted rather than left to excuse
    a type that is now covered.
    """
    assert wire_type in _published_wire_types(), (
        f"{wire_type!r} is recorded in UNCOVERED_WIRE_TYPES but is no longer "
        f"published by lorawan-form.schema.json -- delete the entry"
    )
    used = {form[vocab.WIRE_TYPE] for form in _ALL_FORMS if vocab.WIRE_TYPE in form}
    assert wire_type not in used, (
        f"{wire_type!r} now has a reviewed example -- delete its "
        f"UNCOVERED_WIRE_TYPES entry so the gap list stays accurate"
    )


@pytest.mark.parametrize("descriptor", sorted(vocab.DERIVED_KEYS))
def test_every_derived_descriptor_has_an_example(descriptor):
    """Each ``lorav:derived`` descriptor kind must be evaluated by an example."""
    used: set[str] = set()
    for form in _ALL_FORMS:
        used.update(form.get(vocab.DERIVED, {}))
    assert descriptor in used, f"no reviewed example carries a {descriptor!r} derived value"


@pytest.mark.parametrize("key", [vocab.PW_BIT, vocab.PW_VALUE])
def test_both_present_when_shapes_have_an_example(key):
    """``lorav:presentWhen`` has a flag-bit shape and a match-value shape."""
    used: set[str] = set()
    for form in _ALL_FORMS:
        condition = form.get(vocab.PRESENT_WHEN)
        if isinstance(condition, dict):
            used.update(condition)
    assert key in used, f"no reviewed example uses the {vocab.PRESENT_WHEN} {key!r} shape"


def test_byte_length_covers_fixed_and_remaining():
    """``lorav:byteLength`` carries both an explicit width and the -1 sentinel."""
    used = {form[vocab.BYTE_LENGTH] for form in _ALL_FORMS if vocab.BYTE_LENGTH in form}
    assert vocab.BYTE_LENGTH_REMAINING in used, (
        f"no reviewed example uses {vocab.BYTE_LENGTH} "
        f"{vocab.BYTE_LENGTH_REMAINING} (consume the rest of the payload)"
    )
    assert any(length >= 0 for length in used), (
        f"no reviewed example uses {vocab.BYTE_LENGTH} with an explicit width"
    )


@pytest.mark.parametrize("td_path", sorted(CONFORMANCE_DIR.glob("*.td.json")), ids=lambda p: p.stem)
def test_every_fixture_has_vectors(td_path):
    """A fixture nothing decodes proves nothing; each needs a vectors file."""
    vectors_path = td_path.with_name(f"{td_path.stem.removesuffix('.td')}.vectors.json")
    assert vectors_path in vector_files(), f"{td_path.name} has no {vectors_path.name}"
    spec = load_json(vectors_path)
    assert spec["vectors"], f"{vectors_path.name} declares no vectors"


@pytest.mark.parametrize("td_path", sorted(CONFORMANCE_DIR.glob("*.td.json")), ids=lambda p: p.stem)
def test_fixture_round_trips_through_the_payload_schema(td_path):
    """Converting a fixture to a payload schema and back must preserve its events.

    The curated examples only round-trip the constructs they use. Running the
    fixtures through both directions is what puts the reverse converter in front
    of ``ctv``, the wider wire types and the derived-value descriptors.
    """
    td = load_json(td_path)
    schema = td_to_payload_schema(td)
    rebuilt = payload_schema_to_td(schema, source=td_path.name)
    assert set(rebuilt[vocab.EVENTS]) == set(td[vocab.EVENTS]), (
        f"{td_path.name}: round trip changed the event set\n"
        f"  before: {sorted(td[vocab.EVENTS])}\n"
        f"  after:  {sorted(rebuilt[vocab.EVENTS])}"
    )
    for name, affordance in td[vocab.EVENTS].items():
        want = affordance[vocab.FORMS][0].get(vocab.WIRE_TYPE)
        got = rebuilt[vocab.EVENTS][name][vocab.FORMS][0].get(vocab.WIRE_TYPE)
        # 'number' marks a derived value rather than a wire width, so it has no
        # native spelling to resolve to and is compared as-is.
        if vocab.COMPUTED_TYPE in (want, got):
            assert want == got, f"{td_path.name}: {name} wire type {want!r} came back as {got!r}"
            continue
        assert vocab.resolve_wire_type(want) == vocab.resolve_wire_type(got), (
            f"{td_path.name}: {name} wire type {want!r} came back as {got!r}"
        )
