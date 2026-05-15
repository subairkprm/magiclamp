"""
MagicLamp — Internal Event Bus
Loose coupling between all modules. No module imports another directly.
Usage:
  await bus.emit("lead.created", {"lead_id": 42, "team_id": 1})
  bus.subscribe("lead.created", my_handler)
"""

import asyncio
from typing import Callable, Any
from collections import defaultdict
from core.logger import get_logger

log = get_logger("event_bus")


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._running = False

    def subscribe(self, event: str, handler: Callable):
        """Register a handler for an event pattern. Supports wildcards: 'lead.*'"""
        self._subscribers[event].append(handler)
        log.info(f"[Bus] Subscribed: {handler.__name__} → {event}")

    async def emit(self, event: str, data: Any = None, org_id: str = None):
        """Emit an event. All matching subscribers are called."""
        envelope = {"event": event, "data": data or {}, "org_id": org_id}
        await self._queue.put(envelope)

    def emit_sync(self, event: str, data: Any = None, org_id: str = None):
        """Synchronous emit — for use outside async context."""
        envelope = {"event": event, "data": data or {}, "org_id": org_id}
        try:
            self._queue.put_nowait(envelope)
        except asyncio.QueueFull:
            log.warning(f"[Bus] Queue full — dropped event: {event}")

    async def _dispatch(self, envelope: dict):
        event = envelope["event"]
        handlers = []
        for pattern, subs in self._subscribers.items():
            if self._matches(event, pattern):
                handlers.extend(subs)

        if not handlers:
            return

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(envelope)
                else:
                    handler(envelope)
            except Exception as e:
                log.warning(f"[Bus] Handler {handler.__name__} failed for {event}: {e}")

    def _matches(self, event: str, pattern: str) -> bool:
        if pattern == event:
            return True
        if pattern.endswith("*"):
            return event.startswith(pattern[:-1])
        return False

    async def start(self):
        self._running = True
        log.info("[Bus] Event bus started")
        while self._running:
            try:
                envelope = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._dispatch(envelope)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                log.warning(f"[Bus] Dispatch error: {e}")

    async def stop(self):
        self._running = False

    def stats(self) -> dict:
        return {
            "queue_size": self._queue.qsize(),
            "event_types": len(self._subscribers),
            "total_handlers": sum(len(v) for v in self._subscribers.values()),
        }


bus = EventBus()
