"""Validate that example Thing Description forms match the binding JSON Schema."""

from __future__ import annotations

import jsonschema
import pytest

from lorawan_wot import vocab

from .conftest import EXAMPLES_DIR, VOCAB_DIR, load_json

_FORM_SCHEMA = load_json(VOCAB_DIR / "lorawan-form.schema.json")
_THING_SCHEMA = load_json(VOCAB_DIR / "lorawan-thing.schema.json")

_LORAWAN_TERMS = {
    vocab.WIRE_TYPE,
    vocab.FPORT,
    vocab.BYTE_OFFSET,
    vocab.TAG,
}


def _lorawan_forms():
    """Yield every LoRaWAN-bearing form across all example Thing Descriptions."""
    for td_path in EXAMPLES_DIR.glob("*.td.json"):
        td = load_json(td_path)
        for event_name, affordance in td.get(vocab.EVENTS, {}).items():
            for form in affordance.get(vocab.FORMS, []):
                if _LORAWAN_TERMS & form.keys():
                    yield pytest.param(form, id=f"{td_path.stem}-{event_name}")


@pytest.mark.parametrize("form", list(_lorawan_forms()))
def test_example_form_validates(form):
    jsonschema.validate(instance=form, schema=_FORM_SCHEMA)


def _example_things():
    """Yield every example Thing Description root object."""
    for td_path in sorted(EXAMPLES_DIR.glob("*.td.json")):
        yield pytest.param(load_json(td_path), id=td_path.stem)


@pytest.mark.parametrize("td", list(_example_things()))
def test_example_thing_metadata_validates(td):
    """Thing-level OTAA identity and onboarding terms match the thing schema."""
    jsonschema.validate(instance=td, schema=_THING_SCHEMA)


@pytest.mark.parametrize("td", list(_example_things()))
def test_example_secrets_not_inlined(td):
    """Root keys must be declared as apikey schemes, never inlined as values."""
    schemes = {
        defn.get("name")
        for defn in td.get("securityDefinitions", {}).values()
        if defn.get("scheme") == "apikey"
    }
    if td.get(vocab.MAC_VERSION, "").startswith("1.1"):
        assert vocab.APP_KEY_NAME in schemes, "1.1.x device must declare an AppKey apikey scheme"
        assert vocab.NWK_KEY_NAME in schemes, "1.1.x device must declare a NwkKey apikey scheme"
    for forbidden in ("lorav:appKey", "lorav:nwkKey", "lorav:appkey", "lorav:nwkkey"):
        assert forbidden not in td, f"secret {forbidden!r} must not be inlined in the TD"
