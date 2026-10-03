# Extension-first MVP ve ürün modeli
## Amaç
AI ile geliştirilen kodun ne yaptığını ve neden kullanıldığını, kullanıcının kendi Git değişiklikleri üzerinden öğretmek.

## Dağıtım ve iş modeli
Ana ürün VS Code extension; backend öğrenme servisidir. Cursor desteği test sonrası ilan edilir. Pilot ücretsiz ve kullanım kotalı planlanır. Sonraki hipotez: bireysel abonelik ve takım koltukları; ücretli analiz kotası model maliyetini kontrol eder. Fiyatlar ve ödeme entegrasyonu henüz kararlaştırılmadı.
Backend sağlayıcı anahtarını yönetir; kullanıcıya ilk MVP'de API key girdirtme zorunluluğu yoktur. Üretim için kullanıcı kimliği, sunucu kotası ve token bütçesi gerekir. Geliştirme mock modu model maliyeti oluşturmaz.

## Kullanıcı akışı
1. Git workspace'i seç ve Analyze Changes komutunu çalıştır.
2. staged veya unstaged değişiklik kapsamını seç; snapshot hash üret.
3. Gönderilecek diff/bağlam önizlemesini gör ve gönderimi onayla.
4. Sidebar'da 2–5 kavram ve 3–5 soru gör.
5. Serbest metin cevap ver; rubrik geri bildirimi al.
6. Zorlanılan kavramlar için tekrar tarihi ve geçmişi gör.

## Kabul
- Git olmayan/çoklu workspace/boş diff kontrollü işlenir.
- Onay olmadan kaynak kodu backend'e gönderilmez.
- Diff ve ilgili dosyalar boyut sınırıyla alınır; binary/generated dosyalar atlanır.
- Yerel snapshot değişirse eski kanıt sessizce yeni dosyaya bağlanmaz.
- API/motor şema doğrular; failed ve yeniden deneme davranışı açıktır.
- Cevaplar yalnız kullanıcıya aittir; quota/idempotency sunucuda uygulanır.
- VSIX geliştirme paketi ve yükleme/demo yönergesi vardır.
- Soru kanıtlıdır; rubrik puanı genel yetkinlik kanıtı olarak sunulmaz.

## Sonraki sürüm
GitHub PR analizi, web portalı, ödeme, team dashboard, VS Code Marketplace yayını ve otomatik diff tetikleme. İlk sürümde manuel komut; sürekli kaynak kodu aktarımı yok.

## Pilot
10–20 gönüllü; oturum tamamlanması, 7 günlük tekrar kullanım, algılanan fayda ve yanlış değerlendirme oranı. Eşikler veri toplanmadan ekipçe kaydedilir.

[Pilot protokolü](pilot-protocol.md) ölçüm tanımlarını, önerilen ön kayıt eşiklerini ve görüşme formunu içerir. [Pilot raporu](pilot-report.md) henüz veri toplanmadığını açıkça ayırır. Eşikler ekip onayı alınmış sonuçlar değildir.

## Değerlendirme dili ve tekrar

- **Değerlendirilmedi (unassessed):** Soru cevaplanmadı veya güvenilir değerlendirme üretilemedi. Düşük puan anlamına gelmez.
- **Gelişiyor (developing):** Bu cevapta en az bir rubrik maddesi partial veya missing. Eksik/yanlış nokta ve sonraki adım açıklanır.
- **Bu soruda gösterildi (demonstrated):** Bu sorunun tüm rubrik maddeleri karşılandı. Genel teknoloji yetkinliği iddiası değildir.
- **Belirsiz (uncertain):** Cevap/kanıt yetersiz veya model işlemi başarısız. Kesin sonuç ve yeni tekrar tarihi oluşturulmaz; eski güvenilir geçmiş korunur.

Pilot tekrar önerisi: missing varsa 1 gün, yalnız partial varsa 3 gün, tümü met ise 7 gün. Tarihler UTC saklanıp kullanıcının saat diliminde gösterilir. `due_at=null`, yeni tekrar planı yok demektir. Bu zaman aralıkları öğrenme etkisi kanıtlanmış sonuçlar değil, test edilecek başlangıç politikasıdır.

## İlk dikey akışın somut kabulü

1. Kullanıcı staged/unstaged seçer; önizleme iptalinde backend/model isteği oluşmaz.
2. Gönderilen diff ve SHA-256 özeti eşleşir. Kaynak satırları onaylanan görüntüye bağlanır; base commit çalışma ağacı gibi sunulmaz.
3. Sözleşme geçerli 3–5 farklı soru, 2–5 farklı kavram ve her soruda kanıt + beklenen cevap unsurlarını taşıyan rubrik oluşur.
4. Doğru/kısmi/yanlış/belirsiz cevaplar farklı sonuçlar verir; provider/şema hatasında başarı veya düşük yetkinlik iddiası üretilmez.
5. Cevap, değerlendirme ve due_at yalnız ilgili kullanıcının geçmişine kaydedilir. Belirsiz sonuç eski güvenilir kaydı silmez.
6. Gerçek VSIX'te bu akış ve yeniden açılan geçmiş test edilir. Fake demo bu kabulün yerine geçmez.

Öğrenme motorunun [yerel demo ve testleri](../../services/learning/README.md) mevcut; canlı model, API/DB ve VSIX kabulü ayrı doğrulanacaktır.
