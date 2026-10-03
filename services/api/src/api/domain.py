"""Route-independent API behavior: analyses, answers, idempotency, ownership."""

from learning import LearningError
from learning.contracts import validate

from .errors import ApiError, from_learning_error
from .quota import QuotaPolicy
from .store import InMemoryStore


class AnalysisService:
    def __init__(self, engine, *, store: InMemoryStore | None = None,
                 quota: QuotaPolicy | None = None):
        self.engine = engine
        self.store = store or InMemoryStore()
        self.quota = quota or QuotaPolicy()

    def create_analysis(self, user_id: str, body) -> dict:
        if not isinstance(body, dict):
            raise ApiError(400, "INVALID_INPUT", "JSON gövdesi nesne olmalı.")
        try:
            validate(body, "analysis_request")
        except LearningError as error:
            raise from_learning_error(error) from None
        dedupe_key = (user_id, body["repository_id"], body["snapshot_id"], body["pipeline_version"])
        existing = self.store.find_analysis(dedupe_key)
        if existing is not None:
            # Same user + repository + snapshot + pipeline: no new model call.
            return existing
        self.quota.reserve(self.store, user_id, "analysis")
        analysis_id = self.store.new_analysis_id()
        try:
            result = self.engine.generate(body, analysis_id=analysis_id)
        except LearningError as error:
            raise from_learning_error(error) from None
        self.store.save_analysis(dedupe_key, analysis_id, user_id, result)
        return result

    def get_analysis(self, user_id: str, analysis_id: str) -> dict:
        record = self.store.get_analysis(analysis_id)
        if record is None or record["owner"] != user_id:
            # 404 for both cases: do not reveal whether another user's record exists.
            raise ApiError(404, "NOT_FOUND", "Analiz bulunamadı.")
        return record["result"]

    def submit_answer(self, user_id: str, analysis_id: str, body) -> dict:
        if not isinstance(body, dict):
            raise ApiError(400, "INVALID_INPUT", "JSON gövdesi nesne olmalı.")
        try:
            validate(body, "answer_request")
        except LearningError as error:
            raise from_learning_error(error) from None
        record = self.store.get_analysis(analysis_id)
        if record is None or record["owner"] != user_id:
            raise ApiError(404, "NOT_FOUND", "Analiz bulunamadı.")
        questions = {q["id"]: q for q in record["result"].get("questions", [])}
        question = questions.get(body["question_id"])
        if question is None:
            raise ApiError(404, "NOT_FOUND", "Soru bu analize ait değil.")
        prior = self.store.find_submission(user_id, question["id"], body["submission_id"])
        if prior is not None:
            if prior["answer"] != body["answer"]:
                raise ApiError(409, "SUBMISSION_CONFLICT",
                               "Bu gönderim kimliği farklı bir cevapla kullanıldı.")
            return prior["result"]
        self.quota.reserve(self.store, user_id, "evaluation")
        try:
            result = self.engine.evaluate(question, body)
        except LearningError as error:
            raise from_learning_error(error) from None
        self.store.save_submission(user_id, question["id"], body["submission_id"],
                                   body["answer"], result)
        if result.get("due_at") and not result.get("uncertain"):
            # Uncertain attempts never overwrite a reliable review record.
            self.store.save_review(user_id, question["id"], result)
        return result
