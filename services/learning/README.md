# Öğrenme motoru — DC-006 / DC-007

Murathan'ın backend içi Python modülü. `generate(request)` ve `evaluate(question, answer)` ortak v1 sözleşmesini tüketir; contracts/ değiştirilmedi. Python 3.12+ hedeflenir; yerel doğrulama Python 3.14.3 ile yapıldı.

**Çalışan:** Sentetik request → fake provider → kanıtı doğrulanmış ready analysis; cevap → rubrik → geri bildirim ve tekrar tarihi. Sürümlü promptlar, JSON Schema ve anlamsal doğrulama, bütçe sınırları ve güvenli hata davranışı mevcut. İsteğe bağlı OpenAI HTTP adaptörü mock HTTP ile test edildi.

**Henüz doğrulanmadı:** Canlı model kalitesi, çalışan API/veritabanı bağlantısı, extension/VSIX ve Cursor. Fake provider bilinen fixture'ları tekrarlar; yeni kaynak kodunu analiz etmez ve bilinmeyen cevabı tahmin ederek notlandırmaz.

## Kurulum ve çalıştırma

Repository kökünden:

```bash
python3 -m venv services/learning/.venv
services/learning/.venv/bin/python -m pip install -r services/learning/requirements.txt
PYTHONPATH=services/learning/src services/learning/.venv/bin/python -m learning
PYTHONPATH=services/learning/src services/learning/.venv/bin/python -m learning.quality
PYTHONPATH=services/learning/src services/learning/.venv/bin/python -m unittest discover -s services/learning/tests -v
services/learning/.venv/bin/python scripts/check_contract_examples.py
python3 scripts/check_repository.py
```

Demo 3 soru ve 7 sentetik cevap değerlendirmesini JSON olarak yazdırır; dosya kaydetmez, ağ kullanmaz. Quality komutu beklenen etiketlerle uyuşmayı sayar; fake modundaki 7/7, LLM doğruluk oranı değildir. Tek doğrudan bağımlılık, ortak kontrol betiğinde de kullanılan `jsonschema==4.26.0`; framework veya SDK eklenmedi.

## API adapter kullanımı

```python
from learning import LearningEngine, LearningError
from learning.providers.fake import FakeProvider

engine = LearningEngine(FakeProvider())
ready = engine.generate(request, analysis_id=analysis_id_from_api)
# API soruyu oturum kullanıcısına ait kayıttan yükler; istemciden rubrik almaz.
evaluation = engine.evaluate(saved_question, answer_request)
```

`analysis_id` verilmezse istek, bağlam, sağlayıcı, prompt, şema ve limitlere bağlı kararlı ID üretilir. Bu bir kullanıcı kimliği veya yetkilendirme mekanizması değildir. API'nin queued ID'si verilirse korunur. `engine.fingerprint(request)` önbellek anahtarının yalnız bir bileşenidir; kullanıcı ile birlikte kullanılmalıdır. Motor cache, idempotency veya kota sağlamaz; aynı çağrı tekrar yapılırsa sağlayıcı tekrar çağrılır.

Kimlik doğrulama, önizleme onayı, kullanıcı izolasyonu, `submission_id` idempotency, kalıcı kayıt ve kullanıcı kotası API/extension sorumluluğundadır. Motor istemciden soru veya rubrik kabul eden bir endpoint açmaz. [Entegrasyon teslimi](INTEGRATION.md) kayıt davranışını tanımlar.

## Kanıt sınırı

- `snapshot_id = SHA256(diff UTF-8)` kontrol edilir. Bu, tüm workspace'in hash'i değildir.
- V1 satır tarafı veya bağlam başlangıç satırı taşımıyor. Bu modülde `context[].content` dosyanın 1. satırından başlayan tam onaylı içeriğidir. Parça bağlam için şema koordinasyonu gerekir; ofset tahmin edilmez.
- Yalnız diff'in yeni tarafında açıkça bulunan hunk satırları kaynak gösterilebilir. Bağlam mevcutsa bu satırların metni diff ile eşleşmelidir.
- Aralıklar ayrı hunk'ların arasındaki görünmeyen satırları içeremez. Snapshot, yol, satır, soru ID'si ve rubrik tekilliği kontrol edilir.
- Tamamen silinmiş dosyalar, binary/boş diff ve yeni tarafta kanıt bulunmayan girdiler reddedilir. Quoted Git yolları/combined diff desteklenmez; sessizce tahmin yapılmaz.
- Yapısal doğrulama anlamsal doğruluğu kanıtlamaz. Kanıtsız mimari gerekçeyi “çıkarım” olarak işaretlemek prompt kuralıdır; gerçek modelde insan kalite incelemesi gerekir.

## Değerlendirme ve tekrar

| Durum | assessment_state | uncertain | due_at |
|---|---|---|---|
| Henüz cevap yok | unassessed (UI başlangıcı) | false | null |
| Whitespace cevap | unassessed | false | null |
| Model belirsiz, hata, bütçe veya doğrulama sorunu | unassessed | true | null |
| Tüm rubrik maddeleri met | demonstrated | false | UTC şimdi + 7 gün |
| En az bir missing | developing | false | UTC şimdi + 1 gün |
| Eksik madde yok, en az bir partial | developing | false | UTC şimdi + 3 gün |

Boş string `answer` ortak şemaya göre geçersizdir; UI göndermemelidir. `unassessed + uncertain` düşük not değildir. Belirsizlikte rubrik sonuçları gösterilmez; motor belirsiz cevabı 1 gün sonra tekrar önerir, ancak API yalnız güvenilir sonuçların tekrar kaydını güncellemelidir. Önceki güvenilir geçmişi silmemek API'nin görevidir. Sonuç yalnız bu soruya aittir; global kavram ustalığına otomatik dönüştürülmez. Sıralama veya yüzde puan üretilmez. Tekrar politikası `repetition-2`, pilot hipotezidir.

## Hatalar ve bütçe

Geçersiz istek, snapshot veya aşırı büyük girdi `LearningError` yükseltir. `error.as_dict()` güvenli `code/message/retryable` içerir. Üretimde sağlayıcı/çıktı hatası `failed analysis_result` döndürür; boş sorularla “ready” dönmez. Değerlendirmede sağlayıcı/çıktı hatası `uncertain` döndürür. Varsayılan olarak onarım kapalıdır; `max_repair_attempts=1` açılırsa yalnız kullanım bilgisi alınmış geçersiz model çıktısı için en fazla bir ek çağrı yapılır. İlk çağrı ve onarım aynı girdi/çıktı token bütçesini paylaşır; sağlayıcı hatası veya bilinmeyen kullanımda onarım denenmez. Bu, kota rezervasyonu değildir; API tarafı maliyet tavanını ayrıca uygular.

Varsayılan limitler: request 48.000 UTF-8 byte, answer zarfı 8.000 byte, model JSON çıktısı 48.000 byte, 20 diff/bağlam dosyası, 32.000 input ve 4.000 output token. Girdi kapısı JSON + prompt + şemanın UTF-8 byte sayısı ve 1.024 envelope payıyla muhafazakâr tahmindir; tokenizer hesabı değildir. Sağlayıcının gerçek kullanım sayıları ayrıca kontrol edilir. Çıktı limitinin sonradan aşılmış olduğunun görülmesi oluşan ücreti geri almaz; API kota rezervasyonu gereklidir.

Diff ayrıca en fazla 400 satır ve 16.000 karakter olabilir. `prune_git_diff` preview/onay öncesi lock/build dosyalarını tam dosya blokları halinde çıkarır; kalan diff sınırı aşarsa kesmek yerine reddeder. Backend aynı sınırları ve hariç tutulan yolları yeniden denetler; extension filtrelenen diff/context ile snapshot'ı yeniden üretmelidir.

`on_usage=callback` ile pipeline/prompt sürümü, prompt hash'i, model sürümü, input/output token bilgisi ayrı kayda alınabilir; kaynak ve cevap içermez. Başarıyla alınmış provider response için, JSON doğrulamasından önce çağrılır. Callback hata verirse işlem durur; callback'i API tarafında güvenilir yapın. Ağ kesintisinde kullanım bilinmeyebilir; eksik kayıt sıfır maliyet sayılmaz. Fake kullanım sayıları sıfırdır, gerçek kullanım tahmini değildir.

## İsteğe bağlı gerçek sağlayıcı

```python
import os
from learning import LearningEngine
from learning.providers.openai import OpenAIProvider

engine = LearningEngine(OpenAIProvider(
    api_key=os.environ["LLM_API_KEY"],
    model=os.environ["LLM_MODEL"],
))
```

Yalnız backend ortamı; anahtar kullanıcı mesajında, extension paketinde veya kodda tutulmaz. Model bilinçli olarak sabitlenmedi; ekip Structured Outputs destekli bir model ve bütçe seçmelidir. Canlı kalite seti için bu iki değişkeni güvenli backend ortamında tanımladıktan sonra `python -m learning.quality --provider openai` kullanılabilir (aynı PYTHONPATH/venv ile). Bu komut 7 sentetik cevabı ücretli değerlendirmeye gönderir. Bu teslimde çalıştırılmadı.

Adaptör [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) biçiminde Responses API'ye `text.format` JSON schema gönderir. `store: false`, 30 saniye timeout, çıktı byte sınırı, yönlendirme reddi ve refusal/incomplete kontrolü vardır; tool çağrısı yoktur. `store: false` sağlayıcının tüm saklama politikalarının kapandığı iddiası değildir. Gerçek endpoint/model erişimi ve anlamsal kalite canlı pilot öncesi doğrulanmalıdır.

## Dosyalar

`src/learning/concepts/` kanıt dizini; `questions/` soru doğrulama; `evaluation/` rubrik; `repetition/` tekrar politikası; `providers/` fake/OpenAI sınırı; `prompts/` sürümlü sistem metinleri; `tests/fixtures/answers.json` sentetik kalite seti.
