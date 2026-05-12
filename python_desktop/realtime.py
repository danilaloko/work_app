from __future__ import annotations

import json
import queue
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
        self._ws: Any | None = None
        self._outgoing: queue.Queue[dict[str, Any]] = queue.Queue()

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

                ws = create_connection(url, timeout=10)

                try:
                    self._ws = ws
                    ws.settimeout(1)
                    self.status_changed.emit("Realtime подключен")

                    while not self._stop.is_set():
                        self._flush_outgoing(ws)

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
                finally:
                    self._ws = None
                    ws.close()
            except Exception as exc:
                self.status_changed.emit(f"Realtime отключен: {exc}")

            if not self._stop.is_set():
                time.sleep(RECONNECT_DELAY_SECONDS)

    def _url_with_token(self) -> str:
        parsed = urlparse(self.state.ws_url)
        query = dict(parse_qsl(parsed.query))
        query["token"] = self.state.device_token or ""

        return urlunparse(parsed._replace(query=urlencode(query)))

    def send_profile_update(self) -> None:
        self._outgoing.put(
            {
                "type": "profile_updated",
                "avatar_key": self.state.avatar_key,
                "item_key": self.state.item_key,
            }
        )

    def _flush_outgoing(self, ws: Any) -> None:
        while True:
            try:
                payload = self._outgoing.get_nowait()
            except queue.Empty:
                return

            ws.send(json.dumps(payload, ensure_ascii=False))
