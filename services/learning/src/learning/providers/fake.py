"""Exact synthetic fixture replay. This is deliberately NOT a text grader."""

import json

from ..contracts import MODULE_ROOT, load_example
from ..errors import LearningError
from . import ProviderRequest, ProviderResponse


class FakeProvider:
    identity = "fake/fixture-v2"

    def __init__(self):
        self.cases = json.loads((MODULE_ROOT / "tests/fixtures/answers.json").read_text(encoding="utf-8"))

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        if request.operation == "generate":
            supplied = request.data["analysis_request"]
            fixture = load_example("analysis-request")
            if supplied["diff"] != fixture["diff"] or supplied["context"] != fixture["context"]:
                raise LearningError("FAKE_FIXTURE_ONLY", "Fake sağlayıcı yalnız sentetik demo girdisini destekler.")
            value = {"questions": load_example("analysis-ready")["questions"]}
            for question, kind in zip(value["questions"], ("architecture", "edge_case", "implementation")):
                question["question_type"] = kind
        elif request.operation == "evaluate":
            question = request.data["question"]
            originals = {q["id"]: q for q in load_example("analysis-ready")["questions"]}
            case = next((c for c in self.cases if c["question_id"] == question["id"]
                         and c["answer"] == request.data["answer"]
                         and originals.get(question["id"]) == question), None)
            if case is None:
                value = {"rubric_results": [], "uncertain": True,
                         "feedback": "Bu cevap fake kalite setinde yok; gerçek model değerlendirmesi yapılmadı."}
            else:
                value = {"rubric_results": [
                    {"criterion": criterion, "result": status}
                    for criterion, status in zip(question["rubric"], case["results"])
                ], "uncertain": case["uncertain"], "feedback": case["feedback"]}
        else:
            raise LearningError("INVALID_INPUT", "Bilinmeyen model işlemi.")
        text = json.dumps(value, ensure_ascii=False)
        # Synthetic estimates, never actual billed tokens.
        return ProviderResponse(text, self.identity, 0, 0)
