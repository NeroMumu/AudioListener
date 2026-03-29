from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request

import pystray
from PIL import Image, ImageDraw

from app.config import settings


@dataclass(slots=True)
class BackendStatusSnapshot:
    status: str = "starting"
    detail: str = "Initialisation du backend"
    available: bool = False
    active_file: str | None = None
    eta: str | None = None


class DesktopSupervisor:
    def __init__(self) -> None:
        self.base_dir = settings.base_dir
        self.app_url = f"http://{settings.server_host}:{settings.server_port}"
        self.backend_process: subprocess.Popen[bytes] | None = None
        self.backend_owned = False
        self.stop_event = threading.Event()
        self.icon: pystray.Icon | None = None
        self._snapshot_lock = threading.Lock()
        self._snapshot = BackendStatusSnapshot()

    def run(self) -> None:
        try:
            self.icon = pystray.Icon(
                "AudioJournal",
                self._create_image("starting"),
                settings.systray_title,
                self._build_menu(),
            )

            self.start_backend()
            threading.Thread(target=self._monitor_loop, daemon=True).start()
            self.icon.run()
        except Exception:
            self.stop_backend()
            raise

    def start_backend(self) -> None:
        if self.backend_process is not None and self.backend_process.poll() is None:
            return

        existing_payload = self._probe_backend_state()
        if existing_payload is not None:
            self.backend_process = None
            self.backend_owned = False
            self._apply_remote_snapshot(existing_payload, detail="Backend existant détecté")
            return

        command = [sys.executable, "-u", "run_server.py"]
        self.backend_process = subprocess.Popen(command, cwd=str(self.base_dir))
        self.backend_owned = True
        self._set_snapshot("starting", "Démarrage du backend", available=False)

    def stop_backend(self) -> None:
        process = self.backend_process
        if process is None or not self.backend_owned:
            return

        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        self.backend_process = None
        self.backend_owned = False
        self._set_snapshot("stopped", "Backend arrêté", available=False)

    def restart_backend(self, icon: pystray.Icon | None = None, item: pystray.MenuItem | None = None) -> None:
        del icon, item
        self.stop_backend()
        time.sleep(1)
        self.start_backend()

    def quit(self, icon: pystray.Icon | None = None, item: pystray.MenuItem | None = None) -> None:
        del item
        self.stop_event.set()
        self.stop_backend()
        if icon is not None:
            icon.stop()

    def open_root(self, icon: pystray.Icon | None = None, item: pystray.MenuItem | None = None) -> None:
        del icon, item
        os.startfile(str(self.base_dir))  # type: ignore[attr-defined]

    def open_browser(self, icon: pystray.Icon | None = None, item: pystray.MenuItem | None = None) -> None:
        del icon, item
        webbrowser.open(self.app_url)

    def open_history(self, icon: pystray.Icon | None = None, item: pystray.MenuItem | None = None) -> None:
        del icon, item
        settings.history_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(settings.history_dir))  # type: ignore[attr-defined]

    def open_logs(self, icon: pystray.Icon | None = None, item: pystray.MenuItem | None = None) -> None:
        del icon, item
        settings.server_log_file.parent.mkdir(parents=True, exist_ok=True)
        settings.server_log_file.touch(exist_ok=True)
        os.startfile(str(settings.server_log_file))  # type: ignore[attr-defined]

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(self._status_text, None, enabled=False),
            pystray.MenuItem(self._detail_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Ouvrir l'interface", self.open_browser, default=True),
            pystray.MenuItem("Ouvrir la racine", self.open_root),
            pystray.MenuItem("Ouvrir History", self.open_history),
            pystray.MenuItem("Voir les logs", self.open_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Redémarrer le backend", self.restart_backend),
            pystray.MenuItem("Quitter", self.quit),
        )

    def _status_text(self, item: pystray.MenuItem) -> str:
        del item
        snapshot = self._get_snapshot()
        return f"État : {snapshot.status}"

    def _detail_text(self, item: pystray.MenuItem) -> str:
        del item
        snapshot = self._get_snapshot()
        if snapshot.active_file:
            eta = f" · ETA {snapshot.eta}" if snapshot.eta else ""
            return f"Fichier : {snapshot.active_file}{eta}"
        return snapshot.detail

    def _monitor_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self._refresh_backend_status()
            except Exception:
                self._set_snapshot("error", "Supervision en erreur", available=False)

            if self.icon is not None:
                snapshot = self._get_snapshot()
                self.icon.icon = self._create_image(snapshot.status)
                self.icon.title = f"{settings.systray_title} · {snapshot.status}"
                self.icon.update_menu()

            time.sleep(settings.systray_poll_interval_seconds)

    def _refresh_backend_status(self) -> None:
        process = self.backend_process
        if process is None:
            payload = self._probe_backend_state()
            if payload is not None:
                self._apply_remote_snapshot(payload, detail="Backend externe détecté")
            else:
                self._set_snapshot("stopped", "Backend non démarré", available=False)
            return

        exit_code = process.poll()
        if exit_code is not None:
            self.backend_process = None
            self.backend_owned = False
            self._set_snapshot("error", f"Backend arrêté (code {exit_code})", available=False)
            return

        payload = self._probe_backend_state()
        if payload is None:
            self._set_snapshot("starting", "Backend en cours de démarrage", available=False)
            return

        self._apply_remote_snapshot(payload, detail="Backend prêt")

    def _probe_backend_state(self) -> dict[str, Any] | None:
        try:
            return self._fetch_json(f"{self.app_url}/api/system/state")
        except error.URLError:
            return None

    def _fetch_json(self, url: str) -> dict[str, Any]:
        http_request = request.Request(url, headers={"Accept": "application/json"}, method="GET")
        with request.urlopen(http_request, timeout=2.0) as response:
            return json.loads(response.read().decode("utf-8"))

    def _apply_remote_snapshot(self, payload: dict[str, Any], *, detail: str) -> None:
        self._set_snapshot(
            str(payload.get("status", "unknown")),
            detail,
            available=True,
            active_file=payload.get("active_file"),
            eta=payload.get("eta"),
        )

    def _set_snapshot(
        self,
        status: str,
        detail: str,
        *,
        available: bool,
        active_file: str | None = None,
        eta: str | None = None,
    ) -> None:
        with self._snapshot_lock:
            self._snapshot = BackendStatusSnapshot(
                status=status,
                detail=detail,
                available=available,
                active_file=active_file,
                eta=eta,
            )

    def _get_snapshot(self) -> BackendStatusSnapshot:
        with self._snapshot_lock:
            return BackendStatusSnapshot(
                status=self._snapshot.status,
                detail=self._snapshot.detail,
                available=self._snapshot.available,
                active_file=self._snapshot.active_file,
                eta=self._snapshot.eta,
            )

    def _create_image(self, status: str) -> Image.Image:
        base_image = self._load_base_image()
        image = base_image.copy().convert("RGBA")
        draw = ImageDraw.Draw(image)
        size = image.size[0]
        badge_size = int(size * 0.38)
        padding = int(size * 0.08)
        left = size - badge_size - padding
        top = size - badge_size - padding
        right = size - padding
        bottom = size - padding
        draw.ellipse((left, top, right, bottom), fill=self._status_color(status), outline="white", width=max(2, size // 24))
        return image

    def _load_base_image(self) -> Image.Image:
        icon_path = settings.systray_icon_path
        if icon_path and str(icon_path).strip() and icon_path.is_file():
            try:
                return Image.open(icon_path).convert("RGBA")
            except OSError:
                pass

        canvas = Image.new("RGBA", (64, 64), "#1f2937")
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((10, 10, 54, 54), radius=12, fill="#111827", outline="#e5e7eb", width=2)
        draw.rectangle((28, 18, 36, 38), fill="#e5e7eb")
        draw.ellipse((22, 34, 42, 54), fill="#e5e7eb")
        return canvas

    def _status_color(self, status: str) -> str:
        normalized = status.lower()
        if normalized in {"idle", "ready", "listening"}:
            return "#2ecc71"
        if normalized in {"starting", "loading", "stopping"}:
            return "#f39c12"
        if normalized in {"paused"}:
            return "#3498db"
        return "#e74c3c"
