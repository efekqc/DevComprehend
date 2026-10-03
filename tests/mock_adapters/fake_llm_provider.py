"""
DevComprehend — Fake LLM Provider (Deterministic Mock)

A drop-in replacement for the real LLM provider that returns
deterministic responses based on input content hashes.
Used in CI and local development to avoid real API calls.

Architecture:
  - No API keys required
  - Responses are computed from SHA-256 hash of diff content
  - 100% deterministic: same input → same output
  - Supports both analysis generation and answer evaluation
"""

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any


class FakeLLMProvider:
    """Deterministic fake LLM provider for testing and CI."""

    # ─── Concept Bank ─────────────────────────────────────────────────────
    CONCEPT_BANK = [
        "error-handling", "async-patterns", "type-safety",
        "dependency-injection", "state-management", "security-patterns",
        "api-design", "testing-strategy", "performance-optimization",
        "code-organization"
    ]

    # ─── Question Templates ───────────────────────────────────────────────
    QUESTION_TEMPLATES = {
        "situational": (
            "In your changes to `{file_path}` (lines {line_start}-{line_end}), "
            "you modified the {concept} logic. What would happen if this code "
            "encounters an unexpected input type at runtime?"
        ),
        "open-ended": (
            "Looking at your changes in `{file_path}` (lines {line_start}-{line_end}), "
            "explain the design trade-offs of your approach to {concept}. "
            "What alternative patterns did you consider?"
        ),
    }

    # ─── Rubric Template ──────────────────────────────────────────────────
    DEFAULT_RUBRIC = {
        "max_score": 100,
        "criteria": [
            {"name": "understanding", "weight": 30, "description": "Demonstrates understanding of the concept"},
            {"name": "analysis", "weight": 40, "description": "Provides thorough analysis of implications"},
            {"name": "alternatives", "weight": 30, "description": "Considers alternative approaches"},
        ]
    }

    # ─── Secret Detection Patterns ────────────────────────────────────────
    SECRET_PATTERNS = [
        re.compile(r'(?i)(api[_-]?key|access[_-]?key|apikey|anthropic[_-]?key)\s*[=:]\s*["\']?[\w\-]{16,}'),
        re.compile(r'(?i)(secret[_-]?key|secret|password|passwd|pwd)\s*[=:]\s*["\']?[\S]{8,}'),
        re.compile(r'(?i)(bearer\s+|token\s*[=:]\s*)["\']?[\w\-\.]{16,}'),
        re.compile(r'(?i)(sk-|pk-|ak-|akia|asia)[a-zA-Z0-9_\-]{16,}'),
        re.compile(r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----'),
    ]

    def __init__(self, latency_ms: int = 0):
        """Initialize the fake provider.
        
        Args:
            latency_ms: Simulated latency in milliseconds (0 for instant).
        """
        self.latency_ms = latency_ms
        self.call_log: list[dict] = []

    def _hash_content(self, content: str) -> str:
        """Generate deterministic SHA-256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _select_concept(self, file_path: str, hash_val: str) -> str:
        """Deterministically select a concept based on file path and hash."""
        index = int(hash_val[:8], 16) % len(self.CONCEPT_BANK)
        return self.CONCEPT_BANK[index]

    def mask_secrets(self, text: str) -> str:
        """Replace detected secrets with [REDACTED_SECRET]."""
        masked = text
        for pattern in self.SECRET_PATTERNS:
            masked = pattern.sub("[REDACTED_SECRET]", masked)
        return masked

    def generate_analysis(self, diff_payload: dict) -> dict:
        """Generate deterministic analysis questions from a diff payload.
        
        Args:
            diff_payload: The diff data from the analysis request.
            
        Returns:
            A dict matching the analysis-ready payload format.
        """
        files = diff_payload.get("files", [])
        diff_content = json.dumps(diff_payload, sort_keys=True)
        content_hash = self._hash_content(diff_content)

        questions = []
        for i, file_info in enumerate(files):
            file_path = file_info.get("path", "unknown")
            hunks = file_info.get("hunks", [])
            first_hunk = hunks[0] if hunks else {"start_line": 1, "end_line": 10, "content": ""}

            # Mask any secrets in hunk content
            masked_content = self.mask_secrets(first_hunk.get("content", ""))

            concept = self._select_concept(file_path, content_hash)
            q_type = "situational" if i % 2 == 0 else "open-ended"
            
            question = {
                "question_id": f"q-fake-{content_hash[:8]}-{i:03d}",
                "concept_name": concept,
                "file_path": file_path,
                "line_start": first_hunk.get("start_line", 1),
                "line_end": first_hunk.get("end_line", 10),
                "question_type": q_type,
                "question_text": self.QUESTION_TEMPLATES[q_type].format(
                    file_path=file_path,
                    line_start=first_hunk.get("start_line", 1),
                    line_end=first_hunk.get("end_line", 10),
                    concept=concept,
                ),
                "rubric": self.DEFAULT_RUBRIC,
            }
            questions.append(question)

        result = {
            "analysis_id": f"an-fake-{content_hash[:12]}",
            "status": "READY",
            "model_version": "fake-deterministic-v1",
            "prompt_version": "v1.0.0-fake",
            "questions": questions,
        }

        self.call_log.append({
            "method": "generate_analysis",
            "input_hash": content_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question_count": len(questions),
        })

        return result

    def evaluate_answer(
        self,
        question_text: str,
        rubric: dict,
        user_answer: str,
        concept_name: str = "unknown",
    ) -> dict:
        """Deterministically evaluate a user's answer.
        
        Scoring logic:
          - Base score derived from answer length and keyword overlap
          - Deterministic: same answer text → same score
          
        Args:
            question_text: The original question.
            rubric: The rubric specification.
            user_answer: The user's free-text answer.
            concept_name: The concept being tested.
            
        Returns:
            A dict matching the evaluation-result payload format.
        """
        answer_hash = self._hash_content(user_answer)
        
        # Deterministic scoring based on answer properties
        word_count = len(user_answer.split())
        hash_seed = int(answer_hash[:8], 16)
        
        # Base score: 30-95 range based on word count and hash
        base_score = min(95, max(30, (word_count * 2) + (hash_seed % 30)))
        
        # Criteria scoring
        criteria = rubric.get("criteria", self.DEFAULT_RUBRIC["criteria"])
        criteria_scores = []
        remaining = base_score
        
        for i, criterion in enumerate(criteria):
            max_points = criterion.get("weight", 30)
            # Distribute score proportionally with deterministic variation
            ratio = base_score / 100
            awarded = round(max_points * ratio * (0.8 + (hash_seed >> (i * 4) & 0xF) / 80), 2)
            awarded = min(awarded, max_points)
            criteria_scores.append({
                "name": criterion["name"],
                "awarded": awarded,
                "max": max_points,
            })
        
        total_score = round(sum(c["awarded"] for c in criteria_scores), 2)
        total_score = min(100, total_score)
        passed = total_score >= 60
        
        # Deterministic feedback
        correct_points = ["Demonstrated basic understanding of the concept"]
        missing_points = []
        incorrect_points = []
        
        if word_count > 20:
            correct_points.append("Provided a detailed response")
        if word_count < 10:
            missing_points.append("Response was too brief")
        if total_score < 60:
            missing_points.append("Key aspects of the concept were not addressed")
        if total_score > 80:
            correct_points.append("Showed strong analytical thinking")

        # FSRS parameters (deterministic based on score)
        difficulty = round(5.0 + (100 - total_score) / 20, 1)
        difficulty = min(10.0, max(1.0, difficulty))
        stability = round(total_score / 20, 1) if passed else 0.5
        retrievability = round(min(0.99, total_score / 105), 2)
        
        if total_score >= 80:
            rating = 4  # Easy
            state = "Review"
            next_days = 7
        elif total_score >= 60:
            rating = 3  # Good
            state = "Review"
            next_days = 3
        elif total_score >= 40:
            rating = 2  # Hard
            state = "Learning"
            next_days = 1
        else:
            rating = 1  # Again
            state = "Relearning"
            next_days = 0  # Same day

        now = datetime.now(timezone.utc)
        
        result = {
            "evaluation_id": f"ev-fake-{answer_hash[:8]}",
            "score": total_score,
            "passed": passed,
            "feedback": f"{'Good' if passed else 'Needs improvement'}: Your response {'demonstrates' if passed else 'partially addresses'} the key concepts.",
            "rubric_breakdown": {
                "correct": correct_points,
                "missing": missing_points,
                "incorrect": incorrect_points,
            },
            "criteria_scores": criteria_scores,
            "fsrs": {
                "concept_name": concept_name,
                "difficulty": difficulty,
                "stability": stability,
                "retrievability": retrievability,
                "state": state,
                "rating": rating,
                "next_review_at": (now + timedelta(days=next_days)).isoformat(),
            },
        }

        self.call_log.append({
            "method": "evaluate_answer",
            "input_hash": answer_hash,
            "timestamp": now.isoformat(),
            "score": total_score,
            "passed": passed,
        })

        return result

    def get_call_log(self) -> list[dict]:
        """Return the log of all calls made to this provider."""
        return self.call_log.copy()

    def reset(self) -> None:
        """Reset the call log."""
        self.call_log.clear()
