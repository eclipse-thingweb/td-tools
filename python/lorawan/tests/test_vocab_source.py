"""Keep ``vocab.py`` the only place a ``lorav:`` term is spelled.

The binding's terms are renamed and consolidated as the specification evolves. A
term written as a string literal in a converter is invisible to that process: it
keeps compiling, keeps matching nothing, and silently drops whatever it used to
carry. Routing every mention through :mod:`lorawan_wot.vocab` turns such a
mistake into an import error instead.
"""

from __future__ import annotations

import re

import pytest

from .conftest import REPO_ROOT

SRC_DIR = REPO_ROOT / "src" / "lorawan_wot"

#: Matches a ``lorav:`` term written inline, e.g. ``"lorav:fPort"``.
_INLINE_TERM = re.compile(r"""["']lorav:[A-Za-z]+["']""")


def _modules() -> list[pytest.param]:
    """Every binding module except ``vocab`` itself, which is allowed to spell terms."""
    return [
        pytest.param(path, id=path.name)
        for path in sorted(SRC_DIR.glob("*.py"))
        if path.name != "vocab.py"
    ]


@pytest.mark.parametrize("path", _modules())
def test_module_does_not_spell_terms_inline(path):
    """Terms must be referenced through ``vocab``, not written as literals."""
    found = sorted(set(_INLINE_TERM.findall(path.read_text(encoding="utf-8"))))
    assert not found, (
        f"{path.name} spells binding terms inline: {found}. "
        f"Reference them through lorawan_wot.vocab instead."
    )
