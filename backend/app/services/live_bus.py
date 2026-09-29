"""In-process event bus for broadcasting live telemetry pipeline events to SSE subscribers."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Optional, Set

from app.schemas.live_telemetry import LiveEventType, LiveProcessingEvent

logger = logging.getLogger(__name__)


class LiveEventBus:
    """
    In-process prototype event bus for streaming live telemetry pipeline events to SSE subscribers.

    Architecture Note:
    This is an in-memory, single-process prototype event broker suitable for local execution
    and hackathon demonstration. It does not replace a distributed message broker (Redis / Kafka)
    for horizontal multi-instance deployments. It provides:
    - Bounded per-subscriber queues to avoid unbounded memory growth.
    - Dropping oldest events on slow consumers without blocking the telemetry ingestion pipeline.
    - Thread-safe event dispatch from FastAPI sync worker threads into the async event loop.
    - Automatic subscriber cleanup on client disconnect.
    """

    def __init__(self, max_queue_size: int = 200) -> None:
        self.max_queue_size = max_queue_size
        self._subscribers: Set[asyncio.Queue[LiveProcessingEvent]] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the running asyncio event loop."""
        self._loop = loop

    @property
    def subscriber_count(self) -> int:
        """Return the count of active SSE subscriber queues."""
        return len(self._subscribers)

    def subscribe(self) -> asyncio.Queue[LiveProcessingEvent]:
        """Create and register a new subscriber queue."""
        try:
            current_loop = asyncio.get_running_loop()
            if self._loop is None or not self._loop.is_running():
                self._loop = current_loop
        except RuntimeError:
            pass

        queue: asyncio.Queue[LiveProcessingEvent] = asyncio.Queue(maxsize=self.max_queue_size)
        self._subscribers.add(queue)
        logger.debug(f"[LiveEventBus] Subscriber registered. Total subscribers: {len(self._subscribers)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue[LiveProcessingEvent]) -> None:
        """Unregister a subscriber queue."""
        self._subscribers.discard(queue)
        logger.debug(f"[LiveEventBus] Subscriber unregistered. Total subscribers: {len(self._subscribers)}")

    def _safe_put(self, queue: asyncio.Queue[LiveProcessingEvent], event: LiveProcessingEvent) -> None:
        """Put event into queue, dropping oldest if queue is full to avoid unbounded memory."""
        try:
            if queue.full():
                try:
                    queue.get_nowait()
                except (asyncio.QueueEmpty, ValueError):
                    pass
            queue.put_nowait(event)
        except Exception as exc:
            logger.warning(f"[LiveEventBus] Failed to enqueue event to subscriber: {exc}")

    def publish(self, event: LiveProcessingEvent) -> None:
        """
        Broadcast a live processing event to all active subscribers.
        Non-blocking, thread-safe, and tolerates subscriber exceptions.
        """
        if not self._subscribers:
            return

        target_loop = self._loop
        if target_loop is None or not target_loop.is_running():
            try:
                target_loop = asyncio.get_running_loop()
                self._loop = target_loop
            except RuntimeError:
                target_loop = None

        for queue in list(self._subscribers):
            if target_loop and target_loop.is_running():
                try:
                    # If called from a worker thread (FastAPI threadpool), dispatch safely to event loop
                    target_loop.call_soon_threadsafe(self._safe_put, queue, event)
                except RuntimeError:
                    self._safe_put(queue, event)
            else:
                self._safe_put(queue, event)

    def publish_heartbeat(self) -> None:
        """Emit a heartbeat event to keep SSE connections alive."""
        self.publish(
            LiveProcessingEvent(
                type=LiveEventType.HEARTBEAT,
                status="ok",
                timestamp=datetime.now(timezone.utc),
                summary="Aegis3D telemetry stream heartbeat",
            )
        )

    def clear(self) -> None:
        """Clear all subscribers (useful for test isolation)."""
        self._subscribers.clear()


# Global in-process event bus singleton
_live_event_bus = LiveEventBus()


def get_live_event_bus() -> LiveEventBus:
    """Retrieve the global in-process LiveEventBus instance."""
    return _live_event_bus
