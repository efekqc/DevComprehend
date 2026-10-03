import json
import unittest
from copy import deepcopy
from datetime import datetime, timezone

from learning import LearningEngine, LearningError
from learning.contracts import load_example
from learning.providers.fake import FakeProvider

from api import AnalysisService, QuotaPolicy
from api.errors import ApiError
from api.routes import dispatch

NOW = datetime(2026, 10, 3, 9, tzinfo=timezone.utc)


class CountingFakeProvider(FakeProvider):
    def __init__(self):
        super().__init__()
        self.calls = []

    def complete(self, request):
        self.calls.append(request)
        return super().complete(request)


def make_service(**kwargs):
    provider = CountingFakeProvider()
    engine = LearningEngine(provider, clock=lambda: NOW)
    service = AnalysisService(engine, **kwargs)
    return service, provider


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.request = load_example("analysis-request")
        self.service, self.provider = make_service()

    def test_analysis_happy_path_and_owner_get(self):
        result = self.service.create_analysis("user-a", self.request)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(len(result["questions"]), 3)
        fetched = self.service.get_analysis("user-a", result["id"])
        self.assertEqual(fetched, result)

    def test_duplicate_analysis_reuses_record_without_model_call(self):
        first = self.service.create_analysis("user-a", self.request)
        second = self.service.create_analysis("user-a", deepcopy(self.request))
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len([c for c in self.provider.calls if c.operation == "generate"]), 1)

    def test_same_snapshot_different_user_is_separate(self):
        first = self.service.create_analysis("user-a", self.request)
        second = self.service.create_analysis("user-b", deepcopy(self.request))
        self.assertNotEqual(first["id"], second["id"])

    def test_owner_isolation_hides_records(self):
        result = self.service.create_analysis("user-a", self.request)
        with self.assertRaises(ApiError) as raised:
            self.service.get_analysis("user-b", result["id"])
        self.assertEqual(raised.exception.status, 404)

    def test_invalid_request_rejected_before_engine(self):
        for body in (["not", "object"], {**self.request, "scope": "all"},
                     {**self.request, "surprise": 1}):
            with self.subTest(body=str(body)[:40]):
                with self.assertRaises(ApiError) as raised:
                    self.service.create_analysis("user-a", body)
                self.assertEqual(raised.exception.status, 400)
        self.assertFalse(self.provider.calls)

    def test_stale_snapshot_maps_to_conflict(self):
        request = {**self.request, "snapshot_id": "0" * 64}
        with self.assertRaises(ApiError) as raised:
            self.service.create_analysis("user-a", request)
        self.assertEqual((raised.exception.status, raised.exception.code), (409, "STALE_SNAPSHOT"))

    def test_answer_flow_and_submission_idempotency(self):
        analysis = self.service.create_analysis("user-a", self.request)
        question = analysis["questions"][0]
        answer = {"kind": "answer_request", "contract_version": "1",
                  "question_id": question["id"], "submission_id": "sub-1",
                  "answer": self.provider.cases[0]["answer"]}
        result = self.service.submit_answer("user-a", analysis["id"], answer)
        self.assertEqual(result["assessment_state"],
                         self.provider.cases[0]["expected_state"])
        again = self.service.submit_answer("user-a", analysis["id"], deepcopy(answer))
        self.assertEqual(again, result)
        self.assertEqual(len([c for c in self.provider.calls if c.operation == "evaluate"]), 1)
        conflict = {**answer, "answer": "tamamen farklı bir cevap"}
        with self.assertRaises(ApiError) as raised:
            self.service.submit_answer("user-a", analysis["id"], conflict)
        self.assertEqual((raised.exception.status, raised.exception.code),
                         (409, "SUBMISSION_CONFLICT"))

    def test_answer_requires_ownership_and_question_membership(self):
        analysis = self.service.create_analysis("user-a", self.request)
        answer = {"kind": "answer_request", "contract_version": "1",
                  "question_id": analysis["questions"][0]["id"],
                  "submission_id": "sub-1", "answer": "deneme"}
        with self.assertRaises(ApiError) as raised:
            self.service.submit_answer("user-b", analysis["id"], answer)
        self.assertEqual(raised.exception.status, 404)
        with self.assertRaises(ApiError) as raised:
            self.service.submit_answer("user-a", analysis["id"],
                                       {**answer, "question_id": "q-foreign"})
        self.assertEqual(raised.exception.status, 404)

    def test_uncertain_evaluation_does_not_create_review(self):
        analysis = self.service.create_analysis("user-a", self.request)
        answer = {"kind": "answer_request", "contract_version": "1",
                  "question_id": analysis["questions"][0]["id"],
                  "submission_id": "sub-x",
                  "answer": "Yetki kontrolü bambaşka bir ifade ile anlatıldı."}
        result = self.service.submit_answer("user-a", analysis["id"], answer)
        self.assertTrue(result["uncertain"])
        self.assertNotIn(("user-a", analysis["questions"][0]["id"]), self.service.store._reviews)

    def test_daily_quota_enforced_per_kind(self):
        service, _ = make_service(quota=QuotaPolicy(analyses_per_day=1, evaluations_per_day=1))
        analysis = service.create_analysis("user-a", self.request)
        other = deepcopy(self.request)
        other["repository_id"] = "workspace-other"
        with self.assertRaises(ApiError) as raised:
            service.create_analysis("user-a", other)
        self.assertEqual((raised.exception.status, raised.exception.code),
                         (429, "QUOTA_EXCEEDED"))
        answer = {"kind": "answer_request", "contract_version": "1",
                  "question_id": analysis["questions"][0]["id"],
                  "submission_id": "sub-1", "answer": "bir cevap"}
        service.submit_answer("user-a", analysis["id"], answer)
        with self.assertRaises(ApiError) as raised:
            service.submit_answer("user-a", analysis["id"], {**answer, "submission_id": "sub-2"})
        self.assertEqual(raised.exception.status, 429)

    def test_engine_provider_failure_returns_failed_analysis_safely(self):
        class BrokenEngine:
            def generate(self, request, *, analysis_id=None):
                raise LearningError("PROVIDER_ERROR", "Model sağlayıcısına ulaşılamadı.", True)

        service = AnalysisService(BrokenEngine())
        with self.assertRaises(ApiError) as raised:
            service.create_analysis("user-a", self.request)
        self.assertEqual(raised.exception.status, 500)
        self.assertEqual(raised.exception.code, "INTERNAL")
        self.assertNotIn("sağlayıcı", raised.exception.as_dict()["message"].lower())

    def test_http_boundary_auth_json_size_and_routes(self):
        headers = {"Authorization": "Bearer dev-token"}
        status, _ = dispatch(self.service, "GET", "/v1/analyses/x", {}, b"")
        self.assertEqual(status, 401)
        status, body = dispatch(self.service, "POST", "/v1/analyses", headers, b"not json")
        self.assertEqual((status, body["error"]["code"]), (400, "INVALID_INPUT"))
        status, body = dispatch(self.service, "POST", "/v1/analyses", headers,
                                b" " * 64_001)
        self.assertEqual((status, body["error"]["code"]), (413, "PAYLOAD_TOO_LARGE"))
        status, _ = dispatch(self.service, "GET", "/v1/unknown", headers, b"")
        self.assertEqual(status, 404)
        status, body = dispatch(self.service, "POST", "/v1/analyses", headers,
                                json.dumps(self.request).encode())
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ready")


if __name__ == "__main__":
    unittest.main()
