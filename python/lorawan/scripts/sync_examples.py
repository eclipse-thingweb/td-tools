"""Run the example sync as ``python -m scripts.sync_examples``.

The implementation lives in :mod:`lorawan_wot.sync_examples` because the same
entry point is installed as the ``sync-examples`` console script.  This module
is a wrapper rather than a second copy: when it *was* a copy, the two drifted
and the documented command silently behaved differently from this one.
"""

from __future__ import annotations

from lorawan_wot.sync_examples import main

__all__ = ["main"]


if __name__ == "__main__":
    main()
