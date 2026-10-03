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
            "answer.request", "evaluation.result"
        }
        assert data["event_type"] in valid_types


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
