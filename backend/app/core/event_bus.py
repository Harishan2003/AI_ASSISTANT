"""
Asynchronous Event Bus for Friday AI PC Agent.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], Any]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[Any], Any]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def on(self, event_type: str, handler: Callable[[Any], Any]):
        """Alias for subscribe."""
        self.subscribe(event_type, handler)

    def unsubscribe(self, event_type: str, handler: Callable[[Any], Any]):
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def emit(self, event_type: str, data: Any = None):
        """Emits or publishes an event to all registered subscriber callbacks."""
        handlers = self._subscribers.get(event_type, [])
        for h in handlers:
            try:
                if asyncio.iscoroutinefunction(h):
                    asyncio.create_task(h(data))
                else:
                    h(data)
            except Exception as e:
                print(f"[EventBus Error in {event_type}]: {e}", flush=True)

    async def publish(self, event_type: str, data: Any = None):
        """Alias for emit."""
        await self.emit(event_type, data)


event_bus = EventBus()
