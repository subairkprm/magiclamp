"""Backward-compatible shim for ``api.v1.brain``.

The implementation has been split into the ``api.v1._brain`` package
(see ``docs/adr/0001-brain-router-split.md``). This module continues to expose
the same public name — ``router`` — so existing imports (notably
``brain/main.py``) keep working unchanged.
"""

from ._brain import router

__all__ = ["router"]
