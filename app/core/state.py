from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SystemStateStore:
    def __init__(self) -> None:
        started_at = _utc_now()
        self._lock = Lock()
        self._state: dict[str, Any] = {
            "status": "starting",
            "started_at": started_at,
            "updated_at": started_at,
            "paused": False,
            "active_file": None,
            "eta": None,
            "transcription_model": None,
            "ollama_model": None,
            "history_dir": "",
            "log_file": "",
            "last_error": None,
        }
        self._services: dict[str, dict[str, Any]] = {}

    def set_paths(self, *, history_dir: str, log_file: str) -> None:
        self.update(history_dir=history_dir, log_file=log_file)

    def update(self, **fields: Any) -> None:
        with self._lock:
            self._state.update(fields)
            self._state["updated_at"] = _utc_now()

    def update_service(self, name: str, status: str, detail: str | None = None) -> None:
        with self._lock:
            self._services[name] = {
                "name": name,
                "status": status,
                "detail": detail,
                "updated_at": _utc_now(),
            }
            self._state["updated_at"] = _utc_now()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            snapshot = deepcopy(self._state)
            snapshot["services"] = list(self._services.values())
        return snapshot


system_state = SystemStateStore()
