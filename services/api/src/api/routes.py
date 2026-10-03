"""HTTP routing boundary: /v1 endpoints → domain service, with safe envelopes."""

import json
import re

from .auth import authenticate
from .errors import ApiError, envelope

MAX_BODY_BYTES = 64_000
ANALYSIS_PATH = re.compile(r"^/v1/analyses/([^/]+)$")
ANSWER_PATH = re.compile(r"^/v1/analyses/([^/]+)/answers$")


def _parse_body(raw: bytes):
    if len(raw) > MAX_BODY_BYTES:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "İstek gövdesi boyut sınırını aşıyor.")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise ApiError(400, "INVALID_INPUT", "Geçerli JSON gövdesi gerekli.") from None


def dispatch(service, method: str, path: str, headers: dict, raw_body: bytes) -> tuple[int, dict]:
    try:
        user_id = authenticate(headers)
        if method == "POST" and path == "/v1/analyses":
            return 200, service.create_analysis(user_id, _parse_body(raw_body))
        match = ANALYSIS_PATH.fullmatch(path)
        if method == "GET" and match:
            return 200, service.get_analysis(user_id, match.group(1))
        match = ANSWER_PATH.fullmatch(path)
        if method == "POST" and match:
            return 200, service.submit_answer(user_id, match.group(1), _parse_body(raw_body))
        raise ApiError(404, "NOT_FOUND", "Endpoint bulunamadı.")
    except ApiError as error:
        return envelope(error)
    except Exception:
        # No exception text, source or answer content reaches the client.
        return envelope(ApiError(500, "INTERNAL", "İşlem tamamlanamadı.", True))
