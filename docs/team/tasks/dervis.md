# Derviş - Extension görev planı v2

Backend API, kimlik ve analiz orkestrasyonu

Extension'dan gelen yerel diff'i güvenilir biçimde analiz motoruna bağlamak; kimlik, kota, işlem durumu ve öğrenme kayıtlarını sunucuda yönetmek.

## Alan ve branch

- Alan: services/api/

- Branch: feat/DC-004-analysis-api

- İnceleme: Murathan

## İlk gün

1. API iskeleti ile contract request/response modellerini kur.

2. Fake learning adapter ve in-memory store oluştur.

3. POST analyses ve GET analysis için fixture yanıtı ver.

4. İlk PR’da gerçek LLM/DB olmadan analiz akışını test ederek teslim et.

## İş paketleri

### DC-004-A / API ve adapter sınırı

POST /v1/analyses, GET /v1/analyses/{id} ve cevap endpointini başlangıç sözleşmesine göre tasarla. Fake motorla başla; route içine model mantığı koyma.

Teslim: app/routes/, adapters/, domain/; şema validasyonu; API README.

Kabul: Geçersiz request 400; queued/ready/failed akışı anlaşılır; fake mode üretim modu gibi sunulmaz.

### DC-004-B / Kimlik, kota ve bütçe

Pilot kimlik/oturum yöntemini ADR ile belirle. Token doğrulama, owner kontrolü ve sunucu kullanım sınırı ekle. Gönderilen kodun boyutunu tekrar sınırla.

Teslim: app/auth/; quota/budget politikası; güvenli hata zarfı.

Kabul: Client user_id’ye güvenilmez; başka kullanıcıya ait analysis/question erişimi reddedilir; auth olmadan gerçek pilot açılmaz.

### DC-004-C / İdempotency ve veri entegrasyonu

Kullanıcı + repository + snapshot + pipeline sürümü için mükerrer analizi engelle. Efe'nin DB katmanını bağla. GitHub erişimi ilk koşul değildir.

Teslim: Durum geçişleri; storage adapter; yeniden deneme ve duplicate politikası.

Kabul: Çift istek gereksiz model çağrısı oluşturmaz; failed tekrar davranışı tanımlı; hassas kod/log yok.

### DC-007 / Motor, cevap ve tekrar

Murathan'ın generate/evaluate motorunu bağla. answer_request için submission_id kullan; değerlendirme ve tekrar bilgisini Efe modeliyle kaydet.

Teslim: Gerçek learning adapter; cevap/feedback endpointi; integration testleri.

Kabul: İlk sürüm cevap endpointi senkron response verir; sahibi doğrulanır; provider hatası anlaşılır ve kontrollü döner.

## Entegrasyon

- Ahmet → Derviş: Yerel request, snapshot hash, submission_id; webview değil host API çağrısı.

- Murathan ↔ Derviş: generate/evaluate Python adapter; çıktı ve hata sınıfları.

- Efe ↔ Derviş: Migration, owner relation, idempotency/unique kuralları; token kullanım kaydı.

- Derviş → Ahmet: HTTP endpointler, status ve hata zarfı; auth onboarding davranışı.

## Push

```bash

# Repo zaten bilgisayarındaysa:
cd DevComprehend
git switch main
git pull --ff-only origin main
git switch -c feat/DC-004-analysis-api

# İlgili dosyaları değiştir, sonra:
git status
git add services/api/
git commit -m "feat: add first module increment"
git push -u origin feat/DC-004-analysis-api

```

[Ortak paralel çalışma rehberi](../parallel-work.md)

## Dalga çıktıları

1. API + fake learning/memory storage; contract endpointleri.

2. Kimlik, owner, quota, payload sınırı ve idempotency.

3. Murathan motoru + Efe kalıcı kayıtları; cevap/tekrar.

4. E2E hata davranışı, pilot güvenilirliği ve operasyon rehberi.
