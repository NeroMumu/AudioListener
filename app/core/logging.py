from __future__ import annotations

import logging
from pathlib import Path

from app.core.events import event_bus


class EventBridgeHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if getattr(record, "skip_event_bus", False):
            return

        try:
            event_bus.publish_log_record(record)
        except Exception:
            self.handleError(record)


def configure_logging(log_file: Path, level_name: str = "INFO") -> None:
    resolved_level = getattr(logging, str(level_name).upper(), logging.INFO)
    root_logger = logging.getLogger()

    if getattr(root_logger, "_audio_listener_logging_configured", False):
        root_logger.setLevel(resolved_level)
        return

    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(resolved_level)
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(resolved_level)
    file_handler.setFormatter(formatter)

    event_handler = EventBridgeHandler()
    event_handler.setLevel(resolved_level)

    root_logger.handlers.clear()
    root_logger.setLevel(resolved_level)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(event_handler)
    root_logger._audio_listener_logging_configured = True  # type: ignore[attr-defined]

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
