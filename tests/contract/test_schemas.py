"""
DevComprehend — Contract Schema Validation Tests

Validates that all synthetic JSON fixtures conform to the
message.schema.json (JSON Schema Draft 2020-12).
"""

import json
import os
import pytest
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "contracts" / "v1" / "message.schema.json"
EXAMPLES_DIR = PROJECT_ROOT / "contracts" / "v1" / "examples"

# ─── Fixtures ─────────────────────────────────────────────────────────────────
FIXTURE_FILES = [
    "analysis-request.json",
    "analysis-queued.json",
    "analysis-ready.json",
    "answer-request.json",
    "evaluation-result.json",
    "error-response.json",
]


@pytest.fixture(scope="module")
def schema():
    """Load and return the message schema."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def validator(schema):
    """Create a Draft 2020-12 validator instance."""
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


class TestSchemaValidity:
    """Verify the schema itself is a valid JSON Schema Draft 2020-12."""

    def test_schema_file_exists(self):
        assert SCHEMA_PATH.exists(), f"Schema file not found: {SCHEMA_PATH}"

    def test_schema_is_valid_json(self):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        assert "$schema" in schema
        assert "2020-12" in schema["$schema"]

    def test_schema_has_required_fields(self):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        assert "required" in schema
        required = schema["required"]
        for field in ["version", "event_type", "timestamp", "payload"]:
            assert field in required, f"Missing required field: {field}"


class TestFixtureValidation:
    """Validate each synthetic fixture against the message schema."""

    @pytest.mark.parametrize("fixture_file", FIXTURE_FILES)
    def test_fixture_conforms_to_schema(self, validator, fixture_file):
        fixture_path = EXAMPLES_DIR / fixture_file
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        errors = list(validator.iter_errors(data))
        assert len(errors) == 0, (
            f"Fixture '{fixture_file}' has schema violations:\n"
            + "\n".join(f"  - {e.message}" for e in errors)
        )

    @pytest.mark.parametrize("fixture_file", FIXTURE_FILES)
    def test_fixture_has_correct_version(self, fixture_file):
        fixture_path = EXAMPLES_DIR / fixture_file
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["version"] == "v1.0.0"

    @pytest.mark.parametrize("fixture_file", FIXTURE_FILES)
    def test_fixture_has_valid_event_type(self, fixture_file):
        fixture_path = EXAMPLES_DIR / fixture_file
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        valid_types = {
            "analysis.request", "analysis.queued", "analysis.ready",
            "answer.request", "evaluation.result", "error.response"
        }
        assert data["event_type"] in valid_types


class TestErrorResponseSchema:
    """Verify error.response schema and status code handling."""

    def test_valid_error_payload(self, validator):
        msg = {
            "version": "v1.0.0",
            "event_type": "error.response",
            "timestamp": "2026-10-03T05:00:00Z",
            "payload": {
                "error_code": "EMPTY_DIFF",
                "http_status": 400,
                "message": "Empty diff provided",
            }
        }
        assert validator.is_valid(msg)

    @pytest.mark.parametrize("code,status", [
        ("EMPTY_DIFF", 400),
        ("PAYLOAD_TOO_LARGE", 413),
        ("STALE_SNAPSHOT", 409),
        ("RATE_LIMIT_EXCEEDED", 429),
        ("INVALID_MODEL_OUTPUT", 502),
    ])
    def test_all_standard_error_codes(self, validator, code, status):
        msg = {
            "version": "v1.0.0",
            "event_type": "error.response",
            "timestamp": "2026-10-03T05:00:00Z",
            "payload": {
                "error_code": code,
                "http_status": status,
                "message": f"Test error for {code}",
                "details": {"code": code}
            }
        }
        assert validator.is_valid(msg)

    def test_rejects_invalid_error_code(self, validator):
        msg = {
            "version": "v1.0.0",
            "event_type": "error.response",
            "timestamp": "2026-10-03T05:00:00Z",
            "payload": {
                "error_code": "UNKNOWN_CODE",
                "http_status": 400,
                "message": "Bad error code",
            }
        }
        assert not validator.is_valid(msg)

    def test_rejects_invalid_http_status(self, validator):
        msg = {
            "version": "v1.0.0",
            "event_type": "error.response",
            "timestamp": "2026-10-03T05:00:00Z",
            "payload": {
                "error_code": "EMPTY_DIFF",
                "http_status": 200,  # 200 is not a valid error http_status
                "message": "Bad status code",
            }
        }
        assert not validator.is_valid(msg)


class TestStatusCodes200And202:
    """Verify both 200 OK and 202 Accepted flows are supported."""

    def test_analysis_queued_202_accepted(self, validator):
        msg = {
            "version": "v1.0.0",
            "event_type": "analysis.queued",
            "timestamp": "2026-10-03T00:30:00Z",
            "payload": {
                "analysis_id": "an-123",
                "status": "QUEUED",
                "http_status": 202,
                "retry_after_ms": 3000,
            }
        }
        assert validator.is_valid(msg)

    def test_analysis_queued_200_sync_ready(self, validator):
        msg = {
            "version": "v1.0.0",
            "event_type": "analysis.queued",
            "timestamp": "2026-10-03T00:30:00Z",
            "payload": {
                "analysis_id": "an-123",
                "status": "READY",
                "http_status": 200,
            }
        }
        assert validator.is_valid(msg)


class TestNegativeValidation:
    """Verify schema rejects invalid data."""

    def test_rejects_missing_version(self, validator):
        invalid = {
            "event_type": "analysis.request",
            "timestamp": "2026-10-03T00:00:00Z",
            "payload": {}
        }
        assert not validator.is_valid(invalid)

    def test_rejects_invalid_event_type(self, validator):
        invalid = {
            "version": "v1.0.0",
            "event_type": "invalid.type",
            "timestamp": "2026-10-03T00:00:00Z",
            "payload": {}
        }
        assert not validator.is_valid(invalid)

    def test_rejects_missing_payload(self, validator):
        invalid = {
            "version": "v1.0.0",
            "event_type": "analysis.request",
            "timestamp": "2026-10-03T00:00:00Z"
        }
        assert not validator.is_valid(invalid)

    def test_rejects_invalid_timestamp_format(self, validator):
        invalid = {
            "version": "v1.0.0",
            "event_type": "analysis.request",
            "timestamp": "not-a-date",
            "payload": {}
        }
        assert not validator.is_valid(invalid)
