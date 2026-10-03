"""Offline demonstration: shared request → ready → seven synthetic evaluations."""

import json

from . import LearningEngine
from .contracts import load_example
from .providers.fake import FakeProvider


def main():
    provider = FakeProvider()
    engine = LearningEngine(provider)
    analysis = engine.generate(load_example("analysis-request"), analysis_id="analysis-demo")
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    if analysis["status"] != "ready":
        raise SystemExit(1)
    questions = {question["id"]: question for question in analysis["questions"]}
    for case in provider.cases:
        answer = {"kind": "answer_request", "contract_version": "1", "question_id": case["question_id"],
                  "submission_id": f"demo-{case['id']}", "answer": case["answer"]}
        print(json.dumps(engine.evaluate(questions[case["question_id"]], answer), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
