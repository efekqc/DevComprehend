"""Semantic checks that the shared structural JSON schema cannot express."""

from ..concepts import concepts_from_questions, safe_path
from ..contracts import QUESTION_SCHEMA, validate_provider
from ..errors import LearningError


def validate_question(question: dict) -> None:
    validate_provider(question, QUESTION_SCHEMA)
    texts = [question["id"], question["concept"], question["prompt"], *question["rubric"]]
    if any(not text.strip() for text in texts) or len(set(question["rubric"])) != len(question["rubric"]):
        raise LearningError("INVALID_MODEL_OUTPUT", "Soru veya rubrik boş ya da yineleniyor.", True)
    for source in question["sources"]:
        if not safe_path(source["path"]) or source["start_line"] > source["end_line"]:
            raise LearningError("INVALID_MODEL_OUTPUT", "Kaynak aralığı geçersiz.", True)


def validate_questions(questions: list[dict], snapshot_id: str, evidence: dict) -> None:
    if not 3 <= len(questions) <= 5:
        raise LearningError("INVALID_MODEL_OUTPUT", "Çıktı 3–5 soru içermeli.", True)
    ids = set()
    prompts = set()
    for question in questions:
        validate_question(question)
        if question["id"] in ids or question["prompt"].strip() in prompts:
            raise LearningError("INVALID_MODEL_OUTPUT", "Sorular yineleniyor.", True)
        ids.add(question["id"])
        prompts.add(question["prompt"].strip())
        for source in question["sources"]:
            lines = evidence.get(source["path"], {})
            start, end = source["start_line"], source["end_line"]
            if (source["snapshot_id"] != snapshot_id or end - start >= len(lines)
                    or not all(number in lines for number in range(start, end + 1))):
                raise LearningError("INVALID_MODEL_OUTPUT", "Kaynak diff kanıtıyla eşleşmiyor.", True)
    concepts_from_questions(questions)
