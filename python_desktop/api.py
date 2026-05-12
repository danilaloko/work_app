from __future__ import annotations

import platform
from typing import Any

import requests

from storage import AppState


class ApiError(RuntimeError):
    pass


def create_room(state: AppState) -> dict[str, Any]:
    return _post_join_like(state, "/api/rooms")


def join_room(state: AppState) -> dict[str, Any]:
    return _post_join_like(state, "/api/join")


def heartbeat(state: AppState) -> dict[str, Any]:
    if not state.device_token:
        raise ApiError("Нет токена устройства")

    response = requests.post(
        f"{state.server_url.rstrip('/')}/api/presence/heartbeat",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {state.device_token}",
        },
        timeout=10,
    )

    return _parse_response(response)


def update_profile(state: AppState) -> dict[str, Any]:
    if not state.device_token:
        raise ApiError("Нет токена устройства")

    response = requests.post(
        f"{state.server_url.rstrip('/')}/api/presence/profile",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {state.device_token}",
            "Content-Type": "application/json",
        },
        json={
            "avatar_key": state.avatar_key,
            "item_key": state.item_key,
        },
        timeout=10,
    )

    return _parse_response(response)


def apply_join_response(state: AppState, payload: dict[str, Any]) -> None:
    state.device_token = payload["device_token"]
    state.team_id = int(payload["team"]["id"])
    state.team_name = payload["team"]["name"]
    state.user_id = int(payload["user"]["id"])


def _post_join_like(state: AppState, endpoint: str) -> dict[str, Any]:
    response = requests.post(
        f"{state.server_url.rstrip('/')}{endpoint}",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "name": state.name,
            "invite_code": state.invite_code,
            "device_uuid": state.device_uuid,
            "device_name": state.device_name,
            "platform": platform.system().lower(),
            "hostname": platform.node(),
            "avatar_key": state.avatar_key,
            "item_key": state.item_key,
        },
        timeout=10,
    )

    return _parse_response(response)


def _parse_response(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiError(f"Сервер вернул не JSON: HTTP {response.status_code}") from exc

    if response.ok:
        return payload

    message = payload.get("message") or "Ошибка API"
    errors = payload.get("errors")

    if isinstance(errors, dict):
        first_error = next(iter(errors.values()), None)

        if isinstance(first_error, list) and first_error:
            message = first_error[0]

    raise ApiError(message)
