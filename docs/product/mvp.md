# MVP kapsamı
## Hipotez
AI ile kod geliştiren kullanıcılar, kendi değişikliklerinden üretilmiş kısa sorularla anlayış açıklarını görmek ve tekrar öğrenmek ister.

## Dahil
- Kullanıcı tarafından seçilen repository ve tek commit/PR analizi.
- Sınırlı diff ve ilgili kod bağlamı.
- 2–5 kavram, her biri commit SHA + dosya + satır referansıyla.
- 3–5 soru ve serbest metin cevap.
- Rubrikle geri bildirim, değerlendirilmeyen alanların ayrı gösterilmesi.
- Önceki cevapların ve tekrar tarihinin saklanması.
- Kullanım/token bütçesi ve işlem hata durumları.

## İlk sürüm dışında
VS Code extension, otomatik PR merge engeli, herkese açık yetkinlik badge'i, takım performans sıralaması, büyük knowledge graph veritabanı ve ödeme sistemi.

## Kabul kriterleri
1. Sabit test repository'sinde diff kaynak referansları doğru bulunur.
2. Her soru ilgili kod kanıtı ve değerlendirme rubriği içerir.
3. Belirsiz mimari nedenler kesin gerçek gibi sunulmaz.
4. Cevap verilmeden yetkinlik puanı üretilmez.
5. Model hatası veya bütçe aşımı tekrar denenebilir durum oluşturur.
6. Bir kullanıcı başka kullanıcının analizine erişemez.
7. Kaynak kodu ve cevapların saklama/silme davranışı belgelenir.

## Pilot
10–20 gönüllü kullanıcı. Analizden cevaplamaya dönüşüm, oturum tamamlama, 7 gün içinde tekrar kullanım ve fayda görüşmesi ölçülür. Eşikler pilot başlamadan ekipçe belirlenir; mevcut sayılar hedef kitle büyüklüğü varsayımıdır.
