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
