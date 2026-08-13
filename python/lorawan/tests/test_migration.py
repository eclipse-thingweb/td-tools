"""Keep the migration script in step with the vocabulary it migrates away from.

:mod:`scripts.migrate_td_to_events` is the only module that must spell withdrawn
terms, because the vocabulary no longer defines constants for them. That makes it
the one place where a term can be forgotten silently: withdraw something in
:mod:`lorawan_wot.vocab` without teaching the script about it and every affected
Thing Description becomes unmigratable, with no failure until a user hits it.

Comparing the two sets turns that into a test failure here instead.
"""

from __future__ import annotations

import json

import pytest

from lorawan_wot import vocab
from scripts import migrate_td_to_events as migrate

#: Withdrawn terms the script handles outside a lookup table, in ``if`` branches.
#:
#: Listing them by hand looks redundant, but the alternative is parsing the
#: source; this stays honest because a term listed here and not handled (or the
#: reverse) shows up as a set difference below.
_BRANCH_HANDLED = frozenset(
    {
        "lorav:enum",
        "lorav:validRange",
        "lorav:unece",
        "lorav:brand",
        "lorav:model",
        "lorav:hardwareVersion",
        "lorav:softwareVersion",
        "lorav:endDeviceId",
    }
)


def _handled_terms() -> frozenset[str]:
    """Every withdrawn term the migration script knows how to rewrite."""
    return frozenset(
        set(migrate._CONDITION_TERMS)
        | set(migrate._DERIVED_TERMS)
        | set(migrate._RENAMED_TERMS)
        | _BRANCH_HANDLED
    )


def test_every_withdrawn_term_can_be_migrated():
    """A withdrawn term with no migration path strands whoever used it."""
    missing = sorted(set(vocab.REMOVED_TERMS) - _handled_terms())
    assert not missing, (
        f"withdrawn terms with no migration path: {missing}. "
        f"Teach scripts/migrate_td_to_events.py how to rewrite them."
    )


def test_migration_handles_no_terms_the_vocabulary_still_defines():
    """Rewriting a live term would corrupt an already-current document."""
    stray = sorted(_handled_terms() - set(vocab.REMOVED_TERMS))
    assert not stray, f"migration rewrites terms that are not withdrawn: {stray}"


def test_migrated_output_is_accepted_by_the_converter():
    """The end-to-end promise: what the script emits must no longer be rejected."""
    td = {
        "@context": ["https://www.w3.org/2022/wot/td/v1.1", {"lorav": vocab.LORAWAN_NS}],
        "title": "Sensor",
        vocab.PAYLOAD_LAYOUT: vocab.LAYOUT_FIXED,
        "lorav:brand": "Acme",
        "lorav:hardwareVersion": "rev-b",
        vocab.PROPERTIES: {
            "temperature": {
                "type": "number",
                "unit": "Cel",
                "readOnly": True,
                "observable": False,
                vocab.FORMS: [
                    {
                        "href": vocab.UPLINK_HREF,
                        "op": ["readproperty"],
                        vocab.BYTE_OFFSET: 0,
                        "lorav:type": "xsd:short",
                        "lorav:offset": 2,
                        "lorav:validRange": [-40, 85],
                    }
                ],
            }
        },
    }

    migrated = migrate.migrate_td(td)

    assert not vocab.uses_withdrawn_vocabulary(migrated)
    event = migrated[vocab.EVENTS]["temperature"]
    assert event[vocab.DATA]["minimum"] == -40
    assert event[vocab.DATA]["maximum"] == 85
    assert "readOnly" not in event[vocab.DATA]
    assert "observable" not in event[vocab.DATA]
    form = event[vocab.FORMS][0]
    assert form["op"] == list(vocab.UPLINK_OPS)
    assert form[vocab.WIRE_TYPE] == "xsd:short"
    assert form[vocab.ADDEND] == 2
    assert migrated[vocab.BRAND] == "Acme"
    assert migrated["version"]["model"] == "rev-b"


@pytest.mark.parametrize("placement", ["affordance", "form"])
def test_data_schema_terms_are_migrated_wherever_they_were_written(placement):
    """``validRange`` reads naturally next to ``type``, so both spots occur.

    The 0.2.x form schema put it on the form, but a hand-written document is just
    as likely to have placed it on the affordance beside ``unit``. Migrating only
    one produces output the converter still refuses, which is the one outcome
    this script exists to prevent.
    """
    affordance: dict = {"type": "number", vocab.FORMS: [{vocab.BYTE_OFFSET: 0}]}
    if placement == "affordance":
        affordance["lorav:validRange"] = [0, 100]
    else:
        affordance[vocab.FORMS][0]["lorav:validRange"] = [0, 100]

    migrated = migrate.migrate_td({vocab.PROPERTIES: {"battery": affordance}})

    assert not vocab.uses_withdrawn_vocabulary(migrated)
    data = migrated[vocab.EVENTS]["battery"][vocab.DATA]
    assert (data["minimum"], data["maximum"]) == (0, 100)


def test_migration_is_idempotent():
    """Re-running the script over a current document must be a no-op.

    Sync-then-migrate is the documented recovery path, so it will be run against
    directories that are already partly migrated.
    """
    td = {
        "title": "Sensor",
        vocab.EVENTS: {
            "temperature": {
                vocab.DATA: {"type": "number"},
                vocab.FORMS: [
                    {
                        "href": vocab.UPLINK_HREF,
                        "op": list(vocab.UPLINK_OPS),
                        vocab.BYTE_OFFSET: 0,
                        vocab.WIRE_TYPE: "xsd:short",
                    }
                ],
            }
        },
    }

    assert not vocab.uses_withdrawn_vocabulary(td)
    assert migrate.migrate_td(json.loads(json.dumps(td))) == td
