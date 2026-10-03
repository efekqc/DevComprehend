"""Pilot dev-token authentication. Client-supplied user_id is never trusted."""

import os

from .errors import ApiError

# Development only: real pilot auth method is decided separately (DC-004-B ADR).
DEFAULT_DEV_TOKENS = {"dev-token": "user-dev"}


def _token_map() -> dict:
    users = dict(DEFAULT_DEV_TOKENS)
    for pair in os.environ.get("API_DEV_TOKENS", "").split(","):
        if "=" in pair:
            token, user_id = pair.split("=", 1)
            if token.strip() and user_id.strip():
                users[token.strip()] = user_id.strip()
    return users


def authenticate(headers: dict) -> str:
    header = headers.get("authorization", headers.get("Authorization", ""))
    token = header[7:].strip() if header.startswith("Bearer ") else ""
    user_id = _token_map().get(token)
    if not user_id:
        raise ApiError(401, "UNAUTHENTICATED", "Geçerli bir oturum gerekli.")
    return user_id
