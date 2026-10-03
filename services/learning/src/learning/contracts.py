"""Consume the shared v1 schema, without forking or changing its wire format."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .errors import LearningError

ROOT = Path(__file__).resolve().parents[4]
MODULE_ROOT = ROOT / "services/learning"
SCHEMA = json.loads((ROOT / "contracts/v1/message.schema.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)


def validate(value: dict, kind: str) -> None:
    schema = {"$ref": f"#/$defs/{kind}", "$defs": SCHEMA["$defs"]}
    if not Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(value):
        raise LearningError("INVALID_INPUT", "Mesaj ortak v1 sözleşmesine uymuyor.")


QUESTION_SCHEMA = SCHEMA["$defs"]["analysis_result"]["properties"]["questions"]["items"]
GENERATION_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["questions"],
    "properties": {"questions": {
        "type": "array", "minItems": 3, "maxItems": 5, "items": QUESTION_SCHEMA,
    }},
}
EVALUATION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["rubric_results", "feedback", "uncertain"],
    "properties": {
        key: SCHEMA["$defs"]["evaluation_result"]["properties"][key]
        for key in ("rubric_results", "feedback", "uncertain")
    },
}


def validate_provider(value: dict, schema: dict) -> None:
    if not Draft202012Validator(schema).is_valid(value):
        raise LearningError("INVALID_MODEL_OUTPUT", "Model çıktısı doğrulanamadı.", True)


def load_example(name: str) -> dict:
    return json.loads((ROOT / f"contracts/v1/examples/{name}.json").read_text(encoding="utf-8"))
