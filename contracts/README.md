# Sözleşme v1 - paralel başlangıç
Sorumlu: Efe. Başlangıç şeması [message.schema.json](v1/message.schema.json); sentetik örnekler v1/examples/.
Bu şema çalışma tabanıdır; üretim auth, endpoint ve depolama kodu henüz yoktur.

## Mesajlar
- analysis_request: Yerel diff, repository_id (workspace için üretilen opak ID), base SHA, snapshot_id, staged/unstaged scope, bağlam, pipeline sürümü.
- analysis_result: queued/fetching/generating/ready/failed; sorular; güvenli hata.
- answer_request: question_id, cevap, submission_id.
- evaluation_result: rubrik maddeleri, geri bildirim, belirsizlik ve tekrar tarihi.

Snapshot SHA-256 diff özeti; kaynak referansı bu snapshot'a bağlıdır. base_commit_sha çalışma ağacındaki kodun aynısı değildir.
Kullanıcı ID'si body'de taşınmaz; sunucu kimlik bağlamından belirlenir.

## HTTP başlangıç sözleşmesi
POST /v1/analyses → 202 analysis_result (queued).
GET /v1/analyses/{id} → 200 analysis_result.
POST /v1/analyses/{id}/answers → 200 evaluation_result; ilk sürüm senkron değerlendirme.
Hatalar: 400 INVALID_INPUT, 401 UNAUTHENTICATED, 403 FORBIDDEN, 404 NOT_FOUND, 409 STALE_SNAPSHOT, 413 PAYLOAD_TOO_LARGE, 429 QUOTA_EXCEEDED, 502 PROVIDER_ERROR. Hata zarfı: code, message, retryable. Asenkron cevaba geçilirse sözleşme sürümüyle değiştirilir.

## Motor arayüzü
generate(analysis_request) → ready analysis_result.
evaluate(question,answer_request) → evaluation_result.
Fake provider/motor ve UI fixture'ları aynı biçimi kullanır.

## Değişiklik
Efe PR açar; Ahmet/Derviş/Murathan etkileri inceler. v1 içinde yalnız geriye uyumlu değişiklik; kırıcı değişiklik yeni sürüm veya koordineli migration ile.
