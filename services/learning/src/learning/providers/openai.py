"""Optional backend-only Responses API adapter; never selected implicitly."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..errors import LearningError
from . import ProviderRequest, ProviderResponse


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LearningError("PROVIDER_ERROR", "Model sağlayıcısı yönlendirme döndürdü.")


class OpenAIProvider:
    """No SDK dependency, no retries, no tools, no custom URLs, no payload logging."""

    def __init__(self, *, api_key: str, model: str, timeout: float = 30, opener=None):
        if not api_key.strip() or not model.strip() or not 0 < timeout <= 120:
            raise ValueError("Backend API key, model and a 0–120 second timeout are required")
        self._api_key = api_key
        self.model = model
        self.timeout = timeout
        self._open = opener or build_opener(_NoRedirect()).open

    @property
    def identity(self) -> str:
        return f"openai/{self.model}"

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        body = {
            "model": self.model, "store": False, "instructions": request.system,
            "input": [{"role": "user", "content": json.dumps(request.data, ensure_ascii=False)}],
            "max_output_tokens": request.max_output_tokens,
            "text": {"format": {"type": "json_schema", "name": f"learning_{request.operation}",
                                "strict": True, "schema": request.schema}},
        }
        http_request = Request("https://api.openai.com/v1/responses", method="POST",
                               data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                               headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"})
        try:
            with self._open(http_request, timeout=self.timeout) as response:
                raw = response.read(256_001)
            if len(raw) > 256_000:
                raise LearningError("PROVIDER_ERROR", "Model yanıtı boyut sınırını aştı.", True)
            data = json.loads(raw)
        except HTTPError as error:
            status = error.code
            error.close()
            raise LearningError("PROVIDER_ERROR", "Model sağlayıcısı isteği tamamlayamadı.",
                                status == 429 or status >= 500) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise LearningError("PROVIDER_ERROR", "Model sağlayıcısı isteği tamamlayamadı.", True) from None
        try:
            if data["status"] != "completed":
                raise LearningError("PROVIDER_ERROR", "Model yanıtı tamamlanmadı.", True)
            texts = []
            for item in data["output"]:
                if item.get("type") == "message":
                    for content in item["content"]:
                        if content.get("type") == "refusal":
                            raise LearningError("PROVIDER_REFUSAL", "Model değerlendirmeyi tamamlamadı.")
                        if content.get("type") == "output_text":
                            texts.append(content["text"])
            if len(texts) != 1:
                raise LearningError("INVALID_MODEL_OUTPUT", "Tek bir model çıktısı bekleniyor.", True)
            return ProviderResponse(texts[0], data["model"], data["usage"]["input_tokens"], data["usage"]["output_tokens"])
        except (KeyError, TypeError, AttributeError):
            raise LearningError("INVALID_MODEL_OUTPUT", "Model yanıt zarfı geçersiz.", True) from None
