"""In-memory storage adapter for development; Efe's DB layer replaces this.

Holds analyses, question ownership, submission idempotency, review schedule and
daily usage counters. No cross-process durability; restart clears everything.
"""

from datetime import datetime, timezone
import itertools
import threading


class InMemoryStore:
    def __init__(self):
        # RLock: quota reservation holds the lock across usage read+increment.
        self._lock = threading.RLock()
        self._seq = itertools.count(1)
        self._analyses = {}        # analysis_id -> {"owner", "result"}
        self._dedupe = {}          # (owner, repository_id, snapshot_id, pipeline) -> analysis_id
        self._questions = {}       # question_id -> analysis_id
        self._submissions = {}     # (owner, question_id, submission_id) -> {"answer", "result"}
        self._reviews = {}         # (owner, question_id) -> {"assessment_state", "due_at"}
        self._usage = {}           # (owner, day, kind) -> count

    def new_analysis_id(self) -> str:
        return f"analysis-{next(self._seq)}"

    def find_analysis(self, dedupe_key: tuple) -> dict | None:
        with self._lock:
            analysis_id = self._dedupe.get(dedupe_key)
            record = self._analyses.get(analysis_id) if analysis_id else None
            return record["result"] if record else None

    def save_analysis(self, dedupe_key: tuple, analysis_id: str, owner: str, result: dict) -> None:
        with self._lock:
            self._dedupe[dedupe_key] = analysis_id
            self._analyses[analysis_id] = {"owner": owner, "result": result}
            for question in result.get("questions", []):
                self._questions[question["id"]] = analysis_id

    def get_analysis(self, analysis_id: str) -> dict | None:
        with self._lock:
            return self._analyses.get(analysis_id)

    def analysis_for_question(self, question_id: str) -> dict | None:
        with self._lock:
            analysis_id = self._questions.get(question_id)
            return self._analyses.get(analysis_id) if analysis_id else None

    def find_submission(self, owner: str, question_id: str, submission_id: str) -> dict | None:
        with self._lock:
            return self._submissions.get((owner, question_id, submission_id))

    def save_submission(self, owner: str, question_id: str, submission_id: str,
                        answer: str, result: dict) -> None:
        with self._lock:
            self._submissions[(owner, question_id, submission_id)] = {"answer": answer, "result": result}

    def save_review(self, owner: str, question_id: str, result: dict) -> None:
        with self._lock:
            self._reviews[(owner, question_id)] = {
                "assessment_state": result["assessment_state"], "due_at": result["due_at"],
            }

    def usage(self, owner: str, kind: str, day: str | None = None) -> int:
        day = day or datetime.now(timezone.utc).date().isoformat()
        with self._lock:
            return self._usage.get((owner, day, kind), 0)

    def increment_usage(self, owner: str, kind: str, day: str | None = None) -> int:
        day = day or datetime.now(timezone.utc).date().isoformat()
        with self._lock:
            key = (owner, day, kind)
            self._usage[key] = self._usage.get(key, 0) + 1
            return self._usage[key]
