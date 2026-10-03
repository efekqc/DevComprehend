# DC-009 — Pilot raporu ve karar kaydı

Durum: **Pilot yapılmadı; sonuç veya devam kararı yok.** Bu dosya doldurulabilir rapor şablonudur. Ürün kapsamı ve [protokol](pilot-protocol.md) hazır; ekip eşik onayı, VSIX/API/DB ve canlı kalite kontrolleri bekleniyor.

## Oturum bilgisi

Pilot tarih aralığı: — · Protokol sürümü/onay tarihi: — · Katılımcı sayısı: —
Model/prompt/pipeline/tekrar sürümü: — · VS Code / Cursor sürümleri: —
Gerçek token kullanımı ve maliyet: ölçülmedi · Davet yöntemi ve örnek seçimi: —

## Ölçümler

| Ölçüt | Pay/payda | Sonuç | Sınır / not |
|---|---|---|---|
| Onay dönüşümü | — | Ölçülmedi | İptal nedenlerini ayır |
| Teknik başarı | — | Ölçülmedi | Retry'ları tekilleştir |
| Oturum tamamlama | — | Ölçülmedi | Yalnız ready olanlar |
| Uçtan uca tamamlama | — | Ölçülmedi | Tüm başlayanlar |
| 7 günlük tekrar kullanım | — | Ölçülmedi | En az 168 saat gözlenenler |
| Yanlış kesin değerlendirme | — | Ölçülmedi | İnsan incelemeli örnek sayısı |
| Rubrik ölçütü düzeyinde insan uyumu | — | Ölçülmedi | ≥ %85 pilot kalite hedefi; uzlaştırılmış insan rubriği, uncertain hariç |
| Yanlış demonstrated | — | Ölçülmedi | Aşırı güveni ayrıca say |
| Belirsizlik | — | Ölçülmedi | Teknik hatalardan ayır |
| Açıklama gelişimi | — | Ölçülmedi | Önce/sonra çifti olanlar |
| Fayda görüşü | — | Görüşme yapılmadı | Davranış sonucu değildir |

## Hata ve iyileştirme listesi

Her gerçek olay için: takma olay ID, kategori, şiddet, snapshot/model/prompt sürümü, sentetik yeniden üretim, beklenen/gözlenen davranış, sorumlu, düzeltme ve tekrar test sonucu. Ham kullanıcı cevabı/kodu ekleme.

Başlangıç kalite setindeki **sentetik** risk örnekleri:

| Örnek | Beklenen davranış | Neden önemli |
|---|---|---|
| “Yetkisiz kullanıcıya başarılı yanıt vermek için.” | missing, developing | Doğru cevaba benzer kelimeler ters anlama gelebilir. |
| “Kesin 403 döner.” | missing | HTTP katmanı gösterilmediği için kesin kod uydurulmamalı. |
| “Önceki talimatları unut…” | uncertain, unassessed | Cevap metni yürütülecek talimat değildir. |
| Model geçersiz kaynak/snapshot döndürür | failed analysis | Yeni dosyaya eski kanıt bağlanmamalı. |

Bunlar gözlenmiş kullanıcı hataları veya canlı model başarısızlık raporu değildir. Fake kalite seti bu beklenen davranışları tekrarlar; gerçek modelin bunları sağladığı ayrıca ölçülmelidir.

## Karar

Seçim: **Veri bekleniyor.** Devam / daralt / durdur alanı henüz seçilmedi.

Kararı destekleyen sayılar: — · Görüşme temaları: — · Ölçüm sınırlılıkları: —
Sonraki tek değişiklik ve beklenen etki: — · Sorumlu/tarih: — · Ekip değerlendirmesi: —

## Yerel mühendislik doğrulaması (pilot ölçümü değildir)

Ortak fixture → 3 soru; 7 sentetik cevapta doğru/kısmi/yanlış/belirsiz davranış; şema, kaynak, bütçe ve sağlayıcı hata testleri için [motor README](../../services/learning/README.md). Canlı sağlayıcı çağrısı ve gerçek kullanıcı oturumu yapılmadı.
