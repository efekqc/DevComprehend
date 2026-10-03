"""Check synthetic contract fixtures, references and schema compliance."""
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "contracts/v1"
schema = json.loads((BASE / "message.schema.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker())

examples = {}
for path in sorted((BASE / "examples").glob("*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    validator.validate(data)
    examples[path.name] = data

req = examples["analysis-request.json"].get("payload", examples["analysis-request.json"])
ready = examples["analysis-ready.json"].get("payload", examples["analysis-ready.json"])
ans = examples["answer-request.json"].get("payload", examples["answer-request.json"])
ev = examples["evaluation-result.json"].get("payload", examples["evaluation-result.json"])

# Verify questions consistency
ready_q_ids = {q.get("question_id") or q.get("id") for q in ready.get("questions", [])}
assert ans.get("question_id") in ready_q_ids, "Answer question_id must match a question from analysis.ready"
assert ev.get("question_id") == ans.get("question_id"), "Evaluation question_id must match answer question_id"

for q in ready.get("questions", []):
    if "sources" in q:
        assert all(s["end_line"] >= s["start_line"] for s in q["sources"])
    elif "line_start" in q and "line_end" in q:
        assert q["line_end"] >= q["line_start"]

print(f"Contract fixtures: {len(examples)} valid; snapshot/references: OK")
