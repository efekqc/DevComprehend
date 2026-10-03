"""Preserve rubric coverage; uncertain results never imply a low score."""

from ..errors import LearningError


def validate_rubric(question: dict, result: dict) -> None:
    expected = question["rubric"]
    received = [item["criterion"] for item in result["rubric_results"]]
    if not result["feedback"].strip():
        raise LearningError("INVALID_MODEL_OUTPUT", "Geri bildirim boş olamaz.", True)
    if result["uncertain"] and not received:
        return
    if len(received) != len(expected) or set(received) != set(expected):
        raise LearningError("INVALID_MODEL_OUTPUT", "Rubrik maddeleri eksik veya değiştirilmiş.", True)
    by_criterion = {item["criterion"]: item for item in result["rubric_results"]}
    result["rubric_results"] = [by_criterion[criterion] for criterion in expected]


def unassessed(question_id: str, feedback: str, uncertain: bool = True) -> dict:
    return {
        "kind": "evaluation_result", "contract_version": "1", "question_id": question_id,
        "assessment_state": "unassessed", "rubric_results": [], "feedback": feedback,
        "uncertain": uncertain, "due_at": None,
    }
