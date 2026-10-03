"""
DevComprehend — Wave 3: Full Pipeline E2E Flow Test

Simulates the complete DevComprehend lifecycle WITHOUT any real LLM or database:
  1. analysis.request  — User approves diff from IDE
  2. analysis.queued    — API acknowledges with HTTP 202
  3. analysis.ready     — AI engine generates comprehension questions
  4. answer.request     — User submits free-text answer
  5. evaluation.result  — LLM-as-judge evaluates with FSRS scheduling

All payloads are validated against contracts/v1/message.schema.json.
Uses FakeLLMProvider for deterministic, API-key-free operation.
"""

import json
import sys
import uuid
import pytest
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jsonschema import Draft202012Validator, FormatChecker
from tests.mock_adapters.fake_llm_provider import FakeLLMProvider

# ─── Schema Setup ─────────────────────────────────────────────────────────────
SCHEMA_PATH = PROJECT_ROOT / "contracts" / "v1" / "message.schema.json"


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def validator(schema):
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.fixture(scope="module")
def provider():
    return FakeLLMProvider()


def _make_message(event_type: str, payload: dict) -> dict:
    """Create a contract-conforming message envelope."""
    return {
        "version": "v1.0.0",
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payload": payload,
    }


def _validate(validator, message: dict, label: str):
    """Assert message conforms to schema, with descriptive error."""
    errors = list(validator.iter_errors(message))
    assert len(errors) == 0, (
        f"[{label}] Schema violations:\n"
        + "\n".join(f"  - {e.message}" for e in errors)
    )


class TestFullPipelineE2E:
    """End-to-end pipeline simulation with schema validation at every step."""

    DIFF_PAYLOAD = {
        "files": [
            {
                "path": "src/auth/login.ts",
                "change_type": "modified",
                "hunks": [
                    {
                        "start_line": 12,
                        "end_line": 25,
                        "content": (
                            "@@ -12,5 +12,10 @@\n"
                            "-  const token = getToken();\n"
                            "+  const token = await refreshToken();\n"
                            "+  if (!token) {\n"
                            "+    throw new AuthError('Token refresh failed');\n"
                            "+  }"
                        ),
                    }
                ],
            },
            {
                "path": "src/utils/retry.ts",
                "change_type": "added",
                "hunks": [
                    {
                        "start_line": 1,
                        "end_line": 30,
                        "content": "+ export function withRetry(fn, maxRetries = 3) { ... }",
                    }
                ],
            },
        ]
    }

    def test_step1_analysis_request(self, validator):
        """Step 1: User approves diff from IDE."""
        msg = _make_message("analysis.request", {
            "snapshot_id": "snap-e2e-001",
            "workspace_id": "ws-e2e-001",
            "user_id": "usr-e2e-001",
            "diff": self.DIFF_PAYLOAD,
            "consent": {
                "approved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "scope": "staged_changes_only",
            },
        })
        _validate(validator, msg, "analysis.request")
        assert msg["payload"]["snapshot_id"] == "snap-e2e-001"
        assert len(msg["payload"]["diff"]["files"]) == 2

    def test_step2_analysis_queued(self, validator):
        """Step 2: API responds with HTTP 202 acceptance."""
        msg = _make_message("analysis.queued", {
            "analysis_id": f"an-{uuid.uuid4().hex[:12]}",
            "snapshot_id": "snap-e2e-001",
            "status": "QUEUED",
            "estimated_seconds": 15,
            "retry_after_ms": 3000,
            "queue_position": 1,
        })
        _validate(validator, msg, "analysis.queued")
        assert msg["payload"]["status"] == "QUEUED"

    def test_step3_analysis_ready(self, validator, provider):
        """Step 3: AI engine produces comprehension questions."""
        analysis_result = provider.generate_analysis(self.DIFF_PAYLOAD)

        assert analysis_result["status"] == "READY"
        assert len(analysis_result["questions"]) == 2  # one per file

        # Wrap in message envelope and validate
        msg = _make_message("analysis.ready", analysis_result)
        _validate(validator, msg, "analysis.ready")

        # Verify question structure
        for q in analysis_result["questions"]:
            assert "question_id" in q
            assert "concept_name" in q
            assert "file_path" in q
            assert "question_text" in q
            assert "rubric" in q
            assert q["line_start"] > 0
            assert q["line_end"] >= q["line_start"]

    def test_step4_answer_request(self, validator, provider):
        """Step 4: User submits free-text answer."""
        analysis_result = provider.generate_analysis(self.DIFF_PAYLOAD)
        question = analysis_result["questions"][0]

        msg = _make_message("answer.request", {
            "question_id": question["question_id"],
            "analysis_id": analysis_result["analysis_id"],
            "user_id": "usr-e2e-001",
            "answer_text": (
                "If refreshToken is called from a non-async context without await, "
                "it returns a Promise that rejects, causing an unhandled rejection. "
                "I would wrap it in a try-catch or attach .catch() handler."
            ),
            "time_spent_seconds": 85,
        })
        _validate(validator, msg, "answer.request")
        assert msg["payload"]["question_id"] == question["question_id"]

    def test_step5_evaluation_result(self, validator, provider):
        """Step 5: LLM-as-judge evaluates answer with FSRS scheduling."""
        analysis_result = provider.generate_analysis(self.DIFF_PAYLOAD)
        question = analysis_result["questions"][0]

        user_answer = (
            "If refreshToken is called from a non-async context without await, "
            "the returned Promise rejects silently. This causes an unhandled "
            "promise rejection which can crash Node.js or go unnoticed in browsers. "
            "To handle this, wrap the call in an async IIFE with try-catch, or "
            "attach a .catch() handler. Additionally, register a global "
            "unhandledrejection event listener as a safety net."
        )

        evaluation = provider.evaluate_answer(
            question_text=question["question_text"],
            rubric=question["rubric"],
            user_answer=user_answer,
            concept_name=question["concept_name"],
        )

        msg = _make_message("evaluation.result", evaluation)
        _validate(validator, msg, "evaluation.result")

        # Verify evaluation structure
        assert "score" in evaluation
        assert "passed" in evaluation
        assert "feedback" in evaluation
        assert "rubric_breakdown" in evaluation
        assert "fsrs" in evaluation
        assert isinstance(evaluation["score"], (int, float))
        assert 0 <= evaluation["score"] <= 100

        # Verify FSRS parameters
        fsrs = evaluation["fsrs"]
        assert fsrs["concept_name"] == question["concept_name"]
        assert fsrs["difficulty"] >= 1.0
        assert fsrs["difficulty"] <= 10.0
        assert fsrs["stability"] >= 0.0
        assert fsrs["state"] in ("New", "Learning", "Review", "Relearning")
        assert fsrs["rating"] in (1, 2, 3, 4)
        assert "next_review_at" in fsrs

    def test_full_pipeline_sequence(self, validator, provider):
        """Run all 5 steps sequentially, verifying data flows correctly."""
        # Step 1: Request
        request_msg = _make_message("analysis.request", {
            "snapshot_id": "snap-seq-001",
            "workspace_id": "ws-seq-001",
            "user_id": "usr-seq-001",
            "diff": self.DIFF_PAYLOAD,
            "consent": {
                "approved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "scope": "staged_changes_only",
            },
        })
        _validate(validator, request_msg, "seq-step1")

        # Step 2: Queued
        queued_msg = _make_message("analysis.queued", {
            "analysis_id": "an-seq-001",
            "snapshot_id": "snap-seq-001",
            "status": "QUEUED",
            "estimated_seconds": 10,
            "retry_after_ms": 2000,
        })
        _validate(validator, queued_msg, "seq-step2")

        # Step 3: Ready
        analysis = provider.generate_analysis(self.DIFF_PAYLOAD)
        ready_msg = _make_message("analysis.ready", analysis)
        _validate(validator, ready_msg, "seq-step3")
        assert len(analysis["questions"]) >= 1

        # Step 4: Answer
        question = analysis["questions"][0]
        answer_text = "The async function returns a Promise. Without await, errors are unhandled."
        answer_msg = _make_message("answer.request", {
            "question_id": question["question_id"],
            "analysis_id": analysis["analysis_id"],
            "user_id": "usr-seq-001",
            "answer_text": answer_text,
            "time_spent_seconds": 45,
        })
        _validate(validator, answer_msg, "seq-step4")

        # Step 5: Evaluation
        evaluation = provider.evaluate_answer(
            question["question_text"],
            question["rubric"],
            answer_text,
            question["concept_name"],
        )
        eval_msg = _make_message("evaluation.result", evaluation)
        _validate(validator, eval_msg, "seq-step5")

        # Verify chain integrity
        assert analysis["analysis_id"] == ready_msg["payload"]["analysis_id"]
        assert question["question_id"] == answer_msg["payload"]["question_id"]

    def test_determinism_across_runs(self, provider):
        """Same input produces identical output every time."""
        r1 = provider.generate_analysis(self.DIFF_PAYLOAD)
        r2 = provider.generate_analysis(self.DIFF_PAYLOAD)
        assert r1["analysis_id"] == r2["analysis_id"]
        assert r1["questions"][0]["question_id"] == r2["questions"][0]["question_id"]
        assert r1["questions"][0]["concept_name"] == r2["questions"][0]["concept_name"]

    def test_provider_call_log(self, provider):
        """FakeLLMProvider logs all calls for auditing."""
        provider.reset()
        provider.generate_analysis(self.DIFF_PAYLOAD)
        provider.evaluate_answer("q?", {}, "answer", "concept")
        log = provider.get_call_log()
        assert len(log) == 2
        assert log[0]["method"] == "generate_analysis"
        assert log[1]["method"] == "evaluate_answer"
