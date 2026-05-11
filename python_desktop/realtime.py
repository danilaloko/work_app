from __future__ import annotations

import json
import threading
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from PySide6.QtCore import QObject, Signal
from websocket import WebSocketConnectionClosedException, WebSocketTimeoutException, create_connection

from config import RECONNECT_DELAY_SECONDS
from storage import AppState


class RealtimeClient(QObject):
    event_received = Signal(dict)
    status_changed = Signal(str)

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            if not self.state.device_token:
                self.status_changed.emit("Нет токена устройства")
                return

            try:
                url = self._url_with_token()
                self.status_changed.emit("Подключение к realtime...")

                with create_connection(url, timeout=10) as ws:
                    ws.settimeout(1)
                    self.status_changed.emit("Realtime подключен")

                    while not self._stop.is_set():
                        try:
                            raw = ws.recv()
                        except WebSocketTimeoutException:
                            continue
                        except WebSocketConnectionClosedException:
                            break

                        if not raw or raw == "pong":
                            continue

                        payload: dict[str, Any] = json.loads(raw)

                        if payload.get("device", {}).get("device_uuid") == self.state.device_uuid:
                            continue

                        self.event_received.emit(payload)
            except Exception as exc:
                self.status_changed.emit(f"Realtime отключен: {exc}")

            if not self._stop.is_set():
                time.sleep(RECONNECT_DELAY_SECONDS)

    def _url_with_token(self) -> str:
        parsed = urlparse(self.state.ws_url)
        query = dict(parse_qsl(parsed.query))
        query["token"] = self.state.device_token or ""

        return urlunparse(parsed._replace(query=urlencode(query)))
