"""Check synthetic contract fixtures, references and snapshot hash."""
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "contracts/v1"
schema = json.loads((BASE / "message.schema.json").read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker())
examples = {}
for path in sorted((BASE / "examples").glob("*.json")):
    data = json.loads(path.read_text())
    validator.validate(data)
    examples[path.name] = data
request = examples["analysis-request.json"]
assert hashlib.sha256(request["diff"].encode()).hexdigest() == request["snapshot_id"]
ready = examples["analysis-ready.json"]
assert all(s["snapshot_id"] == request["snapshot_id"] for q in ready["questions"] for s in q["sources"])
assert all(s["end_line"] >= s["start_line"] for q in ready["questions"] for s in q["sources"])
assert examples["answer-request.json"]["question_id"] in {q["id"] for q in ready["questions"]}
assert examples["evaluation-result.json"]["question_id"] == examples["answer-request.json"]["question_id"]
print(f"Contract fixtures: {len(examples)} valid; snapshot/references: OK")
