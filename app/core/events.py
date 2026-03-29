from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from threading import Lock
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(slots=True)
class AppLogEvent:
    event_id: int
    timestamp: str
    level: str
    source: str
    message: str
    code: str | None = None
    job_id: str | None = None
    payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "level": self.level,
            "source": self.source,
            "message": self.message,
            "code": self.code,
            "job_id": self.job_id,
            "payload": self.payload,
        }


class EventBus:
    def __init__(self, max_events: int = 500) -> None:
        self._events: deque[AppLogEvent] = deque(maxlen=max_events)
        self._subscribers: set[asyncio.Queue[AppLogEvent]] = set()
        self._sequence = count(1)
        self._lock = Lock()

    def publish(
        self,
        *,
        level: str,
        source: str,
        message: str,
        code: str | None = None,
        job_id: str | None = None,
        payload: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> AppLogEvent:
        event = AppLogEvent(
            event_id=next(self._sequence),
            timestamp=timestamp or _utc_now(),
            level=level.upper(),
            source=source,
            message=message,
            code=code,
            job_id=job_id,
            payload=payload,
        )

        with self._lock:
            self._events.append(event)
            subscribers = tuple(self._subscribers)

        for queue in subscribers:
            self._publish_to_queue(queue, event)

        return event

    def publish_log_record(self, record: logging.LogRecord) -> AppLogEvent:
        return self.publish(
            timestamp=datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            level=record.levelname,
            source=record.name,
            message=record.getMessage(),
            code=getattr(record, "event_code", None),
            job_id=getattr(record, "job_id", None),
            payload=getattr(record, "event_payload", None),
        )

    def recent(self, limit: int = 100) -> list[AppLogEvent]:
        with self._lock:
            items = list(self._events)
        if limit <= 0:
            return []
        return items[-limit:]

    def subscribe(self, max_queue_size: int = 200) -> asyncio.Queue[AppLogEvent]:
        queue: asyncio.Queue[AppLogEvent] = asyncio.Queue(maxsize=max_queue_size)
        with self._lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[AppLogEvent]) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def _publish_to_queue(self, queue: asyncio.Queue[AppLogEvent], event: AppLogEvent) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                return


event_bus = EventBus()
