# Paralel teslim yolu
Süre ekip kapasitesine bağlıdır. Aşağıdaki her dalga ortak kabul noktasıdır; sıralı kişi bekleme listesi değildir.

| Dalga | Ahmet | Derviş | Murathan | Efe |
|---|---|---|---|---|
| 1 | Extension/sidebar + fixture | API + fake motor | Fake provider + soru/rubrik | Şema + DB/ortam |
| 2 | Git diff + önizleme | Auth + analiz/durum | Gerçek provider + validasyon | Migration + adapter kontrolleri |
| 3 | API + cevap/sonuç | Motor + kayıt/tekrar | Değerlendirme/kalite | E2E + quota/isolation |
| 4 | VSIX + kullanılabilirlik | Hata/yeniden deneme | Pilot değerlendirme | Paket ve pilot kontrolü |

Önce fixture dikey akışı, sonra gerçek yerel diff ve canlı model. Marketplace ve ödeme ayrı sonraki teslimdir.
