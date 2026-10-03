# Murathan Dede - Extension görev planı v2

Ürün koordinasyonu ve AI öğrenme motoru

Yerel Git değişikliklerinden kanıtlı soru ve rubrik üreten motoru geliştirmek; ürün kapsamını ve pilot ölçütlerini yönetmek.

## Alan ve branch

- Alan: services/learning/ · docs/product/

- Branch: feat/DC-006-learning-engine

- İnceleme: Derviş

## İlk gün

1. services/learning/ için modül iskeleti ve fake provider oluştur.

2. contracts/v1/examples/analysis-request.json ile generate akışını çalıştır.

3. Kavram, soru ve rubrik için deterministik çıktı üret; schema doğrulamasını bağla.

4. İlk PR’da fixture → ready analysis örneğini ve çalıştırma komutunu teslim et.

## İş paketleri

### DC-001 / Ürün ve kapsam

Extension komutu → yerel diff önizlemesi → 3-5 soru → cevap → tekrar yolculuğunu kesinleştir. Pilot ölçütlerini veri toplanmadan tanımla.

Teslim: docs/product/mvp.md; pilot görüşme/ölçüm taslağı.

Kabul: Kapsam ekipçe anlaşılır; değerlendirilmedi durumunun ürün dili net; ödeme/Marketplace ilk MVP dışında.

### DC-006 / Kavram, soru ve rubrik

generate(request) arayüzünü fake provider ile başlat. Sonra gerçek sağlayıcıyı bu arayüzün arkasına ekle. Diff'teki kavramları dosya/satır/snapshot kanıtına bağla.

Teslim: src/learning/concepts/, questions/, providers/; sürümlü prompts/; birim testler.

Kabul: 3-5 soru sözleşmeye uyar; kaynak referansları doğru; kanıtsız mimari neden kesin gerçek gibi yazılmaz.

### DC-007 / Cevap değerlendirme ve tekrar

evaluate(question,answer) arayüzünde rubrik met/partial/missing sonuçlarını ve feedback'i üret. unassessed/developing/demonstrated ayrımını koru; belirsiz sonuç için uncertain kullan.

Teslim: evaluation/, repetition/; doğru/kısmi/yanlış/belirsiz cevap fixture'ları.

Kabul: Açıklama rubrikle tutarlı; model hatasında kesin yetkinlik iddiası yok; due_at veya null davranışı açık.

### DC-009 / Pilot ve ürün kararı

Efe ile kalite setini ve pilot ölçümlerini yorumla. Takım arkadaşlarının blokajlarını kısa toplantıyla çöz; ortak dokümanları güncel tut.

Teslim: Pilot raporu; yanlış değerlendirme örnekleri; devam/daraltma kararı.

Kabul: Görüş ve davranış ölçümü ayrılır; örnek sayısı ve sınırlılıklar açık; sonraki özellikler veriyle seçilir.

## Entegrasyon

- Derviş → Murathan: analysis_request; kimliksiz motor çağrısı; snapshot ve pipeline sürümü.

- Murathan → Derviş: generate/evaluate adapter çıktısı; şema hatası ve provider hata davranışı.

- Murathan ↔ Efe: Rubrik/şema ve kalite fixture'ları; model/prompt sürüm kaydı.

- Murathan → Ahmet: Soru/feedback metinleri ve uncertain/değerlendirilmedi görünümü.

## Push

```bash

# Repo zaten bilgisayarındaysa:
cd DevComprehend
git switch main
git pull --ff-only origin main
git switch -c feat/DC-006-learning-engine

# İlgili dosyaları değiştir, sonra:
git status
git add services/learning/ docs/product/
git commit -m "feat: add first module increment"
git push -u origin feat/DC-006-learning-engine

```

[Ortak paralel çalışma rehberi](../parallel-work.md)

## Dalga çıktıları

1. Fake provider + fixture üretimi; kapsam/pilot taslağı.

2. Gerçek provider adapter; kavram/soru/rubrik validasyonu.

3. Derviş’le cevap/tekrar; Efe ile kalite seti.

4. Pilot geri bildirimi; yanlış değerlendirme düzeltmeleri.
