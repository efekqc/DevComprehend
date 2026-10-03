"""Run the synthetic answer matrix. Live mode is explicit and uses backend env only."""

import argparse
import json
import os

from . import LearningEngine
from .contracts import load_example
from .providers.fake import FakeProvider
from .providers.openai import OpenAIProvider


def run(engine: LearningEngine, cases: list[dict]) -> dict:
    questions = {question["id"]: question for question in load_example("analysis-ready")["questions"]}
    rows = []
    for case in cases:
        answer = {"kind": "answer_request", "contract_version": "1", "question_id": case["question_id"],
                  "submission_id": f"quality-{case['id']}", "answer": case["answer"]}
        result = engine.evaluate(questions[case["question_id"]], answer)
        statuses = [item["result"] for item in result["rubric_results"]]
        match = (result["assessment_state"] == case["expected_state"]
                 and result["uncertain"] == case["uncertain"] and statuses == case["results"])
        rows.append({"case": case["id"], "matches_expected": match,
                     "state": result["assessment_state"], "uncertain": result["uncertain"],
                     "rubric_results": statuses})
    return {"total": len(rows), "matching": sum(row["matches_expected"] for row in rows), "cases": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("fake", "openai"), default="fake")
    args = parser.parse_args()
    fake = FakeProvider()
    provider = fake
    if args.provider == "openai":
        key, model = os.environ.get("LLM_API_KEY", ""), os.environ.get("LLM_MODEL", "")
        if not key or not model:
            parser.error("Live mode requires backend LLM_API_KEY and LLM_MODEL environment variables.")
        provider = OpenAIProvider(api_key=key, model=model)
    usage = []
    report = run(LearningEngine(provider, on_usage=usage.append), fake.cases)
    report.update(provider=provider.identity, usage=usage,
                  limitation="Synthetic label agreement only; feedback quality and live generation require human review.")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["matching"] == report["total"] else 1)


if __name__ == "__main__":
    main()
