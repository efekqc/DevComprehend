# Efe - Extension görev planı v2

Sözleşme, veritabanı, ortam ve kalite

Dört alanın aynı veri biçimine göre eşzamanlı ilerlemesini sağlamak; kalıcı öğrenme kayıtlarını ve uçtan uca kalite altyapısını kurmak.

## Alan ve branch

- Alan: contracts/ · infra/ · tests/ · .github/workflows/

- Branch: feat/DC-002-contracts-infra

- İnceleme: Ahmet

## İlk gün

1. contracts/v1/ şema ve sentetik fixture'ları doğrula.

2. DB tabloları ve ilk migration taslağını hazırla.

3. Yerel geliştirme ortamı ve contract CI komutlarını belgele.

4. İlk PR’da contract kontrolü, migration ve temiz ortam yönergesini teslim et.

## İş paketleri

### DC-002 / Ortak sözleşme ve ortam

Mevcut v1 JSON şemasını ekip çalışma tabanı yap. Endpoint/model ihtiyaçlarını üç alan sahibiyle uzlaştır; paket/sürüm ve local ortamı belgele.

Teslim: contracts/v1/; örnek payloadlar; infra/local/; ADR ve dev yönergesi.

Kabul: Fixture'lar şemaya uyar; v1 breaking change sessiz yapılmaz; herkes aynı sözleşmeden mock geliştirebilir.

### DC-005 / Veri modeli ve migration

User, repository/workspace, analysis, question, answer, evaluation, review ve usage modelini kur. Kavram ve prompt/model sürüm ilişkilerini tanımla.

Teslim: infra/db/migrations/ ve sentetik seed; storage sözleşmesi.

Kabul: Owner izolasyonu doğrulanır; snapshot/pipeline kayıtlı; mükerrer analiz/submission kuralları tutarlı; silme politikası açık.

### DC-008-A / Adapter ve E2E kontrolleri

Modül sahiplerinin birim testlerine ek olarak contract, API-motor-DB ve extension akışını doğrula. Deterministik CI için fake provider kullan.

Teslim: tests/contract/, integration/, e2e/; .github/workflows/.

Kabul: Boş/büyük diff, stale snapshot, auth, quota, duplicate ve invalid model output kontrol edilir; gerçek LLM CI koşulu değildir.

### DC-008-B / VSIX ve pilot kalite kapısı

Ahmet'in VSIX paketinin yükleme akışını doğrula; Derviş'le token/işlem kullanımını ölç. Canlı model kalite setini ayrı bütçeyle koordine et.

Teslim: Paket kontrol raporu; usage/budget kontrolü; pilot kabul listesi.

Kabul: VS Code install akışı başarılı; Cursor ayrı raporlanır; kaynak/cevap log sızıntısı yok; pilot kabul kriterleri kanıtlı.

## Entegrasyon

- Efe → Tüm ekip: Şema, sentetik fixture ve sürüm değişiklik notu.

- Derviş ↔ Efe: Kalıcı storage adapter ve owner/idempotency veri kuralları.

- Murathan ↔ Efe: Rubrik kalite seti; model/prompt sürümü; değerlendirme belirsizliği.

- Ahmet ↔ Efe: Extension paket/demo kanıtı; no-Git/stale/error E2E senaryoları.

## Push

```bash

# Repo zaten bilgisayarındaysa:
cd DevComprehend
git switch main
git pull --ff-only origin main
git switch -c feat/DC-002-contracts-infra

# İlgili dosyaları değiştir, sonra:
git status
git add contracts/ infra/ tests/ .github/workflows/
git commit -m "feat: add first module increment"
git push -u origin feat/DC-002-contracts-infra

```

[Ortak paralel çalışma rehberi](../parallel-work.md)

## Dalga çıktıları

1. Contract/fixture, DB taslağı, local ortam ve CI.

2. Migration/storage, bütçe kayıtları; adapter kontrolleri.

3. Extension → API → motor → DB E2E ve hata senaryoları.

4. Paket/uyumluluk kontrolü, pilot ölçüm ve kalite raporu.
