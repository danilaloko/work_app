"""Simple presence WebSocket service for the Python desktop MVP.

Run this on the same server as Laravel so it can read the Laravel SQLite DB:

    python ws_server.py --db /var/www/work_app/database/database.sqlite --host 0.0.0.0 --port 8765

Clients connect to:

    ws://SERVER_IP:8765/ws/presence?token=DEVICE_TOKEN
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import signal
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from websockets.exceptions import ConnectionClosed
from websockets.legacy.server import WebSocketServerProtocol, serve

AVATAR_KEYS = {"cat", "dog", "fox", "robot"}
ITEM_KEYS = {"coffee", "laptop", "book", "plant"}


@dataclass(frozen=True)
class PresenceDevice:
    team_id: int
    user: dict[str, Any]
    device: dict[str, Any]


class PresenceHub:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.connections: dict[int, set[WebSocketServerProtocol]] = {}
        self.devices: dict[WebSocketServerProtocol, PresenceDevice] = {}

    async def handler(self, websocket: WebSocketServerProtocol) -> None:
        device = self.authenticate(websocket.path)

        if device is None:
            await websocket.close(code=4401, reason="Unauthorized")
            return

        self.connections.setdefault(device.team_id, set()).add(websocket)
        self.devices[websocket] = device

        for existing_socket, existing_device in list(self.devices.items()):
            if existing_socket == websocket or existing_device.team_id != device.team_id:
                continue

            await websocket.send(
                json.dumps(
                    {
                        "type": "member_online",
                        "team_id": existing_device.team_id,
                        "user": existing_device.user,
                        "device": existing_device.device,
                    },
                    ensure_ascii=False,
                )
            )

        await self.broadcast(
            device.team_id,
            {
                "type": "member_online",
                "team_id": device.team_id,
                "user": device.user,
                "device": device.device,
            },
            exclude=websocket,
        )

        try:
            async for message in websocket:
                if message == "ping":
                    await websocket.send("pong")
                    continue

                await self.handle_client_message(websocket, message)
        finally:
            await self.disconnect(websocket)

    async def handle_client_message(self, websocket: WebSocketServerProtocol, message: str) -> None:
        device = self.devices.get(websocket)

        if device is None:
            return

        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            return

        if payload.get("type") != "profile_updated":
            return

        avatar_key = payload.get("avatar_key")
        item_key = payload.get("item_key")

        if avatar_key not in AVATAR_KEYS or item_key not in ITEM_KEYS:
            return

        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "update users set avatar_key = ?, item_key = ?, updated_at = CURRENT_TIMESTAMP where id = ?",
                (avatar_key, item_key, device.user["id"]),
            )

        device.user["avatar_key"] = avatar_key
        device.user["item_key"] = item_key

        await self.broadcast(
            device.team_id,
            {
                "type": "member_updated",
                "team_id": device.team_id,
                "user": device.user,
                "device": device.device,
            },
            exclude=websocket,
        )

    def authenticate(self, path: str) -> PresenceDevice | None:
        parsed = urlparse(path)
        token = parse_qs(parsed.query).get("token", [None])[0]

        if not token:
            return None

        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                select
                    devices.id as device_id,
                    devices.team_id,
                    devices.user_id,
                    devices.device_uuid,
                    devices.name as device_name,
                    devices.platform,
                    devices.hostname,
                    users.name as user_name,
                    users.avatar_url,
                    users.avatar_key,
                    users.item_key
                from devices
                join users on users.id = devices.user_id
                where devices.token_hash = ?
                limit 1
                """,
                (token_hash,),
            ).fetchone()

        if row is None:
            return None

        return PresenceDevice(
            team_id=int(row["team_id"]),
            user={
                "id": int(row["user_id"]),
                "name": row["user_name"],
                "avatar_url": row["avatar_url"],
                "avatar_key": row["avatar_key"] or "cat",
                "item_key": row["item_key"] or "laptop",
            },
            device={
                "id": int(row["device_id"]),
                "device_uuid": row["device_uuid"],
                "name": row["device_name"],
                "platform": row["platform"],
                "hostname": row["hostname"],
            },
        )

    async def disconnect(self, websocket: WebSocketServerProtocol) -> None:
        device = self.devices.pop(websocket, None)

        if device is None:
            return

        team_connections = self.connections.get(device.team_id)

        if team_connections is not None:
            team_connections.discard(websocket)

            if not team_connections:
                self.connections.pop(device.team_id, None)

        await self.broadcast(
            device.team_id,
            {
                "type": "member_offline",
                "team_id": device.team_id,
                "user": device.user,
                "device": device.device,
            },
        )

    async def broadcast(
        self,
        team_id: int,
        payload: dict[str, Any],
        exclude: WebSocketServerProtocol | None = None,
    ) -> None:
        message = json.dumps(payload)
        dead_connections: list[WebSocketServerProtocol] = []

        for websocket in self.connections.get(team_id, set()).copy():
            if websocket is exclude:
                continue

            try:
                await websocket.send(message)
            except ConnectionClosed:
                dead_connections.append(websocket)

        for websocket in dead_connections:
            await self.disconnect(websocket)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="../database/database.sqlite")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    db_path = Path(args.db).expanduser().resolve()

    if not db_path.exists():
        raise SystemExit(f"Database file not found: {db_path}")

    hub = PresenceHub(db_path)
    stop = asyncio.Future()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    async with serve(hub.handler, args.host, args.port):
        print(f"Presence WebSocket listening on ws://{args.host}:{args.port}")
        await stop


if __name__ == "__main__":
    asyncio.run(main())
