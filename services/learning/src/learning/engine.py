"""Synchronous, stateless API adapter; each invocation performs at most one model call."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Callable

from .concepts import evidence_index
from .contracts import (
    EVALUATION_SCHEMA, GENERATION_SCHEMA, MODULE_ROOT, validate, validate_provider,
)
from .errors import LearningError
from .evaluation import unassessed, validate_rubric
from .providers import Provider, ProviderRequest, ProviderResponse
from .questions import validate_question, validate_questions
from .repetition import plan

PIPELINE_VERSION = "pilot-1"
PROMPT_VERSION = "v1"


@dataclass(frozen=True)
class Limits:
    max_request_bytes: int = 48_000
    max_answer_bytes: int = 8_000
    max_response_bytes: int = 48_000
    max_input_tokens: int = 32_000
    max_output_tokens: int = 4_000

    def __post_init__(self):
        if any(type(value) is not int or value < 1 for value in vars(self).values()):
            raise ValueError("Limits must be positive integers")


def encode(value) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
        text.encode("utf-8")
        return text
    except (TypeError, ValueError, RecursionError, UnicodeError):
        raise LearningError("INVALID_INPUT", "Geçerli JSON veri yapısı gerekli.") from None


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-finite JSON value")


class LearningEngine:
    def __init__(self, provider: Provider, *, limits: Limits | None = None,
                 clock: Callable[[], datetime] | None = None,
                 on_usage: Callable[[dict], None] | None = None):
        self.provider = provider
        self.limits = limits or Limits()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.on_usage = on_usage
        self.prompts = {
            op: (MODULE_ROOT / f"prompts/{op}.{PROMPT_VERSION}.txt").read_text(encoding="utf-8")
            for op in ("generate", "evaluate")
        }

    def _check_size(self, data, limit: int):
        if len(encode(data).encode("utf-8")) > limit:
            raise LearningError("PAYLOAD_TOO_LARGE", "İçerik boyut sınırını aşıyor.")

    def fingerprint(self, request: dict) -> str:
        """Backend cache key component; must still be scoped to the authenticated user."""
        data = {"request": request, "provider": self.provider.identity,
                "pipeline": PIPELINE_VERSION, "prompt": self.prompts["generate"],
                "limits": vars(self.limits), "schema": GENERATION_SCHEMA}
        return hashlib.sha256(encode(data).encode("utf-8")).hexdigest()

    def _complete(self, operation: str, data: dict, schema: dict) -> dict:
        system = self.prompts[operation]
        # Conservative UTF-8 byte estimate plus envelope allowance. Exact usage
        # comes from the adapter; this is not account quota or billing enforcement.
        upper_estimate = len(encode({"system": system, "data": data, "schema": schema}).encode("utf-8")) + 1024
        if upper_estimate > self.limits.max_input_tokens:
            raise LearningError("TOKEN_BUDGET_EXCEEDED", "Girdi token bütçesine sığmıyor.")
        request = ProviderRequest(operation, system, deepcopy(data), deepcopy(schema), self.limits.max_output_tokens)
        try:
            response = self.provider.complete(request)
        except LearningError:
            raise
        except Exception:
            # No provider exception text is propagated to logs, callers or feedback.
            raise LearningError("PROVIDER_ERROR", "Model sağlayıcısına ulaşılamadı.", True) from None
        if (not isinstance(response, ProviderResponse) or not isinstance(response.text, str)
                or not isinstance(response.model_version, str) or not response.model_version.strip()
                or any(type(value) is not int or value < 0
                       for value in (response.input_tokens, response.output_tokens))):
            raise LearningError("INVALID_MODEL_OUTPUT", "Model kullanım bilgisi geçersiz.", True)
        # Backend can persist this metadata separately: v1 has no metadata field.
        if self.on_usage:
            self.on_usage({"operation": operation, "pipeline_version": PIPELINE_VERSION,
                           "prompt_version": f"{operation}.{PROMPT_VERSION}",
                           "prompt_sha256": hashlib.sha256(system.encode()).hexdigest(),
                           "model_version": response.model_version,
                           "input_tokens": response.input_tokens, "output_tokens": response.output_tokens})
        if (response.input_tokens > self.limits.max_input_tokens
                or response.output_tokens > self.limits.max_output_tokens):
            raise LearningError("TOKEN_BUDGET_EXCEEDED", "Model token bütçesini aştı.")
        try:
            response_bytes = len(response.text.encode("utf-8"))
        except UnicodeError:
            raise LearningError("INVALID_MODEL_OUTPUT", "Model çıktısı geçerli UTF-8 değil.", True) from None
        if response_bytes > self.limits.max_response_bytes:
            raise LearningError("INVALID_MODEL_OUTPUT", "Model çıktısı boyut sınırını aştı.", True)
        try:
            value = json.loads(response.text, object_pairs_hook=_pairs, parse_constant=_reject_constant)
            # JSON escapes can decode into lone surrogates even if the raw bytes were valid.
            encode(value)
        except LearningError:
            raise LearningError("INVALID_MODEL_OUTPUT", "Model çıktısı geçerli UTF-8 JSON değil.", True) from None
        except (ValueError, RecursionError):
            raise LearningError("INVALID_MODEL_OUTPUT", "Model geçerli JSON döndürmedi.", True) from None
        validate_provider(value, schema)
        return value

    def generate(self, request: dict, *, analysis_id: str | None = None) -> dict:
        self._check_size(request, self.limits.max_request_bytes)
        validate(request, "analysis_request")
        if request["pipeline_version"] != PIPELINE_VERSION:
            raise LearningError("INVALID_INPUT", "Desteklenmeyen pipeline sürümü.")
        evidence = evidence_index(request)
        if analysis_id is not None and (not isinstance(analysis_id, str) or not analysis_id.strip()):
            raise LearningError("INVALID_INPUT", "Analiz kimliği boş olamaz.")
        result = {"kind": "analysis_result", "contract_version": "1",
                  "id": analysis_id or f"analysis-{self.fingerprint(request)}",
                  "status": "ready", "questions": [], "error": None}
        try:
            output = self._complete("generate", {"analysis_request": request, "evidence_lines": evidence}, GENERATION_SCHEMA)
            validate_questions(output["questions"], request["snapshot_id"], evidence)
            result["questions"] = output["questions"]
        except LearningError as error:
            result.update(status="failed", error=error.as_dict())
        validate(result, "analysis_result")
        return result

    def evaluate(self, question: dict, answer: dict) -> dict:
        self._check_size(question, self.limits.max_request_bytes)
        validate_question(question)
        self._check_size(answer, self.limits.max_answer_bytes)
        validate(answer, "answer_request")
        if answer["question_id"] != question["id"]:
            raise LearningError("INVALID_INPUT", "Cevap bu soruya ait değil.")
        if not answer["answer"].strip():
            return unassessed(question["id"], "Henüz değerlendirilebilir bir cevap verilmedi.", False)
        try:
            output = self._complete("evaluate", {"question": question, "answer": answer["answer"]}, EVALUATION_SCHEMA)
            validate_rubric(question, output)
        except LearningError:
            return unassessed(question["id"], "Cevap güvenilir biçimde değerlendirilemedi. Daha sonra yeniden deneyin.")
        if output["uncertain"]:
            # Suppress even apparently positive rubric labels when confidence is absent.
            result = unassessed(question["id"], "Belirsiz değerlendirme: " + output["feedback"])
        else:
            state, due_at = plan(output["rubric_results"], False, self.clock())
            result = {"kind": "evaluation_result", "contract_version": "1", "question_id": question["id"],
                      **output, "assessment_state": state, "due_at": due_at}
        validate(result, "evaluation_result")
        return result
