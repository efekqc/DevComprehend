# Backend API — DC-004

Derviş'in alanı. Extension'dan gelen onaylı diff'i öğrenme motoruna bağlar; kimlik, kota, sahiplik ve idempotency sunucudadır. Framework/dependency eklenmedi: stdlib HTTP katmanı + saf domain servisi + in-memory store. Motor olarak `services/learning` modülü kullanılır (FakeProvider varsayılan).

**Çalışan:** Token doğrulama, POST /v1/analyses, GET /v1/analyses/{id}, POST /v1/analyses/{id}/answers; owner izolasyonu, kullanıcı+repo+snapshot+pipeline tekilleştirmesi, submission_id idempotency, günlük pilot kotası (5 analiz / 20 değerlendirme), güvenli hata zarfı. 12 birim testi ve stdlib sunucuyla canlı smoke testi geçti.

**Henüz yok:** Gerçek kimlik ADR'si (dev token geliştirme içindir), Efe'nin kalıcı DB katmanı, retention/silme akışı, gerçek LLM bütçe rezervasyonu, production WSGI/ASGI sunucusu. Memory store yeniden başlatmada sıfırlanır; fake mode üretim modu değildir.

## Çalıştırma

```bash
PYTHONPATH=services/api/src:services/learning/src services/learning/.venv/bin/python -m api
# Auth: Authorization: Bearer dev-token  (ek token: API_DEV_TOKENS="tok1=user-1,tok2=user-2")
PYTHONPATH=services/api/src:services/learning/src services/learning/.venv/bin/python \
  -m unittest discover -s services/api/tests -v
```

## Endpointler

| Endpoint | Davranış |
|---|---|
| POST /v1/analyses | analysis_request doğrulanır → motor `generate` → analysis_result. Aynı kullanıcı+repository+snapshot+pipeline tekrarı yeni model çağrısı yapmadan kayıtlı sonucu döner. |
| GET /v1/analyses/{id} | Yalnız sahibi görür; başkasının kaydı 404 döner (varlık sızdırılmaz). |
| POST /v1/analyses/{id}/answers | answer_request doğrulanır; soru bu analize ve kullanıcıya ait olmalı. Aynı submission_id + aynı cevap kayıtlı sonucu döner; farklı cevap 409. `due_at` ve güvenilir sonuç varsa tekrar kaydı güncellenir; `uncertain` denemeler eski kaydı ezmez. |

## Hata zarfı

`{"error": {"code", "message", "retryable"}}`. Eşleme: INVALID_INPUT/INSUFFICIENT_EVIDENCE → 400, UNAUTHENTICATED → 401, NOT_FOUND → 404, STALE_SNAPSHOT/SUBMISSION_CONFLICT → 409, PAYLOAD_TOO_LARGE/TOKEN_BUDGET_EXCEEDED → 413, QUOTA_EXCEEDED → 429, sağlayıcı/iç hata → 500 INTERNAL (detay sızdırılmaz). Gövde sınırı 64 KB; kaynak ve cevaplar loglanmaz (access log kapalı).

## Dosyalar

`src/api/routes.py` HTTP sınırı · `domain.py` analiz/cevap akışı · `auth.py` dev token · `quota.py` günlük kota · `store.py` in-memory adapter · `server.py` stdlib sunucu · `tests/test_api.py` davranış testleri.
