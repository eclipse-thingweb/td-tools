"""Rewrite a pre-0.3.0 Thing Description into the events model in place.

Version 0.3.0 moved decoded uplink values from ``properties`` to ``events`` and
renamed or withdrew twenty-odd binding terms. That is a breaking change, and the
converter refuses the old shape by design -- guessing at a data schema that is no
longer where the binding looks for it would decode the wrong bytes silently.

Refusing is only half an answer, though: every existing Thing Description has to
get to the new shape somehow, and doing it by hand across hundreds of forms is
exactly the kind of work that invites transcription errors. This script performs
the mechanical part, so a human review is a diff rather than a retype.

It has to spell the withdrawn term names, since by definition the vocabulary no
longer defines them. To stop it falling behind, ``tests/test_migration.py``
asserts that the names it handles are exactly the keys of
:data:`lorawan_wot.vocab.REMOVED_TERMS` -- withdraw a term without teaching this
script about it and the suite fails.

What it cannot do is invent information. ``lorav:hardwareVersion`` and
``lorav:softwareVersion`` become ``version/model`` and ``version/instance``, and
``lorav:endDeviceId`` is dropped because the Thing's ``id`` already identifies
the device -- if a deployment used it for something else, that is a judgement
call the reviewer has to make.

Usage::

    uv run --no-sync python -m scripts.migrate_td_to_events examples/*.td.json
    uv run --no-sync python -m scripts.migrate_td_to_events --check examples
"""

from __future__ import annotations

import argparse
import copy
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from lorawan_wot import vocab

#: Affordance keys that only make sense for a pollable property. An uplink is
#: pushed by the device, so "can I write it?" and "can I observe it?" no longer
#: have anything to say.
_PROPERTY_ONLY_KEYS: frozenset[str] = frozenset({"readOnly", "writeOnly", "observable"})

#: Affordance keys that stay on the event itself rather than moving into ``data``.
_AFFORDANCE_KEYS: frozenset[str] = frozenset(
    {"@type", "title", "titles", "description", "descriptions", vocab.FORMS, "uriVariables"}
)

#: Old presence/switch terms, mapped to their sub-key under ``lorav:presentWhen``.
_CONDITION_TERMS: dict[str, str] = {
    "lorav:presenceField": vocab.PW_FIELD,
    "lorav:presenceBit": vocab.PW_BIT,
    "lorav:switchField": vocab.PW_FIELD,
    "lorav:switchValue": vocab.PW_VALUE,
}

#: Old standalone computed terms, mapped to their sub-key under ``lorav:derived``.
_DERIVED_TERMS: dict[str, str] = {f"lorav:{key}": key for key in vocab.DERIVED_ORDER}

#: Old form terms that simply changed name.
_RENAMED_TERMS: dict[str, str] = {
    "lorav:type": vocab.WIRE_TYPE,
    "lorav:offset": vocab.ADDEND,
    "lorav:length": vocab.BYTE_LENGTH,
    "lorav:var": vocab.ALIAS,
}


def _fold_into_data(key: str, value: Any, data: dict[str, Any]) -> bool:
    """Rewrite a withdrawn term as its TD-core equivalent on ``data``.

    Returns whether ``key`` was one of them, so callers know not to copy it
    through. These three describe the decoded value rather than how it is
    transferred, so they belong on the data schema wherever they were written.
    The 0.2.x form schema placed them on the form, but hand-written documents put
    them next to ``type`` and ``unit`` often enough that both spots must be
    handled -- carrying one through unchanged would produce a "migrated" file the
    converter still refuses.
    """
    if key == "lorav:enum":
        # JSON object keys are strings; the payload indexes them as integers.
        data["oneOf"] = [{"const": int(k), "title": label} for k, label in sorted(value.items())]
    elif key == "lorav:validRange":
        data["minimum"], data["maximum"] = value
    elif key == "lorav:unece":
        data.setdefault("unit", value)  # 'unit' already carries UN/CEFACT codes
    else:
        return False
    return True


def _migrate_form(form: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Return ``form`` in the 0.3.0 shape, folding withdrawn terms into ``data``.

    ``data`` is mutated for the terms that moved out of the form and onto the
    event's data schema, because their meaning describes the decoded value rather
    than how it is transferred.
    """
    migrated: dict[str, Any] = {}
    condition: dict[str, Any] = {}
    derived: dict[str, Any] = {}

    for key, value in form.items():
        if key == "op":
            migrated["op"] = list(vocab.UPLINK_OPS)
        elif key in _RENAMED_TERMS:
            migrated[_RENAMED_TERMS[key]] = value
        elif key in _CONDITION_TERMS:
            condition[_CONDITION_TERMS[key]] = value
        elif key in _DERIVED_TERMS:
            derived[_DERIVED_TERMS[key]] = value
        elif not _fold_into_data(key, value, data):
            migrated[key] = value

    migrated.setdefault("op", list(vocab.UPLINK_OPS))
    if condition:
        migrated[vocab.PRESENT_WHEN] = condition
    if derived:
        migrated[vocab.DERIVED] = {k: derived[k] for k in vocab.DERIVED_ORDER if k in derived}
        migrated[vocab.WIRE_TYPE] = vocab.COMPUTED_TYPE
    return migrated


def _migrate_affordance(affordance: dict[str, Any]) -> dict[str, Any]:
    """Return a 0.2.x property affordance rebuilt as a 0.3.0 event affordance.

    A property states its data schema inline; an event nests it under ``data``,
    because the event itself is the notification and the schema describes what
    the notification carries.
    """
    data: dict[str, Any] = {}
    for key, value in affordance.items():
        if key in _AFFORDANCE_KEYS or key in _PROPERTY_ONLY_KEYS:
            continue
        if not _fold_into_data(key, value, data):
            data[key] = value
    forms = [_migrate_form(form, data) for form in affordance.get(vocab.FORMS, [])]

    event: dict[str, Any] = {}
    for key in ("@type", "title", "titles", "description", "descriptions"):
        if key in affordance:
            event[key] = affordance[key]
    event[vocab.DATA] = data
    event[vocab.FORMS] = forms
    return event


def _migrate_context(context: Any) -> Any:
    """Add the schema.org prefix when the Thing needs it for brand/model."""
    if not isinstance(context, list):
        context = [context]
    prefixes = [entry for entry in context if isinstance(entry, dict)]
    if any(vocab.SCHEMA_ORG_PREFIX in entry for entry in prefixes):
        return context
    if prefixes:
        prefixes[-1][vocab.SCHEMA_ORG_PREFIX] = vocab.SCHEMA_ORG_NS
        return context
    return [*context, {vocab.SCHEMA_ORG_PREFIX: vocab.SCHEMA_ORG_NS}]


def migrate_td(td: dict[str, Any]) -> dict[str, Any]:
    """Return ``td`` rewritten for the 0.3.0 events model."""
    out: dict[str, Any] = {}
    version: dict[str, Any] = dict(td.get("version", {}))
    needs_schema_org = False

    for key, value in td.items():
        if key == vocab.PROPERTIES:
            out[vocab.EVENTS] = {
                name: _migrate_affordance(affordance) for name, affordance in value.items()
            }
        elif key == "lorav:brand":
            out[vocab.BRAND] = value
            needs_schema_org = True
        elif key == "lorav:model":
            out[vocab.MODEL] = value
            needs_schema_org = True
        elif key == "lorav:hardwareVersion":
            version["model"] = value
        elif key == "lorav:softwareVersion":
            version["instance"] = value
        elif key == "lorav:endDeviceId":
            continue  # the Thing's 'id' already identifies the device
        elif key == "version":
            continue  # re-emitted below, once both halves are known
        else:
            out[key] = value

    if version:
        out["version"] = version
    if needs_schema_org and "@context" in out:
        out["@context"] = _migrate_context(out["@context"])
    return out


def _td_paths(targets: Iterable[str]) -> list[Path]:
    """Expand file and directory arguments into a sorted list of TD paths."""
    paths: set[Path] = set()
    for target in targets:
        path = Path(target)
        paths.update(path.rglob("*.td.json") if path.is_dir() else [path])
    return sorted(paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="+", help="Thing Description files or directories")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report which files would change and exit non-zero, without writing",
    )
    args = parser.parse_args(argv)

    stale: list[Path] = []
    for path in _td_paths(args.targets):
        td = json.loads(path.read_text(encoding="utf-8"))
        if not vocab.uses_withdrawn_vocabulary(td):
            continue
        stale.append(path)
        if args.check:
            continue
        migrated = migrate_td(copy.deepcopy(td))
        path.write_text(json.dumps(migrated, indent=2, ensure_ascii=False) + "\n", "utf-8")
        print(f"migrated {path}")

    if args.check and stale:
        for path in stale:
            print(f"needs migration: {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
