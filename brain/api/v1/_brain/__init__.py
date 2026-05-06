"""Composed Brain router.

The legacy ``brain/api/v1/brain.py`` was a 715-LoC god-file. It is now a thin
shim that re-exports the ``router`` defined here, while each feature (memory,
reasoning, training, change-log, scheduler) lives in its own focused module.

See ``docs/adr/0001-brain-router-split.md`` for the rationale.
"""

from fastapi import APIRouter

from . import changes, memory, reason, scheduler, training

router = APIRouter(prefix="/brain", tags=["brain"])
router.include_router(memory.router)
router.include_router(reason.router)
router.include_router(training.router)
router.include_router(changes.router)
router.include_router(scheduler.router)

__all__ = ["router"]
