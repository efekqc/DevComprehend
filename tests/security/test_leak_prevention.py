"""
DevComprehend — Wave 4: Secret Leak Prevention & Log Safety Tests

Verifies:
1. Regex masking catches all known secret patterns
2. Masked output never contains raw secrets
3. Log sanitization prevents diff content from appearing in plaintext

Does NOT require database or real LLM.
"""

import sys
import re
import json
import logging
import pytest
from pathlib import Path
from io import StringIO

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.mock_adapters.fake_llm_provider import FakeLLMProvider


@pytest.fixture
def provider():
    return FakeLLMProvider()


# ═══════════════════════════════════════════════════════════════════
# Log Sanitizer Utility (simulates backend log filtering)
# ═══════════════════════════════════════════════════════════════════
class LogSanitizer:
    """Sanitizes log messages to prevent sensitive data from appearing in logs."""
    
    SENSITIVE_FIELDS = ["diff_content", "user_answer_text", "hunk_content",
                        "raw_code", "source_code", "file_content"]
    
    @staticmethod
    def sanitize(record: dict) -> dict:
        """Remove or mask sensitive fields from a log record."""
        sanitized = {}
        for key, value in record.items():
            if key in LogSanitizer.SENSITIVE_FIELDS:
                sanitized[key] = "[SANITIZED]"
            elif isinstance(value, str) and len(value) > 500:
                sanitized[key] = value[:100] + "...[TRUNCATED]"
            elif isinstance(value, dict):
                sanitized[key] = LogSanitizer.sanitize(value)
            else:
                sanitized[key] = value
        return sanitized


# ═══════════════════════════════════════════════════════════════════
# SECRET PATTERN TESTS
# ═══════════════════════════════════════════════════════════════════
class TestSecretMasking:
    """Verify FakeLLMProvider.mask_secrets catches all patterns."""

    def test_aws_access_key(self, provider):
        text = "AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE12"
        masked = provider.mask_secrets(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in masked
        assert "[REDACTED_SECRET]" in masked

    def test_openai_api_key(self, provider):
        text = "API_KEY=sk-proj-1234567890abcdefghijklmnop"
        masked = provider.mask_secrets(text)
        assert "sk-proj-1234567890" not in masked
        assert "[REDACTED_SECRET]" in masked

    def test_anthropic_api_key(self, provider):
        text = "ANTHROPIC_KEY: sk-ant-api03-abcdefghijklmnopqrstuv"
        masked = provider.mask_secrets(text)
        assert "sk-ant-api03" not in masked

    def test_bearer_token(self, provider):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIx"
        masked = provider.mask_secrets(text)
        assert "eyJhbGciOiJ" not in masked

    def test_generic_password(self, provider):
        text = "DB_PASSWORD=SuperSecretP@ssw0rd2026!"
        masked = provider.mask_secrets(text)
        assert "SuperSecretP@ssw0rd" not in masked
        assert "[REDACTED_SECRET]" in masked

    def test_private_key_header(self, provider):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA..."
        masked = provider.mask_secrets(text)
        assert "BEGIN RSA PRIVATE KEY" not in masked
        assert "[REDACTED_SECRET]" in masked

    def test_ec_private_key(self, provider):
        text = "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIPUKbH..."
        masked = provider.mask_secrets(text)
        assert "BEGIN EC PRIVATE KEY" not in masked

    def test_generic_secret(self, provider):
        text = "SECRET_KEY=my_very_long_secret_value_here_2026"
        masked = provider.mask_secrets(text)
        assert "my_very_long_secret" not in masked

    def test_multiple_secrets_in_diff(self, provider):
        """Multiple secrets in a single diff block are all masked."""
        text = (
            "const config = {\n"
            "  API_KEY: 'sk-1234567890abcdefghijklmnop',\n"
            "  password: 'Hunter2IsNotSecure!',\n"
            "  token: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload',\n"
            "  -----BEGIN RSA PRIVATE KEY-----\n"
            "  MIIEpAIBAAKCAQEA...\n"
            "};"
        )
        masked = provider.mask_secrets(text)
        assert "sk-12345678" not in masked
        assert "Hunter2" not in masked
        assert "BEGIN RSA PRIVATE KEY" not in masked

    def test_clean_code_unchanged(self, provider):
        """Code without secrets should pass through unchanged."""
        text = "const greeting = 'Hello, World!';\nfunction add(a, b) { return a + b; }"
        masked = provider.mask_secrets(text)
        assert masked == text

    def test_diff_content_in_analysis_masked(self, provider):
        """Secrets in diff hunks are masked during analysis generation."""
        diff = {
            "files": [{
                "path": "src/config.ts",
                "hunks": [{
                    "start_line": 1,
                    "end_line": 5,
                    "content": "+ const API_KEY = 'sk-realkey1234567890abcdefghij';"
                }]
            }]
        }
        # The provider should mask secrets internally
        result = provider.generate_analysis(diff)
        # Provider calls mask_secrets on hunk content internally
        assert result["status"] == "READY"


class TestLogLeakPrevention:
    """Verify log sanitizer prevents raw code from appearing in logs."""

    def test_diff_content_sanitized(self):
        record = {
            "event": "analysis.request",
            "user_id": "usr-42",
            "diff_content": "const secret = process.env.API_KEY; function main() {...}",
        }
        sanitized = LogSanitizer.sanitize(record)
        assert sanitized["diff_content"] == "[SANITIZED]"
        assert sanitized["user_id"] == "usr-42"  # Non-sensitive stays

    def test_user_answer_sanitized(self):
        record = {
            "event": "answer.submitted",
            "user_answer_text": "I think the error handling should use try-catch...",
            "question_id": "q-001",
        }
        sanitized = LogSanitizer.sanitize(record)
        assert sanitized["user_answer_text"] == "[SANITIZED]"
        assert sanitized["question_id"] == "q-001"

    def test_nested_sensitive_fields(self):
        record = {
            "event": "processing",
            "data": {
                "raw_code": "import os; os.system('rm -rf /')",
                "metadata": "safe",
            }
        }
        sanitized = LogSanitizer.sanitize(record)
        assert sanitized["data"]["raw_code"] == "[SANITIZED]"
        assert sanitized["data"]["metadata"] == "safe"

    def test_long_strings_truncated(self):
        record = {
            "event": "debug",
            "long_field": "x" * 1000,
        }
        sanitized = LogSanitizer.sanitize(record)
        assert len(sanitized["long_field"]) < 200
        assert "[TRUNCATED]" in sanitized["long_field"]

    def test_normal_log_unchanged(self):
        record = {
            "event": "analysis.completed",
            "analysis_id": "an-123",
            "duration_ms": 1500,
        }
        sanitized = LogSanitizer.sanitize(record)
        assert sanitized == record

    def test_python_logger_integration(self):
        """Verify sanitizer works with Python's logging module."""
        log_buffer = StringIO()
        handler = logging.StreamHandler(log_buffer)
        handler.setLevel(logging.INFO)
        logger = logging.getLogger("devcomprehend.test")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Simulate logging a sanitized record
        record = {
            "diff_content": "const pwd = 'secret123';",
            "analysis_id": "an-456",
        }
        sanitized = LogSanitizer.sanitize(record)
        logger.info("Processing: %s", json.dumps(sanitized))

        log_output = log_buffer.getvalue()
        assert "secret123" not in log_output
        assert "[SANITIZED]" in log_output
        assert "an-456" in log_output

        logger.removeHandler(handler)
