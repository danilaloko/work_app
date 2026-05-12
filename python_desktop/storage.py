from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from config import DEFAULT_SERVER_URL, DEFAULT_WS_URL


@dataclass
class AppState:
    server_url: str = DEFAULT_SERVER_URL
    ws_url: str = DEFAULT_WS_URL
    name: str = ""
    invite_code: str = ""
    device_uuid: str = ""
    device_name: str = "Work laptop"
    device_token: str | None = None
    team_id: int | None = None
    team_name: str | None = None
    user_id: int | None = None
    room_overlay_always_on: bool = False
    avatar_key: str = "cat"
    item_key: str = "laptop"
    room_overlay_scale: int = 100

    @property
    def has_session(self) -> bool:
        return bool(self.device_token and self.team_id)


def config_path() -> Path:
    base = Path.home() / ".config" / "presence-desktop"
    base.mkdir(parents=True, exist_ok=True)

    return base / "config.json"


def load_state() -> AppState:
    path = config_path()

    if not path.exists():
        state = AppState(device_uuid=str(uuid.uuid4()))
        save_state(state)
        return state

    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    state = AppState(**{**asdict(AppState()), **raw})

    if not state.device_uuid:
        state.device_uuid = str(uuid.uuid4())
        save_state(state)

    return state


def save_state(state: AppState) -> None:
    config_path().write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_session(state: AppState) -> AppState:
    state.device_token = None
    state.team_id = None
    state.team_name = None
    state.user_id = None
    save_state(state)

    return state
