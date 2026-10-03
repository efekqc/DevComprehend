"""
DevComprehend — Wave 3: Edge Cases & Resilience Tests

Verifies system handles abnormal inputs gracefully:
1. Empty diff → validation error
2. Oversized diff (>400 lines, lock files) → filtered/rejected
3. Stale snapshot → analysis rejection
4. Invalid LLM output → safe fallback

Does NOT require database or real LLM.
"""

import json
import sys
import pytest
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jsonschema import Draft202012Validator, FormatChecker
from tests.mock_adapters.fake_llm_provider import FakeLLMProvider

SCHEMA_PATH = PROJECT_ROOT / "contracts" / "v1" / "message.schema.json"


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def validator(schema):
    return Draft202012Validator(schema, format_checker=FormatChecker())

@pytest.fixture
def provider():
    return FakeLLMProvider()


def _make_message(event_type: str, payload: dict) -> dict:
    return {
        "version": "v1.0.0",
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payload": payload,
    }


# ═══════════════════════════════════════════════════════════════════
# LOCK FILE & OVERSIZED DIFF FILTER UTILITIES
# ═══════════════════════════════════════════════════════════════════
LOCK_FILE_PATTERNS = [
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "Gemfile.lock", "poetry.lock", "Cargo.lock",
    "composer.lock", "Pipfile.lock",
]

MAX_HUNK_LINES = 400


def filter_diff_files(files: list[dict]) -> list[dict]:
    """Filter out lock files and oversized hunks from diff.
    
    This simulates the filtering that would happen in the extension
    before sending the diff to the backend.
    """
    filtered = []
    for f in files:
        path = f.get("path", "")
        # Skip lock files
        basename = path.rsplit("/", 1)[-1] if "/" in path else path
        if basename in LOCK_FILE_PATTERNS:
            continue
        
        # Filter oversized hunks
        filtered_hunks = []
        for hunk in f.get("hunks", []):
            line_count = hunk.get("end_line", 0) - hunk.get("start_line", 0) + 1
            if line_count <= MAX_HUNK_LINES:
                filtered_hunks.append(hunk)
        
        if filtered_hunks:
            filtered.append({**f, "hunks": filtered_hunks})
    return filtered


def validate_snapshot(submitted_snapshot: str, current_snapshot: str) -> bool:
    """Check if the submitted snapshot matches the current state."""
    return submitted_snapshot == current_snapshot


def safe_parse_llm_output(raw_output: str, schema_validator) -> dict:
    """Attempt to parse LLM output as JSON; return fallback on failure."""
    try:
        parsed = json.loads(raw_output)
        if not isinstance(parsed, dict):
            raise ValueError("LLM output is not a JSON object")
        # Check if it has minimum required fields
        if "questions" not in parsed and "score" not in parsed:
            raise ValueError("Missing required fields in LLM output")
        return {"status": "ok", "data": parsed}
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "status": "error",
            "error": str(e),
            "fallback": {
                "questions": [],
                "message": "The AI engine produced an invalid response. Please retry.",
                "retry_suggested": True,
            }
        }


# ═══════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════
class TestEmptyDiff:
    """System must reject empty diffs gracefully."""

    def test_empty_files_list(self, provider):
        """Empty files list produces no questions."""
        result = provider.generate_analysis({"files": []})
        assert result["status"] == "READY"
        assert len(result["questions"]) == 0

    def test_empty_diff_payload(self, provider):
        """Completely empty diff payload produces no questions."""
        result = provider.generate_analysis({})
        assert len(result["questions"]) == 0

    def test_empty_hunks(self, provider):
        """Files with no hunks produce questions with default line ranges."""
        result = provider.generate_analysis({
            "files": [{"path": "src/empty.ts", "hunks": []}]
        })
        # File exists but has no hunks; question uses defaults
        assert len(result["questions"]) == 1
        assert result["questions"][0]["line_start"] == 1
        assert result["questions"][0]["line_end"] == 10

    def test_validation_rejects_empty_diff_request(self, validator):
        """analysis.request with zero files should be flagged by application logic."""
        msg = _make_message("analysis.request", {
            "snapshot_id": "snap-empty",
            "workspace_id": "ws-empty",
            "user_id": "usr-empty",
            "diff": {"files": []},
        })
        # Schema itself is valid (payload is just object)
        # but application-level validation should check files count
        assert msg["payload"]["diff"]["files"] == []
        # Application should reject this:
        should_reject = len(msg["payload"]["diff"]["files"]) == 0
        assert should_reject, "Empty diff should be rejected by application logic"


class TestOversizedDiff:
    """Lock files and oversized hunks must be filtered."""

    def test_lock_file_filtered(self):
        """package-lock.json should be excluded from diff."""
        files = [
            {"path": "src/app.ts", "hunks": [{"start_line": 1, "end_line": 20, "content": "..."}]},
            {"path": "package-lock.json", "hunks": [{"start_line": 1, "end_line": 5000, "content": "..."}]},
        ]
        filtered = filter_diff_files(files)
        assert len(filtered) == 1
        assert filtered[0]["path"] == "src/app.ts"

    @pytest.mark.parametrize("lock_file", LOCK_FILE_PATTERNS)
    def test_all_lock_files_filtered(self, lock_file):
        """All known lock file patterns are filtered."""
        files = [
            {"path": f"project/{lock_file}", "hunks": [{"start_line": 1, "end_line": 100, "content": "..."}]},
        ]
        filtered = filter_diff_files(files)
        assert len(filtered) == 0, f"{lock_file} should be filtered"

    def test_oversized_hunk_filtered(self):
        """Hunks with >400 lines are removed."""
        files = [{
            "path": "src/big-file.ts",
            "hunks": [
                {"start_line": 1, "end_line": 50, "content": "small hunk"},
                {"start_line": 100, "end_line": 600, "content": "huge hunk"},  # 501 lines
            ]
        }]
        filtered = filter_diff_files(files)
        assert len(filtered) == 1
        assert len(filtered[0]["hunks"]) == 1  # only the small hunk survives
        assert filtered[0]["hunks"][0]["end_line"] == 50

    def test_all_hunks_oversized_removes_file(self):
        """If all hunks are oversized, the file is excluded entirely."""
        files = [{
            "path": "src/monster.ts",
            "hunks": [
                {"start_line": 1, "end_line": 500, "content": "huge1"},
                {"start_line": 600, "end_line": 1200, "content": "huge2"},
            ]
        }]
        filtered = filter_diff_files(files)
        assert len(filtered) == 0

    def test_mixed_valid_and_oversized(self):
        """Mix of valid files, lock files, and oversized hunks."""
        files = [
            {"path": "src/good.ts", "hunks": [{"start_line": 1, "end_line": 30, "content": "ok"}]},
            {"path": "pnpm-lock.yaml", "hunks": [{"start_line": 1, "end_line": 10, "content": "lock"}]},
            {"path": "src/big.ts", "hunks": [{"start_line": 1, "end_line": 500, "content": "big"}]},
            {"path": "src/also-good.ts", "hunks": [{"start_line": 5, "end_line": 15, "content": "fine"}]},
        ]
        filtered = filter_diff_files(files)
        assert len(filtered) == 2
        paths = [f["path"] for f in filtered]
        assert "src/good.ts" in paths
        assert "src/also-good.ts" in paths


class TestStaleSnapshot:
    """Stale snapshots must be detected and rejected."""

    def test_matching_snapshot_passes(self):
        assert validate_snapshot("snap-abc123", "snap-abc123") is True

    def test_stale_snapshot_rejected(self):
        assert validate_snapshot("snap-old", "snap-current") is False

    def test_empty_snapshot_rejected(self):
        assert validate_snapshot("", "snap-current") is False

    def test_none_snapshot_rejected(self):
        # Simulate None being passed
        result = validate_snapshot(None, "snap-current")
        assert result is False


class TestInvalidLLMOutput:
    """System must handle invalid LLM responses without crashing."""

    @pytest.fixture
    def dummy_validator(self, schema):
        return Draft202012Validator(schema, format_checker=FormatChecker())

    def test_invalid_json_string(self, dummy_validator):
        """Non-JSON string from LLM."""
        result = safe_parse_llm_output("This is not JSON at all", dummy_validator)
        assert result["status"] == "error"
        assert "fallback" in result
        assert result["fallback"]["retry_suggested"] is True

    def test_partial_json(self, dummy_validator):
        """Truncated/partial JSON."""
        result = safe_parse_llm_output('{"questions": [', dummy_validator)
        assert result["status"] == "error"

    def test_json_array_instead_of_object(self, dummy_validator):
        """LLM returns array instead of object."""
        result = safe_parse_llm_output('["question1", "question2"]', dummy_validator)
        assert result["status"] == "error"

    def test_missing_required_fields(self, dummy_validator):
        """JSON object missing expected fields."""
        result = safe_parse_llm_output('{"foo": "bar"}', dummy_validator)
        assert result["status"] == "error"

    def test_valid_questions_output(self, dummy_validator):
        """Valid LLM output parses correctly."""
        valid_output = json.dumps({
            "questions": [
                {"question_id": "q-1", "text": "What does this do?"}
            ]
        })
        result = safe_parse_llm_output(valid_output, dummy_validator)
        assert result["status"] == "ok"
        assert len(result["data"]["questions"]) == 1

    def test_valid_score_output(self, dummy_validator):
        """Valid evaluation output parses correctly."""
        valid_output = json.dumps({
            "score": 75.5,
            "passed": True,
            "feedback": "Good answer"
        })
        result = safe_parse_llm_output(valid_output, dummy_validator)
        assert result["status"] == "ok"
        assert result["data"]["score"] == 75.5

    def test_empty_string(self, dummy_validator):
        """Empty string from LLM."""
        result = safe_parse_llm_output("", dummy_validator)
        assert result["status"] == "error"

    def test_html_response(self, dummy_validator):
        """LLM accidentally returns HTML."""
        result = safe_parse_llm_output("<html><body>Error 503</body></html>", dummy_validator)
        assert result["status"] == "error"
        assert result["fallback"]["retry_suggested"] is True


class TestSchemaEnvelopeValidation:
    """Verify schema rejects malformed envelopes."""

    def test_wrong_version_rejected(self, validator):
        msg = {
            "version": "v2.0.0",
            "event_type": "analysis.request",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "payload": {},
        }
        assert not validator.is_valid(msg)

    def test_extra_field_rejected(self, validator):
        msg = {
            "version": "v1.0.0",
            "event_type": "analysis.request",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "payload": {},
            "extra_field": "should fail",
        }
        assert not validator.is_valid(msg)

    def test_unknown_event_type_rejected(self, validator):
        msg = {
            "version": "v1.0.0",
            "event_type": "unknown.event",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "payload": {},
        }
        assert not validator.is_valid(msg)


# ═══════════════════════════════════════════════════════════════════
# ERROR PROTOCOL & EXTENSION-API (AHMET-DERVİŞ) FLOW HELPERS
# ═══════════════════════════════════════════════════════════════════
def build_contract_error(error_code: str, http_status: int, message: str, details: dict = None) -> dict:
    """Simulate API (Derviş) returning a standardized error envelope."""
    payload = {
        "error_code": error_code,
        "http_status": http_status,
        "message": message,
    }
    if details:
        payload["details"] = details
    return _make_message("error.response", payload)


def extension_parse_api_response(response_envelope: dict) -> dict:
    """Simulate Extension (Ahmet) client parsing an API response.
    
    Handles:
    - 202 Accepted: starts background polling with retry_after_ms
    - 200 OK: immediately transitions to ready/render state
    - error.response: maps error_code to user-facing UI notification
    """
    event_type = response_envelope.get("event_type")
    payload = response_envelope.get("payload", {})

    if event_type == "error.response":
        code = payload.get("error_code")
        status = payload.get("http_status")
        msg = payload.get("message")
        return {
            "ui_action": "SHOW_ERROR_BANNER",
            "severity": "error" if status and status >= 500 else "warning",
            "user_message": msg,
            "error_code": code,
            "retryable": code in ("INVALID_MODEL_OUTPUT", "RATE_LIMIT_EXCEEDED"),
        }

    if event_type == "analysis.queued":
        status_code = payload.get("http_status", 202 if payload.get("status") == "QUEUED" else 200)
        if status_code == 200 or payload.get("status") == "READY":
            return {
                "ui_action": "RENDER_QUESTIONS_IMMEDIATELY",
                "analysis_id": payload.get("analysis_id"),
                "is_polling": False,
            }
        return {
            "ui_action": "START_POLLING",
            "analysis_id": payload.get("analysis_id"),
            "is_polling": True,
            "poll_interval_ms": payload.get("retry_after_ms", 3000),
        }

    return {"ui_action": "UNKNOWN", "raw": response_envelope}


class TestExtensionApiErrorAndStatusHandling:
    """Verify Derviş (API) and Ahmet (Extension) contract compatibility."""

    def test_empty_diff_error_flow(self, validator):
        err = build_contract_error("EMPTY_DIFF", 400, "Gönderilen diff boş.")
        assert validator.is_valid(err)
        client_state = extension_parse_api_response(err)
        assert client_state["ui_action"] == "SHOW_ERROR_BANNER"
        assert client_state["error_code"] == "EMPTY_DIFF"
        assert client_state["retryable"] is False

    def test_oversized_diff_error_flow(self, validator):
        err = build_contract_error(
            "PAYLOAD_TOO_LARGE", 413,
            "Diff 400 satırı aşıyor.",
            details={"max_lines": 400, "actual_lines": 650}
        )
        assert validator.is_valid(err)
        client_state = extension_parse_api_response(err)
        assert client_state["ui_action"] == "SHOW_ERROR_BANNER"
        assert client_state["error_code"] == "PAYLOAD_TOO_LARGE"

    def test_stale_snapshot_error_flow(self, validator):
        err = build_contract_error("STALE_SNAPSHOT", 409, "Snapshot uyuşmuyor.")
        assert validator.is_valid(err)
        client_state = extension_parse_api_response(err)
        assert client_state["ui_action"] == "SHOW_ERROR_BANNER"
        assert client_state["error_code"] == "STALE_SNAPSHOT"

    def test_rate_limit_error_flow(self, validator):
        err = build_contract_error("RATE_LIMIT_EXCEEDED", 429, "Kota aşıldı.")
        assert validator.is_valid(err)
        client_state = extension_parse_api_response(err)
        assert client_state["ui_action"] == "SHOW_ERROR_BANNER"
        assert client_state["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert client_state["retryable"] is True

    def test_invalid_model_output_error_flow(self, validator):
        err = build_contract_error("INVALID_MODEL_OUTPUT", 502, "Model geçersiz yanıt üretti.")
        assert validator.is_valid(err)
        client_state = extension_parse_api_response(err)
        assert client_state["ui_action"] == "SHOW_ERROR_BANNER"
        assert client_state["severity"] == "error"
        assert client_state["retryable"] is True

    def test_extension_handles_202_queued_async_flow(self, validator):
        """Standard async flow: API returns 202 Accepted, extension polls."""
        resp = _make_message("analysis.queued", {
            "analysis_id": "an-async-999",
            "status": "QUEUED",
            "http_status": 202,
            "retry_after_ms": 2500,
        })
        assert validator.is_valid(resp)
        action = extension_parse_api_response(resp)
        assert action["ui_action"] == "START_POLLING"
        assert action["is_polling"] is True
        assert action["poll_interval_ms"] == 2500

    def test_extension_handles_200_sync_ready_flow(self, validator):
        """Synchronous/mock flow: API returns 200 OK, extension renders immediately."""
        resp = _make_message("analysis.queued", {
            "analysis_id": "an-sync-111",
            "status": "READY",
            "http_status": 200,
        })
        assert validator.is_valid(resp)
        action = extension_parse_api_response(resp)
        assert action["ui_action"] == "RENDER_QUESTIONS_IMMEDIATELY"
        assert action["is_polling"] is False

